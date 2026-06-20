from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_images
from tests.support.server_test_bootstrap import load_server_module_for_tests


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
IMAGE_ID = "11111111-2222-4333-8444-555555555555"
TARGET_NAME = "generated-image-11111111-2222-4333-8444-555555555555.png"


class _FakeWorkspaceFolders:
    def __init__(self, *, linked: bool = True, deleted: bool = False, fail_get: bool = False) -> None:
        self.linked = linked
        self.deleted = deleted
        self.fail_get = fail_get

    def normalize_workspace_folder_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        if self.fail_get:
            raise RuntimeError("raw folder failure prompt secret remote.php")
        if self.normalize_workspace_folder_id(folder_id) != FOLDER_ID:
            return None
        return {
            "id": FOLDER_ID,
            "display_name": "Dossier serveur",
            "nextcloud_target_name": "Dossier-serveur",
            "nextcloud_sync_state": "linked" if self.linked else "local_only",
            "deleted_at": "2026-06-19T10:00:00Z" if self.deleted else None,
        }


class _RuntimeSuccess:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def store_workspace_folder_generated_image_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ok": True,
            "reason_code": workspace_folder_generated_images.REASON_STORE_OK,
            "status": 201,
            "generated_image": {
                "id": IMAGE_ID,
                "workspace_folder_id": FOLDER_ID,
                "display_name": "Image serveur",
                "display_name_hash": "abc123def456",
                "target_name_internal": TARGET_NAME,
                "target_ref": workspace_folder_generated_images.target_ref_for_target(TARGET_NAME),
                "mime_type": "image/png",
                "image_format": "png",
                "byte_size": 512,
                "width": 64,
                "height": 64,
                "content_hash": "a" * 64,
                "content_hash_short": "a" * 12,
                "generator_key": "image_generator_nano_banana",
                "provider_model": "google/gemini-2.5-flash-image",
                "aspect_ratio": "1:1",
                "image_size": "1K",
                "prompt_present": True,
                "prompt_length_bucket": "chars_001_to_250",
                "local_state": "available",
                "nextcloud_sync_state": "linked",
                "etag_value": '"raw-etag-secret"',
                "etag_hash": "123456abcdef",
                "last_reason_code": workspace_folder_generated_images.REASON_STORE_OK,
                "created_at": "2026-06-19T10:00:00Z",
                "updated_at": "2026-06-19T10:00:00Z",
                "deleted_at": None,
            },
            "generated_image_nextcloud": {
                "store_state": "stored",
                "reason_code": workspace_folder_generated_images.REASON_STORE_OK,
                "target_ref": workspace_folder_generated_images.target_ref_for_target(TARGET_NAME),
                "http_status_class": "2xx",
                "etag_hash": "123456abcdef",
                "etag_present": True,
            },
        }


class _RuntimeFailure:
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        self.calls: list[dict[str, Any]] = []

    def store_workspace_folder_generated_image_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ok": False,
            "reason_code": self.reason_code,
            "status": 503,
            "generated_image": {"status": "unavailable", "reason_code": self.reason_code},
            "generated_image_v1_technical": {"reason_code": self.reason_code},
            "generated_image_nextcloud": {
                "store_state": "blocked",
                "reason_code": self.reason_code,
                "target_ref": "",
                "http_status_class": "none",
                "rollback": {},
            },
        }


class ServerWorkspaceFolderGeneratedImagesContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = load_server_module_for_tests()
        self.client = self.server.app.test_client()

    def _patch(self, *, folders=None, runtime=None):
        original_folders = self.server.workspace_folders
        original_runtime = self.server.workspace_folder_generated_image_nextcloud_runtime
        self.server.workspace_folders = folders or _FakeWorkspaceFolders()
        self.server.workspace_folder_generated_image_nextcloud_runtime = runtime or _RuntimeSuccess()
        return original_folders, original_runtime

    def _restore(self, originals):
        self.server.workspace_folders, self.server.workspace_folder_generated_image_nextcloud_runtime = originals

    def test_create_route_is_namespaced_and_projects_content_free_response(self) -> None:
        runtime = _RuntimeSuccess()
        originals = self._patch(runtime=runtime)
        try:
            response = self.client.post(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images",
                json={
                    "generator_key": "image_generator_nano_banana",
                    "prompt": "synthetic prompt not returned",
                    "aspect_ratio": "1:1",
                    "image_size": "1K",
                    "display_name": "Image serveur",
                },
            )
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.calls[0]["request"]["prompt"], "synthetic prompt not returned")
        projected = body["generated_image"]
        self.assertEqual(projected["generated_image_v1_user"]["display_name"], "Image serveur")
        body_text = str(body)
        self.assertNotIn(TARGET_NAME, body_text)
        self.assertNotIn("raw-etag-secret", body_text)
        self.assertNotIn("data:image", body_text)
        self.assertNotIn("base64", body_text)
        self.assertNotIn("remote.php", body_text)

    def test_global_generated_images_routes_are_absent(self) -> None:
        self.assertIn(self.client.post("/api/generated-images", json={}).status_code, {404, 405})
        self.assertIn(self.client.post("/api/images", json={}).status_code, {404, 405})
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn("/api/workspace-folders/<folder_id>/generated-images", routes)
        self.assertFalse(
            any(
                rule == "/api/generated-images"
                or rule.startswith("/api/generated-images/")
                or rule == "/api/images"
                or rule.startswith("/api/images/")
                for rule in routes
            )
        )

    def test_payload_workspace_folder_id_and_image_id_are_rejected_before_runtime(self) -> None:
        for extra, reason_code in (
            (
                {"workspace_folder_id": "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"},
                "folder_generated_image_client_workspace_folder_id_forbidden",
            ),
            ({"image_id": IMAGE_ID}, "folder_generated_image_client_image_id_forbidden"),
        ):
            with self.subTest(reason_code=reason_code):
                runtime = _RuntimeSuccess()
                originals = self._patch(runtime=runtime)
                try:
                    response = self.client.post(
                        f"/api/workspace-folders/{FOLDER_ID}/generated-images",
                        json={"prompt": "x", **extra},
                    )
                finally:
                    self._restore(originals)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["reason_code"], reason_code)
                self.assertFalse(runtime.calls)

    def test_non_linked_folder_is_rejected_before_runtime(self) -> None:
        runtime = _RuntimeSuccess()
        originals = self._patch(folders=_FakeWorkspaceFolders(linked=False), runtime=runtime)
        try:
            response = self.client.post(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images",
                json={"prompt": "x"},
            )
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["reason_code"],
            "folder_generated_image_folder_not_linked",
        )
        self.assertFalse(runtime.calls)

    def test_folder_lookup_failure_is_content_free(self) -> None:
        originals = self._patch(folders=_FakeWorkspaceFolders(fail_get=True), runtime=_RuntimeSuccess())
        try:
            response = self.client.post(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images",
                json={"prompt": "x"},
            )
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["reason_code"], "folder_generated_image_lookup_failed")
        self.assertNotIn("raw folder failure", str(body))
        self.assertNotIn("remote.php", str(body))

    def test_runtime_failure_is_returned_content_free(self) -> None:
        runtime = _RuntimeFailure("folder_generated_image_store_failed_redacted")
        originals = self._patch(runtime=runtime)
        try:
            response = self.client.post(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images",
                json={"prompt": "SERVER_PROMPT_SENTINEL"},
            )
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["reason_code"], "folder_generated_image_store_failed_redacted")
        self.assertNotIn("SERVER_PROMPT_SENTINEL", str(body))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
