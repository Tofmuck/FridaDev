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
OTHER_FOLDER_ID = "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"


def _image(**overrides):
    payload = {
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
    }
    payload.update(overrides)
    return payload


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


class _FakeGeneratedImages:
    def __init__(
        self,
        images: list[dict[str, Any]] | None = None,
        *,
        fail_list: bool = False,
        fail_get: bool = False,
    ) -> None:
        self.images = list(images or [])
        self.fail_list = fail_list
        self.fail_get = fail_get
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []

    def list_generated_images(self, folder_id, *, include_deleted=False, fail_closed=True):
        self.list_calls.append(
            {
                "folder_id": folder_id,
                "include_deleted": include_deleted,
                "fail_closed": fail_closed,
            }
        )
        if self.fail_list:
            raise RuntimeError("raw image list failure prompt secret remote.php")
        return [
            image
            for image in self.images
            if workspace_folder_generated_images.normalize_workspace_folder_id(
                image.get("workspace_folder_id")
            ) == folder_id
        ]

    def get_generated_image(self, image_id, *, fail_closed=True):
        self.get_calls.append({"image_id": image_id, "fail_closed": fail_closed})
        if self.fail_get:
            raise RuntimeError("raw image get failure prompt secret remote.php")
        for image in self.images:
            if workspace_folder_generated_images.normalize_generated_image_id(
                image.get("id")
            ) == image_id:
                return dict(image)
        return None

    def apply_generated_image_list(self, images, *, folder=None, include_deleted=False):
        return workspace_folder_generated_images.apply_generated_image_list(
            images,
            folder=folder,
            include_deleted=include_deleted,
        )

    def apply_generated_image_projection(self, image, *, folder=None):
        return workspace_folder_generated_images.apply_generated_image_projection(
            image,
            folder=folder,
        )


class ServerWorkspaceFolderGeneratedImagesContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = load_server_module_for_tests()
        self.client = self.server.app.test_client()

    def _patch(self, *, folders=None, runtime=None, images=None):
        original_folders = self.server.workspace_folders
        original_runtime = self.server.workspace_folder_generated_image_nextcloud_runtime
        original_images = self.server.workspace_folder_generated_images
        self.server.workspace_folders = folders or _FakeWorkspaceFolders()
        self.server.workspace_folder_generated_image_nextcloud_runtime = runtime or _RuntimeSuccess()
        self.server.workspace_folder_generated_images = images or workspace_folder_generated_images
        return original_folders, original_runtime, original_images

    def _restore(self, originals):
        (
            self.server.workspace_folders,
            self.server.workspace_folder_generated_image_nextcloud_runtime,
            self.server.workspace_folder_generated_images,
        ) = originals

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
        self.assertNotIn("content_hash", projected)
        self.assertEqual(
            projected["generated_image_v1_technical"]["content_hash_short"],
            "a" * 12,
        )
        body_text = str(body)
        self.assertNotIn("a" * 64, body_text)
        self.assertNotIn(TARGET_NAME, body_text)
        self.assertNotIn("raw-etag-secret", body_text)
        self.assertNotIn("data:image", body_text)
        self.assertNotIn("base64", body_text)
        self.assertNotIn("remote.php", body_text)

    def test_global_generated_images_routes_are_absent(self) -> None:
        self.assertIn(self.client.post("/api/generated-images", json={}).status_code, {404, 405})
        self.assertIn(self.client.post("/api/images", json={}).status_code, {404, 405})
        self.assertIn(self.client.get("/api/generated-images").status_code, {404, 405})
        self.assertIn(self.client.get("/api/images").status_code, {404, 405})
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn("/api/workspace-folders/<folder_id>/generated-images", routes)
        self.assertIn("/api/workspace-folders/<folder_id>/generated-images/<image_id>", routes)
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

    def test_list_generated_images_empty_is_read_model_only(self) -> None:
        runtime = _RuntimeSuccess()
        images = _FakeGeneratedImages([])
        originals = self._patch(runtime=runtime, images=images)
        try:
            response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/generated-images")
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(body["generated_images"], [])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["reason_code"], "folder_generated_image_list_ok")
        self.assertEqual(
            images.list_calls,
            [{"folder_id": FOLDER_ID, "include_deleted": False, "fail_closed": True}],
        )
        self.assertFalse(runtime.calls)

    def test_list_generated_images_projects_multiformat_and_excludes_deleted(self) -> None:
        runtime = _RuntimeSuccess()
        deleted = _image(
            id="44444444-2222-4333-8444-555555555555",
            display_name="Supprimee",
            local_state="deleted",
            deleted_at="2026-06-19T11:00:00Z",
        )
        images = _FakeGeneratedImages(
            [
                _image(display_name="Image PNG", image_format="png", mime_type="image/png"),
                _image(
                    id="22222222-2222-4333-8444-555555555555",
                    display_name="Image JPEG",
                    target_name_internal="generated-image-22222222-2222-4333-8444-555555555555.jpg",
                    target_ref=workspace_folder_generated_images.target_ref_for_target(
                        "generated-image-22222222-2222-4333-8444-555555555555.jpg"
                    ),
                    image_format="jpeg",
                    mime_type="image/jpeg",
                    width=80,
                    height=60,
                ),
                _image(
                    id="33333333-2222-4333-8444-555555555555",
                    display_name="Image WebP",
                    target_name_internal="generated-image-33333333-2222-4333-8444-555555555555.webp",
                    target_ref=workspace_folder_generated_images.target_ref_for_target(
                        "generated-image-33333333-2222-4333-8444-555555555555.webp"
                    ),
                    image_format="webp",
                    mime_type="image/webp",
                    byte_size=1024,
                ),
                deleted,
            ]
        )
        originals = self._patch(runtime=runtime, images=images)
        try:
            response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/generated-images")
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["count"], 3)
        items = body["generated_images"]
        self.assertEqual(
            [item["generated_image_v1_user"]["format"] for item in items],
            ["png", "jpeg", "webp"],
        )
        first_user = items[0]["generated_image_v1_user"]
        self.assertEqual(first_user["display_name"], "Image PNG")
        self.assertEqual(first_user["byte_size"], 512)
        self.assertEqual(first_user["width"], 64)
        self.assertEqual(first_user["height"], 64)
        self.assertEqual(first_user["status"], "available")
        self.assertTrue(first_user["can_download"])
        self.assertTrue(first_user["can_open"])
        self.assertTrue(first_user["can_delete"])
        self.assertEqual(
            first_user["actions"]["download_reason_code"],
            "folder_generated_image_download_ok",
        )
        body_text = str(body)
        self.assertNotIn("Supprimee", body_text)
        self.assertNotIn(TARGET_NAME, body_text)
        self.assertNotIn("raw-etag-secret", body_text)
        self.assertNotIn("data:image", body_text)
        self.assertNotIn("base64", body_text)
        self.assertNotIn("remote.php", body_text)
        self.assertNotIn("a" * 64, body_text)
        self.assertFalse(runtime.calls)

    def test_lookup_generated_image_by_uuid_exact_is_metadata_only(self) -> None:
        runtime = _RuntimeSuccess()
        images = _FakeGeneratedImages([_image()])
        originals = self._patch(runtime=runtime, images=images)
        try:
            response = self.client.get(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}"
            )
        finally:
            self._restore(originals)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["reason_code"], "folder_generated_image_lookup_ok")
        self.assertEqual(
            body["generated_image"]["generated_image_v1_user"]["image_id"],
            IMAGE_ID,
        )
        self.assertEqual(images.get_calls, [{"image_id": IMAGE_ID, "fail_closed": True}])
        self.assertTrue(body["generated_image"]["generated_image_v1_user"]["can_open"])
        self.assertFalse(runtime.calls)
        self.assertNotIn(TARGET_NAME, str(body))
        self.assertNotIn("a" * 64, str(body))

    def test_lookup_invalid_absent_cross_folder_and_deleted_are_refused(self) -> None:
        cases = (
            (
                "not-a-uuid",
                _FakeGeneratedImages([_image()]),
                400,
                "folder_generated_image_id_invalid",
            ),
            (
                "55555555-2222-4333-8444-555555555555",
                _FakeGeneratedImages([_image()]),
                404,
                "folder_generated_image_not_found",
            ),
            (
                IMAGE_ID,
                _FakeGeneratedImages([_image(workspace_folder_id=OTHER_FOLDER_ID)]),
                404,
                "folder_generated_image_not_found",
            ),
            (
                IMAGE_ID,
                _FakeGeneratedImages([
                    _image(local_state="deleted", deleted_at="2026-06-19T11:00:00Z")
                ]),
                410,
                "folder_generated_image_deleted",
            ),
        )
        for image_id, images, status, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                originals = self._patch(runtime=_RuntimeSuccess(), images=images)
                try:
                    response = self.client.get(
                        f"/api/workspace-folders/{FOLDER_ID}/generated-images/{image_id}"
                    )
                finally:
                    self._restore(originals)

                self.assertEqual(response.status_code, status)
                body = response.get_json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["reason_code"], reason_code)
                self.assertNotIn(TARGET_NAME, str(body))

    def test_list_and_lookup_reject_folder_states_before_image_store(self) -> None:
        cases = (
            (_FakeWorkspaceFolders(linked=False), 409, "folder_generated_image_folder_not_linked"),
            (_FakeWorkspaceFolders(deleted=True), 410, "folder_generated_image_folder_deleted"),
            (_FakeWorkspaceFolders(fail_get=True), 503, "folder_generated_image_lookup_failed"),
        )
        for folders, status, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                images = _FakeGeneratedImages([_image()])
                originals = self._patch(folders=folders, runtime=_RuntimeSuccess(), images=images)
                try:
                    list_response = self.client.get(
                        f"/api/workspace-folders/{FOLDER_ID}/generated-images"
                    )
                    lookup_response = self.client.get(
                        f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}"
                    )
                finally:
                    self._restore(originals)

                self.assertEqual(list_response.status_code, status)
                self.assertEqual(lookup_response.status_code, status)
                self.assertEqual(list_response.get_json()["reason_code"], reason_code)
                self.assertEqual(lookup_response.get_json()["reason_code"], reason_code)
                self.assertFalse(images.list_calls)
                self.assertFalse(images.get_calls)
                self.assertNotIn("raw folder failure", str(list_response.get_json()))

    def test_image_store_failures_fail_closed_without_empty_list_or_raw_cause(self) -> None:
        images = _FakeGeneratedImages([_image()], fail_list=True, fail_get=True)
        originals = self._patch(runtime=_RuntimeSuccess(), images=images)
        try:
            list_response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/generated-images")
            lookup_response = self.client.get(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}"
            )
        finally:
            self._restore(originals)

        self.assertEqual(list_response.status_code, 503)
        self.assertEqual(lookup_response.status_code, 503)
        list_body = list_response.get_json()
        lookup_body = lookup_response.get_json()
        self.assertEqual(list_body["reason_code"], "folder_generated_image_lookup_failed")
        self.assertEqual(lookup_body["reason_code"], "folder_generated_image_lookup_failed")
        self.assertFalse(list_body["ok"])
        self.assertFalse(lookup_body["ok"])
        self.assertIn("generated_images", list_body)
        self.assertNotEqual(list_body["reason_code"], "folder_generated_image_list_ok")
        self.assertNotIn("raw image", str(list_body))
        self.assertNotIn("raw image", str(lookup_body))
        self.assertNotIn("remote.php", str(list_body))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
