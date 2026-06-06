from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if "psycopg" not in sys.modules:
    psycopg_module = types.ModuleType("psycopg")
    psycopg_rows_module = types.ModuleType("psycopg.rows")
    psycopg_rows_module.dict_row = object()
    psycopg_module.rows = psycopg_rows_module
    sys.modules["psycopg"] = psycopg_module
    sys.modules["psycopg.rows"] = psycopg_rows_module

from core import chat_service


class ChatServiceBiblioRecentDialogueTests(unittest.TestCase):
    def test_recent_dialogue_keeps_read_passages_content_free_meta(self) -> None:
        conversation = {
            "messages": [
                {"role": "user", "content": "previous user turn"},
                {
                    "role": "assistant",
                    "content": "previous assistant turn",
                    "meta": {
                        "source": "biblio_read_passages_response",
                        "reason_code": "biblio_read_passages_response_meta",
                        "biblio_answer_status": "ready",
                        "biblio_render_mode": "read_passages_llm_response",
                        "biblio_query_kind": "read_passages",
                        "biblio_read_passages_mode": "compare_read_passages",
                        "biblio_read_passages_reason_code": "biblio_read_passages_compare_from_conversation",
                        "biblio_read_passages_count": 2,
                        "biblio_read_passages_chars": 128,
                        "biblio_read_passages_hashes": ["aaa111bbb222", "ccc333ddd444"],
                        "biblio_exact_text_rendered": False,
                        "biblio_exact_text_chars": 0,
                        "biblio_exact_text_hash": "",
                        "biblio_final_lock_authorized": False,
                        "biblio_final_lock_reason_code": "read_passages_llm_response_no_exact_lock",
                        "biblio_surface_intro_present": True,
                        "biblio_surface_intro_chars": 18,
                        "biblio_surface_intro_hash": "introhash123",
                        "biblio_surface_outro_present": True,
                        "biblio_surface_outro_chars": 17,
                        "biblio_surface_outro_hash": "outrohash123",
                        "biblio_surface_empty_reason_codes": [],
                        "prompt_raw": "MUST_NOT_COPY",
                        "dialogue_raw": "MUST_NOT_COPY",
                        "payload_raw": "MUST_NOT_COPY",
                        "snippet": "MUST_NOT_COPY",
                        "excerpt_raw": "MUST_NOT_COPY",
                        "title_raw": "MUST_NOT_COPY",
                        "author_raw": "MUST_NOT_COPY",
                        "secret": "MUST_NOT_COPY",
                        "surface_intro": "MUST_NOT_COPY",
                        "surface_outro": "MUST_NOT_COPY",
                    },
                },
                {"role": "user", "content": "current user turn"},
            ]
        }

        recent = chat_service._biblio_recent_dialogue(conversation, "current user turn")
        assistant_turn = [turn for turn in recent if turn["role"] == "assistant"][-1]

        self.assertIn("meta", assistant_turn)
        meta = assistant_turn["meta"]
        self.assertEqual(meta["source"], "biblio_read_passages_response")
        self.assertEqual(meta["biblio_render_mode"], "read_passages_llm_response")
        self.assertEqual(meta["biblio_read_passages_count"], 2)
        self.assertEqual(meta["biblio_read_passages_hashes"], ["aaa111bbb222", "ccc333ddd444"])
        self.assertEqual(meta["biblio_surface_intro_hash"], "introhash123")
        self.assertEqual(meta["biblio_surface_outro_hash"], "outrohash123")
        self.assertFalse(meta["biblio_final_lock_authorized"])

        forbidden_keys = {
            "prompt_raw",
            "dialogue_raw",
            "payload_raw",
            "snippet",
            "excerpt_raw",
            "title_raw",
            "author_raw",
            "secret",
            "surface_intro",
            "surface_outro",
        }
        self.assertTrue(forbidden_keys.isdisjoint(meta))
        self.assertNotIn("MUST_NOT_COPY", repr(meta))

    def test_recent_dialogue_keeps_existing_rendered_answer_meta(self) -> None:
        conversation = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "previous assistant turn",
                    "meta": {
                        "source": "biblio_rendered_answer",
                        "biblio_answer_status": "ready",
                        "biblio_render_mode": "exact_excerpt",
                        "biblio_exact_text_rendered": True,
                        "biblio_exact_text_chars": 42,
                        "biblio_exact_text_hash": "abc123def456",
                    },
                },
                {"role": "user", "content": "current user turn"},
            ]
        }

        recent = chat_service._biblio_recent_dialogue(conversation, "current user turn")
        meta = recent[-1]["meta"]

        self.assertEqual(meta["source"], "biblio_rendered_answer")
        self.assertTrue(meta["biblio_exact_text_rendered"])
        self.assertEqual(meta["biblio_exact_text_hash"], "abc123def456")


if __name__ == "__main__":
    unittest.main()
