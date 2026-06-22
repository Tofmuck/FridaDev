"""Minimal chat wiring for native Biblio.

This module decides whether an already user-enabled Biblio turn is explicit
enough to consult Catalogue.  It stays content-free outside the prompt lane:
raw titles, locators and passages are only used internally to resolve and
extract a bounded passage.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from . import answer_object as biblio_answer_object
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
QUERY_KIND_READ_PASSAGES = "read_passages"

READ_PASSAGES_MODE_COMPARE = "compare_read_passages"
READ_PASSAGES_MODE_RESUME = "resume_read_passage"
REASON_READ_PASSAGES_COMPARE = "biblio_read_passages_compare_from_conversation"
REASON_READ_PASSAGES_RESUME = "biblio_read_passages_resume_from_conversation"
REASON_READ_PASSAGES_NO_EXACT = "biblio_read_passages_no_exact_conversation_content"
READ_PASSAGES_RESPONSE_SOURCE = "biblio_read_passages_response"
REASON_READ_PASSAGES_RESPONSE_META = "biblio_read_passages_response_meta"
REASON_READ_PASSAGES_SURFACE_INTRO_EMPTY = "biblio_read_passages_surface_intro_empty"
REASON_READ_PASSAGES_SURFACE_OUTRO_EMPTY = "biblio_read_passages_surface_outro_empty"
REASON_READ_PASSAGES_SURFACE_PLAN_MISSING = "biblio_read_passages_surface_plan_missing"

_READ_PASSAGES_HEADER = "[PASSAGES BIBLIO DEJA LUS]"
_READ_PASSAGES_FOOTER = "[/PASSAGES BIBLIO DEJA LUS]"
_READ_PASSAGES_MAX_PASSAGES = 2
_READ_PASSAGES_MAX_TOTAL_CHARS = 12_000
_HASH_LEN = 12


@dataclass(frozen=True)
class BiblioReadPassage:
    index: int
    content: str = field(repr=False, compare=False)
    content_hash: str = ""
    content_chars: int = 0
    source: str = ""
    exact_text_rendered: bool = False
    exact_text_hash: str = ""
    exact_text_chars: int = 0

    def to_observability(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "content_hash": self.content_hash,
            "content_chars": self.content_chars,
            "source": _safe_token(self.source),
            "exact_text_rendered": self.exact_text_rendered,
            "exact_text_hash": _strict_hash_12(self.exact_text_hash) or self.content_hash,
            "exact_text_chars": self.exact_text_chars or self.content_chars,
        }


@dataclass(frozen=True)
class BiblioReadPassagesPromptLane:
    message: dict[str, Any] | None = field(default=None, repr=False, compare=False)
    mode: str = ""
    reason_code: str = ""
    passages: tuple[BiblioReadPassage, ...] = field(default_factory=tuple, repr=False, compare=False)
    chars: int = 0
    max_passages: int = _READ_PASSAGES_MAX_PASSAGES
    max_total_chars: int = _READ_PASSAGES_MAX_TOTAL_CHARS

    @property
    def passage_count(self) -> int:
        return len(self.passages)

    def to_observability(self) -> dict[str, Any]:
        return {
            "present": self.message is not None,
            "mode": _safe_token(self.mode),
            "reason_code": _safe_token(self.reason_code),
            "passage_count": len(self.passages),
            "chars": self.chars,
            "max_passages": self.max_passages,
            "max_total_chars": self.max_total_chars,
            "hashes": [passage.content_hash for passage in self.passages],
            "exact_text_hashes": [
                _strict_hash_12(passage.exact_text_hash) or passage.content_hash
                for passage in self.passages
            ],
            "passage_chars": [passage.content_chars for passage in self.passages],
            "source": "conversation_assistant_messages",
        }

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
    answer_object: biblio_answer_object.BiblioAnswerObject | None = field(default=None, repr=False, compare=False)
    rendered_answer: biblio_answer_object.BiblioRenderedAnswer | None = field(default=None, repr=False, compare=False)
    final_response_lock: biblio_answer_object.BiblioFinalResponseLock | None = field(
        default=None,
        repr=False,
        compare=False,
    )

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
        preliminary_status = "deterministic_candidate" if decision.should_attempt else "not_selected"
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
        read_passages_lane = _build_read_passages_prompt_lane(
            user_msg=user_msg,
            state=state_before,
            recent_dialogue=recent_dialogue,
        )
        if read_passages_lane is not None:
            payload = observability_builder(
                enabled=True,
                used=True,
                query_kind=QUERY_KIND_READ_PASSAGES,
                prompt_lane=read_passages_lane,
                biblio_state=state_before if state_before.present else None,
                librarian_agent=librarian_agent_result,
                status="ready",
                reason_code=read_passages_lane.reason_code,
            )
            return BiblioChatResult(
                enabled=True,
                used=True,
                reason_code=read_passages_lane.reason_code,
                query_kind=QUERY_KIND_READ_PASSAGES,
                prompt_lane=read_passages_lane,
                biblio_state=state_before if state_before.present else None,
                librarian_agent_result=librarian_agent_result,
                observability_payload=payload,
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
                answer_object=agent_first_result.answer_object,
                state_after=state_after,
                state_transition=state_transition,
            )
            final_response_lock = biblio_answer_object.build_final_response_lock(
                agent_first_result.answer_object,
                agent_first_result.rendered_answer,
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
            payload = _with_answer_object_observability(
                payload,
                answer_object=agent_first_result.answer_object,
                rendered_answer=agent_first_result.rendered_answer,
                final_response_lock=final_response_lock,
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
                answer_object=agent_first_result.answer_object,
                rendered_answer=agent_first_result.rendered_answer,
                final_response_lock=final_response_lock,
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

        status = "disabled" if not decision.enabled else "not_selected"
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


def final_response_lock_for_result(result: BiblioChatResult) -> biblio_answer_object.BiblioFinalResponseLock | None:
    lock = result.final_response_lock
    if lock is not None:
        return lock
    if result.answer_object is None and result.rendered_answer is None:
        return None
    return biblio_answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)


def assistant_response_meta_for_result(result: BiblioChatResult) -> dict[str, Any] | None:
    if not (result.enabled and result.used and result.query_kind == QUERY_KIND_READ_PASSAGES):
        return None
    lane = result.prompt_lane
    if not isinstance(lane, BiblioReadPassagesPromptLane):
        return None
    surface_intro, surface_outro, surface_source = _agent_surface_envelope(result.librarian_agent_result)
    empty_reasons: list[str] = []
    if surface_source == "missing":
        empty_reasons.append(REASON_READ_PASSAGES_SURFACE_PLAN_MISSING)
    if not surface_intro:
        empty_reasons.append(REASON_READ_PASSAGES_SURFACE_INTRO_EMPTY)
    if not surface_outro:
        empty_reasons.append(REASON_READ_PASSAGES_SURFACE_OUTRO_EMPTY)
    return {
        "source": READ_PASSAGES_RESPONSE_SOURCE,
        "reason_code": REASON_READ_PASSAGES_RESPONSE_META,
        "biblio_answer_status": "ready",
        "biblio_render_mode": "read_passages_llm_response",
        "biblio_query_kind": QUERY_KIND_READ_PASSAGES,
        "biblio_read_passages_mode": _safe_token(lane.mode),
        "biblio_read_passages_reason_code": _safe_token(lane.reason_code),
        "biblio_read_passages_count": lane.passage_count,
        "biblio_read_passages_chars": lane.chars,
        "biblio_read_passages_hashes": [passage.content_hash for passage in lane.passages],
        "biblio_exact_text_rendered": False,
        "biblio_exact_text_chars": 0,
        "biblio_exact_text_hash": "",
        "biblio_final_lock_authorized": False,
        "biblio_final_lock_reason_code": "read_passages_llm_response_no_exact_lock",
        "biblio_surface_intro_present": bool(surface_intro),
        "biblio_surface_intro_chars": len(surface_intro),
        "biblio_surface_intro_hash": _short_hash(surface_intro) if surface_intro else "",
        "biblio_surface_outro_present": bool(surface_outro),
        "biblio_surface_outro_chars": len(surface_outro),
        "biblio_surface_outro_hash": _short_hash(surface_outro) if surface_outro else "",
        "biblio_surface_empty_reason_codes": empty_reasons,
    }


def assistant_response_envelope_for_result(result: BiblioChatResult) -> dict[str, str] | None:
    if not (result.enabled and result.used and result.query_kind == QUERY_KIND_READ_PASSAGES):
        return None
    if not isinstance(result.prompt_lane, BiblioReadPassagesPromptLane):
        return None
    surface_intro, surface_outro, _surface_source = _agent_surface_envelope(result.librarian_agent_result)
    if not surface_intro and not surface_outro:
        return None
    return {
        "surface_intro": surface_intro,
        "surface_outro": surface_outro,
    }


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
    answer_object: biblio_answer_object.BiblioAnswerObject | None = None,
    state_after: BiblioConversationState,
    state_transition: BiblioStateTransition | None,
) -> dict[str, str]:
    validation_plan = _agent_validation_plan(librarian_agent_result)
    product_method = str(
        getattr(answer_object, "product_method", "") or validation_plan.get("product_method") or ""
    ).strip()
    case_id = librarian_product_methods.normalize_case_id(
        getattr(answer_object, "case_id", "") or validation_plan.get("case_id")
    )
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


def _agent_surface_envelope(librarian_agent_result: Any) -> tuple[str, str, str]:
    comparison = getattr(librarian_agent_result, "agent_result", None)
    if comparison is None:
        return "", "", "missing"
    plan = getattr(comparison, "candidate_plan", None)
    if plan is not None:
        intro = _surface_text(getattr(plan, "surface_intro", ""))
        outro = _surface_text(getattr(plan, "surface_outro", ""))
        return intro, outro, "candidate_plan"
    intro = _surface_text(getattr(comparison, "surface_intro", ""))
    outro = _surface_text(getattr(comparison, "surface_outro", ""))
    if intro or outro:
        return intro, outro, "agent_validation"
    return "", "", "missing"


def _with_answer_object_observability(
    payload: Mapping[str, Any],
    *,
    answer_object: biblio_answer_object.BiblioAnswerObject | None,
    rendered_answer: biblio_answer_object.BiblioRenderedAnswer | None,
    final_response_lock: biblio_answer_object.BiblioFinalResponseLock | None,
) -> dict[str, Any]:
    observed = dict(payload)
    if answer_object is not None:
        observed["answer_object"] = answer_object.to_observability()
    if rendered_answer is not None:
        observed["rendered_answer"] = rendered_answer.to_observability()
    if final_response_lock is not None:
        observed["final_response_lock"] = final_response_lock.to_observability()
    return observed


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


def _build_read_passages_prompt_lane(
    *,
    user_msg: str,
    state: BiblioConversationState,
    recent_dialogue: Sequence[Mapping[str, Any]],
) -> BiblioReadPassagesPromptLane | None:
    passages = _recent_exact_biblio_passages(recent_dialogue)
    if not passages:
        return None
    dialogue_plan = librarian_dialogue_planner.plan_biblio_dialogue(
        user_msg,
        state=state,
        recent_dialogue=recent_dialogue,
    )
    intent = getattr(getattr(dialogue_plan, "intent", None), "intent", "")
    if intent == librarian_dialogue_planner.INTENT_COMPARE_PASSAGES:
        if len(passages) < 2:
            return None
        selected = passages[-2:]
        lane = _read_passages_lane(
            mode=READ_PASSAGES_MODE_COMPARE,
            reason_code=REASON_READ_PASSAGES_COMPARE,
            passages=selected,
        )
        return lane if lane.message is not None else None
    if intent == librarian_dialogue_planner.INTENT_EXPLAIN_PASSAGE:
        selected = passages[-1:]
        lane = _read_passages_lane(
            mode=READ_PASSAGES_MODE_RESUME,
            reason_code=REASON_READ_PASSAGES_RESUME,
            passages=selected,
        )
        return lane if lane.message is not None else None
    return None


def _recent_exact_biblio_passages(
    recent_dialogue: Sequence[Mapping[str, Any]],
) -> tuple[BiblioReadPassage, ...]:
    passages: list[BiblioReadPassage] = []
    for turn in recent_dialogue:
        if not isinstance(turn, Mapping):
            continue
        if str(turn.get("role") or "").strip() != "assistant":
            continue
        content = str(turn.get("content") or "")
        if not content:
            continue
        meta = _mapping(turn.get("meta"))
        source = str(turn.get("biblio_source") or meta.get("source") or "").strip()
        exact_text_rendered = _truthy(turn.get("biblio_exact_text_rendered")) or _truthy(
            meta.get("biblio_exact_text_rendered")
        )
        if source != biblio_answer_object.FINAL_RESPONSE_SOURCE or not exact_text_rendered:
            continue
        content_hash = _short_hash(content)
        exact_text_hash = _strict_hash_12(turn.get("biblio_exact_text_hash")) or _strict_hash_12(
            meta.get("biblio_exact_text_hash")
        )
        exact_text_chars = _optional_positive_int(turn.get("biblio_exact_text_chars")) or _optional_positive_int(
            meta.get("biblio_exact_text_chars")
        )
        passages.append(
            BiblioReadPassage(
                index=len(passages) + 1,
                content=content,
                content_hash=content_hash,
                content_chars=len(content),
                source=source,
                exact_text_rendered=True,
                exact_text_hash=exact_text_hash or content_hash,
                exact_text_chars=exact_text_chars or len(content),
            )
        )
    return tuple(passages[-_READ_PASSAGES_MAX_PASSAGES:])


def _read_passages_lane(
    *,
    mode: str,
    reason_code: str,
    passages: Sequence[BiblioReadPassage],
) -> BiblioReadPassagesPromptLane:
    selected = tuple(passages[:_READ_PASSAGES_MAX_PASSAGES])
    body_lines = [
        "Contrat de lecture conversationnelle:",
        "- Les textes ci-dessous sont des extraits Biblio exacts deja rendus dans cette conversation.",
        "- Utilise ces textes comme contenu conversationnel deja lu.",
        "- Ne lance pas de nouvelle recherche documentaire pour remplacer ces passages deja lus.",
        "- Reponds au dernier message utilisateur a partir de ces passages deja lus.",
        "- Pour comparer, donne une comparaison concise en prose ou en points; ne pretends pas produire un nouvel extrait exact.",
        "- Pour reprendre, repars du passage fourni et signale clairement toute limite de longueur si necessaire.",
    ]
    for index, passage in enumerate(selected, start=1):
        body_lines.extend(
            [
                f"Passage deja lu {index}",
                f"Signal: hash={passage.content_hash}; chars={passage.content_chars}",
                "Texte:",
                _neutralize_read_passage_tags(passage.content),
            ]
        )
    content = "\n".join([_READ_PASSAGES_HEADER, *body_lines, _READ_PASSAGES_FOOTER])
    if len(content) > _READ_PASSAGES_MAX_TOTAL_CHARS:
        return BiblioReadPassagesPromptLane(
            mode=mode,
            reason_code=REASON_READ_PASSAGES_NO_EXACT,
            passages=selected,
            chars=len(content),
        )
    return BiblioReadPassagesPromptLane(
        message={"role": "system", "content": content},
        mode=mode,
        reason_code=reason_code,
        passages=selected,
        chars=len(content),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_token(value: Any, *, max_chars: int = 96) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-.:/"
    return "".join(char for char in text[:max_chars] if char in allowed)


def _optional_positive_int(value: Any) -> int | None:
    if type(value) is int and value > 0:
        return value
    text = str(value or "").strip()
    if text.isdecimal():
        number = int(text)
        return number if number > 0 else None
    return None


def _surface_text(value: Any, *, max_chars: int = 600) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text or len(text) > max_chars:
        return ""
    return text


def _strict_hash_12(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != _HASH_LEN:
        return ""
    if any(char not in "0123456789abcdef" for char in text):
        return ""
    return text


def _short_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:_HASH_LEN]


def _neutralize_read_passage_tags(value: str) -> str:
    return str(value or "").replace(
        _READ_PASSAGES_FOOTER,
        "[BALISE BIBLIO NEUTRALISEE: /PASSAGES BIBLIO DEJA LUS]",
    ).replace(
        _READ_PASSAGES_HEADER,
        "[BALISE BIBLIO NEUTRALISEE: PASSAGES BIBLIO DEJA LUS]",
    )
