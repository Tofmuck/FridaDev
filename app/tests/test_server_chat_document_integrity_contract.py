from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_stream_control
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


SENTINELS = ("LOT10B-BEGIN-SENTINEL", "LOT10B-MIDDLE-SENTINEL", "LOT10B-END-SENTINEL")
DOCUMENT_TEXT = f"{SENTINELS[0]}\nsynthetic body\n{SENTINELS[1]}\nsynthetic tail\n{SENTINELS[2]}"


class _FakeStreamResponse:
    encoding = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self, decode_unicode=True, delimiter="\n"):
        yield 'data: {"choices":[{"delta":{"content":"Reponse synthetique."}}]}'
        yield "data: [DONE]"


class ServerChatDocumentIntegrityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _document(self, source: str, conversation_id: str) -> dict[str, object]:
        document = {
            "document_id": f"doc-{source}",
            "conversation_id": conversation_id,
            "filename": "synthetic-proof.txt",
            "media_type": "text/plain",
            "source_extension": ".txt",
            "byte_size": len(DOCUMENT_TEXT.encode("utf-8")),
            "text_chars": len(DOCUMENT_TEXT),
            "text_sha256_12": "abc123def456",
            "token_estimate": max(1, len(DOCUMENT_TEXT) // 4),
            "status": "active",
            "active": True,
            "created_at": "2026-07-22T00:00:00Z",
            "text_content": DOCUMENT_TEXT,
            "source": source,
        }
        if source == "workspace_file_selection":
            document.update(
                {
                    "workspace_file_id": "33333333-3333-4333-8333-333333333333",
                    "workspace_folder_id": "22222222-2222-4222-8222-222222222222",
                }
            )
        return document

    def _run_turn(self, *, source: str, max_tokens: int) -> tuple[object, dict[str, object], list[dict]]:
        conversation_id = f"conv-{source}-{max_tokens}"
        conversation = {
            "id": conversation_id,
            "created_at": "2026-07-22T00:00:00Z",
            "workspace_folder_id": "22222222-2222-4222-8222-222222222222"
            if source == "workspace_file_selection"
            else None,
            "messages": [{"role": "system", "content": "BACKEND SYSTEM PROMPT"}],
        }
        provider_calls: list[dict] = []
        events: list[dict] = []

        def fake_requests_post(_url, *, json, **_kwargs):
            provider_calls.append(dict(json))
            return _FakeStreamResponse()

        observed, restore_pipeline = server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=fake_requests_post,
            runtime_model="openai/gpt-5.1",
        )
        original_active_reader = self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt
        original_active_injected = self.server.chat_service.active_conversation_documents.record_document_injected
        original_active_excluded = self.server.chat_service.active_conversation_documents.record_document_excluded
        original_workspace_reader = self.server.workspace_file_selections.list_selected_files_for_prompt
        original_workspace_injected = self.server.workspace_file_selections.record_selection_injected
        original_workspace_excluded = self.server.workspace_file_selections.record_selection_excluded
        original_prompt_limit = self.server.config.ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS
        original_estimator = self.server.token_utils.estimate_tokens
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event
        document = self._document(source, conversation_id)
        self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt = (
            (lambda _conversation_id: [document])
            if source == "active_conversation_documents"
            else (lambda _conversation_id: [])
        )
        self.server.workspace_file_selections.list_selected_files_for_prompt = (
            (lambda _conversation_id: [document])
            if source == "workspace_file_selection"
            else (lambda _conversation_id: [])
        )
        self.server.chat_service.active_conversation_documents.record_document_injected = lambda *_args, **_kwargs: True
        self.server.chat_service.active_conversation_documents.record_document_excluded = lambda *_args, **_kwargs: True
        self.server.workspace_file_selections.record_selection_injected = lambda *_args, **_kwargs: True
        self.server.workspace_file_selections.record_selection_excluded = lambda *_args, **_kwargs: True
        self.server.config.ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS = max_tokens
        self.server.token_utils.estimate_tokens = lambda *_args, **_kwargs: 9999 if max_tokens else 1
        self.server.chat_turn_logger.log_store.insert_chat_log_event = lambda event: events.append(dict(event)) or True
        try:
            response = self.client.post(
                "/api/chat",
                json={"message": "Utilise le document si disponible.", "stream": True},
                buffered=True,
            )
        finally:
            self.server.chat_service.active_conversation_documents.list_active_documents_for_prompt = original_active_reader
            self.server.chat_service.active_conversation_documents.record_document_injected = original_active_injected
            self.server.chat_service.active_conversation_documents.record_document_excluded = original_active_excluded
            self.server.workspace_file_selections.list_selected_files_for_prompt = original_workspace_reader
            self.server.workspace_file_selections.record_selection_injected = original_workspace_injected
            self.server.workspace_file_selections.record_selection_excluded = original_workspace_excluded
            self.server.config.ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS = original_prompt_limit
            self.server.token_utils.estimate_tokens = original_estimator
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore_pipeline()

        main_provider_calls = [payload for payload in provider_calls if payload.get("stream") is True]
        self.assertEqual(len(main_provider_calls), 1)
        observed["provider_payload"] = main_provider_calls[0]
        return response, observed, events

    def test_active_and_workspace_documents_reach_fake_provider_whole_when_injectable(self) -> None:
        for source in ("active_conversation_documents", "workspace_file_selection"):
            with self.subTest(source=source):
                response, observed, events = self._run_turn(source=source, max_tokens=0)
                text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
                provider_payload = json.dumps(observed["provider_payload"], ensure_ascii=False)
                event_payload = json.dumps(events, ensure_ascii=False)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(text, "Reponse synthetique.")
                self.assertEqual(terminal["event"], "done")
                for sentinel in SENTINELS:
                    self.assertIn(sentinel, provider_payload)
                    self.assertNotIn(sentinel, event_payload)
                    self.assertNotIn(sentinel, response.get_data(as_text=True))

    def test_active_and_workspace_exclusion_keeps_model_call_and_sends_no_document_fragment(self) -> None:
        for source in ("active_conversation_documents", "workspace_file_selection"):
            with self.subTest(source=source):
                response, observed, events = self._run_turn(source=source, max_tokens=1)
                text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
                provider_payload = json.dumps(observed["provider_payload"], ensure_ascii=False)
                event_payload = json.dumps(events, ensure_ascii=False)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(text, "Reponse synthetique.")
                self.assertEqual(terminal["event"], "done")
                self.assertIn(
                    "reason_code=workspace_file_too_large"
                    if source == "workspace_file_selection"
                    else "reason_code=document_too_large_for_turn",
                    provider_payload,
                )
                self.assertIn("ne pretends jamais l'avoir lu", provider_payload)
                for sentinel in SENTINELS:
                    self.assertNotIn(sentinel, provider_payload)
                    self.assertNotIn(sentinel, event_payload)
                    self.assertNotIn(sentinel, response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
