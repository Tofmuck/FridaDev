from __future__ import annotations

import logging
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
from identity import static_identity_paths
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerAdminSettingsPhase5Tests(unittest.TestCase):
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
        self.assertEqual(data['readonly_info']['context_max_tokens']['label'], 'FRIDA_MAX_TOKENS')
        self.assertIn('Cadre de réponse', data['readonly_info']['system_prompt']['value'])
        self.assertEqual(data['readonly_info']['system_prompt_loader']['value'], 'core.prompt_loader.get_main_system_prompt()')
        self.assertIn("Contrat d'interpretation du prompt augmente", data['readonly_info']['hermeneutical_prompt']['value'])
        self.assertEqual(
            data['readonly_info']['hermeneutical_prompt_loader']['value'],
            'core.prompt_loader.get_main_hermeneutical_prompt()',
        )
        self.assertIn('[FIN DES RÉSULTATS WEB]', data['readonly_info']['hermeneutical_runtime_bricks']['value'])
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

    def test_patch_admin_settings_main_model_rejects_non_mapping_payload(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/main-model',
            data='[1]',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'patch request must be a mapping')

    def test_patch_admin_settings_main_model_returns_503_on_runtime_db_unavailable(self) -> None:
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(*_args, **_kwargs):
            raise self.server.runtime_settings.RuntimeSettingsDbUnavailableError('db unavailable for patch')

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/main-model',
                json={'payload': {'model': {'value': 'openrouter/test'}}},
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'db unavailable for patch')

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

    def test_patch_admin_settings_main_model_rejects_readonly_prompt_field(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/main-model',
            json={
                'payload': {
                    'system_prompt': {'value': 'should-not-pass'},
                },
            },
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('unknown runtime settings field: main_model.system_prompt', data['error'])

    def test_patch_admin_settings_services_rejects_readonly_budget_field(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/services',
            json={
                'payload': {
                    'web_reformulation_max_tokens': {'value': 99},
                },
            },
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn(
            'unknown runtime settings field: services.web_reformulation_max_tokens',
            data['error'],
        )

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
                    'response_max_tokens': {'value': 8192, 'is_secret': False, 'origin': 'admin_ui'},
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
                        'response_max_tokens': {'value': 8192},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'main_model')
        self.assertEqual(observed['updated_by'], 'phase12-admin')
        self.assertEqual(observed['payload'], {'response_max_tokens': {'value': 8192}})
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['payload']['response_max_tokens']['value'], 8192)
        self.assertEqual(data['payload']['response_max_tokens']['origin'], 'admin_ui')
        self.assertEqual(data['readonly_info']['context_max_tokens']['label'], 'FRIDA_MAX_TOKENS')
        self.assertIn('Cadre de réponse', data['readonly_info']['system_prompt']['value'])
        self.assertIn("Contrat d'interpretation du prompt augmente", data['readonly_info']['hermeneutical_prompt']['value'])
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
                    'crawl4ai_explicit_url_max_chars': {'value': 25000, 'is_secret': False, 'origin': 'admin_ui'},
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
                        'crawl4ai_explicit_url_max_chars': {'value': 25000},
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
                'crawl4ai_explicit_url_max_chars': {'value': 25000},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'services')
        self.assertEqual(data['payload']['searxng_url']['value'], 'http://127.0.0.1:8093')
        self.assertEqual(data['payload']['crawl4ai_explicit_url_max_chars']['value'], 25000)
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

    def test_post_admin_settings_resources_validate_rejects_existing_file_outside_allowed_roots(self) -> None:
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            allowed_user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            outside_file = tmp_path / 'outside.txt'
            allowed_user_file.parent.mkdir(parents=True)
            allowed_user_file.write_text('user identity allowed', encoding='utf-8')
            outside_file.write_text('outside identity path', encoding='utf-8')
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                response = self.client.post(
                    '/api/admin/settings/resources/validate',
                    json={
                        'payload': {
                            'llm_identity_path': {'value': str(outside_file)},
                            'user_identity_path': {'value': str(allowed_user_file)},
                        },
                    },
                )
            finally:
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['valid'])
        checks = {check['name']: check for check in data['checks']}
        self.assertFalse(checks['llm_identity_path']['ok'])
        self.assertTrue(checks['user_identity_path']['ok'])
        self.assertIn('resolution=absolute_outside_allowed_roots', checks['llm_identity_path']['detail'])
        self.assertIn('within_allowed_roots=False', checks['llm_identity_path']['detail'])

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
            logging.getLogger('frida.adminlog'),
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
            logging.getLogger('frida.adminlog'),
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
        identity_routes = {
            route for route in routes
            if route.startswith('/api/admin/identity')
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
        self.assertEqual(
            identity_routes,
            {
                '/api/admin/identity/read-model',
                '/api/admin/identity/runtime-representations',
                '/api/admin/identity/mutable',
                '/api/admin/identity/static',
                '/api/admin/identity/governance',
            },
        )
        self.assertTrue(settings_routes)
        self.assertTrue(hermeneutics_routes)
        self.assertTrue(identity_routes)
        self.assertTrue(settings_routes.isdisjoint(hermeneutics_routes))
        self.assertTrue(settings_routes.isdisjoint(identity_routes))
        self.assertTrue(hermeneutics_routes.isdisjoint(identity_routes))
        self.assertFalse(any('hermeneutics' in route for route in settings_routes))
        self.assertFalse(any('/settings' in route for route in hermeneutics_routes))

    def test_admin_resources_ui_keeps_paths_as_resource_references(self) -> None:
        source = (APP_DIR / 'web' / 'admin.js').read_text(encoding='utf-8')
        self.assertIn('LLM static resource path', source)
        self.assertIn('User static resource path', source)
        self.assertIn("Reference de ressource du statique actif cote modele.", source)
        self.assertIn("Reference de ressource du statique actif cote utilisateur.", source)
        self.assertIn("Le contenu s'edite depuis Hermeneutic admin.", source)

    def test_all_admin_settings_validate_routes_are_registered(self) -> None:
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn('/api/admin/settings/main-model/validate', routes)
        self.assertIn('/api/admin/settings/arbiter-model/validate', routes)
        self.assertIn('/api/admin/settings/summary-model/validate', routes)
        self.assertIn('/api/admin/settings/stimmung-agent-model/validate', routes)
        self.assertIn('/api/admin/settings/validation-agent-model/validate', routes)
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

    def test_post_admin_settings_validate_rejects_non_mapping_payload(self) -> None:
        response = self.client.post(
            '/api/admin/settings/main-model/validate',
            data='[]',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'validation payload must be a mapping')

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
            logging.getLogger('frida.adminlog'),
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
