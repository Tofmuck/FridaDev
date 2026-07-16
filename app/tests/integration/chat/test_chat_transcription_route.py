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


class _RouteRequest:
    def __init__(self, *, content_length, content_type='multipart/form-data; boundary=x', files=None, form=None):
        self.content_length = content_length
        self.content_type = content_type
        self._files = files if files is not None else {}
        self._form = form if form is not None else {}
        self.files_accessed = False
        self.form_accessed = False
        self.reject_file_access = False

    @property
    def files(self):
        self.files_accessed = True
        if self.reject_file_access:
            raise AssertionError('request.files must not be accessed after body guard rejection')
        return self._files

    @property
    def form(self):
        self.form_accessed = True
        if self.reject_file_access:
            raise AssertionError('request.form must not be accessed after body guard rejection')
        return self._form


class _SizedFileStorage:
    filename = 'clip.webm'
    mimetype = 'audio/webm'

    def __init__(self, size: int) -> None:
        self.remaining = int(size)
        self.bytes_returned = 0

    def read(self, size: int = -1) -> bytes:
        if self.remaining <= 0:
            return b''
        read_size = self.remaining if size < 0 else min(int(size), self.remaining)
        self.remaining -= read_size
        self.bytes_returned += read_size
        return b'a' * read_size


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

    def _call_route_with_request(self, fake_request, *, transcribe_http_request=None):
        original_request = self.server.request
        original_transcribe = self.server.whisper_transcription_service.transcribe_http_request
        self.server.request = fake_request
        if transcribe_http_request is not None:
            self.server.whisper_transcription_service.transcribe_http_request = transcribe_http_request
        try:
            with self.server.app.app_context():
                response, status = self.server.api_chat_transcribe()
                return response.get_json(), status
        finally:
            self.server.whisper_transcription_service.transcribe_http_request = original_transcribe
            self.server.request = original_request

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
        self.assertRegex(observed['headers'].get('X-Frida-Request-Id', ''), r'^[0-9a-f]{16}$')
        self.assertEqual(observed['timeout'], 30)

    def test_api_chat_transcribe_forwards_large_blob_with_safe_metadata(self) -> None:
        observed = {}
        large_audio = b'a' * (2 * 1024 * 1024)

        def fake_post(url, files=None, data=None, headers=None, timeout=None):
            observed['files'] = dict(files or {})
            observed['timeout'] = timeout
            return _FakeResponse(status_code=200, payload={'text': 'bonjour'})

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={
                    'recording_duration_ms': '150000',
                    'recording_blob_size_bytes': str(len(large_audio)),
                    'recording_chunk_count': '1',
                    'recording_stop_reason': 'auto_limit',
                    'file': (io.BytesIO(large_audio), 'long.webm', 'audio/webm'),
                },
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['input_mode'], 'voice')
        self.assertEqual(len(observed['files']['file'][1]), len(large_audio))
        self.assertEqual(observed['files']['file'][2], 'audio/webm')
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

    def test_declared_body_guard_accepts_exactly_17_mib_and_calls_service(self) -> None:
        fake_request = _RouteRequest(
            content_length=self.server.whisper_transcription_service.MAX_TRANSCRIPTION_REQUEST_BYTES,
        )
        calls = 0

        def fake_transcribe_http_request(**_kwargs):
            nonlocal calls
            calls += 1
            return {'ok': True, 'text': 'bonjour', 'input_mode': 'voice'}, 200

        payload, status = self._call_route_with_request(
            fake_request,
            transcribe_http_request=fake_transcribe_http_request,
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(calls, 1)
        self.assertTrue(fake_request.files_accessed)
        self.assertTrue(fake_request.form_accessed)

    def test_declared_body_guard_rejects_17_mib_plus_one_before_multipart_access(self) -> None:
        fake_request = _RouteRequest(
            content_length=self.server.whisper_transcription_service.MAX_TRANSCRIPTION_REQUEST_BYTES + 1,
        )
        fake_request.reject_file_access = True

        payload, status = self._call_route_with_request(
            fake_request,
            transcribe_http_request=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError('service must not be called after body guard rejection')
            ),
        )

        self.assertEqual(status, 413)
        self.assertEqual(
            payload,
            {
                'ok': False,
                'error': 'requete audio trop volumineuse',
                'reason_code': 'audio_request_too_large',
            },
        )
        self.assertFalse(fake_request.files_accessed)
        self.assertFalse(fake_request.form_accessed)

    def test_missing_or_invalid_content_length_still_uses_real_file_limit(self) -> None:
        for content_length in (None, 'invalid', 1):
            with self.subTest(content_length=content_length):
                file_storage = _SizedFileStorage(
                    self.server.whisper_transcription_service.MAX_AUDIO_FILE_BYTES + 1
                )
                fake_request = _RouteRequest(
                    content_length=content_length,
                    files={'file': file_storage},
                    form={'recording_blob_size_bytes': '1'},
                )
                original_post = self.server.requests.post
                self.server.requests.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('Whisper must not be called for oversized audio')
                )
                try:
                    payload, status = self._call_route_with_request(fake_request)
                finally:
                    self.server.requests.post = original_post

                self.assertEqual(status, 413)
                self.assertEqual(payload['reason_code'], 'audio_file_too_large')
                self.assertEqual(
                    file_storage.bytes_returned,
                    self.server.whisper_transcription_service.MAX_AUDIO_FILE_BYTES + 1,
                )

    def test_api_chat_transcribe_preserves_allowlisted_whisper_rejection(self) -> None:
        def fake_post(*_args, **_kwargs):
            return _FakeResponse(
                status_code=422,
                payload={'detail': {'reason': 'audio_duration_too_long'}},
                text='must not escape',
            )

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={'file': (io.BytesIO(b'audio-bytes'), 'clip.webm', 'audio/webm')},
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'duree audio trop longue',
                'reason_code': 'audio_duration_too_long',
            },
        )
        self.assertNotIn('must not escape', response.get_data(as_text=True))

    def test_api_chat_transcribe_keeps_unknown_whisper_rejection_generic(self) -> None:
        def fake_post(*_args, **_kwargs):
            return _FakeResponse(
                status_code=422,
                payload={
                    'detail': {
                        'reason': 'audio_duration_too_long',
                        'message': 'must not escape',
                    }
                },
                text='must not escape',
            )

        restore = self._patch_runtime(fake_post)
        try:
            response = self.client.post(
                '/api/chat/transcribe',
                data={'file': (io.BytesIO(b'audio-bytes'), 'clip.webm', 'audio/webm')},
                content_type='multipart/form-data',
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'transcription indisponible'},
        )
        self.assertNotIn('must not escape', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
