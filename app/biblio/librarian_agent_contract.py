"""Versioned contract and validation for the Biblio librarian agent."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import librarian_product_methods as product_methods
from . import librarian_planner as planner
from . import librarian_tools as tools
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import safe_token as _safe_token
from .librarian_planner_observability import safe_tool_name as _safe_tool_name


SCHEMA_VERSION = "biblio_librarian_agent_v1"
DEFAULT_TIMEOUT_S = 240

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
REASON_CASE_ID_UNKNOWN = "biblio_librarian_agent_case_id_unknown"
REASON_PRODUCT_METHOD_UNKNOWN = "biblio_librarian_agent_product_method_unknown"
REASON_PRODUCT_METHOD_CASE_MISMATCH = "biblio_librarian_agent_product_method_case_mismatch"
REASON_PRODUCT_METHOD_TOOL_MISMATCH = "biblio_librarian_agent_product_method_tool_mismatch"
REASON_TOOL_FORBIDDEN = "biblio_librarian_agent_forbidden_tool"
REASON_TOOL_UNKNOWN = "biblio_librarian_agent_unknown_tool"
REASON_METHOD_FORBIDDEN = "biblio_librarian_agent_forbidden_method"
REASON_TOOL_NOT_EXECUTABLE = "biblio_librarian_agent_tool_not_executable"
REASON_BUDGET_EXCEEDED = "biblio_librarian_agent_budget_exceeded"

_HASH_LEN = 12
_RECENT_DIALOGUE_CONTENT_MAX_CHARS = 1200
_ROOT_KEYS = {
    "schema_version",
    "case_id",
    "intent",
    "product_method",
    "tool_calls",
    "answer_mode",
    "risk_flags",
    "fallback_reason",
}
_CALL_KEYS = {"tool_name", "method", "params", "call_id"}
_CODE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-")
_TEXT_PARAM_MAX = {
    "q": 240,
    "query": 240,
    "title": 240,
    "document_title": 240,
    "work_title": 240,
    "author": 240,
    "document_id": 160,
    "doc_id": 160,
    "section_id": 160,
    "locator": 120,
    "locator_end": 120,
    "label": 120,
    "kind": 40,
}
_INT_PARAM_BOUNDS = {
    "limit": (1, 500),
    "offset": (0, 100_000),
    "page_no": (1, 100_000),
    "para_no": (1, 100_000),
    "paragraph_id": (1, 2_147_483_647),
    "chapter_no": (1, 100_000),
    "char_offset": (0, 1_000_000),
    "window_chars": (80, 2_000),
    "max_passage_chars": (80, 8_000),
    "locator_anchor_page": (1, 100_000),
    "locator_anchor_para": (1, 100_000),
}
_REASONING_EFFORTS = {"xhigh", "high", "medium", "low", "minimal", "none"}
_TOOL_PARAM_CONTRACTS = {
    tools.TOOL_SEARCH_DOCUMENT: {
        "allowed": {"q", "query", "limit", "offset"},
        "required_any": (("q", "query"),),
        "int_bounds": {"limit": (1, 50), "offset": (0, 100_000)},
    },
    tools.TOOL_SEARCH_WORK: {
        "allowed": {"document_id", "doc_id", "q", "query", "limit"},
        "required_any": (("q", "query"),),
        "int_bounds": {"limit": (1, 50)},
    },
    tools.TOOL_SEARCH_SECTION: {
        "allowed": {"document_id", "doc_id", "q", "query", "limit"},
        "required_any": (("document_id", "doc_id"), ("q", "query")),
        "int_bounds": {"limit": (1, 50)},
    },
    tools.TOOL_RESOLVE_WORK: {
        "allowed": {"document_id", "doc_id", "q", "query", "limit"},
        "required_any": (("document_id", "doc_id", "q", "query"),),
        "int_bounds": {"limit": (1, 20)},
    },
    tools.TOOL_RESOLVE_SECTION: {
        "allowed": {"document_id", "doc_id", "q", "query", "chapter_no", "section_id"},
        "required_any": (("document_id", "doc_id"), ("q", "query", "chapter_no", "section_id")),
        "int_bounds": {"chapter_no": (1, 100_000)},
    },
    tools.TOOL_SECTION_BOUNDS: {
        "allowed": {"document_id", "doc_id", "q", "query", "chapter_no", "section_id"},
        "required_any": (("document_id", "doc_id"), ("q", "query", "chapter_no", "section_id")),
        "int_bounds": {"chapter_no": (1, 100_000)},
    },
    tools.TOOL_CATALOG_LIST: {
        "allowed": {"q", "limit", "offset"},
        "required_any": (),
        "int_bounds": {"limit": (1, 100), "offset": (0, 100_000)},
    },
    tools.TOOL_CATALOG_SEARCH: {
        "allowed": {"q", "query", "document_id", "doc_id", "limit", "offset"},
        "required_any": (("q", "query"),),
        "int_bounds": {"limit": (1, 50), "offset": (0, 0)},
    },
    tools.TOOL_SEARCH_CHAPTERS: {
        "allowed": {"document_id", "doc_id", "q", "query", "limit", "offset"},
        "required_any": (("q", "query"),),
        "int_bounds": {"limit": (1, 50), "offset": (0, 0)},
    },
    tools.TOOL_DOCUMENT_OPEN_SUMMARY: {
        "allowed": {"document_id", "doc_id", "q", "query", "limit"},
        "required_any": (("document_id", "doc_id", "q", "query"),),
        "int_bounds": {"limit": (1, 20)},
    },
    tools.TOOL_DOCUMENT_TOC: {
        "allowed": {"document_id", "doc_id", "limit", "offset"},
        "required_any": (("document_id", "doc_id"),),
        "int_bounds": {"limit": (1, 500), "offset": (0, 100_000)},
    },
    tools.TOOL_PAGE_READ: {
        "allowed": {"document_id", "doc_id", "page_no"},
        "required_any": (("document_id", "doc_id"), ("page_no",)),
        "int_bounds": {"page_no": (1, 100_000)},
    },
    tools.TOOL_LOCATE: {
        "allowed": {"document_id", "doc_id", "locator", "label", "kind", "limit"},
        "required_any": (("document_id", "doc_id"), ("locator", "label")),
        "int_bounds": {"limit": (1, 200)},
    },
    tools.TOOL_PASSAGE_CONTEXT: {
        "allowed": {"document_id", "doc_id", "page_no", "para_no", "paragraph_id", "char_offset", "window_chars"},
        "required_any": (("document_id", "doc_id"),),
        "required_position": True,
        "int_bounds": {
            "page_no": (1, 100_000),
            "para_no": (1, 100_000),
            "paragraph_id": (1, 2_147_483_647),
            "char_offset": (0, 1_000_000),
            "window_chars": (80, 2_000),
        },
    },
    tools.TOOL_CANONICAL_RANGE_EXTRACT: {
        "allowed": {
            "document_id",
            "doc_id",
            "q",
            "query",
            "title",
            "document_title",
            "work_title",
            "author",
            "locator",
            "label",
            "locator_end",
            "kind",
            "locator_anchor_page",
            "locator_anchor_para",
            "max_passage_chars",
        },
        "required_any": (("document_id", "doc_id", "q", "query", "title", "document_title", "work_title", "author"), ("locator", "label"), ("locator_end",)),
        "int_bounds": {
            "locator_anchor_page": (1, 100_000),
            "locator_anchor_para": (1, 100_000),
            "max_passage_chars": (80, 8_000),
        },
    },
}


@dataclass(frozen=True)
class BiblioLibrarianAgentSettings:
    mode: str = MODE_OFF
    primary_model: str = ""
    fallback_model: str = ""
    timeout_s: int = DEFAULT_TIMEOUT_S
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 900
    max_tool_calls: int = 5
    max_model_calls: int = 1
    max_recent_turns: int = 5
    reasoning_effort: str = "none"
    settings_source: str = ""
    settings_source_reason: str = ""

    @classmethod
    def from_config(cls, config_module: Any) -> "BiblioLibrarianAgentSettings":
        return cls(
            mode=normalize_mode(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MODE", MODE_OFF)),
            primary_model=str(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MODEL", "") or "").strip(),
            fallback_model=str(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_FALLBACK_MODEL", "") or "").strip(),
            timeout_s=_positive_int(
                getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_TIMEOUT_S", DEFAULT_TIMEOUT_S),
                DEFAULT_TIMEOUT_S,
            ),
            temperature=_float(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_TEMPERATURE", 0.0), 0.0),
            top_p=_float(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_TOP_P", 1.0), 1.0),
            max_tokens=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_TOKENS", 900), 900),
            max_tool_calls=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_TOOL_CALLS", 5), 5),
            max_model_calls=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_MODEL_CALLS", 1), 1),
            max_recent_turns=_positive_int(getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MAX_RECENT_TURNS", 5), 5),
            reasoning_effort=_reasoning_effort(
                getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_REASONING_EFFORT", "none")
            ),
            settings_source="config",
            settings_source_reason="explicit_config_module",
        )

    @classmethod
    def from_runtime_settings(
        cls,
        *,
        fetcher: Any = None,
        runtime_settings_module: Any = None,
        mode_override: Any = None,
    ) -> "BiblioLibrarianAgentSettings":
        if runtime_settings_module is None:
            from admin import runtime_settings as runtime_settings_module

        view = runtime_settings_module.get_biblio_librarian_agent_settings(fetcher=fetcher)
        payload = view.payload
        mode = normalize_mode(mode_override) if mode_override is not None else normalize_mode(_payload_value(payload, "mode"))
        return cls(
            mode=mode,
            primary_model=_payload_text(payload, "primary_model"),
            fallback_model=_payload_text(payload, "fallback_model"),
            timeout_s=_positive_int(_payload_value(payload, "timeout_s"), DEFAULT_TIMEOUT_S),
            temperature=_float(_payload_value(payload, "temperature"), 0.0),
            top_p=_float(_payload_value(payload, "top_p"), 1.0),
            max_tokens=_positive_int(_payload_value(payload, "max_tokens"), 900),
            max_tool_calls=_positive_int(_payload_value(payload, "max_tool_calls"), 5),
            max_model_calls=_positive_int(_payload_value(payload, "max_model_calls"), 1),
            max_recent_turns=_positive_int(_payload_value(payload, "max_recent_turns"), 5),
            reasoning_effort=_reasoning_effort(_payload_value(payload, "reasoning_effort")),
            settings_source=_safe_token(getattr(view, "source", "")),
            settings_source_reason=_safe_token(getattr(view, "source_reason", "")),
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
                "reasoning_effort": _reasoning_effort(self.reasoning_effort),
                "settings_source": _safe_token(self.settings_source),
                "settings_source_reason": _safe_token(self.settings_source_reason),
                "json_contract_required": True,
                "require_parameters": True,
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


def _reasoning_effort(value: Any) -> str:
    effort = _safe_token(value)
    return effort if effort in _REASONING_EFFORTS else "none"


def _payload_value(payload: Mapping[str, Any], field: str) -> Any:
    field_payload = payload.get(field) if isinstance(payload, Mapping) else None
    if isinstance(field_payload, Mapping):
        return field_payload.get("value")
    return None


def _payload_text(payload: Mapping[str, Any], field: str) -> str:
    return str(_payload_value(payload, field) or "").strip()


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
    validation = validate_agent_payload(
        payload,
        settings=settings,
        json_chars=json_chars,
        json_hash=json_hash,
        finish_reason=finish_reason,
    )
    if validation.status == STATUS_VALIDATED:
        return validation
    repaired = _repair_agent_payload(payload)
    if repaired is payload:
        return validation
    repaired_validation = validate_agent_payload(
        repaired,
        settings=settings,
        json_chars=json_chars,
        json_hash=json_hash,
        finish_reason=finish_reason,
    )
    return repaired_validation if repaired_validation.status == STATUS_VALIDATED else validation


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
    if set(payload.keys()) != _ROOT_KEYS:
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if str(payload.get("schema_version") or "") != SCHEMA_VERSION:
        return _rejected(REASON_SCHEMA_VERSION, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    case_id = product_methods.normalize_case_id(payload.get("case_id"))
    if not _valid_code(payload.get("intent")):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if case_id and not product_methods.is_known_case_id(case_id):
        return _rejected(REASON_CASE_ID_UNKNOWN, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    product_method = str(payload.get("product_method") or "").strip()
    if not product_methods.is_known_product_method(product_method):
        return _rejected(
            REASON_PRODUCT_METHOD_UNKNOWN,
            json_chars=json_chars,
            json_hash=json_hash,
            finish_reason=finish_reason,
        )
    if not product_methods.method_accepts_case_id(product_method, case_id):
        return _rejected(
            REASON_PRODUCT_METHOD_CASE_MISMATCH,
            json_chars=json_chars,
            json_hash=json_hash,
            finish_reason=finish_reason,
        )
    if not _valid_code(payload.get("answer_mode")):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if not _valid_code(payload.get("fallback_reason")):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if not _valid_risk_flags(payload.get("risk_flags")):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    raw_calls = payload.get("tool_calls")
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, (str, bytes, bytearray)):
        return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if len(raw_calls) > effective_settings.max_tool_calls:
        return _rejected(REASON_BUDGET_EXCEEDED, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
    if not raw_calls and product_methods.method_requires_tool_calls(product_method):
        return _rejected(
            REASON_PRODUCT_METHOD_TOOL_MISMATCH,
            json_chars=json_chars,
            json_hash=json_hash,
            finish_reason=finish_reason,
        )

    calls: list[planner.BiblioLibrarianToolCall] = []
    invalid_tool_names: list[str] = []
    carry_document_available = False
    carry_position_available = False
    carry_section_available = False
    for raw_call in raw_calls:
        if not isinstance(raw_call, Mapping):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        if not {"tool_name", "method", "params"}.issubset(raw_call.keys()):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        if not set(raw_call.keys()).issubset(_CALL_KEYS):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        tool_name = _safe_tool_name(raw_call.get("tool_name"))
        method = str(raw_call.get("method") or "").strip().upper()
        if "call_id" in raw_call and not _valid_code(raw_call.get("call_id")):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
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
        if not product_methods.method_allows_tool(product_method, tool_name):
            return _rejected(
                REASON_PRODUCT_METHOD_TOOL_MISMATCH,
                json_chars=json_chars,
                json_hash=json_hash,
                finish_reason=finish_reason,
            )
        params = raw_call.get("params")
        if not isinstance(params, Mapping):
            return _rejected(REASON_SCHEMA_INVALID, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        if not _valid_params(tool_name, params) and not _valid_deferred_params(
            tool_name,
            params,
            carry_document_available=carry_document_available,
            carry_position_available=carry_position_available,
            carry_section_available=carry_section_available,
        ):
            return _rejected(REASON_TOOL_NOT_EXECUTABLE, json_chars=json_chars, json_hash=json_hash, finish_reason=finish_reason)
        calls.append(
            planner.BiblioLibrarianToolCall(
                tool_name=tool_name,
                params=dict(params),
                call_id=str(raw_call.get("call_id") or ""),
                method=method,
            )
        )
        if tool_name in {
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_SEARCH_SECTION,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
        }:
            carry_document_available = True
        if tool_name in {tools.TOOL_CATALOG_SEARCH, tools.TOOL_LOCATE, tools.TOOL_PASSAGE_CONTEXT}:
            carry_position_available = True
            carry_document_available = True
        if tool_name in {tools.TOOL_SEARCH_SECTION, tools.TOOL_RESOLVE_SECTION, tools.TOOL_SECTION_BOUNDS}:
            carry_section_available = True
            carry_document_available = True

    resolved_case_id = case_id or product_methods.default_case_id_for_method(product_method)
    plan = planner.BiblioLibrarianPlan(
        schema_version=planner.SCHEMA_VERSION,
        case_id=resolved_case_id,
        intent=_safe_token(payload.get("intent")),
        product_method=_safe_token(product_method),
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


def _repair_agent_payload(payload: Any) -> Any:
    if not isinstance(payload, Mapping):
        return payload
    payload = _unwrap_agent_payload(payload)
    raw_calls = payload.get("tool_calls")
    if raw_calls is None:
        raw_calls = payload.get("tools") or payload.get("calls")
    changed = False
    if isinstance(raw_calls, Mapping):
        raw_calls = (raw_calls,)
        changed = True
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, (str, bytes, bytearray)):
        return payload
    repaired_calls: list[dict[str, Any]] = []
    for raw_call in raw_calls:
        if not isinstance(raw_call, Mapping):
            return payload
        tool_name = _safe_tool_name(raw_call.get("tool_name") or raw_call.get("name") or raw_call.get("tool"))
        if tool_name not in tools.LOT3_TOOL_NAMES:
            return payload
        params = raw_call.get("params")
        if params is None:
            params = raw_call.get("parameters") or raw_call.get("args")
        params = _repair_raw_params(tool_name, params)
        if params is None:
            return payload
        repaired_tool_name = _repair_tool_name(tool_name, params)
        repaired_params = _repair_params(repaired_tool_name, params)
        repaired_call = {
            "tool_name": repaired_tool_name,
            "method": str(raw_call.get("method") or "GET").strip().upper(),
            "params": repaired_params,
        }
        call_id = raw_call.get("call_id")
        if call_id:
            repaired_call["call_id"] = str(call_id)
        changed = (
            changed
            or repaired_tool_name != tool_name
            or set(raw_call.keys()) != set(repaired_call.keys())
            or dict(params) != repaired_params
        )
        repaired_calls.append(repaired_call)
    repaired_payload = {
        "schema_version": str(payload.get("schema_version") or SCHEMA_VERSION),
        "case_id": "",
        "intent": _safe_token(payload.get("intent")) or "biblio_request",
        "product_method": "",
        "tool_calls": repaired_calls,
        "answer_mode": _safe_token(payload.get("answer_mode")) or "tool",
        "risk_flags": payload.get("risk_flags") if isinstance(payload.get("risk_flags"), list) else [],
        "fallback_reason": _safe_token(payload.get("fallback_reason")),
    }
    inferred_product_method = product_methods.infer_product_method(
        intent=repaired_payload["intent"],
        answer_mode=repaired_payload["answer_mode"],
        tool_names=[str(call.get("tool_name") or "") for call in repaired_calls],
    )
    explicit_product_method = _safe_token(payload.get("product_method"))
    if product_methods.is_section_start_extraction_answer_mode(repaired_payload["answer_mode"]):
        repaired_payload["product_method"] = product_methods.PRODUCT_METHOD_EXTRACTION
    else:
        repaired_payload["product_method"] = explicit_product_method or inferred_product_method
    explicit_case_id = product_methods.normalize_case_id(payload.get("case_id"))
    if explicit_case_id and product_methods.is_known_case_id(explicit_case_id):
        if product_methods.method_accepts_case_id(repaired_payload["product_method"], explicit_case_id):
            repaired_payload["case_id"] = explicit_case_id
        else:
            repaired_payload["case_id"] = ""
    else:
        repaired_payload["case_id"] = product_methods.default_case_id_for_method(
            repaired_payload["product_method"]
        ) or product_methods.infer_case_id_for_legacy_payload(
            product_method=repaired_payload["product_method"],
            intent=repaired_payload["intent"],
            answer_mode=repaired_payload["answer_mode"],
            tool_names=[str(call.get("tool_name") or "") for call in repaired_calls],
        )
    changed = changed or set(payload.keys()) != _ROOT_KEYS
    return repaired_payload if changed else payload


def _unwrap_agent_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if payload.get("tool_calls") is not None:
        return payload
    for key in ("plan", "agent_plan", "biblio_plan", "result", "answer"):
        nested = payload.get(key)
        if not isinstance(nested, Mapping):
            continue
        if nested.get("tool_calls") is None and nested.get("tools") is None and nested.get("calls") is None:
            continue
        merged = dict(payload)
        merged.update(nested)
        for wrapper_key in ("plan", "agent_plan", "biblio_plan", "result", "answer"):
            if wrapper_key not in _ROOT_KEYS:
                merged.pop(wrapper_key, None)
        return merged
    return payload


def _repair_raw_params(tool_name: str, params: Any) -> Mapping[str, Any] | None:
    if isinstance(params, Mapping):
        return params
    if params is None:
        return {}
    if isinstance(params, str) and params.strip():
        if tool_name in {
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_SEARCH_SECTION,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_CATALOG_LIST,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_PASSAGE_CONTEXT,
        }:
            return {"query": params.strip()[:240]}
        if tool_name == tools.TOOL_LOCATE:
            return {"locator": params.strip()[:120]}
        if tool_name == tools.TOOL_CANONICAL_RANGE_EXTRACT:
            return {"query": params.strip()[:240]}
    return None


def _repair_tool_name(tool_name: str, params: Mapping[str, Any]) -> str:
    if tool_name == tools.TOOL_DOCUMENT_TOC and not _has_document_id(params) and _combined_query(params):
        return tools.TOOL_CATALOG_SEARCH
    if tool_name == tools.TOOL_LOCATE and not _has_document_id(params) and _combined_query(params):
        return tools.TOOL_CATALOG_SEARCH
    if tool_name == tools.TOOL_LOCATE and not _has_document_id(params):
        if _safe_token(params.get("kind")) == "fulltext" and _first_text(params, ("label", "locator")):
            return tools.TOOL_CATALOG_SEARCH
    if tool_name == tools.TOOL_PASSAGE_CONTEXT and (
        not _has_document_id(params) or not _has_context_position(params)
    ) and _combined_query(params):
        return tools.TOOL_CATALOG_SEARCH
    return tool_name


def _repair_params(tool_name: str, params: Mapping[str, Any]) -> dict[str, Any]:
    contract = _TOOL_PARAM_CONTRACTS[tool_name]
    allowed = set(contract["allowed"])
    repaired = {
        key: value
        for key, value in params.items()
        if key in allowed and value is not None and not (isinstance(value, str) and not value.strip())
    }
    if tool_name in {
        tools.TOOL_SEARCH_DOCUMENT,
        tools.TOOL_SEARCH_WORK,
        tools.TOOL_SEARCH_SECTION,
        tools.TOOL_RESOLVE_WORK,
        tools.TOOL_RESOLVE_SECTION,
        tools.TOOL_SECTION_BOUNDS,
        tools.TOOL_CATALOG_SEARCH,
        tools.TOOL_DOCUMENT_OPEN_SUMMARY,
        tools.TOOL_CATALOG_LIST,
    }:
        if not (repaired.get("q") or repaired.get("query")):
            query = _combined_query(params)
            if not query and _safe_token(params.get("kind")) == "fulltext":
                query = _first_text(params, ("label", "locator"))
            if query:
                repaired["query" if tool_name != tools.TOOL_CATALOG_LIST else "q"] = query
    if tool_name == tools.TOOL_LOCATE and not (repaired.get("locator") or repaired.get("label")):
        locator = _first_text(params, ("locator_start", "start_locator", "stephanus", "reference"))
        if locator:
            repaired["locator"] = locator
    if tool_name == tools.TOOL_CATALOG_LIST and "limit" not in repaired:
        repaired["limit"] = 100
    return _repair_integer_params(tool_name, repaired)


def _repair_integer_params(tool_name: str, params: Mapping[str, Any]) -> dict[str, Any]:
    bounds = _TOOL_PARAM_CONTRACTS[tool_name].get("int_bounds", {})
    repaired = dict(params)
    for key, (minimum, maximum) in bounds.items():
        if key not in repaired:
            continue
        value = repaired[key]
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if type(value) is int:
            value = max(minimum, min(maximum, value))
            repaired[key] = value
    return repaired


def _combined_query(params: Mapping[str, Any]) -> str:
    values: list[str] = []
    for name in (
        "q",
        "query",
        "title",
        "work_title",
        "document_title",
        "author",
        "theme",
        "theme_query",
        "subject",
    ):
        value = _first_text(params, (name,))
        if value and value not in values:
            values.append(value)
    return " ".join(values)[:240].strip()


def _has_document_id(params: Mapping[str, Any]) -> bool:
    return bool(_first_text(params, ("document_id", "doc_id")))


def _has_context_position(params: Mapping[str, Any]) -> bool:
    has_paragraph = _present_like(params.get("paragraph_id"))
    has_page_pair = _present_like(params.get("page_no")) and _present_like(params.get("para_no"))
    return has_paragraph or has_page_pair


def _has_section_anchor(params: Mapping[str, Any]) -> bool:
    return bool(_first_text(params, ("section_id", "q", "query")) or _present_like(params.get("chapter_no")))


def _present_like(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _first_text(params: Mapping[str, Any], names: Sequence[str]) -> str:
    for name in names:
        value = params.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()[:240]
    return ""


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


def _valid_code(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 96:
        return False
    return all(char in _CODE_CHARS for char in value)


def _valid_risk_flags(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    if len(value) > 12:
        return False
    return all(_valid_code(item) for item in value)


def _valid_params(tool_name: str, params: Mapping[str, Any]) -> bool:
    contract = _TOOL_PARAM_CONTRACTS.get(tool_name)
    if not contract:
        return False
    allowed = contract.get("allowed", set())
    if not isinstance(allowed, set) or not set(params.keys()).issubset(allowed):
        return False
    required_any = contract.get("required_any", ())
    for alternatives in required_any:
        if not any(_present_param(params, key) for key in alternatives):
            return False
    if contract.get("required_position"):
        has_paragraph = _present_param(params, "paragraph_id")
        has_page_pair = _present_param(params, "page_no") and _present_param(params, "para_no")
        if not has_paragraph and not has_page_pair:
            return False
    int_bounds = contract.get("int_bounds", {})
    for key, value in params.items():
        if key in _TEXT_PARAM_MAX:
            if not isinstance(value, str):
                return False
            stripped = value.strip()
            if len(stripped) > _TEXT_PARAM_MAX[key]:
                return False
            if key in {"document_id", "doc_id", "q", "query", "locator", "label"} and not stripped:
                return False
            if key == "kind" and not _valid_code(value):
                return False
            continue
        if key in _INT_PARAM_BOUNDS:
            if type(value) is not int:
                return False
            minimum, maximum = int_bounds.get(key, _INT_PARAM_BOUNDS[key])
            if value < minimum or value > maximum:
                return False
            continue
        return False
    return True


def _valid_deferred_params(
    tool_name: str,
    params: Mapping[str, Any],
    *,
    carry_document_available: bool,
    carry_position_available: bool,
    carry_section_available: bool,
) -> bool:
    synthetic = dict(params)
    if tool_name == tools.TOOL_PASSAGE_CONTEXT:
        if not carry_document_available or not carry_position_available:
            return False
        if not _has_document_id(synthetic):
            synthetic["document_id"] = "doc-carried"
        if not _has_context_position(synthetic):
            synthetic["paragraph_id"] = 1
        return _valid_params(tool_name, synthetic)
    if tool_name in {
        tools.TOOL_DOCUMENT_TOC,
        tools.TOOL_SEARCH_SECTION,
        tools.TOOL_RESOLVE_SECTION,
        tools.TOOL_PAGE_READ,
        tools.TOOL_LOCATE,
        tools.TOOL_CANONICAL_RANGE_EXTRACT,
    }:
        if _has_document_id(synthetic) or not carry_document_available:
            return False
        synthetic["document_id"] = "doc-carried"
        return _valid_params(tool_name, synthetic)
    if tool_name == tools.TOOL_SECTION_BOUNDS:
        if not _has_document_id(synthetic):
            if not carry_document_available:
                return False
            synthetic["document_id"] = "doc-carried"
        if not _has_section_anchor(synthetic):
            if not carry_section_available:
                return False
            synthetic["section_id"] = "section-carried"
        return _valid_params(tool_name, synthetic)
    return False


def _present_param(params: Mapping[str, Any], key: str) -> bool:
    value = params.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    if key in _INT_PARAM_BOUNDS:
        return type(value) is int
    return value is not None


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
