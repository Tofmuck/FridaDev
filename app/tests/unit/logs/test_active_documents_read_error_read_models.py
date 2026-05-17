from __future__ import annotations

import json
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

from observability import dashboard_analytics, dashboard_read_model


class ActiveDocumentsReadErrorReadModelsTests(unittest.TestCase):
    def _event(
        self,
        stage: str,
        *,
        turn_id: str = 'turn-documents',
        status: str = 'ok',
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            'event_id': event_id or f'{turn_id}:{stage}',
            'conversation_id': 'conv-documents',
            'turn_id': turn_id,
            'ts': '2026-05-14T12:00:00+00:00',
            'stage': stage,
            'status': status,
            'payload_json': dict(payload or {}),
        }

    def _minimal_turn(self, turn_id: str) -> list[dict[str, Any]]:
        return [
            self._event('turn_start', turn_id=turn_id, payload={'user_msg_chars': 18}),
            self._event(
                'prompt_prepared',
                turn_id=turn_id,
                payload={'messages_count': 3, 'prompt': 'RAW PROMPT MUST NOT LEAK'},
            ),
            self._event(
                'llm_call',
                turn_id=turn_id,
                payload={'provider_caller': 'llm', 'response_chars': 42},
            ),
            self._event('persist_response', turn_id=turn_id, payload={'conversation_saved': True}),
            self._event('turn_end', turn_id=turn_id, payload={'final_status': 'ok'}),
        ]

    def _assert_content_free(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn('RAW DOCUMENT TEXT MUST NOT LEAK', encoded)
        self.assertNotIn('RAW PROMPT MUST NOT LEAK', encoded)

    def test_fact_keeps_read_error_distinct_from_empty(self) -> None:
        events = [
            *self._minimal_turn('turn-doc-read-error'),
            self._event(
                'active_documents',
                turn_id='turn-doc-read-error',
                status='error',
                payload={
                    'source_kind': 'active_conversation_documents',
                    'status': 'error',
                    'read_status': 'error',
                    'read_reason_code': 'active_documents_read_error',
                    'active_count': 0,
                    'injected_count': 0,
                    'not_injected_count': 0,
                    'reason_code_counts': {'active_documents_read_error': 1},
                    'documents': [],
                    'raw_content_included': False,
                    'text_content': 'RAW DOCUMENT TEXT MUST NOT LEAK',
                },
            ),
        ]

        fact = dashboard_analytics.build_dashboard_turn_fact(events)
        documents = fact['documents']

        self.assertEqual(documents['status'], 'error')
        self.assertEqual(documents['read_status'], 'error')
        self.assertEqual(documents['read_reason_code'], 'active_documents_read_error')
        self.assertEqual(documents['reason_code'], 'active_documents_read_error')
        self.assertEqual(documents['reason_code_counts'], {'active_documents_read_error': 1})
        self.assertEqual(documents['active_count'], 0)
        self.assertEqual(documents['documents'], [])
        self.assertFalse(documents['raw_content_included'])
        self._assert_content_free(fact)

    def test_dashboard_story_tells_read_error_without_inventing_document(self) -> None:
        fact = {
            'conversation_id': 'conv-documents-read-error',
            'turn_id': 'turn-documents-read-error',
            'classification': 'partial',
            'score': 80,
            'source_event_count': 6,
            'persistence': {'status': 'saved', 'assistant_final_saved': True},
            'providers': {'main': {'present': True, 'status': 'ok'}, 'secondary': {}},
            'rag': {'retrieved': 0, 'kept': 0, 'injected': 0},
            'identity': {'block_present': False, 'status': 'missing'},
            'hermeneutic': {'block_present': False, 'status': 'missing'},
            'web': {'requested': False, 'success': False, 'injected': False, 'status': 'not_applicable'},
            'documents': {
                'status': 'error',
                'read_status': 'error',
                'read_reason_code': 'active_documents_reader_unavailable',
                'active_count': 0,
                'injected_count': 0,
                'not_injected_count': 0,
                'reason_code_counts': {'active_documents_reader_unavailable': 1},
                'documents': [],
                'raw_content_included': False,
                'text_content': 'RAW DOCUMENT TEXT MUST NOT LEAK',
            },
            'node_state': {},
            'errors': {'error_count': 0, 'skipped_count': 0, 'fallback_count': 0, 'reason_code_counts': {}},
            'flags': {'events_truncated': False},
            'content_availability': {'content_comprehension_status': 'compact_only'},
        }

        story = dashboard_read_model._turn_story(fact)
        story_text = json.dumps(story, ensure_ascii=False, sort_keys=True)

        self.assertIn('lecture des documents actifs en erreur', story_text)
        self.assertIn('Erreur de lecture des documents actifs de conversation', story_text)
        self.assertIn('active_documents_reader_unavailable', story_text)
        self.assertIn('Aucun document actif n est affirme present', story_text)
        self.assertIn('Aucun texte de document actif n est affiche', story_text)
        self.assertNotIn('Aucun document actif de conversation n est observe sur ce tour', story_text)
        self.assertNotIn('RAW DOCUMENT TEXT MUST NOT LEAK', story_text)

    def test_empty_documents_stays_not_applicable(self) -> None:
        events = [
            *self._minimal_turn('turn-doc-empty'),
            self._event(
                'active_documents',
                turn_id='turn-doc-empty',
                payload={
                    'source_kind': 'active_conversation_documents',
                    'read_status': 'empty',
                    'active_count': 0,
                    'injected_count': 0,
                    'not_injected_count': 0,
                    'reason_code_counts': {},
                    'documents': [],
                    'raw_content_included': False,
                },
            ),
        ]

        fact = dashboard_analytics.build_dashboard_turn_fact(events)
        documents = fact['documents']
        story_lines = dashboard_read_model._document_story_lines(documents)

        self.assertEqual(documents['status'], 'not_applicable')
        self.assertEqual(documents['read_status'], 'empty')
        self.assertEqual(documents['active_count'], 0)
        self.assertEqual(documents['reason_code_counts'], {})
        self.assertEqual(
            dashboard_analytics.summarize_module_turn('documents', fact),
            'Aucun document actif de conversation n est observe sur ce tour.',
        )
        self.assertEqual(story_lines, ['Aucun document actif de conversation n est observe sur ce tour.'])


if __name__ == '__main__':
    unittest.main()
