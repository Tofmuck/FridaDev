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

from memory import memory_identity_mutable_rewriter
from observability import chat_turn_logger
from observability import log_store


class _MutableStore:
    def __init__(self, initial: dict[str, dict[str, Any]] | None = None) -> None:
        self.state = {key: dict(value) for key, value in (initial or {}).items()}
        self.upsert_calls: list[tuple[str, str, str, str]] = []

    def get_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        item = self.state.get(subject)
        return dict(item) if item is not None else None

    def upsert_mutable_identity(
        self,
        subject: str,
        content: str,
        source_trace_id: str | None = None,
        *,
        updated_by: str = 'system',
        update_reason: str = '',
    ) -> dict[str, Any] | None:
        self.upsert_calls.append((subject, content, updated_by, update_reason))
        self.state[subject] = {
            'subject': subject,
            'content': content,
            'source_trace_id': source_trace_id,
            'updated_by': updated_by,
            'update_reason': update_reason,
        }
        return dict(self.state[subject])


class LegacyIdentityMutableRewriterCompatibilityTests(unittest.TestCase):
    def test_validate_rewriter_contract_reports_retired_legacy_shim_for_both_subjects(self) -> None:
        validated, outcomes = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {'action': 'rewrite', 'content': 'obsolete', 'reason': 'obsolete'},
                'user': {'action': 'rewrite', 'content': 'obsolete', 'reason': 'obsolete'},
            }
        )

        self.assertEqual(validated, {})
        self.assertEqual([item['subject'] for item in outcomes], ['llm', 'user'])
        self.assertTrue(all(item['action'] == 'retired' for item in outcomes))
        self.assertTrue(all(item['reason_code'] == 'legacy_rewriter_retired' for item in outcomes))

    def test_refresh_mutable_identities_keeps_existing_state_untouched_and_emits_branch_skipped(self) -> None:
        observed_events: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        log_store.insert_chat_log_event = lambda event, **_kwargs: observed_events.append(event) or True
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-mutable-rewriter',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        store = _MutableStore(
            {
                'llm': {'subject': 'llm', 'content': 'Frida garde une voix sobre.'},
                'user': {'subject': 'user', 'content': 'Utilisateur prefere la clarte.'},
            }
        )
        try:
            summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
                [{'role': 'user', 'content': 'Je prefere des reponses tres courtes.'}],
                arbiter_module=object(),
                memory_store_module=store,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'legacy_rewriter_retired')
        self.assertFalse(summary['legacy_runtime_active'])
        self.assertEqual(
            [item['old_len'] for item in summary['outcomes']],
            [len(store.state['llm']['content']), len(store.state['user']['content'])],
        )
        self.assertEqual(store.upsert_calls, [])
        branch_event = next(event for event in observed_events if event['stage'] == 'branch_skipped')
        self.assertEqual(branch_event['payload_json']['reason_code'], 'legacy_rewriter_retired')
        self.assertEqual(
            branch_event['payload_json']['reason_short'],
            'identity_legacy_rewriter_disabled',
        )
        self.assertFalse(any(event['stage'] == 'identity_mutable_rewrite' for event in observed_events))

    def test_refresh_mutable_identities_stays_fail_closed_when_store_is_missing(self) -> None:
        summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
            [],
            arbiter_module=object(),
            memory_store_module=object(),
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'legacy_rewriter_retired')
        self.assertTrue(all(item['old_len'] == 0 for item in summary['outcomes']))


if __name__ == '__main__':
    unittest.main()
