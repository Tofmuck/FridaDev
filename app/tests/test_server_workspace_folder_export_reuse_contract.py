from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_export_nextcloud_client  # noqa: E402
from core import workspace_folder_export_nextcloud_runtime  # noqa: E402
from core import workspace_folder_exports  # noqa: E402
from tests.support.server_test_bootstrap import load_server_module_for_tests  # noqa: E402


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_FOLDER_ID = "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"
SOURCE_MD_ID = "11111111-2222-4333-8444-555555555555"
SOURCE_TXT_ID = "22222222-3333-4444-8555-666666666666"
SOURCE_DOCX_ID = "33333333-4444-4555-8666-777777777777"
SOURCE_PDF_ID = "44444444-5555-4666-8777-888888888888"


class _FakeWorkspaceFolders:
    def normalize_workspace_folder_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        if self.normalize_workspace_folder_id(folder_id) != FOLDER_ID:
            return None
        return {
            "id": FOLDER_ID,
            "display_name": "Projet reuse",
            "nextcloud_target_name": "Projet-reuse",
            "nextcloud_sync_state": "linked",
            "deleted_at": None,
        }


class _FakeExportsModule:
    def __init__(self, exports=None, *, fail_get=False):
        self.exports = list(exports or [])
        self.fail_get = fail_get
        self.list_calls = []
        self.get_calls = []
        self.stored = []
        self.events = []

    def list_exports(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        self.list_calls.append(
            {
                "workspace_folder_id": workspace_folder_id,
                "include_deleted": include_deleted,
                "fail_closed": fail_closed,
            }
        )
        rows = [
            item
            for item in self.exports
            if (
                workspace_folder_exports.normalize_workspace_folder_id(
                    item.get("workspace_folder_id")
                )
                == workspace_folder_id
            )
        ]
        if not include_deleted:
            rows = [item for item in rows if not workspace_folder_exports.is_deleted(item)]
        return list(rows)

    def get_export(self, export_id, *, fail_closed=True):
        self.get_calls.append({"export_id": export_id, "fail_closed": fail_closed})
        if self.fail_get:
            raise RuntimeError("raw source store failure raw-etag-secret")
        normalized = workspace_folder_exports.normalize_export_id(export_id)
        for item in self.exports:
            if workspace_folder_exports.normalize_export_id(item.get("id")) == normalized:
                return item
        return None

    def upsert_export(self, **fields):
        self.stored.append(dict(fields))
        target_name = fields["target_name"]
        row = _export(
            id=fields["export_id"],
            workspace_folder_id=fields["workspace_folder_id"],
            title=fields["title"],
            title_hash=workspace_folder_exports.title_hash_for_target(target_name),
            target_name=target_name,
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
        self.exports.append(row)
        return row

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeSourceNextcloud:
    def __init__(self, *, content=b"source relue", fail_reason=""):
        self.content = bytes(content)
        self.fail_reason = fail_reason
        self.read_calls = []

    def read_export(self, folder_name, export_name, *, max_bytes):
        self.read_calls.append(
            {
                "folder_name": folder_name,
                "export_name": export_name,
                "max_bytes": max_bytes,
            }
        )
        if self.fail_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.fail_reason,
                http_status=503,
            )
        return workspace_folder_export_nextcloud_client.NextcloudExportReadResponse(
            True,
            workspace_folder_exports.REASON_DOWNLOAD_OK,
            200,
            content=self.content,
        )


class _FakeDestinationNextcloud:
    def __init__(self):
        self.status_calls = []
        self.put_calls = []
        self.deleted = []

    def exports_status(self, folder_name):
        self.status_calls.append(folder_name)
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
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_STORE_OK,
            201,
            etag_value='"destination-etag-hidden"',
        )

    def delete_export(self, folder_name, export_name, *, missing_ok=True):
        self.deleted.append((folder_name, export_name, missing_ok))
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _RuntimeWithFakeNextcloud:
    def __init__(self, nextcloud):
        self.nextcloud = nextcloud
        self.calls = []

    def store_workspace_folder_export_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["nextcloud"] = self.nextcloud
        return workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            **kwargs
        )


