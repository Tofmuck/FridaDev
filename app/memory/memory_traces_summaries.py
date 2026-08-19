from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from memory import memory_lexical_sql
from memory import memory_trace_summary_store
from observability import chat_turn_logger


_LEXICAL_TOKEN_RE = re.compile(r'https?://\S+|[A-Za-z0-9][A-Za-z0-9._:/?-]*')
_LEXICAL_TRANSLATE_FROM = memory_lexical_sql.LEXICAL_TRANSLATE_FROM
_LEXICAL_TRANSLATE_TO = memory_lexical_sql.LEXICAL_TRANSLATE_TO
_NORMALIZED_CONTENT_SQL = memory_lexical_sql.normalized_content_sql(column_name='content')
_LEXICAL_STOPWORDS = {
    'a',
    'au',
    'aux',
    'blog',
    'blogs',
    'ce',
    'ces',
    'cette',
    'comme',
    'dans',
    'de',
    'des',
    'du',
    'en',
    'et',
    'http',
    'https',
    'ici',
    'la',
    'le',
    'les',
    'mais',
    'nos',
    'notre',
    'ou',
    'par',
    'pas',
    'pour',
    'qui',
    'quoi',
    'que',
    'quand',
    'suis',
    'sur',
    'toi',
    'un',
    'une',
    'vos',
    'votre',
    'www',
}
_HYBRID_INTERNAL_LIMIT_MIN = 12
_HYBRID_INTERNAL_LIMIT_MULTIPLIER = 3
_SUMMARY_LANE_LIMIT_MAX = 3
_PRE_ARBITER_TOTAL_LIMIT = 8


@dataclass(frozen=True)
class MemoryRetrievalResult:
    traces: list[dict[str, Any]]
    ok: bool
    top_k_requested: int
    error_code: str | None = None
    error_class: str | None = None
    reason_code: str | None = None

    @property
    def status(self) -> str:
        return 'ok' if self.ok else 'error'

    @property
    def top_k_returned(self) -> int:
        return len(self.traces)


def _normalize_lexical_text(text: str) -> str:
    normalized = (text or '').replace('\u0153', 'oe').replace('\u00e6', 'ae').lower()
    normalized = ''.join(
        ch for ch in unicodedata.normalize('NFKD', normalized) if not unicodedata.combining(ch)
    )
    return re.sub(r'\s+', ' ', normalized).strip()


def _extract_lexical_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in _LEXICAL_TOKEN_RE.findall(query or ''):
        has_digit = any(ch.isdigit() for ch in token)
        is_url = '://' in token
        is_upper = token.isupper() and any(ch.isalpha() for ch in token)
        has_title = token[:1].isupper() and any(ch.islower() for ch in token[1:])
        if not (has_digit or is_url or is_upper or has_title):
            continue

        normalized_token = _normalize_lexical_text(token)
        for part in re.split(r'[^a-z0-9]+', normalized_token):
            if not part:
                continue
            if part in _LEXICAL_STOPWORDS:
                continue
            if len(part) < 3 and not any(ch.isdigit() for ch in part):
                continue
            if part in seen:
                continue
            seen.add(part)
            terms.append(part)
            if len(terms) >= 6:
                return terms
    return terms


def _extract_lexical_exact_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for token in _LEXICAL_TOKEN_RE.findall(query or ''):
        has_digit = any(ch.isdigit() for ch in token)
        is_url = '://' in token
        is_upper = token.isupper() and any(ch.isalpha() for ch in token)
        if not (has_digit or is_url or is_upper):
            continue

        normalized_token = _normalize_lexical_text(token)
        if normalized_token in _LEXICAL_STOPWORDS:
            continue
        if len(normalized_token) < 3:
            continue
        if normalized_token in seen:
            continue
        seen.add(normalized_token)
        tokens.append(normalized_token)
    return tokens


