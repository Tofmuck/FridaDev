"""Build a content-free Lot 1 baseline for Biblio document manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

from .catalogue_client import CatalogueClient, CatalogueClientConfig, CatalogueClientError
from .structure import build_document_manifest, build_manifest_baseline_payload


DEFAULT_OUTPUT_DIR = "app/docs/states/baselines/biblio-manifests"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="", help="Catalogue base URL override")
    parser.add_argument("--timeout-s", type=int, default=8)
    parser.add_argument("--output", default="", help="Output JSON path")
    parser.add_argument("--raw-unit-stats-json", default="", help="Optional content-free raw unit stats JSON")
    parser.add_argument("--db-audit-json", default="", help="Optional content-free DB audit summary JSON")
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

    manifests = []
    failures: list[dict[str, Any]] = []
    for item in _catalog_items(client):
        doc_id = str(item.get("id") or item.get("document_id") or "").strip()
        if not doc_id:
            failures.append({"status": "error", "reason_code": "missing_document_id"})
            continue
        try:
            metadata = client.metadata(doc_id).payload
            overview = client.document(doc_id).payload if args.include_overview else {}
            chapters = client.chapters(doc_id, limit=1000, offset=0).payload
            manifest = build_document_manifest(
                catalog_item=item,
                metadata_payload=metadata,
                overview_payload=overview,
                chapters_payload=chapters,
                raw_unit_stats=_mapping(raw_unit_stats.get(doc_id)),
            )
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
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "documents_seen": payload["summary"]["documents_seen"],
                "manifests_produced": payload["summary"]["manifests_produced"],
                "failures": payload["summary"]["failures"],
                "content_free": payload["content_policy"]["content_free"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if not failures else 2


def _catalog_items(client: CatalogueClient) -> list[Mapping[str, Any]]:
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


def _load_json_mapping(path: str) -> Mapping[str, Any]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
