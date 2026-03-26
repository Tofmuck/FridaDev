from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
import config
import minimal_validation


class MinimalValidationPhase4ResourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_check_prompt_files_uses_runtime_resource_paths_from_db_when_present(self) -> None:
        original_get_resources = minimal_validation.runtime_settings.get_resources_settings

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'llm.txt'
            user_file = tmp_path / 'user.txt'
            llm_file.write_text('identite llm db minimale suffisamment longue', encoding='utf-8')
            user_file.write_text('identite user db minimale suffisamment longue', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            minimal_validation.runtime_settings.get_resources_settings = fake_get_resources_settings
            try:
                details = minimal_validation._check_prompt_files()
            finally:
                minimal_validation.runtime_settings.get_resources_settings = original_get_resources

        self.assertEqual(details['llm_identity']['path'], str(llm_file))
        self.assertEqual(details['user_identity']['path'], str(user_file))
        self.assertEqual(
            details['main_system_prompt']['path'],
            str(APP_DIR / config.MAIN_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['main_hermeneutical_prompt']['path'],
            str(APP_DIR / config.MAIN_HERMENEUTICAL_PROMPT_PATH),
        )
        self.assertEqual(
            details['summary_system_prompt']['path'],
            str(APP_DIR / config.SUMMARY_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['web_reformulation_prompt']['path'],
            str(APP_DIR / config.WEB_REFORMULATION_PROMPT_PATH),
        )
        self.assertIn('const SYSTEM_PROMPT =', details['forbidden_inline_markers']['app_js'])
        self.assertIn('cfg.system', details['forbidden_inline_markers']['app_js'])
        self.assertIn('id="system"', details['forbidden_inline_markers']['index_html'])
        self.assertIn(
            'Tu es un assistant de synthèse. Résume le dialogue suivant en conservant',
            details['forbidden_inline_markers']['summarizer_py'],
        )
        self.assertIn(
            'Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.',
            details['forbidden_inline_markers']['web_search_py'],
        )

    def test_check_prompt_files_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        original_get_resources = minimal_validation.runtime_settings.get_resources_settings
        original_llm_path = config.FRIDA_LLM_IDENTITY_PATH
        original_user_path = config.FRIDA_USER_IDENTITY_PATH

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'llm-env.txt'
            user_file = tmp_path / 'user-env.txt'
            llm_file.write_text('identite llm env minimale suffisamment longue', encoding='utf-8')
            user_file.write_text('identite user env minimale suffisamment longue', encoding='utf-8')

            config.FRIDA_LLM_IDENTITY_PATH = str(llm_file)
            config.FRIDA_USER_IDENTITY_PATH = str(user_file)

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.build_env_seed_bundle('resources').payload,
                    source='env',
                    source_reason='empty_table',
                )

            minimal_validation.runtime_settings.get_resources_settings = fake_get_resources_settings
            try:
                details = minimal_validation._check_prompt_files()
            finally:
                minimal_validation.runtime_settings.get_resources_settings = original_get_resources
                config.FRIDA_LLM_IDENTITY_PATH = original_llm_path
                config.FRIDA_USER_IDENTITY_PATH = original_user_path

        self.assertEqual(details['llm_identity']['path'], str(llm_file))
        self.assertEqual(details['user_identity']['path'], str(user_file))
        self.assertEqual(
            details['main_system_prompt']['path'],
            str(APP_DIR / config.MAIN_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['main_hermeneutical_prompt']['path'],
            str(APP_DIR / config.MAIN_HERMENEUTICAL_PROMPT_PATH),
        )
        self.assertEqual(
            details['summary_system_prompt']['path'],
            str(APP_DIR / config.SUMMARY_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['web_reformulation_prompt']['path'],
            str(APP_DIR / config.WEB_REFORMULATION_PROMPT_PATH),
        )
        self.assertIn('const SYSTEM_PROMPT =', details['forbidden_inline_markers']['app_js'])
        self.assertIn('cfg.system', details['forbidden_inline_markers']['app_js'])


class MinimalValidationPhase4DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

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

    def test_check_db_schema_uses_bootstrap_database_dsn_helper(self) -> None:
        source = (APP_DIR / 'minimal_validation.py').read_text(encoding='utf-8')
        self.assertIn('with psycopg.connect(_bootstrap_database_dsn()) as conn:', source)
        self.assertNotIn('psycopg.connect(config.FRIDA_MEMORY_DB_DSN)', source)
        self.assertIn('"runtime_settings": {', source)
        self.assertIn('"runtime_settings_history": {', source)

    def test_check_db_schema_rejects_unsupported_runtime_database_backend(self) -> None:
        original_get_database = minimal_validation.runtime_settings.get_database_settings
        minimal_validation.runtime_settings.get_database_settings = lambda: self._db_database_view(backend='mysql')
        try:
            with self.assertRaisesRegex(ValueError, 'unsupported runtime database backend: mysql'):
                minimal_validation._check_db_schema()
        finally:
            minimal_validation.runtime_settings.get_database_settings = original_get_database

    def test_bootstrap_database_dsn_requires_env_fallback_while_db_secret_decryption_is_unavailable(self) -> None:
        original_get_database = minimal_validation.runtime_settings.get_database_settings
        original_get_secret = minimal_validation.runtime_settings.get_runtime_secret_value
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        observed = {'called': False}

        def fake_get_runtime_secret_value(section: str, field: str):
            observed['called'] = True
            raise AssertionError('database bootstrap must not resolve runtime secret values')

        minimal_validation.runtime_settings.get_database_settings = self._db_database_view
        minimal_validation.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        config.FRIDA_MEMORY_DB_DSN = ''
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretRequiredError,
                'runtime secret decryption is not available',
            ):
                minimal_validation._bootstrap_database_dsn()
        finally:
            minimal_validation.runtime_settings.get_database_settings = original_get_database
            minimal_validation.runtime_settings.get_runtime_secret_value = original_get_secret
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertFalse(observed['called'])


if __name__ == '__main__':
    unittest.main()
