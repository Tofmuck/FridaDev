from __future__ import annotations

from typing import Any, Callable

_ALLOWED_SUBJECTS = {'llm', 'user'}


def _canonical_subject(subject: str) -> str:
    normalized = str(subject or '').strip().lower()
    if normalized not in _ALLOWED_SUBJECTS:
        return ''
    return normalized


def _serialize_ts(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return str(value.isoformat())
    return str(value)


def _row_to_mutable_identity(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'subject': str(row[0] or ''),
        'content': str(row[1] or ''),
        'source_trace_id': str(row[2]) if row[2] is not None else None,
        'updated_by': str(row[3]) if row[3] is not None else None,
        'update_reason': str(row[4]) if row[4] is not None else None,
        'created_ts': _serialize_ts(row[5]),
        'updated_ts': _serialize_ts(row[6]),
    }


def get_mutable_identity(
    subject: str,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    canonical_subject = _canonical_subject(subject)
    if not canonical_subject:
        return None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        subject,
                        content,
                        source_trace_id,
                        updated_by,
                        update_reason,
                        created_ts,
                        updated_ts
                    FROM identity_mutables
                    WHERE subject = %s
                    LIMIT 1
                    ''',
                    (canonical_subject,),
                )
                return _row_to_mutable_identity(cur.fetchone())
    except Exception as exc:
        logger.error('get_mutable_identity_error subject=%s err=%s', canonical_subject, exc)
        return None


def list_mutable_identities(
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        subject,
                        content,
                        source_trace_id,
                        updated_by,
                        update_reason,
                        created_ts,
                        updated_ts
                    FROM identity_mutables
                    ORDER BY subject ASC
                    '''
                )
                return [
                    item
                    for item in (_row_to_mutable_identity(row) for row in cur.fetchall())
                    if item is not None
                ]
    except Exception as exc:
        logger.error('list_mutable_identities_error err=%s', exc)
        return []


def upsert_mutable_identity(
    subject: str,
    content: str,
    source_trace_id: str | None = None,
    *,
    updated_by: str = 'system',
    update_reason: str = '',
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    canonical_subject = _canonical_subject(subject)
    cleaned_content = str(content or '').strip()
    if not canonical_subject or not cleaned_content:
        return None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO identity_mutables (
                        subject,
                        content,
                        source_trace_id,
                        updated_by,
                        update_reason
                    )
                    VALUES (%s, %s, %s::uuid, %s, %s)
                    ON CONFLICT (subject) DO UPDATE
                    SET
                        content = EXCLUDED.content,
                        source_trace_id = EXCLUDED.source_trace_id,
                        updated_by = EXCLUDED.updated_by,
                        update_reason = EXCLUDED.update_reason,
                        updated_ts = now()
                    RETURNING
                        subject,
                        content,
                        source_trace_id,
                        updated_by,
                        update_reason,
                        created_ts,
                        updated_ts
                    ''',
                    (
                        canonical_subject,
                        cleaned_content,
                        source_trace_id,
                        str(updated_by or 'system')[:120],
                        str(update_reason or '')[:500] or None,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_mutable_identity(row)
    except Exception as exc:
        logger.error('upsert_mutable_identity_error subject=%s err=%s', canonical_subject, exc)
        return None


def clear_mutable_identity(
    subject: str,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    canonical_subject = _canonical_subject(subject)
    if not canonical_subject:
        return None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    DELETE FROM identity_mutables
                    WHERE subject = %s
                    RETURNING
                        subject,
                        content,
                        source_trace_id,
                        updated_by,
                        update_reason,
                        created_ts,
                        updated_ts
                    ''',
                    (canonical_subject,),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_mutable_identity(row)
    except Exception as exc:
        logger.error('clear_mutable_identity_error subject=%s err=%s', canonical_subject, exc)
        return None
