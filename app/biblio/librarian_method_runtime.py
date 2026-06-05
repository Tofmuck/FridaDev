"""Method-driven runtime continuation for Biblio librarian plans.

Lot C keeps the bounded GET-only tool loop, but stops letting scattered
deterministic intents silently decide how an agent-first plan should continue.
The declared ``product_method`` is now the runtime unit that decides whether we
complete toward a document summary, a table of contents, or a bounded passage
context.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import librarian_dialogue_navigation
from . import librarian_planner
from . import librarian_product_methods as product_methods
from . import librarian_tools
from .query_normalizer import fold_text


_SUMMARY_COMPLETION_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION,
        product_methods.PRODUCT_METHOD_WORK_LOOKUP,
    }
)

_TOC_COMPLETION_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
        product_methods.PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
    }
)

_SEARCH_ASSISTED_TOC_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
    }
)

_CONTEXT_COMPLETION_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_EXTRACTION,
        product_methods.PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE,
        product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        product_methods.PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT,
        product_methods.PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT,
        product_methods.PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK,
        product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
    }
)

_SEARCH_ASSISTED_CONTEXT_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE,
        product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
    }
)

_SECTION_START_PAGE_BLOCK_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
    }
)

_SECTION_START_PAGE_BLOCK_ANSWER_MODES = frozenset(
    {
        "bounded_context_extract_start_of_section",
        "deliver_excerpt_context_from_section_start",
        "section_start_page_block_2",
    }
)

_SECTION_START_PAGE_COUNT = 2
_EXTRACTION_PAGE_REQUEST_MAX_PAGES = 3

_THEME_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "au",
        "aux",
        "ce",
        "ces",
        "cet",
        "cette",
        "dans",
        "de",
        "des",
        "du",
        "en",
        "et",
        "la",
        "le",
        "les",
        "l",
        "ou",
        "où",
        "par",
        "pour",
        "sa",
        "se",
        "ses",
        "son",
        "sur",
        "un",
        "une",
    }
)


def complete_product_method_loop(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    plan: librarian_planner.BiblioLibrarianPlan,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    deterministic_plan: Any,
    user_msg: str = "",
    conversation_state: Any = None,
) -> librarian_planner.BiblioLibrarianLoopResult:
    if loop_result.status not in {
        librarian_planner.STATUS_TOOL_EXECUTED,
        librarian_planner.STATUS_TOOL_FAILED,
        librarian_planner.STATUS_TOOL_REJECTED,
    }:
        return loop_result
    product_method = str(getattr(plan, "product_method", "") or "")
    if not product_method:
        return loop_result

    if product_method in _SUMMARY_COMPLETION_METHODS and not _has_document_summary(loop_result):
        doc_id = (
            _summary_completion_document_id(loop_result)
            if product_method == product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION
            else _first_document_id(loop_result)
        )
        if doc_id:
            loop_result = _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=librarian_tools.TOOL_DOCUMENT_OPEN_SUMMARY,
                params={"document_id": doc_id},
            )

    if product_method in _TOC_COMPLETION_METHODS and not _has_endpoint(loop_result, "chapters"):
        doc_id = (
            _summary_completion_document_id(loop_result)
            if product_method == product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE
            else _first_document_id(loop_result)
        )
        if not doc_id and product_method in _SEARCH_ASSISTED_TOC_METHODS:
            for _ in range(2):
                fallback_query = _fallback_search_query(deterministic_plan, loop_result)
                if not fallback_query:
                    break
                loop_result = _append_tool_call(
                    loop_result,
                    registry=registry,
                    tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                    params={
                        "query": fallback_query,
                        "limit": _positive_int(getattr(deterministic_plan, "limit", 0)) or 5,
                    },
                )
                doc_id = _first_document_id(loop_result)
                if doc_id:
                    break
        if doc_id:
            return _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=librarian_tools.TOOL_DOCUMENT_TOC,
                params={"document_id": doc_id, "limit": 500},
            )

    if _wants_section_start_page_block(product_method, plan):
        repaired = _complete_section_start_page_block(
            loop_result,
            plan=plan,
            registry=registry,
        )
        if _has_endpoint(repaired, "page"):
            return repaired
        loop_result = repaired

    if (
        product_method == product_methods.PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK
        and not _has_endpoint(loop_result, "context")
        and not _has_endpoint(loop_result, "page")
    ):
        tool_name, params = _origin_check_current_anchor_tool(conversation_state)
        if tool_name and params:
            repaired = _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=tool_name,
                params=params,
            )
            if _has_endpoint(repaired, "context") or _has_endpoint(repaired, "page"):
                return repaired
            loop_result = repaired

    if (
        product_method == product_methods.PRODUCT_METHOD_EXTRACTION
        and not _has_endpoint(loop_result, "page")
        and not _has_step_reason(loop_result, librarian_tools.REASON_PAGE_READ_DOCUMENT_SCOPE_CONFLICT)
    ):
        repaired = _complete_explicit_page_extraction(
            loop_result,
            registry=registry,
            user_msg=user_msg,
        )
        if _has_endpoint(repaired, "page"):
            return repaired
        loop_result = repaired

    if product_method == product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE:
        repaired = _complete_canonical_range_extraction(
            loop_result,
            plan=plan,
            registry=registry,
            deterministic_plan=deterministic_plan,
        )
        if _has_tool(repaired, librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT):
            return repaired
        loop_result = repaired

    if product_method in _CONTEXT_COMPLETION_METHODS and not _has_endpoint(loop_result, "context"):
        if product_method in _SEARCH_ASSISTED_CONTEXT_METHODS and _method_allows_context_completion(plan):
            for _ in range(3):
                if _first_context_params(loop_result):
                    break
                fallback_query = _fallback_search_query(deterministic_plan, loop_result)
                if not fallback_query:
                    break
                loop_result = _append_tool_call(
                    loop_result,
                    registry=registry,
                    tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                    params={
                        "query": fallback_query,
                        "limit": _positive_int(getattr(deterministic_plan, "limit", 0)) or 8,
                    },
                )
        context_params = {}
        if product_method == product_methods.PRODUCT_METHOD_EXTRACTION:
            context_params = _unique_scoped_search_hit_context_params(loop_result)
        elif _method_allows_context_completion(plan):
            context_params = _first_context_params(loop_result)
        if context_params:
            return _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=librarian_tools.TOOL_PASSAGE_CONTEXT,
                params=context_params,
            )

    return loop_result


def _method_allows_context_completion(plan: librarian_planner.BiblioLibrarianPlan) -> bool:
    product_method = _text(getattr(plan, "product_method", ""))
    answer_mode = _text(getattr(plan, "answer_mode", ""))
    if (
        answer_mode == "scoped_search"
        and product_method
        in {
            product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
            product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
        }
    ):
        return False
    return True


def _append_tool_call(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    tool_name: str,
    params: Mapping[str, Any],
) -> librarian_planner.BiblioLibrarianLoopResult:
    if loop_result.tool_call_count >= loop_result.options.max_tool_calls:
        return loop_result
    call = librarian_planner.BiblioLibrarianToolCall(tool_name=tool_name, method="GET", params=dict(params))
    planner = librarian_planner.BiblioLibrarianPlanner(registry)
    step = planner.run_tool_call(len(loop_result.steps), call)
    steps = (*loop_result.steps, step)
    status = librarian_planner.STATUS_TOOL_EXECUTED
    reason = librarian_planner.REASON_TOOL_EXECUTED
    if step.status != librarian_planner.STATUS_TOOL_EXECUTED:
        status = step.status
        reason = step.reason_code
    return librarian_planner.BiblioLibrarianLoopResult(
        status=status,
        reason_code=reason,
        steps=steps,
        options=loop_result.options,
        duration_ms=loop_result.duration_ms,
        fallback_deterministic=loop_result.fallback_deterministic,
    )


def _has_endpoint(loop_result: librarian_planner.BiblioLibrarianLoopResult, endpoint_kind: str) -> bool:
    return any(
        step.endpoint_kind == endpoint_kind and step.status == librarian_planner.STATUS_TOOL_EXECUTED
        for step in loop_result.steps
    )


def _has_tool(loop_result: librarian_planner.BiblioLibrarianLoopResult, tool_name: str) -> bool:
    return any(step.tool_name == tool_name for step in loop_result.steps)


def _has_step_reason(loop_result: librarian_planner.BiblioLibrarianLoopResult, reason_code: str) -> bool:
    return any(str(step.reason_code or "") == reason_code for step in loop_result.steps)


def _has_document_summary(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> bool:
    return any(
        step.tool_result is not None and bool(step.tool_result.document_summary)
        for step in loop_result.steps
    )


def _wants_section_start_page_block(
    product_method: str,
    plan: librarian_planner.BiblioLibrarianPlan,
) -> bool:
    answer_mode = _text(getattr(plan, "answer_mode", ""))
    if product_method == product_methods.PRODUCT_METHOD_EXTRACTION:
        return answer_mode in _SECTION_START_PAGE_BLOCK_ANSWER_MODES
    if product_method not in _SECTION_START_PAGE_BLOCK_METHODS:
        return False
    if answer_mode in _SECTION_START_PAGE_BLOCK_ANSWER_MODES:
        return True
    for call in getattr(plan, "tool_calls", ()) or ():
        if call.tool_name == librarian_tools.TOOL_SEARCH_CHAPTERS:
            return True
        if call.tool_name == librarian_tools.TOOL_LOCATE and _text(call.params.get("kind")) == "section":
            return True
    return False


def _first_document_id(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> str:
    for step in loop_result.steps:
        result = step.tool_result
        if result is None:
            continue
        direct = _text(getattr(result, "document_id", ""))
        if direct:
            return direct
        if result.document_summary:
            doc_id = _text(result.document_summary.get("document_id"))
            if doc_id:
                return doc_id
        for item in result.items:
            doc_id = _text(item.get("document_id"))
            if doc_id:
                return doc_id
    return ""


def _summary_completion_document_id(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> str:
    for step in loop_result.steps:
        result = step.tool_result
        if result is None:
            continue
        direct = _text(getattr(result, "document_id", ""))
        if direct:
            return direct
        if result.document_summary:
            doc_id = _text(result.document_summary.get("document_id"))
            if doc_id:
                return doc_id
        item_doc_id = _unique_item_document_id(result.items)
        if item_doc_id:
            return item_doc_id
    return ""


def _unique_item_document_id(items: Sequence[Mapping[str, Any]]) -> str:
    doc_ids: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        doc_id = _text(item.get("document_id"))
        if doc_id and doc_id not in doc_ids:
            doc_ids.append(doc_id)
    return doc_ids[0] if len(doc_ids) == 1 else ""


def _first_context_params(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> dict[str, Any]:
    for step in loop_result.steps:
        result = step.tool_result
        if result is None:
            continue
        for item in result.items:
            if not isinstance(item, Mapping):
                continue
            doc_id = _text(item.get("document_id"))
            paragraph_id = _int(item.get("paragraph_id"))
            page_no = _int(item.get("page_no"))
            para_no = _int(item.get("para_no"))
            if doc_id and (paragraph_id or (page_no and para_no)):
                params: dict[str, Any] = {"document_id": doc_id, "window_chars": 700}
                if paragraph_id:
                    params["paragraph_id"] = paragraph_id
                else:
                    params["page_no"] = page_no
                    params["para_no"] = para_no
                return params
    return {}


def _unique_scoped_search_hit_context_params(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
) -> dict[str, Any]:
    scoped_hits: list[Mapping[str, Any]] = []
    for step in loop_result.steps:
        result = step.tool_result
        if result is None or result.tool_name != librarian_tools.TOOL_CATALOG_SEARCH:
            continue
        scoped_doc_id = _text(getattr(result, "document_id", ""))
        if not scoped_doc_id:
            continue
        for item in result.items:
            if not isinstance(item, Mapping):
                continue
            doc_id = _text(item.get("document_id"))
            if doc_id != scoped_doc_id:
                continue
            scoped_hits.append(item)
    if len(scoped_hits) != 1:
        return {}
    hit = scoped_hits[0]
    doc_id = _text(hit.get("document_id"))
    paragraph_id = _int(hit.get("paragraph_id"))
    page_no = _int(hit.get("page_no"))
    para_no = _int(hit.get("para_no"))
    if not doc_id or not (paragraph_id or (page_no and para_no)):
        return {}
    params: dict[str, Any] = {"document_id": doc_id, "window_chars": 700}
    if paragraph_id:
        params["paragraph_id"] = paragraph_id
    else:
        params["page_no"] = page_no
        params["para_no"] = para_no
    return params


def _origin_check_current_anchor_tool(conversation_state: Any) -> tuple[str, dict[str, Any]]:
    last_result = getattr(conversation_state, "last_result", None)
    if not isinstance(last_result, Mapping):
        last_result = {}
    current_document = getattr(conversation_state, "current_document", None)
    if not isinstance(current_document, Mapping):
        current_document = {}
    doc_id = _text(last_result.get("document_id")) or _text(current_document.get("document_id"))
    if not doc_id:
        return "", {}

    paragraph_id = _int(last_result.get("paragraph_id")) or _int(getattr(conversation_state, "paragraph_id", None))
    page_no = _int(last_result.get("page_no")) or _int(getattr(conversation_state, "page_no", None))
    para_no = _int(last_result.get("para_no")) or _int(getattr(conversation_state, "para_no", None))
    if paragraph_id:
        return librarian_tools.TOOL_PASSAGE_CONTEXT, {
            "document_id": doc_id,
            "paragraph_id": paragraph_id,
            "window_chars": 700,
        }
    if page_no and para_no:
        return librarian_tools.TOOL_PASSAGE_CONTEXT, {
            "document_id": doc_id,
            "page_no": page_no,
            "para_no": para_no,
            "window_chars": 700,
        }
    if page_no:
        return librarian_tools.TOOL_PAGE_READ, {
            "document_id": doc_id,
            "page_no": page_no,
        }
    return "", {}


def _complete_section_start_page_block(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    plan: librarian_planner.BiblioLibrarianPlan,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
) -> librarian_planner.BiblioLibrarianLoopResult:
    doc_id = _first_document_id(loop_result)
    if not doc_id:
        return loop_result
    if _text(getattr(plan, "product_method", "")) == product_methods.PRODUCT_METHOD_EXTRACTION:
        return _append_section_start_pages(loop_result, registry=registry, document_id=doc_id)

    section_query = _planned_section_query(plan)
    if not section_query:
        return loop_result
    if not _has_endpoint(loop_result, "chapter_search"):
        loop_result = _append_tool_call(
            loop_result,
            registry=registry,
            tool_name=librarian_tools.TOOL_SEARCH_CHAPTERS,
            params={"document_id": doc_id, "query": section_query, "limit": 10},
        )
    start_page = _first_section_start_page(loop_result, document_id=doc_id)
    if start_page is None:
        return loop_result
    return _append_section_start_pages(loop_result, registry=registry, document_id=doc_id, start_page=start_page)


def _complete_explicit_page_extraction(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    user_msg: str,
) -> librarian_planner.BiblioLibrarianLoopResult:
    doc_id = _summary_completion_document_id(loop_result) or _first_document_id(loop_result)
    if not doc_id:
        return loop_result
    page_numbers = _explicit_page_numbers(user_msg)
    if not page_numbers:
        return loop_result
    available = max(0, loop_result.options.max_tool_calls - loop_result.tool_call_count)
    pages_to_read = tuple(
        page_no
        for page_no in page_numbers
        if not _has_page_read(loop_result, document_id=doc_id, page_no=page_no)
    )
    if not pages_to_read or len(pages_to_read) > available:
        return loop_result
    for page_no in pages_to_read:
        loop_result = _append_tool_call(
            loop_result,
            registry=registry,
            tool_name=librarian_tools.TOOL_PAGE_READ,
            params={"document_id": doc_id, "page_no": page_no},
        )
    return loop_result


def _complete_canonical_range_extraction(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    plan: librarian_planner.BiblioLibrarianPlan,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    deterministic_plan: Any,
) -> librarian_planner.BiblioLibrarianLoopResult:
    if _has_tool(loop_result, librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT) and not _has_tool_reason(
        loop_result,
        librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT,
        "locator_requires_document",
    ):
        return loop_result
    params = _canonical_range_extract_params(plan, deterministic_plan, loop_result)
    if not params:
        return loop_result
    return _append_tool_call(
        loop_result,
        registry=registry,
        tool_name=librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT,
        params=params,
    )


def _canonical_range_extract_params(
    plan: librarian_planner.BiblioLibrarianPlan,
    deterministic_plan: Any,
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
) -> dict[str, Any]:
    locator = _text(getattr(deterministic_plan, "locator", ""))
    locator_end = _text(getattr(deterministic_plan, "locator_end", ""))
    if not locator or not locator_end:
        planned = _planned_locators(plan)
        locator = locator or (planned[0] if planned else "")
        locator_end = locator_end or (planned[1] if len(planned) > 1 else "")
    if not locator or not locator_end:
        return {}

    doc_id = _summary_completion_document_id(loop_result)
    params: dict[str, Any] = {
        "locator": locator,
        "locator_end": locator_end,
        "kind": _text(getattr(deterministic_plan, "locator_kind", "")) or "stephanus",
        "max_passage_chars": 8000,
    }
    if doc_id:
        params["document_id"] = doc_id
    deterministic_doc_id = _text(getattr(deterministic_plan, "document_id", ""))
    if deterministic_doc_id and not params.get("document_id"):
        params["document_id"] = deterministic_doc_id
    for attr, key in (
        ("document_title", "document_title"),
        ("work_title", "work_title"),
        ("author", "author"),
    ):
        value = _text(getattr(deterministic_plan, attr, ""))
        if value:
            params[key] = value
    title = _text(getattr(deterministic_plan, "title", ""))
    if title and not (params.get("document_title") or params.get("work_title")):
        params["title"] = title
    query = _text(getattr(deterministic_plan, "catalogue_query", "")) or _text(
        getattr(deterministic_plan, "theme_query", "")
    )
    if query and not (doc_id or params.get("document_title") or params.get("work_title") or params.get("title")):
        params["query"] = query
    for attr, key in (
        ("locator_anchor_page", "locator_anchor_page"),
        ("locator_anchor_para", "locator_anchor_para"),
    ):
        value = _positive_int(getattr(deterministic_plan, attr, 0))
        if value:
            params[key] = value
    return (
        params
        if any(params.get(key) for key in ("document_id", "query", "title", "document_title", "work_title", "author"))
        else {}
    )


def _planned_locators(plan: librarian_planner.BiblioLibrarianPlan) -> tuple[str, ...]:
    values: list[str] = []
    for call in getattr(plan, "tool_calls", ()) or ():
        if call.tool_name not in {librarian_tools.TOOL_LOCATE, librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT}:
            continue
        for key in ("locator", "label", "locator_end"):
            value = _text(call.params.get(key))
            if value and value not in values:
                values.append(value)
    return tuple(values[:2])


def _explicit_page_numbers(user_msg: str) -> tuple[int, ...]:
    folded = fold_text(str(user_msg or ""))
    request = librarian_dialogue_navigation.page_request(folded)
    if request is None:
        return ()
    start, end = request
    if start <= 0 or end < start:
        return ()
    if (end - start) + 1 > _EXTRACTION_PAGE_REQUEST_MAX_PAGES:
        return ()
    return tuple(range(start, end + 1))


def _append_section_start_pages(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    document_id: str,
    start_page: int | None = None,
) -> librarian_planner.BiblioLibrarianLoopResult:
    effective_start = start_page or _first_section_start_page(loop_result, document_id=document_id)
    if effective_start is None:
        return loop_result
    end_page = _first_section_end_page(loop_result, document_id=document_id)
    requested_end = effective_start + _SECTION_START_PAGE_COUNT - 1
    if end_page is not None and end_page >= effective_start:
        requested_end = min(requested_end, end_page)
    pages_to_read = tuple(
        page_no
        for page_no in range(effective_start, requested_end + 1)
        if not _has_page_read(loop_result, document_id=document_id, page_no=page_no)
    )
    if len(pages_to_read) > max(0, loop_result.options.max_tool_calls - loop_result.tool_call_count):
        return loop_result
    for page_no in pages_to_read:
        loop_result = _append_tool_call(
            loop_result,
            registry=registry,
            tool_name=librarian_tools.TOOL_PAGE_READ,
            params={"document_id": document_id, "page_no": page_no},
        )
    return loop_result


def _planned_section_query(plan: librarian_planner.BiblioLibrarianPlan) -> str:
    for call in getattr(plan, "tool_calls", ()) or ():
        if call.tool_name == librarian_tools.TOOL_SEARCH_CHAPTERS:
            query = _text(call.params.get("query") or call.params.get("q"))
            if query:
                return query
    for call in getattr(plan, "tool_calls", ()) or ():
        if call.tool_name == librarian_tools.TOOL_LOCATE:
            label = _text(call.params.get("label") or call.params.get("locator"))
            if label:
                return label
    return ""


def _first_section_start_page(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    document_id: str,
) -> int | None:
    for step in reversed(loop_result.steps):
        result = step.tool_result
        if result is None:
            continue
        if result.tool_name == librarian_tools.TOOL_SECTION_BOUNDS and result.status == librarian_tools.STATUS_RESOLVED:
            result_doc_id = _text(getattr(result, "document_id", ""))
            if result_doc_id and result_doc_id != document_id:
                continue
            page_no = _page_from_section_bounds(result, key="start")
            if page_no is not None:
                return page_no
            continue
        if result.tool_name != librarian_tools.TOOL_SEARCH_CHAPTERS:
            continue
        for item in result.items:
            if not isinstance(item, Mapping):
                continue
            item_doc_id = _text(item.get("document_id"))
            if item_doc_id and item_doc_id != document_id:
                continue
            page_no = _int(item.get("page_no"))
            if page_no is not None and page_no >= 1:
                return page_no
    return None


def _first_section_end_page(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    document_id: str,
) -> int | None:
    for step in reversed(loop_result.steps):
        result = step.tool_result
        if (
            result is None
            or result.tool_name != librarian_tools.TOOL_SECTION_BOUNDS
            or result.status != librarian_tools.STATUS_RESOLVED
        ):
            continue
        result_doc_id = _text(getattr(result, "document_id", ""))
        if result_doc_id and result_doc_id != document_id:
            continue
        page_no = _page_from_section_bounds(result, key="end")
        if page_no is not None:
            return page_no
    return None


def _page_from_section_bounds(
    result: librarian_tools.BiblioLibrarianToolResult,
    *,
    key: str,
) -> int | None:
    interval_anchor = result.interval.get(key)
    if isinstance(interval_anchor, Mapping):
        page_no = _int(interval_anchor.get("page_no"))
        if page_no >= 1:
            return page_no
        unit_label = _text(interval_anchor.get("unit_label"))
        unit_no = _int(interval_anchor.get("unit_no"))
        if unit_label == "pages" and unit_no >= 1:
            return unit_no
    for item in result.items:
        if not isinstance(item, Mapping):
            continue
        page_no = _int(item.get(f"page_{key}"))
        if page_no >= 1:
            return page_no
        unit_label = _text(item.get("unit_label"))
        unit_no = _int(item.get(f"unit_{key}"))
        if unit_label == "pages" and unit_no >= 1:
            return unit_no
    return None


def _has_page_read(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    document_id: str,
    page_no: int,
) -> bool:
    for step in loop_result.steps:
        result = step.tool_result
        if result is None or result.tool_name != librarian_tools.TOOL_PAGE_READ:
            continue
        if _text(getattr(result, "document_id", "")) != document_id:
            continue
        for position in result.positions:
            if _int(position.get("page_no")) == page_no:
                return True
    return False


def _fallback_search_query(deterministic_plan: Any, loop_result: librarian_planner.BiblioLibrarianLoopResult) -> str:
    if _first_context_params(loop_result):
        return ""
    used = _used_search_queries(loop_result)
    for raw_query in _deterministic_queries(deterministic_plan):
        for candidate in _fallback_query_candidates(raw_query):
            if candidate and candidate not in used:
                return candidate
    return ""


def _used_search_queries(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> set[str]:
    queries: set[str] = set()
    for step in loop_result.steps:
        call = step.tool_call
        if call is None or call.tool_name != librarian_tools.TOOL_CATALOG_SEARCH:
            continue
        for key in ("query", "q"):
            value = _text(call.params.get(key))
            if value:
                queries.add(value)
    return queries


def _deterministic_queries(deterministic_plan: Any) -> tuple[str, ...]:
    values: list[str] = []
    for attr in (
        "theme_query_variants",
        "catalogue_query_variants",
        "work_title_variants",
        "document_title_variants",
    ):
        raw = getattr(deterministic_plan, attr, ())
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for item in raw:
                value = _text(item)
                if value and value not in values:
                    values.append(value)
    for attr in ("theme_query", "catalogue_query", "work_title", "document_title", "author"):
        value = _text(getattr(deterministic_plan, attr, ""))
        if value and value not in values:
            values.append(value)
    values.sort(key=_query_priority)
    return tuple(values)


def _has_tool_reason(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    tool_name: str,
    reason_code: str,
) -> bool:
    return any(
        step.tool_name == tool_name and str(step.reason_code or "") == reason_code
        for step in loop_result.steps
    )


def _query_priority(value: str) -> tuple[int, int]:
    return (0 if _has_non_ascii(value) else 1, len(value))


def _has_non_ascii(value: str) -> bool:
    return any(ord(char) > 127 for char in value)


def _fallback_query_candidates(raw_query: str) -> tuple[str, ...]:
    query = _text(raw_query)
    if not query:
        return ()
    tokens = [
        token
        for token in _query_tokens(query)
        if len(token) > 2 and token.casefold() not in _THEME_QUERY_STOPWORDS
    ]
    candidates: list[str] = []
    if len(tokens) >= 3:
        candidates.append(" ".join(tokens[-3:]))
    if len(tokens) >= 2:
        candidates.append(" ".join(tokens[-2:]))
    if tokens:
        candidates.append(tokens[-1])
    cleaned = " ".join(tokens)
    if cleaned:
        candidates.append(cleaned)
    if not candidates and query:
        candidates.append(query)
    allow_original = len(tokens) == 1
    out: list[str] = []
    for candidate in candidates:
        if not candidate or (not allow_original and candidate == query) or candidate in out:
            continue
        out.append(candidate)
    return tuple(out)


def _query_tokens(query: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in query:
        if char.isalnum() or char in {"'", "’", "-"}:
            current.append(char)
            continue
        if current:
            tokens.append("".join(current).strip("'’-."))
            current = []
    if current:
        tokens.append("".join(current).strip("'’-."))
    return tuple(token for token in tokens if token)


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _text(value: Any) -> str:
    return str(value or "").strip()
