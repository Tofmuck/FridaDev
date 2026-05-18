from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from benchmark.core.campaign import sha256_text


GENERATION_PARAMS = {
    "temperature": 0.3,
    "top_p": 1.0,
    "max_tokens": 2000,
}


def prompt_path(repo_root: Path) -> Path:
    return repo_root / "app" / "prompts" / "summary_system.txt"


def load_material(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("summary material must be a JSON object")
    source = _mapping(data.get("source"))
    turns = data.get("turns")
    if not isinstance(turns, list) or not turns:
        raise ValueError("summary material must define a non-empty turns list")
    normalized_turns = [_normalize_turn(turn, index) for index, turn in enumerate(turns)]
    user_content = build_user_content(normalized_turns)
    return {
        "source": dict(source),
        "turns": normalized_turns,
        "user_content": user_content,
        "user_content_sha256": sha256_text(user_content),
        "turn_count": len(normalized_turns),
        "char_count": len(user_content),
    }


def build_user_content(turns: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for turn in turns:
        role = "Utilisateur" if turn.get("role") == "user" else "Assistant"
        ts = str(turn.get("local_date") or "").strip()
        prefix = f"[{ts}] " if ts else ""
        parts.append(f"{prefix}{role} : {turn.get('content', '')}")
    return "Voici le dialogue à résumer :\n\n" + "\n\n".join(parts)


def generation_params(*, max_tokens: int | None = None) -> dict[str, Any]:
    params = dict(GENERATION_PARAMS)
    if max_tokens is not None:
        params["max_tokens"] = int(max_tokens)
    return params


def build_payload(
    *,
    model: str,
    prompt_text: str,
    user_content: str,
    generation_params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": user_content},
        ],
        **dict(generation_params or GENERATION_PARAMS),
    }


def safe_model_slug(model: str) -> str:
    return (
        str(model or "model")
        .strip()
        .replace("/", "__")
        .replace(":", "_")
        .replace(" ", "_")
    )


def material_public_metadata(material: Mapping[str, Any]) -> dict[str, Any]:
    source = _mapping(material.get("source"))
    return {
        "source_kind": source.get("source_kind") or "live_conversation",
        "conversation_id": source.get("conversation_id"),
        "first_ts": source.get("first_ts"),
        "last_ts": source.get("last_ts"),
        "turn_count": material.get("turn_count"),
        "char_count": material.get("char_count"),
        "approx_tokens": source.get("approx_tokens"),
        "user_content_sha256": material.get("user_content_sha256"),
        "raw_material_written": False,
    }


def _normalize_turn(turn: Any, index: int) -> dict[str, str]:
    if not isinstance(turn, Mapping):
        raise ValueError(f"summary turn #{index} must be an object")
    role = str(turn.get("role") or "").strip()
    if role not in {"user", "assistant"}:
        raise ValueError(f"summary turn #{index} has invalid role: {role}")
    content = str(turn.get("content") or "")
    if not content.strip():
        raise ValueError(f"summary turn #{index} has empty content")
    return {
        "role": role,
        "content": content,
        "timestamp": str(turn.get("timestamp") or ""),
        "local_date": str(turn.get("local_date") or ""),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