def _should_use_exact_token_lookup(
    query: str,
    *,
    normalized_query: str,
    exact_tokens: list[str],
) -> bool:
    if len(exact_tokens) != 1:
        return False

    exact_token = exact_tokens[0]
    if normalized_query == exact_token:
        return True

    # Preserve exact locator probes such as a full URL wrapped in a short sentence.
    if '://' in (query or '') and exact_token in normalized_query:
        return True

    residual = normalized_query.replace(exact_token, ' ')
    residual_terms = [
        part
        for part in re.split(r'[^a-z0-9]+', residual)
        if part and part not in _LEXICAL_STOPWORDS
    ]
    return not residual_terms and (len(exact_token) >= 10 or any(ch.isdigit() for ch in exact_token))


def _internal_recall_limit(top_k: int) -> int:
    return max(int(top_k) * _HYBRID_INTERNAL_LIMIT_MULTIPLIER, _HYBRID_INTERNAL_LIMIT_MIN)


def _trace_public_key(trace: dict[str, Any]) -> tuple[Any, ...]:
    return (
        trace.get('conversation_id'),
        trace.get('role'),
        trace.get('content'),
        trace.get('timestamp'),
        trace.get('summary_id'),
    )


def _summary_public_key(summary: dict[str, Any]) -> tuple[Any, ...]:
    return (
        summary.get('summary_id'),
        summary.get('conversation_id'),
        summary.get('start_ts'),
        summary.get('end_ts'),
        summary.get('content'),
    )


def _timestamp_sort_value(value: Any) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _coerce_trace_row(
    conversation_id: Any,
    role: Any,
    content: Any,
    timestamp: Any,
    summary_id: Any,
    score: Any,
) -> dict[str, Any]:
    return {
        'conversation_id': conversation_id,
        'role': role,
        'content': content,
        'timestamp': str(timestamp) if timestamp else None,
        'summary_id': str(summary_id) if summary_id else None,
        'score': float(score),
    }


def _public_trace_row(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        'conversation_id': trace.get('conversation_id'),
        'role': trace.get('role'),
        'content': trace.get('content'),
        'timestamp': trace.get('timestamp'),
        'summary_id': trace.get('summary_id'),
        'score': float(trace.get('score') or 0.0),
    }


def _coerce_summary_row(
    summary_id: Any,
    conversation_id: Any,
    start_ts: Any,
    end_ts: Any,
    content: Any,
    score: Any,
) -> dict[str, Any]:
    timestamp_iso = str(end_ts) if end_ts else None
    return {
        'conversation_id': conversation_id,
        'role': 'summary',
        'content': content,
        'timestamp': timestamp_iso,
        'timestamp_iso': timestamp_iso,
        'start_ts': str(start_ts) if start_ts else None,
        'end_ts': str(end_ts) if end_ts else None,
        'summary_id': str(summary_id) if summary_id else None,
        'score': float(score),
        'retrieval_score': float(score),
        'semantic_score': float(score),
        'source_kind': 'summary',
        'source_lane': 'summaries',
    }


def _summary_lane_limit(top_k: int) -> int:
    remaining_budget = max(0, _PRE_ARBITER_TOTAL_LIMIT - int(top_k))
    return min(_SUMMARY_LANE_LIMIT_MAX, remaining_budget)


def _retrieve_summary_candidates(
    q_vec: list[float],
    *,
    limit: int,
    conn_factory: Callable[[], Any],
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, conversation_id, start_ts, end_ts, content,
                       1 - (embedding <=> %s::vector) AS score
                FROM summaries
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                ''',
                (str(q_vec), str(q_vec), int(limit)),
            )
            rows = cur.fetchall()
    return [_coerce_summary_row(*row) for row in rows]


def _retrieve_dense_candidates(
    q_vec: list[float],
    *,
    limit: int,
    conn_factory: Callable[[], Any],
) -> list[dict[str, Any]]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT conversation_id, role, content, timestamp, summary_id,
                       1 - (embedding <=> %s::vector) AS score
                FROM   traces
                WHERE  embedding IS NOT NULL
                ORDER  BY embedding <=> %s::vector
                LIMIT  %s
                ''',
                (str(q_vec), str(q_vec), int(limit)),
            )
            rows = cur.fetchall()
    return [_coerce_trace_row(*row) for row in rows]


