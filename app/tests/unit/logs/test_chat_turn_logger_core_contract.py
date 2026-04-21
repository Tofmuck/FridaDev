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


class ChatTurnLoggerCoreContractTests(unittest.TestCase):
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

    def test_end_turn_uses_error_status_when_final_status_is_error(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-error',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            log_store.insert_chat_log_event = original_insert

        turn_end_event = observed[-1]
        self.assertEqual(turn_end_event['stage'], 'turn_end')
        self.assertEqual(turn_end_event['status'], 'error')
        self.assertEqual(turn_end_event['payload_json']['final_status'], 'error')

    def test_pending_conversation_buffers_until_real_conversation_id(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id=None,
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'web_search',
                status='skipped',
                reason_code='feature_disabled',
                payload={
                    'enabled': False,
                    'query_preview': '',
                    'results_count': 0,
                    'context_injected': False,
                    'truncated': False,
                },
            )
            self.assertEqual(observed, [])
            chat_turn_logger.update_conversation_id('conv-real')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(observed[0]['stage'], 'turn_start')
        self.assertEqual(observed[1]['stage'], 'web_search')
        self.assertTrue(all(event['conversation_id'] == 'conv-real' for event in observed))
        self.assertNotIn('__pending__', {event['conversation_id'] for event in observed})

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
            self.assertFalse(chat_turn_logger.emit('context_build', status='ok', payload={'estimated_context_tokens': 12}))
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
                'preview_stage',
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

        preview_event = next(event for event in observed if event['stage'] == 'preview_stage')
        payload = preview_event['payload_json']
        self.assertEqual(len(payload['preview']), 3)
        self.assertEqual(len(payload['keys']), 3)
        self.assertTrue(payload['truncated'])
        self.assertTrue(all(len(item) <= 120 for item in payload['preview']))
        self.assertTrue(all(len(item) <= 64 for item in payload['keys']))

    def test_event_contract_required_fields_and_status_taxonomy(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-contract',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit('context_build', status='ok', payload={'estimated_context_tokens': 42, 'token_limit': 4000})
            chat_turn_logger.emit_branch_skipped(reason_code='no_data', reason_short='no_optional_branch')
            chat_turn_logger.emit_error(
                error_code='upstream_error',
                error_class='RuntimeError',
                message_short='boom',
            )
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertTrue(observed)
        required = {'event_id', 'conversation_id', 'turn_id', 'ts', 'stage', 'status'}
        statuses: set[str] = set()
        for event in observed:
            self.assertTrue(required.issubset(set(event.keys())))
            for field in required:
                self.assertTrue(str(event[field] or '').strip(), msg=f'empty field {field} in {event}')
            statuses.add(str(event['status']))

        self.assertTrue({'ok', 'error', 'skipped'}.issubset(statuses))


if __name__ == '__main__':
    unittest.main()
