from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Sequence


_CODE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SHORT_CODE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
_TIMESTAMP_RE = re.compile(r"^[A-Za-z0-9:+_.-]{1,64}$")
_USER_GESTURES = {
    "exposition",
    "interrogation",
    "orientation",
    "positionnement",
    "regulation",
    "adresse_relationnelle",
}
_PROOF_TYPES = {"factuelle", "scientifique", "argumentative", "hermeneutique", "dialogique"}
_PROVENANCES = {"dialogue_trace", "dialogue_resume", "web"}
_TEMPORAL_SCOPES = {"prospective", "passee", "immediate", "actuelle", "atemporale"}
_TEMPORAL_ANCHORS = {
    "non_ancre",
    "dialogue_trace",
    "dialogue_resume",
    "historique_externe",
    "projection",
    "now",
    "mixte",
}
_SIGNAL_FAMILIES = (
    "referent",
    "visee",
    "critere",
    "portee",
    "ancrage_de_source",
    "coherence",
)
_WEB_ACTIVATION_MODES = {"manual", "auto", "not_requested"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _code(value: Any, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = str(value or "").strip()
    if not text and optional:
        return None
    if not _CODE_RE.fullmatch(text):
        raise ValueError("invalid_canonical_projection_family")
    return text


def _short_code(value: Any) -> str:
    text = str(value or "").strip()
    if not _SHORT_CODE_RE.fullmatch(text):
        raise ValueError("invalid_canonical_projection_family")
    return text


def _timestamp(value: Any, *, optional: bool = True) -> str | None:
    if value is None and optional:
        return None
    text = str(value or "").strip()
    if not text and optional:
        return None
    if not _TIMESTAMP_RE.fullmatch(text):
        raise ValueError("invalid_canonical_projection_family")
    return text


def _non_negative_int(value: Any, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 999999:
        raise ValueError("invalid_canonical_projection_family")
    return int(value)


def _bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("invalid_canonical_projection_family")
    return value


def _closed_list(value: Any, *, allowed: set[str], order: Sequence[str], max_items: int) -> list[str]:
    if not isinstance(value, list) or len(value) > max_items:
        raise ValueError("invalid_canonical_projection_family")
    if any(not isinstance(item, str) or item not in allowed for item in value):
        raise ValueError("invalid_canonical_projection_family")
    if len(set(value)) != len(value):
        raise ValueError("invalid_canonical_projection_family")
    normalized = [item for item in order if item in value]
    if normalized != value:
        raise ValueError("invalid_canonical_projection_family")
    return normalized


def _project_memory_retrieved(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    if not payload:
        return None, "no_data"
    if payload.get("schema_version") != "v1":
        return None, "invalid_input"
    try:
        status = _code(payload.get("status"))
        reason_code = _code(payload.get("reason_code"), optional=True)
        error_code = _code(payload.get("error_code"), optional=True)
        retrieved_count = _non_negative_int(payload.get("retrieved_count"))
        traces = payload.get("traces")
        if not isinstance(traces, list) or retrieved_count != len(traces):
            raise ValueError("invalid_canonical_projection_family")
        parent_summary_count = sum(
            1 for item in traces if isinstance(item, Mapping) and bool(item.get("parent_summary"))
        )
    except ValueError:
        return None, "invalid_input"
    if retrieved_count == 0 and status != "error":
        return None, "no_data"
    return {
        "schema_version": "v1",
        "status": status,
        "reason_code": reason_code,
        "error_code": error_code,
        "retrieved_count": retrieved_count,
        "parent_summary_count": parent_summary_count,
    }, "included"


def _project_memory_arbitration(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    if not payload:
        return None, "no_data"
    if payload.get("schema_version") != "v1":
        return None, "invalid_input"
    try:
        status = _code(payload.get("status"))
        reason_code = _code(payload.get("reason_code"), optional=True)
        projected = {
            "schema_version": "v1",
            "status": status,
            "reason_code": reason_code,
            "raw_candidates_count": _non_negative_int(payload.get("raw_candidates_count")),
            "kept_count": _non_negative_int(payload.get("kept_count")),
            "rejected_count": _non_negative_int(payload.get("rejected_count")),
            "injected_count": len(_sequence(payload.get("injected_candidate_ids"))),
        }
        _non_negative_int(projected["injected_count"])
    except ValueError:
        return None, "invalid_input"
    if (
        projected["raw_candidates_count"] == 0
        and status == "skipped"
        and reason_code in {None, "no_data"}
    ):
        return None, "no_data"
    return projected, "included"


def _project_summary(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    if not payload:
        return None, "no_data"
    if payload.get("schema_version") != "v1":
        return None, "invalid_input"
    try:
        status = _code(payload.get("status"))
        reason_code = _code(payload.get("reason_code"), optional=True)
        error_code = _code(payload.get("error_code"), optional=True)
    except ValueError:
        return None, "invalid_input"
    if status == "missing" and payload.get("summary") is None:
        return None, "no_data"
    summary = _mapping(payload.get("summary"))
    if status == "available" and not summary:
        return None, "invalid_input"
    try:
        projected = {
            "schema_version": "v1",
            "status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "summary_present": bool(summary),
            "start_ts": _timestamp(summary.get("start_ts"), optional=True),
            "end_ts": _timestamp(summary.get("end_ts"), optional=True),
        }
    except ValueError:
        return None, "invalid_input"
    return projected, "included"


def _project_identity(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    if not payload:
        return None, "no_data"
    if payload.get("schema_version") != "v2":
        return None, "invalid_input"
    try:
        status = _code(payload.get("status"))
        projected: dict[str, Any] = {
            "schema_version": "v2",
            "status": status,
            "reason_code": _code(payload.get("reason_code"), optional=True),
            "error_code": _code(payload.get("error_code"), optional=True),
        }
        any_present = False
        for side_name in ("frida", "user"):
            side = _mapping(payload.get(side_name))
            static = _mapping(side.get("static"))
            mutable = _mapping(side.get("mutable"))
            static_present = bool(str(static.get("content") or ""))
            mutable_present = bool(str(mutable.get("content") or ""))
            any_present = any_present or static_present or mutable_present
            projected[side_name] = {
                "static_present": static_present,
                "mutable_present": mutable_present,
            }
    except ValueError:
        return None, "invalid_input"
    if status == "missing" and not any_present:
        return None, "no_data"
    return projected, "included"


def _project_user_turn(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    try:
        if set(payload) != {
            "schema_version",
            "geste_dialogique_dominant",
            "regime_probatoire",
            "qualification_temporelle",
        } or payload.get("schema_version") != "v1":
            raise ValueError("invalid_canonical_projection_family")
        gesture = str(payload.get("geste_dialogique_dominant") or "")
        if gesture not in _USER_GESTURES:
            raise ValueError("invalid_canonical_projection_family")
        proof = _mapping(payload.get("regime_probatoire"))
        if set(proof) != {
            "principe",
            "types_de_preuve_attendus",
            "provenances",
            "regime_de_vigilance",
            "composition_probatoire",
        }:
            raise ValueError("invalid_canonical_projection_family")
        if proof.get("principe") != "maximal_possible":
            raise ValueError("invalid_canonical_projection_family")
        proof_types = _closed_list(
            proof.get("types_de_preuve_attendus"),
            allowed=_PROOF_TYPES,
            order=("factuelle", "scientifique", "argumentative", "hermeneutique", "dialogique"),
            max_items=5,
        )
        provenances = _closed_list(
            proof.get("provenances"),
            allowed=_PROVENANCES,
            order=("dialogue_trace", "dialogue_resume", "web"),
            max_items=3,
        )
        vigilance = str(proof.get("regime_de_vigilance") or "")
        composition = str(proof.get("composition_probatoire") or "")
        if vigilance not in {"standard", "renforce"} or composition not in {"isolee", "appuyee"}:
            raise ValueError("invalid_canonical_projection_family")
        temporal = _mapping(payload.get("qualification_temporelle"))
        if set(temporal) != {"portee_temporelle", "ancrage_temporel"}:
            raise ValueError("invalid_canonical_projection_family")
        scope = str(temporal.get("portee_temporelle") or "")
        anchor = str(temporal.get("ancrage_temporel") or "")
        if scope not in _TEMPORAL_SCOPES or anchor not in _TEMPORAL_ANCHORS:
            raise ValueError("invalid_canonical_projection_family")
    except ValueError:
        return None, "invalid_input"
    return {
        "schema_version": "v1",
        "geste_dialogique_dominant": gesture,
        "regime_probatoire": {
            "principe": "maximal_possible",
            "types_de_preuve_attendus": proof_types,
            "provenances": provenances,
            "regime_de_vigilance": vigilance,
            "composition_probatoire": composition,
        },
        "qualification_temporelle": {
            "portee_temporelle": scope,
            "ancrage_temporel": anchor,
        },
    }, "included"


def _project_user_turn_signals(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    try:
        if set(payload) != {
            "present",
            "ambiguity_present",
            "underdetermination_present",
            "active_signal_families",
            "active_signal_families_count",
        }:
            raise ValueError("invalid_canonical_projection_family")
        present = _bool(payload.get("present"))
        ambiguity = _bool(payload.get("ambiguity_present"))
        underdetermination = _bool(payload.get("underdetermination_present"))
        active = _closed_list(
            payload.get("active_signal_families"),
            allowed=set(_SIGNAL_FAMILIES),
            order=_SIGNAL_FAMILIES,
            max_items=len(_SIGNAL_FAMILIES),
        )
        count = _non_negative_int(payload.get("active_signal_families_count"))
        if count != len(active):
            raise ValueError("invalid_canonical_projection_family")
    except ValueError:
        return None, "invalid_input"
    return {
        "present": present,
        "ambiguity_present": ambiguity,
        "underdetermination_present": underdetermination,
        "active_signal_families": active,
        "active_signal_families_count": count,
    }, "included"


def _project_web(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    if not payload:
        return None, "no_data"
    if payload.get("schema_version") != "v1":
        return None, "invalid_input"
    try:
        enabled = _bool(payload.get("enabled"))
        activation_mode = str(payload.get("activation_mode") or "")
        if activation_mode not in _WEB_ACTIVATION_MODES:
            raise ValueError("invalid_canonical_projection_family")
        used_content_kinds = payload.get("used_content_kinds") or []
        if not isinstance(used_content_kinds, list) or len(used_content_kinds) > 4:
            raise ValueError("invalid_canonical_projection_family")
        normalized_kinds = [_short_code(item) for item in used_content_kinds]
        if len(set(normalized_kinds)) != len(normalized_kinds):
            raise ValueError("invalid_canonical_projection_family")
        confidence = _mapping(payload.get("web_confidence"))
        evidence = _mapping(payload.get("web_evidence"))
        openrouter = _mapping(payload.get("openrouter_fallback"))
        projected = {
            "schema_version": "v1",
            "enabled": enabled,
            "status": _code(payload.get("status")),
            "activation_mode": activation_mode,
            "reason_code": _code(payload.get("reason_code"), optional=True),
            "results_count": _non_negative_int(payload.get("results_count")),
            "read_state": _code(payload.get("read_state"), optional=True),
            "fallback_used": _bool(payload.get("fallback_used")),
            "web_confidence_level": _code(confidence.get("web_confidence_level"), optional=True),
            "web_evidence_status": _code(evidence.get("web_evidence_status"), optional=True),
            "web_evidence_can_answer": _bool(evidence.get("web_evidence_can_answer", False)),
            "web_evidence_requires_caveat": _bool(evidence.get("web_evidence_requires_caveat", False)),
            "web_evidence_can_suggest_reformulation": _bool(
                evidence.get("web_evidence_can_suggest_reformulation", False)
            ),
            "web_evidence_external_fallback_used": _bool(
                evidence.get("web_evidence_external_fallback_used", False)
            ),
            "openrouter_fallback_used": _bool(
                openrouter.get("openrouter_fallback_used", False)
            ),
        }
    except ValueError:
        return None, "invalid_input"
    if not enabled and activation_mode == "not_requested":
        return None, "optional_not_requested"
    return projected, "included"


_PROJECTORS: dict[str, Callable[[Any], tuple[dict[str, Any] | None, str]]] = {
    "memory_retrieved": _project_memory_retrieved,
    "memory_arbitration": _project_memory_arbitration,
    "summary_input": _project_summary,
    "identity_input": _project_identity,
    "user_turn_input": _project_user_turn,
    "user_turn_signals": _project_user_turn_signals,
    "web_input": _project_web,
}


def project_family(family: str, value: Any) -> tuple[dict[str, Any] | None, str]:
    if family == "time_input":
        payload = _mapping(value)
        if not payload:
            return None, "no_data"
        valid = (
            payload.get("schema_version") == "v1"
            and bool(str(payload.get("now_utc_iso") or "").strip())
            and bool(str(payload.get("timezone") or "").strip())
        )
        return (None, "redundant_elsewhere") if valid else (None, "invalid_input")
    if family == "recent_context_input":
        payload = _mapping(value)
        if not payload:
            return None, "no_data"
        valid = payload.get("schema_version") == "v1" and isinstance(payload.get("messages"), list)
        return (None, "redundant_elsewhere") if valid else (None, "invalid_input")
    if family == "recent_window_input":
        payload = _mapping(value)
        if not payload:
            return None, "no_data"
        valid = payload.get("schema_version") == "v1" and isinstance(payload.get("turns"), list)
        return (None, "redundant_elsewhere") if valid else (None, "invalid_input")
    projector = _PROJECTORS.get(family)
    if projector is None:
        raise ValueError("invalid_canonical_projection_family")
    return projector(value)


def validate_projected_family(family: str, value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    projector = _PROJECTORS.get(family)
    if projector is None or not payload:
        raise ValueError("invalid_canonical_projection_family")
    if family == "memory_retrieved":
        expected_keys = {
            "schema_version", "status", "reason_code", "error_code",
            "retrieved_count", "parent_summary_count",
        }
        if set(payload) != expected_keys or payload.get("schema_version") != "v1":
            raise ValueError("invalid_canonical_projection_family")
        _code(payload.get("status"))
        for key in ("reason_code", "error_code"):
            _code(payload.get(key), optional=True)
        for key in ("retrieved_count", "parent_summary_count"):
            _non_negative_int(payload.get(key))
        if payload.get("parent_summary_count", 0) > payload.get("retrieved_count", 0):
            raise ValueError("invalid_canonical_projection_family")
        return dict(payload)
    if family == "memory_arbitration":
        expected_keys = {
            "schema_version", "status", "reason_code", "raw_candidates_count",
            "kept_count", "rejected_count", "injected_count",
        }
        if set(payload) != expected_keys or payload.get("schema_version") != "v1":
            raise ValueError("invalid_canonical_projection_family")
        _code(payload.get("status"))
        _code(payload.get("reason_code"), optional=True)
        for key in expected_keys - {"schema_version", "status", "reason_code"}:
            _non_negative_int(payload.get(key))
        return dict(payload)
    if family == "summary_input":
        expected_keys = {
            "schema_version", "status", "reason_code", "error_code",
            "summary_present", "start_ts", "end_ts",
        }
        if set(payload) != expected_keys or payload.get("schema_version") != "v1":
            raise ValueError("invalid_canonical_projection_family")
        _code(payload.get("status"))
        for key in ("reason_code", "error_code"):
            _code(payload.get(key), optional=True)
        _bool(payload.get("summary_present"))
        _timestamp(payload.get("start_ts"), optional=True)
        _timestamp(payload.get("end_ts"), optional=True)
        return dict(payload)
    if family == "identity_input":
        expected_keys = {
            "schema_version", "status", "reason_code", "error_code",
            "frida", "user",
        }
        if set(payload) != expected_keys or payload.get("schema_version") != "v2":
            raise ValueError("invalid_canonical_projection_family")
        _code(payload.get("status"))
        for key in ("reason_code", "error_code"):
            _code(payload.get(key), optional=True)
        for side_name in ("frida", "user"):
            side = _mapping(payload.get(side_name))
            if set(side) != {"static_present", "mutable_present"}:
                raise ValueError("invalid_canonical_projection_family")
            _bool(side.get("static_present"))
            _bool(side.get("mutable_present"))
        return dict(payload)
    if family == "web_input":
        expected_keys = {
            "schema_version", "enabled", "status", "activation_mode", "reason_code",
            "results_count", "read_state", "fallback_used",
            "web_confidence_level", "web_evidence_status", "web_evidence_can_answer",
            "web_evidence_requires_caveat", "web_evidence_can_suggest_reformulation",
            "web_evidence_external_fallback_used",
            "openrouter_fallback_used",
        }
        if set(payload) != expected_keys:
            raise ValueError("invalid_canonical_projection_family")
        source_shape = {
            **dict(payload),
            "web_confidence": {"web_confidence_level": payload.get("web_confidence_level")},
            "web_evidence": {
                "web_evidence_status": payload.get("web_evidence_status"),
                "web_evidence_can_answer": payload.get("web_evidence_can_answer"),
                "web_evidence_requires_caveat": payload.get("web_evidence_requires_caveat"),
                "web_evidence_can_suggest_reformulation": payload.get(
                    "web_evidence_can_suggest_reformulation"
                ),
                "web_evidence_external_fallback_used": payload.get(
                    "web_evidence_external_fallback_used"
                ),
            },
            "openrouter_fallback": {
                "openrouter_fallback_state": payload.get("openrouter_fallback_state"),
                "openrouter_fallback_used": payload.get("openrouter_fallback_used"),
            },
        }
        normalized, disposition = projector(source_shape)
    else:
        normalized, disposition = projector(payload)
    if disposition != "included" or normalized != dict(payload):
        raise ValueError("invalid_canonical_projection_family")
    return normalized
