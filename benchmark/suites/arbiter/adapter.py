from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GENERATION_PARAMS = {
    "temperature": 0,
    "top_p": 1.0,
    "max_tokens": 600,
}

_FIXTURE_FILES = {
    "diagnostic": "arbiter_memory_cases.json",
    "tournament_round1": "arbiter_tournament_round1.jsonl",
    "tournament_final": "arbiter_tournament_final.jsonl",
}


def prompt_path(repo_root: Path) -> Path:
    return repo_root / "app" / "prompts" / "arbiter.txt"


def fixture_path(repo_root: Path, fixture_set: str = "diagnostic") -> Path:
    filename = _FIXTURE_FILES.get(fixture_set)
    if not filename:
        raise ValueError(f"unknown arbiter fixture set: {fixture_set}")
    return repo_root / "benchmark" / "suites" / "arbiter" / "fixtures" / filename


def load_cases(repo_root: Path, fixture_set: str = "diagnostic") -> list[dict[str, Any]]:
    path = fixture_path(repo_root, fixture_set=fixture_set)
    if path.suffix == ".jsonl":
        data = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("arbiter fixtures must be a JSON list or JSONL sequence")
    normalized = [_normalize_case(case, index) for index, case in enumerate(data)]
    _validate_cases(normalized)
    return normalized


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
    temporal_reference = case.get("temporal_reference")
    temporal_section = (
        f"=== Temporal reference ===\n{json.dumps(temporal_reference, ensure_ascii=False, indent=2)}\n\n"
        if isinstance(temporal_reference, dict) and temporal_reference
        else ""
    )
    recent_text = "\n".join(_format_recent_turn(turn) for turn in case.get("recent_turns", []))
    candidates_text = json.dumps(case.get("candidates", []), ensure_ascii=False, indent=2)
    return (
        f"{temporal_section}"
        f"=== Recent context ===\n{recent_text}\n\n"
        f"=== Candidate memories ===\n{candidates_text}"
    )


def _format_recent_turn(turn: dict[str, Any]) -> str:
    role = str(turn.get("role") or "?").upper()
    content = str(turn.get("content") or "")
    label = str(turn.get("temporal_label") or "").strip()
    prefix = f"[{label}] " if label else ""
    return f"{prefix}{role}: {content}"


def _normalize_case(case: dict[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise ValueError(f"fixture case #{index} must be an object")
    normalized = dict(case)
    normalized.setdefault("origin", "artificial_hard")
    normalized.setdefault("difficulty", "hard" if "hard" in normalized.get("tags", []) else "standard")
    if "recent_turn" in normalized and "recent_turns" not in normalized:
        normalized["recent_turns"] = [
            {
                "role": "user",
                "content": normalized.pop("recent_turn"),
                "temporal_label": normalized.pop(
                    "recent_temporal_label",
                    "lundi 18 mai 2026 à 14h Europe/Paris — aujourd'hui",
                ),
            }
        ]
    normalized.setdefault("recent_turns", [])
    normalized.setdefault("expected_keep_ids", [])

    candidates = []
    for candidate_index, candidate in enumerate(normalized.get("candidates") or []):
        item = dict(candidate)
        item.setdefault("source_kind", "trace")
        item.setdefault("source_lane", "global")
        item.setdefault("role", "user")
        item.setdefault("timestamp_iso", f"2026-05-{(candidate_index % 18) + 1:02d}T10:00:00Z")
        item.setdefault("retrieval_score", 0.78)
        item.setdefault("semantic_score", 0.74)
        item.setdefault("temporal_label", "date anonymisee — contexte de benchmark")
        candidates.append(item)
    normalized["candidates"] = candidates
    return normalized


def _validate_cases(cases: list[dict[str, Any]]) -> None:
    seen_case_ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise ValueError("fixture case missing id")
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate fixture case id: {case_id}")
        seen_case_ids.add(case_id)
        candidates = case.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError(f"fixture {case_id} must define candidates")
        candidate_ids = [str(item.get("candidate_id") or "").strip() for item in candidates if isinstance(item, dict)]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"fixture {case_id} has duplicate candidate ids")
        expected = set(case.get("expected_keep_ids") or [])
        unknown = expected - set(candidate_ids)
        if unknown:
            raise ValueError(f"fixture {case_id} expects unknown ids: {sorted(unknown)}")
        if not str(case.get("why") or "").strip():
            raise ValueError(f"fixture {case_id} must explain why")
