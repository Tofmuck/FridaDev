from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Response


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


ACTIVE_PATH = "/api/conversations/11111111-1111-1111-1111-111111111111/active-documents"
WORKSPACE_PATH = "/api/workspace-folders/11111111-2222-4333-8444-555555555555/files"
WHISPER_PATH = "/api/chat/transcribe"
DIALOGUE_STT_PATH = "/api/chat/dialogue/transcribe"
DIALOGUE_TTS_PATH = "/api/chat/dialogue/speech"


class _TrackingInput(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.bytes_read = 0
        self.file_parts_opened = 0
        self.file_part_bytes_read: list[int] = []

    def read(self, size: int = -1) -> bytes:
        data = super().read(size)
        self.bytes_read += len(data)
        return data

    def readinto(self, buffer) -> int:
        count = super().readinto(buffer)
        self.bytes_read += int(count or 0)
        return count


class _TrackingPart(io.BytesIO):
    def __init__(self) -> None:
        super().__init__()
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        data = super().read(size)
        self.bytes_read += len(data)
        return data


def _multipart_file_body(
    file_size: int,
    *,
    field_name: str = "file",
    filename: str = "proof.txt",
    mime_type: str = "text/plain",
) -> tuple[bytes, str]:
    boundary = "lot10b-boundary"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; '
        f'filename="{filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("ascii")
    footer = f"\r\n--{boundary}--\r\n".encode("ascii")
    payload_size = int(file_size)
    if payload_size < 0:
        raise AssertionError("test multipart file size must be non-negative")
    return header + (b"x" * payload_size) + footer, f"multipart/form-data; boundary={boundary}"


def _multipart_body(total_size: int) -> tuple[bytes, str]:
    envelope, _content_type = _multipart_file_body(0)
    payload_size = int(total_size) - len(envelope)
    if payload_size < 1:
        raise AssertionError("test multipart limit is too small")
    return _multipart_file_body(payload_size)


def _dialogue_multipart_file_body(file_size: int) -> tuple[bytes, str]:
    return _multipart_file_body(
        file_size,
        field_name="audio",
        filename="proof.webm",
        mime_type="audio/webm",
    )


def _dialogue_multipart_body(total_size: int) -> tuple[bytes, str]:
    envelope, _content_type = _dialogue_multipart_file_body(0)
    payload_size = int(total_size) - len(envelope)
    if payload_size < 1:
        raise AssertionError("test multipart limit is too small")
    return _dialogue_multipart_file_body(payload_size)


class ServerMultipartUploadLimitsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def _legacy_route_cases(self):
        return (
            (
                "active_documents",
                ACTIVE_PATH,
                self.server.active_document_upload_service,
                "upload_active_document_response",
                "active_document_upload_too_large",
            ),
            (
                "workspace_files",
                WORKSPACE_PATH,
                self.server.workspace_files_service,
                "upload_workspace_file_response",
                "folder_document_too_large",
            ),
            (
                "whisper",
                WHISPER_PATH,
                self.server.whisper_transcription_service,
                "transcribe_http_request",
                "audio_request_too_large",
            ),
        )

    def _all_route_cases(self):
        return self._legacy_route_cases() + (
            (
                "dialogue_stt",
                DIALOGUE_STT_PATH,
                self.server.dialogue_stt_service,
                "transcribe_dialogue_audio",
                "audio_request_too_large",
            ),
        )

    def _dispatch(
        self,
        path: str,
        body: bytes,
        content_type: str,
        *,
        content_length: str | None,
        input_terminated: bool,
    ) -> tuple[Response, _TrackingInput]:
        stream = _TrackingInput(body)
        environ = EnvironBuilder(
            path=path,
            method="POST",
            input_stream=stream,
            content_type=content_type,
            content_length=len(body),
        ).get_environ()
        if content_length is None:
            environ.pop("CONTENT_LENGTH", None)
        else:
            environ["CONTENT_LENGTH"] = content_length
        if input_terminated:
            environ["wsgi.input_terminated"] = True
        else:
            environ.pop("wsgi.input_terminated", None)
        opened_parts: list[_TrackingPart] = []
        request_class = self.server.app.request_class
        original_stream_factory = request_class._get_file_stream

        def tracked_stream_factory(*_args, **_kwargs):
            part = _TrackingPart()
            opened_parts.append(part)
            return part

        request_class._get_file_stream = tracked_stream_factory
        try:
            response = Response.from_app(self.server.app, environ)
        finally:
            request_class._get_file_stream = original_stream_factory
            stream.file_parts_opened = len(opened_parts)
            stream.file_part_bytes_read = [
                part.bytes_read for part in opened_parts
            ]
            for part in opened_parts:
                part.close()
        return response, stream

    def _fake_upload(self, route_name: str, observed: dict[str, object]):
        def fake(*args, **kwargs):
            if route_name == "dialogue_stt":
                return self._fake_dialogue_stt(observed)(*args, **kwargs)
            files = kwargs.get("files") if route_name == "whisper" else args[1]
            file_obj = files.get("file") if hasattr(files, "get") else None
            observed["called"] = True
            observed["call_count"] = int(observed.get("call_count", 0)) + 1
            observed["file_present"] = file_obj is not None
            if file_obj is None:
                return {"ok": False, "error": "fichier requis"}, 400
            file_stream = getattr(file_obj, "stream", None)
            getbuffer = getattr(file_stream, "getbuffer", None)
            if callable(getbuffer):
                observed["file_bytes"] = len(getbuffer())
            close = getattr(file_obj, "close", None)
            if callable(close):
                close()
            return {"ok": True}, 200

        return fake

    def _fake_dialogue_stt(self, observed: dict[str, object]):
        def fake(audio_bytes, mime_type, **kwargs):
            observed["called"] = True
            observed["call_count"] = int(observed.get("call_count", 0)) + 1
            observed["file_present"] = bool(audio_bytes)
            observed["file_bytes"] = len(audio_bytes)
            calls = observed.setdefault("calls", [])
            calls.append(
                {
                    "audio_bytes": audio_bytes,
                    "mime_type": mime_type,
                    "requests_module": kwargs.get("requests_module"),
                }
            )
            return self.server.dialogue_stt_service.DialogueSttResult(
                ok=True,
                text="synthetic transcript",
                reason_code="dialogue_stt_ok",
                http_status=200,
                duration_ms=1,
            )

        return fake

    def _patch_dialogue_limits(
        self,
        stack: ExitStack,
        *,
        request_limit: int,
        file_limit: int,
    ) -> None:
        stack.enter_context(
            mock.patch.object(
                self.server.dialogue_stt_service,
                "MAX_DIALOGUE_STT_REQUEST_BYTES",
                request_limit,
            )
        )
        stack.enter_context(
            mock.patch.object(
                self.server.dialogue_stt_service,
                "MAX_DIALOGUE_STT_FILE_BYTES",
                file_limit,
            )
        )

    def _dispatch_dialogue(
        self,
        body: bytes,
        content_type: str,
        *,
        content_length: str | None,
        input_terminated: bool,
        request_limit: int,
        file_limit: int,
    ) -> tuple[Response, _TrackingInput, dict[str, object]]:
        observed: dict[str, object] = {}
        with ExitStack() as stack:
            self._patch_dialogue_limits(
                stack,
                request_limit=request_limit,
                file_limit=file_limit,
            )
            stack.enter_context(
                mock.patch.object(
                    self.server.dialogue_stt_service,
                    "transcribe_dialogue_audio",
                    side_effect=self._fake_dialogue_stt(observed),
                )
            )
            response, stream = self._dispatch(
                DIALOGUE_STT_PATH,
                body,
                content_type,
                content_length=content_length,
                input_terminated=input_terminated,
            )
        return response, stream, observed

    def test_runtime_global_body_limit_is_the_existing_40_mib_contract(self) -> None:
        expected = 40 * 1024 * 1024
        self.assertEqual(self.server.app.config["MAX_CONTENT_LENGTH"], expected)
        self.assertEqual(
            self.server.active_document_upload_service.ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH,
            expected,
        )
        self.assertEqual(
            self.server.workspace_files_service.WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH,
            expected,
        )

    def test_dialogue_tts_wsgi_body_rejection_keeps_closed_json_contract(self) -> None:
        body = json.dumps({"text": "x" * 256}).encode("utf-8")
        with mock.patch.dict(
            self.server.app.config,
            {"MAX_CONTENT_LENGTH": 128},
        ):
            response, stream = self._dispatch(
                DIALOGUE_TTS_PATH,
                body,
                "application/json",
                content_length=str(len(body)),
                input_terminated=False,
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            json.loads(response.get_data(as_text=True)),
            {
                "ok": False,
                "reason_code": "dialogue_tts_text_too_large",
                "duration_ms": 0,
            },
        )
        self.assertEqual(stream.bytes_read, 0)

    def test_wsgi_boundary_accepts_limit_minus_one_and_exact_limit_for_all_multipart_routes(
        self,
    ) -> None:
        limit = 1024
        route_cases = self._all_route_cases()
        self.assertEqual(
            {case[1] for case in route_cases},
            {ACTIVE_PATH, WORKSPACE_PATH, WHISPER_PATH, DIALOGUE_STT_PATH},
        )
        for route_name, path, module, function_name, _reason_code in route_cases:
            for body_size in (limit - 1, limit):
                with self.subTest(route=route_name, body_size=body_size):
                    if route_name == "dialogue_stt":
                        body, content_type = _dialogue_multipart_body(body_size)
                    else:
                        body, content_type = _multipart_body(body_size)
                    observed: dict[str, object] = {}
                    with ExitStack() as stack:
                        stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                        if route_name == "dialogue_stt":
                            self._patch_dialogue_limits(
                                stack,
                                request_limit=limit,
                                file_limit=limit,
                            )
                        stack.enter_context(
                            mock.patch.object(
                                self.server.active_document_upload_service,
                                "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
                                limit,
                            )
                        )
                        stack.enter_context(
                            mock.patch.object(
                                self.server.workspace_files_service,
                                "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
                                limit,
                            )
                        )
                        stack.enter_context(
                            mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                        )
                        response, stream = self._dispatch(
                            path,
                            body,
                            content_type,
                            content_length=str(body_size),
                            input_terminated=False,
                        )

                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(observed.get("called"))
                    self.assertEqual(observed.get("call_count"), 1)
                    self.assertTrue(observed.get("file_present"))
                    self.assertEqual(stream.bytes_read, body_size)

    def test_document_file_equal_to_body_cap_is_rejected_because_multipart_envelope_counts(self) -> None:
        limit = 1024
        file_at_limit_body, content_type = _multipart_file_body(limit)
        body_at_limit, _ = _multipart_body(limit)
        envelope_bytes = len(file_at_limit_body) - limit
        self.assertGreater(envelope_bytes, 0)
        self.assertGreater(len(file_at_limit_body), limit)

        for route_name, path, module, function_name, reason_code in self._legacy_route_cases()[:2]:
            with self.subTest(route=route_name, case="file_at_limit"):
                observed: dict[str, object] = {}
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                    stack.enter_context(
                        mock.patch.object(
                            self.server.active_document_upload_service,
                            "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
                            limit,
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            self.server.workspace_files_service,
                            "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
                            limit,
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                    )
                    response, stream = self._dispatch(
                        path,
                        file_at_limit_body,
                        content_type,
                        content_length=str(len(file_at_limit_body)),
                        input_terminated=False,
                    )

                self.assertEqual(response.status_code, 413)
                self.assertEqual(response.get_json()["reason_code"], reason_code)
                self.assertFalse(observed.get("called", False))
                self.assertEqual(stream.bytes_read, 0)

            with self.subTest(route=route_name, case="body_at_limit"):
                observed = {}
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                    stack.enter_context(
                        mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                    )
                    response, stream = self._dispatch(
                        path,
                        body_at_limit,
                        content_type,
                        content_length=str(limit),
                        input_terminated=False,
                    )

                self.assertEqual(response.status_code, 200)
                self.assertTrue(observed.get("called"))
                self.assertEqual(observed.get("file_bytes"), limit - envelope_bytes)
                self.assertLess(observed["file_bytes"], limit)
                self.assertEqual(stream.bytes_read, limit)

    def test_wsgi_boundary_rejects_limit_plus_one_with_route_specific_errors(self) -> None:
        limit = 1024
        body, content_type = _multipart_body(limit + 1)
        for route_name, path, module, function_name, reason_code in self._legacy_route_cases():
            with self.subTest(route=route_name):
                observed: dict[str, object] = {}
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                    stack.enter_context(
                        mock.patch.object(
                            self.server.active_document_upload_service,
                            "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
                            limit,
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            self.server.workspace_files_service,
                            "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
                            limit,
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                    )
                    response, stream = self._dispatch(
                        path,
                        body,
                        content_type,
                        content_length=str(limit + 1),
                        input_terminated=False,
                    )

                self.assertEqual(response.status_code, 413)
                self.assertEqual(response.get_json()["reason_code"], reason_code)
                self.assertFalse(observed.get("called", False))
                self.assertEqual(stream.bytes_read, 0)

    def test_wsgi_boundary_bounds_absent_invalid_and_negative_lengths(self) -> None:
        limit = 1024
        body, content_type = _multipart_body(limit + 1)
        for route_name, path, module, function_name, reason_code in self._legacy_route_cases():
            for declared_length in (None, "invalid", "-1"):
                with self.subTest(route=route_name, content_length=declared_length):
                    observed: dict[str, object] = {}
                    with ExitStack() as stack:
                        stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                        stack.enter_context(
                            mock.patch.object(
                                self.server.active_document_upload_service,
                                "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
                                limit,
                            )
                        )
                        stack.enter_context(
                            mock.patch.object(
                                self.server.workspace_files_service,
                                "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
                                limit,
                            )
                        )
                        stack.enter_context(
                            mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                        )
                        response, stream = self._dispatch(
                            path,
                            body,
                            content_type,
                            content_length=declared_length,
                            input_terminated=True,
                        )

                    self.assertEqual(response.status_code, 413)
                    self.assertEqual(response.get_json()["reason_code"], reason_code)
                    self.assertFalse(observed.get("called", False))
                    self.assertEqual(stream.bytes_read, limit)

    def test_wsgi_boundary_does_not_consume_body_beyond_a_smaller_declared_length(self) -> None:
        limit = 1024
        body, content_type = _multipart_body(limit + 1)
        declared_length = 256
        for route_name, path, module, function_name, _reason_code in self._legacy_route_cases():
            with self.subTest(route=route_name):
                observed: dict[str, object] = {}
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                    stack.enter_context(
                        mock.patch.object(
                            self.server.active_document_upload_service,
                            "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
                            limit,
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            self.server.workspace_files_service,
                            "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
                            limit,
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                    )
                    response, stream = self._dispatch(
                        path,
                        body,
                        content_type,
                        content_length=str(declared_length),
                        input_terminated=False,
                    )

                self.assertEqual(response.status_code, 400)
                self.assertTrue(observed.get("called"))
                self.assertFalse(observed.get("file_present"))
                self.assertLessEqual(stream.bytes_read, declared_length)
                self.assertLess(stream.bytes_read, len(body))

    def test_wsgi_safe_fallback_consumes_nothing_without_length_or_terminated_signal(self) -> None:
        limit = 1024
        body, content_type = _multipart_body(limit + 1)
        for route_name, path, module, function_name, _reason_code in self._legacy_route_cases():
            with self.subTest(route=route_name):
                observed: dict[str, object] = {}
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(self.server.app.config, {"MAX_CONTENT_LENGTH": limit}))
                    stack.enter_context(
                        mock.patch.object(module, function_name, side_effect=self._fake_upload(route_name, observed))
                    )
                    response, stream = self._dispatch(
                        path,
                        body,
                        content_type,
                        content_length=None,
                        input_terminated=False,
                    )

                self.assertEqual(response.status_code, 400)
                self.assertTrue(observed.get("called"))
                self.assertFalse(observed.get("file_present"))
                self.assertEqual(stream.bytes_read, 0)
                self.assertNotIn("proof.txt", json.dumps(response.get_json(), ensure_ascii=False))

    def test_dialogue_wsgi_accepts_adjacent_and_exact_request_limits_once(self) -> None:
        request_limit = 1024
        for body_size in (request_limit - 1, request_limit):
            with self.subTest(body_size=body_size):
                body, content_type = _dialogue_multipart_body(body_size)
                expected_audio = body.split(b"\r\n\r\n", 1)[1].rsplit(
                    b"\r\n--", 1
                )[0]
                response, stream, observed = self._dispatch_dialogue(
                    body,
                    content_type,
                    content_length=str(body_size),
                    input_terminated=False,
                    request_limit=request_limit,
                    file_limit=request_limit,
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.get_json(),
                    {"ok": True, "text": "synthetic transcript", "duration_ms": 1},
                )
                calls = observed.get("calls", [])
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0]["audio_bytes"], expected_audio)
                self.assertEqual(calls[0]["mime_type"], "audio/webm")
                self.assertIs(calls[0]["requests_module"], self.server.requests)
                self.assertEqual(stream.bytes_read, body_size)
                self.assertEqual(stream.file_parts_opened, 1)
                self.assertEqual(stream.file_part_bytes_read, [len(expected_audio)])

    def test_dialogue_wsgi_rejects_request_limit_plus_one_before_parsing(self) -> None:
        request_limit = 1024
        body, content_type = _dialogue_multipart_body(request_limit + 1)
        response, stream, observed = self._dispatch_dialogue(
            body,
            content_type,
            content_length=str(request_limit + 1),
            input_terminated=False,
            request_limit=request_limit,
            file_limit=request_limit,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["reason_code"], "audio_request_too_large")
        self.assertEqual(observed.get("calls", []), [])
        self.assertEqual(stream.bytes_read, 0)
        self.assertEqual(stream.file_parts_opened, 0)
        self.assertEqual(stream.file_part_bytes_read, [])

    def test_dialogue_wsgi_requires_positive_valid_length_without_reading(self) -> None:
        request_limit = 1024
        body, content_type = _dialogue_multipart_body(512)
        cases = (
            (None, False),
            (None, True),
            ("invalid", False),
            ("-1", False),
            ("0", False),
        )
        for declared_length, input_terminated in cases:
            with self.subTest(
                content_length=declared_length,
                input_terminated=input_terminated,
            ):
                response, stream, observed = self._dispatch_dialogue(
                    body,
                    content_type,
                    content_length=declared_length,
                    input_terminated=input_terminated,
                    request_limit=request_limit,
                    file_limit=request_limit,
                )

                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.get_json()["reason_code"],
                    "audio_request_size_required",
                )
                self.assertEqual(observed.get("calls", []), [])
                self.assertEqual(stream.bytes_read, 0)
                self.assertEqual(stream.file_parts_opened, 0)
                self.assertEqual(stream.file_part_bytes_read, [])

    def test_dialogue_wsgi_does_not_overread_a_shorter_declared_body(self) -> None:
        request_limit = 1024
        body, content_type = _dialogue_multipart_file_body(128)
        declared_length = 64
        response, stream, observed = self._dispatch_dialogue(
            body,
            content_type,
            content_length=str(declared_length),
            input_terminated=False,
            request_limit=request_limit,
            file_limit=request_limit,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["reason_code"], "audio_missing")
        self.assertEqual(observed.get("calls", []), [])
        self.assertLessEqual(stream.bytes_read, declared_length)
        self.assertLess(stream.bytes_read, len(body))
        self.assertEqual(stream.file_parts_opened, 0)

    def test_dialogue_wsgi_file_limit_plus_one_uses_bounded_part_read(self) -> None:
        file_limit = 1024
        body, content_type = _dialogue_multipart_file_body(file_limit + 1)
        response, stream, observed = self._dispatch_dialogue(
            body,
            content_type,
            content_length=str(len(body)),
            input_terminated=False,
            request_limit=len(body),
            file_limit=file_limit,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["reason_code"], "audio_file_too_large")
        self.assertEqual(observed.get("calls", []), [])
        self.assertEqual(stream.bytes_read, len(body))
        self.assertEqual(stream.file_parts_opened, 1)
        self.assertEqual(stream.file_part_bytes_read, [file_limit + 1])


if __name__ == "__main__":
    unittest.main()
