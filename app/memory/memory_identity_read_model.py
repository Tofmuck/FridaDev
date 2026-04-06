from __future__ import annotations

from typing import Any, Callable

_ALLOWED_SUBJECTS = {'llm', 'user'}
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _canonical_subject(subject: str) -> str:
    normalized = str(subject or '').strip().lower()
    if normalized not in _ALLOWED_SUBJECTS:
        return ''
    return normalized


def _normalize_limit(limit: int | None) -> int:
    if limit is None:
        return _DEFAULT_LIMIT
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    return max(1, min(value, _MAX_LIMIT))


def _serialize_ts(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return str(value.isoformat())
    return str(value)


def list_identity_fragments(
    subject: str,
    limit: int | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    canonical_subject = _canonical_subject(subject)
    effective_limit = _normalize_limit(limit)
    if not canonical_subject:
        return {'total_count': 0, 'limit': effective_limit, 'items': []}

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*)
                    FROM identities
                    WHERE subject = %s
                    ''',
                    (canonical_subject,),
                )
                total_count = int((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    '''
                    SELECT
                        id,
                        subject,
                        content,
                        weight,
                        created_ts,
                        last_seen_ts,
                        source_trace_id,
                        stability,
                        utterance_mode,
                        recurrence,
                        scope,
                        evidence_kind,
                        confidence,
                        status,
                        content_norm,
                        last_reason,
                        conversation_id,
                        override_state,
                        override_reason,
                        override_actor,
                        override_ts
                    FROM identities
                    WHERE subject = %s
                    ORDER BY created_ts DESC, weight DESC
                    LIMIT %s
                    ''',
                    (canonical_subject, effective_limit),
                )
                rows = cur.fetchall()
        return {
            'total_count': total_count,
            'limit': effective_limit,
            'items': [
                {
                    'identity_id': str(row[0]),
                    'subject': str(row[1] or ''),
                    'content': str(row[2] or ''),
                    'weight': float(row[3] or 0.0),
                    'created_ts': _serialize_ts(row[4]),
                    'last_seen_ts': _serialize_ts(row[5]),
                    'source_trace_id': str(row[6]) if row[6] is not None else None,
                    'stability': str(row[7] or 'unknown'),
                    'utterance_mode': str(row[8] or 'unknown'),
                    'recurrence': str(row[9] or 'unknown'),
                    'scope': str(row[10] or 'unknown'),
                    'evidence_kind': str(row[11] or 'weak'),
                    'confidence': float(row[12] or 0.0),
                    'status': str(row[13] or 'accepted'),
                    'content_norm': str(row[14] or ''),
                    'last_reason': str(row[15] or ''),
                    'conversation_id': str(row[16] or ''),
                    'override_state': str(row[17] or 'none'),
                    'override_reason': str(row[18] or ''),
                    'override_actor': str(row[19] or ''),
                    'override_ts': _serialize_ts(row[20]),
                }
                for row in rows
            ],
        }
    except Exception as exc:
        logger.error('list_identity_fragments_error subject=%s err=%s', canonical_subject, exc)
        return {'total_count': 0, 'limit': effective_limit, 'items': []}


def list_identity_evidence(
    subject: str,
    limit: int | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    canonical_subject = _canonical_subject(subject)
    effective_limit = _normalize_limit(limit)
    if not canonical_subject:
        return {'total_count': 0, 'limit': effective_limit, 'items': []}

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*)
                    FROM identity_evidence
                    WHERE subject = %s
                    ''',
                    (canonical_subject,),
                )
                total_count = int((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    '''
                    SELECT
                        id,
                        conversation_id,
                        subject,
                        content,
                        content_norm,
                        stability,
                        utterance_mode,
                        recurrence,
                        scope,
                        evidence_kind,
                        confidence,
                        status,
                        reason,
                        source_trace_id,
                        created_ts
                    FROM identity_evidence
                    WHERE subject = %s
                    ORDER BY created_ts DESC
                    LIMIT %s
                    ''',
                    (canonical_subject, effective_limit),
                )
                rows = cur.fetchall()
        return {
            'total_count': total_count,
            'limit': effective_limit,
            'items': [
                {
                    'evidence_id': str(row[0]),
                    'conversation_id': str(row[1] or ''),
                    'subject': str(row[2] or ''),
                    'content': str(row[3] or ''),
                    'content_norm': str(row[4] or ''),
                    'stability': str(row[5] or 'unknown'),
                    'utterance_mode': str(row[6] or 'unknown'),
                    'recurrence': str(row[7] or 'unknown'),
                    'scope': str(row[8] or 'unknown'),
                    'evidence_kind': str(row[9] or 'weak'),
                    'confidence': float(row[10] or 0.0),
                    'status': str(row[11] or 'accepted'),
                    'reason': str(row[12] or ''),
                    'source_trace_id': str(row[13]) if row[13] is not None else None,
                    'created_ts': _serialize_ts(row[14]),
                }
                for row in rows
            ],
        }
    except Exception as exc:
        logger.error('list_identity_evidence_error subject=%s err=%s', canonical_subject, exc)
        return {'total_count': 0, 'limit': effective_limit, 'items': []}


def list_identity_conflicts(
    subject: str,
    limit: int | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    canonical_subject = _canonical_subject(subject)
    effective_limit = _normalize_limit(limit)
    if not canonical_subject:
        return {'total_count': 0, 'limit': effective_limit, 'items': []}

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*)
                    FROM identity_conflicts ic
                    JOIN identities ia ON ia.id = ic.identity_id_a
                    JOIN identities ib ON ib.id = ic.identity_id_b
                    WHERE ia.subject = %s OR ib.subject = %s
                    ''',
                    (canonical_subject, canonical_subject),
                )
                total_count = int((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    '''
                    SELECT
                        ic.id,
                        ic.confidence_conflict,
                        ic.reason,
                        ic.resolved_state,
                        ic.created_ts,
                        ic.resolved_ts,
                        ia.id,
                        ia.subject,
                        ia.content,
                        ia.status,
                        ia.source_trace_id,
                        ia.override_state,
                        ib.id,
                        ib.subject,
                        ib.content,
                        ib.status,
                        ib.source_trace_id,
                        ib.override_state
                    FROM identity_conflicts ic
                    JOIN identities ia ON ia.id = ic.identity_id_a
                    JOIN identities ib ON ib.id = ic.identity_id_b
                    WHERE ia.subject = %s OR ib.subject = %s
                    ORDER BY ic.created_ts DESC
                    LIMIT %s
                    ''',
                    (canonical_subject, canonical_subject, effective_limit),
                )
                rows = cur.fetchall()
        return {
            'total_count': total_count,
            'limit': effective_limit,
            'items': [
                {
                    'conflict_id': str(row[0]),
                    'confidence_conflict': float(row[1] or 0.0),
                    'reason': str(row[2] or ''),
                    'resolved_state': str(row[3] or 'open'),
                    'created_ts': _serialize_ts(row[4]),
                    'resolved_ts': _serialize_ts(row[5]),
                    'identity_id_a': str(row[6]),
                    'subject_a': str(row[7] or ''),
                    'content_a': str(row[8] or ''),
                    'status_a': str(row[9] or 'accepted'),
                    'source_trace_id_a': str(row[10]) if row[10] is not None else None,
                    'override_state_a': str(row[11] or 'none'),
                    'identity_id_b': str(row[12]),
                    'subject_b': str(row[13] or ''),
                    'content_b': str(row[14] or ''),
                    'status_b': str(row[15] or 'accepted'),
                    'source_trace_id_b': str(row[16]) if row[16] is not None else None,
                    'override_state_b': str(row[17] or 'none'),
                }
                for row in rows
            ],
        }
    except Exception as exc:
        logger.error('list_identity_conflicts_error subject=%s err=%s', canonical_subject, exc)
        return {'total_count': 0, 'limit': effective_limit, 'items': []}
