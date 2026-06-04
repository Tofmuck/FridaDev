"""Public imports for Biblio document manifests."""

from __future__ import annotations

from .builder import build_document_manifest, build_manifest_baseline_payload
from .schema import (
    BASELINE_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    STATE_AMBIGUOUS,
    STATE_DERIVED,
    STATE_KNOWN,
    STATE_UNKNOWN,
    AliasSignal,
    Anchor,
    CanonicalReference,
    ContentRole,
    DocumentManifest,
    Interval,
    LibraryDocument,
    ManifestValidationResult,
    SectionNode,
    TextUnit,
    Work,
    language_signal,
    short_doc_id,
    text_signal,
)
from .validation import (
    STATUS_INVALID,
    STATUS_VALID,
    STATUS_VALID_WITH_WARNINGS,
    validate_document_manifest,
)

__all__ = [
    "BASELINE_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "STATE_AMBIGUOUS",
    "STATE_DERIVED",
    "STATE_KNOWN",
    "STATE_UNKNOWN",
    "AliasSignal",
    "Anchor",
    "CanonicalReference",
    "ContentRole",
    "DocumentManifest",
    "Interval",
    "LibraryDocument",
    "ManifestValidationResult",
    "SectionNode",
    "TextUnit",
    "Work",
    "STATUS_INVALID",
    "STATUS_VALID",
    "STATUS_VALID_WITH_WARNINGS",
    "build_document_manifest",
    "build_manifest_baseline_payload",
    "language_signal",
    "short_doc_id",
    "text_signal",
    "validate_document_manifest",
]
