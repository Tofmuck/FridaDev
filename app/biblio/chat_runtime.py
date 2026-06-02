"""Minimal chat wiring for native Biblio.

This module decides whether an already user-enabled Biblio turn is explicit
enough to consult Catalogue.  It stays content-free outside the prompt lane:
raw titles, locators and passages are only used internally to resolve and
extract a bounded passage.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from .catalogue_client import CatalogueClient
from .conversation_followup import (
    clarification_for_followup,
    detect_followup_request,
    update_state_for_clarification,
)
from .conversation_state import (
    BiblioConversationState,
    BiblioStateTransition,
    attach_state_to_latest_user_message,
    read_state_from_conversation,
    update_state_from_runtime,
)
from . import document_resolver
from .document_resolver import BiblioResolveRequest
from . import librarian_planner
from . import librarian_tools
from . import librarian_product_methods
from . import librarian_dialogue_planner
from . import librarian_dialogue_navigation
from . import librarian_dialogue_intents
from .librarian_navigation_runtime import run_biblio_navigation_plan
from .library_runtime import run_biblio_library_plan
from .librarian_agent_first import (
    EXECUTION_SCOPE_AGENT_FIRST,
    STATUS_AGENT_FIRST_EXECUTED,
    STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
    run_agent_first_plan,
)
from .librarian_agent_runtime import run_biblio_librarian_agent_comparison
from .observability import build_biblio_event_payload
from .passage_context_search import BiblioPassageContextSearchResult
from .passage_extractor import BiblioPassageExtractor, BiblioPassageResult
from .prompt_lane import build_biblio_prompt_lane
from .query_planner import (
    BiblioQueryPlan,
    INTENT_EXTRACT_PASSAGE,
    INTENT_EXTRACT_RANGE,
    INTENT_SHOW_TABLE_OF_CONTENTS,
    plan_biblio_query,
)


PAYLOAD_KEY_BIBLIO_ENABLED = "biblio_enabled"

REASON_TOGGLE_DISABLED = "biblio_toggle_disabled"
REASON_NO_BIBLIOGRAPHIC_SIGNAL = "biblio_no_bibliographic_signal"
REASON_ADOBE_TOPIC_IGNORED = "biblio_adobe_topic_ignored"
REASON_DOCUMENT_SIGNAL_DETECTED = "biblio_document_signal_detected"
REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED = "biblio_document_locator_signal_detected"
REASON_RUNTIME_ERROR = "biblio_runtime_error"

QUERY_KIND_NOT_REQUESTED = "not_requested"
QUERY_KIND_NO_SIGNAL = "no_signal"
QUERY_KIND_DOCUMENT = "document"
QUERY_KIND_DOCUMENT_LOCATOR = "document_locator"
QUERY_KIND_STATE_FOLLOWUP = "state_followup"
QUERY_KIND_AGENT_FIRST = "agent_first"

@dataclass(frozen=True)
class BiblioChatDecision:
    enabled: bool
    should_attempt: bool
    reason_code: str
    query_kind: str = QUERY_KIND_NOT_REQUESTED
    resolve_request: BiblioResolveRequest | None = field(default=None, repr=False, compare=False)
    query_plan: BiblioQueryPlan | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, repr=False)
class BiblioChatResult:
    enabled: bool
    used: bool
    reason_code: str
    query_kind: str
    observability_payload: dict[str, Any]
    context_result: BiblioPassageContextSearchResult | None = field(default=None, repr=False, compare=False)
    passage_result: BiblioPassageResult | None = field(default=None, repr=False, compare=False)
    prompt_lane: Any = field(default=None, repr=False, compare=False)
    biblio_state: BiblioConversationState | None = field(default=None, repr=False, compare=False)
    state_transition: BiblioStateTransition | None = field(default=None, repr=False, compare=False)
    librarian_agent_result: Any = field(default=None, repr=False, compare=False)

    @property
    def prompt_message(self) -> dict[str, Any] | None:
        if self.prompt_lane is None:
            return None
        return getattr(self.prompt_lane, "message", None)


def resolve_biblio_chat_decision(data: Mapping[str, Any], user_msg: str) -> BiblioChatDecision:
    enabled = _truthy(data.get(PAYLOAD_KEY_BIBLIO_ENABLED))
    if not enabled:
        return BiblioChatDecision(
            enabled=False,
            should_attempt=False,
            reason_code=REASON_TOGGLE_DISABLED,
            query_kind=QUERY_KIND_NOT_REQUESTED,
        )

    plan = plan_biblio_query(user_msg)
    if not plan.should_consult:
        return BiblioChatDecision(
            enabled=True,
            should_attempt=False,
            reason_code=plan.reason_code,
            query_kind=plan.query_kind,
            query_plan=plan,
        )

    request = _resolve_request_from_plan(plan)
    return BiblioChatDecision(
        enabled=True,
        should_attempt=True,
        reason_code=plan.reason_code,
        query_kind=plan.query_kind,
        resolve_request=request,
        query_plan=plan,
    )


def run_biblio_chat_turn(
    data: Mapping[str, Any],
    *,
    user_msg: str,
    conversation_id: str = "",
    conversation_state: BiblioConversationState | None = None,
    recent_dialogue: Sequence[Mapping[str, Any]] = (),
    now_iso: str = "",
    config_module: Any = None,
    client_factory: Any = CatalogueClient,
    extractor_factory: Any = BiblioPassageExtractor,
    lane_builder: Any = build_biblio_prompt_lane,
    observability_builder: Any = build_biblio_event_payload,
    librarian_agent_runner: Any = run_biblio_librarian_agent_comparison,
    librarian_agent_factory: Any = None,
) -> BiblioChatResult:
    state_before = (
        conversation_state
        if isinstance(conversation_state, BiblioConversationState)
        else BiblioConversationState.empty(conversation_id=conversation_id)
    )
    decision = resolve_biblio_chat_decision(data, user_msg)
    librarian_agent_result = None
    if decision.enabled:
        preliminary_status = "deterministic_candidate" if decision.should_attempt else "not_used"
        librarian_agent_result = _run_librarian_agent_comparison(
            runner=librarian_agent_runner,
            factory=librarian_agent_factory,
            enabled=True,
            user_msg=user_msg,
            recent_dialogue=recent_dialogue,
            biblio_state=state_before if state_before.present else None,
            deterministic_plan=decision.query_plan,
            deterministic_status=preliminary_status,
            deterministic_reason_code=decision.reason_code,
            deterministic_query_kind=decision.query_kind,
            config_module=config_module,
        )
        agent_first_result = None
        agent_first_eligible = not _agent_first_prefers_deterministic_controller(decision.query_plan)
        if agent_first_eligible and _agent_first_candidate_allowed(librarian_agent_result=librarian_agent_result):
            try:
                client = client_factory(config_module=config_module)
                agent_first_result = run_agent_first_plan(
                    comparison=librarian_agent_result,
                    client=client,
                    deterministic_plan=decision.query_plan,
                )
            except Exception:
                agent_first_result = None
        elif agent_first_eligible and _agent_first_fallback_allowed(librarian_agent_result):
            fallback_plan = _agent_first_fallback_plan(decision.query_plan) or _agent_first_dialogue_fallback_plan(
                user_msg=user_msg,
                state=state_before,
                recent_dialogue=recent_dialogue,
            )
            if fallback_plan is not None:
                librarian_agent_result = _with_agent_first_fallback_plan(
                    librarian_agent_result,
                    fallback_plan,
                )
                try:
                    client = client_factory(config_module=config_module)
                    agent_first_result = run_agent_first_plan(
                        comparison=librarian_agent_result,
                        client=client,
                        deterministic_plan=decision.query_plan,
                    )
                except Exception:
                    agent_first_result = None
        if agent_first_result is not None and getattr(agent_first_result, "loop_result", None) is not None:
            agent_used = agent_first_result.status in {
                STATUS_AGENT_FIRST_EXECUTED,
                STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
            }
            librarian_agent_result = replace(
                librarian_agent_result,
                tool_loop_result=agent_first_result.loop_result,
                execution_scope=EXECUTION_SCOPE_AGENT_FIRST,
                used_for_response_override=agent_used,
                product_response_changed_override=agent_used,
            )
        if (
            agent_first_result is not None
            and agent_first_result.status in {STATUS_AGENT_FIRST_EXECUTED, STATUS_AGENT_FIRST_NEEDS_CLARIFICATION}
            and agent_first_result.consultation_message is not None
        ):
            state_after, state_transition = update_state_from_runtime(
                state_before,
                query_plan=decision.query_plan,
                library_result=agent_first_result,
                conversation_id=conversation_id,
                now_iso=now_iso,
                reason_code="biblio_state_updated_from_agent_first",
            )
            payload = observability_builder(
                enabled=True,
                used=True,
                query_kind=QUERY_KIND_AGENT_FIRST,
                client_response=agent_first_result.client_observability(),
                resolution=decision.query_plan,
                prompt_lane=agent_first_result.consultation_message,
                biblio_state=state_after if state_after.present else None,
                state_transition=state_transition,
                librarian_agent=librarian_agent_result,
                status=agent_first_result.status,
                reason_code=agent_first_result.reason_code,
            )
            return BiblioChatResult(
                enabled=True,
                used=True,
                reason_code=agent_first_result.reason_code,
                query_kind=QUERY_KIND_AGENT_FIRST,
                prompt_lane=agent_first_result.consultation_message,
                biblio_state=state_after if state_after.present else None,
                state_transition=state_transition,
                librarian_agent_result=librarian_agent_result,
                observability_payload=payload,
            )
    if not decision.should_attempt or decision.query_plan is None:
        navigation_result = (
            _run_navigation_dialogue_plan(
                enabled=decision.enabled,
                user_msg=user_msg,
                state=state_before,
                recent_dialogue=recent_dialogue,
                client_factory=client_factory,
                config_module=config_module,
            )
            if decision.enabled
            else None
        )
        if navigation_result is not None:
            state_after, state_transition = update_state_from_runtime(
                state_before,
                library_result=navigation_result,
                conversation_id=conversation_id,
                now_iso=now_iso,
                source_event="biblio_navigation_dialogue",
                reason_code="biblio_state_updated_from_navigation_dialogue",
            )
            payload = observability_builder(
                enabled=True,
                used=True,
                query_kind=navigation_result.query_kind or decision.query_kind,
                client_response=navigation_result.client_observability(),
                prompt_lane=navigation_result.consultation_message,
                biblio_state=state_after if state_after.present else None,
                state_transition=state_transition,
                librarian_agent=librarian_agent_result,
                status=navigation_result.status,
                reason_code=navigation_result.reason_code,
            )
            return BiblioChatResult(
                enabled=True,
                used=True,
                reason_code=navigation_result.reason_code,
                query_kind=navigation_result.query_kind or decision.query_kind,
                prompt_lane=navigation_result.consultation_message,
                biblio_state=state_after if state_after.present else None,
                state_transition=state_transition,
                librarian_agent_result=librarian_agent_result,
                observability_payload=payload,
            )
        followup = detect_followup_request(user_msg) if decision.enabled else None
        clarification = clarification_for_followup(state_before, followup) if followup else None
        if clarification is not None and followup is not None:
            state_after, state_transition = update_state_for_clarification(
                state_before,
                followup=followup,
                clarification=clarification,
                conversation_id=conversation_id,
                now_iso=now_iso,
            )
            payload = observability_builder(
                enabled=True,
                used=True,
                query_kind=QUERY_KIND_STATE_FOLLOWUP,
                prompt_lane=clarification,
                biblio_state=state_after,
                state_transition=state_transition,
                librarian_agent=librarian_agent_result,
                status=clarification.to_observability()["status"],
                reason_code=clarification.reason_code,
            )
            return BiblioChatResult(
                enabled=True,
                used=True,
                reason_code=clarification.reason_code,
                query_kind=QUERY_KIND_STATE_FOLLOWUP,
                prompt_lane=clarification,
                biblio_state=state_after,
                state_transition=state_transition,
                librarian_agent_result=librarian_agent_result,
                observability_payload=payload,
            )

        status = "not_applicable" if not decision.enabled else "not_used"
        payload = observability_builder(
            enabled=decision.enabled,
            used=False,
            query_kind=decision.query_kind,
            status=status,
            reason_code=decision.reason_code,
            resolution=decision.query_plan,
            biblio_state=state_before if state_before.present else None,
            librarian_agent=librarian_agent_result,
        )
        return BiblioChatResult(
            enabled=decision.enabled,
            used=False,
            reason_code=decision.reason_code,
            query_kind=decision.query_kind,
            biblio_state=state_before if state_before.present else None,
            librarian_agent_result=librarian_agent_result,
            observability_payload=payload,
        )

    try:
        query_plan = _apply_conversation_state_to_plan(decision.query_plan, state_before)
        client = client_factory(config_module=config_module)
        library_result = run_biblio_library_plan(
            client,
            query_plan,
            extractor_factory=extractor_factory,
            lane_builder=lane_builder,
        )
        runtime_projection = library_result.context_result or library_result.passage_result
        state_after, state_transition = update_state_from_runtime(
            state_before,
            query_plan=query_plan,
            library_result=library_result,
            conversation_id=conversation_id,
            now_iso=now_iso,
            reason_code="biblio_state_updated_from_runtime",
        )
        payload = observability_builder(
            enabled=True,
            used=True,
            query_kind=decision.query_kind,
            client_response=library_result.client_observability(),
            resolution=library_result.work_resolution or query_plan,
            passage_result=runtime_projection,
            prompt_lane=library_result.prompt_lane or library_result.consultation_message,
            biblio_state=state_after,
            state_transition=state_transition,
            librarian_agent=librarian_agent_result,
            status=library_result.status,
            reason_code=library_result.reason_code or decision.reason_code,
        )
        return BiblioChatResult(
            enabled=True,
            used=True,
            reason_code=library_result.reason_code or decision.reason_code,
            query_kind=decision.query_kind,
            context_result=library_result.context_result,
            passage_result=library_result.passage_result,
            prompt_lane=library_result.prompt_lane or library_result.consultation_message,
            biblio_state=state_after,
            state_transition=state_transition,
            librarian_agent_result=librarian_agent_result,
            observability_payload=payload,
        )
    except Exception as exc:
        payload = observability_builder(
            enabled=True,
            used=True,
            query_kind=decision.query_kind,
            status="error",
            reason_code=REASON_RUNTIME_ERROR,
            client_error={
                "status": "error",
                "reason_code": REASON_RUNTIME_ERROR,
                "error_class": exc.__class__.__name__,
            },
            biblio_state=state_before if state_before.present else None,
        )
        return BiblioChatResult(
            enabled=True,
            used=True,
            reason_code=REASON_RUNTIME_ERROR,
            query_kind=decision.query_kind,
            biblio_state=state_before if state_before.present else None,
            observability_payload=payload,
        )


def inject_biblio_prompt_lane(
    prompt_messages: list[dict[str, Any]],
    result: BiblioChatResult,
) -> bool:
    message = result.prompt_message
    if not message:
        return False
    insert_at = _before_last_user_index(prompt_messages)
    prompt_messages[insert_at:insert_at] = [dict(message)]
    return True


def read_biblio_conversation_state(conversation: Mapping[str, Any]) -> BiblioConversationState:
    return read_state_from_conversation(conversation)


def attach_biblio_conversation_state(
    conversation: dict[str, Any],
    result: BiblioChatResult,
) -> bool:
    if result.state_transition is None or not result.state_transition.after_present:
        return False
    return attach_state_to_latest_user_message(conversation, result.biblio_state)


def _resolve_request_from_plan(plan: BiblioQueryPlan) -> BiblioResolveRequest | None:
    if not (plan.document_id or plan.document_title or plan.work_title or plan.author or plan.locator):
        return None
    return BiblioResolveRequest(
        document_id=plan.document_id,
        title=plan.document_title or plan.work_title,
        document_title=plan.document_title,
        work_title=plan.work_title,
        author=plan.author,
        locator=plan.locator,
        locator_end=plan.locator_end,
        locator_kind=plan.locator_kind,
    )


def _apply_conversation_state_to_plan(
    plan: BiblioQueryPlan,
    state: BiblioConversationState,
) -> BiblioQueryPlan:
    if plan.intent != INTENT_SHOW_TABLE_OF_CONTENTS:
        return plan
    if plan.document_id or plan.document_title or plan.work_title or plan.catalogue_query:
        return plan
    document_id = str(state.current_document.get("document_id") or "").strip()
    if not document_id:
        return plan
    return replace(plan, document_id=document_id)


def _run_librarian_agent_comparison(
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


def _agent_first_prefers_deterministic_controller(query_plan: Any) -> bool:
    if query_plan is None:
        return False
    intent = str(getattr(query_plan, "intent", "") or "").strip()
    locator = str(getattr(query_plan, "locator", "") or "").strip()
    if not locator:
        return False
    return intent in {INTENT_EXTRACT_PASSAGE, INTENT_EXTRACT_RANGE}


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


def _fallback_product_method(
    *,
    intent: str,
    answer_mode: str,
    tool_calls: Sequence[librarian_planner.BiblioLibrarianToolCall],
    query_kind: str = "",
) -> str:
    clean_intent = str(intent or "").strip()
    clean_query_kind = str(query_kind or "").strip()
    if clean_intent == librarian_dialogue_planner.INTENT_NAVIGATE and clean_query_kind == "passage_context":
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT
    if clean_intent == librarian_dialogue_planner.INTENT_EXPLAIN_PASSAGE:
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT
    if clean_query_kind == "passage_context":
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT
    if clean_intent == librarian_dialogue_planner.INTENT_NAVIGATE and clean_query_kind == "page_read":
        return librarian_product_methods.PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT
    return librarian_product_methods.infer_product_method(
        intent=clean_intent,
        answer_mode=answer_mode,
        tool_names=[str(call.tool_name or "") for call in tool_calls],
    )


def _agent_first_fallback_plan(query_plan: Any) -> librarian_planner.BiblioLibrarianPlan | None:
    intent = str(getattr(query_plan, "intent", "") or "")
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


def _agent_first_dialogue_fallback_plan(
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
    )
    return replace(
        plan,
        schema_version=librarian_planner.SCHEMA_VERSION,
        case_id="",
        product_method=product_method,
        fallback_reason="agent_json_invalid_dialogue_fallback_plan",
    )


def _run_navigation_dialogue_plan(
    *,
    enabled: bool,
    user_msg: str,
    state: BiblioConversationState,
    recent_dialogue: Sequence[Mapping[str, Any]],
    client_factory: Any,
    config_module: Any,
) -> Any:
    if not enabled:
        return None
    dialogue = librarian_dialogue_planner.plan_biblio_dialogue(
        user_msg,
        state=state,
        recent_dialogue=recent_dialogue,
    )
    if dialogue.intent.intent != librarian_dialogue_planner.INTENT_NAVIGATE:
        return None
    if dialogue.status not in {
        librarian_dialogue_planner.STATUS_PLANNED,
        librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION,
        librarian_dialogue_planner.STATUS_UNSUPPORTED_MISSING_TOOL,
    }:
        return None
    if (
        dialogue.status == librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION
        and dialogue.reason_code == librarian_dialogue_planner.REASON_NAVIGATION_EXPLICIT_REFERENCE_UNRESOLVED
    ):
        resolved = _resolve_named_document_page_navigation(
            dialogue=dialogue,
            user_msg=user_msg,
            state=state,
            client_factory=client_factory,
            config_module=config_module,
        )
        if resolved is not None:
            resolved_dialogue, client = resolved
            if resolved_dialogue.status == librarian_dialogue_planner.STATUS_PLANNED and client is not None:
                return run_biblio_navigation_plan(client, resolved_dialogue)
            return run_biblio_navigation_plan(None, resolved_dialogue)
    if dialogue.status == librarian_dialogue_planner.STATUS_PLANNED:
        client = client_factory(config_module=config_module)
        return run_biblio_navigation_plan(client, dialogue)
    return run_biblio_navigation_plan(None, dialogue)


def _resolve_named_document_page_navigation(
    *,
    dialogue: librarian_dialogue_planner.BiblioDialoguePlanningResult,
    user_msg: str,
    state: BiblioConversationState,
    client_factory: Any,
    config_module: Any,
) -> tuple[librarian_dialogue_planner.BiblioDialoguePlanningResult, Any | None] | None:
    kind = str(dialogue.intent.scope_mode or "")
    if not librarian_dialogue_navigation.can_plan_page_navigation(kind):
        return None
    target = librarian_dialogue_navigation.explicit_reference_target(user_msg)
    if not target:
        return None
    client = client_factory(config_module=config_module)
    resolution = document_resolver.BiblioDocumentResolver(client).resolve(
        BiblioResolveRequest(title=target)
    )
    if resolution.status != document_resolver.STATUS_RESOLVED or resolution.document is None:
        return None
    resolved_dialogue = _named_document_page_dialogue(
        dialogue=dialogue,
        user_msg=user_msg,
        state=state,
        document_id=resolution.document.document_id,
        doc_id_short=resolution.document.doc_id_short,
    )
    return resolved_dialogue, client


def _named_document_page_dialogue(
    *,
    dialogue: librarian_dialogue_planner.BiblioDialoguePlanningResult,
    user_msg: str,
    state: BiblioConversationState,
    document_id: str,
    doc_id_short: str,
) -> librarian_dialogue_planner.BiblioDialoguePlanningResult:
    kind = str(dialogue.intent.scope_mode or "")
    tool_required = librarian_dialogue_navigation.tool_required_for_navigation(kind)
    intent = librarian_dialogue_planner.BiblioDialogueIntent(
        librarian_dialogue_planner.INTENT_NAVIGATE,
        query_kind="page_read",
        state_required=True,
        tool_required=tool_required,
        scope_mode=kind,
    )
    resolved_state = _state_for_navigation_document(
        state,
        document_id=document_id,
        doc_id_short=doc_id_short,
    )
    folded = librarian_dialogue_intents.fold_message(
        librarian_dialogue_intents.normalize_message(user_msg)
    )
    page_numbers = librarian_dialogue_navigation.page_numbers_for_navigation(
        kind,
        resolved_state,
        folded,
    )
    if (
        kind == librarian_dialogue_navigation.NAVIGATION_PAGE_EXPLICIT
        and librarian_dialogue_navigation.page_request(folded) is not None
        and not page_numbers
    ):
        return replace(
            dialogue,
            status=librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION,
            reason_code=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_RANGE_TOO_WIDE,
            intent=intent,
            plan=librarian_planner.BiblioLibrarianPlan(
                intent="clarify",
                answer_mode="clarify",
                fallback_reason=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_RANGE_TOO_WIDE,
            ),
            state_present=resolved_state.present,
            current_document_used=False,
            tool_required=tool_required,
        )
    if not page_numbers:
        return replace(
            dialogue,
            status=librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION,
            reason_code=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_ANCHOR_MISSING,
            intent=intent,
            plan=librarian_planner.BiblioLibrarianPlan(
                intent="clarify",
                answer_mode="clarify",
                fallback_reason=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_ANCHOR_MISSING,
            ),
            state_present=resolved_state.present,
            current_document_used=False,
            tool_required=tool_required,
        )
    tool_calls = tuple(
        librarian_planner.BiblioLibrarianToolCall(
            tool_name=librarian_tools.TOOL_PAGE_READ,
            params={"document_id": document_id, "page_no": page_no},
            method="GET",
        )
        for page_no in page_numbers
    )
    return replace(
        dialogue,
        status=librarian_dialogue_planner.STATUS_PLANNED,
        reason_code=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_READ,
        intent=intent,
        plan=librarian_planner.BiblioLibrarianPlan(
            intent=librarian_dialogue_planner.INTENT_NAVIGATE,
            answer_mode="tool",
            tool_calls=tool_calls,
        ),
        state_present=resolved_state.present,
        current_document_used=_navigation_state_matches_document(state, document_id),
        tool_required=tool_required,
    )


def _state_for_navigation_document(
    state: BiblioConversationState,
    *,
    document_id: str,
    doc_id_short: str,
) -> BiblioConversationState:
    if _navigation_state_matches_document(state, document_id):
        return replace(
            state,
            current_document={"document_id": document_id, "doc_id_short": doc_id_short},
        )
    return replace(
        state,
        current_document={"document_id": document_id, "doc_id_short": doc_id_short},
        page_no=None,
        para_no=None,
        paragraph_id=None,
        last_result={},
        last_candidates=(),
        last_ambiguity={},
    )


def _navigation_state_matches_document(state: BiblioConversationState, document_id: str) -> bool:
    anchored = str(state.last_result.get("document_id") or state.current_document.get("document_id") or "").strip()
    return bool(anchored) and anchored == str(document_id or "").strip()


def _fallback_catalogue_query(query_plan: Any) -> str:
    for attr in ("catalogue_query", "theme_query", "work_title", "document_title", "author", "locator"):
        value = str(getattr(query_plan, attr, "") or "").strip()
        if value:
            return value[:240]
    return ""


def _fallback_limit(query_plan: Any, *, default: int) -> int:
    value = getattr(query_plan, "limit", default)
    if type(value) is int and value > 0:
        return min(value, 50)
    return default


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on", "enabled", "active"}


def _before_last_user_index(prompt_messages: Sequence[Mapping[str, Any]]) -> int:
    for index in range(len(prompt_messages) - 1, -1, -1):
        if str(prompt_messages[index].get("role") or "") == "user":
            return index
    return len(prompt_messages)
