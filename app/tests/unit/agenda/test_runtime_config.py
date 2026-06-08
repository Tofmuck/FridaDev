from __future__ import annotations

import unittest

from agenda import runtime_config


class AgendaRuntimeConfigTests(unittest.TestCase):
    def test_build_admin_read_model_exposes_only_content_free_redacted_secret_state(self) -> None:
        fake_secret = 'fake-agenda-secret-must-not-leak'
        payload = {
            'mode': {'value': 'shadow', 'is_secret': False, 'origin': 'db'},
            'caldav_account': {'value': 'tof', 'is_secret': False, 'origin': 'db'},
            'caldav_app_password': {'is_secret': True, 'is_set': True, 'origin': 'admin_ui'},
        }

        read_model = runtime_config.build_admin_read_model(
            payload,
            source='db',
            source_reason='db_row',
            secret_sources={'caldav_app_password': 'db_encrypted'},
        )

        self.assertEqual(read_model['schema_version'], 'frida_agenda_runtime_settings_v1')
        self.assertEqual(read_model['mode'], 'shadow')
        self.assertEqual(read_model['caldav_identity']['account'], 'tof')
        self.assertFalse(read_model['caldav_identity']['service_account'])
        self.assertEqual(
            read_model['caldav_secret'],
            {
                'field': 'caldav_app_password',
                'configured': True,
                'source_configured': True,
                'source': 'db_encrypted',
                'redacted': True,
            },
        )
        self.assertFalse(read_model['caldav_access'])
        self.assertFalse(read_model['nextcloud_access'])
        self.assertTrue(read_model['content_free'])
        self.assertNotIn(fake_secret, repr(read_model))
        self.assertNotIn('value_encrypted', repr(read_model))

    def test_build_admin_read_model_keeps_missing_secret_as_boolean_redacted_state(self) -> None:
        read_model = runtime_config.build_admin_read_model(
            {
                'mode': {'value': 'off', 'is_secret': False, 'origin': 'seed_default'},
                'caldav_account': {'value': 'tof', 'is_secret': False, 'origin': 'seed_default'},
                'caldav_app_password': {'is_secret': True, 'is_set': False, 'origin': 'env_seed'},
            },
            source='env',
            source_reason='empty_table',
            secret_sources={'caldav_app_password': 'missing'},
        )

        self.assertEqual(read_model['mode'], 'off')
        self.assertFalse(read_model['caldav_secret']['configured'])
        self.assertFalse(read_model['caldav_secret']['source_configured'])
        self.assertEqual(read_model['caldav_secret']['source'], 'missing')


if __name__ == '__main__':
    unittest.main()
