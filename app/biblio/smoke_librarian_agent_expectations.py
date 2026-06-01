"""Expectation checks for Biblio librarian agent live smokes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import librarian_agent_contract as agent_contract


EXPECTATION_OUTPUT_KEYS = frozenset(
    {
        "agent_expectation_reason_code",
        "agent_expectation_status",
        "product_expectation_reason_code",
        "product_expectation_status",
        "runtime_expectation_reason_code",
        "runtime_expectation_status",
    }
)


def evaluate_expectations(case_kind: str, record: Mapping[str, Any]) -> dict[str, str]:
    runtime_status, runtime_reason = _evaluate_runtime_expectation(case_kind, record)
    agent_status, agent_reason = _evaluate_agent_expectation(record)
    product_status, product_reason = _combine_expectations(
        case_kind,
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


def smoke_record_violations(
    record: Mapping[str, Any],
    *,
    product_strict: bool = True,
    agent_strict: bool = True,
) -> tuple[str, ...]:
    violations: list[str] = []
    if _to_bool(record.get("raw_marker_leaks")):
        violations.append("raw_marker_leaks")
    if _to_int(record.get("payload_objects_retained")) > 0:
        violations.append("payload_objects_retained")
    if _to_bool(record.get("forbidden_endpoint_used")):
        violations.append("forbidden_endpoint_used")
    agent_first_allowed = _agent_first_execution_allowed(record)
    if _to_bool(record.get("agent_used_for_response")) and not agent_first_allowed:
        violations.append("agent_used_for_response")
    if _to_bool(record.get("agent_product_response_changed")) and not agent_first_allowed:
        violations.append("agent_product_response_changed")
    if _to_int(record.get("agent_tool_call_event_count")) > 0 and not agent_first_allowed:
        violations.append("agent_tool_call_event_count")
    tool_execution = _safe_token(record.get("agent_tool_execution_status"))
    if tool_execution and tool_execution != "not_executed" and not agent_first_allowed:
        violations.append("agent_tool_execution_status")
    if agent_strict and _safe_token(record.get("agent_expectation_status")) == "failed":
        violations.append("agent_expectation_failed")
    if product_strict:
        product_status = _safe_token(record.get("product_expectation_status"))
        if product_status == "failed":
            violations.append("product_expectation_failed")
        elif product_status == "partial_required_attention":
            violations.append("product_expectation_partial_required_attention")
    return tuple(violations)


def _evaluate_runtime_expectation(case_kind: str, record: Mapping[str, Any]) -> tuple[str, str]:
    kind = _safe_token(case_kind)
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
        if displayed_count > 0 and (
            (query_kind == "list_catalog" and status == "listed")
            or (query_kind == "agent_first" and status == "agent_first_executed")
        ):
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
        if query_kind in {"state_followup", "agent_first"} and (lane_injected or anchor_present):
            return "met", "state_followup_handled"
        return "failed", "state_followup_not_reached"
    if kind == "origin_check":
        if query_kind in {"state_followup", "agent_first"} and anchor_present:
            return "met", "origin_anchor_available"
        if query_kind in {"state_followup", "agent_first"} or lane_injected:
            return "partial", "origin_clarification_without_anchor"
        return "failed", "origin_check_not_reached"
    return "partial", "expectation_not_classified"


def _evaluate_agent_expectation(record: Mapping[str, Any]) -> tuple[str, str]:
    mode = _safe_token(record.get("agent_mode"))
    if mode == agent_contract.MODE_OFF:
        return "met", "agent_off_explicit"
    if mode in {agent_contract.MODE_SHADOW, agent_contract.MODE_CANDIDATE}:
        return "failed", "agent_mode_dev_only_not_nominal"
    if mode != agent_contract.MODE_ACTIVE:
        return "failed", "agent_mode_not_nominal"
    if not _to_bool(record.get("agent_present")):
        return "failed", "agent_observation_missing"
    if not _to_bool(record.get("agent_model_called")):
        reason = _safe_token(record.get("agent_reason_code")) or "agent_model_not_called"
        return "failed", reason
    if not _to_bool(record.get("agent_candidate_plan_present")):
        reason = _safe_token(record.get("agent_reason_code")) or "agent_candidate_plan_missing"
        return "failed", reason
    return "met", "agent_active_plan_observed"


def _combine_expectations(
    case_kind: str,
    record: Mapping[str, Any],
    *,
    runtime_status: str,
    runtime_reason: str,
    agent_status: str,
    agent_reason: str,
) -> tuple[str, str]:
    if runtime_status == "met":
        return "met", runtime_reason
    kind = _safe_token(case_kind)
    if kind == "external_theme" and runtime_reason == "theme_search_not_found_without_context":
        return "failed", runtime_reason
    if kind == "origin_check":
        if runtime_status == "partial":
            return "partial_required_attention", runtime_reason
        return runtime_status, runtime_reason
    if runtime_status == "partial" or agent_status == "partial":
        return "partial_required_attention", runtime_reason if runtime_status == "partial" else agent_reason
    if agent_status == "failed" and runtime_status == "failed":
        return "failed", runtime_reason
    return runtime_status, runtime_reason


def _agent_first_execution_allowed(record: Mapping[str, Any]) -> bool:
    if _safe_token(record.get("agent_execution_scope")) != "agent_first":
        return False
    if _safe_token(record.get("agent_mode")) != agent_contract.MODE_ACTIVE:
        return False
    if _safe_token(record.get("agent_tool_execution_status")) != "executed":
        return False
    if _to_int(record.get("agent_tool_call_event_count")) < 1:
        return False
    allowed_tools = {
        "catalog_list",
        "catalog_search",
        "document_open_summary",
        "document_toc",
        "locate",
        "passage_context",
    }
    if not set(_safe_token_list(record.get("agent_plan_tool_names"))).issubset(allowed_tools):
        return False
    allowed_endpoints = {"catalog", "search", "metadata", "chapters", "locate", "context"}
    endpoint_kinds = set(_safe_token_list(record.get("endpoint_kinds")))
    if endpoint_kinds and not endpoint_kinds.issubset(allowed_endpoints):
        return False
    return (
        _to_bool(record.get("agent_used_for_response"))
        and _to_bool(record.get("agent_product_response_changed"))
        and _safe_token(record.get("product_expectation_status")) == "met"
    )


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
