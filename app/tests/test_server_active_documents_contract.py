from __future__ import annotations

import io
import json
import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


CONV_ID = "11111111-1111-1111-1111-111111111111"
DOC_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RAW_DOCUMENT_TEXT = "texte exact du fichier qui ne doit pas revenir dans l API"


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

    def deactivate_document(self, conversation_id, document_id, *, reason_code):
        for item in list(self.items):
            if item["conversation_id"] == conversation_id and item["document_id"] == document_id:
                self.items.remove(item)
                item["last_excluded_reason_code"] = reason_code
                return True
        return False


class ServerActiveDocumentsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_conv_store = self.server.conv_store
        self.original_active_docs = self.server.active_conversation_documents
        self.fake_docs = _FakeActiveDocuments()
        self.server.conv_store = _FakeConvStore()
        self.server.active_conversation_documents = self.fake_docs

    def tearDown(self) -> None:
        self.server.conv_store = self.original_conv_store
        self.server.active_conversation_documents = self.original_active_docs

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

        list_response = self.client.get(f"/api/conversations/{CONV_ID}/active-documents")
        self.assertEqual(list_response.status_code, 200)
        list_payload = list_response.get_json()
        self.assertEqual(len(list_payload["items"]), 1)
        self.assertNotIn(RAW_DOCUMENT_TEXT, json.dumps(list_payload, ensure_ascii=False))

        delete_response = self.client.delete(f"/api/conversations/{CONV_ID}/active-documents/{DOC_ID}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.get_json()["ok"])
        self.assertEqual(self.fake_docs.items, [])

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

    def test_active_documents_require_existing_conversation_scope(self):
        invalid = self.client.get("/api/conversations/not-a-uuid/active-documents")
        self.assertEqual(invalid.status_code, 400)

        missing = self.client.get("/api/conversations/22222222-2222-2222-2222-222222222222/active-documents")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
