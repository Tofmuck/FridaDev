from __future__ import annotations

import hashlib
from typing import Any, Callable

_ALLOWED_SUBJECTS = {'llm', 'user'}
_ALLOWED_MUTATION_KINDS = {'set', 'clear'}


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


def _short_hash(content: str) -> str | None:
    if not content:
        return None
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]


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


def _row_to_mutable_identity_audit(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'audit_id': str(row[0]) if row[0] is not None else None,
        'subject': str(row[1] or ''),
        'mutation_kind': str(row[2] or ''),
        'actor': str(row[3]) if row[3] is not None else None,
        'reason_code': str(row[4]) if row[4] is not None else None,
        'old_chars': int(row[5] or 0),
        'new_chars': int(row[6] or 0),
        'old_sha256_12': str(row[7]) if row[7] is not None else None,
        'new_sha256_12': str(row[8]) if row[8] is not None else None,
        'source_trace_id': str(row[9]) if row[9] is not None else None,
        'created_ts': _serialize_ts(row[10]),
    }


def _record_mutable_identity_audit(
    cur: Any,
    *,
    subject: str,
    mutation_kind: str,
    actor: str,
    reason_code: str,
    old_content: str,
    new_content: str,
    source_trace_id: str | None,
) -> dict[str, Any] | None:
    if mutation_kind not in _ALLOWED_MUTATION_KINDS:
        return None
    cur.execute(
        '''
        INSERT INTO identity_mutable_audit (
            subject,
            mutation_kind,
            actor,
            reason_code,
            old_chars,
            new_chars,
            old_sha256_12,
            new_sha256_12,
            source_trace_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::uuid)
        RETURNING
            audit_id,
            subject,
            mutation_kind,
            actor,
            reason_code,
            old_chars,
            new_chars,
            old_sha256_12,
            new_sha256_12,
            source_trace_id,
            created_ts
        ''',
        (
            subject,
            mutation_kind,
            str(actor or 'system')[:120],
            str(reason_code or mutation_kind)[:500] or None,
            len(old_content),
            len(new_content),
            _short_hash(old_content),
            _short_hash(new_content),
            source_trace_id,
        ),
    )
    return _row_to_mutable_identity_audit(cur.fetchone())


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


def get_latest_mutable_identity_audit(
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
                        audit_id,
                        subject,
                        mutation_kind,
                        actor,
                        reason_code,
                        old_chars,
                        new_chars,
                        old_sha256_12,
                        new_sha256_12,
                        source_trace_id,
                        created_ts
                    FROM identity_mutable_audit
                    WHERE subject = %s
                    ORDER BY created_ts DESC, audit_id DESC
                    LIMIT 1
                    ''',
                    (canonical_subject,),
                )
                return _row_to_mutable_identity_audit(cur.fetchone())
    except Exception as exc:
        logger.error('get_latest_mutable_identity_audit_error subject=%s err=%s', canonical_subject, exc)
        return None


def upsert_mutable_identity(
    subject: str,
    content: str,
    source_trace_id: str | None = None,
    *,
    updated_by: str = 'system',
    update_reason: str = '',
    audit_reason_code: str | None = None,
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
                    SELECT content
                    FROM identity_mutables
                    WHERE subject = %s
                    LIMIT 1
                    ''',
                    (canonical_subject,),
                )
                previous_row = cur.fetchone()
                old_content = str(previous_row[0] or '') if previous_row else ''
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
                _record_mutable_identity_audit(
                    cur,
                    subject=canonical_subject,
                    mutation_kind='set',
                    actor=str(updated_by or 'system'),
                    reason_code=str(audit_reason_code or update_reason or 'set'),
                    old_content=old_content,
                    new_content=cleaned_content,
                    source_trace_id=source_trace_id,
                )
            conn.commit()
        return _row_to_mutable_identity(row)
    except Exception as exc:
        logger.error('upsert_mutable_identity_error subject=%s err=%s', canonical_subject, exc)
        return None


def clear_mutable_identity(
    subject: str,
    *,
    updated_by: str = 'system',
    update_reason: str = 'clear',
    audit_reason_code: str | None = None,
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
                if row:
                    _record_mutable_identity_audit(
                        cur,
                        subject=canonical_subject,
                        mutation_kind='clear',
                        actor=str(updated_by or 'system'),
                        reason_code=str(audit_reason_code or update_reason or 'clear'),
                        old_content=str(row[1] or ''),
                        new_content='',
                        source_trace_id=str(row[2]) if row[2] is not None else None,
                    )
            conn.commit()
        return _row_to_mutable_identity(row)
    except Exception as exc:
        logger.error('clear_mutable_identity_error subject=%s err=%s', canonical_subject, exc)
        return None
