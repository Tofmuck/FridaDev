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
        self.assertEqual(bundle.payload['referer_web_reformulation']['value'], config.OR_REFERER_WEB_REFORMULATION)
        self.assertEqual(bundle.payload['referer_web_discovery']['value'], config.OR_REFERER_WEB_DISCOVERY)
        self.assertEqual(bundle.payload['referer_validation_agent']['value'], config.OR_REFERER_VALIDATION_AGENT)
        self.assertEqual(bundle.payload['title_web_reformulation']['value'], config.OR_TITLE_WEB_REFORMULATION)
        self.assertEqual(bundle.payload['title_web_discovery']['value'], config.OR_TITLE_WEB_DISCOVERY)
        self.assertEqual(bundle.payload['title_identity_extractor']['value'], config.OR_TITLE_IDENTITY_EXTRACTOR)
        self.assertEqual(bundle.payload['temperature']['value'], 0.4)
        self.assertEqual(bundle.payload['reasoning_effort']['value'], 'high')
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

    def test_build_env_seed_bundle_uses_dedicated_web_reformulation_model_values(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('web_reformulation_model')
        self.assertEqual(bundle.payload['model']['value'], config.WEB_REFORMULATION_MODEL)
        self.assertEqual(bundle.payload['temperature']['value'], config.WEB_REFORMULATION_TEMPERATURE)
        self.assertEqual(bundle.payload['max_tokens']['value'], config.WEB_REFORMULATION_MAX_TOKENS)
        self.assertEqual(bundle.payload['timeout_s']['value'], config.WEB_REFORMULATION_TIMEOUT_S)

    def test_build_env_seed_bundle_uses_dedicated_biblio_librarian_agent_values(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('biblio_librarian_agent')
        self.assertEqual(bundle.payload['mode']['value'], config.BIBLIO_LIBRARIAN_AGENT_MODE)
        self.assertEqual(bundle.payload['primary_model']['value'], config.BIBLIO_LIBRARIAN_AGENT_MODEL)
        self.assertEqual(bundle.payload['max_tokens']['value'], config.BIBLIO_LIBRARIAN_AGENT_MAX_TOKENS)
        self.assertEqual(bundle.payload['timeout_s']['value'], config.BIBLIO_LIBRARIAN_AGENT_TIMEOUT_S)
        self.assertEqual(bundle.payload['reasoning_effort']['value'], config.BIBLIO_LIBRARIAN_AGENT_REASONING_EFFORT)

    def test_build_env_seed_bundle_uses_safe_agenda_agent_defaults_without_secret_value(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('agenda_agent')
        self.assertEqual(bundle.payload['mode']['value'], 'off')
        self.assertEqual(bundle.payload['mode']['origin'], 'seed_default')
        self.assertEqual(bundle.payload['caldav_account']['value'], 'tof')
        self.assertEqual(bundle.payload['caldav_account']['origin'], 'seed_default')
        self.assertEqual(bundle.payload['caldav_app_password']['is_secret'], True)
        self.assertFalse(bundle.payload['caldav_app_password']['is_set'])
        self.assertNotIn('value', bundle.payload['caldav_app_password'])
        self.assertNotIn('value_encrypted', bundle.payload['caldav_app_password'])
        self.assertEqual(bundle.secret_values, {})

    def test_build_env_seed_bundle_uses_dedicated_memory_arbiter_model_values(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('memory_arbiter_model')
        self.assertEqual(bundle.payload['model']['value'], config.MEMORY_ARBITER_MODEL)
        self.assertEqual(bundle.payload['temperature']['value'], config.MEMORY_ARBITER_TEMPERATURE)
        self.assertEqual(bundle.payload['top_p']['value'], config.MEMORY_ARBITER_TOP_P)
        self.assertEqual(bundle.payload['max_tokens']['value'], config.MEMORY_ARBITER_MAX_TOKENS)
        self.assertEqual(bundle.payload['timeout_s']['value'], config.MEMORY_ARBITER_TIMEOUT_S)

    def test_build_env_seed_bundle_uses_dedicated_identity_extractor_model_values(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('identity_extractor_model')
        self.assertEqual(bundle.payload['model']['value'], config.IDENTITY_EXTRACTOR_MODEL)
        self.assertEqual(bundle.payload['temperature']['value'], config.IDENTITY_EXTRACTOR_TEMPERATURE)
        self.assertEqual(bundle.payload['top_p']['value'], config.IDENTITY_EXTRACTOR_TOP_P)
        self.assertEqual(bundle.payload['max_tokens']['value'], config.IDENTITY_EXTRACTOR_MAX_TOKENS)
        self.assertEqual(bundle.payload['timeout_s']['value'], config.IDENTITY_EXTRACTOR_TIMEOUT_S)

    def test_build_env_seed_bundle_uses_dedicated_summary_model_values(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('summary_model')
        self.assertEqual(bundle.payload['model']['value'], config.SUMMARY_MODEL)
        self.assertEqual(bundle.payload['temperature']['value'], config.SUMMARY_TEMPERATURE)
        self.assertEqual(bundle.payload['top_p']['value'], config.SUMMARY_TOP_P)
        self.assertEqual(bundle.payload['max_tokens']['value'], config.SUMMARY_TARGET_TOKENS)
        self.assertEqual(bundle.payload['timeout_s']['value'], config.SUMMARY_TIMEOUT_S)

    def test_build_env_seed_bundle_marks_seed_default_fields_with_seed_default_origin(self) -> None:
        main_model_bundle = runtime_settings.build_env_seed_bundle('main_model')
        self.assertEqual(main_model_bundle.payload['temperature']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['top_p']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['response_max_tokens']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['reasoning_effort']['origin'], 'seed_default')
        self.assertEqual(main_model_bundle.payload['referer_llm']['origin'], 'env_seed')
        self.assertEqual(main_model_bundle.payload['referer_web_reformulation']['origin'], 'env_seed')
        self.assertEqual(main_model_bundle.payload['referer_web_discovery']['origin'], 'env_seed')
        self.assertEqual(main_model_bundle.payload['referer_validation_agent']['origin'], 'env_seed')

        stimmung_bundle = runtime_settings.build_env_seed_bundle('stimmung_agent_model')
        self.assertEqual(stimmung_bundle.payload['primary_model']['value'], 'google/gemini-3.1-flash-lite')
        self.assertEqual(stimmung_bundle.payload['fallback_model']['value'], 'openai/gpt-5.4-nano')
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
        self.assertEqual(bundle.payload['reasoning_effort']['origin'], 'db_seed')
        self.assertEqual(bundle.payload['reasoning_effort']['value'], 'high')
        self.assertEqual(bundle.payload['api_key']['origin'], 'env_seed')

    def test_get_unseeded_sections_uses_missing_rows_as_signal(self) -> None:
        missing = runtime_settings.get_unseeded_sections(('main_model', 'services'))
        self.assertEqual(
            missing,
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
                'resources',
                'identity_governance',
            ),
        )
        self.assertEqual(plan[0].payload['model']['origin'], 'db_seed')
        plan_by_section = {bundle.section: bundle for bundle in plan}
        self.assertEqual(plan_by_section['biblio_librarian_agent'].payload['primary_model']['origin'], 'db_seed')
        self.assertEqual(plan_by_section['agenda_agent'].payload['mode']['origin'], 'db_seed')
        self.assertEqual(plan_by_section['database'].payload['backend']['origin'], 'db_seed')


if __name__ == '__main__':
    unittest.main()
