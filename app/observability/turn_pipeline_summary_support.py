from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from observability import agentic_status


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if number != number or number in {float('inf'), float('-inf')}:
        return 0.0
    return round(number, 3)


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def _text(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = event.get('payload')
    if not isinstance(payload, Mapping):
        payload = event.get('payload_json')
    return _mapping(payload)


def _stage(event: Mapping[str, Any]) -> str:
    return str(event.get('stage') or '').strip()


def _status(event: Mapping[str, Any]) -> str:
    return agentic_status.normalize_status(event.get('status_v1') or event.get('status'))


def _event_ts(event: Mapping[str, Any]) -> str | None:
    return _text(event.get('ts'))


def _event_sort_key(event: Mapping[str, Any]) -> tuple[str, str]:
    return str(event.get('ts') or ''), str(event.get('event_id') or '')


def _safe_events(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        [event for event in events if isinstance(event, Mapping)],
        key=_event_sort_key,
    )


def _events_for_stage(events: Sequence[Mapping[str, Any]], stage: str) -> list[Mapping[str, Any]]:
    return [event for event in events if _stage(event) == stage]


def _latest_stage_event(events: Sequence[Mapping[str, Any]], stage: str) -> Mapping[str, Any] | None:
    items = _events_for_stage(events, stage)
    return items[-1] if items else None


def _reason_code(payload: Mapping[str, Any]) -> str | None:
    for key in ('reason_code', 'error_code', 'error_class'):
        text = _text(payload.get(key))
        if text:
            return text
    return None


def _sha256_12_from_payload(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _text(payload.get(key))
        if value:
            return value[:12]
    return None


def _sha256_12_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _duration_ms(event: Mapping[str, Any] | None) -> int | None:
    if not event:
        return None
    value = event.get('duration_ms')
    if value is None:
        return None
    return _to_int(value)
