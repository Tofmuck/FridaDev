from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
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
from identity import identity
from memory import memory_context_read


class ChatTurnLoggerIdentitiesReadTests(unittest.TestCase):
    def test_get_identities_emits_identities_read_with_frida_side(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        '11111111-1111-1111-1111-111111111111',
                        'llm',
                        'Frida style identity',
                        1.0,
                        None,
                        None,
                        None,
                        'durable',
                        'self_description',
                        'repeated',
                        'llm',
                        'strong',
                        0.9,
                        'accepted',
                        'frida style identity',
                        'policy:accepted',
                        'conv-a',
                        'none',
                        None,
                        None,
                        None,
                    )
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-identities',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            rows = memory_context_read.get_identities(
                'llm',
                top_n=5,
                status='accepted',
                conn_factory=lambda: FakeConn(),
                default_top_n=5,
                logger=SimpleNamespace(error=lambda *_a, **_k: None),
            )
            self.assertEqual(len(rows), 1)
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identities_events = [event for event in observed if event['stage'] == 'identities_read']
        self.assertTrue(identities_events)
        payload = identities_events[0]['payload_json']
        self.assertEqual(payload['target_side'], 'frida')
        self.assertEqual(payload['source_kind'], 'durable')
        self.assertEqual(payload['frida_count'], 1)
        self.assertEqual(payload['user_count'], 0)
        self.assertEqual(payload['selected_count'], 1)
        self.assertTrue(payload['content_present'])
        self.assertEqual(payload['total_chars'], len('Frida style identity'))
        self.assertEqual(payload['max_chars'], len('Frida style identity'))
        self.assertEqual(payload['requested_limit'], 5)
        self.assertFalse(payload['truncated'])
        self.assertNotIn('preview', payload)
        self.assertNotIn('keys', payload)

    def test_build_identity_block_emits_identities_read_for_static_sources(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_load_llm_identity = identity.load_llm_identity
        original_load_user_identity = identity.load_user_identity
        original_get_mutable_identity = identity._get_mutable_identity

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        identity.load_llm_identity = lambda: 'Frida static identity'
        identity.load_user_identity = lambda: 'User static identity'
        identity._get_mutable_identity = lambda _subject: None
        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-static-identities',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            block, used_ids = identity.build_identity_block()
            self.assertIn('DU MOD', block)
            self.assertIn("L'UTILISATEUR", block)
            self.assertEqual(used_ids, [])
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            identity.load_llm_identity = original_load_llm_identity
            identity.load_user_identity = original_load_user_identity
            identity._get_mutable_identity = original_get_mutable_identity

        identities_events = [event for event in observed if event['stage'] == 'identities_read']
        static_events = [event for event in identities_events if event['payload_json'].get('source_kind') == 'static']
        self.assertEqual(len(static_events), 2)
        sides = {event['payload_json'].get('target_side') for event in static_events}
        self.assertSetEqual(sides, {'frida', 'user'})
        for event in static_events:
            payload = event['payload_json']
            self.assertEqual(payload['selected_count'], 1)
            self.assertTrue(payload['content_present'])
            self.assertGreater(payload['total_chars'], 0)
            self.assertEqual(payload['total_chars'], payload['max_chars'])
            self.assertFalse(payload['truncated'])
            self.assertNotIn('content', payload)
            self.assertNotIn('raw_content', payload)
            self.assertNotIn('preview', payload)
            self.assertNotIn('keys', payload)

    def test_get_recent_context_hints_emits_identities_read_for_user_side(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
                return [
                    ('conv-u1', 'User context hint alpha ' + ('a' * 200), 'norm-alpha', now, 0.9, 'user', 'episodic', 'self_description', 1.2),
                    ('conv-u2', 'User context hint beta ' + ('b' * 200), 'norm-beta', now, 0.8, 'user', 'episodic', 'self_description', 1.1),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-hints',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            hints = memory_context_read.get_recent_context_hints(
                max_items=2,
                max_age_days=7,
                min_confidence=0.6,
                conn_factory=lambda: FakeConn(),
                default_max_items=2,
                default_max_age_days=7,
                default_min_confidence=0.6,
                logger=SimpleNamespace(error=lambda *_a, **_k: None),
            )
            self.assertEqual(len(hints), 2)
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identities_events = [event for event in observed if event['stage'] == 'identities_read']
        self.assertTrue(identities_events)
        payload = identities_events[0]['payload_json']
        self.assertEqual(payload['target_side'], 'user')
        self.assertEqual(payload['source_kind'], 'context_hint')
        self.assertEqual(payload['frida_count'], 0)
        self.assertEqual(payload['user_count'], 2)
        self.assertEqual(payload['selected_count'], 2)
        self.assertTrue(payload['content_present'])
        self.assertGreater(payload['total_chars'], 0)
        self.assertGreater(payload['max_chars'], 0)
        self.assertEqual(payload['requested_limit'], 2)
        self.assertTrue(payload['truncated'])
        self.assertNotIn('keys', payload)
        self.assertNotIn('preview', payload)
        self.assertNotIn('content', payload)
        self.assertNotIn('raw_identities', payload)


if __name__ == '__main__':
    unittest.main()
