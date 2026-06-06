"""High-level library primitives for the Biblio librarian.

Lot 2 exposes document/work/section search and resolution above the raw
Catalogue GET tools. The functions stay content-free in observability and use
the Lot 1 manifest projection for section anchors and bounds.
"""

from __future__ import annotations

import unicodedata
from typing import Any, Mapping, Sequence

from . import catalogue_client as catalogue
from . import query_planner
from . import librarian_tools as tools
from . import work_resolver
from .structure import schema as structure_schema
from .structure.builder import build_document_manifest


def run_library_tool(client: Any, tool_name: str, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    clean_name = str(tool_name or "").strip()
    handlers = {
        tools.TOOL_SEARCH_DOCUMENT: _search_document,
        tools.TOOL_SEARCH_WORK: _search_work,
        tools.TOOL_SEARCH_SECTION: _search_section,
        tools.TOOL_RESOLVE_WORK: _resolve_work,
        tools.TOOL_RESOLVE_SECTION: _resolve_section,
        tools.TOOL_SECTION_BOUNDS: _section_bounds,
    }
    return handlers[clean_name](client, dict(params or {}))


def _search_document(client: Any, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    tool = tools.TOOL_SEARCH_DOCUMENT
    query = tools._required_text(params, ("q", "query"), tool=tool, max_chars=tools._QUERY_MAX)
    limit = tools._integer(params.get("limit", 20), tool=tool, name="limit", minimum=1, maximum=50)
    offset = tools._integer(params.get("offset", 0), tool=tool, name="offset", minimum=0, maximum=tools._OFFSET_MAX)
    try:
        response = client.catalog(q=query, limit=limit, offset=offset)
    except catalogue.CatalogueClientError as exc:
        return tools._error_result(tool, exc)
    items = tuple(_document_candidate(item) for item in tools._items(response.payload, "items"))
    return tools._ok_result(tool, response, items=items, offset=offset, limit=limit, query=query)


def _search_work(client: Any, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    tool = tools.TOOL_SEARCH_WORK
    query = tools._required_text(params, ("q", "query"), tool=tool, max_chars=tools._QUERY_MAX)
    limit = tools._integer(params.get("limit", 20), tool=tool, name="limit", minimum=1, maximum=50)
    doc_id = tools._doc_id(params, tool=tool)
    try:
        response, candidates = _work_candidates(client, doc_id=doc_id, query=query, limit=limit)
    except catalogue.CatalogueClientError as exc:
        return tools._error_result(tool, exc)
    return tools._ok_result(tool, response, items=candidates, limit=limit, query=query, doc_id=doc_id)


def _search_section(client: Any, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    tool = tools.TOOL_SEARCH_SECTION
    query = tools._required_text(params, ("q", "query"), tool=tool, max_chars=tools._QUERY_MAX)
    doc_id = tools._required_doc_id(params, tool=tool)
    limit = tools._integer(params.get("limit", 20), tool=tool, name="limit", minimum=1, maximum=50)
    try:
        response, candidates = _section_candidates(client, doc_id=doc_id, query=query, limit=limit)
    except catalogue.CatalogueClientError as exc:
        return tools._error_result(tool, exc)
    return tools._ok_result(tool, response, items=candidates, limit=limit, query=query, doc_id=doc_id)


def _resolve_work(client: Any, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    tool = tools.TOOL_RESOLVE_WORK
    doc_id = tools._doc_id(params, tool=tool)
    query = tools._text(params, "q", tool=tool, max_chars=tools._QUERY_MAX) or tools._text(
        params,
        "query",
        tool=tool,
        max_chars=tools._QUERY_MAX,
    )
    structured_plan = _structured_work_resolution_plan(params, doc_id=doc_id, query=query)
    if structured_plan is not None:
        structured = work_resolver.BiblioWorkResolver(client).resolve(structured_plan)
        return _work_resolver_tool_result(tool, structured, query=query, doc_id=doc_id)
    limit = tools._integer(params.get("limit", 5), tool=tool, name="limit", minimum=1, maximum=20)
    if not doc_id and not query:
        raise tools._tool_error(tool, tools.REASON_MISSING_QUERY)
    try:
        if doc_id and not query:
            response = client.metadata(doc_id)
            candidates = (_document_scope_work_candidate(response.payload, doc_id),)
        else:
            response, candidates = _work_candidates(client, doc_id=doc_id, query=query, limit=limit)
    except catalogue.CatalogueClientError as exc:
        return tools._error_result(tool, exc)
    empty_reason = tools.REASON_INTERNAL_WORK_UNRESOLVED if doc_id else tools.REASON_WORK_ALIAS_MISSING
    return _resolution_result(tool, response, candidates, query=query, doc_id=doc_id, empty_reason_code=empty_reason)


def _resolve_section(client: Any, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    tool = tools.TOOL_RESOLVE_SECTION
    doc_id = tools._required_doc_id(params, tool=tool)
    query = tools._text(params, "q", tool=tool, max_chars=tools._QUERY_MAX) or tools._text(
        params,
        "query",
        tool=tool,
        max_chars=tools._QUERY_MAX,
    )
    chapter_no = tools._optional_integer(params, "chapter_no", tool=tool, minimum=1, maximum=100_000)
    section_id = tools._text(params, "section_id", tool=tool, max_chars=160)
    if chapter_no is None and section_id.isdecimal():
        chapter_no = int(section_id)
        section_id = ""
    if chapter_no is None and not section_id and not query:
        raise tools._tool_error(tool, tools.REASON_MISSING_QUERY)
    try:
        response, candidates = _section_candidates(
            client,
            doc_id=doc_id,
            query=query,
            chapter_no=chapter_no,
            section_id=section_id,
            limit=20,
        )
    except catalogue.CatalogueClientError as exc:
        return tools._error_result(tool, exc)
    return _resolution_result(
        tool,
        response,
        candidates,
        query=query,
        doc_id=doc_id,
        empty_reason_code=_empty_section_reason(response, query=query, chapter_no=chapter_no, section_id=section_id),
    )


def _section_bounds(client: Any, params: Mapping[str, Any]) -> tools.BiblioLibrarianToolResult:
    tool = tools.TOOL_SECTION_BOUNDS
    doc_id = tools._required_doc_id(params, tool=tool)
    query = tools._text(params, "q", tool=tool, max_chars=tools._QUERY_MAX) or tools._text(
        params,
        "query",
        tool=tool,
        max_chars=tools._QUERY_MAX,
    )
    chapter_no = tools._optional_integer(params, "chapter_no", tool=tool, minimum=1, maximum=100_000)
    section_id = tools._text(params, "section_id", tool=tool, max_chars=160)
    if chapter_no is None and section_id.isdecimal():
        chapter_no = int(section_id)
        section_id = ""
    if chapter_no is None and not section_id and not query:
        raise tools._tool_error(tool, tools.REASON_MISSING_QUERY)
    try:
        response, candidates = _section_candidates(
            client,
            doc_id=doc_id,
            query=query,
            chapter_no=chapter_no,
            section_id=section_id,
            limit=20,
        )
    except catalogue.CatalogueClientError as exc:
        return tools._error_result(tool, exc)
    if len(candidates) != 1:
        return _resolution_result(
            tool,
            response,
            candidates,
            query=query,
            doc_id=doc_id,
            empty_reason_code=_empty_section_reason(response, query=query, chapter_no=chapter_no, section_id=section_id),
        )
    item = candidates[0]
    interval = tools._mapping(item.get("interval"))
    anchors = tuple(
        anchor
        for anchor in (
            tools._mapping(interval.get("start")),
            tools._mapping(interval.get("end")),
        )
        if anchor
    )
    if not interval or not anchors:
        return _status_result(
            tool,
            response,
            status=tools.STATUS_NOT_FOUND,
            reason_code=tools.REASON_SECTION_BOUNDS_UNAVAILABLE,
            items=candidates,
            query=query,
            doc_id=doc_id,
        )
    return _status_result(
        tool,
        response,
        status=tools.STATUS_RESOLVED,
        reason_code=tools.REASON_RESOLVED,
        items=candidates,
        anchors=anchors,
        interval=dict(interval),
        query=query,
        doc_id=doc_id,
        extra_fields={
            "boundary_state": tools._string(item.get("boundary_state")),
            "chapter_no": tools._raw_int(item.get("chapter_no")),
            "unit_start": tools._raw_int(item.get("unit_start")),
            "unit_end": tools._raw_int(item.get("unit_end")),
        },
    )


def _structured_work_resolution_plan(
    params: Mapping[str, Any],
    *,
    doc_id: str,
    query: str,
) -> query_planner.BiblioQueryPlan | None:
    tool = tools.TOOL_RESOLVE_WORK
    document_title = tools._text(params, "document_title", tool=tool, max_chars=tools._QUERY_MAX)
    work_title = tools._text(params, "work_title", tool=tool, max_chars=tools._QUERY_MAX)
    author = tools._text(params, "author", tool=tool, max_chars=tools._QUERY_MAX)
    locator = tools._text(params, "locator", tool=tool, max_chars=tools._LOCATOR_MAX)
    locator_end = tools._text(params, "locator_end", tool=tool, max_chars=tools._LOCATOR_MAX)
    locator_kind = tools._text(params, "kind", tool=tool, max_chars=40) or "stephanus"
    if not any((document_title, work_title, author, locator, locator_end)):
        return None
    plan = query_planner.BiblioQueryPlan(
        should_consult=True,
        intent=query_planner.INTENT_RESOLVE_WORK,
        reason_code=query_planner.REASON_WORK_REQUESTED,
        query_kind=query_planner.INTENT_RESOLVE_WORK,
        document_id=doc_id,
        catalogue_query=query or document_title or author or work_title,
        document_title=document_title,
        work_title=work_title or (query if not document_title else ""),
        author=author,
        locator=locator,
        locator_end=locator_end,
        locator_kind=locator_kind,
        limit=5,
    )
    with_variants = getattr(query_planner, "_with_variants", None)
    return with_variants(plan) if callable(with_variants) else plan


def _work_resolver_tool_result(
    tool: str,
    resolution: work_resolver.BiblioWorkResolution,
    *,
    query: str,
    doc_id: str,
) -> tools.BiblioLibrarianToolResult:
    if resolution.status == work_resolver.STATUS_CATALOGUE_UNAVAILABLE:
        status = tools.STATUS_ERROR
        reason_code = tools.REASON_CATALOGUE_UNAVAILABLE
    elif resolution.status == work_resolver.STATUS_AMBIGUOUS:
        status = tools.STATUS_AMBIGUOUS
        reason_code = tools.REASON_AMBIGUOUS
    elif resolution.status == work_resolver.STATUS_NOT_FOUND:
        status = tools.STATUS_NOT_FOUND
        reason_code = tools.REASON_WORK_ALIAS_MISSING
    elif resolution.status in {work_resolver.STATUS_RESOLVED, work_resolver.STATUS_SEARCHED}:
        status = tools.STATUS_RESOLVED if resolution.status == work_resolver.STATUS_RESOLVED else tools.STATUS_OK
        reason_code = tools.REASON_RESOLVED if resolution.status == work_resolver.STATUS_RESOLVED else tools.REASON_OK
    else:
        status = tools.STATUS_ERROR
        reason_code = tools.REASON_UNEXPECTED_STATUS

    request = resolution.resolve_request
    request_doc_id = tools._string(getattr(request, "document_id", "")) if request is not None else ""
    effective_doc_id = request_doc_id or doc_id
    position = tools._clean_observation(
        {
            "document_id": effective_doc_id,
            "page_no": tools._raw_int(getattr(request, "locator_anchor_page", None)) if request is not None else None,
            "para_no": tools._raw_int(getattr(request, "locator_anchor_para", None)) if request is not None else None,
        }
    )
    positions = (position,) if position.get("page_no") or position.get("para_no") else ()
    items: tuple[dict[str, Any], ...] = ()
    if effective_doc_id:
        work_title = tools._string(getattr(request, "work_title", "")) if request is not None else ""
        author = tools._string(getattr(request, "author", "")) if request is not None else ""
        work_key = tools._hash(work_title or resolution.documentary_target or effective_doc_id)
        items = (
            tools._clean_observation(
                {
                    "candidate_type": "work",
                    "work_kind": resolution.documentary_target or "work_scope",
                    "work_id": f"{catalogue.short_doc_id(effective_doc_id)}:work:{work_key}",
                    "document_id": effective_doc_id,
                    "doc_id_short": catalogue.short_doc_id(effective_doc_id),
                    "title": work_title,
                    "authors": author,
                    "page_no": position.get("page_no"),
                    "para_no": position.get("para_no"),
                }
            ),
        )
    fields = tools._clean_observation(
        {
            "status_code": 200,
            "result_count": len(items),
            "displayed_count": len(items),
            "doc_id_short": catalogue.short_doc_id(effective_doc_id),
            "doc_id_shorts": [catalogue.short_doc_id(effective_doc_id)] if effective_doc_id else [],
            "query_chars": len(query),
            "query_hash": tools._hash(query),
            "catalog_result_count": resolution.catalog_result_count,
            "search_result_count": resolution.search_result_count,
            "document_candidate_count": len(resolution.document_candidate_ids),
            "anchor_count": len(positions) if positions else None,
            "positions": [dict(position) for position in positions],
            "documentary_target": tools._string(resolution.documentary_target),
            "work_hint_present": bool(resolution.work_hint_present),
            "document_hint_present": bool(resolution.document_hint_present),
        }
    )
    observation = tools.BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=catalogue.ENDPOINT_CATALOG,
        status=status,
        reason_code=reason_code,
        fields=fields,
    )
    return tools.BiblioLibrarianToolResult(
        tool_name=tool,
        status=status,
        reason_code=reason_code,
        endpoint_kind=catalogue.ENDPOINT_CATALOG,
        observation=observation,
        document_id=effective_doc_id,
        items=items,
        positions=positions,
        anchors=positions,
    )


def _work_candidates(
    client: Any,
    *,
    doc_id: str,
    query: str,
    limit: int,
) -> tuple[catalogue.CatalogueResponse, tuple[dict[str, Any], ...]]:
    if doc_id:
        metadata_response = client.metadata(doc_id)
        structure_response, sections_payload, chapters_payload = _structure_payload(client, doc_id)
        manifest = _manifest_from_payloads(
            doc_id=doc_id,
            metadata_payload=metadata_response.payload,
            sections_payload=sections_payload,
            chapters_payload=chapters_payload,
        )
        candidates = []
        document_candidate = _document_scope_work_candidate(metadata_response.payload, doc_id)
        if _candidate_matches(document_candidate, query):
            candidates.append(document_candidate)
        section_by_no = {section.sequence_no: section for section in manifest.sections}
        for row in _raw_structure_rows(sections_payload, chapters_payload):
            section = section_by_no.get(_row_sequence_no(row))
            if section is None:
                continue
            candidate = _manifest_section_work_candidate(section, manifest, row)
            if _candidate_matches(candidate, query):
                candidates.append(_public_candidate(candidate))
        return structure_response, tuple(candidates[:limit])

    response = client.catalog(q=query, limit=limit, offset=0)
    candidates = tuple(_document_candidate(item, work_kind="document_scope") for item in tools._items(response.payload, "items"))
    return response, candidates


def _section_candidates(
    client: Any,
    *,
    doc_id: str,
    query: str = "",
    chapter_no: int | None = None,
    section_id: str = "",
    limit: int = 20,
) -> tuple[catalogue.CatalogueResponse, tuple[dict[str, Any], ...]]:
    response, sections_payload, chapters_payload = _structure_payload(client, doc_id)
    manifest = _manifest_from_payloads(doc_id=doc_id, sections_payload=sections_payload, chapters_payload=chapters_payload)
    candidates = []
    section_by_no = {section.sequence_no: section for section in manifest.sections}
    for row in _raw_structure_rows(sections_payload, chapters_payload):
        section = section_by_no.get(_row_sequence_no(row))
        if section is None:
            continue
        candidate = _manifest_section_candidate(section, manifest, row)
        if chapter_no is not None and tools._raw_int(candidate.get("chapter_no")) != chapter_no:
            continue
        if section_id and tools._string(candidate.get("section_id")) != section_id:
            continue
        if query and not _candidate_matches(candidate, query):
            continue
        candidates.append(_public_candidate(candidate))
    return response, tuple(candidates[:limit])


def _status_result(
    tool: str,
    response: catalogue.CatalogueResponse,
    *,
    status: str,
    reason_code: str,
    items: tuple[dict[str, Any], ...] = (),
    anchors: tuple[dict[str, Any], ...] = (),
    interval: Mapping[str, Any] | None = None,
    query: str = "",
    doc_id: str = "",
    extra_fields: Mapping[str, Any] | None = None,
) -> tools.BiblioLibrarianToolResult:
    fields = {
        "status_code": response.status_code,
        "duration_ms": response.duration_ms,
        "result_count": response.result_count,
        "displayed_count": len(items),
        "doc_id_short": response.doc_id_short or catalogue.short_doc_id(doc_id),
        "doc_id_shorts": list(tools._doc_id_shorts(items)),
        "query_chars": len(query),
        "query_hash": tools._hash(query),
        "anchor_count": len(anchors) if anchors else None,
        "interval_state": tools._string(tools._mapping(interval).get("state")),
        "interval_type": tools._string(tools._mapping(interval).get("type")),
    }
    fields.update({key: value for key, value in dict(extra_fields or {}).items() if value is not None})
    observation = tools.BiblioLibrarianToolObservation(
        tool_name=tool,
        endpoint_kind=response.endpoint_kind,
        status=status,
        reason_code=reason_code,
        fields=fields,
    )
    return tools.BiblioLibrarianToolResult(
        tool_name=tool,
        status=status,
        reason_code=reason_code,
        endpoint_kind=response.endpoint_kind,
        observation=observation,
        document_id=doc_id or _unique_document_id(items),
        items=items,
        anchors=anchors,
        interval=dict(interval or {}),
    )


def _resolution_result(
    tool: str,
    response: catalogue.CatalogueResponse,
    candidates: tuple[dict[str, Any], ...],
    *,
    query: str = "",
    doc_id: str = "",
    empty_reason_code: str = tools.REASON_NOT_FOUND,
) -> tools.BiblioLibrarianToolResult:
    if not candidates:
        return _status_result(
            tool,
            response,
            status=tools.STATUS_NOT_FOUND,
            reason_code=empty_reason_code,
            query=query,
            doc_id=doc_id,
        )
    if len(candidates) > 1:
        return _status_result(
            tool,
            response,
            status=tools.STATUS_AMBIGUOUS,
            reason_code=tools.REASON_AMBIGUOUS,
            items=candidates,
            query=query,
            doc_id=doc_id,
        )
    item = candidates[0]
    interval = tools._mapping(item.get("interval"))
    anchors = tuple(
        anchor
        for anchor in (
            tools._mapping(interval.get("start")),
            tools._mapping(interval.get("end")),
        )
        if anchor
    )
    return _status_result(
        tool,
        response,
        status=tools.STATUS_RESOLVED,
        reason_code=tools.REASON_RESOLVED,
        items=candidates,
        anchors=anchors,
        interval=interval,
        query=query,
        doc_id=doc_id,
    )


def _manifest_from_payloads(
    *,
    doc_id: str,
    metadata_payload: Mapping[str, Any] | None = None,
    sections_payload: Mapping[str, Any] | None = None,
    chapters_payload: Mapping[str, Any] | None = None,
) -> structure_schema.DocumentManifest:
    return build_document_manifest(
        catalog_item={"id": doc_id},
        metadata_payload=metadata_payload,
        sections_payload=sections_payload,
        chapters_payload=chapters_payload,
    )


def _document_candidate(raw: Any, *, work_kind: str = "catalogue_document") -> dict[str, Any]:
    item = tools._mapping(raw)
    doc_id = tools._string(item.get("id") or item.get("document_id"))
    return tools._clean_observation(
        {
            "candidate_type": "document",
            "work_kind": work_kind,
            "document_id": doc_id,
            "doc_id_short": catalogue.short_doc_id(doc_id),
            "title": tools._string(item.get("human_canonical_title") or item.get("canonical_title") or item.get("title")),
            "authors": tools._string(item.get("human_authors") or item.get("authors")),
            "metadata_status": tools._string(item.get("human_metadata_status") or item.get("metadata_status")),
        }
    )


def _document_scope_work_candidate(payload: Mapping[str, Any], fallback_doc_id: str) -> dict[str, Any]:
    summary = tools._document_summary(payload, fallback_doc_id)
    doc_id = tools._string(summary.get("document_id")) or fallback_doc_id
    return tools._clean_observation(
        {
            "candidate_type": "work",
            "work_kind": "document_scope",
            "work_id": f"{catalogue.short_doc_id(doc_id)}:work:document_scope",
            "document_id": doc_id,
            "doc_id_short": catalogue.short_doc_id(doc_id),
            "title": tools._string(summary.get("title")),
            "authors": tools._string(summary.get("authors")),
            "metadata_status": tools._string(summary.get("metadata_status")),
            "source": "catalogue_metadata",
            "alias_count": 1 if tools._string(summary.get("title")) else 0,
            "alias_state": "derived" if tools._string(summary.get("title")) else "unknown",
            "limits": ("internal_works_not_detected_without_explicit_toc_signal",),
        }
    )


def _manifest_section_work_candidate(
    section: structure_schema.SectionNode,
    manifest: structure_schema.DocumentManifest,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _manifest_section_candidate(section, manifest, raw)
    candidate.update(
        {
            "candidate_type": "work",
            "work_kind": "section_scope",
            "work_id": f"{section.section_id}:work",
            "limits": tuple(dict.fromkeys((*section.limits, "section_candidate_not_confirmed_internal_work"))),
        }
    )
    return candidate


def _manifest_section_candidate(
    section: structure_schema.SectionNode,
    manifest: structure_schema.DocumentManifest,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    doc_id = manifest.document.document_id
    interval = section.interval.to_dict()
    start_anchor = section.start_anchor.to_dict()
    end_anchor = section.end_anchor.to_dict() if section.end_anchor else {}
    return tools._clean_observation(
        {
            "candidate_type": "section",
            "document_id": doc_id,
            "doc_id_short": catalogue.short_doc_id(doc_id),
            "section_id": section.section_id,
            "chapter_no": section.sequence_no,
            "section_no": section.sequence_no,
            "level": section.level,
            "parent_section_id": section.parent_id,
            "section_kind": tools._string(raw.get("section_kind")) or ("chapter" if section.level <= 1 else "section"),
            "title": tools._string(raw.get("title")),
            "source": section.source,
            "content_role": section.content_role.value,
            "content_role_state": section.content_role.state,
            "boundary_state": section.boundary_state,
            "unit_label": manifest.document.unit_label,
            "unit_start": tools._raw_int(start_anchor.get("unit_no")),
            "unit_end": tools._raw_int(end_anchor.get("unit_no")),
            "page_start": tools._raw_int(start_anchor.get("page_no")),
            "page_end": tools._raw_int(end_anchor.get("page_no")),
            "interval": interval,
            "alias_count": len(section.aliases.values),
            "alias_state": section.aliases.state,
            "alias_source": section.aliases.source,
            "_match_texts": section.aliases.values,
            "limits": tuple(section.limits),
        }
    )


def _public_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dict(candidate).items() if not str(key).startswith("_")}


def _raw_chapter_rows(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = payload.get("chapters")
    if not isinstance(rows, list):
        return ()
    cleaned = []
    for row in rows:
        if isinstance(row, Mapping) and tools._raw_int(row.get("chapter_no")) and tools._raw_int(row.get("unit_no")):
            cleaned.append(row)
    return tuple(cleaned)


def _raw_section_rows(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = payload.get("sections")
    if not isinstance(rows, list):
        return ()
    cleaned = []
    for row in rows:
        if isinstance(row, Mapping) and tools._raw_int(row.get("section_no")) and tools._raw_int(row.get("unit_start")):
            cleaned.append(row)
    return tuple(cleaned)


def _raw_structure_rows(
    sections_payload: Mapping[str, Any],
    chapters_payload: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    return _raw_section_rows(sections_payload) or _raw_chapter_rows(chapters_payload)


def _row_sequence_no(row: Mapping[str, Any]) -> int:
    return tools._raw_int(row.get("section_no") or row.get("chapter_no")) or 0


def _structure_payload(
    client: Any,
    doc_id: str,
) -> tuple[catalogue.CatalogueResponse, Mapping[str, Any], Mapping[str, Any]]:
    sections_fn = getattr(client, "sections", None)
    if callable(sections_fn):
        try:
            sections_response = sections_fn(doc_id, limit=500, offset=0)
        except catalogue.CatalogueNotFound:
            sections_response = None
        if sections_response is not None and _raw_section_rows(sections_response.payload):
            return sections_response, sections_response.payload, {}

    chapters_response = client.chapters(doc_id, limit=500, offset=0)
    return chapters_response, {}, chapters_response.payload


def _candidate_matches(candidate: Mapping[str, Any], query: str) -> bool:
    query_tokens = _tokens(query)
    if not query_tokens:
        return True
    match_texts = tuple(_match_texts(candidate))
    haystack_tokens = _tokens(" ".join(match_texts))
    if not haystack_tokens:
        return False
    return all(token in haystack_tokens for token in query_tokens)


def _match_texts(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    raw = candidate.get("_match_texts")
    texts: list[str] = []
    if isinstance(raw, (list, tuple)):
        texts.extend(tools._string(item) for item in raw if tools._string(item))
    texts.extend(
        tools._string(candidate.get(key))
        for key in ("title", "authors", "section_id")
        if tools._string(candidate.get(key))
    )
    return tuple(dict.fromkeys(texts))


def _empty_section_reason(
    response: catalogue.CatalogueResponse,
    *,
    query: str,
    chapter_no: int | None,
    section_id: str,
) -> str:
    if query and chapter_no is None and not section_id and _raw_chapter_rows(response.payload):
        return tools.REASON_SECTION_ALIAS_MISSING
    return tools.REASON_NOT_FOUND


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", str(value or "").lower())
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return {
        token
        for token in "".join(ch if ch.isalnum() else " " for ch in ascii_text).split()
        if token
    }


def _unique_document_id(items: Sequence[Mapping[str, Any]]) -> str:
    ids = []
    for item in items:
        doc_id = tools._string(item.get("document_id"))
        if doc_id and doc_id not in ids:
            ids.append(doc_id)
    return ids[0] if len(ids) == 1 else ""
