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
            {'Authorization': 'Bearer whisper-secret'},
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
            )

        self.assertEqual(ctx.exception.status_code, 504)
        self.assertEqual(ctx.exception.error, 'transcription timeout')


if __name__ == '__main__':
    unittest.main()
