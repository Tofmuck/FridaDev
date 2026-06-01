"""Versioned contract and validation for the Biblio librarian agent."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import librarian_planner as planner
from . import librarian_tools as tools
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import safe_token as _safe_token
from .librarian_planner_observability import safe_tool_name as _safe_tool_name


SCHEMA_VERSION = "biblio_librarian_agent_v1"

MODE_OFF = "off"
MODE_SHADOW = "shadow"
MODE_CANDIDATE = "candidate"
MODE_ACTIVE = "active"
ALLOWED_MODES = {MODE_OFF, MODE_SHADOW, MODE_CANDIDATE, MODE_ACTIVE}

STATUS_VALIDATED = "validated"
STATUS_REJECTED = "rejected"

REASON_VALIDATED = "biblio_librarian_agent_json_validated"
REASON_JSON_ABSENT = "biblio_librarian_agent_json_absent"
REASON_JSON_INVALID = "biblio_librarian_agent_json_invalid"
REASON_JSON_FREE_TEXT = "biblio_librarian_agent_free_text"
REASON_JSON_TRUNCATED = "biblio_librarian_agent_json_truncated"
REASON_SCHEMA_VERSION = "biblio_librarian_agent_schema_version_invalid"
REASON_SCHEMA_INVALID = "biblio_librarian_agent_schema_invalid"
REASON_TOOL_FORBIDDEN = "biblio_librarian_agent_forbidden_tool"
REASON_TOOL_UNKNOWN = "biblio_librarian_agent_unknown_tool"
REASON_METHOD_FORBIDDEN = "biblio_librarian_agent_forbidden_method"
REASON_BUDGET_EXCEEDED = "biblio_librarian_agent_budget_exceeded"

_HASH_LEN = 12
_RECENT_DIALOGUE_CONTENT_MAX_CHARS = 1200


@dataclass(frozen=True)
class BiblioLibrarianAgentSettings:
    mode: str = MODE_OFF
    primary_model: str = ""
    fallback_model: str = ""
    timeout_s: int = 10
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 900
    max_tool_calls: int = 5
    max_model_calls: int = 1
    max_recent_turns: int = 5
    json_contract_enabled: bool = True
    require_parameters: bool = True

    @classmethod
    def from_config(cls, config_module: Any) -> "BiblioLibrarianAgentSettings":
        return cls(
            mode=normalize_mode(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MODE", MODE_OFF)),
            primary_model=str(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MODEL", "") or "").strip(),
            fallback_model=str(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_FALLBACK_MODEL", "") or "").strip(),
            timeout_s=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_TIMEOUT_S", 10), 10),
            temperature=_float(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_TEMPERATURE", 0.0), 0.0),
            top_p=_float(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_TOP_P", 1.0), 1.0),
            max_tokens=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_TOKENS", 900), 900),
            max_tool_calls=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_TOOL_CALLS", 5), 5),
            max_model_calls=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_MODEL_CALLS", 1), 1),
            max_recent_turns=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_RECENT_TURNS", 5), 5),
            json_contract_enabled=_bool(
                getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_JSON_CONTRACT_ENABLED", True),
                True,
            ),
            require_parameters=_bool(
                getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_REQUIRE_PARAMETERS", True),
                True,
            ),
        )

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "mode": normalize_mode(self.mode),
                "primary_model": _safe_model_slug(self.primary_model),
                "primary_model_configured": bool(self.primary_model),
                "fallback_model": _safe_model_slug(self.fallback_model),
                "fallback_model_configured": bool(self.fallback_model),
                "timeout_s": self.timeout_s,
                "max_tokens": self.max_tokens,
                "max_tool_calls": self.max_tool_calls,
                "max_model_calls": self.max_model_calls,
                "max_recent_turns": self.max_recent_turns,
                "json_contract_enabled": self.json_contract_enabled,
                "require_parameters": self.require_parameters,
            }
        )


@dataclass(frozen=True)
class BiblioLibrarianAgentRequest:
    user_message: str = field(default="", repr=False, compare=False)
    recent_dialogue: tuple[Mapping[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    biblio_state: Any = field(default=None, repr=False, compare=False)
    deterministic_plan: Any = field(default=None, repr=False, compare=False)
    settings: BiblioLibrarianAgentSettings = field(default_factory=BiblioLibrarianAgentSettings)

    def bounded_recent_dialogue(self) -> tuple[Mapping[str, Any], ...]:
        max_turns = max(0, self.settings.max_recent_turns)
        if max_turns == 0:
            return ()
        return tuple(_bounded_turn(turn) for turn in self.recent_dialogue[-max_turns:])

    def to_observability(self) -> dict[str, Any]:
        bounded = self.bounded_recent_dialogue()
        return _clean(
            {
                "schema_version": SCHEMA_VERSION,
                "user_message_present": bool(self.user_message),
                "user_message_chars": len(self.user_message),
                "user_message_hash": _hash(self.user_message),
                "recent_dialogue_count": len(self.recent_dialogue),
                "bounded_recent_dialogue_count": len(bounded),
                "recent_dialogue_hashes": [_hash(_turn_content(turn)) for turn in bounded],
                "biblio_state_present": self.biblio_state is not None,
                "deterministic_plan_present": self.deterministic_plan is not None,
                "settings": self.settings.to_observability(),
            }
        )


@dataclass(frozen=True)
class BiblioLibrarianAgentValidation:
    status: str
    reason_code: str
    plan: planner.BiblioLibrarianPlan | None = field(default=None, repr=False, compare=False)
    tool_call_count: int = 0
    tool_names: tuple[str, ...] = ()
    invalid_tool_names: tuple[str, ...] = ()
    json_chars: int = 0
    json_hash: str = ""
    finish_reason: str = ""

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "schema_version": SCHEMA_VERSION,
                "status": self.status,
                "reason_code": self.reason_code,
                "tool_call_count": self.tool_call_count,
                "tool_names": list(self.tool_names),
                "invalid_tool_names": list(self.invalid_tool_names),
                "json_chars": self.json_chars,
                "json_hash": self.json_hash,
                "finish_reason": _safe_token(self.finish_reason),
                "plan": self.plan.to_observability() if self.plan else {},
            }
        )


def normalize_mode(value: Any) -> str:
    mode = str(value or MODE_OFF).strip().lower()
    return mode if mode in ALLOWED_MODES else MODE_OFF


def parse_and_validate_agent_json(
    text: str,
    *,
    settings: BiblioLibrarianAgentSettings | None = None,
    finish_reason: str = "",
) -> BiblioLibrarianAgentValidation:
    clean_text = str(text or "").strip()
    json_chars = len(clean_text)
    json_hash = _hash(clean_text)
    if _safe_token(finish_reason) == "length":
        return _rejected(REASON_JSON_TRUNCATED, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if not clean_text:
        return _rejected(REASON_JSON_ABSENT, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    try:
        payload = json.loads(clean_text)
    except json.JSONDecodeError:
        reason = REASON_JSON_INVALID if clean_text[:1] in {"{", "["} else REASON_JSON_FREE_TEXT
        return _rejected(reason, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    return validate_agent_payload(
        payload,
        settings=settings,
        json_chars=json_chars,
        json_hash=json_hash,
        finish_reason=finish_reason,
    )


def validate_agent_payload(
    payload: Any,
    *,
    settings: BiblioLibrarianAgentSettings | None = None,
    json_chars: int = 0,
    json_hash: str = "",
    finish_reason: str = "",
) -> BiblioLibrarianAgentValidation:
    effective_settings = settings or BiblioLibrarianAgentSettings()
    if not isinstance(payload, Mapping):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if str(payload.get("schema_version") or "") != SCHEMA_VERSION:
        return _rejected(REASON_SCHEMA_VERSION, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    raw_calls = payload.get("tool_calls")
    if raw_calls is None:
        raw_calls = ()
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, (str, bytes, bytearray)):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if len(raw_calls) > effective_settings.max_tool_calls:
        return _rejected(REASON_BUDGET_EXCEEDED, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)

    calls: list[planner.BiblioLibrarianToolCall] = []
    invalid_tool_names: list[str] = []
    for raw_call in raw_calls:
        if not isinstance(raw_call, Mapping):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        tool_name = _safe_tool_name(raw_call.get("tool_name") or raw_call.get("name"))
        method = str(raw_call.get("method") or "GET").strip().upper()
        if method != "GET":
            invalid_tool_names.append(tool_name)
            return _rejected(
                REASON_METHOD_FORBIDDEN,
                invalid_tool_names=tuple(invalid_tool_names),
                json_chars=json_chars,
                json_hash=json_hash,
                finish_reason=finish_reason,
            )
        if tool_name in tools.FORBIDDEN_TOOL_NAMES:
            invalid_tool_names.append(tool_name)
            return _rejected(
                REASON_TOOL_FORBIDDEN,
                invalid_tool_names=tuple(invalid_tool_names),
                json_chars=json_chars,
                json_hash=json_hash,
                finish_reason=finish_reason,
            )
        if tool_name not in tools.LOT3_TOOL_NAMES:
            invalid_tool_names.append(tool_name)
            return _rejected(
                REASON_TOOL_UNKNOWN,
                invalid_tool_names=tuple(invalid_tool_names),
                json_chars=json_chars,
                json_hash=json_hash,
                finish_reason=finish_reason,
            )
        params = raw_call.get("params") or {}
        if not isinstance(params, Mapping):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        calls.append(
            planner.BiblioLibrarianToolCall(
                tool_name=tool_name,
                params=dict(params),
                call_id=str(raw_call.get("call_id") or ""),
                method=method,
            )
        )

    plan = planner.BiblioLibrarianPlan(
        schema_version=planner.SCHEMA_VERSION,
        intent=_safe_token(payload.get("intent")),
        tool_calls=tuple(calls),
        answer_mode=_safe_token(payload.get("answer_mode")),
        fallback_reason=_safe_token(payload.get("fallback_reason")),
    )
    return BiblioLibrarianAgentValidation(
        status=STATUS_VALIDATED,
        reason_code=REASON_VALIDATED,
        plan=plan,
        tool_call_count=len(calls),
        tool_names=tuple(call.tool_name for call in calls),
        json_chars=json_chars,
        json_hash=json_hash,
        finish_reason=finish_reason,
    )


def _rejected(
    reason_code: str,
    *,
    invalid_tool_names: tuple[str, ...] = (),
    json_chars: int = 0,
    json_hash: str = "",
    finish_reason: str = "",
) -> BiblioLibrarianAgentValidation:
    return BiblioLibrarianAgentValidation(
        status=STATUS_REJECTED,
        reason_code=reason_code,
        invalid_tool_names=invalid_tool_names,
        json_chars=json_chars,
        json_hash=json_hash,
        finish_reason=finish_reason,
    )


def _bounded_turn(turn: Mapping[str, Any]) -> dict[str, Any]:
    role = _safe_token(turn.get("role"), max_chars=24)
    content = _turn_content(turn)[:_RECENT_DIALOGUE_CONTENT_MAX_CHARS]
    return _clean({"role": role, "content": content})


def _turn_content(turn: Mapping[str, Any]) -> str:
    if not isinstance(turn, Mapping):
        return ""
    return str(turn.get("content") or "")


def _hash(text: Any) -> str:
    value = str(text or "")
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:_HASH_LEN]


def _safe_model_slug(value: Any) -> str:
    return _safe_token(value, max_chars=140)


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