def _retrieve_lexical_candidates(
    query: str,
    *,
    limit: int,
    conn_factory: Callable[[], Any],
) -> list[dict[str, Any]]:
    normalized_query = _normalize_lexical_text(query)
    query_terms = _extract_lexical_query_terms(query)
    exact_tokens = _extract_lexical_exact_tokens(query)
    if not normalized_query or not query_terms:
        return []
    normalized_content_expr = _NORMALIZED_CONTENT_SQL
    if _should_use_exact_token_lookup(
        query,
        normalized_query=normalized_query,
        exact_tokens=exact_tokens,
    ):
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT conversation_id, role, content, timestamp, summary_id
                    FROM traces
                    WHERE {normalized_content_expr} LIKE '%%' || %s || '%%'
                    ORDER BY {normalized_content_expr} <-> %s, char_length(content) ASC, timestamp DESC
                    LIMIT %s
                    ''',
                    (exact_tokens[0], exact_tokens[0], int(limit)),
                )
                rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            candidate = _coerce_trace_row(row[0], row[1], row[2], row[3], row[4], 0.98)
            candidate['_lexical_exact_token_hits'] = 1
            candidate['_lexical_term_hits'] = 1
            candidate['_lexical_phrase_hit'] = 1
            out.append(candidate)
        return out

    tsquery = ' | '.join(query_terms)
    params = [
        normalized_query,
        query_terms,
        exact_tokens,
        tsquery,
        int(limit),
    ]

    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'''
                WITH params AS (
                    SELECT %s::text AS normalized_query,
                           %s::text[] AS query_terms,
                           %s::text[] AS exact_tokens,
                           to_tsquery('simple', %s) AS ts_query
                )
                SELECT conversation_id, role, content, timestamp, summary_id,
                       ts_rank_cd(
                           to_tsvector('simple', {normalized_content_expr}),
                           params.ts_query
                       ) AS lexical_rank,
                       CASE
                           WHEN {normalized_content_expr} LIKE '%%' || params.normalized_query || '%%'
                           THEN 1
                           ELSE 0
                       END AS phrase_hit,
                       (
                           SELECT COUNT(*)
                           FROM unnest(params.exact_tokens) AS token
                           WHERE {normalized_content_expr} LIKE '%%' || token || '%%'
                       ) AS exact_token_hits,
                       (
                           SELECT COUNT(*)
                           FROM unnest(params.query_terms) AS term
                           WHERE {normalized_content_expr} LIKE '%%' || term || '%%'
                       ) AS term_hits
                FROM traces, params
                WHERE to_tsvector('simple', {normalized_content_expr}) @@ params.ts_query
                ORDER BY phrase_hit DESC, exact_token_hits DESC, term_hits DESC, lexical_rank DESC, timestamp DESC
                LIMIT %s
                ''',
                params,
            )
            rows = cur.fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        lexical_rank = float(row[5] or 0.0)
        phrase_hit = int(row[6] or 0)
        exact_token_hits = int(row[7] or 0)
        term_hits = int(row[8] or 0)
        lexical_norm = lexical_rank / (1.0 + lexical_rank)
        lexical_score = min(
            0.99,
            max(
                0.25 * lexical_norm + 0.08 * min(exact_token_hits, 2) + 0.18 * min(term_hits, 4),
                0.98 if phrase_hit else 0.0,
                0.92 if exact_token_hits else 0.0,
            ),
        )
        candidate = _coerce_trace_row(row[0], row[1], row[2], row[3], row[4], lexical_score)
        candidate['_lexical_exact_token_hits'] = exact_token_hits
        candidate['_lexical_term_hits'] = term_hits
        candidate['_lexical_phrase_hit'] = phrase_hit
        out.append(candidate)
    return out


def _hybrid_output_score(
    *,
    dense_score: float,
    lexical_score: float,
    exact_token_hits: int,
    phrase_hit: int,
) -> float:
    if dense_score > 0.0:
        blended = min(
            0.99,
            0.80 * dense_score + 0.25 * lexical_score + 0.02 * min(exact_token_hits, 2) + 0.01 * phrase_hit,
        )
        return max(dense_score, blended)
    if phrase_hit:
        return max(lexical_score, 0.98)
    if exact_token_hits:
        return max(lexical_score, 0.92)
    return lexical_score


def _merge_hybrid_candidates(
    *,
    dense_candidates: list[dict[str, Any]],
    lexical_candidates: list[dict[str, Any]],
    top_k: int,
    include_internal_scores: bool = False,
) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}

    for rank, candidate in enumerate(dense_candidates, start=1):
        key = _trace_public_key(candidate)
        entry = merged.setdefault(
            key,
            {
                **candidate,
                '_dense_rank': None,
                '_dense_score': 0.0,
                '_lexical_rank': None,
                '_lexical_score': 0.0,
                '_lexical_exact_token_hits': 0,
                '_lexical_term_hits': 0,
                '_lexical_phrase_hit': 0,
            },
        )
        entry['_dense_rank'] = rank
        entry['_dense_score'] = float(candidate.get('score') or 0.0)

    for rank, candidate in enumerate(lexical_candidates, start=1):
        key = _trace_public_key(candidate)
        entry = merged.setdefault(
            key,
            {
                'conversation_id': candidate.get('conversation_id'),
                'role': candidate.get('role'),
                'content': candidate.get('content'),
                'timestamp': candidate.get('timestamp'),
                'summary_id': candidate.get('summary_id'),
                'score': float(candidate.get('score') or 0.0),
                '_dense_rank': None,
                '_dense_score': 0.0,
                '_lexical_rank': None,
                '_lexical_score': 0.0,
                '_lexical_exact_token_hits': 0,
                '_lexical_term_hits': 0,
                '_lexical_phrase_hit': 0,
            },
        )
        entry['_lexical_rank'] = rank
        entry['_lexical_score'] = max(entry['_lexical_score'], float(candidate.get('score') or 0.0))
        entry['_lexical_exact_token_hits'] = max(
            entry['_lexical_exact_token_hits'],
            int(candidate.get('_lexical_exact_token_hits') or 0),
        )
        entry['_lexical_term_hits'] = max(
            entry['_lexical_term_hits'],
            int(candidate.get('_lexical_term_hits') or 0),
        )
        entry['_lexical_phrase_hit'] = max(
            entry['_lexical_phrase_hit'],
            int(candidate.get('_lexical_phrase_hit') or 0),
        )

    ranked: list[dict[str, Any]] = []
    for entry in merged.values():
        hybrid_rank = 0.0
        dense_rank = entry.get('_dense_rank')
        lexical_rank = entry.get('_lexical_rank')
        phrase_hit = int(entry.get('_lexical_phrase_hit') or 0)
        exact_token_hits = int(entry.get('_lexical_exact_token_hits') or 0)
        term_hits = int(entry.get('_lexical_term_hits') or 0)
        dense_score = float(entry.get('_dense_score') or 0.0)
        lexical_score = float(entry.get('_lexical_score') or 0.0)
        hybrid_output_score = _hybrid_output_score(
            dense_score=dense_score,
            lexical_score=lexical_score,
            exact_token_hits=exact_token_hits,
            phrase_hit=phrase_hit,
        )

        if dense_rank is not None:
            hybrid_rank += 1.0 / (25 + dense_rank)
        if lexical_rank is not None and (phrase_hit or exact_token_hits or term_hits >= 2 or dense_rank is not None):
            hybrid_rank += 1.0 / (15 + lexical_rank)
            hybrid_rank += 0.02 * phrase_hit
            hybrid_rank += 0.01 * min(exact_token_hits, 2)
            hybrid_rank += 0.004 * min(term_hits, 4)

        ranked.append(
            {
                'conversation_id': entry.get('conversation_id'),
                'role': entry.get('role'),
                'content': entry.get('content'),
                'timestamp': entry.get('timestamp'),
                'summary_id': entry.get('summary_id'),
                'score': hybrid_output_score,
                '_hybrid_rank': hybrid_rank,
            }
        )
        if include_internal_scores:
            ranked[-1]['retrieval_score'] = hybrid_output_score
            ranked[-1]['semantic_score'] = dense_score

    ranked.sort(
        key=lambda item: (
            float(item.get('_hybrid_rank') or 0.0),
            float(item.get('score') or 0.0),
            _timestamp_sort_value(item.get('timestamp')),
        ),
        reverse=True,
    )
    out: list[dict[str, Any]] = []
    for item in ranked[: int(top_k)]:
        row = _public_trace_row(item)
        if include_internal_scores:
            row['retrieval_score'] = float(item.get('retrieval_score') or row['score'])
            row['semantic_score'] = float(item.get('semantic_score') or 0.0)
        out.append(row)
    return out


def _merge_trace_and_summary_candidates(
    *,
    trace_candidates: list[dict[str, Any]],
    summary_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for candidate in trace_candidates:
        merged[_trace_public_key(candidate)] = dict(candidate)
    for candidate in summary_candidates:
        merged[_summary_public_key(candidate)] = dict(candidate)
    out = list(merged.values())
    out.sort(
        key=lambda item: (
            float(item.get('retrieval_score', item.get('score')) or 0.0),
            _timestamp_sort_value(item.get('timestamp_iso') or item.get('timestamp')),
            1 if str(item.get('source_kind') or '') == 'summary' else 0,
        ),
        reverse=True,
    )
    return out


def _embed_with_purpose(
    embed_fn: Callable[..., list[float]],
    text: str,
    *,
    mode: str,
    purpose: str,
) -> list[float]:
    try:
        return embed_fn(text, mode=mode, purpose=purpose)
    except TypeError as exc:
        if 'purpose' not in str(exc):
            raise
        # Compatibility with legacy test doubles exposing embed(text, mode=...).
        return embed_fn(text, mode=mode)


def _message_is_trace_eligible(message: dict[str, Any]) -> bool:
    return memory_trace_summary_store.message_is_trace_eligible(message)


def _trace_exists_for_message(
    conversation_id: str,
    message: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> bool:
    return memory_trace_summary_store.trace_exists_for_message(
        conversation_id,
        message,
        conn_factory=conn_factory,
        logger=logger,
    )


def save_new_traces(
    conversation: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
) -> None:
    memory_trace_summary_store.save_new_traces(
        conversation,
        conn_factory=conn_factory,
        embed_fn=embed_fn,
        logger=logger,
        message_is_trace_eligible_fn=_message_is_trace_eligible,
        trace_exists_for_message_fn=_trace_exists_for_message,
        embed_with_purpose_fn=_embed_with_purpose,
    )


def _emit_retrieval_error_result(
    *,
    started_at: float,
    top_k: int,
    exc: Exception,
    logger: Any,
    log_name: str,
) -> MemoryRetrievalResult:
    error_class = exc.__class__.__name__
    chat_turn_logger.emit(
        'memory_retrieve',
        status='error',
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        error_code='upstream_error',
        payload={
            'top_k_requested': int(top_k),
            'top_k_returned': 0,
            'reason_code': 'retrieve_error',
            'error_code': 'upstream_error',
            'error_class': error_class,
        },
    )
    if log_name == 'retrieve_embed_failed':
        logger.warning('retrieve_embed_failed class=%s', error_class)
    else:
        logger.error('retrieve_error class=%s', error_class)
    return MemoryRetrievalResult(
        traces=[],
        ok=False,
        top_k_requested=int(top_k),
        error_code='upstream_error',
        error_class=error_class,
        reason_code='retrieve_error',
    )


def retrieve_result(
    query: str,
    top_k: int | None = None,
    *,
    include_internal_scores: bool = False,
    include_summary_candidates: bool = False,
    runtime_embedding_value_fn: Callable[[str], Any],
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
) -> MemoryRetrievalResult:
    """
    Return a status-bearing bounded hybrid recall over traces.
    The public shape remains stable: top_k stays the final cap and rows stay
    compatible with downstream timestamp/summary enrichment.
    On retrieval errors, the result is explicit while preserving fail-open callers.
    """
    started_at = time.perf_counter()
    if top_k is None:
        top_k = int(runtime_embedding_value_fn('top_k'))

    try:
        q_vec = _embed_with_purpose(
            embed_fn,
            query,
            mode='query',
            purpose='query',
        )
    except Exception as exc:
        return _emit_retrieval_error_result(
            started_at=started_at,
            top_k=int(top_k),
            exc=exc,
            logger=logger,
            log_name='retrieve_embed_failed',
        )

    try:
        dense_candidates = _retrieve_dense_candidates(
            q_vec,
            limit=_internal_recall_limit(int(top_k)),
            conn_factory=conn_factory,
        )
        lexical_candidates = _retrieve_lexical_candidates(
            query,
            limit=_internal_recall_limit(int(top_k)),
            conn_factory=conn_factory,
        )
        out = _merge_hybrid_candidates(
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            top_k=int(top_k),
            include_internal_scores=include_internal_scores,
        )
        summary_candidates: list[dict[str, Any]] = []
        if include_summary_candidates:
            summary_candidates = _retrieve_summary_candidates(
                q_vec,
                limit=_summary_lane_limit(int(top_k)),
                conn_factory=conn_factory,
            )
            out = _merge_trace_and_summary_candidates(
                trace_candidates=out,
                summary_candidates=summary_candidates,
            )
        chat_turn_logger.emit(
            'memory_retrieve',
            status='ok',
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            payload={
                'top_k_requested': int(top_k),
                'top_k_returned': len(out),
                'dense_candidates_count': len(dense_candidates),
                'lexical_candidates_count': len(lexical_candidates),
                'summary_candidates_count': len(summary_candidates),
            },
        )
        return MemoryRetrievalResult(
            traces=out,
            ok=True,
            top_k_requested=int(top_k),
            reason_code='no_data' if not out else None,
        )
    except Exception as exc:
        return _emit_retrieval_error_result(
            started_at=started_at,
            top_k=int(top_k),
            exc=exc,
            logger=logger,
            log_name='retrieve_error',
        )


def retrieve(
    query: str,
    top_k: int | None = None,
    *,
    include_internal_scores: bool = False,
    include_summary_candidates: bool = False,
    runtime_embedding_value_fn: Callable[[str], Any],
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
) -> list[dict[str, Any]]:
    """
    Return a bounded hybrid recall over traces.
    The public shape remains stable: top_k stays the final cap and rows stay
    compatible with downstream timestamp/summary enrichment.
    Return [] on error to avoid blocking response pipeline.
    """
    return retrieve_result(
        query,
        top_k=top_k,
        include_internal_scores=include_internal_scores,
        include_summary_candidates=include_summary_candidates,
        runtime_embedding_value_fn=runtime_embedding_value_fn,
        conn_factory=conn_factory,
        embed_fn=embed_fn,
        logger=logger,
    ).traces


def save_summary(
    conversation_id: str,
    summary: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
) -> None:
    memory_trace_summary_store.save_summary(
        conversation_id,
        summary,
        conn_factory=conn_factory,
        embed_fn=embed_fn,
        logger=logger,
        embed_with_purpose_fn=_embed_with_purpose,
    )


def update_traces_summary_id(
    conversation_id: str,
    summary_id: str,
    start_ts: str | None,
    end_ts: str | None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> None:
    memory_trace_summary_store.update_traces_summary_id(
        conversation_id,
        summary_id,
        start_ts,
        end_ts,
        conn_factory=conn_factory,
        logger=logger,
    )


def get_summary_for_trace(
    trace: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    return memory_trace_summary_store.get_summary_for_trace(
        trace,
        conn_factory=conn_factory,
        logger=logger,
    )


def enrich_traces_with_summaries(
    traces: list[dict[str, Any]],
    *,
    get_summary_for_trace_fn: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> list[dict[str, Any]]:
    return memory_trace_summary_store.enrich_traces_with_summaries(
        traces,
        get_summary_for_trace_fn=get_summary_for_trace_fn,
    )
