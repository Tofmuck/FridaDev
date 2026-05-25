from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import memory_identity_staging


class _NoopLogger:
    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakeCursor:
    def __init__(self, existing_row: tuple[Any, ...]) -> None:
        self._existing_row = existing_row
        self._result_row: tuple[Any, ...] | None = None
        self._query_kind = ''

    def __enter__(self) -> '_FakeCursor':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        normalized = ' '.join(query.lower().split())
        if normalized.startswith('select'):
            self._query_kind = 'select'
            return
        self._query_kind = 'insert'
        (
            conversation_id,
            buffer_pairs_json,
            buffer_pairs_count,
            buffer_target_pairs,
            auto_canonization_suspended,
            last_agent_status,
            last_agent_reason,
        ) = params
        self._result_row = (
            conversation_id,
            json.loads(buffer_pairs_json),
            buffer_pairs_count,
            buffer_target_pairs,
            auto_canonization_suspended,
            last_agent_status,
            last_agent_reason,
            self._existing_row[7],
            self._existing_row[8],
            '2026-05-13T12:10:00+00:00',
        )

    def fetchone(self) -> tuple[Any, ...] | None:
        if self._query_kind == 'select':
            return self._existing_row
        return self._result_row


class _FakeConn:
    def __init__(self, existing_row: tuple[Any, ...]) -> None:
        self._existing_row = existing_row
        self.committed = False

    def __enter__(self) -> '_FakeConn':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._existing_row)

    def commit(self) -> None:
        self.committed = True


class IdentityStagingLot2Tests(unittest.TestCase):
    def test_append_pair_after_completed_no_change_starts_buffer_without_terminal_reason(self) -> None:
        existing_row = (
            'conv-stage-lot2',
            [],
            0,
            memory_identity_staging.DEFAULT_BUFFER_TARGET_PAIRS,
            False,
            'completed_no_change',
            'completed_no_change',
            '2026-05-13T12:00:00+00:00',
            '2026-05-13T11:00:00+00:00',
            '2026-05-13T12:00:00+00:00',
        )
        conn = _FakeConn(existing_row)

        state = memory_identity_staging.append_identity_staging_pair(
            'conv-stage-lot2',
            [
                {'role': 'user', 'content': 'message utilisateur redacted'},
                {'role': 'assistant', 'content': 'message assistant redacted'},
            ],
            target_pairs=memory_identity_staging.DEFAULT_BUFFER_TARGET_PAIRS,
            conn_factory=lambda: conn,
            logger=_NoopLogger(),
        )

        self.assertIsNotNone(state)
        self.assertEqual(state['buffer_pairs_count'], 1)
        self.assertEqual(state['buffer_target_pairs'], memory_identity_staging.DEFAULT_BUFFER_TARGET_PAIRS)
        self.assertFalse(state['buffer_frozen'])
        self.assertEqual(state['last_agent_status'], 'buffering')
        self.assertIsNone(state['last_agent_reason'])
        self.assertEqual(state['last_agent_run_ts'], '2026-05-13T12:00:00+00:00')
        self.assertTrue(state['pair_appended'])
        self.assertTrue(conn.committed)

    def test_append_pair_resets_legacy_target_buffer_without_reusing_old_window(self) -> None:
        existing_row = (
            'conv-stage-lot2-retarget',
            [
                {
                    'user': {'role': 'user', 'content': 'ancien utilisateur'},
                    'assistant': {'role': 'assistant', 'content': 'ancien assistant'},
                }
            ],
            1,
            15,
            False,
            'buffering',
            'below_threshold',
            None,
            '2026-05-13T11:00:00+00:00',
            '2026-05-13T12:00:00+00:00',
        )
        conn = _FakeConn(existing_row)

        state = memory_identity_staging.append_identity_staging_pair(
            'conv-stage-lot2-retarget',
            [
                {'role': 'user', 'content': 'nouvel utilisateur'},
                {'role': 'assistant', 'content': 'nouvel assistant'},
            ],
            target_pairs=memory_identity_staging.DEFAULT_BUFFER_TARGET_PAIRS,
            conn_factory=lambda: conn,
            logger=_NoopLogger(),
        )

        self.assertIsNotNone(state)
        self.assertEqual(state['buffer_pairs_count'], 1)
        self.assertEqual(state['buffer_target_pairs'], memory_identity_staging.DEFAULT_BUFFER_TARGET_PAIRS)
        self.assertEqual(state['buffer_pairs'][0]['user']['content'], 'nouvel utilisateur')
        self.assertEqual(state['buffer_pairs'][0]['assistant']['content'], 'nouvel assistant')
        self.assertEqual(state['last_agent_status'], 'buffering')
        self.assertIsNone(state['last_agent_reason'])


if __name__ == '__main__':
    unittest.main()
