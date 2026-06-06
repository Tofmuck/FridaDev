from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import answer_object
from biblio import chat_runtime
from biblio import observability as biblio_observability
from biblio import passage_extractor as extractor
from biblio import prompt_lane
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


BIBLIO_SECRET_PASSAGE = "SYNTHETIC_BIBLIO_SERVER_PASSAGE_MUST_ONLY_ENTER_PROMPT"


class _FakeResponse:
    def __init__(self, text: str = "ok biblio") -> None:
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.text}}]}


def _build_prompt_messages(conversation, *_args, **_kwargs):
    user_messages = [message for message in conversation.get("messages", []) if message.get("role") == "user"]
    user_content = user_messages[-1]["content"] if user_messages else "Question"
    return [
        {"role": "system", "content": conversation["messages"][0]["content"]},
        {"role": "user", "content": user_content},
    ]


class ServerChatBiblioContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_chat_pipeline(self, *, conversation: dict):
        return server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=lambda *_args, **_kwargs: _FakeResponse(),
            build_prompt_messages=_build_prompt_messages,
        )

    def test_biblio_enabled_injects_lane_and_emits_content_free_event(self) -> None:
        observed = {"events": []}
        conversation = {
            "id": "conv-biblio-chat",
            "created_at": "2026-05-29T00:00:00Z",
            "messages": [{"role": "system", "content": "BACKEND SYSTEM PROMPT"}],
        }
        observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        original_biblio_turn = self.server.chat_service.biblio_chat_runtime.run_biblio_chat_turn
        original_emit = self.server.chat_service.chat_turn_logger.emit
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point

        def fake_biblio_turn(data, *, user_msg, config_module, **kwargs):
            observed["biblio_data"] = dict(data)
            observed["biblio_user_msg_chars"] = len(user_msg)
            observed["biblio_kwargs"] = dict(kwargs)
            passage = _passage(BIBLIO_SECRET_PASSAGE)
            lane = prompt_lane.build_biblio_prompt_lane([passage])
            payload = biblio_observability.build_biblio_event_payload(
                enabled=True,
                used=True,
                query_kind=chat_runtime.QUERY_KIND_DOCUMENT_LOCATOR,
                passage_result=passage,
                prompt_lane=lane,
                reason_code=chat_runtime.REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED,
            )
            return chat_runtime.BiblioChatResult(
                enabled=True,
                used=True,
                reason_code=chat_runtime.REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED,
                query_kind=chat_runtime.QUERY_KIND_DOCUMENT_LOCATOR,
                passage_result=passage,
                prompt_lane=lane,
                observability_payload=payload,
            )

        def fake_insertion(**kwargs):
            observed["node_kwargs"] = dict(kwargs)
            return None

        self.server.chat_service.biblio_chat_runtime.run_biblio_chat_turn = fake_biblio_turn
        self.server.chat_service.chat_turn_logger.emit = (
            lambda event, **kwargs: observed["events"].append((event, kwargs))
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "Cherche le passage 126b dans Platon dans le catalogue.",
                    "biblio_enabled": True,
                    "web_search": False,
                },
            )
        finally:
            self.server.chat_service.biblio_chat_runtime.run_biblio_chat_turn = original_biblio_turn
            self.server.chat_service.chat_turn_logger.emit = original_emit
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        self.assertTrue(observed["biblio_data"]["biblio_enabled"])
        self.assertIn("conversation_id", observed["biblio_kwargs"])
        self.assertIn("conversation_state", observed["biblio_kwargs"])
        prompt_text = "\n".join(message["content"] for message in observed_state["payload_messages"])
        self.assertIn(prompt_lane.LANE_HEADER, prompt_text)
        self.assertIn(BIBLIO_SECRET_PASSAGE, prompt_text)
        self.assertNotIn(BIBLIO_SECRET_PASSAGE, str(observed.get("node_kwargs")))

        event_dump = str(observed["events"])
        self.assertIn("biblio", event_dump)
        self.assertIn(chat_runtime.REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED, event_dump)
        self.assertNotIn(BIBLIO_SECRET_PASSAGE, event_dump)
        self.assertNotIn(prompt_lane.LANE_HEADER, event_dump)

    def test_biblio_disabled_has_no_lane(self) -> None:
        conversation = {
            "id": "conv-biblio-disabled",
            "created_at": "2026-05-29T00:00:00Z",
            "messages": [{"role": "system", "content": "BACKEND SYSTEM PROMPT"}],
        }
        observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "Cherche le passage 126b dans Platon dans le catalogue.",
                    "biblio_enabled": False,
                },
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        prompt_text = "\n".join(message["content"] for message in observed_state["payload_messages"])
        self.assertNotIn(prompt_lane.LANE_HEADER, prompt_text)
        self.assertNotIn(BIBLIO_SECRET_PASSAGE, prompt_text)

    def test_biblio_final_response_lock_controls_assistant_message(self) -> None:
        observed = {"events": []}
        final_text = (
            "Source: catalogue_doc=doc-1, page 12.\n\n"
            f"{BIBLIO_SECRET_PASSAGE}\n"
        )
        answer = answer_object.BiblioAnswerObject(
            status=answer_object.STATUS_READY,
            reason_codes=("biblio_context_ready",),
            render_mode=answer_object.RENDER_EXACT_EXCERPT,
            anchors=({"document_id": "doc-1", "page_no": 12, "para_no": 3},),
            exact_text=BIBLIO_SECRET_PASSAGE,
        )
        rendered = answer_object.BiblioRenderedAnswer(
            status=answer_object.STATUS_READY,
            reason_code="biblio_context_ready",
            render_mode=answer_object.RENDER_EXACT_EXCERPT,
            content=final_text,
            exact_text_rendered=True,
            exact_text_chars=len(BIBLIO_SECRET_PASSAGE),
            exact_text_hash=answer.exact_text_hash,
        )
        lock = answer_object.build_final_response_lock(answer, rendered)
        conversation = {
            "id": "conv-biblio-final-lock",
            "created_at": "2026-06-04T00:00:00Z",
            "messages": [{"role": "system", "content": "BACKEND SYSTEM PROMPT"}],
        }
        observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        original_biblio_turn = self.server.chat_service.biblio_chat_runtime.run_biblio_chat_turn
        original_emit = self.server.chat_service.chat_turn_logger.emit
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point

        def fake_biblio_turn(data, *, user_msg, config_module, **kwargs):
            payload = biblio_observability.build_biblio_event_payload(
                enabled=True,
                used=True,
                query_kind=chat_runtime.QUERY_KIND_AGENT_FIRST,
                status="agent_first_executed",
                reason_code="biblio_agent_first_plan_executed",
            )
            payload["answer_object"] = answer.to_observability()
            payload["rendered_answer"] = rendered.to_observability()
            payload["final_response_lock"] = lock.to_observability()
            return chat_runtime.BiblioChatResult(
                enabled=True,
                used=True,
                reason_code="biblio_agent_first_plan_executed",
                query_kind=chat_runtime.QUERY_KIND_AGENT_FIRST,
                observability_payload=payload,
                answer_object=answer,
                rendered_answer=rendered,
                final_response_lock=lock,
            )

        def fake_insertion(**kwargs):
            return None

        self.server.chat_service.biblio_chat_runtime.run_biblio_chat_turn = fake_biblio_turn
        self.server.chat_service.chat_turn_logger.emit = (
            lambda event, **kwargs: observed["events"].append((event, kwargs))
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "Rends le passage exact.",
                    "biblio_enabled": True,
                    "web_search": False,
                },
            )
        finally:
            self.server.chat_service.biblio_chat_runtime.run_biblio_chat_turn = original_biblio_turn
            self.server.chat_service.chat_turn_logger.emit = original_emit
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["text"], final_text)
        self.assertEqual(conversation["messages"][-1]["role"], "assistant")
        self.assertEqual(conversation["messages"][-1]["content"], final_text)
        self.assertEqual(
            conversation["messages"][-1]["meta"]["source"],
            answer_object.FINAL_RESPONSE_SOURCE,
        )
        self.assertNotEqual(payload["text"], "ok biblio")
        event_dump = str(observed["events"])
        self.assertIn("biblio", event_dump)
        self.assertNotIn(BIBLIO_SECRET_PASSAGE, event_dump)


def _passage(passage: str) -> extractor.BiblioPassageResult:
    return extractor.BiblioPassageResult(
        status=extractor.STATUS_EXTRACTED,
        reason_code=extractor.REASON_PASSAGE_EXTRACTED,
        passage=passage,
        doc_id_short="doc-1234",
        passage_chars=len(passage),
        passage_hash="",
        char_offset=0,
        window_chars=700,
        max_passage_chars=4_000,
        excerpt_start=0,
        excerpt_end=len(passage),
        text_length=len(passage),
        page_no=12,
        para_no=3,
        paragraph_id=99,
    )


if __name__ == "__main__":
    unittest.main()
