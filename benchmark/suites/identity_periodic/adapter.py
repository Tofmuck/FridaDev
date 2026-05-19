from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import identity_temporal_guard  # noqa: E402


GENERATION_PARAMS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 1400,
}

DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_TIMEOUT_S = 90
FIXTURE_FILE = "haiku_smoke_buffer.json"


def prompt_path(repo_root: Path) -> Path:
    return repo_root / "app" / "prompts" / "identity_periodic_agent.txt"


def source_path(repo_root: Path) -> Path:
    return repo_root / "app" / "memory" / "memory_identity_periodic_agent.py"


def fixture_path(repo_root: Path, fixture_set: str = "haiku_smoke") -> Path:
    if fixture_set not in {"haiku_smoke", "diagnostic"}:
        raise ValueError(f"unknown identity_periodic fixture set: {fixture_set}")
    return repo_root / "benchmark" / "suites" / "identity_periodic" / "fixtures" / FIXTURE_FILE


def load_fixture(repo_root: Path, fixture_set: str = "haiku_smoke") -> dict[str, Any]:
    path = fixture_path(repo_root, fixture_set=fixture_set)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("identity periodic fixture must be a JSON object")
    _validate_fixture(data)
    return data


def buffer_target_pairs(repo_root: Path) -> int:
    tree = ast.parse(source_path(repo_root).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "BUFFER_TARGET_PAIRS":
                    value = ast.literal_eval(node.value)
                    return int(value)
    raise ValueError("BUFFER_TARGET_PAIRS not found")


def build_payload_for_model(fixture: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    target_pairs = buffer_target_pairs(repo_root)
    raw_pairs = list(fixture.get("buffer_pairs") or [])
    sanitized_pairs, source_summary = identity_temporal_guard.sanitized_buffer_pairs_with_source_summary(raw_pairs)
    return {
        "buffer_pairs": sanitized_pairs,
        "buffer_pairs_count": len(sanitized_pairs),
        "buffer_target_pairs": target_pairs,
        "identities": dict(fixture.get("identities") or {}),
        "mutable_budget": dict(fixture.get("mutable_budget") or {}),
        "identity_temporal_policy": {
            "relative_claims_are_non_durable": True,
            "reject_markers": list(identity_temporal_guard.WEAK_RELATIVE_TEMPORAL_IDENTITY_MARKERS),
            "source_summary": source_summary,
            "instruction": (
                "Reject weak relative temporal source claims instead of promoting them "
                "to mutable identity."
            ),
        },
    }


def build_payload(
    *,
    model: str,
    prompt_text: str,
    payload_for_model: dict[str, Any],
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": json.dumps(payload_for_model, ensure_ascii=False, indent=2)},
        ],
        **GENERATION_PARAMS,
    }


def safe_model_slug(model: str) -> str:
    return (
        str(model or "model")
        .strip()
        .replace("/", "__")
        .replace(":", "_")
        .replace(" ", "_")
    )


def _validate_fixture(data: dict[str, Any]) -> None:
    pairs = data.get("buffer_pairs")
    if not isinstance(pairs, list) or len(pairs) != 15:
        raise ValueError("identity periodic haiku smoke fixture expects exactly 15 buffer pairs")
    for index, pair in enumerate(pairs, start=1):
        if not isinstance(pair, dict):
            raise ValueError(f"buffer pair #{index} must be an object")
        for role in ("user", "assistant"):
            message = pair.get(role)
            if not isinstance(message, dict):
                raise ValueError(f"buffer pair #{index} missing {role} message")
            if not str(message.get("content") or "").strip():
                raise ValueError(f"buffer pair #{index} has empty {role} content")
    identities = data.get("identities")
    if not isinstance(identities, dict) or set(identities.keys()) != {"llm", "user"}:
        raise ValueError("identity periodic fixture must define llm/user identities")
    budget = data.get("mutable_budget")
    if not isinstance(budget, dict) or not {"target_chars", "max_chars"}.issubset(budget.keys()):
        raise ValueError("identity periodic fixture must define mutable_budget target_chars/max_chars")
