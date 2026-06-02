"""OpenRouter adapter for the Biblio librarian agent.

The adapter is intentionally not wired into chat product flow. It builds a
strict JSON request and returns only the model text to the immediate validator.
No raw prompt, request payload, or provider JSON is retained by the agent result.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import requests

import config

from . import librarian_tools as tools
from .librarian_agent_contract import SCHEMA_VERSION
from .librarian_agent_contract import BiblioLibrarianAgentRequest
from .librarian_agent_contract import BiblioLibrarianAgentSettings
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import safe_token as _safe_token


STATUS_OK = "ok"
STATUS_ERROR = "error"

REASON_OK = "biblio_librarian_agent_model_ok"
REASON_MODEL_NOT_CONFIGURED = "biblio_librarian_agent_model_not_configured"
REASON_PROVIDER_NOT_CONFIGURED = "biblio_librarian_agent_provider_not_configured"
REASON_TIMEOUT = "biblio_librarian_agent_model_timeout"
REASON_PROVIDER_ERROR = "biblio_librarian_agent_provider_error"
REASON_INVALID_RESPONSE = "biblio_librarian_agent_provider_invalid_response"


@dataclass(frozen=True)
class BiblioLibrarianAgentModelResponse:
    status: str
    reason_code: str
    content: str = field(default="", repr=False, compare=False)
    model_effective: str = ""
    finish_reason: str = ""
    duration_ms: int = 0
    status_code: int | None = None
    response_chars: int = 0
    attempt_count: int = 0
    fallback_model_used: bool = False
    primary_reason_code: str = ""

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "status": self.status,
                "reason_code": self.reason_code,
                "model_effective": _safe_token(self.model_effective, max_chars=140),
                "finish_reason": _safe_token(self.finish_reason),
                "duration_ms": self.duration_ms,
                "status_code": self.status_code,
                "response_chars": self.response_chars,
                "attempt_count": self.attempt_count,
                "fallback_model_used": self.fallback_model_used,
                "primary_reason_code": _safe_token(self.primary_reason_code),
            }
        )


class OpenRouterBiblioLibrarianAgentClient:
    def __init__(
        self,
        *,
        requests_post: Callable[..., Any] = requests.post,
        config_module: Any = config,
        llm_module: Any = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._requests_post = requests_post
        self._config = config_module
        self._llm = llm_module
        self._monotonic = monotonic

    def complete(
        self,
        request: BiblioLibrarianAgentRequest,
        *,
        settings: BiblioLibrarianAgentSettings | None = None,
    ) -> BiblioLibrarianAgentModelResponse:
        effective_settings = settings or request.settings
        if not effective_settings.primary_model:
            return _model_error(REASON_MODEL_NOT_CONFIGURED)
        try:
            provider_headers = self._provider_headers()
            chat_url = self._chat_completions_url()
        except Exception as exc:
            if not _is_provider_config_error(exc):
                raise
            return _model_error(REASON_PROVIDER_NOT_CONFIGURED, model=effective_settings.primary_model)

        primary = self._complete_model(
            request,
            settings=effective_settings,
            model=effective_settings.primary_model,
            provider_headers=provider_headers,
            chat_url=chat_url,
        )
        if (
            primary.status == STATUS_OK
            or not effective_settings.fallback_model
            or effective_settings.max_model_calls < 2
        ):
            return primary
        fallback = self._complete_model(
            request,
            settings=effective_settings,
            model=effective_settings.fallback_model,
            provider_headers=provider_headers,
            chat_url=chat_url,
        )
        return BiblioLibrarianAgentModelResponse(
            status=fallback.status,
            reason_code=fallback.reason_code,
            content=fallback.content,
            model_effective=fallback.model_effective,
            finish_reason=fallback.finish_reason,
            duration_ms=primary.duration_ms + fallback.duration_ms,
            status_code=fallback.status_code,
            response_chars=fallback.response_chars,
            attempt_count=2,
            fallback_model_used=True,
            primary_reason_code=primary.reason_code,
        )

    def _complete_model(
        self,
        request: BiblioLibrarianAgentRequest,
        *,
        settings: BiblioLibrarianAgentSettings,
        model: str,
        provider_headers: Mapping[str, Any],
        chat_url: str,
    ) -> BiblioLibrarianAgentModelResponse:
        started = self._monotonic()
        try:
            response = self._requests_post(
                chat_url,
                headers=dict(provider_headers),
                json=build_librarian_agent_payload(request, settings=settings, model_override=model),
                timeout=settings.timeout_s,
            )
        except requests.Timeout:
            return _model_error(
                REASON_TIMEOUT,
                model=model,
                duration_ms=_duration_ms(started, self._monotonic),
                attempt_count=1,
            )
        except requests.RequestException as exc:
            return _model_error(
                REASON_PROVIDER_ERROR,
                model=model,
                duration_ms=_duration_ms(started, self._monotonic),
                status_code=getattr(getattr(exc, "response", None), "status_code", None),
                attempt_count=1,
            )

        status_code = getattr(response, "status_code", None)
        duration_ms = _duration_ms(started, self._monotonic)
        if status_code is not None and int(status_code) >= 400:
            return _model_error(
                REASON_PROVIDER_ERROR,
                model=model,
                duration_ms=duration_ms,
                status_code=int(status_code),
                attempt_count=1,
            )
        try:
            data = response.json()
        except (TypeError, ValueError):
            return _model_error(
                REASON_INVALID_RESPONSE,
                model=model,
                duration_ms=duration_ms,
                status_code=status_code,
                attempt_count=1,
            )
        choice = _first_choice(data)
        message = choice.get("message") if isinstance(choice.get("message"), Mapping) else {}
        content = str(message.get("content") or "")
        model_effective = str(data.get("model") or model)
        finish_reason = str(choice.get("finish_reason") or "")
        return BiblioLibrarianAgentModelResponse(
            status=STATUS_OK,
            reason_code=REASON_OK,
            content=content,
            model_effective=model_effective,
            finish_reason=finish_reason,
            duration_ms=duration_ms,
            status_code=status_code,
            response_chars=len(content),
            attempt_count=1,
        )

    def _provider_headers(self) -> dict[str, Any]:
        llm_module = self._llm or _default_llm_module()
        return llm_module.or_headers_custom(
            caller="biblio_librarian",
            referer=str(getattr(self._config, "OR_REFERER_BIBLIO_LIBRARIAN", "") or "").strip(),
            title=str(getattr(self._config, "OR_TITLE_BIBLIO_LIBRARIAN", "") or "").strip(),
        )

    def _chat_completions_url(self) -> str:
        llm_module = self._llm or _default_llm_module()
        return llm_module.or_chat_completions_url()


def build_librarian_agent_payload(
    request: BiblioLibrarianAgentRequest,
    *,
    settings: BiblioLibrarianAgentSettings | None = None,
    model_override: str = "",
) -> dict[str, Any]:
    effective_settings = settings or request.settings
    payload: dict[str, Any] = {
        "model": model_override or effective_settings.primary_model,
        "messages": build_librarian_agent_messages(request, settings=effective_settings),
        "max_tokens": effective_settings.max_tokens,
        "temperature": effective_settings.temperature,
        "top_p": effective_settings.top_p,
        "response_format": build_librarian_agent_response_format(
            max_tool_calls=effective_settings.max_tool_calls
        ),
        "provider": {"require_parameters": True},
        "metadata": {
            "frida_caller": "biblio_librarian_agent",
            "frida_contract": SCHEMA_VERSION,
        },
        "trace": {
            "trace_name": "FridaDev",
            "generation_name": "FridaDev / Biblio Librarian Agent",
        },
    }
    if effective_settings.reasoning_effort != "none":
        payload["reasoning"] = {"effort": effective_settings.reasoning_effort, "exclude": True}
    return payload


def build_librarian_agent_messages(
    request: BiblioLibrarianAgentRequest,
    *,
    settings: BiblioLibrarianAgentSettings | None = None,
) -> list[dict[str, str]]:
    effective_settings = settings or request.settings
    system = (
        "Tu es le planificateur bibliothecaire Biblio de FridaDev. "
        "Tu ne reponds jamais en prose libre. Tu produis uniquement un JSON "
        f"conforme a {SCHEMA_VERSION}. Tu choisis seulement des outils GET-only "
        "allowlistes et tu respectes exactement les parametres declares. "
        "N'invente jamais work_title, title, theme, author, start_locator ou "
        "end_locator comme cle de params: utilise q/query, document_id/doc_id, "
        "locator/label, page_no/para_no/paragraph_id, limit, offset, "
        "char_offset ou window_chars selon l'outil. Pour lister toute la "
        "bibliotheque, appelle catalog_list sans q avec limit 100. Pour une "
        "table des matieres sans document_id, commence par catalog_search ou "
        "document_open_summary; le runtime peut porter l'ancre documentaire "
        "unique vers l'outil suivant. Pour un passage, cherche d'abord le "
        "texte primaire demande: distingue texte primaire, table des matieres, "
        "notice, introduction, commentaire, candidats et passage exact. Ne "
        "prends pas un commentaire ou une notice pour le passage principal. "
        "Strategie progressive: catalog_search pour trouver le document ou "
        "l'oeuvre, document_open_summary ou document_toc si la structure aide, "
        "locate pour une reference canonique, puis passage_context seulement "
        "si une position explicite est connue ou portee par un outil precedent. "
        "References Stephanus et plages: reconnais des labels comme 148e, "
        "151d, 126b ou des plages comme 148e-151d et 126b-128a. Pour une plage, "
        "n'envoie pas start_locator/end_locator: utilise locate sur le debut "
        "et, si necessaire, un second locate sur la fin quand un document_id "
        "est disponible ou porte. Si la plage directe n'est pas exploitable, "
        "n'invente pas le texte exact; propose un contexte borne au debut si "
        "possible et signale la limite par un answer_mode ou fallback_reason "
        "compact."
    )
    user_payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": effective_settings.mode,
        "current_user_message": request.user_message,
        "recent_dialogue": list(request.bounded_recent_dialogue()),
        "biblio_state": _state_for_model(request.biblio_state),
        "deterministic_baseline": _observation(request.deterministic_plan),
        "available_tools": list(tools.LOT3_TOOL_NAMES),
        "forbidden_tools": sorted(tools.FORBIDDEN_TOOL_NAMES),
        "tool_param_contracts": _tool_param_contracts(),
        "budgets": {
            "max_tool_calls": effective_settings.max_tool_calls,
            "max_recent_turns": effective_settings.max_recent_turns,
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def _tool_param_contracts() -> dict[str, Any]:
    return {
        "catalog_list": {
            "allowed": ["q", "limit", "offset"],
            "note": "Pour lister la bibliotheque entiere, omettre q et utiliser limit=100.",
        },
        "catalog_search": {
            "allowed": ["q", "query", "limit", "offset"],
            "required_any": [["q", "query"]],
        },
        "document_open_summary": {
            "allowed": ["document_id", "doc_id", "q", "query", "limit"],
            "required_any": [["document_id", "doc_id", "q", "query"]],
        },
        "document_toc": {
            "allowed": ["document_id", "doc_id", "limit", "offset"],
            "required_any": [["document_id", "doc_id"]],
            "note": "Si le doc_id manque, faire preceder par une recherche qui donne un document unique.",
        },
        "page_read": {
            "allowed": ["document_id", "doc_id", "page_no"],
            "required_any": [["document_id", "doc_id"], ["page_no"]],
            "note": "Lecture bornee d'une page explicite; ne pas utiliser latest/page.",
        },
        "locate": {
            "allowed": ["document_id", "doc_id", "locator", "label", "kind", "limit"],
            "required_any": [["document_id", "doc_id"], ["locator", "label"]],
        },
        "passage_context": {
            "allowed": ["document_id", "doc_id", "page_no", "para_no", "paragraph_id", "char_offset", "window_chars"],
            "required_any": [["document_id", "doc_id"]],
            "required_position": True,
            "note": "Une position peut etre portee depuis locate ou catalog_search si elle est unique.",
        },
    }


_CODE_SCHEMA = {"type": "string", "maxLength": 96, "pattern": "^[A-Za-z0-9_:-]{0,96}$"}
_STRING_SCHEMAS = {
    "q": {"type": "string", "minLength": 1, "maxLength": 240},
    "query": {"type": "string", "minLength": 1, "maxLength": 240},
    "document_id": {"type": "string", "minLength": 1, "maxLength": 160},
    "doc_id": {"type": "string", "minLength": 1, "maxLength": 160},
    "locator": {"type": "string", "minLength": 1, "maxLength": 120},
    "label": {"type": "string", "minLength": 1, "maxLength": 120},
    "kind": {"type": "string", "maxLength": 40, "pattern": "^[A-Za-z0-9_:-]{0,40}$"},
}
_PARAM_SCHEMAS_BY_TOOL: dict[str, dict[str, Any]] = {
    tools.TOOL_CATALOG_LIST: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "q": _STRING_SCHEMAS["q"],
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            "offset": {"type": "integer", "minimum": 0, "maximum": 100000},
        },
    },
    tools.TOOL_CATALOG_SEARCH: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "q": _STRING_SCHEMAS["q"],
            "query": _STRING_SCHEMAS["query"],
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "offset": {"type": "integer", "minimum": 0, "maximum": 0},
        },
        "anyOf": [{"required": ["q"]}, {"required": ["query"]}],
    },
    tools.TOOL_DOCUMENT_OPEN_SUMMARY: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_id": _STRING_SCHEMAS["document_id"],
            "doc_id": _STRING_SCHEMAS["doc_id"],
            "q": _STRING_SCHEMAS["q"],
            "query": _STRING_SCHEMAS["query"],
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "anyOf": [{"required": ["document_id"]}, {"required": ["doc_id"]}, {"required": ["q"]}, {"required": ["query"]}],
    },
    tools.TOOL_DOCUMENT_TOC: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_id": _STRING_SCHEMAS["document_id"],
            "doc_id": _STRING_SCHEMAS["doc_id"],
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
            "offset": {"type": "integer", "minimum": 0, "maximum": 100000},
        },
        "anyOf": [{"required": ["document_id"]}, {"required": ["doc_id"]}],
    },
    tools.TOOL_PAGE_READ: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_id": _STRING_SCHEMAS["document_id"],
            "doc_id": _STRING_SCHEMAS["doc_id"],
            "page_no": {"type": "integer", "minimum": 1, "maximum": 100000},
        },
        "allOf": [
            {"anyOf": [{"required": ["document_id"]}, {"required": ["doc_id"]}]},
            {"required": ["page_no"]},
        ],
    },
    tools.TOOL_LOCATE: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_id": _STRING_SCHEMAS["document_id"],
            "doc_id": _STRING_SCHEMAS["doc_id"],
            "locator": _STRING_SCHEMAS["locator"],
            "label": _STRING_SCHEMAS["label"],
            "kind": _STRING_SCHEMAS["kind"],
            "limit": {"type": "integer", "minimum": 1, "maximum": 200},
        },
        "allOf": [
            {"anyOf": [{"required": ["document_id"]}, {"required": ["doc_id"]}]},
            {"anyOf": [{"required": ["locator"]}, {"required": ["label"]}]},
        ],
    },
    tools.TOOL_PASSAGE_CONTEXT: {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_id": _STRING_SCHEMAS["document_id"],
            "doc_id": _STRING_SCHEMAS["doc_id"],
            "page_no": {"type": "integer", "minimum": 1, "maximum": 100000},
            "para_no": {"type": "integer", "minimum": 1, "maximum": 100000},
            "paragraph_id": {"type": "integer", "minimum": 1, "maximum": 2147483647},
            "char_offset": {"type": "integer", "minimum": 0, "maximum": 1000000},
            "window_chars": {"type": "integer", "minimum": 80, "maximum": 2000},
        },
        "allOf": [
            {"anyOf": [{"required": ["document_id"]}, {"required": ["doc_id"]}]},
            {"anyOf": [{"required": ["paragraph_id"]}, {"required": ["page_no", "para_no"]}]},
        ],
    },
}


def build_librarian_agent_response_format(*, max_tool_calls: int = 5) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_VERSION,
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "schema_version",
                    "intent",
                    "tool_calls",
                    "answer_mode",
                    "risk_flags",
                    "fallback_reason",
                ],
                "properties": {
                    "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
                    "intent": _CODE_SCHEMA,
                    "tool_calls": {
                        "type": "array",
                        "maxItems": max(0, int(max_tool_calls)),
                        "items": {"oneOf": [_tool_call_schema(tool_name) for tool_name in tools.LOT3_TOOL_NAMES]},
                    },
                    "answer_mode": _CODE_SCHEMA,
                    "risk_flags": {"type": "array", "items": _CODE_SCHEMA, "maxItems": 12},
                    "fallback_reason": _CODE_SCHEMA,
                },
            },
        },
    }


def _tool_call_schema(tool_name: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["tool_name", "method", "params"],
        "properties": {
            "tool_name": {"type": "string", "enum": [tool_name]},
            "method": {"type": "string", "enum": ["GET"]},
            "params": _PARAM_SCHEMAS_BY_TOOL[tool_name],
            "call_id": _CODE_SCHEMA,
        },
    }


def _is_provider_config_error(exc: Exception) -> bool:
    return exc.__class__.__name__ in {
        "RuntimeSettingsDbUnavailableError",
        "RuntimeSettingsSecretRequiredError",
        "RuntimeSettingsSecretResolutionError",
    }


def _default_llm_module() -> Any:
    from core import llm_client

    return llm_client


def _state_for_model(state: Any) -> Any:
    if state is None:
        return {}
    if hasattr(state, "to_dict"):
        raw = state.to_dict()
        if isinstance(raw, Mapping):
            return _state_mapping_for_model(raw)
    if hasattr(state, "to_observability"):
        return state.to_observability()
    if isinstance(state, Mapping):
        return _state_mapping_for_model(state)
    return {"present": True}


def _state_mapping_for_model(state: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "current_document",
        "current_work",
        "page_no",
        "para_no",
        "paragraph_id",
        "last_passage_hash",
        "last_result",
        "last_candidates",
        "last_ambiguity",
        "last_intent",
    }
    projected = {key: state[key] for key in allowed if key in state}
    projected["present"] = bool(
        projected.get("current_document")
        or projected.get("current_work")
        or projected.get("last_result")
        or projected.get("last_candidates")
        or projected.get("last_ambiguity")
        or projected.get("last_intent")
    )
    return projected


def _observation(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_observability"):
        observed = value.to_observability()
        return dict(observed) if isinstance(observed, Mapping) else {}
    if isinstance(value, Mapping):
        return dict(value)
    return {"present": True}


def _first_choice(data: Mapping[str, Any]) -> Mapping[str, Any]:
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
        return choices[0]
    return {}


def _model_error(
    reason_code: str,
    *,
    model: str = "",
    duration_ms: int = 0,
    status_code: int | None = None,
    attempt_count: int = 0,
) -> BiblioLibrarianAgentModelResponse:
    return BiblioLibrarianAgentModelResponse(
        status=STATUS_ERROR,
        reason_code=reason_code,
        model_effective=model,
        duration_ms=duration_ms,
        status_code=status_code,
        attempt_count=attempt_count,
    )


def _duration_ms(started: float, monotonic: Callable[[], float]) -> int:
    return max(0, int((monotonic() - started) * 1000))
