from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GENERATION_PARAMS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 700,
}

_FIXTURE_FILES = {
    "human": "identity_extractor_human_cases.json",
    "diagnostic": "identity_extractor_human_cases.json",
}


def prompt_path(repo_root: Path) -> Path:
    return repo_root / "app" / "prompts" / "identity_extractor.txt"


def fixture_path(repo_root: Path, fixture_set: str = "human") -> Path:
    filename = _FIXTURE_FILES.get(fixture_set)
    if not filename:
        raise ValueError(f"unknown identity_extractor fixture set: {fixture_set}")
    return repo_root / "benchmark" / "suites" / "identity_extractor" / "fixtures" / filename


def load_cases(repo_root: Path, fixture_set: str = "human") -> list[dict[str, Any]]:
    path = fixture_path(repo_root, fixture_set=fixture_set)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("identity extractor fixtures must be a JSON list")
    cases = [_normalize_case(case, index) for index, case in enumerate(data)]
    _validate_cases(cases)
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
    subject = str(case["subject"]).upper()
    message = str(case["message"]).strip()
    return (
        "Here is the dialogue fragment to inspect for identity evidence.\n\n"
        "Return only the JSON object requested by the system prompt.\n\n"
        f"{subject}: {message}"
    )


def safe_model_slug(model: str) -> str:
    return (
        str(model or "model")
        .strip()
        .replace("/", "__")
        .replace(":", "_")
        .replace(" ", "_")
    )


def _normalize_case(case: Any, index: int) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise ValueError(f"identity extractor fixture #{index} must be an object")
    normalized = dict(case)
    normalized.setdefault("origin", "artificial_human_reading")
    normalized.setdefault("difficulty", "hard" if index else "simple")
    normalized.setdefault("tags", [])
    return normalized


def _validate_cases(cases: list[dict[str, Any]]) -> None:
    seen_ids: set[str] = set()
    subject_counts = {"user": 0, "llm": 0}
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise ValueError("identity extractor fixture missing id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate identity extractor fixture id: {case_id}")
        seen_ids.add(case_id)

        subject = str(case.get("subject") or "").strip()
        if subject not in subject_counts:
            raise ValueError(f"identity extractor fixture {case_id} has invalid subject: {subject}")
        subject_counts[subject] += 1

        if not str(case.get("message") or "").strip():
            raise ValueError(f"identity extractor fixture {case_id} has empty message")
        if not str(case.get("design_note") or "").strip():
            raise ValueError(f"identity extractor fixture {case_id} must define design_note")
        if not isinstance(case.get("tags"), list) or not case.get("tags"):
            raise ValueError(f"identity extractor fixture {case_id} must define tags")

    if len(cases) != 10:
        raise ValueError(f"identity extractor human campaign expects 10 cases, got {len(cases)}")
    if subject_counts != {"user": 5, "llm": 5}:
        raise ValueError(f"identity extractor human campaign expects 5 user and 5 llm cases, got {subject_counts}")
