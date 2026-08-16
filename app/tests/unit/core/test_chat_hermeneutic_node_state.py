from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core import chat_hermeneutic_node_state
from core import chat_service


class ChatHermeneuticNodeStateTests(unittest.TestCase):
    def test_chat_service_reexports_named_state_boundary(self) -> None:
        helper_names = (
            '_read_hermeneutic_node_state',
            '_existing_node_state_from_read',
            '_skipped_hermeneutic_node_state_write',
            '_write_hermeneutic_node_state',
            '_build_final_hermeneutic_node_state',
        )

        self.assertTrue(all(hasattr(chat_service, name) for name in helper_names))
        self.assertEqual(
            {getattr(chat_service, name).__module__ for name in helper_names},
            {'core.chat_hermeneutic_node_state'},
        )

    def test_read_boundary_fails_closed_without_raw_error_content(self) -> None:
        unavailable = chat_service._read_hermeneutic_node_state(
            memory_store_module=SimpleNamespace(),
            conversation_id='conv-state-read',
        )

        def failing_reader(_conversation_id: str) -> dict[str, object]:
            raise RuntimeError('RAW_NODE_STATE_READ_SENTINEL')

        failed = chat_service._read_hermeneutic_node_state(
            memory_store_module=SimpleNamespace(read_hermeneutic_node_state=failing_reader),
            conversation_id='conv-state-read',
        )
        state = {'schema_version': 'v1', 'conversation_id': 'conv-state-read'}
        present = chat_service._read_hermeneutic_node_state(
            memory_store_module=SimpleNamespace(
                read_hermeneutic_node_state=lambda _conversation_id: {
                    'state': state,
                    'present': True,
                    'valid': True,
                    'reason_code': 'ok',
                    'schema_version': 'v1',
                    'state_sha256_12': '0123456789ab',
                }
            ),
            conversation_id='conv-state-read',
        )

        self.assertEqual(unavailable['reason_code'], 'reader_unavailable')
        self.assertFalse(unavailable['valid'])
        self.assertEqual(failed['reason_code'], 'read_error')
        self.assertEqual(failed['error_class'], 'RuntimeError')
        self.assertNotIn('RAW_NODE_STATE_READ_SENTINEL', repr(failed))
        self.assertEqual(chat_service._existing_node_state_from_read(present), state)
        self.assertIsNone(
            chat_service._existing_node_state_from_read(
                {'state': state, 'present': True, 'valid': False}
            )
        )

    def test_write_boundary_preserves_attempt_semantics_without_raw_error_content(self) -> None:
        unavailable = chat_service._write_hermeneutic_node_state(
            memory_store_module=SimpleNamespace(),
            conversation_id='conv-state-write',
            node_state_payload={'schema_version': 'v1'},
        )

        def failing_writer(_conversation_id: str, _payload: object) -> dict[str, object]:
            raise ValueError('RAW_NODE_STATE_WRITE_SENTINEL')

        failed = chat_service._write_hermeneutic_node_state(
            memory_store_module=SimpleNamespace(write_hermeneutic_node_state=failing_writer),
            conversation_id='conv-state-write',
            node_state_payload={'schema_version': 'v1'},
        )
        skipped = chat_service._skipped_hermeneutic_node_state_write('')

        self.assertFalse(unavailable['attempted'])
        self.assertEqual(unavailable['reason_code'], 'writer_unavailable')
        self.assertTrue(failed['attempted'])
        self.assertFalse(failed['written'])
        self.assertEqual(failed['reason_code'], 'write_error')
        self.assertEqual(failed['error_class'], 'ValueError')
        self.assertNotIn('RAW_NODE_STATE_WRITE_SENTINEL', repr(failed))
        self.assertEqual(skipped['reason_code'], 'not_applicable')
        self.assertFalse(skipped['attempted'])

    def test_final_state_boundary_builds_only_supported_validated_states(self) -> None:
        built: list[dict[str, object]] = []

        def fake_build_node_state(**kwargs: object) -> dict[str, object]:
            built.append(dict(kwargs))
            return {'schema_version': 'v1', 'last_judgment_posture': kwargs['judgment_posture']}

        with patch.object(
            chat_hermeneutic_node_state.runtime_node_state,
            'build_node_state',
            side_effect=fake_build_node_state,
        ):
            answer, answer_reason = chat_service._build_final_hermeneutic_node_state(
                conversation_id='conv-final-state',
                now_iso='2026-08-16T18:00:00Z',
                validated_result=SimpleNamespace(
                    validated_output={
                        'final_judgment_posture': 'answer',
                        'final_output_regime': 'simple',
                    }
                ),
                existing_node_state=None,
            )
            clarify, clarify_reason = chat_service._build_final_hermeneutic_node_state(
                conversation_id='conv-final-state',
                now_iso='2026-08-16T18:01:00Z',
                validated_result=SimpleNamespace(
                    validated_output={
                        'final_judgment_posture': 'clarify',
                        'final_output_regime': 'meta',
                    }
                ),
                existing_node_state={'schema_version': 'v1'},
            )
            presence, presence_reason = chat_service._build_final_hermeneutic_node_state(
                conversation_id='conv-final-state',
                now_iso='2026-08-16T18:02:00Z',
                validated_result=SimpleNamespace(
                    validated_output={
                        'final_judgment_posture': 'answer',
                        'final_output_regime': 'presence',
                    }
                ),
                existing_node_state=None,
            )

        self.assertEqual(answer, {'schema_version': 'v1', 'last_judgment_posture': 'answer'})
        self.assertEqual(answer_reason, '')
        self.assertEqual(clarify, {'schema_version': 'v1', 'last_judgment_posture': 'clarify'})
        self.assertEqual(clarify_reason, '')
        self.assertIsNone(presence)
        self.assertEqual(presence_reason, 'presence_turn_local')
        self.assertEqual([item['judgment_posture'] for item in built], ['answer', 'clarify'])
        self.assertEqual(
            [item['output_regime']['discursive_regime'] for item in built],
            ['simple', 'meta'],
        )

    def test_final_state_boundary_rejects_invalid_validated_combinations(self) -> None:
        cases = (
            (None, 'validated_output_missing'),
            (
                {'final_judgment_posture': 'suspend', 'final_output_regime': 'presence'},
                'invalid_presence_judgment_posture',
            ),
            (
                {'final_judgment_posture': 'answer', 'final_output_regime': 'meta'},
                'unsupported_final_output_regime',
            ),
            (
                {'final_judgment_posture': 'unknown', 'final_output_regime': 'simple'},
                'invalid_final_judgment_posture',
            ),
        )

        for validated_output, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                state, reason = chat_service._build_final_hermeneutic_node_state(
                    conversation_id='conv-invalid-final-state',
                    now_iso='2026-08-16T18:03:00Z',
                    validated_result=SimpleNamespace(validated_output=validated_output),
                    existing_node_state=None,
                )
                self.assertIsNone(state)
                self.assertEqual(reason, expected_reason)

        with patch.object(
            chat_hermeneutic_node_state.runtime_node_state,
            'build_node_state',
            side_effect=ValueError('RAW_INVALID_FINAL_STATE_SENTINEL'),
        ):
            state, reason = chat_service._build_final_hermeneutic_node_state(
                conversation_id='conv-invalid-final-state',
                now_iso='2026-08-16T18:04:00Z',
                validated_result=SimpleNamespace(
                    validated_output={
                        'final_judgment_posture': 'answer',
                        'final_output_regime': 'simple',
                    }
                ),
                existing_node_state=None,
            )

        self.assertIsNone(state)
        self.assertEqual(reason, 'invalid_validated_node_state')
        self.assertNotIn('RAW_INVALID_FINAL_STATE_SENTINEL', reason)


if __name__ == '__main__':
    unittest.main()
