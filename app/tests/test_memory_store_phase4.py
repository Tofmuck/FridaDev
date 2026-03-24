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

    def _db_database_view(self, *, backend: str = 'postgresql'):
        return runtime_settings.RuntimeSectionView(
            section='database',
            payload=runtime_settings.normalize_stored_payload(
                'database',
                {
                    'backend': {'value': backend, 'origin': 'db'},
                    'dsn': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                },
            ),
            source='db',
            source_reason='db_row',
        )

    def test_embed_uses_runtime_embedding_settings_and_model(self) -> None:
        observed = {'url': None, 'headers': None, 'json': None}
        original_get_settings = memory_store.runtime_settings.get_embedding_settings
        original_get_secret = memory_store.runtime_settings.get_runtime_secret_value
        original_post = memory_store.requests.post

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

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('embedding', 'token'))
            return runtime_settings.RuntimeSecretValue(
                section='embedding',
                field='token',
                value='embed-db-token',
                source='db_encrypted',
                source_reason='db_row',
            )

        memory_store.runtime_settings.get_embedding_settings = self._db_embedding_view
        memory_store.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        memory_store.requests.post = fake_post
        try:
            vec = memory_store.embed('bonjour', mode='query')
        finally:
            memory_store.runtime_settings.get_embedding_settings = original_get_settings
            memory_store.runtime_settings.get_runtime_secret_value = original_get_secret
            memory_store.requests.post = original_post

        self.assertEqual(vec, [0.1, 0.2, 0.3])
        self.assertEqual(observed['url'], 'https://embed.override.example/embed')
        self.assertEqual(observed['headers']['X-Embed-Token'], 'embed-db-token')
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

    def test_runtime_embedding_token_uses_env_fallback_when_runtime_layer_returns_it(self) -> None:
        original_get_secret = memory_store.runtime_settings.get_runtime_secret_value

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('embedding', 'token'))
            return runtime_settings.RuntimeSecretValue(
                section='embedding',
                field='token',
                value='embed-env-fallback-token',
                source='env_fallback',
                source_reason='empty_table',
            )

        memory_store.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            token = memory_store._runtime_embedding_token()
        finally:
            memory_store.runtime_settings.get_runtime_secret_value = original_get_secret

        self.assertEqual(token, 'embed-env-fallback-token')

    def test_runtime_embedding_token_raises_explicit_error_when_db_secret_is_not_decryptable(self) -> None:
        original_get_secret = memory_store.runtime_settings.get_runtime_secret_value

        def fake_get_runtime_secret_value(section: str, field: str):
            raise runtime_settings.RuntimeSettingsSecretResolutionError(
                'failed to decrypt runtime secret embedding.token: bad ciphertext'
            )

        memory_store.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretResolutionError,
                'failed to decrypt runtime secret embedding.token: bad ciphertext',
            ):
                memory_store._runtime_embedding_token()
        finally:
            memory_store.runtime_settings.get_runtime_secret_value = original_get_secret

    def test_conn_uses_external_bootstrap_dsn_with_runtime_postgresql_backend(self) -> None:
        observed = {'dsn': None}
        original_get_settings = memory_store.runtime_settings.get_database_settings
        original_connect = memory_store.psycopg.connect
        original_dsn = config.FRIDA_MEMORY_DB_DSN

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return object()

        memory_store.runtime_settings.get_database_settings = self._db_database_view
        memory_store.psycopg.connect = fake_connect
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        try:
            conn = memory_store._conn()
        finally:
            memory_store.runtime_settings.get_database_settings = original_get_settings
            memory_store.psycopg.connect = original_connect
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertIsNotNone(conn)
        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )

    def test_conn_rejects_unsupported_runtime_database_backend(self) -> None:
        original_get_settings = memory_store.runtime_settings.get_database_settings
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        memory_store.runtime_settings.get_database_settings = lambda: self._db_database_view(backend='mysql')
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        try:
            with self.assertRaisesRegex(ValueError, 'unsupported runtime database backend: mysql'):
                memory_store._conn()
        finally:
            memory_store.runtime_settings.get_database_settings = original_get_settings
            config.FRIDA_MEMORY_DB_DSN = original_dsn

    def test_bootstrap_database_dsn_requires_env_fallback_while_db_secret_decryption_is_unavailable(self) -> None:
        original_get_settings = memory_store.runtime_settings.get_database_settings
        original_get_secret = memory_store.runtime_settings.get_runtime_secret_value
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        observed = {'called': False}

        def fake_get_runtime_secret_value(section: str, field: str):
            observed['called'] = True
            raise AssertionError('database bootstrap must not resolve runtime secret values')

        memory_store.runtime_settings.get_database_settings = self._db_database_view
        memory_store.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        config.FRIDA_MEMORY_DB_DSN = ''
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretRequiredError,
                'runtime secret decryption is not available',
            ):
                memory_store._bootstrap_database_dsn()
        finally:
            memory_store.runtime_settings.get_database_settings = original_get_settings
            memory_store.runtime_settings.get_runtime_secret_value = original_get_secret
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertFalse(observed['called'])


if __name__ == '__main__':
    unittest.main()
