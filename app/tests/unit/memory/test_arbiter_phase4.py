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
                        'candidate_id': 'cand-codex-live',
                        'source_kind': 'trace',
                        'source_lane': 'global',
                        'role': 'user',
                        'content': 'codex-8192-live-1775296899',
                        'timestamp_iso': '2026-04-10T09:00:00Z',
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
        self.assertEqual(observed_candidates[0]['candidate_id'], 'cand-codex-live')
        self.assertEqual(observed_candidates[0]['source_kind'], 'trace')
        self.assertEqual(observed_candidates[0]['source_lane'], 'global')
        self.assertEqual(observed_candidates[0]['retrieval_score'], 0.98)
        self.assertEqual(observed_candidates[0]['semantic_score'], 0.0)
        self.assertNotIn('score', observed_candidates[0])

    def test_filter_traces_payload_exposes_local_temporal_anchor_for_relative_memories(self) -> None:
        observed = {'user_content': ''}
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

        def fake_post(_url, json, headers, timeout):
            observed['user_content'] = json['messages'][1]['content']
            return FakeResponse()

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        arbiter.llm_client.or_headers = lambda caller='arbiter': {'Authorization': f'caller={caller}'}
        arbiter.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            arbiter.filter_traces_with_diagnostics(
                [
                    {
                        'candidate_id': 'cand-hier',
                        'source_kind': 'trace',
                        'source_lane': 'global',
                        'role': 'user',
                        'content': "Hier soir j'avais besoin de calme",
                        'timestamp_iso': '2026-05-17T21:00:00Z',
                        'retrieval_score': 0.91,
                        'semantic_score': 0.91,
                    }
                ],
                [
                    {
                        'role': 'user',
                        'content': "Aujourd'hui je reparle de ce calme",
                        'timestamp': '2026-05-17T22:05:00Z',
                    }
                ],
                now_iso='2026-05-17T22:05:00Z',
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            arbiter.llm_client.or_headers = original_or_headers
            arbiter.llm_client.log_provider_metadata = original_log_provider_metadata

        user_content = observed['user_content']
        self.assertLess(user_content.index('=== Temporal reference ==='), user_content.index('=== Recent context ==='))
        self.assertIn('"local_date": "2026-05-18"', user_content)
        self.assertIn('"timezone": "Europe/Paris"', user_content)
        self.assertIn("lundi 18 mai 2026 à 0h05 Europe/Paris — à l'instant", user_content)
        candidates = json.loads(user_content.split('=== Candidate memories ===\\n', 1)[1])
        self.assertEqual(candidates[0]['candidate_id'], 'cand-hier')
        self.assertEqual(
            candidates[0]['temporal_label'],
            'dimanche 17 mai 2026 à 23h Europe/Paris — hier',
        )

    def test_identity_extractor_rejects_weak_relative_temporal_entries(self) -> None:
        observed = {'user_content': ''}
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
                return {
                    'choices': [
                        {
                            'message': {
                                'content': json.dumps(
                                    {
                                        'entries': [
                                            {
                                                'subject': 'user',
                                                'content': "Aujourd'hui je suis anxieux",
                                                'stability': 'durable',
                                                'utterance_mode': 'self_description',
                                                'recurrence': 'first_seen',
                                                'scope': 'user',
                                                'evidence_kind': 'explicit',
                                                'confidence': 0.9,
                                                'reason': 'temporal self description',
                                            }
                                        ]
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }

        def fake_post(_url, json, headers, timeout):
            observed['user_content'] = json['messages'][1]['content']
            return FakeResponse()

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        arbiter.llm_client.or_headers = lambda caller='identity_extractor': {'Authorization': f'caller={caller}'}
        arbiter.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            entries = arbiter.extract_identities(
                [{'role': 'user', 'content': "Aujourd'hui je suis anxieux"}],
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            arbiter.llm_client.or_headers = original_or_headers
            arbiter.llm_client.log_provider_metadata = original_log_provider_metadata

        self.assertEqual(entries, [])
        self.assertIn('Temporal identity policy', observed['user_content'])
        self.assertIn('prefer no entry', observed['user_content'])

    def test_identity_periodic_agent_rejects_weak_relative_temporal_operations(self) -> None:
        observed = {'user_content': ''}
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
                return {
                    'choices': [
                        {
                            'message': {
                                'content': (
                                    '{"llm":{"operations":[{"kind":"no_change","proposition":"","reason":"no update"}]},'
                                    '"user":{"operations":[{"kind":"add","proposition":"En ce moment l utilisateur est anxieux",'
                                    '"reason":"current state"}]},'
                                    '"meta":{"execution_status":"complete","buffer_pairs_count":15,"window_complete":true}}'
                                )
                            }
                        }
                    ]
                }

        def fake_post(_url, json, headers, timeout):
            observed['user_content'] = json['messages'][1]['content']
            return FakeResponse()

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        arbiter.llm_client.or_headers = lambda caller='identity_periodic_agent': {'Authorization': f'caller={caller}'}
        arbiter.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            result = arbiter.run_identity_periodic_agent(
                {
                    'buffer_pairs': [],
                    'buffer_pairs_count': 15,
                    'buffer_target_pairs': 15,
                    'identities': {
                        'llm': {'static': 'Frida statique', 'mutable_current': ''},
                        'user': {'static': 'Utilisateur statique', 'mutable_current': ''},
                    },
                    'mutable_budget': {'target_chars': 3000, 'max_chars': 3300},
                }
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            arbiter.llm_client.or_headers = original_or_headers
            arbiter.llm_client.log_provider_metadata = original_log_provider_metadata

        self.assertEqual(
            result['user']['operations'],
            [
                {
                    'kind': 'no_change',
                    'proposition': '',
                    'reason': 'relative temporal identity signal rejected',
                }
            ],
        )
        self.assertIn('identity_temporal_policy', observed['user_content'])

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
                '{"llm":{"operations":[{"kind":"no_change","proposition":"","reason":"no update"}]},'
                '"user":{"operations":[{"kind":"no_change","proposition":"","reason":"no update"}]},'
                '"meta":{"execution_status":"complete","buffer_pairs_count":15,"window_complete":true}}',
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
            periodic = arbiter.run_identity_periodic_agent(
                {
                    'buffer_pairs': [
                        {
                            'user': {'role': 'user', 'content': 'bonjour'},
                            'assistant': {'role': 'assistant', 'content': 'salut'},
                        }
                    ],
                    'buffer_pairs_count': 15,
                    'buffer_target_pairs': 15,
                    'identities': {
                        'llm': {'static': 'Frida statique', 'mutable_current': ''},
                        'user': {'static': 'Utilisateur statique', 'mutable_current': ''},
                    },
                    'mutable_budget': {'target_chars': 3000, 'max_chars': 3300},
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
            periodic,
            {
                'llm': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'no update'},
                    ],
                },
                'user': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'no update'},
                    ],
                },
                'meta': {
                    'execution_status': 'complete',
                    'buffer_pairs_count': 15,
                    'window_complete': True,
                },
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
                {'Authorization': 'caller=identity_periodic_agent'},
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
                    'identity_periodic_agent_provider_response',
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
                '{"llm":{"operations":[{"kind":"no_change","proposition":"","reason":"no update"}]},'
                '"user":{"operations":[{"kind":"no_change","proposition":"","reason":"no update"}]},'
                '"meta":{"execution_status":"complete","buffer_pairs_count":15,"window_complete":true}}'
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
            arbiter.run_identity_periodic_agent(
                {
                    'buffer_pairs': [
                        {
                            'user': {'role': 'user', 'content': 'bonjour'},
                            'assistant': {'role': 'assistant', 'content': 'salut'},
                        }
                    ],
                    'buffer_pairs_count': 15,
                    'buffer_target_pairs': 15,
                    'identities': {
                        'llm': {'static': 'Frida statique', 'mutable_current': ''},
                        'user': {'static': 'Utilisateur statique', 'mutable_current': ''},
                    },
                    'mutable_budget': {'target_chars': 3000, 'max_chars': 3300},
                }
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post

        self.assertEqual(observed_models, [config.ARBITER_MODEL, config.ARBITER_MODEL, config.ARBITER_MODEL])


if __name__ == '__main__':
    unittest.main()
