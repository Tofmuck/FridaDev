from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
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

from observability import agentic_status
from observability import chat_turn_logger
from observability import log_store
from observability.turn_observability_checklist import build_turn_observability_checklist
from observability.turn_pipeline_read_model import build_turn_pipeline_item


class _NoopLogger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class AgenticObservabilityStatusTests(unittest.TestCase):
    def _event(
        self,
        stage: str,
        *,
        status: str = 'ok',
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            'event_id': event_id or f'evt-{stage}-{status}',
            'conversation_id': 'conv-agentic-status',
            'turn_id': 'turn-agentic-status',
            'ts': '2026-06-20T10:00:00Z',
            'stage': stage,
            'status': status,
            'status_v1': status,
            'status_schema_version': agentic_status.STATUS_SCHEMA_VERSION,
            'payload': dict(payload or {}),
        }

    def _complete_events(self) -> list[dict[str, Any]]:
        return [
            self._event('turn_start', payload={'web_search_enabled': False}),
            self._event(
                'prompt_prepared',
                payload={
                    'identity_prompt_injection': {
                        'injected': True,
                        'identity_block_present': True,
                    },
                    'memory_prompt_injection': {
                        'trace_memory_injected': True,
                        'trace_memory_injected_count': 1,
                    },
                },
            ),
            self._event('llm_call', payload={'provider_caller': 'llm', 'response_chars': 16}),
            self._event(
                'persist_response',
                payload={'persist_phase': 'assistant_final', 'conversation_saved': True},
            ),
            self._event('turn_end', payload={'final_status': 'ok'}),
        ]

    def test_log_store_accepts_status_taxonomy_v1(self) -> None:
        observed: dict[str, Any] = {'statuses': [], 'commits': 0}

        class FakeCursor:
            def __init__(self) -> None:
                self.rowcount = 1

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, params: tuple[Any, ...]) -> None:
                observed['statuses'].append(params[5])

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed['commits'] += 1

        for status in agentic_status.STATUS_V1_ALLOWED:
            with self.subTest(status=status):
                inserted = log_store.insert_chat_log_event(
                    {
                        'event_id': f'evt-{status}',
                        'conversation_id': 'conv-status',
                        'turn_id': 'turn-status',
                        'ts': '2026-06-20T10:00:00Z',
                        'stage': 'agentic_status',
                        'status': status,
                        'payload_json': {'status_schema_version': agentic_status.STATUS_SCHEMA_VERSION},
                    },
                    conn_factory=lambda: FakeConn(),
                    logger_instance=_NoopLogger(),
                )
                self.assertTrue(inserted)

        self.assertEqual(observed['statuses'], list(agentic_status.STATUS_V1_ALLOWED))
        self.assertEqual(observed['commits'], len(agentic_status.STATUS_V1_ALLOWED))

    def test_init_log_storage_migrates_status_check_to_taxonomy_v1(self) -> None:
        observed: dict[str, Any] = {'queries': []}

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
                observed['queries'].append(query)

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        log_store.init_log_storage(
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        joined = '\n'.join(observed['queries'])
        self.assertIn('DROP CONSTRAINT IF EXISTS chat_log_events_status_check', joined)
        self.assertIn('ADD CONSTRAINT chat_log_events_status_check', joined)
        for status in agentic_status.STATUS_V1_ALLOWED:
            self.assertIn(f"'{status}'", joined)

    def test_read_chat_log_events_projects_v1_and_legacy_without_backfill(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self._step = 0

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                self._step += 1

            def fetchone(self) -> tuple[int]:
                return (2,)

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        'evt-v1',
                        'conv-status',
                        'turn-status',
                        datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc),
                        'chat_response',
                        'refused',
                        None,
                        {'status_schema_version': agentic_status.STATUS_SCHEMA_VERSION, 'reason_code': 'payload_refused'},
                    ),
                    (
                        'evt-legacy',
                        'conv-status',
                        'turn-status',
                        datetime(2026, 6, 20, 9, 59, tzinfo=timezone.utc),
                        'branch_skipped',
                        'skipped',
                        None,
                        {'reason_code': 'not_applicable'},
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_store.read_chat_log_events(
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['items'][0]['status'], 'refused')
        self.assertEqual(result['items'][0]['status_v1'], 'refused')
        self.assertEqual(result['items'][0]['status_schema_version'], agentic_status.STATUS_SCHEMA_VERSION)
        self.assertFalse(result['items'][0]['legacy_status'])
        self.assertEqual(result['items'][1]['status'], 'skipped')
        self.assertEqual(result['items'][1]['status_v1'], 'skipped')
        self.assertEqual(result['items'][1]['status_schema_version'], 'legacy')
        self.assertTrue(result['items'][1]['legacy_status'])

    def test_legacy_ok_skipped_error_without_marker_stay_legacy(self) -> None:
        for status in (
            agentic_status.STATUS_OK,
            agentic_status.STATUS_SKIPPED,
            agentic_status.STATUS_ERROR,
        ):
            with self.subTest(status=status):
                self.assertEqual(
                    agentic_status.projected_schema_version(payload={}, status=status),
                    'legacy',
                )

    def test_chat_turn_logger_marks_fresh_ok_turn_as_agentic_v1(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-fresh-v1',
            user_msg='fresh status marker sentinel',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'prompt_prepared',
                payload={
                    'identity_prompt_injection': {
                        'injected': True,
                        'identity_block_present': True,
                    },
                    'memory_prompt_injection': {
                        'trace_memory_injected': True,
                        'trace_memory_injected_count': 1,
                    },
                },
            )
            chat_turn_logger.emit(
                'llm_call',
                payload={'provider_caller': 'llm', 'response_chars': 16},
            )
            chat_turn_logger.emit(
                'persist_response',
                payload={'persist_phase': 'assistant_final', 'conversation_saved': True},
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            chat_turn_logger.log_store.insert_chat_log_event = original_insert

        self.assertEqual(
            [event['stage'] for event in observed],
            ['turn_start', 'prompt_prepared', 'llm_call', 'persist_response', 'turn_end'],
        )
        self.assertEqual({event['status'] for event in observed}, {'ok'})
        for event in observed:
            self.assertEqual(
                event['payload_json'].get('status_schema_version'),
                agentic_status.STATUS_SCHEMA_VERSION,
            )

        item = build_turn_pipeline_item(observed)
        self.assertEqual(item['status_schema']['source_kind'], 'agentic_v1')
        self.assertEqual(item['status_schema']['v1_event_count'], len(observed))
        self.assertEqual(item['status_schema']['legacy_event_count'], 0)
        self.assertFalse(item['status_schema']['historical_events_reclassified'])

    def test_chat_turn_logger_invalid_writer_status_never_becomes_ok(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-invalid-status',
            user_msg='invalid status raw message sentinel',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'audit_invalid_status',
                status='totally_invalid_status',
                error_code='raw_invalid_error_code_sentinel',
                model='raw_invalid_model_sentinel',
                prompt_kind='raw_invalid_prompt_kind_sentinel',
                payload={'reason_code': 'synthetic_writer_bug'},
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            chat_turn_logger.log_store.insert_chat_log_event = original_insert

        invalid_event = next(
            event for event in observed if event['stage'] == 'audit_invalid_status'
        )
        self.assertEqual(invalid_event['status'], 'error')
        self.assertEqual(
            invalid_event['payload_json'].get('status_schema_version'),
            agentic_status.STATUS_SCHEMA_VERSION,
        )
        self.assertEqual(
            invalid_event['payload_json'].get('reason_code'),
            'agentic_status_invalid',
        )
        self.assertEqual(
            invalid_event['payload_json'].get('error_code'),
            'agentic_status_invalid',
        )
        self.assertTrue(invalid_event['payload_json'].get('invalid_status_redacted'))
        serialized = json.dumps(observed, sort_keys=True)
        self.assertNotIn('raw_invalid_error_code_sentinel', serialized)
        self.assertNotIn('raw_invalid_model_sentinel', serialized)
        self.assertNotIn('raw_invalid_prompt_kind_sentinel', serialized)
        self.assertNotIn('totally_invalid_status', serialized)
        self.assertNotIn('invalid status raw message sentinel', serialized)
        self.assertNotIn("'ok', 'synthetic'", serialized)

    def test_chat_turn_logger_valid_error_keeps_error_code(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-valid-error',
            user_msg='valid error raw message sentinel',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'upstream_error_stage',
                status='error',
                error_code='upstream_error',
                payload={'error_class': 'TimeoutError'},
            )
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            chat_turn_logger.log_store.insert_chat_log_event = original_insert

        error_event = next(
            event for event in observed if event['stage'] == 'upstream_error_stage'
        )
        self.assertEqual(error_event['status'], 'error')
        self.assertEqual(
            error_event['payload_json'].get('status_schema_version'),
            agentic_status.STATUS_SCHEMA_VERSION,
        )
        self.assertEqual(error_event['payload_json'].get('error_code'), 'upstream_error')
        self.assertNotIn('invalid_status_redacted', error_event['payload_json'])
        serialized = json.dumps(observed, sort_keys=True)
        self.assertNotIn('valid error raw message sentinel', serialized)

    def test_chat_turn_logger_emits_refusal_without_error_status(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-refused',
            user_msg='raw message must not be copied to refusal',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit_refusal(
                reason_code='payload_refused',
                reason_short='chat status 400',
                status='refused',
            )
            chat_turn_logger.end_turn(token, final_status='refused')
        finally:
            chat_turn_logger.log_store.insert_chat_log_event = original_insert

        statuses = {event['stage']: event['status'] for event in observed}
        self.assertEqual(statuses['chat_response'], 'refused')
        self.assertEqual(statuses['turn_end'], 'refused')
        self.assertNotIn('error', statuses.values())
        serialized = json.dumps(observed, sort_keys=True)
        self.assertNotIn('raw message must not be copied', serialized)

    def test_checklist_does_not_degrade_normal_agentic_noops(self) -> None:
        events = self._complete_events()
        events.extend(
            [
                self._event(
                    'web_search',
                    status='not_selected',
                    payload={'reason_code': 'web_search_not_requested'},
                ),
                self._event(
                    'agenda',
                    status='disabled',
                    payload={'reason_code': 'agenda_toggle_off'},
                ),
                self._event(
                    'biblio',
                    status='not_applicable',
                    payload={'reason_code': 'biblio_no_bibliographic_signal'},
                ),
                self._event(
                    'generated_images',
                    status='not_configured',
                    payload={'reason_code': 'provider_not_configured'},
                ),
            ]
        )

        checklist = build_turn_observability_checklist(events)

        self.assertEqual(checklist['classification'], 'complete')
        self.assertEqual(checklist['status_counts']['degraded'], 0)
        self.assertEqual(checklist['status_counts']['missing'], 0)
        self.assertEqual(self._find_item(checklist, 'stage_errors')['status'], 'ok')

    def test_checklist_keeps_failed_and_error_visible(self) -> None:
        events = self._complete_events()
        events.append(
            self._event(
                'secondary_provider',
                status='failed',
                payload={'reason_code': 'provider_timeout'},
            )
        )

        checklist = build_turn_observability_checklist(events)

        self.assertEqual(checklist['classification'], 'degraded')
        self.assertEqual(self._find_item(checklist, 'stage_errors')['status'], 'degraded')
        self.assertEqual(self._find_item(checklist, 'stage_errors')['reason_code'], 'stage_error_present')

    def test_turn_pipeline_distinguishes_v1_and_legacy_status_sources(self) -> None:
        events = self._complete_events()
        events.append(
            self._event(
                'chat_response',
                status='refused',
                payload={'reason_code': 'payload_refused'},
            )
        )
        events.append(
            {
                'event_id': 'evt-legacy-skipped',
                'conversation_id': 'conv-agentic-status',
                'turn_id': 'turn-agentic-status',
                'ts': '2026-06-20T09:59:00Z',
                'stage': 'legacy_stage',
                'status': 'skipped',
                'payload': {'reason_code': 'legacy_skip'},
            }
        )

        item = build_turn_pipeline_item(events)

        self.assertEqual(item['status_schema']['source_kind'], 'mixed_v1_and_legacy')
        self.assertEqual(item['status_schema']['v1_event_count'], len(events) - 1)
        self.assertEqual(item['status_schema']['legacy_event_count'], 1)
        self.assertFalse(item['status_schema']['historical_events_reclassified'])
        self.assertEqual(item['errors']['refused_count'], 1)
        self.assertEqual(item['errors']['error_count'], 0)

    def _find_item(self, checklist: dict[str, Any], key: str) -> dict[str, Any]:
        for item in checklist.get('items') or []:
            if item.get('key') == key:
                return item
        raise AssertionError(f'checklist item not found: {key}')


if __name__ == '__main__':
    unittest.main()
