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
from memory import memory_identity_dynamics
from memory import memory_store
from memory import memory_traces_summaries


class ChatTurnLoggerEmbeddingsTests(unittest.TestCase):
    def test_embedding_events_include_source_kind_for_query_trace_and_summary(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_runtime_embedding_value = memory_store._runtime_embedding_value
        original_runtime_embedding_token = memory_store._runtime_embedding_token
        original_embed_impl = memory_store.memory_store_infra.embed
        original_trace_exists = memory_traces_summaries._trace_exists_for_message

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                return []

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        def fake_runtime_embedding_value(field: str) -> Any:
            if field == 'endpoint':
                return 'https://embed.example/v1'
            if field == 'dimensions':
                return 1536
            return None

        log_store.insert_chat_log_event = fake_insert
        memory_store._runtime_embedding_value = fake_runtime_embedding_value
        memory_store._runtime_embedding_token = lambda: 'token-test'
        memory_store.memory_store_infra.embed = lambda *_args, **_kwargs: [0.1, 0.2, 0.3]
        memory_traces_summaries._trace_exists_for_message = lambda *_args, **_kwargs: False

        token = chat_turn_logger.begin_turn(
            conversation_id='conv-embedding-kinds',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_traces_summaries.save_new_traces(
                {
                    'id': 'conv-embedding-kinds',
                    'messages': [
                        {'role': 'user', 'content': 'hello user', 'timestamp': '2026-03-28T10:00:00Z'},
                        {'role': 'assistant', 'content': 'hello assistant', 'timestamp': '2026-03-28T10:00:01Z'},
                    ],
                },
                conn_factory=lambda: FakeConn(),
                embed_fn=memory_store.embed,
                logger=SimpleNamespace(info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
            memory_traces_summaries.retrieve(
                'search memory',
                top_k=1,
                runtime_embedding_value_fn=lambda _field: 1,
                conn_factory=lambda: FakeConn(),
                embed_fn=memory_store.embed,
                logger=SimpleNamespace(warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
            memory_traces_summaries.save_summary(
                'conv-embedding-kinds',
                {
                    'id': 'summary-1',
                    'content': 'summary content',
                    'start_ts': '2026-03-28T10:00:00Z',
                    'end_ts': '2026-03-28T10:05:00Z',
                },
                conn_factory=lambda: FakeConn(),
                embed_fn=memory_store.embed,
                logger=SimpleNamespace(info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            memory_store._runtime_embedding_value = original_runtime_embedding_value
            memory_store._runtime_embedding_token = original_runtime_embedding_token
            memory_store.memory_store_infra.embed = original_embed_impl
            memory_traces_summaries._trace_exists_for_message = original_trace_exists

        embedding_events = [event for event in observed if event['stage'] == 'embedding' and event['status'] == 'ok']
        source_kinds = [event['payload_json'].get('source_kind') for event in embedding_events]
        self.assertCountEqual(
            source_kinds,
            ['trace_user', 'trace_assistant', 'query', 'summary'],
        )
        for event in embedding_events:
            payload = event['payload_json']
            self.assertIn(payload.get('source_kind'), {'query', 'trace_user', 'trace_assistant', 'summary'})
            self.assertIn('mode', payload)
            self.assertIn('provider', payload)
            self.assertIn('dimensions', payload)
            self.assertNotIn('text', payload)
            self.assertNotIn('content', payload)
            self.assertNotIn('vector', payload)

    def test_identity_conflict_embeddings_are_labeled_and_summarized_without_unknown_source_kind(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_runtime_embedding_value = memory_store._runtime_embedding_value
        original_runtime_embedding_token = memory_store._runtime_embedding_token
        original_embed_impl = memory_store.memory_store_infra.embed

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchone(self) -> tuple[Any, ...]:
                return (
                    '11111111-1111-1111-1111-111111111111',
                    'llm',
                    'Current identity',
                    'current identity',
                    'accepted',
                    datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc),
                    'none',
                )

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        '22222222-2222-2222-2222-222222222222',
                        'Candidate one',
                        'candidate one',
                        'accepted',
                        datetime(2026, 4, 8, 9, 59, tzinfo=timezone.utc),
                        'none',
                    ),
                    (
                        '33333333-3333-3333-3333-333333333333',
                        'Candidate two',
                        'candidate two',
                        'accepted',
                        datetime(2026, 4, 8, 9, 58, tzinfo=timezone.utc),
                        'none',
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        def fake_runtime_embedding_value(field: str) -> Any:
            if field == 'endpoint':
                return 'https://embed.example/v1'
            if field == 'dimensions':
                return 1536
            return None

        policy_module = SimpleNamespace(
            is_contradictory=lambda *_args, **_kwargs: (False, 0.0, 'no_conflict'),
            conflict_resolution_action=lambda _confidence: 'no_op',
        )

        log_store.insert_chat_log_event = fake_insert
        memory_store._runtime_embedding_value = fake_runtime_embedding_value
        memory_store._runtime_embedding_token = lambda: 'token-test'
        memory_store.memory_store_infra.embed = lambda *_args, **_kwargs: [0.1, 0.2, 0.3]

        token = chat_turn_logger.begin_turn(
            conversation_id='conv-identity-conflict-observability',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.detect_and_record_conflicts(
                '11111111-1111-1111-1111-111111111111',
                conn_factory=lambda: FakeConn(),
                policy_module=policy_module,
                logger=SimpleNamespace(warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
                conflict_already_open_fn=lambda *_args, **_kwargs: False,
                embed_identity_conflict_vector_fn=memory_store._embed_identity_conflict_vector,
                embedding_similarity_safe_fn=memory_store._embedding_similarity_safe,
                insert_conflict_fn=lambda *_args, **_kwargs: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            memory_store._runtime_embedding_value = original_runtime_embedding_value
            memory_store._runtime_embedding_token = original_runtime_embedding_token
            memory_store.memory_store_infra.embed = original_embed_impl

        embedding_events = [event for event in observed if event['stage'] == 'embedding' and event['status'] == 'ok']
        source_kinds = [event['payload_json'].get('source_kind') for event in embedding_events]
        self.assertCountEqual(
            source_kinds,
            [
                'identity_conflict_current',
                'identity_conflict_candidate',
                'identity_conflict_candidate',
            ],
        )
        self.assertNotIn('unknown', source_kinds)
        for event in embedding_events:
            payload = event['payload_json']
            self.assertIn(
                payload.get('source_kind'),
                {'identity_conflict_current', 'identity_conflict_candidate'},
            )
            self.assertNotIn('text', payload)
            self.assertNotIn('content', payload)
            self.assertNotIn('vector', payload)

        scan_event = next(event for event in observed if event['stage'] == 'identity_conflict_scan')
        payload = scan_event['payload_json']
        self.assertEqual(scan_event['status'], 'ok')
        self.assertEqual(payload['candidate_count'], 2)
        self.assertEqual(payload['same_content_skipped'], 0)
        self.assertEqual(payload['open_conflict_skipped'], 0)
        self.assertEqual(payload['similarity_comparisons'], 2)
        self.assertEqual(payload['conflicts_detected'], 0)
        self.assertEqual(payload['current_embedding_calls'], 1)
        self.assertEqual(payload['candidate_embedding_calls'], 2)
        self.assertEqual(payload['embedding_calls_total'], 3)
        self.assertTrue(payload['current_embedding_reused'])
        self.assertFalse(payload['current_embedding_blocked'])
        self.assertNotIn('content', payload)
        self.assertNotIn('preview', payload)


if __name__ == '__main__':
    unittest.main()
