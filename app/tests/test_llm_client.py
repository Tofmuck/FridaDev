from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import llm_client
import config


class LlmClientRuntimeSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_or_headers_uses_decrypted_db_api_key_when_available(self) -> None:
        original = llm_client.runtime_settings.get_runtime_secret_value

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('main_model', 'api_key'))
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-db-runtime-key',
                source='db_encrypted',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            headers = llm_client.or_headers(caller='arbiter')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original

        self.assertEqual(headers['Authorization'], 'Bearer sk-db-runtime-key')
        self.assertEqual(headers['X-OpenRouter-Title'], config.OR_TITLE_ARBITER)
        self.assertEqual(headers['X-Title'], config.OR_TITLE_ARBITER)
        self.assertEqual(headers['HTTP-Referer'], config.OR_REFERER_ARBITER)

    def test_or_headers_uses_distinct_identity_extractor_title(self) -> None:
        original_secret = llm_client.runtime_settings.get_runtime_secret_value
        original_view = llm_client.runtime_settings.get_main_model_settings

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('main_model', 'api_key'))
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-db-runtime-key',
                source='db_encrypted',
                source_reason='db_row',
            )

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'referer_llm': {'value': 'https://llm.frida-system.fr/', 'origin': 'db'},
                        'referer_arbiter': {'value': 'https://arbiter.frida-system.fr/', 'origin': 'db'},
                        'referer_identity_extractor': {'value': 'https://identity-extractor.frida-system.fr/', 'origin': 'db'},
                        'referer_resumer': {'value': 'https://resumer.frida-system.fr/', 'origin': 'db'},
                        'referer_stimmung_agent': {'value': 'https://stimmung-agent.frida-system.fr/', 'origin': 'db'},
                        'referer_validation_agent': {'value': 'https://validation-agent.frida-system.fr/', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_identity_extractor': {'value': 'FridaDev/IdentityExtractor', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'title_stimmung_agent': {'value': 'FridaDev/StimmungAgent', 'origin': 'db'},
                        'title_validation_agent': {'value': 'FridaDev/ValidationAgent', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            headers = llm_client.or_headers(caller='identity_extractor')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original_secret
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(headers['X-OpenRouter-Title'], 'FridaDev/IdentityExtractor')
        self.assertEqual(headers['X-Title'], 'FridaDev/IdentityExtractor')
        self.assertEqual(headers['HTTP-Referer'], 'https://identity-extractor.frida-system.fr/')

    def test_or_headers_keeps_internal_caller_marker_local(self) -> None:
        headers = llm_client.or_headers(caller='validation_agent')

        self.assertEqual(headers[llm_client.INTERNAL_PROVIDER_CALLER_HEADER], 'validation_agent')
        self.assertEqual(headers['X-OpenRouter-Title'], config.OR_TITLE_VALIDATION_AGENT)
        self.assertEqual(headers['X-Title'], config.OR_TITLE_VALIDATION_AGENT)
        self.assertEqual(headers['HTTP-Referer'], config.OR_REFERER_VALIDATION_AGENT)

    def test_or_headers_uses_distinct_component_referers_for_all_known_callers(self) -> None:
        observed = {
            caller: llm_client.or_headers(caller=caller)['HTTP-Referer']
            for caller in (
                'llm',
                'web_reformulation',
                'arbiter',
                'identity_extractor',
                'resumer',
                'stimmung_agent',
                'validation_agent',
            )
        }

        self.assertEqual(
            observed,
            {
                'llm': config.OR_REFERER_LLM,
                'web_reformulation': config.OR_REFERER_WEB_REFORMULATION,
                'arbiter': config.OR_REFERER_ARBITER,
                'identity_extractor': config.OR_REFERER_IDENTITY_EXTRACTOR,
                'resumer': config.OR_REFERER_RESUMER,
                'stimmung_agent': config.OR_REFERER_STIMMUNG_AGENT,
                'validation_agent': config.OR_REFERER_VALIDATION_AGENT,
            },
        )

    def test_or_headers_uses_dedicated_web_reformulation_identity_without_runtime_field(self) -> None:
        original_secret = llm_client.runtime_settings.get_runtime_secret_value
        original_view = llm_client.runtime_settings.get_main_model_settings

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('main_model', 'api_key'))
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-db-runtime-key',
                source='db_encrypted',
                source_reason='db_row',
            )

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://shared.frida-system.fr/', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            headers = llm_client.or_headers(caller='web_reformulation')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original_secret
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(headers[llm_client.INTERNAL_PROVIDER_CALLER_HEADER], 'web_reformulation')
        self.assertEqual(headers['X-OpenRouter-Title'], config.OR_TITLE_WEB_REFORMULATION)
        self.assertEqual(headers['X-Title'], config.OR_TITLE_WEB_REFORMULATION)
        self.assertEqual(headers['HTTP-Referer'], config.OR_REFERER_WEB_REFORMULATION)

    def test_or_headers_keeps_env_fallback_when_db_secret_is_missing(self) -> None:
        original = llm_client.runtime_settings.get_runtime_secret_value
        original_api_key = config.OR_KEY
        config.OR_KEY = 'sk-env-fallback-key'

        def fake_get_runtime_secret_value(section: str, field: str):
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-env-fallback-key',
                source='env_fallback',
                source_reason='empty_table',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            headers = llm_client.or_headers(caller='llm')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original
            config.OR_KEY = original_api_key

        self.assertEqual(headers['Authorization'], 'Bearer sk-env-fallback-key')

    def test_resolve_provider_caller_from_headers_prefers_internal_header_and_falls_back_to_title(self) -> None:
        self.assertEqual(
            llm_client.resolve_provider_caller_from_headers(
                {
                    llm_client.INTERNAL_PROVIDER_CALLER_HEADER: 'stimmung_agent',
                    'X-Title': config.OR_TITLE_LLM,
                }
            ),
            'stimmung_agent',
        )
        self.assertEqual(
            llm_client.resolve_provider_caller_from_headers(
                {'X-Title': config.OR_TITLE_VALIDATION_AGENT}
            ),
            'validation_agent',
        )
        self.assertEqual(
            llm_client.strip_internal_provider_headers(
                {
                    llm_client.INTERNAL_PROVIDER_CALLER_HEADER: 'validation_agent',
                    'X-Title': config.OR_TITLE_VALIDATION_AGENT,
                }
            ),
            {'X-Title': config.OR_TITLE_VALIDATION_AGENT},
        )

    def test_resolve_provider_referer_prefers_component_field_and_falls_back_to_shared_then_seed(self) -> None:
        original_view = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'referer': {'value': 'https://shared.frida-system.fr/', 'origin': 'db'},
                        'referer_llm': {'value': 'https://llm.frida-system.fr/', 'origin': 'db'},
                        'referer_validation_agent': {'value': '', 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            self.assertEqual(
                llm_client.resolve_provider_referer('llm'),
                'https://llm.frida-system.fr/',
            )
            self.assertEqual(
                llm_client.resolve_provider_referer('validation_agent'),
                'https://shared.frida-system.fr/',
            )
            self.assertEqual(
                llm_client.resolve_provider_referer('stimmung_agent'),
                'https://shared.frida-system.fr/',
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original_view

    def test_resolve_provider_referer_falls_back_to_component_seed_when_shared_is_missing(self) -> None:
        original_view = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'referer': {'value': '', 'origin': 'db'},
                        'referer_validation_agent': {'value': '', 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            self.assertEqual(
                llm_client.resolve_provider_referer('validation_agent'),
                config.OR_REFERER_VALIDATION_AGENT,
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original_view

    def test_build_payload_uses_runtime_main_model_from_db_when_present(self) -> None:
        original = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'referer_llm': {'value': 'https://llm.frida-system.fr/', 'origin': 'db'},
                        'referer_arbiter': {'value': 'https://arbiter.frida-system.fr/', 'origin': 'db'},
                        'referer_identity_extractor': {'value': 'https://identity-extractor.frida-system.fr/', 'origin': 'db'},
                        'referer_resumer': {'value': 'https://resumer.frida-system.fr/', 'origin': 'db'},
                        'referer_stimmung_agent': {'value': 'https://stimmung-agent.frida-system.fr/', 'origin': 'db'},
                        'referer_validation_agent': {'value': 'https://validation-agent.frida-system.fr/', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            payload = llm_client.build_payload(
                messages=[{'role': 'user', 'content': 'bonjour'}],
                temperature=0.7,
                top_p=0.9,
                max_tokens=512,
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original

        self.assertEqual(payload['model'], 'openai/gpt-5.4')
        self.assertEqual(payload['temperature'], 0.7)
        self.assertEqual(payload['top_p'], 0.9)
        self.assertEqual(payload['max_tokens'], 512)

    def test_build_payload_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        original = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='empty_table',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            payload = llm_client.build_payload(
                messages=[{'role': 'user', 'content': 'bonjour'}],
                temperature=0.4,
                top_p=1.0,
                max_tokens=256,
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original

        self.assertEqual(payload['model'], config.OR_MODEL)

    def test_extract_openrouter_provider_metadata_reads_post_call_usage_and_generation_id(self) -> None:
        metadata = llm_client.extract_openrouter_provider_metadata(
            {
                'id': 'gen-123',
                'model': 'openai/gpt-5.4-mini',
                'usage': {
                    'prompt_tokens': 111,
                    'completion_tokens': 22,
                    'total_tokens': 133,
                },
            },
            requested_model='openai/requested-model',
        )

        self.assertEqual(
            metadata,
            {
                'provider_generation_id': 'gen-123',
                'provider_model': 'openai/gpt-5.4-mini',
                'provider_prompt_tokens': 111,
                'provider_completion_tokens': 22,
                'provider_total_tokens': 133,
            },
        )

    def test_merge_openrouter_provider_metadata_keeps_requested_model_and_merges_stream_usage(self) -> None:
        merged = llm_client.merge_openrouter_provider_metadata(
            None,
            {},
            requested_model='openai/gpt-5.4',
        )
        merged = llm_client.merge_openrouter_provider_metadata(
            merged,
            {'id': 'gen-stream', 'model': 'openai/gpt-5.4'},
            requested_model='openai/gpt-5.4',
        )
        merged = llm_client.merge_openrouter_provider_metadata(
            merged,
            {'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}},
            requested_model='openai/gpt-5.4',
        )

        self.assertEqual(
            merged,
            {
                'provider_model': 'openai/gpt-5.4',
                'provider_generation_id': 'gen-stream',
                'provider_prompt_tokens': 80,
                'provider_completion_tokens': 20,
                'provider_total_tokens': 100,
            },
        )

    def test_build_provider_observability_fields_adds_caller_and_title(self) -> None:
        original_view = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'referer_llm': {'value': 'https://llm.frida-system.fr/', 'origin': 'db'},
                        'referer_arbiter': {'value': 'https://arbiter.frida-system.fr/', 'origin': 'db'},
                        'referer_identity_extractor': {'value': 'https://identity-extractor.frida-system.fr/', 'origin': 'db'},
                        'referer_resumer': {'value': 'https://resumer.frida-system.fr/', 'origin': 'db'},
                        'referer_stimmung_agent': {'value': 'https://stimmung-agent.frida-system.fr/', 'origin': 'db'},
                        'referer_validation_agent': {'value': 'https://validation-agent.frida-system.fr/', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_identity_extractor': {'value': 'FridaDev/IdentityExtractor', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'title_stimmung_agent': {'value': 'FridaDev/StimmungAgent', 'origin': 'db'},
                        'title_validation_agent': {'value': 'FridaDev/ValidationAgent', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            fields = llm_client.build_provider_observability_fields(
                caller='identity_extractor',
                provider_metadata={
                    'provider_generation_id': 'gen-42',
                    'provider_total_tokens': 99,
                },
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(
            fields,
            {
                'provider_caller': 'identity_extractor',
                'provider_title': 'FridaDev/IdentityExtractor',
                'provider_generation_id': 'gen-42',
                'provider_total_tokens': 99,
            },
        )

    def test_log_provider_metadata_infers_caller_and_title_from_event_name(self) -> None:
        original_view = llm_client.runtime_settings.get_main_model_settings
        observed = []

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_identity_extractor': {'value': 'FridaDev/IdentityExtractor', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'title_stimmung_agent': {'value': 'FridaDev/StimmungAgent', 'origin': 'db'},
                        'title_validation_agent': {'value': 'FridaDev/ValidationAgent', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            llm_client.log_provider_metadata(
                type('Logger', (), {'info': lambda self, msg, *args: observed.append(args)})(),
                'validation_agent_provider_response',
                {'provider_model': 'openai/gpt-5.4-mini'},
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(
            observed,
            [
                (
                    'validation_agent_provider_response',
                    'validation_agent',
                    'FridaDev/ValidationAgent',
                    '',
                    'openai/gpt-5.4-mini',
                    None,
                    None,
                    None,
                )
            ],
        )


if __name__ == '__main__':
    unittest.main()
