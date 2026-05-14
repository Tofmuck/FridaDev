from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable, Mapping

from core.hermeneutic_node.runtime import node_state as runtime_node_state


def _text(value: Any) -> str:
    return str(value or "").strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _iso_value(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return _text(value)


def _json_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        loaded = json.loads(text)
        if isinstance(loaded, Mapping):
            return dict(loaded)
    return None


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    try:
        return row[index]
    except (TypeError, IndexError, KeyError):
        return None


def _canonical_state_json(state: Mapping[str, Any]) -> str:
    validated = runtime_node_state.validate_node_state(state)
    return json.dumps(validated, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _state_hash(state: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_state_json(state).encode("utf-8")).hexdigest()[:12]


def _validated_conversation_id(value: Any) -> str:
    conversation_id = _text(value)
    if not conversation_id:
        raise ValueError("invalid_conversation_id")
    return conversation_id


def _state_from_row(row: Any) -> dict[str, Any]:
    return runtime_node_state.validate_node_state(
        {
            "schema_version": _text(_row_value(row, "schema_version", 1)),
            "conversation_id": _text(_row_value(row, "conversation_id", 0)),
            "updated_at": _iso_value(_row_value(row, "state_updated_at", 2)),
            "last_judgment_posture": _text(_row_value(row, "last_judgment_posture", 3)),
            "last_answer_output_regime": _json_payload(
                _row_value(row, "last_answer_output_regime_json", 4)
            ),
        }
    )


def ensure_table(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hermeneutic_node_states (
            conversation_id                  TEXT PRIMARY KEY,
            schema_version                   TEXT        NOT NULL DEFAULT 'v1',
            state_updated_at                 TIMESTAMPTZ NOT NULL,
            last_judgment_posture            TEXT        NOT NULL,
            last_answer_output_regime_json   JSONB,
            state_sha256_12                  TEXT        NOT NULL,
            created_ts                       TIMESTAMPTZ DEFAULT now(),
            updated_ts                       TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT hermeneutic_node_states_schema_chk CHECK (schema_version = 'v1'),
            CONSTRAINT hermeneutic_node_states_posture_chk
                CHECK (last_judgment_posture IN ('answer', 'clarify', 'suspend'))
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS hermeneutic_node_states_updated_ts_idx
        ON hermeneutic_node_states (updated_ts DESC);
        """
    )


def read_node_state(
    conversation_id: str,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    try:
        conv_id = _validated_conversation_id(conversation_id)
    except ValueError:
        return {
            "state": None,
            "present": False,
            "valid": False,
            "reason_code": "invalid_conversation_id",
            "schema_version": "",
            "state_sha256_12": "",
        }

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        conversation_id,
                        schema_version,
                        state_updated_at,
                        last_judgment_posture,
                        last_answer_output_regime_json,
                        state_sha256_12,
                        updated_ts
                    FROM hermeneutic_node_states
                    WHERE conversation_id = %s
                    """,
                    (conv_id,),
                )
                row = cur.fetchone()
    except Exception as exc:
        logger.warning("hermeneutic_node_state_read_failed err=%s", exc)
        return {
            "state": None,
            "present": False,
            "valid": False,
            "reason_code": "read_error",
            "schema_version": "",
            "state_sha256_12": "",
            "error_class": exc.__class__.__name__,
        }

    if row is None:
        return {
            "state": None,
            "present": False,
            "valid": True,
            "reason_code": "not_found",
            "schema_version": "",
            "state_sha256_12": "",
        }

    try:
        state = _state_from_row(row)
        stored_hash = _text(_row_value(row, "state_sha256_12", 5)) or _state_hash(state)
        return {
            "state": state,
            "present": True,
            "valid": True,
            "reason_code": "ok",
            "schema_version": state["schema_version"],
            "state_sha256_12": stored_hash,
        }
    except Exception as exc:
        logger.warning("hermeneutic_node_state_invalid err=%s", exc)
        return {
            "state": None,
            "present": True,
            "valid": False,
            "reason_code": "invalid_node_state",
            "schema_version": _text(_row_value(row, "schema_version", 1)),
            "state_sha256_12": _text(_row_value(row, "state_sha256_12", 5)),
            "error_class": exc.__class__.__name__,
        }


def write_node_state(
    conversation_id: str,
    state: Mapping[str, Any] | None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    try:
        conv_id = _validated_conversation_id(conversation_id)
        validated = runtime_node_state.validate_node_state(state)
        if validated["conversation_id"] != conv_id:
            raise ValueError("invalid_conversation_id")
        state_hash = _state_hash(validated)
        output_regime = validated.get("last_answer_output_regime")
        output_regime_json = json.dumps(output_regime, ensure_ascii=False) if output_regime else None
    except Exception as exc:
        return {
            "attempted": True,
            "written": False,
            "changed": False,
            "reason_code": "invalid_node_state",
            "schema_version": "",
            "state_sha256_12": "",
            "error_class": exc.__class__.__name__,
        }

    try:
        old_hash = ""
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT state_sha256_12 FROM hermeneutic_node_states WHERE conversation_id = %s",
                    (conv_id,),
                )
                row = cur.fetchone()
                if row is not None:
                    old_hash = _text(_row_value(row, "state_sha256_12", 0))
                cur.execute(
                    """
                    INSERT INTO hermeneutic_node_states (
                        conversation_id,
                        schema_version,
                        state_updated_at,
                        last_judgment_posture,
                        last_answer_output_regime_json,
                        state_sha256_12
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (conversation_id) DO UPDATE
                    SET
                        schema_version = EXCLUDED.schema_version,
                        state_updated_at = EXCLUDED.state_updated_at,
                        last_judgment_posture = EXCLUDED.last_judgment_posture,
                        last_answer_output_regime_json = EXCLUDED.last_answer_output_regime_json,
                        state_sha256_12 = EXCLUDED.state_sha256_12,
                        updated_ts = now()
                    """,
                    (
                        conv_id,
                        validated["schema_version"],
                        validated["updated_at"],
                        validated["last_judgment_posture"],
                        output_regime_json,
                        state_hash,
                    ),
                )
            conn.commit()
        changed = old_hash != state_hash
        return {
            "attempted": True,
            "written": True,
            "changed": changed,
            "reason_code": "written" if changed else "unchanged",
            "schema_version": validated["schema_version"],
            "state_sha256_12": state_hash,
        }
    except Exception as exc:
        logger.warning("hermeneutic_node_state_write_failed err=%s", exc)
        return {
            "attempted": True,
            "written": False,
            "changed": False,
            "reason_code": "write_error",
            "schema_version": validated["schema_version"],
            "state_sha256_12": state_hash,
            "error_class": exc.__class__.__name__,
        }
