from __future__ import annotations

import sys
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

    def tearDown(self) -> None:
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = self._original_crypto_key

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


if __name__ == '__main__':
    unittest.main()
