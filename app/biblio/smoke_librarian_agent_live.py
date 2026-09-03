"""Content-free product smokes for the active Biblio librarian agent.

This runner validates the live product envelope with the agent-first controller
under strict GET-only guardrails.  It records compact operator truth about
model plans, bounded fallback repairs, executed tools and product outcomes.
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
from . import librarian_product_methods as product_methods
from . import smoke_librarian_agent_expectations as expectations
from .librarian_dialogue_planner import BiblioDialoguePlanningResult, plan_biblio_dialogue


@dataclass(frozen=True)
class BiblioLibrarianProductSmokeCase:
    case_id: str
    case_kind: str
    message: str
    conversation_key: str = ""
    expected_document_id: str = ""


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

DEFAULT_AGENT_MODE = agent_contract.MODE_ACTIVE
_AGENT_MODE_CONFIG = "config"
_ALLOWED_AGENT_MODES = (
    agent_contract.MODE_OFF,
    _AGENT_MODE_CONFIG,
    agent_contract.MODE_ACTIVE,
    agent_contract.MODE_SHADOW,
    agent_contract.MODE_CANDIDATE,
)
_OUTPUT_KEYS = {
    "agent_plan_answer_mode",
    "agent_plan_case_id",
    "agent_plan_product_method",
    "agent_candidate_plan_present",
    "agent_mode",
    "agent_model_called",
    "agent_model_effective",
    "agent_provider_attempt_count",
    "agent_present",
    "agent_product_response_changed",
    "agent_reason_code",
    "agent_expectation_reason_code",
    "agent_expectation_status",
    "agent_execution_scope",
    "agent_executed_tool_names",
    "agent_loop_reason_code",
    "agent_loop_status",
    "agent_plan_tool_call_count",
    "agent_plan_tool_names",
    "agent_status",
    "agent_tool_call_event_count",
    "agent_tool_execution_status",
    "agent_used_for_response",
    "candidate_count",
    "answer_content_kind",
    "answer_incomplete_pages",
    "answer_page_end",
    "answer_page_start",
    "answer_page_truncated",
    "answer_range_complete",
    "answer_range_state",
    "answer_requested_page_end",
    "answer_status",
    "answer_next_anchor_page_no",
    "answer_next_anchor_present",
    "b2_expected_document_id_present",
    "b2_expected_document_id_short",
    "b2_precondition_reason_code",
    "b2_precondition_status",
    "b2_previous_case_kind",
    "b2_previous_product_expectation_status",
    "b2_state_after_expected_document_match",
    "b2_state_after_last_result_expected_document_match",
    "b2_state_before_expected_document_match",
    "b2_state_before_last_result_expected_document_match",
    "b2_state_before_matches_previous_after",
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
    "final_lock_ok",
    "final_lock_reason_code",
    "hashes",
    "lane_chars",
    "lane_injected",
    "lengths",
    "passage_count",
    "payload_objects_retained",
    "product_case_id",
    "product_expectation_reason_code",
    "product_expectation_status",
    "product_method_effective",
    "product_truth",
    "query_kind",
    "raw_marker_leaks",
    "render_exact_text_rendered",
    "render_section_complete_claim",
    "render_section_segment_claim",
    "reason_code",
    "runtime_expectation_reason_code",
    "runtime_expectation_status",
    "selected_count",
    "status",
    "total_count",
    "displayed_count",
    "state_present_after",
    "state_incomplete_page_no",
    "state_interval_state",
    "state_next_page_no",
    "state_before_document_id_short",
    "state_before_last_result_document_id_short",
    "state_before_page_no",
    "state_before_para_no",
    "state_before_paragraph_id",
    "state_before_passage_hash",
    "state_after_document_id_short",
    "state_after_last_result_document_id_short",
    "state_after_page_no",
    "state_after_para_no",
    "state_after_paragraph_id",
    "state_after_passage_hash",
    "truncated",
} | expectations.EXPECTATION_OUTPUT_KEYS


class _AgentModeConfig:
    def __init__(self, *, mode: str, base_config: Any = None) -> None:
        self.BIBLIO_LIBRARIAN_AGENT_MODE = mode
        self._runtime_settings_mode_override = True
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
    on_record: Callable[[Mapping[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    states: dict[str, BiblioConversationState] = {}
    recent_dialogues: dict[str, list[dict[str, Any]]] = {}
    previous_records: dict[str, dict[str, Any]] = {}
    previous_states_after: dict[str, BiblioConversationState] = {}
    agent_config = _config_for_agent_mode(agent_mode, config_module=config_module)
    for case in cases:
        conversation_id = case.conversation_key or case.case_id
        state = states.get(conversation_id, BiblioConversationState.empty(conversation_id=conversation_id))
        previous_record = previous_records.get(conversation_id)
        previous_state_after = previous_states_after.get(conversation_id)
        precondition_status, precondition_reason = _b2_interturn_precondition(
            case,
            state=state,
            previous_record=previous_record,
            previous_state_after=previous_state_after,
        )
        if precondition_status == "failed":
            record = _b2_precondition_failure_record(
                case,
                state=state,
                previous_record=previous_record,
                previous_state_after=previous_state_after,
                reason_code=precondition_reason,
                agent_mode=agent_mode,
                raw_markers=raw_markers,
            )
            records.append(record)
            previous_records[conversation_id] = record
            if on_record is not None:
                on_record(record)
            continue
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
        record = _record_for_result(
            case,
            result,
            dialogue,
            state_before=state,
            previous_record=previous_record,
            previous_state_after=previous_state_after,
            b2_precondition_status=precondition_status,
            b2_precondition_reason_code=precondition_reason,
            raw_markers=raw_markers,
        )
        records.append(record)
        previous_records[conversation_id] = record
        if result.biblio_state is not None:
            previous_states_after[conversation_id] = result.biblio_state
        if on_record is not None:
            on_record(record)
    return records


def _b2_interturn_precondition(
    case: BiblioLibrarianProductSmokeCase,
    *,
    state: BiblioConversationState,
    previous_record: Mapping[str, Any] | None,
    previous_state_after: BiblioConversationState | None,
) -> tuple[str, str]:
    kind = _safe_token(case.case_kind)
    if kind not in {"document_switch", "document_switch_continue"}:
        return "not_applicable", ""
    expected_document_id = _canonical_document_id(getattr(case, "expected_document_id", ""))
    if not expected_document_id:
        return "failed", "b2_expected_document_id_missing"
    previous = _mapping(previous_record)
    if not _states_equal(state, previous_state_after):
        return "failed", "b2_previous_state_mismatch"
    if kind == "document_switch":
        if (
            _safe_token(previous.get("case_kind")) != "state_seed"
            or _safe_token(previous.get("product_expectation_status")) != "met"
            or not _to_bool(previous.get("b2_expected_document_id_present"))
            or not _to_bool(previous.get("b2_state_after_expected_document_match"))
        ):
            return "failed", "b2_source_not_met"
        if not _state_has_position(state):
            return "failed", "b2_source_anchor_missing"
        return "met", "b2_source_anchor_verified"
    if (
        _safe_token(previous.get("case_kind")) != "document_switch"
        or _safe_token(previous.get("product_expectation_status")) != "met"
    ):
        return "failed", "b2_switch_not_met"
    current_document_id, last_result_document_id = _canonical_state_document_ids(state)
    if current_document_id != expected_document_id or last_result_document_id != expected_document_id:
        return "failed", "b2_switch_target_mismatch"
    if _state_has_position(state):
        return "failed", "b2_switch_position_present"
    return "met", "b2_switch_state_verified"


def _b2_precondition_failure_record(
    case: BiblioLibrarianProductSmokeCase,
    *,
    state: BiblioConversationState,
    previous_record: Mapping[str, Any] | None,
    previous_state_after: BiblioConversationState | None,
    reason_code: str,
    agent_mode: str,
    raw_markers: Sequence[str],
) -> dict[str, Any]:
    state_coordinates = _state_coordinates(state)
    base_record: dict[str, Any] = {
        "case_id": case.case_id,
        "case_kind": case.case_kind,
        "status": "precondition_failed",
        "reason_code": reason_code,
        "query_kind": "not_run",
        "client_count": 0,
        "endpoint_count": 0,
        "endpoint_kinds": [],
        "lane_injected": False,
        "agent_mode": _safe_token(agent_mode),
        "agent_present": False,
        "agent_model_called": False,
        "agent_candidate_plan_present": False,
        "agent_plan_tool_names": [],
        "agent_executed_tool_names": [],
        "agent_tool_execution_status": "not_executed",
        "agent_tool_call_event_count": 0,
        **{f"state_before_{key}": value for key, value in state_coordinates.items()},
        **{f"state_after_{key}": value for key, value in state_coordinates.items()},
        **_b2_sequence_projection(
            case,
            state_before=state,
            state_after=state,
            previous_record=previous_record,
            previous_state_after=previous_state_after,
            precondition_status="failed",
            precondition_reason_code=reason_code,
        ),
    }
    base_record.update(_evaluate_expectations(case, base_record))
    return _finalize_record(base_record, raw_markers=raw_markers)


def _record_for_result(
    case: BiblioLibrarianProductSmokeCase,
    result: BiblioChatResult,
    dialogue: BiblioDialoguePlanningResult,
    *,
    state_before: BiblioConversationState,
    previous_record: Mapping[str, Any] | None = None,
    previous_state_after: BiblioConversationState | None = None,
    b2_precondition_status: str = "",
    b2_precondition_reason_code: str = "",
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
    nested_agent = _mapping(agent.get("agent"))
    agent_model = _mapping(nested_agent.get("model"))
    agent_validation_plan = _agent_validation_plan(result)
    answer_observation = _answer_observation(result)
    extraction = _mapping(answer_observation.get("extraction"))
    rendered_observation = _rendered_observation(result)
    rendered_content = str(getattr(result.rendered_answer, "content", "") or "")
    final_lock_observation = _final_lock_observation(result)
    state_interval = _state_interval(result)
    before_state = _state_coordinates(state_before)
    after_state = _state_coordinates(result.biblio_state)
    b2_projection = _b2_sequence_projection(
        case,
        state_before=state_before,
        state_after=result.biblio_state,
        previous_record=previous_record,
        previous_state_after=previous_state_after,
        precondition_status=b2_precondition_status,
        precondition_reason_code=b2_precondition_reason_code,
    )
    dialogue_intent = _mapping(dialogue_observation.get("intent"))
    dialogue_plan = _mapping(dialogue_observation.get("plan"))
    endpoint_kinds = _endpoint_kinds(client, context, passage_search)
    passage_count = (
        _to_int(lane.get("passage_count"))
        or _to_int(passage_search.get("passage_count"))
        or _to_int(counts.get("passage_count"))
    )
    client_context_count = _endpoint_kind_count(client, "context")
    client_search_count = _endpoint_kind_count(client, "search")
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
        "candidate_count": _to_int(passage_search.get("candidate_count"))
        or _to_int(context.get("candidate_count"))
        or client_search_count,
        "context_call_count": _to_int(passage_search.get("context_call_count"))
        or _to_int(context.get("context_call_count"))
        or client_context_count,
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
        "agent_model_effective": _safe_token(agent_model.get("model_effective")),
        "agent_provider_attempt_count": _to_int(agent_model.get("attempt_count")),
        "agent_candidate_plan_present": _to_bool(agent.get("candidate_plan_present")),
        "agent_plan_tool_call_count": _agent_plan_tool_call_count(agent),
        "agent_plan_tool_names": _agent_plan_tool_names(agent),
        "agent_plan_case_id": product_methods.normalize_case_id(agent_validation_plan.get("case_id")),
        "agent_plan_product_method": str(agent_validation_plan.get("product_method") or "").strip(),
        "agent_plan_answer_mode": _safe_token(agent_validation_plan.get("answer_mode")),
        "product_case_id": product_methods.normalize_case_id(event.get("product_case_id")),
        "product_method_effective": _safe_token(event.get("product_method")),
        "product_truth": _safe_token(event.get("product_truth")),
        "agent_executed_tool_names": _agent_executed_tool_names(agent),
        "agent_used_for_response": _to_bool(agent.get("used_for_response")),
        "agent_product_response_changed": _to_bool(agent.get("product_response_changed")),
        "agent_tool_execution_status": _safe_token(agent.get("tool_execution_status")),
        "agent_tool_call_event_count": _to_int(agent.get("tool_call_event_count")),
        "agent_execution_scope": _safe_token(agent.get("execution_scope")),
        "agent_loop_status": _safe_token(_mapping(agent.get("tool_loop")).get("status")),
        "agent_loop_reason_code": _safe_token(_mapping(agent.get("tool_loop")).get("reason_code")),
        "answer_status": _safe_token(answer_observation.get("status")),
        "answer_content_kind": _safe_token(extraction.get("content_kind")),
        "answer_range_state": _safe_token(extraction.get("range_state")),
        "answer_range_complete": _to_bool(extraction.get("range_complete")),
        "answer_page_truncated": _to_bool(extraction.get("page_truncated")),
        "answer_page_start": _to_int(extraction.get("page_start")),
        "answer_page_end": _to_int(extraction.get("page_end")),
        "answer_requested_page_end": _to_int(extraction.get("requested_page_end")),
        "answer_incomplete_pages": [
            _to_int(page) for page in _sequence(extraction.get("incomplete_pages")) if _to_int(page)
        ],
        "answer_next_anchor_present": _to_bool(extraction.get("next_anchor_present")),
        "answer_next_anchor_page_no": _to_int(extraction.get("next_anchor_page_no")),
        "render_exact_text_rendered": _to_bool(rendered_observation.get("exact_text_rendered")),
        "render_section_complete_claim": "Section complete." in rendered_content,
        "render_section_segment_claim": "Segment de section." in rendered_content,
        "final_lock_ok": _safe_token(final_lock_observation.get("status")) == "authorized",
        "final_lock_reason_code": _safe_token(final_lock_observation.get("reason_code")),
        "state_present_after": bool(result.biblio_state and result.biblio_state.present),
        "state_interval_state": _safe_token(state_interval.get("state")),
        "state_incomplete_page_no": _to_int(state_interval.get("incomplete_page_no")),
        "state_next_page_no": _to_int(state_interval.get("next_page_no")),
        **{f"state_before_{key}": value for key, value in before_state.items()},
        **{f"state_after_{key}": value for key, value in after_state.items()},
        **b2_projection,
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


def smoke_record_violations(
    record: Mapping[str, Any],
    *,
    product_strict: bool = True,
    agent_strict: bool = True,
) -> tuple[str, ...]:
    return expectations.smoke_record_violations(
        record,
        product_strict=product_strict,
        agent_strict=agent_strict,
    )


def smoke_exit_code(
    records: Sequence[Mapping[str, Any]],
    *,
    strict: bool = True,
    product_strict: bool = True,
    agent_strict: bool = True,
) -> int:
    if not strict:
        return EXIT_OK
    for record in records:
        if smoke_record_violations(record, product_strict=product_strict, agent_strict=agent_strict):
            return EXIT_VALIDATION_FAILURE
    return EXIT_OK


def _evaluate_expectations(
    case: BiblioLibrarianProductSmokeCase,
    record: Mapping[str, Any],
) -> dict[str, str]:
    return expectations.evaluate_expectations(case.case_kind, record)


def _finalize_record(
    record: Mapping[str, Any],
    *,
    raw_markers: Sequence[str],
    source_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sanitized = {key: record[key] for key in sorted(_OUTPUT_KEYS) if key in record}
    record_leaks = _contains_raw_marker(record, raw_markers) or _contains_raw_marker(sanitized, raw_markers)
    sanitized["raw_marker_leaks"] = bool(record_leaks)
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


def _agent_executed_tool_names(agent: Mapping[str, Any]) -> list[str]:
    loop = _mapping(agent.get("tool_loop"))
    return _safe_token_list(loop.get("tool_names"))


def _agent_validation_plan(result: BiblioChatResult) -> Mapping[str, Any]:
    comparison = getattr(result, "librarian_agent_result", None)
    agent_result = getattr(comparison, "agent_result", None)
    validation = getattr(agent_result, "validation_observation", None)
    if isinstance(validation, Mapping):
        plan = validation.get("plan")
        if isinstance(plan, Mapping):
            return plan
    return {}


def _answer_observation(result: BiblioChatResult) -> Mapping[str, Any]:
    answer = result.answer_object
    observed = getattr(answer, "to_observability", lambda: {})()
    return observed if isinstance(observed, Mapping) else {}


def _rendered_observation(result: BiblioChatResult) -> Mapping[str, Any]:
    rendered = result.rendered_answer
    observed = getattr(rendered, "to_observability", lambda: {})()
    return observed if isinstance(observed, Mapping) else {}


def _final_lock_observation(result: BiblioChatResult) -> Mapping[str, Any]:
    lock = result.final_response_lock
    observed = getattr(lock, "to_observability", lambda: {})()
    return observed if isinstance(observed, Mapping) else {}


def _state_interval(result: BiblioChatResult) -> Mapping[str, Any]:
    state = result.biblio_state
    if state is None:
        return {}
    last_result = getattr(state, "last_result", None)
    if not isinstance(last_result, Mapping):
        return {}
    return _mapping(last_result.get("interval_hint"))


def _state_coordinates(state: Any) -> dict[str, Any]:
    if state is None:
        return {}
    current_document = _mapping(getattr(state, "current_document", None))
    last_result = _mapping(getattr(state, "last_result", None))
    return {
        "document_id_short": _safe_token(current_document.get("doc_id_short")),
        "last_result_document_id_short": _safe_token(last_result.get("doc_id_short")),
        "page_no": _to_int(getattr(state, "page_no", None)),
        "para_no": _to_int(getattr(state, "para_no", None)),
        "paragraph_id": _to_int(getattr(state, "paragraph_id", None)),
        "passage_hash": _safe_token(getattr(state, "last_passage_hash", "")),
    }


def _b2_sequence_projection(
    case: BiblioLibrarianProductSmokeCase,
    *,
    state_before: Any,
    state_after: Any,
    previous_record: Mapping[str, Any] | None,
    previous_state_after: Any,
    precondition_status: str,
    precondition_reason_code: str,
) -> dict[str, Any]:
    expected_document_id = _canonical_document_id(getattr(case, "expected_document_id", ""))
    if _safe_token(case.case_kind) not in {"document_switch", "document_switch_continue"} and not expected_document_id:
        return {}
    before_document_id, before_result_document_id = _canonical_state_document_ids(state_before)
    after_document_id, after_result_document_id = _canonical_state_document_ids(state_after)
    previous = _mapping(previous_record)
    return {
        "b2_expected_document_id_present": bool(expected_document_id),
        "b2_expected_document_id_short": expected_document_id[:8],
        "b2_precondition_status": _safe_token(precondition_status),
        "b2_precondition_reason_code": _safe_token(precondition_reason_code),
        "b2_previous_case_kind": _safe_token(previous.get("case_kind")),
        "b2_previous_product_expectation_status": _safe_token(previous.get("product_expectation_status")),
        "b2_state_before_matches_previous_after": _states_equal(state_before, previous_state_after),
        "b2_state_before_expected_document_match": bool(
            expected_document_id and before_document_id == expected_document_id
        ),
        "b2_state_before_last_result_expected_document_match": bool(
            expected_document_id and before_result_document_id == expected_document_id
        ),
        "b2_state_after_expected_document_match": bool(
            expected_document_id and after_document_id == expected_document_id
        ),
        "b2_state_after_last_result_expected_document_match": bool(
            expected_document_id and after_result_document_id == expected_document_id
        ),
    }


def _canonical_state_document_ids(state: Any) -> tuple[str, str]:
    if state is None:
        return "", ""
    current_document = _mapping(getattr(state, "current_document", None))
    last_result = _mapping(getattr(state, "last_result", None))
    return (
        _canonical_document_id(current_document.get("document_id")),
        _canonical_document_id(last_result.get("document_id")),
    )


def _canonical_document_id(value: Any) -> str:
    return str(value or "").strip()


def _state_has_position(state: Any) -> bool:
    if state is None:
        return False
    last_result = _mapping(getattr(state, "last_result", None))
    return bool(
        _to_int(getattr(state, "page_no", None))
        or _to_int(getattr(state, "para_no", None))
        or _to_int(getattr(state, "paragraph_id", None))
        or _safe_token(getattr(state, "last_passage_hash", ""))
        or _to_int(last_result.get("page_no"))
        or _to_int(last_result.get("para_no"))
        or _to_int(last_result.get("paragraph_id"))
        or _safe_token(last_result.get("passage_hash"))
    )


def _states_equal(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    left_to_dict = getattr(left, "to_dict", None)
    right_to_dict = getattr(right, "to_dict", None)
    if callable(left_to_dict) and callable(right_to_dict):
        return left_to_dict() == right_to_dict()
    return left == right


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


def _endpoint_kind_count(client: Mapping[str, Any], endpoint_kind: str) -> int:
    expected = _safe_token(endpoint_kind)
    return sum(
        1
        for item in _sequence(client.get("items"))
        if isinstance(item, Mapping) and _safe_token(item.get("endpoint_kind")) == expected
    )


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
        "--no-agent-strict",
        action="store_true",
        help="Debug only: do not fail on failed agent expectations.",
    )
    parser.add_argument(
        "--agent-mode",
        choices=_ALLOWED_AGENT_MODES,
        default=DEFAULT_AGENT_MODE,
        help="Agent comparison mode for the smoke. Default requires an active model-validated plan.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Run only the given smoke case id. Repeat for several cases.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Run only the first N selected cases. Debug/segmentation only; not a full-smoke proof.",
    )
    args = parser.parse_args(argv)
    selected_cases = _select_cases(DEFAULT_SMOKE_CASES, case_ids=args.case_id, max_cases=args.max_cases)
    emitted: list[dict[str, Any]] = []

    def emit_record(record: Mapping[str, Any]) -> None:
        if args.jsonl:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True), flush=True)
        emitted.append(dict(record))

    records = run_smokes(agent_mode=args.agent_mode, cases=selected_cases, on_record=emit_record)
    if args.jsonl:
        if records != emitted:
            for record in records[len(emitted) :]:
                print(json.dumps(record, ensure_ascii=False, sort_keys=True), flush=True)
    else:
        print(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True))
    return smoke_exit_code(
        records,
        strict=not args.no_strict,
        product_strict=not args.no_product_strict,
        agent_strict=not args.no_agent_strict,
    )


def _select_cases(
    cases: Sequence[BiblioLibrarianProductSmokeCase],
    *,
    case_ids: Sequence[str],
    max_cases: int = 0,
) -> tuple[BiblioLibrarianProductSmokeCase, ...]:
    selected = tuple(cases)
    wanted = {str(case_id or "").strip().upper() for case_id in case_ids if str(case_id or "").strip()}
    if wanted:
        selected = tuple(case for case in selected if case.case_id.upper() in wanted)
    if max_cases > 0:
        selected = selected[:max_cases]
    return selected


if __name__ == "__main__":
    raise SystemExit(main())
