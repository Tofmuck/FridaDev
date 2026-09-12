from __future__ import annotations

import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

import requests
from werkzeug.datastructures import MultiDict


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = {"text": "bonjour"} if payload is None else payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _StreamingBody:
    def __init__(self, data: bytes) -> None:
        self._data = bytes(data)
        self._offset = 0
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(int(size))
        if size < 0:
            raise AssertionError("unbounded response read")
        chunk = self._data[self._offset : self._offset + int(size)]
        self._offset += len(chunk)
        return chunk


class _StreamingResponse:
    def __init__(
        self,
        data: bytes,
        *,
        status_code: int = 200,
        content_type: str = "audio/mpeg",
    ) -> None:
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.raw = _StreamingBody(data)
        self.closed = False

    @property
    def content(self):
        raise AssertionError("response.content must never be used")

    @property
    def text(self):
        raise AssertionError("provider response text must never be read")

    def close(self) -> None:
        self.closed = True


class _SizedFileStorage:
    def __init__(
        self,
        size: int,
        *,
        filename: str = "clip.webm",
        mimetype: str = "audio/webm",
    ) -> None:
        self.filename = filename
        self.mimetype = mimetype
        self.remaining = int(size)
        self.bytes_returned = 0
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(int(size))
        if self.remaining <= 0:
            return b""
        read_size = self.remaining if size < 0 else min(int(size), self.remaining)
        self.remaining -= read_size
        self.bytes_returned += read_size
        return b"a" * read_size


class _RouteRequest:
    def __init__(
        self,
        *,
        content_length,
        content_type: str = "multipart/form-data; boundary=x",
        files=None,
        form=None,
    ) -> None:
        self.content_length = content_length
        self.content_type = content_type
        self._files = files if files is not None else MultiDict()
        self._form = form if form is not None else MultiDict()
        self.files_accessed = False
        self.form_accessed = False
        self.reject_multipart_access = False

    @property
    def files(self):
        self.files_accessed = True
        if self.reject_multipart_access:
            raise AssertionError("request.files must not be parsed after body rejection")
        return self._files

    @property
    def form(self):
        self.form_accessed = True
        if self.reject_multipart_access:
            raise AssertionError("request.form must not be parsed after body rejection")
        return self._form


class ChatDialogueAudioRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_provider(self, fake_post):
        originals = []

        def patch_attr(obj, name, value):
            originals.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        patch_attr(self.server.requests, "post", fake_post)
        patch_attr(
            self.server.llm,
            "or_audio_transcriptions_url",
            lambda: "https://openrouter.example/api/v1/audio/transcriptions",
        )
        patch_attr(
            self.server.llm,
            "or_headers_custom",
            lambda **_kwargs: {
                "Authorization": "Bearer synthetic-test-key",
                "Content-Type": "application/json",
                self.server.llm.INTERNAL_PROVIDER_CALLER_HEADER: "dialogue_stt",
            },
        )
        patch_attr(
            self.server.config,
            "OR_REFERER_DIALOGUE_STT",
            "https://fridadev.frida-system.fr/openrouter/dialogue-stt",
        )
        patch_attr(self.server.config, "OR_TITLE_DIALOGUE_STT", "FridaDev / Dialogue STT")
        patch_attr(self.server.config, "DIALOGUE_STT_TIMEOUT_S", 65)

        def restore():
            while originals:
                obj, name, value = originals.pop()
                setattr(obj, name, value)

        return restore

    def _call_route_with_request(self, fake_request):
        original_request = self.server.request
        self.server.request = fake_request
        try:
            with self.server.app.app_context():
                response, status = self.server.api_chat_dialogue_transcribe()
                return response.get_json(), status
        finally:
            self.server.request = original_request

    def _assert_dialogue_frontend_speech_contract(self, web_dir: Path) -> None:
        html_source = (web_dir / "index.html").read_text(encoding="utf-8")
        button_match = re.search(
            r'<button\b[^>]*\bid="btnDialogueMode"[^>]*>',
            html_source,
        )
        self.assertIsNotNone(button_match, "Dialogue product button must exist")
        button_tag = button_match.group(0) if button_match else ""
        self.assertNotRegex(
            button_tag,
            r"\bdisabled\b",
            "Dialogue product button must be enabled",
        )

        consumers = []
        for javascript_path in web_dir.rglob("*.js"):
            relative_path = javascript_path.relative_to(web_dir)
            if "vendor" in relative_path.parts:
                continue
            if "/api/chat/dialogue/speech" in javascript_path.read_text(encoding="utf-8"):
                consumers.append(relative_path.as_posix())
        self.assertEqual(
            sorted(consumers),
            ["dialogue/dialogue_audio_client.js"],
            "Dialogue TTS frontend consumer inventory drift",
        )

    def _patch_tts_provider(self, fake_post):
        originals = []
        missing = object()

        def patch_attr(obj, name, value):
            originals.append((obj, name, getattr(obj, name, missing)))
            setattr(obj, name, value)

        patch_attr(self.server.requests, "post", fake_post)
        patch_attr(
            self.server.llm,
            "or_audio_speech_url",
            lambda: "https://openrouter.example/api/v1/audio/speech",
        )
        patch_attr(
            self.server.llm,
            "or_headers_custom",
            lambda **_kwargs: {
                "Authorization": "Bearer synthetic-test-key",
                "Content-Type": "application/json",
                self.server.llm.INTERNAL_PROVIDER_CALLER_HEADER: "dialogue_tts",
            },
        )
        patch_attr(
            self.server.config,
            "OR_REFERER_DIALOGUE_TTS",
            "https://fridadev.frida-system.fr/openrouter/dialogue-tts",
        )
        patch_attr(self.server.config, "OR_TITLE_DIALOGUE_TTS", "FridaDev / Dialogue TTS")
        patch_attr(self.server.config, "DIALOGUE_TTS_TIMEOUT_S", 60)

        def restore():
            while originals:
                obj, name, value = originals.pop()
                if value is missing:
                    delattr(obj, name)
                else:
                    setattr(obj, name, value)

        return restore

    def test_speech_success_returns_only_exact_mp3_bytes_and_no_store(self) -> None:
        observed = {}
        provider_response = _StreamingResponse(b"ID3 exact route mp3")

        def fake_post(url, *, json=None, headers=None, timeout=None, stream=None):
            observed.update(
                url=url,
                json=dict(json or {}),
                headers=dict(headers or {}),
                timeout=timeout,
                stream=stream,
            )
            return provider_response

        restore = self._patch_tts_provider(fake_post)
        try:
            response = self.client.post(
                "/api/chat/dialogue/speech",
                json={"text": "  Texte final canonique.  "},
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"ID3 exact route mp3")
        self.assertEqual(response.content_type, "audio/mpeg")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertEqual(
            observed["json"],
            {
                "model": "microsoft/mai-voice-2-flash",
                "input": "  Texte final canonique.  ",
                "voice": "fr-FR-Soleil:MAI-Voice-2",
                "response_format": "mp3",
            },
        )
        self.assertEqual(observed["timeout"], 60)
        self.assertTrue(observed["stream"])
        self.assertTrue(provider_response.closed)

    def test_speech_accepts_only_the_exact_bounded_text_object(self) -> None:
        cases = (
            (None, "dialogue_tts_text_payload_invalid"),
            ({}, "dialogue_tts_text_field_invalid"),
            ({"text": "ok", "voice": "other"}, "dialogue_tts_text_field_invalid"),
            ({"text": 123}, "dialogue_tts_text_type_invalid"),
            ({"text": ""}, "dialogue_tts_text_empty"),
            ({"text": " \n\t"}, "dialogue_tts_text_empty"),
            ({"text": "x" * 16_001}, "dialogue_tts_text_too_large"),
        )

        for payload, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                if payload is None:
                    response = self.client.post(
                        "/api/chat/dialogue/speech",
                        data=b"not-json",
                        content_type="text/plain",
                    )
                else:
                    response = self.client.post(
                        "/api/chat/dialogue/speech",
                        json=payload,
                    )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.get_json(),
                    {"ok": False, "reason_code": reason_code, "duration_ms": 0},
                )

    def test_global_flask_body_limit_keeps_the_speech_error_contract(self) -> None:
        original_limit = self.server.app.config["MAX_CONTENT_LENGTH"]
        self.server.app.config["MAX_CONTENT_LENGTH"] = 128
        try:
            response = self.client.post(
                "/api/chat/dialogue/speech",
                json={"text": "x" * 256},
            )
        finally:
            self.server.app.config["MAX_CONTENT_LENGTH"] = original_limit

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.get_json(),
            {
                "ok": False,
                "reason_code": "dialogue_tts_text_too_large",
                "duration_ms": 0,
            },
        )

    def test_speech_failure_returns_generic_json_and_never_partial_audio(self) -> None:
        provider_response = _StreamingResponse(
            b"private-provider-error-body",
            status_code=400,
            content_type="application/json",
        )
        restore = self._patch_tts_provider(
            lambda *_args, **_kwargs: provider_response
        )
        try:
            with self.assertLogs("frida.server", level="WARNING") as captured:
                response = self.client.post(
                    "/api/chat/dialogue/speech",
                    json={"text": "private-text-marker"},
                )
        finally:
            restore()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {
                "ok": False,
                "reason_code": "dialogue_tts_provider_contract_rejected",
                "duration_ms": response.get_json()["duration_ms"],
            },
        )
        rendered = response.get_data(as_text=True) + "\n" + "\n".join(captured.output)
        self.assertNotIn("private-text-marker", rendered)
        self.assertNotIn("private-provider-error-body", rendered)
        self.assertNotIn("audio/mpeg", response.content_type)
        self.assertTrue(provider_response.closed)

    def test_stt_remains_json_while_tts_returns_audio_bytes(self) -> None:
        restore_stt = self._patch_provider(
            lambda *_args, **_kwargs: _FakeResponse(payload={"text": "bonjour"})
        )
        try:
            stt_response = self.client.post(
                "/api/chat/dialogue/transcribe",
                data={
                    "audio": (
                        io.BytesIO(b"audio-bytes"),
                        "clip.webm",
                        "audio/webm",
                    )
                },
                content_type="multipart/form-data",
            )
        finally:
            restore_stt()

        restore_tts = self._patch_tts_provider(
            lambda *_args, **_kwargs: _StreamingResponse(b"ID3 mp3")
        )
        try:
            tts_response = self.client.post(
                "/api/chat/dialogue/speech",
                json={"text": "bonjour"},
            )
        finally:
            restore_tts()

        self.assertEqual(stt_response.status_code, 200)
        self.assertTrue(stt_response.is_json)
        self.assertEqual(stt_response.get_json()["text"], "bonjour")
        self.assertEqual(tts_response.status_code, 200)
        self.assertEqual(tts_response.content_type, "audio/mpeg")
        self.assertEqual(tts_response.data, b"ID3 mp3")

    def test_dialogue_frontend_has_active_button_and_single_expected_speech_consumer(self) -> None:
        self._assert_dialogue_frontend_speech_contract(APP_DIR / "web")

    def test_dialogue_frontend_contract_rejects_disabled_missing_or_second_speech_consumer(self) -> None:
        cases = (
            (
                "disabled_button",
                '<button id="btnDialogueMode" disabled></button>',
                {"dialogue/dialogue_audio_client.js": "/api/chat/dialogue/speech"},
                "Dialogue product button must be enabled",
            ),
            (
                "missing_consumer",
                '<button id="btnDialogueMode"></button>',
                {
                    "dialogue/dialogue_audio_client.js": "/api/chat/dialogue/transcribe",
                    "vendor/dialogue-vad/ignored.js": "/api/chat/dialogue/speech",
                },
                "Dialogue TTS frontend consumer inventory drift",
            ),
            (
                "second_consumer",
                '<button id="btnDialogueMode"></button>',
                {
                    "dialogue/dialogue_audio_client.js": "/api/chat/dialogue/speech",
                    "dialogue/second_consumer.js": "/api/chat/dialogue/speech",
                },
                "Dialogue TTS frontend consumer inventory drift",
            ),
        )

        for name, button_html, javascript_files, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                web_dir = Path(temp_dir)
                (web_dir / "index.html").write_text(button_html, encoding="utf-8")
                for relative_path, source in javascript_files.items():
                    javascript_path = web_dir / relative_path
                    javascript_path.parent.mkdir(parents=True, exist_ok=True)
                    javascript_path.write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(AssertionError, expected_error):
                    self._assert_dialogue_frontend_speech_contract(web_dir)

    def test_success_and_empty_transcript_are_confirmed_honestly(self) -> None:
        for transcript in ("bonjour", ""):
            with self.subTest(transcript=transcript):
                observed = {}

                def fake_post(url, *, files=None, data=None, headers=None, timeout=None):
                    observed.update(
                        url=url,
                        files=dict(files or {}),
                        data=dict(data or {}),
                        headers=dict(headers or {}),
                        timeout=timeout,
                    )
                    return _FakeResponse(payload={"text": transcript})

                restore = self._patch_provider(fake_post)
                try:
                    response = self.client.post(
                        "/api/chat/dialogue/transcribe",
                        data={
                            "audio": (
                                io.BytesIO(b"audio-bytes"),
                                "clip.webm",
                                "audio/webm",
                            )
                        },
                        content_type="multipart/form-data",
                    )
                finally:
                    restore()

                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(payload["ok"], True)
                self.assertEqual(payload["text"], transcript)
                self.assertIsInstance(payload["duration_ms"], int)
                self.assertNotIn("reason_code", payload)
                self.assertEqual(
                    observed["url"],
                    "https://openrouter.example/api/v1/audio/transcriptions",
                )
                self.assertEqual(
                    observed["data"],
                    {
                        "model": "microsoft/mai-transcribe-2",
                        "language": "fr",
                        "temperature": "0",
                        "response_format": "json",
                    },
                )
                self.assertEqual(observed["timeout"], 65)
                self.assertEqual(
                    observed["files"],
                    {"file": ("audio.webm", b"audio-bytes", "audio/webm")},
                )
                self.assertNotIn("Content-Type", observed["headers"])
                self.assertNotIn(
                    self.server.llm.INTERNAL_PROVIDER_CALLER_HEADER,
                    observed["headers"],
                )

    def test_missing_multiple_or_unexpected_audio_fields_are_rejected(self) -> None:
        cases = (
            ({}, "audio_missing"),
            ({"other": (io.BytesIO(b"audio"), "clip.webm", "audio/webm")}, "audio_field_invalid"),
            ({"caption": "private text"}, "audio_field_invalid"),
        )

        for data, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                response = self.client.post(
                    "/api/chat/dialogue/transcribe",
                    data=data,
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.get_json(),
                    {"ok": False, "reason_code": reason_code, "duration_ms": 0},
                )

        response = self.client.post(
            "/api/chat/dialogue/transcribe",
            data=MultiDict(
                [
                    ("audio", (io.BytesIO(b"first"), "first.webm", "audio/webm")),
                    ("audio", (io.BytesIO(b"second"), "second.webm", "audio/webm")),
                ]
            ),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["reason_code"], "audio_multiple")

    def test_empty_file_mime_extension_and_mismatch_are_rejected(self) -> None:
        cases = (
            (b"", "empty.webm", "audio/webm", "audio_empty"),
            (b"audio", "clip.webm", "application/octet-stream", "audio_type_unsupported"),
            (b"audio", "clip.txt", "audio/webm", "audio_extension_unsupported"),
            (b"audio", "clip.wav", "audio/webm", "audio_type_mismatch"),
        )

        for data, filename, mime_type, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                response = self.client.post(
                    "/api/chat/dialogue/transcribe",
                    data={"audio": (io.BytesIO(data), filename, mime_type)},
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.get_json()["reason_code"], reason_code)

    def test_file_limit_reads_only_limit_plus_one_and_skips_provider(self) -> None:
        file_storage = _SizedFileStorage(
            self.server.dialogue_stt_service.MAX_DIALOGUE_STT_FILE_BYTES + 1024 * 1024
        )
        fake_request = _RouteRequest(
            content_length=self.server.dialogue_stt_service.MAX_DIALOGUE_STT_REQUEST_BYTES,
            files=MultiDict([("audio", file_storage)]),
        )

        payload, status = self._call_route_with_request(fake_request)

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "audio_file_too_large")
        self.assertEqual(
            file_storage.bytes_returned,
            self.server.dialogue_stt_service.MAX_DIALOGUE_STT_FILE_BYTES + 1,
        )
        self.assertNotIn(-1, file_storage.read_sizes)

    def test_declared_body_limit_rejects_before_multipart_parsing(self) -> None:
        fake_request = _RouteRequest(
            content_length=(
                self.server.dialogue_stt_service.MAX_DIALOGUE_STT_REQUEST_BYTES + 1
            )
        )
        fake_request.reject_multipart_access = True

        payload, status = self._call_route_with_request(fake_request)

        self.assertEqual(status, 422)
        self.assertEqual(
            payload,
            {"ok": False, "reason_code": "audio_request_too_large", "duration_ms": 0},
        )
        self.assertFalse(fake_request.files_accessed)
        self.assertFalse(fake_request.form_accessed)

    def test_missing_body_size_is_rejected_before_multipart_parsing(self) -> None:
        fake_request = _RouteRequest(content_length=None)
        fake_request.reject_multipart_access = True

        payload, status = self._call_route_with_request(fake_request)

        self.assertEqual(status, 422)
        self.assertEqual(
            payload,
            {"ok": False, "reason_code": "audio_request_size_required", "duration_ms": 0},
        )
        self.assertFalse(fake_request.files_accessed)
        self.assertFalse(fake_request.form_accessed)

    def test_non_multipart_body_is_rejected_without_provider_call(self) -> None:
        response = self.client.post(
            "/api/chat/dialogue/transcribe",
            data=b"private audio bytes",
            content_type="audio/webm",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["reason_code"], "multipart_required")

    def test_global_flask_body_limit_keeps_the_dialogue_error_contract(self) -> None:
        original_limit = self.server.app.config["MAX_CONTENT_LENGTH"]
        self.server.app.config["MAX_CONTENT_LENGTH"] = 128
        try:
            response = self.client.post(
                "/api/chat/dialogue/transcribe",
                data={
                    "audio": (
                        io.BytesIO(b"a" * 256),
                        "clip.webm",
                        "audio/webm",
                    )
                },
                content_type="multipart/form-data",
            )
        finally:
            self.server.app.config["MAX_CONTENT_LENGTH"] = original_limit

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.get_json(),
            {"ok": False, "reason_code": "audio_request_too_large", "duration_ms": 0},
        )

    def test_provider_failures_never_expose_partial_audio_or_raw_error_text(self) -> None:
        cases = (
            (
                _FakeResponse(
                    status_code=500,
                    payload={"error": {"message": "private provider detail"}},
                    text="partial private transcript",
                ),
                503,
                "provider_unavailable",
            ),
            (
                _FakeResponse(
                    payload=ValueError("private invalid json"),
                    text="partial private transcript",
                ),
                502,
                "provider_invalid_response",
            ),
        )

        for provider_response, expected_status, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                restore = self._patch_provider(
                    lambda *_args, **_kwargs: provider_response
                )
                try:
                    with self.assertLogs("frida.server", level="WARNING") as captured:
                        response = self.client.post(
                            "/api/chat/dialogue/transcribe",
                            data={
                                "audio": (
                                    io.BytesIO(b"private audio bytes"),
                                    "clip.webm",
                                    "audio/webm",
                                )
                            },
                            content_type="multipart/form-data",
                        )
                finally:
                    restore()

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(
                    response.get_json()["reason_code"],
                    reason_code,
                )
                rendered = response.get_data(as_text=True) + "\n" + "\n".join(captured.output)
                self.assertNotIn("private audio bytes", rendered)
                self.assertNotIn("private provider detail", rendered)
                self.assertNotIn("private invalid json", rendered)
                self.assertNotIn("partial private transcript", rendered)
                self.assertNotIn('"text"', response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
