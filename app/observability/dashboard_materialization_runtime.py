from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from observability import dashboard_analytics


RECENT_MATERIALIZATION_HOURS = 24
DEFAULT_STALE_GRACE_SECONDS = 30
DEFAULT_MIN_REFRESH_INTERVAL_SECONDS = 10

_REFRESH_LOCK = threading.Lock()
_REFRESH_RUNNING = False
_LAST_REFRESH_STARTED_MONOTONIC = 0.0


def _now_utc(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or '').strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text[:-1] + '+00:00' if text.endswith('Z') else text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _window_for(now: datetime) -> tuple[datetime, datetime]:
    end = _now_utc(now)
    start = end - timedelta(hours=RECENT_MATERIALIZATION_HOURS)
    return start, end


def _read_freshness(
    *,
    conn_factory: Callable[[], Any],
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT MAX(ts) FROM observability.chat_log_events')
            latest_event_ts = (cur.fetchone() or [None])[0]
            cur.execute(
                '''
                SELECT window_end, updated_ts
                FROM observability.dashboard_materialization_status
                ORDER BY updated_ts DESC
                LIMIT 1
                '''
            )
            row = cur.fetchone()
    window_end = row[0] if row else None
    updated_ts = row[1] if row else None
    return {
        'latest_event_ts': _parse_ts(latest_event_ts),
        'materialized_window_end': _parse_ts(window_end),
        'materialization_updated_ts': _parse_ts(updated_ts),
    }


def materialize_recent_dashboard_analytics(
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_dt = _now_utc(now)
    window_start, window_end = _window_for(now_dt)
    analytics = dashboard_analytics.materialize_dashboard_analytics_window(
        ts_from=_iso(window_start),
        ts_to=_iso(window_end),
        now=now_dt,
        conn_factory=conn_factory,
        logger_instance=logger_instance,
    )
    status = analytics.get('materialization_status')
    if not isinstance(status, Mapping):
        status = {}
    result = {
        'ok': True,
        'reason': str(reason or 'unspecified'),
        'window_start': _iso(window_start),
        'window_end': _iso(window_end),
        'turns_materialized_count': int(status.get('turns_materialized_count') or 0),
        'source_events_count': int(status.get('source_events_count') or 0),
        'lag_seconds': status.get('lag_seconds'),
        'status': status.get('status') or 'unknown',
        'raw_content_included': False,
        'event_limit_dependency': False,
    }
    logger_instance.info(
        'dashboard_recent_materialized reason=%s status=%s turns=%s source_events=%s lag=%s',
        result['reason'],
        result['status'],
        result['turns_materialized_count'],
        result['source_events_count'],
        result['lag_seconds'],
    )
    return result


def _run_refresh(
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    reason: str,
    now: datetime | None,
) -> dict[str, Any]:
    global _REFRESH_RUNNING
    try:
        return materialize_recent_dashboard_analytics(
            conn_factory=conn_factory,
            logger_instance=logger_instance,
            reason=reason,
            now=now,
        )
    except Exception as exc:
        logger_instance.warning(
            'dashboard_recent_materialization_failed reason=%s err=%s',
            reason,
            exc,
        )
        return {
            'ok': False,
            'reason': str(reason or 'unspecified'),
            'error_code': exc.__class__.__name__,
            'raw_content_included': False,
        }
    finally:
        with _REFRESH_LOCK:
            _REFRESH_RUNNING = False


def schedule_recent_dashboard_analytics_materialization(
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    reason: str,
    run_async: bool = True,
    now: datetime | None = None,
    min_refresh_interval_seconds: int = DEFAULT_MIN_REFRESH_INTERVAL_SECONDS,
) -> dict[str, Any]:
    global _LAST_REFRESH_STARTED_MONOTONIC
    global _REFRESH_RUNNING

    monotonic_now = time.monotonic()
    with _REFRESH_LOCK:
        if _REFRESH_RUNNING:
            return {
                'scheduled': False,
                'reason_code': 'refresh_already_running',
                'raw_content_included': False,
            }
        if (
            _LAST_REFRESH_STARTED_MONOTONIC
            and monotonic_now - _LAST_REFRESH_STARTED_MONOTONIC < max(0, int(min_refresh_interval_seconds))
        ):
            return {
                'scheduled': False,
                'reason_code': 'refresh_cooldown',
                'raw_content_included': False,
            }
        _REFRESH_RUNNING = True
        _LAST_REFRESH_STARTED_MONOTONIC = monotonic_now

    if not run_async:
        result = _run_refresh(
            conn_factory=conn_factory,
            logger_instance=logger_instance,
            reason=reason,
            now=now,
        )
        return {
            'scheduled': True,
            'async': False,
            'result': result,
            'raw_content_included': False,
        }

    thread = threading.Thread(
        target=_run_refresh,
        kwargs={
            'conn_factory': conn_factory,
            'logger_instance': logger_instance,
            'reason': reason,
            'now': now,
        },
        name='dashboard-recent-materialization',
        daemon=True,
    )
    try:
        thread.start()
    except Exception as exc:
        with _REFRESH_LOCK:
            _REFRESH_RUNNING = False
        logger_instance.warning(
            'dashboard_recent_materialization_thread_start_failed reason=%s err=%s',
            reason,
            exc,
        )
        return {
            'scheduled': False,
            'reason_code': 'thread_start_failed',
            'error_code': exc.__class__.__name__,
            'raw_content_included': False,
        }
    return {
        'scheduled': True,
        'async': True,
        'raw_content_included': False,
    }


def ensure_recent_dashboard_analytics_fresh(
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    reason: str,
    now: datetime | None = None,
    stale_grace_seconds: int = DEFAULT_STALE_GRACE_SECONDS,
) -> dict[str, Any]:
    now_dt = _now_utc(now)
    try:
        freshness = _read_freshness(conn_factory=conn_factory)
    except Exception as exc:
        logger_instance.warning('dashboard_freshness_probe_failed reason=%s err=%s', reason, exc)
        return {
            'ok': False,
            'refreshed': False,
            'reason_code': 'freshness_probe_failed',
            'error_code': exc.__class__.__name__,
            'read_now': now_dt,
            'raw_content_included': False,
        }

    latest_event_ts = freshness.get('latest_event_ts')
    materialized_window_end = freshness.get('materialized_window_end')
    if not isinstance(latest_event_ts, datetime):
        return {
            'ok': True,
            'refreshed': False,
            'reason_code': 'no_source_events',
            'read_now': now_dt,
            'raw_content_included': False,
        }
    if isinstance(materialized_window_end, datetime):
        source_lag_seconds = int((latest_event_ts - materialized_window_end).total_seconds())
        wall_lag_seconds = int((now_dt - materialized_window_end).total_seconds())
        lag_seconds = max(source_lag_seconds, wall_lag_seconds)
        if lag_seconds <= max(0, int(stale_grace_seconds)):
            return {
                'ok': True,
                'refreshed': False,
                'reason_code': 'fresh_enough',
                'lag_seconds': max(0, lag_seconds),
                'read_now': materialized_window_end,
                'raw_content_included': False,
            }

    result = schedule_recent_dashboard_analytics_materialization(
        conn_factory=conn_factory,
        logger_instance=logger_instance,
        reason=reason,
        run_async=False,
        now=now,
        min_refresh_interval_seconds=0,
    )
    scheduled = bool(result.get('scheduled'))
    materialization_result = result.get('result')
    if not isinstance(materialization_result, Mapping):
        materialization_result = {}
    return {
        'ok': scheduled or str(result.get('reason_code') or '') == 'refresh_already_running',
        'refreshed': scheduled,
        'reason_code': 'materialization_stale' if scheduled else result.get('reason_code'),
        'latest_event_ts': _iso(latest_event_ts),
        'materialized_window_end': _iso(materialized_window_end),
        'schedule': result,
        'read_now': _parse_ts(materialization_result.get('window_end')) if scheduled else now_dt,
        'raw_content_included': False,
    }
