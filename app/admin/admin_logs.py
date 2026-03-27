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


LOG_PATH = Path(os.environ.get('FRIDA_ADMIN_LOG_PATH', '/app/logs/admin.log.jsonl')).resolve()
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
