"""Content-free product smokes for the future Biblio librarian agent.

This runner validates the live product envelope without activating the agent as
controller.  It exercises the deterministic Biblio path, records the passive
librarian comparison and dialogue plan projections, and emits compact JSONL.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import config as runtime_config

from .catalogue_client import CatalogueClient, ENDPOINT_DOCUMENT
from .chat_runtime import BiblioChatResult, run_biblio_chat_turn
from .conversation_state import BiblioConversationState
from . import librarian_agent_contract as agent_contract
from .librarian_dialogue_planner import BiblioDialoguePlanningResult, plan_biblio_dialogue


@dataclass(frozen=True)
class BiblioLibrarianProductSmokeCase:
    case_id: str
    case_kind: str
    message: str
    conversation_key: str = ""


DEFAULT_SMOKE_CASES: tuple[BiblioLibrarianProductSmokeCase, ...] = (
    BiblioLibrarianProductSmokeCase("P01", "catalog_full", "Quels ouvrages as-tu dans la bibliothèque ?"),
    BiblioLibrarianProductSmokeCase("P02", "catalog_full", "Il y a 100 ouvrages ? Liste-les tous."),
    BiblioLibrarianProductSmokeCase("P03", "work_lookup", "Trouve-moi le Théétète de Platon."),
    BiblioLibrarianProductSmokeCase("P04", "range_extract", "Dans le Théétète de Platon, sors-moi 126b à 128a."),
    BiblioLibrarianProductSmokeCase(
        "P05",
        "theme_search",
        "Dans le Théétète, trouve le passage où Socrate parle de la maïeutique.",
    ),
    BiblioLibrarianProductSmokeCase(
        "P06",
        "theme_search",
        "Dans le Theetete, trouve le passage ou Socrate parle de la maieutique.",
    ),
    BiblioLibrarianProductSmokeCase(
        "P07",
        "theme_search",
        "Dans le Théétète, trouve le passage sur la sage-femme.",
    ),
    BiblioLibrarianProductSmokeCase(
        "P08",
        "theme_search",
        "Dans le Théétète, trouve le passage sur accoucher les âmes.",
    ),
    BiblioLibrarianProductSmokeCase("P09", "toc", "Montre-moi la table des matières du Théétète."),
    BiblioLibrarianProductSmokeCase(
        "P10",
        "state_seed",
        "Dans le Théétète de Platon, sors-moi 126b à 128a.",
        conversation_key="stateful",
    ),
    BiblioLibrarianProductSmokeCase("P11", "state_followup", "Explique ce passage.", conversation_key="stateful"),
    BiblioLibrarianProductSmokeCase("P12", "state_followup", "Autour de ce passage.", conversation_key="stateful"),
    BiblioLibrarianProductSmokeCase("P13", "state_followup", "Plus haut.", conversation_key="stateful"),
    BiblioLibrarianProductSmokeCase("P14", "state_followup", "Continue.", conversation_key="stateful"),
    BiblioLibrarianProductSmokeCase("P15", "origin_check", "D'où vient ce passage ?", conversation_key="stateful"),
    BiblioLibrarianProductSmokeCase(
        "P16",
        "external_theme",
        "Dans Qu'est-ce que les Lumières ? de Kant, trouve le passage sur Sapere aude.",
    ),
    BiblioLibrarianProductSmokeCase(
        "P17",
        "external_theme",
        "Dans Qu'est-ce que les Lumières ? de Kant, trouve le passage où Kant parle de penser par soi-même.",
    ),
    BiblioLibrarianProductSmokeCase(
        "P18",
        "external_theme",
        "Dans Qu'est-ce que les Lumières ? de Kant, trouve le passage sur oser se servir de son propre entendement.",
    ),
)

DEFAULT_RAW_MARKERS: tuple[str, ...] = (
    "Théétète",
    "Theetete",
    "Platon",
    "Socrate",
    "maïeutique",
    "maieutique",
    "sage-femme",
    "sage femme",
    "accoucher",
    "âmes",
    "les âmes",
    "les ames",
    "Kant",
    "Sapere",
    "aude",
    "Lumières",
    "Lumieres",
    "entendement",
    "126b",
    "128a",
)

SmokeTurnRunner = Callable[..., BiblioChatResult]

EXIT_OK = 0
EXIT_VALIDATION_FAILURE = 2

DEFAULT_AGENT_MODE = agent_contract.MODE_CANDIDATE
_AGENT_MODE_CONFIG = "config"
_ALLOWED_AGENT_MODES = (
    agent_contract.MODE_OFF,
    _AGENT_MODE_CONFIG,
    agent_contract.MODE_SHADOW,
    agent_contract.MODE_CANDIDATE,
)
_OUTPUT_KEYS = {
    "agent_candidate_plan_present",
    "agent_mode",
    "agent_model_called",
    "agent_present",
    "agent_product_response_changed",
    "agent_reason_code",
    "agent_expectation_reason_code",
    "agent_expectation_status",
    "agent_plan_tool_call_count",
    "agent_plan_tool_names",
    "agent_status",
    "agent_tool_call_event_count",
    "agent_tool_execution_status",
    "agent_used_for_response",
    "candidate_count",
    "case_id",
    "case_kind",
    "client_count",
    "context_call_count",
    "dialogue_current_document_used",
    "dialogue_intent",
    "dialogue_reason_code",
    "dialogue_state_present",
    "dialogue_status",
    "dialogue_tool_call_count",
    "dialogue_tool_names",
    "doc_id_shorts",
    "endpoint_count",
    "endpoint_kinds",
    "forbidden_endpoint_used",
    "hashes",
    "lane_chars",
    "lane_injected",
    "lengths",
    "passage_count",
    "payload_objects_retained",
    "product_expectation_reason_code",
    "product_expectation_status",
    "query_kind",
    "raw_marker_leaks",
    "reason_code",
    "runtime_expectation_reason_code",
    "runtime_expectation_status",
    "selected_count",
    "status",
    "total_count",
    "displayed_count",
    "truncated",
}


class _AgentModeConfig:
    def __init__(self, *, mode: str, base_config: Any = None) -> None:
        self.BIBLIO_LIBRARIAN_AGENT_MODE = mode
        self._base_config = base_config or runtime_config

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base_config, name)


def run_smokes(
    *,
    cases: Sequence[BiblioLibrarianProductSmokeCase] = DEFAULT_SMOKE_CASES,
    turn_runner: SmokeTurnRunner = run_biblio_chat_turn,
    client_factory: Any = CatalogueClient,
    config_module: Any = None,
    agent_mode: str = DEFAULT_AGENT_MODE,
    raw_markers: Sequence[str] = DEFAULT_RAW_MARKERS,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    states: dict[str, BiblioConversationState] = {}
    recent_dialogues: dict[str, list[dict[str, Any]]] = {}
    agent_config = _config_for_agent_mode(agent_mode, config_module=config_module)
    for case in cases:
        conversation_id = case.conversation_key or case.case_id
        state = states.get(conversation_id, BiblioConversationState.empty(conversation_id=conversation_id))
        recent_dialogue = tuple(recent_dialogues.get(conversation_id, ()))
        dialogue = plan_biblio_dialogue(case.message, state=state, recent_dialogue=recent_dialogue)
        result = turn_runner(
            {"biblio_enabled": True},
            user_msg=case.message,
            conversation_id=conversation_id,
            conversation_state=state,
            recent_dialogue=recent_dialogue,
            client_factory=client_factory,
            config_module=agent_config,
        )
        if result.biblio_state is not None:
            states[conversation_id] = result.biblio_state
        recent_dialogues.setdefault(conversation_id, []).append(_recent_turn_observation(case, result))
        records.append(_record_for_result(case, result, dialogue, raw_markers=raw_markers))
    return records


def _record_for_result(
    case: BiblioLibrarianProductSmokeCase,
    result: BiblioChatResult,
    dialogue: BiblioDialoguePlanningResult,
    *,
    raw_markers: Sequence[str],
) -> dict[str, Any]:
    event = dict(result.observability_payload or {})
    context = result.context_result.to_observability() if result.context_result is not None else {}
    dialogue_observation = dialogue.to_observability()
    lane = _lane_observability(result.prompt_lane) or _mapping(event.get("lane"))
    client = _mapping(event.get("client"))
    counts = _mapping(event.get("counts"))
    passage_search = _mapping(event.get("passage_search"))
    agent = _mapping(event.get("librarian_agent"))
    dialogue_intent = _mapping(dialogue_observation.get("intent"))
    dialogue_plan = _mapping(dialogue_observation.get("plan"))
    endpoint_kinds = _endpoint_kinds(client, context, passage_search)
    passage_count = (
        _to_int(lane.get("passage_count"))
        or _to_int(passage_search.get("passage_count"))
        or _to_int(counts.get("passage_count"))
    )
    lane_chars = _to_int(lane.get("chars")) or _to_int(passage_search.get("lane_chars")) or _to_int(
        counts.get("lane_chars")
    )
    prompt_content = (result.prompt_message or {}).get("content") if result.prompt_message else ""
    base_record: dict[str, Any] = {
        "case_id": case.case_id,
        "case_kind": case.case_kind,
        "status": _safe_token(event.get("status")),
        "reason_code": _safe_token(event.get("reason_code")),
        "query_kind": _safe_token(result.query_kind or event.get("query_kind")),
        "client_count": _to_int(client.get("event_count")),
        "endpoint_count": _to_int(passage_search.get("endpoint_count"))
        or _to_int(context.get("endpoint_count"))
        or _to_int(client.get("event_count")),
        "endpoint_kinds": endpoint_kinds,
        "candidate_count": _to_int(passage_search.get("candidate_count")) or _to_int(context.get("candidate_count")),
        "context_call_count": _to_int(passage_search.get("context_call_count"))
        or _to_int(context.get("context_call_count")),
        "selected_count": _to_int(passage_search.get("selected_count")) or _to_int(context.get("selected_count")),
        "passage_count": passage_count,
        "lane_injected": result.prompt_message is not None,
        "lane_chars": lane_chars,
        "total_count": _to_int(lane.get("total_count")),
        "displayed_count": _to_int(lane.get("displayed_count")) or _to_int(lane.get("item_count")),
        "truncated": _to_bool(lane.get("truncated")),
        "doc_id_shorts": _doc_id_shorts(lane, context, passage_search),
        "hashes": _hashes(lane, context, passage_search),
        "lengths": {
            "lane_chars": lane_chars,
            "prompt_chars": len(prompt_content) if isinstance(prompt_content, str) else 0,
            "passage_chars": _to_int(context.get("passage_chars")) or _to_int(counts.get("passage_chars")),
        },
        "payload_objects_retained": _payload_objects_retained(result),
        "forbidden_endpoint_used": ENDPOINT_DOCUMENT in set(endpoint_kinds),
        "dialogue_status": _safe_token(dialogue_observation.get("status")),
        "dialogue_reason_code": _safe_token(dialogue_observation.get("reason_code")),
        "dialogue_intent": _safe_token(dialogue_intent.get("intent")),
        "dialogue_tool_call_count": len(_sequence(dialogue_plan.get("tool_names"))),
        "dialogue_tool_names": _safe_token_list(dialogue_plan.get("tool_names")),
        "dialogue_state_present": _to_bool(dialogue_observation.get("state_present")),
        "dialogue_current_document_used": _to_bool(dialogue_observation.get("current_document_used")),
        "agent_present": _to_bool(agent.get("present")),
        "agent_status": _safe_token(agent.get("status")),
        "agent_reason_code": _safe_token(agent.get("reason_code")),
        "agent_mode": _safe_token(agent.get("mode")),
        "agent_model_called": _to_bool(agent.get("model_called")),
        "agent_candidate_plan_present": _to_bool(agent.get("candidate_plan_present")),
        "agent_plan_tool_call_count": _agent_plan_tool_call_count(agent),
        "agent_plan_tool_names": _agent_plan_tool_names(agent),
        "agent_used_for_response": _to_bool(agent.get("used_for_response")),
        "agent_product_response_changed": _to_bool(agent.get("product_response_changed")),
        "agent_tool_execution_status": _safe_token(agent.get("tool_execution_status")),
        "agent_tool_call_event_count": _to_int(agent.get("tool_call_event_count")),
    }
    base_record.update(_evaluate_expectations(case, base_record))
    return _finalize_record(
        base_record,
        raw_markers=raw_markers,
        source_projection={
            "event": event,
            "context": context,
            "dialogue": dialogue_observation,
            "lane": lane,
        },
    )


def smoke_record_violations(record: Mapping[str, Any], *, product_strict: bool = True) -> tuple[str, ...]:
    violations: list[str] = []
    if _to_bool(record.get("raw_marker_leaks")):
        violations.append("raw_marker_leaks")
    if _to_int(record.get("payload_objects_retained")) > 0:
        violations.append("payload_objects_retained")
    if _to_bool(record.get("forbidden_endpoint_used")):
        violations.append("forbidden_endpoint_used")
    if _to_bool(record.get("agent_used_for_response")):
        violations.append("agent_used_for_response")
    if _to_bool(record.get("agent_product_response_changed")):
        violations.append("agent_product_response_changed")
    if _to_int(record.get("agent_tool_call_event_count")) > 0:
        violations.append("agent_tool_call_event_count")
    tool_execution = _safe_token(record.get("agent_tool_execution_status"))
    if tool_execution and tool_execution != "not_executed":
        violations.append("agent_tool_execution_status")
    if product_strict:
        if _safe_token(record.get("agent_expectation_status")) == "failed":
            violations.append("agent_expectation_failed")
        product_status = _safe_token(record.get("product_expectation_status"))
        if product_status == "failed":
            violations.append("product_expectation_failed")
        elif product_status == "partial_required_attention":
            violations.append("product_expectation_partial_required_attention")
    return tuple(violations)


def smoke_exit_code(
    records: Sequence[Mapping[str, Any]],
    *,
    strict: bool = True,
    product_strict: bool = True,
) -> int:
    if not strict:
        return EXIT_OK
    for record in records:
        if smoke_record_violations(record, product_strict=product_strict):
            return EXIT_VALIDATION_FAILURE
    return EXIT_OK


def _evaluate_expectations(
    case: BiblioLibrarianProductSmokeCase,
    record: Mapping[str, Any],
) -> dict[str, str]:
    runtime_status, runtime_reason = _evaluate_runtime_expectation(case, record)
    agent_status, agent_reason = _evaluate_agent_expectation(record)
    product_status, product_reason = _combine_expectations(
        case,
        record,
        runtime_status=runtime_status,
        runtime_reason=runtime_reason,
        agent_status=agent_status,
        agent_reason=agent_reason,
    )
    return {
        "runtime_expectation_status": runtime_status,
        "runtime_expectation_reason_code": runtime_reason,
        "agent_expectation_status": agent_status,
        "agent_expectation_reason_code": agent_reason,
        "product_expectation_status": product_status,
        "product_expectation_reason_code": product_reason,
    }


def _evaluate_runtime_expectation(
    case: BiblioLibrarianProductSmokeCase,
    record: Mapping[str, Any],
) -> tuple[str, str]:
    kind = case.case_kind
    status = _safe_token(record.get("status"))
    query_kind = _safe_token(record.get("query_kind"))
    endpoint_count = _to_int(record.get("endpoint_count"))
    context_call_count = _to_int(record.get("context_call_count"))
    candidate_count = _to_int(record.get("candidate_count"))
    passage_count = _to_int(record.get("passage_count"))
    lane_injected = _to_bool(record.get("lane_injected"))
    total_count = _to_int(record.get("total_count"))
    displayed_count = _to_int(record.get("displayed_count"))
    truncated = _to_bool(record.get("truncated"))
    anchor_present = bool(record.get("doc_id_shorts") or record.get("hashes"))

    if kind == "catalog_full":
        if query_kind == "list_catalog" and status == "listed" and displayed_count > 0:
            if total_count and total_count <= 100 and displayed_count == total_count and not truncated:
                return "met", "catalogue_list_complete"
            if total_count and total_count > 100 and truncated:
                return "met", "catalogue_list_paginated_explicit"
            return "partial", "catalogue_listed_without_complete_total"
        return "failed", "catalogue_list_not_reached"
    if kind in {"range_extract", "state_seed"}:
        if passage_count > 0 and lane_injected:
            return "met", "passage_lane_available"
        if endpoint_count > 0:
            return "partial", "catalogue_consulted_without_passage_lane"
        return "failed", "passage_request_not_consulted"
    if kind in {"theme_search", "external_theme"}:
        if context_call_count > 0 and (candidate_count > 0 or passage_count > 0 or lane_injected):
            return "met", "theme_search_reached_context"
        if endpoint_count > 0:
            if status == "not_found" and candidate_count == 0 and context_call_count == 0:
                return "failed", "theme_search_not_found_without_context"
            return "partial", "theme_search_consulted_without_context"
        return "failed", "theme_search_not_reached"
    if kind == "work_lookup":
        if endpoint_count > 0:
            return "met", "work_lookup_consulted"
        return "failed", "work_lookup_not_reached"
    if kind == "toc":
        endpoints = set(_safe_token_list(record.get("endpoint_kinds")))
        if "chapters" in endpoints or status == "toc_listed":
            return "met", "toc_listed"
        if endpoint_count > 0:
            return "partial", "toc_planned_or_clarified"
        return "failed", "toc_not_reached"
    if kind == "state_followup":
        if query_kind == "state_followup" and (lane_injected or anchor_present):
            return "met", "state_followup_handled"
        return "failed", "state_followup_not_reached"
    if kind == "origin_check":
        if query_kind == "state_followup" and anchor_present:
            return "met", "origin_anchor_available"
        if query_kind == "state_followup" or lane_injected:
            return "partial", "origin_clarification_without_anchor"
        return "failed", "origin_check_not_reached"
    return "partial", "expectation_not_classified"


def _evaluate_agent_expectation(record: Mapping[str, Any]) -> tuple[str, str]:
    mode = _safe_token(record.get("agent_mode"))
    if mode == agent_contract.MODE_OFF:
        return "met", "agent_off_explicit"
    if mode not in {agent_contract.MODE_SHADOW, agent_contract.MODE_CANDIDATE}:
        return "failed", "agent_mode_not_nominal"
    if not _to_bool(record.get("agent_present")):
        return "failed", "agent_observation_missing"
    if not _to_bool(record.get("agent_model_called")):
        reason = _safe_token(record.get("agent_reason_code")) or "agent_model_not_called"
        return "failed", reason
    if not _to_bool(record.get("agent_candidate_plan_present")):
        reason = _safe_token(record.get("agent_reason_code")) or "agent_candidate_plan_missing"
        return "failed", reason
    return "met", "agent_candidate_plan_observed"


def _combine_expectations(
    case: BiblioLibrarianProductSmokeCase,
    record: Mapping[str, Any],
    *,
    runtime_status: str,
    runtime_reason: str,
    agent_status: str,
    agent_reason: str,
) -> tuple[str, str]:
    if runtime_status == "met":
        return "met", runtime_reason
    agent_plan_satisfies = _agent_plan_can_satisfy(record, agent_status=agent_status)
    if case.case_kind == "external_theme" and runtime_reason == "theme_search_not_found_without_context":
        if agent_plan_satisfies:
            return "partial_required_attention", "external_theme_runtime_not_found_agent_plan_only"
        return "failed", runtime_reason
    if case.case_kind == "origin_check":
        if runtime_status == "partial":
            return "partial_required_attention", runtime_reason
        return runtime_status, runtime_reason
    if agent_plan_satisfies and case.case_kind in {
        "work_lookup",
        "toc",
        "state_followup",
        "theme_search",
        "range_extract",
        "state_seed",
    }:
        return "met", agent_reason
    if runtime_status == "partial" or agent_status == "partial":
        return "partial_required_attention", runtime_reason if runtime_status == "partial" else agent_reason
    if agent_status == "failed" and runtime_status == "failed":
        return "failed", runtime_reason
    return runtime_status, runtime_reason


def _agent_plan_can_satisfy(record: Mapping[str, Any], *, agent_status: str) -> bool:
    mode = _safe_token(record.get("agent_mode"))
    return agent_status == "met" and mode in {agent_contract.MODE_SHADOW, agent_contract.MODE_CANDIDATE}


def _finalize_record(
    record: Mapping[str, Any],
    *,
    raw_markers: Sequence[str],
    source_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sanitized = {key: record[key] for key in sorted(_OUTPUT_KEYS) if key in record}
    source_leaks = _contains_raw_marker(source_projection or {}, raw_markers)
    record_leaks = _contains_raw_marker(record, raw_markers) or _contains_raw_marker(sanitized, raw_markers)
    sanitized["raw_marker_leaks"] = bool(source_leaks or record_leaks)
    return sanitized


def _recent_turn_observation(
    case: BiblioLibrarianProductSmokeCase,
    result: BiblioChatResult,
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "case_kind": case.case_kind,
        "status": _safe_token((result.observability_payload or {}).get("status")),
        "reason_code": _safe_token(result.reason_code),
        "query_kind": _safe_token(result.query_kind),
        "state_present": result.biblio_state.present if result.biblio_state is not None else False,
    }


def _config_for_agent_mode(agent_mode: str, *, config_module: Any = None) -> Any:
    normalized = _safe_token(agent_mode) or DEFAULT_AGENT_MODE
    if normalized == _AGENT_MODE_CONFIG:
        return config_module
    if normalized not in set(_ALLOWED_AGENT_MODES):
        normalized = DEFAULT_AGENT_MODE
    return _AgentModeConfig(mode=normalized, base_config=config_module)


def _agent_plan_tool_call_count(agent: Mapping[str, Any]) -> int:
    nested_agent = _mapping(agent.get("agent"))
    validation = _mapping(nested_agent.get("validation"))
    plan = _mapping(validation.get("plan"))
    return _to_int(validation.get("tool_call_count")) or _to_int(plan.get("tool_call_count"))


def _agent_plan_tool_names(agent: Mapping[str, Any]) -> list[str]:
    nested_agent = _mapping(agent.get("agent"))
    validation = _mapping(nested_agent.get("validation"))
    plan = _mapping(validation.get("plan"))
    names = _safe_token_list(validation.get("tool_names"))
    return names or _safe_token_list(plan.get("tool_names"))


def _lane_observability(value: Any) -> dict[str, Any]:
    to_observability = getattr(value, "to_observability", None)
    if callable(to_observability):
        observed = to_observability()
        if isinstance(observed, Mapping):
            return dict(observed)
    return {}


def _endpoint_kinds(
    client: Mapping[str, Any],
    context: Mapping[str, Any],
    passage_search: Mapping[str, Any],
) -> list[str]:
    kinds: set[str] = set()
    for item in _sequence(client.get("items")):
        if isinstance(item, Mapping):
            kind = _safe_token(item.get("endpoint_kind"))
            if kind:
                kinds.add(kind)
    for item in _sequence(context.get("endpoint_kinds")):
        kind = _safe_token(item)
        if kind:
            kinds.add(kind)
    for item in _sequence(passage_search.get("endpoint_kinds")):
        kind = _safe_token(item)
        if kind:
            kinds.add(kind)
    return sorted(kinds)


def _doc_id_shorts(
    lane: Mapping[str, Any],
    context: Mapping[str, Any],
    passage_search: Mapping[str, Any],
) -> list[str]:
    values: list[str] = []
    for source in (
        lane.get("doc_id_shorts"),
        passage_search.get("doc_id_shorts"),
        context.get("doc_id_short"),
        _mapping(context.get("candidate_search")).get("doc_id_shorts"),
    ):
        if isinstance(source, str):
            values.append(source)
        else:
            values.extend(_safe_token(item) for item in _sequence(source) if item)
    return list(dict.fromkeys(item for item in values if item))[:12]


def _hashes(
    lane: Mapping[str, Any],
    context: Mapping[str, Any],
    passage_search: Mapping[str, Any],
) -> list[str]:
    values: list[str] = []
    for source in (lane.get("hashes"), passage_search.get("hashes"), context.get("passage_hash")):
        if isinstance(source, str):
            values.append(source)
        else:
            values.extend(_safe_token(item) for item in _sequence(source) if item)
    return list(dict.fromkeys(item for item in values if item))[:12]


def _payload_objects_retained(result: BiblioChatResult) -> int:
    total = 0
    context = result.context_result
    if context is None:
        return total
    candidate_result = context.candidate_result
    if candidate_result is not None:
        total += sum(1 for item in candidate_result.endpoint_observations if hasattr(item, "payload"))
    total += sum(1 for item in context.context_observations if hasattr(item, "payload"))
    return total


def _contains_raw_marker(value: Any, raw_markers: Sequence[str]) -> bool:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).casefold()
    return any(str(marker or "").casefold() in encoded for marker in raw_markers if str(marker or "").strip())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return value
    return ()


def _safe_token(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _safe_token_list(value: Any) -> list[str]:
    return [_safe_token(item) for item in _sequence(value) if _safe_token(item)][:24]


def _to_int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def _to_bool(value: Any) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run content-free Biblio librarian product smokes.")
    parser.add_argument("--jsonl", action="store_true", help="Print one JSON object per line.")
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Print records even if guardrails fail and exit 0.",
    )
    parser.add_argument(
        "--no-product-strict",
        action="store_true",
        help="Do not fail the process on failed product expectations.",
    )
    parser.add_argument(
        "--agent-mode",
        choices=_ALLOWED_AGENT_MODES,
        default=DEFAULT_AGENT_MODE,
        help="Agent comparison mode for the smoke. Default asks the model for a candidate plan.",
    )
    args = parser.parse_args(argv)
    records = run_smokes(agent_mode=args.agent_mode)
    if args.jsonl:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True))
    return smoke_exit_code(records, strict=not args.no_strict, product_strict=not args.no_product_strict)


if __name__ == "__main__":
    raise SystemExit(main())
