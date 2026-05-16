from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from core import active_document_prompt_lane as prompt_lane
from core import chat_service
from observability import active_documents_observability


CONV_ID = "11111111-1111-1111-1111-111111111111"
DOC_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RAW_DOCUMENT_TEXT = "CONTENU DOCUMENTAIRE EXACT QUI NE DOIT PAS SORTIR DANS LES PREUVES"


def _document(*, document_id: str = DOC_ID, text: str = RAW_DOCUMENT_TEXT) -> dict[str, object]:
    return {
        "document_id": document_id,
        "conversation_id": CONV_ID,
        "filename": "note-active.txt",
        "media_type": "text/plain",
        "source_extension": ".txt",
        "byte_size": len(text.encode("utf-8")),
        "text_chars": len(text),
        "text_sha256_12": "abc123def456",
        "token_estimate": max(1, len(text) // 4),
        "status": "active",
        "active": True,
        "created_at": "2026-05-16T12:00:00Z",
        "deactivated_at": "",
        "last_injected_turn_id": "",
        "last_excluded_turn_id": "",
        "last_excluded_reason_code": "",
        "source": "active_conversation_documents",
        "text_content": text,
    }


class _FakeActiveDocuments:
    def __init__(self, documents: list[dict[str, object]]):
        self.documents = {str(item["document_id"]): dict(item) for item in documents}
        self.injected_records: list[tuple[str, str, str]] = []
        self.excluded_records: list[tuple[str, str, str, str]] = []

    def list_active_documents_for_prompt(self, conversation_id: str):
        return [
            dict(item)
            for item in self.documents.values()
            if item.get("conversation_id") == conversation_id
            and item.get("status") == "active"
            and not item.get("deactivated_at")
        ]

    def record_document_injected(self, conversation_id: str, document_id: str, *, turn_id: str) -> bool:
        item = self.documents.get(document_id)
        if not item or item.get("conversation_id") != conversation_id or item.get("status") != "active":
            return False
        item["last_injected_turn_id"] = turn_id
        item["last_excluded_turn_id"] = ""
        item["last_excluded_reason_code"] = ""
        self.injected_records.append((conversation_id, document_id, turn_id))
        return True

    def record_document_excluded(
        self,
        conversation_id: str,
        document_id: str,
        *,
        turn_id: str,
        reason_code: str,
    ) -> bool:
        item = self.documents.get(document_id)
        if not item or item.get("conversation_id") != conversation_id or item.get("status") != "active":
            return False
        item["last_excluded_turn_id"] = turn_id
        item["last_excluded_reason_code"] = reason_code
        self.excluded_records.append((conversation_id, document_id, turn_id, reason_code))
        return True

    def deactivate_document(self, conversation_id: str, document_id: str) -> bool:
        item = self.documents.get(document_id)
        if not item or item.get("conversation_id") != conversation_id:
            return False
        item["status"] = "inactive"
        item["deactivated_at"] = "2026-05-16T12:05:00Z"
        item["last_excluded_reason_code"] = "manual_remove"
        return True


def _run_operator_turn(
    active_documents: _FakeActiveDocuments,
    *,
    turn_id: str,
    max_tokens: int = 0,
    token_count: int = 1,
) -> tuple[list[dict[str, object]], object, list[dict[str, object]]]:
    prompt_messages: list[dict[str, object]] = [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "Question du tour"},
    ]
    lane = prompt_lane.inject_active_document_prompt_lane(
        prompt_messages,
        active_documents.list_active_documents_for_prompt(CONV_ID),
        model="model-test",
        count_tokens_func=lambda _messages, _model: token_count,
        max_tokens=max_tokens,
    )
    chat_service._record_active_document_prompt_decisions(
        conversation={"id": CONV_ID},
        lane=lane,
        turn_id=turn_id,
        active_documents_module=active_documents,
        logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
    )
    events: list[dict[str, object]] = []
    active_documents_observability.emit_prompt_decision_event(
        lane,
        chat_turn_logger_module=SimpleNamespace(
            emit=lambda stage, status, payload: events.append(
                {"stage": stage, "status": status, "payload": payload}
            )
            or True
        ),
    )
    return prompt_messages, lane, events


