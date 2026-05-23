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
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='test',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            headers = llm_client.or_headers(caller='arbiter')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original
            llm_client.runtime_settings.get_main_model_settings = original_view

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
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'referer_llm': {'value': 'https://llm.frida-system.fr/', 'origin': 'db'},
                        'referer_web_reformulation': {'value': 'https://web.frida-system.fr/', 'origin': 'db'},
                        'referer_arbiter': {'value': 'https://arbiter.frida-system.fr/', 'origin': 'db'},
                        'referer_identity_extractor': {'value': 'https://identity-extractor.frida-system.fr/', 'origin': 'db'},
                        'referer_identity_periodic': {'value': 'https://identity-periodic.frida-system.fr/', 'origin': 'db'},
                        'referer_resumer': {'value': 'https://resumer.frida-system.fr/', 'origin': 'db'},
                        'referer_stimmung_agent': {'value': 'https://stimmung-agent.frida-system.fr/', 'origin': 'db'},
                        'referer_validation_agent': {'value': 'https://validation-agent.frida-system.fr/', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_web_reformulation': {'value': 'FridaDev/Web', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_identity_extractor': {'value': 'FridaDev/IdentityExtractor', 'origin': 'db'},
                        'title_identity_periodic': {'value': 'FridaDev/IdentityPeriodic', 'origin': 'db'},
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

    def test_or_headers_uses_distinct_identity_periodic_title(self) -> None:
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
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'referer_identity_periodic': {'value': 'https://identity-periodic.frida-system.fr/', 'origin': 'db'},
                        'title_identity_periodic': {'value': 'FridaDev/IdentityPeriodic', 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            headers = llm_client.or_headers(caller='identity_periodic_agent')
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original_secret
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(headers[llm_client.INTERNAL_PROVIDER_CALLER_HEADER], 'identity_periodic_agent')
        self.assertEqual(headers['X-OpenRouter-Title'], 'FridaDev/IdentityPeriodic')
        self.assertEqual(headers['X-Title'], 'FridaDev/IdentityPeriodic')
        self.assertEqual(headers['HTTP-Referer'], 'https://identity-periodic.frida-system.fr/')

    def test_or_headers_keeps_internal_caller_marker_local(self) -> None:
        headers = llm_client.or_headers(caller='validation_agent')

        self.assertEqual(headers[llm_client.INTERNAL_PROVIDER_CALLER_HEADER], 'validation_agent')
        self.assertEqual(headers['X-OpenRouter-Title'], config.OR_TITLE_VALIDATION_AGENT)
        self.assertEqual(headers['X-Title'], config.OR_TITLE_VALIDATION_AGENT)
        self.assertEqual(headers['HTTP-Referer'], config.OR_REFERER_VALIDATION_AGENT)

    def test_or_headers_custom_keeps_explicit_tool_attribution(self) -> None:
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
            headers = llm_client.or_headers_custom(
                caller='image_generator_nano_banana',
                referer='https://fridadev.frida-system.fr/openrouter/image-generation/nano-banana',
                title='FridaDev / Image Generator / Nano Banana',
            )
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original

        self.assertEqual(headers['Authorization'], 'Bearer sk-db-runtime-key')
        self.assertEqual(headers[llm_client.INTERNAL_PROVIDER_CALLER_HEADER], 'image_generator_nano_banana')
        self.assertEqual(
            headers['HTTP-Referer'],
            'https://fridadev.frida-system.fr/openrouter/image-generation/nano-banana',
        )
        self.assertEqual(headers['X-OpenRouter-Title'], 'FridaDev / Image Generator / Nano Banana')
        self.assertEqual(headers['X-Title'], 'FridaDev / Image Generator / Nano Banana')

    def test_or_headers_uses_distinct_component_referers_for_all_known_callers(self) -> None:
        original_secret = llm_client.runtime_settings.get_runtime_secret_value
        original_view = llm_client.runtime_settings.get_main_model_settings

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('main_model', 'api_key'))
            return runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-db-runtime-key',
                source='env',
                source_reason='test',
            )

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='test',
            )

        llm_client.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        llm_client.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        try:
            observed = {
                caller: llm_client.or_headers(caller=caller)['HTTP-Referer']
                for caller in (
                    'llm',
                    'web_reformulation',
                    'web_discovery',
                    'arbiter',
                    'identity_extractor',
                    'identity_periodic_agent',
                    'resumer',
                    'stimmung_agent',
                    'validation_agent',
                )
            }
        finally:
            llm_client.runtime_settings.get_runtime_secret_value = original_secret
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(
            observed,
            {
                'llm': config.OR_REFERER_LLM,
                'web_reformulation': config.OR_REFERER_WEB_REFORMULATION,
                'web_discovery': config.OR_REFERER_WEB_DISCOVERY,
                'arbiter': config.OR_REFERER_ARBITER,
                'identity_extractor': config.OR_REFERER_IDENTITY_EXTRACTOR,
                'identity_periodic_agent': config.OR_REFERER_IDENTITY_PERIODIC,
                'resumer': config.OR_REFERER_RESUMER,
                'stimmung_agent': config.OR_REFERER_STIMMUNG_AGENT,
                'validation_agent': config.OR_REFERER_VALIDATION_AGENT,
            },
        )

    def test_or_headers_uses_dedicated_web_reformulation_runtime_fields(self) -> None:
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
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://shared.frida-system.fr/', 'origin': 'db'},
                        'referer_web_reformulation': {'value': 'https://web.frida-system.fr/', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_web_reformulation': {'value': 'FridaDev/Web Reformulation', 'origin': 'db'},
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
        self.assertEqual(headers['X-OpenRouter-Title'], 'FridaDev/Web Reformulation')
        self.assertEqual(headers['X-Title'], 'FridaDev/Web Reformulation')
        self.assertEqual(headers['HTTP-Referer'], 'https://web.frida-system.fr/')

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
            llm_client.resolve_provider_caller_from_headers(
                {'X-Title': config.OR_TITLE_IDENTITY_PERIODIC}
            ),
            'identity_periodic_agent',
        )
        self.assertEqual(
            llm_client.resolve_provider_caller_from_headers(
                {llm_client.INTERNAL_PROVIDER_CALLER_HEADER: 'web_discovery'}
            ),
            'web_discovery',
        )
        self.assertEqual(
            llm_client.resolve_provider_caller_from_headers(
                {'X-Title': config.OR_TITLE_WEB_DISCOVERY}
            ),
            'web_discovery',
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

    def test_provider_attribution_names_all_known_callers_without_user_field(self) -> None:
        expected = {
            'llm': ('main_chat', 'main_model'),
            'web_reformulation': (
                'web_reformulation',
                'web_reformulation_model',
            ),
            'web_discovery': (
                'web_discovery',
                'web_search_discovery',
            ),
            'arbiter': ('memory_arbiter', 'memory_arbiter_model'),
            'identity_extractor': (
                'identity_extractor',
                'identity_extractor_model',
            ),
            'identity_periodic_agent': (
                'identity_periodic',
                'identity_periodic_model',
            ),
            'resumer': ('summary', 'summary_model'),
            'stimmung_agent': ('stimmung_agent', 'stimmung_agent_model'),
            'validation_agent': (
                'validation_agent',
                'validation_agent_model',
            ),
        }

        for caller, (frida_caller, frida_slot) in expected.items():
            with self.subTest(caller=caller):
                attribution = llm_client.provider_attribution(caller)
                self.assertEqual(
                    attribution['metadata'],
                    {'frida_caller': frida_caller, 'frida_slot': frida_slot},
                )
                self.assertEqual(
                    attribution['trace'],
                    {'trace_name': 'FridaDev', 'generation_name': llm_client.resolve_provider_title(caller)},
                )
                self.assertNotIn('user', attribution)

    def test_with_provider_attribution_merges_existing_metadata_and_trace(self) -> None:
        payload = llm_client.with_provider_attribution(
            {
                'model': 'test/model',
                'metadata': {'campaign': 'unit'},
                'trace': {'span': 'existing'},
            },
            caller='resumer',
        )

        self.assertEqual(payload['metadata']['campaign'], 'unit')
        self.assertEqual(payload['metadata']['frida_caller'], 'summary')
        self.assertEqual(payload['metadata']['frida_slot'], 'summary_model')
        self.assertEqual(payload['trace']['span'], 'existing')
        self.assertEqual(payload['trace']['trace_name'], 'FridaDev')
        self.assertEqual(payload['trace']['generation_name'], llm_client.resolve_provider_title('resumer'))
        self.assertNotIn('user', payload)

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
                        'model': {'value': 'openai/gpt-5.1', 'origin': 'db'},
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
                        'reasoning_effort': {'value': 'medium', 'origin': 'db'},
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

        self.assertEqual(payload['model'], 'openai/gpt-5.1')
        self.assertEqual(payload['temperature'], 0.7)
        self.assertEqual(payload['top_p'], 0.9)
        self.assertEqual(payload['max_tokens'], 512)
        self.assertEqual(payload['reasoning'], {'effort': 'medium', 'exclude': True})
        self.assertNotIn('include_reasoning', payload)
        self.assertEqual(
            payload['metadata'],
            {'frida_caller': 'main_chat', 'frida_slot': 'main_model'},
        )
        self.assertEqual(
            payload['trace'],
            {'trace_name': 'FridaDev', 'generation_name': 'FridaDev/LLM'},
        )

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
        self.assertEqual(payload['reasoning'], {'effort': 'high', 'exclude': True})
        self.assertEqual(payload['metadata']['frida_caller'], 'main_chat')
        self.assertEqual(payload['metadata']['frida_slot'], 'main_model')

    def test_build_payload_omits_reasoning_for_non_gpt51_main_model(self) -> None:
        original = llm_client.runtime_settings.get_main_model_settings

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'model': {'value': 'openai/gpt-5.4-mini', 'origin': 'db'},
                        'reasoning_effort': {'value': 'high', 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
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

        self.assertNotIn('reasoning', payload)
        self.assertNotIn('include_reasoning', payload)

    def test_main_llm_reasoning_observability_from_payload_is_content_free(self) -> None:
        fields = llm_client.main_llm_reasoning_observability_from_payload(
            {
                'model': 'openai/gpt-5.1',
                'reasoning': {'effort': 'low', 'exclude': True},
                'reasoning_details': 'SHOULD NOT LEAK',
            }
        )

        self.assertEqual(fields['main_llm_reasoning_effort_requested'], 'low')
        self.assertEqual(fields['main_llm_reasoning_effort_effective'], 'low')
        self.assertTrue(fields['main_llm_reasoning_hidden'])
        self.assertNotIn('SHOULD NOT LEAK', str(fields))

    def test_read_openrouter_response_payload_strips_provider_reasoning_fields(self) -> None:
        class FakeResponse:
            def json(self):
                return {
                    'id': 'gen-with-reasoning',
                    'reasoning': 'top-level-hidden',
                    'choices': [
                        {
                            'message': {
                                'role': 'assistant',
                                'content': 'OK',
                                'reasoning_details': [{'text': 'SHOULD NOT LEAK'}],
                                'reasoning': 'message-hidden',
                            },
                        },
                    ],
                    'usage': {
                        'completion_tokens_details': {
                            'reasoning_tokens': 12,
                        },
                    },
                }

        payload = llm_client.read_openrouter_response_payload(FakeResponse())

        self.assertEqual(payload['choices'][0]['message']['content'], 'OK')
        self.assertNotIn('reasoning', payload)
        self.assertNotIn('reasoning', payload['choices'][0]['message'])
        self.assertNotIn('reasoning_details', payload['choices'][0]['message'])
        self.assertNotIn('SHOULD NOT LEAK', str(payload))

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
                        'title_identity_periodic': {'value': 'FridaDev/IdentityPeriodic', 'origin': 'db'},
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
                        'title_identity_periodic': {'value': 'FridaDev/IdentityPeriodic', 'origin': 'db'},
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
                'identity_periodic_agent_provider_response',
                {'provider_model': 'anthropic/claude-haiku-4.5'},
            )
        finally:
            llm_client.runtime_settings.get_main_model_settings = original_view

        self.assertEqual(
            observed,
            [
                (
                    'identity_periodic_agent_provider_response',
                    'identity_periodic_agent',
                    'FridaDev/IdentityPeriodic',
                    '',
                    'anthropic/claude-haiku-4.5',
                    None,
                    None,
                    None,
                )
            ],
        )


class LlmClientTextSanitizationTests(unittest.TestCase):
    def test_sanitize_provider_text_repairs_double_encoded_text(self) -> None:
        self.assertEqual(llm_client.sanitize_provider_text('FranÃ§ais'), 'Français')
        self.assertEqual(llm_client.sanitize_provider_text('Bonjour'), 'Bonjour')

    def test_extract_openrouter_text_uses_public_sanitizer(self) -> None:
        payload = {
            'choices': [
                {
                    'message': {
                        'content': ' CafÃ© ',
                    }
                }
            ]
        }

        self.assertEqual(llm_client.extract_openrouter_text(payload), 'Café')

    def test_extract_openrouter_text_accepts_provider_null_content_as_empty_text(self) -> None:
        payload = {
            'choices': [
                {
                    'message': {
                        'content': None,
                    }
                }
            ]
        }

        self.assertEqual(llm_client.extract_openrouter_text(payload), '')


if __name__ == '__main__':
    unittest.main()
