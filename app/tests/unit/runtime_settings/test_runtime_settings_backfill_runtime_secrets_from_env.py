from __future__ import annotations

import json
import sys
import types
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


class RuntimeSettingsBackfillRuntimeSecretsFromEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_backfill_runtime_secrets_from_env_encrypts_env_secrets_without_persisting_clear_text(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }
        cipher_by_value = {
            'sk-main-env-secret': 'cipher-main-model',
            'embed-env-secret': 'cipher-embedding',
            'crawl-env-secret': 'cipher-services',
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db': 'cipher-database',
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return []

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return FakeConnection()

        def fake_encrypt(value: str) -> str:
            return cipher_by_value[value]

        original_or_key = config.OR_KEY
        original_embed_token = config.EMBED_TOKEN
        original_crawl4ai_token = config.CRAWL4AI_TOKEN
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_psycopg = sys.modules.get('psycopg')
        config.OR_KEY = 'sk-main-env-secret'
        config.EMBED_TOKEN = 'embed-env-secret'
        config.CRAWL4AI_TOKEN = 'crawl-env-secret'
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            result = runtime_settings.backfill_runtime_secrets_from_env(updated_by='phase5bis-backfill-test')
        finally:
            config.OR_KEY = original_or_key
            config.EMBED_TOKEN = original_embed_token
            config.CRAWL4AI_TOKEN = original_crawl4ai_token
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(
            result,
            {
                'updated_fields': (
                    'main_model.api_key',
                    'embedding.token',
                    'services.crawl4ai_token',
                    'database.dsn',
                ),
                'updated_sections': ('database', 'embedding', 'main_model', 'services'),
            },
        )

        serialized_params = '\n'.join(
            '' if params is None else '|'.join(str(part) for part in params)
            for params in observed['params']
        )
        self.assertIn('cipher-main-model', serialized_params)
        self.assertIn('cipher-embedding', serialized_params)
        self.assertIn('cipher-services', serialized_params)
        self.assertIn('cipher-database', serialized_params)
        self.assertNotIn('sk-main-env-secret', serialized_params)
        self.assertNotIn('embed-env-secret', serialized_params)
        self.assertNotIn('crawl-env-secret', serialized_params)
        self.assertNotIn('bootstrap-pass', serialized_params)

        runtime_payloads = [
            json.loads(params[2])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings (section' in query
        ]
        history_after_payloads = [
            json.loads(params[3])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings_history' in query
        ]
        self.assertEqual(len(runtime_payloads), 4)
        self.assertEqual(len(history_after_payloads), 4)
        self.assertEqual(runtime_payloads[0]['api_key']['value_encrypted'], 'cipher-main-model')
        self.assertEqual(runtime_payloads[1]['token']['value_encrypted'], 'cipher-embedding')
        self.assertEqual(runtime_payloads[2]['crawl4ai_token']['value_encrypted'], 'cipher-services')
        self.assertEqual(runtime_payloads[3]['dsn']['value_encrypted'], 'cipher-database')
        for payload in runtime_payloads + history_after_payloads:
            rendered = json.dumps(payload)
            self.assertNotIn('sk-main-env-secret', rendered)
            self.assertNotIn('embed-env-secret', rendered)
            self.assertNotIn('crawl-env-secret', rendered)
            self.assertNotIn('bootstrap-pass', rendered)

    def test_backfill_runtime_secrets_from_env_does_not_overwrite_existing_encrypted_values(self) -> None:
        observed = {
            'queries': [],
            'params': [],
            'encrypted_inputs': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return [
                    (
                        'main_model',
                        {
                            'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                            'model': {'value': 'openrouter/main-model', 'origin': 'db'},
                            'api_key': {
                                'is_secret': True,
                                'is_set': True,
                                'origin': 'admin_ui',
                                'value_encrypted': 'cipher-existing-main-model',
                            },
                        },
                    ),
                ]

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        def fake_connect(_dsn):
            return FakeConnection()

        def fake_encrypt(value: str) -> str:
            observed['encrypted_inputs'].append(value)
            return f'cipher::{len(observed["encrypted_inputs"])}'

        original_or_key = config.OR_KEY
        original_embed_token = config.EMBED_TOKEN
        original_crawl4ai_token = config.CRAWL4AI_TOKEN
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_psycopg = sys.modules.get('psycopg')
        config.OR_KEY = 'sk-main-env-secret'
        config.EMBED_TOKEN = ''
        config.CRAWL4AI_TOKEN = ''
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            result = runtime_settings.backfill_runtime_secrets_from_env(updated_by='phase5bis-reseed-test')
        finally:
            config.OR_KEY = original_or_key
            config.EMBED_TOKEN = original_embed_token
            config.CRAWL4AI_TOKEN = original_crawl4ai_token
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertNotIn('main_model.api_key', result['updated_fields'])
        self.assertEqual(
            result,
            {
                'updated_fields': ('database.dsn',),
                'updated_sections': ('database',),
            },
        )
        self.assertNotIn('sk-main-env-secret', observed['encrypted_inputs'])


if __name__ == '__main__':
    unittest.main()