class ActiveDocumentOperatorProofsLot8Test(unittest.TestCase):
    def test_document_is_reinjected_on_two_successive_turns_with_content_free_events(self) -> None:
        active_documents = _FakeActiveDocuments([_document()])

        first_messages, first_lane, first_events = _run_operator_turn(
            active_documents,
            turn_id="turn-1",
        )
        second_messages, second_lane, second_events = _run_operator_turn(
            active_documents,
            turn_id="turn-2",
        )

        self.assertEqual(first_lane.injected_count, 1)
        self.assertEqual(second_lane.injected_count, 1)
        self.assertIn(RAW_DOCUMENT_TEXT, _joined_contents(first_messages))
        self.assertIn(RAW_DOCUMENT_TEXT, _joined_contents(second_messages))
        self.assertEqual(
            active_documents.injected_records,
            [
                (CONV_ID, DOC_ID, "turn-1"),
                (CONV_ID, DOC_ID, "turn-2"),
            ],
        )
        self.assertEqual(active_documents.documents[DOC_ID]["last_injected_turn_id"], "turn-2")
        self.assertNotIn(RAW_DOCUMENT_TEXT, json.dumps(first_events + second_events, ensure_ascii=False))
        self.assertTrue(all(event["stage"] == "active_documents" for event in first_events + second_events))

    def test_manual_remove_makes_following_turn_absent_from_prompt_and_events(self) -> None:
        active_documents = _FakeActiveDocuments([_document()])

        _run_operator_turn(active_documents, turn_id="turn-before-remove")
        self.assertTrue(active_documents.deactivate_document(CONV_ID, DOC_ID))
        after_messages, after_lane, after_events = _run_operator_turn(
            active_documents,
            turn_id="turn-after-remove",
        )

        self.assertEqual(after_lane.injected_count, 0)
        self.assertEqual(after_lane.not_injected_count, 0)
        self.assertNotIn("[DOCUMENTS ACTIFS DE CONVERSATION]", _joined_contents(after_messages))
        self.assertNotIn(RAW_DOCUMENT_TEXT, _joined_contents(after_messages))
        self.assertEqual(after_events, [])
        self.assertEqual(active_documents.documents[DOC_ID]["last_excluded_reason_code"], "manual_remove")

    def test_too_large_document_is_excluded_entirely_and_turn_continues_with_compact_signal(self) -> None:
        active_documents = _FakeActiveDocuments([_document()])

        messages, lane, events = _run_operator_turn(
            active_documents,
            turn_id="turn-too-large",
            max_tokens=10,
            token_count=9999,
        )
        prompt_text = _joined_contents(messages)
        event_text = json.dumps(events, ensure_ascii=False, sort_keys=True)

        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertIn("Question du tour", prompt_text)
        self.assertIn("document_too_large_for_turn", prompt_text)
        self.assertIn("ne pretends jamais l'avoir lu", prompt_text)
        self.assertNotIn(RAW_DOCUMENT_TEXT, prompt_text)
        self.assertEqual(
            active_documents.excluded_records,
            [(CONV_ID, DOC_ID, "turn-too-large", "document_too_large_for_turn")],
        )
        self.assertEqual(events[0]["payload"]["not_injected_count"], 1)
        self.assertEqual(events[0]["payload"]["too_large_count"], 1)
        self.assertNotIn(RAW_DOCUMENT_TEXT, event_text)
        self.assertFalse(events[0]["payload"]["raw_content_included"])


def _joined_contents(messages) -> str:
    return "\n".join(str(message.get("content") or "") for message in messages)


if __name__ == "__main__":
    unittest.main()
