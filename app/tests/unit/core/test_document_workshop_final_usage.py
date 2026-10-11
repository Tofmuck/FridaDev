"""OpenRouter final accounting frame through the real reader and HTTP socket."""
import asyncio
import json
import unittest
from unittest.mock import patch

from core import llm_client, token_utils
from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_progress import DocumentPreparation
from core.document_workshop_provider import prepare_and_read_document
from tests.unit.core import test_document_workshop_http_transport as http
from tests.unit.core.test_document_workshop_canonical_paths import canonical


def chunk(delta=None, reason=None, **metadata):
    return dict(model='openai/gpt-5.1', choices=[dict(index=0, delta=delta or {},
                finish_reason=reason, native_finish_reason=reason)], **metadata)


def document_frames():
    content = http.document_response()['choices'][0]['message']['content']
    return [chunk(dict(content=content)), chunk(dict(content='', role='assistant'), 'stop')]


def final_usage():
    return chunk(dict(content='', role='assistant'), 'stop',
                 usage=dict(prompt_tokens=123, completion_tokens=17, total_tokens=140,
                            completion_tokens_details=dict(reasoning_tokens=3)))


class FinalUsageHTTPTests(unittest.IsolatedAsyncioTestCase):
    # Reuse socket/settings ownership without inheriting and recounting tests.
    setUp = http.DocumentHTTPTransportTests.setUp
    asyncTearDown = http.DocumentHTTPTransportTests.asyncTearDown
    release = http.DocumentHTTPTransportTests.release

    async def read(self, frames, *, done=True):
        self.transport = self.module.DocumentHTTPTransport()
        self.progress = DocumentPreparation()
        body = ''.join('data: ' + json.dumps(frame) + '\n\n' for frame in frames).encode()
        if done:
            body += b'data: [DONE]\n\n'
        response = [b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: '
                    + str(len(body)).encode() + b'\r\n\r\n', body]
        async with http.LoopbackProvider(response).running() as peer:
            try:
                with patch.object(llm_client, 'or_chat_completions_url', return_value=peer.url):
                    return await asyncio.wait_for(prepare_and_read_document([dict(role='user', content='Synthetic')],
                        transport=self.transport, count_tokens_func=token_utils.estimate_tokens,
                        progress=self.progress, stream=True), 2)
            finally:
                await self.release(peer)
                self.assertEqual(len(peer.requests), 1)
                self.assertEqual(peer.errors, [])

    async def test_documented_final_usage_repeating_stop_keeps_exact_canonical_and_usage(self):
        try:
            result = await self.read(document_frames() + [final_usage()])
        except DocumentWorkshopError as error:
            self.fail(f'Documented accounting frame rejected: {error.reason_code}; {error.sse_rejection}')
        self.assertEqual(result.canonical.as_dict(), canonical())
        self.assertEqual(result.finish_reason, 'stop')
        self.assertEqual(result.model, 'openai/gpt-5.1')
        self.assertEqual((result.provider_usage.prompt_tokens, result.provider_usage.completion_tokens,
                          result.provider_usage.total_tokens, result.provider_usage.reasoning_tokens), (123,17,140,3))
        self.assertEqual(self.progress.snapshot().state, 'succeeded')

    async def test_accounting_frame_merges_valid_partial_usage_after_content_bearing_stop(self):
        content = http.document_response()['choices'][0]['message']['content']
        for delta in ({}, dict(content=None), dict(content='', role='assistant')):
            with self.subTest(delta=delta):
                frames = [chunk(dict(content=content), 'stop', usage=dict(completion_tokens=17)),
                          chunk(delta, 'stop', usage=dict(prompt_tokens=123, total_tokens=140))]
                result = await self.read(frames)
                self.assertEqual(result.canonical.as_dict(), canonical())
                self.assertEqual((result.provider_usage.prompt_tokens, result.provider_usage.completion_tokens,
                                  result.provider_usage.total_tokens), (123,17,140))

    async def test_accounting_exception_keeps_nearby_rejections_and_diagnostics(self):
        valid_usage = dict(prompt_tokens=123, completion_tokens=17, total_tokens=140)
        cases = [
            ('bare', chunk({}, 'stop'), 'document_provider_incomplete', 'duplicate_stop'),
            ('empty_usage', chunk({}, 'stop', usage={}), 'document_provider_incomplete', 'duplicate_stop'),
            ('unrecognized_usage_only', chunk({}, 'stop', usage=dict(cost=1)), 'document_provider_incomplete', 'duplicate_stop'),
            ('null_usage', chunk({}, 'stop', usage=None), 'document_provider_incomplete', 'duplicate_stop'),
            ('late_content', chunk(dict(content='PRIVATE_SENTINEL'), 'stop', usage=valid_usage), 'document_provider_incomplete', 'content_after_stop'),
            ('tool_call', chunk(dict(tool_calls=[dict(name='PRIVATE_SENTINEL')]), 'stop', usage=valid_usage), 'document_provider_incomplete', 'tool_call'),
            ('function_call', chunk(dict(function_call=dict(name='PRIVATE_SENTINEL')), 'stop', usage=valid_usage), 'document_provider_incomplete', 'tool_call'),
            ('refusal', chunk(dict(refusal='PRIVATE_SENTINEL'), 'stop', usage=valid_usage), 'document_provider_refused', None),
            ('empty_tool_key', chunk(dict(tool_calls=[]), 'stop', usage=valid_usage), 'document_provider_incomplete', 'duplicate_stop'),
            ('empty_refusal_key', chunk(dict(refusal=None), 'stop', usage=valid_usage), 'document_provider_incomplete', 'duplicate_stop'),
            ('wrong_role', chunk(dict(role='user'), 'stop', usage=valid_usage), 'document_provider_incomplete', 'duplicate_stop'),
            ('unknown_delta', chunk(dict(other='PRIVATE_SENTINEL'), 'stop', usage=valid_usage), 'document_provider_incomplete', 'duplicate_stop'),
            ('length', chunk({}, 'length', usage=valid_usage), 'document_provider_length', None),
            ('filtered', chunk({}, 'content_filter', usage=valid_usage), 'document_provider_refused', None),
            ('error', chunk({}, 'error', usage=valid_usage), 'document_provider_error', None),
            ('unknown_terminal', chunk({}, 'PRIVATE_SENTINEL', usage=valid_usage), 'document_provider_incomplete', 'unrecognized_terminal_reason'),
            ('provider_error', chunk({}, 'stop', usage=valid_usage, error=dict(code=500,message='PRIVATE_SENTINEL')), 'document_provider_error', None),
            ('usage_type', chunk({}, 'stop', usage=[]), 'document_provider_protocol_invalid', None),
            ('usage_negative', chunk({}, 'stop', usage=dict(completion_tokens=-1)), 'document_provider_protocol_invalid', None),
            ('usage_bool', chunk({}, 'stop', usage=dict(prompt_tokens=True)), 'document_provider_protocol_invalid', None),
            ('usage_text', chunk({}, 'stop', usage=dict(total_tokens='PRIVATE_SENTINEL')), 'document_provider_protocol_invalid', None),
            ('completion_limit', chunk({}, 'stop', usage=dict(completion_tokens=24001)), 'document_provider_output_limit', None),
            ('reasoning_limit', chunk({}, 'stop', usage=dict(completion_tokens_details=dict(reasoning_tokens=24001))), 'document_provider_output_limit', None),
            ('total_limit', chunk({}, 'stop', usage=dict(total_tokens=400001)), 'document_provider_context_limit', None),
            ('partial_context_limit', chunk({}, 'stop', usage=dict(prompt_tokens=399999,completion_tokens=17)), 'document_provider_context_limit', None),
        ]
        for label, field, value, reason in (
                ('missing_index', 'index', None, 'document_provider_incomplete'),
                ('wrong_index', 'index', 1, 'document_provider_protocol_invalid'),
                ('bool_index', 'index', True, 'document_provider_protocol_invalid')):
            frame = final_usage()
            if value is None:
                del frame['choices'][0][field]
            else:
                frame['choices'][0][field] = value
            cases.append((label, frame, reason, 'duplicate_stop' if value is None else None))
        changed_model = final_usage() | dict(model='PRIVATE_SENTINEL')
        cases.append(('changed_model', changed_model, 'document_provider_model_invalid', None))
        for label, frame, reason, site in cases:
            with self.subTest(case=label):
                with self.assertRaises(DocumentWorkshopError) as raised:
                    await self.read(document_frames() + [frame])
                self.assertEqual(raised.exception.reason_code, reason)
                self.assertEqual(str(raised.exception), reason)
                self.assertEqual(self.progress.snapshot().state, 'failed')
                diagnostic = raised.exception.sse_rejection
                if site:
                    self.assertEqual(diagnostic.site, site)
                    self.assertTrue(diagnostic.stop_observed)
                    self.assertFalse(diagnostic.done_observed)
                    self.assertEqual(diagnostic.http_end, 'content_length_consumed')
                else:
                    self.assertIsNone(diagnostic)
                self.assertNotIn('PRIVATE_SENTINEL', repr(diagnostic))

    async def test_final_usage_still_requires_done_and_cannot_repeat_twice(self):
        cases = (([final_usage()], False, 'sse_without_done'),
                 ([final_usage(), final_usage()], True, 'duplicate_stop'),
                 ([final_usage(), chunk(dict(content='PRIVATE_SENTINEL'))], True, 'content_after_stop'),
                 ([final_usage(), chunk({}, 'stop', usage=dict(total_tokens=400001))], True, None))
        for extra, done, site in cases:
            with self.subTest(site=site, done=done):
                with self.assertRaises(DocumentWorkshopError) as raised:
                    await self.read(document_frames() + extra, done=done)
                self.assertEqual(raised.exception.reason_code,
                                 'document_provider_incomplete' if site else 'document_provider_context_limit')
                if site:
                    self.assertEqual(raised.exception.sse_rejection.site, site)
                    self.assertTrue(raised.exception.sse_rejection.stop_observed)
                    self.assertFalse(raised.exception.sse_rejection.done_observed)

    async def test_cancellation_and_inactivity_after_accounting_still_abort_real_socket(self):
        wire = ''.join('data: ' + json.dumps(frame) + '\n\n'
                       for frame in document_frames() + [final_usage()]).encode()
        for mode in ('cancel', 'inactivity'):
            with self.subTest(mode=mode):
                blocked = asyncio.Event()
                class ObservedTransport(self.module.DocumentHTTPTransport):
                    async def _read(transport, size):
                        if transport._remaining == 1000:
                            blocked.set()
                        return await super()._read(size)
                self.transport = ObservedTransport()
                clock = http.VirtualClock()
                progress = DocumentPreparation(monotonic=clock, wait_until=clock.wait_until)
                response = [b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: '
                            + str(len(wire) + 1000).encode() + b'\r\n\r\n', wire]
                async with http.LoopbackProvider(response).running() as peer:
                    with patch.object(llm_client, 'or_chat_completions_url', return_value=peer.url):
                        task = asyncio.create_task(prepare_and_read_document([dict(role='user', content='Synthetic')],
                            transport=self.transport, count_tokens_func=token_utils.estimate_tokens,
                            progress=progress, stream=True))
                        try:
                            await asyncio.wait_for(blocked.wait(), 2)
                            self.assertFalse(task.done())
                            if mode == 'cancel':
                                task.cancel()
                                with self.assertRaises(asyncio.CancelledError):
                                    await asyncio.wait_for(task, 2)
                            else:
                                clock.advance(120)
                                with self.assertRaises(DocumentWorkshopError) as raised:
                                    await asyncio.wait_for(task, 2)
                                self.assertEqual(str(raised.exception), 'document_inactivity')
                        finally:
                            task.cancel()
                            await asyncio.gather(task, return_exceptions=True)
                            await self.release(peer)
                    self.assertEqual(self.transport.http_end, 'not_observed')
                    self.assertEqual(len(peer.requests), 1)
                    self.assertEqual(progress.snapshot().state, 'cancelled' if mode == 'cancel' else 'failed')
