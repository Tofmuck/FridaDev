from __future__ import annotations

import json
import sys
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

from admin import runtime_settings
import config


class RuntimeSettingsBootstrapFromEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

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
                'identity_extractor_model',
                'identity_periodic_model',
                'memory_arbiter_model',
                'summary_model',
                'web_reformulation_model',
                'stimmung_agent_model',
                'validation_agent_model',
                'biblio_librarian_agent',
                'agenda_agent',
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
        self.assertEqual(len(runtime_payloads), 14)
        payload_by_section = dict(zip(result['inserted_sections'], runtime_payloads))
        self.assertEqual(payload_by_section['arbiter_model']['model']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['arbiter_model']['timeout_s']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['identity_extractor_model']['max_tokens']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['identity_periodic_model']['max_tokens']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['memory_arbiter_model']['max_tokens']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['summary_model']['model']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['stimmung_agent_model']['primary_model']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['validation_agent_model']['fallback_model']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['biblio_librarian_agent']['primary_model']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['agenda_agent']['mode']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['database']['backend']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['services']['searxng_url']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['resources']['llm_identity_path']['origin'], 'db_seed')
        self.assertEqual(payload_by_section['identity_governance']['CONTEXT_HINTS_MAX_ITEMS']['origin'], 'db_seed')

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
                payload.pop('referer_web_reformulation', None)
                payload.pop('referer_web_discovery', None)
                payload.pop('referer_arbiter', None)
                payload.pop('referer_identity_extractor', None)
                payload.pop('referer_identity_periodic', None)
                payload.pop('referer_resumer', None)
                payload.pop('referer_stimmung_agent', None)
                payload.pop('referer_validation_agent', None)
                payload.pop('title_web_reformulation', None)
                payload.pop('title_web_discovery', None)
                payload.pop('title_identity_periodic', None)
                payload.pop('reasoning_effort', None)
            if section == 'summary_model':
                payload = dict(payload)
                payload.pop('max_tokens', None)
                payload.pop('timeout_s', None)
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
        self.assertEqual(result['updated_sections'], ('main_model', 'summary_model'))
        self.assertEqual(
            result['updated_fields'],
            (
                'main_model.referer_llm',
                'main_model.referer_web_reformulation',
                'main_model.referer_web_discovery',
                'main_model.referer_arbiter',
                'main_model.referer_identity_extractor',
                'main_model.referer_identity_periodic',
                'main_model.referer_resumer',
                'main_model.referer_stimmung_agent',
                'main_model.referer_validation_agent',
                'main_model.title_web_reformulation',
                'main_model.title_web_discovery',
                'main_model.title_identity_periodic',
                'main_model.response_max_tokens',
                'main_model.reasoning_effort',
                'summary_model.max_tokens',
                'summary_model.timeout_s',
            ),
        )

        updated_payloads = [
            json.loads(params[2])
            for query, params in zip(observed['queries'], observed['params'])
            if params and 'INSERT INTO runtime_settings (section' in query
        ]
        self.assertEqual(len(updated_payloads), 2)
        self.assertEqual(updated_payloads[0]['referer_llm']['value'], config.OR_REFERER_LLM)
        self.assertEqual(updated_payloads[0]['referer_llm']['origin'], 'db_seed')
        self.assertEqual(
            updated_payloads[0]['referer_web_reformulation']['value'],
            config.OR_REFERER_WEB_REFORMULATION,
        )
        self.assertEqual(updated_payloads[0]['title_web_reformulation']['value'], config.OR_TITLE_WEB_REFORMULATION)
        self.assertEqual(updated_payloads[0]['referer_web_discovery']['value'], config.OR_REFERER_WEB_DISCOVERY)
        self.assertEqual(updated_payloads[0]['title_web_discovery']['value'], config.OR_TITLE_WEB_DISCOVERY)
        self.assertEqual(updated_payloads[0]['response_max_tokens']['value'], 8192)
        self.assertEqual(updated_payloads[0]['response_max_tokens']['origin'], 'db_seed')
        self.assertEqual(updated_payloads[0]['reasoning_effort']['value'], 'high')
        self.assertEqual(updated_payloads[0]['reasoning_effort']['origin'], 'db_seed')
        self.assertEqual(updated_payloads[1]['max_tokens']['value'], config.SUMMARY_TARGET_TOKENS)
        self.assertEqual(updated_payloads[1]['max_tokens']['origin'], 'db_seed')
        self.assertEqual(updated_payloads[1]['timeout_s']['value'], config.SUMMARY_TIMEOUT_S)
        self.assertEqual(updated_payloads[1]['timeout_s']['origin'], 'db_seed')


if __name__ == '__main__':
    unittest.main()
