from __future__ import annotations

import json
from typing import Any


ALLOWED_SUBJECTS = {"user", "llm"}
ALLOWED_STABILITY = {"durable", "episodic", "unknown"}
ALLOWED_UTTERANCE_MODE = {"self_description", "projection", "role_play", "irony", "speculation", "unknown"}
ALLOWED_RECURRENCE = {"first_seen", "repeated", "habitual", "unknown"}
ALLOWED_SCOPE = {"user", "llm", "situation", "mixed", "unknown"}
ALLOWED_EVIDENCE_KIND = {"explicit", "inferred", "weak"}


def score_response(case: dict[str, Any], raw_text: str | None, provider_error: str | None) -> dict[str, Any]:
    if provider_error:
        return _empty_score(provider_error=provider_error)
    if raw_text is None:
        return _empty_score(provider_error="dry_run")

    try:
        data = _load_json_object(raw_text)
    except Exception as exc:
        return _empty_score(json_valid=False, schema_valid=False, provider_error=f"json_error:{exc}")

    entries = data.get("entries")
    if not isinstance(entries, list):
        return _empty_score(json_valid=True, schema_valid=False, provider_error="schema_error:missing_entries")

    errors: list[str] = []
    normalized_entries: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry_{index}:not_object")
            continue
        entry_errors = _validate_entry(entry, index)
        errors.extend(entry_errors)
        normalized_entries.append(
            {
                "subject": entry.get("subject"),
                "content": entry.get("content"),
                "stability": entry.get("stability"),
                "utterance_mode": entry.get("utterance_mode"),
                "recurrence": entry.get("recurrence"),
                "scope": entry.get("scope"),
                "evidence_kind": entry.get("evidence_kind"),
                "confidence": entry.get("confidence"),
                "reason": entry.get("reason"),
            }
        )

    schema_valid = not errors
    return {
        "json_valid": True,
        "schema_valid": schema_valid,
        "entry_count": len(entries),
        "entries": normalized_entries,
        "schema_errors": errors,
        "error": None if schema_valid else "schema_error",
        "case_subject": case.get("subject"),
    }


def summarize_model(model: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
    count = max(len(calls), 1)
    json_valid = sum(1 for call in calls if call["score"].get("json_valid"))
    schema_valid = sum(1 for call in calls if call["score"].get("schema_valid"))
    provider_errors = sum(1 for call in calls if not call["provider"].get("ok"))
    entry_count = sum(int(call["score"].get("entry_count") or 0) for call in calls)
    output_chars = sum(len(str(call["provider"].get("raw_text") or "")) for call in calls)
    avg_latency = sum(float(call["provider"].get("elapsed_ms") or 0.0) for call in calls) / count
    costs = [call["provider"].get("cost_estimate_usd") for call in calls]
    numeric_costs = [float(cost) for cost in costs if isinstance(cost, (int, float))]
    total_cost = round(sum(numeric_costs), 8) if numeric_costs else None
    finish_reasons = sorted(
        {
            str(call["provider"].get("finish_reason"))
            for call in calls
            if call["provider"].get("finish_reason") is not None
        }
    )
    return {
        "model": model,
        "json_valid_rate": json_valid / count,
        "schema_valid_rate": schema_valid / count,
        "provider_error_rate": provider_errors / count,
        "entry_count": entry_count,
        "output_chars": output_chars,
        "avg_output_chars": round(output_chars / count, 3),
        "avg_latency_ms": round(avg_latency, 3),
        "cost_estimate_usd": total_cost,
        "finish_reasons": finish_reasons,
        "notes": _notes(provider_errors, schema_valid, count, entry_count),
    }


def _validate_entry(entry: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    if entry.get("subject") not in ALLOWED_SUBJECTS:
        errors.append(f"entry_{index}:invalid_subject")
    if not str(entry.get("content") or "").strip():
        errors.append(f"entry_{index}:empty_content")
    if entry.get("stability") not in ALLOWED_STABILITY:
        errors.append(f"entry_{index}:invalid_stability")
    if entry.get("utterance_mode") not in ALLOWED_UTTERANCE_MODE:
        errors.append(f"entry_{index}:invalid_utterance_mode")
    if entry.get("recurrence") not in ALLOWED_RECURRENCE:
        errors.append(f"entry_{index}:invalid_recurrence")
    if entry.get("scope") not in ALLOWED_SCOPE:
        errors.append(f"entry_{index}:invalid_scope")
    if entry.get("evidence_kind") not in ALLOWED_EVIDENCE_KIND:
        errors.append(f"entry_{index}:invalid_evidence_kind")
    if not _confidence_in_range(entry.get("confidence")):
        errors.append(f"entry_{index}:invalid_confidence")
    if not str(entry.get("reason") or "").strip():
        errors.append(f"entry_{index}:empty_reason")
    return errors


def _load_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _confidence_in_range(value: Any) -> bool:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return False
    return 0.0 <= confidence <= 1.0


def _empty_score(
    *,
    json_valid: bool = False,
    schema_valid: bool = False,
    provider_error: str | None,
) -> dict[str, Any]:
    return {
        "json_valid": json_valid,
        "schema_valid": schema_valid,
        "entry_count": 0,
        "entries": [],
        "schema_errors": [],
        "error": provider_error,
        "case_subject": None,
    }


def _notes(provider_errors: int, schema_valid: int, count: int, entry_count: int) -> str:
    parts: list[str] = []
    if provider_errors:
        parts.append(f"{provider_errors} provider error(s)")
    if schema_valid < count:
        parts.append(f"{count - schema_valid} schema issue(s)")
    parts.append(f"{entry_count} extracted entrie(s)")
    return ", ".join(parts)
