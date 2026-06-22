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

from observability import chat_turn_logger
from observability import admin_log_projection
from observability import log_markdown_export
from observability import log_store
from observability import observability_payload_guard


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
        self.assertEqual(preview_event['status'], 'refused')
        self.assertEqual(payload['schema_version'], observability_payload_guard.SCHEMA_VERSION)
        self.assertEqual(payload['reason_code'], observability_payload_guard.REASON_CODE)
        encoded = json.dumps({'event': preview_event}, ensure_ascii=False)
        for marker in ('x' * 80, 'y' * 80, 'z' * 80, 'w' * 80):
            self.assertNotIn(marker, encoded)

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
            chat_turn_logger.emit(
                'context_build',
                status='ok',
                payload={
                    'estimated_context_tokens': 42,
                    'prompt_soft_token_limit': 4000,
                    'prompt_soft_limit_exceeded': False,
                    'dialogue_messages_truncated': False,
                },
            )
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

    def test_writer_guard_rejects_raw_payload_without_false_ok(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        raw_message = 'SENSITIVE_WRITER_MESSAGE_C'
        raw_url = 'https://provider.example.invalid/raw?token=secret'
        raw_data_url = 'data:image/png;base64,AAAA'

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-writer-guard',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'writer_guard_probe',
                status='ok',
                payload={
                    'messages': [{'role': 'user', 'content': raw_message}],
                    'nested': {
                        'provider_payload': {'content': raw_message},
                        'reason_code': raw_url,
                        'image_data_url': raw_data_url,
                    },
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        rejected = next(event for event in observed if event['stage'] == 'writer_guard_probe')
        payload = rejected['payload_json']
        self.assertEqual(rejected['status'], 'refused')
        self.assertEqual(payload['schema_version'], observability_payload_guard.SCHEMA_VERSION)
        self.assertEqual(payload['reason_code'], observability_payload_guard.REASON_CODE)
        self.assertEqual(payload['guarded_original_status'], 'ok')
        self.assertFalse(payload['raw_event_payloads_included'])
        self.assertFalse(payload['raw_message_included'])
        self.assertFalse(payload['raw_provider_payload_included'])

        projected = admin_log_projection.project_event_item(
            {
                'event_id': rejected['event_id'],
                'conversation_id': rejected['conversation_id'],
                'turn_id': rejected['turn_id'],
                'ts': rejected['ts'],
                'stage': rejected['stage'],
                'status': rejected['status'],
                'duration_ms': rejected['duration_ms'],
                'payload': rejected['payload_json'],
            }
        )
        markdown = log_markdown_export._build_markdown(
            scope='turn',
            conversation_id='conv-writer-guard',
            turn_id=rejected['turn_id'],
            items=[projected],
            generated_at=datetime(2026, 6, 22, tzinfo=timezone.utc),
        )
        encoded = json.dumps({'event': rejected, 'projection': projected, 'markdown': markdown}, ensure_ascii=False)
        for marker in (raw_message, raw_url, raw_data_url, 'provider.example.invalid', 'base64'):
            self.assertNotIn(marker, encoded)

    def test_writer_guard_rejects_neutral_free_text_without_false_ok(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        sentinel = 'neutral writer text sentinel should not pass'

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-writer-neutral-guard',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'writer_guard_neutral_probe',
                status='ok',
                payload={
                    'private_sentence': sentinel,
                    'safe_count': 1,
                    'status_schema_version': 'agentic_v1',
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        rejected = next(event for event in observed if event['stage'] == 'writer_guard_neutral_probe')
        payload = rejected['payload_json']
        self.assertEqual(rejected['status'], 'refused')
        self.assertEqual(payload['schema_version'], observability_payload_guard.SCHEMA_VERSION)
        self.assertEqual(payload['reason_code'], observability_payload_guard.REASON_CODE)
        self.assertIn('unknown_string_key', payload['issue_classes'])

        projected = admin_log_projection.project_event_item(
            {
                'event_id': rejected['event_id'],
                'conversation_id': rejected['conversation_id'],
                'turn_id': rejected['turn_id'],
                'ts': rejected['ts'],
                'stage': rejected['stage'],
                'status': rejected['status'],
                'duration_ms': rejected['duration_ms'],
                'payload': rejected['payload_json'],
            }
        )
        markdown = log_markdown_export._build_markdown(
            scope='turn',
            conversation_id='conv-writer-neutral-guard',
            turn_id=rejected['turn_id'],
            items=[projected],
            generated_at=datetime(2026, 6, 22, tzinfo=timezone.utc),
        )
        encoded = json.dumps({'event': rejected, 'projection': projected, 'markdown': markdown}, ensure_ascii=False)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn('private_sentence', encoded)

    def test_writer_guard_allows_valid_main_payload_manifest(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        manifest = {
            'schema_version': 'main_payload_manifest_v1',
            'scope': 'main_chat',
            'main_model_called': True,
            'messages': [
                {
                    'index': 0,
                    'provider_role': 'system',
                    'logical_roles': ['system_prompt'],
                    'origin': 'core.chat_prompt_context',
                    'origin_stage': 'base_prompt_with_guards',
                    'content_kind': 'system_instruction',
                    'content_present': True,
                    'content_chars': 42,
                    'estimated_tokens': 8,
                    'excluded': False,
                    'exclusion_reason_code': '',
                    'content_parts_count': 1,
                    'text_part_count': 1,
                    'image_part_count': 0,
                    'file_part_count': 0,
                    'raw_content_included': False,
                }
            ],
            'lane_statuses': {
                'system_prompt': {
                    'status': 'ok',
                    'reason_code': '',
                    'selected': True,
                    'enabled': True,
                    'input_count': 1,
                    'injected_count': 1,
                    'excluded_count': 0,
                    'content_chars': 42,
                    'estimated_tokens': None,
                    'origin': 'core.chat_prompt_context',
                    'raw_lane_content_included': False,
                }
            },
            'raw_flags': {
                'raw_prompt_included': False,
                'raw_message_included': False,
                'raw_content_included': False,
                'raw_lane_content_included': False,
                'raw_provider_payload_included': False,
                'raw_secret_included': False,
            },
        }

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-valid-manifest',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit('main_payload_manifest', status='ok', payload=manifest)
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        manifest_event = next(event for event in observed if event['stage'] == 'main_payload_manifest')
        self.assertEqual(manifest_event['status'], 'ok')
        self.assertEqual(manifest_event['payload_json']['schema_version'], 'main_payload_manifest_v1')
        self.assertNotEqual(
            manifest_event['payload_json'].get('reason_code'),
            observability_payload_guard.REASON_CODE,
        )


if __name__ == '__main__':
    unittest.main()
