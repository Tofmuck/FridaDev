from __future__ import annotations

from typing import Any


def runtime_database_view(runtime_settings_module: Any):
    return runtime_settings_module.get_database_settings()


def runtime_database_backend(runtime_settings_module: Any) -> str:
    view = runtime_database_view(runtime_settings_module)
    payload = view.payload.get('backend') or {}
    if 'value' in payload:
        return str(payload['value'])

    env_bundle = runtime_settings_module.build_env_seed_bundle('database')
    fallback = env_bundle.payload.get('backend') or {}
    if 'value' in fallback:
        return str(fallback['value'])

    raise KeyError('missing database runtime value: backend')


def bootstrap_database_dsn(config_module: Any, runtime_settings_module: Any) -> str:
    env_dsn = str(config_module.FRIDA_MEMORY_DB_DSN or '').strip()
    if env_dsn:
        return env_dsn

    view = runtime_database_view(runtime_settings_module)
    payload = view.payload.get('dsn') or {}
    if bool(payload.get('is_set')):
        raise runtime_settings_module.RuntimeSettingsSecretRequiredError(
            'database.dsn is set in runtime settings but runtime secret decryption is not available; '
            'FRIDA_MEMORY_DB_DSN env fallback is required during the transition'
        )

    runtime_settings_module.require_secret_configured(view, 'dsn')
    raise AssertionError('unreachable')


def connect_runtime_database(
    psycopg_module: Any,
    config_module: Any,
    runtime_settings_module: Any,
):
    backend = runtime_database_backend(runtime_settings_module)
    if backend != 'postgresql':
        raise ValueError(f'unsupported runtime database backend: {backend}')
    return psycopg_module.connect(bootstrap_database_dsn(config_module, runtime_settings_module))
