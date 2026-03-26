from __future__ import annotations

import json
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Tuple
from urllib.parse import urlparse

import config
from admin import runtime_secrets
from core import prompt_loader


SECTION_NAMES: Tuple[str, ...] = (
    'main_model',
    'arbiter_model',
    'summary_model',
    'embedding',
    'database',
    'services',
    'resources',
)


@dataclass(frozen=True)
class FieldSpec:
    key: str
    value_type: str
    is_secret: bool = False
    env_var: str | None = None
    seed_from_env: bool = True
    seed_default: Any = None

    def public_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            'key': self.key,
            'value_type': self.value_type,
            'is_secret': self.is_secret,
            'seed_from_env': self.seed_from_env,
        }
        if self.env_var:
            out['env_var'] = self.env_var
        if self.seed_default is not None:
            out['seed_default'] = self.seed_default
        return out


@dataclass(frozen=True)
class SectionSpec:
    name: str
    fields: Tuple[FieldSpec, ...]

    def field_names(self) -> Tuple[str, ...]:
        return tuple(field.key for field in self.fields)

    def field_map(self) -> Dict[str, FieldSpec]:
        return {field.key: field for field in self.fields}

    def public_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'fields': [field.public_dict() for field in self.fields],
        }


@dataclass(frozen=True)
class SectionSeedBundle:
    section: str
    payload: Dict[str, Dict[str, Any]]
    secret_values: Dict[str, str]


@dataclass(frozen=True)
class RuntimeSettingsSnapshot:
    rows: Dict[str, Dict[str, Dict[str, Any]]]
    db_state: str


@dataclass(frozen=True)
class RuntimeSectionView:
    section: str
    payload: Dict[str, Dict[str, Any]]
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


SECRET_V1_FIELDS: Tuple[Tuple[str, str], ...] = (
    ('main_model', 'api_key'),
    ('embedding', 'token'),
    ('services', 'crawl4ai_token'),
    ('database', 'dsn'),
)


SECTION_SPECS: Dict[str, SectionSpec] = {
    'main_model': SectionSpec(
        name='main_model',
        fields=(
            FieldSpec('base_url', 'text', env_var='OPENROUTER_BASE'),
            FieldSpec('model', 'text', env_var='OPENROUTER_MODEL'),
            FieldSpec('api_key', 'text', is_secret=True, env_var='OPENROUTER_API_KEY'),
            FieldSpec('referer', 'text', env_var='OPENROUTER_REFERER'),
            FieldSpec('app_name', 'text', env_var='OPENROUTER_APP_NAME'),
            FieldSpec('title_llm', 'text', env_var='OPENROUTER_TITLE_LLM'),
            FieldSpec('title_arbiter', 'text', env_var='OPENROUTER_TITLE_ARBITER'),
            FieldSpec('title_resumer', 'text', env_var='OPENROUTER_TITLE_RESUMER'),
            FieldSpec('temperature', 'float', seed_from_env=False, seed_default=0.4),
            FieldSpec('top_p', 'float', seed_from_env=False, seed_default=1.0),
            FieldSpec('response_max_tokens', 'int', seed_from_env=False, seed_default=1500),
        ),
    ),
    'arbiter_model': SectionSpec(
        name='arbiter_model',
        fields=(
            FieldSpec('model', 'text', env_var='ARBITER_MODEL'),
            FieldSpec('temperature', 'float', seed_from_env=False, seed_default=0.0),
            FieldSpec('top_p', 'float', seed_from_env=False, seed_default=1.0),
            FieldSpec('timeout_s', 'int', env_var='ARBITER_TIMEOUT_S'),
        ),
    ),
    'summary_model': SectionSpec(
        name='summary_model',
        fields=(
            FieldSpec('model', 'text', env_var='SUMMARY_MODEL'),
            FieldSpec('temperature', 'float', seed_from_env=False, seed_default=0.3),
            FieldSpec('top_p', 'float', seed_from_env=False, seed_default=1.0),
        ),
    ),
    'embedding': SectionSpec(
        name='embedding',
        fields=(
            FieldSpec('endpoint', 'text', env_var='EMBED_BASE_URL'),
            FieldSpec('model', 'text', seed_from_env=False, seed_default='intfloat/multilingual-e5-small'),
            FieldSpec('token', 'text', is_secret=True, env_var='EMBED_TOKEN'),
            FieldSpec('dimensions', 'int', env_var='EMBED_DIM'),
            FieldSpec('top_k', 'int', env_var='MEMORY_TOP_K'),
        ),
    ),
    'database': SectionSpec(
        name='database',
        fields=(
            FieldSpec('backend', 'text', seed_from_env=False, seed_default='postgresql'),
            FieldSpec('dsn', 'text', is_secret=True, env_var='FRIDA_MEMORY_DB_DSN', seed_from_env=False),
        ),
    ),
    'services': SectionSpec(
        name='services',
        fields=(
            FieldSpec('searxng_url', 'text', env_var='SEARXNG_URL'),
            FieldSpec('searxng_results', 'int', env_var='SEARXNG_RESULTS'),
            FieldSpec('crawl4ai_url', 'text', env_var='CRAWL4AI_URL'),
            FieldSpec('crawl4ai_token', 'text', is_secret=True, env_var='CRAWL4AI_TOKEN'),
            FieldSpec('crawl4ai_top_n', 'int', env_var='CRAWL4AI_TOP_N'),
            FieldSpec('crawl4ai_max_chars', 'int', env_var='CRAWL4AI_MAX_CHARS'),
        ),
    ),
    'resources': SectionSpec(
        name='resources',
        fields=(
            FieldSpec('llm_identity_path', 'text', env_var='FRIDA_LLM_IDENTITY_PATH'),
            FieldSpec('user_identity_path', 'text', env_var='FRIDA_USER_IDENTITY_PATH'),
        ),
    ),
}


