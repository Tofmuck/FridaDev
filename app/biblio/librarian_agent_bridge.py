"""Bridge the bounded librarian agent into the Biblio chat runtime.

This module owns the agent-side orchestration slice that does not belong in the
top-level chat runtime anymore:

- safe comparison execution;
- candidate vs fallback agent-first eligibility;
- fallback plan construction;
- bounded agent-first handoff back to the runtime orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from .conversation_state import BiblioConversationState
from . import librarian_agent_first
from . import librarian_agent_runtime
from . import librarian_dialogue_navigation
from . import librarian_dialogue_planner
from . import librarian_planner
from . import librarian_product_methods
from . import librarian_tools
from .query_planner import INTENT_SHOW_TABLE_OF_CONTENTS


@dataclass(frozen=True)
class BiblioAgentBridgeResult:
    librarian_agent_result: Any = None
    agent_first_result: Any = None


def run_librarian_agent_comparison_safely(
    *,
    runner: Any,
    factory: Any,
    enabled: bool,
    user_msg: str,
    recent_dialogue: Sequence[Mapping[str, Any]],
    biblio_state: BiblioConversationState | None,
    deterministic_plan: Any,
    deterministic_status: str,
    deterministic_reason_code: str,
    deterministic_query_kind: str,
    config_module: Any,
) -> Any:
    if not enabled:
        return None
    kwargs = {
        "biblio_enabled": True,
        "user_msg": user_msg,
        "recent_dialogue": recent_dialogue,
        "biblio_state": biblio_state,
        "deterministic_plan": deterministic_plan,
        "deterministic_status": deterministic_status,
        "deterministic_reason_code": deterministic_reason_code,
        "deterministic_query_kind": deterministic_query_kind,
        "config_module": config_module,
    }
    if factory is not None:
        kwargs["agent_factory"] = factory
    try:
        return runner(**kwargs)
    except Exception as exc:
        return {
            "present": True,
            "status": "fallback_deterministic",
            "reason_code": "biblio_librarian_agent_runtime_error",
            "error_class": exc.__class__.__name__,
            "model_called": False,
            "used_for_response": False,
            "fallback_deterministic": True,
            "deterministic_controller": True,
            "product_response_changed": False,
        }


def run_agent_first_bridge(
    *,
    librarian_agent_result: Any,
    query_plan: Any,
    user_msg: str,
    state: BiblioConversationState,
    recent_dialogue: Sequence[Mapping[str, Any]],
    client_factory: Any,
    config_module: Any,
) -> BiblioAgentBridgeResult:
    result = librarian_agent_result
    agent_first_result = None
    eligible = True
    if eligible and _agent_first_candidate_allowed(librarian_agent_result=result):
        try:
            client = client_factory(config_module=config_module)
            agent_first_result = librarian_agent_first.run_agent_first_plan(
                comparison=result,
                client=client,
                deterministic_plan=query_plan,
                user_msg=user_msg,
                conversation_state=state,
            )
        except Exception:
            agent_first_result = None
        repaired = _repair_agent_first_with_query_fallback(
            librarian_agent_result=result,
            query_plan=query_plan,
            client_factory=client_factory,
            config_module=config_module,
        )
        if repaired is not None:
            result, agent_first_result = repaired
        elif not _agent_first_result_is_usable(agent_first_result):
            repaired = _repair_agent_first_with_query_fallback(
                librarian_agent_result=result,
                query_plan=query_plan,
                client_factory=client_factory,
                config_module=config_module,
            )
            if repaired is None:
                repaired = _repair_agent_first_with_dialogue_fallback(
                    librarian_agent_result=result,
                    user_msg=user_msg,
                    state=state,
                    recent_dialogue=recent_dialogue,
                    client_factory=client_factory,
                    config_module=config_module,
                    deterministic_plan=query_plan,
                )
            if repaired is not None:
                result, agent_first_result = repaired
    elif eligible and _agent_first_fallback_allowed(result):
        fallback_plan = build_query_fallback_plan(query_plan) or build_dialogue_fallback_plan(
            user_msg=user_msg,
            state=state,
            recent_dialogue=recent_dialogue,
        )
        if fallback_plan is not None:
            result = _with_agent_first_fallback_plan(result, fallback_plan)
            try:
                client = client_factory(config_module=config_module)
                agent_first_result = librarian_agent_first.run_agent_first_plan(
                    comparison=result,
                    client=client,
                    deterministic_plan=query_plan,
                    user_msg=user_msg,
                    conversation_state=state,
                )
            except Exception:
                agent_first_result = None
    if agent_first_result is not None and getattr(agent_first_result, "loop_result", None) is not None:
        agent_used = agent_first_result.status in {
            librarian_agent_first.STATUS_AGENT_FIRST_EXECUTED,
            librarian_agent_first.STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
        }
        result = replace(
            result,
            tool_loop_result=agent_first_result.loop_result,
            execution_scope=librarian_agent_first.EXECUTION_SCOPE_AGENT_FIRST,
            used_for_response_override=agent_used,
            product_response_changed_override=agent_used,
        )
    return BiblioAgentBridgeResult(librarian_agent_result=result, agent_first_result=agent_first_result)


def _execute_agent_first_fallback_plan(
    *,
    librarian_agent_result: Any,
    plan: librarian_planner.BiblioLibrarianPlan,
    query_plan: Any,
    client_factory: Any,
    config_module: Any,
) -> tuple[Any, Any] | None:
    repaired_result = _with_agent_first_fallback_plan(librarian_agent_result, plan)
    try:
        client = client_factory(config_module=config_module)
        repaired_execution = librarian_agent_first.run_agent_first_plan(
            comparison=repaired_result,
            client=client,
            deterministic_plan=query_plan,
        )
    except Exception:
        return None
    if not _agent_first_result_is_usable(repaired_execution):
        return None
    return repaired_result, repaired_execution


def _repair_agent_first_with_query_fallback(
    *,
    librarian_agent_result: Any,
    query_plan: Any,
    client_factory: Any,
    config_module: Any,
) -> tuple[Any, Any] | None:
    fallback_plan = build_query_fallback_plan(query_plan)
    if fallback_plan is None:
        return None
    if str(getattr(fallback_plan, "fallback_reason", "") or "") != "agent_query_fallback_canonical_range":
        return None
    candidate_plan = _candidate_plan(librarian_agent_result)
    if candidate_plan is not None:
        candidate_method = str(getattr(candidate_plan, "product_method", "") or "").strip()
        fallback_method = str(getattr(fallback_plan, "product_method", "") or "").strip()
        if candidate_method == fallback_method:
            return None
    return _execute_agent_first_fallback_plan(
        librarian_agent_result=librarian_agent_result,
        plan=fallback_plan,
        query_plan=query_plan,
        client_factory=client_factory,
        config_module=config_module,
    )


def _canonical_range_fallback_params(query_plan: Any) -> dict[str, Any]:
    locator = str(getattr(query_plan, "locator", "") or "").strip()
    locator_end = str(getattr(query_plan, "locator_end", "") or "").strip()
    if not locator or not locator_end:
        return {}
    params: dict[str, Any] = {
        "locator": locator,
        "locator_end": locator_end,
        "kind": str(getattr(query_plan, "locator_kind", "") or "stephanus").strip() or "stephanus",
        "max_passage_chars": 8000,
    }
    for attr, key in (
        ("document_id", "document_id"),
        ("document_title", "document_title"),
        ("work_title", "work_title"),
        ("author", "author"),
    ):
        value = str(getattr(query_plan, attr, "") or "").strip()
        if value:
            params[key] = value
    query = str(getattr(query_plan, "catalogue_query", "") or "").strip()
    if query and not any(params.get(key) for key in ("document_id", "document_title", "work_title", "author")):
        params["query"] = query
    return params if any(params.get(key) for key in ("document_id", "document_title", "work_title", "author", "query")) else {}


def _build_canonical_range_fallback_plan(query_plan: Any) -> librarian_planner.BiblioLibrarianPlan | None:
    params = _canonical_range_fallback_params(query_plan)
    if not params:
        return None
    return librarian_planner.BiblioLibrarianPlan(
        schema_version=librarian_planner.SCHEMA_VERSION,
        case_id="P04",
        intent=str(getattr(query_plan, "intent", "") or "extract_range"),
        product_method=librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
        tool_calls=(
            librarian_planner.BiblioLibrarianToolCall(
                tool_name=librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT,
                method="GET",
                params=params,
            ),
        ),
        answer_mode="canonical_range_extract",
        fallback_reason="agent_query_fallback_canonical_range",
    )


def build_query_fallback_plan(query_plan: Any) -> librarian_planner.BiblioLibrarianPlan | None:
    intent = str(getattr(query_plan, "intent", "") or "")
    if intent == "extract_range":
        canonical_range_plan = _build_canonical_range_fallback_plan(query_plan)
        if canonical_range_plan is not None:
            return canonical_range_plan
    calls: list[librarian_planner.BiblioLibrarianToolCall] = []
    if intent == "list_catalog":
        calls.append(
            librarian_planner.BiblioLibrarianToolCall(
                tool_name=librarian_tools.TOOL_CATALOG_LIST,
                method="GET",
                params={"limit": 100},
            )
        )
    elif intent == INTENT_SHOW_TABLE_OF_CONTENTS:
        query = _fallback_catalogue_query(query_plan)
        if query:
            calls.append(
                librarian_planner.BiblioLibrarianToolCall(
                    tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                    method="GET",
                    params={"query": query, "limit": _fallback_limit(query_plan, default=5)},
                )
            )
    elif intent in {"search_catalog", "extract_passage", "extract_range", "document_locator", "resolve_work"}:
        query = _fallback_catalogue_query(query_plan)
        if query:
            calls.append(
                librarian_planner.BiblioLibrarianToolCall(
                    tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                    method="GET",
                    params={"query": query, "limit": _fallback_limit(query_plan, default=8)},
                )
            )
    if not calls:
        return None
    product_method = _fallback_product_method(
        intent=intent or "biblio_request",
        answer_mode="tool",
        tool_calls=tuple(calls),
        query_kind=str(getattr(query_plan, "query_kind", "") or ""),
    )
    return librarian_planner.BiblioLibrarianPlan(
        schema_version=librarian_planner.SCHEMA_VERSION,
        case_id="",
        intent=intent or "biblio_request",
        product_method=product_method,
        tool_calls=tuple(calls),
        answer_mode="tool",
        fallback_reason="agent_json_invalid_fallback_plan",
    )


def _repair_agent_first_with_dialogue_fallback(
    *,
    librarian_agent_result: Any,
    user_msg: str,
    state: BiblioConversationState,
    recent_dialogue: Sequence[Mapping[str, Any]],
    client_factory: Any,
    config_module: Any,
    deterministic_plan: Any,
) -> tuple[Any, Any] | None:
    candidate_plan = _candidate_plan(librarian_agent_result)
    if candidate_plan is None:
        return None
    fallback_plan = build_dialogue_fallback_plan(
        user_msg=user_msg,
        state=state,
        recent_dialogue=recent_dialogue,
    )
    if fallback_plan is None or not _dialogue_fallback_matches_candidate(candidate_plan, fallback_plan):
        return None
    repaired_plan = replace(
        fallback_plan,
        case_id=str(getattr(candidate_plan, "case_id", "") or ""),
        product_method=str(getattr(candidate_plan, "product_method", "") or fallback_plan.product_method or ""),
        fallback_reason="agent_dialogue_fallback_repaired_plan",
    )
    repaired_result = _with_agent_first_fallback_plan(librarian_agent_result, repaired_plan)
    try:
        client = client_factory(config_module=config_module)
        repaired_execution = librarian_agent_first.run_agent_first_plan(
            comparison=repaired_result,
            client=client,
            deterministic_plan=deterministic_plan,
            user_msg=user_msg,
            conversation_state=state,
        )
    except Exception:
        return None
    if not _agent_first_result_is_usable(repaired_execution):
        return None
    return repaired_result, repaired_execution

def build_dialogue_fallback_plan(
    *,
    user_msg: str,
    state: BiblioConversationState,
    recent_dialogue: Sequence[Mapping[str, Any]],
) -> librarian_planner.BiblioLibrarianPlan | None:
    dialogue = librarian_dialogue_planner.plan_biblio_dialogue(
        user_msg,
        state=state,
        recent_dialogue=recent_dialogue,
    )
    plan = dialogue.plan
    tool_calls = tuple(getattr(plan, "tool_calls", ()) or ())
    if dialogue.status != librarian_dialogue_planner.STATUS_PLANNED or not tool_calls:
        return None
    if not all(str(getattr(call, "method", "") or "").strip().upper() == "GET" for call in tool_calls):
        return None
    product_method = _fallback_product_method(
        intent=str(getattr(plan, "intent", "") or ""),
        answer_mode=str(getattr(plan, "answer_mode", "") or ""),
        tool_calls=tool_calls,
        query_kind=str(getattr(dialogue.intent, "query_kind", "") or ""),
        scope_mode=str(getattr(dialogue.intent, "scope_mode", "") or ""),
    )
    return replace(
        plan,
        schema_version=librarian_planner.SCHEMA_VERSION,
        case_id="",
        product_method=product_method,
        fallback_reason="agent_json_invalid_dialogue_fallback_plan",
    )


def _agent_first_candidate_allowed(
    *,
    librarian_agent_result: Any,
) -> bool:
    if librarian_agent_result is None or isinstance(librarian_agent_result, Mapping):
        return False
    if str(getattr(getattr(librarian_agent_result, "settings", None), "mode", "") or "").strip().lower() != "active":
        return False
    agent_result = getattr(librarian_agent_result, "agent_result", None)
    plan = getattr(agent_result, "candidate_plan", None)
    tool_calls = tuple(getattr(plan, "tool_calls", ()) or ())
    if not tool_calls:
        return False
    return all(str(getattr(call, "method", "") or "").strip().upper() == "GET" for call in tool_calls)


def _agent_first_fallback_allowed(librarian_agent_result: Any) -> bool:
    if librarian_agent_result is None or isinstance(librarian_agent_result, Mapping):
        return False
    if str(getattr(getattr(librarian_agent_result, "settings", None), "mode", "") or "").strip().lower() != "active":
        return False
    agent_result = getattr(librarian_agent_result, "agent_result", None)
    if agent_result is None or not bool(getattr(agent_result, "model_called", False)):
        return False
    plan = getattr(agent_result, "candidate_plan", None)
    tool_calls = tuple(getattr(plan, "tool_calls", ()) or ()) if plan is not None else ()
    if tool_calls:
        return False
    return True


def _with_agent_first_fallback_plan(librarian_agent_result: Any, plan: librarian_planner.BiblioLibrarianPlan) -> Any:
    agent_result = getattr(librarian_agent_result, "agent_result", None)
    if agent_result is None:
        return librarian_agent_result
    return replace(librarian_agent_result, agent_result=replace(agent_result, candidate_plan=plan))


def _candidate_plan(librarian_agent_result: Any) -> librarian_planner.BiblioLibrarianPlan | None:
    agent_result = getattr(librarian_agent_result, "agent_result", None)
    plan = getattr(agent_result, "candidate_plan", None)
    if isinstance(plan, librarian_planner.BiblioLibrarianPlan):
        return plan
    return None


def _dialogue_fallback_matches_candidate(
    candidate_plan: librarian_planner.BiblioLibrarianPlan,
    fallback_plan: librarian_planner.BiblioLibrarianPlan,
) -> bool:
    candidate_method = str(getattr(candidate_plan, "product_method", "") or "").strip()
    fallback_method = str(getattr(fallback_plan, "product_method", "") or "").strip()
    if not candidate_method or candidate_method != fallback_method:
        return False
    candidate_tools = tuple(str(getattr(call, "tool_name", "") or "").strip() for call in candidate_plan.tool_calls)
    fallback_tools = tuple(str(getattr(call, "tool_name", "") or "").strip() for call in fallback_plan.tool_calls)
    if not candidate_tools or not fallback_tools:
        return False
    if candidate_tools == fallback_tools:
        return True
    spec = librarian_product_methods.get_product_method_spec(candidate_method)
    if spec is None:
        return False
    allowed = {str(name or "").strip() for name in spec.allowed_tool_names if str(name or "").strip()}
    if not allowed:
        return False
    return set(candidate_tools).issubset(allowed) and set(fallback_tools).issubset(allowed)


def _agent_first_result_is_usable(agent_first_result: Any) -> bool:
    return agent_first_result is not None and getattr(agent_first_result, "status", "") in {
        librarian_agent_first.STATUS_AGENT_FIRST_EXECUTED,
        librarian_agent_first.STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
    }


def _fallback_product_method(
    *,
    intent: str,
    answer_mode: str,
    tool_calls: Sequence[librarian_planner.BiblioLibrarianToolCall],
    query_kind: str = "",
    scope_mode: str = "",
) -> str:
    clean_intent = str(intent or "").strip()
    clean_query_kind = str(query_kind or "").strip()
    clean_scope_mode = str(scope_mode or "").strip()
    if clean_intent == librarian_dialogue_planner.INTENT_NAVIGATE and clean_query_kind == "passage_context":
        if clean_scope_mode in {
            librarian_dialogue_navigation.NAVIGATION_UP,
            librarian_dialogue_navigation.NAVIGATION_PAGE_PREVIOUS,
        }:
            return librarian_product_methods.PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT
        if clean_scope_mode in {
            librarian_dialogue_navigation.NAVIGATION_CONTINUE,
            librarian_dialogue_navigation.NAVIGATION_PAGE_NEXT,
        }:
            return librarian_product_methods.PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT
    if clean_intent == librarian_dialogue_planner.INTENT_ORIGIN_CHECK:
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK
    if clean_intent == librarian_dialogue_planner.INTENT_EXPLAIN_PASSAGE:
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT
    if clean_intent == librarian_dialogue_planner.INTENT_COMPARE_PASSAGES:
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES
    if clean_query_kind == "passage_context":
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT
    if clean_intent == librarian_dialogue_planner.INTENT_NAVIGATE and clean_query_kind == "page_read":
        if clean_scope_mode in {
            librarian_dialogue_navigation.NAVIGATION_UP,
            librarian_dialogue_navigation.NAVIGATION_PAGE_PREVIOUS,
        }:
            return librarian_product_methods.PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT
    return librarian_product_methods.infer_product_method(
        intent=clean_intent,
        answer_mode=answer_mode,
        tool_names=[str(call.tool_name or "") for call in tool_calls],
    )


def _fallback_catalogue_query(query_plan: Any) -> str:
    for attr in ("catalogue_query", "theme_query", "document_title", "work_title", "author"):
        value = str(getattr(query_plan, attr, "") or "").strip()
        if value:
            return value
    return ""


def _fallback_limit(query_plan: Any, *, default: int) -> int:
    try:
        parsed = int(getattr(query_plan, "limit", default) or default)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
