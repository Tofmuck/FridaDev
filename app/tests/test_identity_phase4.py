from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from identity import identity
import config


class IdentityPhase4MainModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_identity_token_count_uses_runtime_main_model_from_db_when_present(self) -> None:
        observed = {'model': None}
        original_get_settings = identity.runtime_settings.get_main_model_settings
        original_count_tokens = identity.token_utils.count_tokens

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4-nano', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        def fake_count_tokens(messages, model):
            observed['model'] = model
            return 42

        identity.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        identity.token_utils.count_tokens = fake_count_tokens
        try:
            count = identity._count_tokens('memoire identitaire')
        finally:
            identity.runtime_settings.get_main_model_settings = original_get_settings
            identity.token_utils.count_tokens = original_count_tokens

        self.assertEqual(count, 42)
        self.assertEqual(observed['model'], 'openai/gpt-5.4-nano')

    def test_identity_token_count_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        observed = {'model': None}
        original_get_settings = identity.runtime_settings.get_main_model_settings
        original_count_tokens = identity.token_utils.count_tokens

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='empty_table',
            )

        def fake_count_tokens(messages, model):
            observed['model'] = model
            return 7

        identity.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        identity.token_utils.count_tokens = fake_count_tokens
        try:
            count = identity._count_tokens('memoire identitaire')
        finally:
            identity.runtime_settings.get_main_model_settings = original_get_settings
            identity.token_utils.count_tokens = original_count_tokens

        self.assertEqual(count, 7)
        self.assertEqual(observed['model'], config.OR_MODEL)


if __name__ == '__main__':
    unittest.main()
