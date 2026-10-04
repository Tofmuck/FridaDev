from __future__ import annotations

import asyncio
import copy
import importlib
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import llm_client, token_utils
from tests.unit.core.test_document_workshop_canonical_paths import canonical


class VirtualClock:
    def __init__(self):
        self.now = 0.0
        self.waiters = []

    def __call__(self):
        return self.now

    async def wait_until(self, deadline):
        if self.now >= deadline:
            return
        future = asyncio.get_running_loop().create_future()
        entry = (deadline, future)
        self.waiters.append(entry)
        try:
            await future
        finally:
            self.waiters.remove(entry)

    def advance(self, seconds):
        self.now += seconds
        for deadline, future in tuple(self.waiters):
            if self.now >= deadline and not future.done():
                future.set_result(None)


async def settle():
    for _ in range(12):
        await asyncio.sleep(0)


def response(*, finish="stop", content=None, model="openai/gpt-5.1"):
    return {
        "model": model,
        "choices": [{"index": 0, "finish_reason": finish, "message": {
            "role": "assistant", "content": json.dumps(canonical(), ensure_ascii=False) if content is None else content,
            "reasoning": "synthetic hidden reasoning", "reasoning_details": [{"text": "synthetic hidden reasoning"}],
        }}],
        "usage": {"prompt_tokens": 32, "completion_tokens": 77, "total_tokens": 109,
                  "completion_tokens_details": {"reasoning_tokens": 7}},
    }


def event(chunk, delay=0):
    return [(delay, "data: " + json.dumps(chunk, ensure_ascii=False)), (0, "")]


