from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from memory import arbiter
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
        observed = {'dense_limit': None, 'lexical_limit': None, 'merge_top_k': None}
        original_get_settings = memory_store.runtime_settings.get_embedding_settings
        original_embed = memory_store.embed
        original_conn = memory_store._conn
        original_dense = memory_store.memory_traces_summaries._retrieve_dense_candidates
        original_lexical = memory_store.memory_traces_summaries._retrieve_lexical_candidates
        original_merge = memory_store.memory_traces_summaries._merge_hybrid_candidates

        memory_store.runtime_settings.get_embedding_settings = self._db_embedding_view
        memory_store.embed = lambda query, mode='query', purpose=None: [0.1, 0.2, 0.3]
        memory_store._conn = lambda: object()

        def fake_dense(_q_vec, *, limit, conn_factory):
            observed['dense_limit'] = limit
            self.assertIsNotNone(conn_factory)
            return []

        def fake_lexical(_query, *, limit, conn_factory):
            observed['lexical_limit'] = limit
            self.assertIsNotNone(conn_factory)
            return []

        def fake_merge(*, dense_candidates, lexical_candidates, top_k, include_internal_scores=False):
            observed['merge_top_k'] = top_k
            self.assertFalse(include_internal_scores)
            self.assertEqual(dense_candidates, [])
            self.assertEqual(lexical_candidates, [])
            return []

        memory_store.memory_traces_summaries._retrieve_dense_candidates = fake_dense
        memory_store.memory_traces_summaries._retrieve_lexical_candidates = fake_lexical
        memory_store.memory_traces_summaries._merge_hybrid_candidates = fake_merge
        try:
            rows = memory_store.retrieve('question')
        finally:
            memory_store.runtime_settings.get_embedding_settings = original_get_settings
            memory_store.embed = original_embed
            memory_store._conn = original_conn
            memory_store.memory_traces_summaries._retrieve_dense_candidates = original_dense
            memory_store.memory_traces_summaries._retrieve_lexical_candidates = original_lexical
            memory_store.memory_traces_summaries._merge_hybrid_candidates = original_merge

        self.assertEqual(rows, [])
        self.assertEqual(observed['merge_top_k'], 9)
        self.assertEqual(observed['dense_limit'], 27)
        self.assertEqual(observed['lexical_limit'], 27)

    def test_retrieve_for_arbiter_requests_internal_scores_while_public_retrieve_stays_stable(self) -> None:
        observed_include_internal_scores = []
        original_retrieve = memory_store.memory_traces_summaries.retrieve

        def fake_retrieve(
            _query,
            top_k=None,
            *,
            include_internal_scores=False,
            runtime_embedding_value_fn,
            conn_factory,
            embed_fn,
            logger,
        ):
            observed_include_internal_scores.append(include_internal_scores)
            self.assertIsNone(top_k)
            self.assertIsNotNone(runtime_embedding_value_fn)
            self.assertIsNotNone(conn_factory)
            self.assertIsNotNone(embed_fn)
            self.assertIsNotNone(logger)
            row = {
                'conversation_id': 'conv-1',
                'role': 'user',
                'content': 'Christophe Muck',
                'timestamp': '2026-04-10T12:34:56Z',
                'summary_id': 'sum-1',
                'score': 0.98,
            }
            if include_internal_scores:
                row['retrieval_score'] = 0.98
                row['semantic_score'] = 0.0
            return [row]

        memory_store.memory_traces_summaries.retrieve = fake_retrieve
        try:
            public_rows = memory_store.retrieve('question')
            internal_rows = memory_store.retrieve_for_arbiter('question')
        finally:
            memory_store.memory_traces_summaries.retrieve = original_retrieve

        self.assertEqual(observed_include_internal_scores, [False, True])
        self.assertEqual(
            set(public_rows[0].keys()),
            {'conversation_id', 'role', 'content', 'timestamp', 'summary_id', 'score'},
        )
        self.assertEqual(public_rows[0]['summary_id'], 'sum-1')
        self.assertEqual(internal_rows[0]['retrieval_score'], 0.98)
        self.assertEqual(internal_rows[0]['semantic_score'], 0.0)

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

    def test_init_db_creates_pg_trgm_extension_and_exact_trigram_index(self) -> None:
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
        self.assertIn('CREATE EXTENSION IF NOT EXISTS pg_trgm;', joined)
        self.assertIn('traces_content_exact_trgm_gist_idx', joined)
        self.assertIn('gist_trgm_ops', joined)

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

    def test_record_arbiter_decisions_uses_explicit_effective_model_when_decisions_omit_it(self) -> None:
        observed = {'models': [], 'committed': False}
        original_conn = memory_store._conn

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['models'].append(params[11])

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                observed['committed'] = True
                return None

        memory_store._conn = lambda: FakeConnection()
        try:
            memory_store.record_arbiter_decisions(
                conversation_id='conv-phase4-arbiter-db',
                traces=[
                    {
                        'role': 'assistant',
                        'content': 'memoire candidate',
                        'timestamp': '2026-03-26T00:00:00Z',
                        'score': 0.9,
                    }
                ],
                decisions=[
                    {
                        'candidate_id': '0',
                        'keep': True,
                        'semantic_relevance': 0.9,
                        'contextual_gain': 0.7,
                        'redundant_with_recent': False,
                        'reason': 'kept',
                        'decision_source': 'llm',
                    }
                ],
                effective_model='openrouter/arbiter-runtime-db',
            )
        finally:
            memory_store._conn = original_conn

        self.assertEqual(observed['models'], ['openrouter/arbiter-runtime-db'])
        self.assertTrue(observed['committed'])

    def test_record_arbiter_decisions_keeps_explicit_env_fallback_model_when_decisions_omit_it(self) -> None:
        observed = {'models': [], 'committed': False}
        original_conn = memory_store._conn

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['models'].append(params[11])

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                observed['committed'] = True
                return None

        memory_store._conn = lambda: FakeConnection()
        try:
            memory_store.record_arbiter_decisions(
                conversation_id='conv-phase4-arbiter-env',
                traces=[
                    {
                        'role': 'assistant',
                        'content': 'memoire candidate',
                        'timestamp': '2026-03-26T00:00:00Z',
                        'score': 0.6,
                    }
                ],
                decisions=[
                    {
                        'candidate_id': '0',
                        'keep': False,
                        'semantic_relevance': 0.2,
                        'contextual_gain': 0.1,
                        'redundant_with_recent': False,
                        'reason': 'fallback',
                        'decision_source': 'fallback',
                    }
                ],
                effective_model=config.ARBITER_MODEL,
            )
        finally:
            memory_store._conn = original_conn

        self.assertEqual(observed['models'], [config.ARBITER_MODEL])
        self.assertTrue(observed['committed'])

    def test_record_arbiter_decisions_persists_effective_model_even_if_runtime_changes_before_insert(self) -> None:
        observed = {'persisted_models': [], 'request_models': []}
        original_arbiter_get_settings = arbiter.runtime_settings.get_arbiter_model_settings
        original_load_prompt = arbiter._load_prompt
        original_post = arbiter.requests.post
        original_conn = memory_store._conn

        call_count = {'n': 0}

        def fake_get_arbiter_model_settings():
            call_count['n'] += 1
            model = (
                'openrouter/runtime-arbiter-v1'
                if call_count['n'] == 1
                else 'openrouter/runtime-arbiter-v2'
            )
            return runtime_settings.RuntimeSectionView(
                section='arbiter_model',
                payload=runtime_settings.normalize_stored_payload(
                    'arbiter_model',
                    {
                        'model': {'value': model, 'origin': 'db'},
                        'temperature': {'value': 0.0, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                        'timeout_s': {'value': 45, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        class FakeArbiterResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    'choices': [
                        {
                            'message': {
                                'content': (
                                    '{"decisions":[{"candidate_id":"0","keep":true,'
                                    '"semantic_relevance":0.9,"contextual_gain":0.9,'
                                    '"redundant_with_recent":false,"reason":"kept"}]}'
                                )
                            }
                        }
                    ]
                }

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['persisted_models'].append(params[11])

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        def fake_post(url, json, headers, timeout):
            observed['request_models'].append(json['model'])
            return FakeArbiterResponse()

        traces = [
            {
                'role': 'assistant',
                'content': 'memoire candidate',
                'timestamp': '2026-03-26T00:00:00Z',
                'score': 0.9,
            }
        ]
        recent_turns = [{'role': 'user', 'content': 'question recente'}]

        arbiter.runtime_settings.get_arbiter_model_settings = fake_get_arbiter_model_settings
        arbiter._load_prompt = lambda _path, _label: 'prompt'
        arbiter.requests.post = fake_post
        memory_store._conn = lambda: FakeConnection()
        try:
            _kept, decisions = arbiter.filter_traces_with_diagnostics(traces, recent_turns)
            effective_model = observed['request_models'][0]
            decisions_without_model = [{k: v for k, v in d.items() if k != 'model'} for d in decisions]
            memory_store.record_arbiter_decisions(
                'conv-phase4-arbiter-race',
                traces,
                decisions_without_model,
                effective_model=effective_model,
            )
        finally:
            arbiter.runtime_settings.get_arbiter_model_settings = original_arbiter_get_settings
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            memory_store._conn = original_conn

        self.assertEqual(observed['request_models'], ['openrouter/runtime-arbiter-v1'])
        self.assertEqual(observed['persisted_models'], ['openrouter/runtime-arbiter-v1'])


if __name__ == '__main__':
    unittest.main()
