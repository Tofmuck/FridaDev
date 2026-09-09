from __future__ import annotations

import io
import sys
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
