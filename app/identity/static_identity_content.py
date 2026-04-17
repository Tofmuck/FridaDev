from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from admin import runtime_settings
from identity import static_identity_paths


logger = logging.getLogger('frida.identity.static_content')

STATIC_STORAGE_KIND = 'resource_path'
ACTIVE_STATIC_SOURCE = 'resource_path_content'
STATIC_EDIT_ROUTE = '/api/admin/identity/static'
_STATIC_IDENTITY_METADATA_SUFFIX = '.identity-meta.json'
_SUBJECT_RESOURCE_FIELDS = {
    'llm': 'llm_identity_path',
    'user': 'user_identity_path',
}


class StaticIdentityContentError(RuntimeError):
    error_code = 'static_identity_content_error'


class StaticIdentityResourceUnresolvedError(StaticIdentityContentError):
    error_code = 'static_identity_resource_unresolved'


class StaticIdentityResourceOutsideAllowedRootsError(StaticIdentityContentError):
    error_code = 'static_identity_resource_outside_allowed_roots'


class StaticIdentityWriteError(StaticIdentityContentError):
    error_code = 'static_identity_write_failed'


@dataclass(frozen=True)
class StaticIdentitySnapshot:
    subject: str
    resource_field: str
    configured_path: str
    resolution_kind: str
    resolved_path: Path | None
    content: str
    raw_content: str = ''
    within_allowed_roots: bool = False
    storage_kind: str = STATIC_STORAGE_KIND
    source_kind: str = ACTIVE_STATIC_SOURCE
    editable_via: str = STATIC_EDIT_ROUTE
    updated_by: str = ''
    update_reason: str = ''
    updated_ts: str = ''

    @property
    def resolved_path_str(self) -> str | None:
        if self.resolved_path is None:
            return None
        return str(self.resolved_path)

    @property
    def stored(self) -> bool:
        return bool(self.raw_content)


def resource_field_for_subject(subject: str) -> str:
    return _SUBJECT_RESOURCE_FIELDS.get(str(subject or '').strip().lower(), '')


def normalize_runtime_static_content(raw_content: str) -> str:
    return str(raw_content or '').strip()


def _text(value: Any) -> str:
    return str(value or '').strip()


def _metadata_path(path: Path) -> Path:
    return path.with_name(f'.{path.name}{_STATIC_IDENTITY_METADATA_SUFFIX}')


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _metadata_payload(
    *,
    updated_by: str,
    update_reason: str,
    updated_ts: str | None,
) -> dict[str, str]:
    return {
        'updated_by': _text(updated_by),
        'update_reason': _text(update_reason),
        'updated_ts': _text(updated_ts) or _utc_now_iso(),
    }


def _read_write_metadata(path: Path) -> dict[str, str]:
    metadata_path = _metadata_path(path)
    if not metadata_path.is_file():
        return {
            'updated_by': '',
            'update_reason': '',
            'updated_ts': '',
        }
    try:
        payload = json.loads(metadata_path.read_text(encoding='utf-8'))
    except Exception as exc:
        logger.warning(
            'static_identity_metadata_read_error resolved_path=%s metadata_path=%s err=%s',
            path,
            metadata_path,
            exc,
        )
        return {
            'updated_by': '',
            'update_reason': '',
            'updated_ts': '',
        }
    if not isinstance(payload, dict):
        return {
            'updated_by': '',
            'update_reason': '',
            'updated_ts': '',
        }
    return {
        'updated_by': _text(payload.get('updated_by')),
        'update_reason': _text(payload.get('update_reason')),
        'updated_ts': _text(payload.get('updated_ts')),
    }


def _replace_text_file(
    path: Path,
    content: str,
    *,
    target_mode: int,
    target_uid: int,
    target_gid: int,
) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            handle.write(str(content))
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        temp_stat = temp_path.stat()
        if stat.S_IMODE(temp_stat.st_mode) != target_mode:
            os.chmod(temp_path, target_mode)
        if temp_stat.st_uid != target_uid or temp_stat.st_gid != target_gid:
            os.chown(temp_path, target_uid, target_gid)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _write_metadata_file(
    path: Path,
    *,
    updated_by: str,
    update_reason: str,
    updated_ts: str | None,
) -> None:
    metadata_path = _metadata_path(path)
    reference_stat = metadata_path.stat() if metadata_path.exists() else path.stat()
    payload = _metadata_payload(
        updated_by=updated_by,
        update_reason=update_reason,
        updated_ts=updated_ts,
    )
    _replace_text_file(
        metadata_path,
        json.dumps(payload, ensure_ascii=True, sort_keys=True) + '\n',
        target_mode=stat.S_IMODE(reference_stat.st_mode),
        target_uid=reference_stat.st_uid,
        target_gid=reference_stat.st_gid,
    )


def _runtime_resource_path(field: str, *, runtime_settings_module: Any = runtime_settings) -> str:
    view = runtime_settings_module.get_resources_settings()
    payload = view.payload.get(field) or {}
    if 'value' in payload:
        return str(payload['value'])

    env_bundle = runtime_settings_module.build_env_seed_bundle('resources')
    fallback = env_bundle.payload.get(field) or {}
    if 'value' in fallback:
        return str(fallback['value'])

    raise KeyError(f'missing resources runtime value: {field}')


