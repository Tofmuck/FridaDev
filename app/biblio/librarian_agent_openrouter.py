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

from . import librarian_product_methods as product_methods
from . import librarian_tools as tools
from .librarian_agent_contract import SCHEMA_VERSION
from .librarian_agent_contract import BiblioLibrarianAgentRequest
from .librarian_agent_contract import BiblioLibrarianAgentSettings
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import safe_token as _safe_token
from .query_normalizer import fold_text


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
    model = str(model_override or effective_settings.primary_model or "").strip()
    payload: dict[str, Any] = {
        "model": model,
        "messages": build_librarian_agent_messages(request, settings=effective_settings),
        "max_tokens": effective_settings.max_tokens,
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
    if _model_supports_sampling_parameters(model):
        payload["temperature"] = effective_settings.temperature
        payload["top_p"] = effective_settings.top_p
    if effective_settings.reasoning_effort != "none":
        payload["reasoning"] = {"effort": effective_settings.reasoning_effort, "exclude": True}
    return payload


def _model_supports_sampling_parameters(model: Any) -> bool:
    normalized = str(model or "").strip().lower()
    if normalized.startswith("openai/gpt-5"):
        return False
    return True


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
        "section_id, chapter_no, locator/label, page_no/para_no/paragraph_id, "
        "limit, offset, char_offset ou window_chars selon l'outil. Retourne toujours un "
        "product_method explicite et un "
        "case_id quand la demande correspond clairement a un cas de reference; "
        "si tu ne peux pas choisir honnetement entre plusieurs cas, laisse "
        "case_id vide. Le product_method est obligatoire et doit decrire la methode "
        "produit, pas seulement l'outil. Utilise seulement des codes compacts "
        "sans espaces pour intent et answer_mode. intents autorises: "
        "inventory_metadata, document_resolution, list_catalog, show_table_of_contents, "
        "resolve_work, search_catalog, extract_passage, extract_range, compare_passages, clarify. "
        "answer_mode autorises: tool_calls, clarify, catalog_list, toc, "
        "passage, conceptual_search, needs_tool_result_then_page_read, "
        "bounded_context_extract_start_of_section, "
        "deliver_excerpt_context_from_section_start, section_start_page_block_2. "
        "Pour une demande de debut de section ou d'oeuvre interne suivie de "
        "premieres pages, garde un answer_mode compact de cette famille et "
        "n'ecris jamais une phrase libre a la place d'un code. Pour les questions "
        "canoniques d'inventaire/metadonnees (quels ouvrages, combien, langue, pages, "
        "metadonnees connues), choisis product_method=inventory_metadata avec case_id "
        "vide; appelle catalog_list pour l'inventaire, search_document ou "
        "document_open_summary pour un ouvrage cible. Pour les questions canoniques "
        "de resolution documentaire (trouver/resoudre un document, une oeuvre ou "
        "un volume), choisis product_method=document_resolution avec case_id vide; "
        "utilise search_document, search_work, resolve_work ou document_open_summary. "
        "Ne choisis jamais un premier candidat si plusieurs restent possibles: "
        "laisse le statut ambiguous visible. Pour lister toute la "
        "bibliotheque, appelle catalog_list sans q avec limit 100. Pour une "
        "table des matieres sans document_id, commence par catalog_search ou "
        "document_open_summary; le runtime peut porter l'ancre documentaire "
        "unique vers l'outil suivant. Pour un passage, cherche d'abord le "
        "texte primaire demande: distingue texte primaire, table des matieres, "
        "notice, introduction, commentaire, candidats et passage exact. Ne "
        "prends pas un commentaire ou une notice pour le passage principal. "
        "Strategie progressive: prefere search_document/search_work pour la "
        "resolution documentaire, search_section/resolve_section/section_bounds "
        "pour une section dans un document connu, puis locate pour une reference "
        "canonique et passage_context seulement si une position explicite est "
        "connue ou portee par un outil precedent. "
        "Pour le debut d'une section ou d'une oeuvre interne dans un volume/"
        "corpus sans locator canonique, prefere resolve_section puis "
        "section_bounds pour trouver l'entree structurelle; utilise page_read "
        "ensuite si la demande cible explicitement les premieres pages. "
        "Quand un catalog_search, document_open_summary ou locate precede un "
        "autre outil, tu peux omettre document_id si l'ancre sera portee par "
        "le runtime. Pour passage_context, tu peux omettre la position "
        "seulement si un outil precedent la porte deja. Garde les params "
        "strictement minimaux: n'envoie pas de champs null. window_chars doit "
        "rester borne (2000 max, 700 par defaut utile). Pour une recherche "
        "thematique, n'utilise pas locate avec un label en prose libre: "
        "commence par catalog_search, puis passage_context si une position "
        "explicite ou portee est disponible. Quand plusieurs cas partagent la "
        "meme methode, choisis le case_id qui correspond a la forme reelle de "
        "la demande au lieu d'aplatir vers le premier cas de la famille. "
        "Pour P05-P08, utilise aussi les indices de forme exposes dans le "
        "payload utilisateur: si la demande garde la forme canonique avec "
        "accents/non-ASCII, choisis P05; si elle est la variante ASCII/sans "
        "accents de la forme canonique, choisis P06 plutot que P05. "
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
        "current_user_message_folded_ascii": fold_text(request.user_message),
        "current_user_message_has_non_ascii": any(ord(char) > 127 for char in str(request.user_message or "")),
        "recent_dialogue": list(request.bounded_recent_dialogue()),
        "biblio_state": _state_for_model(request.biblio_state),
        "deterministic_baseline": _observation(request.deterministic_plan),
        "case_grammar": list(product_methods.CASE_IDS),
        "case_reference_signatures": list(product_methods.case_reference_signatures()),
        "canonical_families": list(product_methods.all_canonical_family_names()),
        "canonical_family_by_product_method": {
            method: product_methods.canonical_family_for_method(method)
            for method in product_methods.all_product_method_names()
        },
        "available_product_methods": list(product_methods.all_product_method_names()),
        "available_tools": list(tools.LOT3_TOOL_NAMES),
        "forbidden_tools": sorted(tools.FORBIDDEN_TOOL_NAMES),
        "tool_param_contracts": _tool_param_contracts(),
        "budgets": {
            "max_tool_calls": effective_settings.max_tool_calls,
            "max_recent_turns": effective_settings.max_recent_turns,
        },
        "case_selection_note": (
            "Quand plusieurs cas partagent la meme methode, ne les aplatis pas vers "
            "le cas de base si la signature de reference correspond clairement a la "
            "formulation courante. P05-P08: meme methode, mais P05 est la forme "
            "canonique accentuee, P06 la variante sans accents/translitteree, "
            "P07 le voisinage lexical/metaphorique, P08 la paraphrase plus libre. "
            "P16-P18: meme "
            "principe pour la recherche thematique hors oeuvre courante."
        ),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def _tool_param_contracts() -> dict[str, Any]:
    return {
        "search_document": {
            "allowed": ["q", "query", "limit", "offset"],
            "required_any": [["q", "query"]],
            "note": "Recherche bornee de documents/ouvrages dans le catalogue, sans recherche plein texte de passages.",
        },
        "search_work": {
            "allowed": ["document_id", "doc_id", "q", "query", "limit"],
            "required_any": [["q", "query"]],
            "note": "Recherche une oeuvre documentaire; avec document_id, inspecte la structure du document au lieu d'une recherche globale.",
        },
        "search_section": {
            "allowed": ["document_id", "doc_id", "q", "query", "limit"],
            "required_any": [["document_id", "doc_id"], ["q", "query"]],
            "note": "Recherche une section dans la TOC d'un document deja cible.",
        },
        "resolve_work": {
            "allowed": ["document_id", "doc_id", "q", "query", "limit"],
            "required_any": [["document_id", "doc_id", "q", "query"]],
            "note": "Resolution stricte: resolved si unique, ambiguous si plusieurs, not_found si aucune.",
        },
        "resolve_section": {
            "allowed": ["document_id", "doc_id", "q", "query", "chapter_no", "section_id"],
            "required_any": [["document_id", "doc_id"], ["q", "query", "chapter_no", "section_id"]],
            "note": "Resolution stricte d'une section dans un document connu.",
        },
        "section_bounds": {
            "allowed": ["document_id", "doc_id", "q", "query", "chapter_no", "section_id"],
            "required_any": [["document_id", "doc_id"], ["q", "query", "chapter_no", "section_id"]],
            "note": "Renvoie les ancres debut/fin derivees d'une section resolue.",
        },
        "catalog_list": {
            "allowed": ["q", "limit", "offset"],
            "note": "Pour lister la bibliotheque entiere, omettre q et utiliser limit=100.",
        },
        "catalog_search": {
            "allowed": ["q", "query", "limit", "offset"],
            "required_any": [["q", "query"]],
        },
        "search_chapters": {
            "allowed": ["document_id", "doc_id", "q", "query", "limit", "offset"],
            "required_any": [["q", "query"]],
            "note": "Recherche structurelle de chapitres/sections; document_id facultatif si le runtime porte deja une ancre documentaire unique.",
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
                    "case_id",
                    "intent",
                    "product_method",
                    "tool_calls",
                    "answer_mode",
                    "risk_flags",
                    "fallback_reason",
                ],
                "properties": {
                    "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
                    "case_id": {"type": "string", "enum": ["", *product_methods.CASE_IDS]},
                    "intent": _CODE_SCHEMA,
                    "product_method": {"type": "string", "enum": list(product_methods.all_product_method_names())},
                    "tool_calls": {
                        "type": "array",
                        "maxItems": max(0, int(max_tool_calls)),
                        "items": _tool_call_schema(),
                    },
                    "answer_mode": _CODE_SCHEMA,
                    "risk_flags": {"type": "array", "items": _CODE_SCHEMA, "maxItems": 12},
                    "fallback_reason": _CODE_SCHEMA,
                },
            },
        },
    }


