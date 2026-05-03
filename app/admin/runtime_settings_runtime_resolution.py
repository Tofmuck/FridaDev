from __future__ import annotations

from typing import Any, Callable, Mapping

from admin import runtime_secrets
from admin.runtime_settings_spec import SECTION_NAMES, get_field_spec, get_section_spec


RuntimeRows = dict[str, dict[str, dict[str, Any]]]
NormalizeStoredPayload = Callable[..., dict[str, dict[str, Any]]]

_SNAPSHOT_CACHE: Any | None = None


def invalidate_runtime_settings_cache() -> None:
    global _SNAPSHOT_CACHE
    _SNAPSHOT_CACHE = None


def load_snapshot(
    *,
    fetcher: Callable[[], RuntimeRows] | None,
    default_fetcher: Callable[[], RuntimeRows],
    runtime_settings_snapshot_cls: type,
    db_unavailable_error_cls: type[Exception],
) -> Any:
    global _SNAPSHOT_CACHE

    use_cache = fetcher is None
    if use_cache and _SNAPSHOT_CACHE is not None:
        return _SNAPSHOT_CACHE

    active_fetcher = fetcher or default_fetcher
    try:
        rows = active_fetcher()
    except db_unavailable_error_cls:
        snapshot = runtime_settings_snapshot_cls(rows={}, db_state='db_unavailable')
    else:
        snapshot = runtime_settings_snapshot_cls(
            rows=rows,
            db_state='db_rows' if rows else 'empty_table',
        )

    if use_cache:
        _SNAPSHOT_CACHE = snapshot
    return snapshot


def env_payload_for_runtime(section: str, *, build_env_seed_bundle: Callable[[str], Any]) -> dict[str, dict[str, Any]]:
    return build_env_seed_bundle(section).payload


def get_runtime_section(
    section: str,
    *,
    fetcher: Callable[[], RuntimeRows] | None,
    default_fetcher: Callable[[], RuntimeRows],
    build_env_seed_bundle: Callable[[str], Any],
    runtime_settings_snapshot_cls: type,
    runtime_section_view_cls: type,
    db_unavailable_error_cls: type[Exception],
) -> Any:
    get_section_spec(section)
    snapshot = load_snapshot(
        fetcher=fetcher,
        default_fetcher=default_fetcher,
        runtime_settings_snapshot_cls=runtime_settings_snapshot_cls,
        db_unavailable_error_cls=db_unavailable_error_cls,
    )

    payload = snapshot.rows.get(section)
    if payload is not None:
        return runtime_section_view_cls(
            section=section,
            payload=payload,
            source='db',
            source_reason='db_row',
        )

    source_reason = 'missing_section' if snapshot.db_state == 'db_rows' else snapshot.db_state
    return runtime_section_view_cls(
        section=section,
        payload=env_payload_for_runtime(section, build_env_seed_bundle=build_env_seed_bundle),
        source='env',
        source_reason=source_reason,
    )


def get_runtime_section_for_api(
    section: str,
    *,
    fetcher: Callable[[], RuntimeRows] | None,
    default_fetcher: Callable[[], RuntimeRows],
    build_env_seed_bundle: Callable[[str], Any],
    runtime_settings_snapshot_cls: type,
    runtime_section_view_cls: type,
    db_unavailable_error_cls: type[Exception],
    redact_payload_for_api: Callable[[str, Mapping[str, Any]], dict[str, dict[str, Any]]],
) -> Any:
    view = get_runtime_section(
        section,
        fetcher=fetcher,
        default_fetcher=default_fetcher,
        build_env_seed_bundle=build_env_seed_bundle,
        runtime_settings_snapshot_cls=runtime_settings_snapshot_cls,
        runtime_section_view_cls=runtime_section_view_cls,
        db_unavailable_error_cls=db_unavailable_error_cls,
    )
    return runtime_section_view_cls(
        section=view.section,
        payload=redact_payload_for_api(section, view.payload),
        source=view.source,
        source_reason=view.source_reason,
    )


def get_runtime_status(
    *,
    fetcher: Callable[[], RuntimeRows] | None,
    default_fetcher: Callable[[], RuntimeRows],
    runtime_settings_snapshot_cls: type,
    db_unavailable_error_cls: type[Exception],
) -> dict[str, Any]:
    snapshot = load_snapshot(
        fetcher=fetcher,
        default_fetcher=default_fetcher,
        runtime_settings_snapshot_cls=runtime_settings_snapshot_cls,
        db_unavailable_error_cls=db_unavailable_error_cls,
    )
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


