"""Content-free document manifests for Frida Biblio.

Lot 1 deliberately derives structure from the existing Catalogue/API payloads.
It does not change the import pipeline, the DB schema, chat runtime, or product
renderer.  The objects below are allowed to carry ids, counts, states, anchors
and short hashes, but not raw book text or raw bibliographic labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any, Mapping

MANIFEST_SCHEMA_VERSION = "frida_biblio_document_manifest.v1"
BASELINE_SCHEMA_VERSION = "frida_biblio_document_manifest_baseline.v1"

STATE_KNOWN = "known"
STATE_UNKNOWN = "unknown"
STATE_DERIVED = "derived"
STATE_AMBIGUOUS = "ambiguous"

ROLE_PRIMARY_TEXT = "primary_text"
ROLE_COMMENTARY = "commentary"
ROLE_PREFACE = "preface"
ROLE_INTRODUCTION = "introduction"
ROLE_NOTICE = "notice"
ROLE_NOTE = "note"
ROLE_APPARATUS = "apparatus"
ROLE_METADATA = "metadata"
ROLE_UNKNOWN = "unknown"

ROLE_SIGNAL_MAP = {
    "body": ROLE_PRIMARY_TEXT,
    "commentary": ROLE_COMMENTARY,
    "introduction": ROLE_INTRODUCTION,
    "notice": ROLE_NOTICE,
}

LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})?$")


def short_hash(value: Any, *, length: int = 12) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[: max(4, int(length))]


def short_doc_id(document_id: Any) -> str:
    return str(document_id or "").strip()[:8]


def text_signal(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {"state": STATE_UNKNOWN, "chars": 0, "sha256_12": ""}
    return {"state": STATE_KNOWN, "chars": len(text), "sha256_12": short_hash(text)}


def language_signal(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {"state": STATE_UNKNOWN}
    normalized = text.lower().replace("_", "-")
    if LANGUAGE_CODE_RE.fullmatch(normalized):
        return {"state": STATE_KNOWN, "value": normalized, "source": "catalogue_metadata"}
    return {
        "state": STATE_DERIVED,
        "chars": len(text),
        "sha256_12": short_hash(text),
        "source": "catalogue_metadata_non_code",
    }


@dataclass(frozen=True)
class AliasSignal:
    values: tuple[str, ...] = field(default_factory=tuple, repr=False, compare=False)
    state: str = STATE_UNKNOWN
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        signals = []
        for value in self.values[:20]:
            signal = text_signal(value)
            if signal.get("state") != STATE_UNKNOWN:
                signals.append(signal)
        return _compact(
            {
                "state": self.state,
                "count": len(self.values),
                "source": self.source,
                "signals": signals,
            }
        )


@dataclass(frozen=True)
class ContentRole:
    value: str = ROLE_UNKNOWN
    state: str = STATE_UNKNOWN
    source: str = ""
    confidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "value": self.value,
                "state": self.state,
                "source": self.source,
                "confidence": self.confidence,
            }
        )


@dataclass(frozen=True)
class Anchor:
    document_id: str
    unit_label: str
    unit_no: int | None = None
    page_no: int | None = None
    para_no: int | None = None
    raw_unit_index: int | None = None
    char_offset: int | None = None
    section_id: str = ""
    source_state: str = STATE_UNKNOWN
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "document_id": self.document_id,
                "doc_id_short": short_doc_id(self.document_id),
                "unit_label": self.unit_label,
                "unit_no": self.unit_no,
                "page_no": self.page_no,
                "para_no": self.para_no,
                "raw_unit_index": self.raw_unit_index,
                "char_offset": self.char_offset,
                "section_id": self.section_id,
                "source_state": self.source_state,
                "source": self.source,
            }
        )


@dataclass(frozen=True)
class Interval:
    start: Anchor | None = None
    end: Anchor | None = None
    interval_type: str = "unknown"
    state: str = STATE_UNKNOWN
    source: str = ""
    boundary_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "type": self.interval_type,
                "state": self.state,
                "source": self.source,
                "boundary_note": self.boundary_note,
                "start": self.start.to_dict() if self.start else None,
                "end": self.end.to_dict() if self.end else None,
            }
        )


@dataclass(frozen=True)
class CanonicalReference:
    kind: str
    count: int
    state: str = STATE_KNOWN
    source: str = "milestones"

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "kind": self.kind,
                "count": self.count,
                "state": self.state,
                "source": self.source,
            }
        )


@dataclass(frozen=True)
class TextUnit:
    unit_kind: str
    count: int
    state: str
    source: str
    unit_label: str = ""
    coverage_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "unit_kind": self.unit_kind,
                "count": self.count,
                "state": self.state,
                "source": self.source,
                "unit_label": self.unit_label,
                "coverage_note": self.coverage_note,
            }
        )


@dataclass(frozen=True)
class LibraryDocument:
    document_id: str
    title_signal: dict[str, Any]
    source_filename_signal: dict[str, Any]
    source_type: str
    technical_origin: str
    technical_origin_state: str
    unit_label: str
    unit_count: int
    page_count: int
    paragraph_count: int
    chapter_count: int
    toc_source: str
    metadata_status: str
    language_state: str
    language_signal: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    source_limits: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "document_id": self.document_id,
                "doc_id_short": short_doc_id(self.document_id),
                "title_signal": self.title_signal,
                "source_filename_signal": self.source_filename_signal,
                "source_type": self.source_type,
                "technical_origin": self.technical_origin,
                "technical_origin_state": self.technical_origin_state,
                "unit_label": self.unit_label,
                "unit_count": self.unit_count,
                "page_count": self.page_count,
                "paragraph_count": self.paragraph_count,
                "chapter_count": self.chapter_count,
                "toc_source": self.toc_source,
                "metadata_status": self.metadata_status,
                "language_state": self.language_state,
                "language_signal": self.language_signal,
                "quality": self.quality,
                "source_limits": list(self.source_limits),
            }
        )


@dataclass(frozen=True)
class Work:
    work_id: str
    work_kind: str
    title_signal: dict[str, Any]
    state: str
    source: str
    interval: Interval
    content_role: ContentRole
    limits: tuple[str, ...] = field(default_factory=tuple)
    aliases: AliasSignal = field(default_factory=AliasSignal)

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "work_id": self.work_id,
                "work_kind": self.work_kind,
                "title_signal": self.title_signal,
                "state": self.state,
                "source": self.source,
                "interval": self.interval.to_dict(),
                "content_role": self.content_role.to_dict(),
                "limits": list(self.limits),
                "aliases": self.aliases.to_dict(),
            }
        )


@dataclass(frozen=True)
class SectionNode:
    section_id: str
    sequence_no: int
    level: int
    title_signal: dict[str, Any]
    source: str
    content_role: ContentRole
    start_anchor: Anchor
    end_anchor: Anchor | None
    interval: Interval
    boundary_state: str
    parent_id: str = ""
    limits: tuple[str, ...] = field(default_factory=tuple)
    aliases: AliasSignal = field(default_factory=AliasSignal)

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "section_id": self.section_id,
                "sequence_no": self.sequence_no,
                "level": self.level,
                "parent_id": self.parent_id,
                "title_signal": self.title_signal,
                "source": self.source,
                "content_role": self.content_role.to_dict(),
                "start_anchor": self.start_anchor.to_dict(),
                "end_anchor": self.end_anchor.to_dict() if self.end_anchor else None,
                "interval": self.interval.to_dict(),
                "boundary_state": self.boundary_state,
                "limits": list(self.limits),
                "aliases": self.aliases.to_dict(),
            }
        )


@dataclass(frozen=True)
class DocumentManifest:
    manifest_version: str
    document: LibraryDocument
    works: tuple[Work, ...]
    sections: tuple[SectionNode, ...]
    text_units: tuple[TextUnit, ...]
    canonical_references: tuple[CanonicalReference, ...]
    field_states: dict[str, str]
    ambiguities: tuple[str, ...]
    limits: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "manifest_version": self.manifest_version,
                "document": self.document.to_dict(),
                "works": [work.to_dict() for work in self.works],
                "sections": [section.to_dict() for section in self.sections],
                "text_units": [unit.to_dict() for unit in self.text_units],
                "canonical_references": [
                    reference.to_dict() for reference in self.canonical_references
                ],
                "field_states": dict(sorted(self.field_states.items())),
                "ambiguities": list(self.ambiguities),
                "limits": list(self.limits),
            }
        )


@dataclass(frozen=True)
class ManifestValidationResult:
    status: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    warning_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "status": self.status,
                "reason_codes": list(self.reason_codes),
                "warning_codes": list(self.warning_codes),
            }
        )


def _compact(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if value not in ("", None, [], {}, ())
    }
