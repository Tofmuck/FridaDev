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

from core.hermeneutic_node.inputs import memory_retrieved_input
from memory import memory_pre_arbiter_basket


def _retrieved_trace(
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


def _internal_trace(trace: dict[str, object], *, semantic_score: float) -> dict[str, object]:
    return {
        'conversation_id': trace['conversation_id'],
        'role': trace['role'],
        'content': trace['content'],
        'timestamp': trace['timestamp'],
        'summary_id': trace['summary_id'],
        'score': trace['score'],
        'retrieval_score': trace['score'],
        'semantic_score': semantic_score,
    }


def _memory_retrieved(traces: list[dict[str, object]]) -> dict[str, object]:
    return memory_retrieved_input.build_memory_retrieved_input(
        retrieval_query='test',
        top_k_requested=12,
        traces=traces,
    )


class MemoryPreArbiterBasketPhase7BTests(unittest.TestCase):
    def test_build_pre_arbiter_basket_dedupes_exact_duplicates_and_preserves_parent_summary_chain(self) -> None:
        retrieved = [
            _retrieved_trace(
                conversation_id='conv-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.94,
                summary_id='sum-user',
                parent_summary={
                    'id': 'sum-user',
                    'conversation_id': 'conv-a',
                    'start_ts': '2026-04-10T08:00:00Z',
                    'end_ts': '2026-04-10T09:00:00Z',
                    'content': 'Identite utilisateur',
                },
            ),
            _retrieved_trace(
                conversation_id='conv-b',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T08:00:00Z',
                score=0.88,
            ),
            _retrieved_trace(
                conversation_id='conv-c',
                role='assistant',
                content='Nous travaillons sur FridaDev',
                timestamp='2026-04-10T09:30:00Z',
                score=0.73,
            ),
        ]
        internal = [
            _internal_trace(retrieved[0], semantic_score=0.82),
            _internal_trace(retrieved[1], semantic_score=0.79),
            _internal_trace(retrieved[2], semantic_score=0.61),
        ]
        memory_retrieved = _memory_retrieved(retrieved)

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=internal,
        )

        self.assertEqual(len(basket.candidates), 2)
        exact_candidate = basket.candidates[0]
        prompt_candidate = basket.prompt_candidates[0]
        source_ids = [trace['candidate_id'] for trace in memory_retrieved['traces'][:2]]

        self.assertEqual(exact_candidate['candidate_id'], memory_retrieved['traces'][0]['candidate_id'])
        self.assertEqual(exact_candidate['source_candidate_ids'], source_ids)
        self.assertEqual(exact_candidate['dedup_reason_code'], 'exact_duplicate')
        self.assertEqual(exact_candidate['timestamp_iso'], '2026-04-10T09:00:00Z')
        self.assertEqual(exact_candidate['summary_id'], 'sum-user')
        self.assertTrue(exact_candidate['parent_summary_present'])
        self.assertEqual(prompt_candidate['candidate_id'], exact_candidate['candidate_id'])
        self.assertEqual(prompt_candidate['parent_summary']['id'], 'sum-user')
        self.assertEqual(prompt_candidate['source_candidate_ids'], source_ids)

    def test_build_pre_arbiter_basket_applies_conservative_same_conversation_same_idea_without_collapsing_new_fact(self) -> None:
        retrieved = [
            _retrieved_trace(
                conversation_id='conv-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.92,
            ),
            _retrieved_trace(
                conversation_id='conv-a',
                role='user',
                content='Je suis Christophe Muck maintenant',
                timestamp='2026-04-10T09:00:05Z',
                score=0.89,
            ),
            _retrieved_trace(
                conversation_id='conv-a',
                role='user',
                content='Je suis Christophe Muck et j habite Rennes',
                timestamp='2026-04-10T09:00:10Z',
                score=0.87,
            ),
        ]
        internal = [
            _internal_trace(retrieved[0], semantic_score=0.81),
            _internal_trace(retrieved[1], semantic_score=0.79),
            _internal_trace(retrieved[2], semantic_score=0.78),
        ]
        memory_retrieved = _memory_retrieved(retrieved)

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=internal,
        )

        self.assertEqual(len(basket.candidates), 2)
        merged_candidate = basket.candidates[0]
        distinct_candidate = basket.candidates[1]
        self.assertEqual(merged_candidate['dedup_reason_code'], 'same_conversation_same_idea')
        self.assertEqual(len(merged_candidate['source_candidate_ids']), 2)
        self.assertEqual(distinct_candidate['content'], 'Je suis Christophe Muck et j habite Rennes')

    def test_build_pre_arbiter_basket_caps_candidates_to_eight(self) -> None:
        retrieved = [
            _retrieved_trace(
                conversation_id=f'conv-{index}',
                role='user',
                content=f'Souvenir distinct {index}',
                timestamp=f'2026-04-10T09:{index:02d}:00Z',
                score=1.0 - (index * 0.01),
            )
            for index in range(10)
        ]
        internal = [
            _internal_trace(trace, semantic_score=0.5)
            for trace in retrieved
        ]
        memory_retrieved = _memory_retrieved(retrieved)

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=internal,
        )

        self.assertEqual(len(basket.candidates), 8)
        self.assertEqual(
            [candidate['content'] for candidate in basket.candidates],
            [f'Souvenir distinct {index}' for index in range(8)],
        )
        self.assertEqual(len({candidate['candidate_id'] for candidate in basket.candidates}), 8)

    def test_select_prompt_candidates_keeps_stable_candidate_ids(self) -> None:
        retrieved = [
            _retrieved_trace(
                conversation_id='conv-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.94,
            ),
            _retrieved_trace(
                conversation_id='conv-b',
                role='assistant',
                content='Nous travaillons sur FridaDev',
                timestamp='2026-04-10T09:30:00Z',
                score=0.73,
            ),
        ]
        internal = [
            _internal_trace(retrieved[0], semantic_score=0.82),
            _internal_trace(retrieved[1], semantic_score=0.61),
        ]
        memory_retrieved = _memory_retrieved(retrieved)
        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=internal,
        )

        selected = memory_pre_arbiter_basket.select_prompt_candidates(
            basket,
            decisions=[
                {
                    'candidate_id': basket.candidates[1]['candidate_id'],
                    'keep': True,
                }
            ],
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['candidate_id'], basket.candidates[1]['candidate_id'])
        self.assertEqual(selected[0]['source_candidate_ids'], [basket.candidates[1]['candidate_id']])
        self.assertEqual(selected[0]['timestamp_iso'], '2026-04-10T09:30:00Z')


if __name__ == '__main__':
    unittest.main()
