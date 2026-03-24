from __future__ import annotations

from typing import Any, Dict

import config


RUNTIME_SETTINGS_CRYPTO_ENV_VAR = 'FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY'


class RuntimeSettingsCryptoKeyMissingError(RuntimeError):
    pass


def has_runtime_settings_crypto_key() -> bool:
    return bool(str(config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY or '').strip())


def require_runtime_settings_crypto_key() -> str:
    key = str(config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY or '').strip()
    if key:
        return key

    raise RuntimeSettingsCryptoKeyMissingError(
        f'missing runtime settings crypto key: {RUNTIME_SETTINGS_CRYPTO_ENV_VAR}'
    )


def describe_runtime_secrets_policy() -> Dict[str, Any]:
    return {
        'crypto_env_var': RUNTIME_SETTINGS_CRYPTO_ENV_VAR,
        'crypto_key_present': has_runtime_settings_crypto_key(),
        'crypto_key_source': 'external_env',
        'secret_storage': 'db_encrypted',
        'frontend_exposure': 'masked_only',
    }
