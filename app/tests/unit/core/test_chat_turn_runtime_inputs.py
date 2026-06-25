from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_turn_runtime_inputs
from core.hermeneutic_node.inputs import identity_input as canonical_identity_input
from core.hermeneutic_node.inputs import summary_input as canonical_summary_input


class ChatTurnRuntimeInputsWebTimeTests(unittest.TestCase):
    def test_web_runtime_payload_forwards_turn_now_iso(self) -> None:
        observed = {}

        def fake_build_context_payload(_user_msg, **kwargs):
            observed.update(kwargs)
            return {
                'enabled': True,
                'status': 'ok',
                'reason_code': None,
                'original_user_message': 'cherche',
                'query': 'requete',
                'results_count': 1,
                'runtime': {},
                'sources': [],
                'context_block': 'WEB',
            }

        payload = chat_turn_runtime_inputs.resolve_web_runtime_payload(
            user_msg='cherche',
            web_search_on=True,
            web_search_module=SimpleNamespace(build_context_payload=fake_build_context_payload),
            requests_module=SimpleNamespace(),
            llm_module=SimpleNamespace(),
            now_iso='2026-05-17T22:05:00Z',
        )

        self.assertEqual(observed['now_iso'], '2026-05-17T22:05:00Z')
        self.assertEqual(payload['activation_mode'], 'manual')


class ChatTurnRuntimeInputsMemoryFailureTests(unittest.TestCase):
    def test_summary_input_distinguishes_missing_available_and_read_error(self) -> None:
        missing_payload = canonical_summary_input.build_summary_input(
            active_summary=None,
            conversation_id='conv-memory-input',
        )
        available_payload = canonical_summary_input.build_summary_input(
            active_summary={
                'id': 'summary-1',
                'conversation_id': 'conv-memory-input',
                'start_ts': '2026-06-25T08:00:00Z',
                'end_ts': '2026-06-25T09:00:00Z',
                'content': 'synthetic summary content',
            },
            conversation_id='conv-memory-input',
        )

        class BoomLogger:
            def warning(self, *_args, **_kwargs):
                return None

            def error(self, *_args, **_kwargs):
                return None

        class BadConvStore:
            logger = BoomLogger()

            @staticmethod
            def _db_conn():
                raise RuntimeError('RAW_SUMMARY_BOOM')

            @staticmethod
            def _ts_to_iso(value):
                return str(value)

        error_payload = chat_turn_runtime_inputs.resolve_summary_input(
            conversation_id='conv-memory-input',
            conv_store_module=BadConvStore,
        )

        self.assertEqual(missing_payload['status'], 'missing')
        self.assertIsNone(missing_payload['summary'])
        self.assertEqual(available_payload['status'], 'available')
        self.assertEqual(available_payload['summary']['id'], 'summary-1')
        self.assertEqual(error_payload['status'], 'error')
        self.assertEqual(error_payload['reason_code'], chat_turn_runtime_inputs.SUMMARY_READ_ERROR_REASON)
        self.assertEqual(error_payload['error_code'], chat_turn_runtime_inputs.UPSTREAM_ERROR_CODE)
        self.assertEqual(error_payload['error_class'], 'RuntimeError')
        self.assertIsNone(error_payload['summary'])
        self.assertNotIn('RAW_SUMMARY_BOOM', repr(error_payload))

    def test_identity_input_distinguishes_missing_available_and_read_error(self) -> None:
        missing_payload = canonical_identity_input.build_identity_input()
        available_payload = canonical_identity_input.build_identity_input(
            user_static_content='synthetic user identity',
        )

        class BadIdentity:
            @staticmethod
            def build_identity_input():
                raise RuntimeError('RAW_IDENTITY_BOOM')

        error_payload = chat_turn_runtime_inputs.resolve_identity_input(
            identity_module=BadIdentity,
        )

        self.assertEqual(missing_payload['status'], 'missing')
        self.assertEqual(available_payload['status'], 'available')
        self.assertEqual(error_payload['status'], 'error')
        self.assertEqual(error_payload['reason_code'], chat_turn_runtime_inputs.IDENTITY_READ_ERROR_REASON)
        self.assertEqual(error_payload['error_code'], chat_turn_runtime_inputs.UPSTREAM_ERROR_CODE)
        self.assertEqual(error_payload['error_class'], 'RuntimeError')
        self.assertEqual(error_payload['frida']['static']['content'], '')
        self.assertEqual(error_payload['user']['mutable']['content'], '')
        self.assertNotIn('RAW_IDENTITY_BOOM', repr(error_payload))

    def test_error_status_reaches_hermeneutic_node_canonical_inputs(self) -> None:
        from core import chat_service

        captured: dict[str, object] = {}
        original_validate = chat_service.validation_agent.build_validated_output

        def fake_validate(*_args, canonical_inputs, **_kwargs):
            captured['canonical_inputs'] = canonical_inputs
            return SimpleNamespace(validated_output={})

        summary_payload = canonical_summary_input.build_summary_input(
            active_summary=None,
            status='error',
            reason_code=chat_turn_runtime_inputs.SUMMARY_READ_ERROR_REASON,
            error_code=chat_turn_runtime_inputs.UPSTREAM_ERROR_CODE,
            error_class='RuntimeError',
        )
        identity_payload = canonical_identity_input.build_identity_input(
            status='error',
            reason_code=chat_turn_runtime_inputs.IDENTITY_READ_ERROR_REASON,
            error_code=chat_turn_runtime_inputs.UPSTREAM_ERROR_CODE,
            error_class='RuntimeError',
        )

        chat_service.validation_agent.build_validated_output = fake_validate
        try:
            result = chat_service._run_hermeneutic_node_insertion_point(
                conversation={'id': 'conv-memory-input', 'messages': []},
                user_msg='synthetic message',
                now_iso='2026-06-25T10:00:00Z',
                current_mode='shadow',
                memory_traces=[],
                context_hints=[],
                summary_input=summary_payload,
                identity_input=identity_payload,
                memory_store_module=SimpleNamespace(),
                requests_module=SimpleNamespace(),
            )
        finally:
            chat_service.validation_agent.build_validated_output = original_validate

        canonical_inputs = captured['canonical_inputs']
        self.assertEqual(canonical_inputs['summary_input']['status'], 'error')
        self.assertEqual(canonical_inputs['summary_input']['reason_code'], chat_turn_runtime_inputs.SUMMARY_READ_ERROR_REASON)
        self.assertEqual(canonical_inputs['identity_input']['status'], 'error')
        self.assertEqual(canonical_inputs['identity_input']['reason_code'], chat_turn_runtime_inputs.IDENTITY_READ_ERROR_REASON)
        self.assertIn('primary_payload', result)
        self.assertNotIn('RAW_', repr(canonical_inputs))


if __name__ == '__main__':
    unittest.main()
