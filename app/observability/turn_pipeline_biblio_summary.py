from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.biblio_librarian_agent_read_model import build_biblio_librarian_agent_summary
from observability.turn_pipeline_summary_support import (
    _event_ts,
    _events_for_stage,
    _mapping,
    _payload,
    _sequence,
    _sha256_12_text,
    _status,
    _to_float,
    _to_int,
)


_BIBLIO_TOKEN_CHARS = set('abcdefghijklmnopqrstuvwxyz0123456789_-.:/')
_BIBLIO_HEX_CHARS = set('0123456789abcdef')


def _biblio_token(value: Any, *, max_chars: int = 120) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered != text:
        return f'sha256:{_sha256_12_text(text)}'
    if any(char not in _BIBLIO_TOKEN_CHARS for char in lowered):
        return f'sha256:{_sha256_12_text(text)}'
    return lowered[:max_chars]


def _biblio_hash(value: Any) -> str | None:
    text = str(value or '').strip().lower()
    if len(text) == 12 and all(char in _BIBLIO_HEX_CHARS for char in text):
        return text
    return None


def _biblio_doc_id(value: Any) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    lowered = text.lower()
    if len(text) <= 16 and all(char in _BIBLIO_TOKEN_CHARS for char in lowered):
        return text[:8]
    return f'sha256:{_sha256_12_text(text)}'


