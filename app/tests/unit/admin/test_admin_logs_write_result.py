from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from admin import admin_logs


class AdminLogsWriteResultTests(unittest.TestCase):
    def test_log_event_returns_true_only_after_writing_sanitized_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / 'admin.log.jsonl'
            with (
                mock.patch.object(admin_logs, 'LOG_PATH', log_path),
                mock.patch.object(admin_logs, '_BOOTSTRAP_DONE', True),
            ):
                stored = admin_logs.log_event(
                    'write_result_success',
                    safe_field='safe',
                    content='RAW CONTENT MUST NOT BE STORED',
                )

            lines = log_path.read_text(encoding='utf-8').splitlines()

        self.assertIs(stored, True)
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload['event'], 'write_result_success')
        self.assertEqual(payload['safe_field'], 'safe')
        self.assertNotIn('content', payload)
        self.assertNotIn('RAW CONTENT MUST NOT BE STORED', lines[0])

    def test_log_event_returns_false_when_no_line_can_be_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blocked_path = Path(tmp) / 'blocked-as-file'
            blocked_path.mkdir()
            with (
                mock.patch.object(admin_logs, 'LOG_PATH', blocked_path),
                mock.patch.object(admin_logs, '_BOOTSTRAP_DONE', True),
                self.assertLogs(admin_logs.logger, level='ERROR') as captured,
            ):
                stored = admin_logs.log_event(
                    'write_result_failure',
                    content='RAW FAILURE CONTENT MUST NOT LEAK',
                )

            self.assertEqual(list(blocked_path.iterdir()), [])

        self.assertIs(stored, False)
        self.assertNotIn('RAW FAILURE CONTENT MUST NOT LEAK', '\n'.join(captured.output))


if __name__ == '__main__':
    unittest.main()
