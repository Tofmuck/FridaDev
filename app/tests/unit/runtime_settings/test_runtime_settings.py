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

from admin import runtime_settings, runtime_settings_repo, runtime_settings_spec
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


if __name__ == '__main__':
    unittest.main()