def _export(**overrides):
    payload = {
        "id": SOURCE_MD_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Source reuse",
        "title_hash": workspace_folder_exports.title_hash_for_target("Source-reuse.md"),
        "target_name": "Source-reuse.md",
        "export_format": "md",
        "source_kind": "conversation",
        "source_ref": "conversation:22222222:abc123def456",
        "source_hash": "456defabc123",
        "content_hash": "789abc123def",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "remote_export_ref": "workspace-export:11111111:abc123def456",
        "etag_value": '"raw-etag-secret"',
        "etag_hash": "123456abcdef",
        "byte_size": 42,
        "char_count": 12,
        "reason_code": "folder_export_store_ok",
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


def _request(**overrides):
    payload = {
        "export_format": "txt",
        "title": "Nouvel export reuse",
        "source_kind": "export",
        "source_export_id": SOURCE_MD_ID,
        "explicit_source": True,
    }
    payload.update(overrides)
    return payload


class ServerWorkspaceFolderExportReuseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_exports = self.server.workspace_folder_exports
        self.original_runtime = self.server.workspace_folder_export_nextcloud_runtime
        self.original_from_env = (
            self.server.workspace_folder_exports_service
            .workspace_folder_export_reader
            .export_client.NextcloudExportClient.__dict__["from_env"]
        )
        self.fake_exports = _FakeExportsModule(exports=[_export()])
        self.source_nextcloud = _FakeSourceNextcloud(content=b"# Source\n\ncontenu source relu")
        self.destination_nextcloud = _FakeDestinationNextcloud()
        self.server.workspace_folders = _FakeWorkspaceFolders()
        self.server.workspace_folder_exports = self.fake_exports
        self.server.workspace_folder_export_nextcloud_runtime = _RuntimeWithFakeNextcloud(
            self.destination_nextcloud
        )
        (
            self.server.workspace_folder_exports_service
            .workspace_folder_export_reader
            .export_client.NextcloudExportClient.from_env
        ) = lambda environ=None: self.source_nextcloud

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_exports = self.original_workspace_folder_exports
        self.server.workspace_folder_export_nextcloud_runtime = self.original_runtime
        (
            self.server.workspace_folder_exports_service
            .workspace_folder_export_reader
            .export_client.NextcloudExportClient.from_env
        ) = self.original_from_env

    def test_export_source_md_creates_new_export_from_exact_nextcloud_read(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(),
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["export"]["export_v1_user"]["source_kind"], "export")
        self.assertEqual(self.source_nextcloud.read_calls[0]["folder_name"], "Projet-reuse")
        self.assertEqual(self.source_nextcloud.read_calls[0]["export_name"], "Source-reuse.md")
        self.assertEqual(self.destination_nextcloud.status_calls, ["Projet-reuse"])
        self.assertEqual(self.destination_nextcloud.put_calls[0]["export_name"], "Nouvel-export-reuse.txt")
        self.assertIn(b"contenu source relu", self.destination_nextcloud.put_calls[0]["content"])
        self.assertEqual(self.fake_exports.stored[0]["source_kind"], "export")
        self.assertTrue(self.fake_exports.stored[0]["source_ref"].startswith("workspace-export:"))
        response_text = str(payload)
        self.assertNotIn("contenu source relu", response_text)
        self.assertNotIn("Source-reuse.md", response_text)
        self.assertNotIn("raw-etag-secret", response_text)

    def test_export_source_txt_creates_new_export(self) -> None:
        self.fake_exports.exports = [
            _export(
                id=SOURCE_TXT_ID,
                target_name="Source-reuse.txt",
                export_format="txt",
            )
        ]

        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(source_export_id=SOURCE_TXT_ID, title="Reuse txt"),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.source_nextcloud.read_calls[0]["export_name"], "Source-reuse.txt")
        self.assertEqual(self.fake_exports.stored[0]["source_kind"], "export")

    def test_export_source_requires_explicit_source_and_source_export_id(self) -> None:
        cases = (
            (_request(explicit_source=False), "folder_export_source_ambiguous"),
            (_request(source_export_id=None), "folder_export_source_missing"),
            (_request(messages=[{"id": "m1", "role": "user", "content": "payload injecte"}]), "folder_export_source_ambiguous"),
        )
        for request_payload, reason in cases:
            with self.subTest(reason=reason):
                self.source_nextcloud.read_calls.clear()
                self.destination_nextcloud.status_calls.clear()
                self.destination_nextcloud.put_calls.clear()

                response = self.client.post(
                    f"/api/workspace-folders/{FOLDER_ID}/exports",
                    json=request_payload,
                )

                self.assertEqual(response.status_code, 400)
                payload = response.get_json()
                self.assertEqual(payload["reason_code"], reason)
                self.assertNotIn("payload injecte", str(payload))
                self.assertEqual(self.source_nextcloud.read_calls, [])
                self.assertEqual(self.destination_nextcloud.status_calls, [])
                self.assertEqual(self.destination_nextcloud.put_calls, [])

    def test_source_absent_deleted_cross_folder_or_non_linked_prevents_put_and_upsert(self) -> None:
        cases = (
            ([], SOURCE_MD_ID, 404, "folder_export_not_found"),
            ([_export(local_state="deleted", deleted_at="2026-06-19T12:00:00Z")], SOURCE_MD_ID, 410, "folder_export_deleted"),
            ([_export(workspace_folder_id=OTHER_FOLDER_ID)], SOURCE_MD_ID, 404, "folder_export_not_found"),
            ([_export(nextcloud_sync_state="sync_error")], SOURCE_MD_ID, 409, "folder_export_not_linked"),
        )
        for exports, source_id, status, reason in cases:
            with self.subTest(reason=reason):
                self.fake_exports = _FakeExportsModule(exports=exports)
                self.server.workspace_folder_exports = self.fake_exports
                self.source_nextcloud.read_calls.clear()
                self.destination_nextcloud.status_calls.clear()
                self.destination_nextcloud.put_calls.clear()

                response = self.client.post(
                    f"/api/workspace-folders/{FOLDER_ID}/exports",
                    json=_request(source_export_id=source_id),
                )

                self.assertEqual(response.status_code, status)
                self.assertEqual(response.get_json()["reason_code"], reason)
                self.assertEqual(self.source_nextcloud.read_calls, [])
                self.assertEqual(self.destination_nextcloud.status_calls, [])
                self.assertEqual(self.destination_nextcloud.put_calls, [])
                self.assertEqual(self.fake_exports.stored, [])

    def test_docx_pdf_store_and_nextcloud_failures_prevent_put_and_upsert(self) -> None:
        cases = (
            (
                _FakeExportsModule(exports=[
                    _export(
                        id=SOURCE_DOCX_ID,
                        target_name="Source-reuse.docx",
                        export_format="docx",
                    )
                ]),
                SOURCE_DOCX_ID,
                _FakeSourceNextcloud(),
                400,
                "folder_export_source_format_unsupported",
            ),
            (
                _FakeExportsModule(exports=[
                    _export(
                        id=SOURCE_PDF_ID,
                        target_name="Source-reuse.pdf",
                        export_format="pdf",
                    )
                ]),
                SOURCE_PDF_ID,
                _FakeSourceNextcloud(),
                400,
                "folder_export_source_format_unsupported",
            ),
            (
                _FakeExportsModule(exports=[_export()], fail_get=True),
                SOURCE_MD_ID,
                _FakeSourceNextcloud(),
                503,
                "folder_export_lookup_failed",
            ),
            (
                _FakeExportsModule(exports=[_export()]),
                SOURCE_MD_ID,
                _FakeSourceNextcloud(
                    fail_reason=workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
                ),
                502,
                "folder_export_source_read_unavailable",
            ),
        )
        for exports, source_id, source_nextcloud, status, reason in cases:
            with self.subTest(reason=reason):
                self.fake_exports = exports
                self.source_nextcloud = source_nextcloud
                self.server.workspace_folder_exports = self.fake_exports
                self.destination_nextcloud.status_calls.clear()
                self.destination_nextcloud.put_calls.clear()

                response = self.client.post(
                    f"/api/workspace-folders/{FOLDER_ID}/exports",
                    json=_request(source_export_id=source_id),
                )

                self.assertEqual(response.status_code, status)
                payload = response.get_json()
                self.assertEqual(payload["reason_code"], reason)
                self.assertNotIn("raw source store failure", str(payload))
                self.assertEqual(self.destination_nextcloud.status_calls, [])
                self.assertEqual(self.destination_nextcloud.put_calls, [])
                self.assertEqual(self.fake_exports.stored, [])

    def test_client_export_id_remains_forbidden_before_source_read(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(export_id=SOURCE_MD_ID),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["reason_code"], "folder_export_client_export_id_forbidden")
        self.assertEqual(self.source_nextcloud.read_calls, [])
        self.assertEqual(self.destination_nextcloud.put_calls, [])
        self.assertEqual(self.fake_exports.stored, [])

    def test_payload_only_selection_and_frida_response_remain_refused(self) -> None:
        cases = (
            _request(
                source_kind="message_selection",
                selected_message_ids=["a1"],
                messages=[{"id": "a1", "role": "assistant", "content": "selection injectee"}],
            ),
            _request(
                source_kind="frida_response",
                response_message_id="a1",
                messages=[{"id": "a1", "role": "assistant", "content": "reponse injectee"}],
            ),
        )
        for request_payload in cases:
            with self.subTest(source_kind=request_payload["source_kind"]):
                response = self.client.post(
                    f"/api/workspace-folders/{FOLDER_ID}/exports",
                    json=request_payload,
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["reason_code"], "folder_export_source_not_prepared")
                self.assertEqual(self.source_nextcloud.read_calls, [])
                self.assertEqual(self.destination_nextcloud.put_calls, [])
                self.assertEqual(self.fake_exports.stored, [])


if __name__ == "__main__":
    unittest.main()
