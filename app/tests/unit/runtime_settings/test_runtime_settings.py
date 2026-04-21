from __future__ import annotations

import ast
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings, runtime_settings_repo, runtime_settings_spec, runtime_settings_validation
import config
from identity import static_identity_paths


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
                'stimmung_agent_model',
                'validation_agent_model',
                'embedding',
                'database',
                'services',
                'resources',
                'identity_governance',
            ),
        )

    def test_secret_v1_field_list_is_fixed(self) -> None:
        self.assertEqual(
            runtime_settings.list_secret_v1_fields(),
            (
                ('main_model', 'api_key'),
                ('embedding', 'token'),
                ('services', 'crawl4ai_token'),
                ('database', 'dsn'),
            ),
        )

    def test_runtime_settings_facade_reexports_runtime_settings_spec_symbols(self) -> None:
        self.assertIs(runtime_settings.FieldSpec, runtime_settings_spec.FieldSpec)
        self.assertIs(runtime_settings.SectionSpec, runtime_settings_spec.SectionSpec)
        self.assertIs(runtime_settings.SECTION_NAMES, runtime_settings_spec.SECTION_NAMES)
        self.assertIs(runtime_settings.SECRET_V1_FIELDS, runtime_settings_spec.SECRET_V1_FIELDS)
        self.assertIs(runtime_settings.SECTION_SPECS, runtime_settings_spec.SECTION_SPECS)
        self.assertIs(
            runtime_settings.get_section_spec('services'),
            runtime_settings_spec.get_section_spec('services'),
        )

    def test_runtime_settings_init_db_facade_delegates_to_repository_module(self) -> None:
        observed: dict[str, object] = {}

        def fake_init_runtime_settings_db(**kwargs):
            observed.update(kwargs)
            return {
                'sql_path': str(kwargs['sql_path']),
                'tables': ('runtime_settings', 'runtime_settings_history'),
            }

        original_impl = runtime_settings_repo.init_runtime_settings_db
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_sql_path = runtime_settings.RUNTIME_SETTINGS_SQL_PATH
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        runtime_settings.RUNTIME_SETTINGS_SQL_PATH = Path('/tmp/runtime_settings_v1.sql')
        runtime_settings_repo.init_runtime_settings_db = fake_init_runtime_settings_db
        try:
            details = runtime_settings.init_runtime_settings_db()
        finally:
            runtime_settings_repo.init_runtime_settings_db = original_impl
            runtime_settings.RUNTIME_SETTINGS_SQL_PATH = original_sql_path
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(observed['sql_path'], Path('/tmp/runtime_settings_v1.sql'))
        self.assertIs(
            observed['db_unavailable_error_cls'],
            runtime_settings.RuntimeSettingsDbUnavailableError,
        )
        self.assertEqual(
            details,
            {
                'sql_path': '/tmp/runtime_settings_v1.sql',
                'tables': ('runtime_settings', 'runtime_settings_history'),
            },
        )

    def test_runtime_settings_validate_facade_delegates_to_validation_module(self) -> None:
        observed: dict[str, object] = {}

        def fake_validate_runtime_section(**kwargs):
            observed.update(kwargs)
            return {'section': kwargs['section'], 'valid': True, 'checks': []}

        original_impl = runtime_settings_validation.validate_runtime_section
        runtime_settings_validation.validate_runtime_section = fake_validate_runtime_section
        try:
            result = runtime_settings.validate_runtime_section(
                'services',
                {'searxng_url': {'value': 'http://127.0.0.1:8092'}},
                fetcher=lambda: {},
            )
        finally:
            runtime_settings_validation.validate_runtime_section = original_impl

        self.assertEqual(observed['section'], 'services')
        self.assertEqual(observed['patch_payload'], {'searxng_url': {'value': 'http://127.0.0.1:8092'}})
        self.assertTrue(callable(observed['fetcher']))
        self.assertIs(observed['candidate_runtime_section'], runtime_settings._candidate_runtime_section)
        self.assertIs(observed['resolve_runtime_secret_from_view'], runtime_settings._resolve_runtime_secret_from_view)
        self.assertIs(observed['secret_required_error_cls'], runtime_settings.RuntimeSettingsSecretRequiredError)
        self.assertIs(observed['secret_resolution_error_cls'], runtime_settings.RuntimeSettingsSecretResolutionError)
        self.assertIs(observed['config_module'], config)
        self.assertEqual(result, {'section': 'services', 'valid': True, 'checks': []})

    def test_main_model_includes_global_sampling_fields(self) -> None:
        spec = runtime_settings.get_section_spec('main_model')
        self.assertIn('temperature', spec.field_names())
        self.assertIn('top_p', spec.field_names())

    def test_main_model_includes_response_max_tokens_field(self) -> None:
        spec = runtime_settings.get_field_spec('main_model', 'response_max_tokens')
        self.assertEqual(spec.value_type, 'int')
        self.assertFalse(spec.is_secret)
        self.assertFalse(spec.seed_from_env)
        self.assertEqual(spec.seed_default, 8192)

    def test_main_model_includes_identity_extractor_title_field(self) -> None:
        spec = runtime_settings.get_field_spec('main_model', 'title_identity_extractor')
        self.assertEqual(spec.value_type, 'text')
        self.assertFalse(spec.is_secret)
        self.assertTrue(spec.seed_from_env)
        self.assertEqual(spec.env_var, 'OPENROUTER_TITLE_IDENTITY_EXTRACTOR')

    def test_main_model_includes_component_referer_fields(self) -> None:
        expected_env_vars = {
            'referer_llm': 'OPENROUTER_REFERER_LLM',
            'referer_arbiter': 'OPENROUTER_REFERER_ARBITER',
            'referer_identity_extractor': 'OPENROUTER_REFERER_IDENTITY_EXTRACTOR',
            'referer_resumer': 'OPENROUTER_REFERER_RESUMER',
            'referer_stimmung_agent': 'OPENROUTER_REFERER_STIMMUNG_AGENT',
            'referer_validation_agent': 'OPENROUTER_REFERER_VALIDATION_AGENT',
        }

        for field_name, env_var in expected_env_vars.items():
            spec = runtime_settings.get_field_spec('main_model', field_name)
            self.assertEqual(spec.value_type, 'text')
            self.assertFalse(spec.is_secret)
            self.assertTrue(spec.seed_from_env)
            self.assertEqual(spec.env_var, env_var)

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
        self.assertTrue(
            any(
                field['key'] == 'crawl4ai_explicit_url_max_chars'
                and field['value_type'] == 'int'
                and field.get('env_var') == 'CRAWL4AI_EXPLICIT_URL_MAX_CHARS'
                for field in description['fields']
            )
        )

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

    def test_describe_secret_sources_marks_env_seed_secret_as_env_fallback(self) -> None:
        payload = runtime_settings.build_env_seed_bundle('main_model').payload
        secret_sources = runtime_settings.describe_secret_sources('main_model', payload)
        self.assertEqual(secret_sources['api_key'], 'env_fallback' if config.OR_KEY else 'missing')

    def test_describe_secret_sources_marks_db_secret_as_db_encrypted(self) -> None:
        secret_sources = runtime_settings.describe_secret_sources(
            'services',
            {
                'searxng_url': {'value': 'http://127.0.0.1:8092', 'origin': 'db'},
                'searxng_results': {'value': 5, 'origin': 'db'},
                'crawl4ai_url': {'value': 'http://127.0.0.1:11235', 'origin': 'db'},
                'crawl4ai_token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                'crawl4ai_top_n': {'value': 2, 'origin': 'db'},
                'crawl4ai_max_chars': {'value': 5000, 'origin': 'db'},
                'crawl4ai_explicit_url_max_chars': {'value': 25000, 'origin': 'db'},
            },
        )
        self.assertEqual(secret_sources['crawl4ai_token'], 'db_encrypted')

    def test_describe_secret_sources_keeps_database_dsn_on_env_fallback_while_bootstrap_env_exists(self) -> None:
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        try:
            secret_sources = runtime_settings.describe_secret_sources(
                'database',
                {
                    'backend': {'value': 'postgresql', 'origin': 'db'},
                    'dsn': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                },
            )
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertEqual(secret_sources['dsn'], 'env_fallback')

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
                        'crawl4ai_explicit_url_max_chars': {'value': 25000, 'origin': 'db'},
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

    def test_runtime_status_reports_db_state_and_section_sources(self) -> None:
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

        status = runtime_settings.get_runtime_status(fetcher=fetcher)
        self.assertEqual(status['db_state'], 'db_rows')
        self.assertEqual(status['bootstrap']['database_dsn_source'], 'env')
        self.assertEqual(status['bootstrap']['database_dsn_env_var'], 'FRIDA_MEMORY_DB_DSN')
        self.assertEqual(status['sections']['main_model'], {'source': 'db', 'source_reason': 'db_row'})
        self.assertEqual(status['sections']['services'], {'source': 'env', 'source_reason': 'missing_section'})

    def test_require_secret_configured_raises_explicit_error(self) -> None:
        view = runtime_settings.get_runtime_section('database', fetcher=lambda: {})
        with self.assertRaisesRegex(runtime_settings.RuntimeSettingsSecretRequiredError, 'missing secret config: database.dsn'):
            runtime_settings.require_secret_configured(view, 'dsn')

    def test_get_runtime_secret_value_uses_env_fallback_when_section_is_from_env(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-env-fallback-secret'
        try:
            secret = runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=lambda: {})
        finally:
            config.OR_KEY = original_api_key

        self.assertEqual(secret.value, 'sk-env-fallback-secret')
        self.assertEqual(secret.source, 'env_fallback')
        self.assertEqual(secret.source_reason, 'empty_table')

    def test_get_runtime_secret_value_decrypts_db_secret_when_encrypted_value_is_present(self) -> None:
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value

        def fake_decrypt_runtime_secret_value(value_encrypted: str) -> str:
            self.assertEqual(value_encrypted, 'cipher-main-model')
            return 'sk-db-main-model'

        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openrouter/runtime-main', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'cipher-main-model', 'origin': 'db'},
                    },
                )
            }

        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = fake_decrypt_runtime_secret_value
        try:
            secret = runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=fetcher)
        finally:
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt

        self.assertEqual(secret.value, 'sk-db-main-model')
        self.assertEqual(secret.source, 'db_encrypted')
        self.assertEqual(secret.source_reason, 'db_row')

    def test_get_runtime_secret_value_raises_explicit_error_when_db_secret_is_not_decryptable(self) -> None:
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value

        def fake_decrypt_runtime_secret_value(value_encrypted: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError('bad ciphertext')

        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openrouter/runtime-main', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'cipher-main-model', 'origin': 'db'},
                    },
                )
            }

        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = fake_decrypt_runtime_secret_value
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretResolutionError,
                'failed to decrypt runtime secret main_model.api_key: bad ciphertext',
            ):
                runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=fetcher)
        finally:
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt

    def test_get_runtime_secret_value_raises_explicit_error_when_db_secret_is_marked_set_without_ciphertext(self) -> None:
        def fetcher():
            return {
                'main_model': runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openrouter/runtime-main', 'origin': 'db'},
                        'api_key': {'is_set': True, 'origin': 'db'},
                    },
                )
            }

        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsSecretResolutionError,
            'secret marked as set but no decryptable value is available: main_model.api_key',
        ):
            runtime_settings.get_runtime_secret_value('main_model', 'api_key', fetcher=fetcher)

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

    def test_runtime_settings_facade_keeps_public_transition_entrypoints(self) -> None:
        expected_symbols = (
            'list_sections',
            'get_section_spec',
            'build_env_seed_bundle',
            'get_runtime_section',
            'get_runtime_status',
            'get_runtime_secret_value',
            'init_runtime_settings_db',
            'bootstrap_runtime_settings_from_env',
            'backfill_runtime_secrets_from_env',
            'update_runtime_section',
            'validate_runtime_section',
        )
        for symbol in expected_symbols:
            self.assertTrue(hasattr(runtime_settings, symbol), symbol)

    def test_critical_app_callers_import_runtime_settings_via_admin_facade(self) -> None:
        caller_paths = (
            APP_DIR / 'server.py',
            APP_DIR / 'minimal_validation.py',
            APP_DIR / 'memory' / 'arbiter.py',
            APP_DIR / 'memory' / 'memory_store.py',
            APP_DIR / 'core' / 'llm_client.py',
            APP_DIR / 'memory' / 'summarizer.py',
            APP_DIR / 'identity' / 'identity.py',
            APP_DIR / 'tools' / 'web_search.py',
        )

        forbidden_modules = {
            'admin.runtime_settings_spec',
            'admin.runtime_settings_repo',
            'admin.runtime_settings_validation',
            'admin.runtime_settings',
        }

        for path in caller_paths:
            tree = ast.parse(path.read_text(encoding='utf-8'))
            has_facade_import = False
            imported_modules: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module_name = str(node.module or '')
                    imported_modules.add(module_name)
                    if module_name == 'admin':
                        imported_names = {alias.name for alias in node.names}
                        if 'runtime_settings' in imported_names:
                            has_facade_import = True
            self.assertTrue(has_facade_import, str(path))
            for module_name in forbidden_modules:
                self.assertNotIn(module_name, imported_modules, f'{path} imports {module_name}')

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
                raise FakeUndefinedTable('relation "runtime_settings" does not exist')

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
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsDbUnavailableError,
                'runtime settings tables missing',
            ):
                runtime_settings._default_db_fetch_all_sections()
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertIn('FROM runtime_settings', observed['query'])

    def test_init_runtime_settings_db_uses_external_bootstrap_dsn_and_executes_sql(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'committed': False,
        }

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query):
                observed['queries'].append(query)

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                observed['committed'] = True

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return FakeConnection()

        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        original_sql_path = runtime_settings.RUNTIME_SETTINGS_SQL_PATH
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(connect=fake_connect)
        with tempfile.TemporaryDirectory() as tmp:
            sql_path = Path(tmp) / 'runtime_settings_v1.sql'
            sql_path.write_text('CREATE TABLE IF NOT EXISTS runtime_settings (section TEXT PRIMARY KEY);', encoding='utf-8')
            runtime_settings.RUNTIME_SETTINGS_SQL_PATH = sql_path
            try:
                details = runtime_settings.init_runtime_settings_db()
            finally:
                runtime_settings.RUNTIME_SETTINGS_SQL_PATH = original_sql_path
                config.FRIDA_MEMORY_DB_DSN = original_dsn
                if original_psycopg is None:
                    del sys.modules['psycopg']
                else:
                    sys.modules['psycopg'] = original_psycopg

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(observed['queries'], ['CREATE TABLE IF NOT EXISTS runtime_settings (section TEXT PRIMARY KEY);'])
        self.assertTrue(observed['committed'])
        self.assertEqual(details['tables'], ('runtime_settings', 'runtime_settings_history'))
        self.assertEqual(details['sql_path'], str(sql_path))

    def test_bootstrap_runtime_settings_from_env_inserts_missing_sections_with_db_seed_non_secret_values(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
            'committed': False,
        }

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return [
                    ('main_model', runtime_settings.build_db_seed_bundle('main_model').payload),
                    ('embedding', runtime_settings.build_db_seed_bundle('embedding').payload),
                ]

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                observed['committed'] = True

        def fake_connect(dsn):
            observed['dsn'] = dsn
            return FakeConnection()

        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(connect=fake_connect)
        try:
            result = runtime_settings.bootstrap_runtime_settings_from_env(updated_by='phase11-bootstrap-test')
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
        self.assertTrue(observed['committed'])
        self.assertEqual(
            result['inserted_sections'],
            (
                'arbiter_model',
                'summary_model',
                'stimmung_agent_model',
                'validation_agent_model',
                'database',
                'services',
                'resources',
                'identity_governance',
            ),
        )
        self.assertEqual(result['updated_sections'], ())
        self.assertEqual(result['updated_fields'], ())

        runtime_payloads = [
            json.loads(params[2])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings (section' in query
        ]
        self.assertEqual(len(runtime_payloads), 8)
        self.assertEqual(runtime_payloads[0]['model']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[0]['timeout_s']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[2]['primary_model']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[-1]['CONTEXT_HINTS_MAX_ITEMS']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[3]['fallback_model']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[4]['backend']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[5]['searxng_url']['origin'], 'db_seed')
        self.assertEqual(runtime_payloads[6]['llm_identity_path']['origin'], 'db_seed')

    def test_bootstrap_runtime_settings_from_env_does_not_overwrite_existing_sections(self) -> None:
        observed = {
            'queries': [],
            'params': [],
        }

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return [
                    (section, runtime_settings.build_db_seed_bundle(section).payload)
                    for section in runtime_settings.list_sections()
                ]

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        def fake_connect(_dsn):
            return FakeConnection()

        original_psycopg = sys.modules.get('psycopg')
        sys.modules['psycopg'] = types.SimpleNamespace(connect=fake_connect)
        try:
            result = runtime_settings.bootstrap_runtime_settings_from_env(updated_by='phase11-noop-test')
        finally:
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertEqual(
            result,
            {
                'inserted_sections': (),
                'inserted_fields': (),
                'updated_sections': (),
                'updated_fields': (),
            },
        )
        self.assertEqual(len(observed['queries']), 1)
        self.assertIn('SELECT section', observed['queries'][0])

    def test_bootstrap_runtime_settings_from_env_backfills_missing_non_secret_fields_on_existing_sections(self) -> None:
        observed = {
            'queries': [],
            'params': [],
            'committed': False,
        }

        existing_rows = []
        for section in runtime_settings.list_sections():
            payload = runtime_settings.build_db_seed_bundle(section).payload
            if section == 'main_model':
                payload = dict(payload)
                payload.pop('response_max_tokens', None)
                payload.pop('referer_llm', None)
                payload.pop('referer_arbiter', None)
                payload.pop('referer_identity_extractor', None)
                payload.pop('referer_resumer', None)
                payload.pop('referer_stimmung_agent', None)
                payload.pop('referer_validation_agent', None)
            existing_rows.append((section, payload))

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return list(existing_rows)

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                observed['committed'] = True

        def fake_connect(_dsn):
            return FakeConnection()

        original_psycopg = sys.modules.get('psycopg')
        sys.modules['psycopg'] = types.SimpleNamespace(connect=fake_connect)
        try:
            result = runtime_settings.bootstrap_runtime_settings_from_env(updated_by='phase12-backfill-test')
        finally:
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertTrue(observed['committed'])
        self.assertEqual(result['inserted_sections'], ())
        self.assertEqual(result['inserted_fields'], ())
        self.assertEqual(result['updated_sections'], ('main_model',))
        self.assertEqual(
            result['updated_fields'],
            (
                'main_model.referer_llm',
                'main_model.referer_arbiter',
                'main_model.referer_identity_extractor',
                'main_model.referer_resumer',
                'main_model.referer_stimmung_agent',
                'main_model.referer_validation_agent',
                'main_model.response_max_tokens',
            ),
        )

        updated_payloads = [
            json.loads(params[2])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings (section' in query
        ]
        self.assertEqual(len(updated_payloads), 1)
        self.assertEqual(updated_payloads[0]['referer_llm']['value'], config.OR_REFERER_LLM)
        self.assertEqual(updated_payloads[0]['referer_llm']['origin'], 'db_seed')
        self.assertEqual(updated_payloads[0]['response_max_tokens']['value'], 8192)
        self.assertEqual(updated_payloads[0]['response_max_tokens']['origin'], 'db_seed')

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
        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsValidationError,
            'ambiguous secret patch payload for main_model.api_key: use replace_value only',
        ):
            runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'api_key': {'value': 'sk-secret'},
                },
            )

    def test_normalize_admin_patch_payload_encrypts_secret_replace_value(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            self.assertEqual(value, 'sk-phase5bis-secret')
            return 'ciphertext-main-model'

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            normalized = runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'api_key': {'replace_value': 'sk-phase5bis-secret'},
                },
            )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

        self.assertEqual(
            normalized,
            {
                'api_key': {
                    'is_secret': True,
                    'is_set': True,
                    'origin': 'admin_ui',
                    'value_encrypted': 'ciphertext-main-model',
                }
            },
        )

    def test_normalize_admin_patch_payload_rejects_secret_patch_without_replace_value(self) -> None:
        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsValidationError,
            'missing replace_value for services.crawl4ai_token',
        ):
            runtime_settings.normalize_admin_patch_payload(
                'services',
                {
                    'crawl4ai_token': {},
                },
            )

    def test_normalize_admin_patch_payload_rejects_secret_patch_when_crypto_key_is_missing(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoKeyMissingError(
                'missing runtime settings crypto key: FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY'
            )

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsValidationError,
                'missing runtime settings crypto key: FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY',
            ):
                runtime_settings.normalize_admin_patch_payload(
                    'embedding',
                    {
                        'token': {'replace_value': 'embed-secret'},
                    },
                )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

    def test_normalize_admin_patch_payload_does_not_echo_secret_value_when_encrypt_fails(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        secret_value = 'sk-should-not-leak-via-encrypt-error'

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError(
                f'crypto engine exploded on {value}'
            )

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            with self.assertRaises(runtime_settings.RuntimeSettingsValidationError) as ctx:
                runtime_settings.normalize_admin_patch_payload(
                    'main_model',
                    {
                        'api_key': {'replace_value': secret_value},
                    },
                )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

        self.assertEqual(str(ctx.exception), 'failed to encrypt secret for main_model.api_key')
        self.assertNotIn(secret_value, str(ctx.exception))

    def test_normalize_admin_patch_payload_accepts_main_model_response_max_tokens(self) -> None:
        normalized = runtime_settings.normalize_admin_patch_payload(
            'main_model',
            {
                'response_max_tokens': {'value': 8192},
            },
        )

        self.assertEqual(
            normalized,
            {
                'response_max_tokens': {
                    'value': 8192,
                    'is_secret': False,
                    'origin': 'admin_ui',
                },
            },
        )

    def test_normalize_admin_patch_payload_rejects_readonly_prompt_field(self) -> None:
        with self.assertRaisesRegex(
            runtime_settings.RuntimeSettingsValidationError,
            'unknown runtime settings field: main_model.system_prompt',
        ):
            runtime_settings.normalize_admin_patch_payload(
                'main_model',
                {
                    'system_prompt': {'value': 'should-not-pass'},
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

    def test_update_runtime_section_encrypts_secret_patch_without_persisting_clear_text(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __init__(self):
                self.last_query = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params):
                self.last_query = query
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchone(self):
                if self.last_query and 'pgp_sym_encrypt' in self.last_query:
                    return ('ciphertext-main-model',)
                if self.last_query and 'SELECT payload' in self.last_query:
                    return None
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

        original_crypto_key = config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_psycopg = sys.modules.get('psycopg')
        config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = 'phase5bis-key'
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            view = runtime_settings.update_runtime_section(
                'main_model',
                {
                    'api_key': {'replace_value': 'sk-phase5bis-secret'},
                },
                updated_by='phase5bis-test',
                fetcher=lambda: {},
            )
        finally:
            config.FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = original_crypto_key
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        payload_after = observed['params'][2][2]
        history_after = observed['params'][3][3]
        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(view.payload['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'})
        self.assertIn('ciphertext-main-model', payload_after)
        self.assertIn('ciphertext-main-model', history_after)
        self.assertNotIn('sk-phase5bis-secret', payload_after)
        self.assertNotIn('sk-phase5bis-secret', history_after)

    def test_update_runtime_section_updates_main_model_response_max_tokens(self) -> None:
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
                    'response_max_tokens': {'value': 8192},
                },
                updated_by='phase12-test',
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
        self.assertEqual(view.payload['response_max_tokens']['value'], 8192)
        self.assertEqual(view.payload['response_max_tokens']['origin'], 'admin_ui')
        payload_after = observed['params'][1][2]
        history_after = observed['params'][2][3]
        self.assertIn('"response_max_tokens": {"value": 8192, "is_secret": false, "origin": "admin_ui"}', payload_after)
        self.assertIn('"response_max_tokens": {"value": 8192, "is_secret": false, "origin": "admin_ui"}', history_after)

    def test_backfill_runtime_secrets_from_env_encrypts_env_secrets_without_persisting_clear_text(self) -> None:
        observed = {
            'dsn': None,
            'queries': [],
            'params': [],
        }
        cipher_by_value = {
            'sk-main-env-secret': 'cipher-main-model',
            'embed-env-secret': 'cipher-embedding',
            'crawl-env-secret': 'cipher-services',
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db': 'cipher-database',
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return []

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

        def fake_encrypt(value: str) -> str:
            return cipher_by_value[value]

        original_or_key = config.OR_KEY
        original_embed_token = config.EMBED_TOKEN
        original_crawl4ai_token = config.CRAWL4AI_TOKEN
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_psycopg = sys.modules.get('psycopg')
        config.OR_KEY = 'sk-main-env-secret'
        config.EMBED_TOKEN = 'embed-env-secret'
        config.CRAWL4AI_TOKEN = 'crawl-env-secret'
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            result = runtime_settings.backfill_runtime_secrets_from_env(updated_by='phase5bis-backfill-test')
        finally:
            config.OR_KEY = original_or_key
            config.EMBED_TOKEN = original_embed_token
            config.CRAWL4AI_TOKEN = original_crawl4ai_token
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertEqual(
            observed['dsn'],
            'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db',
        )
        self.assertEqual(
            result,
            {
                'updated_fields': (
                    'main_model.api_key',
                    'embedding.token',
                    'services.crawl4ai_token',
                    'database.dsn',
                ),
                'updated_sections': ('database', 'embedding', 'main_model', 'services'),
            },
        )

        serialized_params = '\n'.join(
            '' if params is None else '|'.join(str(part) for part in params)
            for params in observed['params']
        )
        self.assertIn('cipher-main-model', serialized_params)
        self.assertIn('cipher-embedding', serialized_params)
        self.assertIn('cipher-services', serialized_params)
        self.assertIn('cipher-database', serialized_params)
        self.assertNotIn('sk-main-env-secret', serialized_params)
        self.assertNotIn('embed-env-secret', serialized_params)
        self.assertNotIn('crawl-env-secret', serialized_params)
        self.assertNotIn('bootstrap-pass', serialized_params)

        runtime_payloads = [
            json.loads(params[2])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings (section' in query
        ]
        history_after_payloads = [
            json.loads(params[3])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings_history' in query
        ]
        self.assertEqual(len(runtime_payloads), 4)
        self.assertEqual(len(history_after_payloads), 4)
        self.assertEqual(runtime_payloads[0]['api_key']['value_encrypted'], 'cipher-main-model')
        self.assertEqual(runtime_payloads[1]['token']['value_encrypted'], 'cipher-embedding')
        self.assertEqual(runtime_payloads[2]['crawl4ai_token']['value_encrypted'], 'cipher-services')
        self.assertEqual(runtime_payloads[3]['dsn']['value_encrypted'], 'cipher-database')
        for payload in runtime_payloads + history_after_payloads:
            rendered = json.dumps(payload)
            self.assertNotIn('sk-main-env-secret', rendered)
            self.assertNotIn('embed-env-secret', rendered)
            self.assertNotIn('crawl-env-secret', rendered)
            self.assertNotIn('bootstrap-pass', rendered)

    def test_backfill_runtime_secrets_from_env_does_not_overwrite_existing_encrypted_values(self) -> None:
        observed = {
            'queries': [],
            'params': [],
            'encrypted_inputs': [],
        }

        class FakeUndefinedTable(Exception):
            pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self):
                return [
                    (
                        'main_model',
                        {
                            'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                            'model': {'value': 'openrouter/main-model', 'origin': 'db'},
                            'api_key': {
                                'is_secret': True,
                                'is_set': True,
                                'origin': 'admin_ui',
                                'value_encrypted': 'cipher-existing-main-model',
                            },
                        },
                    ),
                ]

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

        def fake_connect(_dsn):
            return FakeConnection()

        def fake_encrypt(value: str) -> str:
            observed['encrypted_inputs'].append(value)
            return f'cipher::{len(observed["encrypted_inputs"])}'

        original_or_key = config.OR_KEY
        original_embed_token = config.EMBED_TOKEN
        original_crawl4ai_token = config.CRAWL4AI_TOKEN
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_psycopg = sys.modules.get('psycopg')
        config.OR_KEY = 'sk-main-env-secret'
        config.EMBED_TOKEN = ''
        config.CRAWL4AI_TOKEN = ''
        config.FRIDA_MEMORY_DB_DSN = 'postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db'
        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt
        sys.modules['psycopg'] = types.SimpleNamespace(
            connect=fake_connect,
            errors=types.SimpleNamespace(UndefinedTable=FakeUndefinedTable),
        )
        try:
            result = runtime_settings.backfill_runtime_secrets_from_env(updated_by='phase5bis-reseed-test')
        finally:
            config.OR_KEY = original_or_key
            config.EMBED_TOKEN = original_embed_token
            config.CRAWL4AI_TOKEN = original_crawl4ai_token
            config.FRIDA_MEMORY_DB_DSN = original_dsn
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            if original_psycopg is None:
                del sys.modules['psycopg']
            else:
                sys.modules['psycopg'] = original_psycopg
            runtime_settings.invalidate_runtime_settings_cache()

        self.assertNotIn('main_model.api_key', result['updated_fields'])
        self.assertEqual(
            result,
            {
                'updated_fields': ('database.dsn',),
                'updated_sections': ('database',),
            },
        )
        self.assertNotIn('sk-main-env-secret', observed['encrypted_inputs'])

    def test_validate_runtime_section_accepts_candidate_main_model_payload(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-validation'
        try:
            result = runtime_settings.validate_runtime_section(
                'main_model',
                {
                    'model': {'value': 'openrouter/validate-main'},
                    'temperature': {'value': 0.5},
                    'top_p': {'value': 0.8},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertTrue(result['valid'])
        self.assertEqual(result['section'], 'main_model')
        self.assertEqual(result['source'], 'candidate')
        self.assertEqual(result['source_reason'], 'validate_payload')
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['model']['ok'])
        self.assertTrue(checks['referer_llm']['ok'])
        self.assertTrue(checks['referer_validation_agent']['ok'])
        self.assertTrue(checks['temperature']['ok'])
        self.assertTrue(checks['top_p']['ok'])
        self.assertTrue(checks['api_key_runtime']['ok'])
        self.assertIn('env_fallback', checks['api_key_runtime']['detail'])

    def test_validate_runtime_section_rejects_invalid_component_referer(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-validation'
        try:
            result = runtime_settings.validate_runtime_section(
                'main_model',
                {
                    'referer_validation_agent': {'value': 'notaurl'},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertFalse(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertFalse(checks['referer_validation_agent']['ok'])
        self.assertIn('notaurl', checks['referer_validation_agent']['detail'])

    def test_validate_runtime_section_accepts_blank_component_referers_when_shared_referer_is_valid(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-validation'
        try:
            result = runtime_settings.validate_runtime_section(
                'main_model',
                {
                    'referer': {'value': 'https://shared.example/'},
                    'referer_llm': {'value': ''},
                    'referer_arbiter': {'value': ''},
                    'referer_identity_extractor': {'value': ''},
                    'referer_resumer': {'value': ''},
                    'referer_stimmung_agent': {'value': ''},
                    'referer_validation_agent': {'value': ''},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['referer']['ok'])
        self.assertTrue(checks['referer_llm']['ok'])
        self.assertTrue(checks['referer_validation_agent']['ok'])
        self.assertIn('shared_referer=https://shared.example/', checks['referer_llm']['detail'])

    def test_validate_runtime_section_rejects_blank_component_referers_without_shared_fallback(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-validation'
        try:
            result = runtime_settings.validate_runtime_section(
                'main_model',
                {
                    'referer': {'value': ''},
                    'referer_validation_agent': {'value': ''},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertFalse(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertFalse(checks['referer_validation_agent']['ok'])
        self.assertIn('shared_referer=missing', checks['referer_validation_agent']['detail'])

    def test_validate_runtime_section_accepts_candidate_main_model_secret_patch_from_db_encrypted(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value
        original_api_key = config.OR_KEY
        config.OR_KEY = ''

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = lambda value: 'cipher-main-model'
        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = lambda value: 'sk-candidate-main-model'
        try:
            result = runtime_settings.validate_runtime_section(
                'main_model',
                {
                    'api_key': {'replace_value': 'sk-candidate-main-model'},
                },
                fetcher=lambda: {},
            )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt
            config.OR_KEY = original_api_key

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['api_key_runtime']['ok'])
        self.assertIn('db_encrypted', checks['api_key_runtime']['detail'])

    def test_validate_runtime_section_accepts_candidate_stimmung_agent_model_payload(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-stimmung'
        try:
            result = runtime_settings.validate_runtime_section(
                'stimmung_agent_model',
                {
                    'primary_model': {'value': 'openai/gpt-5.4-mini'},
                    'fallback_model': {'value': 'openai/gpt-5.4-nano'},
                    'timeout_s': {'value': 11},
                    'temperature': {'value': 0.2},
                    'top_p': {'value': 0.95},
                    'max_tokens': {'value': 240},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['primary_model']['ok'])
        self.assertTrue(checks['fallback_model']['ok'])
        self.assertTrue(checks['timeout_s']['ok'])
        self.assertTrue(checks['temperature']['ok'])
        self.assertTrue(checks['top_p']['ok'])
        self.assertTrue(checks['max_tokens']['ok'])
        self.assertTrue(checks['shared_transport_runtime']['ok'])
        self.assertIn('main_model.api_key', checks['shared_transport_runtime']['detail'])

    def test_validate_runtime_section_accepts_candidate_validation_agent_model_payload(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-validation-agent'
        try:
            result = runtime_settings.validate_runtime_section(
                'validation_agent_model',
                {
                    'primary_model': {'value': 'openai/gpt-5.4-mini'},
                    'fallback_model': {'value': 'openai/gpt-5.4-nano'},
                    'timeout_s': {'value': 9},
                    'temperature': {'value': 0.0},
                    'top_p': {'value': 1.0},
                    'max_tokens': {'value': 80},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['primary_model']['ok'])
        self.assertTrue(checks['fallback_model']['ok'])
        self.assertTrue(checks['timeout_s']['ok'])
        self.assertTrue(checks['temperature']['ok'])
        self.assertTrue(checks['top_p']['ok'])
        self.assertTrue(checks['max_tokens']['ok'])
        self.assertTrue(checks['shared_transport_runtime']['ok'])
        self.assertIn('main_model.api_key', checks['shared_transport_runtime']['detail'])

    def test_validate_runtime_section_rejects_candidate_validation_agent_model_payload_above_contractual_max_tokens(self) -> None:
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-phase5-validation-agent'
        try:
            over_cap_result = runtime_settings.validate_runtime_section(
                'validation_agent_model',
                {
                    'primary_model': {'value': 'openai/gpt-5.4-mini'},
                    'fallback_model': {'value': 'openai/gpt-5.4-nano'},
                    'timeout_s': {'value': 9},
                    'temperature': {'value': 0.0},
                    'top_p': {'value': 1.0},
                    'max_tokens': {'value': 96},
                },
                fetcher=lambda: {},
            )
            probe_result = runtime_settings.validate_runtime_section(
                'validation_agent_model',
                {
                    'primary_model': {'value': 'openai/gpt-5.4-mini'},
                    'fallback_model': {'value': 'openai/gpt-5.4-nano'},
                    'timeout_s': {'value': 9},
                    'temperature': {'value': 0.0},
                    'top_p': {'value': 1.0},
                    'max_tokens': {'value': 2000},
                },
                fetcher=lambda: {},
            )
        finally:
            config.OR_KEY = original_api_key

        self.assertFalse(over_cap_result['valid'])
        over_cap_checks = {check['name']: check for check in over_cap_result['checks']}
        self.assertFalse(over_cap_checks['max_tokens']['ok'])
        self.assertIn('max_allowed=80', over_cap_checks['max_tokens']['detail'])

        self.assertFalse(probe_result['valid'])
        probe_checks = {check['name']: check for check in probe_result['checks']}
        self.assertFalse(probe_checks['max_tokens']['ok'])
        self.assertIn('max_tokens=2000', probe_checks['max_tokens']['detail'])
        self.assertIn('max_allowed=80', probe_checks['max_tokens']['detail'])

    def test_validate_runtime_section_accepts_candidate_embedding_secret_patch_from_db_encrypted(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value
        original_token = config.EMBED_TOKEN
        config.EMBED_TOKEN = ''

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = lambda value: 'cipher-embedding-token'
        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = lambda value: 'embed-candidate-token'
        try:
            result = runtime_settings.validate_runtime_section(
                'embedding',
                {
                    'token': {'replace_value': 'embed-candidate-token'},
                },
                fetcher=lambda: {},
            )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt
            config.EMBED_TOKEN = original_token

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['token_runtime']['ok'])
        self.assertIn('db_encrypted', checks['token_runtime']['detail'])

    def test_validate_runtime_section_accepts_candidate_services_secret_patch_from_db_encrypted(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        original_decrypt = runtime_settings.runtime_secrets.decrypt_runtime_secret_value
        original_token = config.CRAWL4AI_TOKEN
        config.CRAWL4AI_TOKEN = ''

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = lambda value: 'cipher-crawl4ai-token'
        runtime_settings.runtime_secrets.decrypt_runtime_secret_value = lambda value: 'crawl-candidate-token'
        try:
            result = runtime_settings.validate_runtime_section(
                'services',
                {
                    'crawl4ai_token': {'replace_value': 'crawl-candidate-token'},
                },
                fetcher=lambda: {},
            )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            runtime_settings.runtime_secrets.decrypt_runtime_secret_value = original_decrypt
            config.CRAWL4AI_TOKEN = original_token

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['crawl4ai_token_runtime']['ok'])
        self.assertIn('db_encrypted', checks['crawl4ai_token_runtime']['detail'])

    def test_validate_runtime_section_rejects_services_explicit_url_budget_below_default_crawl_budget(self) -> None:
        result = runtime_settings.validate_runtime_section(
            'services',
            {
                'crawl4ai_max_chars': {'value': 5000},
                'crawl4ai_explicit_url_max_chars': {'value': 4000},
            },
            fetcher=lambda: {},
        )

        self.assertFalse(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertFalse(checks['crawl4ai_explicit_url_max_chars']['ok'])
        self.assertIn('crawl4ai_explicit_url_max_chars=4000', checks['crawl4ai_explicit_url_max_chars']['detail'])

    def test_validate_runtime_section_does_not_echo_secret_value_when_encrypt_fails(self) -> None:
        original_encrypt = runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        secret_value = 'embed-secret-should-not-leak-via-validation'

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError(
                f'validation crypto error on {value}'
            )

        runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            with self.assertRaises(runtime_settings.RuntimeSettingsValidationError) as ctx:
                runtime_settings.validate_runtime_section(
                    'embedding',
                    {
                        'token': {'replace_value': secret_value},
                    },
                    fetcher=lambda: {},
                )
        finally:
            runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt

        self.assertEqual(str(ctx.exception), 'failed to encrypt secret for embedding.token')
        self.assertNotIn(secret_value, str(ctx.exception))

    def test_validate_runtime_section_reports_missing_resource_file(self) -> None:
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            existing = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            missing = tmp_path / 'app' / 'data' / 'identity' / 'missing.txt'
            existing.parent.mkdir(parents=True)
            existing.write_text('llm identity', encoding='utf-8')
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                result = runtime_settings.validate_runtime_section(
                    'resources',
                    {
                        'llm_identity_path': {'value': str(existing)},
                        'user_identity_path': {'value': str(missing)},
                    },
                    fetcher=lambda: {},
                )
            finally:
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertFalse(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['llm_identity_path']['ok'])
        self.assertFalse(checks['user_identity_path']['ok'])
        self.assertIn(str(missing), checks['user_identity_path']['detail'])
        self.assertIn('within_allowed_roots=False', checks['user_identity_path']['detail'])

    def test_validate_runtime_section_accepts_runtime_data_resource_files_via_host_state_mirror(self) -> None:
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / 'app').mkdir()
            identity_dir = tmp_path / 'state' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            (identity_dir / 'llm_identity.txt').write_text('llm identity mirror', encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text('user identity mirror', encoding='utf-8')

            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                result = runtime_settings.validate_runtime_section(
                    'resources',
                    {
                        'llm_identity_path': {'value': 'data/identity/llm_identity.txt'},
                        'user_identity_path': {'value': 'data/identity/user_identity.txt'},
                    },
                    fetcher=lambda: {},
                )
            finally:
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertTrue(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['llm_identity_path']['ok'])
        self.assertTrue(checks['user_identity_path']['ok'])
        self.assertIn('data/identity/llm_identity.txt', checks['llm_identity_path']['detail'])
        self.assertIn('resolution=host_state_mirror', checks['llm_identity_path']['detail'])
        self.assertIn('data/identity/user_identity.txt', checks['user_identity_path']['detail'])
        self.assertIn('resolution=host_state_mirror', checks['user_identity_path']['detail'])

    def test_validate_runtime_section_rejects_existing_resource_file_outside_allowed_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            outside = tmp_path / 'outside.txt'
            outside.write_text('outside identity file', encoding='utf-8')

            result = runtime_settings.validate_runtime_section(
                'resources',
                {
                    'llm_identity_path': {'value': str(outside)},
                    'user_identity_path': {'value': str(outside)},
                },
                fetcher=lambda: {},
            )

        self.assertFalse(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertFalse(checks['llm_identity_path']['ok'])
        self.assertFalse(checks['user_identity_path']['ok'])
        self.assertIn('resolution=absolute_outside_allowed_roots', checks['llm_identity_path']['detail'])
        self.assertIn('within_allowed_roots=False', checks['llm_identity_path']['detail'])

    def test_validate_runtime_section_requires_bootstrap_dsn_during_transition(self) -> None:
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        config.FRIDA_MEMORY_DB_DSN = ''
        try:
            result = runtime_settings.validate_runtime_section('database', fetcher=lambda: {})
        finally:
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertFalse(result['valid'])
        checks = {check['name']: check for check in result['checks']}
        self.assertTrue(checks['backend']['ok'])
        self.assertFalse(checks['dsn_transition']['ok'])

    def test_validate_runtime_section_identity_governance_enforces_core_invariants(self) -> None:
        valid = runtime_settings.validate_runtime_section(
            'identity_governance',
            {
                'IDENTITY_MIN_CONFIDENCE': {'value': 0.8},
                'IDENTITY_DEFER_MIN_CONFIDENCE': {'value': 0.6},
                'IDENTITY_MIN_RECURRENCE_FOR_DURABLE': {'value': 3},
                'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS': {'value': 2},
                'CONTEXT_HINTS_MAX_ITEMS': {'value': 3},
                'CONTEXT_HINTS_MAX_TOKENS': {'value': 256},
                'CONTEXT_HINTS_MAX_AGE_DAYS': {'value': 14},
                'CONTEXT_HINTS_MIN_CONFIDENCE': {'value': 0.7},
                'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS': {'value': 12},
            },
            fetcher=lambda: {},
        )
        invalid = runtime_settings.validate_runtime_section(
            'identity_governance',
            {
                'IDENTITY_MIN_CONFIDENCE': {'value': 0.7},
                'IDENTITY_DEFER_MIN_CONFIDENCE': {'value': 0.8},
            },
            fetcher=lambda: {},
        )

        self.assertTrue(valid['valid'])
        self.assertFalse(invalid['valid'])
        invalid_checks = {check['name']: check for check in invalid['checks']}
        self.assertFalse(invalid_checks['IDENTITY_DEFER_MIN_CONFIDENCE']['ok'])


if __name__ == '__main__':
    unittest.main()
