"""Validated dispatch boundary for the bounded Biblio tool registry."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from . import catalogue_client as catalogue


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

REASON_UNKNOWN_TOOL = "unknown_tool"
REASON_FORBIDDEN_TOOL = "forbidden_tool"


class BiblioLibrarianToolError(Exception):
    def __init__(
        self,
        *,
        tool_name: str = "",
        reason_code: str = "invalid_parameter",
        endpoint_kind: str = "",
        status_code: int | None = None,
        doc_id: str = "",
        error_class: str = "",
        detail: str = "",
    ) -> None:
        self.tool_name = str(tool_name or "").strip()
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
        return {
            key: value
            for key, value in {
                "tool_name": self.tool_name,
                "endpoint_kind": self.endpoint_kind,
                "status": "error",
                "reason_code": self.reason_code,
                "status_code": self.status_code,
                "doc_id_short": self.doc_id_short,
                "error_class": self.error_class,
            }.items()
            if value is not None and value != "" and value != [] and value != {}
        }


class BiblioLibrarianToolRegistry:
    """Expose one exact tool namespace and dispatch only validated calls."""

    def __init__(
        self,
        *,
        handlers: Mapping[str, Callable[[Mapping[str, Any]], Any]],
        client: Any = None,
    ) -> None:
        handler_names = tuple(handlers)
        if handler_names != LOT3_TOOL_NAMES:
            raise ValueError("Biblio registry handlers must exactly match the ordered tool namespace")
        self._handlers = dict(handlers)
        self._client = client

    @property
    def tool_names(self) -> tuple[str, ...]:
        return LOT3_TOOL_NAMES

    def run(self, tool_name: str, params: Mapping[str, Any] | None = None) -> Any:
        clean_name = str(tool_name or "").strip()
        if clean_name in FORBIDDEN_TOOL_NAMES:
            raise BiblioLibrarianToolError(tool_name=clean_name, reason_code=REASON_FORBIDDEN_TOOL)
        if clean_name not in self._handlers:
            raise BiblioLibrarianToolError(tool_name=clean_name, reason_code=REASON_UNKNOWN_TOOL)
        return self._handlers[clean_name](dict(params or {}))
