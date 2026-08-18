"""Pure continuation decisions for Biblio product methods."""

from __future__ import annotations

from typing import Any, Sequence

from . import librarian_dialogue_navigation
from . import librarian_planner
from . import librarian_product_methods as product_methods
from . import librarian_tools
from .query_normalizer import fold_text


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


def allows_context_completion(plan: librarian_planner.BiblioLibrarianPlan) -> bool:
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


def wants_section_start_page_block(
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


def wants_section_complete_extraction(
    product_method: str,
    plan: librarian_planner.BiblioLibrarianPlan,
) -> bool:
    answer_mode = _text(getattr(plan, "answer_mode", ""))
    return (
        product_method == product_methods.PRODUCT_METHOD_SECTION_COMPLETE_EXTRACTION
        or product_methods.is_section_complete_extraction_answer_mode(answer_mode)
    )


def planned_section_query(plan: librarian_planner.BiblioLibrarianPlan) -> str:
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


def planned_locators(plan: librarian_planner.BiblioLibrarianPlan) -> tuple[str, ...]:
    values: list[str] = []
    for call in getattr(plan, "tool_calls", ()) or ():
        if call.tool_name not in {librarian_tools.TOOL_LOCATE, librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT}:
            continue
        for key in ("locator", "label", "locator_end"):
            value = _text(call.params.get(key))
            if value and value not in values:
                values.append(value)
    return tuple(values[:2])


def explicit_page_numbers(user_msg: str) -> tuple[int, ...]:
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


def fallback_search_query(
    deterministic_plan: Any,
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    context_available: bool,
) -> str:
    if context_available:
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


def _text(value: Any) -> str:
    return str(value or "").strip()
