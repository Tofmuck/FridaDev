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
CONVERSATION_ID = "22222222-3333-4444-8555-666666666666"
EXPORT_ID = "11111111-2222-4333-8444-555555555555"


class _FakeWorkspaceFolders:
    def __init__(self, *, linked=True, deleted=False):
        self.linked = linked
        self.deleted = deleted

    def normalize_workspace_folder_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        normalized = self.normalize_workspace_folder_id(folder_id)
        if normalized != FOLDER_ID:
            return None
        return {
            "id": FOLDER_ID,
            "display_name": "Projet serveur",
            "nextcloud_target_name": "Projet-serveur",
            "nextcloud_sync_state": "linked" if self.linked else "local_only",
            "deleted_at": "2026-06-19T11:00:00Z" if self.deleted else None,
        }


class _FakeExportsModule:
    def __init__(self, exports=None, *, fail_list=False, fail_get=False):
        self.exports = list(exports or [])
        self.fail_list = fail_list
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
        if self.fail_list:
            raise RuntimeError("raw list failure with Export serveur and raw-etag-secret")
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
            raise RuntimeError("raw get failure with Export serveur and raw-etag-secret")
        normalized = workspace_folder_exports.normalize_export_id(export_id)
        for item in self.exports:
            if workspace_folder_exports.normalize_export_id(item.get("id")) == normalized:
                return item
        return None

    def upsert_export(self, **fields):
        self.stored.append(dict(fields))
        target_name = fields["target_name"]
        return {
            "id": fields["export_id"],
            "workspace_folder_id": fields["workspace_folder_id"],
            "title": fields["title"],
            "title_hash": workspace_folder_exports.title_hash_for_target(target_name),
            "target_name": target_name,
            "export_format": fields["export_format"],
            "source_kind": fields["source_kind"],
            "source_ref": fields["source_ref"],
            "source_hash": fields["source_hash"],
            "content_hash": fields["content_hash"],
            "local_state": fields["local_state"],
            "nextcloud_sync_state": fields["nextcloud_sync_state"],
            "remote_export_ref": fields["remote_export_ref"],
            "etag_value": fields["etag_value"],
            "etag_hash": fields["etag_hash"],
            "byte_size": fields["byte_size"],
            "char_count": fields["char_count"],
            "reason_code": fields["reason_code"],
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
            "deleted_at": None,
        }

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeNextcloudExports:
    def __init__(self):
        self.status_calls = []
        self.put_calls = []

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
            etag_value='"server-etag-hidden"',
        )

    def delete_export(self, folder_name, export_name, *, missing_ok=True):
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _FakeConversationStore:
    def __init__(self):
        self.calls = []

    def normalize_conversation_id(self, value):
        self.calls.append(("normalize", value))
        return CONVERSATION_ID if str(value or "") == CONVERSATION_ID else None

    def get_conversation_summary(self, conversation_id, *, include_deleted=False):
        self.calls.append(("summary", conversation_id, include_deleted))
        return {
            "id": CONVERSATION_ID,
            "title": "Conversation serveur",
            "message_count": 2,
            "deleted_at": None,
        }

    def read_conversation(self, conversation_id, system_prompt):
        self.calls.append(("read", conversation_id, system_prompt))
        return {
            "id": CONVERSATION_ID,
            "messages": [
                {"id": "u-store", "role": "user", "content": "Contenu public relu store"},
                {"id": "a-store", "role": "assistant", "content": "Reponse publique relue store"},
            ],
        }


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


class _RuntimeFailure:
    def __init__(self, reason_code):
        self.reason_code = reason_code
        self.calls = []

    def store_workspace_folder_export_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ok": False,
            "reason_code": self.reason_code,
            "status": 503,
            "export_v1_technical": {"reason_code": self.reason_code},
            "export_nextcloud": {
                "store_state": "blocked",
                "reason_code": self.reason_code,
                "export_name_hash": "",
                "http_status_class": "none",
                "rollback": {},
            },
        }


def _request(**overrides):
    payload = {
        "export_format": "txt",
        "title": "Export serveur",
        "source_kind": "conversation",
        "explicit_source": True,
        "conversation_id": CONVERSATION_ID,
        "messages": [
            {"id": "u-injected", "role": "user", "content": "Message client injecte"},
        ],
    }
    payload.update(overrides)
    return payload


