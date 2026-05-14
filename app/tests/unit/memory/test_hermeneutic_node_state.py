from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import hermeneutic_node_state


def _state(
    *,
    conversation_id: str = "conv-state",
    updated_at: str = "2026-05-14T12:00:00Z",
) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "conversation_id": conversation_id,
        "updated_at": updated_at,
        "last_judgment_posture": "answer",
        "last_answer_output_regime": {
            "discursive_regime": "simple",
            "resituation_level": "none",
            "time_reference_mode": "atemporal",
        },
    }


class _Cursor:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self.store = store
        self.result: Any = None
        self.executed: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        normalized = " ".join(query.lower().split())
        self.executed.append(normalized)
        params = params or ()
        if normalized.startswith("select state_sha256_12 from hermeneutic_node_states"):
            row = self.store.get(str(params[0]))
            self.result = (row["state_sha256_12"],) if row else None
            return
        if normalized.startswith("insert into hermeneutic_node_states"):
            conversation_id, schema_version, state_updated_at, posture, output_json, state_hash = params
            self.store[str(conversation_id)] = {
                "conversation_id": str(conversation_id),
                "schema_version": str(schema_version),
                "state_updated_at": str(state_updated_at),
                "last_judgment_posture": str(posture),
                "last_answer_output_regime_json": output_json,
                "state_sha256_12": str(state_hash),
            }
            self.result = None
            return
        if normalized.startswith("select conversation_id, schema_version, state_updated_at"):
            row = self.store.get(str(params[0]))
            self.result = None if row is None else (
                row["conversation_id"],
                row["schema_version"],
                row["state_updated_at"],
                row["last_judgment_posture"],
                row["last_answer_output_regime_json"],
                row["state_sha256_12"],
                "2026-05-14T12:00:00Z",
            )
            return
        self.result = None

    def fetchone(self):
        return self.result


class _Conn:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self.store = store
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return _Cursor(self.store)

    def commit(self):
        self.commits += 1


class _Logger:
    def warning(self, *_args, **_kwargs):
        return None


class HermeneuticNodeStatePersistenceTests(unittest.TestCase):
    def test_write_then_read_node_state_without_raw_content(self) -> None:
        store: dict[str, dict[str, Any]] = {}
        conn_factory = lambda: _Conn(store)

        write_result = hermeneutic_node_state.write_node_state(
            "conv-state",
            _state(),
            conn_factory=conn_factory,
            logger=_Logger(),
        )
        read_result = hermeneutic_node_state.read_node_state(
            "conv-state",
            conn_factory=conn_factory,
            logger=_Logger(),
        )
        second_write = hermeneutic_node_state.write_node_state(
            "conv-state",
            _state(),
            conn_factory=conn_factory,
            logger=_Logger(),
        )

        self.assertTrue(write_result["written"])
        self.assertTrue(write_result["changed"])
        self.assertTrue(read_result["present"])
        self.assertTrue(read_result["valid"])
        self.assertEqual(read_result["state"], _state())
        self.assertEqual(read_result["schema_version"], "v1")
        self.assertFalse(second_write["changed"])
        serialized = repr({**write_result, **read_result, **second_write})
        self.assertNotIn("prompt", serialized)
        self.assertNotIn("content", serialized)
        self.assertNotIn("message", serialized)

    def test_invalid_state_is_not_written(self) -> None:
        store: dict[str, dict[str, Any]] = {}
        result = hermeneutic_node_state.write_node_state(
            "conv-state",
            {"schema_version": "v1", "conversation_id": "conv-state", "content": "raw"},
            conn_factory=lambda: _Conn(store),
            logger=_Logger(),
        )

        self.assertTrue(result["attempted"])
        self.assertFalse(result["written"])
        self.assertEqual(result["reason_code"], "invalid_node_state")
        self.assertEqual(store, {})

    def test_invalid_stored_state_returns_compact_reason(self) -> None:
        store = {
            "conv-state": {
                "conversation_id": "conv-state",
                "schema_version": "v1",
                "state_updated_at": "2026-05-14T12:00:00Z",
                "last_judgment_posture": "invalid",
                "last_answer_output_regime_json": None,
                "state_sha256_12": "abc123",
            }
        }

        result = hermeneutic_node_state.read_node_state(
            "conv-state",
            conn_factory=lambda: _Conn(store),
            logger=_Logger(),
        )

        self.assertTrue(result["present"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason_code"], "invalid_node_state")
        self.assertIsNone(result["state"])

    def test_schema_creation_sql_is_idempotent(self) -> None:
        store: dict[str, dict[str, Any]] = {}
        cur = _Cursor(store)

        hermeneutic_node_state.ensure_table(cur)
        hermeneutic_node_state.ensure_table(cur)

        sql = "\n".join(cur.executed)
        self.assertIn("create table if not exists hermeneutic_node_states", sql)
        self.assertIn("create index if not exists hermeneutic_node_states_updated_ts_idx", sql)


if __name__ == "__main__":
    unittest.main()
