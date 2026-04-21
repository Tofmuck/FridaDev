from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_memory_flow
from memory import hermeneutics_policy
from memory import memory_identity_dynamics


def _event_payloads(events, name: str):
    return [payload for event, payload in events if event == name]

class ChatMemoryFlowTests(unittest.TestCase):
    def test_record_identity_entries_for_mode_filters_unsupported_web_reading_claim_in_enforced_mode(self) -> None:
        events = []
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Claims to have the linked article open and read it',
                    'confidence': 0.91,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-guard-enforced',
            [{'role': 'assistant', 'content': 'bad claim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_not_read_snippet_fallback'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-guard-enforced', []))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['action'], 'record_legacy_identity_diagnostics_and_stage')
        self.assertEqual(event['entries'], 0)
        self.assertEqual(event['extracted_entries'], 1)
        self.assertEqual(event['guard_filtered_count'], 1)
        self.assertEqual(event['guard_filtered_by_side'], {'frida': 1, 'user': 0})
        self.assertEqual(
            event['guard_reason_codes_by_side']['frida'],
            ['web_reading_claim_unsupported_for_page_not_read_snippet_fallback'],
        )
        self.assertEqual(event['guard_reason_codes_by_side']['user'], [])
        self.assertNotIn('guard_filtered_preview', event)

    def test_record_identity_entries_for_mode_filters_frida_pipeline_meta_identity_in_enforced_mode(self) -> None:
        events = []
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Unable to provide a substantive answer on that turn because the rules did not allow it',
                    'confidence': 0.92,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-meta-filter',
            [{'role': 'assistant', 'content': 'meta'}],
            mode='enforced_all',
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-meta-filter', []))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['guard_filtered_count'], 1)
        self.assertEqual(event['guard_filtered_by_side'], {'frida': 1, 'user': 0})
        self.assertEqual(
            event['guard_reason_codes_by_side']['frida'],
            ['llm_identity_pipeline_meta'],
        )
        self.assertEqual(event['guard_reason_codes_by_side']['user'], [])
        self.assertNotIn('guard_filtered_preview', event)

    def test_record_identity_entries_for_mode_keeps_prudent_web_limitation_statement(self) -> None:
        events = []
        observed = {'persisted': None}
        prudent_entry = {
            'subject': 'llm',
            'content': "Frida n'a pas accès au contenu complet d'un article via un lien direct dans ce contexte",
            'confidence': 0.82,
            'stability': 'episodic',
            'utterance_mode': 'self_description',
            'recurrence': 'first_seen',
            'scope': 'llm',
            'evidence_kind': 'explicit',
        }

        arbiter_module = SimpleNamespace(extract_identities=lambda _turns: [dict(prudent_entry)])
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-prudent',
            [{'role': 'assistant', 'content': 'prudent claim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_not_read_crawl_empty'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-prudent', [prudent_entry]))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['guard_filtered_count'], 0)

    def test_record_identity_entries_for_mode_keeps_supported_direct_reading_claim_when_page_read(self) -> None:
        events = []
        observed = {'persisted': None}
        direct_read_entry = {
            'subject': 'llm',
            'content': 'Claims to have the linked article open and read it',
            'confidence': 0.91,
            'stability': 'durable',
            'utterance_mode': 'self_description',
            'recurrence': 'repeated',
            'scope': 'llm',
            'evidence_kind': 'explicit',
        }

        arbiter_module = SimpleNamespace(extract_identities=lambda _turns: [dict(direct_read_entry)])
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-page-read',
            [{'role': 'assistant', 'content': 'supported claim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_read'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-page-read', [direct_read_entry]))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['guard_filtered_count'], 0)

    def test_record_identity_entries_for_mode_filters_overclaim_when_page_partially_read(self) -> None:
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Claims to have read the full article in detail',
                    'confidence': 0.88,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-partial',
            [{'role': 'assistant', 'content': 'overclaim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_partially_read'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-partial', []))

    def test_record_identity_entries_for_mode_accepts_explicit_user_identity_revelation(self) -> None:
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'user',
                    'content': 'Je suis Christophe Muck',
                    'confidence': 0.93,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'first_seen',
                    'scope': 'user',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {
                    'persisted': (
                        conversation_id,
                        memory_identity_dynamics.preview_identity_entries(
                            list(entries),
                            policy_module=hermeneutics_policy,
                            config_module=SimpleNamespace(
                                IDENTITY_MIN_CONFIDENCE=0.6,
                                IDENTITY_DEFER_MIN_CONFIDENCE=0.3,
                            ),
                            trace_float_fn=lambda value: float(value or 0.0),
                        ),
                    )
                }
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-user-identity-revelation',
            [{'role': 'user', 'content': 'Je suis Christophe Muck'}],
            mode='enforced_all',
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        persisted = observed['persisted']
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted[0], 'conv-user-identity-revelation')
        self.assertEqual(persisted[1][0]['status'], 'accepted')
        self.assertIn('explicit_user_identity_revelation', persisted[1][0]['reason'])


if __name__ == '__main__':
    unittest.main()
