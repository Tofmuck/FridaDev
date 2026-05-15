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

    def test_fake_module_extends_catalog_and_buckets_without_projection_change(self) -> None:
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
        self.assertEqual(fake_buckets[0]['metrics'], {})

    def test_catalog_public_labels_do_not_include_runtime_content(self) -> None:
        raw_values = (
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
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
