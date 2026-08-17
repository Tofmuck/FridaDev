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

from observability import dashboard_analytics
from observability.dashboard_analytics_storage import _MODULE_KEYS
from observability.dashboard_observable_module_domains import (
    _finalize_pipeline_metrics,
    _reduce_documents_metrics,
    _reduce_pipeline_metrics,
)
from observability.dashboard_observable_module_serialization import _module_to_public_dict
from observability.dashboard_observable_modules import ObservableModule


class DashboardObservableModulesLot3Tests(unittest.TestCase):
    def _fake_module(self) -> ObservableModule:
        def reduce_fake_metrics(metrics: dict[str, Any], fact: dict[str, Any]) -> None:
            fake = fact.get('fake_documents')
            if not isinstance(fake, dict):
                return
            metrics['fake_used_count'] = int(metrics.get('fake_used_count') or 0) + int(fake.get('used_count') or 0)
            metrics['fake_requested_turns'] = int(metrics.get('fake_requested_turns') or 0) + (1 if fake.get('requested') else 0)

        def render_fake_summary(fact: dict[str, Any]) -> str:
            fake = fact.get('fake_documents')
            used_count = int(fake.get('used_count') or 0) if isinstance(fake, dict) else 0
            return f"Les documents factices ont servi {used_count} element(s) compact(s)."

        def resolve_fake_reason(fact: dict[str, Any]) -> str | None:
            fake = fact.get('fake_documents')
            if isinstance(fake, dict) and int(fake.get('used_count') or 0) == 0:
                return 'fake_missing'
            return None

        return ObservableModule(
            module_key='fake_documents',
            label_fr='Documents factices',
            description_fr='Module de test pour prouver l extension du catalogue.',
            calculation_version='fake_documents_v1',
            global_metrics=(('fake_used_count', 'Documents factices utilises'),),
            conversation_summary=(('fake_turns', 'Tours avec documents factices'),),
            turn_summary=(('fake_present', 'Document factice present'),),
            human_detail=(('fake_flow', 'Explique le flux documentaire factice.'),),
            states=('success', 'degraded', 'error', 'skipped', 'not_applicable'),
            content_free_rules=(
                'Aucun contenu brut par defaut.',
                'Le contenu factice complet reste derriere gate.',
            ),
            sources=('fixture test content-free',),
            limits=('Ne porte aucun contenu documentaire brut.',),
            degradation_reasons=(
                ('fake_missing', 'Le document factice attendu n est pas disponible.'),
            ),
            gated_content=('Document factice complet',),
            future=True,
            bucket_metrics_reducer=reduce_fake_metrics,
            turn_summary_renderer=render_fake_summary,
            turn_degradation_reason_resolver=resolve_fake_reason,
        )

    def _turn_fact(self) -> dict[str, Any]:
        return {
            'kind': 'dashboard_turn_fact',
            'schema_version': '1',
            'calculation_version': 'dashboard_analytics_v1',
            'conversation_id': 'conv-modules',
            'turn_id': 'turn-modules',
            'first_ts': '2026-05-15T10:00:00+00:00',
            'latest_ts': '2026-05-15T10:00:20+00:00',
            'classification': 'complete',
            'score': 100,
            'source_event_ids': ['evt-1', 'evt-2', 'evt-3'],
            'source_event_count': 3,
            'persistence': {
                'status': 'ok',
                'assistant_final_present': True,
                'assistant_final_saved': True,
                'assistant_interrupted': False,
            },
            'providers': {
                'main': {
                    'present': True,
                    'status': 'ok',
                    'duration_ms': 120,
                    'response_chars': 42,
                },
                'secondary': {},
            },
            'rag': {
                'source_kind': 'memory_chain_snapshot',
                'retrieved': 4,
                'basket': 3,
                'kept': 2,
                'rejected': 1,
                'injected': 2,
                'context_hints': 1,
            },
            'identity': {'status': 'ok', 'block_present': True, 'chars': 12},
            'hermeneutic': {'status': 'ok', 'block_present': True, 'fallback': False},
            'web': {
                'status': 'ok',
                'requested': True,
                'success': True,
                'skipped': False,
                'error': False,
                'injected': True,
                'results_count': 2,
                'injected_chars': 77,
            },
            'documents': {
                'source_kind': 'active_conversation_documents',
                'active_count': 2,
                'injected_count': 1,
                'not_injected_count': 1,
                'too_large_count': 1,
                'ocr_applied_count': 1,
                'ocr_duration_ms_total': 1200,
                'ocr_engine_counts': {'stirling-pdf': 1},
                'reason_code_counts': {'document_too_large_for_turn': 1},
                'future_biblio_included': False,
                'raw_content_included': False,
            },
            'biblio': {
                'source_kind': 'biblio_native_catalogue',
                'event_present': True,
                'enabled': True,
                'used': True,
                'status': 'ok',
                'query_kind': 'document_locator',
                'document_status': 'resolved',
                'document_reason_code': 'document_and_locator_resolved',
                'document_candidate_count': 1,
                'document_candidate_ids': ['doc-1234'],
                'doc_id_shorts': ['doc-1234'],
                'locator_kind': 'stephanus',
                'locator_candidate_count': 1,
                'requested_locator_kind': 'stephanus',
                'passage_status': 'extracted',
                'passage_reason_code': 'passage_extracted',
                'passage_chars': 42,
                'passage_hash': 'abcdef123456',
                'passage_count': 1,
                'skipped_count': 0,
                'lane_present': True,
                'lane_chars': 300,
                'hashes': ['abcdef123456'],
                'positions': [{'page_no': 12, 'para_no': 3, 'paragraph_id': 99}],
                'search_candidate_count': 3,
                'context_fetch_count': 2,
                'selected_passage_count': 1,
                'passage_result_count': 1,
                'ambiguous': False,
                'endpoint_count': 3,
                'endpoint_kinds': ['search', 'context'],
                'ranking_available': True,
                'selection_reason_codes': ['dominant_context'],
                'confidence_available': False,
                'confidence_reason_code': 'biblio_confidence_not_implemented',
                'reason_code_counts': {
                    'document_and_locator_resolved': 1,
                    'passage_extracted': 1,
                },
                'raw_content_included': False,
            },
            'node_state': {
                'read_present': True,
                'read_valid': True,
                'write_attempted': True,
                'write_succeeded': True,
                'write_changed': False,
                'fail_open': False,
            },
            'errors': {
                'error_count': 0,
                'skipped_count': 0,
                'fallback_count': 0,
                'reason_code_counts': {},
            },
            'fake_documents': {'requested': True, 'used_count': 2},
            'flags': {'events_truncated': False},
            'redaction': {
                'raw_content_stored': False,
                'raw_event_payloads_included': False,
            },
        }

    def test_initial_and_future_modules_declare_required_contract(self) -> None:
        initial_keys = set(dashboard_analytics.observable_module_keys())
        self.assertEqual(
            {
                'pipeline',
                'persistence',
                'memory',
                'web',
                'documents',
                'biblio',
                'providers',
                'identity',
                'hermeneutic',
                'node_state',
                'errors',
            },
            initial_keys,
        )
        future_keys = set(dashboard_analytics.observable_module_keys(include_future=True))
        self.assertIn('documents', future_keys)
        self.assertIn('images', future_keys)

        for module in dashboard_analytics.observable_modules(include_future=True):
            self.assertTrue(module.module_key)
            self.assertTrue(module.label_fr)
            self.assertTrue(module.global_metrics)
            self.assertTrue(module.conversation_summary)
            self.assertTrue(module.turn_summary)
            self.assertTrue(module.human_detail)
            self.assertTrue(module.states)
            self.assertTrue(module.content_free_rules)
            self.assertTrue(module.sources)
            self.assertTrue(module.limits)
            self.assertTrue(module.calculation_version)

    def test_registry_order_is_the_single_order_used_by_catalog_and_storage(self) -> None:
        expected = (
            'pipeline',
            'persistence',
            'memory',
            'web',
            'documents',
            'biblio',
            'providers',
            'identity',
            'hermeneutic',
            'node_state',
            'errors',
        )
        catalog = dashboard_analytics.build_dashboard_module_catalog()

        self.assertEqual(expected, dashboard_analytics.observable_module_keys())
        self.assertEqual(expected, _MODULE_KEYS)
        self.assertEqual(list(expected), catalog['module_keys'])
        self.assertEqual(list(expected), [module['module_key'] for module in catalog['modules']])

    def test_domain_reducers_are_directly_testable_and_remain_content_free(self) -> None:
        pipeline_metrics: dict[str, Any] = {}
        _reduce_pipeline_metrics(
            pipeline_metrics,
            {'classification': 'complete', 'score': 91, 'flags': {'events_truncated': True}},
        )
        _finalize_pipeline_metrics(pipeline_metrics)
        self.assertEqual(
            {
                'classification_counts': {'complete': 1},
                'score_total': 91,
                'score_count': 1,
                'events_truncated_turns': 1,
                'score_avg': 91.0,
            },
            pipeline_metrics,
        )

        document_metrics: dict[str, Any] = {}
        _reduce_documents_metrics(
            document_metrics,
            {
                'documents': {
                    'status': 'ok',
                    'active_count': 2,
                    'injected_count': 1,
                    'not_injected_count': 1,
                    'too_large_count': 1,
                    'empty_count': 0,
                    'ocr_applied_count': 1,
                    'ocr_duration_ms_total': 1200,
                    'ocr_engine_counts': {'synthetic-engine': 1},
                    'reason_code_counts': {'synthetic_reason': 1},
                    'raw_content': 'RAW DOCUMENT SENTINEL MUST NOT LEAK',
                },
            },
        )
        self.assertEqual(2, document_metrics['active_documents_total'])
        self.assertEqual(1, document_metrics['injected_documents_total'])
        self.assertEqual({'synthetic-engine': 1}, document_metrics['ocr_engine_counts'])
        self.assertEqual({'synthetic_reason': 1}, document_metrics['reason_code_counts'])
        self.assertNotIn('RAW DOCUMENT SENTINEL MUST NOT LEAK', json.dumps(document_metrics))

    def test_public_module_serialization_keeps_the_bounded_contract(self) -> None:
        serialized = _module_to_public_dict(self._fake_module())

        self.assertEqual(
            [
                'module_key',
                'label_fr',
                'description_fr',
                'calculation_version',
                'global_metrics',
                'conversation_summary',
                'turn_summary',
                'human_detail',
                'states',
                'content_free_rules',
                'sources',
                'limits',
                'degradation_reasons',
                'gated_content',
                'bucket_metrics',
                'turn_summary_renderer_declared',
                'turn_degradation_reason_resolver_declared',
                'future',
            ],
            list(serialized),
        )
        self.assertEqual('fake_documents', serialized['module_key'])
        self.assertEqual({'fake_used_count': 'Documents factices utilises'}, serialized['global_metrics'])
        self.assertEqual(
            {'fake_missing': 'Le document factice attendu n est pas disponible.'},
            serialized['degradation_reasons'],
        )
        self.assertEqual(
            {'reducer_declared': True, 'finalizer_declared': False},
            serialized['bucket_metrics'],
        )
        self.assertTrue(serialized['turn_summary_renderer_declared'])
        self.assertTrue(serialized['turn_degradation_reason_resolver_declared'])
        self.assertTrue(serialized['future'])
        self.assertNotIn('bucket_metrics_reducer', serialized)

    def test_degradation_explanations_are_human_and_content_free(self) -> None:
        self.assertEqual(
            dashboard_analytics.explain_module_degradation(
                'memory',
                reason_code='memory_chain_snapshot_missing',
            ),
            'La chaine memoire detaillee n est pas disponible pour ce tour.',
        )
        fallback = dashboard_analytics.explain_module_degradation(
            'providers',
            reason_code='unknown_backend_reason',
        )
        self.assertIn('Modeles consultes', fallback)
        self.assertNotIn('unknown_backend_reason', fallback)
        self.assertNotIn('provider_caller', fallback)

    def test_fake_module_owns_specialized_metrics_without_projection_change(self) -> None:
        fake = self._fake_module()
        catalog = dashboard_analytics.build_dashboard_module_catalog(extra_modules=(fake,))
        self.assertIn('fake_documents', catalog['module_keys'])

        buckets = dashboard_analytics.build_dashboard_metric_buckets(
            [self._turn_fact()],
            now=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
            extra_modules=(fake,),
        )
        fake_buckets = [
            bucket for bucket in buckets
            if bucket.get('module_key') == 'fake_documents'
            and bucket.get('granularity') == 'hour'
        ]
        self.assertEqual(len(fake_buckets), 1)
        self.assertEqual(fake_buckets[0]['turn_count'], 1)
        self.assertEqual(fake_buckets[0]['event_count'], 3)
        self.assertEqual(fake_buckets[0]['metrics']['fake_used_count'], 2)
        self.assertEqual(fake_buckets[0]['metrics']['fake_requested_turns'], 1)

    def test_fake_module_owns_specialized_human_summary(self) -> None:
        fake = self._fake_module()
        summary = dashboard_analytics.summarize_module_turn(
            'fake_documents',
            self._turn_fact(),
            extra_modules=(fake,),
        )

        self.assertEqual(summary, 'Les documents factices ont servi 2 element(s) compact(s).')
        self.assertNotIn('fake_documents', summary)
        self.assertNotIn('complete', summary)
        self.assertNotIn('ok', summary)

    def test_fake_module_owns_specialized_degradation_reason(self) -> None:
        fake = self._fake_module()
        reason = dashboard_analytics.resolve_module_turn_degradation_reason(
            'fake_documents',
            {'fake_documents': {'used_count': 0}},
            extra_modules=(fake,),
        )

        self.assertEqual(reason, 'fake_missing')

    def test_current_module_metrics_are_not_regressed_by_module_hooks(self) -> None:
        buckets = dashboard_analytics.build_dashboard_metric_buckets(
            [self._turn_fact()],
            now=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        by_key = {
            bucket['module_key']: bucket
            for bucket in buckets
            if bucket.get('granularity') == 'hour'
        }

        self.assertEqual(by_key['pipeline']['metrics']['score_avg'], 100.0)
        self.assertEqual(by_key['pipeline']['metrics']['classification_counts']['complete'], 1)
        self.assertEqual(by_key['memory']['metrics']['retrieved_total'], 4)
        self.assertEqual(by_key['memory']['metrics']['injected_total'], 2)
        self.assertEqual(by_key['web']['metrics']['requested_turns'], 1)
        self.assertEqual(by_key['web']['metrics']['injected_turns'], 1)
        self.assertEqual(by_key['documents']['metrics']['active_turns'], 1)
        self.assertEqual(by_key['documents']['metrics']['active_documents_total'], 2)
        self.assertEqual(by_key['documents']['metrics']['injected_documents_total'], 1)
        self.assertEqual(by_key['documents']['metrics']['not_injected_documents_total'], 1)
        self.assertEqual(by_key['documents']['metrics']['too_large_documents_total'], 1)
        self.assertEqual(by_key['documents']['metrics']['ocr_applied_documents_total'], 1)
        self.assertEqual(by_key['documents']['metrics']['ocr_duration_ms_total'], 1200)
        self.assertEqual(by_key['documents']['metrics']['ocr_engine_counts']['stirling-pdf'], 1)
        self.assertEqual(by_key['biblio']['metrics']['used_turns'], 1)
        self.assertEqual(by_key['biblio']['metrics']['passages_total'], 1)
        self.assertEqual(by_key['biblio']['metrics']['lane_chars_total'], 300)
        self.assertEqual(by_key['biblio']['metrics']['document_status_counts']['resolved'], 1)
        self.assertEqual(by_key['biblio']['metrics']['search_candidates_total'], 3)
        self.assertEqual(by_key['biblio']['metrics']['context_fetch_total'], 2)
        self.assertEqual(by_key['biblio']['metrics']['selected_passages_total'], 1)
        self.assertEqual(by_key['biblio']['metrics']['ranking_available_turns'], 1)
        self.assertEqual(by_key['biblio']['metrics']['endpoint_kind_counts']['search'], 1)
        self.assertEqual(by_key['biblio']['metrics']['selection_reason_counts']['dominant_context'], 1)
        self.assertEqual(by_key['providers']['metrics']['main_call_present_count'], 1)
        self.assertEqual(by_key['providers']['metrics']['main_duration_ms_p50'], 120)
        self.assertEqual(by_key['identity']['metrics']['block_present_turns'], 1)
        self.assertEqual(by_key['hermeneutic']['metrics']['block_present_turns'], 1)
        self.assertEqual(by_key['node_state']['metrics']['write_succeeded_count'], 1)
        self.assertEqual(by_key['errors']['metrics']['error_count'], 0)

    def test_documents_module_has_specialized_summary_and_reason(self) -> None:
        summary = dashboard_analytics.summarize_module_turn(
            'documents',
            self._turn_fact(),
        )
        reason = dashboard_analytics.resolve_module_turn_degradation_reason(
            'documents',
            self._turn_fact(),
        )

        self.assertEqual(
            summary,
            '2 document(s) actif(s) etaient presents; 1 etaient trop gros pour ce tour. 1 etaient OCRise(s).',
        )
        self.assertEqual(reason, 'document_too_large_for_turn')
        self.assertNotIn('RAW', summary)
        self.assertNotIn('library_document', summary)

    def test_documents_module_tells_read_error_without_inventing_document(self) -> None:
        fact = self._turn_fact()
        fact['documents'] = {
            'source_kind': 'active_conversation_documents',
            'status': 'error',
            'read_status': 'error',
            'read_reason_code': 'active_documents_read_error',
            'active_count': 0,
            'injected_count': 0,
            'not_injected_count': 0,
            'reason_code_counts': {'active_documents_read_error': 1},
            'raw_content_included': False,
        }

        summary = dashboard_analytics.summarize_module_turn('documents', fact)
        reason = dashboard_analytics.resolve_module_turn_degradation_reason('documents', fact)

        self.assertIn('lecture des documents actifs', summary)
        self.assertIn('active_documents_read_error', summary)
        self.assertNotIn('Aucun document actif de conversation n est observe', summary)
        self.assertEqual(reason, 'active_documents_read_error')
        self.assertNotIn('RAW', summary)

    def test_documents_module_does_not_promise_out_of_turn_reasons_as_turn_degradations(self) -> None:
        catalog = dashboard_analytics.build_dashboard_module_catalog()
        document_module = next(
            module for module in catalog['modules']
            if module['module_key'] == 'documents'
        )

        self.assertIn('active_documents_read_error', document_module['degradation_reasons'])
        self.assertIn('active_documents_reader_unavailable', document_module['degradation_reasons'])
        self.assertIn('document_too_large_for_turn', document_module['degradation_reasons'])
        self.assertIn('document_empty_text', document_module['degradation_reasons'])
        self.assertNotIn('document_parse_error', document_module['degradation_reasons'])
        self.assertNotIn('manual_remove', document_module['degradation_reasons'])

    def test_biblio_module_has_specialized_summary_and_reason(self) -> None:
        summary = dashboard_analytics.summarize_module_turn(
            'biblio',
            self._turn_fact(),
        )
        reason = dashboard_analytics.resolve_module_turn_degradation_reason(
            'biblio',
            self._turn_fact(),
        )

        self.assertEqual(
            summary,
            'La Biblio a ete consultee; 1 passage(s) de bibliotheque sont observes en lane compacte.',
        )
        self.assertEqual(reason, 'document_and_locator_resolved')
        self.assertNotIn('abcdef123456', summary)
        self.assertNotIn('doc-1234', summary)
        self.assertNotIn('RAW', summary)

    def test_biblio_module_tells_ambiguity_without_document_content(self) -> None:
        fact = self._turn_fact()
        fact['biblio'] = {
            'source_kind': 'biblio_native_catalogue',
            'event_present': True,
            'enabled': True,
            'used': True,
            'status': 'ambiguous',
            'document_status': 'ambiguous',
            'document_reason_code': 'ambiguous_document',
            'passage_count': 3,
            'search_candidate_count': 8,
            'context_fetch_count': 3,
            'selected_passage_count': 0,
            'ambiguous': True,
            'selection_reason_codes': ['selection_gap_too_small'],
            'reason_code_counts': {'biblio_context_candidates_ambiguous': 1, 'selection_gap_too_small': 1},
            'raw_content_included': False,
        }

        summary = dashboard_analytics.summarize_module_turn('biblio', fact)
        reason = dashboard_analytics.resolve_module_turn_degradation_reason('biblio', fact)

        self.assertIn('resolution est ambigue', summary)
        self.assertIn('3 passage(s) candidat(s)', summary)
        self.assertIn('3 contexte(s)', summary)
        self.assertIn('biblio_context_candidates_ambiguous', summary)
        self.assertEqual(reason, 'biblio_context_candidates_ambiguous')
        self.assertNotIn('RAW', summary)

    def test_catalog_public_labels_do_not_include_runtime_content(self) -> None:
        raw_values = (
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
            'RAW DOCUMENT TEXT MUST NOT LEAK',
        )
        catalog = dashboard_analytics.build_dashboard_module_catalog(
            include_future=True,
            extra_modules=(self._fake_module(),),
        )
        encoded = json.dumps(catalog, ensure_ascii=False, sort_keys=True)
        for raw in raw_values:
            self.assertNotIn(raw, encoded)
        self.assertFalse(catalog['redaction']['raw_content_stored'])
        self.assertFalse(catalog['redaction']['raw_labels_from_runtime_content'])

    def test_duplicate_module_key_is_rejected(self) -> None:
        duplicate = ObservableModule(
            module_key='memory',
            label_fr='Memoire duplicate',
            description_fr='Duplicate interdit.',
            calculation_version='duplicate_v1',
            global_metrics=(('x', 'X'),),
            conversation_summary=(('x', 'X'),),
            turn_summary=(('x', 'X'),),
            human_detail=(('x', 'X'),),
            states=('success',),
            content_free_rules=('Aucun contenu brut par defaut.',),
            sources=('fixture',),
            limits=('fixture',),
        )
        with self.assertRaises(ValueError):
            dashboard_analytics.observable_module_keys(extra_modules=(duplicate,))


if __name__ == '__main__':
    unittest.main()
