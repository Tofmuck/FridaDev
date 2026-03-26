from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import runtime_db_bootstrap


class RuntimeDbBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _db_database_view(self, *, backend: str = 'postgresql', dsn_is_set: bool = True):
        payload = {
            'backend': {'value': backend, 'origin': 'db'},
            'dsn': {'value_encrypted': 'ciphertext', 'origin': 'db'},
        }
        if not dsn_is_set:
            payload['dsn'] = {'is_set': False, 'origin': 'db'}
        return runtime_settings.RuntimeSectionView(
            section='database',
            payload=runtime_settings.normalize_stored_payload('database', payload),
            source='db',
            source_reason='db_row',
        )

    def test_connect_runtime_database_uses_bootstrap_dsn_for_postgresql_backend(self) -> None:
        observed = {'dsn': None}

        fake_psycopg = types.SimpleNamespace(
            connect=lambda dsn: observed.update({'dsn': dsn}) or object(),
        )
        fake_config = types.SimpleNamespace(
            FRIDA_MEMORY_DB_DSN='postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        fake_runtime_settings = types.SimpleNamespace(
            get_database_settings=lambda: self._db_database_view(backend='postgresql'),
            build_env_seed_bundle=runtime_settings.build_env_seed_bundle,
            RuntimeSettingsSecretRequiredError=runtime_settings.RuntimeSettingsSecretRequiredError,
            require_secret_configured=runtime_settings.require_secret_configured,
        )

        conn = runtime_db_bootstrap.connect_runtime_database(fake_psycopg, fake_config, fake_runtime_settings)

        self.assertIsNotNone(conn)
        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )

    def test_connect_runtime_database_rejects_unsupported_backend(self) -> None:
        fake_psycopg = types.SimpleNamespace(connect=lambda _dsn: object())
        fake_config = types.SimpleNamespace(FRIDA_MEMORY_DB_DSN='postgresql://bootstrap')
        fake_runtime_settings = types.SimpleNamespace(
            get_database_settings=lambda: self._db_database_view(backend='mysql'),
            build_env_seed_bundle=runtime_settings.build_env_seed_bundle,
            RuntimeSettingsSecretRequiredError=runtime_settings.RuntimeSettingsSecretRequiredError,
            require_secret_configured=runtime_settings.require_secret_configured,
        )

        with self.assertRaisesRegex(ValueError, 'unsupported runtime database backend: mysql'):
            runtime_db_bootstrap.connect_runtime_database(fake_psycopg, fake_config, fake_runtime_settings)

    def test_bootstrap_database_dsn_requires_env_fallback_when_db_secret_is_set(self) -> None:
        observed = {'require_secret_configured_called': False}
        fake_config = types.SimpleNamespace(FRIDA_MEMORY_DB_DSN='')

        def fake_require_secret_configured(_view, _field: str) -> None:
            observed['require_secret_configured_called'] = True

        fake_runtime_settings = types.SimpleNamespace(
            get_database_settings=lambda: self._db_database_view(backend='postgresql', dsn_is_set=True),
            build_env_seed_bundle=runtime_settings.build_env_seed_bundle,
            RuntimeSettingsSecretRequiredError=runtime_settings.RuntimeSettingsSecretRequiredError,
            require_secret_configured=fake_require_secret_configured,
        )

        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsSecretRequiredError,
            'runtime secret decryption is not available',
        ):
            runtime_db_bootstrap.bootstrap_database_dsn(fake_config, fake_runtime_settings)

        self.assertFalse(observed['require_secret_configured_called'])


if __name__ == '__main__':
    unittest.main()
