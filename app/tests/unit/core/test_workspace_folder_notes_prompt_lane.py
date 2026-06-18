from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_notes_prompt_lane


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
NOTE_ID = "33333333-3333-4333-8333-333333333333"
OTHER_NOTE_ID = "44444444-4444-4444-8444-444444444444"


def _read_result(
    markdown: str = "# Note\n\nContenu utile",
    *,
    note_id: str = NOTE_ID,
    title: str = "Carnet sensible",
) -> dict:
    target = workspace_folder_notes.sanitize_note_target_name(title)
    return {
        "ok": True,
        "reason_code": workspace_folder_notes.REASON_READ_OK,
        "status": 200,
        "note": {
            "note_v1_user": {
                "note_id": note_id,
                "note_ref": workspace_folder_notes.note_ref(note_id),
                "title": title,
            },
            "note_v1_technical": {
                "note_ref": workspace_folder_notes.note_ref(note_id),
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
            "note_ref": workspace_folder_notes.note_ref(note_id),
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


class _FakeWorkspaceFolders:
    def get_workspace_folder(self, folder_id, *, include_deleted=False):
        return {
            "id": folder_id,
            "display_name": "Projet",
            "nextcloud_target_name": "Projet",
            "nextcloud_sync_state": "linked",
            "deleted_at": None,
        }


class _FakeNotesRead:
    def __init__(self):
        self.calls = []

    def prepare_workspace_folder_note_for_conversation(self, folder, *, note_id, notes_module):
        self.calls.append(note_id)
        return _read_result(f"# Note {len(self.calls)}", note_id=note_id, title=f"Note {len(self.calls)}")


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

    def test_prompt_lane_injects_only_one_note_per_turn_and_reports_the_rest(self) -> None:
        first = "# Note 1\n\nA injecter"
        second = "# Note 2\n\nNe doit pas etre injectee"
        messages = [{"role": "user", "content": "Lis les notes"}]

        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            messages,
            [
                _read_result(first, note_id=NOTE_ID, title="Note une"),
                _read_result(second, note_id=OTHER_NOTE_ID, title="Note deux"),
            ],
            requested_count=2,
        )

        self.assertEqual(lane.injected_count, 1)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertIn(first, messages[1]["content"])
        self.assertNotIn(second, str(messages))
        self.assertIn(workspace_folder_notes.REASON_TURN_LIMIT_EXCEEDED, messages[0]["content"])
        self.assertNotIn(second, str(lane.as_content_free_dict()))

    def test_prompt_lane_refuses_note_over_global_char_budget_without_truncation(self) -> None:
        oversized = "x" * (workspace_folder_notes_prompt_lane.MAX_NOTES_TOTAL_CHARS_PER_TURN + 1)
        messages = [{"role": "user", "content": "Lis la note"}]

        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            messages,
            [_read_result(oversized)],
            requested_count=1,
        )

        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertIn(workspace_folder_notes.REASON_TURN_LIMIT_EXCEEDED, str(messages))
        self.assertNotIn(oversized, str(messages))
        self.assertNotIn(oversized, str(lane.as_content_free_dict()))

    def test_requested_notes_beyond_read_limit_are_reported_content_free(self) -> None:
        note_ids = [
            "00000000-0000-4000-8000-000000000001",
            "00000000-0000-4000-8000-000000000002",
            "00000000-0000-4000-8000-000000000003",
            "00000000-0000-4000-8000-000000000004",
            "00000000-0000-4000-8000-000000000005",
            "00000000-0000-4000-8000-000000000006",
        ]
        reader = _FakeNotesRead()

        result = workspace_folder_notes_prompt_lane.read_workspace_folder_notes_for_prompt(
            data={"workspace_note_ids": note_ids},
            conversation={"workspace_folder_id": FOLDER_ID},
            workspace_folders_module=_FakeWorkspaceFolders(),
            workspace_folder_notes_module=workspace_folder_notes,
            workspace_folder_notes_read_module=reader,
        )
        messages = [{"role": "user", "content": "Lis les notes"}]
        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            messages,
            result.note_reads,
            read_status=result.status,
            requested_count=result.requested_count,
            invalid_requested_count=result.invalid_requested_count,
            over_limit_count=result.over_limit_count,
        )

        self.assertEqual(
            len(reader.calls),
            workspace_folder_notes_prompt_lane.MAX_NOTES_INJECTED_PER_TURN,
        )
        self.assertEqual(reader.calls, [note_ids[0]])
        self.assertEqual(result.requested_count, 6)
        self.assertEqual(result.over_limit_count, 5)
        self.assertEqual(lane.not_injected_count, 5)
        self.assertIn(workspace_folder_notes.REASON_TURN_LIMIT_EXCEEDED, str(messages))
        self.assertEqual(lane.as_content_free_dict()["over_limit_count"], 5)


if __name__ == "__main__":
    unittest.main()
