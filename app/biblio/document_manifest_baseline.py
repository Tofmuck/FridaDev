"""Build a content-free Lot 1 baseline for Biblio document manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Mapping, Protocol

from .catalogue_client import CatalogueClient, CatalogueClientConfig, CatalogueClientError
from .structure import (
    STATUS_INVALID,
    build_document_manifest,
    build_manifest_baseline_payload,
    validate_document_manifest,
)


DEFAULT_OUTPUT_DIR = "app/docs/states/baselines/biblio-manifests"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="", help="Catalogue base URL override")
    parser.add_argument("--timeout-s", type=int, default=8)
    parser.add_argument("--output", default="", help="Output JSON path")
    parser.add_argument("--raw-unit-stats-json", default="", help="Optional content-free raw unit stats JSON")
    parser.add_argument("--db-audit-json", default="", help="Optional content-free DB audit summary JSON")
    parser.add_argument(
        "--database-url",
        default="",
        help="Optional document DB URL; default uses DOC_PIPELINE_DATABASE_URL or DATABASE_URL.",
    )
    parser.add_argument(
        "--no-db-audit",
        action="store_true",
        help="Disable integrated content-free DB audit collection.",
    )
    parser.add_argument(
        "--include-overview",
        action="store_true",
        help="Also call GET /doc/{id}; off by default because it can be heavy on large documents.",
    )
    args = parser.parse_args(argv)

    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = generated_at.replace("-", "").replace(":", "").replace("+00:00", "Z")
    output = Path(args.output) if args.output else Path(DEFAULT_OUTPUT_DIR) / f"frida-biblio-document-manifest-lot1-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    config = CatalogueClientConfig(
        base_url=(args.base_url.strip().rstrip("/") if args.base_url else "http://platform-doc-pipeline-api:8090"),
        timeout_s=max(1, int(args.timeout_s or 8)),
    )
    client = CatalogueClient(config=config)
    raw_unit_stats = _load_json_mapping(args.raw_unit_stats_json)
    db_audit = _load_json_mapping(args.db_audit_json)

    if not args.no_db_audit and (not raw_unit_stats or not db_audit):
        collected = collect_content_free_db_audit(
            args.database_url
            or os.getenv("DOC_PIPELINE_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or ""
        )
        if not raw_unit_stats:
            raw_unit_stats = _mapping(collected.get("raw_unit_stats"))
        if not db_audit:
            db_audit = _mapping(collected.get("db_audit"))
    elif not db_audit:
        db_audit = {"status": "skipped", "reason_code": "db_audit_disabled"}

    payload, failures = build_baseline_from_client(
        client=client,
        generated_at=generated_at,
        raw_unit_stats=raw_unit_stats,
        db_audit=db_audit,
        include_overview=args.include_overview,
    )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "documents_seen": payload["summary"]["documents_seen"],
                "manifests_produced": payload["summary"]["manifests_produced"],
                "failures": payload["summary"]["failures"],
                "validation_status_counts": payload["summary"].get("validation_status_counts", {}),
                "content_free": payload["content_policy"]["content_free"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if not failures else 2


class CatalogueLike(Protocol):
    def catalog(self, *, limit: int, offset: int) -> Any: ...
    def metadata(self, document_id: str) -> Any: ...
    def document(self, document_id: str) -> Any: ...
    def chapters(self, document_id: str, *, limit: int, offset: int) -> Any: ...


def build_baseline_from_client(
    *,
    client: CatalogueLike,
    generated_at: str,
    raw_unit_stats: Mapping[str, Any] | None = None,
    db_audit: Mapping[str, Any] | None = None,
    include_overview: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifests = []
    failures: list[dict[str, Any]] = []
    for item in _catalog_items(client):
        doc_id = str(item.get("id") or item.get("document_id") or "").strip()
        if not doc_id:
            failures.append({"status": "error", "reason_code": "missing_document_id"})
            continue
        try:
            metadata = client.metadata(doc_id).payload
            overview = client.document(doc_id).payload if include_overview else {}
            chapters = client.chapters(doc_id, limit=1000, offset=0).payload
            manifest = build_document_manifest(
                catalog_item=item,
                metadata_payload=metadata,
                overview_payload=overview,
                chapters_payload=chapters,
                raw_unit_stats=_mapping((raw_unit_stats or {}).get(doc_id)),
            )
            validation = validate_document_manifest(manifest)
            if validation.status == STATUS_INVALID:
                failures.append(
                    {
                        "document_id": doc_id,
                        "doc_id_short": doc_id[:8],
                        "status": "invalid",
                        "reason_code": "manifest_validation_failed",
                        "validation_reason_codes": list(validation.reason_codes),
                        "validation_warning_codes": list(validation.warning_codes),
                    }
                )
                continue
            manifests.append(manifest)
        except CatalogueClientError as exc:
            failures.append(
                {
                    "document_id": doc_id,
                    "doc_id_short": doc_id[:8],
                    "status": "error",
                    "reason_code": exc.reason_code,
                    "endpoint_kind": exc.endpoint_kind,
                    "status_code": exc.status_code,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "document_id": doc_id,
                    "doc_id_short": doc_id[:8],
                    "status": "error",
                    "reason_code": "manifest_build_failed",
                    "error_class": exc.__class__.__name__,
                }
            )

    payload = build_manifest_baseline_payload(
        manifests=manifests,
        failures=failures,
        generated_at=generated_at,
        db_audit=db_audit,
    )
    return payload, failures


def collect_content_free_db_audit(database_url: str) -> Mapping[str, Any]:
    if not database_url:
        return {
            "raw_unit_stats": {},
            "db_audit": {"status": "unavailable", "reason_code": "db_url_not_provided"},
        }
    try:
        import psycopg  # type: ignore[import-not-found]
    except Exception as exc:
        return {
            "raw_unit_stats": {},
            "db_audit": {
                "status": "unavailable",
                "reason_code": "psycopg_unavailable",
                "error_class": exc.__class__.__name__,
            },
        }
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            return collect_content_free_db_audit_from_connection(conn)
    except Exception as exc:
        return {
            "raw_unit_stats": {},
            "db_audit": {
                "status": "error",
                "reason_code": "db_audit_failed",
                "error_class": exc.__class__.__name__,
            },
        }


def collect_content_free_db_audit_from_connection(conn: Any) -> Mapping[str, Any]:
    raw_unit_stats: dict[str, dict[str, Any]] = {}
    for document_id, unit_kind, count in _query_rows(
        conn,
        """
        SELECT document_id::text, unit_kind, COUNT(*)::int
        FROM raw_units
        GROUP BY document_id, unit_kind
        ORDER BY document_id::text, unit_kind
        """,
    ):
        entry = raw_unit_stats.setdefault(
            str(document_id),
            {"raw_unit_count": 0, "raw_unit_kinds": {}},
        )
        entry["raw_unit_count"] += int(count or 0)
        entry["raw_unit_kinds"][str(unit_kind or "unknown")] = int(count or 0)

    db_audit = {
        "status": "ok",
        "source": "fridadev_document_manifest_baseline_db_audit",
        "tables": _table_counts(conn),
        "source_type_unit_label_counts": _pair_counts(
            conn,
            """
            SELECT COALESCE(source_type, 'unknown'), COALESCE(unit_label, 'unknown'), COUNT(*)::int
            FROM documents
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
            first_key="source_type",
            second_key="unit_label",
        ),
        "toc_source_counts": _single_counts(
            conn,
            """
            SELECT COALESCE(toc_source, 'none'), COUNT(*)::int
            FROM documents
            GROUP BY 1
            ORDER BY 1
            """,
        ),
        "metadata_status_counts": _single_counts(
            conn,
            """
            SELECT COALESCE(metadata_status, 'to_review'), COUNT(*)::int
            FROM catalogue_human_metadata
            GROUP BY 1
            ORDER BY 1
            """,
        ),
        "language_state_counts": {
            "known": _scalar(
                conn,
                """
                SELECT COUNT(*)::int
                FROM documents d
                LEFT JOIN catalogue_human_metadata h ON h.document_id = d.id
                WHERE COALESCE(NULLIF(h.language_override, ''), NULLIF(d.language_detected, '')) IS NOT NULL
                """,
            ),
            "unknown": _scalar(
                conn,
                """
                SELECT COUNT(*)::int
                FROM documents d
                LEFT JOIN catalogue_human_metadata h ON h.document_id = d.id
                WHERE COALESCE(NULLIF(h.language_override, ''), NULLIF(d.language_detected, '')) IS NULL
                """,
            ),
        },
        "milestone_kind_counts": _single_counts(
            conn,
            """
            SELECT kind, COUNT(*)::int
            FROM milestones
            GROUP BY kind
            ORDER BY kind
            """,
        ),
        "quality_counts": {
            "llm_json_format_valid_true": _scalar(conn, "SELECT COUNT(*)::int FROM documents WHERE llm_json_format_valid IS TRUE"),
            "llm_json_format_valid_false": _scalar(conn, "SELECT COUNT(*)::int FROM documents WHERE llm_json_format_valid IS FALSE"),
            "llm_json_safe_for_db_true": _scalar(conn, "SELECT COUNT(*)::int FROM documents WHERE llm_json_safe_for_db IS TRUE"),
            "llm_json_safe_for_db_false": _scalar(conn, "SELECT COUNT(*)::int FROM documents WHERE llm_json_safe_for_db IS FALSE"),
        },
        "content_policy": {
            "content_free": True,
            "raw_book_text_included": False,
            "raw_titles_included": False,
            "raw_authors_included": False,
        },
    }
    return {"raw_unit_stats": raw_unit_stats, "db_audit": db_audit}


