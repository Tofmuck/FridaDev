from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs


class AdminLogsModeObservationTests(unittest.TestCase):
    def _write_log(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text(
            '\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n',
            encoding='utf-8',
        )

    def test_summarize_mode_observation_returns_current_mode_observed_segment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_log(
                tmp_path / 'admin-20260331-153851.log.jsonl',
                [
                    {'timestamp': '2026-03-31T07:58:01Z', 'event': 'hermeneutic_mode', 'mode': 'shadow'},
                    {'timestamp': '2026-03-31T07:59:03Z', 'event': 'hermeneutic_mode', 'mode': 'shadow'},
                ],
            )
            self._write_log(
                tmp_path / 'admin.log.jsonl',
                [
                    {'timestamp': '2026-04-03T15:38:51Z', 'event': 'hermeneutic_mode', 'mode': 'enforced_all'},
                    {'timestamp': '2026-04-09T12:00:00Z', 'event': 'hermeneutic_mode', 'mode': 'enforced_all'},
                ],
            )

            summary = admin_logs.summarize_hermeneutic_mode_observation(
                'enforced_all',
                log_path=tmp_path / 'admin.log.jsonl',
            )

        self.assertEqual(summary['source'], 'admin_logs_retained_observations')
        self.assertEqual(summary['semantics'], 'current_mode_observed_segment_not_exact_switch')
        self.assertTrue(summary['current_mode_observed'])
        self.assertEqual(summary['observed_since'], '2026-04-03T15:38:51Z')
        self.assertEqual(summary['last_observed_at'], '2026-04-09T12:00:00Z')
        self.assertEqual(summary['observation_count'], 2)
        self.assertEqual(summary['previous_mode'], 'shadow')
        self.assertEqual(summary['previous_mode_last_observed_at'], '2026-03-31T07:59:03Z')
        self.assertEqual(summary['latest_observed_mode'], 'enforced_all')
        self.assertEqual(summary['latest_observed_at'], '2026-04-09T12:00:00Z')
        self.assertFalse(summary['exact_switch_known'])

    def test_summarize_mode_observation_does_not_invent_current_mode_when_unobserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_log(
                tmp_path / 'admin.log.jsonl',
                [
                    {'timestamp': '2026-03-31T07:59:03Z', 'event': 'hermeneutic_mode', 'mode': 'shadow'},
                ],
            )

            summary = admin_logs.summarize_hermeneutic_mode_observation(
                'enforced_all',
                log_path=tmp_path / 'admin.log.jsonl',
            )

        self.assertFalse(summary['current_mode_observed'])
        self.assertIsNone(summary['observed_since'])
        self.assertIsNone(summary['last_observed_at'])
        self.assertEqual(summary['observation_count'], 0)
        self.assertIsNone(summary['previous_mode'])
        self.assertIsNone(summary['previous_mode_last_observed_at'])
        self.assertEqual(summary['latest_observed_mode'], 'shadow')
        self.assertEqual(summary['latest_observed_at'], '2026-03-31T07:59:03Z')
        self.assertFalse(summary['exact_switch_known'])


if __name__ == '__main__':
    unittest.main()
