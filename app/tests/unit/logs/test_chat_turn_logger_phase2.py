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

from observability import chat_turn_logger
from observability import log_store
from memory import memory_arbiter_audit


class ChatTurnLoggerPhase2Tests(unittest.TestCase):
    def test_identity_periodic_agent_event_stays_compact_without_content_preview(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-periodic-agent',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'identity_periodic_agent',
                status='ok',
                payload={
                    'buffer_pairs_count': 15,
                    'buffer_target_pairs': 15,
                    'buffer_cleared': True,
                    'writes_applied': True,
                    'promotions': [
                        {
                            'subject': 'llm',
                            'operation_kind': 'add',
                            'promotion_reason_code': 'promoted_to_static',
                            'threshold_verdict': 'accepted',
                            'strength': 0.91,
                        }
                    ],
                    'outcomes': [
                        {
                            'subject': 'llm',
                            'action': 'tighten',
                            'old_len': 10,
                            'new_len': 42,
                            'validation_ok': True,
                            'reason_code': 'tighten_applied',
                        },
                        {
                            'subject': 'user',
                            'action': 'raise_conflict',
                            'old_len': 20,
                            'new_len': 20,
                            'validation_ok': True,
                            'reason_code': 'raise_conflict',
                        },
                    ],
                },
                prompt_kind='identity_periodic_agent',
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        periodic_event = next(event for event in observed if event['stage'] == 'identity_periodic_agent')
        payload = periodic_event['payload_json']
        self.assertEqual(payload['prompt_kind'], 'identity_periodic_agent')
        self.assertNotIn('preview', payload)
        self.assertNotIn('buffer_pairs', payload)
        self.assertNotIn('candidates', payload)
        self.assertEqual(len(payload['outcomes']), 2)
        self.assertTrue(all('content' not in outcome for outcome in payload['outcomes']))
        self.assertTrue(all(outcome['action'] != 'rewrite' for outcome in payload['outcomes']))
        self.assertTrue(all(outcome['reason_code'] != 'rewrite_applied' for outcome in payload['outcomes']))
        self.assertEqual(len(payload['promotions']), 1)
        self.assertTrue(all('content' not in promotion for promotion in payload['promotions']))

class ChatInstrumentationPhase2Tests(unittest.TestCase):
    def test_record_arbiter_decisions_emits_compact_arbiter_reasons_and_fallback(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

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

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-arbiter-logs',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_arbiter_audit.record_arbiter_decisions(
                'conv-arbiter-logs',
                traces=[
                    {'role': 'assistant', 'content': 'trace kept', 'timestamp': '2026-03-27T10:00:00Z', 'score': 0.9},
                    {'role': 'assistant', 'content': 'trace rejected 1', 'timestamp': '2026-03-27T10:01:00Z', 'score': 0.4},
                    {'role': 'assistant', 'content': 'trace rejected 2', 'timestamp': '2026-03-27T10:02:00Z', 'score': 0.3},
                ],
                decisions=[
                    {
                        'candidate_id': '0',
                        'keep': True,
                        'semantic_relevance': 0.92,
                        'contextual_gain': 0.88,
                        'redundant_with_recent': False,
                        'reason': 'kept',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '1',
                        'keep': False,
                        'semantic_relevance': 0.40,
                        'contextual_gain': 0.20,
                        'redundant_with_recent': False,
                        'reason': 'below_contextual_gain_threshold | lexical_near_duplicate_low_context_gain(sim=0.84)',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '2',
                        'keep': False,
                        'semantic_relevance': 0.20,
                        'contextual_gain': 0.10,
                        'redundant_with_recent': False,
                        'reason': 'fallback:parse_or_runtime_error',
                        'decision_source': 'fallback',
                        'model': 'openrouter/arbiter-v1',
                    },
                ],
                effective_model='openrouter/arbiter-v1',
                mode='shadow',
                conn_factory=lambda: FakeConn(),
                trace_float_fn=lambda value: float(value or 0.0),
                logger=SimpleNamespace(error=lambda *_a, **_k: None, info=lambda *_a, **_k: None),
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        arbiter_events = [event for event in observed if event['stage'] == 'arbiter']
        self.assertEqual(len(arbiter_events), 1)
        payload = arbiter_events[0]['payload_json']
        self.assertEqual(payload['raw_candidates'], 3)
        self.assertEqual(payload['kept_candidates'], 1)
        self.assertEqual(payload['rejected_candidates'], 2)
        self.assertEqual(payload['mode'], 'shadow')
        self.assertEqual(payload['model'], 'openrouter/arbiter-v1')
        self.assertEqual(payload['decision_source'], 'mixed')
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['fallback_decisions'], 1)
        self.assertEqual(payload['rejection_reason_counts']['below_contextual_gain_threshold'], 1)
        self.assertEqual(payload['rejection_reason_counts']['fallback:parse_or_runtime_error'], 1)
        self.assertNotIn('candidate_content', payload)
        self.assertNotIn('candidates', payload)

    def test_record_arbiter_decisions_keeps_true_counts_when_persistence_fails(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FailingCursor:
            def __enter__(self) -> 'FailingCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                raise RuntimeError('db insert failed')

        class FailingConn:
            def __enter__(self) -> 'FailingConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FailingCursor:
                return FailingCursor()

            def commit(self) -> None:
                return None

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-arbiter-db-fail',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_arbiter_audit.record_arbiter_decisions(
                'conv-arbiter-db-fail',
                traces=[
                    {'role': 'assistant', 'content': 'trace kept', 'timestamp': '2026-03-27T10:00:00Z', 'score': 0.9},
                    {'role': 'assistant', 'content': 'trace rejected 1', 'timestamp': '2026-03-27T10:01:00Z', 'score': 0.4},
                    {'role': 'assistant', 'content': 'trace rejected 2', 'timestamp': '2026-03-27T10:02:00Z', 'score': 0.3},
                ],
                decisions=[
                    {
                        'candidate_id': '0',
                        'keep': True,
                        'semantic_relevance': 0.92,
                        'contextual_gain': 0.88,
                        'redundant_with_recent': False,
                        'reason': 'kept',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '1',
                        'keep': False,
                        'semantic_relevance': 0.40,
                        'contextual_gain': 0.20,
                        'redundant_with_recent': False,
                        'reason': 'below_contextual_gain_threshold',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '2',
                        'keep': False,
                        'semantic_relevance': 0.20,
                        'contextual_gain': 0.10,
                        'redundant_with_recent': False,
                        'reason': 'fallback:parse_or_runtime_error',
                        'decision_source': 'fallback',
                        'model': 'openrouter/arbiter-v1',
                    },
                ],
                effective_model='openrouter/arbiter-v1',
                mode='shadow',
                conn_factory=lambda: FailingConn(),
                trace_float_fn=lambda value: float(value or 0.0),
                logger=SimpleNamespace(error=lambda *_a, **_k: None, info=lambda *_a, **_k: None),
            )
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            log_store.insert_chat_log_event = original_insert

        arbiter_events = [event for event in observed if event['stage'] == 'arbiter']
        self.assertEqual(len(arbiter_events), 1)
        self.assertEqual(arbiter_events[0]['status'], 'error')
        payload = arbiter_events[0]['payload_json']
        self.assertEqual(payload['raw_candidates'], 3)
        self.assertEqual(payload['kept_candidates'], 1)
        self.assertEqual(payload['rejected_candidates'], 2)
        self.assertEqual(payload['decision_source'], 'mixed')
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['fallback_decisions'], 1)
        self.assertEqual(payload['rejection_reason_counts']['below_contextual_gain_threshold'], 1)
        self.assertEqual(payload['rejection_reason_counts']['fallback:parse_or_runtime_error'], 1)
        self.assertEqual(payload['error_class'], 'RuntimeError')

if __name__ == '__main__':
    unittest.main()
