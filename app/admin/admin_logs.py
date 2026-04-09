from __future__ import annotations

import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _repo_log_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'logs' / 'admin.log.jsonl'


def _container_log_path() -> Path:
    return Path('/app/logs/admin.log.jsonl')


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _parent_is_writable(path: Path) -> bool:
    parent = _nearest_existing_parent(path)
    return os.access(parent, os.W_OK | os.X_OK)


def _resolve_log_path() -> Path:
    raw = os.environ.get('FRIDA_ADMIN_LOG_PATH')
    if raw:
        return Path(raw).resolve()

    container_path = _container_log_path().resolve()
    if _parent_is_writable(container_path):
        return container_path

    return _repo_log_path().resolve()


LOG_PATH = _resolve_log_path()
MAX_LOG_BYTES = _env_int('FRIDA_ADMIN_LOG_MAX_BYTES', 5 * 1024 * 1024)
MAX_ROTATED_FILES = _env_int('FRIDA_ADMIN_LOG_MAX_FILES', 14)

LEGACY_LOG_PATH = Path(__file__).resolve().parent / 'logs' / 'admin.log.jsonl'
logger = logging.getLogger('frida.adminlog')
_BOOTSTRAP_DONE = False

_REDACT_KEYS = {
    'message',
    'messages',
    'prompt',
    'content',
    'history',
    'system',
    'user_msg',
    'assistant_text',
}


def log_event(event: str, level: str = 'INFO', **fields: Any) -> None:
    _bootstrap_legacy_logs_if_needed()
    payload = {
        'timestamp': _now_iso(),
        'event': event,
        'level': level,
    }
    payload.update(_sanitize(fields))
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed()
        with LOG_PATH.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except Exception as exc:
        logger.error('admin_log_write_error err=%s', exc)


def read_logs(limit: int = 200) -> list[dict[str, Any]]:
    _bootstrap_legacy_logs_if_needed()
    if limit < 1:
        return []
    if not LOG_PATH.exists():
        return []
    lines: deque[str] = deque(maxlen=limit)
    try:
        with LOG_PATH.open('r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if line:
                    lines.append(line)
    except Exception as exc:
        logger.error('admin_log_read_error err=%s', exc)
        return []
    entries: list[dict[str, Any]] = []
    for line in reversed(lines):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _iter_log_paths(log_path: Path | None = None) -> list[Path]:
    root = (log_path or LOG_PATH).resolve()
    try:
        paths = list(root.parent.glob('admin*.log.jsonl'))
    except OSError:
        paths = []
    if root.exists() and root not in paths:
        paths.append(root)
    return sorted(set(paths), key=lambda path: path.name)


def _parse_iso8601_timestamp(value: Any) -> datetime | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    normalized = raw[:-1] + '+00:00' if raw.endswith('Z') else raw
    try:
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)
    except ValueError:
        return None


def _utc_iso_z(dt: datetime | None) -> str | None:
    if not isinstance(dt, datetime):
        return None
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def summarize_hermeneutic_mode_observation(
    current_mode: str,
    *,
    log_path: Path | None = None,
) -> dict[str, Any]:
    normalized_current_mode = str(current_mode or '').strip().lower()
    observations: list[dict[str, Any]] = []

    for path in _iter_log_paths(log_path):
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except OSError as exc:
            logger.error('admin_log_mode_summary_read_error file=%s err=%s', path, exc)
            continue

        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(item.get('event') or '').strip() != 'hermeneutic_mode':
                continue
            observed_mode = str(item.get('mode') or '').strip().lower()
            observed_at = _parse_iso8601_timestamp(item.get('timestamp'))
            if not observed_mode or observed_at is None:
                continue
            observations.append(
                {
                    'mode': observed_mode,
                    'observed_at': observed_at,
                }
            )

    observations.sort(key=lambda item: item['observed_at'])
    latest_observation = observations[-1] if observations else None

    summary = {
        'source': 'admin_logs_retained_observations',
        'semantics': 'current_mode_observed_segment_not_exact_switch',
        'current_mode_observed': False,
        'observed_since': None,
        'last_observed_at': None,
        'observation_count': 0,
        'previous_mode': None,
        'previous_mode_last_observed_at': None,
        'latest_observed_mode': latest_observation['mode'] if latest_observation else None,
        'latest_observed_at': _utc_iso_z(latest_observation['observed_at']) if latest_observation else None,
        'exact_switch_known': False,
    }

    if not normalized_current_mode or not latest_observation or latest_observation['mode'] != normalized_current_mode:
        return summary

    segment_start = len(observations) - 1
    while segment_start > 0 and observations[segment_start - 1]['mode'] == normalized_current_mode:
        segment_start -= 1

    current_segment = observations[segment_start:]
    previous_observation = observations[segment_start - 1] if segment_start > 0 else None

    summary.update(
        {
            'current_mode_observed': True,
            'observed_since': _utc_iso_z(current_segment[0]['observed_at']),
            'last_observed_at': _utc_iso_z(current_segment[-1]['observed_at']),
            'observation_count': len(current_segment),
            'previous_mode': previous_observation['mode'] if previous_observation else None,
            'previous_mode_last_observed_at': (
                _utc_iso_z(previous_observation['observed_at']) if previous_observation else None
            ),
        }
    )
    return summary


def _bootstrap_legacy_logs_if_needed() -> None:
    global _BOOTSTRAP_DONE
    if _BOOTSTRAP_DONE:
        return
    _BOOTSTRAP_DONE = True

    if LEGACY_LOG_PATH == LOG_PATH:
        return
    if not LEGACY_LOG_PATH.exists():
        return

    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEGACY_LOG_PATH.open('r', encoding='utf-8') as src, LOG_PATH.open('a', encoding='utf-8') as dst:
            for line in src:
                dst.write(line)
        LEGACY_LOG_PATH.unlink(missing_ok=True)
        try:
            LEGACY_LOG_PATH.parent.rmdir()
        except OSError:
            pass
        logger.info('admin_log_legacy_migrated from=%s to=%s', LEGACY_LOG_PATH, LOG_PATH)
    except Exception as exc:
        logger.error('admin_log_migration_error err=%s', exc)


def _rotate_if_needed() -> None:
    if not LOG_PATH.exists():
        return

    try:
        stat = LOG_PATH.stat()
    except OSError:
        return

    file_day = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime('%Y%m%d')
    today_day = datetime.now(timezone.utc).strftime('%Y%m%d')
    should_rotate = stat.st_size >= MAX_LOG_BYTES or file_day != today_day
    if not should_rotate:
        return

    suffix = f"{file_day}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    rotated = LOG_PATH.with_name(f'admin-{suffix}.log.jsonl')
    counter = 1
    while rotated.exists():
        rotated = LOG_PATH.with_name(f'admin-{suffix}-{counter}.log.jsonl')
        counter += 1

    try:
        LOG_PATH.replace(rotated)
    except OSError as exc:
        logger.error('admin_log_rotate_error err=%s', exc)
        return

    _prune_rotated_files()


def _prune_rotated_files() -> None:
    if MAX_ROTATED_FILES <= 0:
        return

    candidates = sorted(
        LOG_PATH.parent.glob('admin-*.log.jsonl'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in candidates[MAX_ROTATED_FILES:]:
        try:
            stale.unlink(missing_ok=True)
        except OSError as exc:
            logger.error('admin_log_prune_error file=%s err=%s', stale, exc)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(val)
            for key, val in value.items()
            if key not in _REDACT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
