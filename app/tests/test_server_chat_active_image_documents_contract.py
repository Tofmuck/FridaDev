from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - local host may not have repo deps.
    sys.modules["psycopg"] = types.ModuleType("psycopg")
    rows_module = types.ModuleType("psycopg.rows")
    rows_module.dict_row = object()
    sys.modules["psycopg.rows"] = rows_module
    types_module = types.ModuleType("psycopg.types")
    json_module = types.ModuleType("psycopg.types.json")
    json_module.Json = lambda value: value
    sys.modules["psycopg.types"] = types_module
    sys.modules["psycopg.types.json"] = json_module

from core import chat_stream_control
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


MAIN_IMAGE_MODEL = "anthropic/claude-sonnet-4.6"


class ServerChatActiveImageDocumentsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def test_stream_chat_injects_active_image_as_multimodal_provider_payload_only(self) -> None:
        observed: dict[str, object] = {"injected": [], "excluded": [], "events": []}
        conversation = {
            "id": "conv-active-image-lot2",
            "created_at": "2026-05-19T10:00:00Z",
            "messages": [{"role": "system", "content": "BACKEND SYSTEM PROMPT"}],
        }
        active_image = {
            "document_id": "image-doc-1",
            "conversation_id": conversation["id"],
            "filename": "capture.png",
            "media_type": "image/png",
            "source_extension": "png",
            "byte_size": len(b"image-bytes"),
            "text_chars": 0,
            "text_sha256_12": "",
            "media_kind": "image",
            "content_sha256_12": "123456abcdef",
            "image_width": 80,
            "image_height": 64,
            "token_estimate": 0,
            "status": "active",
            "active": True,
            "created_at": "2026-05-19T10:00:00Z",
            "image_content": b"image-bytes",
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter="\n"):
                yield 'data: {"id":"gen-image","model":"anthropic/claude-sonnet-4.6","choices":[{"delta":{"content":"Vu"}}]}'
                yield 'data: [DONE]'

        def fake_requests_post(_url, *, json, **kwargs):
            observed["provider_payload"] = dict(json)
            observed["stream"] = kwargs.get("stream")
            return FakeStreamResponse()

        observed_state, restore_pipeline = server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=fake_requests_post,
            runtime_model=MAIN_IMAGE_MODEL,
        )
        original_reader = self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt
        original_injected = self.server.chat_service.active_conversation_documents.record_document_injected
        original_excluded = self.server.chat_service.active_conversation_documents.record_document_excluded
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event
        self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt = (
            lambda _conversation_id: [active_image]
        )
        self.server.chat_service.active_conversation_documents.record_document_injected = (
            lambda conversation_id, document_id, *, turn_id: observed["injected"].append(
                (conversation_id, document_id, turn_id)
            )
            or True
        )
        self.server.chat_service.active_conversation_documents.record_document_excluded = (
            lambda conversation_id, document_id, *, turn_id, reason_code: observed["excluded"].append(
                (conversation_id, document_id, turn_id, reason_code)
            )
            or True
        )
        self.server.chat_turn_logger.log_store.insert_chat_log_event = (
            lambda event: observed["events"].append(dict(event)) or True
        )
        try:
            response = self.client.post(
                "/api/chat",
                json={"message": "Lis cette capture.", "stream": True},
                buffered=True,
            )
        finally:
            self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt = original_reader
            self.server.chat_service.active_conversation_documents.record_document_injected = original_injected
            self.server.chat_service.active_conversation_documents.record_document_excluded = original_excluded
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore_pipeline()

        text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(text, "Vu")
        self.assertEqual(terminal["event"], "done")
        self.assertTrue(observed["stream"])

        multimodal_messages = [
            message
            for message in observed_state["payload_messages"]
            if isinstance(message.get("content"), list)
        ]
        self.assertEqual(len(multimodal_messages), 1)
        parts = multimodal_messages[0]["content"]
        self.assertEqual(parts[0]["type"], "text")
        self.assertEqual(parts[1]["type"], "image_url")
        self.assertNotIn("data:image", parts[0]["text"])
        self.assertEqual(parts[1]["image_url"]["url"], "data:image/png;base64,aW1hZ2UtYnl0ZXM=")
        self.assertNotIn("imageUrl", json.dumps(observed["provider_payload"], ensure_ascii=False))

        persisted = json.dumps(conversation["messages"], ensure_ascii=False)
        self.assertNotIn("data:image", persisted)
        self.assertNotIn("aW1hZ2UtYnl0ZXM=", persisted)
        self.assertNotIn("image_url", persisted)
        self.assertNotIn("image_content", persisted)
        self.assertNotIn("binary_content", persisted)
        trace_payload = json.dumps(observed_state["save_new_traces_calls"], ensure_ascii=False)
        self.assertNotIn("data:image", trace_payload)
        self.assertNotIn("aW1hZ2UtYnl0ZXM=", trace_payload)
        self.assertNotIn("image_url", trace_payload)
        self.assertNotIn("image_content", trace_payload)
        self.assertNotIn("binary_content", trace_payload)
        self.assertEqual(observed["excluded"], [])
        self.assertEqual(len(observed["injected"]), 1)

        active_events = [event for event in observed["events"] if event["stage"] == "active_documents"]
        self.assertEqual(len(active_events), 1)
        active_payload = active_events[0]["payload_json"]
        self.assertEqual(active_payload["documents"][0]["decision"], "injected")
        self.assertEqual(active_payload["documents"][0]["media_kind"], "image")
        self.assertEqual(active_payload["documents"][0]["payload_order"], "text_then_image_url")
        self.assertEqual(active_payload["documents"][0]["provider_model"], MAIN_IMAGE_MODEL)
        self.assertNotIn("data:image", json.dumps(active_payload, ensure_ascii=False))

    def test_stream_chat_excludes_active_image_over_provider_payload_cap(self) -> None:
        observed: dict[str, object] = {"injected": [], "excluded": [], "events": []}
        conversation = {
            "id": "conv-active-image-large-lot2",
            "created_at": "2026-05-19T10:00:00Z",
            "messages": [{"role": "system", "content": "BACKEND SYSTEM PROMPT"}],
        }
        active_image = {
            "document_id": "image-doc-large",
            "conversation_id": conversation["id"],
            "filename": "large-capture.png",
            "media_type": "image/png",
            "source_extension": "png",
            "byte_size": len(b"large-image-bytes"),
            "text_chars": 0,
            "text_sha256_12": "",
            "media_kind": "image",
            "content_sha256_12": "abcdef123456",
            "image_width": 4096,
            "image_height": 4096,
            "token_estimate": 0,
            "status": "active",
            "active": True,
            "created_at": "2026-05-19T10:00:00Z",
            "image_content": b"large-image-bytes",
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter="\n"):
                yield 'data: {"id":"gen-no-image","model":"anthropic/claude-sonnet-4.6","choices":[{"delta":{"content":"Je n\\u0027ai pas vu l\\u0027image."}}]}'
                yield 'data: [DONE]'

        def fake_requests_post(_url, *, json, **kwargs):
            observed["provider_payload"] = dict(json)
            observed["stream"] = kwargs.get("stream")
            return FakeStreamResponse()

        observed_state, restore_pipeline = server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=fake_requests_post,
            runtime_model=MAIN_IMAGE_MODEL,
        )
        original_reader = self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt
        original_injected = self.server.chat_service.active_conversation_documents.record_document_injected
        original_excluded = self.server.chat_service.active_conversation_documents.record_document_excluded
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event
        original_cap = self.server.chat_service.active_document_prompt_lane.ACTIVE_IMAGE_PROVIDER_MAX_BYTES
        self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt = (
            lambda _conversation_id: [active_image]
        )
        self.server.chat_service.active_conversation_documents.record_document_injected = (
            lambda conversation_id, document_id, *, turn_id: observed["injected"].append(
                (conversation_id, document_id, turn_id)
            )
            or True
        )
        self.server.chat_service.active_conversation_documents.record_document_excluded = (
            lambda conversation_id, document_id, *, turn_id, reason_code: observed["excluded"].append(
                (conversation_id, document_id, turn_id, reason_code)
            )
            or True
        )
        self.server.chat_turn_logger.log_store.insert_chat_log_event = (
            lambda event: observed["events"].append(dict(event)) or True
        )
        self.server.chat_service.active_document_prompt_lane.ACTIVE_IMAGE_PROVIDER_MAX_BYTES = 4
        try:
            response = self.client.post(
                "/api/chat",
                json={"message": "Lis cette capture.", "stream": True},
                buffered=True,
            )
        finally:
            self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt = original_reader
            self.server.chat_service.active_conversation_documents.record_document_injected = original_injected
            self.server.chat_service.active_conversation_documents.record_document_excluded = original_excluded
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            self.server.chat_service.active_document_prompt_lane.ACTIVE_IMAGE_PROVIDER_MAX_BYTES = original_cap
            restore_pipeline()

        text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(text, "Je n'ai pas vu l'image.")
        self.assertEqual(terminal["event"], "done")
        self.assertTrue(observed["stream"])
        self.assertEqual(observed["injected"], [])
        self.assertEqual(len(observed["excluded"]), 1)
        excluded = observed["excluded"][0]
        self.assertEqual(excluded[0], conversation["id"])
        self.assertEqual(excluded[1], "image-doc-large")
        self.assertTrue(str(excluded[2]).startswith("turn-"))
        self.assertEqual(excluded[3], "image_too_large_for_provider_payload")

        provider_payload_json = json.dumps(observed["provider_payload"], ensure_ascii=False)
        self.assertNotIn("data:image", provider_payload_json)
        self.assertNotIn("image_url", provider_payload_json)
        self.assertFalse(any(isinstance(message.get("content"), list) for message in observed_state["payload_messages"]))
        persisted = json.dumps(conversation["messages"], ensure_ascii=False)
        trace_payload = json.dumps(observed_state["save_new_traces_calls"], ensure_ascii=False)
        for payload in (persisted, trace_payload):
            self.assertNotIn("data:image", payload)
            self.assertNotIn("image_url", payload)
            self.assertNotIn("image_content", payload)
            self.assertNotIn("binary_content", payload)

        active_events = [event for event in observed["events"] if event["stage"] == "active_documents"]
        self.assertEqual(len(active_events), 1)
        document = active_events[0]["payload_json"]["documents"][0]
        self.assertEqual(document["decision"], "excluded")
        self.assertEqual(document["reason_code"], "image_too_large_for_provider_payload")
        self.assertEqual(document["media_kind"], "image")
        self.assertEqual(document["byte_size"], len(b"large-image-bytes"))
        self.assertEqual(document["image_width"], 4096)
        self.assertEqual(document["image_height"], 4096)
        self.assertEqual(document["provider_model"], MAIN_IMAGE_MODEL)
        self.assertEqual(document["payload_order"], "")
        self.assertNotIn("data:image", json.dumps(active_events[0]["payload_json"], ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
