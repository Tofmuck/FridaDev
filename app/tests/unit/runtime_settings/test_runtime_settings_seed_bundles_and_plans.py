from __future__ import annotations

import sys
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


class RuntimeSettingsSeedBundlesAndPlansTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_build_env_seed_bundle_keeps_secret_value_out_of_payload(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('main_model')
        self.assertEqual(bundle.section, 'main_model')
        self.assertEqual(bundle.payload['base_url']['value'], config.OR_BASE)
        self.assertEqual(bundle.payload['referer_llm']['value'], config.OR_REFERER_LLM)
        self.assertEqual(bundle.payload['referer_validation_agent']['value'], config.OR_REFERER_VALIDATION_AGENT)
        self.assertEqual(bundle.payload['title_identity_extractor']['value'], config.OR_TITLE_IDENTITY_EXTRACTOR)
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

    def test_build_env_seed_bundle_uses_explicit_url_budget_seed_for_services(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('services')
        self.assertEqual(
            bundle.payload['crawl4ai_explicit_url_max_chars']['value'],
            config.CRAWL4AI_EXPLICIT_URL_MAX_CHARS,
        )
        self.assertEqual(
            bundle.payload['crawl4ai_explicit_url_max_chars']['origin'],
            'env_seed',
        )

    def test_build_env_seed_bundle_marks_seed_default_fields_with_seed_default_origin(self) -> None:
        main_model_bundle = runtime_settings.build_env_seed_bundle('main_model')
        self.assertEqual(main_model_bundle.payload['temperature']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['top_p']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['response_max_tokens']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['referer_llm']['origin'], 'env_seed')
        self.assertEqual(main_model_bundle.payload['referer_validation_agent']['origin'], 'env_seed')

        stimmung_bundle = runtime_settings.build_env_seed_bundle('stimmung_agent_model')
        self.assertEqual(
            {field_name: field_payload['origin'] for field_name, field_payload in stimmung_bundle.payload.items()},
            {
                'primary_model': 'seed_default',
                'fallback_model': 'seed_default',
                'timeout_s': 'seed_default',
                'temperature': 'seed_default',
                'top_p': 'seed_default',
                'max_tokens': 'seed_default',
            },
        )

        validation_bundle = runtime_settings.build_env_seed_bundle('validation_agent_model')
        self.assertEqual(
            {field_name: field_payload['origin'] for field_name, field_payload in validation_bundle.payload.items()},
            {
                'primary_model': 'seed_default',
                'fallback_model': 'seed_default',
                'timeout_s': 'seed_default',
                'temperature': 'seed_default',
                'top_p': 'seed_default',
                'max_tokens': 'seed_default',
            },
        )

    def test_build_db_seed_bundle_uses_db_seed_for_non_secret_fields(self) -> None:
        bundle = runtime_settings.build_db_seed_bundle('main_model')
        self.assertEqual(bundle.payload['base_url']['origin'], 'db_seed')
        self.assertEqual(bundle.payload['model']['origin'], 'db_seed')
        self.assertEqual(bundle.payload['temperature']['origin'], 'db_seed')
        self.assertEqual(bundle.payload['response_max_tokens']['origin'], 'db_seed')
        self.assertEqual(bundle.payload['response_max_tokens']['value'], 8192)
        self.assertEqual(bundle.payload['api_key']['origin'], 'env_seed')

    def test_get_unseeded_sections_uses_missing_rows_as_signal(self) -> None:
        missing = runtime_settings.get_unseeded_sections(('main_model', 'services'))
        self.assertEqual(
            missing,
            (
                'arbiter_model',
                'summary_model',
                'stimmung_agent_model',
                'validation_agent_model',
                'embedding',
                'database',
                'resources',
                'identity_governance',
            ),
        )

    def test_build_env_seed_plan_skips_existing_sections(self) -> None:
        plan = runtime_settings.build_env_seed_plan(('main_model', 'embedding', 'services'))
        self.assertEqual(
            tuple(bundle.section for bundle in plan),
            (
                'arbiter_model',
                'summary_model',
                'stimmung_agent_model',
                'validation_agent_model',
                'database',
                'resources',
                'identity_governance',
            ),
        )

    def test_build_db_seed_plan_skips_existing_sections_and_marks_non_secret_payloads(self) -> None:
        plan = runtime_settings.build_db_seed_plan(('main_model', 'embedding', 'services'))
        self.assertEqual(
            tuple(bundle.section for bundle in plan),
            (
                'arbiter_model',
                'summary_model',
                'stimmung_agent_model',
                'validation_agent_model',
                'database',
                'resources',
                'identity_governance',
            ),
        )
        self.assertEqual(plan[0].payload['model']['origin'], 'db_seed')
        self.assertEqual(plan[4].payload['backend']['origin'], 'db_seed')


if __name__ == '__main__':
    unittest.main()
