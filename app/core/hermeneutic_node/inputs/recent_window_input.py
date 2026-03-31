from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"
MAX_RECENT_TURNS = 5


def _canonical_message(message: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role": str(message.get("role") or ""),
        "content": str(message.get("content") or ""),
        "timestamp": str(message.get("timestamp")) if message.get("timestamp") is not None else None,
    }


def _finalize_turn(*, messages: Sequence[Mapping[str, Any]], turn_status: str) -> dict[str, Any]:
    return {
        "turn_status": str(turn_status),
        "messages": [_canonical_message(message) for message in messages],
    }


def build_recent_window_input(
    *,
    recent_context_input_payload: Mapping[str, Any] | None,
    max_recent_turns: int = MAX_RECENT_TURNS,
) -> dict[str, Any]:
    raw_messages = []
    if isinstance(recent_context_input_payload, Mapping):
        maybe_messages = recent_context_input_payload.get("messages")
        if isinstance(maybe_messages, Sequence):
            raw_messages = [
                message
                for message in maybe_messages
                if isinstance(message, Mapping)
                and str(message.get("role") or "") in {"user", "assistant"}
            ]

    turns: list[dict[str, Any]] = []
    current_turn: list[Mapping[str, Any]] = []

    for message in raw_messages:
        role = str(message.get("role") or "")
        if role == "user":
            if current_turn:
                turns.append(_finalize_turn(messages=current_turn, turn_status="in_progress"))
            current_turn = [message]
            continue

        if not current_turn:
            # A leading assistant message remains visible in recent_context_input
            # but does not open a canonical recent turn on its own.
            continue

        current_turn.append(message)
        turns.append(_finalize_turn(messages=current_turn, turn_status="complete"))
        current_turn = []

    if current_turn:
        turns.append(_finalize_turn(messages=current_turn, turn_status="in_progress"))

    retained_turns = turns[-max(0, int(max_recent_turns)) :] if max_recent_turns >= 0 else list(turns)

    return {
        "schema_version": SCHEMA_VERSION,
        "max_recent_turns": int(max_recent_turns),
        "turn_count": len(retained_turns),
        "has_in_progress_turn": bool(retained_turns and retained_turns[-1]["turn_status"] == "in_progress"),
        "turns": retained_turns,
    }
