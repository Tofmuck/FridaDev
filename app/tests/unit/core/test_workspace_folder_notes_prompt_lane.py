from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_notes_prompt_lane


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
NOTE_ID = "33333333-3333-4333-8333-333333333333"


def _read_result(markdown: str = "# Note\n\nContenu utile") -> dict:
    title = "Carnet sensible"
    target = workspace_folder_notes.sanitize_note_target_name(title)
    return {
        "ok": True,
        "reason_code": workspace_folder_notes.REASON_READ_OK,
        "status": 200,
        "note": {
            "note_v1_user": {
                "note_id": NOTE_ID,
                "note_ref": workspace_folder_notes.note_ref(NOTE_ID),
                "title": title,
            },
            "note_v1_technical": {
                "note_ref": workspace_folder_notes.note_ref(NOTE_ID),
                "folder_ref": workspace_folder_notes.folder_ref(FOLDER_ID),
                "title_hash": workspace_folder_notes.title_hash_for_target(target),
                "etag_present": True,
                "etag_hash": "abcdef123456",
                "status": "available",
                "reason_code": workspace_folder_notes.REASON_READ_OK,
            },
        },
        "note_conversation": {
            "read_state": "ready",
            "reason_code": workspace_folder_notes.REASON_READ_OK,
            "note_ref": workspace_folder_notes.note_ref(NOTE_ID),
            "folder_ref": workspace_folder_notes.folder_ref(FOLDER_ID),
            "markdown_char_count": len(markdown),
            "markdown_content": markdown,
            "injection_scope": "current_turn_only",
            "memory_rag_identity_summary": "not_used",
        },
        "note_nextcloud": {
            "read_state": "ready",
            "reason_code": workspace_folder_notes.REASON_READ_OK,
            "etag_hash": "abcdef123456",
            "etag_present": True,
        },
    }


class WorkspaceFolderNotesPromptLaneTests(unittest.TestCase):
    def test_prompt_lane_injects_markdown_only_in_content_message(self) -> None:
        markdown = "# Note\n\nContenu utile"
        messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "Lis la note"}]

        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            messages,
            [_read_result(markdown)],
            requested_count=1,
        )

        self.assertEqual(lane.injected_count, 1)
        self.assertEqual(messages[1]["role"], "system")
        self.assertEqual(messages[2]["role"], "user")
        self.assertIn(markdown, messages[2]["content"])
        self.assertNotIn(markdown, messages[1]["content"])
        technical_payload = lane.as_content_free_dict()
        self.assertNotIn(markdown, str(technical_payload))
        self.assertNotIn("Carnet sensible", str(technical_payload))
        self.assertNotIn("abcdef123456", messages[1]["content"])

    def test_prompt_lane_keeps_failed_read_content_free(self) -> None:
        failed = {
            "ok": False,
            "reason_code": workspace_folder_notes.REASON_TOO_LARGE,
            "status": 413,
            "note": {},
            "note_conversation": {
                "read_state": "too_large",
                "reason_code": workspace_folder_notes.REASON_TOO_LARGE,
                "markdown_char_count": 0,
                "injection_scope": "none",
                "memory_rag_identity_summary": "not_used",
            },
            "note_nextcloud": {
                "read_state": "too_large",
                "reason_code": workspace_folder_notes.REASON_TOO_LARGE,
                "etag_present": False,
            },
        }

        messages = [{"role": "user", "content": "Lis la note"}]
        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            messages,
            [failed],
            requested_count=1,
        )

        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn(workspace_folder_notes.REASON_TOO_LARGE, messages[0]["content"])
        self.assertNotIn("markdown_content", str(lane.as_content_free_dict()))


if __name__ == "__main__":
    unittest.main()