def _catalog_items(client: CatalogueLike) -> list[Mapping[str, Any]]:
    items: list[Mapping[str, Any]] = []
    offset = 0
    limit = 500
    total = None
    while total is None or offset < total:
        response = client.catalog(limit=limit, offset=offset)
        payload = response.payload
        batch = payload.get("items")
        if not isinstance(batch, list):
            break
        items.extend(item for item in batch if isinstance(item, Mapping))
        total = int(payload.get("total") or len(items))
        if not batch:
            break
        offset += len(batch)
    return items


def _table_counts(conn: Any) -> dict[str, int]:
    tables = (
        "documents",
        "pages",
        "paragraphs",
        "raw_units",
        "document_chapters",
        "milestones",
    )
    return {table: _scalar(conn, f"SELECT COUNT(*)::int FROM {table}") for table in tables}


def _single_counts(conn: Any, sql: str) -> dict[str, int]:
    return {str(key or "unknown"): int(count or 0) for key, count in _query_rows(conn, sql)}


def _pair_counts(conn: Any, sql: str, *, first_key: str, second_key: str) -> list[dict[str, Any]]:
    return [
        {first_key: str(first or "unknown"), second_key: str(second or "unknown"), "count": int(count or 0)}
        for first, second, count in _query_rows(conn, sql)
    ]


def _scalar(conn: Any, sql: str) -> int:
    rows = _query_rows(conn, sql)
    if not rows:
        return 0
    return int((rows[0][0] if rows[0] else 0) or 0)


def _query_rows(conn: Any, sql: str) -> list[Any]:
    with conn.cursor() as cur:
        cur.execute(sql)
        return list(cur.fetchall())


def _load_json_mapping(path: str) -> Mapping[str, Any]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
