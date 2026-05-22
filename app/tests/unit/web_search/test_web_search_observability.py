from __future__ import annotations

import sys
import types
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

sys.modules.setdefault('psycopg', types.SimpleNamespace())

from core.hermeneutic_node.inputs import web_input
from observability import hermeneutic_node_logger
from observability import turn_observability_checklist
from observability import turn_pipeline_read_model


def _event(stage: str, *, payload: dict[str, Any] | None = None, status: str = 'ok') -> dict[str, Any]:
    return {
        'event_id': f'evt-{stage}',
        'stage': stage,
        'status': status,
        'ts': '2026-05-22T12:00:00+00:00',
        'payload': dict(payload or {}),
    }


def _phase4_searxng_payload() -> dict[str, Any]:
    return {
        'enabled': True,
        'status': 'ok',
        'activation_mode': 'manual',
        'search_profile': 'documentation_officielle',
        'query_plan_kind': 'bounded_specialized',
        'query_count': 2,
        'deduped_result_count': 5,
        'searxng_profile_params_kind': 'profiled_engine_basket',
        'searxng_profile_params_policy': 'governed_local_only',
        'searxng_categories': ['general'],
        'searxng_engines': ['microsoft learn', 'bing'],
        'searxng_time_range': '',
        'searxng_language': 'fr-FR',
        'searxng_safesearch': '0',
        'searxng_params_reason_codes': [
            'profile_documentation_officielle',
            'source_first_authority_detected',
        ],
        'searxng_hard_parameters': ['engines', 'categories', 'language'],
        'searxng_soft_signal_policy': 'source_first_domains_plus_rerank',
        'profile_policy_kind': 'local_web_profile_policy_v0',
        'profile_policy_mode': 'source_first_strict_when_authority_named',
        'profile_expected_domains': ['learn.microsoft.com'],
        'profile_secondary_domains': ['developer.mozilla.org'],
        'profile_downrank_domains': ['stackoverflow.com'],
        'profile_situated_secondary_domains': [],
        'profile_policy_reason_codes': ['source_first_authority_named_strict'],
        'profile_crawl_top_n_budget': 3,
        'profile_crawl_max_chars_budget': 7000,
        'profile_manual_latency_target_s': 25,
        'profile_source_evidence_policy_kind': 'local_web_profile_source_evidence_v0',
        'profile_expected_source_present': True,
        'profile_expected_material_used': True,
        'profile_secondary_source_present': False,
        'profile_secondary_material_used': False,
        'profile_situated_source_present': False,
        'profile_situated_material_used': False,
        'profile_downrank_source_present': False,
        'profile_downrank_material_used': False,
        'profile_insufficient_evidence': False,
        'profile_insufficient_evidence_reason_codes': [],
        'profile_source_domain_counts': {'expected_seen': 1, 'expected_used': 1},
        'results_count': 5,
        'context_injected': True,
        'read_state': 'page_read',
    }


class WebSearchObservabilityTests(unittest.TestCase):
    def test_phase4_searxng_engine_basket_fields_survive_downstream_observability(self) -> None:
        payload = _phase4_searxng_payload()
        canonical_web = web_input.build_web_input_from_runtime_payload(payload)

        self.assertEqual(
            canonical_web['searxng_profile_params']['searxng_params_reason_codes'],
            ['profile_documentation_officielle', 'source_first_authority_detected'],
        )
        self.assertEqual(
            canonical_web['searxng_profile_params']['searxng_hard_parameters'],
            ['engines', 'categories', 'language'],
        )
        self.assertEqual(
            canonical_web['searxng_profile_params']['searxng_soft_signal_policy'],
            'source_first_domains_plus_rerank',
        )
        self.assertEqual(canonical_web['profile_policy']['profile_expected_domains'], ['learn.microsoft.com'])
        self.assertEqual(canonical_web['profile_policy']['profile_crawl_top_n_budget'], 3)
        self.assertTrue(canonical_web['profile_policy']['profile_expected_material_used'])

        node_payload = hermeneutic_node_logger.build_hermeneutic_node_insertion_payload(
            current_mode='shadow',
            web_input=canonical_web,
        )
        node_web = node_payload['inputs']['web']
        self.assertEqual(
            node_web['searxng_params_reason_codes'],
            ['profile_documentation_officielle', 'source_first_authority_detected'],
        )
        self.assertEqual(node_web['searxng_hard_parameters'], ['engines', 'categories', 'language'])
        self.assertEqual(node_web['searxng_soft_signal_policy'], 'source_first_domains_plus_rerank')
        self.assertEqual(node_web['profile_expected_domains'], ['learn.microsoft.com'])
        self.assertTrue(node_web['profile_expected_material_used'])

        events = [
            _event('turn_start', payload={'web_search_enabled': True}),
            _event('web_search', payload=payload),
        ]
        pipeline_web = turn_pipeline_read_model._web_summary(events)
        self.assertEqual(
            pipeline_web['searxng_params_reason_codes'],
            ['profile_documentation_officielle', 'source_first_authority_detected'],
        )
        self.assertEqual(pipeline_web['searxng_hard_parameters'], ['engines', 'categories', 'language'])
        self.assertEqual(pipeline_web['searxng_soft_signal_policy'], 'source_first_domains_plus_rerank')
        self.assertEqual(pipeline_web['profile_expected_domains'], ['learn.microsoft.com'])
        self.assertTrue(pipeline_web['profile_expected_material_used'])

        checklist = turn_observability_checklist.build_turn_observability_checklist(events)
        checklist_web = next(item for item in checklist['items'] if item['key'] == 'web_search')
        self.assertEqual(
            checklist_web['evidence']['searxng_params_reason_codes'],
            ['profile_documentation_officielle', 'source_first_authority_detected'],
        )
        self.assertEqual(
            checklist_web['evidence']['searxng_hard_parameters'],
            ['engines', 'categories', 'language'],
        )
        self.assertEqual(
            checklist_web['evidence']['searxng_soft_signal_policy'],
            'source_first_domains_plus_rerank',
        )
        self.assertEqual(checklist_web['evidence']['profile_expected_domains'], ['learn.microsoft.com'])
        self.assertTrue(checklist_web['evidence']['profile_expected_material_used'])


if __name__ == '__main__':
    unittest.main()
