from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from observability import active_documents_observability


class ActiveDocumentsObservabilityLot7Tests(unittest.TestCase):
    def test_prompt_decision_payload_is_content_free(self) -> None:
        lane = SimpleNamespace(
            decisions=(
                SimpleNamespace(
                    document_id='doc-injected',
                    filename='note.txt',
                    media_type='text/plain',
                    source_extension='.txt',
                    byte_size=42,
                    text_chars=31,
                    token_estimate=8,
                    text_sha256_12='hashtext1234',
                    ocr_applied=True,
                    ocr_engine='stirling-pdf',
                    ocr_languages='fra+eng+deu',
                    ocr_duration_ms=1200,
                    injected=True,
                    reason_code='',
                    text_content='RAW DOCUMENT TEXT MUST NOT LEAK',
                ),
                SimpleNamespace(
                    document_id='doc-large',
                    filename='grand.pdf',
                    media_type='application/pdf',
                    source_extension='.pdf',
                    byte_size=900000,
                    text_chars=300000,
                    token_estimate=75000,
                    text_sha256_12='hashlarge123',
                    injected=False,
                    reason_code='document_too_large_for_turn',
                    text_content='RAW LARGE DOCUMENT TEXT MUST NOT LEAK',
                ),
            )
        )

        payload = active_documents_observability.build_prompt_decision_payload(lane)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertEqual(payload['source_kind'], 'active_conversation_documents')
        self.assertEqual(payload['active_count'], 2)
        self.assertEqual(payload['injected_count'], 1)
        self.assertEqual(payload['not_injected_count'], 1)
        self.assertEqual(payload['too_large_count'], 1)
        self.assertEqual(payload['ocr_applied_count'], 1)
        self.assertEqual(payload['ocr_duration_ms_total'], 1200)
        self.assertEqual(payload['ocr_engine_counts'], {'stirling-pdf': 1})
        self.assertTrue(payload['documents'][0]['ocr_applied'])
        self.assertEqual(payload['reason_code_counts'], {'document_too_large_for_turn': 1})
        self.assertFalse(payload['future_biblio_included'])
        self.assertFalse(payload['raw_content_included'])
        self.assertIn('document_ref', payload['documents'][0])
        self.assertNotIn('RAW DOCUMENT TEXT MUST NOT LEAK', encoded)
        self.assertNotIn('RAW LARGE DOCUMENT TEXT MUST NOT LEAK', encoded)
        self.assertNotIn('text_content', encoded)

    def test_prompt_decision_event_uses_active_documents_stage(self) -> None:
        events: list[dict[str, object]] = []
        lane = SimpleNamespace(
            decisions=(
                SimpleNamespace(
                    document_id='doc-1',
                    filename='note.txt',
                    media_type='text/plain',
                    source_extension='.txt',
                    byte_size=42,
                    text_chars=31,
                    token_estimate=8,
                    text_sha256_12='hashtext1234',
                    injected=True,
                    reason_code='',
                ),
            )
        )
        logger = SimpleNamespace(
            emit=lambda stage, status, payload: events.append(
                {'stage': stage, 'status': status, 'payload': payload}
            )
            or True
        )

        self.assertTrue(
            active_documents_observability.emit_prompt_decision_event(
                lane,
                chat_turn_logger_module=logger,
            )
        )

        self.assertEqual(events[0]['stage'], 'active_documents')
        self.assertEqual(events[0]['status'], 'ok')
        self.assertEqual(events[0]['payload']['injected_count'], 1)

    def test_admin_activation_and_remove_events_are_content_free(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        admin_logs = SimpleNamespace(
            log_event=lambda stage, **payload: events.append((stage, payload))
        )

        active_documents_observability.log_activation_success(
            admin_logs,
            conversation_id='conv-1',
            document={
                'document_id': 'doc-1',
                'filename': 'note.txt',
                'media_type': 'text/plain',
                'source_extension': '.txt',
                'byte_size': 42,
                'text_chars': 31,
                'token_estimate': 8,
                'text_sha256_12': 'hashtext1234',
                'ocr_applied': True,
                'ocr_engine': 'stirling-pdf',
                'ocr_languages': 'fra+eng+deu',
                'ocr_duration_ms': 1200,
                'text_content': 'RAW DOCUMENT TEXT MUST NOT LEAK',
            },
        )
        active_documents_observability.log_activation_failure(
            admin_logs,
            conversation_id='conv-1',
            extraction={
                'filename': 'bad.bin',
                'media_type': 'application/octet-stream',
                'source_extension': '.bin',
                'status': 'unsupported',
                'reason_code': 'document_type_unsupported',
                'ocr_applied': False,
                'ocr_engine': 'stirling-pdf',
                'ocr_languages': 'fra+eng+deu',
                'ocr_duration_ms': 800,
                'text': 'RAW BAD DOCUMENT TEXT MUST NOT LEAK',
            },
        )
        active_documents_observability.log_manual_remove(
            admin_logs,
            conversation_id='conv-1',
            document_id='doc-1',
        )

        encoded = json.dumps(events, ensure_ascii=False, sort_keys=True)
        self.assertEqual([stage for stage, _payload in events], [
            'active_document_activated',
            'active_document_activation_failed',
            'active_document_removed',
        ])
        self.assertIn('document_ref', events[0][1])
        self.assertTrue(events[0][1]['ocr_applied'])
        self.assertEqual(events[0][1]['ocr_engine'], 'stirling-pdf')
        self.assertEqual(events[1][1]['ocr_duration_ms'], 800)
        self.assertEqual(events[2][1]['reason_code'], 'manual_remove')
        self.assertNotIn('turn_id', events[1][1])
        self.assertNotIn('turn_id', events[2][1])
        self.assertNotIn('RAW DOCUMENT TEXT MUST NOT LEAK', encoded)
        self.assertNotIn('RAW BAD DOCUMENT TEXT MUST NOT LEAK', encoded)
        self.assertNotIn('text_content', encoded)


if __name__ == '__main__':
    unittest.main()
