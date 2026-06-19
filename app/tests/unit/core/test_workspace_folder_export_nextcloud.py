from __future__ import annotations

import unittest

from core import workspace_folder_export_nextcloud_client
from core import workspace_folder_export_nextcloud_runtime
from core import workspace_folder_exports
from core import workspace_folder_exports_service
from core import workspace_folder_nextcloud_client


EXPORT_ID = "11111111-2222-4333-8444-555555555555"
FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _FakeExportsModule:
    def __init__(self, *, existing=None, fail_list=False, fail_upsert=False):
        self.existing = list(existing or [])
        self.fail_list = fail_list
        self.fail_upsert = fail_upsert
        self.stored = []
        self.events = []

    def list_exports(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        if self.fail_list:
            raise RuntimeError("raw db failure with export private")
        if include_deleted:
            return list(self.existing)
        return [item for item in self.existing if not item.get("deleted_at")]

    def upsert_export(self, **fields):
        if self.fail_upsert:
            raise RuntimeError("raw db failure with export private")
        self.stored.append(dict(fields))
        return _export(
            id=fields["export_id"],
            workspace_folder_id=fields["workspace_folder_id"],
            title=fields["title"],
            title_hash=workspace_folder_exports.title_hash_for_target(fields["target_name"]),
            target_name=fields["target_name"],
            export_format=fields["export_format"],
            source_kind=fields["source_kind"],
            source_ref=fields["source_ref"],
            source_hash=fields["source_hash"],
            content_hash=fields["content_hash"],
            local_state=fields["local_state"],
            nextcloud_sync_state=fields["nextcloud_sync_state"],
            remote_export_ref=fields["remote_export_ref"],
            etag_value=fields["etag_value"],
            etag_hash=fields["etag_hash"],
            byte_size=fields["byte_size"],
            char_count=fields["char_count"],
            reason_code=fields["reason_code"],
        )

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeNextcloudExports:
    def __init__(self, *, status_reason="", put_reason="", delete_reason="", etag='"etag-secret"'):
        self.status_reason = status_reason
        self.put_reason = put_reason
        self.delete_reason = delete_reason
        self.etag = etag
        self.status_calls = []
        self.put_calls = []
        self.deleted = []

    def exports_status(self, folder_name):
        self.status_calls.append(folder_name)
        if self.status_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.status_reason,
                http_status=404 if self.status_reason.endswith("_missing") else 207,
            )
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_STORE_OK,
            207,
        )

    def put_export(self, folder_name, export_name, content, *, media_type=""):
        self.put_calls.append(
            {
                "folder_name": folder_name,
                "export_name": export_name,
                "content": bytes(content or b""),
                "media_type": media_type,
            }
        )
        if self.put_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.put_reason,
                http_status=409 if "conflict" in self.put_reason else 503,
            )
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_STORE_OK,
            201,
            etag_value=self.etag,
        )

    def delete_export(self, folder_name, export_name, *, missing_ok=True):
        self.deleted.append((folder_name, export_name, missing_ok))
        if self.delete_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.delete_reason,
                http_status=503,
            )
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _StatusOnlyExportClient(workspace_folder_export_nextcloud_client.NextcloudExportClient):
    def __init__(self, status):
        super().__init__(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )
        self.status = status

    def _request_status(self, method, url, *, data=None, headers=None):
        return self.status, '"etag-secret"'


class _FakeFolders:
    def __init__(self, *, linked=True, deleted=False):
        self.folder = _folder(linked=linked, deleted=deleted)

    def normalize_workspace_folder_id(self, value):
        return FOLDER_ID if str(value or "") == FOLDER_ID else None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        return dict(self.folder) if folder_id == FOLDER_ID else None


class _FakeRuntime:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def store_workspace_folder_export_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _folder(*, linked=True, deleted=False):
    return {
        "id": FOLDER_ID,
        "display_name": "Projet Tulu",
        "nextcloud_target_name": "Projet-Tulu",
        "nextcloud_sync_state": "linked" if linked else "local_only",
        "deleted_at": "2026-06-19T10:00:00Z" if deleted else None,
    }


