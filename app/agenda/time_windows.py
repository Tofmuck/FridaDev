from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def build_canonical_time_windows(*, now_iso: str, timezone_name: str) -> dict[str, dict[str, str]]:
    now_utc = _parse_iso_utc(now_iso)
    if now_utc is None:
        return {}
    tz = _zoneinfo(timezone_name)
    local_today = now_utc.astimezone(tz).date()
    return {
        'today': _day_window(local_today, tz=tz),
        'tomorrow': _day_window(local_today + timedelta(days=1), tz=tz),
    }


def _day_window(day: date, *, tz) -> dict[str, str]:
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return {
        'start': _to_utc_iso(start_local),
        'end': _to_utc_iso(end_local),
        'timezone': _timezone_name(tz),
        'local_date': day.isoformat(),
    }


def _parse_iso_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _zoneinfo(timezone_name: str):
    raw = str(timezone_name or '').strip()
    if not raw:
        return timezone.utc
    try:
        return ZoneInfo(raw)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def _timezone_name(tz) -> str:
    return str(getattr(tz, 'key', '') or 'UTC')


def _to_utc_iso(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace('+00:00', 'Z')
    )