def _tool_call_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["tool_name", "method", "params", "call_id"],
        "properties": {
            "tool_name": {"type": "string", "enum": list(tools.LOT3_TOOL_NAMES)},
            "method": {"type": "string", "enum": ["GET"]},
            "params": _tool_params_schema(),
            "call_id": _nullable_code_schema(),
        },
    }


def _tool_params_schema() -> dict[str, Any]:
    properties = {
        "q": _nullable_text_schema(max_chars=240),
        "query": _nullable_text_schema(max_chars=240),
        "document_id": _nullable_text_schema(max_chars=160),
        "doc_id": _nullable_text_schema(max_chars=160),
        "section_id": _nullable_text_schema(max_chars=160),
        "locator": _nullable_text_schema(max_chars=120),
        "label": _nullable_text_schema(max_chars=120),
        "kind": _nullable_code_schema(),
        "limit": _nullable_integer_schema(minimum=0, maximum=100000),
        "offset": _nullable_integer_schema(minimum=0, maximum=100000),
        "chapter_no": _nullable_integer_schema(minimum=0, maximum=100000),
        "page_no": _nullable_integer_schema(minimum=0, maximum=100000),
        "para_no": _nullable_integer_schema(minimum=0, maximum=100000),
        "paragraph_id": _nullable_integer_schema(minimum=0, maximum=1000000000),
        "char_offset": _nullable_integer_schema(minimum=0, maximum=100000000),
        "window_chars": _nullable_integer_schema(minimum=0, maximum=1000000),
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "description": "Utilise null pour toute cle non employee; ne fournis une valeur que pour les params reels de l'outil choisi.",
        "required": sorted(properties.keys()),
        "properties": properties,
    }


def _nullable_text_schema(*, max_chars: int) -> dict[str, Any]:
    return {
        "type": ["string", "null"],
        "maxLength": max_chars,
    }


def _nullable_code_schema() -> dict[str, Any]:
    return {
        "type": ["string", "null"],
        "maxLength": 96,
        "pattern": "^[A-Za-z0-9_:-]{0,96}$",
    }


def _nullable_integer_schema(*, minimum: int, maximum: int) -> dict[str, Any]:
    return {
        "type": ["integer", "null"],
        "minimum": minimum,
        "maximum": maximum,
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
