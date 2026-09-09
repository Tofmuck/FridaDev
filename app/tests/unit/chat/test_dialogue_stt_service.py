from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import requests


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import dialogue_stt_service


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = {"text": "bonjour"} if payload is None else payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def info(self, message, *args) -> None:
        self.lines.append(message % args)

    def warning(self, message, *args) -> None:
        self.lines.append(message % args)


class _FakeLlmClient:
    INTERNAL_PROVIDER_CALLER_HEADER = "X-Frida-Caller"

    def __init__(self) -> None:
        self.attribution_calls: list[dict[str, str]] = []

    def or_audio_transcriptions_url(self) -> str:
        return "https://openrouter.example/api/v1/audio/transcriptions"

    def or_headers_custom(self, *, caller: str, referer: str, title: str) -> dict[str, str]:
        self.attribution_calls.append(
            {"caller": caller, "referer": referer, "title": title}
        )
        return {
            "Authorization": "Bearer synthetic-test-key",
            "Content-Type": "application/json",
            self.INTERNAL_PROVIDER_CALLER_HEADER: caller,
            "HTTP-Referer": referer,
            "X-OpenRouter-Title": title,
            "X-Title": title,
        }

    def strip_internal_provider_headers(self, headers) -> dict[str, str]:
        sanitized = dict(headers)
        sanitized.pop(self.INTERNAL_PROVIDER_CALLER_HEADER, None)
        return sanitized


