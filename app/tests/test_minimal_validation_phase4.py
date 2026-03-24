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


if __name__ == '__main__':
    unittest.main()
