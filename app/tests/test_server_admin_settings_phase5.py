from __future__ import annotations

import importlib
import logging
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
from core import conv_store
from memory import memory_store


class ServerAdminSettingsPhase5Tests(unittest.TestCase):
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
        runtime_settings.invalidate_runtime_settings_cache()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original_log_path = self.server.admin_logs.LOG_PATH
        self._original_bootstrap_done = self.server.admin_logs._BOOTSTRAP_DONE
        temp_log_path = Path(self._tmpdir.name) / 'admin.log.jsonl'
        admin_logs.LOG_PATH = temp_log_path
        admin_logs._BOOTSTRAP_DONE = True
        self.server.admin_logs.LOG_PATH = temp_log_path
        self.server.admin_logs._BOOTSTRAP_DONE = True
        self.client = self.server.app.test_client()

    def tearDown(self) -> None:
        admin_logs.LOG_PATH = self._original_log_path
        admin_logs._BOOTSTRAP_DONE = self._original_bootstrap_done
        self.server.admin_logs.LOG_PATH = self._original_log_path
        self.server.admin_logs._BOOTSTRAP_DONE = self._original_bootstrap_done
        self._tmpdir.cleanup()

    def test_get_admin_settings_returns_aggregated_sections_with_redacted_secrets(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            if section == 'main_model':
                payload = {
                    'model': {'value': 'openrouter/test-runtime-model', 'is_secret': False, 'origin': 'db'},
                    'response_max_tokens': {'value': 1500, 'is_secret': False, 'origin': 'db_seed'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                }
                return runtime_settings.RuntimeSectionView(
                    section=section,
                    payload=payload,
                    source='db',
                    source_reason='db_row',
                )
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={},
                source='env',
                source_reason='empty_table',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(set(data['sections'].keys()), set(runtime_settings.list_sections()))
        self.assertEqual(
            data['sections']['main_model']['payload']['model']['value'],
            'openrouter/test-runtime-model',
        )
        self.assertEqual(
            data['sections']['main_model']['payload']['response_max_tokens']['value'],
            1500,
        )
        self.assertEqual(
            data['sections']['main_model']['payload']['api_key'],
            {'is_secret': True, 'is_set': True, 'origin': 'db'},
        )
        self.assertEqual(
            data['sections']['main_model']['readonly_info']['context_max_tokens']['label'],
            'FRIDA_MAX_TOKENS',
        )
        self.assertIn(
            'Cadre de réponse',
            data['sections']['main_model']['readonly_info']['system_prompt']['value'],
        )
        self.assertEqual(
            data['sections']['arbiter_model']['readonly_info']['decision_max_tokens']['value'],
            600,
        )
        self.assertEqual(
            data['sections']['arbiter_model']['readonly_info']['identity_extractor_max_tokens']['value'],
            700,
        )
        self.assertIn(
            'You are a conversational memory arbiter.',
            data['sections']['arbiter_model']['readonly_info']['arbiter_prompt']['value'],
        )
        self.assertEqual(
            data['sections']['summary_model']['readonly_info']['summary_target_tokens']['value'],
            runtime_settings.config.SUMMARY_TARGET_TOKENS,
        )
        self.assertIn(
            'Tu es un assistant de synthèse.',
            data['sections']['summary_model']['readonly_info']['system_prompt']['value'],
        )
        self.assertEqual(
            data['sections']['services']['readonly_info']['web_reformulation_max_tokens']['value'],
            40,
        )
        self.assertIn(
            'Nous sommes le {today}.',
            data['sections']['services']['readonly_info']['web_reformulation_system_prompt']['value'],
        )
        self.assertEqual(data['sections']['main_model']['secret_sources']['api_key'], 'db_encrypted')

    def test_get_admin_settings_status_returns_bootstrap_and_section_sources(self) -> None:
        original_get_status = self.server.runtime_settings.get_runtime_status

        def fake_get_runtime_status():
            return {
                'db_state': 'db_rows',
                'bootstrap': {
                    'database_dsn_source': 'env',
                    'database_dsn_env_var': 'FRIDA_MEMORY_DB_DSN',
                    'database_dsn_mode': 'external_bootstrap',
                },
                'sections': {
                    'main_model': {'source': 'db', 'source_reason': 'db_row'},
                    'services': {'source': 'env', 'source_reason': 'missing_section'},
                },
            }

        self.server.runtime_settings.get_runtime_status = fake_get_runtime_status
        try:
            response = self.client.get('/api/admin/settings/status')
        finally:
            self.server.runtime_settings.get_runtime_status = original_get_status

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['db_state'], 'db_rows')
        self.assertEqual(data['bootstrap']['database_dsn_source'], 'env')
        self.assertEqual(data['bootstrap']['database_dsn_env_var'], 'FRIDA_MEMORY_DB_DSN')
        self.assertEqual(data['sections']['main_model'], {'source': 'db', 'source_reason': 'db_row'})
        self.assertEqual(data['sections']['services'], {'source': 'env', 'source_reason': 'missing_section'})

    def test_get_admin_settings_main_model_returns_single_section_with_redacted_secrets(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'main_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/main-model-route', 'is_secret': False, 'origin': 'db'},
                    'response_max_tokens': {'value': 1500, 'is_secret': False, 'origin': 'db_seed'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/main-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'main_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/main-model-route')
        self.assertEqual(data['payload']['response_max_tokens']['value'], 1500)
        self.assertEqual(
            data['payload']['api_key'],
            {'is_secret': True, 'is_set': True, 'origin': 'db'},
        )
        self.assertEqual(data['readonly_info']['context_max_tokens']['label'], 'FRIDA_MAX_TOKENS')
        self.assertIn('Cadre de réponse', data['readonly_info']['system_prompt']['value'])
        self.assertEqual(data['secret_sources']['api_key'], 'db_encrypted')

    def test_get_admin_settings_arbiter_model_returns_single_section(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'arbiter_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/arbiter-route', 'is_secret': False, 'origin': 'db'},
                    'timeout_s': {'value': 12, 'is_secret': False, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/arbiter-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'arbiter_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/arbiter-route')
        self.assertEqual(data['payload']['timeout_s']['value'], 12)
        self.assertEqual(data['readonly_info']['decision_max_tokens']['value'], 600)
        self.assertEqual(data['readonly_info']['identity_extractor_max_tokens']['value'], 700)
        self.assertEqual(data['readonly_info']['arbiter_prompt_path']['value'], 'prompts/arbiter.txt')
        self.assertEqual(
            data['readonly_info']['identity_extractor_prompt_path']['value'],
            'prompts/identity_extractor.txt',
        )
        self.assertIn(
            'You are a conversational memory arbiter.',
            data['readonly_info']['arbiter_prompt']['value'],
        )
        self.assertIn(
            'You are an identity evidence extractor.',
            data['readonly_info']['identity_extractor_prompt']['value'],
        )

    def test_get_admin_settings_summary_model_returns_single_section(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'summary_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/summary-route', 'is_secret': False, 'origin': 'db'},
                    'temperature': {'value': 0.3, 'is_secret': False, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/summary-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'summary_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/summary-route')
        self.assertEqual(data['payload']['temperature']['value'], 0.3)
        self.assertEqual(
            data['readonly_info']['summary_target_tokens']['value'],
            runtime_settings.config.SUMMARY_TARGET_TOKENS,
        )
        self.assertEqual(
            data['readonly_info']['summary_threshold_tokens']['value'],
            runtime_settings.config.SUMMARY_THRESHOLD_TOKENS,
        )
        self.assertEqual(
            data['readonly_info']['summary_keep_turns']['value'],
            runtime_settings.config.SUMMARY_KEEP_TURNS,
        )
        self.assertIn(
            'Tu es un assistant de synthèse.',
            data['readonly_info']['system_prompt']['value'],
        )

    def test_get_admin_settings_embedding_returns_single_section_with_redacted_secret(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'embedding')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'endpoint': {'value': 'https://embed.override.example', 'is_secret': False, 'origin': 'db'},
                    'model': {'value': 'intfloat/multilingual-e5-small', 'is_secret': False, 'origin': 'db'},
                    'token': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/embedding')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'embedding')
        self.assertEqual(data['payload']['endpoint']['value'], 'https://embed.override.example')
        self.assertEqual(data['payload']['token'], {'is_secret': True, 'is_set': True, 'origin': 'db'})
        self.assertEqual(data['secret_sources']['token'], 'db_encrypted')

    def test_get_admin_settings_database_returns_single_section_with_redacted_secret(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'database')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'backend': {'value': 'postgresql', 'is_secret': False, 'origin': 'db'},
                    'dsn': {'is_secret': True, 'is_set': False, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/database')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'database')
        self.assertEqual(data['payload']['backend']['value'], 'postgresql')
        self.assertEqual(data['payload']['dsn'], {'is_secret': True, 'is_set': False, 'origin': 'db'})
        self.assertEqual(data['secret_sources']['dsn'], 'env_fallback')

    def test_get_admin_settings_services_returns_single_section_with_redacted_secret(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'services')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'searxng_url': {'value': 'http://127.0.0.1:8092', 'is_secret': False, 'origin': 'db'},
                    'crawl4ai_token': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/services')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'services')
        self.assertEqual(data['payload']['searxng_url']['value'], 'http://127.0.0.1:8092')
        self.assertEqual(data['payload']['crawl4ai_token'], {'is_secret': True, 'is_set': True, 'origin': 'db'})
        self.assertEqual(data['readonly_info']['web_reformulation_max_tokens']['value'], 40)
        self.assertIn(
            'Nous sommes le {today}.',
            data['readonly_info']['web_reformulation_system_prompt']['value'],
        )
        self.assertIn(
            'Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.',
            data['readonly_info']['web_reformulation_system_prompt']['value'],
        )
        self.assertEqual(data['secret_sources']['crawl4ai_token'], 'db_encrypted')

    def test_get_admin_settings_resources_returns_single_section(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'resources')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'is_secret': False, 'origin': 'db'},
                    'user_identity_path': {'value': 'data/identity/user_identity.txt', 'is_secret': False, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/resources')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'resources')
        self.assertEqual(data['payload']['llm_identity_path']['value'], 'data/identity/llm_identity.txt')
        self.assertEqual(data['payload']['user_identity_path']['value'], 'data/identity/user_identity.txt')

    def test_all_get_admin_settings_routes_mask_secret_fields(self) -> None:
        original_fetcher = self.server.runtime_settings._default_db_fetch_all_sections

        fake_rows = {
            'main_model': runtime_settings.normalize_stored_payload(
                'main_model',
                {
                    'model': {'value': 'openrouter/db-main', 'origin': 'db'},
                    'api_key': {'value_encrypted': 'cipher-main', 'origin': 'db'},
                },
            ),
            'embedding': runtime_settings.normalize_stored_payload(
                'embedding',
                {
                    'endpoint': {'value': 'https://embed.override.example', 'origin': 'db'},
                    'model': {'value': 'intfloat/multilingual-e5-small', 'origin': 'db'},
                    'token': {'value_encrypted': 'cipher-embed', 'origin': 'db'},
                    'dimensions': {'value': 384, 'origin': 'db'},
                    'top_k': {'value': 9, 'origin': 'db'},
                },
            ),
            'database': runtime_settings.normalize_stored_payload(
                'database',
                {
                    'backend': {'value': 'postgresql', 'origin': 'db'},
                    'dsn': {'value_encrypted': 'cipher-dsn', 'origin': 'db'},
                },
            ),
            'services': runtime_settings.normalize_stored_payload(
                'services',
                {
                    'searxng_url': {'value': 'http://127.0.0.1:8092', 'origin': 'db'},
                    'searxng_results': {'value': 5, 'origin': 'db'},
                    'crawl4ai_url': {'value': 'http://127.0.0.1:11235', 'origin': 'db'},
                    'crawl4ai_token': {'value_encrypted': 'cipher-crawl', 'origin': 'db'},
                    'crawl4ai_top_n': {'value': 2, 'origin': 'db'},
                    'crawl4ai_max_chars': {'value': 5000, 'origin': 'db'},
                },
            ),
        }

        def fake_fetcher():
            return fake_rows

        def assert_secret_payload_masked(section: str, payload: dict) -> None:
            secret_fields = [
                field.key
                for field in runtime_settings.get_section_spec(section).fields
                if field.is_secret
            ]
            for field_name in secret_fields:
                secret_payload = payload[field_name]
                self.assertEqual(
                    set(secret_payload.keys()),
                    {'is_secret', 'is_set', 'origin'},
                    msg=f'unexpected keys in masked secret payload for {section}.{field_name}: {secret_payload}',
                )
                self.assertTrue(secret_payload['is_secret'])
                self.assertIsInstance(secret_payload['is_set'], bool)

        self.server.runtime_settings._default_db_fetch_all_sections = fake_fetcher
        self.server.runtime_settings.invalidate_runtime_settings_cache()
        try:
            aggregated = self.client.get('/api/admin/settings')
            self.assertEqual(aggregated.status_code, 200)
            aggregated_data = aggregated.get_json()
            self.assertTrue(aggregated_data['ok'])
            for section in ('main_model', 'embedding', 'database', 'services'):
                assert_secret_payload_masked(
                    section,
                    aggregated_data['sections'][section]['payload'],
                )

            for path, section in (
                ('/api/admin/settings/main-model', 'main_model'),
                ('/api/admin/settings/embedding', 'embedding'),
                ('/api/admin/settings/database', 'database'),
                ('/api/admin/settings/services', 'services'),
            ):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, msg=path)
                data = response.get_json()
                self.assertTrue(data['ok'])
                assert_secret_payload_masked(section, data['payload'])
        finally:
            self.server.runtime_settings._default_db_fetch_all_sections = original_fetcher
            self.server.runtime_settings.invalidate_runtime_settings_cache()

    def test_get_admin_settings_is_protected_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase5-admin-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            unauthorized = self.client.get('/api/admin/settings')
            authorized = self.client.get(
                '/api/admin/settings',
                headers={'X-Admin-Token': 'phase5-admin-token'},
            )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)

    def test_all_admin_settings_routes_are_protected_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase5-admin-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            guarded_rules = []
            for rule in self.server.app.url_map.iter_rules():
                if not rule.rule.startswith('/api/admin/settings'):
                    continue
                methods = sorted(method for method in rule.methods if method in {'GET', 'PATCH', 'POST'})
                for method in methods:
                    guarded_rules.append((method, rule.rule))

            self.assertTrue(guarded_rules)

            for method, path in guarded_rules:
                kwargs = {}
                if method in {'PATCH', 'POST'}:
                    kwargs['json'] = {}
                response = self.client.open(path, method=method, **kwargs)
                self.assertEqual(
                    response.status_code,
                    401,
                    msg=f'expected admin guard on {method} {path}, got {response.status_code}',
                )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only

    def test_patch_admin_settings_main_model_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/patched-main-model', 'is_secret': False, 'origin': 'admin_ui'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'env_seed'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/main-model',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'model': {'value': 'openrouter/patched-main-model'},
                        'temperature': {'value': 0.4},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'main_model')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'model': {'value': 'openrouter/patched-main-model'},
                'temperature': {'value': 0.4},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'main_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/patched-main-model')
        self.assertEqual(data['payload']['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'env_seed'})
        self.assertEqual(data['secret_sources']['api_key'], 'env_fallback')

    def test_patch_admin_settings_main_model_rejects_invalid_payload(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/main-model',
            json={'payload': {'api_key': {'value': 'sk-secret'}}},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('ambiguous secret patch payload', data['error'])

    def test_patch_admin_settings_main_model_rejects_top_level_readonly_info(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/main-model',
            json={
                'payload': {'model': {'value': 'openrouter/test'}},
                'readonly_info': {'system_prompt': {'value': 'should-not-pass'}},
            },
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'readonly_info is read-only and cannot be patched')

    def test_patch_admin_settings_main_model_rejects_payload_readonly_info(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/main-model',
            json={
                'payload': {
                    'model': {'value': 'openrouter/test'},
                    'readonly_info': {'system_prompt': {'value': 'should-not-pass'}},
                },
            },
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'readonly_info is read-only and cannot be patched')

    def test_patch_admin_settings_main_model_updates_response_max_tokens(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/patched-main-model', 'is_secret': False, 'origin': 'db'},
                    'response_max_tokens': {'value': 4096, 'is_secret': False, 'origin': 'admin_ui'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/main-model',
                json={
                    'updated_by': 'phase12-admin',
                    'payload': {
                        'response_max_tokens': {'value': 4096},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'main_model')
        self.assertEqual(observed['updated_by'], 'phase12-admin')
        self.assertEqual(observed['payload'], {'response_max_tokens': {'value': 4096}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['payload']['response_max_tokens']['value'], 4096)
        self.assertEqual(data['payload']['response_max_tokens']['origin'], 'admin_ui')
        self.assertEqual(data['secret_sources']['api_key'], 'db_encrypted')

    def test_patch_admin_settings_main_model_accepts_secret_replace_value(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/patched-main-model', 'is_secret': False, 'origin': 'db'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/main-model',
                json={
                    'updated_by': 'phase5bis-admin',
                    'payload': {
                        'api_key': {'replace_value': 'sk-main-replaced'},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'main_model')
        self.assertEqual(observed['updated_by'], 'phase5bis-admin')
        self.assertEqual(observed['payload'], {'api_key': {'replace_value': 'sk-main-replaced'}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['payload']['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'})
        self.assertEqual(data['secret_sources']['api_key'], 'db_encrypted')

    def test_patch_admin_settings_arbiter_model_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/arbiter-patched', 'is_secret': False, 'origin': 'admin_ui'},
                    'timeout_s': {'value': 8, 'is_secret': False, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/arbiter-model',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'model': {'value': 'openrouter/arbiter-patched'},
                        'timeout_s': {'value': 8},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'arbiter_model')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'model': {'value': 'openrouter/arbiter-patched'},
                'timeout_s': {'value': 8},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'arbiter_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/arbiter-patched')
        self.assertEqual(data['payload']['timeout_s']['value'], 8)

    def test_patch_admin_settings_summary_model_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/summary-patched', 'is_secret': False, 'origin': 'admin_ui'},
                    'temperature': {'value': 0.15, 'is_secret': False, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/summary-model',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'model': {'value': 'openrouter/summary-patched'},
                        'temperature': {'value': 0.15},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'summary_model')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'model': {'value': 'openrouter/summary-patched'},
                'temperature': {'value': 0.15},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'summary_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/summary-patched')
        self.assertEqual(data['payload']['temperature']['value'], 0.15)

    def test_patch_admin_settings_embedding_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'endpoint': {'value': 'https://embed.next.example', 'is_secret': False, 'origin': 'admin_ui'},
                    'model': {'value': 'intfloat/multilingual-e5-small', 'is_secret': False, 'origin': 'admin_ui'},
                    'dimensions': {'value': 384, 'is_secret': False, 'origin': 'admin_ui'},
                    'token': {'is_secret': True, 'is_set': True, 'origin': 'env_seed'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/embedding',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'endpoint': {'value': 'https://embed.next.example'},
                        'dimensions': {'value': 384},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'embedding')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'endpoint': {'value': 'https://embed.next.example'},
                'dimensions': {'value': 384},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'embedding')
        self.assertEqual(data['payload']['endpoint']['value'], 'https://embed.next.example')
        self.assertEqual(data['payload']['token'], {'is_secret': True, 'is_set': True, 'origin': 'env_seed'})
        self.assertEqual(data['secret_sources']['token'], 'env_fallback')

    def test_patch_admin_settings_embedding_accepts_secret_replace_value(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'endpoint': {'value': 'https://embed.next.example', 'is_secret': False, 'origin': 'db'},
                    'token': {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/embedding',
                json={
                    'updated_by': 'phase5bis-admin',
                    'payload': {
                        'token': {'replace_value': 'embed-secret-replaced'},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'embedding')
        self.assertEqual(observed['updated_by'], 'phase5bis-admin')
        self.assertEqual(observed['payload'], {'token': {'replace_value': 'embed-secret-replaced'}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['payload']['token'], {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'})
        self.assertEqual(data['secret_sources']['token'], 'db_encrypted')

    def test_patch_admin_settings_database_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'backend': {'value': 'postgresql', 'is_secret': False, 'origin': 'admin_ui'},
                    'dsn': {'is_secret': True, 'is_set': False, 'origin': 'env_seed'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/database',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'backend': {'value': 'postgresql'},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'database')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(observed['payload'], {'backend': {'value': 'postgresql'}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'database')
        self.assertEqual(data['payload']['backend']['value'], 'postgresql')
        self.assertEqual(data['payload']['dsn'], {'is_secret': True, 'is_set': False, 'origin': 'env_seed'})
        self.assertEqual(data['secret_sources']['dsn'], 'env_fallback')

    def test_patch_admin_settings_database_accepts_secret_replace_value(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'backend': {'value': 'postgresql', 'is_secret': False, 'origin': 'db'},
                    'dsn': {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/database',
                json={
                    'updated_by': 'phase5bis-admin',
                    'payload': {
                        'dsn': {'replace_value': 'postgresql://user:pass@host/db'},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'database')
        self.assertEqual(observed['updated_by'], 'phase5bis-admin')
        self.assertEqual(observed['payload'], {'dsn': {'replace_value': 'postgresql://user:pass@host/db'}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['payload']['dsn'], {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'})
        self.assertEqual(data['secret_sources']['dsn'], 'env_fallback')

    def test_patch_admin_settings_services_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'searxng_url': {'value': 'http://127.0.0.1:8093', 'is_secret': False, 'origin': 'admin_ui'},
                    'crawl4ai_max_chars': {'value': 6000, 'is_secret': False, 'origin': 'admin_ui'},
                    'crawl4ai_token': {'is_secret': True, 'is_set': True, 'origin': 'env_seed'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/services',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'searxng_url': {'value': 'http://127.0.0.1:8093'},
                        'crawl4ai_max_chars': {'value': 6000},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'services')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'searxng_url': {'value': 'http://127.0.0.1:8093'},
                'crawl4ai_max_chars': {'value': 6000},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'services')
        self.assertEqual(data['payload']['searxng_url']['value'], 'http://127.0.0.1:8093')
        self.assertEqual(data['payload']['crawl4ai_token'], {'is_secret': True, 'is_set': True, 'origin': 'env_seed'})
        self.assertEqual(data['secret_sources']['crawl4ai_token'], 'env_fallback')

    def test_patch_admin_settings_services_accepts_secret_replace_value(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'searxng_url': {'value': 'http://127.0.0.1:8093', 'is_secret': False, 'origin': 'db'},
                    'crawl4ai_token': {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/services',
                json={
                    'updated_by': 'phase5bis-admin',
                    'payload': {
                        'crawl4ai_token': {'replace_value': 'crawl-secret-replaced'},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'services')
        self.assertEqual(observed['updated_by'], 'phase5bis-admin')
        self.assertEqual(observed['payload'], {'crawl4ai_token': {'replace_value': 'crawl-secret-replaced'}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['payload']['crawl4ai_token'], {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'})
        self.assertEqual(data['secret_sources']['crawl4ai_token'], 'db_encrypted')

    def test_patch_admin_settings_resources_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'llm_identity_path': {'value': 'data/identity/llm_identity.next.txt', 'is_secret': False, 'origin': 'admin_ui'},
                    'user_identity_path': {'value': 'data/identity/user_identity.next.txt', 'is_secret': False, 'origin': 'admin_ui'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/resources',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'llm_identity_path': {'value': 'data/identity/llm_identity.next.txt'},
                        'user_identity_path': {'value': 'data/identity/user_identity.next.txt'},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'resources')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'llm_identity_path': {'value': 'data/identity/llm_identity.next.txt'},
                'user_identity_path': {'value': 'data/identity/user_identity.next.txt'},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'resources')
        self.assertEqual(data['payload']['llm_identity_path']['value'], 'data/identity/llm_identity.next.txt')
        self.assertEqual(data['payload']['user_identity_path']['value'], 'data/identity/user_identity.next.txt')

    def test_patch_admin_settings_secret_values_are_not_logged_in_clear(self) -> None:
        class CaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.messages = []

            def emit(self, record):
                self.messages.append(record.getMessage())

        secret_value = 'sk-phase5-secret-should-never-be-logged'
        cases = (
            ('/api/admin/settings/main-model', {'api_key': {'value': secret_value}}),
            ('/api/admin/settings/embedding', {'token': {'value': secret_value}}),
            ('/api/admin/settings/database', {'dsn': {'value': secret_value}}),
            ('/api/admin/settings/services', {'crawl4ai_token': {'value': secret_value}}),
        )

        capture = CaptureHandler()
        target_loggers = (
            logging.getLogger(),
            logging.getLogger('frida.server'),
            logging.getLogger('kiki.adminlog'),
        )
        for logger in target_loggers:
            logger.addHandler(capture)

        try:
            for path, payload in cases:
                response = self.client.patch(path, json={'payload': payload})
                self.assertEqual(response.status_code, 400, msg=path)
                body = response.get_data(as_text=True)
                self.assertNotIn(secret_value, body, msg=path)
                self.assertTrue(
                    'ambiguous secret patch payload' in body or 'missing runtime settings crypto key' in body,
                    msg=body,
                )
        finally:
            for logger in target_loggers:
                logger.removeHandler(capture)

        if self.server.admin_logs.LOG_PATH.exists():
            admin_log_text = self.server.admin_logs.LOG_PATH.read_text(encoding='utf-8')
            self.assertNotIn(secret_value, admin_log_text)

        self.assertFalse(
            any(secret_value in message for message in capture.messages),
            msg=f'secret leaked to log records: {capture.messages!r}',
        )

    def test_patch_admin_settings_encrypt_error_does_not_echo_secret_value(self) -> None:
        class CaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.messages = []

            def emit(self, record):
                self.messages.append(record.getMessage())

        secret_value = 'sk-should-not-leak-from-patch-error'
        original_encrypt = self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        capture = CaptureHandler()
        target_loggers = (
            logging.getLogger(),
            logging.getLogger('frida.server'),
            logging.getLogger('kiki.adminlog'),
        )
        for logger in target_loggers:
            logger.addHandler(capture)

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise self.server.runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError(
                f'crypto engine exploded on {value}'
            )

        self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            response = self.client.patch(
                '/api/admin/settings/main-model',
                json={'payload': {'api_key': {'replace_value': secret_value}}},
            )
        finally:
            self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            for logger in target_loggers:
                logger.removeHandler(capture)

        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn('failed to encrypt secret for main_model.api_key', body)
        self.assertNotIn(secret_value, body)
        if self.server.admin_logs.LOG_PATH.exists():
            admin_log_text = self.server.admin_logs.LOG_PATH.read_text(encoding='utf-8')
            self.assertNotIn(secret_value, admin_log_text)
        self.assertFalse(
            any(secret_value in message for message in capture.messages),
            msg=f'secret leaked to log records: {capture.messages!r}',
        )

    def test_admin_logs_route_keeps_legacy_contract(self) -> None:
        original_read_logs = self.server.admin_logs.read_logs
        observed = {'limit': None}

        def fake_read_logs(limit=200):
            observed['limit'] = limit
            return [{'event': 'legacy-log', 'level': 'INFO'}]

        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/logs?limit=5')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['limit'], 5)
        data = response.get_json()
        self.assertEqual(
            data,
            {
                'ok': True,
                'logs': [{'event': 'legacy-log', 'level': 'INFO'}],
            },
        )

    def test_admin_restart_route_keeps_legacy_contract(self) -> None:
        original_restart = self.server.admin_actions.restart_runtime_async
        observed = {'target': None}

        def fake_restart_runtime_async(target):
            observed['target'] = target

        self.server.admin_actions.restart_runtime_async = fake_restart_runtime_async
        try:
            response = self.client.post('/api/admin/restart')
        finally:
            self.server.admin_actions.restart_runtime_async = original_restart

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['target'], 'FridaDev')
        data = response.get_json()
        self.assertEqual(
            data,
            {
                'ok': True,
                'target': 'FridaDev',
                'mode': 'container_self_exit',
            },
        )

    def test_hermeneutics_and_settings_routes_stay_separated(self) -> None:
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}

        settings_routes = {
            route for route in routes
            if route.startswith('/api/admin/settings')
        }
        hermeneutics_routes = {
            route for route in routes
            if route.startswith('/api/admin/hermeneutics')
        }

        self.assertEqual(
            hermeneutics_routes,
            {
                '/api/admin/hermeneutics/identity-candidates',
                '/api/admin/hermeneutics/arbiter-decisions',
                '/api/admin/hermeneutics/identity/force-accept',
                '/api/admin/hermeneutics/identity/force-reject',
                '/api/admin/hermeneutics/identity/relabel',
                '/api/admin/hermeneutics/dashboard',
                '/api/admin/hermeneutics/corrections-export',
            },
        )
        self.assertTrue(settings_routes)
        self.assertTrue(hermeneutics_routes)
        self.assertTrue(settings_routes.isdisjoint(hermeneutics_routes))
        self.assertFalse(any('hermeneutics' in route for route in settings_routes))
        self.assertFalse(any('/settings' in route for route in hermeneutics_routes))

    def test_all_admin_settings_validate_routes_are_registered(self) -> None:
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn('/api/admin/settings/main-model/validate', routes)
        self.assertIn('/api/admin/settings/arbiter-model/validate', routes)
        self.assertIn('/api/admin/settings/summary-model/validate', routes)
        self.assertIn('/api/admin/settings/embedding/validate', routes)
        self.assertIn('/api/admin/settings/database/validate', routes)
        self.assertIn('/api/admin/settings/services/validate', routes)
        self.assertIn('/api/admin/settings/resources/validate', routes)

    def test_post_admin_settings_validate_uses_runtime_validation_result(self) -> None:
        observed = {'section': None, 'payload': None}
        original_validate = self.server.runtime_settings.validate_runtime_section

        def fake_validate_runtime_section(section, patch_payload=None, *, fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            return {
                'section': section,
                'valid': True,
                'source': 'candidate',
                'source_reason': 'validate_payload',
                'checks': [
                    {'name': 'endpoint', 'ok': True, 'detail': 'endpoint=https://embed.next.example'},
                    {'name': 'dimensions', 'ok': True, 'detail': 'dimensions=384'},
                ],
            }

        self.server.runtime_settings.validate_runtime_section = fake_validate_runtime_section
        try:
            response = self.client.post(
                '/api/admin/settings/embedding/validate',
                json={
                    'payload': {
                        'endpoint': {'value': 'https://embed.next.example'},
                        'dimensions': {'value': 384},
                    },
                },
            )
        finally:
            self.server.runtime_settings.validate_runtime_section = original_validate

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'embedding')
        self.assertEqual(
            observed['payload'],
            {
                'endpoint': {'value': 'https://embed.next.example'},
                'dimensions': {'value': 384},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['valid'])
        self.assertEqual(data['section'], 'embedding')
        self.assertEqual(data['source'], 'candidate')
        self.assertEqual(data['source_reason'], 'validate_payload')
        self.assertEqual(len(data['checks']), 2)

    def test_post_admin_settings_validate_rejects_invalid_payload(self) -> None:
        response = self.client.post(
            '/api/admin/settings/main-model/validate',
            json={'payload': {'api_key': {'value': 'sk-secret'}}},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('ambiguous secret patch payload', data['error'])

    def test_post_admin_settings_validate_encrypt_error_does_not_echo_secret_value(self) -> None:
        class CaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.messages = []

            def emit(self, record):
                self.messages.append(record.getMessage())

        secret_value = 'embed-secret-should-not-leak-from-validate-error'
        original_encrypt = self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        capture = CaptureHandler()
        target_loggers = (
            logging.getLogger(),
            logging.getLogger('frida.server'),
            logging.getLogger('kiki.adminlog'),
        )
        for logger in target_loggers:
            logger.addHandler(capture)

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise self.server.runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError(
                f'validate crypto failure on {value}'
            )

        self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            response = self.client.post(
                '/api/admin/settings/embedding/validate',
                json={'payload': {'token': {'replace_value': secret_value}}},
            )
        finally:
            self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            for logger in target_loggers:
                logger.removeHandler(capture)

        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn('failed to encrypt secret for embedding.token', body)
        self.assertNotIn(secret_value, body)
        if self.server.admin_logs.LOG_PATH.exists():
            admin_log_text = self.server.admin_logs.LOG_PATH.read_text(encoding='utf-8')
            self.assertNotIn(secret_value, admin_log_text)
        self.assertFalse(
            any(secret_value in message for message in capture.messages),
            msg=f'secret leaked to log records: {capture.messages!r}',
        )


if __name__ == '__main__':
    unittest.main()
