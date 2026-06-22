from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_image_nextcloud_client
from core import workspace_folder_generated_image_nextcloud_runtime
from core import workspace_folder_generated_image_provider
from core import workspace_folder_generated_image_validation
from core import workspace_folder_generated_images
from core import workspace_folder_nextcloud_client


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def _folder(*, linked: bool = True, deleted: bool = False) -> dict[str, Any]:
    return {
        "id": FOLDER_ID,
        "display_name": "Dossier Images",
        "nextcloud_target_name": "Dossier-Images",
        "nextcloud_sync_state": "linked" if linked else "local_only",
        "deleted_at": "2026-06-19T10:00:00Z" if deleted else None,
    }


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


def _webp_bytes(width: int = 56, height: int = 48) -> bytes:
    def u24(value: int) -> bytes:
        return bytes((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF))

    payload = b"\x00\x00\x00\x00" + u24(int(width) - 1) + u24(int(height) - 1)
    return b"RIFF" + (18).to_bytes(4, "little") + b"WEBPVP8X" + (10).to_bytes(4, "little") + payload


def _gif_bytes(width: int = 32, height: int = 32) -> bytes:
    return b"GIF89a" + int(width).to_bytes(2, "little") + int(height).to_bytes(2, "little")


def _data_url(content: bytes, *, mime_type: str = "image/png") -> str:
    return f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"


class _FakeProvider:
    def __init__(self, result: workspace_folder_generated_image_provider.GeneratedImageProviderResult | None = None):
        self.result = result or workspace_folder_generated_image_provider.GeneratedImageProviderResult(
            True,
            workspace_folder_generated_images.REASON_CREATE_OK,
            status=200,
            data_url=_data_url(_png_bytes()),
            generator_key="image_generator_nano_banana",
            provider_model="google/gemini-2.5-flash-image",
            aspect_ratio="1:1",
            image_size="1K",
            prompt_length=120,
            data_url_chars=128,
        )
        self.calls = 0

    def generate_generated_image_data_url(self, payload: dict[str, Any]):
        self.calls += 1
        return self.result


