from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conversations_prompt_window
from core.hermeneutic_node.inputs import memory_arbitration_input, memory_retrieved_input
from memory import memory_pre_arbiter_basket
from observability import prompt_injection_summary


def _trace_candidate(
    *,
    conversation_id: str,
    role: str,
    content: str,
    timestamp: str,
    score: float,
    summary_id: str | None = None,
    parent_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        'conversation_id': conversation_id,
        'role': role,
        'content': content,
        'timestamp': timestamp,
        'summary_id': summary_id,
        'score': score,
        'parent_summary': parent_summary,
    }


def _summary_candidate(
    *,
    conversation_id: str,
    summary_id: str,
    start_ts: str,
    end_ts: str,
    content: str,
    score: float,
) -> dict[str, object]:
    return {
        'conversation_id': conversation_id,
        'role': 'summary',
        'source_kind': 'summary',
        'source_lane': 'summaries',
        'content': content,
        'timestamp': end_ts,
        'timestamp_iso': end_ts,
        'start_ts': start_ts,
        'end_ts': end_ts,
        'summary_id': summary_id,
        'score': score,
        'retrieval_score': score,
        'semantic_score': score,
    }


def _internal_candidate(candidate: dict[str, object], *, semantic_score: float) -> dict[str, object]:
    return {
        'conversation_id': candidate['conversation_id'],
        'role': candidate['role'],
        'content': candidate['content'],
        'timestamp': candidate.get('timestamp') or candidate.get('timestamp_iso'),
        'timestamp_iso': candidate.get('timestamp_iso') or candidate.get('timestamp'),
        'start_ts': candidate.get('start_ts'),
        'end_ts': candidate.get('end_ts'),
        'summary_id': candidate['summary_id'],
        'score': candidate['score'],
        'retrieval_score': candidate.get('retrieval_score', candidate['score']),
        'semantic_score': semantic_score,
        'source_kind': candidate.get('source_kind'),
        'source_lane': candidate.get('source_lane'),
    }


def _memory_retrieved(candidates: list[dict[str, object]]) -> dict[str, object]:
    return memory_retrieved_input.build_memory_retrieved_input(
        retrieval_query='probe summary lane',
        top_k_requested=5,
        traces=candidates,
    )


