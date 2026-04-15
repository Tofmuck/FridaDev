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


class FrontendWhisperContractTests(unittest.TestCase):
    def test_index_loads_whisper_dictation_assets_in_chat_composer(self) -> None:
        source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="btnMic"', source)
        self.assertIn('class="btn-dictation"', source)
        self.assertIn('id="dictationStatus"', source)
        self.assertIn('<script src="whisper/whisper_dictation.js"></script>', source)

    def test_frontend_chat_wires_dictation_without_touching_api_chat_payload(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        dictation_source = (APP_DIR / "web" / "whisper" / "whisper_dictation.js").read_text(encoding="utf-8")

        self.assertIn('window.FridaWhisperDictation.createWhisperDictation({', app_source)
        self.assertIn('endpoint: "/api/chat/transcribe"', app_source)
        self.assertIn('isBusy: () => chatRequestInFlight,', app_source)
        self.assertIn('message: userText,', app_source)
        self.assertIn('conversation_id: thread ? thread.conversation_id : null,', app_source)
        self.assertIn('stream: true,', app_source)
        self.assertIn('web_search: webSearchEnabled,', app_source)
        self.assertNotIn('input_mode:', app_source)
        self.assertIn('function joinTranscriptToDraft(currentDraft, transcript)', dictation_source)
        self.assertIn('const DEFAULT_ENDPOINT = "/api/chat/transcribe";', dictation_source)


if __name__ == "__main__":
    unittest.main()