class _FakeTransport:
    exceptions = requests.exceptions

    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response or _FakeResponse()
        self.error = error
        self.calls: list[dict[str, object]] = []

    def post(self, url, *, files=None, data=None, headers=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "files": dict(files or {}),
                "data": dict(data or {}),
                "headers": dict(headers or {}),
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class DialogueSttServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SimpleNamespace(
            DIALOGUE_STT_TIMEOUT_S=65,
            OR_REFERER_DIALOGUE_STT=(
                "https://fridadev.frida-system.fr/openrouter/dialogue-stt"
            ),
            OR_TITLE_DIALOGUE_STT="FridaDev / Dialogue STT",
        )
        self.llm = _FakeLlmClient()
        self.logger = _FakeLogger()

    def _transcribe(self, audio=b"audio-bytes", mime_type="audio/webm", *, transport=None):
        effective_transport = transport or _FakeTransport()
        result = dialogue_stt_service.transcribe_dialogue_audio(
            audio,
            mime_type,
            requests_module=effective_transport,
            config_module=self.config,
            llm_module=self.llm,
            logger_obj=self.logger,
        )
        return result, effective_transport

    def test_success_uses_the_dedicated_exact_openrouter_contract(self) -> None:
        transport = _FakeTransport(
            _FakeResponse(payload={"text": "bonjour", "usage": {"seconds": 1.25}})
        )

        result, _ = self._transcribe(transport=transport)

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "bonjour")
        self.assertEqual(result.reason_code, "dialogue_stt_ok")
        self.assertEqual(result.http_status, 200)
        self.assertGreaterEqual(result.duration_ms, 0)
        self.assertEqual(len(transport.calls), 1)
        call = transport.calls[0]
        self.assertEqual(
            call["url"],
            "https://openrouter.example/api/v1/audio/transcriptions",
        )
        self.assertEqual(
            call["files"],
            {"file": ("audio.webm", b"audio-bytes", "audio/webm")},
        )
        self.assertEqual(
            call["data"],
            {
                "model": "microsoft/mai-transcribe-2",
                "language": "fr",
                "temperature": "0",
                "response_format": "json",
            },
        )
        self.assertEqual(call["timeout"], 65)
        self.assertEqual(
            self.llm.attribution_calls,
            [
                {
                    "caller": "dialogue_stt",
                    "referer": (
                        "https://fridadev.frida-system.fr/openrouter/dialogue-stt"
                    ),
                    "title": "FridaDev / Dialogue STT",
                }
            ],
        )
        self.assertEqual(
            call["headers"],
            {
                "Authorization": "Bearer synthetic-test-key",
                "HTTP-Referer": (
                    "https://fridadev.frida-system.fr/openrouter/dialogue-stt"
                ),
                "X-OpenRouter-Title": "FridaDev / Dialogue STT",
                "X-Title": "FridaDev / Dialogue STT",
            },
        )

    def test_empty_confirmed_transcript_is_a_success(self) -> None:
        result, transport = self._transcribe(
            transport=_FakeTransport(_FakeResponse(payload={"text": ""}))
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "")
        self.assertEqual(result.http_status, 200)
        self.assertEqual(len(transport.calls), 1)

    def test_supported_mime_types_use_canonical_provider_extensions(self) -> None:
        expected = {
            "audio/wav": "audio.wav",
            "audio/mpeg": "audio.mp3",
            "audio/flac": "audio.flac",
            "audio/mp4": "audio.m4a",
            "audio/ogg": "audio.ogg",
            "audio/webm": "audio.webm",
            "audio/aac": "audio.aac",
        }

        for mime_type, filename in expected.items():
            with self.subTest(mime_type=mime_type):
                result, transport = self._transcribe(mime_type=mime_type)
                self.assertTrue(result.ok)
                self.assertEqual(transport.calls[0]["files"]["file"][0], filename)

    def test_empty_audio_is_rejected_before_transport(self) -> None:
        result, transport = self._transcribe(audio=b"")

        self.assertFalse(result.ok)
        self.assertEqual(result.text, "")
        self.assertEqual(result.reason_code, "audio_empty")
        self.assertEqual(result.http_status, 422)
        self.assertEqual(transport.calls, [])

    def test_unsupported_mime_is_rejected_before_transport(self) -> None:
        result, transport = self._transcribe(
            mime_type="application/private-audio-marker"
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "audio_type_unsupported")
        self.assertEqual(result.http_status, 422)
        self.assertEqual(transport.calls, [])
        self.assertNotIn("private-audio-marker", "\n".join(self.logger.lines))

    def test_file_limit_is_enforced_before_transport(self) -> None:
        limit = dialogue_stt_service.MAX_DIALOGUE_STT_FILE_BYTES
        result, transport = self._transcribe(audio=b"a" * (limit + 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "audio_file_too_large")
        self.assertEqual(result.http_status, 422)
        self.assertEqual(transport.calls, [])

    def test_timeout_and_transport_error_are_closed_unavailable_results(self) -> None:
        cases = (
            (requests.exceptions.Timeout("private timeout text"), "provider_timeout"),
            (
                requests.exceptions.RequestException("private transport text"),
                "provider_transport_error",
            ),
        )

        for error, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                self.logger.lines.clear()
                result, transport = self._transcribe(
                    transport=_FakeTransport(error=error)
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.text, "")
                self.assertEqual(result.reason_code, reason_code)
                self.assertEqual(result.http_status, 503)
                self.assertEqual(len(transport.calls), 1)
                logs = "\n".join(self.logger.lines)
                self.assertNotIn(str(error), logs)

    def test_provider_http_errors_are_closed_unavailable_results(self) -> None:
        cases = (
            (401, "provider_auth_error"),
            (403, "provider_auth_error"),
            (429, "provider_rate_limited"),
            (500, "provider_unavailable"),
            (502, "provider_unavailable"),
            (503, "provider_unavailable"),
            (524, "provider_timeout"),
            (529, "provider_unavailable"),
        )

        for status_code, reason_code in cases:
            with self.subTest(status_code=status_code):
                self.logger.lines.clear()
                response = _FakeResponse(
                    status_code=status_code,
                    payload={"error": {"message": "private provider detail"}},
                    text="partial private transcript",
                )
                result, transport = self._transcribe(
                    transport=_FakeTransport(response)
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.text, "")
                self.assertEqual(result.reason_code, reason_code)
                self.assertEqual(result.http_status, 503)
                self.assertEqual(len(transport.calls), 1)
                logs = "\n".join(self.logger.lines)
                self.assertNotIn("private provider detail", logs)
                self.assertNotIn("partial private transcript", logs)

    def test_invalid_provider_responses_are_closed_bad_gateway_results(self) -> None:
        cases = (
            ValueError("private invalid json"),
            ["not", "an", "object"],
            {"usage": {"seconds": 1}},
            {"text": None},
            {"text": 123},
        )

        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                self.logger.lines.clear()
                result, transport = self._transcribe(
                    transport=_FakeTransport(
                        _FakeResponse(
                            payload=payload,
                            text="partial private transcript",
                        )
                    )
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.text, "")
                self.assertEqual(result.reason_code, "provider_invalid_response")
                self.assertEqual(result.http_status, 502)
                self.assertEqual(len(transport.calls), 1)
                logs = "\n".join(self.logger.lines)
                self.assertNotIn("private invalid json", logs)
                self.assertNotIn("partial private transcript", logs)


if __name__ == "__main__":
    unittest.main()
