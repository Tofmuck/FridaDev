from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from memory import memory_trace_summary_store, memory_traces_summaries


class MemoryTraceSummaryStoreBoundaryTests(unittest.TestCase):
    def test_facade_delegates_trace_persistence_with_compatibility_hooks(self) -> None:
        observed: dict[str, object] = {}

        def fake_save_new_traces(conversation, **kwargs) -> None:
            observed["conversation"] = conversation
            observed.update(kwargs)

        fake_store = SimpleNamespace(save_new_traces=fake_save_new_traces)
        conversation = {"id": "synthetic-boundary", "messages": []}
        conn_factory = lambda: object()
        embed_fn = lambda *_args, **_kwargs: [0.1]
        logger = SimpleNamespace()

        with patch.object(
            memory_traces_summaries,
            "memory_trace_summary_store",
            fake_store,
            create=True,
        ):
            memory_traces_summaries.save_new_traces(
                conversation,
                conn_factory=conn_factory,
                embed_fn=embed_fn,
                logger=logger,
            )

        self.assertIs(observed.get("conversation"), conversation)
        self.assertIs(observed["conn_factory"], conn_factory)
        self.assertIs(observed["embed_fn"], embed_fn)
        self.assertIs(observed["logger"], logger)
        self.assertIs(
            observed["message_is_trace_eligible_fn"],
            memory_traces_summaries._message_is_trace_eligible,
        )
        self.assertIs(
            observed["trace_exists_for_message_fn"],
            memory_traces_summaries._trace_exists_for_message,
        )
        self.assertIs(
            observed["embed_with_purpose_fn"],
            memory_traces_summaries._embed_with_purpose,
        )

    def test_summary_facade_propagates_writer_storage_outcome(self) -> None:
        observed: dict[str, object] = {}

        def fake_save_summary(conversation_id, summary, **kwargs) -> bool:
            observed['conversation_id'] = conversation_id
            observed['summary'] = summary
            observed.update(kwargs)
            return False

        fake_store = SimpleNamespace(save_summary=fake_save_summary)
        summary = {'id': 'summary-boundary', 'content': 'synthetic summary'}
        conn_factory = lambda: object()
        embed_fn = lambda *_args, **_kwargs: [0.1]
        logger = SimpleNamespace()

        with patch.object(memory_traces_summaries, 'memory_trace_summary_store', fake_store):
            stored = memory_traces_summaries.save_summary(
                'conversation-boundary',
                summary,
                conn_factory=conn_factory,
                embed_fn=embed_fn,
                logger=logger,
            )

        self.assertFalse(stored)
        self.assertEqual(observed['conversation_id'], 'conversation-boundary')
        self.assertIs(observed['summary'], summary)
        self.assertIs(observed['conn_factory'], conn_factory)
        self.assertIs(observed['embed_fn'], embed_fn)
        self.assertIs(observed['logger'], logger)
        self.assertIs(observed['embed_with_purpose_fn'], memory_traces_summaries._embed_with_purpose)

    def test_committed_text_is_stored_when_embedding_is_unavailable(self) -> None:
        observed: dict[str, object] = {'sql': '', 'params': None, 'commits': 0, 'warnings': []}

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params):
                observed['sql'] = ' '.join(str(sql).split())
                observed['params'] = params

            def fetchone(self):
                return ('summary-text-only',)

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return Cursor()

            def commit(self):
                observed['commits'] += 1

        logger = SimpleNamespace(
            warning=lambda *args: observed['warnings'].append(args),
            info=lambda *_args: None,
            error=lambda *_args: None,
        )

        stored = memory_trace_summary_store.save_summary(
            'conversation-text-only',
            {
                'id': 'summary-text-only',
                'start_ts': '2026-09-02T10:00:00Z',
                'end_ts': '2026-09-02T10:02:00Z',
                'content': 'synthetic durable text',
            },
            conn_factory=lambda: Connection(),
            embed_fn=lambda *_args, **_kwargs: self.fail('embedding wrapper controls this test'),
            logger=logger,
            embed_with_purpose_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError('synthetic embedding unavailable')
            ),
        )

        self.assertTrue(stored)
        self.assertEqual(observed['commits'], 1)
        self.assertIn('ON CONFLICT (id) DO NOTHING', observed['sql'])
        self.assertEqual(observed['params'][4], 'synthetic durable text')
        self.assertIsNone(observed['params'][5])
        self.assertTrue(any(args[0] == 'summary_embed_skip err=%s' for args in observed['warnings']))

    def test_idempotent_conflict_requires_exact_existing_text_row(self) -> None:
        for existing_row_matches in (True, False):
            with self.subTest(existing_row_matches=existing_row_matches):
                observed = {'commits': 0, 'errors': [], 'queries': []}
                existing_row = {
                    'id': 'summary-conflict',
                    'conversation_id': 'conversation-conflict',
                    'start_ts': '2026-09-02T10:00:00Z',
                    'end_ts': '2026-09-02T10:02:00Z',
                    'content': (
                        'synthetic conflict text'
                        if existing_row_matches
                        else 'different pre-existing text'
                    ),
                }

                class Cursor:
                    def __init__(self):
                        self.row = None

                    def __enter__(self):
                        return self

                    def __exit__(self, exc_type, exc, tb):
                        return False

                    def execute(self, sql, params):
                        compact_sql = ' '.join(str(sql).split())
                        observed['queries'].append(compact_sql)
                        if compact_sql.startswith('INSERT INTO summaries'):
                            self.row = None
                            return
                        required_predicates = (
                            'WHERE id = %s',
                            'AND conversation_id = %s',
                            'AND start_ts IS NOT DISTINCT FROM %s::timestamptz',
                            'AND end_ts IS NOT DISTINCT FROM %s::timestamptz',
                            'AND content = %s',
                        )
                        if not all(predicate in compact_sql for predicate in required_predicates):
                            raise AssertionError('exact conflict comparison predicates are required')
                        summary_id, conversation_id, start_ts, end_ts, content = params
                        self.row = (1,) if (
                            existing_row['id'] == summary_id
                            and existing_row['conversation_id'] == conversation_id
                            and existing_row['start_ts'] == start_ts
                            and existing_row['end_ts'] == end_ts
                            and existing_row['content'] == content
                        ) else None

                    def fetchone(self):
                        return self.row

                class Connection:
                    def __enter__(self):
                        return self

                    def __exit__(self, exc_type, exc, tb):
                        return False

                    def cursor(self):
                        return Cursor()

                    def commit(self):
                        observed['commits'] += 1

                stored = memory_trace_summary_store.save_summary(
                    'conversation-conflict',
                    {
                        'id': 'summary-conflict',
                        'start_ts': '2026-09-02T10:00:00Z',
                        'end_ts': '2026-09-02T10:02:00Z',
                        'content': 'synthetic conflict text',
                    },
                    conn_factory=lambda: Connection(),
                    embed_fn=lambda *_args, **_kwargs: [0.1],
                    logger=SimpleNamespace(
                        warning=lambda *_args: None,
                        info=lambda *_args: None,
                        error=lambda *args: observed['errors'].append(args),
                    ),
                    embed_with_purpose_fn=lambda *_args, **_kwargs: [0.1],
                )

                self.assertEqual(stored, existing_row_matches)
                self.assertEqual(observed['commits'], 1 if existing_row_matches else 0)
                self.assertIn('ON CONFLICT (id) DO NOTHING RETURNING id', observed['queries'][0])
                self.assertTrue(observed['queries'][1].startswith('SELECT 1 FROM summaries'))
                if existing_row_matches:
                    self.assertEqual(observed['errors'], [])
                else:
                    self.assertEqual(observed['errors'][0][0], 'save_summary_conflict_mismatch conv=%s summary_id=%s')


if __name__ == "__main__":
    unittest.main()
