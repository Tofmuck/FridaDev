from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

from observability.turn_pipeline_biblio_summary import build_biblio_summary
from observability.turn_pipeline_documents_summary import build_documents_summary
from observability.turn_pipeline_memory_summary import build_memory_rag_summary
from observability.turn_pipeline_read_model import build_turn_pipeline_item
from observability.turn_pipeline_web_summary import build_web_summary


class TurnPipelineDomainSummariesTest(unittest.TestCase):
    RAW_SENTINELS = (
        'RAW MEMORY CONTENT MUST NOT LEAK',
        'RAW WEB QUERY MUST NOT LEAK',
        'RAW WEB CONTEXT MUST NOT LEAK',
        'RAW DOCUMENT CONTENT MUST NOT LEAK',
        'RAW BIBLIO CONTENT MUST NOT LEAK',
    )

    @staticmethod
    def _event(
        stage: str,
        *,
        status: str = 'ok',
        payload: dict[str, Any] | None = None,
        suffix: str = '1',
    ) -> dict[str, Any]:
        return {
            'event_id': f'turn-domain:{suffix}:{stage}',
            'conversation_id': 'conv-domain',
            'turn_id': 'turn-domain',
            'ts': f'2026-08-17T08:00:0{suffix}+00:00',
            'stage': stage,
            'status': status,
            'payload_json': dict(payload or {}),
        }

    def _events(self) -> list[dict[str, Any]]:
        return [
            self._event(
                'turn_start',
                payload={'web_search_enabled': True},
                suffix='1',
            ),
            self._event(
                'memory_chain_snapshot',
                payload={
                    'retrieval': {'status': 'ok', 'retrieved_count': 3},
                    'basket': {'basket_candidates_count': 2, 'deduped_retrieved_count': 1},
                    'arbiter': {'kept_count': 1, 'rejected_count': 1},
                    'injection': {'injected_candidate_count': 1, 'context_hints_count': 0},
                    'retrieved_candidates': [{'content': self.RAW_SENTINELS[0]}],
                },
                suffix='2',
            ),
            self._event(
                'prompt_prepared',
                payload={
                    'messages_count': 5,
                    'memory_prompt_injection': {
                        'injected': True,
                        'trace_memory_injected_count': 1,
                        'summary_context_injected': False,
                    },
                    'memory_retrieval': {'status': 'ok', 'top_k_returned': 3},
                },
                suffix='3',
            ),
            self._event(
                'web_search',
                payload={
                    'enabled': True,
                    'reason_code': 'web_search_completed',
                    'query': self.RAW_SENTINELS[1],
                    'query_present': True,
                    'query_chars': len(self.RAW_SENTINELS[1]),
                    'results_count': 2,
                    'context_injected': True,
                    'injected_chars': 44,
                    'context_block': self.RAW_SENTINELS[2],
                },
                suffix='4',
            ),
            self._event(
                'active_documents',
                payload={
                    'source_kind': 'active_conversation_documents',
                    'active_count': 1,
                    'injected_count': 1,
                    'not_injected_count': 0,
                    'documents': [
                        {
                            'document_id': 'synthetic-doc',
                            'document_ref': 'synthetic-ref',
                            'filename': 'synthetic.txt',
                            'media_type': 'text/plain',
                            'byte_size': 24,
                            'text_chars': 19,
                            'active': True,
                            'injected': True,
                            'raw_content_included': False,
                            'text_content': self.RAW_SENTINELS[3],
                        }
                    ],
                    'raw_content_included': False,
                },
                suffix='5',
            ),
            self._event(
                'biblio',
                payload={
                    'source_kind': 'biblio_native_catalogue',
                    'enabled': True,
                    'used': True,
                    'query_kind': 'document_locator',
                    'status': self.RAW_SENTINELS[4],
                    'lane': {'present': True, 'passage_count': 1, 'chars': 30},
                    'counts': {'passage_count': 1, 'lane_chars': 30},
                    'passage': self.RAW_SENTINELS[4],
                    'redaction': {'raw_content_included': False},
                },
                suffix='6',
            ),
            self._event(
                'agenda',
                status='disabled',
                payload={
                    'status_schema_version': 'agentic_v1',
                    'reason_code': 'agenda_toggle_off',
                },
                suffix='7',
            ),
        ]

    def _assert_content_free(self, value: Any) -> None:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
        for sentinel in self.RAW_SENTINELS:
            self.assertNotIn(sentinel, serialized)

    def test_memory_rag_builder_preserves_snapshot_contract_content_free(self) -> None:
        events = self._events()
        prompt_payload = next(
            event['payload_json'] for event in events if event['stage'] == 'prompt_prepared'
        )

        summary = build_memory_rag_summary(events, prompt_payload)

        self.assertEqual(summary['source_kind'], 'memory_chain_snapshot')
        self.assertEqual(summary['retrieved'], 3)
        self.assertEqual(summary['basket'], 2)
        self.assertEqual(summary['kept'], 1)
        self.assertEqual(summary['injected'], 1)
        self.assertEqual(summary['conversation_summary_status'], 'unknown')
        self._assert_content_free(summary)

    def test_web_builder_preserves_projection_content_free(self) -> None:
        summary = build_web_summary(self._events())

        self.assertTrue(summary['requested'])
        self.assertTrue(summary['query_present'])
        self.assertEqual(summary['query_chars'], len(self.RAW_SENTINELS[1]))
        self.assertEqual(summary['results_count'], 2)
        self.assertTrue(summary['injected'])
        self._assert_content_free(summary)

    def test_documents_builder_preserves_projection_content_free(self) -> None:
        summary = build_documents_summary(self._events())

        self.assertEqual(summary['source_kind'], 'active_conversation_documents')
        self.assertEqual(summary['active_count'], 1)
        self.assertEqual(summary['injected_count'], 1)
        self.assertEqual(summary['documents'][0]['document_id'], 'synthetic-doc')
        self.assertEqual(summary['documents'][0]['filename'], 'synthetic.txt')
        self.assertFalse(summary['raw_content_included'])
        self._assert_content_free(summary)

    def test_biblio_builder_preserves_projection_content_free(self) -> None:
        summary = build_biblio_summary(self._events())

        self.assertTrue(summary['event_present'])
        self.assertTrue(summary['enabled'])
        self.assertTrue(summary['used'])
        self.assertTrue(summary['status'].startswith('sha256:'))
        self.assertEqual(summary['passage_count'], 1)
        self.assertEqual(summary['lane_chars'], 30)
        self.assertFalse(summary['raw_content_included'])
        self._assert_content_free(summary)

    def test_facade_delegates_real_domains_without_inventing_agenda_summary(self) -> None:
        with (
            patch(
                'observability.turn_pipeline_read_model.build_memory_rag_summary',
                return_value={'domain': 'memory'},
            ) as memory_builder,
            patch(
                'observability.turn_pipeline_read_model.build_web_summary',
                return_value={'domain': 'web'},
            ) as web_builder,
            patch(
                'observability.turn_pipeline_read_model.build_documents_summary',
                return_value={'domain': 'documents'},
            ) as documents_builder,
            patch(
                'observability.turn_pipeline_read_model.build_biblio_summary',
                return_value={'domain': 'biblio'},
            ) as biblio_builder,
        ):
            item = build_turn_pipeline_item(self._events())

        self.assertEqual(item['rag'], {'domain': 'memory'})
        self.assertEqual(item['web'], {'domain': 'web'})
        self.assertEqual(item['documents'], {'domain': 'documents'})
        self.assertEqual(item['biblio'], {'domain': 'biblio'})
        self.assertNotIn('agenda', item)
        self.assertEqual(item['stage_counts']['agenda'], 1)
        memory_builder.assert_called_once()
        web_builder.assert_called_once()
        documents_builder.assert_called_once()
        biblio_builder.assert_called_once()


if __name__ == '__main__':
    unittest.main()
