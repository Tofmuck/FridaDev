from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from agenda import agent_contract as contract
from agenda import product_methods


DRAFT_KEYS = {
    'title',
    'location',
    'description',
    'calendar_id',
    'start',
    'end',
    'timezone',
    'all_day',
    'target_event_id',
    'change_summary',
}

_TEXT_LIMITS = {
    'title': 160,
    'location': 240,
    'description': 800,
    'change_summary': 400,
}
_SAFE_CODE_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-/')
_LOCAL_ID_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-')
_FORBIDDEN_MARKERS = (
    'BEGIN:VCALENDAR',
    'BEGIN:VEVENT',
    'END:VEVENT',
    'UID:',
    'ETag:',
    'SUMMARY:',
    'LOCATION:',
    'DESCRIPTION:',
    'ATTENDEE:',
    'ORGANIZER:',
    'RRULE:',
    'RDATE:',
    'EXDATE:',
    'DTSTART:',
    'DTEND:',
    'Authorization',
    'Cookie:',
    'app-password',
    'app_password',
    'value_encrypted',
    'caldav_path',
    'caldav_url',
)


def normalize_draft(value: Any) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or set(value.keys()) != DRAFT_KEYS:
        return contract.REASON_SCHEMA_INVALID
    draft: dict[str, Any] = {}
    for key in sorted(DRAFT_KEYS):
        item = value.get(key)
        if item is None:
            draft[key] = None
            continue
        if key == 'all_day':
            if not isinstance(item, bool):
                return contract.REASON_DRAFT_INVALID
            draft[key] = bool(item)
            continue
        if key in {'start', 'end'}:
            if not _valid_iso_text(item, allow_empty=True):
                return contract.REASON_DRAFT_INVALID
            draft[key] = str(item or '').strip()
            continue
        if key == 'timezone':
            if not _valid_timezone(item, allow_empty=True):
                return contract.REASON_DRAFT_INVALID
            draft[key] = str(item or '').strip()
            continue
        if key in {'calendar_id', 'target_event_id'}:
            if not _valid_local_identifier(item, allow_empty=True):
                return contract.REASON_DRAFT_INVALID
            draft[key] = str(item or '').strip()
            continue
        if key in _TEXT_LIMITS:
            if not _valid_human_text(item, max_chars=_TEXT_LIMITS[key], allow_empty=True):
                return contract.REASON_DRAFT_INVALID
            draft[key] = str(item or '').strip()
            continue
        return contract.REASON_SCHEMA_INVALID
    return draft


def validate_product_draft(
    method: product_methods.AgendaProductMethod,
    draft: Mapping[str, Any],
    calendar_scope: Mapping[str, Any],
) -> str:
    if method.family != product_methods.FAMILY_PROPOSE:
        return ''
    operation = method.mutation_kind
    if operation == 'create':
        if not _text(draft.get('title')):
            return contract.REASON_DRAFT_INVALID
        if not _calendar_id(draft, calendar_scope):
            return contract.REASON_DRAFT_INVALID
        if not _text(draft.get('start')) or not _text(draft.get('end')) or not _text(draft.get('timezone')):
            return contract.REASON_DRAFT_INVALID
        return ''
    if operation == 'update':
        if not _has_update_change(draft):
            return contract.REASON_DRAFT_INVALID
        return ''
    if operation == 'delete':
        return ''
    return ''


def _has_update_change(draft: Mapping[str, Any]) -> bool:
    for key in ('title', 'location', 'description', 'start', 'end'):
        if _text(draft.get(key)):
            return True
    return False


def _calendar_id(draft: Mapping[str, Any], calendar_scope: Mapping[str, Any]) -> str:
    explicit = _text(draft.get('calendar_id'))
    if explicit:
        return explicit
    calendar_ids = calendar_scope.get('calendar_ids') or ()
    if isinstance(calendar_ids, (str, bytes)):
        return ''
    values = [str(item or '').strip() for item in calendar_ids if str(item or '').strip()]
    return values[0] if len(values) == 1 else ''


def _valid_human_text(value: Any, *, max_chars: int, allow_empty: bool) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return allow_empty
    if len(text) > max_chars or any(char in text for char in '\r\t'):
        return False
    return not _contains_forbidden_marker(text) and not _dangerous_text(text)


def _valid_iso_text(value: Any, *, allow_empty: bool) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return allow_empty
    if len(text) > 64 or _dangerous_text(text):
        return False
    try:
        datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return False
    return True


def _valid_timezone(value: Any, *, allow_empty: bool) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return allow_empty
    return len(text) <= 80 and not _dangerous_text(text) and all(char in _SAFE_CODE_CHARS for char in text)


def _valid_local_identifier(value: Any, *, allow_empty: bool) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return allow_empty
    if len(text) > 80 or _dangerous_text(text):
        return False
    return all(char in _LOCAL_ID_CHARS for char in text)


def _contains_forbidden_marker(value: Any) -> bool:
    lower = str(value or '').lower()
    return any(marker.lower() in lower for marker in _FORBIDDEN_MARKERS)


def _dangerous_text(value: Any) -> bool:
    text = str(value or '').strip()
    lower = text.lower()
    if _contains_forbidden_marker(text):
        return True
    if '://' in lower or lower.startswith(('http:', 'https:', 'webcal:', 'caldav:')):
        return True
    if lower.startswith('/remote.php/') or '/remote.php/dav' in lower or '/calendars/' in lower:
        return True
    if lower.startswith(('uid:', 'uid=', 'etag:', 'etag=')):
        return True
    secret_markers = ('authorization', 'bearer ', 'cookie', 'token', 'app-password', 'app_password')
    return any(marker in lower for marker in secret_markers)


def _text(value: Any) -> str:
    return str(value or '').strip()
