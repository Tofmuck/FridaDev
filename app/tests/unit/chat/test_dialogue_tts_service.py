from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests
from urllib3 import exceptions as urllib3_exceptions


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from core import dialogue_tts_service
except ImportError:
    dialogue_tts_service = None


class _StreamingBody:
    def __init__(self, data: bytes, *, error: BaseException | None = None) -> None:
        self._data = bytes(data)
        self._offset = 0
        self._error = error
        self.read_sizes: list[int] = []
        self.bytes_returned = 0

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(int(size))
        if size < 0:
            raise AssertionError("unbounded provider response read")
        if self._error is not None:
            error = self._error
            self._error = None
            raise error
        if self._offset >= len(self._data):
            return b""
        chunk = self._data[self._offset : self._offset + int(size)]
        self._offset += len(chunk)
        self.bytes_returned += len(chunk)
        return chunk


class _StreamingResponse:
    def __init__(
        self,
        data: bytes = b"ID3 synthetic mp3",
        *,
        status_code: int = 200,
        content_type: str = "audio/mpeg",
        content_length: object | None = None,
        read_error: BaseException | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.raw = _StreamingBody(data, error=read_error)
        self.closed = False
        self.close_calls = 0

    @property
    def content(self):
        raise AssertionError("response.content must never be used")

    @property
    def text(self):
        raise AssertionError("provider response text must never be read")

    def json(self):
        raise AssertionError("provider response JSON must never be read")

    def close(self) -> None:
        self.closed = True
        self.close_calls += 1


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

    def or_audio_speech_url(self) -> str:
        return "https://private-url-marker.invalid/api/v1/audio/speech"

    def or_headers_custom(self, *, caller: str, referer: str, title: str) -> dict[str, str]:
        self.attribution_calls.append(
            {"caller": caller, "referer": referer, "title": title}
        )
        return {
            "Authorization": "Bearer private-secret-marker",
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
        self.response = response or _StreamingResponse()
        self.error = error
        self.calls: list[dict[str, object]] = []

    def post(self, url, *, json=None, headers=None, timeout=None, stream=None):
        self.calls.append(
            {
                "url": url,
                "json": dict(json or {}),
                "headers": dict(headers or {}),
                "timeout": timeout,
                "stream": stream,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class DialogueTtsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = self._require_service()
        self.config = SimpleNamespace(
            DIALOGUE_TTS_TIMEOUT_S=60,
            OR_REFERER_DIALOGUE_TTS=(
                "https://fridadev.frida-system.fr/openrouter/dialogue-tts"
            ),
            OR_TITLE_DIALOGUE_TTS="FridaDev / Dialogue TTS",
        )
        self.llm = _FakeLlmClient()
        self.logger = _FakeLogger()

    def _require_service(self):
        self.assertIsNotNone(
            dialogue_tts_service,
            "core.dialogue_tts_service must implement the bounded TTS boundary",
        )
        return dialogue_tts_service

    def _synthesize(self, text="  Bonjour, Tof.  ", *, transport=None):
        effective_transport = transport or _FakeTransport()
        result = self.service.synthesize_dialogue_speech(
            text,
            requests_module=effective_transport,
            config_module=self.config,
            llm_module=self.llm,
            logger_obj=self.logger,
        )
        return result, effective_transport

    def test_success_uses_exact_contract_and_preserves_the_text(self) -> None:
        response = _StreamingResponse(
            b"ID3 exact mp3",
            content_type="audio/mpeg; charset=binary",
            content_length=13,
        )
        result, transport = self._synthesize(
            "  Bonjour, Tof.  ",
            transport=_FakeTransport(response),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.audio_bytes, b"ID3 exact mp3")
        self.assertEqual(result.content_type, "audio/mpeg")
        self.assertEqual(result.reason_code, "dialogue_tts_ok")
        self.assertEqual(result.http_status, 200)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            transport.calls[0],
            {
                "url": "https://private-url-marker.invalid/api/v1/audio/speech",
                "json": {
                    "model": "microsoft/mai-voice-2-flash",
                    "input": "  Bonjour, Tof.  ",
                    "voice": "fr-FR-Soleil:MAI-Voice-2",
                    "response_format": "mp3",
                },
                "headers": {
                    "Authorization": "Bearer private-secret-marker",
                    "Content-Type": "application/json",
                    "HTTP-Referer": (
                        "https://fridadev.frida-system.fr/openrouter/dialogue-tts"
                    ),
                    "X-OpenRouter-Title": "FridaDev / Dialogue TTS",
                    "X-Title": "FridaDev / Dialogue TTS",
                },
                "timeout": 60,
                "stream": True,
            },
        )
        self.assertEqual(
            self.llm.attribution_calls,
            [
                {
                    "caller": "dialogue_tts",
                    "referer": (
                        "https://fridadev.frida-system.fr/openrouter/dialogue-tts"
                    ),
                    "title": "FridaDev / Dialogue TTS",
                }
            ],
        )
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)

    def test_result_equality_includes_audio_while_repr_excludes_it(self) -> None:
        first = self.service.DialogueTtsResult(
            ok=True,
            audio_bytes=b"private-audio-one",
            content_type="audio/mpeg",
            reason_code="dialogue_tts_ok",
            http_status=200,
            duration_ms=1,
        )
        second = self.service.DialogueTtsResult(
            ok=True,
            audio_bytes=b"private-audio-two",
            content_type="audio/mpeg",
            reason_code="dialogue_tts_ok",
            http_status=200,
            duration_ms=1,
        )

        self.assertNotEqual(first, second)
        self.assertNotIn("private-audio-one", repr(first))

    def test_invalid_text_is_rejected_before_transport_without_rewriting(self) -> None:
        cases = (
            (None, "dialogue_tts_text_type_invalid"),
            (123, "dialogue_tts_text_type_invalid"),
            ("", "dialogue_tts_text_empty"),
            (" \t\n ", "dialogue_tts_text_empty"),
            (
                "x" * (self.service.MAX_DIALOGUE_TTS_TEXT_CHARS + 1),
                "dialogue_tts_text_too_large",
            ),
        )

        for text, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result, transport = self._synthesize(text)
                self.assertFalse(result.ok)
                self.assertEqual(result.audio_bytes, b"")
                self.assertEqual(result.content_type, "")
                self.assertEqual(result.reason_code, reason_code)
                self.assertEqual(result.http_status, 422)
                self.assertEqual(transport.calls, [])

    def test_wrong_or_misleading_media_is_a_closed_bad_gateway(self) -> None:
        for media_type in ("application/json", "audio/mpeg-private"):
            with self.subTest(media_type=media_type):
                response = _StreamingResponse(
                    b"private-provider-body",
                    content_type=media_type,
                )
                result, _ = self._synthesize(transport=_FakeTransport(response))

                self.assertFalse(result.ok)
                self.assertEqual(result.reason_code, "dialogue_tts_provider_invalid_media")
                self.assertEqual(result.http_status, 502)
                self.assertEqual(result.audio_bytes, b"")
                self.assertEqual(response.raw.bytes_returned, 0)
                self.assertTrue(response.closed)

    def test_empty_truncated_and_unreadable_audio_are_closed_bad_gateways(self) -> None:
        cases = (
            (_StreamingResponse(b""), "dialogue_tts_provider_audio_empty"),
            (
                _StreamingResponse(b"abc", content_length=4),
                "dialogue_tts_provider_audio_truncated",
            ),
            (
                _StreamingResponse(
                    read_error=OSError("private-unreadable-marker")
                ),
                "dialogue_tts_provider_audio_unreadable",
            ),
        )

        for response, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result, _ = self._synthesize(transport=_FakeTransport(response))
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_code, reason_code)
                self.assertEqual(result.http_status, 502)
                self.assertEqual(result.audio_bytes, b"")
                self.assertTrue(response.closed)

    def test_declared_oversize_is_rejected_without_reading_and_closes(self) -> None:
        response = _StreamingResponse(
            b"private-audio-marker",
            content_length=self.service.MAX_DIALOGUE_TTS_AUDIO_BYTES + 1,
        )

        result, _ = self._synthesize(transport=_FakeTransport(response))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "dialogue_tts_provider_audio_too_large")
        self.assertEqual(result.http_status, 502)
        self.assertEqual(response.raw.read_sizes, [])
        self.assertTrue(response.closed)

    def test_missing_length_is_still_physically_bounded_to_limit_plus_one(self) -> None:
        response = _StreamingResponse(b"abcdefghij")

        with patch.object(self.service, "MAX_DIALOGUE_TTS_AUDIO_BYTES", 4):
            result, _ = self._synthesize(transport=_FakeTransport(response))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "dialogue_tts_provider_audio_too_large")
        self.assertEqual(response.raw.bytes_returned, 5)
        self.assertNotIn(-1, response.raw.read_sizes)
        self.assertTrue(response.closed)

    def test_real_body_at_limit_succeeds_and_limit_plus_one_fails(self) -> None:
        for body, ok in ((b"abcd", True), (b"abcde", False)):
            with self.subTest(body_size=len(body)):
                response = _StreamingResponse(body)
                with patch.object(self.service, "MAX_DIALOGUE_TTS_AUDIO_BYTES", 4):
                    result, _ = self._synthesize(transport=_FakeTransport(response))

                self.assertEqual(result.ok, ok)
                self.assertEqual(result.audio_bytes, body if ok else b"")
                self.assertEqual(
                    result.http_status,
                    200 if ok else 502,
                )
                self.assertTrue(response.closed)

    def test_provider_statuses_have_the_refined_closed_http_classification(self) -> None:
        cases = (
            (400, 502, "dialogue_tts_provider_contract_rejected"),
            (404, 502, "dialogue_tts_provider_contract_rejected"),
            (422, 502, "dialogue_tts_provider_contract_rejected"),
            (401, 503, "dialogue_tts_provider_auth_error"),
            (403, 503, "dialogue_tts_provider_auth_error"),
            (429, 503, "dialogue_tts_provider_rate_limited"),
            (500, 503, "dialogue_tts_provider_unavailable"),
            (502, 503, "dialogue_tts_provider_unavailable"),
            (503, 503, "dialogue_tts_provider_unavailable"),
        )

        for provider_status, http_status, reason_code in cases:
            with self.subTest(provider_status=provider_status):
                response = _StreamingResponse(
                    b"private-provider-error-body",
                    status_code=provider_status,
                    content_type="application/json",
                )
                result, _ = self._synthesize(transport=_FakeTransport(response))

                self.assertFalse(result.ok)
                self.assertEqual(result.reason_code, reason_code)
                self.assertEqual(result.http_status, http_status)
                self.assertEqual(result.audio_bytes, b"")
                self.assertEqual(response.raw.bytes_returned, 0)
                self.assertTrue(response.closed)

    def test_timeout_and_transport_failures_are_closed_unavailable_results(self) -> None:
        cases = (
            (
                requests.exceptions.Timeout("private-timeout-marker"),
                "dialogue_tts_provider_timeout",
            ),
            (
                requests.exceptions.RequestException("private-transport-marker"),
                "dialogue_tts_provider_transport_error",
            ),
        )

        for error, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result, _ = self._synthesize(transport=_FakeTransport(error=error))
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_code, reason_code)
                self.assertEqual(result.http_status, 503)
                self.assertEqual(result.audio_bytes, b"")

    def test_stream_read_urllib3_timeout_is_unavailable(self) -> None:
        private_marker = "private-stream-timeout-marker"
        response = _StreamingResponse(
            read_error=urllib3_exceptions.ReadTimeoutError(
                None,
                "/api/v1/audio/speech",
                private_marker,
            )
        )

        result, _ = self._synthesize(transport=_FakeTransport(response))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "dialogue_tts_provider_timeout")
        self.assertEqual(result.http_status, 503)
        self.assertEqual(result.audio_bytes, b"")
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)
        self.assertNotIn(
            private_marker,
            repr(result) + str(result.to_payload()) + "\n".join(self.logger.lines),
        )

    def test_stream_read_urllib3_protocol_error_is_unavailable(self) -> None:
        private_marker = "private-stream-transport-marker"
        response = _StreamingResponse(
            read_error=urllib3_exceptions.ProtocolError(private_marker)
        )

        result, _ = self._synthesize(transport=_FakeTransport(response))

        self.assertFalse(result.ok)
        self.assertEqual(
            result.reason_code,
            "dialogue_tts_provider_transport_error",
        )
        self.assertEqual(result.http_status, 503)
        self.assertEqual(result.audio_bytes, b"")
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)
        self.assertNotIn(
            private_marker,
            repr(result) + str(result.to_payload()) + "\n".join(self.logger.lines),
        )

    def test_stream_read_control_flow_exceptions_propagate_and_close(self) -> None:
        for error_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(error_type=error_type.__name__):
                response = _StreamingResponse(read_error=error_type())

                with self.assertRaises(error_type):
                    self._synthesize(transport=_FakeTransport(response))

                self.assertTrue(response.closed)
                self.assertEqual(response.close_calls, 1)

    def test_payload_repr_and_logs_never_expose_content_or_provider_details(self) -> None:
        private_text = "private-text-marker"
        response = _StreamingResponse(
            b"private-provider-error-body",
            status_code=400,
            content_type="application/json",
        )

        result, _ = self._synthesize(
            private_text,
            transport=_FakeTransport(response),
        )

        rendered = repr(result) + "\n" + str(result.to_payload()) + "\n" + "\n".join(
            self.logger.lines
        )
        for private_marker in (
            private_text,
            "private-provider-error-body",
            "private-secret-marker",
            "private-url-marker",
        ):
            self.assertNotIn(private_marker, rendered)
        self.assertEqual(
            result.to_payload(),
            {
                "ok": False,
                "reason_code": "dialogue_tts_provider_contract_rejected",
                "duration_ms": result.duration_ms,
            },
        )


if __name__ == "__main__":
    unittest.main()