def stream_events(text=None, *, finish="stop", done=True):
    text = json.dumps(canonical(), ensure_ascii=False) if text is None else text
    chunks = event({"model": "openai/gpt-5.1", "choices": [{"index": 0, "delta": {"content": text, "reasoning": "synthetic hidden reasoning"}, "finish_reason": None}]})
    chunks += event({"model": "openai/gpt-5.1", "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
    chunks += event({"model": "openai/gpt-5.1", "choices": [], "usage": {"prompt_tokens": 32, "completion_tokens": 77, "total_tokens": 109}})
    return chunks + ([(0, "data: [DONE]"), (0, "")] if done else [])


class SimulatedTransport:
    """Owned async HTTP boundary; only provider I/O is substituted."""
    def __init__(self, *, payload=None, lines=(), clock=None, status=200, blocked=False, late=False, blocked_send=False):
        self.payload = response() if payload is None else payload
        self.lines = lines
        self.clock = clock
        self.status = status
        self.blocked = blocked
        self.late = late
        self.blocked_send = blocked_send
        self.release = asyncio.Event()
        self.read_returned = asyncio.Event()
        self.sent = []
        self.close_count = 0
        self.line_count = 0

    async def send(self, prepared):
        self.sent.append(prepared)
        if self.blocked_send:
            await self.release.wait()
        return self.status

    async def read_json(self):
        if self.blocked:
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                if not self.late:
                    raise
                await self.release.wait()
        self.read_returned.set()
        if isinstance(self.payload, Exception):
            raise self.payload
        return copy.deepcopy(self.payload)

    async def iter_lines(self):
        for delay, line in self.lines:
            if self.clock:
                self.clock.advance(delay)
            self.line_count += 1
            yield line
        if self.blocked:
            await self.release.wait()

    def close(self):
        self.close_count += 1
        if not self.late:
            self.release.set()


class DocumentProviderProgressTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for name in ("core.document_workshop_provider", "core.document_workshop_progress"):
            self.assertIsNotNone(importlib.util.find_spec(name), "M0 provider/progress interface absent")
        self.provider = importlib.import_module("core.document_workshop_provider")
        self.progress_module = importlib.import_module("core.document_workshop_progress")
        self.error = importlib.import_module("core.document_workshop_contract").DocumentWorkshopError
        self.clock = VirtualClock()
        self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
        view = SimpleNamespace(payload={"model": {"value": "openai/gpt-5.1"}, "reasoning_effort": {"value": "medium"}, "base_url": {"value": "https://provider.invalid/api/v1"}})
        for patcher in (
            patch.object(llm_client.runtime_settings, "get_main_model_settings", return_value=view),
            patch.object(llm_client, "or_headers", return_value={"Content-Type": "application/json", "Authorization": "synthetic"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def run_call(self, transport, *, stream=False, counter=token_utils.estimate_tokens, messages=None):
        return await self.provider.prepare_and_read_document(
            messages or [{"role": "system", "content": "Prompt spécialisé synthétique"}, {"role": "user", "content": "Source intégrale " * 30}],
            transport=transport, count_tokens_func=counter, progress=self.progress, stream=stream,
        )

    async def reject(self, transport, code, **kwargs):
        with self.assertRaises(self.error) as raised:
            await self.run_call(transport, **kwargs)
        self.assertEqual(raised.exception.reason_code, code)
        self.assertEqual(str(raised.exception), code)
        self.assertEqual(transport.close_count, 1)

    async def test_actual_shared_admission_builder_and_simulated_send(self):
        transport = SimulatedTransport()
        result = await self.run_call(transport, messages=[{"role": "user", "content": json.dumps({"source_pages": 35, "source_text": "entière " * 300, "metadata": {"version": "v2"}}, ensure_ascii=False)}])
        self.assertEqual(len(transport.sent), 1)
        call = transport.sent[0]
        payload = json.loads(call.body)
        self.assertEqual(payload["max_tokens"], 24000)
        self.assertEqual(payload["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(call.admission.estimated_input_tokens, token_utils.estimate_tokens(payload["messages"], payload["model"]))
        self.assertEqual(result.canonical.as_dict(), canonical())
        self.assertEqual(result.state, "complete")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.model, "openai/gpt-5.1")
        self.assertEqual(result.provider_usage.prompt_tokens, 32)
        self.assertEqual(result.provider_usage.completion_tokens, 77)
        self.assertEqual(result.provider_usage.total_tokens, 109)
        self.assertEqual(result.provider_usage.reasoning_tokens, 7)
        self.assertNotIn("hidden reasoning", repr(result))
        self.assertNotIn("hidden reasoning", json.dumps(result.canonical.as_dict()))
        self.assertEqual(transport.close_count, 1)
        self.assertEqual(self.progress.snapshot().state, "succeeded")

    async def test_refused_estimate_never_sends(self):
        transport = SimulatedTransport()
        await self.reject(transport, "document_estimated_context_limit", counter=lambda *_: 376001)
        self.assertEqual(transport.sent, [])

    async def test_counter_exception_never_sends_and_is_content_free(self):
        def broken(*_):
            raise ValueError("synthetic raw private exception")
        transport = SimulatedTransport()
        await self.reject(transport, "document_estimation_unavailable", counter=broken)
        self.assertEqual(transport.sent, [])

    async def test_complete_json_with_length_refused_without_repair(self):
        transport = SimulatedTransport(payload=response(finish="length"))
        await self.reject(transport, "document_provider_length")
        self.assertEqual(len(transport.sent), 1)

    async def test_nonstream_empty_missing_terminal_invalid_json_or_canonical_refused(self):
        cases = (
            (response(content=""), "document_provider_empty"),
            (response(finish=None), "document_provider_incomplete"),
            (response(content="{"), "document_canonical_invalid"),
            (response(content='{}'), "document_canonical_invalid"),
            (response(content=json.dumps(canonical("x" * 75001))), "document_character_limit"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
                await self.reject(SimulatedTransport(payload=payload), code)

    async def test_provider_context_error_refusal_http_and_exception_have_no_fallthrough(self):
        cases = (
            (SimulatedTransport(payload={"error": {"code": "context_length_exceeded", "message": "synthetic raw provider text"}}), "document_provider_context_limit"),
            (SimulatedTransport(payload={"error": {"message": "synthetic raw provider text"}}), "document_provider_error"),
            (SimulatedTransport(status=413), "document_provider_context_limit"),
            (SimulatedTransport(status=500), "document_provider_error"),
            (SimulatedTransport(payload=RuntimeError("synthetic raw provider exception")), "document_provider_error"),
        )
        refusal = response()
        refusal["choices"][0]["message"]["refusal"] = "synthetic refusal"
        cases += ((SimulatedTransport(payload=refusal), "document_provider_refused"),)
        for transport, code in cases:
            with self.subTest(code=code):
                self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
                await self.reject(transport, code)
                self.assertEqual(len(transport.sent), 1)

    async def test_reported_usage_reuses_existing_extractor_and_absence_not_invented(self):
        with patch.object(llm_client, "extract_openrouter_provider_metadata", wraps=llm_client.extract_openrouter_provider_metadata) as extractor:
            result = await self.run_call(SimulatedTransport())
        self.assertGreater(extractor.call_count, 0)
        self.assertEqual(result.provider_usage.total_tokens, 109)
        self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
        payload = response()
        del payload["usage"]
        result = await self.run_call(SimulatedTransport(payload=payload))
        self.assertIsNone(result.provider_usage)

    async def test_reported_completion_over_budget_refused(self):
        payload = response()
        payload["usage"]["completion_tokens"] = 24001
        await self.reject(SimulatedTransport(payload=payload), "document_provider_output_limit")

    async def test_reported_context_overflow_without_total_is_refused(self):
        for usage in (
            {"prompt_tokens": 400001},
            {"prompt_tokens": 399990, "completion_tokens": 11},
            {"prompt_tokens": 400001, "total_tokens": 1},
            {"prompt_tokens": 399990, "completion_tokens": 11, "total_tokens": 10},
            {"prompt_tokens": 399990, "completion_tokens_details": {"reasoning_tokens": 11}},
        ):
            with self.subTest(usage=usage):
                self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
                payload = response()
                payload["usage"] = usage
                await self.reject(SimulatedTransport(payload=payload), "document_provider_context_limit")
        self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
        payload = response()
        payload["usage"] = {"prompt_tokens": 399990, "completion_tokens": 10,
                            "completion_tokens_details": {"reasoning_tokens": 5}}
        result = await self.run_call(SimulatedTransport(payload=payload))
        self.assertEqual(result.provider_usage.prompt_tokens, 399990)
        self.assertEqual(result.provider_usage.completion_tokens, 10)
        self.assertIsNone(result.provider_usage.total_tokens)

    async def test_streamed_usage_components_merge_before_context_check(self):
        lines = stream_events()[:-4]
        lines += event({"choices": [], "usage": {"prompt_tokens": 399990}})
        lines += event({"choices": [], "usage": {"completion_tokens": 11}})
        lines += [(0, "data: [DONE]"), (0, "")]
        await self.reject(SimulatedTransport(lines=lines), "document_provider_context_limit", stream=True)

    async def test_model_change_or_model_absence_refused(self):
        for model in ("another/model", None):
            self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
            await self.reject(SimulatedTransport(payload=response(model=model)), "document_provider_model_invalid")

    async def test_stream_is_consumed_and_terminal_usage_preserved(self):
        lines = stream_events()
        transport = SimulatedTransport(lines=lines)
        result = await self.run_call(transport, stream=True)
        self.assertEqual(transport.line_count, len(lines))
        self.assertEqual(result.canonical.as_dict(), canonical())
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.provider_usage.total_tokens, 109)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.close_count, 1)

    async def test_done_control_or_reasoning_only_cannot_prove_document(self):
        streams = (
            [(0, ": heartbeat"), (0, ""), (0, "data: [DONE]"), (0, "")],
            event({"model": "openai/gpt-5.1", "choices": [{"delta": {"reasoning": "hidden"}, "finish_reason": "stop"}]}) + [(0, "data: [DONE]"), (0, "")],
        )
        for lines in streams:
            self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
            with self.assertRaises(self.error):
                await self.run_call(SimulatedTransport(lines=lines), stream=True)
            self.assertEqual(self.progress.snapshot().received_content_codepoints, 0)

    async def test_stream_length_no_done_and_error_frames_refused(self):
        cases = (
            (stream_events(finish="length"), "document_provider_length"),
            (stream_events(done=False), "document_provider_incomplete"),
            (event({"error": {"code": "context_length_exceeded", "message": "synthetic raw"}}), "document_provider_context_limit"),
            ([(0, "data: {"), (0, "")], "document_provider_protocol_invalid"),
        )
        for lines, code in cases:
            self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
            await self.reject(SimulatedTransport(lines=lines), code, stream=True)

    async def test_valid_multiline_sse_and_post_terminal_content_refused(self):
        raw = json.dumps({"model": "openai/gpt-5.1", "choices": [{"delta": {"content": json.dumps(canonical(), ensure_ascii=False)}, "finish_reason": "stop"}]}, ensure_ascii=False, indent=2)
        lines = [(0, "data: " + line) for line in raw.splitlines()] + [(0, ""), (0, "data: [DONE]"), (0, "")]
        result = await self.run_call(SimulatedTransport(lines=lines), stream=True)
        self.assertEqual(result.canonical.as_dict(), canonical())
        self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
        lines = stream_events()[:-2] + event({"choices": [{"delta": {"content": "late"}, "finish_reason": None}]}) + [(0, "data: [DONE]"), (0, "")]
        await self.reject(SimulatedTransport(lines=lines), "document_provider_incomplete", stream=True)

    async def test_stream_valid_json_without_finish_and_malformed_usage_refused(self):
        lines = event({"model": "openai/gpt-5.1", "choices": [{"delta": {"content": json.dumps(canonical())}, "finish_reason": None}]}) + [(0, "data: [DONE]"), (0, "")]
        await self.reject(SimulatedTransport(lines=lines), "document_provider_incomplete", stream=True)
        for malformed in (True, -1, "77", 77.0):
            self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
            payload = response()
            payload["usage"]["completion_tokens"] = malformed
            await self.reject(SimulatedTransport(payload=payload), "document_provider_protocol_invalid")

    async def test_initial_cancel_and_failed_transport_release_do_not_succeed(self):
        self.progress.cancel()
        transport = SimulatedTransport()
        await self.reject(transport, "document_cancelled")
        self.assertEqual(transport.sent, [])
        self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
        transport = SimulatedTransport()
        def broken_close():
            transport.close_count += 1
            raise RuntimeError("synthetic raw private transport exception")
        transport.close = broken_close
        await self.reject(transport, "document_transport_close_failed")
        self.assertEqual(self.progress.snapshot().state, "failed")

    async def test_useful_stream_progress_allows_total_duration_over_120(self):
        text = json.dumps(canonical(), ensure_ascii=False)
        parts = (text[:50], text[50:100], text[100:])
        lines = []
        for part in parts:
            lines += event({"model": "openai/gpt-5.1", "choices": [{"delta": {"content": part}, "finish_reason": None}]}, delay=119)
        lines += event({"model": "openai/gpt-5.1", "choices": [{"delta": {}, "finish_reason": "stop"}]})
        lines += [(0, "data: [DONE]"), (0, "")]
        result = await self.run_call(SimulatedTransport(lines=lines, clock=self.clock), stream=True)
        self.assertEqual(self.clock.now, 357)
        self.assertEqual(result.canonical.as_dict(), canonical())
        self.assertEqual(self.progress.snapshot().received_content_codepoints, len(text))

    async def test_first_wait_blocked_read_exact_threshold_and_close(self):
        transport = SimulatedTransport(blocked=True)
        task = asyncio.create_task(self.run_call(transport))
        await settle()
        self.clock.advance(119.999)
        await settle()
        self.assertFalse(task.done())
        self.clock.advance(0.001)
        with self.assertRaises(self.error) as raised:
            await asyncio.wait_for(task, 0.5)
        self.assertEqual(raised.exception.reason_code, "document_inactivity")
        self.assertEqual(transport.close_count, 1)
        self.assertEqual(len(transport.sent), 1)

    async def test_blocked_open_is_also_covered(self):
        transport = SimulatedTransport(blocked_send=True)
        task = asyncio.create_task(self.run_call(transport))
        await settle()
        self.clock.advance(120)
        with self.assertRaises(self.error) as raised:
            await asyncio.wait_for(task, 0.5)
        self.assertEqual(raised.exception.reason_code, "document_inactivity")
        self.assertEqual(transport.close_count, 1)

    async def test_continuous_keepalives_empty_or_reasoning_chunks_do_not_reset(self):
        for line in (": keepalive", "data: " + json.dumps({"choices": [{"delta": {"content": ""}, "finish_reason": None}]}), "data: " + json.dumps({"choices": [{"delta": {"reasoning": "hidden"}, "finish_reason": None}]})):
            self.clock = VirtualClock()
            self.progress = self.progress_module.DocumentPreparation(monotonic=self.clock, wait_until=self.clock.wait_until)
            lines = [(1, line), (0, "")] * 121
            transport = SimulatedTransport(lines=lines, clock=self.clock)
            await self.reject(transport, "document_inactivity", stream=True)
            self.assertEqual(self.clock.now, 120)
            self.assertEqual(self.progress.snapshot().received_content_codepoints, 0)

    async def test_cancellation_is_prompt_and_no_late_result_can_succeed(self):
        transport = SimulatedTransport(blocked=True, late=True)
        task = asyncio.create_task(self.run_call(transport))
        await settle()
        self.progress.cancel()
        try:
            with self.assertRaises(self.error) as raised:
                await asyncio.wait_for(task, 0.5)
            self.assertEqual(raised.exception.reason_code, "document_cancelled")
            self.assertEqual(transport.close_count, 1)
        finally:
            transport.release.set()
        await asyncio.wait_for(transport.read_returned.wait(), 0.5)
        await settle()
        self.assertEqual(self.progress.snapshot().state, "cancelled")

    async def test_inactivity_late_result_is_neutralized(self):
        transport = SimulatedTransport(blocked=True, late=True)
        task = asyncio.create_task(self.run_call(transport))
        await settle()
        self.clock.advance(120)
        try:
            with self.assertRaises(self.error) as raised:
                await asyncio.wait_for(task, 0.5)
            self.assertEqual(raised.exception.reason_code, "document_inactivity")
        finally:
            transport.release.set()
        await asyncio.wait_for(transport.read_returned.wait(), 0.5)
        await settle()
        self.assertEqual(self.progress.snapshot().state, "failed")
        self.assertEqual(transport.close_count, 1)

    async def test_caller_task_cancellation_closes_transport(self):
        transport = SimulatedTransport(blocked=True)
        task = asyncio.create_task(self.run_call(transport))
        await settle()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(transport.close_count, 1)
        self.assertEqual(self.progress.snapshot().state, "cancelled")

    async def test_synchronous_preparation_cannot_hide_elapsed_inactivity(self):
        def stalled_counter(*_):
            self.clock.advance(120)
            return 1
        transport = SimulatedTransport()
        await self.reject(transport, "document_inactivity", counter=stalled_counter)
        self.assertEqual(transport.sent, [])

    async def test_steps_cannot_be_repeated_to_manufacture_progress(self):
        self.progress.complete_step("payload_prepared")
        self.clock.advance(60)
        with self.assertRaises(self.error):
            self.progress.complete_step("payload_prepared")
        self.clock.advance(60)
        with self.assertRaises(self.error) as raised:
            self.progress.check()
        self.assertEqual(raised.exception.reason_code, "document_inactivity")

    async def test_same_preparation_does_not_send_twice(self):
        first = SimulatedTransport()
        await self.run_call(first)
        second = SimulatedTransport()
        await self.reject(second, "document_preparation_closed")
        self.assertEqual(second.sent, [])


if __name__ == "__main__":
    unittest.main()
