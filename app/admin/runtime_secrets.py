from __future__ import annotations

import config
from typing import Any, Dict


RUNTIME_SETTINGS_CRYPTO_ENV_VAR = 'FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY'


class RuntimeSettingsCryptoKeyMissingError(RuntimeError):
    pass


class RuntimeSettingsCryptoEngineError(RuntimeError):
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


def _pgcrypto_scalar(query: str, params: tuple[Any, ...]) -> str:
    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise RuntimeSettingsCryptoEngineError(f'psycopg unavailable: {exc}') from exc

    try:
        with psycopg.connect(config.FRIDA_MEMORY_DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
    except Exception as exc:
        raise RuntimeSettingsCryptoEngineError(str(exc)) from exc

    if not row or row[0] in (None, ''):
        raise RuntimeSettingsCryptoEngineError('pgcrypto returned no value')
    return str(row[0])


def encrypt_runtime_secret_value(value: str) -> str:
    key = require_runtime_settings_crypto_key()
    return _pgcrypto_scalar(
        '''
        SELECT armor(
            pgp_sym_encrypt(
                %s::text,
                %s::text,
                'cipher-algo=aes256,compress-algo=0'
            )
        )
        ''',
        (str(value), key),
    )


def decrypt_runtime_secret_value(value_encrypted: str) -> str:
    key = require_runtime_settings_crypto_key()
    return _pgcrypto_scalar(
        '''
        SELECT pgp_sym_decrypt(
            dearmor(%s::text),
            %s::text
        )
        ''',
        (str(value_encrypted), key),
    )
