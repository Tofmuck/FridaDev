from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


def init_runtime_settings_db(
    *,
    dsn: str,
    sql_path: Path,
    db_unavailable_error_cls: type[RuntimeError],
) -> dict[str, Any]:
    try:
        migration_sql = sql_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise RuntimeError(f'cannot read runtime settings migration sql: {exc}') from exc

    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise db_unavailable_error_cls(f'psycopg unavailable: {exc}') from exc

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
            conn.commit()
    except Exception as exc:
        raise db_unavailable_error_cls(str(exc)) from exc

    return {
        'sql_path': str(sql_path),
        'tables': ('runtime_settings', 'runtime_settings_history'),
    }


def fetch_all_sections(
    *,
    dsn: str,
    normalize_stored_payload: Callable[..., dict[str, dict[str, Any]]],
    db_unavailable_error_cls: type[RuntimeError],
) -> dict[str, dict[str, dict[str, Any]]]:
    try:
        import psycopg
        from psycopg import errors as psycopg_errors
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise db_unavailable_error_cls(f'psycopg unavailable: {exc}') from exc

    try:
        with psycopg.connect(dsn) as conn:
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
        raise db_unavailable_error_cls(f'runtime settings tables missing: {exc}') from exc
    except Exception as exc:
        raise db_unavailable_error_cls(str(exc)) from exc

    out: dict[str, dict[str, dict[str, Any]]] = {}
    for section, payload in rows:
        out[str(section)] = normalize_stored_payload(str(section), payload, default_origin='db')
    return out


def bootstrap_runtime_settings_from_env(
    *,
    dsn: str,
    updated_by: str,
    build_db_seed_plan: Callable[[Iterable[str]], tuple[Any, ...]],
    normalize_stored_payload: Callable[..., dict[str, dict[str, Any]]],
    merge_missing_db_seed_fields: Callable[
        [str, Mapping[str, Any]],
        tuple[dict[str, dict[str, Any]], tuple[str, ...]],
    ],
    invalidate_runtime_settings_cache: Callable[[], None],
    db_unavailable_error_cls: type[RuntimeError],
) -> dict[str, Any]:
    actor = str(updated_by or '').strip() or 'runtime_settings_bootstrap'

    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise db_unavailable_error_cls(f'psycopg unavailable: {exc}') from exc

    inserted_sections: list[str] = []
    inserted_fields: list[str] = []
    updated_sections: list[str] = []
    updated_fields: list[str] = []

    try:
        with psycopg.connect(dsn) as conn:
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
                    next_payload, missing_fields = merge_missing_db_seed_fields(section, current_payload)
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
        raise db_unavailable_error_cls(str(exc)) from exc

    if inserted_sections or updated_sections:
        invalidate_runtime_settings_cache()

    return {
        'inserted_sections': tuple(inserted_sections),
        'inserted_fields': tuple(inserted_fields),
        'updated_sections': tuple(updated_sections),
        'updated_fields': tuple(updated_fields),
    }


def backfill_runtime_secrets_from_env(
    *,
    dsn: str,
    updated_by: str,
    secret_v1_fields: tuple[tuple[str, str], ...],
    normalize_stored_payload: Callable[..., dict[str, dict[str, Any]]],
    build_env_seed_bundle: Callable[[str], Any],
    backfill_env_secret_value: Callable[[str, str], str],
    should_backfill_secret_field: Callable[[Mapping[str, Any]], bool],
    encrypt_runtime_secret_value: Callable[[str], str],
    invalidate_runtime_settings_cache: Callable[[], None],
    db_unavailable_error_cls: type[RuntimeError],
) -> dict[str, Any]:
    actor = str(updated_by or '').strip() or 'runtime_secret_backfill'

    try:
        import psycopg
        from psycopg import errors as psycopg_errors
    except Exception as exc:  # pragma: no cover - dependency issue, not business logic
        raise db_unavailable_error_cls(f'psycopg unavailable: {exc}') from exc

    updated_fields: list[str] = []
    updated_sections: set[str] = set()

    try:
        with psycopg.connect(dsn) as conn:
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

                for section, field in secret_v1_fields:
                    env_value = backfill_env_secret_value(section, field)
                    if not env_value:
                        continue

                    current_payload = rows.get(section)
                    if current_payload is None:
                        next_payload = normalize_stored_payload(
                            section,
                            build_env_seed_bundle(section).payload,
                            default_origin='env_seed',
                        )
                        before_payload: dict[str, dict[str, Any]] = {}
                    else:
                        next_payload = normalize_stored_payload(section, current_payload, default_origin='db')
                        before_payload = normalize_stored_payload(section, current_payload, default_origin='db')

                    current_field_payload = next_payload.get(field) or {}
                    if not should_backfill_secret_field(current_field_payload):
                        continue

                    encrypted_value = encrypt_runtime_secret_value(env_value)
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
        raise db_unavailable_error_cls(f'runtime settings tables missing: {exc}') from exc
    except Exception as exc:
        raise db_unavailable_error_cls(str(exc)) from exc

    if updated_fields:
        invalidate_runtime_settings_cache()

    return {
        'updated_fields': tuple(updated_fields),
        'updated_sections': tuple(sorted(updated_sections)),
    }
