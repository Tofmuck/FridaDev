from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace
from typing import Any, Mapping

from memory import memory_identity_periodic_agent, memory_identity_staging


def synthetic_pair(index: int, *, chars_per_message: int = 24) -> list[dict[str, str]]:
    user_marker = f"LOT0_USER_{index:02d}_"
    assistant_marker = f"LOT0_ASSISTANT_{index:02d}_"
    return [
        {"role": "user", "content": user_marker + ("u" * chars_per_message)},
        {"role": "assistant", "content": assistant_marker + ("a" * chars_per_message)},
    ]


def window_fingerprint(state: Mapping[str, Any]) -> str:
    payload = json.dumps(
        list(state.get("buffer_pairs") or []),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def no_change_contract() -> dict[str, Any]:
    verdicts = []
    for subject in ("llm", "user"):
        verdicts.append(
            {
                "subject": subject,
                "verdict": "no_change",
                "proposition": "",
                "reason_code": "no_mutable_identity_signal",
                "continuity_kind": "none",
                "source_refs": [],
                "guard_notes": [],
            }
        )
    return {
        "schema_version": "mutable_judge_v2",
        "meta": {
            "execution_status": "complete",
            "window_pairs_count": memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            "window_complete": True,
        },
        "verdicts": verdicts,
    }


def add_contract() -> dict[str, Any]:
    contract = no_change_contract()
    contract["verdicts"][1] = {
        "subject": "user",
        "verdict": "add",
        "proposition": "Tof tient une limite synthetique explicite stable.",
        "reason_code": "explicit_self_limit_continuity",
        "continuity_kind": "limit",
        "source_refs": ["pair_05"],
        "guard_notes": ["synthetic_fixture"],
    }
    return contract


def ok_judge_result(contract: Mapping[str, Any]) -> dict[str, Any]:
    verdicts = list(contract.get("verdicts") or [])
    return {
        "status": "ok",
        "reason_code": "judge_complete",
        "contract": copy.deepcopy(dict(contract)),
        "observability": {
            "status": "ok",
            "reason_code": "judge_complete",
            "schema_version": "mutable_judge_v2",
            "prompt_kind": "mutable_identity_judge_v2",
            "window_pairs_count": memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            "window_complete": True,
            "verdict_count": len(verdicts),
            "verdict_counts": {
                verdict: sum(1 for item in verdicts if item.get("verdict") == verdict)
                for verdict in sorted({str(item.get("verdict") or "") for item in verdicts})
            },
            "subjects_seen": sorted({str(item.get("subject") or "") for item in verdicts}),
            "subjects_touched": sorted(
                {str(item.get("subject") or "") for item in verdicts if item.get("verdict") == "add"}
            ),
            "continuity_kinds": sorted({str(item.get("continuity_kind") or "") for item in verdicts}),
            "reason_codes": sorted({str(item.get("reason_code") or "") for item in verdicts}),
            "source_refs_count": sum(len(item.get("source_refs") or []) for item in verdicts),
            "guard_notes_count": sum(len(item.get("guard_notes") or []) for item in verdicts),
        },
    }


class _Cursor:
    def __init__(self, backend: "SyntheticSqlStagingBackend") -> None:
        self.backend = backend
        self.row: tuple[Any, ...] | None = None

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: Any) -> bool:
        return False

    def execute(self, statement: str, params: tuple[Any, ...] | None = None) -> None:
        sql = " ".join(statement.split())
        values = tuple(params or ())
        if sql.startswith("SELECT") and "WHERE conversation_id = %s" in sql:
            self.row = self.backend.rows.get(str(values[0]))
            return
        if sql.startswith("INSERT INTO identity_mutable_staging"):
            conversation_id, pairs_json, count, target, suspended, status, reason = values
            previous = self.backend.rows.get(str(conversation_id))
            created_ts = previous[8] if previous else "2026-08-20T00:00:00Z"
            last_run = previous[7] if previous else None
            self.row = (
                str(conversation_id),
                str(pairs_json),
                int(count),
                int(target),
                bool(suspended),
                status,
                reason,
                last_run,
                created_ts,
                "2026-08-20T00:00:01Z",
            )
            self.backend.rows[str(conversation_id)] = self.row
            return
        if sql.startswith("UPDATE identity_mutable_staging SET last_agent_status"):
            status, reason, touch_run, suspended, conversation_id = values
            current = list(self.backend.rows[str(conversation_id)])
            current[5] = status
            current[6] = reason
            if touch_run:
                current[7] = "2026-08-20T00:00:02Z"
            if suspended is not None:
                current[4] = bool(suspended)
            current[9] = "2026-08-20T00:00:03Z"
            self.row = tuple(current)
            self.backend.rows[str(conversation_id)] = self.row
            return
        if sql.startswith("UPDATE identity_mutable_staging SET buffer_pairs_json"):
            pairs_json, status, reason, suspended, conversation_id = values
            current = list(self.backend.rows[str(conversation_id)])
            current[1] = str(pairs_json)
            current[2] = 0
            current[4] = bool(suspended)
            current[5] = status
            current[6] = reason
            current[7] = "2026-08-20T00:00:04Z"
            current[9] = "2026-08-20T00:00:04Z"
            self.row = tuple(current)
            self.backend.rows[str(conversation_id)] = self.row
            return
        raise AssertionError(f"unsupported staging SQL: {sql[:80]}")

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.row


