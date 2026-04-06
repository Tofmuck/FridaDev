from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
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

from memory import memory_identity_read_model


class _NoopLogger:
    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakeCursor:
    def __init__(self, count_row: tuple[Any, ...], rows: list[tuple[Any, ...]]) -> None:
        self._count_row = count_row
        self._rows = rows
        self._last_query = ''

    def __enter__(self) -> '_FakeCursor':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, _params: tuple[Any, ...]) -> None:
        self._last_query = ' '.join(query.lower().split())

    def fetchone(self) -> tuple[Any, ...]:
        if 'count(*)' in self._last_query:
            return self._count_row
        return self._rows[0] if self._rows else (0,)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class _FakeConn:
    def __init__(self, count_row: tuple[Any, ...], rows: list[tuple[Any, ...]]) -> None:
        self._count_row = count_row
        self._rows = rows

    def __enter__(self) -> '_FakeConn':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._count_row, self._rows)


class IdentityReadModelPhase2Tests(unittest.TestCase):
    def test_list_identity_fragments_returns_compact_snapshot(self) -> None:
        rows = [
            (
                'frag-1',
                'llm',
                'Fragment legacy',
                0.7,
                datetime(2026, 4, 6, 9, 0, tzinfo=timezone.utc),
                datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                None,
                'durable',
                'self_description',
                'frequent',
                'user',
                'strong',
                0.9,
                'accepted',
                'fragment legacy',
                'reason',
                'conv-1',
                'none',
                '',
                '',
                None,
            )
        ]
        snapshot = memory_identity_read_model.list_identity_fragments(
            'llm',
            limit=5,
            conn_factory=lambda: _FakeConn((3,), rows),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 3)
        self.assertEqual(snapshot['limit'], 5)
        self.assertEqual(snapshot['items'][0]['identity_id'], 'frag-1')
        self.assertEqual(snapshot['items'][0]['content'], 'Fragment legacy')

    def test_list_identity_evidence_returns_compact_snapshot(self) -> None:
        rows = [
            (
                'ev-1',
                'conv-1',
                'user',
                'Evidence text',
                'evidence text',
                'episodic',
                'self_description',
                'rare',
                'situation',
                'weak',
                0.6,
                'accepted',
                'reason',
                None,
                datetime(2026, 4, 6, 11, 0, tzinfo=timezone.utc),
            )
        ]
        snapshot = memory_identity_read_model.list_identity_evidence(
            'user',
            limit=7,
            conn_factory=lambda: _FakeConn((4,), rows),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 4)
        self.assertEqual(snapshot['limit'], 7)
        self.assertEqual(snapshot['items'][0]['evidence_id'], 'ev-1')
        self.assertEqual(snapshot['items'][0]['content'], 'Evidence text')

    def test_list_identity_conflicts_returns_flattened_pairs(self) -> None:
        rows = [
            (
                'conf-1',
                0.85,
                'contradiction',
                'open',
                datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc),
                None,
                'frag-a',
                'llm',
                'Version A',
                'accepted',
                None,
                'none',
                'frag-b',
                'llm',
                'Version B',
                'deferred',
                None,
                'force_reject',
            )
        ]
        snapshot = memory_identity_read_model.list_identity_conflicts(
            'llm',
            limit=9,
            conn_factory=lambda: _FakeConn((2,), rows),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 2)
        self.assertEqual(snapshot['limit'], 9)
        self.assertEqual(snapshot['items'][0]['conflict_id'], 'conf-1')
        self.assertEqual(snapshot['items'][0]['identity_id_a'], 'frag-a')
        self.assertEqual(snapshot['items'][0]['content_b'], 'Version B')


if __name__ == '__main__':
    unittest.main()
