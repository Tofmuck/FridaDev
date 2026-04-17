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


class IdentityMutableRewriterPhase1BTests(unittest.TestCase):
    def test_validate_rewriter_contract_accepts_strict_no_change_and_rewrite(self) -> None:
        validated, rejections = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {
                    'action': 'no_change',
                    'content': '',
                    'reason': 'no durable update',
                },
                'user': {
                    'action': 'rewrite',
                    'content': 'Utilisateur prefere des reponses breves et structurees.',
                    'reason': 'new durable preference',
                },
            }
        )

        self.assertEqual(rejections, [])
        self.assertEqual(validated['llm']['action'], 'no_change')
        self.assertEqual(validated['user']['action'], 'rewrite')
        self.assertIn('Utilisateur prefere', validated['user']['content'])

    def test_validate_rewriter_contract_rejects_rewrite_above_hard_cap(self) -> None:
        validated, rejections = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {
                    'action': 'rewrite',
                    'content': 'x' * 3301,
                    'reason': 'too long',
                },
                'user': {
                    'action': 'no_change',
                    'content': '',
                    'reason': 'no durable update',
                },
            }
        )

        self.assertIn('user', validated)
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]['subject'], 'llm')
        self.assertEqual(rejections[0]['reason_code'], 'mutable_content_too_long')
        self.assertEqual(rejections[0]['new_len'], 3301)

    def test_validate_rewriter_contract_rejects_subject_without_explicit_content_key(self) -> None:
        validated, rejections = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {
                    'action': 'no_change',
                    'reason': 'no durable update',
                },
                'user': {
                    'action': 'no_change',
                    'content': '',
                    'reason': 'no durable update',
                },
            }
        )

        self.assertIn('user', validated)
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]['subject'], 'llm')
        self.assertEqual(rejections[0]['reason_code'], 'contract_content_missing')

    def test_validate_rewriter_contract_rejects_subject_without_explicit_reason_key(self) -> None:
        validated, rejections = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {
                    'action': 'no_change',
                    'content': '',
                },
                'user': {
                    'action': 'no_change',
                    'content': '',
                    'reason': 'no durable update',
                },
            }
        )

        self.assertIn('user', validated)
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]['subject'], 'llm')
        self.assertEqual(rejections[0]['reason_code'], 'contract_reason_missing')

    def test_validate_rewriter_contract_rejects_prompt_like_rewrite_in_english(self) -> None:
        validated, rejections = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {
                    'action': 'rewrite',
                    'content': 'You must verify sources and cite each important point.',
                    'reason': 'durable policy',
                },
                'user': {
                    'action': 'no_change',
                    'content': '',
                    'reason': 'no durable update',
                },
            }
        )

        self.assertNotIn('llm', validated)
        self.assertEqual(rejections[0]['subject'], 'llm')
        self.assertEqual(rejections[0]['reason_code'], 'mutable_content_prompt_like_operator_instruction')

    def test_validate_rewriter_contract_accepts_technical_interest_as_narrative_identity(self) -> None:
        validated, rejections = memory_identity_mutable_rewriter.validate_rewriter_contract(
            {
                'llm': {
                    'action': 'no_change',
                    'content': '',
                    'reason': 'no durable update',
                },
                'user': {
                    'action': 'rewrite',
                    'content': 'Tof aime discuter du runtime, des pipelines et des architectures complexes.',
                    'reason': 'durable technical interest',
                },
            }
        )

        self.assertEqual(rejections, [])
        self.assertEqual(validated['user']['action'], 'rewrite')
        self.assertIn('runtime', validated['user']['content'])

    def test_refresh_mutable_identities_applies_valid_rewrite_and_logs_compact_outcomes(self) -> None:
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
                arbiter_module=type(
                    'ArbiterStub',
                    (),
                    {
                        'rewrite_identity_mutables': staticmethod(
                            lambda _payload: {
                                'llm': {
                                    'action': 'no_change',
                                    'content': '',
                                    'reason': 'no durable update',
                                },
                                'user': {
                                    'action': 'rewrite',
                                    'content': 'Utilisateur prefere des reponses tres courtes, directes et structurees.',
                                    'reason': 'new durable preference',
                                },
                            }
                        )
                    },
                )(),
                memory_store_module=store,
                load_llm_identity_fn=lambda: 'Frida statique',
                load_user_identity_fn=lambda: 'Utilisateur statique',
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(summary['status'], 'ok')
        by_subject = {item['subject']: item for item in summary['outcomes']}
        self.assertEqual(by_subject['llm']['action'], 'no_change')
        self.assertEqual(by_subject['user']['action'], 'rewrite')
        self.assertEqual(by_subject['user']['reason_code'], 'rewrite_applied')
        self.assertEqual(
            store.state['user']['content'],
            'Utilisateur prefere des reponses tres courtes, directes et structurees.',
        )
        self.assertEqual(store.upsert_calls[0][0], 'user')
        self.assertEqual(store.upsert_calls[0][2], 'identity_mutable_rewriter')
        rewrite_event = next(event for event in observed_events if event['stage'] == 'identity_mutable_rewrite')
        payload = rewrite_event['payload_json']
        self.assertEqual(payload['request_status'], 'ok')
        self.assertEqual(payload['reason_code'], 'processed')
        self.assertNotIn('preview', payload)
        self.assertTrue(all('content' not in outcome for outcome in payload['outcomes']))

    def test_refresh_mutable_identities_treats_identical_rewrite_as_no_change(self) -> None:
        store = _MutableStore(
            {
                'llm': {'subject': 'llm', 'content': 'Frida garde une voix sobre.'},
                'user': {'subject': 'user', 'content': 'Utilisateur prefere la clarte.'},
            }
        )

        summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
            [{'role': 'assistant', 'content': 'Reponse structurée.'}],
            arbiter_module=type(
                'ArbiterStub',
                (),
                {
                    'rewrite_identity_mutables': staticmethod(
                        lambda _payload: {
                            'llm': {
                                'action': 'rewrite',
                                'content': 'Frida garde une voix sobre.',
                                'reason': 'same content',
                            },
                            'user': {
                                'action': 'no_change',
                                'content': '',
                                'reason': 'no durable update',
                            },
                        }
                    )
                },
            )(),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida statique',
            load_user_identity_fn=lambda: 'Utilisateur statique',
        )

        by_subject = {item['subject']: item for item in summary['outcomes']}
        self.assertEqual(by_subject['llm']['action'], 'no_change')
        self.assertEqual(by_subject['llm']['reason_code'], 'unchanged')
        self.assertEqual(store.upsert_calls, [])

    def test_refresh_mutable_identities_rejects_too_long_rewrite_without_erasing_existing_state(self) -> None:
        store = _MutableStore(
            {
                'llm': {'subject': 'llm', 'content': 'Frida garde une voix sobre.'},
                'user': {'subject': 'user', 'content': 'Utilisateur prefere la clarte.'},
            }
        )
        summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
            [{'role': 'user', 'content': 'Ajoute beaucoup de details.'}],
            arbiter_module=type(
                'ArbiterStub',
                (),
                {
                    'rewrite_identity_mutables': staticmethod(
                        lambda _payload: {
                            'llm': {
                                'action': 'rewrite',
                                'content': 'x' * 3301,
                                'reason': 'too long',
                            },
                            'user': {
                                'action': 'no_change',
                                'content': '',
                                'reason': 'no durable update',
                            },
                        }
                    )
                },
            )(),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida statique',
            load_user_identity_fn=lambda: 'Utilisateur statique',
        )

        by_subject = {item['subject']: item for item in summary['outcomes']}
        self.assertEqual(by_subject['llm']['action'], 'rejected')
        self.assertEqual(by_subject['llm']['reason_code'], 'mutable_content_too_long')
        self.assertEqual(store.state['llm']['content'], 'Frida garde une voix sobre.')
        self.assertEqual(store.upsert_calls, [])

    def test_refresh_mutable_identities_rejects_prompt_like_rewrite_without_erasing_existing_state(self) -> None:
        store = _MutableStore(
            {
                'llm': {'subject': 'llm', 'content': 'Frida garde une voix sobre.'},
                'user': {'subject': 'user', 'content': 'Utilisateur prefere la clarte.'},
            }
        )
        summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
            [{'role': 'user', 'content': 'Peux-tu garder une trace durable ?'}],
            arbiter_module=type(
                'ArbiterStub',
                (),
                {
                    'rewrite_identity_mutables': staticmethod(
                        lambda _payload: {
                            'llm': {
                                'action': 'rewrite',
                                'content': 'You must verify sources and cite each important point.',
                                'reason': 'durable policy',
                            },
                            'user': {
                                'action': 'no_change',
                                'content': '',
                                'reason': 'no durable update',
                            },
                        }
                    )
                },
            )(),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida statique',
            load_user_identity_fn=lambda: 'Utilisateur statique',
        )

        by_subject = {item['subject']: item for item in summary['outcomes']}
        self.assertEqual(by_subject['llm']['action'], 'rejected')
        self.assertEqual(
            by_subject['llm']['reason_code'],
            'mutable_content_prompt_like_operator_instruction',
        )
        self.assertEqual(store.state['llm']['content'], 'Frida garde une voix sobre.')
        self.assertEqual(store.upsert_calls, [])

    def test_refresh_mutable_identities_accepts_narrative_technical_interest(self) -> None:
        store = _MutableStore(
            {
                'llm': {'subject': 'llm', 'content': 'Frida garde une voix sobre.'},
                'user': {'subject': 'user', 'content': 'Utilisateur prefere la clarte.'},
            }
        )
        summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
            [{'role': 'user', 'content': 'Je reviens souvent sur les architectures complexes.'}],
            arbiter_module=type(
                'ArbiterStub',
                (),
                {
                    'rewrite_identity_mutables': staticmethod(
                        lambda _payload: {
                            'llm': {
                                'action': 'no_change',
                                'content': '',
                                'reason': 'no durable update',
                            },
                            'user': {
                                'action': 'rewrite',
                                'content': 'Tof aime discuter du runtime, des pipelines et des architectures complexes.',
                                'reason': 'durable technical interest',
                            },
                        }
                    )
                },
            )(),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida statique',
            load_user_identity_fn=lambda: 'Utilisateur statique',
        )

        by_subject = {item['subject']: item for item in summary['outcomes']}
        self.assertEqual(by_subject['user']['action'], 'rewrite')
        self.assertEqual(by_subject['user']['reason_code'], 'rewrite_applied')
        self.assertIn('runtime', store.state['user']['content'])


if __name__ == '__main__':
    unittest.main()