class _FakeNextcloud:
    def __init__(
        self,
        *,
        status_reason: str = "",
        put_status: int = 201,
        delete_fails: bool = False,
    ) -> None:
        self.status_reason = status_reason
        self.put_status = put_status
        self.delete_fails = delete_fails
        self.status_calls: list[str] = []
        self.put_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []

    def images_status(self, folder_name: str):
        self.status_calls.append(folder_name)
        if self.status_reason:
            raise workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError(
                self.status_reason,
                http_status=404 if self.status_reason.endswith("missing") else 409,
            )
        return workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageResponse(
            True,
            workspace_folder_generated_images.REASON_STORE_OK,
            207,
        )

    def put_image(self, folder_name: str, image_name: str, content: bytes, *, media_type: str = ""):
        self.put_calls.append(
            {
                "folder_name": folder_name,
                "image_name": image_name,
                "content": bytes(content or b""),
                "media_type": media_type,
            }
        )
        if self.put_status == 201:
            return workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageResponse(
                True,
                workspace_folder_generated_images.REASON_STORE_OK,
                201,
                etag_value='"hidden-etag"',
            )
        reason = (
            workspace_folder_generated_images.REASON_NAME_CONFLICT
            if self.put_status in {200, 204}
            else workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
        )
        raise workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError(
            reason,
            http_status=self.put_status,
        )

    def delete_image(self, folder_name: str, image_name: str, *, missing_ok: bool = True):
        self.delete_calls.append(
            {"folder_name": folder_name, "image_name": image_name, "missing_ok": missing_ok}
        )
        if self.delete_fails:
            raise workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
                http_status=500,
            )
        return workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageResponse(
            True,
            workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _ChunkedReadResponse:
    def __init__(self, chunks: list[bytes], *, content_length: str = "") -> None:
        self.status = 200
        self.headers = {"Content-Length": content_length, "Content-Type": "image/png"}
        self._chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _FakeImagesModule:
    def __init__(self, *, fail_upsert: bool = False) -> None:
        self.fail_upsert = fail_upsert
        self.stored: list[dict[str, Any]] = []
        self.events: list[tuple[str, dict[str, Any]]] = []

    def upsert_generated_image(self, **fields: Any):
        self.stored.append(dict(fields))
        if self.fail_upsert:
            raise RuntimeError("raw db failure prompt secret remote.php")
        target = fields["target_name_internal"]
        return {
            "id": fields["generated_image_id"],
            "workspace_folder_id": fields["workspace_folder_id"],
            "display_name": fields["display_name"],
            "display_name_hash": workspace_folder_generated_images.display_name_hash_for_value(
                fields["display_name"]
            ),
            "target_name_internal": target,
            "target_ref": workspace_folder_generated_images.target_ref_for_target(target),
            "mime_type": fields["mime_type"],
            "image_format": fields["image_format"],
            "byte_size": fields["byte_size"],
            "width": fields["width"],
            "height": fields["height"],
            "content_hash": fields["content_hash"],
            "content_hash_short": fields["content_hash_short"],
            "generator_key": fields["generator_key"],
            "provider_model": fields["provider_model"],
            "aspect_ratio": fields["aspect_ratio"],
            "image_size": fields["image_size"],
            "prompt_present": fields["prompt_present"],
            "prompt_length_bucket": fields["prompt_length_bucket"],
            "local_state": fields["local_state"],
            "nextcloud_sync_state": fields["nextcloud_sync_state"],
            "etag_value": fields["etag_value"],
            "etag_hash": fields["etag_hash"],
            "last_reason_code": fields["last_reason_code"],
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
            "deleted_at": None,
        }

    def log_content_free_event(self, event: str, **fields: Any) -> None:
        self.events.append((event, dict(fields)))


class WorkspaceFolderGeneratedImageValidationAndRuntimeTests(unittest.TestCase):
    def test_nextcloud_read_refuses_oversized_content_without_truncation(self) -> None:
        client = workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClient(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="https://nextcloud.example",
                username="user",
                app_password="secret",
            )
        )
        original_urlopen = workspace_folder_generated_image_nextcloud_client.urlopen
        workspace_folder_generated_image_nextcloud_client.urlopen = lambda _request, timeout=12: (
            _ChunkedReadResponse([b"1234", b"5678", b"9"])
        )
        try:
            with self.assertRaises(
                workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClientError
            ) as ctx:
                client.read_image("Dossier-Images", "generated-image-x.png", max_bytes=8)
        finally:
            workspace_folder_generated_image_nextcloud_client.urlopen = original_urlopen

        self.assertEqual(ctx.exception.reason_code, "folder_generated_image_too_large")
        self.assertEqual(ctx.exception.http_status, 200)

    def test_validation_accepts_png_and_rejects_gif_svg_invalid_dimensions_and_large_payloads(self) -> None:
        ok = workspace_folder_generated_image_validation.validate_generated_image_data_url(
            _data_url(_png_bytes())
        )
        self.assertTrue(ok.ok)
        self.assertEqual(ok.mime_type, "image/png")
        self.assertEqual(ok.image_format, "png")

        jpeg = workspace_folder_generated_image_validation.validate_generated_image_data_url(
            _data_url(_jpeg_bytes(width=48, height=40), mime_type="image/jpeg")
        )
        self.assertTrue(jpeg.ok)
        self.assertEqual(jpeg.mime_type, "image/jpeg")
        self.assertEqual(jpeg.image_format, "jpeg")
        self.assertEqual(jpeg.width, 48)
        self.assertEqual(jpeg.height, 40)

        webp = workspace_folder_generated_image_validation.validate_generated_image_data_url(
            _data_url(_webp_bytes(width=56, height=48), mime_type="image/webp")
        )
        self.assertTrue(webp.ok)
        self.assertEqual(webp.mime_type, "image/webp")
        self.assertEqual(webp.image_format, "webp")
        self.assertEqual(webp.width, 56)
        self.assertEqual(webp.height, 48)

        gif = workspace_folder_generated_image_validation.validate_generated_image_data_url(
            _data_url(_gif_bytes(), mime_type="image/gif")
        )
        self.assertFalse(gif.ok)
        self.assertEqual(gif.reason_code, "folder_generated_image_format_unsupported")

        svg = workspace_folder_generated_image_validation.validate_generated_image_data_url(
            "data:image/svg+xml;base64,PHN2Zy8+"
        )
        self.assertFalse(svg.ok)
        self.assertEqual(svg.reason_code, "folder_generated_image_format_unsupported")

        small = workspace_folder_generated_image_validation.validate_generated_image_data_url(
            _data_url(_png_bytes(width=31, height=32))
        )
        self.assertFalse(small.ok)
        self.assertEqual(small.reason_code, "folder_generated_image_dimensions_invalid")

        original = workspace_folder_generated_image_validation.V1_IMAGE_MAX_BYTES
        workspace_folder_generated_image_validation.V1_IMAGE_MAX_BYTES = 8
        try:
            too_large = workspace_folder_generated_image_validation.validate_generated_image_data_url(
                _data_url(_png_bytes())
            )
        finally:
            workspace_folder_generated_image_validation.V1_IMAGE_MAX_BYTES = original
        self.assertFalse(too_large.ok)
        self.assertEqual(too_large.reason_code, "folder_generated_image_too_large")

        original_chars = workspace_folder_generated_image_validation.V1_IMAGE_DATA_URL_MAX_CHARS
        workspace_folder_generated_image_validation.V1_IMAGE_DATA_URL_MAX_CHARS = 24
        try:
            too_long_url = workspace_folder_generated_image_validation.validate_generated_image_data_url(
                _data_url(_png_bytes())
            )
        finally:
            workspace_folder_generated_image_validation.V1_IMAGE_DATA_URL_MAX_CHARS = original_chars
        self.assertFalse(too_long_url.ok)
        self.assertEqual(
            too_long_url.reason_code,
            "folder_generated_image_data_url_too_large",
        )

    def test_folder_not_linked_and_client_image_id_are_refused_before_provider(self) -> None:
        provider = _FakeProvider()
        images = _FakeImagesModule()
        nextcloud = _FakeNextcloud()

        folder_result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(linked=False),
            request={"prompt": "x"},
            provider_module=provider,
            images_module=images,
            nextcloud=nextcloud,
        )
        self.assertFalse(folder_result["ok"])
        self.assertEqual(folder_result["reason_code"], "folder_generated_image_folder_not_linked")
        self.assertEqual(provider.calls, 0)
        self.assertFalse(nextcloud.status_calls)
        self.assertFalse(images.stored)

        image_id_result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(),
            request={"image_id": "11111111-2222-4333-8444-555555555555"},
            provider_module=provider,
            images_module=images,
            nextcloud=nextcloud,
        )
        self.assertFalse(image_id_result["ok"])
        self.assertEqual(
            image_id_result["reason_code"],
            "folder_generated_image_client_image_id_forbidden",
        )
        self.assertEqual(provider.calls, 0)

    def test_put_201_persists_linked_metadata_only(self) -> None:
        provider = _FakeProvider()
        images = _FakeImagesModule()
        nextcloud = _FakeNextcloud()

        result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(),
            request={"prompt": "x", "display_name": "Image utilisateur"},
            provider_module=provider,
            images_module=images,
            nextcloud=nextcloud,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], "folder_generated_image_store_ok")
        self.assertEqual(nextcloud.status_calls, ["Dossier-Images"])
        self.assertEqual(len(nextcloud.put_calls), 1)
        self.assertEqual(nextcloud.put_calls[0]["media_type"], "image/png")
        self.assertEqual(len(images.stored), 1)
        stored = images.stored[0]
        self.assertTrue(stored["remote_proof"])
        self.assertEqual(stored["nextcloud_sync_state"], "linked")
        self.assertEqual(stored["prompt_length_bucket"], "chars_001_to_250")
        self.assertNotIn("prompt", stored)
        self.assertNotIn("image_bytes", stored)
        self.assertNotIn("data_url", stored)

    def test_jpeg_and_webp_runtime_use_canonical_formats_and_extensions(self) -> None:
        cases = (
            ("image/jpeg", _jpeg_bytes(), "jpeg", ".jpg"),
            ("image/webp", _webp_bytes(), "webp", ".webp"),
        )
        for mime_type, content, image_format, extension in cases:
            with self.subTest(mime_type=mime_type):
                provider = _FakeProvider(
                    workspace_folder_generated_image_provider.GeneratedImageProviderResult(
                        True,
                        workspace_folder_generated_images.REASON_CREATE_OK,
                        status=200,
                        data_url=_data_url(content, mime_type=mime_type),
                        generator_key="image_generator_nano_banana",
                        provider_model="google/gemini-2.5-flash-image",
                        aspect_ratio="1:1",
                        image_size="1K",
                        prompt_length=64,
                        data_url_chars=128,
                    )
                )
                images = _FakeImagesModule()
                nextcloud = _FakeNextcloud()

                result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
                    folder=_folder(),
                    request={"prompt": "x"},
                    provider_module=provider,
                    images_module=images,
                    nextcloud=nextcloud,
                )

                self.assertTrue(result["ok"])
                self.assertEqual(nextcloud.put_calls[0]["media_type"], mime_type)
                self.assertTrue(nextcloud.put_calls[0]["image_name"].endswith(extension))
                self.assertEqual(images.stored[0]["mime_type"], mime_type)
                self.assertEqual(images.stored[0]["image_format"], image_format)
                self.assertTrue(images.stored[0]["target_name_internal"].endswith(extension))

    def test_put_update_like_is_conflict_without_local_upsert(self) -> None:
        images = _FakeImagesModule()
        nextcloud = _FakeNextcloud(put_status=200)

        result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(),
            request={"prompt": "x"},
            provider_module=_FakeProvider(),
            images_module=images,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_generated_image_name_conflict")
        self.assertEqual(len(nextcloud.put_calls), 1)
        self.assertFalse(images.stored)

    def test_provider_ok_but_storage_unavailable_is_failure_without_linked_row(self) -> None:
        images = _FakeImagesModule()
        nextcloud = _FakeNextcloud(
            status_reason=workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION
        )

        result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(),
            request={"prompt": "x"},
            provider_module=_FakeProvider(),
            images_module=images,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["reason_code"],
            "folder_generated_image_images_target_not_collection",
        )
        self.assertFalse(nextcloud.put_calls)
        self.assertFalse(images.stored)
        self.assertNotIn("data:image", str(result))

    def test_remote_created_then_local_persistence_failure_rolls_back_exact_target(self) -> None:
        images = _FakeImagesModule(fail_upsert=True)
        nextcloud = _FakeNextcloud()

        result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(),
            request={"prompt": "x"},
            provider_module=_FakeProvider(),
            images_module=images,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_generated_image_local_persistence_failed")
        self.assertEqual(len(nextcloud.put_calls), 1)
        self.assertEqual(len(nextcloud.delete_calls), 1)
        self.assertEqual(nextcloud.delete_calls[0]["image_name"], nextcloud.put_calls[0]["image_name"])
        self.assertTrue(result["generated_image_nextcloud"]["rollback"]["ok"])
        self.assertNotIn("raw db failure", str(result))

    def test_rollback_failure_is_explicit_content_free(self) -> None:
        result = workspace_folder_generated_image_nextcloud_runtime.store_workspace_folder_generated_image_nextcloud_first(
            folder=_folder(),
            request={"prompt": "x"},
            provider_module=_FakeProvider(),
            images_module=_FakeImagesModule(fail_upsert=True),
            nextcloud=_FakeNextcloud(delete_fails=True),
        )

        self.assertFalse(result["ok"])
        rollback = result["generated_image_nextcloud"]["rollback"]
        self.assertFalse(rollback["ok"])
        self.assertEqual(
            rollback["reason_code"],
            "folder_generated_image_remote_compensation_failed",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
