from __future__ import annotations

from typing import Any, Mapping, Sequence


def _canonical_side(target_side: str) -> str:
    return 'frida' if str(target_side) == 'frida' else 'user'


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
