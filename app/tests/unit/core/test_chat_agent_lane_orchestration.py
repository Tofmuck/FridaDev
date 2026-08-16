from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core import chat_service


class _FinalLock:
    def __init__(self, source: str, *, ok: bool = True, content: str = "LOCKED") -> None:
        self.source = source
        self.ok = ok
        self.content = content
        self.reason_code = f"{source}_authorized"

    def to_message_meta(self) -> dict[str, object]:
        return {"source": self.source, "locked": True}

    def to_observability(self) -> dict[str, object]:
        return {"source": self.source, "content_free": True}


class ChatAgentLaneOrchestrationTests(unittest.TestCase):
    def test_assistant_output_boundary_preserves_priority_and_biblio_surface(self) -> None:
        self.assertTrue(
            hasattr(chat_service, "resolve_agent_lane_assistant_output"),
            "Lot 9B.2 requires a named agent-lane assistant output boundary",
        )
        resolver = chat_service.resolve_agent_lane_assistant_output
        agenda_lock = _FinalLock("agenda_readonly_response")
        biblio_lock = _FinalLock("biblio_rendered_answer")
        biblio_result = SimpleNamespace(final_response_lock=biblio_lock)
        agenda_result = SimpleNamespace(final_response_lock=agenda_lock)
        validated_result = SimpleNamespace(
            status="ok",
            validated_output={
                "final_judgment_posture": "answer",
                "final_output_regime": "presence",
            },
        )

        with (
            patch.object(
                chat_service.biblio_chat_runtime,
                "final_response_lock_for_result",
                return_value=biblio_lock,
            ),
            patch.object(
                chat_service.agenda_chat_runtime,
                "final_response_lock_for_result",
                return_value=agenda_lock,
            ),
            patch.object(
                chat_service.biblio_chat_runtime,
                "assistant_response_meta_for_result",
                return_value={"source": "biblio_read_passages_response", "content_free": True},
            ),
            patch.object(
                chat_service.biblio_chat_runtime,
                "assistant_response_envelope_for_result",
                return_value={"surface_intro": "INTRO", "surface_outro": "OUTRO"},
            ),
        ):
            resolved = resolver(
                biblio_result=biblio_result,
                agenda_result=agenda_result,
                validated_result=validated_result,
            )

        self.assertEqual(resolved.assistant_response_override.source, "agenda_readonly_response")
        self.assertEqual(
            resolved.assistant_response_meta,
            {"source": "biblio_read_passages_response", "content_free": True},
        )
        self.assertEqual(
            resolved.assistant_response_envelope,
            {"surface_intro": "INTRO", "surface_outro": "OUTRO"},
        )
        self.assertEqual(
            resolver.__module__,
            "core.chat_agent_lane_orchestration",
        )

    def test_invalid_domain_locks_fall_back_to_validated_presence_only(self) -> None:
        self.assertTrue(hasattr(chat_service, "resolve_agent_lane_assistant_output"))
        invalid_biblio = _FinalLock("biblio_rendered_answer", ok=False)
        invalid_agenda = _FinalLock("agenda_readonly_response", content="")
        with (
            patch.object(
                chat_service.biblio_chat_runtime,
                "final_response_lock_for_result",
                return_value=invalid_biblio,
            ),
            patch.object(
                chat_service.agenda_chat_runtime,
                "final_response_lock_for_result",
                return_value=invalid_agenda,
            ),
            patch.object(
                chat_service.biblio_chat_runtime,
                "assistant_response_meta_for_result",
                return_value=None,
            ),
            patch.object(
                chat_service.biblio_chat_runtime,
                "assistant_response_envelope_for_result",
                return_value=None,
            ),
        ):
            resolved = chat_service.resolve_agent_lane_assistant_output(
                biblio_result=SimpleNamespace(final_response_lock=invalid_biblio),
                agenda_result=SimpleNamespace(final_response_lock=invalid_agenda),
                validated_result=SimpleNamespace(
                    status="ok",
                    validated_output={
                        "final_judgment_posture": "answer",
                        "final_output_regime": "presence",
                    },
                ),
            )

        self.assertEqual(resolved.assistant_response_override.source, "hermeneutic_presence")
        self.assertEqual(resolved.assistant_response_override.content, "...")
        self.assertIsNone(resolved.assistant_response_meta)
        self.assertEqual(resolved.assistant_response_envelope, {})

    def test_notes_lane_without_selection_remains_observability_noop(self) -> None:
        states: list[tuple[str, dict[str, object]]] = []
        events: list[tuple[str, dict[str, object]]] = []
        lane = SimpleNamespace(
            as_content_free_dict=lambda: {
                "status": "empty",
                "reason_code": "no_workspace_note_selected",
                "requested_count": 0,
                "invalid_requested_count": 0,
                "injected_count": 0,
            }
        )
        with (
            patch.object(
                chat_service.chat_turn_logger,
                "set_state",
                side_effect=lambda stage, payload: states.append((stage, payload)),
            ),
            patch.object(
                chat_service.chat_turn_logger,
                "emit",
                side_effect=lambda stage, **payload: events.append((stage, payload)),
            ),
        ):
            chat_service._emit_workspace_folder_notes_prompt_observability(lane)

        self.assertEqual(states, [])
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
