from __future__ import annotations

import sys
import tempfile
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

from admin import runtime_settings, runtime_settings_validation
import config
from identity import static_identity_paths


class RuntimeSettingsValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

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