def require_secret_configured(
    view: Any,
    field: str,
    *,
    secret_required_error_cls: type[Exception],
) -> None:
    spec = get_field_spec(view.section, field)
    if not spec.is_secret:
        raise ValueError(f'field is not secret: {view.section}.{field}')

    payload = view.payload.get(field) or {}
    if bool(payload.get('is_set')):
        return

    raise secret_required_error_cls(
        f'missing secret config: {view.section}.{field} (source={view.source}, reason={view.source_reason})'
    )


def resolve_runtime_secret_from_view(
    view: Any,
    field: str,
    *,
    seed_value: Callable[[str, str], Any],
    runtime_secret_value_cls: type,
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> Any:
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
            raise secret_resolution_error_cls(
                f'missing runtime settings crypto key while decrypting {field_ref}'
            ) from exc
        except runtime_secrets.RuntimeSettingsCryptoEngineError as exc:
            raise secret_resolution_error_cls(
                f'failed to decrypt runtime secret {field_ref}: {exc}'
            ) from exc

        if not str(decrypted_value or '').strip():
            raise secret_resolution_error_cls(
                f'empty decrypted runtime secret: {field_ref}'
            )

        return runtime_secret_value_cls(
            section=view.section,
            field=field,
            value=str(decrypted_value),
            source='db_encrypted',
            source_reason=view.source_reason,
        )

    env_value = str(seed_value(view.section, field) or '').strip()
    if payload.get('origin') == 'env_seed' and env_value:
        return runtime_secret_value_cls(
            section=view.section,
            field=field,
            value=env_value,
            source='env_fallback',
            source_reason=view.source_reason,
        )

    if view.source in {'db', 'candidate'} and is_set:
        raise secret_resolution_error_cls(
            f'secret marked as set but no decryptable value is available: {field_ref}'
        )

    raise secret_required_error_cls(
        f'missing secret config: {field_ref} (source={view.source}, reason={view.source_reason})'
    )


def get_runtime_secret_value(
    section: str,
    field: str,
    *,
    fetcher: Callable[[], RuntimeRows] | None,
    default_fetcher: Callable[[], RuntimeRows],
    build_env_seed_bundle: Callable[[str], Any],
    runtime_settings_snapshot_cls: type,
    runtime_section_view_cls: type,
    db_unavailable_error_cls: type[Exception],
    seed_value: Callable[[str, str], Any],
    runtime_secret_value_cls: type,
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> Any:
    view = get_runtime_section(
        section,
        fetcher=fetcher,
        default_fetcher=default_fetcher,
        build_env_seed_bundle=build_env_seed_bundle,
        runtime_settings_snapshot_cls=runtime_settings_snapshot_cls,
        runtime_section_view_cls=runtime_section_view_cls,
        db_unavailable_error_cls=db_unavailable_error_cls,
    )
    return resolve_runtime_secret_from_view(
        view,
        field,
        seed_value=seed_value,
        runtime_secret_value_cls=runtime_secret_value_cls,
        secret_required_error_cls=secret_required_error_cls,
        secret_resolution_error_cls=secret_resolution_error_cls,
    )


def effective_runtime_payload(
    section: str,
    payload: Mapping[str, Any],
    *,
    build_env_seed_bundle: Callable[[str], Any],
    normalize_stored_payload: NormalizeStoredPayload,
) -> dict[str, dict[str, Any]]:
    effective = normalize_stored_payload(
        section,
        build_env_seed_bundle(section).payload,
        default_origin='env_seed',
    )
    effective.update(normalize_stored_payload(section, payload, default_origin='db'))
    return effective


def candidate_runtime_section(
    section: str,
    *,
    patch_payload: Mapping[str, Any] | None,
    fetcher: Callable[[], RuntimeRows] | None,
    get_runtime_section: Callable[..., Any],
    build_env_seed_bundle: Callable[[str], Any],
    normalize_stored_payload: NormalizeStoredPayload,
    normalize_admin_patch_payload: Callable[[str, Mapping[str, Any]], dict[str, dict[str, Any]]],
    runtime_section_view_cls: type,
) -> Any:
    current_view = get_runtime_section(section, fetcher=fetcher)
    candidate_payload = effective_runtime_payload(
        section,
        current_view.payload,
        build_env_seed_bundle=build_env_seed_bundle,
        normalize_stored_payload=normalize_stored_payload,
    )
    if patch_payload:
        candidate_payload.update(normalize_admin_patch_payload(section, patch_payload))
        return runtime_section_view_cls(
            section=section,
            payload=candidate_payload,
            source='candidate',
            source_reason='validate_payload',
        )

    return runtime_section_view_cls(
        section=section,
        payload=candidate_payload,
        source=current_view.source,
        source_reason=current_view.source_reason,
    )
