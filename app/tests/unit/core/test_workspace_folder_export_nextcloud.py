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
    def __init__(
        self,
        *,
        status_reason="",
        put_reason="",
        delete_reason="",
        etag='"etag-secret"',
        remote_version_after_put="",
    ):
        self.status_reason = status_reason
        self.put_reason = put_reason
        self.delete_reason = delete_reason
        self.etag = etag
        self.remote_version_after_put = remote_version_after_put
        self.status_calls = []
        self.put_calls = []
        self.deleted = []
        self.conditional_delete_calls = []
        self.remote_present = False
        self.remote_version = ""

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
        self.remote_present = True
        self.remote_version = self.remote_version_after_put or self.etag
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
        self.remote_present = False
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
            204,
        )

    def delete_created_export_if_match(self, folder_name, export_name, *, etag_value):
        self.conditional_delete_calls.append((folder_name, export_name, etag_value))
        if self.delete_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.delete_reason,
                http_status=503,
            )
        if not etag_value:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                "folder_export_remote_compensation_ownership_unverified"
            )
        if self.remote_version != etag_value:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                "folder_export_remote_compensation_precondition_failed",
                http_status=412,
            )
        self.remote_present = False
        self.deleted.append((folder_name, export_name, True))
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _StatusOnlyExportClient(workspace_folder_export_nextcloud_client.NextcloudExportClient):
    def __init__(self, status, *, response_etag='"etag-secret"'):
        super().__init__(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )
        self.status = status
        self.response_etag = response_etag

    def _request_status(self, method, url, *, data=None, headers=None):
        self.last_headers = dict(headers or {})
        return self.status, self.response_etag


