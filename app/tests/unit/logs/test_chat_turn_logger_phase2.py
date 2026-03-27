from __future__ import annotations

import sys
import unittest
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

from logs import chat_turn_logger
from logs import log_store
from memory import memory_context_read
from memory import memory_identity_dynamics
from tools import web_search


class ChatTurnLoggerPhase2Tests(unittest.TestCase):
    def test_begin_end_emits_turn_start_and_turn_end(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-phase2',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(observed[0]['stage'], 'turn_start')
        self.assertEqual(observed[0]['status'], 'ok')
        self.assertEqual(observed[-1]['stage'], 'turn_end')
        self.assertEqual(observed[-1]['payload_json']['final_status'], 'ok')

    def test_emit_is_best_effort_when_store_insert_raises(self) -> None:
        original_insert = log_store.insert_chat_log_event

        def fake_insert_raise(*_args: Any, **_kwargs: Any) -> bool:
            raise RuntimeError('store down')

        log_store.insert_chat_log_event = fake_insert_raise
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-phase2',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            # No exception must propagate despite insert failures.
            self.assertFalse(chat_turn_logger.emit('context_build', status='ok', payload={'context_tokens': 12}))
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

    def test_emit_sanitizes_preview_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-preview',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'identities_read',
                status='ok',
                payload={
                    'preview': ['x' * 300, 'y' * 300, 'z' * 300, 'w' * 300],
                    'keys': ['a' * 200, 'b' * 200, 'c' * 200, 'd' * 200],
                    'truncated': False,
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identities_event = next(event for event in observed if event['stage'] == 'identities_read')
        payload = identities_event['payload_json']
        self.assertEqual(len(payload['preview']), 3)
        self.assertEqual(len(payload['keys']), 3)
        self.assertTrue(payload['truncated'])
        self.assertTrue(all(len(item) <= 120 for item in payload['preview']))
        self.assertTrue(all(len(item) <= 64 for item in payload['keys']))


class ChatInstrumentationPhase2Tests(unittest.TestCase):
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
        self.assertEqual(payload['frida_count'], 1)
        self.assertEqual(payload['user_count'], 0)

    def test_persist_identity_entries_emits_identity_write_for_both_sides(self) -> None:
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
                        'content': 'Frida keeps this',
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
                        'content': 'User preference',
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
                        'content': 'Rejected noise',
                        'status': 'rejected',
                        'stability': 'unknown',
                        'utterance_mode': 'irony',
                        'recurrence': 'single',
                        'scope': 'user',
                        'evidence_kind': 'weak',
                        'confidence': 0.2,
                        'reason': 'policy:reject',
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
        for event in identity_write_events:
            self.assertIn('actions_count', event['payload_json'])
            self.assertIn('retained_count', event['payload_json'])

    def test_web_search_build_context_emits_ok_and_skipped(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_format_context = web_search._format_context

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        try:
            token_ok = chat_turn_logger.begin_turn(
                conversation_id='conv-web-ok',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query ok'
            web_search.search = lambda _query: [{'title': 'A', 'url': 'https://a', 'content': 'x'}]
            web_search._format_context = lambda _query, _results: 'CTX OK'
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('CTX OK', 'query ok', 1))
                chat_turn_logger.end_turn(token_ok, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context

            token_skip = chat_turn_logger.begin_turn(
                conversation_id='conv-web-skip',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query none'
            web_search.search = lambda _query: []
            web_search._format_context = lambda _query, _results: ''
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('', 'query none', 0))
                chat_turn_logger.end_turn(token_skip, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context
        finally:
            log_store.insert_chat_log_event = original_insert

        web_search_events = [event for event in observed if event['stage'] == 'web_search']
        self.assertGreaterEqual(len(web_search_events), 2)
        statuses = {event['status'] for event in web_search_events}
        self.assertIn('ok', statuses)
        self.assertIn('skipped', statuses)
        for event in web_search_events:
            self.assertEqual(event['payload_json'].get('prompt_kind'), 'chat_web_reformulation')


if __name__ == '__main__':
    unittest.main()
