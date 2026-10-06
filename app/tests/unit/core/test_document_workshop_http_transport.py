from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
import importlib
import importlib.util
import json
import ssl
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import llm_client, token_utils
from core.document_workshop_admission import prepare_document_call
from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_progress import DocumentPreparation
from core.document_workshop_provider import prepare_and_read_document
from tests.unit.core.test_document_workshop_canonical_paths import canonical
from tests.unit.core.test_document_workshop_provider_progress import VirtualClock


class LoopbackProvider:
    """Actual socket peer; no provider, transport or application consumer double."""

    def __init__(self, response=None, *, eof=False, ssl_context=None, raw_stall=False):
        self.response = response
        self.eof = eof
        self.ssl_context = ssl_context
        self.raw_stall = raw_stall
        self.requests = []
        self.received = asyncio.Event()
        self.responded = asyncio.Event()
        self.peer_closed = asyncio.Event()
        self.tasks = set()
        self.writers = set()
        self.errors = []

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        self.writers.add(writer)
        try:
            if self.raw_stall:
                # Receive a real ClientHello without replying to the handshake.
                if await reader.read(4096):
                    self.received.set()
                try:
                    await reader.read()
                except (ConnectionResetError, BrokenPipeError):
                    pass
                self.peer_closed.set()
                return
            head = await reader.readuntil(b"\r\n\r\n")
            headers = dict(line.split(b":", 1) for line in head.split(b"\r\n")[1:-2])
            body = await reader.readexactly(int(headers[b"Content-Length"]))
            self.requests.append((head, body))
            self.received.set()
            if self.response is not None:
                for part in self.response:
                    writer.write(part)
                    await writer.drain()
                    await asyncio.sleep(0)
                self.responded.set()
                if self.eof:
                    writer.write_eof()
            try:
                await reader.read()
            except (ConnectionResetError, BrokenPipeError):
                pass
            self.peer_closed.set()
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            self.peer_closed.set()
        except Exception as error:
            self.errors.append(type(error).__name__)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionResetError, BrokenPipeError):
                pass
            self.writers.discard(writer)
            self.tasks.discard(task)

    @asynccontextmanager
    async def running(self):
        server = await asyncio.start_server(self.handle, "127.0.0.1", 0, ssl=self.ssl_context)
        self.url = "%s://127.0.0.1:%d/api/v1/chat/completions?synthetic=1" % (
            "https" if self.ssl_context else "http", server.sockets[0].getsockname()[1])
        try:
            yield self
        finally:
            server.close()
            await server.wait_closed()
            for writer in tuple(self.writers):
                writer.close()
            if self.tasks:
                await asyncio.wait_for(asyncio.gather(*tuple(self.tasks)), 2)


def json_response(body):
    return (b"HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: "
            + str(len(body)).encode() + b"\r\n\r\n", body)


def document_response():
    envelope = {"schema_version": 1, "status": "prepared", "surface_text": "Document préparé.",
                "proposal": {"operation": "create", "format": "markdown", "relative_path": "Documents/test.md",
                             "source_file_ids": [], "limitations": [], "canonical": canonical()}}
    return {"model": "openai/gpt-5.1", "choices": [{"index": 0, "finish_reason": "stop",
             "message": {"content": json.dumps(envelope, ensure_ascii=False)}}]}


class DocumentHTTPTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("core.document_workshop_http_transport"),
                             "M4 transport HTTP cancellable absent")
        self.module = importlib.import_module("core.document_workshop_http_transport")
        self.transport = self.module.DocumentHTTPTransport()
        view = SimpleNamespace(payload={"model": {"value": "openai/gpt-5.1"},
                    "reasoning_effort": {"value": "medium"}, "base_url": {"value": "https://provider.invalid/api/v1"}})
        for patcher in (patch.object(llm_client.runtime_settings, "get_main_model_settings", return_value=view),
                        patch.object(llm_client, "or_headers", return_value={"Content-Type": "application/json",
                                     "Authorization": "Bearer synthetic", "X-Title": "Frida"})):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        if hasattr(self, "transport"):
            self.transport.close()
            await self.transport.wait_closed()

    def prepared(self, peer, *, stream=False):
        with patch.object(llm_client, "or_chat_completions_url", return_value=peer.url):
            return prepare_document_call([{"role": "user", "content": "Source intégrale € « test »"}],
                        count_tokens_func=token_utils.estimate_tokens, stream=stream)

    async def release(self, peer):
        self.transport.close()
        self.transport.close()
        await asyncio.wait_for(self.transport.wait_closed(), 2)
        await asyncio.wait_for(peer.peer_closed.wait(), 2)

    async def reject_response(self, raw, method="json", reason="document_provider_protocol_invalid"):
        async with LoopbackProvider(raw).running() as peer:
            with self.assertRaises(DocumentWorkshopError) as raised:
                await self.transport.send(self.prepared(peer, stream=method == "sse"))
                if method == "json":
                    await self.transport.read_json()
                else:
                    async for _ in self.transport.iter_lines():
                        pass
            self.assertEqual(raised.exception.reason_code, reason)
            self.assertEqual(str(raised.exception), reason)
            await self.release(peer)
        self.assertEqual(peer.errors, [])
        self.assertEqual(peer.tasks, set())

    async def test_frozen_admitted_bytes_and_headers_reach_real_socket_verbatim_once(self):
        expected = {"choices": [], "value": "réponse €"}
        raw = json.dumps(expected, ensure_ascii=False).encode()
        async with LoopbackProvider(json_response(raw)).running() as peer:
            prepared = self.prepared(peer)
            self.assertEqual(await self.transport.send(prepared), 200)
            self.assertEqual(await self.transport.read_json(), expected)
            head, body = peer.requests[0]
            self.assertEqual(body, prepared.body)
            self.assertTrue(head.startswith(b"POST /api/v1/chat/completions?synthetic=1 HTTP/1.1\r\n"))
            for name, value in prepared.headers:
                self.assertIn((name + ": " + value + "\r\n").encode(), head)
            self.assertIn(b"Accept-Encoding: identity\r\n", head)
            self.assertIn(b"Connection: close\r\n", head)
            with self.assertRaises(DocumentWorkshopError):
                await self.transport.send(prepared)
            await self.release(peer)
            self.assertEqual(len(peer.requests), 1)
        self.assertEqual(peer.tasks, set())

    async def test_real_chunked_sse_utf8_split_across_chunks_is_consumed(self):
        body = "data: {\"text\":\"été €\"}\r\n\r\ndata: [DONE]\n\n".encode()
        parts = [body[:22], body[22:23], body[23:31], body[31:]]
        response = [b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n"]
        response += [hex(len(part))[2:].encode() + b";synthetic=ok\r\n" + part + b"\r\n" for part in parts]
        response += [b"0\r\nX-Synthetic: yes\r\n\r\n"]
        async with LoopbackProvider(response).running() as peer:
            self.assertEqual(await self.transport.send(self.prepared(peer, stream=True)), 200)
            lines = [line async for line in self.transport.iter_lines()]
            self.assertEqual(lines, ['data: {"text":"été €"}', "", "data: [DONE]", ""])
            await self.release(peer)

    async def test_chunked_json_response_is_consumed(self):
        async with LoopbackProvider([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n",
                                   b"4\r\n{\"a\"\r\n", b"3\r\n:1}\r\n0\r\n\r\n"]).running() as peer:
            await self.transport.send(self.prepared(peer))
            self.assertEqual(await self.transport.read_json(), {"a": 1})
            await self.release(peer)

    async def test_eof_framed_json_response_is_consumed(self):
        peer = LoopbackProvider([b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"ok\":true}"])
        async with peer.running():
            task = asyncio.create_task(self.transport.send(self.prepared(peer)))
            await asyncio.wait_for(peer.responded.wait(), 2)
            for writer in tuple(peer.writers):
                writer.write_eof()
            self.assertEqual(await task, 200)
            self.assertEqual(await self.transport.read_json(), {"ok": True})
            await self.release(peer)

    async def test_close_interrupts_initial_headers_and_peer_observes_eof(self):
        async with LoopbackProvider().running() as peer:
            pending = asyncio.create_task(self.transport.send(self.prepared(peer)))
            await asyncio.wait_for(peer.received.wait(), 2)
            self.assertFalse(pending.done())
            await self.release(peer)
            with self.assertRaises(DocumentWorkshopError):
                await asyncio.wait_for(pending, 2)
            self.assertEqual(len(peer.requests), 1)

    async def test_close_interrupts_real_pending_tls_handshake_without_connection_leak(self):
        async with LoopbackProvider(raw_stall=True).running() as peer:
            prepared = replace(self.prepared(peer), url=peer.url.replace("http://", "https://"))
            pending = asyncio.create_task(self.transport.send(prepared))
            await asyncio.wait_for(peer.received.wait(), 2)
            self.assertFalse(pending.done())
            await self.release(peer)
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(pending, 2)
            self.assertEqual(peer.requests, [])
        self.assertEqual(peer.tasks, set())

    async def test_close_interrupts_json_body_and_peer_observes_eof(self):
        async with LoopbackProvider([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{"]).running() as peer:
            await self.transport.send(self.prepared(peer))
            pending = asyncio.create_task(self.transport.read_json())
            await asyncio.sleep(0)
            self.assertFalse(pending.done())
            await self.release(peer)
            with self.assertRaises(DocumentWorkshopError):
                await asyncio.wait_for(pending, 2)

    async def test_close_interrupts_sse_body_and_peer_observes_eof(self):
        async with LoopbackProvider([b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n"]).running() as peer:
            await self.transport.send(self.prepared(peer, stream=True))
            async def consume():
                return [line async for line in self.transport.iter_lines()]
            pending = asyncio.create_task(consume())
            await asyncio.sleep(0)
            self.assertFalse(pending.done())
            await self.release(peer)
            with self.assertRaises(DocumentWorkshopError):
                await asyncio.wait_for(pending, 2)

    async def test_real_m0_success_closes_peer_after_one_json_exchange(self):
        async with LoopbackProvider(json_response(json.dumps(document_response()).encode())).running() as peer:
            with patch.object(llm_client, "or_chat_completions_url", return_value=peer.url):
                result = await prepare_and_read_document([{"role": "user", "content": "Prépare un document."}],
                    transport=self.transport, count_tokens_func=token_utils.estimate_tokens, stream=False)
            self.assertEqual(result.canonical.as_dict(), canonical())
            await asyncio.wait_for(peer.peer_closed.wait(), 2)
            self.assertEqual(len(peer.requests), 1)

    async def test_real_m0_consumes_sse_terminal_and_closes_one_exchange(self):
        content = document_response()["choices"][0]["message"]["content"]
        frames = [{"model": "openai/gpt-5.1", "choices": [{"index": 0, "finish_reason": None,
                    "delta": {"content": content}}]},
                  {"model": "openai/gpt-5.1", "choices": [{"index": 0, "finish_reason": "stop", "delta": {}}]}]
        body = "".join("data: " + json.dumps(frame, ensure_ascii=False) + "\r\n\r\n" for frame in frames).encode()
        body += b"data: [DONE]\r\n\r\n"
        response = [b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n"]
        response += [hex(len(body))[2:].encode() + b"\r\n" + body + b"\r\n0\r\n\r\n"]
        async with LoopbackProvider(response).running() as peer:
            with patch.object(llm_client, "or_chat_completions_url", return_value=peer.url):
                result = await prepare_and_read_document([{"role": "user", "content": "Source"}],
                    transport=self.transport, count_tokens_func=token_utils.estimate_tokens, stream=True)
            self.assertEqual(result.canonical.as_dict(), canonical())
            await asyncio.wait_for(peer.peer_closed.wait(), 2)
            self.assertEqual(len(peer.requests), 1)

    async def test_m0_inactivity_aborts_initial_headers_socket_without_provider_event(self):
        clock = VirtualClock()
        progress = DocumentPreparation(monotonic=clock, wait_until=clock.wait_until)
        async with LoopbackProvider().running() as peer:
            with patch.object(llm_client, "or_chat_completions_url", return_value=peer.url):
                pending = asyncio.create_task(prepare_and_read_document([{"role": "user", "content": "Source"}],
                    transport=self.transport, count_tokens_func=token_utils.estimate_tokens, progress=progress, stream=False))
                await asyncio.wait_for(peer.received.wait(), 2)
                clock.advance(120)
                with self.assertRaises(DocumentWorkshopError) as raised:
                    await asyncio.wait_for(pending, 2)
            self.assertEqual(raised.exception.reason_code, "document_inactivity")
            self.assertEqual(progress.snapshot().state, "failed")
            await asyncio.wait_for(peer.peer_closed.wait(), 2)
            await self.transport.wait_closed()

    async def test_m0_cancellation_aborts_blocked_body_and_leaves_no_exchange_task(self):
        async with LoopbackProvider([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{"]).running() as peer:
            with patch.object(llm_client, "or_chat_completions_url", return_value=peer.url):
                before = asyncio.all_tasks()
                pending = asyncio.create_task(prepare_and_read_document([{"role": "user", "content": "Source"}],
                    transport=self.transport, count_tokens_func=token_utils.estimate_tokens, stream=False))
                await asyncio.wait_for(peer.responded.wait(), 2)
                pending.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(pending, 2)
            await asyncio.wait_for(peer.peer_closed.wait(), 2)
            await self.transport.wait_closed()
            await asyncio.sleep(0)
            live = {task for task in asyncio.all_tasks() - before if not task.done()}
            self.assertEqual(live, set())

    async def test_m0_inactivity_aborts_blocked_json_and_sse_read_without_late_success(self):
        cases = (
            (False, [b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{"]),
            (True, [b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n: keepalive\n\n"]),
        )
        for stream, response in cases:
            with self.subTest(stream=stream):
                self.transport = self.module.DocumentHTTPTransport()
                clock = VirtualClock()
                progress = DocumentPreparation(monotonic=clock, wait_until=clock.wait_until)
                async with LoopbackProvider(response).running() as peer:
                    with patch.object(llm_client, "or_chat_completions_url", return_value=peer.url):
                        pending = asyncio.create_task(prepare_and_read_document([{"role": "user", "content": "Source"}],
                            transport=self.transport, count_tokens_func=token_utils.estimate_tokens,
                            progress=progress, stream=stream))
                        await asyncio.wait_for(peer.responded.wait(), 2)
                        clock.advance(120)
                        with self.assertRaises(DocumentWorkshopError) as raised:
                            await asyncio.wait_for(pending, 2)
                    self.assertEqual(raised.exception.reason_code, "document_inactivity")
                    self.assertEqual(progress.snapshot().received_content_codepoints, 0)
                    self.assertEqual(progress.snapshot().state, "failed")
                    await asyncio.wait_for(peer.peer_closed.wait(), 2)
                    await self.transport.wait_closed()
                    with self.assertRaises(DocumentWorkshopError):
                        await self.transport.read_json()

    async def test_response_protocol_rejects_ambiguous_framing_encoding_and_headers(self):
        cases = (
            b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: gzip, chunked\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length: -1\r\n\r\n",
            b"HTTP/1.1 200 OK\r\n folded: bad\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nX-Test: raw\x00provider\r\n\r\n",
            b"invalid status\r\n\r\n",
        )
        for raw in cases:
            with self.subTest(case=cases.index(raw)):
                self.transport = self.module.DocumentHTTPTransport()
                await self.reject_response([raw])

    async def test_body_protocol_rejects_invalid_json_and_utf8_content_free(self):
        for raw in (b"{", b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":"\xff"}'):
            with self.subTest(case=len(raw)):
                self.transport = self.module.DocumentHTTPTransport()
                await self.reject_response(json_response(raw))

    async def test_sse_rejects_invalid_utf8_without_replacement(self):
        await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: 8\r\n\r\n",
                                    b"data: \xff\n"], method="sse")

    async def test_network_bound_rejects_announced_oversize_before_body_read(self):
        await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Length: 33554433\r\n\r\n"],
                                    reason="document_provider_network_limit")

    async def test_network_bound_counts_chunked_decoded_bytes(self):
        with patch.object(self.module, "MAX_RESPONSE_BYTES", 1024):
            await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n",
                b"258\r\n" + b"x" * 600 + b"\r\n258\r\n" + b"x" * 600 + b"\r\n0\r\n\r\n"],
                reason="document_provider_network_limit")

    async def test_network_bound_includes_chunk_framing_not_only_decoded_body(self):
        chunks = [b"1;" + b"synthetic=" + b"x" * 300 + b"\r\n" + char + b"\r\n" for char in (b" ", b" ", b"{", b"}")]
        with patch.object(self.module, "MAX_RESPONSE_BYTES", 1024):
            await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n",
                                        *chunks, b"0\r\n\r\n"], reason="document_provider_network_limit")

    async def test_large_provider_envelope_has_network_space_beyond_canonical_limit(self):
        body = json.dumps({"synthetic": "x" * (1048576 + 65536)}).encode()
        async with LoopbackProvider(json_response(body)).running() as peer:
            await self.transport.send(self.prepared(peer))
            self.assertEqual(len((await self.transport.read_json())["synthetic"]), 1114112)
            await self.release(peer)

    async def test_oversize_headers_are_bounded_before_end_marker(self):
        await self.reject_response([b"HTTP/1.1 200 OK\r\nX-Test: " + b"x" * 65536],
                                    reason="document_provider_network_limit")

    async def test_invalid_chunk_size_and_terminator_are_rejected(self):
        for body in (b"X\r\n", b"1\r\nx!!", b"+1\r\nx\r\n"):
            with self.subTest(case=body[:2]):
                self.transport = self.module.DocumentHTTPTransport()
                await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n", body])

    async def test_request_framing_injection_is_refused_before_any_socket(self):
        async with LoopbackProvider(json_response(b"{}")).running() as peer:
            good = self.prepared(peer)
            cases = (replace(good, headers=good.headers + (("Content-Length", "1"),)),
                     replace(good, headers=good.headers + (("X-Test", "value\r\nInjected: yes"),)),
                     replace(good, url=peer.url + "\r\nInjected"),
                     replace(good, url=peer.url + "#fragment"),
                     replace(good, url=peer.url.replace("http://", "http://user:password@")))
            for prepared in cases:
                self.transport = self.module.DocumentHTTPTransport()
                with self.assertRaises(DocumentWorkshopError) as raised:
                    await self.transport.send(prepared)
                self.assertEqual(raised.exception.reason_code, "document_provider_protocol_invalid")
                await self.transport.wait_closed()
            self.assertEqual(peer.requests, [])
            self.assertEqual(peer.tasks, set())

    async def test_premature_eof_is_refused_for_content_length_and_chunked(self):
        cases = (b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{}",
                 b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n")
        for raw in cases:
            with self.subTest(framing=cases.index(raw)):
                self.transport = self.module.DocumentHTTPTransport()
                async with LoopbackProvider([raw], eof=True).running() as peer:
                    await self.transport.send(self.prepared(peer))
                    with self.assertRaises(DocumentWorkshopError) as raised:
                        await self.transport.read_json()
                    self.assertEqual(raised.exception.reason_code, "document_provider_protocol_invalid")
                    await self.release(peer)

    async def test_sse_lines_accept_cr_lf_and_crlf_across_response_chunks(self):
        body = [b"data: first\r", b"\n\r", b"data: second\ndata: last\r"]
        async with LoopbackProvider([b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: 38\r\n\r\n", *body]).running() as peer:
            await self.transport.send(self.prepared(peer, stream=True))
            self.assertEqual([line async for line in self.transport.iter_lines()],
                             ["data: first", "", "data: second", "data: last"])
            await self.release(peer)

    async def test_eof_network_bound_is_enforced_without_waiting_for_peer_close(self):
        with patch.object(self.module, "MAX_RESPONSE_BYTES", 1024):
            await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n", b"x" * 1025],
                                       reason="document_provider_network_limit")

    async def test_trailer_framing_cannot_replace_response_authority(self):
        await self.reject_response([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n",
                                    b"2\r\n{}\r\n0\r\nContent-Length: 2\r\n\r\n"])

    async def test_tls_verifies_certificate_on_real_loopback_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            certificate = directory + "/synthetic-cert.pem"
            key = directory + "/synthetic-key.pem"
            await asyncio.to_thread(subprocess.run, ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-keyout", key, "-out", certificate, "-subj", "/CN=synthetic.invalid",
                "-addext", "subjectAltName=IP:127.0.0.1"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_context.load_cert_chain(certificate, key)
            loop = asyncio.get_running_loop()
            original_handler = loop.get_exception_handler()
            handshake_failures = []
            loop.set_exception_handler(lambda _loop, context: handshake_failures.append(type(context.get("exception")).__name__))
            try:
                async with LoopbackProvider(json_response(b'{"ok":true}'), ssl_context=server_context).running() as peer:
                    with self.assertRaises(DocumentWorkshopError) as raised:
                        await self.transport.send(self.prepared(peer))
                    self.assertEqual(str(raised.exception), "document_provider_error")
                    self.assertEqual(peer.requests, [])
                    await self.transport.wait_closed()
                verified = ssl.create_default_context(cafile=certificate)
                self.assertTrue(verified.check_hostname)
                self.assertEqual(verified.verify_mode, ssl.CERT_REQUIRED)
                self.transport = self.module.DocumentHTTPTransport()
                async with LoopbackProvider(json_response(b'{"ok":true}'), ssl_context=server_context).running() as peer:
                    wrong_hostname = replace(self.prepared(peer), url=peer.url.replace("127.0.0.1", "localhost"))
                    with patch.object(self.module.ssl, "create_default_context", return_value=verified):
                        with self.assertRaises(DocumentWorkshopError) as raised:
                            await self.transport.send(wrong_hostname)
                    self.assertEqual(str(raised.exception), "document_provider_error")
                    self.assertEqual(peer.requests, [])
                    await self.transport.wait_closed()
                self.transport = self.module.DocumentHTTPTransport()
                async with LoopbackProvider(json_response(b'{"ok":true}'), ssl_context=server_context).running() as peer:
                    with patch.object(self.module.ssl, "create_default_context", return_value=verified), \
                         patch.object(self.module.asyncio, "open_connection", wraps=asyncio.open_connection) as connect:
                        await self.transport.send(self.prepared(peer))
                    self.assertEqual(connect.call_args.kwargs.get("ssl_handshake_timeout"), 120)
                    self.assertEqual(await self.transport.read_json(), {"ok": True})
                    await self.release(peer)
                self.assertTrue(all(name in {"SSLError", "ConnectionResetError"} for name in handshake_failures))
            finally:
                loop.set_exception_handler(original_handler)


if __name__ == "__main__":
    unittest.main()