def _export(**overrides):
    payload = {
        "id": EXPORT_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Synthese sensible",
        "title_hash": workspace_folder_exports.title_hash_for_target("Synthese-sensible.txt"),
        "target_name": "Synthese-sensible.txt",
        "export_format": "txt",
        "source_kind": "conversation",
        "source_ref": "conversation:22222222:abc123def456",
        "source_hash": "abc123def456",
        "content_hash": "456defabc123",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "remote_export_ref": "workspace-export:11111111:abc123def456",
        "etag_value": '"etag-secret"',
        "etag_hash": "789abc123def",
        "byte_size": 512,
        "char_count": 42,
        "reason_code": workspace_folder_exports.REASON_STORE_OK,
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


def _request(**overrides):
    payload = {
        "export_id": EXPORT_ID,
        "export_format": "txt",
        "title": "Synthese sensible",
        "source_kind": "conversation",
        "explicit_source": True,
        "conversation_id": "22222222-3333-4444-8555-666666666666",
        "messages": [
            {"id": "u1", "role": "user", "content": "Contenu synthetique source"},
            {"id": "a1", "role": "assistant", "content": "Reponse synthetique source"},
        ],
    }
    payload.update(overrides)
    return payload


class WorkspaceFolderExportNextcloudTests(unittest.TestCase):
    def test_store_export_nextcloud_first_persists_metadata_only_after_remote_creation(self) -> None:
        exports = _FakeExportsModule()
        nextcloud = _FakeNextcloudExports()

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(),
            exports_module=exports,
            nextcloud=nextcloud,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_store_ok")
        self.assertEqual(nextcloud.status_calls, ["Projet-Tulu"])
        self.assertEqual(nextcloud.put_calls[0]["export_name"], "Synthese-sensible.txt")
        self.assertIn(b"Contenu synthetique source", nextcloud.put_calls[0]["content"])
        self.assertEqual(exports.stored[0]["target_name"], "Synthese-sensible.txt")
        self.assertEqual(exports.stored[0]["nextcloud_sync_state"], "linked")
        self.assertEqual(exports.stored[0]["etag_value"], '"etag-secret"')
        self.assertNotIn("export_content", exports.stored[0])
        self.assertNotIn("export_bytes", exports.stored[0])
        projected = workspace_folder_exports.apply_export_projection(result["export"], folder=_folder(linked=True))
        self.assertEqual(projected["export_v1_user"]["title"], "Synthese sensible")
        technical_text = str(projected["export_v1_technical"])
        self.assertNotIn("Synthese sensible", technical_text)
        self.assertNotIn("Contenu synthetique source", technical_text)
        self.assertNotIn("etag-secret", str(result["export_nextcloud"]))
        self.assertNotIn("Synthese-sensible.txt", str(result["export_nextcloud"]))

    def test_store_export_refuses_non_linked_folder_before_generation_or_webdav(self) -> None:
        nextcloud = _FakeNextcloudExports()
        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=False),
            request=_request(),
            exports_module=_FakeExportsModule(),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_folder_not_linked")
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])

    def test_store_export_refuses_missing_or_non_collection_exports_target(self) -> None:
        for reason in (
            workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING,
            workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
        ):
            with self.subTest(reason=reason):
                result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
                    folder=_folder(linked=True),
                    request=_request(),
                    exports_module=_FakeExportsModule(),
                    nextcloud=_FakeNextcloudExports(status_reason=reason),
                )

                self.assertFalse(result["ok"])
                self.assertEqual(result["reason_code"], reason)

    def test_store_export_refuses_local_conflict_without_remote_put(self) -> None:
        existing = _export()
        nextcloud = _FakeNextcloudExports()

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(title="Synthese sensible"),
            exports_module=_FakeExportsModule(existing=[existing]),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_name_conflict")
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])

    def test_export_client_accepts_only_safe_creation_status_for_put(self) -> None:
        ok = _StatusOnlyExportClient(201).put_export("Projet", "Export.txt", b"")
        self.assertTrue(ok.ok)
        self.assertEqual(ok.status_class, "2xx")

        for status in (200, 204):
            with self.assertRaises(workspace_folder_export_nextcloud_client.NextcloudExportClientError) as ctx:
                _StatusOnlyExportClient(status).put_export("Projet", "Export.txt", b"")
            self.assertEqual(ctx.exception.reason_code, "folder_export_name_conflict")

    def test_store_export_rolls_back_remote_if_local_persistence_fails(self) -> None:
        nextcloud = _FakeNextcloudExports()

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(),
            exports_module=_FakeExportsModule(fail_upsert=True),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_local_persistence_failed")
        self.assertTrue(result["export_nextcloud"]["rollback"]["ok"])
        self.assertEqual(nextcloud.deleted[0], ("Projet-Tulu", "Synthese-sensible.txt", True))
        self.assertNotIn("Synthese sensible", str(result["export_nextcloud"]))
        self.assertNotIn("Contenu synthetique source", str(result["export_nextcloud"]))

    def test_store_export_reports_content_free_when_remote_rollback_fails(self) -> None:
        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(),
            exports_module=_FakeExportsModule(fail_upsert=True),
            nextcloud=_FakeNextcloudExports(
                delete_reason=workspace_folder_exports.REASON_REMOTE_COMPENSATION_FAILED
            ),
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["export_nextcloud"]["rollback"]["ok"])
        self.assertEqual(
            result["export_nextcloud"]["rollback"]["reason_code"],
            "folder_export_remote_compensation_failed",
        )
        self.assertNotIn("Synthese sensible", str(result["export_nextcloud"]))
        self.assertNotIn("Contenu synthetique source", str(result["export_nextcloud"]))

    def test_service_response_uses_route_folder_and_exposes_projection_without_raw_target(self) -> None:
        runtime = _FakeRuntime(
            {
                "ok": True,
                "status": 201,
                "reason_code": workspace_folder_exports.REASON_STORE_OK,
                "export": _export(),
                "export_nextcloud": {
                    "store_state": "stored",
                    "reason_code": workspace_folder_exports.REASON_STORE_OK,
                    "export_name_hash": workspace_folder_exports.title_hash_for_target(
                        "Synthese-sensible.txt"
                    ),
                    "http_status_class": "2xx",
                    "etag_present": True,
                    "etag_hash": "789abc123def",
                },
            }
        )

        payload, status = workspace_folder_exports_service.create_workspace_folder_export_response(
            FOLDER_ID,
            {**_request(), "workspace_folder_id": "99999999-2222-4333-8444-555555555555"},
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_folder_exports_module=_FakeExportsModule(),
            exports_nextcloud_runtime_module=runtime,
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(runtime.calls[0]["request"]["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(payload["export"]["export_v1_user"]["title"], "Synthese sensible")
        self.assertNotIn("target_name", payload["export"])
        self.assertNotIn("etag_value", payload["export"])
        self.assertNotIn("Synthese-sensible.txt", str(payload["export"]["export_v1_technical"]))
        self.assertNotIn("etag-secret", str(payload))


if __name__ == "__main__":
    unittest.main()
