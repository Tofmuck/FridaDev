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

from admin import runtime_settings
import config


class RuntimeSettingsRuntimeReadPathTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_describe_secret_sources_marks_env_seed_secret_as_env_fallback(self) -> None:
        payload = runtime_settings.build_env_seed_bundle('main_model').payload
        secret_sources = runtime_settings.describe_secret_sources('main_model', payload)
        self.assertEqual(secret_sources['api_key'], 'env_fallback' if config.OR_KEY else 'missing')

    def test_describe_secret_sources_marks_db_secret_as_db_encrypted(self) -> None:
        secret_sources = runtime_settings.describe_secret_sources(
            'services',
            {
                'searxng_url': {'value': 'http://127.0.0.1:8092', 'origin': 'db'},
                'searxng_results': {'value': 5, 'origin': 'db'},
                'crawl4ai_url': {'value': 'http://127.0.0.1:11235', 'origin': 'db'},
                'crawl4ai_token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                'crawl4ai_top_n': {'value': 2, 'origin': 'db'},
                'crawl4ai_max_chars': {'value': 5000, 'origin': 'db'},
                'crawl4ai_explicit_url_max_chars': {'value': 25000, 'origin': 'db'},
            },
        )
        self.assertEqual(secret_sources['crawl4ai_token'], 'db_encrypted')

    def test_describe_secret_sources_keeps_database_dsn_on_env_fallback_while_bootstrap_env_exists(self) -> None:
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        try:
            secret_sources = runtime_settings.describe_secret_sources(
                'database',
                {
                    'backend': {'value': 'postgresql', 'origin': 'db'},
                    'dsn': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                },
            )
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertEqual(secret_sources['dsn'], 'env_fallback')

    def test_runtime_section_falls_back_to_env_when_table_is_empty(self) -> None:
        view = runtime_settings.get_runtime_section('main_model', fetcher=lambda: {})
        self.assertEqual(view.source, 'env')
        self.assertEqual(view.source_reason, 'empty_table')
        self.assertEqual(view.payload['model']['value'], config.OR_MODEL)

    def test_runtime_section_falls_back_to_env_when_db_is_unavailable(self) -> None:
        def failing_fetcher():
            raise runtime_settings.RuntimeSettingsDbUnavailableError('db down')

        view = runtime_settings.get_runtime_section('services', fetcher=failing_fetcher)
        self.assertEqual(view.source, 'env')
        self.assertEqual(view.source_reason, 'db_unavailable')
        self.assertEqual(view.payload['searxng_url']['value'], config.SEARXNG_URL)

    def test_runtime_section_uses_db_row_when_present(self) -> None:
        def fetcher():
            return {
                'embedding': runtime_settings.normalize_stored_payload(
                    'embedding',
                    {
                        'endpoint': {'value': 'https://embed.override.example', 'origin': 'db'},
                        'model': {'value': 'custom-embed-model', 'origin': 'db'},
                        'token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'dimensions': {'value': 768, 'origin': 'db'},
                        'top_k': {'value': 9, 'origin': 'db'},
                    },
                )
            }

        view = runtime_settings.get_embedding_settings(fetcher=fetcher)
        self.assertEqual(view.source, 'db')
        self.assertEqual(view.source_reason, 'db_row')
        self.assertEqual(view.payload['model']['value'], 'custom-embed-model')
        self.assertEqual(view.payload['dimensions']['value'], 768)

    def test_runtime_section_marks_missing_section_when_other_rows_exist(self) -> None:
        def fetcher():
            return {
                'services': runtime_settings.normalize_stored_payload(
                    'services',
                    {
                        'searxng_url': {'value': 'http://127.0.0.1:8092', 'origin': 'db'},
                        'searxng_results': {'value': 5, 'origin': 'db'},
                        'crawl4ai_url': {'value': 'http://127.0.0.1:11235', 'origin': 'db'},
                        'crawl4ai_token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'crawl4ai_top_n': {'value': 2, 'origin': 'db'},
                        'crawl4ai_max_chars': {'value': 5000, 'origin': 'db'},
                        'crawl4ai_explicit_url_max_chars': {'value': 25000, 'origin': 'db'},
                    },
                )
            }

        view = runtime_settings.get_runtime_section('main_model', fetcher=fetcher)
        self.assertEqual(view.source, 'env')
        self.assertEqual(view.source_reason, 'missing_section')

    def test_runtime_section_for_api_redacts_secrets(self) -> None:
        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                )
            }

        view = runtime_settings.get_runtime_section_for_api('main_model', fetcher=fetcher)
        self.assertEqual(view.payload['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'db'})
        self.assertEqual(view.payload['model']['value'], 'openai/gpt-5.1')

    def test_runtime_status_reports_db_state_and_section_sources(self) -> None:
        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                )
            }

        status = runtime_settings.get_runtime_status(fetcher=fetcher)
        self.assertEqual(status['db_state'], 'db_rows')
        self.assertEqual(status['bootstrap']['database_dsn_source'], 'env')
        self.assertEqual(status['bootstrap']['database_dsn_env_var'], 'FRIDA_MEMORY_DB_DSN')
        self.assertEqual(status['sections']['main_model'], {'source': 'db', 'source_reason': 'db_row'})
        self.assertEqual(status['sections']['services'], {'source': 'env', 'source_reason': 'missing_section'})

    def test_require_secret_configured_raises_explicit_error(self) -> None:
        view = runtime_settings.get_runtime_section('database', fetcher=lambda: {})
        with self.assertRaisesRegex(runtime_settings.RuntimeSettingsSecretRequiredError, 'missing secret config: database.dsn'):
            runtime_settings.require_secret_configured(view, 'dsn')

    def test_get_runtime_secret_value_uses_env_fallback_when_section_is_from_env(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-env-fallback-secret'
        try:
            secret = runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=lambda: {})
        finally:
            config.OR_KEY = original_api_key

        self.assertEqual(secret.value, 'sk-env-fallback-secret')
        self.assertEqual(secret.source, 'env_fallback')
        self.assertEqual(secret.source_reason, 'empty_table')

    def test_get_runtime_secret_value_decrypts_db_secret_when_encrypted_value_is_present(self) -> None:
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value

        def fake_decrypt_runtime_secret_value(value_encrypted: str) -> str:
            self.assertEqual(value_encrypted, 'cipher-main-model')
            return 'sk-db-main-model'

        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openrouter/runtime-main', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'cipher-main-model', 'origin': 'db'},
                    },
                )
            }

        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = fake_decrypt_runtime_secret_value
        try:
            secret = runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=fetcher)
        finally:
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt

        self.assertEqual(secret.value, 'sk-db-main-model')
        self.assertEqual(secret.source, 'db_encrypted')
        self.assertEqual(secret.source_reason, 'db_row')

    def test_get_runtime_secret_value_raises_explicit_error_when_db_secret_is_not_decryptable(self) -> None:
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value

        def fake_decrypt_runtime_secret_value(value_encrypted: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError('bad ciphertext')

        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openrouter/runtime-main', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'cipher-main-model', 'origin': 'db'},
                    },
                )
            }

        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = fake_decrypt_runtime_secret_value
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretResolutionError,
                'failed to decrypt runtime secret main_model.api_key: bad ciphertext',
            ):
                runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=fetcher)
        finally:
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt

    def test_get_runtime_secret_value_raises_explicit_error_when_db_secret_is_marked_set_without_ciphertext(self) -> None:
        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openrouter/runtime-main', 'origin': 'db'},
                        'api_key': {'is_set': True, 'origin': 'db'},
                    },
                )
            }

        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsSecretResolutionError,
            'secret marked as set but no decryptable value is available: main_model.api_key',
        ):
            runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=fetcher)


if __name__ == '__main__':
    unittest.main()
