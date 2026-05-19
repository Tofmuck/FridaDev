from __future__ import annotations

import io
import json
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests
from core import active_document_image_validation


CONV_ID = "11111111-1111-1111-1111-111111111111"
DOC_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RAW_DOCUMENT_TEXT = "texte exact du fichier qui ne doit pas revenir dans l API"


def _png_bytes(width=64, height=48):
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + int(width).to_bytes(4, "big")
        + int(height).to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


def _jpeg_bytes(width=64, height=48):
    return (
        b"\xff\xd8\xff\xc0\x00\x11\x08"
        + int(height).to_bytes(2, "big")
        + int(width).to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )


def _webp_bytes(width=64, height=48):
    def u24(value):
        return bytes((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF))

    payload = b"\x00\x00\x00\x00" + u24(width - 1) + u24(height - 1)
    return b"RIFF" + (18).to_bytes(4, "little") + b"WEBPVP8X" + (10).to_bytes(4, "little") + payload


def _gif_bytes(width=64, height=48):
    return b"GIF89a" + int(width).to_bytes(2, "little") + int(height).to_bytes(2, "little")


class _FakeConvStore:
    def normalize_conversation_id(self, value):
        raw = str(value or "").strip()
        try:
            return str(uuid.UUID(raw))
        except ValueError:
            return None

    def read_conversation(self, conversation_id, _system_prompt):
        if conversation_id == CONV_ID:
            return {"id": conversation_id, "messages": []}
        return None


class _FakeActiveDocuments:
    DEFAULT_REMOVE_REASON = "manual_remove"

    def __init__(self):
        self.items = []
        self.activated_texts = []
        self.activated_images = []

    def list_active_documents(self, conversation_id):
        return [dict(item) for item in self.items if item["conversation_id"] == conversation_id]

    def activate_document(self, conversation_id, **kwargs):
        self.activated_texts.append(kwargs.get("text_content") or "")
        item = {
            "document_id": DOC_ID,
            "conversation_id": conversation_id,
            "filename": kwargs.get("filename") or "",
            "media_type": kwargs.get("media_type") or "",
            "source_extension": kwargs.get("source_extension") or "",
            "byte_size": kwargs.get("byte_size") or 0,
            "text_chars": len(kwargs.get("text_content") or ""),
            "text_sha256_12": "abc123def456",
            "token_estimate": kwargs.get("token_estimate") or 0,
            "status": "active",
            "active": True,
            "created_at": "2026-05-16T12:00:00Z",
            "deactivated_at": "",
            "last_injected_turn_id": "",
            "last_excluded_turn_id": "",
            "last_excluded_reason_code": "",
            "source": "active_conversation_documents",
        }
        self.items.append(item)
        return dict(item)

    def activate_image_document(self, conversation_id, **kwargs):
        self.activated_images.append(bytes(kwargs.get("image_content") or b""))
        item = {
            "document_id": DOC_ID,
            "conversation_id": conversation_id,
            "filename": kwargs.get("filename") or "",
            "media_type": kwargs.get("media_type") or "",
            "source_extension": kwargs.get("source_extension") or "",
            "byte_size": kwargs.get("byte_size") or 0,
            "text_chars": 0,
            "text_sha256_12": "",
            "media_kind": "image",
            "content_sha256_12": kwargs.get("content_sha256_12") or "",
            "image_width": kwargs.get("image_width") or 0,
            "image_height": kwargs.get("image_height") or 0,
            "token_estimate": 0,
            "status": "active",
            "active": True,
            "created_at": "2026-05-16T12:00:00Z",
            "deactivated_at": "",
            "last_injected_turn_id": "",
            "last_excluded_turn_id": "",
            "last_excluded_reason_code": "",
            "source": "active_conversation_documents",
        }
        self.items.append(item)
        return dict(item)

    def deactivate_document(self, conversation_id, document_id, *, reason_code):
        for item in list(self.items):
            if item["conversation_id"] == conversation_id and item["document_id"] == document_id:
                self.items.remove(item)
                item["last_excluded_reason_code"] = reason_code
                return True
        return False


class _FakeAdminLogs:
    def __init__(self):
        self.events = []

    def log_event(self, stage, **payload):
        self.events.append({"stage": stage, "payload": payload})


class ServerActiveDocumentsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_conv_store = self.server.conv_store
        self.original_active_docs = self.server.active_conversation_documents
        self.original_admin_logs = self.server.admin_logs
        self.fake_docs = _FakeActiveDocuments()
        self.fake_admin_logs = _FakeAdminLogs()
        self.server.conv_store = _FakeConvStore()
        self.server.active_conversation_documents = self.fake_docs
        self.server.admin_logs = self.fake_admin_logs

    def tearDown(self) -> None:
        self.server.conv_store = self.original_conv_store
        self.server.active_conversation_documents = self.original_active_docs
        self.server.admin_logs = self.original_admin_logs

    def test_upload_list_and_remove_active_document_are_content_free(self):
        response = self.client.post(
            f"/api/conversations/{CONV_ID}/active-documents",
            data={"file": (io.BytesIO(RAW_DOCUMENT_TEXT.encode("utf-8")), "note.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["document"]["filename"], "note.txt")
        self.assertEqual(payload["document"]["source_extension"], ".txt")
        self.assertNotIn("text_content", payload["document"])
        self.assertNotIn("text", payload["document"])
        self.assertEqual(self.fake_docs.activated_texts, [RAW_DOCUMENT_TEXT])
        self.assertNotIn(RAW_DOCUMENT_TEXT, json.dumps(payload, ensure_ascii=False))
        self.assertEqual(self.fake_admin_logs.events[0]["stage"], "active_document_activated")
        self.assertFalse(self.fake_admin_logs.events[0]["payload"]["raw_content_included"])
        self.assertNotIn(RAW_DOCUMENT_TEXT, json.dumps(self.fake_admin_logs.events, ensure_ascii=False))

        list_response = self.client.get(f"/api/conversations/{CONV_ID}/active-documents")
        self.assertEqual(list_response.status_code, 200)
        list_payload = list_response.get_json()
        self.assertEqual(len(list_payload["items"]), 1)
        self.assertNotIn(RAW_DOCUMENT_TEXT, json.dumps(list_payload, ensure_ascii=False))

        delete_response = self.client.delete(f"/api/conversations/{CONV_ID}/active-documents/{DOC_ID}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.get_json()["ok"])
        self.assertEqual(self.fake_docs.items, [])
        self.assertEqual(self.fake_admin_logs.events[-1]["stage"], "active_document_removed")
        self.assertEqual(self.fake_admin_logs.events[-1]["payload"]["reason_code"], "manual_remove")

    def test_upload_png_active_image_is_content_free_and_removable(self):
        raw_image = _png_bytes(80, 64)
        response = self.client.post(
            f"/api/conversations/{CONV_ID}/active-documents",
            data={"file": (io.BytesIO(raw_image), "capture.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        encoded_logs = json.dumps(self.fake_admin_logs.events, ensure_ascii=False)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["document"]["media_kind"], "image")
        self.assertEqual(payload["document"]["media_type"], "image/png")
        self.assertEqual(payload["document"]["image_width"], 80)
        self.assertEqual(payload["document"]["image_height"], 64)
        self.assertEqual(payload["document"]["text_chars"], 0)
        self.assertNotIn("text_content", payload["document"])
        self.assertNotIn("binary_content", encoded_payload)
        self.assertNotIn("data:image", encoded_payload)
        self.assertEqual(self.fake_docs.activated_images, [raw_image])
        self.assertEqual(self.fake_admin_logs.events[-1]["stage"], "active_document_activated")
        self.assertEqual(self.fake_admin_logs.events[-1]["payload"]["media_kind"], "image")
        self.assertEqual(self.fake_admin_logs.events[-1]["payload"]["image_width"], 80)
        self.assertFalse(self.fake_admin_logs.events[-1]["payload"]["raw_content_included"])
        self.assertNotIn("data:image", encoded_logs)

        delete_response = self.client.delete(f"/api/conversations/{CONV_ID}/active-documents/{DOC_ID}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.get_json()["ok"])

    def test_upload_jpeg_and_webp_active_images(self):
        cases = [
            ("photo.jpg", "image/jpeg", _jpeg_bytes(64, 40), "image/jpeg"),
            ("diagram.webp", "image/webp", _webp_bytes(72, 48), "image/webp"),
        ]
        for filename, media_type, raw_image, expected_media_type in cases:
            with self.subTest(filename=filename):
                self.fake_docs.items.clear()
                self.fake_docs.activated_images.clear()
                response = self.client.post(
                    f"/api/conversations/{CONV_ID}/active-documents",
                    data={"file": (io.BytesIO(raw_image), filename)},
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 201)
                payload = response.get_json()
                self.assertEqual(payload["document"]["media_kind"], "image")
                self.assertEqual(payload["document"]["media_type"], expected_media_type)
                self.assertEqual(self.fake_docs.activated_images, [raw_image])

    def test_image_upload_rejects_gif_in_v0(self):
        response = self.client.post(
            f"/api/conversations/{CONV_ID}/active-documents",
            data={"file": (io.BytesIO(_gif_bytes()), "animated.gif")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 422)
        payload = response.get_json()
        self.assertEqual(payload["reason_code"], "image_gif_unsupported_v0")
        self.assertEqual(self.fake_docs.activated_images, [])

    def test_image_upload_rejects_misleading_extension(self):
        response = self.client.post(
            f"/api/conversations/{CONV_ID}/active-documents",
            data={"file": (io.BytesIO(_png_bytes()), "photo.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 422)
        payload = response.get_json()
        self.assertEqual(payload["reason_code"], "image_extension_mismatch")
        self.assertEqual(self.fake_docs.activated_images, [])

    def test_image_upload_rejects_too_small_too_large_and_too_wide(self):
        cases = [
            ("tiny.png", _png_bytes(1, 1), "image_too_small_for_provider", None),
            ("huge.png", _png_bytes(64, 64) + (b"x" * 64), "image_too_large", 16),
            ("wide.png", _png_bytes(17000, 64), "image_dimensions_unsupported", None),
        ]
        for filename, raw_image, reason_code, max_bytes in cases:
            with self.subTest(filename=filename):
                patcher = (
                    mock.patch.object(active_document_image_validation, "ACTIVE_IMAGE_SOURCE_MAX_BYTES", max_bytes)
                    if max_bytes
                    else mock.patch.object(active_document_image_validation, "ACTIVE_IMAGE_SOURCE_MAX_BYTES", 32 * 1024 * 1024)
                )
                with patcher:
                    response = self.client.post(
                        f"/api/conversations/{CONV_ID}/active-documents",
                        data={"file": (io.BytesIO(raw_image), filename)},
                        content_type="multipart/form-data",
                    )
                self.assertEqual(response.status_code, 422)
                payload = response.get_json()
                self.assertEqual(payload["reason_code"], reason_code)
        self.assertEqual(self.fake_docs.activated_images, [])

    def test_unsupported_upload_returns_visible_reason_without_activation(self):
        response = self.client.post(
            f"/api/conversations/{CONV_ID}/active-documents",
            data={"file": (io.BytesIO(b"not supported"), "archive.bin")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 422)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "document_type_unsupported")
        self.assertEqual(payload["document"]["status"], "unsupported")
        self.assertNotIn("text", payload["document"])
        self.assertEqual(self.fake_docs.items, [])
        self.assertEqual(self.fake_docs.activated_texts, [])
        self.assertEqual(self.fake_admin_logs.events[-1]["stage"], "active_document_activation_failed")
        self.assertEqual(
            self.fake_admin_logs.events[-1]["payload"]["reason_code"],
            "document_type_unsupported",
        )
        self.assertNotIn("not supported", json.dumps(self.fake_admin_logs.events, ensure_ascii=False))

    def test_parse_error_upload_never_activates_or_returns_partial_text(self):
        raw_invalid_docx = b"RAW PARTIAL DOCX TEXT MUST NOT LEAK"
        response = self.client.post(
            f"/api/conversations/{CONV_ID}/active-documents",
            data={"file": (io.BytesIO(raw_invalid_docx), "broken.docx")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 422)
        payload = response.get_json()
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        encoded_logs = json.dumps(self.fake_admin_logs.events, ensure_ascii=False)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "document_parse_error")
        self.assertEqual(payload["document"]["status"], "parse_error")
        self.assertNotIn("text", payload["document"])
        self.assertEqual(self.fake_docs.items, [])
        self.assertEqual(self.fake_docs.activated_texts, [])
        self.assertEqual(self.fake_admin_logs.events[-1]["stage"], "active_document_activation_failed")
        self.assertEqual(
            self.fake_admin_logs.events[-1]["payload"]["reason_code"],
            "document_parse_error",
        )
        self.assertNotIn("RAW PARTIAL DOCX TEXT MUST NOT LEAK", encoded_payload)
        self.assertNotIn("RAW PARTIAL DOCX TEXT MUST NOT LEAK", encoded_logs)

    def test_active_documents_require_existing_conversation_scope(self):
        invalid = self.client.get("/api/conversations/not-a-uuid/active-documents")
        self.assertEqual(invalid.status_code, 400)

        missing = self.client.get("/api/conversations/22222222-2222-2222-2222-222222222222/active-documents")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
