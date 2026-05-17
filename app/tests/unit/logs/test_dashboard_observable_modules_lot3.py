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
