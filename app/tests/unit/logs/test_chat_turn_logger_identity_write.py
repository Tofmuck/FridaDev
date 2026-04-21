from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from observability import chat_turn_logger
from observability import log_store
from memory import memory_identity_dynamics


class ChatTurnLoggerIdentityWriteTests(unittest.TestCase):
    def test_persist_identity_entries_emits_legacy_diagnostic_identity_write_for_both_sides(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-write',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.persist_identity_entries(
                'conv-write',
                entries=[],
                source_trace_id='trace-1',
                preview_identity_entries_fn=lambda _entries: [
                    {
                        'subject': 'llm',
                        'content': 'Frida keeps this ' + ('x' * 220),
                        'status': 'accepted',
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'llm',
                        'evidence_kind': 'strong',
                        'confidence': 0.9,
                        'reason': 'policy:accepted',
                    },
                    {
                        'subject': 'user',
                        'content': 'User preference ' + ('y' * 220),
                        'status': 'deferred',
                        'stability': 'episodic',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'user',
                        'evidence_kind': 'weak',
                        'confidence': 0.7,
                        'reason': 'policy:defer',
                    },
                    {
                        'subject': 'user',
                        'content': 'Rejected noise ' + ('z' * 220),
                        'status': 'rejected',
                        'stability': 'unknown',
                        'utterance_mode': 'irony',
                        'recurrence': 'single',
                        'scope': 'user',
                        'evidence_kind': 'weak',
                        'confidence': 0.2,
                        'reason': 'policy:reject',
                    },
                    {
                        'subject': 'user',
                        'content': 'Another retained user identity ' + ('k' * 220),
                        'status': 'accepted',
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'user',
                        'evidence_kind': 'strong',
                        'confidence': 0.85,
                        'reason': 'policy:accepted',
                    },
                ],
                record_identity_evidence_fn=lambda *_args, **_kwargs: None,
                add_identity_fn=lambda *_args, **_kwargs: 'identity-id',
                detect_and_record_conflicts_fn=lambda *_args, **_kwargs: None,
                normalize_identity_content_fn=lambda text: text.strip().lower(),
                apply_defer_policy_for_content_fn=lambda *_args, **_kwargs: None,
                expire_stale_deferred_global_fn=lambda: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identity_write_events = [event for event in observed if event['stage'] == 'identity_write']
        self.assertEqual({event['payload_json']['target_side'] for event in identity_write_events}, {'frida', 'user'})
        user_payload = next(
            event['payload_json']
            for event in identity_write_events
            if event['payload_json']['target_side'] == 'user'
        )
        self.assertEqual(user_payload.get('persisted_count'), 3)
        self.assertEqual(user_payload.get('retained_count'), 2)
        self.assertEqual(user_payload.get('observed_count'), 3)
        self.assertTrue(user_payload.get('content_present'))
        self.assertGreater(user_payload.get('observed_total_chars', 0), 0)
        self.assertGreater(user_payload.get('observed_max_chars', 0), 0)
        for event in identity_write_events:
            payload = event['payload_json']
            self.assertEqual(payload.get('write_mode'), 'legacy_diagnostic')
            self.assertEqual(payload.get('write_effect'), 'legacy_diagnostic_write')
            self.assertGreaterEqual(int(payload.get('persisted_count') or 0), int(payload.get('retained_count') or 0))
            self.assertIn('evidence_count', payload)
            self.assertIn('observed_count', payload)
            self.assertIn('actions_count', payload)
            self.assertIn('retained_count', payload)
            self.assertSetEqual(set(payload['actions_count'].keys()), {'add', 'update', 'override', 'reject', 'defer'})
            self.assertEqual(payload.get('observed_count'), payload.get('evidence_count'))
            self.assertNotIn('preview', payload)
            self.assertNotIn('keys', payload)
            self.assertNotIn('truncated', payload)
            self.assertNotIn('entries', payload)
            self.assertNotIn('raw_identities', payload)

    def test_persist_identity_entries_emits_per_side_legacy_diagnostic_visibility_when_one_side_has_no_data(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-write-single-side',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.persist_identity_entries(
                'conv-write-single-side',
                entries=[],
                source_trace_id='trace-1',
                preview_identity_entries_fn=lambda _entries: [
                    {
                        'subject': 'llm',
                        'content': 'Frida durable identity',
                        'status': 'accepted',
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'llm',
                        'evidence_kind': 'strong',
                        'confidence': 0.95,
                        'reason': 'policy:accepted',
                    }
                ],
                record_identity_evidence_fn=lambda *_args, **_kwargs: None,
                add_identity_fn=lambda *_args, **_kwargs: 'identity-id',
                detect_and_record_conflicts_fn=lambda *_args, **_kwargs: None,
                normalize_identity_content_fn=lambda text: text.strip().lower(),
                apply_defer_policy_for_content_fn=lambda *_args, **_kwargs: None,
                expire_stale_deferred_global_fn=lambda: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identity_write_events = [event for event in observed if event['stage'] == 'identity_write']
        self.assertEqual(len(identity_write_events), 2)
        by_side = {event['payload_json']['target_side']: event for event in identity_write_events}
        self.assertSetEqual(set(by_side.keys()), {'frida', 'user'})

        frida_event = by_side['frida']
        self.assertEqual(frida_event['status'], 'ok')
        self.assertEqual(frida_event['payload_json']['write_mode'], 'legacy_diagnostic')
        self.assertEqual(frida_event['payload_json']['write_effect'], 'legacy_diagnostic_write')
        self.assertEqual(frida_event['payload_json']['persisted_count'], 1)
        self.assertEqual(frida_event['payload_json']['evidence_count'], 1)
        self.assertEqual(frida_event['payload_json']['retained_count'], 1)

        user_event = by_side['user']
        self.assertEqual(user_event['status'], 'skipped')
        self.assertEqual(user_event['payload_json']['reason_code'], 'no_data')
        self.assertEqual(user_event['payload_json']['write_mode'], 'legacy_diagnostic')
        self.assertEqual(user_event['payload_json']['write_effect'], 'none')
        self.assertEqual(user_event['payload_json']['persisted_count'], 0)
        self.assertEqual(user_event['payload_json']['evidence_count'], 0)
        self.assertEqual(user_event['payload_json']['observed_count'], 0)
        self.assertEqual(user_event['payload_json']['retained_count'], 0)
        self.assertFalse(user_event['payload_json']['content_present'])
        self.assertEqual(user_event['payload_json']['observed_total_chars'], 0)
        self.assertEqual(user_event['payload_json']['observed_max_chars'], 0)
        self.assertNotIn('preview', user_event['payload_json'])

        for event in identity_write_events:
            payload = event['payload_json']
            self.assertNotIn('entries', payload)
            self.assertNotIn('raw_identities', payload)

    def test_persist_identity_entries_tracks_persisted_count_for_rejected_entries_in_legacy_diagnostic_pipeline(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-write-rejected-only',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.persist_identity_entries(
                'conv-write-rejected-only',
                entries=[],
                source_trace_id='trace-rj',
                preview_identity_entries_fn=lambda _entries: [
                    {
                        'subject': 'llm',
                        'content': 'Rejected Frida identity',
                        'status': 'rejected',
                        'stability': 'unknown',
                        'utterance_mode': 'irony',
                        'recurrence': 'single',
                        'scope': 'llm',
                        'evidence_kind': 'weak',
                        'confidence': 0.2,
                        'reason': 'policy:reject',
                    }
                ],
                record_identity_evidence_fn=lambda *_args, **_kwargs: None,
                add_identity_fn=lambda *_args, **_kwargs: 'identity-rejected-id',
                detect_and_record_conflicts_fn=lambda *_args, **_kwargs: None,
                normalize_identity_content_fn=lambda text: text.strip().lower(),
                apply_defer_policy_for_content_fn=lambda *_args, **_kwargs: None,
                expire_stale_deferred_global_fn=lambda: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identity_write_events = [event for event in observed if event['stage'] == 'identity_write']
        by_side = {event['payload_json']['target_side']: event for event in identity_write_events}
        self.assertSetEqual(set(by_side.keys()), {'frida', 'user'})

        frida_payload = by_side['frida']['payload_json']
        self.assertEqual(by_side['frida']['status'], 'ok')
        self.assertEqual(frida_payload.get('write_mode'), 'legacy_diagnostic')
        self.assertEqual(frida_payload.get('write_effect'), 'legacy_diagnostic_write')
        self.assertEqual(frida_payload.get('persisted_count'), 1)
        self.assertEqual(frida_payload.get('retained_count'), 0)
        self.assertEqual(frida_payload.get('actions_count', {}).get('reject'), 1)

        user_payload = by_side['user']['payload_json']
        self.assertEqual(by_side['user']['status'], 'skipped')
        self.assertEqual(user_payload.get('persisted_count'), 0)
        self.assertEqual(user_payload.get('retained_count'), 0)
        self.assertEqual(user_payload.get('observed_count'), 0)
        self.assertNotIn('preview', user_payload)


if __name__ == '__main__':
    unittest.main()
