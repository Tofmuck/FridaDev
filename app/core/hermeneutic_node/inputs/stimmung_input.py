from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"
SIGNAL_META_KEY = "affective_turn_signal"
MAX_SIGNAL_TURNS = 4
ACTIVE_TONES_LIMIT = 3
MIN_ACTIVE_STRENGTH = 3
ACTIVE_TONE_DELTA = 2
STABLE_MIN_SUPPORT = 2
STABLE_MIN_STRENGTH = 4
STABLE_DELTA_THRESHOLD = 2
HYSTERESIS_DELTA = 2

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


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _as_strength(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("validation_error")
    if value < 1 or value > 10:
        raise ValueError("validation_error")
    return int(value)


def _as_confidence(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("validation_error")
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("validation_error") from exc
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("validation_error")
    return confidence


def _build_missing_stimmung() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "present": False,
        "dominant_tone": None,
        "active_tones": [],
        "stability": "",
        "shift_state": "",
        "turns_considered": 0,
    }


def _validate_signal(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    if set(payload.keys()) != {"schema_version", "present", "tones", "dominant_tone", "confidence"}:
        raise ValueError("validation_error")
    if str(payload.get("schema_version") or "") != SCHEMA_VERSION:
        raise ValueError("validation_error")

    present = payload.get("present")
    if not isinstance(present, bool):
        raise ValueError("validation_error")

    raw_tones = payload.get("tones")
    if not isinstance(raw_tones, list):
        raise ValueError("validation_error")

    tones: list[dict[str, Any]] = []
    tone_names: list[str] = []
    seen: set[str] = set()
    for item in raw_tones:
        tone_payload = _mapping(item)
        if set(tone_payload.keys()) != {"tone", "strength"}:
            raise ValueError("validation_error")
        tone = str(tone_payload.get("tone") or "").strip()
        if tone not in ALLOWED_TONES:
            raise ValueError("validation_error")
        strength = _as_strength(tone_payload.get("strength"))
        if tone in seen:
            continue
        seen.add(tone)
        tone_names.append(tone)
        tones.append({"tone": tone, "strength": strength})

    confidence = _as_confidence(payload.get("confidence"))
    dominant_tone = payload.get("dominant_tone")

    if present:
        if not tones:
            raise ValueError("validation_error")
        if not isinstance(dominant_tone, str) or dominant_tone not in tone_names:
            raise ValueError("validation_error")
    else:
        if tones or dominant_tone is not None:
            raise ValueError("validation_error")

    return {
        "schema_version": SCHEMA_VERSION,
        "present": present,
        "tones": tones,
        "dominant_tone": dominant_tone,
        "confidence": confidence,
    }


def _extract_signal_from_message(message: Mapping[str, Any]) -> dict[str, Any] | None:
    if str(message.get("role") or "") != "user":
        return None
    meta = _mapping(message.get("meta"))
    if SIGNAL_META_KEY not in meta:
        return None
    try:
        signal = _validate_signal(meta.get(SIGNAL_META_KEY))
    except ValueError:
        return None
    if not signal["present"]:
        return None
    return signal


def extract_recent_affective_turn_signals(
    *,
    messages: Sequence[Mapping[str, Any]] | None,
    max_signal_turns: int = MAX_SIGNAL_TURNS,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for message in _sequence(messages):
        if not isinstance(message, Mapping):
            continue
        signal = _extract_signal_from_message(message)
        if signal is not None:
            signals.append(signal)
    return signals[-max(0, int(max_signal_turns)) :] if max_signal_turns >= 0 else signals


def _latest_user_signal(messages: Sequence[Mapping[str, Any]] | None) -> dict[str, Any] | None:
    for message in reversed(list(_sequence(messages))):
        if not isinstance(message, Mapping):
            continue
        if str(message.get("role") or "") != "user":
            continue
        return _extract_signal_from_message(message)
    return None


def _ordered_tones(
    *,
    score_map: Mapping[str, float],
    strength_map: Mapping[str, int],
    last_seen_map: Mapping[str, int],
) -> list[str]:
    return sorted(
        score_map.keys(),
        key=lambda tone: (
            -float(score_map.get(tone) or 0.0),
            -int(strength_map.get(tone) or 0),
            -int(last_seen_map.get(tone) or 0),
            tone,
        ),
    )


def _clamp_strength(value: float) -> int:
    return max(1, min(10, int(round(value))))


def build_stimmung_input(
    *,
    messages: Sequence[Mapping[str, Any]] | None,
    max_signal_turns: int = MAX_SIGNAL_TURNS,
) -> dict[str, Any]:
    latest_signal = _latest_user_signal(messages)
    if latest_signal is None:
        return _build_missing_stimmung()

    signals = extract_recent_affective_turn_signals(messages=messages, max_signal_turns=max_signal_turns)
    if not signals:
        return _build_missing_stimmung()

    score_map: dict[str, float] = {}
    present_weight_map: dict[str, float] = {}
    support_count_map: dict[str, int] = {}
    last_seen_map: dict[str, int] = {}

    for index, signal in enumerate(signals, start=1):
        weight = float(index)
        for tone_payload in signal["tones"]:
            tone = str(tone_payload["tone"])
            strength = int(tone_payload["strength"])
            score_map[tone] = score_map.get(tone, 0.0) + (weight * strength)
            present_weight_map[tone] = present_weight_map.get(tone, 0.0) + weight
            support_count_map[tone] = support_count_map.get(tone, 0) + 1
            last_seen_map[tone] = index

    if not score_map:
        return _build_missing_stimmung()

    strength_map = {
        tone: _clamp_strength(score_map[tone] / max(present_weight_map.get(tone, 1.0), 1.0))
        for tone in score_map
    }
    ordered_tones = _ordered_tones(
        score_map=score_map,
        strength_map=strength_map,
        last_seen_map=last_seen_map,
    )
    candidate_tone = ordered_tones[0]
    previous_dominant = signals[-2]["dominant_tone"] if len(signals) > 1 else None
    dominant_tone = candidate_tone
    hysteresis_retained = False

    if previous_dominant and previous_dominant in strength_map and candidate_tone != previous_dominant:
        if strength_map[candidate_tone] - strength_map[previous_dominant] < HYSTERESIS_DELTA:
            dominant_tone = previous_dominant
            hysteresis_retained = True

    dominant_strength = int(strength_map[dominant_tone])
    active_tones: list[dict[str, Any]] = []
    minimum_strength = max(MIN_ACTIVE_STRENGTH, dominant_strength - ACTIVE_TONE_DELTA)
    for tone in ordered_tones:
        strength = int(strength_map[tone])
        if tone != dominant_tone and strength < minimum_strength:
            continue
        active_tones.append({"tone": tone, "strength": strength})
        if len(active_tones) >= ACTIVE_TONES_LIMIT:
            break

    if not any(item["tone"] == dominant_tone for item in active_tones):
        active_tones.insert(0, {"tone": dominant_tone, "strength": dominant_strength})
        active_tones = active_tones[:ACTIVE_TONES_LIMIT]
    else:
        active_tones = sorted(
            active_tones,
            key=lambda item: (
                0 if item["tone"] == dominant_tone else 1,
                -int(item["strength"]),
                str(item["tone"]),
            ),
        )

    second_strength = int(active_tones[1]["strength"]) if len(active_tones) > 1 else 0
    latest_dominant = str(signals[-1]["dominant_tone"] or "")
    dominant_support = int(support_count_map.get(dominant_tone) or 0)

    if (
        dominant_support >= STABLE_MIN_SUPPORT
        and latest_dominant == dominant_tone
        and dominant_strength >= STABLE_MIN_STRENGTH
        and (dominant_strength - second_strength) >= STABLE_DELTA_THRESHOLD
    ):
        stability = "stable"
    elif latest_dominant == dominant_tone:
        stability = "emerging"
    else:
        stability = "volatile"

    if hysteresis_retained:
        shift_state = "candidate_shift"
    elif not previous_dominant or previous_dominant == dominant_tone:
        shift_state = "steady"
    elif latest_dominant != dominant_tone:
        shift_state = "candidate_shift"
    else:
        shift_state = "shifted"

    return {
        "schema_version": SCHEMA_VERSION,
        "present": True,
        "dominant_tone": dominant_tone,
        "active_tones": active_tones,
        "stability": stability,
        "shift_state": shift_state,
        "turns_considered": len(signals),
    }
