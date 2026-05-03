from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import config
from admin import runtime_secrets, runtime_settings_api_view, runtime_settings_repo, runtime_settings_validation
from admin.runtime_settings_spec import (
    FieldSpec,
    SECRET_V1_FIELDS,
    SECTION_NAMES,
    SECTION_SPECS,
    SectionSpec,
    describe_section,
    get_field_spec,
    get_section_spec,
    list_secret_v1_fields,
    list_sections,
)
from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.inputs import recent_window_input as canonical_recent_window_input

# Phase 3 internal split plan (incremental, compatibility-first):
# 1) spec/schema/catalogue -> admin.runtime_settings_spec (this tranche)
# 2) DB + seed + backfill -> admin.runtime_settings_repo (this tranche)
# 3) runtime section validation -> admin.runtime_settings_validation (this tranche)
# 4) admin API view assembly -> admin.runtime_settings_api_view (this tranche)
# 5) runtime section/secret resolution -> future runtime service module
# runtime_settings.py remains the stable public facade during transition.


@dataclass(frozen=True)
class SectionSeedBundle:
    section: str
    payload: dict[str, dict[str, Any]]
    secret_values: dict[str, str]


@dataclass(frozen=True)
class RuntimeSettingsSnapshot:
    rows: dict[str, dict[str, dict[str, Any]]]
    db_state: str


@dataclass(frozen=True)
class RuntimeSectionView:
    section: str
    payload: dict[str, dict[str, Any]]
    source: str
    source_reason: str


@dataclass(frozen=True)
class RuntimeSecretValue:
    section: str
    field: str
    value: str
    source: str
    source_reason: str


class RuntimeSettingsDbUnavailableError(RuntimeError):
    pass


class RuntimeSettingsSecretRequiredError(RuntimeError):
    pass


class RuntimeSettingsSecretResolutionError(RuntimeError):
    pass


class RuntimeSettingsValidationError(ValueError):
    pass


_SNAPSHOT_CACHE: RuntimeSettingsSnapshot | None = None
RUNTIME_SETTINGS_SQL_PATH = Path(__file__).resolve().parent / 'sql' / 'runtime_settings_v1.sql'


def normalize_stored_payload(
    section: str,
    payload: Mapping[str, Any],
    *,
    default_origin: str = 'manual_sql',
) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise TypeError('payload must be a mapping')

    normalized: dict[str, dict[str, Any]] = {}
    for field_name, raw_value in payload.items():
        spec = get_field_spec(section, field_name)
        if not isinstance(raw_value, Mapping):
            raise TypeError(f'field payload must be a mapping: {section}.{field_name}')

        origin = str(raw_value.get('origin') or default_origin)

        if spec.is_secret:
            if 'value' in raw_value:
                raise ValueError(f'secret field does not accept plain value: {section}.{field_name}')

            encrypted_value = raw_value.get('value_encrypted')
            is_set = bool(raw_value.get('is_set') or encrypted_value)
            field_payload: dict[str, Any] = {
                'is_secret': True,
                'is_set': is_set,
                'origin': origin,
            }
            if encrypted_value not in (None, ''):
                field_payload['value_encrypted'] = encrypted_value
        else:
            if 'value_encrypted' in raw_value:
                raise ValueError(f'non-secret field does not accept encrypted value: {section}.{field_name}')
            if 'value' not in raw_value:
                raise ValueError(f'non-secret field requires value: {section}.{field_name}')
            field_payload = {
                'value': raw_value.get('value'),
                'is_secret': False,
                'origin': origin,
            }

        normalized[str(field_name)] = field_payload

    return normalized


