from __future__ import annotations

"""Content-free observability helpers for active conversation documents."""

import hashlib
from typing import Any, Mapping


def _text(value: Any, *, max_chars: int = 500) -> str:
    text = str(value or '').strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars]
    return text


def _to_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def _sha256_12(value: Any) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _metadata_from_mapping(item: Mapping[str, Any]) -> dict[str, Any]:
    document_id = _text(item.get('document_id'), max_chars=120)
    metadata = {
        'document_id': document_id,
        'document_ref': _sha256_12(document_id),
        'filename': _text(item.get('filename'), max_chars=500) or 'document',
        'media_type': _text(item.get('media_type'), max_chars=120),
        'source_extension': _text(item.get('source_extension'), max_chars=40),
        'byte_size': _to_int(item.get('byte_size') if 'byte_size' in item else item.get('bytes')),
        'text_chars': _to_int(item.get('text_chars') if 'text_chars' in item else item.get('chars')),
        'token_estimate': _to_int(item.get('token_estimate')),
        'text_sha256_12': _text(
            item.get('text_sha256_12') if 'text_sha256_12' in item else item.get('sha256_12'),
            max_chars=12,
        ),
        'source': 'active_conversation_documents',
        'raw_content_included': False,
    }
    metadata.update(_ocr_metadata_from_mapping(item))
    return metadata


def _metadata_from_decision(decision: Any) -> dict[str, Any]:
    document_id = _text(getattr(decision, 'document_id', ''), max_chars=120)
    metadata = {
        'document_id': document_id,
        'document_ref': _sha256_12(document_id),
        'filename': _text(getattr(decision, 'filename', ''), max_chars=500) or 'document',
        'media_type': _text(getattr(decision, 'media_type', ''), max_chars=120),
        'source_extension': _text(getattr(decision, 'source_extension', ''), max_chars=40),
        'byte_size': _to_int(getattr(decision, 'byte_size', 0)),
        'text_chars': _to_int(getattr(decision, 'text_chars', 0)),
        'token_estimate': _to_int(getattr(decision, 'token_estimate', 0)),
        'text_sha256_12': _text(getattr(decision, 'text_sha256_12', ''), max_chars=12),
        'source': 'active_conversation_documents',
        'raw_content_included': False,
    }
    metadata.update(
        {
            'ocr_applied': _to_bool(getattr(decision, 'ocr_applied', False)),
            'ocr_engine': _text(getattr(decision, 'ocr_engine', ''), max_chars=120),
            'ocr_languages': _text(getattr(decision, 'ocr_languages', ''), max_chars=120),
            'ocr_duration_ms': _to_int(getattr(decision, 'ocr_duration_ms', 0)),
        }
    )
    return metadata


def _ocr_metadata_from_mapping(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'ocr_applied': _to_bool(item.get('ocr_applied')),
        'ocr_engine': _text(item.get('ocr_engine'), max_chars=120),
        'ocr_languages': _text(item.get('ocr_languages'), max_chars=120),
        'ocr_duration_ms': _to_int(item.get('ocr_duration_ms')),
    }


def build_prompt_decision_payload(lane: Any) -> dict[str, Any]:
    decisions = list(getattr(lane, 'decisions', ()) or ())
    documents: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    injected_count = 0
    not_injected_count = 0
    too_large_count = 0
    empty_count = 0
    ocr_applied_count = 0
    ocr_duration_ms_total = 0
    ocr_engine_counts: dict[str, int] = {}

    for decision in decisions:
        injected = bool(getattr(decision, 'injected', False))
        reason_code = _text(getattr(decision, 'reason_code', ''), max_chars=120)
        metadata = _metadata_from_decision(decision)
        metadata.update(
            {
                'active': True,
                'injected': injected,
                'reason_code': reason_code,
            }
        )
        documents.append(metadata)
        if metadata.get('ocr_applied'):
            ocr_applied_count += 1
            ocr_duration_ms_total += _to_int(metadata.get('ocr_duration_ms'))
            engine = _text(metadata.get('ocr_engine'), max_chars=120) or 'unknown'
            ocr_engine_counts[engine] = int(ocr_engine_counts.get(engine, 0)) + 1
        if injected:
            injected_count += 1
            continue
        not_injected_count += 1
        reason = reason_code or 'document_not_injected'
        reason_counts[reason] = int(reason_counts.get(reason, 0)) + 1
        if reason == 'document_too_large_for_turn':
            too_large_count += 1
        if reason == 'document_empty_text':
            empty_count += 1

    status = 'not_applicable'
    if documents:
        status = 'partial' if not_injected_count else 'ok'
    return {
        'kind': 'active_document_prompt_decisions',
        'source_kind': 'active_conversation_documents',
        'status': status,
        'active_count': len(documents),
        'injected_count': injected_count,
        'not_injected_count': not_injected_count,
        'too_large_count': too_large_count,
        'empty_count': empty_count,
        'ocr_applied_count': ocr_applied_count,
        'ocr_duration_ms_total': ocr_duration_ms_total,
        'ocr_engine_counts': dict(sorted(ocr_engine_counts.items())),
        'reason_code_counts': dict(sorted(reason_counts.items())),
        'documents': documents,
        'future_biblio_included': False,
        'raw_content_included': False,
    }


def emit_prompt_decision_event(lane: Any, *, chat_turn_logger_module: Any) -> bool:
    payload = build_prompt_decision_payload(lane)
    if _to_int(payload.get('active_count')) <= 0:
        return False
    emitter = getattr(chat_turn_logger_module, 'emit', None)
    if not callable(emitter):
        return False
    return bool(
        emitter(
            'active_documents',
            status='ok',
            payload=payload,
        )
    )


def log_activation_success(
    admin_logs_module: Any,
    *,
    conversation_id: str,
    document: Mapping[str, Any],
) -> None:
    logger = getattr(admin_logs_module, 'log_event', None)
    if not callable(logger):
        return
    payload = _metadata_from_mapping(document)
    payload.update(
        {
            'conversation_id': _text(conversation_id, max_chars=120),
            'active': True,
            'event_kind': 'active_document_activation',
            'future_biblio_included': False,
        }
    )
    logger('active_document_activated', **payload)


def log_activation_failure(
    admin_logs_module: Any,
    *,
    conversation_id: str,
    extraction: Mapping[str, Any],
) -> None:
    logger = getattr(admin_logs_module, 'log_event', None)
    if not callable(logger):
        return
    payload = _metadata_from_mapping(extraction)
    payload.update(
        {
            'conversation_id': _text(conversation_id, max_chars=120),
            'active': False,
            'injected': False,
            'status': _text(extraction.get('status'), max_chars=80) or 'activation_failed',
            'reason_code': _text(extraction.get('reason_code'), max_chars=120) or 'document_runtime_unavailable',
            'event_kind': 'active_document_activation_failed',
            'future_biblio_included': False,
        }
    )
    logger('active_document_activation_failed', **payload)


def log_manual_remove(
    admin_logs_module: Any,
    *,
    conversation_id: str,
    document_id: str,
    reason_code: str = 'manual_remove',
) -> None:
    logger = getattr(admin_logs_module, 'log_event', None)
    if not callable(logger):
        return
    doc_id = _text(document_id, max_chars=120)
    logger(
        'active_document_removed',
        conversation_id=_text(conversation_id, max_chars=120),
        document_id=doc_id,
        document_ref=_sha256_12(doc_id),
        active=False,
        injected=False,
        reason_code=_text(reason_code, max_chars=120) or 'manual_remove',
        source='active_conversation_documents',
        future_biblio_included=False,
        raw_content_included=False,
    )
