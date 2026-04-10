from __future__ import annotations

import json
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

from admin import runtime_settings
from memory import arbiter
import config


class ArbiterPhase4ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_deterministic_fallback_uses_explicit_semantic_score_when_available(self) -> None:
        traces = [
            {
                'role': 'user',
                'content': 'codex-8192-live-1775296899',
                'timestamp': '2026-04-10T09:00:00Z',
                'score': 0.98,
                'retrieval_score': 0.98,
                'semantic_score': 0.0,
            },
            {
                'role': 'assistant',
                'content': 'Migration OVH vers Caddy et Authelia',
                'timestamp': '2026-04-10T09:01:00Z',
                'score': 0.71,
                'retrieval_score': 0.71,
                'semantic_score': 0.71,
            },
        ]

        kept, decisions = arbiter._deterministic_fallback(
            traces,
            reason='timeout',
            model='openai/gpt-5.4-mini',
        )

        self.assertEqual([trace['content'] for trace in kept], ['Migration OVH vers Caddy et Authelia'])
        self.assertEqual(decisions[0]['semantic_relevance'], 0.0)
        self.assertTrue(decisions[1]['keep'])

    def test_filter_traces_payload_exposes_retrieval_and_semantic_scores_separately(self) -> None:
        observed_candidates = []
        original_get_settings = arbiter.runtime_settings.get_arbiter_model_settings
        original_load_prompt = arbiter._load_prompt
        original_post = arbiter.requests.post
        original_or_headers = arbiter.llm_client.or_headers
        original_log_provider_metadata = arbiter.llm_client.log_provider_metadata

        def fake_get_arbiter_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='arbiter_model',
                payload=runtime_settings.build_env_seed_bundle('arbiter_model').payload,
                source='env',
                source_reason='empty_table',
            )

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'choices': [{'message': {'content': '{"decisions":[]}'}}]}

        def fake_post(url, json, headers, timeout):
            user_content = json['messages'][1]['content']
            payload_marker = '=== Candidate memories ===\\n'
            observed_candidates.extend(json_module.loads(user_content.split(payload_marker, 1)[1]))
            return FakeResponse()

        json_module = json
        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        arbiter.llm_client.or_headers = lambda caller='arbiter': {'Authorization': f'caller={caller}'}
        arbiter.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            arbiter.filter_traces_with_diagnostics(
                [
                    {
                        'role': 'user',
                        'content': 'codex-8192-live-1775296899',
                        'timestamp': '2026-04-10T09:00:00Z',
                        'score': 0.98,
                        'retrieval_score': 0.98,
                        'semantic_score': 0.0,
                    }
                ],
                [{'role': 'user', 'content': 'Quel etait le code ?'}],
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            arbiter.llm_client.or_headers = original_or_headers
            arbiter.llm_client.log_provider_metadata = original_log_provider_metadata

        self.assertEqual(len(observed_candidates), 1)
        self.assertEqual(observed_candidates[0]['retrieval_score'], 0.98)
        self.assertEqual(observed_candidates[0]['semantic_score'], 0.0)
        self.assertNotIn('score', observed_candidates[0])

    def test_arbiter_calls_use_runtime_model_from_db_when_present(self) -> None:
        observed_models = []
        observed_headers = []
        observed_provider_logs = []
        original_get_settings = arbiter.runtime_settings.get_arbiter_model_settings
        original_load_prompt = arbiter._load_prompt
        original_post = arbiter.requests.post
        original_or_headers = arbiter.llm_client.or_headers
        original_log_provider_metadata = arbiter.llm_client.log_provider_metadata

        def fake_get_arbiter_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='arbiter_model',
                payload=runtime_settings.normalize_stored_payload(
                    'arbiter_model',
                    {
                        'model': {'value': 'openai/gpt-5.4-mini', 'origin': 'db'},
                        'temperature': {'value': 0.0, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                        'timeout_s': {'value': 45, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        class FakeResponse:
            def __init__(self, content: str, generation_id: str) -> None:
                self._content = content
                self._generation_id = generation_id

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    'id': self._generation_id,
                    'model': 'openai/gpt-5.4-mini',
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 3, 'total_tokens': 13},
                    'choices': [{'message': {'content': self._content}}],
                }

        def fake_post(url, json, headers, timeout):
            observed_models.append(json['model'])
            observed_headers.append(dict(headers))
            if len(observed_models) == 1:
                return FakeResponse(
                    '{"decisions":[{"candidate_id":"0","keep":false,"semantic_relevance":0.1,"contextual_gain":0.1,"redundant_with_recent":false,"reason":"noop"}]}',
                    generation_id='gen-1',
                )
            if len(observed_models) == 2:
                return FakeResponse('{"entries":[]}', generation_id='gen-2')
            return FakeResponse(
                '{"llm":{"action":"no_change","content":"","reason":"no update"},'
                '"user":{"action":"no_change","content":"","reason":"no update"}}',
                generation_id='gen-3',
            )

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        arbiter.llm_client.or_headers = lambda caller='llm': {'Authorization': f'caller={caller}'}
        arbiter.llm_client.log_provider_metadata = lambda _logger, event_name, provider_metadata: observed_provider_logs.append(
            (event_name, dict(provider_metadata))
        )
        try:
            kept, decisions = arbiter.filter_traces_with_diagnostics(
                [{'role': 'assistant', 'content': 'memoire candidate', 'timestamp': '2026-03-24T00:00:00Z', 'score': 0.9}],
                [{'role': 'user', 'content': 'question recente'}],
            )
            entries = arbiter.extract_identities(
                [{'role': 'user', 'content': 'je suis chercheur'}],
            )
            rewrite = arbiter.rewrite_identity_mutables(
                {
                    'recent_turns': [{'role': 'user', 'content': 'bonjour'}],
                    'identities': {
                        'llm': {'static': 'Frida statique', 'mutable_current': ''},
                        'user': {'static': 'Utilisateur statique', 'mutable_current': ''},
                    },
                    'mutable_budget': {'target_chars': 1500, 'max_chars': 1650},
                }
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            arbiter.llm_client.or_headers = original_or_headers
            arbiter.llm_client.log_provider_metadata = original_log_provider_metadata

        self.assertEqual(kept, [])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(entries, [])
        self.assertEqual(
            rewrite,
            {
                'llm': {'action': 'no_change', 'content': '', 'reason': 'no update'},
                'user': {'action': 'no_change', 'content': '', 'reason': 'no update'},
            },
        )
        self.assertEqual(
            observed_models,
            ['openai/gpt-5.4-mini', 'openai/gpt-5.4-mini', 'openai/gpt-5.4-mini'],
        )
        self.assertEqual(
            observed_headers,
            [
                {'Authorization': 'caller=arbiter'},
                {'Authorization': 'caller=identity_extractor'},
                {'Authorization': 'caller=identity_mutable_rewriter'},
            ],
        )
        self.assertEqual(
            observed_provider_logs,
            [
                (
                    'arbiter_provider_response',
                    {
                        'provider_generation_id': 'gen-1',
                        'provider_model': 'openai/gpt-5.4-mini',
                        'provider_prompt_tokens': 10,
                        'provider_completion_tokens': 3,
                        'provider_total_tokens': 13,
                    },
                ),
                (
                    'identity_extractor_provider_response',
                    {
                        'provider_generation_id': 'gen-2',
                        'provider_model': 'openai/gpt-5.4-mini',
                        'provider_prompt_tokens': 10,
                        'provider_completion_tokens': 3,
                        'provider_total_tokens': 13,
                    },
                ),
                (
                    'identity_mutable_rewriter_provider_response',
                    {
                        'provider_generation_id': 'gen-3',
                        'provider_model': 'openai/gpt-5.4-mini',
                        'provider_prompt_tokens': 10,
                        'provider_completion_tokens': 3,
                        'provider_total_tokens': 13,
                    },
                ),
            ],
        )

    def test_arbiter_calls_keep_env_fallback_when_db_row_is_missing(self) -> None:
        observed_models = []
        original_get_settings = arbiter.runtime_settings.get_arbiter_model_settings
        original_load_prompt = arbiter._load_prompt
        original_post = arbiter.requests.post

        def fake_get_arbiter_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='arbiter_model',
                payload=runtime_settings.build_env_seed_bundle('arbiter_model').payload,
                source='env',
                source_reason='empty_table',
            )

        class FakeResponse:
            def __init__(self, content: str) -> None:
                self._content = content

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'choices': [{'message': {'content': self._content}}]}

        def fake_post(url, json, headers, timeout):
            observed_models.append(json['model'])
            if len(observed_models) == 1:
                return FakeResponse(
                    '{"decisions":[{"candidate_id":"0","keep":false,"semantic_relevance":0.1,"contextual_gain":0.1,"redundant_with_recent":false,"reason":"noop"}]}'
                )
            if len(observed_models) == 2:
                return FakeResponse('{"entries":[]}')
            return FakeResponse(
                '{"llm":{"action":"no_change","content":"","reason":"no update"},'
                '"user":{"action":"no_change","content":"","reason":"no update"}}'
            )

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        try:
            arbiter.filter_traces_with_diagnostics(
                [{'role': 'assistant', 'content': 'memoire candidate', 'timestamp': '2026-03-24T00:00:00Z', 'score': 0.9}],
                [{'role': 'user', 'content': 'question recente'}],
            )
            arbiter.extract_identities(
                [{'role': 'user', 'content': 'je suis chercheur'}],
            )
            arbiter.rewrite_identity_mutables(
                {
                    'recent_turns': [{'role': 'user', 'content': 'bonjour'}],
                    'identities': {
                        'llm': {'static': 'Frida statique', 'mutable_current': ''},
                        'user': {'static': 'Utilisateur statique', 'mutable_current': ''},
                    },
                    'mutable_budget': {'target_chars': 1500, 'max_chars': 1650},
                }
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post

        self.assertEqual(observed_models, [config.ARBITER_MODEL, config.ARBITER_MODEL, config.ARBITER_MODEL])


if __name__ == '__main__':
    unittest.main()
