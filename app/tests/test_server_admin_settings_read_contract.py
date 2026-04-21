from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerAdminSettingsReadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

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
                    'response_max_tokens': {'value': 8192, 'is_secret': False, 'origin': 'db_seed'},
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
            8192,
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
            data['sections']['main_model']['readonly_info']['system_prompt_path']['value'],
            runtime_settings.config.MAIN_SYSTEM_PROMPT_PATH,
        )
        self.assertEqual(
            data['sections']['main_model']['readonly_info']['system_prompt_loader']['value'],
            'core.prompt_loader.get_main_system_prompt()',
        )
        self.assertIn(
            "Contrat d'interpretation du prompt augmente",
            data['sections']['main_model']['readonly_info']['hermeneutical_prompt']['value'],
        )
        self.assertEqual(
            data['sections']['main_model']['readonly_info']['hermeneutical_prompt_path']['value'],
            runtime_settings.config.MAIN_HERMENEUTICAL_PROMPT_PATH,
        )
        self.assertEqual(
            data['sections']['main_model']['readonly_info']['hermeneutical_prompt_loader']['value'],
            'core.prompt_loader.get_main_hermeneutical_prompt()',
        )
        self.assertIn(
            '[RÉFÉRENCE TEMPORELLE]',
            data['sections']['main_model']['readonly_info']['hermeneutical_runtime_bricks']['value'],
        )
        self.assertIn(
            '[Mémoire — souvenirs pertinents]',
            data['sections']['main_model']['readonly_info']['hermeneutical_runtime_bricks']['value'],
        )
        self.assertEqual(
            data['sections']['arbiter_model']['readonly_info']['decision_max_tokens']['value'],
            600,
        )
        self.assertEqual(
            data['sections']['arbiter_model']['readonly_info']['identity_extractor_max_tokens']['value'],
            700,
        )
        self.assertEqual(
            data['sections']['identity_governance']['readonly_info']['surface_route']['value'],
            '/hermeneutic-admin',
        )
        self.assertEqual(
            data['sections']['identity_governance']['readonly_info']['update_route']['value'],
            '/api/admin/identity/governance',
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

    def test_get_admin_settings_aggregated_presence_of_readonly_info_matches_phase12_scope(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={},
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])

        for section in (
            'main_model',
            'arbiter_model',
            'summary_model',
            'stimmung_agent_model',
            'validation_agent_model',
            'services',
            'identity_governance',
        ):
            readonly_info = data['sections'][section]['readonly_info']
            self.assertTrue(readonly_info, section)
            for item in readonly_info.values():
                self.assertEqual(set(item.keys()), {'label', 'value', 'is_editable', 'source'})
                self.assertFalse(item['is_editable'])

        for section in ('embedding', 'database', 'resources'):
            self.assertEqual(data['sections'][section]['readonly_info'], {}, section)

    def test_get_admin_settings_main_model_returns_single_section_with_redacted_secrets(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'main_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/main-model-route', 'is_secret': False, 'origin': 'db'},
                    'referer_identity_extractor': {'value': 'https://identity-extractor.frida-system.fr/', 'is_secret': False, 'origin': 'db'},
                    'title_identity_extractor': {'value': 'FridaDev/IdentityExtractor', 'is_secret': False, 'origin': 'db'},
                    'response_max_tokens': {'value': 8192, 'is_secret': False, 'origin': 'db_seed'},
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
        self.assertEqual(
            data['payload']['referer_identity_extractor']['value'],
            'https://identity-extractor.frida-system.fr/',
        )
        self.assertEqual(data['payload']['title_identity_extractor']['value'], 'FridaDev/IdentityExtractor')
        self.assertEqual(data['payload']['response_max_tokens']['value'], 8192)
        self.assertEqual(
            data['payload']['api_key'],
            {'is_secret': True, 'is_set': True, 'origin': 'db'},
        )
        self.assertEqual(data['readonly_info']['context_max_tokens']['label'], 'FRIDA_MAX_TOKENS')
        self.assertIn('Cadre de réponse', data['readonly_info']['system_prompt']['value'])
        self.assertEqual(data['readonly_info']['system_prompt_path']['value'], runtime_settings.config.MAIN_SYSTEM_PROMPT_PATH)
        self.assertIn("Contrat d'interpretation du prompt augmente", data['readonly_info']['hermeneutical_prompt']['value'])
        self.assertEqual(
            data['readonly_info']['hermeneutical_prompt_path']['value'],
            runtime_settings.config.MAIN_HERMENEUTICAL_PROMPT_PATH,
        )
        self.assertIn('[Indices contextuels recents]', data['readonly_info']['hermeneutical_runtime_bricks']['value'])
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

    def test_get_admin_settings_stimmung_agent_model_returns_single_section(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'stimmung_agent_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'primary_model': {'value': 'openai/gpt-5.4-mini', 'is_secret': False, 'origin': 'db'},
                    'fallback_model': {'value': 'openai/gpt-5.4-nano', 'is_secret': False, 'origin': 'db'},
                    'timeout_s': {'value': 11, 'is_secret': False, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/stimmung-agent-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'stimmung_agent_model')
        self.assertEqual(data['payload']['primary_model']['value'], 'openai/gpt-5.4-mini')
        self.assertEqual(data['payload']['timeout_s']['value'], 11)
        self.assertEqual(data['readonly_info']['prompt_path']['value'], 'prompts/stimmung_agent.txt')
        self.assertIn('main_model.title_stimmung_agent', data['readonly_info']['shared_transport']['value'])

    def test_get_admin_settings_validation_agent_model_returns_single_section(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'validation_agent_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'primary_model': {'value': 'openai/gpt-5.4-mini', 'is_secret': False, 'origin': 'db'},
                    'fallback_model': {'value': 'openai/gpt-5.4-nano', 'is_secret': False, 'origin': 'db'},
                    'max_tokens': {'value': 80, 'is_secret': False, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/validation-agent-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'validation_agent_model')
        self.assertEqual(data['payload']['primary_model']['value'], 'openai/gpt-5.4-mini')
        self.assertEqual(data['payload']['max_tokens']['value'], 80)
        self.assertEqual(data['readonly_info']['prompt_path']['value'], 'prompts/validation_agent.txt')
        self.assertIn('final_judgment_posture', data['readonly_info']['validated_output_contract']['value'])
        self.assertIn('final_output_regime', data['readonly_info']['validated_output_contract']['value'])
        self.assertIn('arbiter_reason', data['readonly_info']['validated_output_contract']['value'])

    def test_get_admin_settings_hermeneutic_agent_models_report_seed_default_origin_without_db(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            return original_get_section(section, fetcher=lambda: {})

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            stimmung_response = self.client.get('/api/admin/settings/stimmung-agent-model')
            validation_response = self.client.get('/api/admin/settings/validation-agent-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(stimmung_response.status_code, 200)
        stimmung_data = stimmung_response.get_json()
        self.assertTrue(stimmung_data['ok'])
        self.assertEqual(stimmung_data['source'], 'env')
        self.assertEqual(
            {field_name: field_payload['origin'] for field_name, field_payload in stimmung_data['payload'].items()},
            {
                'primary_model': 'seed_default',
                'fallback_model': 'seed_default',
                'timeout_s': 'seed_default',
                'temperature': 'seed_default',
                'top_p': 'seed_default',
                'max_tokens': 'seed_default',
            },
        )

        self.assertEqual(validation_response.status_code, 200)
        validation_data = validation_response.get_json()
        self.assertTrue(validation_data['ok'])
        self.assertEqual(validation_data['source'], 'env')
        self.assertEqual(
            {field_name: field_payload['origin'] for field_name, field_payload in validation_data['payload'].items()},
            {
                'primary_model': 'seed_default',
                'fallback_model': 'seed_default',
                'timeout_s': 'seed_default',
                'temperature': 'seed_default',
                'top_p': 'seed_default',
                'max_tokens': 'seed_default',
            },
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
                    'crawl4ai_explicit_url_max_chars': {'value': 25000, 'origin': 'db'},
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

    def test_get_admin_settings_is_available_without_admin_token(self) -> None:
        response = self.client.get('/api/admin/settings')
        self.assertEqual(response.status_code, 200)

    def test_all_admin_settings_routes_are_available_without_admin_token(self) -> None:
        public_rules = []
        for rule in self.server.app.url_map.iter_rules():
            if not rule.rule.startswith('/api/admin/settings'):
                continue
            methods = sorted(method for method in rule.methods if method in {'GET', 'PATCH', 'POST'})
            for method in methods:
                public_rules.append((method, rule.rule))

        self.assertTrue(public_rules)

        for method, path in public_rules:
            kwargs = {}
            if method in {'PATCH', 'POST'}:
                kwargs['json'] = {}
            response = self.client.open(path, method=method, **kwargs)
            self.assertNotIn(
                response.status_code,
                {401, 403},
                msg=f'unexpected admin guard on {method} {path}, got {response.status_code}',
            )

    def test_admin_guard_rejects_untrusted_peer_even_with_remote_user_header(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        self.server._trusted_admin_proxy_ips = lambda: {'172.20.0.19'}
        try:
            response = self.client.get(
                '/api/admin/settings/status',
                headers={'Remote-User': 'operator'},
                environ_overrides={'REMOTE_ADDR': '172.20.0.5'},
            )
        finally:
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'admin access denied'})

    def test_admin_guard_rejects_trusted_proxy_without_remote_user_header(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        self.server._trusted_admin_proxy_ips = lambda: {'172.20.0.19'}
        try:
            response = self.client.get(
                '/api/admin/settings/status',
                environ_overrides={'REMOTE_ADDR': '172.20.0.19'},
            )
        finally:
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'admin access denied'})

    def test_admin_guard_accepts_trusted_proxy_with_remote_user_header(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        self.server._trusted_admin_proxy_ips = lambda: {'172.20.0.19'}
        try:
            response = self.client.get(
                '/api/admin/settings/status',
                headers={'Remote-User': 'operator'},
                environ_overrides={'REMOTE_ADDR': '172.20.0.19'},
            )
        finally:
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
