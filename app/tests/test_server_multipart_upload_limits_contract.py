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


class _TrackingInput(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        data = super().read(size)
        self.bytes_read += len(data)
        return data

    def readinto(self, buffer) -> int:
        count = super().readinto(buffer)
        self.bytes_read += int(count or 0)
        return count


def _multipart_body(total_size: int) -> tuple[bytes, str]:
    boundary = "lot10b-boundary"
    header = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="proof.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode("ascii")
    footer = f"\r\n--{boundary}--\r\n".encode("ascii")
    payload_size = int(total_size) - len(header) - len(footer)
    if payload_size < 1:
        raise AssertionError("test multipart limit is too small")
    return header + (b"x" * payload_size) + footer, f"multipart/form-data; boundary={boundary}"


class ServerMultipartUploadLimitsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def _route_cases(self):
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
        opened_parts: list[io.BytesIO] = []
        request_class = self.server.app.request_class
        original_stream_factory = request_class._get_file_stream

        def tracked_stream_factory(*_args, **_kwargs):
            part = io.BytesIO()
            opened_parts.append(part)
            return part

        request_class._get_file_stream = tracked_stream_factory
        try:
            response = Response.from_app(self.server.app, environ)
        finally:
            request_class._get_file_stream = original_stream_factory
            for part in opened_parts:
                part.close()
        return response, stream

    def _fake_upload(self, route_name: str, observed: dict[str, object]):
        def fake(*args, **kwargs):
            files = kwargs.get("files") if route_name == "whisper" else args[1]
            file_obj = files.get("file") if hasattr(files, "get") else None
            observed["called"] = True
            observed["file_present"] = file_obj is not None
            if file_obj is None:
                return {"ok": False, "error": "fichier requis"}, 400
            close = getattr(file_obj, "close", None)
            if callable(close):
                close()
            return {"ok": True}, 200

        return fake

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

    def test_wsgi_boundary_accepts_limit_minus_one_and_exact_limit_for_all_multipart_routes(self) -> None:
        limit = 1024
        for route_name, path, module, function_name, _reason_code in self._route_cases():
            for body_size in (limit - 1, limit):
                with self.subTest(route=route_name, body_size=body_size):
                    body, content_type = _multipart_body(body_size)
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
                            content_length=str(body_size),
                            input_terminated=False,
                        )

                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(observed.get("called"))
                    self.assertTrue(observed.get("file_present"))
                    self.assertEqual(stream.bytes_read, body_size)

    def test_wsgi_boundary_rejects_limit_plus_one_with_route_specific_errors(self) -> None:
        limit = 1024
        body, content_type = _multipart_body(limit + 1)
        for route_name, path, module, function_name, reason_code in self._route_cases():
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
        for route_name, path, module, function_name, reason_code in self._route_cases():
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
        for route_name, path, module, function_name, _reason_code in self._route_cases():
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
        for route_name, path, module, function_name, _reason_code in self._route_cases():
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


if __name__ == "__main__":
    unittest.main()