def redact_payload_for_api(section: str, payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return runtime_settings_api_view.redact_payload_for_api(
        section,
        payload,
        normalize_stored_payload=normalize_stored_payload,
    )


def describe_secret_sources(section: str, payload: Mapping[str, Any]) -> dict[str, str]:
    return runtime_settings_api_view.describe_secret_sources(
        section,
        payload,
        normalize_stored_payload=normalize_stored_payload,
    )


def _seed_value(section: str, field: str) -> Any:
    values: dict[tuple[str, str], Any] = {
        ('main_model', 'base_url'): config.OR_BASE,
        ('main_model', 'model'): config.OR_MODEL,
        ('main_model', 'api_key'): config.OR_KEY,
        ('main_model', 'referer'): config.OR_REFERER,
        ('main_model', 'referer_llm'): config.OR_REFERER_LLM,
        ('main_model', 'referer_arbiter'): config.OR_REFERER_ARBITER,
        ('main_model', 'referer_identity_extractor'): config.OR_REFERER_IDENTITY_EXTRACTOR,
        ('main_model', 'referer_resumer'): config.OR_REFERER_RESUMER,
        ('main_model', 'referer_stimmung_agent'): config.OR_REFERER_STIMMUNG_AGENT,
        ('main_model', 'referer_validation_agent'): config.OR_REFERER_VALIDATION_AGENT,
        ('main_model', 'app_name'): config.OR_TITLE_BASE,
        ('main_model', 'title_llm'): config.OR_TITLE_LLM,
        ('main_model', 'title_arbiter'): config.OR_TITLE_ARBITER,
        ('main_model', 'title_identity_extractor'): config.OR_TITLE_IDENTITY_EXTRACTOR,
        ('main_model', 'title_resumer'): config.OR_TITLE_RESUMER,
        ('main_model', 'title_stimmung_agent'): config.OR_TITLE_STIMMUNG_AGENT,
        ('main_model', 'title_validation_agent'): config.OR_TITLE_VALIDATION_AGENT,
        ('main_model', 'temperature'): 0.4,
        ('main_model', 'top_p'): 1.0,
        ('main_model', 'response_max_tokens'): 8192,
        ('arbiter_model', 'model'): config.ARBITER_MODEL,
        ('arbiter_model', 'temperature'): 0.0,
        ('arbiter_model', 'top_p'): 1.0,
        ('arbiter_model', 'timeout_s'): config.ARBITER_TIMEOUT_S,
        ('summary_model', 'model'): config.SUMMARY_MODEL,
        ('summary_model', 'temperature'): 0.3,
        ('summary_model', 'top_p'): 1.0,
        ('embedding', 'endpoint'): config.EMBED_BASE_URL,
        ('embedding', 'model'): 'intfloat/multilingual-e5-small',
        ('embedding', 'token'): config.EMBED_TOKEN,
        ('embedding', 'dimensions'): config.EMBED_DIM,
        ('embedding', 'top_k'): config.MEMORY_TOP_K,
        ('database', 'backend'): 'postgresql',
        ('services', 'searxng_url'): config.SEARXNG_URL,
        ('services', 'searxng_results'): config.SEARXNG_RESULTS,
        ('services', 'crawl4ai_url'): config.CRAWL4AI_URL,
        ('services', 'crawl4ai_token'): config.CRAWL4AI_TOKEN,
        ('services', 'crawl4ai_top_n'): config.CRAWL4AI_TOP_N,
        ('services', 'crawl4ai_max_chars'): config.CRAWL4AI_MAX_CHARS,
        ('services', 'crawl4ai_explicit_url_max_chars'): config.CRAWL4AI_EXPLICIT_URL_MAX_CHARS,
        ('resources', 'llm_identity_path'): config.FRIDA_LLM_IDENTITY_PATH,
        ('resources', 'user_identity_path'): config.FRIDA_USER_IDENTITY_PATH,
        ('identity_governance', 'IDENTITY_MIN_CONFIDENCE'): config.IDENTITY_MIN_CONFIDENCE,
        ('identity_governance', 'IDENTITY_DEFER_MIN_CONFIDENCE'): config.IDENTITY_DEFER_MIN_CONFIDENCE,
        (
            'identity_governance',
            'IDENTITY_MIN_RECURRENCE_FOR_DURABLE',
        ): config.IDENTITY_MIN_RECURRENCE_FOR_DURABLE,
        ('identity_governance', 'IDENTITY_RECURRENCE_WINDOW_DAYS'): config.IDENTITY_RECURRENCE_WINDOW_DAYS,
        (
            'identity_governance',
            'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS',
        ): config.IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS,
        (
            'identity_governance',
            'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
        ): config.IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS,
        ('identity_governance', 'CONTEXT_HINTS_MAX_ITEMS'): config.CONTEXT_HINTS_MAX_ITEMS,
        ('identity_governance', 'CONTEXT_HINTS_MAX_TOKENS'): config.CONTEXT_HINTS_MAX_TOKENS,
        ('identity_governance', 'CONTEXT_HINTS_MAX_AGE_DAYS'): config.CONTEXT_HINTS_MAX_AGE_DAYS,
        ('identity_governance', 'CONTEXT_HINTS_MIN_CONFIDENCE'): config.CONTEXT_HINTS_MIN_CONFIDENCE,
    }
    spec = get_field_spec(section, field)
    return values.get((section, field), spec.seed_default)


def _non_secret_seed_origin(field: FieldSpec) -> str:
    if field.seed_from_env:
        return 'env_seed'
    return 'seed_default'


def build_env_seed_bundle(section: str) -> SectionSeedBundle:
    spec = get_section_spec(section)
    payload: dict[str, dict[str, Any]] = {}
    secret_values: dict[str, str] = {}

    for field in spec.fields:
        value = _seed_value(section, field.key)

        if field.is_secret:
            is_set = False
            if field.seed_from_env and value not in (None, ''):
                secret_values[field.key] = str(value)
                is_set = True

            payload[field.key] = {
                'is_secret': True,
                'is_set': is_set,
                'origin': 'env_seed',
            }
            continue

        payload[field.key] = {
            'value': value,
            'is_secret': False,
            'origin': _non_secret_seed_origin(field),
        }

    return SectionSeedBundle(section=section, payload=payload, secret_values=secret_values)


def build_db_seed_bundle(section: str) -> SectionSeedBundle:
    env_bundle = build_env_seed_bundle(section)
    payload = normalize_stored_payload(section, env_bundle.payload, default_origin='env_seed')
    seeded_payload: dict[str, dict[str, Any]] = {}

    for field_name, field_payload in payload.items():
        spec = get_field_spec(section, field_name)
        next_field_payload = dict(field_payload)
        if not spec.is_secret:
            next_field_payload['origin'] = 'db_seed'
        seeded_payload[field_name] = next_field_payload

    return SectionSeedBundle(
        section=env_bundle.section,
        payload=seeded_payload,
        secret_values=env_bundle.secret_values,
    )


def get_unseeded_sections(existing_sections: Iterable[str]) -> tuple[str, ...]:
    existing = {str(section) for section in existing_sections}
    return tuple(section for section in SECTION_NAMES if section not in existing)


def build_env_seed_plan(existing_sections: Iterable[str] = ()) -> tuple[SectionSeedBundle, ...]:
    return tuple(build_env_seed_bundle(section) for section in get_unseeded_sections(existing_sections))


def build_db_seed_plan(existing_sections: Iterable[str] = ()) -> tuple[SectionSeedBundle, ...]:
    return tuple(build_db_seed_bundle(section) for section in get_unseeded_sections(existing_sections))


def _merge_missing_db_seed_fields(
    section: str,
    current_payload: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    normalized_current = normalize_stored_payload(section, current_payload, default_origin='db')
    seeded_payload = build_db_seed_bundle(section).payload
    merged_payload = dict(normalized_current)
    added_fields: list[str] = []

    for field_name, field_payload in seeded_payload.items():
        spec = get_field_spec(section, field_name)
        if spec.is_secret or field_name in merged_payload:
            continue
        merged_payload[field_name] = dict(field_payload)
        added_fields.append(field_name)

    return merged_payload, tuple(added_fields)


def _backfill_env_secret_value(section: str, field: str) -> str:
    if section == 'database' and field == 'dsn':
        return str(config.FRIDA_MEMORY_DB_DSN or '').strip()

    value = _seed_value(section, field)
    if value in (None, ''):
        return ''
    return str(value).strip()


def _should_backfill_secret_field(field_payload: Mapping[str, Any]) -> bool:
    encrypted_value = str(field_payload.get('value_encrypted') or '').strip()
    if encrypted_value:
        return False

    is_set = bool(field_payload.get('is_set'))
    origin = str(field_payload.get('origin') or '').strip()
    if is_set and origin not in {'', 'env_seed'}:
        return False

    return True


def backfill_runtime_secrets_from_env(*, updated_by: str = 'runtime_secret_backfill') -> dict[str, Any]:
    return runtime_settings_repo.backfill_runtime_secrets_from_env(
        dsn=config.FRIDA_MEMORY_DB_DSN,
        updated_by=updated_by,
        secret_v1_fields=SECRET_V1_FIELDS,
        normalize_stored_payload=normalize_stored_payload,
        build_env_seed_bundle=build_env_seed_bundle,
        backfill_env_secret_value=_backfill_env_secret_value,
        should_backfill_secret_field=_should_backfill_secret_field,
        encrypt_runtime_secret_value=runtime_secrets.encrypt_runtime_secret_value,
        invalidate_runtime_settings_cache=invalidate_runtime_settings_cache,
        db_unavailable_error_cls=RuntimeSettingsDbUnavailableError,
    )


def init_runtime_settings_db() -> dict[str, Any]:
    return runtime_settings_repo.init_runtime_settings_db(
        dsn=config.FRIDA_MEMORY_DB_DSN,
        sql_path=RUNTIME_SETTINGS_SQL_PATH,
        db_unavailable_error_cls=RuntimeSettingsDbUnavailableError,
    )


def bootstrap_runtime_settings_from_env(*, updated_by: str = 'runtime_settings_bootstrap') -> dict[str, Any]:
    return runtime_settings_repo.bootstrap_runtime_settings_from_env(
        dsn=config.FRIDA_MEMORY_DB_DSN,
        updated_by=updated_by,
        build_db_seed_plan=build_db_seed_plan,
        normalize_stored_payload=normalize_stored_payload,
        merge_missing_db_seed_fields=_merge_missing_db_seed_fields,
        invalidate_runtime_settings_cache=invalidate_runtime_settings_cache,
        db_unavailable_error_cls=RuntimeSettingsDbUnavailableError,
    )


def invalidate_runtime_settings_cache() -> None:
    global _SNAPSHOT_CACHE
    _SNAPSHOT_CACHE = None


def _default_db_fetch_all_sections() -> dict[str, dict[str, dict[str, Any]]]:
    return runtime_settings_repo.fetch_all_sections(
        dsn=config.FRIDA_MEMORY_DB_DSN,
        normalize_stored_payload=normalize_stored_payload,
        db_unavailable_error_cls=RuntimeSettingsDbUnavailableError,
    )


def _load_snapshot(
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSettingsSnapshot:
    global _SNAPSHOT_CACHE

    use_cache = fetcher is None
    if use_cache and _SNAPSHOT_CACHE is not None:
        return _SNAPSHOT_CACHE

    active_fetcher = fetcher or _default_db_fetch_all_sections
    try:
        rows = active_fetcher()
    except RuntimeSettingsDbUnavailableError:
        snapshot = RuntimeSettingsSnapshot(rows={}, db_state='db_unavailable')
    else:
        snapshot = RuntimeSettingsSnapshot(
            rows=rows,
            db_state='db_rows' if rows else 'empty_table',
        )

    if use_cache:
        _SNAPSHOT_CACHE = snapshot
    return snapshot


def _env_payload_for_runtime(section: str) -> dict[str, dict[str, Any]]:
    return build_env_seed_bundle(section).payload


def get_runtime_section(
    section: str,
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSectionView:
    get_section_spec(section)
    snapshot = _load_snapshot(fetcher=fetcher)

    payload = snapshot.rows.get(section)
    if payload is not None:
        return RuntimeSectionView(
            section=section,
            payload=payload,
            source='db',
            source_reason='db_row',
        )

    source_reason = 'missing_section' if snapshot.db_state == 'db_rows' else snapshot.db_state
    return RuntimeSectionView(
        section=section,
        payload=_env_payload_for_runtime(section),
        source='env',
        source_reason=source_reason,
    )


def get_runtime_section_for_api(
    section: str,
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSectionView:
    view = get_runtime_section(section, fetcher=fetcher)
    return RuntimeSectionView(
        section=view.section,
        payload=redact_payload_for_api(section, view.payload),
        source=view.source,
        source_reason=view.source_reason,
    )


def get_section_readonly_info(section: str) -> dict[str, dict[str, Any]]:
    return runtime_settings_api_view.get_section_readonly_info(section)


def get_main_model_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('main_model', fetcher=fetcher)


def get_arbiter_model_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('arbiter_model', fetcher=fetcher)


def get_summary_model_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('summary_model', fetcher=fetcher)


def get_embedding_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('embedding', fetcher=fetcher)


def get_stimmung_agent_model_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('stimmung_agent_model', fetcher=fetcher)


def get_validation_agent_model_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('validation_agent_model', fetcher=fetcher)


def get_database_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('database', fetcher=fetcher)


def get_services_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('services', fetcher=fetcher)


def get_resources_settings(*, fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('resources', fetcher=fetcher)


def get_identity_governance_settings(
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSectionView:
    return get_runtime_section('identity_governance', fetcher=fetcher)


def get_runtime_status(
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    snapshot = _load_snapshot(fetcher=fetcher)
    sections: dict[str, dict[str, str]] = {}
    for section in SECTION_NAMES:
        if section in snapshot.rows:
            sections[section] = {
                'source': 'db',
                'source_reason': 'db_row',
            }
        else:
            source_reason = 'missing_section' if snapshot.db_state == 'db_rows' else snapshot.db_state
            sections[section] = {
                'source': 'env',
                'source_reason': source_reason,
            }

    return {
        'db_state': snapshot.db_state,
        'bootstrap': {
            'database_dsn_source': 'env',
            'database_dsn_env_var': 'FRIDA_MEMORY_DB_DSN',
            'database_dsn_mode': 'external_bootstrap',
        },
        'sections': sections,
    }


def require_secret_configured(view: RuntimeSectionView, field: str) -> None:
    spec = get_field_spec(view.section, field)
    if not spec.is_secret:
        raise ValueError(f'field is not secret: {view.section}.{field}')

    payload = view.payload.get(field) or {}
    if bool(payload.get('is_set')):
        return

    raise RuntimeSettingsSecretRequiredError(
        f'missing secret config: {view.section}.{field} (source={view.source}, reason={view.source_reason})'
    )


def _resolve_runtime_secret_from_view(view: RuntimeSectionView, field: str) -> RuntimeSecretValue:
    spec = get_field_spec(view.section, field)
    if not spec.is_secret:
        raise ValueError(f'field is not secret: {view.section}.{field}')

    payload = view.payload.get(field) or {}
    field_ref = f'{view.section}.{field}'
    encrypted_value = str(payload.get('value_encrypted') or '').strip()
    is_set = bool(payload.get('is_set'))

    if encrypted_value:
        try:
            decrypted_value = runtime_secrets.decrypt_runtime_secret_value(encrypted_value)
        except runtime_secrets.RuntimeSettingsCryptoKeyMissingError as exc:
            raise RuntimeSettingsSecretResolutionError(
                f'missing runtime settings crypto key while decrypting {field_ref}'
            ) from exc
        except runtime_secrets.RuntimeSettingsCryptoEngineError as exc:
            raise RuntimeSettingsSecretResolutionError(
                f'failed to decrypt runtime secret {field_ref}: {exc}'
            ) from exc

        if not str(decrypted_value or '').strip():
            raise RuntimeSettingsSecretResolutionError(
                f'empty decrypted runtime secret: {field_ref}'
            )

        return RuntimeSecretValue(
            section=view.section,
            field=field,
            value=str(decrypted_value),
            source='db_encrypted',
            source_reason=view.source_reason,
        )

    env_value = str(_seed_value(view.section, field) or '').strip()
    if payload.get('origin') == 'env_seed' and env_value:
        return RuntimeSecretValue(
            section=view.section,
            field=field,
            value=env_value,
            source='env_fallback',
            source_reason=view.source_reason,
        )

    if view.source in {'db', 'candidate'} and is_set:
        raise RuntimeSettingsSecretResolutionError(
            f'secret marked as set but no decryptable value is available: {field_ref}'
        )

    raise RuntimeSettingsSecretRequiredError(
        f'missing secret config: {field_ref} (source={view.source}, reason={view.source_reason})'
    )


def get_runtime_secret_value(
    section: str,
    field: str,
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSecretValue:
    view = get_runtime_section(section, fetcher=fetcher)
    return _resolve_runtime_secret_from_view(view, field)


def _coerce_field_value(section: str, field: str, value: Any) -> Any:
    spec = get_field_spec(section, field)
    field_ref = f'{section}.{field}'

    if spec.value_type == 'text':
        if not isinstance(value, str):
            raise RuntimeSettingsValidationError(f'invalid text value for {field_ref}')
        return value

    if spec.value_type == 'int':
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeSettingsValidationError(f'invalid int value for {field_ref}')
        return int(value)

    if spec.value_type == 'float':
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeSettingsValidationError(f'invalid float value for {field_ref}')
        return float(value)

    raise RuntimeSettingsValidationError(f'unsupported value type for {field_ref}: {spec.value_type}')


def normalize_admin_patch_payload(section: str, payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    get_section_spec(section)
    if not isinstance(payload, Mapping) or not payload:
        raise RuntimeSettingsValidationError(f'patch payload must be a non-empty mapping for {section}')

    normalized: dict[str, dict[str, Any]] = {}
    for field_name, raw_value in payload.items():
        try:
            spec = get_field_spec(section, str(field_name))
        except KeyError as exc:
            raise RuntimeSettingsValidationError(str(exc)) from exc
        field_ref = f'{section}.{field_name}'

        if not isinstance(raw_value, Mapping):
            raise RuntimeSettingsValidationError(f'field patch must be a mapping for {field_ref}')

        if spec.is_secret:
            has_replace_value = 'replace_value' in raw_value
            has_plain_value = 'value' in raw_value
            has_encrypted_value = 'value_encrypted' in raw_value

            if has_plain_value or has_encrypted_value:
                raise RuntimeSettingsValidationError(
                    f'ambiguous secret patch payload for {field_ref}: use replace_value only'
                )
            if not has_replace_value:
                raise RuntimeSettingsValidationError(f'missing replace_value for {field_ref}')

            replace_value = raw_value.get('replace_value')
            if not isinstance(replace_value, str):
                raise RuntimeSettingsValidationError(f'invalid text value for {field_ref}')
            try:
                encrypted_value = runtime_secrets.encrypt_runtime_secret_value(replace_value)
            except runtime_secrets.RuntimeSettingsCryptoKeyMissingError as exc:
                raise RuntimeSettingsValidationError(str(exc)) from exc
            except runtime_secrets.RuntimeSettingsCryptoEngineError as exc:
                raise RuntimeSettingsValidationError(f'failed to encrypt secret for {field_ref}') from exc

            normalized[str(field_name)] = {
                'is_secret': True,
                'is_set': True,
                'origin': 'admin_ui',
                'value_encrypted': encrypted_value,
            }
            continue

        if 'value' not in raw_value:
            raise RuntimeSettingsValidationError(f'missing value for {field_ref}')

        normalized[str(field_name)] = {
            'value': _coerce_field_value(section, str(field_name), raw_value.get('value')),
            'is_secret': False,
            'origin': 'admin_ui',
        }

    return normalized


def update_runtime_section(
    section: str,
    patch_payload: Mapping[str, Any],
    *,
    updated_by: str = 'admin_api',
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSectionView:
    actor = str(updated_by or '').strip() or 'admin_api'
    normalized_patch = normalize_admin_patch_payload(section, patch_payload)
    current_view = get_runtime_section(section, fetcher=fetcher)
    next_payload = normalize_stored_payload(section, current_view.payload, default_origin=current_view.source_reason)
    next_payload.update(normalized_patch)

    try:
        import psycopg
        from psycopg import errors as psycopg_errors
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise RuntimeSettingsDbUnavailableError(f'psycopg unavailable: {exc}') from exc

    try:
        with psycopg.connect(config.FRIDA_MEMORY_DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT payload
                    FROM runtime_settings
                    WHERE section = %s
                    ''',
                    (section,),
                )
                row = cur.fetchone()
                if row:
                    before_payload = normalize_stored_payload(section, row[0], default_origin='db')
                else:
                    before_payload = {}

                cur.execute(
                    '''
                    INSERT INTO runtime_settings (section, schema_version, updated_by, payload)
                    VALUES (%s, 'v1', %s, %s::jsonb)
                    ON CONFLICT (section) DO UPDATE
                    SET schema_version = EXCLUDED.schema_version,
                        updated_at = now(),
                        updated_by = EXCLUDED.updated_by,
                        payload = EXCLUDED.payload
                    ''',
                    (section, actor, json.dumps(next_payload)),
                )
                cur.execute(
                    '''
                    INSERT INTO runtime_settings_history (
                        section,
                        schema_version,
                        changed_by,
                        payload_before,
                        payload_after
                    )
                    VALUES (%s, 'v1', %s, %s::jsonb, %s::jsonb)
                    ''',
                    (section, actor, json.dumps(before_payload), json.dumps(next_payload)),
                )
            conn.commit()
    except psycopg_errors.UndefinedTable as exc:
        raise RuntimeSettingsDbUnavailableError(f'runtime settings tables missing: {exc}') from exc
    except Exception as exc:
        raise RuntimeSettingsDbUnavailableError(str(exc)) from exc

    invalidate_runtime_settings_cache()
    return RuntimeSectionView(
        section=section,
        payload=redact_payload_for_api(section, next_payload),
        source='db',
        source_reason='db_row',
    )


def _effective_runtime_payload(
    section: str,
    payload: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    effective = normalize_stored_payload(
        section,
        build_env_seed_bundle(section).payload,
        default_origin='env_seed',
    )
    effective.update(normalize_stored_payload(section, payload, default_origin='db'))
    return effective


def _candidate_runtime_section(
    section: str,
    *,
    patch_payload: Mapping[str, Any] | None = None,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> RuntimeSectionView:
    current_view = get_runtime_section(section, fetcher=fetcher)
    candidate_payload = _effective_runtime_payload(section, current_view.payload)
    if patch_payload:
        candidate_payload.update(normalize_admin_patch_payload(section, patch_payload))
        return RuntimeSectionView(
            section=section,
            payload=candidate_payload,
            source='candidate',
            source_reason='validate_payload',
        )

    return RuntimeSectionView(
        section=section,
        payload=candidate_payload,
        source=current_view.source,
        source_reason=current_view.source_reason,
    )


def validate_runtime_section(
    section: str,
    patch_payload: Mapping[str, Any] | None = None,
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    return runtime_settings_validation.validate_runtime_section(
        section=section,
        patch_payload=patch_payload,
        fetcher=fetcher,
        candidate_runtime_section=_candidate_runtime_section,
        resolve_runtime_secret_from_view=_resolve_runtime_secret_from_view,
        secret_required_error_cls=RuntimeSettingsSecretRequiredError,
        secret_resolution_error_cls=RuntimeSettingsSecretResolutionError,
        config_module=config,
    )
