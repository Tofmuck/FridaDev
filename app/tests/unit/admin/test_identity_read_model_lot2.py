from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_read_model_service


class _MemoryStore:
    def get_latest_identity_staging_state(self) -> dict[str, object]:
        return {
            'conversation_id': 'conv-stage-lot2',
            'buffer_pairs': [],
            'buffer_pairs_count': 4,
            'buffer_target_pairs': 15,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'last_agent_status': 'buffering',
            'last_agent_reason': 'completed_no_change',
            'last_agent_run_ts': '2026-05-13T12:00:00+00:00',
            'updated_ts': '2026-05-13T12:10:00+00:00',
        }


class _LogStoreWithoutReasonCode:
    def read_chat_log_events(self, **_kwargs: object) -> dict[str, object]:
        return {'items': []}


class IdentityReadModelLot2Tests(unittest.TestCase):
    def test_current_buffer_and_last_completed_agent_are_separated_when_legacy_reason_is_terminal(self) -> None:
        staging = admin_identity_read_model_service.build_identity_staging_block(
            memory_store_module=_MemoryStore(),
            log_store_module=_LogStoreWithoutReasonCode(),
        )

        self.assertEqual(staging['last_agent_status'], 'buffering')
        self.assertIsNone(staging['last_agent_reason'])
        self.assertEqual(staging['current_buffer']['status'], 'buffering')
        self.assertEqual(staging['current_buffer']['reason_code'], 'below_threshold')
        self.assertEqual(staging['current_buffer']['pairs_count'], 4)
        self.assertEqual(staging['current_buffer']['target_pairs'], 15)
        self.assertFalse(staging['current_buffer']['frozen'])
        self.assertTrue(staging['last_completed_agent']['present'])
        self.assertEqual(staging['last_completed_agent']['status'], 'ok')
        self.assertEqual(staging['last_completed_agent']['reason_code'], 'completed_no_change')
        self.assertEqual(staging['last_completed_agent']['run_ts'], '2026-05-13T12:00:00+00:00')
        self.assertNotIn('buffer_pairs', staging)
        self.assertNotIn('buffer_pairs', staging['current_buffer'])
        self.assertNotIn('buffer_pairs', staging['last_completed_agent'])


if __name__ == '__main__':
    unittest.main()