class _ContentOnlyExportClient(workspace_folder_export_nextcloud_client.NextcloudExportClient):
    def __init__(self, status, content=b"export"):
        super().__init__(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )
        self.status = status
        self.content = bytes(content)
        self.calls = []

    def _request_content(self, method, url, *, max_bytes):
        self.calls.append((method, url, max_bytes))
        if self.status == 200 and len(self.content) > max_bytes:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                workspace_folder_exports.REASON_TOO_LARGE,
                http_status=200,
            )
        return self.status, self.content if self.status == 200 else b""


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
        self.assertNotEqual(exports.stored[0]["export_id"], EXPORT_ID)
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

    def test_store_export_conversation_uses_reader_before_payload_messages(self) -> None:
        exports = _FakeExportsModule()
        nextcloud = _FakeNextcloudExports()

        def conversation_reader(payload):
            return {
                "ok": True,
                "conversation_id": payload["conversation_id"],
                "title": "Conversation relue",
                "messages": [
                    {"id": "u-store", "role": "user", "content": "Contenu relu depuis store"},
                    {"id": "a-store", "role": "assistant", "content": "Reponse relue depuis store"},
                ],
            }

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(
                title="Conversation relue",
                messages=[
                    {"id": "u-injected", "role": "user", "content": "Message client injecte"},
                ],
            ),
            exports_module=exports,
            nextcloud=nextcloud,
            conversation_reader=conversation_reader,
        )

        self.assertTrue(result["ok"])
        stored_content = nextcloud.put_calls[0]["content"]
        self.assertIn(b"Contenu relu depuis store", stored_content)
        self.assertIn(b"Reponse relue depuis store", stored_content)
        self.assertNotIn(b"Message client injecte", stored_content)

    def test_store_export_refuses_client_export_id_before_webdav_or_upsert(self) -> None:
        exports = _FakeExportsModule()
        nextcloud = _FakeNextcloudExports()

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(export_id=EXPORT_ID),
            exports_module=exports,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_client_export_id_forbidden")
        self.assertEqual(result["status"], 400)
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])
        self.assertEqual(exports.stored, [])

    def test_store_export_refuses_existing_client_export_id_conflict_before_remote_creation(self) -> None:
        exports = _FakeExportsModule(existing=[_export(id=EXPORT_ID)])
        nextcloud = _FakeNextcloudExports()

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(export_id=EXPORT_ID, title="Autre titre"),
            exports_module=exports,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_client_export_id_forbidden")
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])
        self.assertEqual(exports.stored, [])

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

    def test_export_compensation_client_uses_if_match_and_distinguishes_outcomes(self) -> None:
        success = _StatusOnlyExportClient(204)
        success.last_headers = None
        delete_if_match = getattr(success, "delete_created_export_if_match", None)
        self.assertTrue(callable(delete_if_match))
        deleted = delete_if_match("Folder", "sample.txt", etag_value='"created-version"')
        self.assertEqual(deleted.reason_code, "folder_export_remote_compensation_ok")
        self.assertEqual(success.last_headers, {"If-Match": '"created-version"'})

        missing = _StatusOnlyExportClient(404).delete_created_export_if_match(
            "Folder",
            "sample.txt",
            etag_value='"created-version"',
        )
        self.assertEqual(missing.reason_code, "folder_export_remote_compensation_missing")

        with self.assertRaises(workspace_folder_export_nextcloud_client.NextcloudExportClientError) as refused:
            _StatusOnlyExportClient(412).delete_created_export_if_match(
                "Folder",
                "sample.txt",
                etag_value='"created-version"',
            )
        self.assertEqual(
            refused.exception.reason_code,
            "folder_export_remote_compensation_precondition_failed",
        )

        no_version = _StatusOnlyExportClient(204)
        no_version.last_headers = None
        with self.assertRaises(workspace_folder_export_nextcloud_client.NextcloudExportClientError) as unverified:
            no_version.delete_created_export_if_match("Folder", "sample.txt", etag_value="")
        self.assertEqual(
            unverified.exception.reason_code,
            "folder_export_remote_compensation_ownership_unverified",
        )
        self.assertIsNone(no_version.last_headers)

        oversized = _StatusOnlyExportClient(201, response_etag='"' + ("x" * 600) + '"')
        created = oversized.put_export("Folder", "sample.txt", b"synthetic")
        self.assertEqual(created.etag_value, "")
        oversized.last_headers = None
        with self.assertRaises(
            workspace_folder_export_nextcloud_client.NextcloudExportClientError
        ) as oversized_unverified:
            oversized.delete_created_export_if_match(
                "Folder",
                "sample.txt",
                etag_value=created.etag_value,
            )
        self.assertEqual(
            oversized_unverified.exception.reason_code,
            "folder_export_remote_compensation_ownership_unverified",
        )
        self.assertIsNone(oversized.last_headers)

    def test_export_client_reads_exact_target_without_listing(self) -> None:
        client = _ContentOnlyExportClient(200, b"contenu export")

        result = client.read_export("Projet", "Export.txt", max_bytes=25 * 1024 * 1024)

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, "folder_export_download_ok")
        self.assertEqual(result.content, b"contenu export")
        self.assertEqual(result.status_class, "2xx")
        method, url, max_bytes = client.calls[0]
        self.assertEqual(method, "GET")
        self.assertIn("/Exports/Export.txt", url)
        self.assertEqual(max_bytes, 25 * 1024 * 1024)

    def test_export_client_refuses_missing_or_oversized_download(self) -> None:
        with self.assertRaises(workspace_folder_export_nextcloud_client.NextcloudExportClientError) as missing:
            _ContentOnlyExportClient(404).read_export(
                "Projet",
                "Export.txt",
                max_bytes=25 * 1024 * 1024,
            )
        self.assertEqual(missing.exception.reason_code, "folder_export_not_found")

        with self.assertRaises(workspace_folder_export_nextcloud_client.NextcloudExportClientError) as too_large:
            _ContentOnlyExportClient(200, b"x" * 11).read_export(
                "Projet",
                "Export.txt",
                max_bytes=10,
            )
        self.assertEqual(too_large.exception.reason_code, "folder_export_too_large")

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
        self.assertEqual(result["export_nextcloud"]["rollback"]["state"], "deleted")
        self.assertEqual(len(nextcloud.conditional_delete_calls), 1)
        self.assertFalse(nextcloud.remote_present)
        self.assertEqual(nextcloud.deleted[0], ("Projet-Tulu", "Synthese-sensible.txt", True))
        self.assertNotIn("Synthese sensible", str(result["export_nextcloud"]))
        self.assertNotIn("Contenu synthetique source", str(result["export_nextcloud"]))

    def test_store_export_reports_content_free_when_remote_rollback_fails(self) -> None:
        nextcloud = _FakeNextcloudExports(
            delete_reason=workspace_folder_exports.REASON_REMOTE_COMPENSATION_FAILED
        )
        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(),
            exports_module=_FakeExportsModule(fail_upsert=True),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["export_nextcloud"]["rollback"]["ok"])
        self.assertEqual(result["export_nextcloud"]["rollback"]["state"], "failed")
        self.assertEqual(
            result["export_nextcloud"]["rollback"]["reason_code"],
            "folder_export_remote_compensation_failed",
        )
        self.assertTrue(nextcloud.remote_present)
        self.assertEqual(nextcloud.remote_version, '"etag-secret"')
        self.assertEqual(len(nextcloud.conditional_delete_calls), 1)
        self.assertEqual(nextcloud.deleted, [])
        self.assertNotIn("Synthese sensible", str(result["export_nextcloud"]))
        self.assertNotIn("Contenu synthetique source", str(result["export_nextcloud"]))

    def test_store_export_preserves_changed_remote_version_after_local_failure(self) -> None:
        nextcloud = _FakeNextcloudExports(remote_version_after_put='"changed-version"')

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(),
            exports_module=_FakeExportsModule(fail_upsert=True),
            nextcloud=nextcloud,
        )

        self.assertTrue(nextcloud.remote_present)
        self.assertEqual(nextcloud.remote_version, '"changed-version"')
        self.assertEqual(
            result["export_nextcloud"]["rollback"]["reason_code"],
            "folder_export_remote_compensation_precondition_failed",
        )
        self.assertEqual(result["export_nextcloud"]["rollback"]["state"], "precondition_failed")
        self.assertEqual(nextcloud.deleted, [])

    def test_store_export_without_creation_version_retains_remote_object(self) -> None:
        nextcloud = _FakeNextcloudExports(etag="", remote_version_after_put='"unproven-version"')

        result = workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            folder=_folder(linked=True),
            request=_request(),
            exports_module=_FakeExportsModule(fail_upsert=True),
            nextcloud=nextcloud,
        )

        self.assertTrue(nextcloud.remote_present)
        self.assertEqual(nextcloud.remote_version, '"unproven-version"')
        self.assertEqual(
            result["export_nextcloud"]["rollback"]["reason_code"],
            "folder_export_remote_compensation_ownership_unverified",
        )
        self.assertEqual(nextcloud.conditional_delete_calls, [])
        self.assertEqual(nextcloud.deleted, [])

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

    def test_service_refuses_client_export_id_before_runtime_call(self) -> None:
        runtime = _FakeRuntime({"ok": True})

        payload, status = workspace_folder_exports_service.create_workspace_folder_export_response(
            FOLDER_ID,
            _request(export_id=EXPORT_ID),
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_folder_exports_module=_FakeExportsModule(),
            exports_nextcloud_runtime_module=runtime,
        )

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_client_export_id_forbidden")
        self.assertEqual(payload["export_nextcloud"]["store_state"], "blocked")
        self.assertEqual(runtime.calls, [])

    def test_service_refuses_unprepared_public_payload_message_sources_before_runtime(self) -> None:
        for source_kind, extra in (
            (
                "message_selection",
                {"selected_message_ids": ["a1"]},
            ),
            (
                "frida_response",
                {"response_message_id": "a1"},
            ),
        ):
            with self.subTest(source_kind=source_kind):
                runtime = _FakeRuntime({"ok": True})

                payload, status = workspace_folder_exports_service.create_workspace_folder_export_response(
                    FOLDER_ID,
                    _request(
                        source_kind=source_kind,
                        messages=[
                            {
                                "id": "a1",
                                "role": "assistant",
                                "content": "Message public injecte",
                            }
                        ],
                        **extra,
                    ),
                    workspace_folders_module=_FakeFolders(linked=True),
                    workspace_folder_exports_module=_FakeExportsModule(),
                    exports_nextcloud_runtime_module=runtime,
                )

                self.assertEqual(status, 400)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["reason_code"], "folder_export_source_not_prepared")
                self.assertEqual(payload["export_v1_technical"]["source"]["source_kind"], source_kind)
                self.assertEqual(payload["export_nextcloud"]["store_state"], "blocked")
                self.assertNotIn("Message public injecte", str(payload))
                self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main()
