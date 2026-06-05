"""Bounded GET-only Catalogue tools for the future Biblio librarian agent."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import catalogue_client as catalogue
from . import passage_extractor
from .document_resolver import BiblioResolveRequest
from .passage_extractor import BiblioPassageRequest


TOOL_SEARCH_DOCUMENT = "search_document"
TOOL_SEARCH_WORK = "search_work"
TOOL_SEARCH_SECTION = "search_section"
TOOL_RESOLVE_WORK = "resolve_work"
TOOL_RESOLVE_SECTION = "resolve_section"
TOOL_SECTION_BOUNDS = "section_bounds"
TOOL_CATALOG_LIST = "catalog_list"
TOOL_CATALOG_SEARCH = "catalog_search"
TOOL_SEARCH_CHAPTERS = "search_chapters"
TOOL_DOCUMENT_OPEN_SUMMARY = "document_open_summary"
TOOL_DOCUMENT_TOC = "document_toc"
TOOL_PAGE_READ = "page_read"
TOOL_LOCATE = "locate"
TOOL_PASSAGE_CONTEXT = "passage_context"
TOOL_CANONICAL_RANGE_EXTRACT = "canonical_range_extract"

LOT2_LIBRARY_TOOL_NAMES = (
    TOOL_SEARCH_DOCUMENT,
    TOOL_SEARCH_WORK,
    TOOL_SEARCH_SECTION,
    TOOL_RESOLVE_WORK,
    TOOL_RESOLVE_SECTION,
    TOOL_SECTION_BOUNDS,
)

LOT3_TOOL_NAMES = (
    *LOT2_LIBRARY_TOOL_NAMES,
    TOOL_CATALOG_LIST,
    TOOL_CATALOG_SEARCH,
    TOOL_SEARCH_CHAPTERS,
    TOOL_DOCUMENT_OPEN_SUMMARY,
    TOOL_DOCUMENT_TOC,
    TOOL_PAGE_READ,
    TOOL_LOCATE,
    TOOL_PASSAGE_CONTEXT,
    TOOL_CANONICAL_RANGE_EXTRACT,
)

FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "page",
        "latest/page",
        "latest/context",
        "export",
        "export/chunk",
        "export_chunk",
        "document",
        "document_read",
        "settings",
        "settings/reset",
        "progress/recent/clear",
    }
)

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_INCOHERENT_CATALOGUE = "incoherent_catalogue"
STATUS_RESOLVED = "resolved"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_NOT_FOUND = "not_found"

REASON_OK = "ok"
REASON_RESOLVED = "resolved"
REASON_AMBIGUOUS = "ambiguous"
REASON_NOT_FOUND = "not_found"
REASON_UNKNOWN_TOOL = "unknown_tool"
REASON_FORBIDDEN_TOOL = "forbidden_tool"
REASON_INVALID_PARAMETER = "invalid_parameter"
REASON_MISSING_DOCUMENT_ID = "missing_document_id"
REASON_MISSING_QUERY = "missing_query"
REASON_MISSING_POSITION = "missing_position"
REASON_TIMEOUT = "timeout"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"
REASON_UNEXPECTED_STATUS = "unexpected_status"
REASON_INVALID_JSON = "invalid_json"
REASON_BUDGET_OR_LIMIT_EXCEEDED = "budget_or_limit_exceeded"
REASON_CONTEXT_INCOHERENT = "biblio_librarian_context_incoherent_catalogue"
REASON_PAGE_INCOHERENT = "biblio_librarian_page_incoherent_catalogue"
REASON_SECTION_BOUNDS_UNAVAILABLE = "section_bounds_unavailable"
REASON_WORK_ALIAS_MISSING = "work_alias_missing"
REASON_INTERNAL_WORK_UNRESOLVED = "internal_work_unresolved"
REASON_SECTION_ALIAS_MISSING = "section_alias_missing"
REASON_PRIMARY_TEXT_ROLE_UNKNOWN = "primary_text_role_unknown"
REASON_SCOPED_SEARCH_SCOPE_MISSING = "scoped_search_scope_missing"
REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE = "scoped_search_no_hits_in_scope"
REASON_PAGE_READ_DOCUMENT_SCOPE_CONFLICT = "page_read_document_scope_conflict"
REASON_EXTRACTION_ANCHOR_MISSING = "extraction_anchor_missing"
REASON_EXTRACTION_MECHANICAL_TEXT_MISSING = "extraction_mechanical_text_missing"
REASON_EXTRACTION_SOURCE_TOOL_UNSUPPORTED = "extraction_source_tool_unsupported"
REASON_EXTRACTION_DOCUMENT_MISMATCH = "extraction_document_mismatch"
REASON_EXTRACTION_PAGE_RANGE_INCOMPLETE = "extraction_page_range_incomplete"
REASON_EXTRACTION_PAGE_RANGE_TOO_LONG = "extraction_page_range_too_long"
REASON_EXTRACTION_MIXED_BLOCK_TYPES = "extraction_mixed_block_types_unsupported"
REASON_CANONICAL_RANGE_BOUND_MISSING = "canonical_range_bound_missing"
REASON_CANONICAL_RANGE_INCOMPLETE = "canonical_range_incomplete"

ENDPOINT_CANONICAL_RANGE = "canonical_range"

_ENDPOINT_BY_TOOL = {
    TOOL_SEARCH_DOCUMENT: catalogue.ENDPOINT_CATALOG,
    TOOL_SEARCH_WORK: catalogue.ENDPOINT_CATALOG,
    TOOL_SEARCH_SECTION: catalogue.ENDPOINT_CHAPTERS,
    TOOL_RESOLVE_WORK: catalogue.ENDPOINT_CATALOG,
    TOOL_RESOLVE_SECTION: catalogue.ENDPOINT_CHAPTERS,
    TOOL_SECTION_BOUNDS: catalogue.ENDPOINT_CHAPTERS,
    TOOL_CATALOG_LIST: catalogue.ENDPOINT_CATALOG,
    TOOL_CATALOG_SEARCH: catalogue.ENDPOINT_SEARCH,
    TOOL_SEARCH_CHAPTERS: catalogue.ENDPOINT_CHAPTER_SEARCH,
    TOOL_DOCUMENT_OPEN_SUMMARY: catalogue.ENDPOINT_METADATA,
    TOOL_DOCUMENT_TOC: catalogue.ENDPOINT_CHAPTERS,
    TOOL_PAGE_READ: catalogue.ENDPOINT_PAGE,
    TOOL_LOCATE: catalogue.ENDPOINT_LOCATE,
    TOOL_PASSAGE_CONTEXT: catalogue.ENDPOINT_CONTEXT,
    TOOL_CANONICAL_RANGE_EXTRACT: ENDPOINT_CANONICAL_RANGE,
}
_QUERY_MAX = 240
_LOCATOR_MAX = 120
_DOC_ID_MAX = 160
_OFFSET_MAX = 100_000
_PAGE_TEXT_MAX_CHARS = 2_500
_MAX_CANONICAL_RANGE_CHARS = passage_extractor.MAX_MAX_PASSAGE_CHARS


class BiblioLibrarianToolError(Exception):
    def __init__(
        self,
        *,
        tool_name: str = "",
        reason_code: str = REASON_INVALID_PARAMETER,
        endpoint_kind: str = "",
        status_code: int | None = None,
        doc_id: str = "",
        error_class: str = "",
        detail: str = "",
    ) -> None:
        self.tool_name = _clean_tool_name(tool_name)
        self.reason_code = reason_code
        self.endpoint_kind = endpoint_kind
        self.status_code = status_code
        self.doc_id_short = catalogue.short_doc_id(doc_id)
        self.error_class = error_class
        self.detail = detail
        super().__init__(self.__str__())

    def __str__(self) -> str:
        parts = [self.reason_code]
        for key, value in (
            ("tool", self.tool_name),
            ("endpoint", self.endpoint_kind),
            ("doc_id_short", self.doc_id_short),
            ("error_class", self.error_class),
            ("detail", self.detail),
        ):
            if value:
                parts.append(f"{key}={value}")
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        return " ".join(parts)

    def to_observability(self) -> dict[str, Any]:
        return _clean_observation(
            {
                "tool_name": self.tool_name,
                "endpoint_kind": self.endpoint_kind,
                "status": STATUS_ERROR,
                "reason_code": self.reason_code,
                "status_code": self.status_code,
                "doc_id_short": self.doc_id_short,
                "error_class": self.error_class,
            }
        )


@dataclass(frozen=True)
class BiblioLibrarianToolObservation:
    tool_name: str
    endpoint_kind: str
    status: str
    reason_code: str
    fields: dict[str, Any] = field(default_factory=dict)

    def to_observability(self) -> dict[str, Any]:
        return _clean_observation(
            {
                "tool_name": self.tool_name,
                "endpoint_kind": self.endpoint_kind,
                "status": self.status,
                "reason_code": self.reason_code,
                **self.fields,
            }
        )


@dataclass(frozen=True)
class BiblioLibrarianToolResult:
    tool_name: str
    status: str
    reason_code: str
    endpoint_kind: str
    observation: BiblioLibrarianToolObservation
    document_id: str = field(default="", repr=False, compare=False)
    items: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    document_summary: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    chapter_hint: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    chapters: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    positions: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    anchors: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    interval: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    context_text: str = field(default="", repr=False, compare=False)
    page_text: str = field(default="", repr=False, compare=False)

    def to_observability(self) -> dict[str, Any]:
        return self.observation.to_observability()


class BiblioLibrarianToolRegistry:
    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def tool_names(self) -> tuple[str, ...]:
        return LOT3_TOOL_NAMES

    def run(self, tool_name: str, params: Mapping[str, Any] | None = None) -> BiblioLibrarianToolResult:
        clean_name = _validate_tool_name(tool_name)
        handlers = {
            TOOL_SEARCH_DOCUMENT: self._search_document,
            TOOL_SEARCH_WORK: self._search_work,
            TOOL_SEARCH_SECTION: self._search_section,
            TOOL_RESOLVE_WORK: self._resolve_work,
            TOOL_RESOLVE_SECTION: self._resolve_section,
            TOOL_SECTION_BOUNDS: self._section_bounds,
            TOOL_CATALOG_LIST: self._catalog_list,
            TOOL_CATALOG_SEARCH: self._catalog_search,
            TOOL_SEARCH_CHAPTERS: self._search_chapters,
            TOOL_DOCUMENT_OPEN_SUMMARY: self._document_open_summary,
            TOOL_DOCUMENT_TOC: self._document_toc,
            TOOL_PAGE_READ: self._page_read,
            TOOL_LOCATE: self._locate,
            TOOL_PASSAGE_CONTEXT: self._passage_context,
            TOOL_CANONICAL_RANGE_EXTRACT: self._canonical_range_extract,
        }
        return handlers[clean_name](dict(params or {}))

    def _search_document(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        return _run_library_tool(self._client, TOOL_SEARCH_DOCUMENT, params)

    def _search_work(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        return _run_library_tool(self._client, TOOL_SEARCH_WORK, params)

    def _search_section(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        return _run_library_tool(self._client, TOOL_SEARCH_SECTION, params)

    def _resolve_work(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        return _run_library_tool(self._client, TOOL_RESOLVE_WORK, params)

    def _resolve_section(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        return _run_library_tool(self._client, TOOL_RESOLVE_SECTION, params)

    def _section_bounds(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        return _run_library_tool(self._client, TOOL_SECTION_BOUNDS, params)

    def _catalog_list(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_CATALOG_LIST
        query = _text(params, "q", tool=tool, max_chars=_QUERY_MAX)
        limit = _integer(params.get("limit", 100), tool=tool, name="limit", minimum=1, maximum=100)
        offset = _integer(params.get("offset", 0), tool=tool, name="offset", minimum=0, maximum=_OFFSET_MAX)
        try:
            response = self._client.catalog(q=query, limit=limit, offset=offset)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        items = tuple(_catalog_item(item) for item in _items(response.payload, "items"))
        if query and not items and offset == 0:
            try:
                response = self._client.catalog(limit=limit, offset=offset)
            except catalogue.CatalogueClientError as exc:
                return _error_result(tool, exc)
            items = tuple(_catalog_item(item) for item in _items(response.payload, "items"))
        return _ok_result(tool, response, items=items, offset=offset, limit=limit, query=query)

    def _catalog_search(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_CATALOG_SEARCH
        query = _required_text(params, ("q", "query"), tool=tool, max_chars=_QUERY_MAX)
        limit = _integer(params.get("limit", 20), tool=tool, name="limit", minimum=1, maximum=50)
        _integer(params.get("offset", 0), tool=tool, name="offset", minimum=0, maximum=0)
        doc_id = _doc_id(params, tool=tool)
        try:
            response = self._client.search(query, limit=limit)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        items = tuple(_search_item(item) for item in _items(response.payload, "results"))
        if doc_id:
            items = tuple(item for item in items if _string(item.get("document_id")) == doc_id)
        return _ok_result(tool, response, items=items, limit=limit, query=query, doc_id=doc_id)

    def _search_chapters(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_SEARCH_CHAPTERS
        query = _required_text(params, ("q", "query"), tool=tool, max_chars=_QUERY_MAX)
        limit = _integer(params.get("limit", 20), tool=tool, name="limit", minimum=1, maximum=50)
        _integer(params.get("offset", 0), tool=tool, name="offset", minimum=0, maximum=0)
        doc_id = _doc_id(params, tool=tool)
        try:
            response = self._client.search_chapters(query, limit=limit)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        items = tuple(_chapter_search_item(item) for item in _items(response.payload, "results"))
        if doc_id:
            items = tuple(item for item in items if _string(item.get("document_id")) == doc_id)
        return _ok_result(tool, response, items=items, limit=limit, query=query, doc_id=doc_id)

    def _document_open_summary(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_DOCUMENT_OPEN_SUMMARY
        doc_id = _doc_id(params, tool=tool)
        query = _text(params, "q", tool=tool, max_chars=_QUERY_MAX) or _text(
            params,
            "query",
            tool=tool,
            max_chars=_QUERY_MAX,
        )
        if not doc_id and not query:
            raise _tool_error(tool, REASON_MISSING_DOCUMENT_ID)
        if doc_id:
            try:
                response = self._client.metadata(doc_id)
            except catalogue.CatalogueClientError as exc:
                return _error_result(tool, exc)
            summary = _document_summary(response.payload, doc_id)
            return _ok_result(tool, response, document_summary=summary, doc_id=doc_id)

        limit = _integer(params.get("limit", 5), tool=tool, name="limit", minimum=1, maximum=20)
        try:
            response = self._client.catalog(q=query, limit=limit, offset=0)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc, endpoint_kind=catalogue.ENDPOINT_CATALOG)
        items = tuple(_catalog_item(item) for item in _items(response.payload, "items"))
        return _ok_result(tool, response, items=items, limit=limit, query=query)

    def _document_toc(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_DOCUMENT_TOC
        doc_id = _required_doc_id(params, tool=tool)
        limit = _integer(params.get("limit", 500), tool=tool, name="limit", minimum=1, maximum=500)
        offset = _integer(params.get("offset", 0), tool=tool, name="offset", minimum=0, maximum=_OFFSET_MAX)
        try:
            response = self._client.chapters(doc_id, limit=limit, offset=offset)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        chapters = tuple(_chapter_item(item) for item in _items(response.payload, "chapters"))
        return _ok_result(tool, response, chapters=chapters, offset=offset, limit=limit, doc_id=doc_id)

    def _page_read(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_PAGE_READ
        doc_id = _required_doc_id(params, tool=tool)
        page_no = _integer(
            params.get("page_no"),
            tool=tool,
            name="page_no",
            minimum=catalogue.PAGE_NO_MIN,
            maximum=catalogue.PAGE_NO_MAX,
        )
        try:
            response = self._client.page(doc_id, page_no)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        if _string(response.payload.get("document_id")) != doc_id:
            return _incoherent_page_result(tool, response, doc_id)
        page_text = _page_text(response.payload)
        summary = _page_document_summary(response.payload, doc_id)
        chapter_hint = _chapter_hint(response.payload)
        return _ok_result(
            tool,
            response,
            document_summary=summary,
            chapter_hint=chapter_hint,
            positions=(_position({"page_no": page_no}),),
            doc_id=doc_id,
            content=page_text,
            page_text=page_text,
            extra_fields={
                "paragraph_count": _raw_int(response.payload.get("paragraph_count")),
                "current_chapter_no": _raw_int(chapter_hint.get("chapter_no")),
                "current_chapter_unit_start": _raw_int(chapter_hint.get("unit_start")),
                "current_chapter_unit_end": _raw_int(chapter_hint.get("unit_end")),
                "next_chapter_no": _raw_int(chapter_hint.get("next_chapter_no")),
                "chapter_source": _string(chapter_hint.get("source")),
                "page_truncated": bool(
                    isinstance(response.payload.get("raw_text"), str)
                    and len(str(response.payload.get("raw_text") or "")) > len(page_text)
                ),
            },
        )

    def _locate(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_LOCATE
        doc_id = _required_doc_id(params, tool=tool)
        locator = _required_text(params, ("locator", "label"), tool=tool, max_chars=_LOCATOR_MAX)
        kind = _text(params, "kind", tool=tool, max_chars=40) or "stephanus"
        limit = _integer(params.get("limit", 200), tool=tool, name="limit", minimum=1, maximum=200)
        try:
            response = self._client.locate(doc_id, locator, kind=kind, limit=limit)
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        positions = tuple(_position(item) for item in _locate_items(response.payload))
        return _ok_result(tool, response, positions=positions, doc_id=doc_id, locator=locator, limit=limit)

    def _passage_context(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_PASSAGE_CONTEXT
        doc_id = _required_doc_id(params, tool=tool)
        paragraph_id = _optional_integer(
            params,
            "paragraph_id",
            tool=tool,
            minimum=catalogue.CONTEXT_PARAGRAPH_ID_MIN,
            maximum=catalogue.CONTEXT_PARAGRAPH_ID_MAX,
        )
        page_no = _optional_integer(
            params,
            "page_no",
            tool=tool,
            minimum=catalogue.CONTEXT_PAGE_NO_MIN,
            maximum=catalogue.CONTEXT_PAGE_NO_MAX,
        )
        para_no = _optional_integer(
            params,
            "para_no",
            tool=tool,
            minimum=catalogue.CONTEXT_PARA_NO_MIN,
            maximum=catalogue.CONTEXT_PARA_NO_MAX,
        )
        if paragraph_id is None and (page_no is None or para_no is None):
            raise _tool_error(tool, REASON_MISSING_POSITION, doc_id=doc_id)
        char_offset = _integer(
            params.get("char_offset", 0),
            tool=tool,
            name="char_offset",
            minimum=catalogue.CONTEXT_CHAR_OFFSET_MIN,
            maximum=catalogue.CONTEXT_CHAR_OFFSET_MAX,
        )
        window_chars = _integer(
            params.get("window_chars", 700),
            tool=tool,
            name="window_chars",
            minimum=catalogue.CONTEXT_WINDOW_CHARS_MIN,
            maximum=2_000,
        )
        try:
            response = self._client.context(
                doc_id,
                page_no=page_no,
                para_no=para_no,
                paragraph_id=paragraph_id,
                char_offset=char_offset,
                window_chars=window_chars,
            )
        except catalogue.CatalogueClientError as exc:
            return _error_result(tool, exc)
        if _string(response.payload.get("document_id")) != doc_id:
            return _incoherent_context_result(tool, response, doc_id)
        context_text = _context_text(response.payload)
        chapter_hint = _chapter_hint(response.payload)
        positions = (
            _position(
                {
                    "page_no": page_no,
                    "para_no": para_no,
                    "paragraph_id": paragraph_id,
                    "char_offset": char_offset,
                    "window_chars": window_chars,
                }
            ),
        )
        return _ok_result(
            tool,
            response,
            chapter_hint=chapter_hint,
            positions=positions,
            context_text=context_text,
            doc_id=doc_id,
            content=context_text,
            extra_fields={
                "current_chapter_no": _raw_int(chapter_hint.get("chapter_no")),
                "current_chapter_unit_start": _raw_int(chapter_hint.get("unit_start")),
                "current_chapter_unit_end": _raw_int(chapter_hint.get("unit_end")),
                "next_chapter_no": _raw_int(chapter_hint.get("next_chapter_no")),
                "chapter_source": _string(chapter_hint.get("source")),
            },
        )

    def _canonical_range_extract(self, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
        tool = TOOL_CANONICAL_RANGE_EXTRACT
        locator = _required_text(params, ("locator", "label"), tool=tool, max_chars=_LOCATOR_MAX)
        locator_end = _required_text(params, ("locator_end",), tool=tool, max_chars=_LOCATOR_MAX)
        kind = _text(params, "kind", tool=tool, max_chars=40) or "stephanus"
        doc_id = _doc_id(params, tool=tool)
        query = _text(params, "query", tool=tool, max_chars=_QUERY_MAX) or _text(
            params,
            "q",
            tool=tool,
            max_chars=_QUERY_MAX,
        )
        title = _text(params, "title", tool=tool, max_chars=_QUERY_MAX)
        document_title = _text(params, "document_title", tool=tool, max_chars=_QUERY_MAX) or query
        work_title = _text(params, "work_title", tool=tool, max_chars=_QUERY_MAX)
        author = _text(params, "author", tool=tool, max_chars=_QUERY_MAX)
        locator_anchor_page = _optional_integer(
            params,
            "locator_anchor_page",
            tool=tool,
            minimum=catalogue.PAGE_NO_MIN,
            maximum=catalogue.PAGE_NO_MAX,
        )
        locator_anchor_para = _optional_integer(
            params,
            "locator_anchor_para",
            tool=tool,
            minimum=catalogue.CONTEXT_PARA_NO_MIN,
            maximum=catalogue.CONTEXT_PARA_NO_MAX,
        )
        max_passage_chars = _integer(
            params.get("max_passage_chars", _MAX_CANONICAL_RANGE_CHARS),
            tool=tool,
            name="max_passage_chars",
            minimum=passage_extractor.MIN_MAX_PASSAGE_CHARS,
            maximum=_MAX_CANONICAL_RANGE_CHARS,
        )
        request = BiblioPassageRequest(
            resolve_request=BiblioResolveRequest(
                document_id=doc_id,
                title=title,
                document_title=document_title,
                work_title=work_title,
                author=author,
                locator=locator,
                locator_end=locator_end,
                locator_kind=kind,
                locator_anchor_page=locator_anchor_page,
                locator_anchor_para=locator_anchor_para,
            ),
            max_passage_chars=max_passage_chars,
        )
        result = passage_extractor.BiblioPassageExtractor(self._client).extract(request)
        return _canonical_range_result(tool, result)


def build_librarian_tool_registry(client: Any | None = None) -> BiblioLibrarianToolRegistry:
    return BiblioLibrarianToolRegistry(client or catalogue.CatalogueClient())


def _run_library_tool(client: Any, tool_name: str, params: Mapping[str, Any]) -> BiblioLibrarianToolResult:
    from . import librarian_library_tools

    return librarian_library_tools.run_library_tool(client, tool_name, params)


def _validate_tool_name(tool_name: str) -> str:
    clean_name = _clean_tool_name(tool_name)
    if clean_name in FORBIDDEN_TOOL_NAMES:
        raise BiblioLibrarianToolError(tool_name=clean_name, reason_code=REASON_FORBIDDEN_TOOL)
    if clean_name not in LOT3_TOOL_NAMES:
        raise BiblioLibrarianToolError(tool_name=clean_name, reason_code=REASON_UNKNOWN_TOOL)
    return clean_name


def _ok_result(
    tool: str,
    response: catalogue.CatalogueResponse,
    *,
    items: tuple[dict[str, Any], ...] = (),
    document_summary: dict[str, Any] | None = None,
    chapter_hint: dict[str, Any] | None = None,
    chapters: tuple[dict[str, Any], ...] = (),
    positions: tuple[dict[str, Any], ...] = (),
    anchors: tuple[dict[str, Any], ...] = (),
    interval: Mapping[str, Any] | None = None,
    context_text: str = "",
    page_text: str = "",
    offset: int = 0,
    limit: int = 0,
    query: str = "",
    locator: str = "",
    doc_id: str = "",
    content: str = "",
    extra_fields: Mapping[str, Any] | None = None,
) -> BiblioLibrarianToolResult:
    visible_items = items or chapters or positions
    fields = {
        "status_code": response.status_code,
        "duration_ms": response.duration_ms,
        "result_count": response.result_count,
        "total_count": _total_count(response.payload),
        "displayed_count": len(visible_items) if visible_items else None,
        "truncated": _truncated(_total_count(response.payload), response.result_count, offset, limit),
        "doc_id_short": response.doc_id_short or catalogue.short_doc_id(doc_id),
        "doc_id_shorts": list(_doc_id_shorts(items or (document_summary or {},))),
        "query_chars": len(query),
        "query_hash": _hash(query),
        "locator_chars": len(locator),
        "locator_hash": _hash(locator),
        "content_chars": len(content),
        "content_hash": _hash(content),
        "positions": [dict(position) for position in positions],
        "anchor_count": len(anchors) if anchors else None,
        "interval_state": _string(_mapping(interval).get("state")),
        "interval_type": _string(_mapping(interval).get("type")),
    }
    fields.update({key: value for key, value in dict(extra_fields or {}).items() if value is not None})
    observation = BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=response.endpoint_kind,
        status=STATUS_OK,
        reason_code=REASON_OK,
        fields=fields,
    )
    return BiblioLibrarianToolResult(
        tool_name=tool,
        status=STATUS_OK,
        reason_code=REASON_OK,
        endpoint_kind=response.endpoint_kind,
        observation=observation,
        document_id=doc_id,
        items=items,
        document_summary=dict(document_summary or {}),
        chapter_hint=dict(chapter_hint or {}),
        chapters=chapters,
        positions=positions,
        anchors=anchors,
        interval=dict(interval or {}),
        context_text=context_text,
        page_text=page_text,
    )


def _incoherent_context_result(
    tool: str,
    response: catalogue.CatalogueResponse,
    doc_id: str,
) -> BiblioLibrarianToolResult:
    observation = BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=response.endpoint_kind,
        status=STATUS_INCOHERENT_CATALOGUE,
        reason_code=REASON_CONTEXT_INCOHERENT,
        fields={
            "status_code": response.status_code,
            "duration_ms": response.duration_ms,
            "doc_id_short": response.doc_id_short or catalogue.short_doc_id(doc_id),
        },
    )
    return BiblioLibrarianToolResult(
        tool_name=tool,
        status=STATUS_INCOHERENT_CATALOGUE,
        reason_code=REASON_CONTEXT_INCOHERENT,
        endpoint_kind=response.endpoint_kind,
        observation=observation,
    )


def _incoherent_page_result(
    tool: str,
    response: catalogue.CatalogueResponse,
    doc_id: str,
) -> BiblioLibrarianToolResult:
    observation = BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=response.endpoint_kind,
        status=STATUS_INCOHERENT_CATALOGUE,
        reason_code=REASON_PAGE_INCOHERENT,
        fields={
            "status_code": response.status_code,
            "duration_ms": response.duration_ms,
            "doc_id_short": response.doc_id_short or catalogue.short_doc_id(doc_id),
        },
    )
    return BiblioLibrarianToolResult(
        tool_name=tool,
        status=STATUS_INCOHERENT_CATALOGUE,
        reason_code=REASON_PAGE_INCOHERENT,
        endpoint_kind=response.endpoint_kind,
        observation=observation,
        document_id=doc_id,
    )


def _error_result(
    tool: str,
    exc: catalogue.CatalogueClientError,
    *,
    endpoint_kind: str = "",
) -> BiblioLibrarianToolResult:
    reason_code = _map_client_reason(exc)
    observation = BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=exc.endpoint_kind or endpoint_kind or _ENDPOINT_BY_TOOL[tool],
        status=STATUS_ERROR,
        reason_code=reason_code,
        fields={
            "status_code": exc.status_code,
            "duration_ms": exc.duration_ms,
            "doc_id_short": exc.doc_id_short,
            "error_class": exc.error_class,
        },
    )
    return BiblioLibrarianToolResult(
        tool_name=tool,
        status=STATUS_ERROR,
        reason_code=reason_code,
        endpoint_kind=observation.endpoint_kind,
        observation=observation,
    )


def _canonical_range_result(
    tool: str,
    result: passage_extractor.BiblioPassageResult,
) -> BiblioLibrarianToolResult:
    document_id = _canonical_range_document_id(result)
    interval = result.interval_hint.to_observability() if result.interval_hint else {}
    positions = (_canonical_range_position(result),) if _canonical_range_position(result) else ()
    anchors = _canonical_range_anchors(result)
    doc_id_short = result.doc_id_short or catalogue.short_doc_id(document_id)
    fields = _clean_observation(
        {
            "status_code": 200,
            "doc_id_short": doc_id_short,
            "content_chars": result.passage_chars,
            "content_hash": result.passage_hash,
            "range_reason_code": result.reason_code,
            "range_status": result.status,
            "range_complete": result.status == passage_extractor.STATUS_EXTRACTED and bool(result.passage),
            "start_bound_resolved": bool(result.page_no or result.para_no or result.paragraph_id),
            "end_bound_resolved": bool(interval.get("end_page_no") or interval.get("end_para_no") or interval.get("end_paragraph_id")),
            "page_start": _raw_int(interval.get("start_page_no")),
            "page_end": _raw_int(interval.get("end_page_no")),
            "page_span": _raw_int(interval.get("page_span")),
            "paragraph_span": _raw_int(interval.get("paragraph_span")),
            "interval_mode": _string(interval.get("mode")),
        }
    )
    if result.status == passage_extractor.STATUS_EXTRACTED and result.passage:
        response = catalogue.CatalogueResponse(
            endpoint_kind=ENDPOINT_CANONICAL_RANGE,
            status_code=200,
            payload={"result_count": 1},
            duration_ms=0,
            result_count=1,
            doc_id_short=doc_id_short,
            content_chars=result.passage_chars,
        )
        return _ok_result(
            tool,
            response,
            positions=positions,
            anchors=anchors,
            interval=interval,
            context_text=result.passage,
            doc_id=document_id,
            content=result.passage,
            extra_fields=fields,
        )

    status = _canonical_range_status(result.status)
    reason_code = result.reason_code or REASON_CANONICAL_RANGE_INCOMPLETE
    observation = BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=ENDPOINT_CANONICAL_RANGE,
        status=status,
        reason_code=reason_code,
        fields=fields,
    )
    return BiblioLibrarianToolResult(
        tool_name=tool,
        status=status,
        reason_code=reason_code,
        endpoint_kind=ENDPOINT_CANONICAL_RANGE,
        observation=observation,
        document_id=document_id,
        positions=positions,
        anchors=anchors,
        interval=interval,
    )


def _canonical_range_status(status: str) -> str:
    if status == passage_extractor.STATUS_AMBIGUOUS:
        return STATUS_AMBIGUOUS
    if status in {passage_extractor.STATUS_NOT_FOUND, passage_extractor.STATUS_EMPTY}:
        return STATUS_NOT_FOUND
    return STATUS_ERROR


def _canonical_range_document_id(result: passage_extractor.BiblioPassageResult) -> str:
    resolution = result.resolution
    document = getattr(resolution, "document", None) if resolution is not None else None
    return _string(getattr(document, "document_id", ""))


def _canonical_range_position(result: passage_extractor.BiblioPassageResult) -> dict[str, Any]:
    return _position(
        {
            "page_no": result.page_no,
            "para_no": result.para_no,
            "paragraph_id": result.paragraph_id,
        }
    )


def _canonical_range_anchors(result: passage_extractor.BiblioPassageResult) -> tuple[dict[str, Any], ...]:
    document_id = _canonical_range_document_id(result)
    if not document_id:
        return ()
    interval = result.interval_hint.to_observability() if result.interval_hint else {}
    anchors: list[dict[str, Any]] = []
    for prefix in ("start", "end"):
        anchor = _clean_observation(
            {
                "document_id": document_id,
                "page_no": _raw_int(interval.get(f"{prefix}_page_no")),
                "para_no": _raw_int(interval.get(f"{prefix}_para_no")),
                "paragraph_id": _raw_int(interval.get(f"{prefix}_paragraph_id")),
            }
        )
        if anchor and anchor not in anchors:
            anchors.append(anchor)
    if not anchors:
        position = _canonical_range_position(result)
        if position:
            position["document_id"] = document_id
            anchors.append(position)
    return tuple(anchors)


def _map_client_reason(exc: catalogue.CatalogueClientError) -> str:
    if isinstance(exc, (catalogue.CatalogueForbiddenMethod, catalogue.CatalogueForbiddenRoute)):
        return REASON_FORBIDDEN_TOOL
    if isinstance(exc, catalogue.CatalogueTimeout):
        return REASON_TIMEOUT
    if isinstance(exc, catalogue.CatalogueInvalidJson):
        return REASON_INVALID_JSON
    if isinstance(exc, catalogue.CatalogueUnexpectedStatus):
        return REASON_UNEXPECTED_STATUS
    if isinstance(exc, catalogue.CatalogueInvalidParameter):
        return REASON_INVALID_PARAMETER
    return REASON_CATALOGUE_UNAVAILABLE


def _required_doc_id(params: Mapping[str, Any], *, tool: str) -> str:
    doc_id = _doc_id(params, tool=tool)
    if not doc_id:
        raise _tool_error(tool, REASON_MISSING_DOCUMENT_ID)
    return doc_id


def _doc_id(params: Mapping[str, Any], *, tool: str) -> str:
    raw = params.get("document_id", params.get("doc_id"))
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise _tool_error(tool, REASON_INVALID_PARAMETER, detail="document_id_must_be_string")
    value = raw.strip()
    if not value:
        return ""
    if len(value) > _DOC_ID_MAX or any(char in value for char in "/?#\\"):
        raise _tool_error(tool, REASON_INVALID_PARAMETER, detail="document_id_invalid")
    return value


def _required_text(
    params: Mapping[str, Any],
    names: Sequence[str],
    *,
    tool: str,
    max_chars: int,
) -> str:
    for name in names:
        value = _text(params, name, tool=tool, max_chars=max_chars)
        if value:
            return value
    raise _tool_error(tool, REASON_MISSING_QUERY)


def _text(params: Mapping[str, Any], name: str, *, tool: str, max_chars: int) -> str:
    raw = params.get(name)
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise _tool_error(tool, REASON_INVALID_PARAMETER, detail=f"{name}_must_be_string")
    value = raw.strip()
    if len(value) > max_chars:
        raise _tool_error(tool, REASON_BUDGET_OR_LIMIT_EXCEEDED, detail=f"{name}_too_long")
    return value


def _optional_integer(
    params: Mapping[str, Any],
    name: str,
    *,
    tool: str,
    minimum: int,
    maximum: int,
) -> int | None:
    if name not in params or params.get(name) is None:
        return None
    return _integer(params.get(name), tool=tool, name=name, minimum=minimum, maximum=maximum)


def _integer(value: Any, *, tool: str, name: str, minimum: int, maximum: int) -> int:
    if type(value) is int:
        number = value
    elif isinstance(value, str) and value.isdecimal():
        number = int(value)
    else:
        raise _tool_error(tool, REASON_INVALID_PARAMETER, detail=f"{name}_must_be_integer")
    if number < minimum:
        raise _tool_error(tool, REASON_INVALID_PARAMETER, detail=f"{name}_out_of_range")
    if number > maximum:
        raise _tool_error(tool, REASON_BUDGET_OR_LIMIT_EXCEEDED, detail=f"{name}_out_of_range")
    return number


def _tool_error(tool: str, reason: str, *, doc_id: str = "", detail: str = "") -> BiblioLibrarianToolError:
    return BiblioLibrarianToolError(
        tool_name=tool,
        reason_code=reason,
        endpoint_kind=_ENDPOINT_BY_TOOL[tool],
        doc_id=doc_id,
        detail=detail,
    )


def _catalog_item(raw: Any) -> dict[str, Any]:
    item = _mapping(raw)
    doc_id = _string(item.get("id") or item.get("document_id"))
    return {
        "document_id": doc_id,
        "doc_id_short": catalogue.short_doc_id(doc_id),
        "title": _string(item.get("human_canonical_title") or item.get("canonical_title") or item.get("title")),
        "authors": _string(item.get("human_authors") or item.get("authors")),
        "language": _string(item.get("human_language") or item.get("language")),
        "page_count": _raw_int(item.get("page_count") or item.get("unit_count")),
        "metadata_status": _string(item.get("human_metadata_status") or item.get("metadata_status")),
    }


def _search_item(raw: Any) -> dict[str, Any]:
    item = _mapping(raw)
    doc_id = _string(item.get("document_id") or item.get("id"))
    return _clean_observation(
        {
            "document_id": doc_id,
            "doc_id_short": catalogue.short_doc_id(doc_id),
            "title": _string(item.get("human_canonical_title") or item.get("canonical_title") or item.get("title")),
            "authors": _string(item.get("human_authors") or item.get("authors")),
            "snippet": _string(item.get("snippet") or item.get("excerpt") or item.get("text")),
            "page_no": _raw_int(item.get("page_no")),
            "para_no": _raw_int(item.get("para_no")),
            "paragraph_id": _raw_int(item.get("paragraph_id")),
            "rank": _raw_float(item.get("rank")),
            "score": _raw_float(item.get("score")),
            "document_role_signal": _string(item.get("document_role_signal")),
            "document_role_signal_source": _string(item.get("document_role_signal_source")),
            "document_role_signal_strength": _string(item.get("document_role_signal_strength")),
        }
    )


def _chapter_search_item(raw: Any) -> dict[str, Any]:
    item = _mapping(raw)
    doc_id = _string(item.get("document_id") or item.get("id"))
    unit_no = _raw_int(item.get("unit_no"))
    return _clean_observation(
        {
            "document_id": doc_id,
            "doc_id_short": catalogue.short_doc_id(doc_id),
            "title": _string(item.get("chapter_title") or item.get("title")),
            "document_title": _string(item.get("document_title")),
            "chapter_no": _raw_int(item.get("chapter_no")),
            "page_no": unit_no,
            "unit_no": unit_no,
            "rank": _raw_float(item.get("rank")),
            "score": _raw_float(item.get("score")),
            "source": _string(item.get("source")),
            "document_role_signal": _string(item.get("document_role_signal")),
            "document_role_signal_source": _string(item.get("document_role_signal_source")),
            "document_role_signal_strength": _string(item.get("document_role_signal_strength")),
        }
    )


def _document_summary(payload: Mapping[str, Any], fallback_doc_id: str) -> dict[str, Any]:
    document = _mapping(payload.get("document"))
    human = _mapping(payload.get("human_metadata"))
    doc_id = _string(document.get("id")) or fallback_doc_id
    return {
        "document_id": doc_id,
        "doc_id_short": catalogue.short_doc_id(doc_id),
        "title": _string(human.get("canonical_title") or document.get("title")),
        "authors": _string(human.get("authors") or document.get("authors")),
        "language": _string(human.get("language") or document.get("language")),
        "page_count": _raw_int(document.get("page_count") or document.get("unit_count")),
        "metadata_status": _string(payload.get("metadata_status") or human.get("metadata_status")),
    }


def _page_document_summary(payload: Mapping[str, Any], fallback_doc_id: str) -> dict[str, Any]:
    doc_id = _string(payload.get("document_id")) or fallback_doc_id
    return {
        "document_id": doc_id,
        "doc_id_short": catalogue.short_doc_id(doc_id),
        "title": _string(payload.get("title")),
        "authors": "",
        "metadata_status": "",
    }


def _chapter_item(raw: Any) -> dict[str, Any]:
    item = _mapping(raw)
    return _clean_observation(
        {
            "chapter_no": _raw_int(item.get("chapter_no")),
            "title": _string(item.get("title")),
            "page_start": _raw_int(item.get("page_start")),
            "page_end": _raw_int(item.get("page_end")),
            "paragraph_start": _raw_int(item.get("paragraph_start")),
            "paragraph_end": _raw_int(item.get("paragraph_end")),
        }
    )


def _chapter_hint(payload: Mapping[str, Any]) -> dict[str, Any]:
    item = _mapping(payload.get("chapter"))
    return _clean_observation(
        {
            "chapter_no": _raw_int(item.get("chapter_no")),
            "title": _string(item.get("title")),
            "unit_start": _raw_int(item.get("unit_start")),
            "unit_end": _raw_int(item.get("unit_end")),
            "source": _string(item.get("source")),
            "next_chapter_no": _raw_int(item.get("next_chapter_no")),
            "next_chapter_title": _string(item.get("next_chapter_title")),
            "document_role_signal": _string(item.get("document_role_signal")),
            "document_role_signal_source": _string(item.get("document_role_signal_source")),
            "document_role_signal_strength": _string(item.get("document_role_signal_strength")),
        }
    )


def _locate_items(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    found: list[Mapping[str, Any]] = []
    if isinstance(payload.get("best"), Mapping):
        found.append(payload["best"])  # type: ignore[arg-type]
    for key in ("matches", "alternatives"):
        found.extend(item for item in _items(payload, key) if isinstance(item, Mapping))
    return tuple(found)


def _position(raw: Mapping[str, Any]) -> dict[str, Any]:
    return _clean_observation(
        {
            key: _raw_int(raw.get(key))
            for key in ("page_no", "para_no", "paragraph_id", "order_index", "char_offset", "window_chars")
        }
        | {"rank": _raw_float(raw.get("rank")), "score": _raw_float(raw.get("score"))}
    )


def _context_text(payload: Mapping[str, Any]) -> str:
    for key in ("text", "context", "excerpt", "markdown"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def _page_text(payload: Mapping[str, Any]) -> str:
    value = payload.get("raw_text")
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if len(text) <= _PAGE_TEXT_MAX_CHARS:
        return text
    return text[:_PAGE_TEXT_MAX_CHARS].rstrip() + "\n[page bornee: suite masquee]"


def _items(payload: Mapping[str, Any], key: str) -> tuple[Any, ...]:
    value = payload.get(key)
    return tuple(value) if isinstance(value, list) else ()


def _total_count(payload: Mapping[str, Any]) -> int | None:
    for key in ("total", "count", "match_count"):
        if type(payload.get(key)) is int:
            return payload[key]  # type: ignore[return-value]
    return None


def _truncated(total: int | None, count: int | None, offset: int, limit: int) -> bool:
    if total is None:
        return False
    return offset + min(count or 0, max(limit, 0)) < total


def _doc_id_shorts(items: Any) -> tuple[str, ...]:
    if isinstance(items, Mapping):
        items = (items,)
    if not isinstance(items, tuple):
        return ()
    seen: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            value = _string(item.get("doc_id_short")) or catalogue.short_doc_id(_string(item.get("document_id")))
            if value and value not in seen:
                seen.append(value)
    return tuple(seen[:10])


def _clean_tool_name(tool_name: str) -> str:
    return str(tool_name or "").strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _raw_int(value: Any) -> int | None:
    return value if type(value) is int else None


def _raw_float(value: Any) -> float | None:
    return float(value) if type(value) in {int, float} else None


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] if value else ""


def _clean_observation(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }
