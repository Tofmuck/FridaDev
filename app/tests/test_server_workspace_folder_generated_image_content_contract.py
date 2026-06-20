from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_image_content_service
from core import workspace_folder_generated_images
from tests.support.server_test_bootstrap import load_server_module_for_tests


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
IMAGE_ID = "11111111-2222-4333-8444-555555555555"


class _FakeContentService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.download_calls: list[dict[str, str]] = []
        self.delete_calls: list[dict[str, str]] = []

    def download_workspace_folder_generated_image_response(self, folder_id, image_id, **kwargs):
        self.download_calls.append(
            {
                "folder_id": folder_id,
                "image_id": image_id,
                "disposition": str(kwargs.get("disposition") or ""),
            }
        )
        if self.fail:
            return workspace_folder_generated_image_content_service.GeneratedImageContentResponse(
                False,
                503,
                workspace_folder_generated_images.REASON_LOOKUP_FAILED,
                payload={
                    "ok": False,
                    "reason_code": workspace_folder_generated_images.REASON_LOOKUP_FAILED,
                    "error": "recherche image impossible",
                    "generated_image_v1_technical": {
                        "reason_code": workspace_folder_generated_images.REASON_LOOKUP_FAILED,
                        "target_ref": "generated-image-target:123456abcdef",
                    },
                },
            )
        reason = (
            workspace_folder_generated_images.REASON_OPEN_OK
            if kwargs.get("disposition") == "inline"
            else workspace_folder_generated_images.REASON_DOWNLOAD_OK
        )
        return workspace_folder_generated_image_content_service.GeneratedImageContentResponse(
            True,
            200,
            reason,
            content=b"image-bytes",
            media_type="image/png",
            headers={
                "Content-Type": "image/png",
                "Content-Length": "11",
                "Content-Disposition": f'{kwargs.get("disposition")}; filename="Image.png"',
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frida-Reason-Code": reason,
            },
        )

    def delete_workspace_folder_generated_image_response(self, folder_id, image_id, **kwargs):
        self.delete_calls.append({"folder_id": folder_id, "image_id": image_id})
        return {
            "ok": not self.fail,
            "reason_code": (
                workspace_folder_generated_images.REASON_DELETE_OK
                if not self.fail
                else workspace_folder_generated_images.REASON_DELETE_FAILED_REDACTED
            ),
        }, (200 if not self.fail else 502)


class ServerWorkspaceFolderGeneratedImageContentContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = load_server_module_for_tests()
        self.client = self.server.app.test_client()

    def _patch(self, content_service):
        original = self.server.workspace_folder_generated_image_content_service
        self.server.workspace_folder_generated_image_content_service = content_service
        return original

    def _restore(self, original) -> None:
        self.server.workspace_folder_generated_image_content_service = original

    def test_open_and_download_routes_are_namespaced_and_preserve_safe_headers(self) -> None:
        fake = _FakeContentService()
        original = self._patch(fake)
        try:
            opened = self.client.get(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}/open"
            )
            downloaded = self.client.get(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}/download"
            )
        finally:
            self._restore(original)

        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.headers["Content-Type"], "image/png")
        self.assertEqual(opened.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(opened.headers["Cache-Control"], "private, no-store")
        self.assertIn("inline", opened.headers["Content-Disposition"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertIn("attachment", downloaded.headers["Content-Disposition"])
        self.assertEqual(
            fake.download_calls,
            [
                {"folder_id": FOLDER_ID, "image_id": IMAGE_ID, "disposition": "inline"},
                {"folder_id": FOLDER_ID, "image_id": IMAGE_ID, "disposition": "attachment"},
            ],
        )
        self.assertEqual(
            self.client.get(f"/api/generated-images/{IMAGE_ID}/download").status_code,
            404,
        )
        self.assertEqual(self.client.get(f"/api/images/{IMAGE_ID}/open").status_code, 404)

    def test_delete_route_is_namespaced(self) -> None:
        fake = _FakeContentService()
        original = self._patch(fake)
        try:
            response = self.client.delete(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}"
            )
        finally:
            self._restore(original)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["reason_code"], "folder_generated_image_delete_ok")
        self.assertEqual(fake.delete_calls, [{"folder_id": FOLDER_ID, "image_id": IMAGE_ID}])
        self.assertIn(
            self.client.delete(f"/api/generated-images/{IMAGE_ID}").status_code,
            {404, 405},
        )
        self.assertIn(self.client.delete(f"/api/images/{IMAGE_ID}").status_code, {404, 405})

    def test_content_service_errors_remain_content_free(self) -> None:
        fake = _FakeContentService(fail=True)
        original = self._patch(fake)
        try:
            response = self.client.get(
                f"/api/workspace-folders/{FOLDER_ID}/generated-images/{IMAGE_ID}/download"
            )
        finally:
            self._restore(original)

        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertFalse(body["ok"])
        text = str(body)
        self.assertNotIn("generated-image-11111111", text)
        self.assertNotIn("remote.php", text)
        self.assertNotIn("data:image", text)
        self.assertNotIn("base64", text)
        self.assertNotIn("raw-etag", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
