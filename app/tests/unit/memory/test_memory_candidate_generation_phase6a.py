from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import memory_traces_summaries


class MemoryCandidateGenerationPhase6ATests(unittest.TestCase):
    def test_extract_lexical_query_terms_keeps_only_salient_exact_tokens(self) -> None:
        self.assertEqual(
            memory_traces_summaries._extract_lexical_query_terms(
                'OVH migration Authelia Caddy Docker'
            ),
            ['ovh', 'authelia', 'caddy', 'docker'],
        )
        self.assertEqual(
            memory_traces_summaries._extract_lexical_query_terms(
                'memoire identite durable episodique utilisateur'
            ),
            [],
        )
        self.assertEqual(
            memory_traces_summaries._extract_lexical_query_terms(
                'codex-8192-live-1775296899'
            ),
            ['codex', '8192', 'live', '1775296899'],
        )
        self.assertEqual(
            memory_traces_summaries._extract_lexical_query_terms(
                'qui suis-je pour toi maintenant identite durable'
            ),
            [],
        )

    def test_exact_lookup_trigger_keeps_url_locator_queries_exact(self) -> None:
        exact_tokens = memory_traces_summaries._extract_lexical_exact_tokens(
            'Tu peux le trouver et le lire là : '
            'https://blogs.mediapart.fr/christophe-muck/blog/030426/apres-la-garde-vue-de-rima-hassan-ce-que-l-occident-refuse-de-voir'
        )
        self.assertTrue(
            memory_traces_summaries._should_use_exact_token_lookup(
                'Tu peux le trouver et le lire là : '
                'https://blogs.mediapart.fr/christophe-muck/blog/030426/apres-la-garde-vue-de-rima-hassan-ce-que-l-occident-refuse-de-voir',
                normalized_query=memory_traces_summaries._normalize_lexical_text(
                    'Tu peux le trouver et le lire là : '
                    'https://blogs.mediapart.fr/christophe-muck/blog/030426/apres-la-garde-vue-de-rima-hassan-ce-que-l-occident-refuse-de-voir'
                ),
                exact_tokens=exact_tokens,
            )
        )

    def test_exact_lookup_trigger_does_not_hijack_semantic_queries_with_one_numeric_token(self) -> None:
        exact_tokens = memory_traces_summaries._extract_lexical_exact_tokens(
            'OVH migration 2026'
        )
        self.assertFalse(
            memory_traces_summaries._should_use_exact_token_lookup(
                'OVH migration 2026',
                normalized_query=memory_traces_summaries._normalize_lexical_text(
                    'OVH migration 2026'
                ),
                exact_tokens=exact_tokens,
            )
        )

    def test_merge_hybrid_candidates_respects_final_cap_and_preserves_public_shape(self) -> None:
        dense_candidates = [
            {
                'conversation_id': 'conv-1',
                'role': 'user',
                'content': 'OVH migration',
                'timestamp': '2026-04-10T10:00:00Z',
                'summary_id': 'sum-1',
                'score': 0.91,
            },
            {
                'conversation_id': 'conv-2',
                'role': 'assistant',
                'content': 'Infrastructure a Roubaix',
                'timestamp': '2026-04-09T10:00:00Z',
                'summary_id': None,
                'score': 0.86,
            },
            {
                'conversation_id': 'conv-3',
                'role': 'user',
                'content': 'Exact lexical candidate',
                'timestamp': '2026-04-08T10:00:00Z',
                'summary_id': None,
                'score': 0.71,
            },
        ]
        lexical_candidates = [
            {
                'conversation_id': 'conv-3',
                'role': 'user',
                'content': 'Exact lexical candidate',
                'timestamp': '2026-04-08T10:00:00Z',
                'summary_id': None,
                'score': 0.98,
                '_lexical_term_hits': 4,
                '_lexical_phrase_hit': 1,
            },
            {
                'conversation_id': 'conv-4',
                'role': 'assistant',
                'content': 'lexical-only weak candidate',
                'timestamp': '2026-04-07T10:00:00Z',
                'summary_id': None,
                'score': 0.28,
                '_lexical_term_hits': 1,
                '_lexical_phrase_hit': 0,
            },
        ]

        out = memory_traces_summaries._merge_hybrid_candidates(
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            top_k=2,
        )

        self.assertEqual(len(out), 2)
        self.assertEqual(
            set(out[0].keys()),
            {'conversation_id', 'role', 'content', 'timestamp', 'summary_id', 'score'},
        )
        self.assertEqual(out[0]['content'], 'Exact lexical candidate')
        self.assertEqual(out[1]['summary_id'], 'sum-1')
        self.assertEqual(out[1]['timestamp'], '2026-04-10T10:00:00Z')

    def test_merge_hybrid_candidates_dedupes_same_row_across_dense_and_lexical(self) -> None:
        shared = {
            'conversation_id': 'conv-1',
            'role': 'user',
            'content': 'codex-8192-live-1775296899',
            'timestamp': '2026-04-10T11:00:00Z',
            'summary_id': None,
        }
        out = memory_traces_summaries._merge_hybrid_candidates(
            dense_candidates=[{**shared, 'score': 0.95}],
            lexical_candidates=[
                {
                    **shared,
                    'score': 0.98,
                    '_lexical_term_hits': 4,
                    '_lexical_phrase_hit': 1,
                }
            ],
            top_k=5,
        )

        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['content'], shared['content'])
        self.assertGreaterEqual(out[0]['score'], 0.98)

    def test_merge_hybrid_candidates_does_not_let_single_term_lexical_noise_outrank_dense_top_items(self) -> None:
        dense_candidates = [
            {
                'conversation_id': 'conv-1',
                'role': 'assistant',
                'content': 'dense item one',
                'timestamp': '2026-04-10T10:00:00Z',
                'summary_id': None,
                'score': 0.92,
            },
            {
                'conversation_id': 'conv-2',
                'role': 'assistant',
                'content': 'dense item two',
                'timestamp': '2026-04-10T09:00:00Z',
                'summary_id': None,
                'score': 0.89,
            },
        ]
        lexical_candidates = [
            {
                'conversation_id': 'conv-3',
                'role': 'user',
                'content': 'single term lexical noise',
                'timestamp': '2026-04-10T12:00:00Z',
                'summary_id': None,
                'score': 0.35,
                '_lexical_term_hits': 1,
                '_lexical_phrase_hit': 0,
            }
        ]

        out = memory_traces_summaries._merge_hybrid_candidates(
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            top_k=2,
        )

        self.assertEqual([row['content'] for row in out], ['dense item one', 'dense item two'])

    def test_retrieve_preserves_timestamp_and_summary_id_for_lexical_only_candidate(self) -> None:
        original_dense = memory_traces_summaries._retrieve_dense_candidates
        original_lexical = memory_traces_summaries._retrieve_lexical_candidates

        memory_traces_summaries._retrieve_dense_candidates = lambda *_args, **_kwargs: []
        memory_traces_summaries._retrieve_lexical_candidates = lambda *_args, **_kwargs: [
            {
                'conversation_id': 'conv-lex',
                'role': 'user',
                'content': 'Christophe Muck',
                'timestamp': '2026-04-10T12:34:56Z',
                'summary_id': 'sum-lex',
                'score': 0.98,
                '_lexical_term_hits': 2,
                '_lexical_phrase_hit': 1,
            }
        ]
        try:
            rows = memory_traces_summaries.retrieve(
                'Christophe Muck',
                top_k=1,
                runtime_embedding_value_fn=lambda _field: 5,
                conn_factory=lambda: object(),
                embed_fn=lambda *_args, **_kwargs: [0.1, 0.2, 0.3],
                logger=SimpleNamespace(warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
        finally:
            memory_traces_summaries._retrieve_dense_candidates = original_dense
            memory_traces_summaries._retrieve_lexical_candidates = original_lexical

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['timestamp'], '2026-04-10T12:34:56Z')
        self.assertEqual(rows[0]['summary_id'], 'sum-lex')
        self.assertEqual(
            set(rows[0].keys()),
            {'conversation_id', 'role', 'content', 'timestamp', 'summary_id', 'score'},
        )
