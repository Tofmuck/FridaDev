from __future__ import annotations

import json
from typing import Any


ALLOWED_TONES = {
    "apaisement",
    "enthousiasme",
    "curiosite",
    "confusion",
    "frustration",
    "colere",
    "anxiete",
    "decouragement",
    "neutralite",
}
EXPECTED_KEYS = {"schema_version", "present", "tones", "dominant_tone", "confidence"}
EXPECTED_TONE_KEYS = {"tone", "strength"}


def score_response(case: dict[str, Any], raw_text: str | None, provider_error: str | None) -> dict[str, Any]:
    if provider_error:
        return _empty_score(provider_error=provider_error)
    if raw_text is None:
        return _empty_score(provider_error="dry_run")

    try:
        data = _load_json_object(raw_text)
    except Exception as exc:
        return _empty_score(json_valid=False, schema_valid=False, provider_error=f"json_error:{exc}")

    schema_errors = validate_signal_payload(data)
    schema_valid = not schema_errors
    if not schema_valid:
        return {
            **_empty_score(json_valid=True, schema_valid=False, provider_error="schema_error"),
            "schema_errors": schema_errors,
        }

    tones = [{"tone": item["tone"], "strength": int(item["strength"])} for item in data["tones"]]
    dominant = data["dominant_tone"]
    expected = case.get("expected_acceptables") or {}
    expected_dominants = set(expected.get("dominant_tones") or [])
    acceptable_tones = set(expected.get("tones") or expected_dominants)
    avoid_tones = set(expected.get("avoid_tones") or [])
    tone_names = {item["tone"] for item in tones}
    strengths = [int(item["strength"]) for item in tones]

    dominant_match = not expected_dominants or dominant in expected_dominants
    tone_overlap = not acceptable_tones or bool(tone_names & acceptable_tones)
    avoid_hits = sorted(tone_names & avoid_tones)
    max_strength = _int_or_none(expected.get("max_strength"))
    min_strength = _int_or_none(expected.get("min_strength"))
    max_strength_exceeded = max_strength is not None and strengths and max(strengths) > max_strength
    min_strength_missed = min_strength is not None and strengths and max(strengths) < min_strength
    tags = set(case.get("tags") or [])
    neutral_overcoded = "neutral_probe" in tags and (dominant != "neutralite" or max(strengths or [0]) > 5)
    flat_miss = "marked_affect" in tags and dominant == "neutralite"
    hard_pass = (
        dominant_match
        and tone_overlap
        and not avoid_hits
        and not max_strength_exceeded
        and not min_strength_missed
        and not neutral_overcoded
        and not flat_miss
    )

    return {
        "json_valid": True,
        "schema_valid": True,
        "schema_errors": [],
        "present": data["present"],
        "tones": tones,
        "dominant_tone": dominant,
        "confidence": float(data["confidence"]),
        "dominant_match": dominant_match,
        "tone_overlap": tone_overlap,
        "avoid_hits": avoid_hits,
        "max_strength_exceeded": max_strength_exceeded,
        "min_strength_missed": min_strength_missed,
        "neutral_overcoded": neutral_overcoded,
        "flat_miss": flat_miss,
        "hard_pass": hard_pass,
        "error": None,
    }


