from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


GENERATION_PARAMS = {
    "temperature": 0.1,
    "top_p": 1.0,
    "max_tokens": 220,
}

CONTEXT_WINDOW_TURNS = 5
MAX_CONTEXT_MESSAGE_CHARS = 220
MAX_CURRENT_TURN_CHARS = 600

_FIXTURE_FILES = {
    "primary": "stimmung_primary_cases.json",
    "diagnostic": "stimmung_primary_cases.json",
    "final": "stimmung_primary_final_cases.json",
    "real_final": "stimmung_primary_final_cases.json",
}


def prompt_path(repo_root: Path) -> Path:
    return repo_root / "app" / "prompts" / "stimmung_agent.txt"


def fixture_path(repo_root: Path, fixture_set: str = "primary") -> Path:
    filename = _FIXTURE_FILES.get(fixture_set)
    if not filename:
        raise ValueError(f"unknown stimmung fixture set: {fixture_set}")
    return repo_root / "benchmark" / "suites" / "stimmung" / "fixtures" / filename


def load_cases(repo_root: Path, fixture_set: str = "primary") -> list[dict[str, Any]]:
    path = fixture_path(repo_root, fixture_set=fixture_set)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("stimmung fixtures must be a JSON list")
    cases = [_normalize_case(case, index) for index, case in enumerate(data)]
    _validate_cases(cases, fixture_set=fixture_set)
    return cases


def build_payload(case: dict[str, Any], model: str, prompt_text: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": build_user_content(case)},
        ],
        **GENERATION_PARAMS,
    }


def build_user_content(case: dict[str, Any]) -> str:
    user_msg = str(case["current_user_message"]).strip()
    contextual_window = _serialize_recent_window(
        recent_turns=case.get("recent_turns"),
        user_msg=user_msg,
    )
    return (
        f"{contextual_window}\n\n"
        "Tour utilisateur courant (centre de l'analyse, signal a produire pour ce tour) :\n"
        f"{_compact_text(user_msg, max_chars=MAX_CURRENT_TURN_CHARS)}"
    )


def safe_model_slug(model: str) -> str:
    return (
        str(model or "model")
        .strip()
        .replace("/", "__")
        .replace(":", "_")
        .replace(" ", "_")
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _compact_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 3)].rstrip()}..."


def _serialize_recent_window(*, recent_turns: Any, user_msg: str) -> str:
    if not isinstance(recent_turns, list):
        return f"Aucun contexte recent exploitable ({CONTEXT_WINDOW_TURNS} tours max)."

    turns = [_mapping(item) for item in recent_turns if isinstance(item, Mapping)]
    turns = turns[-CONTEXT_WINDOW_TURNS:]
    if not turns:
        return f"Aucun contexte recent exploitable ({CONTEXT_WINDOW_TURNS} tours max)."

    lines = [f"Fenetre conversationnelle locale ({CONTEXT_WINDOW_TURNS} tours max) :"]
    for index, turn_payload in enumerate(turns, start=1):
        turn_status = str(turn_payload.get("turn_status") or "unknown")
        lines.append(f"- Tour {index} [{turn_status}]")
        raw_messages = turn_payload.get("messages")
        if not isinstance(raw_messages, list):
            continue
        for message in raw_messages:
            message_payload = _mapping(message)
            role = str(message_payload.get("role") or "").strip()
            content = _compact_text(message_payload.get("content"), max_chars=MAX_CONTEXT_MESSAGE_CHARS)
            if role in {"user", "assistant"} and content:
                lines.append(f"  - {role}: {content}")

    return "\n".join(lines)


def _normalize_case(case: Any, index: int) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise ValueError(f"stimmung fixture #{index} must be an object")
    normalized = dict(case)
    normalized.setdefault("origin", "artificial_diagnostic")
    normalized.setdefault("difficulty", "hard" if index else "simple")
    normalized.setdefault("tags", [])
    normalized.setdefault("recent_turns", [])
    return normalized


def _validate_cases(cases: list[dict[str, Any]], *, fixture_set: str) -> None:
    seen_ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise ValueError("stimmung fixture missing id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate stimmung fixture id: {case_id}")
        seen_ids.add(case_id)

        if not str(case.get("current_user_message") or "").strip():
            raise ValueError(f"stimmung fixture {case_id} has empty current_user_message")
        if not str(case.get("design_note") or "").strip():
            raise ValueError(f"stimmung fixture {case_id} must define design_note")
        if not isinstance(case.get("tags"), list) or not case.get("tags"):
            raise ValueError(f"stimmung fixture {case_id} must define tags")
        expected = case.get("expected_acceptables")
        if not isinstance(expected, dict):
            raise ValueError(f"stimmung fixture {case_id} must define expected_acceptables")
        if not expected.get("dominant_tones"):
            raise ValueError(f"stimmung fixture {case_id} must define expected dominant_tones")

    expected_count = 10 if fixture_set in {"final", "real_final"} else 24
    if len(cases) != expected_count:
        raise ValueError(f"stimmung {fixture_set} campaign expects {expected_count} cases, got {len(cases)}")
