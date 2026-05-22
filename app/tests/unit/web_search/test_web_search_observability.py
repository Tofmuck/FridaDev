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


if __name__ == '__main__':
    unittest.main()
