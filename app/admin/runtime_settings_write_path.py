from __future__ import annotations

import json
from typing import Any, Callable, Mapping

from admin import runtime_secrets
from admin.runtime_settings_spec import get_field_spec, get_section_spec


RuntimeRows = dict[str, dict[str, dict[str, Any]]]


def runtime_validation_failure_message(section: str, validation: Mapping[str, Any]) -> str:
    failed_checks = [
        check
        for check in validation.get('checks', [])
        if isinstance(check, Mapping) and not bool(check.get('ok'))
    ]
    details = '; '.join(
        f"{str(check.get('name') or 'check')}: {str(check.get('detail') or '').strip()}"
        for check in failed_checks[:4]
    )
    message = f'runtime settings validation failed for {section}'
    if details:
        message = f'{message}: {details}'
    return message


def coerce_field_value(
    section: str,
    field: str,
    value: Any,
    *,
    validation_error_cls: type[Exception],
) -> Any:
    spec = get_field_spec(section, field)
    field_ref = f'{section}.{field}'

    if spec.value_type == 'text':
        if not isinstance(value, str):
            raise validation_error_cls(f'invalid text value for {field_ref}')
        return value

    if spec.value_type == 'int':
        if isinstance(value, bool) or not isinstance(value, int):
            raise validation_error_cls(f'invalid int value for {field_ref}')
        return int(value)

    if spec.value_type == 'float':
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise validation_error_cls(f'invalid float value for {field_ref}')
        return float(value)

    raise validation_error_cls(f'unsupported value type for {field_ref}: {spec.value_type}')


def normalize_admin_patch_payload(
    section: str,
    payload: Mapping[str, Any],
    *,
    validation_error_cls: type[Exception],
    encrypt_runtime_secret_value: Callable[[str], str],
) -> dict[str, dict[str, Any]]:
    get_section_spec(section)
    if not isinstance(payload, Mapping) or not payload:
        raise validation_error_cls(f'patch payload must be a non-empty mapping for {section}')

    normalized: dict[str, dict[str, Any]] = {}
    for field_name, raw_value in payload.items():
        try:
            spec = get_field_spec(section, str(field_name))
        except KeyError as exc:
            raise validation_error_cls(str(exc)) from exc
        field_ref = f'{section}.{field_name}'

        if not isinstance(raw_value, Mapping):
            raise validation_error_cls(f'field patch must be a mapping for {field_ref}')

        if spec.is_secret:
            has_replace_value = 'replace_value' in raw_value
            has_plain_value = 'value' in raw_value
            has_encrypted_value = 'value_encrypted' in raw_value

            if has_plain_value or has_encrypted_value:
                raise validation_error_cls(
                    f'ambiguous secret patch payload for {field_ref}: use replace_value only'
                )
            if not has_replace_value:
                raise validation_error_cls(f'missing replace_value for {field_ref}')

            replace_value = raw_value.get('replace_value')
            if not isinstance(replace_value, str):
                raise validation_error_cls(f'invalid text value for {field_ref}')
            try:
                encrypted_value = encrypt_runtime_secret_value(replace_value)
            except runtime_secrets.RuntimeSettingsCryptoKeyMissingError as exc:
                raise validation_error_cls(str(exc)) from exc
            except runtime_secrets.RuntimeSettingsCryptoEngineError as exc:
                raise validation_error_cls(f'failed to encrypt secret for {field_ref}') from exc

            normalized[str(field_name)] = {
                'is_secret': True,
                'is_set': True,
                'origin': 'admin_ui',
                'value_encrypted': encrypted_value,
            }
            continue

        if 'value' not in raw_value:
            raise validation_error_cls(f'missing value for {field_ref}')

        normalized[str(field_name)] = {
            'value': coerce_field_value(
                section,
                str(field_name),
                raw_value.get('value'),
                validation_error_cls=validation_error_cls,
            ),
            'is_secret': False,
            'origin': 'admin_ui',
        }

    return normalized


def update_runtime_section(
    section: str,
    patch_payload: Mapping[str, Any],
    *,
    updated_by: str,
    fetcher: Callable[[], RuntimeRows] | None,
    dsn: str,
    get_runtime_section: Callable[..., Any],
    normalize_admin_patch_payload: Callable[[str, Mapping[str, Any]], dict[str, dict[str, Any]]],
    normalize_stored_payload: Callable[..., dict[str, dict[str, Any]]],
    redact_payload_for_api: Callable[[str, Mapping[str, Any]], dict[str, dict[str, Any]]],
    validate_runtime_section: Callable[..., dict[str, Any]],
    invalidate_runtime_settings_cache: Callable[[], None],
    runtime_section_view_cls: type,
    validation_error_cls: type[Exception],
    db_unavailable_error_cls: type[Exception],
) -> Any:
    actor = str(updated_by or '').strip() or 'admin_api'
    validation = validate_runtime_section(section, patch_payload=patch_payload, fetcher=fetcher)
    if not validation.get('valid'):
        raise validation_error_cls(runtime_validation_failure_message(section, validation))

    normalized_patch = normalize_admin_patch_payload(section, patch_payload)
    current_view = get_runtime_section(section, fetcher=fetcher)
    next_payload = normalize_stored_payload(section, current_view.payload, default_origin=current_view.source_reason)
    next_payload.update(normalized_patch)

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
        raise db_unavailable_error_cls(f'runtime settings tables missing: {exc}') from exc
    except Exception as exc:
        raise db_unavailable_error_cls(str(exc)) from exc

    invalidate_runtime_settings_cache()
    return runtime_section_view_cls(
        section=section,
        payload=redact_payload_for_api(section, next_payload),
        source='db',
        source_reason='db_row',
    )