class MemorySummariesPhase8CTests(unittest.TestCase):
    def test_summary_candidates_are_normalized_with_stable_id_and_end_ts_anchor(self) -> None:
        summary = _summary_candidate(
            conversation_id='conv-summary',
            summary_id='sum-001',
            start_ts='2026-04-01T10:00:00Z',
            end_ts='2026-04-01T10:05:00Z',
            content='Resume de la fenetre utilisateur',
            score=0.93,
        )
        memory_retrieved = _memory_retrieved([summary])

        self.assertEqual(len(memory_retrieved['traces']), 1)
        canonical = memory_retrieved['traces'][0]
        self.assertEqual(canonical['candidate_id'], 'summary:sum-001')
        self.assertEqual(canonical['source_kind'], 'summary')
        self.assertEqual(canonical['source_lane'], 'summaries')
        self.assertEqual(canonical['timestamp_iso'], '2026-04-01T10:05:00Z')
        self.assertEqual(canonical['start_ts'], '2026-04-01T10:00:00Z')
        self.assertEqual(canonical['end_ts'], '2026-04-01T10:05:00Z')
        self.assertEqual(canonical['summary_id'], 'sum-001')
        self.assertIsNone(canonical['parent_summary'])

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=[summary],
            internal_traces=[_internal_candidate(summary, semantic_score=0.93)],
        )

        self.assertEqual(len(basket.candidates), 1)
        candidate = basket.candidates[0]
        self.assertEqual(candidate['candidate_id'], 'summary:sum-001')
        self.assertEqual(candidate['source_candidate_ids'], ['summary:sum-001'])
        self.assertEqual(candidate['source_kind'], 'summary')
        self.assertEqual(candidate['source_lane'], 'summaries')
        self.assertEqual(candidate['timestamp_iso'], '2026-04-01T10:05:00Z')
        self.assertEqual(candidate['start_ts'], '2026-04-01T10:00:00Z')
        self.assertEqual(candidate['end_ts'], '2026-04-01T10:05:00Z')
        self.assertEqual(candidate['summary_id'], 'sum-001')
        self.assertFalse(candidate['parent_summary_present'])

    def test_summary_can_absorb_multiple_traces_without_double_injection(self) -> None:
        parent_summary = {
            'id': 'sum-prefs',
            'conversation_id': 'conv-prefs',
            'start_ts': '2026-04-02T09:00:00Z',
            'end_ts': '2026-04-02T09:10:00Z',
            'content': 'Preferences utilisateur durables',
        }
        summary = _summary_candidate(
            conversation_id='conv-prefs',
            summary_id='sum-prefs',
            start_ts='2026-04-02T09:00:00Z',
            end_ts='2026-04-02T09:10:00Z',
            content='Preferences durables: reponses courtes, ton direct et calme.',
            score=0.91,
        )
        trace_a = _trace_candidate(
            conversation_id='conv-prefs',
            role='user',
            content='Tu preferes les reponses courtes.',
            timestamp='2026-04-02T09:02:00Z',
            score=0.82,
            summary_id='sum-prefs',
            parent_summary=parent_summary,
        )
        trace_b = _trace_candidate(
            conversation_id='conv-prefs',
            role='user',
            content='Tu veux un ton direct et calme.',
            timestamp='2026-04-02T09:05:00Z',
            score=0.81,
            summary_id='sum-prefs',
            parent_summary=parent_summary,
        )
        retrieved = [summary, trace_a, trace_b]
        memory_retrieved = _memory_retrieved(retrieved)
        internal = [
            _internal_candidate(summary, semantic_score=0.91),
            _internal_candidate(trace_a, semantic_score=0.82),
            _internal_candidate(trace_b, semantic_score=0.81),
        ]

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=internal,
        )

        self.assertEqual(len(basket.candidates), 1)
        representative = basket.candidates[0]
        self.assertEqual(representative['candidate_id'], 'summary:sum-prefs')
        self.assertEqual(representative['source_kind'], 'summary')
        self.assertEqual(representative['dedup_reason_code'], 'trace_summary_collision')
        self.assertEqual(
            set(representative['source_candidate_ids']),
            {
                'summary:sum-prefs',
                memory_retrieved['traces'][1]['candidate_id'],
                memory_retrieved['traces'][2]['candidate_id'],
            },
        )
        self.assertFalse(representative['parent_summary_present'])

        selected = memory_pre_arbiter_basket.select_prompt_candidates(basket)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['candidate_id'], 'summary:sum-prefs')
        self.assertIsNone(selected[0]['parent_summary'])

        prompt_messages = [
            {
                'role': 'system',
                'content': conversations_prompt_window.MEMORY_TRACES_BLOCK_HEADER + '\nResume : Preferences durables...',
            }
        ]
        injection = prompt_injection_summary.build_memory_prompt_injection_summary(
            prompt_messages,
            memory_traces=selected,
        )
        self.assertEqual(injection['injected_candidate_ids'], ['summary:sum-prefs'])
        self.assertEqual(injection['memory_traces_injected_count'], 1)
        self.assertEqual(injection['memory_context_summary_count'], 0)

        decisions = [
            {
                'candidate_id': representative['candidate_id'],
                'keep': True,
                'semantic_relevance': 0.91,
                'contextual_gain': 0.88,
                'redundant_with_recent': False,
                'reason': 'summary_subsumes_multiple_traces',
                'decision_source': 'fallback',
                'model': 'tests',
            }
        ]
        memory_arbitration = memory_arbitration_input.build_memory_arbitration_input(
            memory_retrieved=memory_retrieved,
            raw_candidates_count=len(retrieved),
            decisions=decisions,
            status='available',
            basket_candidates=basket.candidates,
            injected_candidate_ids=[trace['candidate_id'] for trace in selected],
        )
        self.assertEqual(memory_arbitration['injected_candidate_ids'], ['summary:sum-prefs'])
        self.assertEqual(memory_arbitration['basket_candidates'][0]['candidate_id'], 'summary:sum-prefs')
        self.assertEqual(memory_arbitration['basket_candidates'][0]['summary_id'], 'sum-prefs')
        self.assertEqual(memory_arbitration['basket_candidates'][0]['end_ts'], '2026-04-02T09:10:00Z')
        self.assertEqual(memory_arbitration['decisions'][0]['candidate_id'], 'summary:sum-prefs')

    def test_trace_remains_preferred_over_single_colliding_summary(self) -> None:
        parent_summary = {
            'id': 'sum-identity',
            'conversation_id': 'conv-id',
            'start_ts': '2026-04-03T18:00:00Z',
            'end_ts': '2026-04-03T18:03:00Z',
            'content': 'Echange identitaire',
        }
        trace = _trace_candidate(
            conversation_id='conv-id',
            role='user',
            content='Je suis Christophe Muck.',
            timestamp='2026-04-03T18:02:00Z',
            score=0.87,
            summary_id='sum-identity',
            parent_summary=parent_summary,
        )
        summary = _summary_candidate(
            conversation_id='conv-id',
            summary_id='sum-identity',
            start_ts='2026-04-03T18:00:00Z',
            end_ts='2026-04-03T18:03:00Z',
            content='Resume large de la conversation identitaire.',
            score=0.95,
        )
        retrieved = [summary, trace]
        memory_retrieved = _memory_retrieved(retrieved)
        internal = [
            _internal_candidate(summary, semantic_score=0.95),
            _internal_candidate(trace, semantic_score=0.87),
        ]

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=internal,
        )

        self.assertEqual(len(basket.candidates), 1)
        representative = basket.candidates[0]
        self.assertEqual(representative['source_kind'], 'trace')
        self.assertEqual(representative['candidate_id'], memory_retrieved['traces'][1]['candidate_id'])
        self.assertEqual(
            set(representative['source_candidate_ids']),
            {'summary:sum-identity', memory_retrieved['traces'][1]['candidate_id']},
        )
        self.assertTrue(representative['parent_summary_present'])
        self.assertEqual(basket.prompt_candidates[0]['parent_summary']['id'], 'sum-identity')

    def test_make_memory_message_renders_summary_role_explicitly(self) -> None:
        message = conversations_prompt_window.make_memory_message(
            [
                {
                    'role': 'summary',
                    'content': 'Resume de preferences durables',
                    'timestamp': '2026-04-04T10:00:00Z',
                }
            ],
            '2026-04-05T10:00:00Z',
            delta_t_label_func=lambda *_args: '',
        )

        self.assertIsNotNone(message)
        self.assertIn('Resume : Resume de preferences durables', message['content'])


if __name__ == '__main__':
    unittest.main()