def _export(**overrides):
    payload = {
        "id": EXPORT_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Export serveur",
        "title_hash": "abc123def456",
        "target_name": "Export-serveur.txt",
        "export_format": "txt",
        "source_kind": "conversation",
        "source_ref": "conversation:22222222:abc123def456",
        "source_hash": "456defabc123",
        "content_hash": "789abc123def",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "remote_export_ref": "export:789abc123def",
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


class ServerWorkspaceFolderExportsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_exports = self.server.workspace_folder_exports
        self.original_workspace_folder_export_nextcloud_runtime = (
            self.server.workspace_folder_export_nextcloud_runtime
        )
        self.original_conv_store = self.server.conv_store
        self.fake_exports = _FakeExportsModule()
        self.fake_nextcloud = _FakeNextcloudExports()
        self.fake_runtime = _RuntimeWithFakeNextcloud(self.fake_nextcloud)
        self.server.workspace_folders = _FakeWorkspaceFolders()
        self.server.workspace_folder_exports = self.fake_exports
        self.server.workspace_folder_export_nextcloud_runtime = self.fake_runtime
        self.server.conv_store = _FakeConversationStore()

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_exports = self.original_workspace_folder_exports
        self.server.workspace_folder_export_nextcloud_runtime = (
            self.original_workspace_folder_export_nextcloud_runtime
        )
        self.server.conv_store = self.original_conv_store

    def test_workspace_folder_export_route_is_namespaced_without_global_exports_route(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(),
        )
        global_response = self.client.post("/api/exports", json=_request())
        global_nested_response = self.client.post("/api/exports/anything", json=_request())
        global_list_response = self.client.get("/api/exports")
        global_lookup_response = self.client.get(f"/api/exports/{EXPORT_ID}")

        self.assertEqual(response.status_code, 201)
        self.assertIn(global_response.status_code, {404, 405})
        self.assertIn(global_nested_response.status_code, {404, 405})
        self.assertIn(global_list_response.status_code, {404, 405})
        self.assertIn(global_lookup_response.status_code, {404, 405})
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn("/api/workspace-folders/<folder_id>/exports", routes)
        self.assertIn("/api/workspace-folders/<folder_id>/exports/<export_id>", routes)
        self.assertFalse(any(rule == "/api/exports" or rule.startswith("/api/exports/") for rule in routes))

    def test_workspace_folder_export_list_empty_from_local_read_model_only(self) -> None:
        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["exports"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["reason_code"], "folder_export_list_ok")
        self.assertEqual(len(self.fake_exports.list_calls), 1)
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_list_projects_actions_and_excludes_deleted(self) -> None:
        deleted_id = "22222222-3333-4444-8555-666666666666"
        self.fake_exports.exports = [
            _export(export_format="txt", target_name="Export-serveur.txt", title="Export serveur"),
            _export(
                id="33333333-4444-4555-8666-777777777777",
                export_format="pdf",
                target_name="Rapport-serveur.pdf",
                title="Rapport serveur",
            ),
            _export(
                id=deleted_id,
                export_format="md",
                target_name="Supprime.md",
                title="Supprime",
                local_state="deleted",
                deleted_at="2026-06-19T11:00:00Z",
            ),
        ]

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["count"], 2)
        formats = {item["export_v1_user"]["format"] for item in payload["exports"]}
        self.assertEqual(formats, {"txt", "pdf"})
        for item in payload["exports"]:
            user = item["export_v1_user"]
            technical = item["export_v1_technical"]
            self.assertTrue(user["can_download"])
            self.assertTrue(user["can_open"])
            self.assertEqual(user["actions"]["download_reason_code"], "folder_export_download_ok")
            self.assertEqual(user["actions"]["open_reason_code"], "folder_export_download_ok")
            if user["format"] == "txt":
                self.assertTrue(user["can_reuse_as_source"])
                self.assertEqual(
                    user["actions"]["reuse_as_source_reason_code"],
                    "folder_export_reuse_ok",
                )
            else:
                self.assertFalse(user["can_reuse_as_source"])
                self.assertEqual(
                    user["actions"]["reuse_as_source_reason_code"],
                    "folder_export_source_format_unsupported",
                )
            technical_text = str(technical)
            self.assertNotIn("Export serveur", technical_text)
            self.assertNotIn("Rapport serveur", technical_text)
            self.assertNotIn("raw-etag-secret", technical_text)
            self.assertNotIn("target_name", technical_text)
            self.assertNotIn("Export-serveur.txt", technical_text)
        self.assertNotIn(deleted_id, str(payload))
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_lookup_by_uuid_ok_from_local_read_model_only(self) -> None:
        self.fake_exports.exports = [_export()]

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_lookup_ok")
        user = payload["export"]["export_v1_user"]
        self.assertEqual(user["title"], "Export serveur")
        self.assertTrue(user["can_download"])
        self.assertTrue(user["can_open"])
        self.assertTrue(user["can_reuse_as_source"])
        self.assertEqual(user["actions"]["reuse_as_source_reason_code"], "folder_export_reuse_ok")
        self.assertEqual(len(self.fake_exports.get_calls), 1)
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_lookup_absent_or_cross_folder_is_not_exposed(self) -> None:
        absent = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}")
        self.fake_exports.exports = [_export(workspace_folder_id=OTHER_FOLDER_ID)]
        other_folder = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}"
        )

        self.assertEqual(absent.status_code, 404)
        self.assertEqual(absent.get_json()["reason_code"], "folder_export_not_found")
        self.assertEqual(other_folder.status_code, 404)
        self.assertEqual(other_folder.get_json()["reason_code"], "folder_export_not_found")
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_lookup_deleted_is_refused(self) -> None:
        self.fake_exports.exports = [
            _export(local_state="deleted", deleted_at="2026-06-19T11:00:00Z")
        ]

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}")

        self.assertEqual(response.status_code, 410)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_deleted")
        self.assertNotIn("raw-etag-secret", str(payload))
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_list_store_failure_is_fail_closed(self) -> None:
        self.server.workspace_folder_exports = _FakeExportsModule(fail_list=True)

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports")

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_lookup_failed")
        self.assertEqual(payload["exports"], [])
        self.assertEqual(payload["count"], 0)
        self.assertNotIn("Export serveur", str(payload))
        self.assertNotIn("raw-etag-secret", str(payload))
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_list_refuses_non_linked_folder_before_store(self) -> None:
        self.server.workspace_folders = _FakeWorkspaceFolders(linked=False)

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports")

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_folder_not_linked")
        self.assertEqual(payload["exports"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(self.fake_exports.list_calls, [])
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_list_refuses_deleted_folder_before_store(self) -> None:
        self.server.workspace_folders = _FakeWorkspaceFolders(deleted=True)

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports")

        self.assertEqual(response.status_code, 410)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "workspace_folder_deleted")
        self.assertEqual(self.fake_exports.list_calls, [])
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_reuse_route_is_not_delivered(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/reuse",
            json={"mode": "as_source"},
        )

        self.assertIn(response.status_code, {404, 405})
        self.assertEqual(self.fake_exports.get_calls, [])
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])

    def test_workspace_folder_export_route_uses_path_folder_id_over_payload(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(workspace_folder_id=OTHER_FOLDER_ID),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.fake_runtime.calls[0]["request"]["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(self.fake_exports.stored[0]["workspace_folder_id"], FOLDER_ID)

    def test_workspace_folder_export_route_refuses_client_export_id_before_runtime(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(export_id=EXPORT_ID),
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_client_export_id_forbidden")
        self.assertEqual(self.fake_runtime.calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])
        self.assertEqual(self.fake_exports.stored, [])

    def test_workspace_folder_export_route_refuses_payload_only_selection_and_response_sources(self) -> None:
        cases = (
            (
                "message_selection",
                {
                    "selected_message_ids": ["a1"],
                    "messages": [
                        {"id": "a1", "role": "assistant", "content": "Selection publique injectee"},
                    ],
                },
            ),
            (
                "frida-response",
                {
                    "response_message_id": "a1",
                    "messages": [
                        {"id": "a1", "role": "assistant", "content": "Reponse publique injectee"},
                    ],
                },
            ),
        )
        for source_kind, extra in cases:
            with self.subTest(source_kind=source_kind):
                response = self.client.post(
                    f"/api/workspace-folders/{FOLDER_ID}/exports",
                    json=_request(source_kind=source_kind, **extra),
                )

                self.assertEqual(response.status_code, 400)
                payload = response.get_json()
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["reason_code"], "folder_export_source_not_prepared")
                self.assertNotIn("Selection publique injectee", str(payload))
                self.assertNotIn("Reponse publique injectee", str(payload))

        self.assertEqual(self.fake_runtime.calls, [])
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])
        self.assertEqual(self.fake_exports.stored, [])

    def test_workspace_folder_export_route_conversation_uses_store_not_payload_messages(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(),
        )

        self.assertEqual(response.status_code, 201)
        stored_content = self.fake_nextcloud.put_calls[0]["content"]
        self.assertIn(b"Contenu public relu store", stored_content)
        self.assertIn(b"Reponse publique relue store", stored_content)
        self.assertNotIn(b"Message client injecte", stored_content)
        self.assertIn(("read", CONVERSATION_ID, ""), self.server.conv_store.calls)

    def test_workspace_folder_export_route_returns_content_free_runtime_error(self) -> None:
        self.server.workspace_folder_export_nextcloud_runtime = _RuntimeFailure(
            workspace_folder_exports.REASON_LOOKUP_FAILED
        )

        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(messages=[{"id": "u1", "role": "user", "content": "Payload prive"}]),
        )

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_lookup_failed")
        self.assertNotIn("Payload prive", str(payload))
        self.assertNotIn("Message client injecte", str(payload))


if __name__ == "__main__":
    unittest.main()
