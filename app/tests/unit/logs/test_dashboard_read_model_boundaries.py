from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest

from observability import dashboard_read_model
from observability.dashboard_read_model_inspection import build_turn_story
from observability.dashboard_read_model_overview import (
    aggregate_module_metrics,
    build_conversation_summary,
)
from observability.dashboard_read_model_query import (
    build_source_status,
    resolve_dashboard_window,
    turn_fact_from_row,
)


class DashboardReadModelBoundariesTest(unittest.TestCase):
    def test_query_window_boundary_preserves_window_and_coverage_contract(self) -> None:
        now = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)

        window = resolve_dashboard_window({'window': '24h'}, now=now)
        source = build_source_status(
            window,
            {
                'status': 'ok',
                'window_start': '2026-08-16T08:00:00+00:00',
                'window_end': '2026-08-17T09:00:00+00:00',
                'calculation_version': 'dashboard_long_term_v1',
            },
        )

        self.assertEqual(window['start'], '2026-08-16T09:00:00+00:00')
        self.assertEqual(window['end'], '2026-08-17T09:00:00+00:00')
        self.assertEqual(window['granularity'], 'hour')
        self.assertEqual(source['status'], 'ok')
        self.assertEqual(source['coverage']['status'], 'complete')
        self.assertFalse(source['limits']['raw_content_included'])
        self.assertIs(dashboard_read_model.resolve_dashboard_window, resolve_dashboard_window)

    def test_overview_and_conversation_builders_are_independent_and_content_free(self) -> None:
        modules = aggregate_module_metrics(
            [
                {
                    'module_key': 'web',
                    'turn_count': 1,
                    'event_count': 2,
                    'metrics': {'requested_turns': 1, 'latency_p95': 900},
                },
                {
                    'module_key': 'web',
                    'turn_count': 2,
                    'event_count': 3,
                    'metrics': {'requested_turns': 2, 'latency_p95': 950},
                },
            ]
        )
        row = (
            'conv-boundary',
            'Conversation synthetique',
            'persisted_summary',
            datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 17, 8, 1, tzinfo=timezone.utc),
            'turn-boundary',
            'complete',
            {'retrieved': 1, 'injected': 1},
            {'requested': True, 'injected': False},
            {'active_count': 1, 'injected_count': 1, 'not_injected_count': 0},
            {'used': True, 'passage_count': 2},
            {'error_count': 0, 'failed_count': 0, 'fallback_count': 1},
            {
                'status_schema': {
                    'source_kind': 'v1',
                    'schema_counts': {'agentic_v1': 2},
                    'v1_event_count': 2,
                    'legacy_event_count': 0,
                }
            },
        )

        conversation = build_conversation_summary([row])

        self.assertEqual(modules['web']['turn_count'], 3)
        self.assertEqual(modules['web']['event_count'], 5)
        self.assertEqual(modules['web']['metrics'], {'requested_turns': 3})
        self.assertEqual(conversation['conversation_id'], 'conv-boundary')
        self.assertEqual(conversation['memory_used_turns'], 1)
        self.assertEqual(conversation['web_requested_turns'], 1)
        self.assertEqual(conversation['biblio_passages_total'], 2)
        self.assertEqual(conversation['problem_count'], 1)
        self.assertFalse(conversation['redaction']['raw_content_included'])

    def test_query_boundary_projects_turn_fact_without_raw_content(self) -> None:
        row = (
            'conv-boundary',
            'turn-boundary',
            datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 17, 8, 1, tzinfo=timezone.utc),
            'complete',
            100,
            4,
            'event-first',
            'event-last',
            {'assistant_final_saved': True},
            {'main': {'present': True}},
            {'retrieved': 1},
            {'block_present': True},
            {'block_present': False},
            {'requested': False},
            {'active_count': 0},
            {'used': False},
            {'read_present': True},
            {'total_ms': 12},
            {'error_count': 0},
            {'turn_start': 1},
            {'status_schema': {'source_kind': 'v1', 'v1_event_count': 4}},
            {'prompt_manifest_available': True},
            'dashboard_long_term_v1',
            datetime(2026, 8, 17, 8, 2, tzinfo=timezone.utc),
        )

        fact = turn_fact_from_row(row)

        self.assertEqual(fact['turn_id'], 'turn-boundary')
        self.assertEqual(fact['status_schema']['source_kind'], 'v1')
        self.assertEqual(fact['content_availability'], {'prompt_manifest_available': True})
        self.assertEqual(fact['redaction'], {'raw_content_included': False})

    def test_inspection_story_builder_keeps_translated_content_free_contract(self) -> None:
        raw_sentinel = 'RAW OPERATOR CONTENT MUST NOT LEAK'
        story = build_turn_story(
            {
                'conversation_id': 'conv-boundary',
                'turn_id': 'turn-boundary',
                'classification': 'complete',
                'score': 100,
                'source_event_count': 4,
                'persistence': {'assistant_final_saved': True, 'assistant_interrupted': False},
                'providers': {'main': {'present': True, 'status': 'ok'}, 'secondary': {}},
                'rag': {'retrieved': 1, 'basket': 1, 'kept': 1, 'injected': 1},
                'identity': {'block_present': True, 'chars': 12, 'status': 'ok'},
                'hermeneutic': {'block_present': False, 'fallback': False},
                'web': {'requested': False, 'injected': False},
                'documents': {'active_count': 0, 'raw': raw_sentinel},
                'biblio': {'used': False},
                'node_state': {},
                'errors': {},
                'flags': {},
                'content_availability': {'prompt_manifest_available': True},
            }
        )

        self.assertEqual(story['kind'], 'dashboard_turn_story')
        self.assertEqual(
            [section['key'] for section in story['sections']],
            ['received', 'pipeline', 'model_context', 'modules', 'problems', 'massive_data', 'proof_limits'],
        )
        self.assertEqual(story['proof_level'], 'translated_compact_inspection')
        self.assertFalse(story['redaction']['raw_content_included'])
        self.assertNotIn(raw_sentinel, json.dumps(story, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
