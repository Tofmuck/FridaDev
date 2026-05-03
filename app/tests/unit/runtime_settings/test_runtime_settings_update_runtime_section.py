from __future__ import annotations

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


class RuntimeSettingsUpdateRuntimeSectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_or_base = config.OR_BASE
        self._original_or_key = config.OR_KEY
        self._original_or_referer = config.OR_REFERER
        config.OR_BASE = 'https://openrouter.test/api/v1'
        config.OR_KEY = 'sk-test-runtime-settings-update'
        config.OR_REFERER = 'https://fridadev.test'
        runtime_settings.invalidate_runtime_settings_cache()

    def tearDown(self) -> None:
        config.OR_BASE = self._original_or_base
        config.OR_KEY = self._original_or_key
        config.OR_REFERER = self._original_or_referer
        runtime_settings.invalidate_runtime_settings_cache()

    def test_update_runtime_section_uses_external_bootstrap_dsn_and_returns_redacted_payload(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchone(self):
                return None

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

        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            view = runtime_settings.update_runtime_section(
                'main_model',
                {
                    'model': {'value': 'openrouter/runtime-main-model'},
                    'temperature': {'value': 0.25},
                },
                updated_by='phase5-test',
                fetcher=lambda: {},
            )
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(view.section, 'main_model')
        self.assertEqual(view.source, 'db')
        self.assertEqual(view.payload['model']['value'], 'openrouter/runtime-main-model')
        self.assertEqual(view.payload['temperature']['value'], 0.25)
        self.assertEqual(view.payload['api_key']['is_secret'], True)
        self.assertIn('INSERT INTO runtime_settings', observed['queries'][1])
        self.assertIn('INSERT INTO runtime_settings_history', observed['queries'][2])

    def test_update_runtime_section_encrypts_secret_patch_without_persisting_clear_text(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __init__(self):
                self.last_query = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                self.last_query = query
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchone(self):
                if self.last_query and 'pgp_sym_encrypt' in self.last_query:
                    return ('ciphertext-main-model',)
                if self.last_query and 'pgp_sym_decrypt' in self.last_query:
                    return ('sk-phase5bis-secret',)
                if self.last_query and 'SELECT payload' in self.last_query:
                    return None
                return None

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

        original_crypto_key = config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = 'phase5bis-key'
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            view = runtime_settings.update_runtime_section(
                'main_model',
                {
                    'api_key': {'replace_value': 'sk-phase5bis-secret'},
                },
                updated_by='phase5bis-test',
                fetcher=lambda: {},
            )
        finally:
            config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = original_crypto_key
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        payload_after = next(
            params[2]
            for params in observed['params']
            if len(params) == 3 and params[0] == 'main_model' and params[1] == 'phase5bis-test'
        )
        history_after = next(
            params[3]
            for params in observed['params']
            if len(params) == 4 and params[0] == 'main_model' and params[1] == 'phase5bis-test'
        )
        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(view.payload['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'})
        self.assertIn('ciphertext-main-model', payload_after)
        self.assertIn('ciphertext-main-model', history_after)
        self.assertNotIn('sk-phase5bis-secret', payload_after)
        self.assertNotIn('sk-phase5bis-secret', history_after)

    def test_update_runtime_section_updates_main_model_response_max_tokens(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchone(self):
                return None

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

        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            view = runtime_settings.update_runtime_section(
                'main_model',
                {
                    'response_max_tokens': {'value': 8192},
                },
                updated_by='phase12-test',
                fetcher=lambda: {},
            )
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(view.payload['response_max_tokens']['value'], 8192)
        self.assertEqual(view.payload['response_max_tokens']['origin'], 'admin_ui')
        payload_after = observed['params'][1][2]
        history_after = observed['params'][2][3]
        self.assertIn('"response_max_tokens": {"value": 8192, "is_secret": false, "origin": "admin_ui"}', payload_after)
        self.assertIn('"response_max_tokens": {"value": 8192, "is_secret": false, "origin": "admin_ui"}', history_after)

    def test_update_runtime_section_rejects_invalid_candidate_before_db_write(self) -> None:
        observed = {
            'connect_calls': 0,
            'cache_invalidations': 0,
        }

        class FakeUndefinedTable(Exception):
            pass

        def fail_if_connect_called(_dsn):
            observed['connect_calls'] += 1
            raise AssertionError('psycopg.connect must not be called for invalid runtime settings')

        def fake_invalidate_cache():
            observed['cache_invalidations'] += 1

        original_psycopg = sys.modules.get('psycopg')
        original_invalidate = runtime_settings.invalidate_runtime_settings_cache
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fail_if_connect_called,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        runtime_settings.invalidate_runtime_settings_cache = fake_invalidate_cache
        try:
            with self.assertRaises(runtime_settings.RuntimeSettingsValidationError) as ctx:
                runtime_settings.update_runtime_section(
                    'main_model',
                    {
                        'temperature': {'value': 3.0},
                    },
                    updated_by='lot2-invalid-test',
                    fetcher=lambda: {},
                )
        finally:
            runtime_settings.invalidate_runtime_settings_cache = original_invalidate
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg

        self.assertIn('runtime settings validation failed for main_model', str(ctx.exception))
        self.assertIn('temperature=3.0', str(ctx.exception))
        self.assertEqual(observed['connect_calls'], 0)
        self.assertEqual(observed['cache_invalidations'], 0)

    def test_update_runtime_section_rejects_invalid_identity_governance_before_db_write(self) -> None:
        observed = {
            'connect_calls': 0,
            'cache_invalidations': 0,
        }

        class FakeUndefinedTable(Exception):
            pass

        def fail_if_connect_called(_dsn):
            observed['connect_calls'] += 1
            raise AssertionError('psycopg.connect must not be called for invalid identity governance settings')

        def fake_invalidate_cache():
            observed['cache_invalidations'] += 1

        original_psycopg = sys.modules.get('psycopg')
        original_invalidate = runtime_settings.invalidate_runtime_settings_cache
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fail_if_connect_called,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        runtime_settings.invalidate_runtime_settings_cache = fake_invalidate_cache
        try:
            with self.assertRaises(runtime_settings.RuntimeSettingsValidationError) as ctx:
                runtime_settings.update_runtime_section(
                    'identity_governance',
                    {
                        'IDENTITY_MIN_CONFIDENCE': {'value': 2.0},
                    },
                    updated_by='lot2-invalid-identity-test',
                    fetcher=lambda: {},
                )
        finally:
            runtime_settings.invalidate_runtime_settings_cache = original_invalidate
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg

        self.assertIn('runtime settings validation failed for identity_governance', str(ctx.exception))
        self.assertIn('IDENTITY_MIN_CONFIDENCE=2.0', str(ctx.exception))
        self.assertEqual(observed['connect_calls'], 0)
        self.assertEqual(observed['cache_invalidations'], 0)


if __name__ == '__main__':
    unittest.main()
