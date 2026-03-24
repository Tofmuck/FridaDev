from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import llm_client
import config


class LlmClientRuntimeSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_or_headers_uses_decrypted_db_api_key_when_available(self) -> None:
        original = llm_client.runtime_settings.get_runtime_secret_value

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('main_model', 'api_key'))
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-db-runtime-key',
                source='db_encrypted',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            headers = llm_client.or_headers(caller='arbiter')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original

        self.assertEqual(headers['Authorization'], 'Bearer sk-db-runtime-key')
        self.assertEqual(headers['X-Title'], config.OR_TITLE_ARBITER)

    def test_or_headers_keeps_env_fallback_when_db_secret_is_missing(self) -> None:
        original = llm_client.runtime_settings.get_runtime_secret_value
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-env-fallback-key'

        def fake_get_runtime_secret_value(section: str, field: str):
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-env-fallback-key',
                source='env_fallback',
                source_reason='empty_table',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            headers = llm_client.or_headers(caller='llm')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original
            config.OR_KEY = original_api_key

        self.assertEqual(headers['Authorization'], 'Bearer sk-env-fallback-key')

    def test_build_payload_uses_runtime_main_model_from_db_when_present(self) -> None:
        original = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4', 'origin': 'db'},
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

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            payload = llm_client.build_payload(
                messages=[{'role': 'user', 'content': 'bonjour'}],
                temperature=0.7,
                top_p=0.9,
                max_tokens=512,
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original

        self.assertEqual(payload['model'], 'openai/gpt-5.4')
        self.assertEqual(payload['temperature'], 0.7)
        self.assertEqual(payload['top_p'], 0.9)
        self.assertEqual(payload['max_tokens'], 512)

    def test_build_payload_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        original = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='empty_table',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            payload = llm_client.build_payload(
                messages=[{'role': 'user', 'content': 'bonjour'}],
                temperature=0.4,
                top_p=1.0,
                max_tokens=256,
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original

        self.assertEqual(payload['model'], config.OR_MODEL)


if __name__ == '__main__':
    unittest.main()
