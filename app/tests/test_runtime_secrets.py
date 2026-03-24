from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_secrets
import config


class RuntimeSecretsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_crypto_key = config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY
        self._original_psycopg = sys.modules.get('psycopg')

    def tearDown(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = self._original_crypto_key
        if self._original_psycopg is None:
            sys.modules.pop('psycopg', None)
        else:
            sys.modules['psycopg'] = self._original_psycopg

    def test_has_runtime_settings_crypto_key_is_false_when_missing(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = ''
        self.assertFalse(runtime_secrets.has_runtime_settings_crypto_key())

    def test_has_runtime_settings_crypto_key_is_true_when_present(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = ' phase5bis-key '
        self.assertTrue(runtime_secrets.has_runtime_settings_crypto_key())

    def test_require_runtime_settings_crypto_key_returns_stripped_value(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = ' phase5bis-key '
        self.assertEqual(runtime_secrets.require_runtime_settings_crypto_key(), 'phase5bis-key')

    def test_require_runtime_settings_crypto_key_raises_explicit_error_when_missing(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = ''
        with self.assertRaisesRegex(
            runtime_secrets.RuntimeSettingsCryptoKeyMissingError,
            'missing runtime settings crypto key: FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY',
        ):
            runtime_secrets.require_runtime_settings_crypto_key()

    def test_describe_runtime_secrets_policy_does_not_expose_key_value(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = 'phase5bis-key'
        policy = runtime_secrets.describe_runtime_secrets_policy()
        self.assertEqual(
            policy,
            {
                'crypto_env_var': 'FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY',
                'crypto_key_present': True,
                'crypto_key_source': 'external_env',
                'secret_storage': 'db_encrypted',
                'frontend_exposure': 'masked_only',
            },
        )
        self.assertNotIn('phase5bis-key', repr(policy))

    def test_encrypt_runtime_secret_value_uses_pgcrypto_with_external_key(self) -> None:
        observed = {'dsn': None, 'query': None, 'params': None}

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['query'] = query
                observed['params'] = params

            def fetchone(self):
                return ('-----BEGIN PGP MESSAGE-----ciphertext',)

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return FakeConnection()

        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = 'phase5bis-key'
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(connect=fake_connect)
        try:
            encrypted = runtime_secrets.encrypt_runtime_secret_value('plain-secret')
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertEqual(encrypted, '-----BEGIN PGP MESSAGE-----ciphertext')
        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertIn('armor', observed['query'])
        self.assertIn('pgp_sym_encrypt', observed['query'])
        self.assertEqual(observed['params'], ('plain-secret', 'phase5bis-key'))

    def test_decrypt_runtime_secret_value_uses_pgcrypto_with_external_key(self) -> None:
        observed = {'query': None, 'params': None}

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['query'] = query
                observed['params'] = params

            def fetchone(self):
                return ('plain-secret',)

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

        sys.modules['psycopg'] = types.SimpleNamespace(connect=lambda dsn: FakeConnection())
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = 'phase5bis-key'

        decrypted = runtime_secrets.decrypt_runtime_secret_value('-----BEGIN PGP MESSAGE-----ciphertext')

        self.assertEqual(decrypted, 'plain-secret')
        self.assertIn('pgp_sym_decrypt', observed['query'])
        self.assertIn('dearmor', observed['query'])
        self.assertEqual(
            observed['params'],
            ('-----BEGIN PGP MESSAGE-----ciphertext', 'phase5bis-key'),
        )

    def test_encrypt_runtime_secret_value_requires_crypto_key(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = ''
        with self.assertRaisesRegex(
            runtime_secrets.RuntimeSettingsCryptoKeyMissingError,
            'missing runtime settings crypto key: FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY',
        ):
            runtime_secrets.encrypt_runtime_secret_value('plain-secret')


if __name__ == '__main__':
    unittest.main()
