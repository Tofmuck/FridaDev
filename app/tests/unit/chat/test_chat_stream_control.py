from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_stream_control


class ChatStreamControlTests(unittest.TestCase):
    def test_build_and_parse_done_terminal_preserves_updated_at(self) -> None:
        chunk = chat_stream_control.build_terminal_chunk(
            "done",
            updated_at="2026-04-15T17:30:00Z",
        )

        self.assertEqual(
            chat_stream_control.parse_terminal_chunk(chunk),
            {
                "event": "done",
                "updated_at": "2026-04-15T17:30:00Z",
            },
        )

    def test_build_and_parse_error_terminal_preserves_error_code_and_updated_at(self) -> None:
        chunk = chat_stream_control.build_terminal_chunk(
            "error",
            error_code="upstream_error",
            updated_at="2026-04-15T17:31:00Z",
        )

        self.assertEqual(
            chat_stream_control.parse_terminal_chunk(chunk),
            {
                "event": "error",
                "error_code": "upstream_error",
                "updated_at": "2026-04-15T17:31:00Z",
            },
        )

    def test_split_text_and_terminal_keeps_visible_text_separate_from_terminal_metadata(self) -> None:
        raw = (
            "Bonjour"
            + chat_stream_control.build_terminal_chunk(
                "done",
                updated_at="2026-04-15T17:32:00Z",
            )
        )

        visible_text, terminal = chat_stream_control.split_text_and_terminal(raw)

        self.assertEqual(visible_text, "Bonjour")
        self.assertEqual(
            terminal,
            {
                "event": "done",
                "updated_at": "2026-04-15T17:32:00Z",
            },
        )


if __name__ == "__main__":
    unittest.main()
