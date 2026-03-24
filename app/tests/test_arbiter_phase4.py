from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from memory import arbiter
import config


class ArbiterPhase4ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_arbiter_calls_use_runtime_model_from_db_when_present(self) -> None:
        observed_models = []
        original_get_settings = arbiter.runtime_settings.get_arbiter_model_settings
        original_load_prompt = arbiter._load_prompt
        original_post = arbiter.requests.post

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
            return FakeResponse('{"entries":[]}')

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        try:
            kept, decisions = arbiter.filter_traces_with_diagnostics(
                [{'role': 'assistant', 'content': 'memoire candidate', 'timestamp': '2026-03-24T00:00:00Z', 'score': 0.9}],
                [{'role': 'user', 'content': 'question recente'}],
            )
            entries = arbiter.extract_identities(
                [{'role': 'user', 'content': 'je suis chercheur'}],
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post

        self.assertEqual(kept, [])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(entries, [])
        self.assertEqual(observed_models, ['openai/gpt-5.4-mini', 'openai/gpt-5.4-mini'])

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
            return FakeResponse('{"entries":[]}')

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
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post

        self.assertEqual(observed_models, [config.ARBITER_MODEL, config.ARBITER_MODEL])


if __name__ == '__main__':
    unittest.main()
