from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

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
            None,
            None,
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


def apply_mutable_identity_subject_updates(
    updates: Sequence[Mapping[str, Any]],
    *,
    staging_conversation_id: str | None = None,
    staging_window_fingerprint: str | None = None,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]] | None:
    staging_conversation_key = str(staging_conversation_id or '').strip()
    staging_fingerprint = str(staging_window_fingerprint or '').strip()
    if bool(staging_conversation_key) != bool(staging_fingerprint):
        return None
    if staging_fingerprint and (
        len(staging_fingerprint) != 12
        or any(character not in '0123456789abcdef' for character in staging_fingerprint)
    ):
        return None

    normalized_updates: list[dict[str, Any]] = []
    for raw_update in list(updates or []):
        payload = raw_update if isinstance(raw_update, Mapping) else {}
        subject = _canonical_subject(str(payload.get('subject') or ''))
        mutation_kind = str(payload.get('mutation_kind') or '').strip().lower()
        content = str(payload.get('content') or '').strip()
        raw_source_trace_id = str(payload.get('source_trace_id') or '').strip()
        source_trace_id = raw_source_trace_id or None
        updated_by = str(payload.get('updated_by') or 'system')[:120]
        update_reason = str(payload.get('update_reason') or '')[:500] or None
        audit_reason_code = str(payload.get('audit_reason_code') or update_reason or mutation_kind)

        if not subject or mutation_kind not in _ALLOWED_MUTATION_KINDS:
            return None
        if mutation_kind == 'set' and not content:
            return None
        normalized_updates.append(
            {
                'subject': subject,
                'mutation_kind': mutation_kind,
                'content': content,
                'source_trace_id': source_trace_id,
                'updated_by': updated_by,
                'update_reason': update_reason,
                'audit_reason_code': audit_reason_code,
            }
        )

    if not normalized_updates:
        return []

    try:
        with conn_factory() as conn:
            results: list[dict[str, Any]] = []
            with conn.cursor() as cur:
                for update in normalized_updates:
                    subject = update['subject']
                    mutation_kind = update['mutation_kind']
                    source_trace_id = update['source_trace_id']
                    updated_by = update['updated_by']
                    update_reason = update['update_reason']
                    audit_reason_code = update['audit_reason_code']

                    cur.execute(
                        '''
                        SELECT content
                        FROM identity_mutables
                        WHERE subject = %s
                        LIMIT 1
                        ''',
                        (subject,),
                    )
                    previous_row = cur.fetchone()
                    old_content = str(previous_row[0] or '') if previous_row else ''

                    if mutation_kind == 'set':
                        content = update['content']
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
                                subject,
                                content,
                                source_trace_id,
                                updated_by,
                                update_reason,
                            ),
                        )
                        row = cur.fetchone()
                        _record_mutable_identity_audit(
                            cur,
                            subject=subject,
                            mutation_kind='set',
                            actor=updated_by,
                            reason_code=audit_reason_code,
                            old_content=old_content,
                            new_content=content,
                            source_trace_id=source_trace_id,
                        )
                        normalized_row = _row_to_mutable_identity(row)
                        if normalized_row is None:
                            raise RuntimeError('mutable_set_return_missing')
                        results.append(normalized_row)
                        continue

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
                        (subject,),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise RuntimeError('mutable_clear_target_missing')
                    old_content = str(row[1] or '')
                    _record_mutable_identity_audit(
                        cur,
                        subject=subject,
                        mutation_kind='clear',
                        actor=updated_by,
                        reason_code=audit_reason_code,
                        old_content=old_content,
                        new_content='',
                        source_trace_id=str(row[2]) if row[2] is not None else None,
                    )
                    normalized_row = _row_to_mutable_identity(row)
                    if normalized_row is None:
                        raise RuntimeError('mutable_clear_return_missing')
                    results.append(normalized_row)
                if normalized_updates and staging_conversation_key:
                    cur.execute(
                        '''
                        UPDATE identity_mutable_staging
                        SET
                            last_agent_status = 'canonical_write_committed',
                            last_agent_reason = %s,
                            updated_ts = now()
                        WHERE conversation_id = %s
                          AND buffer_pairs_count = 5
                        RETURNING conversation_id
                        ''',
                        (
                            f'canonical_write_recovery_pending:{staging_fingerprint}',
                            staging_conversation_key,
                        ),
                    )
                    fence_row = cur.fetchone()
                    if not fence_row:
                        raise RuntimeError('identity_staging_write_fence_missing')
            conn.commit()
            return results
    except Exception as exc:
        logger.error('apply_mutable_identity_subject_updates_error count=%s err=%s', len(normalized_updates), exc)
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
