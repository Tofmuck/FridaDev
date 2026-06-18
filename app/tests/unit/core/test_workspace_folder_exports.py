from __future__ import annotations

import unittest

from core import workspace_folder_exports
from core import workspace_folder_exports_store


EXPORT_ID = "11111111-2222-4333-8444-555555555555"
FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _FakeCursor:
    def __init__(self):
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append(" ".join(str(sql).split()))


class _FailingConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        raise RuntimeError("raw db failure with Export sensible and raw-etag-secret")


class _FakeLogger:
    def __init__(self):
        self.records = []

    def warning(self, message, *args, **kwargs):
        self.records.append((message, args, kwargs))


def _export(**overrides):
    payload = {
        "id": EXPORT_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Synthese sensible",
        "title_hash": "abc123def456",
        "target_name": "Synthese-sensible.pdf",
        "export_format": "pdf",
        "source_kind": "note",
        "source_ref": "workspace-note:11111111:abc123def456",
        "source_hash": "456defabc123",
        "content_hash": "789abc123def",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "remote_export_ref": "export:789abc123def",
        "etag_value": '"raw-etag-secret"',
        "etag_hash": "123456abcdef",
        "byte_size": 512,
        "char_count": 42,
        "reason_code": "folder_export_list_ok",
        "created_at": "2026-06-18T10:00:00Z",
        "updated_at": "2026-06-18T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


def _folder(*, linked=True, deleted=False):
    return {
        "id": FOLDER_ID,
        "display_name": "Projet Tulu",
        "nextcloud_sync_state": "linked" if linked else "local_only",
        "deleted_at": "2026-06-18T10:00:00Z" if deleted else None,
    }


class WorkspaceFolderExportsTests(unittest.TestCase):
    def test_schema_creates_mandatory_exports_table_without_foreign_model_dependency(self) -> None:
        cur = _FakeCursor()

        workspace_folder_exports_store.ensure_schema(cur)

        sql = "\n".join(cur.queries).lower()
        self.assertIn("create table if not exists workspace_folder_exports", sql)
        self.assertIn("workspace_folder_id uuid", sql)
        self.assertIn("references workspace_folders(id) on delete cascade", sql)
        self.assertIn("workspace_folder_exports_folder_title_format_active_idx", sql)
        self.assertIn("workspace_folder_exports_source_idx", sql)
        self.assertIn("export_format", sql)
        self.assertIn("source_kind", sql)
        self.assertIn("etag_value", sql)
        self.assertNotIn("export_content", sql)
        self.assertNotIn("body text", sql)
        self.assertNotIn("references workspace_files", sql)
        self.assertNotIn("references workspace_folder_notes", sql)

    def test_user_projection_keeps_title_and_technical_projection_redacts_sensitive_values(self) -> None:
        item = workspace_folder_exports.apply_export_projection(
            {
                **_export(),
                "export_content": "contenu exporte a ne jamais exposer",
                "markdown_content": "[MARKDOWN] secret",
                "path": "/opt/platform/fridadev/secret",
                "url": "https://example.test/remote.php/dav/files/secret",
                "xml": "<d:multistatus>secret</d:multistatus>",
                "authorization": "Bearer secret",
            }
        )

        user = item["export_v1_user"]
        technical = item["export_v1_technical"]
        self.assertEqual(user["title"], "Synthese sensible")
        self.assertEqual(user["format"], "pdf")
        self.assertEqual(technical["title_hash"], "abc123def456")
        self.assertEqual(technical["etag_hash"], "123456abcdef")
        self.assertTrue(technical["etag_present"])
        technical_text = str(technical)
        self.assertNotIn("Synthese sensible", technical_text)
        self.assertNotIn("raw-etag-secret", technical_text)
        self.assertNotIn("contenu exporte", technical_text)
        self.assertNotIn("remote.php", technical_text)
        self.assertNotIn("Bearer", technical_text)
        self.assertNotIn("target_name", technical_text)
        self.assertNotIn("remote_export_ref", technical_text)
        self.assertNotIn("etag_value", technical_text)
        self.assertNotIn("export_content", item)
        self.assertNotIn("markdown_content", item)
        self.assertNotIn("path", item)
        self.assertNotIn("url", item)
        self.assertNotIn("xml", item)
        self.assertNotIn("authorization", item)

    def test_invalid_ids_are_redacted_in_technical_refs(self) -> None:
        technical = workspace_folder_exports.build_technical_projection(
            _export(id="SecretExportName", workspace_folder_id="ProjetTulu")
        )

        self.assertNotIn("SecretExportName", str(technical))
        self.assertNotIn("ProjetTulu", str(technical))
        self.assertTrue(technical["export_ref"].startswith("workspace-export:redacted:"))
        self.assertTrue(technical["folder_ref"].startswith("workspace-folder:redacted:"))

    def test_title_validation_detects_local_sanitized_conflict_per_format(self) -> None:
        result = workspace_folder_exports.validate_export_title(
            "Plan",
            export_format="pdf",
            existing_exports=[
                {
                    "id": EXPORT_ID,
                    "title": "Plan",
                    "target_name": "Plan.pdf",
                    "title_hash": workspace_folder_exports.title_hash_for_target("Plan.pdf"),
                    "export_format": "pdf",
                    "local_state": "available",
                    "deleted_at": None,
                }
            ],
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_name_conflict")

    def test_same_title_is_allowed_for_different_export_format(self) -> None:
        result = workspace_folder_exports.validate_export_title(
            "Plan",
            export_format="txt",
            existing_exports=[
                {
                    "id": EXPORT_ID,
                    "target_name": "Plan.pdf",
                    "title_hash": workspace_folder_exports.title_hash_for_target("Plan.pdf"),
                    "export_format": "pdf",
                    "local_state": "available",
                    "deleted_at": None,
                }
            ],
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["target_name"], "Plan.txt")

    def test_tombstone_exports_are_excluded_from_active_projection_list(self) -> None:
        active = _export(id=EXPORT_ID, title="Active", target_name="Active.md", export_format="md")
        deleted = _export(
            id="22222222-3333-4444-8555-666666666666",
            title="Supprime",
            target_name="Supprime.md",
            export_format="md",
            local_state="deleted",
            deleted_at="2026-06-18T10:00:00Z",
        )

        items = workspace_folder_exports.apply_export_list([active, deleted])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["export_v1_user"]["title"], "Active")

    def test_non_linked_or_deleted_folder_marks_export_unavailable_for_future_writes(self) -> None:
        non_linked = workspace_folder_exports.build_technical_projection(
            _export(),
            folder=_folder(linked=False),
        )
        deleted = workspace_folder_exports.build_technical_projection(
            _export(),
            folder=_folder(deleted=True),
        )

        self.assertEqual(non_linked["status"], "unavailable")
        self.assertEqual(non_linked["reason_code"], "folder_export_folder_not_linked")
        self.assertEqual(deleted["status"], "unavailable")
        self.assertEqual(deleted["reason_code"], "folder_export_folder_deleted")

    def test_store_serialization_keeps_metadata_only_and_projection_hides_internal_refs(self) -> None:
        row = workspace_folder_exports_store.serialize_export_row(
            {
                **_export(),
                "source_ref": "https://example.test/remote.php/dav/leak",
                "remote_export_ref": "https://example.test/remote.php/dav/leak",
            }
        )

        self.assertIsNotNone(row)
        self.assertEqual(row["source_ref"], "")
        self.assertEqual(row["remote_export_ref"], "")
        projection = workspace_folder_exports.apply_export_projection(row)
        text = str(projection["export_v1_technical"])
        self.assertNotIn("remote.php", text)
        self.assertNotIn("raw-etag-secret", text)
        self.assertNotIn("target_name", text)
        self.assertNotIn("remote_export_ref", text)

    def test_list_exports_fail_closed_on_db_failure_without_raw_cause(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(workspace_folder_exports_store.WorkspaceFolderExportLookupError) as ctx:
            workspace_folder_exports_store.list_exports(
                FOLDER_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=True,
            )

        self.assertEqual(str(ctx.exception), "folder_export_lookup_failed")
        self.assertIsNone(ctx.exception.__cause__)
        self.assertIn("folder_export_lookup_failed", workspace_folder_exports.REASON_CODE_CATALOG)
        log_text = str(logger.records)
        self.assertNotIn("Export sensible", log_text)
        self.assertNotIn("raw-etag-secret", log_text)
        self.assertNotIn("sql", log_text.lower())

    def test_get_export_fail_closed_on_db_failure_without_raw_cause(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(workspace_folder_exports_store.WorkspaceFolderExportLookupError) as ctx:
            workspace_folder_exports_store.get_export(
                EXPORT_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=True,
            )

        self.assertEqual(ctx.exception.operation, "get")
        self.assertEqual(str(ctx.exception), "folder_export_lookup_failed")
        self.assertIsNone(ctx.exception.__cause__)
        self.assertNotIn("raw db failure", str(ctx.exception))

    def test_soft_lookup_compatibility_is_explicit(self) -> None:
        logger = _FakeLogger()

        self.assertEqual(
            workspace_folder_exports_store.list_exports(
                FOLDER_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=False,
            ),
            [],
        )
        self.assertIsNone(
            workspace_folder_exports_store.get_export(
                EXPORT_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=False,
            )
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
