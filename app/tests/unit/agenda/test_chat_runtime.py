from __future__ import annotations

import unittest

from agenda import chat_runtime


class AgendaChatRuntimeLot1Tests(unittest.TestCase):
    def test_normalize_agenda_enabled_matches_frontend_payload_contract(self) -> None:
        self.assertFalse(chat_runtime.normalize_agenda_enabled(None))
        self.assertFalse(chat_runtime.normalize_agenda_enabled(False))
        self.assertFalse(chat_runtime.normalize_agenda_enabled('off'))
        self.assertTrue(chat_runtime.normalize_agenda_enabled(True))
        self.assertTrue(chat_runtime.normalize_agenda_enabled('1'))
        self.assertTrue(chat_runtime.normalize_agenda_enabled('enabled'))

    def test_enabled_turn_is_content_free_noop_without_caldav_or_secret_access(self) -> None:
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Lis mon agenda demain',
            conversation_id='conv-agenda',
            now_iso='2026-06-08T00:00:00Z',
        )

        self.assertTrue(result.enabled)
        self.assertFalse(result.used)
        self.assertEqual(result.status, 'not_implemented')
        self.assertEqual(result.reason_code, chat_runtime.REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED)
        payload = result.observability_payload
        self.assertEqual(payload['schema_version'], 'frida_agenda_lot1_noop_v1')
        self.assertFalse(payload['runtime_available'])
        self.assertFalse(payload['caldav_access'])
        self.assertFalse(payload['nextcloud_access'])
        self.assertFalse(payload['secret_access'])
        self.assertFalse(payload['mutation_attempted'])
        self.assertTrue(payload['content_free'])
        self.assertNotIn('Lis mon agenda demain', repr(payload))

    def test_disabled_turn_returns_local_disabled_noop(self) -> None:
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': False},
            user_msg='Ignore Agenda',
        )

        self.assertFalse(result.enabled)
        self.assertFalse(result.used)
        self.assertEqual(result.status, 'disabled')
        self.assertEqual(result.reason_code, 'agenda_toggle_off')
        self.assertFalse(result.observability_payload['caldav_access'])


if __name__ == '__main__':
    unittest.main()
