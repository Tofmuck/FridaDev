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


class RuntimeSettingsAdminPatchNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_normalize_admin_patch_payload_validates_non_secret_types(self) -> None:
        normalized = runtime_settings.normalize_admin_patch_payload(
            'main_model',
            {
                'model': {'value': 'openrouter/next-model'},
                'temperature': {'value': 0.55},
                'top_p': {'value': 0.9},
            },
        )
        self.assertEqual(normalized['model']['value'], 'openrouter/next-model')
        self.assertEqual(normalized['temperature']['value'], 0.55)
        self.assertEqual(normalized['top_p']['value'], 0.9)
        self.assertEqual(normalized['model']['origin'], 'admin_ui')

    def test_normalize_admin_patch_payload_rejects_secret_updates_for_now(self) -> None:
        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsValidationError,
            'ambiguous secret patch payload for main_model.api_key: use replace_value only',
        ):
            runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'api_key': {'value': 'sk-secret'},
                },
            )

    def test_normalize_admin_patch_payload_encrypts_secret_replace_value(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            self.assertEqual(value, 'sk-phase5bis-secret')
            return 'ciphertext-main-model'

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            normalized = runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'api_key': {'replace_value': 'sk-phase5bis-secret'},
                },
            )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

        self.assertEqual(
            normalized,
            {
                'api_key': {
                    'is_secret': True,
                    'is_set': True,
                    'origin': 'admin_ui',
                    'value_encrypted': 'ciphertext-main-model',
                }
            },
        )

    def test_normalize_admin_patch_payload_rejects_secret_patch_without_replace_value(self) -> None:
        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsValidationError,
            'missing replace_value for services.crawl4ai_token',
        ):
            runtime_settings.normalize_admin_patch_payload(
                'services',
                {
                    'crawl4ai_token': {},
                },
            )

    def test_normalize_admin_patch_payload_rejects_secret_patch_when_crypto_key_is_missing(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoKeyMissingError(
                'missing runtime settings crypto key: FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY'
            )

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsValidationError,
                'missing runtime settings crypto key: FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY',
            ):
                runtime_settings.normalize_admin_patch_payload(
                    'embedding',
                    {
                        'token': {'replace_value': 'embed-secret'},
                    },
                )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

    def test_normalize_admin_patch_payload_does_not_echo_secret_value_when_encrypt_fails(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        secret_value = 'sk-should-not-leak-via-encrypt-error'

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError(
                f'crypto engine exploded on {value}'
            )

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            with self.assertRaises(runtime_settings.RuntimeSettingsValidationError) as ctx:
                runtime_settings.normalize_admin_patch_payload(
                    'main_model',
                    {
                        'api_key': {'replace_value': secret_value},
                    },
                )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

        self.assertEqual(str(ctx.exception), 'failed to encrypt secret for main_model.api_key')
        self.assertNotIn(secret_value, str(ctx.exception))

    def test_normalize_admin_patch_payload_accepts_main_model_response_max_tokens(self) -> None:
        normalized = runtime_settings.normalize_admin_patch_payload(
            'main_model',
            {
                'response_max_tokens': {'value': 8192},
            },
        )

        self.assertEqual(
            normalized,
            {
                'response_max_tokens': {
                    'value': 8192,
                    'is_secret': False,
                    'origin': 'admin_ui',
                },
            },
        )

    def test_normalize_admin_patch_payload_rejects_readonly_prompt_field(self) -> None:
        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsValidationError,
            'unknown runtime settings field: main_model.system_prompt',
        ):
            runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'system_prompt': {'value': 'should-not-pass'},
                },
            )


if __name__ == '__main__':
    unittest.main()
