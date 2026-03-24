from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
import config


class RuntimeSettingsSchemaTests(unittest.TestCase):
    def test_section_order_is_fixed(self) -> None:
        self.assertEqual(
            runtime_settings.list_sections(),
            (
                'main_model',
                'arbiter_model',
                'summary_model',
                'embedding',
                'database',
                'services',
                'resources',
            ),
        )

    def test_main_model_includes_global_sampling_fields(self) -> None:
        spec = runtime_settings.get_section_spec('main_model')
        self.assertIn('temperature', spec.field_names())
        self.assertIn('top_p', spec.field_names())

    def test_embedding_model_exists_but_is_not_seeded_from_env(self) -> None:
        spec = runtime_settings.get_field_spec('embedding', 'model')
        self.assertEqual(spec.value_type, 'text')
        self.assertFalse(spec.is_secret)
        self.assertFalse(spec.seed_from_env)
        self.assertEqual(spec.seed_default, 'intfloat/multilingual-e5-small')

    def test_database_dsn_stays_out_of_env_seed(self) -> None:
        spec = runtime_settings.get_field_spec('database', 'dsn')
        self.assertTrue(spec.is_secret)
        self.assertEqual(spec.env_var, 'FRIDA_MEMORY_DB_DSN')
        self.assertFalse(spec.seed_from_env)

    def test_describe_section_exposes_public_metadata(self) -> None:
        description = runtime_settings.describe_section('services')
        self.assertEqual(description['name'], 'services')
        self.assertIn('fields', description)
        self.assertTrue(any(field['key'] == 'crawl4ai_token' and field['is_secret'] for field in description['fields']))

    def test_normalize_stored_payload_rejects_plain_secret_value(self) -> None:
        with self.assertRaisesRegex(ValueError, 'secret field does not accept plain value'):
            runtime_settings.normalize_stored_payload(
                'main_model',
                {
                    'api_key': {
                        'value': 'plain-text-should-not-pass',
                    }
                },
            )

    def test_normalize_stored_payload_accepts_secret_encrypted_value(self) -> None:
        normalized = runtime_settings.normalize_stored_payload(
            'main_model',
            {
                'api_key': {
                    'value_encrypted': 'ciphertext',
                    'origin': 'env_seed',
                }
            },
        )
        self.assertEqual(
            normalized,
            {
                'api_key': {
                    'is_secret': True,
                    'is_set': True,
                    'origin': 'env_seed',
                    'value_encrypted': 'ciphertext',
                }
            },
        )

    def test_redact_payload_for_api_hides_secret_value(self) -> None:
        redacted = runtime_settings.redact_payload_for_api(
            'services',
            {
                'crawl4ai_token': {
                    'value_encrypted': 'ciphertext',
                    'origin': 'admin_ui',
                },
                'crawl4ai_url': {
                    'value': 'http://127.0.0.1:11235',
                    'origin': 'env_seed',
                },
            },
        )
        self.assertEqual(
            redacted,
            {
                'crawl4ai_token': {
                    'is_secret': True,
                    'is_set': True,
                    'origin': 'admin_ui',
                },
                'crawl4ai_url': {
                    'value': 'http://127.0.0.1:11235',
                    'is_secret': False,
                    'origin': 'env_seed',
                },
            },
        )

    def test_build_env_seed_bundle_keeps_secret_value_out_of_payload(self) -> None:
        bundle = runtime_settings.build_env_seed_bundle('main_model')
        self.assertEqual(bundle.section, 'main_model')
        self.assertEqual(bundle.payload['base_url']['value'], config.OR_BASE)
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

    def test_get_unseeded_sections_uses_missing_rows_as_signal(self) -> None:
        missing = runtime_settings.get_unseeded_sections(('main_model', 'services'))
        self.assertEqual(
            missing,
            (
                'arbiter_model',
                'summary_model',
                'embedding',
                'database',
                'resources',
            ),
        )

    def test_build_env_seed_plan_skips_existing_sections(self) -> None:
        plan = runtime_settings.build_env_seed_plan(('main_model', 'embedding', 'services'))
        self.assertEqual(
            tuple(bundle.section for bundle in plan),
            (
                'arbiter_model',
                'summary_model',
                'database',
                'resources',
            ),
        )


if __name__ == '__main__':
    unittest.main()
