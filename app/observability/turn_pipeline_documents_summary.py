from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.turn_pipeline_summary_support import (
    _event_ts,
    _events_for_stage,
    _mapping,
    _payload,
    _reason_code,
    _sequence,
    _status,
    _text,
    _to_bool,
    _to_int,
)


def _safe_document_items(value: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_item in _sequence(value):
        item = _mapping(raw_item)
        filename = _text(item.get('filename')) or 'document'
        items.append(
            {
                'document_id': _text(item.get('document_id')),
                'document_ref': _text(item.get('document_ref')),
                'filename': filename,
                'media_type': _text(item.get('media_type')),
                'source_extension': _text(item.get('source_extension')),
                'byte_size': _to_int(item.get('byte_size')),
                'text_chars': _to_int(item.get('text_chars')),
                'token_estimate': _to_int(item.get('token_estimate')),
                'text_sha256_12': _text(item.get('text_sha256_12')),
                'ocr_applied': _to_bool(item.get('ocr_applied')),
                'ocr_engine': _text(item.get('ocr_engine')),
                'ocr_languages': _text(item.get('ocr_languages')),
                'ocr_duration_ms': _to_int(item.get('ocr_duration_ms')),
                'active': bool(item.get('active')),
                'injected': bool(item.get('injected')),
                'reason_code': _text(item.get('reason_code')),
            }
        )
    return items


def build_documents_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    document_events = _events_for_stage(events, 'active_documents')
    latest = document_events[-1] if document_events else None
    payload = _payload(latest or {})
    documents = _safe_document_items(payload.get('documents'))
    reason_counts = dict(_mapping(payload.get('reason_code_counts')))
    active_count = _to_int(payload.get('active_count')) or len(documents)
    injected_count = _to_int(payload.get('injected_count')) or sum(1 for item in documents if item.get('injected'))
    not_injected_count = _to_int(payload.get('not_injected_count')) or sum(
        1 for item in documents if not item.get('injected')
    )
    too_large_count = _to_int(payload.get('too_large_count')) or _to_int(
        reason_counts.get('document_too_large_for_turn')
    )
    empty_count = _to_int(payload.get('empty_count')) or _to_int(reason_counts.get('document_empty_text'))
    ocr_applied_count = _to_int(payload.get('ocr_applied_count')) or sum(
        1 for item in documents if item.get('ocr_applied')
    )
    ocr_duration_ms_total = _to_int(payload.get('ocr_duration_ms_total')) or sum(
        _to_int(item.get('ocr_duration_ms')) for item in documents if item.get('ocr_applied')
    )
    ocr_engine_counts = dict(_mapping(payload.get('ocr_engine_counts')))
    if not ocr_engine_counts:
        for item in documents:
            if not item.get('ocr_applied'):
                continue
            engine = _text(item.get('ocr_engine')) or 'unknown'
            ocr_engine_counts[engine] = int(ocr_engine_counts.get(engine, 0)) + 1
    read_status = (_text(payload.get('read_status')) or '').lower()
    read_reason = _text(payload.get('read_reason_code'))
    if latest:
        read_error = read_status == 'error' or _status(latest) == 'error'
        if read_error:
            status = 'error'
            reason = read_reason or _reason_code(payload) or 'active_documents_read_error'
            read_reason = reason
            reason_counts[reason] = max(1, _to_int(reason_counts.get(reason)))
        else:
            status = 'active' if active_count else 'not_applicable'
            reason = _reason_code(payload)
        if not read_status:
            read_status = 'ok' if active_count else 'empty'
    else:
        status = 'not_applicable'
        reason = 'active_documents_not_observed'
        read_status = 'not_observed'
    return {
        'source_kind': 'active_conversation_documents',
        'event_present': bool(latest),
        'status': status,
        'read_status': read_status,
        'read_reason_code': read_reason,
        'active_count': active_count,
        'injected_count': injected_count,
        'not_injected_count': not_injected_count,
        'too_large_count': too_large_count,
        'empty_count': empty_count,
        'ocr_applied_count': ocr_applied_count,
        'ocr_duration_ms_total': ocr_duration_ms_total,
        'ocr_engine_counts': dict(sorted(ocr_engine_counts.items())),
        'reason_code_counts': reason_counts,
        'reason_code': reason,
        'documents': documents,
        'future_biblio_included': bool(payload.get('future_biblio_included')),
        'raw_content_included': False,
        'latest_ts': _event_ts(latest or {}),
    }
