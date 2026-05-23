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

    def test_frontend_chat_wires_dictation_transport_into_api_chat_payload(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        dictation_source = (APP_DIR / "web" / "whisper" / "whisper_dictation.js").read_text(encoding="utf-8")
        styles_source = (APP_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('window.FridaWhisperDictation.createWhisperDictation({', app_source)
        self.assertIn('endpoint: "/api/chat/transcribe"', app_source)
        self.assertIn('isBusy: () => chatRequestInFlight,', app_source)
        self.assertIn('let currentDraftInputMode = "keyboard";', app_source)
        self.assertIn('onDraftInputMode: setCurrentDraftInputMode,', app_source)
        self.assertIn('message: userText,', app_source)
        self.assertIn('conversation_id: thread ? thread.conversation_id : null,', app_source)
        self.assertIn('stream: true,', app_source)
        self.assertIn('const adobePayload = adobeModeController ? adobeModeController.getPayload() : {};', app_source)
        self.assertIn('const adobeActive = Boolean(adobePayload.specialization_profile);', app_source)
        self.assertIn('web_search: adobeActive ? false : webSearchEnabled,', app_source)
        self.assertIn('input_mode: inputMode === "voice" ? "voice" : "keyboard",', app_source)
        self.assertIn('...adobePayload,', app_source)
        self.assertIn('function joinTranscriptToDraft(currentDraft, transcript)', dictation_source)
        self.assertIn('const DEFAULT_ENDPOINT = "/api/chat/transcribe";', dictation_source)
        self.assertIn('const DEFAULT_MAX_RECORDING_MS = 150_000;', dictation_source)
        self.assertIn('const MAX_RECORDING_MS_LIMIT = 150_000;', dictation_source)
        self.assertIn('recording_stop_reason', dictation_source)
        self.assertIn('onDraftInputMode("voice");', dictation_source)
        self.assertIn('setStatusMessage(', dictation_source)
        self.assertIn('activeState,', dictation_source)
        self.assertIn('.dictation-status[data-dictation-state="recording"]::after', styles_source)
        self.assertIn('.dictation-status[data-dictation-state="transcribing"]::after', styles_source)
        self.assertIn('@keyframes dictation-dots-wave', styles_source)
        self.assertIn('@media (prefers-reduced-motion: reduce)', styles_source)


if __name__ == "__main__":
    unittest.main()
