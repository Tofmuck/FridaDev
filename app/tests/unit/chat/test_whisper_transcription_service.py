from __future__ import annotations

import io
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

from core import whisper_transcription_service


class _FakeResponse:
    def __init__(self, *, status_code: int, payload, text: str = '') -> None:
        self.status_code = status_code
        self._payload = payload
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


class _SizedFileStorage:
    def __init__(self, size: int, *, filename: str = 'clip.webm', mimetype: str = 'audio/webm') -> None:
        self.filename = filename
        self.mimetype = mimetype
        self.remaining = int(size)
        self.read_sizes: list[int] = []
        self.bytes_returned = 0

    def read(self, size: int = -1) -> bytes:
        requested = int(size)
        self.read_sizes.append(requested)
        if self.remaining <= 0:
            return b''
        read_size = self.remaining if requested < 0 else min(requested, self.remaining)
        self.remaining -= read_size
        self.bytes_returned += read_size
        return b'a' * read_size


class WhisperTranscriptionServiceTests(unittest.TestCase):
    def test_transcribe_upload_calls_whisper_api_with_expected_contract(self) -> None:
        observed = {}

        def fake_post(url, files=None, data=None, headers=None, timeout=None):
            observed['url'] = url
            observed['files'] = dict(files or {})
            observed['data'] = dict(data or {})
            observed['headers'] = dict(headers or {})
            observed['timeout'] = timeout
            return _FakeResponse(status_code=200, payload={'text': 'bonjour'})

        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=requests.exceptions,
        )
        config_module = SimpleNamespace(
            WHISPER_API_URL='http://platform-whisper-api:9001',
            WHISPER_API_TIMEOUT_S=42,
            WHISPER_API_KEY='whisper-secret',
        )

        text = whisper_transcription_service.transcribe_upload(
            whisper_transcription_service.TranscriptionUpload(
                filename='clip.webm',
                content_type='audio/webm',
                data=b'audio-bytes',
            ),
            requests_module=requests_module,
            config_module=config_module,
            logger_obj=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
            request_id='req-test',
        )

        self.assertEqual(text, 'bonjour')
        self.assertEqual(
            observed['url'],
            'http://platform-whisper-api:9001/v1/audio/transcriptions',
        )
        self.assertEqual(observed['files']['file'][0], 'clip.webm')
        self.assertEqual(observed['files']['file'][1], b'audio-bytes')
        self.assertEqual(observed['files']['file'][2], 'audio/webm')
        self.assertEqual(
            observed['data'],
            {
                'model': 'whisper-1',
                'response_format': 'json',
            },
        )
        self.assertEqual(
            observed['headers'],
            {
                'Authorization': 'Bearer whisper-secret',
                'X-Frida-Request-Id': 'req-test',
            },
        )
        self.assertEqual(observed['timeout'], 42)

    def test_transcribe_upload_maps_upstream_http_error_to_502(self) -> None:
        requests_module = SimpleNamespace(
            post=lambda *_args, **_kwargs: _FakeResponse(
                status_code=500,
                payload={'detail': 'backend failed'},
                text='backend failed',
            ),
            exceptions=requests.exceptions,
        )
        config_module = SimpleNamespace(
            WHISPER_API_URL='http://platform-whisper-api:9001',
            WHISPER_API_TIMEOUT_S=42,
            WHISPER_API_KEY='',
        )

        with self.assertRaises(whisper_transcription_service.WhisperTranscriptionServiceError) as ctx:
            whisper_transcription_service.transcribe_upload(
                whisper_transcription_service.TranscriptionUpload(
                    filename='clip.webm',
                    content_type='audio/webm',
                    data=b'audio-bytes',
                ),
                requests_module=requests_module,
                config_module=config_module,
                logger_obj=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
                request_id='req-test',
            )

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.error, 'transcription indisponible')

    def test_transcribe_upload_maps_timeout_to_504(self) -> None:
        def fake_post(*_args, **_kwargs):
            raise requests.exceptions.Timeout('too slow')

        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=requests.exceptions,
        )
        config_module = SimpleNamespace(
            WHISPER_API_URL='http://platform-whisper-api:9001',
            WHISPER_API_TIMEOUT_S=42,
            WHISPER_API_KEY='',
        )

        with self.assertRaises(whisper_transcription_service.WhisperTranscriptionServiceError) as ctx:
            whisper_transcription_service.transcribe_upload(
                whisper_transcription_service.TranscriptionUpload(
                    filename='clip.webm',
                    content_type='audio/webm',
                    data=b'audio-bytes',
                ),
                requests_module=requests_module,
                config_module=config_module,
                logger_obj=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
                request_id='req-test',
            )

        self.assertEqual(ctx.exception.status_code, 504)
        self.assertEqual(ctx.exception.error, 'transcription timeout')

    def test_transcribe_upload_default_timeout_allows_long_dictation_margin(self) -> None:
        observed = {}

        def fake_post(_url, files=None, data=None, headers=None, timeout=None):
            observed['timeout'] = timeout
            return _FakeResponse(status_code=200, payload={'text': 'bonjour'})

        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=requests.exceptions,
        )
        config_module = SimpleNamespace(
            WHISPER_API_URL='http://platform-whisper-api:9001',
            WHISPER_API_KEY='',
        )

        whisper_transcription_service.transcribe_upload(
            whisper_transcription_service.TranscriptionUpload(
                filename='clip.webm',
                content_type='audio/webm',
                data=b'audio-bytes',
            ),
            requests_module=requests_module,
            config_module=config_module,
            logger_obj=_FakeLogger(),
            request_id='req-test',
        )

        self.assertEqual(observed['timeout'], 180)

    def test_transcribe_http_request_logs_content_free_metadata_only(self) -> None:
        observed = {}

        def fake_post(url, files=None, data=None, headers=None, timeout=None):
            observed['file_bytes'] = dict(files or {})['file'][1]
            return _FakeResponse(status_code=200, payload={'text': 'secret transcript'})

        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=requests.exceptions,
        )
        config_module = SimpleNamespace(
            WHISPER_API_URL='http://platform-whisper-api:9001',
            WHISPER_API_TIMEOUT_S=180,
            WHISPER_API_KEY='whisper-secret',
        )
        logger = _FakeLogger()
        stream = io.BytesIO(b'audio-bytes')
        file_storage = SimpleNamespace(
            filename='private-filename.webm',
            mimetype='audio/webm',
            read=stream.read,
        )

        payload, status = whisper_transcription_service.transcribe_http_request(
            content_type='multipart/form-data; boundary=x',
            files={'file': file_storage},
            form={
                'recording_duration_ms': '150000',
                'recording_blob_size_bytes': '11',
                'recording_chunk_count': '1',
                'recording_stop_reason': 'auto_limit',
            },
            requests_module=requests_module,
            config_module=config_module,
            logger_obj=logger,
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload['text'], 'secret transcript')
        self.assertEqual(observed['file_bytes'], b'audio-bytes')
        logs = '\n'.join(logger.lines)
        self.assertIn('upload_bytes=11', logs)
        self.assertRegex(logs, r'request_id=[0-9a-f]{16}')
        self.assertIn('recording_duration_ms=150000', logs)
        self.assertIn('stop_reason=auto_limit', logs)
        self.assertIn('transcript_chars=17', logs)
        self.assertNotIn('audio-bytes', logs)
        self.assertNotIn('secret transcript', logs)
        self.assertNotIn('private-filename', logs)
        self.assertNotIn('whisper-secret', logs)

    def test_transcribe_upload_logs_upstream_status_without_detail_body(self) -> None:
        logger = _FakeLogger()
        requests_module = SimpleNamespace(
            post=lambda *_args, **_kwargs: _FakeResponse(
                status_code=500,
                payload={'detail': 'private upstream detail'},
                text='private upstream detail',
            ),
            exceptions=requests.exceptions,
        )
        config_module = SimpleNamespace(
            WHISPER_API_URL='http://platform-whisper-api:9001',
            WHISPER_API_TIMEOUT_S=180,
            WHISPER_API_KEY='',
        )

        with self.assertRaises(whisper_transcription_service.WhisperTranscriptionServiceError):
            whisper_transcription_service.transcribe_upload(
                whisper_transcription_service.TranscriptionUpload(
                    filename='private.webm',
                    content_type='audio/webm',
                    data=b'audio-bytes',
                ),
                requests_module=requests_module,
                config_module=config_module,
                logger_obj=logger,
                request_id='req-test',
            )

        logs = '\n'.join(logger.lines)
        self.assertIn('whisper_upstream_bad_status request_id=req-test status=500 timeout_s=180', logs)
        self.assertNotIn('private upstream detail', logs)
        self.assertNotIn('audio-bytes', logs)
        self.assertNotIn('private.webm', logs)

    def test_prepare_upload_enforces_real_file_size_boundaries_with_bounded_reads(self) -> None:
        limit = whisper_transcription_service.MAX_AUDIO_FILE_BYTES
        cases = (
            (limit - 1, True),
            (limit, True),
            (limit + 1, False),
        )

        for actual_size, accepted in cases:
            with self.subTest(actual_size=actual_size):
                file_storage = _SizedFileStorage(actual_size)
                if accepted:
                    upload = whisper_transcription_service.prepare_upload(
                        content_type='multipart/form-data; boundary=x',
                        files={'file': file_storage},
                    )
                    self.assertEqual(len(upload.data), actual_size)
                else:
                    with self.assertRaises(
                        whisper_transcription_service.WhisperTranscriptionServiceError
                    ) as ctx:
                        whisper_transcription_service.prepare_upload(
                            content_type='multipart/form-data; boundary=x',
                            files={'file': file_storage},
                        )
                    self.assertEqual(ctx.exception.status_code, 413)
                    self.assertEqual(ctx.exception.reason_code, 'audio_file_too_large')

                self.assertNotIn(-1, file_storage.read_sizes)
                self.assertLessEqual(
                    file_storage.bytes_returned,
                    whisper_transcription_service.MAX_AUDIO_FILE_BYTES + 1,
                )

    def test_oversized_real_file_stops_at_limit_plus_one_without_whisper_call(self) -> None:
        post_calls = 0

        def fake_post(*_args, **_kwargs):
            nonlocal post_calls
            post_calls += 1
            raise AssertionError('Whisper must not be called for oversized audio')

        file_storage = _SizedFileStorage(
            whisper_transcription_service.MAX_AUDIO_FILE_BYTES + 1024 * 1024
        )
        with self.assertRaises(whisper_transcription_service.WhisperTranscriptionServiceError) as ctx:
            whisper_transcription_service.transcribe_http_request(
                content_type='multipart/form-data; boundary=x',
                files={'file': file_storage},
                form={'recording_blob_size_bytes': '1'},
                requests_module=SimpleNamespace(post=fake_post, exceptions=requests.exceptions),
                config_module=SimpleNamespace(
                    WHISPER_API_URL='http://platform-whisper-api:9001',
                    WHISPER_API_TIMEOUT_S=180,
                    WHISPER_API_KEY='',
                ),
                logger_obj=_FakeLogger(),
            )

        self.assertEqual(ctx.exception.status_code, 413)
        self.assertEqual(ctx.exception.reason_code, 'audio_file_too_large')
        self.assertEqual(post_calls, 0)
        self.assertEqual(
            file_storage.bytes_returned,
            whisper_transcription_service.MAX_AUDIO_FILE_BYTES + 1,
        )

    def test_client_blob_size_metadata_never_overrides_real_file_size(self) -> None:
        metadata_values = (None, 'invalid', '1', str(whisper_transcription_service.MAX_AUDIO_FILE_BYTES + 1))

        for metadata_value in metadata_values:
            with self.subTest(metadata_value=metadata_value):
                post_calls = 0

                def fake_post(*_args, **_kwargs):
                    nonlocal post_calls
                    post_calls += 1
                    return _FakeResponse(status_code=200, payload={'text': 'bonjour'})

                form = {}
                if metadata_value is not None:
                    form['recording_blob_size_bytes'] = metadata_value
                payload, status = whisper_transcription_service.transcribe_http_request(
                    content_type='multipart/form-data; boundary=x',
                    files={'file': _SizedFileStorage(11)},
                    form=form,
                    requests_module=SimpleNamespace(post=fake_post, exceptions=requests.exceptions),
                    config_module=SimpleNamespace(
                        WHISPER_API_URL='http://platform-whisper-api:9001',
                        WHISPER_API_TIMEOUT_S=180,
                        WHISPER_API_KEY='',
                    ),
                    logger_obj=_FakeLogger(),
                )

                self.assertEqual(status, 200)
                self.assertEqual(payload['text'], 'bonjour')
                self.assertEqual(post_calls, 1)

    def test_transcribe_upload_maps_allowlisted_whisper_rejections_without_detail_leak(self) -> None:
        cases = (
            (413, 'audio_file_too_large', 'fichier audio trop volumineux'),
            (422, 'audio_duration_unknown', 'duree audio indeterminable'),
            (422, 'audio_duration_too_long', 'duree audio trop longue'),
        )

        for status_code, reason_code, public_error in cases:
            with self.subTest(reason_code=reason_code):
                logger = _FakeLogger()
                response = _FakeResponse(
                    status_code=status_code,
                    payload={'detail': {'reason': reason_code}},
                    text='private upstream detail',
                )
                with self.assertRaises(
                    whisper_transcription_service.WhisperTranscriptionServiceError
                ) as ctx:
                    whisper_transcription_service.transcribe_upload(
                        whisper_transcription_service.TranscriptionUpload(
                            filename='clip.webm',
                            content_type='audio/webm',
                            data=b'audio-bytes',
                        ),
                        requests_module=SimpleNamespace(
                            post=lambda *_args, **_kwargs: response,
                            exceptions=requests.exceptions,
                        ),
                        config_module=SimpleNamespace(
                            WHISPER_API_URL='http://platform-whisper-api:9001',
                            WHISPER_API_TIMEOUT_S=180,
                            WHISPER_API_KEY='',
                        ),
                        logger_obj=logger,
                        request_id='req-test',
                    )

                self.assertEqual(ctx.exception.status_code, status_code)
                self.assertEqual(ctx.exception.error, public_error)
                self.assertEqual(ctx.exception.reason_code, reason_code)
                self.assertEqual(
                    ctx.exception.as_response(),
                    ({'ok': False, 'error': public_error, 'reason_code': reason_code}, status_code),
                )
                logs = '\n'.join(logger.lines)
                self.assertIn(f'reason_code={reason_code}', logs)
                self.assertNotIn('private upstream detail', logs)

    def test_transcribe_upload_keeps_unknown_or_malformed_rejections_generic(self) -> None:
        cases = (
            {'detail': 'private upstream detail'},
            {'detail': {'reason': 'unknown_private_reason', 'message': 'private upstream detail'}},
            {'detail': {'reason': 'audio_duration_too_long', 'message': 'private upstream detail'}},
            ValueError('private upstream detail'),
        )

        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                logger = _FakeLogger()
                with self.assertRaises(
                    whisper_transcription_service.WhisperTranscriptionServiceError
                ) as ctx:
                    whisper_transcription_service.transcribe_upload(
                        whisper_transcription_service.TranscriptionUpload(
                            filename='clip.webm',
                            content_type='audio/webm',
                            data=b'audio-bytes',
                        ),
                        requests_module=SimpleNamespace(
                            post=lambda *_args, **_kwargs: _FakeResponse(
                                status_code=422,
                                payload=payload,
                                text='private upstream detail',
                            ),
                            exceptions=requests.exceptions,
                        ),
                        config_module=SimpleNamespace(
                            WHISPER_API_URL='http://platform-whisper-api:9001',
                            WHISPER_API_TIMEOUT_S=180,
                            WHISPER_API_KEY='',
                        ),
                        logger_obj=logger,
                        request_id='req-test',
                    )

                self.assertEqual(ctx.exception.status_code, 502)
                self.assertEqual(ctx.exception.error, 'transcription indisponible')
                self.assertIsNone(ctx.exception.reason_code)
                self.assertEqual(
                    ctx.exception.as_response(),
                    ({'ok': False, 'error': 'transcription indisponible'}, 502),
                )
                self.assertNotIn('private upstream detail', '\n'.join(logger.lines))


if __name__ == '__main__':
    unittest.main()
