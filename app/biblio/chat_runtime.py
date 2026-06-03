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
from .conversation_followup import update_state_for_clarification
from .conversation_state import (
    BiblioConversationState,
    BiblioStateTransition,
    attach_state_to_latest_user_message,
    read_state_from_conversation,
    update_state_from_runtime,
)
from .document_resolver import BiblioResolveRequest
from . import librarian_agent_first
from . import librarian_agent_bridge
from . import librarian_dialogue_planner
from . import librarian_dialogue_runtime
from . import librarian_product_methods
from . import librarian_tools
from .library_runtime import run_biblio_library_plan
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
        librarian_agent_result = librarian_agent_bridge.run_librarian_agent_comparison_safely(
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
        bridge_result = librarian_agent_bridge.run_agent_first_bridge(
            librarian_agent_result=librarian_agent_result,
            query_plan=decision.query_plan,
            user_msg=user_msg,
            state=state_before,
            recent_dialogue=recent_dialogue,
            client_factory=client_factory,
            config_module=config_module,
        )
        librarian_agent_result = bridge_result.librarian_agent_result
        agent_first_result = bridge_result.agent_first_result
        if (
            agent_first_result is not None
            and agent_first_result.status in {
                librarian_agent_first.STATUS_AGENT_FIRST_EXECUTED,
                librarian_agent_first.STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
            }
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
            product_projection = _agent_first_product_projection(
                librarian_agent_result=librarian_agent_result,
                state_after=state_after,
                state_transition=state_transition,
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
                product_case_id=product_projection["case_id"],
                product_method=product_projection["product_method"],
                execution_status=product_projection["execution_status"],
                product_truth=product_projection["product_truth"],
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
            librarian_dialogue_runtime.run_navigation_dialogue_plan(
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
        followup_clarification = librarian_dialogue_runtime.detect_biblio_followup_clarification(
            enabled=decision.enabled,
            user_msg=user_msg,
            state=state_before,
        )
        if followup_clarification is not None:
            followup = followup_clarification.followup
            clarification = followup_clarification.clarification
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


def _agent_first_product_projection(
    *,
    librarian_agent_result: Any,
    state_after: BiblioConversationState,
    state_transition: BiblioStateTransition | None,
) -> dict[str, str]:
    validation_plan = _agent_validation_plan(librarian_agent_result)
    product_method = str(validation_plan.get("product_method") or "").strip()
    case_id = librarian_product_methods.normalize_case_id(validation_plan.get("case_id"))
    if not case_id:
        case_id = librarian_product_methods.default_case_id_for_method(product_method)
    execution_status = librarian_product_methods.EXECUTION_STATUS_SUCCESS
    product_truth = _project_agent_first_truth(
        product_method,
        answer_mode=str(validation_plan.get("answer_mode") or "").strip(),
        validation_plan=validation_plan,
        librarian_agent_result=librarian_agent_result,
    )
    return {
        "case_id": case_id,
        "product_method": product_method,
        "execution_status": execution_status if product_method else "",
        "product_truth": product_truth,
    }


def _agent_validation_plan(librarian_agent_result: Any) -> Mapping[str, Any]:
    comparison = getattr(librarian_agent_result, "agent_result", None)
    validation = getattr(comparison, "validation_observation", None)
    if isinstance(validation, Mapping):
        plan = validation.get("plan")
        if isinstance(plan, Mapping):
            return plan
    return {}


def _default_truth_for_method(product_method: str) -> str:
    spec = librarian_product_methods.get_product_method_spec(product_method)
    if not spec or not spec.truth_levels:
        return ""
    return str(spec.truth_levels[0] or "").strip()


def _project_agent_first_truth(
    product_method: str,
    *,
    answer_mode: str,
    validation_plan: Mapping[str, Any],
    librarian_agent_result: Any,
) -> str:
    default_truth = _default_truth_for_method(product_method)
    plan_tool_names = {
        str(name or "").strip()
        for name in (validation_plan.get("tool_names") or [])
        if str(name or "").strip()
    }
    if (
        answer_mode not in {
            "bounded_context_extract_start_of_section",
            "deliver_excerpt_context_from_section_start",
            "section_start_page_block_2",
        }
        and librarian_tools.TOOL_SEARCH_CHAPTERS not in plan_tool_names
    ):
        return default_truth
    loop_result = getattr(librarian_agent_result, "tool_loop_result", None)
    if loop_result is None:
        return librarian_product_methods.TRUTH_LEVEL_CONTEXTUAL
    endpoint_kinds = {
        str(step.endpoint_kind or "").strip()
        for step in getattr(loop_result, "steps", ()) or ()
        if getattr(step, "status", "") == "tool_executed"
    }
    if "page" in endpoint_kinds:
        return default_truth
    return librarian_product_methods.TRUTH_LEVEL_CONTEXTUAL


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
