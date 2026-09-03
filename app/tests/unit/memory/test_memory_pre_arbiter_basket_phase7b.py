from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core.hermeneutic_node.inputs import memory_arbitration_input, memory_retrieved_input
from memory import arbiter
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
    def test_distinct_weekday_corrections_reach_the_real_arbiter_messages(self) -> None:
        older_text = (
            'Le rendez-vous pour poursuivre notre discussion est fixé mardi '
            'à dix heures exactement.'
        )
        newer_text = (
            'Le rendez-vous pour poursuivre notre discussion est fixé jeudi '
            'à dix heures exactement.'
        )
        retrieved = [
            _retrieved_trace(
                conversation_id='conv-correction',
                role='user',
                content=older_text,
                timestamp='2026-08-25T10:00:00Z',
                score=0.97,
            ),
            _retrieved_trace(
                conversation_id='conv-correction',
                role='user',
                content=newer_text,
                timestamp='2026-08-27T10:00:00Z',
                score=0.89,
            ),
        ]
        memory_retrieved = _memory_retrieved(retrieved)
        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=[
                _internal_trace(retrieved[0], semantic_score=0.91),
                _internal_trace(retrieved[1], semantic_score=0.88),
            ],
        )
        captured_messages: list[dict[str, str]] = []

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {'choices': [{'message': {'content': '{"decisions":[]}'}}]}

        def fake_post(_url, *, json, headers, timeout):
            captured_messages.extend(json['messages'])
            return FakeResponse()

        with (
            mock.patch.object(
                arbiter,
                '_runtime_memory_arbiter_settings',
                return_value={
                    'model': 'synthetic-arbiter',
                    'temperature': 0.0,
                    'top_p': 1.0,
                    'max_tokens': 64,
                    'timeout_s': 1,
                },
            ),
            mock.patch.object(arbiter, '_load_prompt', return_value='synthetic prompt'),
            mock.patch.object(
                arbiter.llm_client,
                'with_provider_attribution',
                side_effect=lambda payload, caller: payload,
            ),
            mock.patch.object(
                arbiter.llm_client,
                'or_chat_completions_url',
                return_value='https://synthetic.invalid/chat/completions',
            ),
            mock.patch.object(arbiter.llm_client, 'or_headers', return_value={}),
            mock.patch.object(arbiter.llm_client, 'log_provider_metadata', return_value=None),
            mock.patch.object(arbiter.requests, 'post', side_effect=fake_post),
        ):
            arbiter.filter_traces_with_diagnostics(
                basket.prompt_candidates,
                [],
                now_iso='2026-09-03T12:00:00Z',
            )

        self.assertEqual([message['role'] for message in captured_messages], ['system', 'user'])
        candidate_payload = json.loads(
            captured_messages[1]['content'].split('=== Candidate memories ===\\n', 1)[1]
        )
        self.assertEqual([candidate['content'] for candidate in candidate_payload], [older_text, newer_text])
        self.assertEqual(
            [candidate['candidate_id'] for candidate in candidate_payload],
            [trace['candidate_id'] for trace in memory_retrieved['traces']],
        )
        self.assertEqual(
            [candidate['timestamp_iso'] for candidate in candidate_payload],
            ['2026-08-25T10:00:00Z', '2026-08-27T10:00:00Z'],
        )

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
        self.assertTrue(exact_candidate['dedup_key'])
        self.assertEqual(prompt_candidate['candidate_id'], exact_candidate['candidate_id'])
        self.assertEqual(prompt_candidate['parent_summary']['id'], 'sum-user')
        self.assertEqual(prompt_candidate['source_candidate_ids'], source_ids)

        decisions = [
            {
                'candidate_id': exact_candidate['candidate_id'],
                'keep': True,
                'semantic_relevance': 0.9,
                'contextual_gain': 0.8,
                'redundant_with_recent': False,
                'reason': 'synthetic keep',
                'decision_source': 'llm',
                'model': 'synthetic-arbiter',
            }
        ]
        selected = memory_pre_arbiter_basket.select_prompt_candidates(
            basket,
            decisions=decisions,
        )
        self.assertEqual(len(selected), 1)
        arbitration = memory_arbitration_input.build_memory_arbitration_input(
            memory_retrieved=memory_retrieved,
            raw_candidates_count=len(retrieved),
            decisions=decisions,
            status='available',
            basket_candidates=basket.candidates,
            injected_candidate_ids=[selected[0]['candidate_id']],
        )

        self.assertEqual(selected[0]['source_candidate_ids'], source_ids)
        self.assertEqual(arbitration['decisions'][0]['source_candidate_ids'], source_ids)
        self.assertEqual(arbitration['injected_candidate_ids'], [exact_candidate['candidate_id']])

    def test_distinct_quantity_negation_and_punctuation_are_not_textually_deduped(self) -> None:
        cases = [
            (
                'Le rendez-vous très important pour poursuivre notre discussion détaillée '
                'nécessite précisément 20 exemplaires préparés avant notre prochaine réunion.',
                'Le rendez-vous très important pour poursuivre notre discussion détaillée '
                'nécessite précisément 30 exemplaires préparés avant notre prochaine réunion.',
            ),
            ('Je peux venir demain.', 'Je peux venir demain : non.'),
            ('Le contrat reste valide.', 'Le contrat reste valide ?'),
        ]

        for older_text, newer_text in cases:
            with self.subTest(newer_text=newer_text):
                retrieved = [
                    _retrieved_trace(
                        conversation_id='conv-distinction',
                        role='user',
                        content=older_text,
                        timestamp='2026-08-25T10:00:00Z',
                        score=0.96,
                    ),
                    _retrieved_trace(
                        conversation_id='conv-distinction',
                        role='user',
                        content=newer_text,
                        timestamp='2026-08-27T10:00:00Z',
                        score=0.88,
                    ),
                ]
                memory_retrieved = _memory_retrieved(retrieved)

                basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
                    memory_retrieved=memory_retrieved,
                    retrieved_candidates=retrieved,
                    internal_traces=[
                        _internal_trace(retrieved[0], semantic_score=0.90),
                        _internal_trace(retrieved[1], semantic_score=0.86),
                    ],
                )

                self.assertEqual([candidate['content'] for candidate in basket.candidates], [older_text, newer_text])
                self.assertEqual([candidate['dedup_reason_code'] for candidate in basket.candidates], ['none', 'none'])
                self.assertEqual(len({candidate['dedup_key'] for candidate in basket.candidates}), 2)
                self.assertEqual(
                    [candidate['source_candidate_ids'] for candidate in basket.candidates],
                    [[trace['candidate_id']] for trace in memory_retrieved['traces']],
                )

    def test_same_conversation_extension_is_preserved_without_semantic_guessing(self) -> None:
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

        self.assertEqual(len(basket.candidates), 3)
        self.assertEqual(
            [candidate['content'] for candidate in basket.candidates],
            [
                'Je suis Christophe Muck',
                'Je suis Christophe Muck maintenant',
                'Je suis Christophe Muck et j habite Rennes',
            ],
        )
        self.assertTrue(all(candidate['dedup_reason_code'] == 'none' for candidate in basket.candidates))

    def test_distinct_formulations_keep_rank_when_arrival_and_scores_are_reversed(self) -> None:
        lower_ranked = _retrieved_trace(
            conversation_id='conv-order',
            role='user',
            content=(
                'Le rendez-vous pour poursuivre notre discussion est fixé mardi '
                'à dix heures exactement.'
            ),
            timestamp='2026-08-25T10:00:00Z',
            score=0.80,
        )
        higher_ranked = _retrieved_trace(
            conversation_id='conv-order',
            role='user',
            content=(
                'Le rendez-vous pour poursuivre notre discussion est fixé jeudi '
                'à dix heures exactement.'
            ),
            timestamp='2026-08-27T10:00:00Z',
            score=0.98,
        )
        retrieved = [lower_ranked, higher_ranked]
        memory_retrieved = _memory_retrieved(retrieved)

        basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved,
            internal_traces=[
                _internal_trace(lower_ranked, semantic_score=0.79),
                _internal_trace(higher_ranked, semantic_score=0.94),
            ],
        )

        self.assertEqual(
            [candidate['content'] for candidate in basket.candidates],
            [higher_ranked['content'], lower_ranked['content']],
        )
        self.assertTrue(all(len(candidate['source_candidate_ids']) == 1 for candidate in basket.candidates))

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
        self.assertTrue(all(candidate['dedup_reason_code'] == 'none' for candidate in basket.candidates))
        selected_source_ids = {
            source_id
            for candidate in basket.candidates
            for source_id in candidate['source_candidate_ids']
        }
        excluded_ids = {trace['candidate_id'] for trace in memory_retrieved['traces'][8:]}
        self.assertTrue(selected_source_ids.isdisjoint(excluded_ids))

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