class _Connection:
    def __init__(self, backend: "SyntheticSqlStagingBackend") -> None:
        self.backend = backend

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: Any) -> bool:
        return False

    def cursor(self) -> _Cursor:
        return _Cursor(self.backend)

    def commit(self) -> None:
        self.backend.commit_count += 1


class SyntheticSqlStagingBackend:
    """SQL seam only; all staging transition decisions remain in production code."""

    def __init__(self) -> None:
        self.rows: dict[str, tuple[Any, ...]] = {}
        self.commit_count = 0

    def connection(self) -> _Connection:
        return _Connection(self)


class RealStagingIdentityStore:
    def __init__(self) -> None:
        self.backend = SyntheticSqlStagingBackend()
        self.logger = SimpleNamespace(error=lambda *_args, **_kwargs: None)
        self.mutable: dict[str, dict[str, Any]] = {}
        self.canonical_update_batches: list[list[dict[str, Any]]] = []
        self.legacy_persist_calls: list[dict[str, Any]] = []
        self.fail_canonical_updates = False

    def append_identity_staging_pair(self, conversation_id: str, pair: Any, *, target_pairs: int) -> Any:
        return memory_identity_staging.append_identity_staging_pair(
            conversation_id,
            pair,
            target_pairs=target_pairs,
            conn_factory=self.backend.connection,
            logger=self.logger,
        )

    def get_identity_staging_state(self, conversation_id: str) -> Any:
        return memory_identity_staging.get_identity_staging_state(
            conversation_id,
            conn_factory=self.backend.connection,
            logger=self.logger,
        )

    def mark_identity_staging_status(self, conversation_id: str, **kwargs: Any) -> Any:
        return memory_identity_staging.mark_identity_staging_status(
            conversation_id,
            conn_factory=self.backend.connection,
            logger=self.logger,
            **kwargs,
        )

    def clear_identity_staging_buffer(self, conversation_id: str, **kwargs: Any) -> Any:
        return memory_identity_staging.clear_identity_staging_buffer(
            conversation_id,
            conn_factory=self.backend.connection,
            logger=self.logger,
            **kwargs,
        )

    def persist_identity_entries(self, conversation_id: str, entries: Any) -> None:
        self.legacy_persist_calls.append(
            {"conversation_id": conversation_id, "entries_count": len(list(entries or []))}
        )

    def get_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        value = self.mutable.get(subject)
        return copy.deepcopy(value) if value is not None else None

    def apply_mutable_identity_subject_updates(self, updates: list[dict[str, Any]]) -> Any:
        batch = copy.deepcopy(list(updates))
        self.canonical_update_batches.append(batch)
        if self.fail_canonical_updates:
            return None
        results = []
        for update in batch:
            subject = str(update["subject"])
            payload = {
                "subject": subject,
                "content": str(update.get("content") or ""),
                "source_trace_id": update.get("source_trace_id"),
                "updated_by": str(update.get("updated_by") or ""),
                "update_reason": str(update.get("update_reason") or ""),
            }
            self.mutable[subject] = payload
            results.append(copy.deepcopy(payload))
        return results


def assert_frozen_window_golden(summary: Mapping[str, Any]) -> None:
    expected = {
        "pairs_count": 5,
        "target_pairs": 5,
        "frozen": True,
        "pair_fingerprints_equal": True,
        "sixth_absent": True,
        "statuses": ["window_too_large", "window_too_large"],
        "reasons": ["window_too_large", "window_too_large"],
        "buffer_cleared": [False, False],
        "canonical_update_count": 0,
    }
    if dict(summary) != expected:
        raise AssertionError("Lot 0 frozen Identity window contract changed")


def assert_error_case(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    if dict(actual) != dict(expected):
        raise AssertionError(
            f"Lot 0 Identity error matrix changed: actual={dict(actual)!r} expected={dict(expected)!r}"
        )


def assert_identity_cardinality(actual: Mapping[str, Any]) -> None:
    expected = {
        "turns": 5,
        "assistant_saves": 5,
        "final_user_messages": 5,
        "final_assistant_messages": 5,
        "extractor_calls": 5,
        "judge_calls": 1,
        "judge_extract_counts": [5],
        "legacy_persist_calls": 5,
        "canonical_update_count": 0,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 0 Identity post-save cardinality changed")
