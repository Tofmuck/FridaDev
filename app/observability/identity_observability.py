from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

_IDENTITY_HASH_CHARS = 12


def _canonical_side(target_side: str) -> str:
    return 'frida' if str(target_side) == 'frida' else 'user'


def _text(value: Any) -> str:
    return str(value or '').strip()


def _short_hash(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:_IDENTITY_HASH_CHARS]


def _text_fingerprint(value: Any) -> dict[str, Any]:
    text = _text(value)
    return {
        'present': bool(text),
        'chars': len(text),
        'sha256_12': _short_hash(text),
    }


def _empty_static_layer() -> dict[str, Any]:
    payload = _text_fingerprint('')
    payload['source_present'] = False
    return payload


def _static_layer(value: Any, *, source: Any = None) -> dict[str, Any]:
    payload = _text_fingerprint(value)
    source_text = _text(source)
    payload['source_present'] = bool(source_text)
    if source_text:
        payload['source'] = source_text
    return payload


def _empty_mutable_layer() -> dict[str, Any]:
    payload = _text_fingerprint('')
    payload.update(
        {
            'source_trace_id_present': False,
            'updated_by': None,
            'update_reason_present': False,
            'update_reason_chars': 0,
            'update_reason_sha256_12': None,
            'updated_ts': None,
        }
    )
    return payload


def _mutable_layer(value: Mapping[str, Any] | None) -> dict[str, Any]:
    entry = value if isinstance(value, Mapping) else {}
    payload = _text_fingerprint(entry.get('content'))
    update_reason = _text(entry.get('update_reason'))
    payload.update(
        {
            'source_trace_id_present': bool(_text(entry.get('source_trace_id'))),
            'updated_by': _text(entry.get('updated_by')) or None,
            'update_reason_present': bool(update_reason),
            'update_reason_chars': len(update_reason),
            'update_reason_sha256_12': _short_hash(update_reason),
            'updated_ts': _text(entry.get('updated_ts') or entry.get('created_ts')) or None,
        }
    )
    return payload


def _clean_texts(values: Sequence[Any]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text:
            cleaned.append(text)
    return cleaned


def _char_stats(values: Sequence[Any]) -> tuple[bool, int, int]:
    cleaned = _clean_texts(values)
    lengths = [len(item) for item in cleaned]
    if not lengths:
        return False, 0, 0
    return True, sum(lengths), max(lengths)


def build_identities_read_payload(
    *,
    target_side: str,
    source_kind: str,
    selected_count: int,
    content_values: Sequence[Any],
    requested_limit: int | None = None,
) -> dict[str, Any]:
    side = _canonical_side(target_side)
    content_present, total_chars, max_chars = _char_stats(content_values)
    payload = {
        'target_side': side,
        'source_kind': str(source_kind or '').strip(),
        'frida_count': int(selected_count) if side == 'frida' else 0,
        'user_count': int(selected_count) if side == 'user' else 0,
        'selected_count': int(selected_count),
        'content_present': bool(content_present),
        'total_chars': int(total_chars),
        'max_chars': int(max_chars),
        'truncated': False,
    }
    if requested_limit is not None:
        limit = max(0, int(requested_limit))
        payload['requested_limit'] = limit
        payload['truncated'] = bool(limit and int(selected_count) >= limit)
    return payload


def empty_identity_prompt_injection_payload() -> dict[str, Any]:
    return {
        'injected': False,
        'identity_block_present': False,
        'identity_block_chars': 0,
        'identity_block_sha256_12': None,
        'used_identity_ids_count': 0,
        'staging_included': False,
        'subjects': {
            'llm': {
                'static': _empty_static_layer(),
                'mutable': _empty_mutable_layer(),
            },
            'user': {
                'static': _empty_static_layer(),
                'mutable': _empty_mutable_layer(),
            },
        },
    }


def build_identity_prompt_injection_payload(
    *,
    identity_block: Any,
    used_identity_ids: Sequence[Any],
    llm_static: Any,
    user_static: Any,
    frida_mutable: Mapping[str, Any] | None,
    user_mutable: Mapping[str, Any] | None,
    llm_static_source: Any = None,
    user_static_source: Any = None,
) -> dict[str, Any]:
    block = _text(identity_block)
    payload = empty_identity_prompt_injection_payload()
    payload.update(
        {
            'injected': bool(block),
            'identity_block_present': bool(block),
            'identity_block_chars': len(block),
            'identity_block_sha256_12': _short_hash(block),
            'used_identity_ids_count': len([item for item in used_identity_ids if _text(item)]),
            'staging_included': False,
            'subjects': {
                'llm': {
                    'static': _static_layer(llm_static, source=llm_static_source),
                    'mutable': _mutable_layer(frida_mutable),
                },
                'user': {
                    'static': _static_layer(user_static, source=user_static_source),
                    'mutable': _mutable_layer(user_mutable),
                },
            },
        }
    )
    return payload


def build_identity_write_payload(
    *,
    target_side: str,
    write_mode: str,
    write_effect: str,
    persisted_count: int,
    evidence_count: int,
    observed_count: int,
    retained_count: int,
    actions_count: Mapping[str, int],
    observed_values: Sequence[Any],
    mode: str | None = None,
    content_present: bool | None = None,
) -> dict[str, Any]:
    content_present_value, total_chars, max_chars = _char_stats(observed_values)
    payload = {
        'target_side': _canonical_side(target_side),
        'write_mode': str(write_mode or '').strip(),
        'write_effect': str(write_effect or '').strip(),
        'persisted_count': int(persisted_count),
        'evidence_count': int(evidence_count),
        'observed_count': int(observed_count),
        'retained_count': int(retained_count),
        'actions_count': {str(key): int(value or 0) for key, value in actions_count.items()},
        'content_present': bool(content_present if content_present is not None else content_present_value),
        'observed_total_chars': int(total_chars),
        'observed_max_chars': int(max_chars),
    }
    if mode is not None:
        payload['mode'] = str(mode or '').strip()
    return payload


def summarize_guard_filtered_entries(
    filtered_entries: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    counts = {'frida': 0, 'user': 0}
    reason_codes_by_side: dict[str, list[str]] = {'frida': [], 'user': []}
    seen_reason_codes: dict[str, set[str]] = {'frida': set(), 'user': set()}
    for entry in filtered_entries:
        subject = str(entry.get('subject') or '').strip().lower()
        side = 'frida' if subject == 'llm' else 'user' if subject == 'user' else None
        if side is None:
            continue
        counts[side] += 1
        reason_code = str(entry.get('reason') or '').strip()
        if reason_code and reason_code not in seen_reason_codes[side]:
            seen_reason_codes[side].add(reason_code)
            reason_codes_by_side[side].append(reason_code)
    return counts, reason_codes_by_side
