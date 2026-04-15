from __future__ import annotations

import importlib
import io
import sys
import unittest
from pathlib import Path

import requests


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from memory import memory_store


class _FakeResponse:
    def __init__(self, *, status_code: int, payload, text: str = '') -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class ChatTranscriptionRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        original_init_db = memory_store.init_db
        original_init_catalog_db = conv_store.init_catalog_db
        original_init_messages_db = conv_store.init_messages_db
        sys.modules.pop('server', None)
        memory_store.init_db = lambda: None
        conv_store.init_catalog_db = lambda: None
        conv_store.init_messages_db = lambda: None
        try:
            cls.server = importlib.import_module('server')
        finally:
            memory_store.init_db = original_init_db
            conv_store.init_catalog_db = original_init_catalog_db
            conv_store.init_messages_db = original_init_messages_db

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_runtime(self, fake_post):
        originals = []

        def patch_attr(obj, name, value):
            originals.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        patch_attr(self.server.requests, 'post', fake_post)
        patch_attr(self.server.config, 'WHISPER_API_URL', 'http://platform-whisper-api:9001')
        patch_attr(self.server.config, 'WHISPER_API_TIMEOUT_S', 30)
        patch_attr(self.server.config, 'WHISPER_API_KEY', '')

        def restore():
            while originals:
                obj, name, value = originals.pop()
                setattr(obj, name, value)

        return restore

    def test_api_chat_transcribe_success_contract(self) -> None:
        observed = {}

        def fake_post(url, files=None, data=None, headers=None, timeout=None):
            observed['url'] = url
            observed['files'] = dict(files or {})
            observed['data'] = dict(data or {})
            observed['headers'] = dict(headers or {})
            observed['timeout'] = timeout
            return _FakeResponse(status_code=200, payload={'text': 'bonjour'})

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={
                    'file': (io.BytesIO(b'audio-bytes'), 'clip.webm', 'audio/webm'),
                },
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                'ok': True,
                'text': 'bonjour',
                'input_mode': 'voice',
            },
        )
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
        self.assertEqual(observed['headers'], {})
        self.assertEqual(observed['timeout'], 30)

    def test_api_chat_transcribe_returns_400_when_file_is_missing(self) -> None:
        def fake_post(*_args, **_kwargs):
            raise AssertionError('upstream should not be called when file is missing')

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={},
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'file requis',
            },
        )

    def test_api_chat_transcribe_returns_400_when_file_is_empty(self) -> None:
        def fake_post(*_args, **_kwargs):
            raise AssertionError('upstream should not be called when file is empty')

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={
                    'file': (io.BytesIO(b''), 'empty.webm', 'audio/webm'),
                },
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'file vide',
            },
        )

    def test_api_chat_transcribe_maps_upstream_error_to_502(self) -> None:
        def fake_post(*_args, **_kwargs):
            return _FakeResponse(
                status_code=500,
                payload={'detail': 'backend failed'},
                text='backend failed',
            )

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={
                    'file': (io.BytesIO(b'audio-bytes'), 'clip.webm', 'audio/webm'),
                },
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'transcription indisponible',
            },
        )

    def test_api_chat_transcribe_maps_upstream_timeout_to_504(self) -> None:
        def fake_post(*_args, **_kwargs):
            raise requests.exceptions.Timeout('too slow')

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={
                    'file': (io.BytesIO(b'audio-bytes'), 'clip.webm', 'audio/webm'),
                },
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 504)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'transcription timeout',
            },
        )


if __name__ == '__main__':
    unittest.main()
