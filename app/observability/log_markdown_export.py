from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

import psycopg

import config
from admin import runtime_settings
from core import runtime_db_bootstrap

logger = logging.getLogger('frida.log_markdown_export')

_MAX_PAYLOAD_KEYS = 12
_MAX_LIST_PREVIEW = 3
_MAX_TEXT_CHARS = 140


def _conn() -> Any:
    return runtime_db_bootstrap.connect_runtime_database(
        psycopg,
        config,
        runtime_settings,
    )


def _compact_text(value: Any, *, max_chars: int = _MAX_TEXT_CHARS) -> str:
    text = str(value or '')
    normalized = ' '.join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + '...'


def _compact_value(value: Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f'`{_compact_text(value)}`'
    if isinstance(value, list):
        if not value:
            return '`[]`'
        preview = ', '.join(_compact_text(entry, max_chars=48) for entry in value[:_MAX_LIST_PREVIEW])
        if len(value) > _MAX_LIST_PREVIEW:
            return f'`[{preview}, ...] ({len(value)})`'
        return f'`[{preview}]`'
    if isinstance(value, dict):
        keys = sorted(str(key) for key in value.keys())
        preview = ', '.join(keys[:_MAX_LIST_PREVIEW])
        if len(keys) > _MAX_LIST_PREVIEW:
            return f'`{{{preview}, ...}} ({len(keys)} keys)`'
        return f'`{{{preview}}}`'
    return f'`{_compact_text(value)}`'


def _payload_lines(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not payload:
        return ['- payload: `(none)`']

    keys = sorted(str(key) for key in payload.keys())
    lines = ['- payload:']
    for key in keys[:_MAX_PAYLOAD_KEYS]:
        lines.append(f'  - `{_compact_text(key, max_chars=64)}`: {_compact_value(payload.get(key))}')

    remaining = len(keys) - _MAX_PAYLOAD_KEYS
    if remaining > 0:
        lines.append(f'  - `_truncated_keys`: `{remaining}`')
    return lines


def _normalize_scope(conversation_id: str | None, turn_id: str | None) -> tuple[str, str | None, str]:
    conversation_id_s = str(conversation_id or '').strip()
    turn_id_s = str(turn_id or '').strip() or None

    if not conversation_id_s:
        raise ValueError('conversation_id is required for markdown export')

    scope = 'turn' if turn_id_s else 'conversation'
    return conversation_id_s, turn_id_s, scope


def _read_scope_events(
    *,
    conversation_id: str,
    turn_id: str | None,
    conn_factory: Callable[[], Any],
) -> list[dict[str, Any]]:
    where_clauses = ['conversation_id = %s']
    params: list[Any] = [conversation_id]
    if turn_id:
        where_clauses.append('turn_id = %s')
        params.append(turn_id)

    where_sql = ' AND '.join(where_clauses)
    rows: list[tuple[Any, ...]] = []
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT
                        event_id,
                        conversation_id,
                        turn_id,
                        ts,
                        stage,
                        status,
                        duration_ms,
                        payload_json
                    FROM observability.chat_log_events
                    WHERE {where_sql}
                    ORDER BY ts ASC, event_id ASC
                    ''',
                    tuple(params),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger.error(
            'chat_log_markdown_export_read_failed conversation_id=%s turn_id=%s err=%s',
            conversation_id,
            turn_id,
            exc,
        )
        raise RuntimeError('chat log markdown export read failed') from exc

    items: list[dict[str, Any]] = []
    for row in rows:
        ts = row[3]
        payload_json = row[7] if isinstance(row[7], dict) else {}
        items.append(
            {
                'event_id': str(row[0] or ''),
                'conversation_id': str(row[1] or ''),
                'turn_id': str(row[2] or ''),
                'ts': ts.astimezone(timezone.utc).isoformat() if isinstance(ts, datetime) else str(ts or ''),
                'stage': str(row[4] or ''),
                'status': str(row[5] or ''),
                'duration_ms': int(row[6]) if row[6] is not None else None,
                'payload': payload_json,
            }
        )
    return items


def _build_markdown(
    *,
    scope: str,
    conversation_id: str,
    turn_id: str | None,
    items: list[dict[str, Any]],
    generated_at: datetime,
) -> str:
    generated_iso = generated_at.astimezone(timezone.utc).isoformat()
    lines = [
        '# Frida Chat Logs Export',
        '',
        f'- scope: `{scope}`',
        f'- conversation_id: `{conversation_id}`',
    ]
    if turn_id:
        lines.append(f'- turn_id: `{turn_id}`')
    lines.extend(
        [
            f'- generated_at: `{generated_iso}`',
            f'- events_count: `{len(items)}`',
            '',
            '## Events',
        ]
    )

    if not items:
        lines.append('_No log events found for this scope._')
        return '\n'.join(lines).rstrip() + '\n'

    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                '',
                f'### {index}. `{item["ts"]}` · `{item["stage"]}` · `{item["status"]}`',
                f'- event_id: `{item["event_id"]}`',
                f'- turn_id: `{item["turn_id"]}`',
            ]
        )
        if item['duration_ms'] is not None:
            lines.append(f'- duration_ms: `{item["duration_ms"]}`')
        lines.extend(_payload_lines(item.get('payload')))

    return '\n'.join(lines).rstrip() + '\n'


def export_chat_logs_markdown(
    *,
    conversation_id: str | None,
    turn_id: str | None = None,
    conn_factory: Callable[[], Any] = _conn,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    conversation_id_s, turn_id_s, scope = _normalize_scope(conversation_id, turn_id)
    items = _read_scope_events(
        conversation_id=conversation_id_s,
        turn_id=turn_id_s,
        conn_factory=conn_factory,
    )
    now = generated_at or datetime.now(timezone.utc)
    markdown = _build_markdown(
        scope=scope,
        conversation_id=conversation_id_s,
        turn_id=turn_id_s,
        items=items,
        generated_at=now,
    )
    return {
        'scope': scope,
        'conversation_id': conversation_id_s,
        'turn_id': turn_id_s,
        'events_count': len(items),
        'markdown': markdown,
    }
