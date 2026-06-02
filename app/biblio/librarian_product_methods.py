"""Declarative product methods for the Biblio librarian contract.

Lot B introduces a stable layer above raw GET-only tools:

- product cases belong to the product grammar;
- product methods are the runtime-facing execution contract;
- raw tools stay technical primitives used by those methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import librarian_tools as tools


TRUTH_LEVEL_EXACT = "exact"
TRUTH_LEVEL_PLAUSIBLE = "plausible"
TRUTH_LEVEL_CONTEXTUAL = "contextuel"

EXECUTION_STATUS_SUCCESS = "success"
EXECUTION_STATUS_CLARIFICATION = "clarification"
EXECUTION_STATUS_NOT_FOUND = "not_found"
EXECUTION_STATUS_ERROR = "error"

PRODUCT_METHOD_CATALOG_LIST_FULL = "catalog_list_full"
PRODUCT_METHOD_CATALOG_LIST_BOUNDED = "catalog_list_bounded"
PRODUCT_METHOD_WORK_LOOKUP = "work_lookup"
PRODUCT_METHOD_DOCUMENT_TOC_SHOW = "document_toc_show"
PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE = "passage_extract_canonical_range"
PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE = "passage_set_current_reference"
PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK = "passage_search_in_work"
PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT = "passage_explain_current"
PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT = "passage_show_around_current"
PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES = "passage_compare_candidates"
PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT = "passage_move_previous_segment"
PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT = "passage_continue_next_segment"
PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK = "passage_origin_check"
PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK = "passage_search_external_work"
PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST = "clarify_biblio_request"

CASE_IDS = tuple(f"P{index:02d}" for index in range(1, 19))
CASE_ID_SET = frozenset(CASE_IDS)


@dataclass(frozen=True)
class BiblioProductMethodSpec:
    product_method: str
    case_ids: tuple[str, ...] = ()
    allowed_tool_names: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    truth_levels: tuple[str, ...] = ()
    execution_statuses: tuple[str, ...] = ()
    requires_tool_calls: bool = True


METHOD_SPECS = (
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_CATALOG_LIST_FULL,
        case_ids=("P01",),
        allowed_tool_names=(tools.TOOL_CATALOG_LIST,),
        preconditions=("biblio_enabled",),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_CATALOG_LIST_BOUNDED,
        case_ids=("P02",),
        allowed_tool_names=(tools.TOOL_CATALOG_LIST,),
        preconditions=("biblio_enabled",),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_WORK_LOOKUP,
        case_ids=("P03",),
        allowed_tool_names=(tools.TOOL_CATALOG_SEARCH, tools.TOOL_DOCUMENT_OPEN_SUMMARY, tools.TOOL_DOCUMENT_TOC),
        preconditions=("biblio_enabled", "work_signal_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
        case_ids=("P09",),
        allowed_tool_names=(tools.TOOL_CATALOG_SEARCH, tools.TOOL_DOCUMENT_OPEN_SUMMARY, tools.TOOL_DOCUMENT_TOC),
        preconditions=("biblio_enabled", "resolved_document_or_unique_match"),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
        case_ids=("P04",),
        allowed_tool_names=(
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("biblio_enabled", "canonical_locator_present", "resolved_document_or_unique_match"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_CONTEXTUAL),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE,
        case_ids=("P10",),
        allowed_tool_names=(
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("exact_passage_anchor_available",),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        case_ids=("P05", "P06", "P07", "P08"),
        allowed_tool_names=(
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("biblio_enabled", "theme_query_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE, TRUTH_LEVEL_CONTEXTUAL),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT,
        case_ids=("P11",),
        allowed_tool_names=(tools.TOOL_PASSAGE_CONTEXT,),
        preconditions=("current_passage_anchor_present",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT,
        case_ids=("P12",),
        allowed_tool_names=(tools.TOOL_PASSAGE_CONTEXT,),
        preconditions=("current_passage_anchor_present",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES,
        case_ids=(),
        allowed_tool_names=(tools.TOOL_PASSAGE_CONTEXT,),
        preconditions=("candidate_context_positions_present",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT,
        case_ids=("P13",),
        allowed_tool_names=(tools.TOOL_PAGE_READ, tools.TOOL_PASSAGE_CONTEXT),
        preconditions=("current_document_anchor_present", "navigation_anchor_present"),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT,
        case_ids=("P14",),
        allowed_tool_names=(tools.TOOL_PAGE_READ, tools.TOOL_PASSAGE_CONTEXT),
        preconditions=("current_document_anchor_present", "navigation_anchor_present"),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK,
        case_ids=("P15",),
        allowed_tool_names=(
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("current_passage_anchor_present",),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
        case_ids=("P16", "P17", "P18"),
        allowed_tool_names=(
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("biblio_enabled", "theme_query_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE, TRUTH_LEVEL_CONTEXTUAL),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST,
        case_ids=(),
        allowed_tool_names=(),
        preconditions=("insufficient_resolution",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL,),
        execution_statuses=(EXECUTION_STATUS_CLARIFICATION,),
        requires_tool_calls=False,
    ),
)

METHODS_BY_NAME = {spec.product_method: spec for spec in METHOD_SPECS}


def all_product_method_names() -> tuple[str, ...]:
    return tuple(METHODS_BY_NAME.keys())


def get_product_method_spec(product_method: str) -> BiblioProductMethodSpec | None:
    return METHODS_BY_NAME.get(str(product_method or "").strip())


def is_known_product_method(product_method: Any) -> bool:
    return get_product_method_spec(str(product_method or "").strip()) is not None


def normalize_case_id(case_id: Any) -> str:
    return str(case_id or "").strip().upper()


def is_known_case_id(case_id: Any) -> bool:
    text = normalize_case_id(case_id)
    return bool(text) and text in CASE_ID_SET


def method_accepts_case_id(product_method: str, case_id: str) -> bool:
    spec = get_product_method_spec(product_method)
    if spec is None:
        return False
    case = normalize_case_id(case_id)
    if not case:
        return True
    return case in spec.case_ids


def method_allows_tool(product_method: str, tool_name: str) -> bool:
    spec = get_product_method_spec(product_method)
    if spec is None:
        return False
    return str(tool_name or "").strip() in set(spec.allowed_tool_names)


def method_requires_tool_calls(product_method: str) -> bool:
    spec = get_product_method_spec(product_method)
    return bool(spec and spec.requires_tool_calls)


def default_case_id_for_method(product_method: str) -> str:
    spec = get_product_method_spec(product_method)
    if spec is None or len(spec.case_ids) != 1:
        return ""
    return spec.case_ids[0]


def infer_case_id_for_legacy_payload(
    *,
    product_method: Any,
    intent: Any,
    answer_mode: Any,
    tool_names: list[str] | tuple[str, ...],
) -> str:
    """Return a conservative case_id for repaired legacy payloads.

    Lot B guarantees the product_method layer first. During transition, a legacy
    payload may be honest about the method while still being unable to
    discriminate a precise case inside the family. In that situation we keep
    case_id empty instead of guessing.
    """

    _ = (product_method, intent, answer_mode, tool_names)
    return ""


def infer_product_method(*, intent: Any, answer_mode: Any, tool_names: list[str] | tuple[str, ...]) -> str:
    clean_intent = str(intent or "").strip()
    clean_answer_mode = str(answer_mode or "").strip()
    unique_tools = tuple(dict.fromkeys(str(name or "").strip() for name in tool_names if str(name or "").strip()))
    tool_set = set(unique_tools)

    if clean_answer_mode == "clarify" or clean_intent == "clarify" or not unique_tools:
        return PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST
    if clean_intent == "list_catalog":
        return PRODUCT_METHOD_CATALOG_LIST_BOUNDED
    if clean_intent == "show_table_of_contents":
        return PRODUCT_METHOD_DOCUMENT_TOC_SHOW
    if clean_intent == "resolve_work":
        return PRODUCT_METHOD_WORK_LOOKUP
    if clean_intent == "compare_passages":
        return PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES
    if clean_intent in {"extract_passage", "extract_range", "document_locator"} or tools.TOOL_LOCATE in tool_set:
        return PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE
    if clean_intent == "search_catalog":
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    if clean_answer_mode == "catalog_list":
        return PRODUCT_METHOD_CATALOG_LIST_BOUNDED
    if clean_answer_mode == "toc":
        return PRODUCT_METHOD_DOCUMENT_TOC_SHOW
    if clean_answer_mode in {"passage", "conceptual_search"}:
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    if tools.TOOL_DOCUMENT_TOC in tool_set:
        return PRODUCT_METHOD_DOCUMENT_TOC_SHOW
    if tools.TOOL_CATALOG_LIST in tool_set:
        return PRODUCT_METHOD_CATALOG_LIST_BOUNDED
    if tools.TOOL_PASSAGE_CONTEXT in tool_set or tools.TOOL_CATALOG_SEARCH in tool_set:
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    return ""