def list_sections() -> Tuple[str, ...]:
    return SECTION_NAMES


def list_secret_v1_fields() -> Tuple[Tuple[str, str], ...]:
    return SECRET_V1_FIELDS


def get_section_spec(section: str) -> SectionSpec:
    try:
        return SECTION_SPECS[str(section)]
    except KeyError as exc:
        raise KeyError(f'unknown runtime settings section: {section}') from exc


def get_field_spec(section: str, field: str) -> FieldSpec:
    field_map = get_section_spec(section).field_map()
    try:
        return field_map[str(field)]
    except KeyError as exc:
        raise KeyError(f'unknown runtime settings field: {section}.{field}') from exc


def describe_section(section: str) -> Dict[str, Any]:
    return get_section_spec(section).public_dict()


def normalize_stored_payload(
    section: str,
    payload: Mapping[str, Any],
    *,
    default_origin: str = 'manual_sql',
) -> Dict[str, Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise TypeError('payload must be a mapping')

    normalized: Dict[str, Dict[str, Any]] = {}
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
            field_payload: Dict[str, Any] = {
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


def redact_payload_for_api(section: str, payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    redacted: Dict[str, Dict[str, Any]] = {}
    for field_name, field_payload in normalize_stored_payload(section, payload).items():
        spec = get_field_spec(section, field_name)
        if spec.is_secret:
            redacted[field_name] = {
                'is_secret': True,
                'is_set': bool(field_payload.get('is_set')),
                'origin': field_payload.get('origin'),
            }
        else:
            redacted[field_name] = dict(field_payload)
    return redacted


def _secret_effective_source(section: str, field: str, payload: Mapping[str, Any]) -> str:
    spec = get_field_spec(section, field)
    if not spec.is_secret:
        raise ValueError(f'field is not secret: {section}.{field}')

    if section == 'database' and field == 'dsn':
        if str(config.FRIDA_MEMORY_DB_DSN or '').strip():
            return 'env_fallback'
        return 'db_encrypted' if bool(payload.get('is_set')) else 'missing'

    is_set = bool(payload.get('is_set'))
    if not is_set:
        return 'missing'

    origin = str(payload.get('origin') or '').strip()
    if origin == 'env_seed':
        return 'env_fallback'
    return 'db_encrypted'


def describe_secret_sources(section: str, payload: Mapping[str, Any]) -> Dict[str, str]:
    normalized = normalize_stored_payload(section, payload)
    secret_sources: Dict[str, str] = {}
    for field in get_section_spec(section).fields:
        if not field.is_secret:
            continue
        secret_sources[field.key] = _secret_effective_source(
            section,
            field.key,
            normalized.get(field.key) or {},
        )
    return secret_sources


def _seed_value(section: str, field: str) -> Any:
    values: Dict[tuple[str, str], Any] = {
        ('main_model', 'base_url'): config.OR_BASE,
        ('main_model', 'model'): config.OR_MODEL,
        ('main_model', 'api_key'): config.OR_KEY,
        ('main_model', 'referer'): config.OR_REFERER,
        ('main_model', 'app_name'): config.OR_TITLE_BASE,
        ('main_model', 'title_llm'): config.OR_TITLE_LLM,
        ('main_model', 'title_arbiter'): config.OR_TITLE_ARBITER,
        ('main_model', 'title_resumer'): config.OR_TITLE_RESUMER,
        ('main_model', 'temperature'): 0.4,
        ('main_model', 'top_p'): 1.0,
        ('main_model', 'response_max_tokens'): 1500,
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
        ('resources', 'llm_identity_path'): config.FRIDA_LLM_IDENTITY_PATH,
        ('resources', 'user_identity_path'): config.FRIDA_USER_IDENTITY_PATH,
    }
    spec = get_field_spec(section, field)
    return values.get((section, field), spec.seed_default)


def build_env_seed_bundle(section: str) -> SectionSeedBundle:
    spec = get_section_spec(section)
    payload: Dict[str, Dict[str, Any]] = {}
    secret_values: Dict[str, str] = {}

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
            'origin': 'env_seed',
        }

    return SectionSeedBundle(section=section, payload=payload, secret_values=secret_values)


def build_db_seed_bundle(section: str) -> SectionSeedBundle:
    env_bundle = build_env_seed_bundle(section)
    payload = normalize_stored_payload(section, env_bundle.payload, default_origin='env_seed')
    seeded_payload: Dict[str, Dict[str, Any]] = {}

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


def get_unseeded_sections(existing_sections: Iterable[str]) -> Tuple[str, ...]:
    existing = {str(section) for section in existing_sections}
    return tuple(section for section in SECTION_NAMES if section not in existing)


def build_env_seed_plan(existing_sections: Iterable[str] = ()) -> Tuple[SectionSeedBundle, ...]:
    return tuple(build_env_seed_bundle(section) for section in get_unseeded_sections(existing_sections))


def build_db_seed_plan(existing_sections: Iterable[str] = ()) -> Tuple[SectionSeedBundle, ...]:
    return tuple(build_db_seed_bundle(section) for section in get_unseeded_sections(existing_sections))


def _merge_missing_db_seed_fields(
    section: str,
    current_payload: Mapping[str, Any],
) -> Tuple[Dict[str, Dict[str, Any]], Tuple[str, ...]]:
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


def backfill_runtime_secrets_from_env(*, updated_by: str = 'runtime_secret_backfill') -> Dict[str, Any]:
    actor = str(updated_by or '').strip() or 'runtime_secret_backfill'

    try:
        import psycopg
        from psycopg import errors as psycopg_errors
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise RuntimeSettingsDbUnavailableError(f'psycopg unavailable: {exc}') from exc

    updated_fields: list[str] = []
    updated_sections: set[str] = set()

    try:
        with psycopg.connect(config.FRIDA_MEMORY_DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT section, payload
                    FROM runtime_settings
                    ORDER BY section
                    '''
                )
                rows = {
                    str(section): normalize_stored_payload(str(section), payload, default_origin='db')
                    for section, payload in cur.fetchall()
                }

                for section, field in SECRET_V1_FIELDS:
                    env_value = _backfill_env_secret_value(section, field)
                    if not env_value:
                        continue

                    current_payload = rows.get(section)
                    if current_payload is None:
                        next_payload = normalize_stored_payload(
                            section,
                            build_env_seed_bundle(section).payload,
                            default_origin='env_seed',
                        )
                        before_payload: Dict[str, Dict[str, Any]] = {}
                    else:
                        next_payload = normalize_stored_payload(section, current_payload, default_origin='db')
                        before_payload = normalize_stored_payload(section, current_payload, default_origin='db')

                    current_field_payload = next_payload.get(field) or {}
                    if not _should_backfill_secret_field(current_field_payload):
                        continue

                    encrypted_value = runtime_secrets.encrypt_runtime_secret_value(env_value)
                    next_payload[field] = {
                        'is_secret': True,
                        'is_set': True,
                        'origin': 'env_backfill',
                        'value_encrypted': encrypted_value,
                    }

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

                    rows[section] = next_payload
                    updated_sections.add(section)
                    updated_fields.append(f'{section}.{field}')
            conn.commit()
    except psycopg_errors.UndefinedTable as exc:
        raise RuntimeSettingsDbUnavailableError(f'runtime settings tables missing: {exc}') from exc
    except Exception as exc:
        raise RuntimeSettingsDbUnavailableError(str(exc)) from exc

    if updated_fields:
        invalidate_runtime_settings_cache()

    return {
        'updated_fields': tuple(updated_fields),
        'updated_sections': tuple(sorted(updated_sections)),
    }


def init_runtime_settings_db() -> Dict[str, Any]:
    try:
        migration_sql = RUNTIME_SETTINGS_SQL_PATH.read_text(encoding='utf-8')
    except OSError as exc:
        raise RuntimeError(f'cannot read runtime settings migration sql: {exc}') from exc

    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise RuntimeSettingsDbUnavailableError(f'psycopg unavailable: {exc}') from exc

    try:
        with psycopg.connect(config.FRIDA_MEMORY_DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
            conn.commit()
    except Exception as exc:
        raise RuntimeSettingsDbUnavailableError(str(exc)) from exc

    return {
        'sql_path': str(RUNTIME_SETTINGS_SQL_PATH),
        'tables': ('runtime_settings', 'runtime_settings_history'),
    }


def bootstrap_runtime_settings_from_env(*, updated_by: str = 'runtime_settings_bootstrap') -> Dict[str, Any]:
    actor = str(updated_by or '').strip() or 'runtime_settings_bootstrap'

    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise RuntimeSettingsDbUnavailableError(f'psycopg unavailable: {exc}') from exc

    inserted_sections: list[str] = []
    inserted_fields: list[str] = []
    updated_sections: list[str] = []
    updated_fields: list[str] = []

    try:
        with psycopg.connect(config.FRIDA_MEMORY_DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT section, payload
                    FROM runtime_settings
                    ORDER BY section
                    '''
                )
                existing_rows = {
                    str(section): normalize_stored_payload(str(section), payload, default_origin='db')
                    for section, payload in cur.fetchall()
                }
                existing_sections = tuple(existing_rows.keys())
                for bundle in build_db_seed_plan(existing_sections):
                    cur.execute(
                        '''
                        INSERT INTO runtime_settings (section, schema_version, updated_by, payload)
                        VALUES (%s, 'v1', %s, %s::jsonb)
                        ''',
                        (bundle.section, actor, json.dumps(bundle.payload)),
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
                        (bundle.section, actor, json.dumps({}), json.dumps(bundle.payload)),
                    )
                    inserted_sections.append(bundle.section)
                    inserted_fields.extend(f'{bundle.section}.{field_name}' for field_name in bundle.payload.keys())
                for section, current_payload in existing_rows.items():
                    next_payload, missing_fields = _merge_missing_db_seed_fields(section, current_payload)
                    if not missing_fields:
                        continue
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
                        (section, actor, json.dumps(current_payload), json.dumps(next_payload)),
                    )
                    updated_sections.append(section)
                    updated_fields.extend(f'{section}.{field_name}' for field_name in missing_fields)
            conn.commit()
    except Exception as exc:
        raise RuntimeSettingsDbUnavailableError(str(exc)) from exc

    if inserted_sections or updated_sections:
        invalidate_runtime_settings_cache()

    return {
        'inserted_sections': tuple(inserted_sections),
        'inserted_fields': tuple(inserted_fields),
        'updated_sections': tuple(updated_sections),
        'updated_fields': tuple(updated_fields),
    }


def invalidate_runtime_settings_cache() -> None:
    global _SNAPSHOT_CACHE
    _SNAPSHOT_CACHE = None


def _default_db_fetch_all_sections() -> Dict[str, Dict[str, Dict[str, Any]]]:
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
                    SELECT section, payload
                    FROM runtime_settings
                    ORDER BY section
                    '''
                )
                rows = cur.fetchall()
    except psycopg_errors.UndefinedTable as exc:
        raise RuntimeSettingsDbUnavailableError(f'runtime settings tables missing: {exc}') from exc
    except Exception as exc:
        raise RuntimeSettingsDbUnavailableError(str(exc)) from exc

    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for section, payload in rows:
        out[str(section)] = normalize_stored_payload(str(section), payload, default_origin='db')
    return out


def _load_snapshot(
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
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


def _env_payload_for_runtime(section: str) -> Dict[str, Dict[str, Any]]:
    return build_env_seed_bundle(section).payload


def get_runtime_section(
    section: str,
    *,
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
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
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
) -> RuntimeSectionView:
    view = get_runtime_section(section, fetcher=fetcher)
    return RuntimeSectionView(
        section=view.section,
        payload=redact_payload_for_api(section, view.payload),
        source=view.source,
        source_reason=view.source_reason,
    )


def _ast_expr_to_string(expr: ast.AST) -> str:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.JoinedStr):
        parts = []
        for value in expr.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                try:
                    rendered = ast.unparse(value.value)
                except Exception:
                    rendered = 'expr'
                parts.append('{' + rendered + '}')
        return ''.join(parts)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        return _ast_expr_to_string(expr.left) + _ast_expr_to_string(expr.right)
    return ''


def _read_python_function_string_assignment(module_relpath: str, function_name: str, variable_name: str) -> str:
    module_path = Path(__file__).resolve().parents[1] / module_relpath
    try:
        source = module_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return ''

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != function_name:
            continue
        for statement in ast.walk(node):
            if not isinstance(statement, ast.Assign):
                continue
            if len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if not isinstance(target, ast.Name) or target.id != variable_name:
                continue
            value = _ast_expr_to_string(statement.value)
            return value.strip()
    return ''


def _read_python_function_dict_path_string(
    module_relpath: str,
    function_name: str,
    variable_name: str,
    path: Tuple[Any, ...],
) -> str:
    module_path = Path(__file__).resolve().parents[1] / module_relpath
    try:
        source = module_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return ''

    current: ast.AST | None = None
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != function_name:
            continue
        for statement in ast.walk(node):
            if not isinstance(statement, ast.Assign):
                continue
            if len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id == variable_name:
                current = statement.value
                break
        break

    if current is None:
        return ''

    for step in path:
        if isinstance(step, str):
            if not isinstance(current, ast.Dict):
                return ''
            next_node = None
            for key_node, value_node in zip(current.keys, current.values):
                if isinstance(key_node, ast.Constant) and key_node.value == step:
                    next_node = value_node
                    break
            if next_node is None:
                return ''
            current = next_node
            continue
        if isinstance(step, int):
            if not isinstance(current, ast.List):
                return ''
            if step < 0 or step >= len(current.elts):
                return ''
            current = current.elts[step]
            continue
        return ''

    return _ast_expr_to_string(current).strip()


def get_section_readonly_info(section: str) -> Dict[str, Dict[str, Any]]:
    get_section_spec(section)
    if section == 'main_model':
        return {
            'context_max_tokens': {
                'label': 'FRIDA_MAX_TOKENS',
                'value': int(config.MAX_TOKENS),
                'is_editable': False,
                'source': 'config_py',
            },
            'system_prompt': {
                'label': 'SYSTEM_PROMPT',
                'value': prompt_loader.get_main_system_prompt(),
                'is_editable': False,
                'source': 'prompt_file',
            },
        }
    if section == 'arbiter_model':
        return {
            'decision_max_tokens': {
                'label': 'decision_max_tokens',
                'value': 600,
                'is_editable': False,
                'source': 'memory_arbiter_py',
            },
            'identity_extractor_max_tokens': {
                'label': 'identity_extractor_max_tokens',
                'value': 700,
                'is_editable': False,
                'source': 'memory_arbiter_py',
            },
            'arbiter_prompt_path': {
                'label': 'ARBITER_PROMPT_PATH',
                'value': str(config.ARBITER_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'identity_extractor_prompt_path': {
                'label': 'IDENTITY_EXTRACTOR_PROMPT_PATH',
                'value': str(config.IDENTITY_EXTRACTOR_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'arbiter_prompt': {
                'label': 'arbiter_prompt',
                'value': prompt_loader.read_prompt_text(str(config.ARBITER_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
            'identity_extractor_prompt': {
                'label': 'identity_extractor_prompt',
                'value': prompt_loader.read_prompt_text(str(config.IDENTITY_EXTRACTOR_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
        }
    if section == 'summary_model':
        return {
            'summary_target_tokens': {
                'label': 'SUMMARY_TARGET_TOKENS',
                'value': int(config.SUMMARY_TARGET_TOKENS),
                'is_editable': False,
                'source': 'config_py',
            },
            'summary_threshold_tokens': {
                'label': 'SUMMARY_THRESHOLD_TOKENS',
                'value': int(config.SUMMARY_THRESHOLD_TOKENS),
                'is_editable': False,
                'source': 'config_py',
            },
            'summary_keep_turns': {
                'label': 'SUMMARY_KEEP_TURNS',
                'value': int(config.SUMMARY_KEEP_TURNS),
                'is_editable': False,
                'source': 'config_py',
            },
            'system_prompt': {
                'label': 'summary_system_prompt',
                'value': _read_python_function_string_assignment(
                    'memory/summarizer.py',
                    'summarize_conversation',
                    'system',
                ),
                'is_editable': False,
                'source': 'memory_summarizer_py',
            },
        }
    if section == 'services':
        return {
            'web_reformulation_max_tokens': {
                'label': 'web_reformulation_max_tokens',
                'value': 40,
                'is_editable': False,
                'source': 'tools_web_search_py',
            },
            'web_reformulation_system_prompt': {
                'label': 'web_reformulation_system_prompt',
                'value': _read_python_function_dict_path_string(
                    'tools/web_search.py',
                    'reformulate',
                    'payload',
                    ('messages', 0, 'content'),
                ),
                'is_editable': False,
                'source': 'tools_web_search_py',
            },
        }
    return {}


def get_main_model_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('main_model', fetcher=fetcher)


def get_arbiter_model_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('arbiter_model', fetcher=fetcher)


def get_summary_model_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('summary_model', fetcher=fetcher)


def get_embedding_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('embedding', fetcher=fetcher)


def get_database_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('database', fetcher=fetcher)


def get_services_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('services', fetcher=fetcher)


def get_resources_settings(*, fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None) -> RuntimeSectionView:
    return get_runtime_section('resources', fetcher=fetcher)


def get_runtime_status(
    *,
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
) -> Dict[str, Any]:
    snapshot = _load_snapshot(fetcher=fetcher)
    sections: Dict[str, Dict[str, str]] = {}
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
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
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


def normalize_admin_patch_payload(section: str, payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    get_section_spec(section)
    if not isinstance(payload, Mapping) or not payload:
        raise RuntimeSettingsValidationError(f'patch payload must be a non-empty mapping for {section}')

    normalized: Dict[str, Dict[str, Any]] = {}
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
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
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
) -> Dict[str, Dict[str, Any]]:
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
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
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


def _validation_check(name: str, ok: bool, detail: str) -> Dict[str, Any]:
    return {
        'name': name,
        'ok': bool(ok),
        'detail': str(detail),
    }


def _runtime_text_value(view: RuntimeSectionView, field: str) -> str:
    payload = view.payload.get(field) or {}
    return str(payload.get('value') or '').strip()


def _runtime_int_value(view: RuntimeSectionView, field: str) -> int | None:
    payload = view.payload.get(field) or {}
    value = payload.get('value')
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _runtime_float_value(view: RuntimeSectionView, field: str) -> float | None:
    payload = view.payload.get(field) or {}
    value = payload.get('value')
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_http_url(value: str) -> bool:
    parsed = urlparse(str(value or '').strip())
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def _resolve_app_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def validate_runtime_section(
    section: str,
    patch_payload: Mapping[str, Any] | None = None,
    *,
    fetcher: Callable[[], Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
) -> Dict[str, Any]:
    view = _candidate_runtime_section(section, patch_payload=patch_payload, fetcher=fetcher)
    checks: list[Dict[str, Any]] = []

    if section == 'main_model':
        base_url = _runtime_text_value(view, 'base_url')
        model = _runtime_text_value(view, 'model')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        try:
            api_key_secret = _resolve_runtime_secret_from_view(view, 'api_key')
            api_key_ok = bool(str(api_key_secret.value).strip())
            api_key_detail = f'main_model.api_key available from {api_key_secret.source}'
        except (RuntimeSettingsSecretRequiredError, RuntimeSettingsSecretResolutionError) as exc:
            api_key_ok = False
            api_key_detail = str(exc)
        checks.extend(
            (
                _validation_check('base_url', _is_http_url(base_url), f'base_url={base_url or "missing"}'),
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check(
                    'temperature',
                    temperature is not None and 0.0 <= temperature <= 2.0,
                    f'temperature={temperature!r}',
                ),
                _validation_check(
                    'top_p',
                    top_p is not None and 0.0 < top_p <= 1.0,
                    f'top_p={top_p!r}',
                ),
                _validation_check('api_key_runtime', api_key_ok, api_key_detail),
            )
        )
    elif section == 'arbiter_model':
        model = _runtime_text_value(view, 'model')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        checks.extend(
            (
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check('timeout_s', timeout_s is not None and timeout_s > 0, f'timeout_s={timeout_s!r}'),
                _validation_check(
                    'temperature',
                    temperature is not None and 0.0 <= temperature <= 2.0,
                    f'temperature={temperature!r}',
                ),
                _validation_check(
                    'top_p',
                    top_p is not None and 0.0 < top_p <= 1.0,
                    f'top_p={top_p!r}',
                ),
            )
        )
    elif section == 'summary_model':
        model = _runtime_text_value(view, 'model')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        checks.extend(
            (
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check(
                    'temperature',
                    temperature is not None and 0.0 <= temperature <= 2.0,
                    f'temperature={temperature!r}',
                ),
                _validation_check(
                    'top_p',
                    top_p is not None and 0.0 < top_p <= 1.0,
                    f'top_p={top_p!r}',
                ),
            )
        )
    elif section == 'embedding':
        endpoint = _runtime_text_value(view, 'endpoint')
        model = _runtime_text_value(view, 'model')
        dimensions = _runtime_int_value(view, 'dimensions')
        top_k = _runtime_int_value(view, 'top_k')
        try:
            token_secret = _resolve_runtime_secret_from_view(view, 'token')
            token_ok = bool(str(token_secret.value).strip())
            token_detail = f'embedding.token available from {token_secret.source}'
        except (RuntimeSettingsSecretRequiredError, RuntimeSettingsSecretResolutionError) as exc:
            token_ok = False
            token_detail = str(exc)
        checks.extend(
            (
                _validation_check('endpoint', _is_http_url(endpoint), f'endpoint={endpoint or "missing"}'),
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check('dimensions', dimensions is not None and dimensions > 0, f'dimensions={dimensions!r}'),
                _validation_check('top_k', top_k is not None and top_k > 0, f'top_k={top_k!r}'),
                _validation_check('token_runtime', token_ok, token_detail),
            )
        )
    elif section == 'database':
        backend = _runtime_text_value(view, 'backend')
        dsn = str(config.FRIDA_MEMORY_DB_DSN or '').strip()
        checks.extend(
            (
                _validation_check(
                    'backend',
                    backend == 'postgresql',
                    f'backend={backend or "missing"}',
                ),
                _validation_check(
                    'dsn_transition',
                    bool(dsn),
                    'FRIDA_MEMORY_DB_DSN env bootstrap available'
                    if dsn
                    else 'FRIDA_MEMORY_DB_DSN env bootstrap missing during transition',
                ),
            )
        )
    elif section == 'services':
        searxng_url = _runtime_text_value(view, 'searxng_url')
        searxng_results = _runtime_int_value(view, 'searxng_results')
        crawl4ai_url = _runtime_text_value(view, 'crawl4ai_url')
        crawl4ai_top_n = _runtime_int_value(view, 'crawl4ai_top_n')
        crawl4ai_max_chars = _runtime_int_value(view, 'crawl4ai_max_chars')
        try:
            crawl4ai_token_secret = _resolve_runtime_secret_from_view(view, 'crawl4ai_token')
            crawl4ai_token_ok = bool(str(crawl4ai_token_secret.value).strip())
            crawl4ai_token_detail = f'services.crawl4ai_token available from {crawl4ai_token_secret.source}'
        except (RuntimeSettingsSecretRequiredError, RuntimeSettingsSecretResolutionError) as exc:
            crawl4ai_token_ok = False
            crawl4ai_token_detail = str(exc)
        checks.extend(
            (
                _validation_check('searxng_url', _is_http_url(searxng_url), f'searxng_url={searxng_url or "missing"}'),
                _validation_check(
                    'searxng_results',
                    searxng_results is not None and searxng_results > 0,
                    f'searxng_results={searxng_results!r}',
                ),
                _validation_check('crawl4ai_url', _is_http_url(crawl4ai_url), f'crawl4ai_url={crawl4ai_url or "missing"}'),
                _validation_check(
                    'crawl4ai_top_n',
                    crawl4ai_top_n is not None and crawl4ai_top_n > 0,
                    f'crawl4ai_top_n={crawl4ai_top_n!r}',
                ),
                _validation_check(
                    'crawl4ai_max_chars',
                    crawl4ai_max_chars is not None and crawl4ai_max_chars > 0,
                    f'crawl4ai_max_chars={crawl4ai_max_chars!r}',
                ),
                _validation_check('crawl4ai_token_runtime', crawl4ai_token_ok, crawl4ai_token_detail),
            )
        )
    elif section == 'resources':
        llm_identity_path = _resolve_app_path(_runtime_text_value(view, 'llm_identity_path'))
        user_identity_path = _resolve_app_path(_runtime_text_value(view, 'user_identity_path'))
        checks.extend(
            (
                _validation_check(
                    'llm_identity_path',
                    llm_identity_path.is_file(),
                    f'llm_identity_path={llm_identity_path}',
                ),
                _validation_check(
                    'user_identity_path',
                    user_identity_path.is_file(),
                    f'user_identity_path={user_identity_path}',
                ),
            )
        )
    else:  # pragma: no cover - SECTION_NAMES locks known values
        raise KeyError(f'unknown runtime settings section: {section}')

    return {
        'section': section,
        'source': view.source,
        'source_reason': view.source_reason,
        'valid': all(check['ok'] for check in checks),
        'checks': checks,
    }
