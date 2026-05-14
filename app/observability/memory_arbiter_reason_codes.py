from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping


_FALLBACK_REASON_CODES = {
    "parse_or_runtime_error": "fallback_parse_or_runtime_error",
    "prompt_missing": "fallback_prompt_missing",
    "timeout": "fallback_timeout",
}

_KNOWN_REASON_CODES = {
    "below_contextual_gain_threshold",
    "below_semantic_threshold",
    "circumstantial_low_response_utility",
    "circumstantial_penalty_applied",
    "legacy_ids_format",
    "lexical_near_duplicate_low_context_gain",
    "missing_from_llm_output",
    "redundant_with_recent",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256_12(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _normalize_fragment(value: str) -> str:
    text = value.strip().lower()
    text = text.split("(", 1)[0].strip()
    text = re.sub(r"\s+", "_", text)
    return re.sub(r"[^a-z0-9_:-]+", "", text)


def arbiter_reason_code(reason: Any) -> str:
    text = _text(reason)
    if not text:
        return "unspecified"

    for fragment in (part.strip() for part in text.split("|")):
        normalized = _normalize_fragment(fragment)
        if not normalized:
            continue
        if normalized == "fallback":
            return "fallback"
        if normalized.startswith("fallback:"):
            fallback_reason = normalized.split(":", 1)[1]
            return _FALLBACK_REASON_CODES.get(fallback_reason, "fallback")
        if normalized in _KNOWN_REASON_CODES:
            return normalized

    return "model_reason"


def compact_arbiter_reason_observability(reason: Any) -> dict[str, Any]:
    text = _text(reason)
    return {
        "reason_code": arbiter_reason_code(text),
        "reason_chars": len(text),
        "reason_sha256_12": _sha256_12(text),
    }


def rejection_reason_code_counts(
    decisions: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        if bool(decision.get("keep", False)):
            continue
        code = arbiter_reason_code(decision.get("reason"))
        counts[code] = counts.get(code, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {key: value for key, value in ordered[:limit]}


def compact_reason_code_counts_from_mapping(
    raw_counts: Mapping[str, Any],
    *,
    limit: int = 5,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw_reason, raw_count in raw_counts.items():
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 0
        if count <= 0:
            continue
        code = arbiter_reason_code(raw_reason)
        counts[code] = counts.get(code, 0) + count
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {key: value for key, value in ordered[:limit]}
