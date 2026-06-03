"""Validation contract for content-free Biblio document manifests."""

from __future__ import annotations

from .schema import (
    MANIFEST_SCHEMA_VERSION,
    STATE_KNOWN,
    STATE_UNKNOWN,
    DocumentManifest,
    ManifestValidationResult,
)

STATUS_VALID = "valid"
STATUS_VALID_WITH_WARNINGS = "valid_with_warnings"
STATUS_INVALID = "invalid"


def validate_document_manifest(manifest: DocumentManifest) -> ManifestValidationResult:
    """Return a content-free validation result for a manifest projection.

    The validator deliberately checks shape, anchors and structural availability,
    not bibliographic truth.  Missing canonical fields become explicit reason
    codes so a new import cannot silently escape the shared Biblio format.
    """

    reasons: list[str] = []
    warnings: list[str] = []
    document = manifest.document

    if manifest.manifest_version != MANIFEST_SCHEMA_VERSION:
        reasons.append("manifest_version_unsupported")
    if not document.document_id:
        reasons.append("document_id_missing")
    if not document.source_type:
        reasons.append("source_type_missing")
    if not document.technical_origin:
        reasons.append("technical_origin_missing")
    if not document.unit_label:
        reasons.append("unit_label_missing")
    if document.unit_count <= 0 and document.page_count <= 0:
        reasons.append("document_units_missing")
    if document.page_count <= 0:
        reasons.append("pages_missing")
    if document.paragraph_count <= 0:
        reasons.append("paragraphs_missing")
    if not manifest.works:
        reasons.append("document_scope_work_missing")
    if not manifest.text_units:
        reasons.append("text_units_missing")

    if document.language_signal.get("state", STATE_UNKNOWN) == STATE_UNKNOWN:
        warnings.append("language_unknown")
    if document.technical_origin_state != STATE_KNOWN:
        warnings.append("technical_origin_not_fully_known")
    if manifest.field_states.get("raw_units") != STATE_KNOWN:
        warnings.append("raw_units_unknown")
    if manifest.field_states.get("sections") != STATE_KNOWN:
        warnings.append("sections_unknown")
    if manifest.field_states.get("internal_works") != STATE_KNOWN:
        warnings.append("internal_works_unknown")
    if manifest.field_states.get("content_roles") != STATE_KNOWN:
        warnings.append("content_roles_not_fully_known")
    if manifest.field_states.get("canonical_references") != STATE_KNOWN:
        warnings.append("canonical_references_unknown")
    if any(section.end_anchor is None for section in manifest.sections):
        warnings.append("section_bounds_incomplete")

    if reasons:
        status = STATUS_INVALID
    elif warnings:
        status = STATUS_VALID_WITH_WARNINGS
    else:
        status = STATUS_VALID

    return ManifestValidationResult(
        status=status,
        reason_codes=tuple(sorted(set(reasons))),
        warning_codes=tuple(sorted(set(warnings))),
    )
