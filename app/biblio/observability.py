"""Content-free observability helpers for native Biblio.

This module does not call Catalogue, does not build prompt content, and does
not write state.  It only projects already produced Biblio objects into compact
operator/admin facts.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

from . import catalogue_client
from .passage_extractor import BiblioPassageResult, STATUS_EXTRACTED
from .prompt_lane import BiblioPromptLane


SCHEMA_VERSION = "1"
MODULE_KEY = "biblio"
EVENT_STAGE = "biblio"
SOURCE_KIND = "biblio_native_catalogue"

ADMIN_ROUTE = "/api/admin/biblio/observability"

_TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-.:/")
_HEX_CHARS = set("0123456789abcdef")
_DANGEROUS_KEYS = {
    "author",
    "authors",
    "authorization",
    "content",
    "context",
    "cookie",
    "dsn",
    "env",
    "excerpt",
    "headers",
    "lane_message",
    "message",
    "messages",
    "ocr_text",
    "passage",
    "payload",
    "prompt",
    "query",
    "raw",
    "request",
    "secret",
    "source_filename",
    "text",
    "title",
    "token",
}
_HASH_KEYS = {"hash", "sha256_12", "passage_hash", "text_sha256_12", "content_sha256_12"}
_DOC_ID_KEYS = {"doc_id", "doc_id_short", "document_id", "document_candidate_ids", "doc_id_shorts"}
_TOKEN_KEYS = {
    "calculation_version",
    "decision",
    "endpoint_kind",
    "error_class",
    "event_kind",
    "kind",
    "module_key",
    "query_kind",
    "reason_code",
    "requested_locator_kind",
    "source_kind",
    "source_reason_code",
    "status",
}


def build_admin_observability(*, config_module: Any = None) -> dict[str, Any]:
    """Return a read-only, content-free status payload for operators."""
    config = catalogue_client.get_catalogue_client_config(config_module)
    base_url, base_url_status = _sanitized_base_url(config.base_url)
    return {
        "kind": "biblio_admin_observability",
        "schema_version": SCHEMA_VERSION,
        "module_key": MODULE_KEY,
        "source_kind": SOURCE_KIND,
        "status": "available_wired",
        "admin_route": ADMIN_ROUTE,
        "module_state": {
            "client_available": True,
            "resolver_available": True,
            "extractor_available": True,
            "prompt_lane_available": True,
            "observability_available": True,
            "chat_wired": True,
            "frontend_wired": True,
            "toggle_wired": True,
            "automatic_catalogue_call": False,
            "db_write": False,
        },
        "config": {
            "catalogue_base_url": base_url,
            "catalogue_base_url_status": base_url_status,
            "timeout_s": int(config.timeout_s),
            "get_only": True,
            "allowed_methods": ["GET"],
            "allowed_endpoint_kinds": [
                catalogue_client.ENDPOINT_HEALTH,
                catalogue_client.ENDPOINT_CATALOG,
                catalogue_client.ENDPOINT_DOCUMENT,
                catalogue_client.ENDPOINT_METADATA,
                catalogue_client.ENDPOINT_LOCATE,
                catalogue_client.ENDPOINT_CONTEXT,
                catalogue_client.ENDPOINT_SEARCH,
            ],
            "forbidden_mutations": [
                "DELETE /doc/{id}",
                "DELETE /doc/{id}/with-files",
                "PUT /doc/{id}/metadata",
                "PUT /settings",
                "POST /settings/reset",
                "POST /progress/recent/clear",
            ],
        },
        "components": {
            "client": {
                "status": "available",
                "get_only": True,
                "reason_code": "biblio_catalogue_client_available",
            },
            "resolver": {
                "status": "available",
                "reason_code": "biblio_document_resolver_available",
            },
            "extractor": {
                "status": "available",
                "reason_code": "biblio_passage_extractor_available",
            },
            "prompt_lane": {
                "status": "available",
                "reason_code": "biblio_prompt_lane_available",
                "raw_prompt_content_included": False,
            },
            "observability": {
                "status": "available",
                "reason_code": "biblio_observability_content_free",
            },
        },
        "boundaries": _boundaries(),
        "redaction": _redaction(),
    }


def build_biblio_event_payload(
    *,
    enabled: bool = False,
    used: bool = False,
    query_kind: str = "",
    client_response: Any = None,
    client_error: Any = None,
    resolution: Any = None,
    passage_result: Any = None,
    prompt_lane: Any = None,
    status: str = "",
    reason_code: str = "",
) -> dict[str, Any]:
    """Project one potential Biblio operation into compact observability.

    The function is intentionally passive.  Lot 6 exposes the builder and admin
    surface; later chat wiring may decide when to call and emit it.
    """
    client_items = [
        item
        for item in (
            *_object_projections(client_response),
            *_object_projections(client_error),
        )
        if item
    ]
    resolver_projection = _object_projection(resolution)
    extractor_projection = _passage_result_projection(passage_result)
    lane_projection = _prompt_lane_projection(prompt_lane)
    counts = _counts(
        client_items=client_items,
        resolver=resolver_projection,
        extractor=extractor_projection,
        lane=lane_projection,
    )
    safe_reason_code = _safe_token(reason_code)
    reason_counts = _reason_counts(
        {"reason_code": safe_reason_code} if safe_reason_code else {},
        client_items,
        resolver_projection,
        extractor_projection,
        lane_projection,
    )
    effective_used = bool(used or client_items or resolver_projection or extractor_projection or lane_projection)
    effective_status = _event_status(
        explicit=status,
        enabled=enabled,
        used=effective_used,
        resolver=resolver_projection,
        extractor=extractor_projection,
        lane=lane_projection,
        client_items=client_items,
    )
    return {
        "kind": "biblio_observability_event",
        "schema_version": SCHEMA_VERSION,
        "module_key": MODULE_KEY,
        "source_kind": SOURCE_KIND,
        "enabled": bool(enabled),
        "used": effective_used,
        "query_kind": _safe_token(query_kind) or ("not_requested" if not enabled else "unknown"),
        "status": effective_status,
        "reason_code": safe_reason_code,
        "client": {
            "event_count": len(client_items),
            "items": client_items,
        },
        "resolver": resolver_projection,
        "extractor": extractor_projection,
        "lane": lane_projection,
        "counts": counts,
        "confidence": {
            "available": False,
            "reason_code": "biblio_confidence_not_implemented",
        },
        "reason_code_counts": reason_counts,
        "boundaries": _boundaries(),
        "redaction": _redaction(),
    }


def emit_biblio_event(payload: Mapping[str, Any], *, chat_turn_logger_module: Any) -> bool:
    """Emit a compact Biblio event if a turn logger is already active."""
    emitter = getattr(chat_turn_logger_module, "emit", None)
    if not callable(emitter):
        return False
    clean_payload = _sanitize_mapping(payload)
    return bool(
        emitter(
            EVENT_STAGE,
            status=_event_log_status(str(clean_payload.get("status") or "")),
            payload=clean_payload,
        )
    )


def _boundaries() -> dict[str, bool]:
    return {
        "active_document": False,
        "workspace": False,
        "memory_rag": False,
        "identity": False,
        "summary": False,
        "web": False,
        "hermeneutic": False,
        "anythingllm": False,
        "ocr_active_documents": False,
    }


def _redaction() -> dict[str, bool]:
    return {
        "raw_content_included": False,
        "raw_passage_included": False,
        "raw_catalogue_payload_included": False,
        "raw_prompt_included": False,
        "raw_query_included": False,
        "raw_locator_included": False,
        "secret_included": False,
    }


def _object_projection(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    to_observability = getattr(value, "to_observability", None)
    if callable(to_observability):
        try:
            projected = dict(to_observability())
            if isinstance(value, catalogue_client.CatalogueClientError):
                projected.setdefault("status", "error")
            elif isinstance(value, catalogue_client.CatalogueResponse):
                projected.setdefault("status", "ok")
            return _sanitize_mapping(projected)
        except Exception as exc:  # pragma: no cover - defensive projection path.
            return {
                "status": "error",
                "reason_code": "biblio_observability_projection_error",
                "error_class": _safe_token(exc.__class__.__name__),
            }
    if isinstance(value, Mapping):
        return _sanitize_mapping(value)
    return {
        "status": "unsupported",
        "reason_code": "biblio_observability_unsupported_object",
        "object_class": _safe_token(value.__class__.__name__),
    }


def _object_projections(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        projections: list[dict[str, Any]] = []
        for item in value:
            projected = _object_projection(item)
            if projected:
                projections.append(projected)
        return projections
    projected = _object_projection(value)
    return [projected] if projected else []


def _passage_result_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, BiblioPassageResult):
        return _object_projection(value)
    observed = dict(value.to_observability())
    observed["passage_hash"] = _observable_passage_hash(value)
    observed.pop("passage", None)
    return _sanitize_mapping(observed)


def _prompt_lane_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, BiblioPromptLane):
        return _object_projection(value)
    observed = dict(value.to_observability())
    observed.pop("message", None)
    return _sanitize_mapping(observed)


def _counts(
    *,
    client_items: Sequence[Mapping[str, Any]],
    resolver: Mapping[str, Any],
    extractor: Mapping[str, Any],
    lane: Mapping[str, Any],
) -> dict[str, Any]:
    resolver_document = resolver.get("document") if isinstance(resolver.get("document"), Mapping) else {}
    return {
        "client_event_count": len(client_items),
        "document_candidate_count": _to_int(resolver.get("document_candidate_count")),
        "locator_candidate_count": _to_int(resolver.get("locator_candidate_count")),
        "document_resolved_count": 1 if resolver_document else 0,
        "passage_count": _to_int(lane.get("passage_count"))
        or (1 if extractor.get("status") == STATUS_EXTRACTED else 0),
        "skipped_count": _to_int(lane.get("skipped_count")),
        "passage_chars": _to_int(extractor.get("passage_chars")),
        "lane_chars": _to_int(lane.get("chars")),
        "hash_count": len(lane.get("hashes") or []) if isinstance(lane.get("hashes"), Sequence) else 0,
    }


def _reason_counts(*values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            reason = _safe_token(value.get("reason_code"))
            if reason:
                counts[reason] = int(counts.get(reason, 0)) + 1
            for child in value.values():
                visit(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for child in value:
                visit(child)

    for value in values:
        visit(value)
    return dict(sorted(counts.items()))


def _event_status(
    *,
    explicit: str,
    enabled: bool,
    used: bool,
    resolver: Mapping[str, Any],
    extractor: Mapping[str, Any],
    lane: Mapping[str, Any],
    client_items: Sequence[Mapping[str, Any]],
) -> str:
    explicit_status = _safe_token(explicit)
    if explicit_status:
        return explicit_status
    client_statuses = {str(item.get("status") or "").lower() for item in client_items}
    resolver_status = str(resolver.get("status") or "").lower()
    extractor_status = str(extractor.get("status") or "").lower()
    if "error" in client_statuses or resolver_status == "catalogue_unavailable" or extractor_status == "catalogue_unavailable":
        return "error"
    if resolver_status == "ambiguous":
        return "ambiguous"
    if resolver_status == "not_found" or extractor_status == "not_found":
        return "not_found"
    if extractor_status == STATUS_EXTRACTED or _to_int(lane.get("passage_count")) > 0:
        return "ok"
    if used:
        return "skipped"
    if enabled:
        return "not_used"
    return "not_applicable"


def _event_log_status(status: str) -> str:
    if status in {"error", "catalogue_unavailable"}:
        return "error"
    if status in {"not_applicable", "not_used", "skipped"}:
        return "skipped"
    return "ok"


def _sanitize_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, raw_value in value.items():
        key_text = str(key or "").strip()
        if not key_text:
            continue
        if key_text.lower() in _DANGEROUS_KEYS:
            continue
        clean[key_text] = _sanitize_value(raw_value, key=key_text)
    return clean


def _sanitize_value(value: Any, *, key: str = "") -> Any:
    key_l = key.lower()
    if isinstance(value, Mapping):
        return _sanitize_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(item, key=key) for item in list(value)[:50]]
    if isinstance(value, str):
        if key_l in _HASH_KEYS:
            return _strict_hash_12(value)
        if key_l in _DOC_ID_KEYS:
            return _safe_doc_id(value)
        if key_l in _TOKEN_KEYS:
            return _safe_token(value)
        return _compact_text_signal(value)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    return _compact_text_signal(str(value))


def _safe_token(value: Any, *, max_chars: int = 120) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered != text:
        return f"sha256:{_sha256_12(text)}"
    if any(char not in _TOKEN_CHARS for char in lowered):
        return f"sha256:{_sha256_12(text)}"
    return lowered[:max_chars]


def _safe_doc_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 16 and all(char.lower() in _TOKEN_CHARS for char in text):
        return text[:8]
    return f"sha256:{_sha256_12(text)}"


def _strict_hash_12(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) == 12 and all(char in _HEX_CHARS for char in text):
        return text
    return ""


def _observable_passage_hash(result: BiblioPassageResult) -> str:
    if result.passage:
        return _sha256_12(result.passage)
    return _strict_hash_12(result.passage_hash)


def _compact_text_signal(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {"present": False, "chars": 0, "sha256_12": ""}
    return {
        "present": True,
        "chars": len(text),
        "sha256_12": _sha256_12(text),
    }


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _sanitized_base_url(value: str) -> tuple[str, str]:
    parsed = urlparse(str(value or "").strip())
    if not parsed.scheme or not parsed.hostname:
        return "", "invalid"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{parsed.hostname}{port}"
    path = parsed.path.rstrip("/")
    sanitized = urlunparse((parsed.scheme, netloc, path, "", "", ""))
    return sanitized.rstrip("/"), "ok"
