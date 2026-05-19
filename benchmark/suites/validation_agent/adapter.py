"""Payload adapter for the validation_agent benchmark suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROMPT_PATH = Path("app/prompts/validation_agent.txt")
FIXTURE_PATH = Path("benchmark/suites/validation_agent/fixtures/validation_agent_primary_cases.json")

TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 140
TIMEOUT_S = 10

MAX_VALIDATION_CONTEXT_JSON_CHARS = 4200
MAX_PRIMARY_VERDICT_JSON_CHARS = 1000
MAX_JUSTIFICATIONS_JSON_CHARS = 700
MAX_CANONICAL_INPUTS_JSON_CHARS = 700

ALLOWED_POSTURES = {"answer", "clarify", "suspend"}
ALLOWED_OUTPUT_REGIMES = {"simple", "meta"}

_URL_NOT_READ_STATES = {
    "page_not_read_snippet_fallback",
    "page_not_read_crawl_empty",
    "page_not_read_error",
}


def load_prompt(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def load_fixtures(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("validation_agent fixture file must contain a non-empty cases list")
    for case in cases:
        validate_fixture(case)
    return cases


def validate_fixture(case: dict[str, Any]) -> None:
    required = {
        "id",
        "origin",
        "source_reference",
        "design_note",
        "dialogue",
        "primary",
        "canonical",
        "expected",
    }
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"fixture {case.get('id', '<unknown>')} missing keys: {missing}")
    if not isinstance(case["dialogue"], list) or not case["dialogue"]:
        raise ValueError(f"fixture {case['id']} dialogue must be a non-empty list")

    expected = case["expected"]
    posture = expected.get("final_judgment_posture")
    regime = expected.get("final_output_regime")
    if posture not in ALLOWED_POSTURES:
        raise ValueError(f"fixture {case['id']} invalid expected posture: {posture}")
    if regime not in ALLOWED_OUTPUT_REGIMES:
        raise ValueError(f"fixture {case['id']} invalid expected output regime: {regime}")


def build_payload(
    case: dict[str, Any],
    model: str,
    prompt: str | None = None,
    *,
    generation_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt_text = prompt if prompt is not None else load_prompt()
    settings = generation_settings or generation_params()
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": build_user_content(case)},
        ],
        "temperature": settings["temperature"],
        "top_p": settings["top_p"],
        "max_tokens": settings["max_tokens"],
    }


def build_user_content(case: dict[str, Any]) -> str:
    primary_verdict = build_primary_verdict(case)
    canonical_inputs = build_canonical_inputs(case)
    hard_guards = evaluate_hard_guards(primary_verdict, canonical_inputs)
    time_reference = validation_time_reference(canonical_inputs)

    compacted_time_reference = bounded_json_preview(time_reference, max_chars=420) if time_reference else ""
    compacted_validation_dialogue_context = compacted_validation_dialogue_context_text(
        build_validation_dialogue_context(case),
        time_reference=time_reference,
    )
    compacted_primary_verdict = bounded_json_preview(primary_verdict, max_chars=MAX_PRIMARY_VERDICT_JSON_CHARS)
    compacted_justifications = bounded_json_preview(
        case.get("justifications") or {},
        max_chars=MAX_JUSTIFICATIONS_JSON_CHARS,
    )
    compacted_canonical_inputs = bounded_json_preview(
        canonical_inputs,
        max_chars=MAX_CANONICAL_INPUTS_JSON_CHARS,
    )
    hard_guard_block = ""
    if hard_guards.get("applied_hard_guards"):
        hard_guard_block = (
            "hard_guards (contraintes deterministes non cassables):\n"
            f"{bounded_json_preview(hard_guards, max_chars=320)}\n\n"
        )
    return (
        "temporal_reference (autorite locale pour lire le validation_dialogue_context):\n"
        f"{compacted_time_reference or '{}'}\n\n"
        "validation_dialogue_context (matiere hermeneutique principale, fenetre dialogique locale canonisee):\n"
        f"{compacted_validation_dialogue_context}\n\n"
        "primary_verdict (recommendation structuree amont, secondaire et non terminale):\n"
        f"{compacted_primary_verdict}\n\n"
        "justifications (support secondaire frere, hors primary_verdict):\n"
        f"{compacted_justifications}\n\n"
        "canonical_inputs (supports secondaires de relecture contextuelle):\n"
        f"{compacted_canonical_inputs}\n\n"
        f"{hard_guard_block}"
        "Tache:\n"
        "- decide final_judgment_posture\n"
        "- decide final_output_regime\n"
        "- relis le dernier enonce et le dialogue comme texte dans la tension Warum / Wofür / Wozu, sans checklist ni sortie dediee\n"
        "- privilegie la lecture la plus naturelle du tour, la continuite dialogique locale et la reponse simple\n"
        "- si answer reste possible, privilegie final_output_regime = simple\n"
        "- reserve meta aux cas ou une reprise meta est reellement necessaire\n"
        "- si un hard guard interdit answer, choisis entre clarify et suspend\n"
        "- un hard guard ne force pas a lui seul meta\n"
        "- validation_decision legacy sera derivee downstream: ne l'invente pas\n"
        "- reponds en JSON strict uniquement\n"
        '- schema attendu: {"schema_version":"v1","final_judgment_posture":"answer|clarify|suspend","final_output_regime":"simple|meta","arbiter_reason":"raison_courte_lisible"}'
    )


def build_validation_dialogue_context(case: dict[str, Any]) -> dict[str, Any]:
    messages = []
    for item in case["dialogue"]:
        messages.append(
            {
                "role": item["role"],
                "content": item["content"],
                **({"temporal_label": item["temporal_label"]} if item.get("temporal_label") else {}),
            }
        )
    return {"schema_version": "v1", "messages": messages}


def build_primary_verdict(case: dict[str, Any]) -> dict[str, Any]:
    primary = case["primary"]
    posture = primary["judgment_posture"]
    regime = primary["discursive_regime"]
    return {
        "schema_version": "v1",
        "system_state": primary.get("system_state", "ok"),
        "epistemic_regime": primary.get("epistemic_regime", "answerable"),
        "epistemic_regime_reason": primary.get("epistemic_regime_reason", "fixture"),
        "judgment_posture": posture,
        "judgment_posture_reason": primary.get("judgment_posture_reason", "fixture"),
        "discursive_regime": regime,
        "discursive_regime_reason": primary.get("discursive_regime_reason", "fixture"),
        "proof_regime": primary.get("proof_regime", "internal"),
        "proof_regime_reason": primary.get("proof_regime_reason", "fixture"),
        "uncertainty_posture": primary.get("uncertainty_posture", "normal"),
        "uncertainty_posture_reason": primary.get("uncertainty_posture_reason", "fixture"),
        "source_priority": primary.get(
            "source_priority",
            ["tour_utilisateur", "temps", "memoire/contexte_recent/identity", "resume", "web", "stimmung"],
        ),
        "source_conflicts": primary.get("source_conflicts", []),
        "active_signal_families": primary.get("active_signal_families", []),
        "dialogue_phase": primary.get("dialogue_phase", "continuation"),
    }


def build_canonical_inputs(case: dict[str, Any]) -> dict[str, Any]:
    canonical = case["canonical"]
    return {
        "time_input": canonical.get(
            "time_input",
            {
                "now_utc_iso": "2026-05-18T14:48:27Z",
                "timezone": "Europe/Paris",
                "now_local_iso": "2026-05-18T16:48:27+02:00",
                "local_date": "2026-05-18",
                "local_time": "16:48:27",
            },
        ),
        "user_turn_input": {
            "content": canonical.get("current_user_message", ""),
            "speaker": "user",
        },
        "user_turn_signals": canonical.get(
            "user_turn_signals",
            {
                "qualified_turn": canonical.get("qualified_turn", "question"),
                "ambiguity_present": canonical.get("ambiguity_present", False),
                "explicit_external_reference": canonical.get("explicit_external_reference", False),
                "temporal_signal": canonical.get("temporal_signal", "none"),
            },
        ),
        "recent_context_input": canonical.get("recent_context_input", {"available": True, "turns_count": 2}),
        "recent_window_input": canonical.get("recent_window_input", {"available": True}),
        "memory_retrieved": canonical.get("memory_retrieved", {"items_count": 0}),
        "memory_arbitration": canonical.get("memory_arbitration", {"kept_count": 0, "dropped_count": 0}),
        "summary_input": canonical.get("summary_input", {"available": False}),
        "identity_input": canonical.get("identity_input", {"available": False}),
        "stimmung_input": canonical.get("stimmung_input", {"available": True, "dominant_tone": "neutral"}),
        "web_input": canonical.get("web_input", {"mode": "none", "materially_used": False}),
    }


def evaluate_hard_guards(
    primary_verdict: dict[str, Any], canonical_inputs: dict[str, Any]
) -> dict[str, Any]:
    web_input = canonical_inputs.get("web_input") or {}
    guards: list[str] = []

    if web_input.get("explicit_url_detected") and web_input.get("read_state") in _URL_NOT_READ_STATES:
        guards.append("explicit_url_not_read")

    proof_regime = primary_verdict.get("proof_regime")
    web_material_used = bool(web_input.get("materially_used") or web_input.get("evidence_available"))
    if proof_regime == "verification_externe_requise" and not web_material_used:
        guards.append("external_verification_missing")

    if not guards:
        return {"applied_hard_guards": [], "hard_guard_effect": None, "allowed_postures": ["answer", "clarify", "suspend"]}
    return {
        "applied_hard_guards": guards,
        "hard_guard_effect": "answer_forbidden",
        "allowed_postures": ["clarify", "suspend"],
    }


def compact_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 3)].rstrip()}..."


def bounded_json_preview(value: Any, *, max_chars: int) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(raw) <= max_chars:
        return raw
    preview_chars = max(32, max_chars - 48)
    bounded = json.dumps(
        {"truncated": True, "preview": compact_text(raw, max_chars=preview_chars)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    while len(bounded) > max_chars and preview_chars > 16:
        preview_chars -= 16
        bounded = json.dumps(
            {"truncated": True, "preview": compact_text(raw, max_chars=preview_chars)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return bounded


def validation_time_reference(canonical_inputs: dict[str, Any]) -> dict[str, Any]:
    time_payload = canonical_inputs.get("time_input") or {}
    now_utc_iso = str(time_payload.get("now_utc_iso") or "").strip()
    timezone_name = str(time_payload.get("timezone") or "").strip()
    if not now_utc_iso or not timezone_name:
        return {}
    return {
        "now_utc_iso": now_utc_iso,
        "timezone": timezone_name,
        "now_local_iso": str(time_payload.get("now_local_iso") or "").strip(),
        "local_date": str(time_payload.get("local_date") or "").strip(),
        "local_time": str(time_payload.get("local_time") or "").strip(),
    }


def compacted_validation_dialogue_context_text(
    value: dict[str, Any],
    *,
    time_reference: dict[str, Any] | None = None,
) -> str:
    raw_messages = value.get("messages")
    if not isinstance(raw_messages, list):
        return bounded_json_preview(value, max_chars=MAX_VALIDATION_CONTEXT_JSON_CHARS)
    retained_messages: list[dict[str, Any]] = []
    content_truncated = False
    for item in raw_messages[-5:]:
        role = str((item or {}).get("role") or "")
        if role not in {"user", "assistant"}:
            continue
        raw_content = str((item or {}).get("content") or "")
        content = compact_text(raw_content, max_chars=420)
        content_truncated = content_truncated or raw_content != content
        retained = {
            "role": role,
            "timestamp": (item or {}).get("timestamp") or None,
            "content": content,
        }
        if item.get("temporal_label"):
            retained["temporal_label"] = str(item.get("temporal_label"))
        retained_messages.append(retained)

    compacted_payload: dict[str, Any] = {
        "schema_version": str(value.get("schema_version") or "v1"),
        "message_count": int(value.get("source_message_count") or len(raw_messages)),
        "retained_message_count": len(retained_messages),
        "current_user_retained": bool(
            value.get(
                "current_user_retained",
                bool(retained_messages and retained_messages[-1].get("role") == "user"),
            )
        ),
        "last_assistant_retained": bool(
            value.get(
                "last_assistant_retained",
                any(item.get("role") == "assistant" for item in retained_messages),
            )
        ),
        "messages": retained_messages,
        "truncated": bool(value.get("truncated", False) or content_truncated),
    }
    if time_reference:
        compacted_payload["time_reference"] = {
            key: str(time_reference.get(key) or "")
            for key in ("now_utc_iso", "timezone", "now_local_iso", "local_date", "local_time")
            if str(time_reference.get(key) or "")
        }
    return bounded_json_preview(compacted_payload, max_chars=MAX_VALIDATION_CONTEXT_JSON_CHARS)


def dry_run_response(case: dict[str, Any]) -> str:
    expected = case["expected"]
    payload = {
        "schema_version": "v1",
        "final_judgment_posture": expected["final_judgment_posture"],
        "final_output_regime": expected["final_output_regime"],
        "arbiter_reason": "dry-run expected fixture decision",
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def generation_params(*, max_tokens: int | None = None) -> dict[str, Any]:
    resolved_max_tokens = MAX_TOKENS if max_tokens is None else int(max_tokens)
    if resolved_max_tokens <= 0:
        raise ValueError("validation_agent max_tokens must be positive")
    return {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": resolved_max_tokens,
        "timeout_s": TIMEOUT_S,
    }
