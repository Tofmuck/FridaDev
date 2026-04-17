from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Sequence


DEFAULT_BUFFER_TARGET_PAIRS = 15


def _text(value: Any) -> str:
    return str(value or '').strip()


def _serialize_ts(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return str(value.isoformat())
    return str(value)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _normalize_message(value: Any, *, expected_role: str) -> dict[str, Any] | None:
    payload = _mapping(value)
    role = _text(payload.get('role')).lower()
    if role != expected_role:
        return None
    content = _text(payload.get('content'))
    return {
        'role': expected_role,
        'content': content,
        'timestamp': _text(payload.get('timestamp')) or None,
    }


def _normalize_pair(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    items = list(value)
    if len(items) != 2:
        return None
    user = _normalize_message(items[0], expected_role='user')
    assistant = _normalize_message(items[1], expected_role='assistant')
    if user is None or assistant is None:
        return None
    return {
        'user': user,
        'assistant': assistant,
    }


def _row_to_staging_state(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    buffer_pairs = row[1]
    if isinstance(buffer_pairs, str):
        try:
            buffer_pairs = json.loads(buffer_pairs)
        except Exception:
            buffer_pairs = []
    if not isinstance(buffer_pairs, list):
        buffer_pairs = []
    return {
        'conversation_id': _text(row[0]),
        'buffer_pairs': list(buffer_pairs),
        'buffer_pairs_count': int(row[2] or 0),
        'buffer_target_pairs': int(row[3] or DEFAULT_BUFFER_TARGET_PAIRS),
        'auto_canonization_suspended': bool(row[4]),
        'last_agent_status': _text(row[5]) or None,
        'last_agent_reason': _text(row[6]) or None,
        'last_agent_run_ts': _serialize_ts(row[7]),
        'created_ts': _serialize_ts(row[8]),
        'updated_ts': _serialize_ts(row[9]),
    }


def get_identity_staging_state(
    conversation_id: str,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    conversation_key = _text(conversation_id)
    if not conversation_key:
        return None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        conversation_id,
                        buffer_pairs_json,
                        buffer_pairs_count,
                        buffer_target_pairs,
                        auto_canonization_suspended,
                        last_agent_status,
                        last_agent_reason,
                        last_agent_run_ts,
                        created_ts,
                        updated_ts
                    FROM identity_mutable_staging
                    WHERE conversation_id = %s
                    LIMIT 1
                    ''',
                    (conversation_key,),
                )
                return _row_to_staging_state(cur.fetchone())
    except Exception as exc:
        logger.error('get_identity_staging_state_error conversation_id=%s err=%s', conversation_key, exc)
        return None


def append_identity_staging_pair(
    conversation_id: str,
    pair: Any,
    *,
    target_pairs: int = DEFAULT_BUFFER_TARGET_PAIRS,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    conversation_key = _text(conversation_id)
    normalized_pair = _normalize_pair(pair)
    if not conversation_key or normalized_pair is None:
        return None

    buffer_target = max(1, int(target_pairs or DEFAULT_BUFFER_TARGET_PAIRS))
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        conversation_id,
                        buffer_pairs_json,
                        buffer_pairs_count,
                        buffer_target_pairs,
                        auto_canonization_suspended,
                        last_agent_status,
                        last_agent_reason,
                        last_agent_run_ts,
                        created_ts,
                        updated_ts
                    FROM identity_mutable_staging
                    WHERE conversation_id = %s
                    FOR UPDATE
                    ''',
                    (conversation_key,),
                )
                current_state = _row_to_staging_state(cur.fetchone())
                current_pairs = list((current_state or {}).get('buffer_pairs') or [])
                next_pairs = current_pairs + [normalized_pair]
                next_status = _text((current_state or {}).get('last_agent_status')) or 'buffering'
                if len(current_pairs) == 0 and next_status in {'applied', 'completed_no_change', 'not_run'}:
                    next_status = 'buffering'
                cur.execute(
                    '''
                    INSERT INTO identity_mutable_staging (
                        conversation_id,
                        buffer_pairs_json,
                        buffer_pairs_count,
                        buffer_target_pairs,
                        auto_canonization_suspended,
                        last_agent_status,
                        last_agent_reason
                    )
                    VALUES (%s, %s::jsonb, %s, %s, %s, %s, %s)
                    ON CONFLICT (conversation_id) DO UPDATE
                    SET
                        buffer_pairs_json = EXCLUDED.buffer_pairs_json,
                        buffer_pairs_count = EXCLUDED.buffer_pairs_count,
                        buffer_target_pairs = EXCLUDED.buffer_target_pairs,
                        auto_canonization_suspended = EXCLUDED.auto_canonization_suspended,
                        last_agent_status = EXCLUDED.last_agent_status,
                        last_agent_reason = EXCLUDED.last_agent_reason,
                        updated_ts = now()
                    RETURNING
                        conversation_id,
                        buffer_pairs_json,
                        buffer_pairs_count,
                        buffer_target_pairs,
                        auto_canonization_suspended,
                        last_agent_status,
                        last_agent_reason,
                        last_agent_run_ts,
                        created_ts,
                        updated_ts
                    ''',
                    (
                        conversation_key,
                        json.dumps(next_pairs, ensure_ascii=False),
                        len(next_pairs),
                        buffer_target,
                        False,
                        next_status,
                        _text((current_state or {}).get('last_agent_reason')) or None,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_staging_state(row)
    except Exception as exc:
        logger.error('append_identity_staging_pair_error conversation_id=%s err=%s', conversation_key, exc)
        return None


def mark_identity_staging_status(
    conversation_id: str,
    *,
    status: str,
    reason: str = '',
    touch_run_ts: bool = False,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    conversation_key = _text(conversation_id)
    status_text = _text(status)
    if not conversation_key or not status_text:
        return None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE identity_mutable_staging
                    SET
                        last_agent_status = %s,
                        last_agent_reason = %s,
                        last_agent_run_ts = CASE WHEN %s THEN now() ELSE last_agent_run_ts END,
                        updated_ts = now()
                    WHERE conversation_id = %s
                    RETURNING
                        conversation_id,
                        buffer_pairs_json,
                        buffer_pairs_count,
                        buffer_target_pairs,
                        auto_canonization_suspended,
                        last_agent_status,
                        last_agent_reason,
                        last_agent_run_ts,
                        created_ts,
                        updated_ts
                    ''',
                    (
                        status_text,
                        _text(reason) or None,
                        bool(touch_run_ts),
                        conversation_key,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_staging_state(row)
    except Exception as exc:
        logger.error('mark_identity_staging_status_error conversation_id=%s err=%s', conversation_key, exc)
        return None


def clear_identity_staging_buffer(
    conversation_id: str,
    *,
    status: str,
    reason: str = '',
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    conversation_key = _text(conversation_id)
    status_text = _text(status)
    if not conversation_key or not status_text:
        return None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE identity_mutable_staging
                    SET
                        buffer_pairs_json = %s::jsonb,
                        buffer_pairs_count = 0,
                        last_agent_status = %s,
                        last_agent_reason = %s,
                        last_agent_run_ts = now(),
                        updated_ts = now()
                    WHERE conversation_id = %s
                    RETURNING
                        conversation_id,
                        buffer_pairs_json,
                        buffer_pairs_count,
                        buffer_target_pairs,
                        auto_canonization_suspended,
                        last_agent_status,
                        last_agent_reason,
                        last_agent_run_ts,
                        created_ts,
                        updated_ts
                    ''',
                    (
                        json.dumps([], ensure_ascii=False),
                        status_text,
                        _text(reason) or None,
                        conversation_key,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_staging_state(row)
    except Exception as exc:
        logger.error('clear_identity_staging_buffer_error conversation_id=%s err=%s', conversation_key, exc)
        return None
