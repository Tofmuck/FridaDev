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
        file_storage = SimpleNamespace(
            filename='private-filename.webm',
            mimetype='audio/webm',
            read=lambda: b'audio-bytes',
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


if __name__ == '__main__':
    unittest.main()
