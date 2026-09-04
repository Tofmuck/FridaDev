from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_image_content_service
from core import workspace_folder_generated_image_nextcloud_client
from core import workspace_folder_generated_images


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
IMAGE_ID = "11111111-2222-4333-8444-555555555555"
TARGET_NAME = "generated-image-11111111-2222-4333-8444-555555555555.png"
_DEFAULT_IMAGE = object()


def _png_bytes(width: int = 32, height: int = 32) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\r"
        b"IHDR"
        + int(width).to_bytes(4, "big")
        + int(height).to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


def _jpeg_bytes(width: int = 48, height: int = 40) -> bytes:
    return (
        b"\xff\xd8\xff\xc0\x00\x11\x08"
        + int(height).to_bytes(2, "big")
        + int(width).to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )


def _folder(*, linked: bool = True, deleted: bool = False) -> dict[str, Any]:
    return {
        "id": FOLDER_ID,
        "display_name": "Dossier Images",
        "nextcloud_target_name": "Dossier-Images",
        "nextcloud_sync_state": "linked" if linked else "local_only",
        "deleted_at": "2026-06-20T10:00:00Z" if deleted else None,
    }


def _image(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": IMAGE_ID,
        "workspace_folder_id": FOLDER_ID,
        "display_name": "Image serveur",
        "target_name_internal": TARGET_NAME,
        "target_ref": workspace_folder_generated_images.target_ref_for_target(TARGET_NAME),
        "mime_type": "image/png",
        "image_format": "png",
        "byte_size": 64,
        "width": 32,
        "height": 32,
        "content_hash_short": "123456abcdef",
        "generator_key": "image_generator_nano_banana",
        "provider_model": "google/gemini-2.5-flash-image",
        "aspect_ratio": "1:1",
        "image_size": "1K",
        "prompt_present": True,
        "prompt_length_bucket": "chars_001_to_250",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "last_reason_code": "folder_generated_image_store_ok",
        "created_at": "2026-06-20T10:00:00Z",
        "updated_at": "2026-06-20T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


class _FakeFolders:
    def __init__(self, folder: dict[str, Any] | None = None, *, fail: bool = False) -> None:
        self.folder = folder if folder is not None else _folder()
        self.fail = fail

    def normalize_workspace_folder_id(self, value: Any) -> str:
        return workspace_folder_generated_images.normalize_workspace_folder_id(value)

    def get_workspace_folder(self, folder_id: str, include_deleted: bool = False):
        if self.fail:
            raise RuntimeError("raw folder db failure secret remote.php")
        return self.folder


class _FakeImages:
    def __init__(
        self,
        image: dict[str, Any] | None | object = _DEFAULT_IMAGE,
        *,
        fail_get: bool = False,
        fail_tombstone: bool = False,
    ) -> None:
        self.image = _image() if image is _DEFAULT_IMAGE else image
        self.fail_get = fail_get
        self.fail_tombstone = fail_tombstone
        self.tombstones: list[dict[str, Any]] = []
        self.events: list[tuple[str, dict[str, Any]]] = []

    def get_generated_image(self, image_id: str, fail_closed: bool = False):
        if self.fail_get:
            raise RuntimeError("raw image db failure prompt remote.php")
        return self.image

    def tombstone_generated_image(
        self,
        image_id: str,
        *,
        expected_workspace_folder_id: str,
        expected_target_name_internal: str,
        expected_target_ref: str,
        reason_code: str = "",
    ):
        self.tombstones.append(
            {
                "image_id": image_id,
                "workspace_folder_id": expected_workspace_folder_id,
                "target_name_internal": expected_target_name_internal,
                "target_ref": expected_target_ref,
                "reason_code": reason_code,
            }
        )
        if self.fail_tombstone:
            raise RuntimeError("raw tombstone db failure secret target")
        return _image(
            local_state="deleted",
            nextcloud_sync_state="deleted",
            deleted_at="2026-06-20T10:10:00Z",
            last_reason_code=reason_code,
        )

    def apply_generated_image_projection(self, image, *, folder=None):
        return workspace_folder_generated_images.apply_generated_image_projection(
            image,
            folder=folder,
        )

    def log_content_free_event(self, event: str, level: str = "info", **fields: Any) -> None:
        self.events.append((event, dict(fields)))


class _FakeNextcloud:
    def __init__(
        self,
        *,
        content: bytes = b"",
        media_type: str = "image/png",
        read_error: workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError | None = None,
        delete_error: workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError | None = None,
    ) -> None:
        self.content = content or _png_bytes()
        self.media_type = media_type
        self.read_error = read_error
        self.delete_error = delete_error
        self.read_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []

    def read_image(self, folder_name: str, image_name: str, *, max_bytes: int):
        self.read_calls.append(
            {"folder_name": folder_name, "image_name": image_name, "max_bytes": max_bytes}
        )
        if self.read_error:
            raise self.read_error
        return workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageReadResponse(
            True,
            workspace_folder_generated_images.REASON_DOWNLOAD_OK,
            200,
            content=self.content,
            media_type=self.media_type,
        )

    def delete_image(self, folder_name: str, image_name: str, *, missing_ok: bool = True):
        self.delete_calls.append(
            {"folder_name": folder_name, "image_name": image_name, "missing_ok": missing_ok}
        )
        if self.delete_error:
            raise self.delete_error
        return workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageResponse(
            True,
            workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class WorkspaceFolderGeneratedImageContentServiceTests(unittest.TestCase):
    def test_open_and_download_read_exact_target_and_set_safe_headers(self) -> None:
        nextcloud = _FakeNextcloud(content=_png_bytes())

        opened = workspace_folder_generated_image_content_service.download_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=_FakeImages(),
            nextcloud=nextcloud,
            disposition="inline",
        )

        self.assertTrue(opened.ok)
        self.assertEqual(opened.headers["Content-Type"], "image/png")
        self.assertEqual(opened.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(opened.headers["Cache-Control"], "private, no-store")
        self.assertIn("inline", opened.headers["Content-Disposition"])
        self.assertIn("Image-serveur.png", opened.headers["Content-Disposition"])
        self.assertNotIn(TARGET_NAME, opened.headers["Content-Disposition"])
        self.assertEqual(nextcloud.read_calls[0]["image_name"], TARGET_NAME)
        self.assertEqual(
            nextcloud.read_calls[0]["max_bytes"],
            workspace_folder_generated_image_content_service.IMAGE_CONTENT_MAX_BYTES,
        )

        downloaded = workspace_folder_generated_image_content_service.download_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=_FakeImages(),
            nextcloud=nextcloud,
            disposition="attachment",
        )

        self.assertTrue(downloaded.ok)
        self.assertIn("attachment", downloaded.headers["Content-Disposition"])

    def test_delete_is_remote_first_then_tombstones_local(self) -> None:
        images = _FakeImages()
        nextcloud = _FakeNextcloud()

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(nextcloud.delete_calls[0]["image_name"], TARGET_NAME)
        self.assertTrue(nextcloud.delete_calls[0]["missing_ok"])
        self.assertEqual(images.tombstones[0]["image_id"], IMAGE_ID)
        self.assertEqual(images.tombstones[0]["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(images.tombstones[0]["target_name_internal"], TARGET_NAME)
        self.assertEqual(
            images.tombstones[0]["target_ref"],
            workspace_folder_generated_images.target_ref_for_target(TARGET_NAME),
        )
        self.assertEqual(payload["generated_image_delete"]["delete_state"], "deleted")
        self.assertEqual(payload["reason_code"], "folder_generated_image_delete_ok")

    def test_local_failures_refuse_before_any_webdav(self) -> None:
        cases = (
            ("folder_non_linked", _FakeFolders(_folder(linked=False)), _FakeImages()),
            ("folder_deleted", _FakeFolders(_folder(deleted=True)), _FakeImages()),
            ("folder_store_failure", _FakeFolders(fail=True), _FakeImages()),
            ("image_absent", _FakeFolders(), _FakeImages(None)),
            (
                "cross_folder",
                _FakeFolders(),
                _FakeImages(_image(workspace_folder_id="bbbbbbbb-cccc-4ddd-8eee-ffffffffffff")),
            ),
            ("image_deleted", _FakeFolders(), _FakeImages(_image(deleted_at="x"))),
            (
                "image_sync_error",
                _FakeFolders(),
                _FakeImages(_image(nextcloud_sync_state="sync_error")),
            ),
            (
                "target_invalid",
                _FakeFolders(),
                _FakeImages(_image(target_name_internal="ClientSecretTarget.png")),
            ),
            ("image_store_failure", _FakeFolders(), _FakeImages(fail_get=True)),
        )

        for _name, folders, images in cases:
            with self.subTest(case=_name):
                nextcloud = _FakeNextcloud()
                result = workspace_folder_generated_image_content_service.download_workspace_folder_generated_image_response(
                    FOLDER_ID,
                    IMAGE_ID,
                    workspace_folders_module=folders,
                    generated_images_module=images,
                    nextcloud=nextcloud,
                )
                self.assertFalse(result.ok)
                self.assertFalse(nextcloud.read_calls)
                payload, _status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
                    FOLDER_ID,
                    IMAGE_ID,
                    workspace_folders_module=folders,
                    generated_images_module=images,
                    nextcloud=nextcloud,
                )
                self.assertFalse(payload["ok"])
                self.assertFalse(nextcloud.delete_calls)
                self.assertNotIn("remote.php", str(result.payload))
                self.assertNotIn("Secret", str(result.payload))

    def test_remote_read_too_large_invalid_bytes_and_mime_mismatch_fail_closed(self) -> None:
        too_large = _FakeNextcloud(
            read_error=workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_TOO_LARGE,
                http_status=200,
            )
        )
        result = workspace_folder_generated_image_content_service.download_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=_FakeImages(),
            nextcloud=too_large,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 413)

        invalid = workspace_folder_generated_image_content_service.download_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=_FakeImages(),
            nextcloud=_FakeNextcloud(content=b"not an image", media_type="image/png"),
        )
        self.assertFalse(invalid.ok)
        self.assertEqual(invalid.reason_code, "folder_generated_image_mime_invalid")

        mismatch = workspace_folder_generated_image_content_service.download_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=_FakeImages(),
            nextcloud=_FakeNextcloud(content=_jpeg_bytes(), media_type="image/jpeg"),
        )
        self.assertFalse(mismatch.ok)
        self.assertEqual(mismatch.reason_code, "folder_generated_image_mime_invalid")

    def test_delete_remote_failure_does_not_tombstone_and_tombstone_failure_is_partial(self) -> None:
        for remote_status in (0, 401, 403, 500):
            with self.subTest(remote_status=remote_status):
                images = _FakeImages()
                remote_failure = _FakeNextcloud(
                    delete_error=workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError(
                        workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
                        http_status=remote_status,
                    )
                )

                payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
                    FOLDER_ID,
                    IMAGE_ID,
                    workspace_folders_module=_FakeFolders(),
                    generated_images_module=images,
                    nextcloud=remote_failure,
                )

                self.assertFalse(payload["ok"])
                self.assertEqual(status, 502)
                self.assertFalse(images.tombstones)

        tombstone_failure_images = _FakeImages(fail_tombstone=True)
        partial, partial_status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=tombstone_failure_images,
            nextcloud=_FakeNextcloud(),
        )

        self.assertEqual(partial_status, 503)
        self.assertFalse(partial["ok"])
        self.assertEqual(
            partial["generated_image_delete"]["delete_state"],
            "remote_deleted_local_tombstone_failed",
        )
        self.assertNotIn("raw tombstone", str(partial))
        self.assertNotIn(TARGET_NAME, str(partial))

    def test_tombstone_precondition_miss_is_never_reported_as_success(self) -> None:
        class _PreconditionMissImages(_FakeImages):
            def tombstone_generated_image(self, image_id: str, **kwargs: Any):
                self.tombstones.append({"image_id": image_id, **kwargs})
                return None

        images = _PreconditionMissImages()

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_FakeFolders(),
            generated_images_module=images,
            nextcloud=_FakeNextcloud(),
        )

        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertEqual(
            payload["generated_image_delete"]["delete_state"],
            "remote_deleted_local_tombstone_failed",
        )
        self.assertNotIn(TARGET_NAME, str(payload))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
