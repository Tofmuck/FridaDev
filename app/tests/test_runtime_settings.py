from __future__ import annotations

import ast
import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
import config


class RuntimeSettingsSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_section_order_is_fixed(self) -> None:
        self.assertEqual(
            runtime_settings.list_sections(),
            (
                'main_model',
                'arbiter_model',
                'summary_model',
                'embedding',
                'database',
                'services',
                'resources',
            ),
        )

    def test_main_model_includes_global_sampling_fields(self) -> None:
        spec = runtime_settings.get_section_spec('main_model')
        self.assertIn('temperature', spec.field_names())
        self.assertIn('top_p', spec.field_names())

    def test_embedding_model_exists_but_is_not_seeded_from_env(self) -> None:
        spec = runtime_settings.get_field_spec('embedding', 'model')
        self.assertEqual(spec.value_type, 'text')
        self.assertFalse(spec.is_secret)
        self.assertFalse(spec.seed_from_env)
        self.assertEqual(spec.seed_default, 'intfloat/multilingual-e5-small')

    def test_database_dsn_stays_out_of_env_seed(self) -> None:
        spec = runtime_settings.get_field_spec('database', 'dsn')
        self.assertTrue(spec.is_secret)
        self.assertEqual(spec.env_var, 'FRIDA_MEMORY_DB_DSN')
        self.assertFalse(spec.seed_from_env)

    def test_describe_section_exposes_public_metadata(self) -> None:
        description = runtime_settings.describe_section('services')
        self.assertEqual(description['name'], 'services')
        self.assertIn('fields', description)
        self.assertTrue(any(field['key'] == 'crawl4ai_token' and field['is_secret'] for field in description['fields']))

    def test_normalize_stored_payload_rejects_plain_secret_value(self) -> None:
        with self.assertRaisesRegex(ValueError, 'secret field does not accept plain value'):
            runtime_settings.normalize_stored_payload(
                'main_model',
                {
                    'api_key': {
                        'value': 'plain-text-should-not-pass',
                    }
                },
            )

    def test_normalize_stored_payload_accepts_secret_encrypted_value(self) -> None:
        normalized = runtime_settings.normalize_stored_payload(
            'main_model',
            {
                'api_key': {
                    'value_encrypted': 'ciphertext',
                    'origin': 'env_seed',
                }
            },
        )
        self.assertEqual(
            normalized,
            {
                'api_key': {
                    'is_secret': True,
                    'is_set': True,
                    'origin': 'env_seed',
                    'value_encrypted': 'ciphertext',
                }
            },
        )

    def test_redact_payload_for_api_hides_secret_value(self) -> None:
        redacted = runtime_settings.redact_payload_for_api(
            'services',
            {
                'crawl4ai_token': {
                    'value_encrypted': 'ciphertext',
                    'origin': 'admin_ui',
                },
                'crawl4ai_url': {
                    'value': 'http://127.0.0.1:11235',
                    'origin': 'env_seed',
                },
            },
        )
        self.assertEqual(
            redacted,
            {
                'crawl4ai_token': {
                    'is_secret': True,
                    'is_set': True,
                    'origin': 'admin_ui',
                },
                'crawl4ai_url': {
                    'value': 'http://127.0.0.1:11235',
                    'is_secret': False,
                    'origin': 'env_seed',
                },
            },
        )

    def test_build_env_seed_bundle_keeps_secret_value_out_of_payload(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('main_model')
        self.assertEqual(bundle.section, 'main_model')
        self.assertEqual(bundle.payload['base_url']['value'], config.OR_BASE)
        self.assertEqual(bundle.payload['temperature']['value'], 0.4)
        self.assertEqual(bundle.payload['api_key']['is_secret'], True)
        self.assertEqual(bundle.payload['api_key']['is_set'], bool(config.OR_KEY))
        self.assertNotIn('value', bundle.payload['api_key'])
        self.assertNotIn('value_encrypted', bundle.payload['api_key'])
        if config.OR_KEY:
            self.assertEqual(bundle.secret_values['api_key'], config.OR_KEY)

    def test_build_env_seed_bundle_excludes_database_dsn_secret_seed(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('database')
        self.assertEqual(bundle.payload['backend']['value'], 'postgresql')
        self.assertEqual(bundle.payload['dsn']['is_secret'], True)
        self.assertFalse(bundle.payload['dsn']['is_set'])
        self.assertEqual(bundle.secret_values, {})

    def test_build_env_seed_bundle_uses_current_embedding_value(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('embedding')
        self.assertEqual(bundle.payload['endpoint']['value'], config.EMBED_BASE_URL)
        self.assertEqual(bundle.payload['model']['value'], 'intfloat/multilingual-e5-small')
        self.assertEqual(bundle.payload['dimensions']['value'], config.EMBED_DIM)
        self.assertEqual(bundle.payload['top_k']['value'], config.MEMORY_TOP_K)
        self.assertEqual(bundle.payload['token']['is_set'], bool(config.EMBED_TOKEN))

    def test_get_unseeded_sections_uses_missing_rows_as_signal(self) -> None:
        missing = runtime_settings.get_unseeded_sections(('main_model', 'services'))
        self.assertEqual(
            missing,
            (
                'arbiter_model',
                'summary_model',
                'embedding',
                'database',
                'resources',
            ),
        )

    def test_build_env_seed_plan_skips_existing_sections(self) -> None:
        plan = runtime_settings.build_env_seed_plan(('main_model', 'embedding', 'services'))
        self.assertEqual(
            tuple(bundle.section for bundle in plan),
            (
                'arbiter_model',
                'summary_model',
                'database',
                'resources',
            ),
        )

    def test_runtime_section_falls_back_to_env_when_table_is_empty(self) -> None:
        view = runtime_settings.get_runtime_section('main_model', fetcher=lambda: {})
        self.assertEqual(view.source, 'env')
        self.assertEqual(view.source_reason, 'empty_table')
        self.assertEqual(view.payload['model']['value'], config.OR_MODEL)

    def test_runtime_section_falls_back_to_env_when_db_is_unavailable(self) -> None:
        def failing_fetcher():
            raise runtime_settings.RuntimeSettingsDbUnavailableError('db down')

        view = runtime_settings.get_runtime_section('services', fetcher=failing_fetcher)
        self.assertEqual(view.source, 'env')
        self.assertEqual(view.source_reason, 'db_unavailable')
        self.assertEqual(view.payload['searxng_url']['value'], config.SEARXNG_URL)

    def test_runtime_section_uses_db_row_when_present(self) -> None:
        def fetcher():
            return {
                'embedding': runtime_settings.normalize_stored_payload(
                    'embedding',
                    {
                        'endpoint': {'value': 'https://embed.override.example', 'origin': 'db'},
                        'model': {'value': 'custom-embed-model', 'origin': 'db'},
                        'token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'dimensions': {'value': 768, 'origin': 'db'},
                        'top_k': {'value': 9, 'origin': 'db'},
                    },
                )
            }

        view = runtime_settings.get_embedding_settings(fetcher=fetcher)
        self.assertEqual(view.source, 'db')
        self.assertEqual(view.source_reason, 'db_row')
        self.assertEqual(view.payload['model']['value'], 'custom-embed-model')
        self.assertEqual(view.payload['dimensions']['value'], 768)

    def test_runtime_section_marks_missing_section_when_other_rows_exist(self) -> None:
        def fetcher():
            return {
                'services': runtime_settings.normalize_stored_payload(
                    'services',
                    {
                        'searxng_url': {'value': 'http://127.0.0.1:8092', 'origin': 'db'},
                        'searxng_results': {'value': 5, 'origin': 'db'},
                        'crawl4ai_url': {'value': 'http://127.0.0.1:11235', 'origin': 'db'},
                        'crawl4ai_token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'crawl4ai_top_n': {'value': 2, 'origin': 'db'},
                        'crawl4ai_max_chars': {'value': 5000, 'origin': 'db'},
                    },
                )
            }

        view = runtime_settings.get_runtime_section('main_model', fetcher=fetcher)
        self.assertEqual(view.source, 'env')
        self.assertEqual(view.source_reason, 'missing_section')

    def test_runtime_section_for_api_redacts_secrets(self) -> None:
        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                )
            }

        view = runtime_settings.get_runtime_section_for_api('main_model', fetcher=fetcher)
        self.assertEqual(view.payload['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'db'})
        self.assertEqual(view.payload['model']['value'], 'openai/gpt-5.1')

    def test_require_secret_configured_raises_explicit_error(self) -> None:
        view = runtime_settings.get_runtime_section('database', fetcher=lambda: {})
        with self.assertRaisesRegex(runtime_settings.RuntimeSettingsSecretRequiredError, 'missing secret config: database.dsn'):
            runtime_settings.require_secret_configured(view, 'dsn')

    def test_runtime_settings_layer_does_not_import_admin_logs(self) -> None:
        module_path = APP_DIR / 'admin' / 'runtime_settings.py'
        tree = ast.parse(module_path.read_text())
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        self.assertNotIn('admin_logs', imported_modules)
        self.assertNotIn('admin.admin_logs', imported_modules)

    def test_web_host_and_port_stay_out_of_runtime_settings_scope(self) -> None:
        env_vars = {
            field.env_var
            for spec in runtime_settings.SECTION_SPECS.values()
            for field in spec.fields
            if field.env_var
        }
        self.assertNotIn('FRIDA_WEB_HOST', env_vars)
        self.assertNotIn('FRIDA_WEB_PORT', env_vars)

    def test_default_db_fetch_uses_external_bootstrap_dsn(self) -> None:
        observed = {'dsn': None, 'query': None}

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query):
                observed['query'] = query

            def fetchall(self):
                return []

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return FakeConnection()

        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            rows = runtime_settings._default_db_fetch_all_sections()
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg

        self.assertEqual(rows, {})
        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertIn('FROM runtime_settings', observed['query'])

    def test_cache_can_be_invalidated(self) -> None:
        calls = {'count': 0}

        def fetcher():
            calls['count'] += 1
            return {}

        runtime_settings.get_runtime_section('main_model', fetcher=fetcher)
        runtime_settings.get_runtime_section('main_model', fetcher=fetcher)
        self.assertEqual(calls['count'], 2)

        calls = {'count': 0}

        def cached_fetcher():
            calls['count'] += 1
            return {}

        runtime_settings.invalidate_runtime_settings_cache()
        original = runtime_settings._default_db_fetch_all_sections
        runtime_settings._default_db_fetch_all_sections = cached_fetcher
        try:
            runtime_settings.get_runtime_section('main_model')
            runtime_settings.get_runtime_section('main_model')
            self.assertEqual(calls['count'], 1)
            runtime_settings.invalidate_runtime_settings_cache()
            runtime_settings.get_runtime_section('main_model')
            self.assertEqual(calls['count'], 2)
        finally:
            runtime_settings._default_db_fetch_all_sections = original
            runtime_settings.invalidate_runtime_settings_cache()

    def test_normalize_admin_patch_payload_validates_non_secret_types(self) -> None:
        normalized = runtime_settings.normalize_admin_patch_payload(
            'main_model',
            {
                'model': {'value': 'openrouter/next-model'},
                'temperature': {'value': 0.55},
                'top_p': {'value': 0.9},
            },
        )
        self.assertEqual(normalized['model']['value'], 'openrouter/next-model')
        self.assertEqual(normalized['temperature']['value'], 0.55)
        self.assertEqual(normalized['top_p']['value'], 0.9)
        self.assertEqual(normalized['model']['origin'], 'admin_ui')

    def test_normalize_admin_patch_payload_rejects_secret_updates_for_now(self) -> None:
        with self.assertRaisesRegex(runtime_settings.RuntimeSettingsValidationError, 'secret updates are not supported yet: main_model.api_key'):
            runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'api_key': {'value': 'sk-secret'},
                },
            )

    def test_update_runtime_section_uses_external_bootstrap_dsn_and_returns_redacted_payload(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchone(self):
                return None

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return FakeConnection()

        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            view = runtime_settings.update_runtime_section(
                'main_model',
                {
                    'model': {'value': 'openrouter/runtime-main-model'},
                    'temperature': {'value': 0.25},
                },
                updated_by='phase5-test',
                fetcher=lambda: {},
            )
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(view.section, 'main_model')
        self.assertEqual(view.source, 'db')
        self.assertEqual(view.payload['model']['value'], 'openrouter/runtime-main-model')
        self.assertEqual(view.payload['temperature']['value'], 0.25)
        self.assertEqual(view.payload['api_key']['is_secret'], True)
        self.assertIn('INSERT INTO runtime_settings', observed['queries'][1])
        self.assertIn('INSERT INTO runtime_settings_history', observed['queries'][2])


if __name__ == '__main__':
    unittest.main()