def resolve_active_static_identity(subject: str, *, runtime_settings_module: Any = runtime_settings) -> StaticIdentitySnapshot:
    normalized_subject = str(subject or '').strip().lower()
    resource_field = resource_field_for_subject(normalized_subject)
    if not resource_field:
        raise ValueError(f'unsupported static identity subject: {subject!r}')

    configured_path = _runtime_resource_path(resource_field, runtime_settings_module=runtime_settings_module)
    resolution = static_identity_paths.resolve_static_identity_path(configured_path)
    return StaticIdentitySnapshot(
        subject=normalized_subject,
        resource_field=resource_field,
        configured_path=configured_path,
        resolution_kind=resolution.resolution_kind,
        resolved_path=resolution.resolved_path,
        content='',
        raw_content='',
        within_allowed_roots=resolution.within_allowed_roots,
    )


def read_static_identity_snapshot(
    subject: str,
    *,
    runtime_settings_module: Any = runtime_settings,
) -> StaticIdentitySnapshot:
    resolved = resolve_active_static_identity(subject, runtime_settings_module=runtime_settings_module)
    raw_content = ''
    content = ''
    metadata = {
        'updated_by': '',
        'update_reason': '',
        'updated_ts': '',
    }
    if resolved.resolved_path is not None and resolved.within_allowed_roots:
        try:
            raw_content = resolved.resolved_path.read_text(encoding='utf-8')
            content = normalize_runtime_static_content(raw_content)
            metadata = _read_write_metadata(resolved.resolved_path)
        except Exception as exc:
            logger.warning(
                'static_identity_read_error subject=%s configured_path=%s resolved_path=%s resolution=%s err=%s',
                resolved.subject,
                resolved.configured_path,
                resolved.resolved_path,
                resolved.resolution_kind,
                exc,
            )
            raw_content = ''
            content = ''
    elif resolved.resolved_path is not None:
        logger.warning(
            'static_identity_outside_allowed_roots subject=%s configured_path=%s resolved_path=%s resolution=%s',
            resolved.subject,
            resolved.configured_path,
            resolved.resolved_path,
            resolved.resolution_kind,
        )
    return StaticIdentitySnapshot(
        subject=resolved.subject,
        resource_field=resolved.resource_field,
        configured_path=resolved.configured_path,
        resolution_kind=resolved.resolution_kind,
        resolved_path=resolved.resolved_path,
        content=content,
        raw_content=raw_content,
        within_allowed_roots=resolved.within_allowed_roots,
        updated_by=metadata['updated_by'],
        update_reason=metadata['update_reason'],
        updated_ts=metadata['updated_ts'],
    )


def read_static_identity_text(
    subject: str,
    *,
    runtime_settings_module: Any = runtime_settings,
) -> str:
    return read_static_identity_snapshot(subject, runtime_settings_module=runtime_settings_module).content


def write_static_identity_content(
    subject: str,
    content: str,
    *,
    runtime_settings_module: Any = runtime_settings,
    updated_by: str = 'system',
    update_reason: str = '',
    updated_ts: str | None = None,
) -> StaticIdentitySnapshot:
    resolved = resolve_active_static_identity(subject, runtime_settings_module=runtime_settings_module)
    path = resolved.resolved_path
    if path is None or not path.is_file():
        raise StaticIdentityResourceUnresolvedError(
            f'unresolved static identity resource for {resolved.resource_field}: {resolved.configured_path}'
        )
    if not resolved.within_allowed_roots:
        raise StaticIdentityResourceOutsideAllowedRootsError(
            f'static identity resource outside allowed roots for {resolved.resource_field}: {resolved.configured_path}'
        )

    original_snapshot = read_static_identity_snapshot(subject, runtime_settings_module=runtime_settings_module)
    target_stat = path.stat()
    target_mode = stat.S_IMODE(target_stat.st_mode)
    original_raw_content = original_snapshot.raw_content
    original_metadata = {
        'updated_by': _text(original_snapshot.updated_by),
        'update_reason': _text(original_snapshot.update_reason),
        'updated_ts': _text(original_snapshot.updated_ts),
    }
    metadata_path = _metadata_path(path)
    had_metadata_file = metadata_path.exists()
    wrote_content = False
    try:
        _replace_text_file(
            path,
            str(content),
            target_mode=target_mode,
            target_uid=target_stat.st_uid,
            target_gid=target_stat.st_gid,
        )
        wrote_content = True
        _write_metadata_file(
            path,
            updated_by=updated_by,
            update_reason=update_reason,
            updated_ts=updated_ts,
        )
    except Exception as exc:
        if wrote_content:
            try:
                _replace_text_file(
                    path,
                    original_raw_content,
                    target_mode=target_mode,
                    target_uid=target_stat.st_uid,
                    target_gid=target_stat.st_gid,
                )
                if had_metadata_file or any(original_metadata.values()):
                    _write_metadata_file(path, **original_metadata)
                else:
                    metadata_path.unlink(missing_ok=True)
            except Exception as rollback_exc:
                logger.warning(
                    'static_identity_write_rollback_failed subject=%s configured_path=%s resolved_path=%s err=%s',
                    resolved.subject,
                    resolved.configured_path,
                    resolved.resolved_path,
                    rollback_exc,
                )
        raise StaticIdentityWriteError(
            f'failed to write static identity content for {resolved.resource_field}'
        ) from exc

    return read_static_identity_snapshot(subject, runtime_settings_module=runtime_settings_module)
