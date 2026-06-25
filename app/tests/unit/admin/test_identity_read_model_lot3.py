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
            'conversation_id': 'conv-stage-lot3',
            'buffer_pairs': [],
            'buffer_pairs_count': 0,
            'buffer_target_pairs': 5,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'last_agent_status': 'applied',
            'last_agent_reason': 'applied',
            'last_agent_run_ts': '2026-05-13T12:00:00+00:00',
            'updated_ts': '2026-05-13T12:00:00+00:00',
        }


class _LogStoreWithOkReasonCode:
    def read_chat_log_events(self, **_kwargs: object) -> dict[str, object]:
        return {
            'items': [
                {
                    'conversation_id': 'conv-stage-lot3',
                    'turn_id': 'turn-lot3',
                    'ts': '2026-05-13T12:00:01+00:00',
                    'stage': 'mutable_identity_judge',
                    'status': 'ok',
                    'payload': {
                        'reason_code': 'applied',
                        'runtime_pipeline': 'mutable_identity_judge_v2_add_only',
                        'prompt_kind': 'mutable_identity_judge_v2',
                        'write_mode': 'enforced',
                        'writes_applied': True,
                        'buffer_pairs_count': 5,
                        'buffer_target_pairs': 5,
                        'judge_status': 'ok',
                        'apply_status': 'ok',
                        'verdict_count': 1,
                        'verdict_counts': {'add': 1},
                        'subjects_seen': ['llm', 'user'],
                        'subjects_touched': ['user'],
                        'continuity_kinds': ['limit'],
                        'reason_codes': ['explicit_self_formulation'],
                        'source_refs_count': 1,
                        'guard_notes_count': 1,
                        'applied_count': 1,
                        'skipped_count': 0,
                        'failed_count': 0,
                        'promotion_count': 0,
                        'promotions': [],
                        'outcomes': [
                            {
                                'subject': 'user',
                                'verdict': 'add',
                                'status': 'applied',
                                'reason_code': 'add_applied',
                                'old_chars': 0,
                                'new_chars': 42,
                                'continuity_kind': 'limit',
                                'source_refs_count': 1,
                                'guard_notes_count': 1,
                            }
                        ],
                        'rejection_reasons': {},
                    },
                }
            ]
        }


class IdentityReadModelLot3Tests(unittest.TestCase):
    def test_latest_agent_activity_keeps_ok_reason_code_from_event_payload(self) -> None:
        staging = admin_identity_read_model_service.build_identity_staging_block(
            memory_store_module=_MemoryStore(),
            log_store_module=_LogStoreWithOkReasonCode(),
        )

        activity = staging['latest_agent_activity']
        self.assertTrue(activity['present'])
        self.assertEqual(activity['status'], 'ok')
        self.assertEqual(activity['reason_code'], 'applied')
        self.assertTrue(activity['writes_applied'])
        self.assertEqual(activity['promotion_count'], 0)
        self.assertEqual(activity['stage'], 'mutable_identity_judge')
        self.assertEqual(activity['runtime_pipeline'], 'mutable_identity_judge_v2_add_only')
        self.assertEqual(activity['buffer_target_pairs'], 5)
        self.assertEqual(activity['verdict_counts'], {'add': 1})
        self.assertNotIn('operation_kinds', activity)
        self.assertEqual(activity['outcome_count'], 1)
        self.assertEqual(activity['outcome_summaries'][0]['new_chars'], 42)
        self.assertNotIn('old_sha256_12', activity['outcome_summaries'][0])
        self.assertNotIn('new_sha256_12', activity['outcome_summaries'][0])
        self.assertNotIn('content', activity['outcome_summaries'][0])
        self.assertNotIn('proposition', activity['outcome_summaries'][0])
        self.assertEqual(staging['last_completed_agent']['reason_code'], 'applied')
        self.assertNotIn('outcomes', activity)
        self.assertNotIn('buffer_pairs', activity)


if __name__ == '__main__':
    unittest.main()