def _biblio_reason_counts(value: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, count in _mapping(value).items():
        reason = _biblio_token(key)
        if reason:
            counts[reason] = _to_int(count)
    return dict(sorted(counts.items()))


def _biblio_hashes(value: Any) -> list[str]:
    hashes: list[str] = []
    for item in _sequence(value):
        digest = _biblio_hash(item)
        if digest:
            hashes.append(digest)
    return hashes


def _biblio_doc_ids(value: Any) -> list[str]:
    ids: list[str] = []
    for item in _sequence(value):
        doc_id = _biblio_doc_id(item)
        if doc_id:
            ids.append(doc_id)
    return ids


def _biblio_tokens(value: Any) -> list[str]:
    tokens: list[str] = []
    for item in _sequence(value):
        token = _biblio_token(item)
        if token:
            tokens.append(token)
    return tokens[:24]


def _biblio_positions(value: Any) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for raw_item in _sequence(value):
        item = _mapping(raw_item)
        positions.append(
            {
                'page_no': item.get('page_no') if type(item.get('page_no')) is int else None,
                'para_no': item.get('para_no') if type(item.get('para_no')) is int else None,
                'paragraph_id': item.get('paragraph_id') if type(item.get('paragraph_id')) is int else None,
                'excerpt_start': item.get('excerpt_start') if type(item.get('excerpt_start')) is int else None,
                'excerpt_end': item.get('excerpt_end') if type(item.get('excerpt_end')) is int else None,
                'text_length': item.get('text_length') if type(item.get('text_length')) is int else None,
            }
        )
    return positions[:12]


def build_biblio_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    biblio_events = _events_for_stage(events, 'biblio')
    latest = biblio_events[-1] if biblio_events else None
    payload = _payload(latest or {})
    resolver = _mapping(payload.get('resolver'))
    extractor = _mapping(payload.get('extractor'))
    lane = _mapping(payload.get('lane'))
    counts = _mapping(payload.get('counts'))
    confidence = _mapping(payload.get('confidence'))
    passage_search = _mapping(payload.get('passage_search'))
    librarian_agent = build_biblio_librarian_agent_summary(payload)
    resolver_document = _mapping(resolver.get('document'))
    resolver_locator = _mapping(resolver.get('locator'))
    extractor_resolution = _mapping(extractor.get('resolution'))
    extractor_document = _mapping(extractor_resolution.get('document'))
    doc_ids = _biblio_doc_ids(lane.get('doc_id_shorts'))
    document_doc_id = _biblio_doc_id(resolver_document.get('doc_id_short')) or _biblio_doc_id(
        extractor_document.get('doc_id_short')
    )
    if document_doc_id and document_doc_id not in doc_ids:
        doc_ids.insert(0, document_doc_id)
    search_doc_ids = _biblio_doc_ids(passage_search.get('doc_id_shorts'))
    for doc_id in search_doc_ids:
        if doc_id not in doc_ids:
            doc_ids.append(doc_id)
    status = (
        _biblio_token(payload.get('status'))
        or (_status(latest or {}) if latest else None)
        or ('not_applicable' if not latest else 'unknown')
    )
    return {
        'source_kind': 'biblio_native_catalogue',
        'event_present': bool(latest),
        'enabled': bool(payload.get('enabled')),
        'used': bool(payload.get('used')),
        'status': status,
        'query_kind': _biblio_token(payload.get('query_kind')),
        'document_status': _biblio_token(resolver.get('status')),
        'document_reason_code': _biblio_token(resolver.get('reason_code')),
        'document_candidate_count': _to_int(resolver.get('document_candidate_count')),
        'document_candidate_ids': _biblio_doc_ids(resolver.get('document_candidate_ids')),
        'doc_id_shorts': doc_ids[:12],
        'locator_kind': _biblio_token(resolver_locator.get('kind')),
        'locator_candidate_count': _to_int(resolver.get('locator_candidate_count')),
        'requested_locator_kind': _biblio_token(resolver.get('requested_locator_kind')),
        'passage_status': _biblio_token(extractor.get('status')),
        'passage_reason_code': _biblio_token(extractor.get('reason_code')),
        'passage_chars': _to_int(extractor.get('passage_chars')) or _to_int(counts.get('passage_chars')),
        'passage_hash': _biblio_hash(extractor.get('passage_hash')),
        'passage_count': _to_int(lane.get('passage_count')) or _to_int(counts.get('passage_count')),
        'skipped_count': _to_int(lane.get('skipped_count')) or _to_int(counts.get('skipped_count')),
        'lane_present': bool(lane.get('present')),
        'lane_chars': _to_int(lane.get('chars')) or _to_int(counts.get('lane_chars')),
        'hashes': _biblio_hashes(lane.get('hashes')),
        'positions': _biblio_positions(lane.get('positions')),
        'search_candidate_count': _to_int(passage_search.get('candidate_count'))
        or _to_int(counts.get('candidate_count')),
        'search_total_candidate_count': _to_int(passage_search.get('total_candidate_count')),
        'context_fetch_count': _to_int(passage_search.get('context_call_count'))
        or _to_int(counts.get('context_call_count')),
        'plausible_context_count': _to_int(passage_search.get('plausible_context_count')),
        'selected_passage_count': _to_int(passage_search.get('selected_count'))
        or _to_int(counts.get('selected_count')),
        'passage_result_count': _to_int(passage_search.get('passage_result_count'))
        or _to_int(counts.get('passage_result_count')),
        'ambiguous': bool(passage_search.get('ambiguous')) or status == 'ambiguous',
        'lane_injected': bool(passage_search.get('lane_injected')) or bool(lane.get('present')),
        'endpoint_count': _to_int(passage_search.get('endpoint_count')) or _to_int(counts.get('endpoint_count')),
        'endpoint_kinds': _biblio_tokens(passage_search.get('endpoint_kinds')),
        'ranking_available': bool(passage_search.get('ranking_available')),
        'selection_reason_codes': _biblio_tokens(passage_search.get('selection_reason_codes')),
        'top_score': _to_float(passage_search.get('top_score')),
        'score_gap': _to_float(passage_search.get('score_gap')),
        'candidate_top_score': _to_float(passage_search.get('candidate_top_score')),
        'candidate_query_variant_count': _to_int(passage_search.get('candidate_query_variant_count')),
        'librarian_agent': librarian_agent,
        'librarian_agent_present': bool(librarian_agent.get('present')),
        'librarian_agent_mode': _biblio_token(librarian_agent.get('mode')),
        'librarian_agent_model_called': bool(librarian_agent.get('model_called')),
        'librarian_agent_candidate_plan_present': bool(librarian_agent.get('candidate_plan_present')),
        'librarian_agent_used_for_response': bool(librarian_agent.get('used_for_response')),
        'librarian_agent_product_response_changed': bool(librarian_agent.get('product_response_changed')),
        'librarian_agent_deterministic_controller': bool(librarian_agent.get('deterministic_controller')),
        'librarian_agent_tool_execution_status': _biblio_token(librarian_agent.get('tool_execution_status')),
        'librarian_agent_attempt_count': _to_int(librarian_agent.get('attempt_count')),
        'confidence_available': bool(confidence.get('available')),
        'confidence_reason_code': _biblio_token(confidence.get('reason_code')),
        'reason_code_counts': _biblio_reason_counts(payload.get('reason_code_counts')),
        'raw_content_included': False,
        'latest_ts': _event_ts(latest or {}),
    }
