from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from memory import memory_store
import config


class MemoryStorePhase4EmbeddingTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _db_embedding_view(self):
        return runtime_settings.RuntimeSectionView(
            section='embedding',
            payload=runtime_settings.normalize_stored_payload(
                'embedding',
                {
                    'endpoint': {'value': 'https://embed.override.example', 'origin': 'db'},
                    'model': {'value': 'intfloat/multilingual-e5-small', 'origin': 'db'},
                    'token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                    'dimensions': {'value': 768, 'origin': 'db'},
                    'top_k': {'value': 9, 'origin': 'db'},
                },
            ),
            source='db',
            source_reason='db_row',
        )

    def test_embed_uses_runtime_embedding_settings_and_model(self) -> None:
        observed = {'url': None, 'headers': None, 'json': None}
        original_get_settings = memory_store.runtime_settings.get_embedding_settings
        original_post = memory_store.requests.post
        original_token = config.EMBED_TOKEN

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return [[0.1, 0.2, 0.3]]

        def fake_post(url, headers, json, timeout):
            observed['url'] = url
            observed['headers'] = headers
            observed['json'] = json
            return FakeResponse()

        memory_store.runtime_settings.get_embedding_settings = self._db_embedding_view
        memory_store.requests.post = fake_post
        config.EMBED_TOKEN = 'embed-env-token'
        try:
            vec = memory_store.embed('bonjour', mode='query')
        finally:
            memory_store.runtime_settings.get_embedding_settings = original_get_settings
            memory_store.requests.post = original_post
            config.EMBED_TOKEN = original_token

        self.assertEqual(vec, [0.1, 0.2, 0.3])
        self.assertEqual(observed['url'], 'https://embed.override.example/embed')
        self.assertEqual(observed['headers']['X-Embed-Token'], 'embed-env-token')
        self.assertEqual(observed['json']['model'], 'intfloat/multilingual-e5-small')
        self.assertEqual(observed['json']['inputs'], ['query: bonjour'])

    def test_retrieve_uses_runtime_embedding_top_k_by_default(self) -> None:
        observed = {'limit': None}
        original_get_settings = memory_store.runtime_settings.get_embedding_settings
        original_embed = memory_store.embed
        original_conn = memory_store._conn

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['limit'] = params[2]

            def fetchall(self):
                return []

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

        memory_store.runtime_settings.get_embedding_settings = self._db_embedding_view
        memory_store.embed = lambda query, mode='query': [0.1, 0.2, 0.3]
        memory_store._conn = lambda: FakeConnection()
        try:
            rows = memory_store.retrieve('question')
        finally:
            memory_store.runtime_settings.get_embedding_settings = original_get_settings
            memory_store.embed = original_embed
            memory_store._conn = original_conn

        self.assertEqual(rows, [])
        self.assertEqual(observed['limit'], 9)

    def test_init_db_uses_runtime_embedding_dimensions(self) -> None:
        observed_queries = []
        original_get_settings = memory_store.runtime_settings.get_embedding_settings
        original_conn = memory_store._conn

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed_queries.append(query)

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        memory_store.runtime_settings.get_embedding_settings = self._db_embedding_view
        memory_store._conn = lambda: FakeConnection()
        try:
            memory_store.init_db()
        finally:
            memory_store.runtime_settings.get_embedding_settings = original_get_settings
            memory_store._conn = original_conn

        joined = '\n'.join(observed_queries)
        self.assertIn('embedding       vector(768)', joined)

    def test_embedding_token_requires_env_fallback_while_db_secret_decryption_is_unavailable(self) -> None:
        original_get_settings = memory_store.runtime_settings.get_embedding_settings
        original_token = config.EMBED_TOKEN
        memory_store.runtime_settings.get_embedding_settings = self._db_embedding_view
        config.EMBED_TOKEN = ''
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretRequiredError,
                'runtime secret decryption is not available',
            ):
                memory_store._runtime_embedding_token()
        finally:
            memory_store.runtime_settings.get_embedding_settings = original_get_settings
            config.EMBED_TOKEN = original_token


if __name__ == '__main__':
    unittest.main()
