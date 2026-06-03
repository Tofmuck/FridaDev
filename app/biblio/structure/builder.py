"""Derive content-free Biblio document manifests from Catalogue payloads."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .schema import (
    BASELINE_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    ROLE_SIGNAL_MAP,
    ROLE_UNKNOWN,
    STATE_AMBIGUOUS,
    STATE_DERIVED,
    STATE_KNOWN,
    STATE_UNKNOWN,
    Anchor,
    CanonicalReference,
    ContentRole,
    DocumentManifest,
    Interval,
    LibraryDocument,
    SectionNode,
    TextUnit,
    Work,
    _compact,
    language_signal,
    short_doc_id,
    text_signal,
)
from .validation import validate_document_manifest

def build_document_manifest(
    *,
    catalog_item: Mapping[str, Any],
    metadata_payload: Mapping[str, Any] | None = None,
    overview_payload: Mapping[str, Any] | None = None,
    chapters_payload: Mapping[str, Any] | None = None,
    raw_unit_stats: Mapping[str, Any] | None = None,
) -> DocumentManifest:
    document_row = _document_row(catalog_item, metadata_payload, overview_payload, chapters_payload)
    document_id = _string(document_row.get("id") or catalog_item.get("id") or catalog_item.get("document_id"))
    if not document_id:
        raise ValueError("document_id_required")

    unit_label = _string(document_row.get("unit_label") or catalog_item.get("unit_label") or "units") or "units"
    source_type = _string(document_row.get("source_type") or catalog_item.get("source_type") or "unknown") or "unknown"
    unit_count = _int(document_row.get("unit_count") or catalog_item.get("unit_count"))
    page_count = _int(document_row.get("page_count") or catalog_item.get("page_count"))
    paragraph_count = _int(document_row.get("paragraph_count") or catalog_item.get("paragraph_count"))
    chapter_count = _int(document_row.get("chapter_count") or catalog_item.get("chapter_count"))
    toc_source = _string(document_row.get("toc_source") or catalog_item.get("toc_source") or "none") or "none"

    metadata = _mapping((metadata_payload or {}).get("human_metadata"))
    metadata_status = _string(
        (metadata_payload or {}).get("metadata_status")
        or metadata.get("metadata_status")
        or catalog_item.get("human_metadata_status")
        or "unknown"
    )
    title_value = (
        metadata.get("canonical_title")
        or metadata.get("original_title")
        or document_row.get("title")
        or catalog_item.get("title")
    )
    source_filename = document_row.get("source_filename") or catalog_item.get("source_filename")
    language = language_signal(
        metadata.get("language_override")
        or document_row.get("language_detected")
        or catalog_item.get("language_detected")
    )

    library_document = LibraryDocument(
        document_id=document_id,
        title_signal=text_signal(title_value),
        source_filename_signal=text_signal(source_filename),
        source_type=source_type,
        technical_origin=_technical_origin(source_type, unit_label),
        technical_origin_state=_technical_origin_state(source_type),
        unit_label=unit_label,
        unit_count=unit_count,
        page_count=page_count,
        paragraph_count=paragraph_count,
        chapter_count=chapter_count,
        toc_source=toc_source,
        metadata_status=metadata_status or "unknown",
        language_state=language.get("state", STATE_UNKNOWN),
        language_signal=language,
        quality=_quality(document_row),
        source_limits=_source_limits(source_type, unit_label),
    )

    chapters = _chapter_rows(overview_payload, chapters_payload)
    sections = _section_nodes(document_id, unit_label, unit_count or page_count, chapters)
    works = (_document_scope_work(document_id, unit_label, unit_count or page_count, title_value),)
    text_units = _text_units(
        page_count=page_count,
        paragraph_count=paragraph_count,
        raw_unit_stats=raw_unit_stats,
        unit_label=unit_label,
    )
    canonical_references = _canonical_references(overview_payload, catalog_item)
    field_states = _field_states(
        document=library_document,
        sections=sections,
        raw_unit_stats=raw_unit_stats,
        canonical_references=canonical_references,
    )
    ambiguities = _ambiguities(source_type, unit_label, chapters, raw_unit_stats)
    limits = _limits(source_type, unit_label, chapters, raw_unit_stats)

    return DocumentManifest(
        manifest_version=MANIFEST_SCHEMA_VERSION,
        document=library_document,
        works=works,
        sections=sections,
        text_units=text_units,
        canonical_references=canonical_references,
        field_states=field_states,
        ambiguities=tuple(ambiguities),
        limits=tuple(limits),
    )


def build_manifest_baseline_payload(
    *,
    manifests: Sequence[DocumentManifest],
    failures: Sequence[Mapping[str, Any]] = (),
    generated_at: str,
    db_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_dicts = []
    for manifest in manifests:
        item = manifest.to_dict()
        item["validation"] = validate_document_manifest(manifest).to_dict()
        manifest_dicts.append(item)
    summary = _baseline_summary(manifests, failures=failures, db_audit=db_audit or {})
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "content_policy": {
            "content_free": True,
            "raw_book_text_included": False,
            "raw_prompt_included": False,
            "raw_catalogue_payload_included": False,
            "raw_titles_included": False,
            "raw_authors_included": False,
        },
        "summary": summary,
        "manifests": manifest_dicts,
        "failures": [dict(item) for item in failures],
    }


def _baseline_summary(
    manifests: Sequence[DocumentManifest],
    *,
    failures: Sequence[Mapping[str, Any]],
    db_audit: Mapping[str, Any],
) -> dict[str, Any]:
    origin_counts = Counter(manifest.document.technical_origin for manifest in manifests)
    source_counts = Counter(manifest.document.source_type for manifest in manifests)
    toc_counts = Counter(manifest.document.toc_source for manifest in manifests)
    validation_status_counts: Counter[str] = Counter()
    validation_reason_counts: Counter[str] = Counter()
    validation_warning_counts: Counter[str] = Counter()
    failure_reason_counts: Counter[str] = Counter()
    for failure in failures:
        failure_reason_counts[str(failure.get("reason_code") or "unknown")] += 1
    role_counts: Counter[str] = Counter()
    bounded_sections = 0
    for manifest in manifests:
        validation = validate_document_manifest(manifest)
        validation_status_counts[validation.status] += 1
        validation_reason_counts.update(validation.reason_codes)
        validation_warning_counts.update(validation.warning_codes)
        for section in manifest.sections:
            role_counts[section.content_role.value] += 1
            if section.end_anchor is not None:
                bounded_sections += 1
    docs_with = {
        "pages": sum(1 for manifest in manifests if manifest.document.page_count > 0),
        "paragraphs": sum(1 for manifest in manifests if manifest.document.paragraph_count > 0),
        "sections": sum(1 for manifest in manifests if manifest.sections),
        "raw_units": sum(
            1
            for manifest in manifests
            if any(unit.source == "db_raw_units" and unit.count > 0 for unit in manifest.text_units)
        ),
        "canonical_references": sum(1 for manifest in manifests if manifest.canonical_references),
    }
    return {
        "documents_seen": len(manifests) + len(failures),
        "manifests_produced": len(manifests),
        "failures": len(failures),
        "technical_origin_counts": dict(sorted(origin_counts.items())),
        "source_type_counts": dict(sorted(source_counts.items())),
        "toc_source_counts": dict(sorted(toc_counts.items())),
        "docs_with": docs_with,
        "sections_total": sum(len(manifest.sections) for manifest in manifests),
        "sections_with_derived_end": bounded_sections,
        "content_role_counts": dict(sorted(role_counts.items())),
        "validation_status_counts": dict(sorted(validation_status_counts.items())),
        "validation_reason_counts": dict(sorted(validation_reason_counts.items())),
        "validation_warning_counts": dict(sorted(validation_warning_counts.items())),
        "failure_reason_counts": dict(sorted(failure_reason_counts.items())),
        "invalid_manifest_failures": failure_reason_counts.get("manifest_validation_failed", 0),
        "ambiguity_count": sum(len(manifest.ambiguities) for manifest in manifests),
        "limit_count": sum(len(manifest.limits) for manifest in manifests),
        "db_audit": dict(db_audit),
    }


def _document_row(
    catalog_item: Mapping[str, Any],
    metadata_payload: Mapping[str, Any] | None,
    overview_payload: Mapping[str, Any] | None,
    chapters_payload: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    for payload in (metadata_payload, overview_payload, chapters_payload):
        row = _mapping((payload or {}).get("document"))
        if row:
            return row
    return catalog_item


def _chapter_rows(
    overview_payload: Mapping[str, Any] | None,
    chapters_payload: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    rows = (chapters_payload or {}).get("chapters")
    if not isinstance(rows, list):
        rows = (overview_payload or {}).get("chapters")
    if not isinstance(rows, list):
        return ()
    cleaned = []
    for row in rows:
        if isinstance(row, Mapping) and _int(row.get("chapter_no")) > 0 and _int(row.get("unit_no")) > 0:
            cleaned.append(row)
    return tuple(sorted(cleaned, key=lambda item: (_int(item.get("chapter_no")), _int(item.get("unit_no")))))


def _section_nodes(
    document_id: str,
    unit_label: str,
    document_unit_count: int,
    chapters: Sequence[Mapping[str, Any]],
) -> tuple[SectionNode, ...]:
    sections: list[SectionNode] = []
    for index, row in enumerate(chapters):
        chapter_no = _int(row.get("chapter_no"))
        start_unit = _int(row.get("unit_no"))
        next_start = _int(chapters[index + 1].get("unit_no")) if index + 1 < len(chapters) else 0
        end_unit = _derived_end_unit(start_unit, next_start, document_unit_count)
        section_id = f"{short_doc_id(document_id)}:section:{chapter_no}"
        start_anchor = Anchor(
            document_id=document_id,
            section_id=section_id,
            unit_label=unit_label,
            unit_no=start_unit,
            page_no=start_unit if unit_label == "pages" else None,
            source_state=STATE_KNOWN,
            source=_string(row.get("source") or "document_chapters"),
        )
        end_anchor = None
        boundary_state = STATE_UNKNOWN
        boundary_note = "section_end_unknown"
        if end_unit:
            end_anchor = Anchor(
                document_id=document_id,
                section_id=section_id,
                unit_label=unit_label,
                unit_no=end_unit,
                page_no=end_unit if unit_label == "pages" else None,
                source_state=STATE_DERIVED,
                source="next_chapter_or_document_end",
            )
            boundary_state = STATE_DERIVED
            boundary_note = "end_derived_from_next_chapter_or_document_end"
        role = _content_role(row)
        sections.append(
            SectionNode(
                section_id=section_id,
                sequence_no=chapter_no,
                level=1,
                title_signal=text_signal(row.get("title") or row.get("chapter_title")),
                source=_string(row.get("source") or "document_chapters") or "document_chapters",
                content_role=role,
                start_anchor=start_anchor,
                end_anchor=end_anchor,
                interval=Interval(
                    start=start_anchor,
                    end=end_anchor,
                    interval_type="section",
                    state=boundary_state,
                    source="document_chapters",
                    boundary_note=boundary_note,
                ),
                boundary_state=boundary_state,
                limits=tuple(_section_limits(row, end_anchor)),
            )
        )
    return tuple(sections)


def _document_scope_work(
    document_id: str,
    unit_label: str,
    document_unit_count: int,
    title_value: Any,
) -> Work:
    start = Anchor(
        document_id=document_id,
        unit_label=unit_label,
        unit_no=1 if document_unit_count > 0 else None,
        page_no=1 if unit_label == "pages" and document_unit_count > 0 else None,
        source_state=STATE_DERIVED,
        source="document_scope",
    )
    end = Anchor(
        document_id=document_id,
        unit_label=unit_label,
        unit_no=document_unit_count or None,
        page_no=document_unit_count if unit_label == "pages" and document_unit_count > 0 else None,
        source_state=STATE_DERIVED if document_unit_count > 0 else STATE_UNKNOWN,
        source="document_scope",
    )
    return Work(
        work_id=f"{short_doc_id(document_id)}:work:document_scope",
        work_kind="document_scope",
        title_signal=text_signal(title_value),
        state=STATE_DERIVED,
        source="catalogue_document",
        interval=Interval(
            start=start,
            end=end if document_unit_count > 0 else None,
            interval_type="document",
            state=STATE_DERIVED if document_unit_count > 0 else STATE_UNKNOWN,
            source="document_counts",
            boundary_note="document_scope_not_internal_work_detection",
        ),
        content_role=ContentRole(value=ROLE_UNKNOWN, state=STATE_UNKNOWN),
        limits=("internal_works_not_detected_without_explicit_toc_signal",),
    )


def _text_units(
    *,
    page_count: int,
    paragraph_count: int,
    raw_unit_stats: Mapping[str, Any] | None,
    unit_label: str,
) -> tuple[TextUnit, ...]:
    units = [
        TextUnit("page", page_count, STATE_KNOWN if page_count else STATE_UNKNOWN, "pages", unit_label),
        TextUnit(
            "paragraph",
            paragraph_count,
            STATE_KNOWN if paragraph_count else STATE_UNKNOWN,
            "paragraphs",
            unit_label,
        ),
    ]
    raw_stats = _mapping(raw_unit_stats)
    raw_kinds = _mapping(raw_stats.get("raw_unit_kinds"))
    if raw_kinds:
        for kind, count in sorted(raw_kinds.items()):
            units.append(
                TextUnit(
                    _string(kind) or "unknown",
                    _int(count),
                    STATE_KNOWN,
                    "db_raw_units",
                    unit_label,
                )
            )
    else:
        units.append(
            TextUnit(
                "raw_unit",
                0,
                STATE_UNKNOWN,
                "db_raw_units",
                unit_label,
                "raw_unit_distribution_missing_from_api_or_audit",
            )
        )
    return tuple(units)


def _canonical_references(
    overview_payload: Mapping[str, Any] | None,
    catalog_item: Mapping[str, Any],
) -> tuple[CanonicalReference, ...]:
    counts = _mapping((overview_payload or {}).get("milestone_counts"))
    references = [
        CanonicalReference(kind=_string(kind) or "unknown", count=_int(count))
        for kind, count in sorted(counts.items())
        if _int(count) > 0
    ]
    if not references and _int(catalog_item.get("stephanus_count")) > 0:
        references.append(CanonicalReference(kind="stephanus", count=_int(catalog_item.get("stephanus_count"))))
    return tuple(references)


def _field_states(
    *,
    document: LibraryDocument,
    sections: Sequence[SectionNode],
    raw_unit_stats: Mapping[str, Any] | None,
    canonical_references: Sequence[CanonicalReference],
) -> dict[str, str]:
    return {
        "document": STATE_KNOWN,
        "title": document.title_signal.get("state", STATE_UNKNOWN),
        "source_filename": document.source_filename_signal.get("state", STATE_UNKNOWN),
        "language": document.language_signal.get("state", STATE_UNKNOWN),
        "technical_origin": document.technical_origin_state,
        "pages": STATE_KNOWN if document.page_count else STATE_UNKNOWN,
        "paragraphs": STATE_KNOWN if document.paragraph_count else STATE_UNKNOWN,
        "raw_units": STATE_KNOWN if _mapping(raw_unit_stats).get("raw_unit_kinds") else STATE_UNKNOWN,
        "sections": STATE_KNOWN if sections else STATE_UNKNOWN,
        "section_bounds": STATE_DERIVED if any(section.end_anchor for section in sections) else STATE_UNKNOWN,
        "internal_works": STATE_UNKNOWN,
        "content_roles": STATE_DERIVED
        if any(section.content_role.state == STATE_DERIVED for section in sections)
        else STATE_UNKNOWN,
        "canonical_references": STATE_KNOWN if canonical_references else STATE_UNKNOWN,
    }


def _ambiguities(
    source_type: str,
    unit_label: str,
    chapters: Sequence[Mapping[str, Any]],
    raw_unit_stats: Mapping[str, Any] | None,
) -> list[str]:
    items: list[str] = []
    if source_type == "pdf":
        items.append("pdf_origin_does_not_distinguish_scanned_ocr_from_text_pdf")
    if unit_label not in {"pages", "sections"}:
        items.append("unit_label_not_canonical")
    if not chapters:
        items.append("toc_absent_or_unusable")
    if not _mapping(raw_unit_stats).get("raw_unit_kinds"):
        items.append("raw_unit_distribution_unknown")
    return items


def _limits(
    source_type: str,
    unit_label: str,
    chapters: Sequence[Mapping[str, Any]],
    raw_unit_stats: Mapping[str, Any] | None,
) -> list[str]:
    items = ["no_raw_book_text_in_manifest", "section_hierarchy_not_available"]
    if source_type == "pdf":
        items.append("pdf_quality_requires_external_ocr_text_audit")
    if unit_label == "sections":
        items.append("epub_sections_mapped_to_page_no_semantics_in_current_api")
    if chapters:
        items.append("section_ends_are_derived_not_imported")
    if not _mapping(raw_unit_stats).get("raw_unit_kinds"):
        items.append("raw_unit_counts_missing_unless_db_audit_provided")
    return items


def _quality(document_row: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "llm_json_quality_score": _optional_int(document_row.get("llm_json_quality_score")),
            "llm_json_format_valid": _optional_bool(document_row.get("llm_json_format_valid")),
            "llm_json_safe_for_db": _optional_bool(document_row.get("llm_json_safe_for_db")),
        }
    )


def _technical_origin(source_type: str, unit_label: str) -> str:
    if source_type == "epub":
        return "epub"
    if source_type == "pdf":
        return "pdf_unknown_ocr_or_text"
    if source_type:
        return source_type
    if unit_label == "sections":
        return "unknown_sectioned"
    return "unknown"


def _technical_origin_state(source_type: str) -> str:
    if source_type == "pdf":
        return STATE_AMBIGUOUS
    if source_type in {"epub", "unknown"}:
        return STATE_KNOWN if source_type == "epub" else STATE_UNKNOWN
    return STATE_KNOWN


def _source_limits(source_type: str, unit_label: str) -> tuple[str, ...]:
    limits: list[str] = []
    if source_type == "pdf":
        limits.append("pdf_source_type_does_not_encode_ocr_vs_text_pdf")
    if source_type == "epub":
        limits.append("epub_sections_are_exposed_through_page_like_api_units")
    if unit_label not in {"pages", "sections"}:
        limits.append("non_standard_unit_label")
    return tuple(limits)


def _content_role(row: Mapping[str, Any]) -> ContentRole:
    signal = _string(row.get("document_role_signal"))
    if signal in ROLE_SIGNAL_MAP:
        return ContentRole(
            value=ROLE_SIGNAL_MAP[signal],
            state=STATE_DERIVED,
            source=_string(row.get("document_role_signal_source") or "role_signal"),
            confidence=_string(row.get("document_role_signal_strength") or "weak") or "weak",
        )
    return ContentRole(value=ROLE_UNKNOWN, state=STATE_UNKNOWN)


def _section_limits(row: Mapping[str, Any], end_anchor: Anchor | None) -> list[str]:
    limits = []
    if end_anchor is None:
        limits.append("section_end_unknown")
    if not row.get("document_role_signal"):
        limits.append("content_role_unknown")
    return limits


def _derived_end_unit(start_unit: int, next_start: int, document_unit_count: int) -> int:
    if next_start and next_start > start_unit:
        return next_start - 1
    if document_unit_count and document_unit_count >= start_unit:
        return document_unit_count
    return 0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
