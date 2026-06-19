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


class _UpsertCursor:
    def __init__(self):
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.params = params

    def fetchone(self):
        params = self.params
        return {
            "id": params[0],
            "workspace_folder_id": params[1],
            "title": params[2],
            "title_hash": params[3],
            "target_name": params[4],
            "export_format": params[5],
            "source_kind": params[6],
            "source_ref": params[7],
            "source_hash": params[8],
            "content_hash": params[9],
            "local_state": params[10],
            "nextcloud_sync_state": params[11],
            "remote_export_ref": params[12],
            "etag_value": params[13],
            "etag_hash": params[14],
            "byte_size": params[15],
            "char_count": params[16],
            "reason_code": params[17],
            "created_at": "2026-06-18T10:00:00Z",
            "updated_at": "2026-06-18T10:00:00Z",
            "deleted_at": None,
        }


class _UpsertConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _UpsertCursor()

    def commit(self):
        return None


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
        "nextcloud_target_name": "Projet-Tulu",
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
        self.assertIn("nextcloud_sync_state text not null default 'sync_error'", sql)
        self.assertIn("alter column nextcloud_sync_state set default 'sync_error'", sql)
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

    def test_user_projection_exposes_download_open_actions_without_reuse_source(self) -> None:
        item = workspace_folder_exports.apply_export_projection(_export())

        user = item["export_v1_user"]
        technical = item["export_v1_technical"]
        self.assertTrue(user["can_download"])
        self.assertTrue(user["can_open"])
        self.assertFalse(user["can_reuse_as_source"])
        self.assertEqual(
            user["actions"]["download_reason_code"],
            "folder_export_download_ok",
        )
        self.assertEqual(
            user["actions"]["open_reason_code"],
            "folder_export_download_ok",
        )
        self.assertEqual(
            user["actions"]["reuse_as_source_reason_code"],
            "folder_export_access_not_prepared",
        )
        self.assertNotIn("actions", technical)
        self.assertNotIn("raw-etag-secret", str(user["actions"]))
        self.assertNotIn("Synthese-sensible.pdf", str(user["actions"]))

    def test_user_projection_refuses_actions_when_export_is_not_linked(self) -> None:
        user = workspace_folder_exports.build_user_projection(
            _export(nextcloud_sync_state="sync_error")
        )

        self.assertFalse(user["can_download"])
        self.assertFalse(user["can_open"])
        self.assertFalse(user["can_reuse_as_source"])
        self.assertEqual(user["actions"]["download_reason_code"], "folder_export_not_linked")
        self.assertEqual(user["actions"]["open_reason_code"], "folder_export_not_linked")
        self.assertEqual(
            user["actions"]["reuse_as_source_reason_code"],
            "folder_export_not_linked",
        )

    def test_user_projection_refuses_actions_without_persisted_folder_target(self) -> None:
        user = workspace_folder_exports.build_user_projection(
            _export(),
            folder={**_folder(), "nextcloud_target_name": ""},
        )

        self.assertFalse(user["can_download"])
        self.assertFalse(user["can_open"])
        self.assertFalse(user["can_reuse_as_source"])
        self.assertEqual(user["actions"]["download_reason_code"], "folder_export_name_invalid")
        self.assertEqual(user["actions"]["open_reason_code"], "folder_export_name_invalid")

    def test_technical_projection_rejects_private_alnum_source_ref(self) -> None:
        technical = workspace_folder_exports.build_technical_projection(
            _export(source_ref="FlorenceBoitezPrivateNote")
        )

        self.assertEqual(technical["source_ref"], "")
        self.assertNotIn("FlorenceBoitezPrivateNote", str(technical))

    def test_technical_projection_allows_only_structured_content_free_source_ref(self) -> None:
        valid_refs = [
            "workspace-note:11111111:abc123def456",
            "workspace-file:redacted:abc123def456",
            "workspace-export:11111111:abc123def456",
            "conversation:redacted:abc123def456",
            "message-selection:11111111:abc123def456",
            "frida-response:redacted:abc123def456",
        ]

        for ref in valid_refs:
            with self.subTest(ref=ref):
                technical = workspace_folder_exports.build_technical_projection(
                    _export(source_ref=ref)
                )
                self.assertEqual(technical["source_ref"], ref)

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

    def test_upsert_without_nextcloud_proof_defaults_to_sync_error(self) -> None:
        row = workspace_folder_exports_store.upsert_export(
            export_id=EXPORT_ID,
            workspace_folder_id=FOLDER_ID,
            title="Synthese locale",
            target_name="Synthese-locale.md",
            export_format="md",
            source_kind="conversation",
            source_ref="conversation:11111111:abc123def456",
            db_conn_func=lambda: _UpsertConnection(),
            logger=_FakeLogger(),
        )

        self.assertEqual(row["nextcloud_sync_state"], "sync_error")
        self.assertEqual(row["reason_code"], "folder_export_nextcloud_error_redacted")
        user = workspace_folder_exports.build_user_projection(row)
        technical = workspace_folder_exports.build_technical_projection(row)
        self.assertEqual(user["nextcloud_sync_state"], "sync_error")
        self.assertEqual(user["sync_label"], "synchronisation incomplete")
        self.assertEqual(technical["nextcloud_sync_state"], "sync_error")
        self.assertNotEqual(technical["nextcloud_sync_state"], "linked")

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