def summarize_model(model: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
    count = max(len(calls), 1)
    provider_errors = sum(1 for call in calls if not (call.get("provider") or {}).get("ok"))
    json_valid = sum(1 for call in calls if (call.get("score") or {}).get("json_valid"))
    schema_valid = sum(1 for call in calls if (call.get("score") or {}).get("schema_valid"))
    hard_pass = sum(1 for call in calls if (call.get("score") or {}).get("hard_pass"))
    avoid_hit_count = sum(len((call.get("score") or {}).get("avoid_hits") or []) for call in calls)
    neutral_overcoded = sum(1 for call in calls if (call.get("score") or {}).get("neutral_overcoded"))
    flat_miss = sum(1 for call in calls if (call.get("score") or {}).get("flat_miss"))
    completion_tokens = [
        int((call.get("provider") or {}).get("usage", {}).get("completion_tokens") or 0)
        for call in calls
    ]
    avg_latency = sum(float((call.get("provider") or {}).get("elapsed_ms") or 0.0) for call in calls) / count
    costs = [(call.get("provider") or {}).get("cost_estimate_usd") for call in calls]
    numeric_costs = [float(cost) for cost in costs if isinstance(cost, (int, float))]
    finish_reasons = sorted(
        {
            str((call.get("provider") or {}).get("finish_reason"))
            for call in calls
            if (call.get("provider") or {}).get("finish_reason") is not None
        }
    )
    dominant_counts: dict[str, int] = {}
    for call in calls:
        dominant = (call.get("score") or {}).get("dominant_tone")
        if dominant:
            dominant_counts[str(dominant)] = dominant_counts.get(str(dominant), 0) + 1

    hard_pass_rate = hard_pass / count
    schema_valid_rate = schema_valid / count
    verdict = _provisional_verdict(
        schema_valid_rate=schema_valid_rate,
        hard_pass_rate=hard_pass_rate,
        provider_errors=provider_errors,
        avoid_hit_count=avoid_hit_count,
        neutral_overcoded=neutral_overcoded,
        flat_miss=flat_miss,
    )
    return {
        "model": model,
        "provider_error_rate": provider_errors / count,
        "json_valid_rate": json_valid / count,
        "schema_valid_rate": schema_valid_rate,
        "hard_pass_rate": hard_pass_rate,
        "hard_pass_count": hard_pass,
        "avoid_hit_count": avoid_hit_count,
        "neutral_overcoded_count": neutral_overcoded,
        "flat_miss_count": flat_miss,
        "avg_latency_ms": round(avg_latency, 3),
        "cost_estimate_usd": round(sum(numeric_costs), 8) if numeric_costs else None,
        "avg_completion_tokens": round(sum(completion_tokens) / count, 3),
        "finish_reasons": finish_reasons,
        "dominant_counts": dominant_counts,
        "provisional_verdict": verdict,
        "notes": _notes(
            provider_errors=provider_errors,
            schema_valid=schema_valid,
            count=count,
            avoid_hit_count=avoid_hit_count,
            neutral_overcoded=neutral_overcoded,
            flat_miss=flat_miss,
        ),
    }


def validate_signal_payload(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(data.keys()) != EXPECTED_KEYS:
        errors.append("invalid_keys")
    if data.get("schema_version") != "v1":
        errors.append("invalid_schema_version")
    if not isinstance(data.get("present"), bool):
        errors.append("invalid_present")
    tones = data.get("tones")
    if not isinstance(tones, list):
        errors.append("invalid_tones")
        tones = []
    seen: set[str] = set()
    tone_names: list[str] = []
    for index, item in enumerate(tones):
        if not isinstance(item, dict):
            errors.append(f"tone_{index}:not_object")
            continue
        if set(item.keys()) != EXPECTED_TONE_KEYS:
            errors.append(f"tone_{index}:invalid_keys")
        tone = item.get("tone")
        if tone not in ALLOWED_TONES:
            errors.append(f"tone_{index}:invalid_tone")
        elif tone in seen:
            errors.append(f"tone_{index}:duplicate_tone")
        else:
            seen.add(str(tone))
            tone_names.append(str(tone))
        strength = item.get("strength")
        if isinstance(strength, bool) or not isinstance(strength, int) or strength < 1 or strength > 10:
            errors.append(f"tone_{index}:invalid_strength")
    confidence = data.get("confidence")
    if isinstance(confidence, bool):
        errors.append("invalid_confidence")
    else:
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            errors.append("invalid_confidence")
        else:
            if confidence_value < 0.0 or confidence_value > 1.0:
                errors.append("invalid_confidence")
    dominant = data.get("dominant_tone")
    present = data.get("present")
    if present is True:
        if not tone_names:
            errors.append("missing_tones_for_present")
        if not isinstance(dominant, str) or dominant not in tone_names:
            errors.append("invalid_dominant_tone")
    elif present is False:
        if tones or dominant is not None:
            errors.append("invalid_absent_signal")
    return errors


# Compatibility for callers internal to the historical mono-turn suite.
_schema_errors = validate_signal_payload


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


def _empty_score(
    *,
    json_valid: bool = False,
    schema_valid: bool = False,
    provider_error: str | None,
) -> dict[str, Any]:
    return {
        "json_valid": json_valid,
        "schema_valid": schema_valid,
        "schema_errors": [],
        "present": None,
        "tones": [],
        "dominant_tone": None,
        "confidence": None,
        "dominant_match": False,
        "tone_overlap": False,
        "avoid_hits": [],
        "max_strength_exceeded": False,
        "min_strength_missed": False,
        "neutral_overcoded": False,
        "flat_miss": False,
        "hard_pass": False,
        "error": provider_error,
    }


def _provisional_verdict(
    *,
    schema_valid_rate: float,
    hard_pass_rate: float,
    provider_errors: int,
    avoid_hit_count: int,
    neutral_overcoded: int,
    flat_miss: int,
) -> str:
    if provider_errors or schema_valid_rate < 1.0:
        return "exclure provisoirement"
    if hard_pass_rate >= 0.75 and avoid_hit_count <= 2 and neutral_overcoded <= 2 and flat_miss <= 2:
        return "candidat serieux"
    if hard_pass_rate >= 0.55:
        return "tester plus"
    return "exclure provisoirement"


def _notes(
    *,
    provider_errors: int,
    schema_valid: int,
    count: int,
    avoid_hit_count: int,
    neutral_overcoded: int,
    flat_miss: int,
) -> str:
    parts: list[str] = []
    if provider_errors:
        parts.append(f"{provider_errors} provider error(s)")
    if schema_valid < count:
        parts.append(f"{count - schema_valid} schema issue(s)")
    if avoid_hit_count:
        parts.append(f"{avoid_hit_count} avoid tone hit(s)")
    if neutral_overcoded:
        parts.append(f"{neutral_overcoded} neutral overcoding case(s)")
    if flat_miss:
        parts.append(f"{flat_miss} flat miss case(s)")
    return ", ".join(parts) or "schema stable"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
