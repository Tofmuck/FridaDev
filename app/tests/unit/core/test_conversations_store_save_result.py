from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import assistant_turn_state
from core import conversations_store


class TransactionalConversationDb:
    def __init__(self, *, catalog: dict, messages: list[dict]) -> None:
        self.catalog = copy.deepcopy(catalog)
        self.messages = copy.deepcopy(messages)
        self.statements: list[str] = []

    def connect(self):
        return TransactionalConversationConnection(self)


class TransactionalConversationConnection:
    def __init__(self, database: TransactionalConversationDb) -> None:
        self.database = database
        self.pending_catalog = copy.deepcopy(database.catalog)
        self.pending_messages = copy.deepcopy(database.messages)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.rollback()
        return False

    def cursor(self, **_kwargs):
        return TransactionalConversationCursor(self)

    def commit(self):
        self.database.catalog = copy.deepcopy(self.pending_catalog)
        self.database.messages = copy.deepcopy(self.pending_messages)

    def rollback(self):
        self.pending_catalog = copy.deepcopy(self.database.catalog)
        self.pending_messages = copy.deepcopy(self.database.messages)


class TransactionalConversationCursor:
    def __init__(self, connection: TransactionalConversationConnection) -> None:
        self.connection = connection
        self.row = None
        self.rows: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        compact_sql = ' '.join(sql.split())
        self.connection.database.statements.append(compact_sql)
        self.row = None
        self.rows = []
        if compact_sql.startswith('SELECT role, content, timestamp, summarized_by, embedded, meta'):
            self.rows = copy.deepcopy(self.connection.pending_messages)
            return
        if compact_sql.startswith('INSERT INTO conversations'):
            existing = self.connection.pending_catalog or {}
            preserve_deleted = bool(params[7])
            self.connection.pending_catalog = {
                'id': params[0],
                'title': params[1],
                'created_at': existing.get('created_at', params[2]),
                'updated_at': params[3],
                'message_count': params[4],
                'last_message_preview': params[5],
                'workspace_folder_id': params[6] or existing.get('workspace_folder_id'),
                'deleted_at': existing.get('deleted_at') if preserve_deleted else None,
            }
            self.row = {'id': params[0]}
            return
        if compact_sql.startswith('DELETE FROM conversation_messages'):
            self.connection.pending_messages = []
            return
        if compact_sql.startswith('UPDATE conversations SET title'):
            if not self.connection.pending_catalog:
                return
            self.connection.pending_catalog['title'] = params[0]
            self.connection.pending_catalog['updated_at'] = datetime(
                2026, 9, 4, 13, 0, tzinfo=timezone.utc
            )
            self.row = copy.deepcopy(self.connection.pending_catalog)
            return
        raise AssertionError(f'unexpected SQL: {compact_sql}')

    def executemany(self, sql, rows):
        compact_sql = ' '.join(sql.split())
        self.connection.database.statements.append(compact_sql)
        stored = []
        for row in rows:
            raw_meta = getattr(row[7], 'obj', row[7])
            stored.append(
                {
                    'role': row[2],
                    'content': row[3],
                    'timestamp': row[4],
                    'summarized_by': row[5],
                    'embedded': row[6],
                    'meta': copy.deepcopy(raw_meta),
                }
            )
        self.connection.pending_messages = stored

    def fetchone(self):
        return copy.deepcopy(self.row)

    def fetchall(self):
        return copy.deepcopy(self.rows)


class ConversationsStoreSaveResultTests(unittest.TestCase):
    def test_dialogic_presence_meta_survives_storage_and_rehydration(self) -> None:
        marker = assistant_turn_state.build_dialogic_presence_assistant_turn_meta()
        normalized = conversations_store.normalize_messages_for_storage(
            [
                {
                    'role': 'assistant',
                    'content': '...',
                    'timestamp': '2026-07-23T09:00:01Z',
                    'meta': marker,
                }
            ],
            ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                raw,
                now_iso_func=lambda: self.fail('valid timestamp must not use now'),
            ),
            coerce_bool_func=conversations_store.coerce_bool,
        )

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, *_args, **_kwargs):
                return None

            def fetchall(self):
                return [
                    {
                        'role': normalized[0]['role'],
                        'content': normalized[0]['content'],
                        'timestamp': datetime(2026, 7, 23, 9, 0, 1, tzinfo=timezone.utc),
                        'summarized_by': None,
                        'embedded': False,
                        'meta': normalized[0]['meta'],
                    }
                ]

        class FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, **_kwargs):
                return FakeCursor()

        loaded = conversations_store.load_messages_from_db(
            '11111111-1111-4111-8111-111111111111',
            normalize_conversation_id_func=lambda raw: str(raw) if raw else None,
            db_conn_func=lambda: FakeConn(),
            ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                raw,
                now_iso_func=lambda: self.fail('persisted timestamp must not use now'),
            ),
            logger=type('Logger', (), {'warning': lambda *_args, **_kwargs: None})(),
        )

        self.assertEqual(loaded[0]['content'], '...')
        self.assertEqual(loaded[0]['timestamp'], '2026-07-23T09:00:01Z')
        self.assertEqual(loaded[0]['meta'], marker)
        self.assertTrue(assistant_turn_state.is_dialogic_presence_assistant_turn(loaded[0]))
        self.assertFalse(
            assistant_turn_state.is_dialogic_presence_assistant_turn(
                {'role': 'user', 'content': '...', 'meta': marker}
            )
        )

    def test_load_json_conversation_file_logs_read_error_without_raw_exception(self) -> None:
        raw_error = 'ARTIFICIAL_CONVERSATION_SECRET from corrupt json'
        admin_events = []
        logger_events = []

        class Logger:
            def error(self, *args, **_kwargs):
                logger_events.append(args)

        def fake_open(*_args, **_kwargs):
            raise RuntimeError(raw_error)

        class FakePath:
            def open(self, *_args, **_kwargs):
                return fake_open()

            def exists(self):
                return False

            def __str__(self):
                return '/tmp/synthetic-conversation.json'

        result = conversations_store.load_json_conversation_file(
            FakePath(),
            'conv-corrupt',
            'SYSTEM',
            backup_on_error=False,
            now_compact_func=lambda: '20260625T000000Z',
            normalize_conversation_func=lambda *_args: self.fail('normalize must not run after read error'),
            logger=Logger(),
            admin_log_event_func=lambda event, **kwargs: admin_events.append((event, kwargs)),
        )

        self.assertIsNone(result)
        self.assertEqual(admin_events[0][0], 'conv_read_error')
        payload = admin_events[0][1]
        self.assertEqual(payload['error_code'], 'conversation_json_read_error')
        self.assertEqual(payload['reason_code'], 'conversation_json_read_error')
        self.assertEqual(payload['error_class'], 'RuntimeError')
        self.assertFalse(payload['raw_error_message_included'])
        self.assertNotIn('error', payload)
        self.assertNotIn(raw_error, str(payload))
        self.assertNotIn(raw_error, str(logger_events))

    def test_ts_to_iso_rejects_invalid_timestamp_without_calling_now(self) -> None:
        with self.assertRaisesRegex(conversations_store.InvalidTimestampError, 'invalid_timestamp'):
            conversations_store.ts_to_iso(
                'not-a-date',
                now_iso_func=lambda: self.fail('invalid timestamp must not fall back to now'),
            )

    def test_parse_iso_to_dt_rejects_invalid_timestamp_without_now(self) -> None:
        with self.assertRaisesRegex(conversations_store.InvalidTimestampError, 'invalid_timestamp'):
            conversations_store.parse_iso_to_dt('still-not-a-date')

    def test_normalize_messages_for_storage_rejects_invalid_timestamp(self) -> None:
        with self.assertRaisesRegex(conversations_store.InvalidTimestampError, 'invalid_timestamp'):
            conversations_store.normalize_messages_for_storage(
                [{'role': 'user', 'content': 'bonjour', 'timestamp': 'bad-date'}],
                ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                    raw,
                    now_iso_func=lambda: self.fail('invalid message timestamp must not become now'),
                ),
                coerce_bool_func=conversations_store.coerce_bool,
            )

    def _save(self, *, catalog_result, messages_result):
        conversation = {
            'id': 'conv-save-result',
            'created_at': '2026-05-03T00:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'bonjour', 'timestamp': '2026-05-03T00:00:01Z'},
                {'role': 'assistant', 'content': 'salut', 'timestamp': '2026-05-03T00:00:02Z'},
            ],
        }
        logs = []

        logger = type(
            'Logger',
            (),
            {
                'info': lambda _self, *args, **_kwargs: logs.append(('info', args)),
                'warning': lambda _self, *args, **_kwargs: logs.append(('warning', args)),
            },
        )()

        result = conversations_store.save_conversation(
            conversation,
            updated_at='2026-05-03T00:00:03Z',
            preserve_deleted=False,
            now_iso_func=lambda: '2026-05-03T00:00:04Z',
            normalize_messages_for_storage_func=lambda messages: list(messages),
            logger=logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
            upsert_conversation_catalog_func=lambda *_args, **_kwargs: catalog_result,
            upsert_conversation_messages_func=lambda *_args, **_kwargs: messages_result,
        )
        return result, conversation, logs

    def _save_atomic_snapshot(
        self,
        database: TransactionalConversationDb,
        messages: list[dict],
        *,
        updated_at: str,
    ):
        conversation = {
            'id': '11111111-1111-4111-8111-111111111111',
            'title': 'Conversation concurrente',
            'created_at': '2026-09-04T10:00:00Z',
            'updated_at': updated_at,
            'messages': copy.deepcopy(messages),
        }
        logger = type(
            'Logger',
            (),
            {
                'info': lambda *_args, **_kwargs: None,
                'warning': lambda *_args, **_kwargs: None,
            },
        )()

        def normalize_messages(raw_messages):
            return conversations_store.normalize_messages_for_storage(
                raw_messages,
                ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                    raw,
                    now_iso_func=lambda: self.fail('valid timestamps must not use now'),
                ),
                coerce_bool_func=conversations_store.coerce_bool,
            )

        def metadata(item):
            return conversations_store.conversation_metadata(
                item,
                safe_title_func=conversations_store.safe_title,
                ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                    raw,
                    now_iso_func=lambda: self.fail('valid timestamps must not use now'),
                ),
                now_iso_func=lambda: self.fail('complete conversation metadata must not use now'),
                default_title='Nouvelle conversation',
                infer_title_from_messages_func=lambda items: conversations_store.infer_title_from_messages(
                    items,
                    collapse_ws_func=conversations_store.collapse_ws,
                    safe_title_func=conversations_store.safe_title,
                ),
                last_message_preview_func=lambda items: conversations_store.last_message_preview(
                    items,
                    collapse_ws_func=conversations_store.collapse_ws,
                ),
            )

        def atomic_save(item, preserve_deleted):
            return conversations_store.save_conversation_catalog_and_messages_atomic(
                item,
                preserve_deleted=preserve_deleted,
                conversation_metadata_func=metadata,
                normalize_conversation_id_func=conversations_store.normalize_conversation_id,
                normalize_messages_for_storage_func=normalize_messages,
                db_conn_func=database.connect,
                parse_iso_to_dt_func=conversations_store.parse_iso_to_dt,
                logger=logger,
            )

        result = conversations_store.save_conversation(
            conversation,
            updated_at=updated_at,
            preserve_deleted=True,
            now_iso_func=lambda: self.fail('explicit updated_at must not use now'),
            normalize_messages_for_storage_func=normalize_messages,
            logger=logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
            upsert_conversation_catalog_func=lambda *_args, **_kwargs: self.fail('legacy catalog path used'),
            upsert_conversation_messages_func=lambda *_args, **_kwargs: self.fail('legacy messages path used'),
            atomic_save_func=atomic_save,
        )
        return result, conversation

    def _initial_transactional_database(self, messages: list[dict]) -> TransactionalConversationDb:
        return TransactionalConversationDb(
            catalog={
                'id': '11111111-1111-4111-8111-111111111111',
                'title': 'Conversation concurrente',
                'created_at': datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
                'updated_at': datetime(2026, 9, 4, 10, 2, tzinfo=timezone.utc),
                'message_count': 2,
                'last_message_preview': 'réponse commune',
                'workspace_folder_id': '22222222-2222-4222-8222-222222222222',
                'deleted_at': None,
            },
            messages=[
                {
                    'role': message['role'],
                    'content': message['content'],
                    'timestamp': conversations_store.parse_iso_to_dt(message['timestamp']),
                    'summarized_by': message.get('summarized_by'),
                    'embedded': bool(message.get('embedded')),
                    'meta': copy.deepcopy(message.get('meta')),
                }
                for message in messages
            ],
        )

    def test_atomic_save_rejects_stale_prefix_without_removing_committed_suffix(self) -> None:
        common = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T10:00:00Z'},
            {
                'role': 'user',
                'content': 'question commune',
                'timestamp': '2026-09-04T10:01:00Z',
                'meta': {'input_mode': 'voice'},
            },
            {
                'role': 'assistant',
                'content': 'réponse commune',
                'timestamp': '2026-09-04T10:02:00Z',
                'summarized_by': 'summary-common',
                'embedded': True,
                'meta': {'assistant_runtime_provenance': {'origin': 'main_model'}},
            },
        ]
        committed_turn = [
            {
                'role': 'user',
                'content': 'tour A',
                'timestamp': '2026-09-04T10:03:00Z',
                'meta': {'affective_turn_signal': {'movement': 'steady'}},
            },
            {
                'role': 'assistant',
                'content': 'réponse A',
                'timestamp': '2026-09-04T10:04:00Z',
                'embedded': True,
                'meta': {'source': 'synthetic-test'},
            },
        ]
        database = self._initial_transactional_database(common)

        first, _conversation = self._save_atomic_snapshot(
            database,
            common + committed_turn,
            updated_at='2026-09-04T10:04:00Z',
        )
        stale, _conversation = self._save_atomic_snapshot(
            database,
            common,
            updated_at='2026-09-04T10:05:00Z',
        )

        self.assertTrue(first.ok)
        self.assertFalse(stale.ok)
        self.assertEqual(stale.reason, 'conversation_snapshot_conflict')
        self.assertFalse(stale.catalog_saved)
        self.assertFalse(stale.messages_saved)
        self.assertEqual(
            [(row['role'], row['content']) for row in database.messages],
            [(message['role'], message['content']) for message in common + committed_turn],
        )
        self.assertEqual(
            [row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ') for row in database.messages],
            [message['timestamp'] for message in common + committed_turn],
        )
        self.assertEqual(database.messages[2]['summarized_by'], 'summary-common')
        self.assertTrue(database.messages[2]['embedded'])
        self.assertEqual(database.messages[3]['meta'], committed_turn[0]['meta'])
        self.assertEqual(database.messages[4]['meta'], committed_turn[1]['meta'])
        self.assertTrue(
            any(
                statement.startswith('SELECT role, content, timestamp, summarized_by, embedded, meta')
                and statement.endswith('FOR UPDATE')
                for statement in database.statements
            )
        )

    def test_atomic_save_rejects_same_length_divergent_snapshot_without_touching_canon(self) -> None:
        common = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T11:00:00Z'},
            {'role': 'user', 'content': 'préfixe', 'timestamp': '2026-09-04T11:01:00Z'},
        ]
        branch_a = common + [
            {'role': 'assistant', 'content': 'branche A', 'timestamp': '2026-09-04T11:02:00Z'}
        ]
        branch_b = common + [
            {'role': 'assistant', 'content': 'branche B', 'timestamp': '2026-09-04T11:02:30Z'}
        ]
        database = self._initial_transactional_database(common)

        first, _conversation = self._save_atomic_snapshot(
            database,
            branch_a,
            updated_at='2026-09-04T11:02:00Z',
        )
        divergent, _conversation = self._save_atomic_snapshot(
            database,
            branch_b,
            updated_at='2026-09-04T11:03:00Z',
        )

        self.assertTrue(first.ok)
        self.assertFalse(divergent.ok)
        self.assertEqual(divergent.reason, 'conversation_snapshot_conflict')
        self.assertEqual([row['content'] for row in database.messages], ['SYSTEM', 'préfixe', 'branche A'])
        self.assertEqual(database.catalog['updated_at'], conversations_store.parse_iso_to_dt('2026-09-04T11:02:00Z'))

    def test_atomic_save_preserves_canonical_metadata_missing_from_same_snapshot(self) -> None:
        canonical = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T12:00:00Z'},
            {
                'role': 'user',
                'content': 'message stable',
                'timestamp': '2026-09-04T12:01:00Z',
                'summarized_by': 'summary-stable',
                'embedded': True,
                'meta': {
                    'input_mode': 'voice',
                    'affective_turn_signal': {'movement': 'steady'},
                },
            },
        ]
        stale_metadata = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T12:00:00Z'},
            {
                'role': 'user',
                'content': 'message stable',
                'timestamp': '2026-09-04T12:01:00Z',
                'meta': {'input_mode': 'voice'},
            },
        ]
        database = self._initial_transactional_database(canonical)

        result, _conversation = self._save_atomic_snapshot(
            database,
            stale_metadata,
            updated_at='2026-09-04T12:02:00Z',
        )

        self.assertTrue(result.ok)
        self.assertEqual(database.messages[1]['summarized_by'], 'summary-stable')
        self.assertTrue(database.messages[1]['embedded'])
        self.assertEqual(database.messages[1]['meta'], canonical[1]['meta'])

    def test_atomic_save_accepts_monotonic_metadata_updates(self) -> None:
        canonical = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T12:10:00Z'},
            {
                'role': 'assistant',
                'content': 'message stable',
                'timestamp': '2026-09-04T12:11:00Z',
                'meta': {'assistant_runtime_provenance': {'origin': 'main_model'}},
            },
        ]
        enriched = copy.deepcopy(canonical)
        enriched[1]['summarized_by'] = 'summary-new'
        enriched[1]['embedded'] = True
        enriched[1]['meta']['assistant_runtime_provenance']['final_lock'] = True
        database = self._initial_transactional_database(canonical)

        result, _conversation = self._save_atomic_snapshot(
            database,
            enriched,
            updated_at='2026-09-04T12:12:00Z',
        )

        self.assertTrue(result.ok)
        self.assertEqual(database.messages[1]['summarized_by'], 'summary-new')
        self.assertTrue(database.messages[1]['embedded'])
        self.assertEqual(database.messages[1]['meta'], enriched[1]['meta'])

    def test_atomic_save_rejects_conflicting_metadata_without_touching_canon(self) -> None:
        canonical = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T12:20:00Z'},
            {
                'role': 'assistant',
                'content': 'message stable',
                'timestamp': '2026-09-04T12:21:00Z',
                'meta': {'assistant_runtime_provenance': {'origin': 'main_model'}},
            },
        ]
        conflicting = copy.deepcopy(canonical)
        conflicting[1]['meta']['assistant_runtime_provenance']['origin'] = 'other_model'
        database = self._initial_transactional_database(canonical)
        before_catalog = copy.deepcopy(database.catalog)
        before_messages = copy.deepcopy(database.messages)

        result, _conversation = self._save_atomic_snapshot(
            database,
            conflicting,
            updated_at='2026-09-04T12:22:00Z',
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, 'conversation_snapshot_conflict')
        self.assertEqual(database.catalog, before_catalog)
        self.assertEqual(database.messages, before_messages)

    def test_rename_conversation_updates_only_catalog_title(self) -> None:
        messages = [
            {'role': 'system', 'content': 'SYSTEM', 'timestamp': '2026-09-04T12:30:00Z'},
            {'role': 'user', 'content': 'dialogue intact', 'timestamp': '2026-09-04T12:31:00Z'},
        ]
        database = self._initial_transactional_database(messages)
        database.catalog['deleted_at'] = datetime(2026, 9, 4, 12, 45, tzinfo=timezone.utc)
        before_messages = copy.deepcopy(database.messages)
        before_folder = database.catalog['workspace_folder_id']
        before_created_at = database.catalog['created_at']

        renamed = conversations_store.rename_conversation(
            '11111111-1111-4111-8111-111111111111',
            '  Titre ciblé  ',
            normalize_conversation_id_func=conversations_store.normalize_conversation_id,
            safe_title_func=conversations_store.safe_title,
            get_conversation_summary_func=lambda *_args, **_kwargs: self.fail('rename must not load summary'),
            read_conversation_func=lambda *_args, **_kwargs: self.fail('rename must not load messages'),
            save_conversation_func=lambda *_args, **_kwargs: self.fail('rename must not save messages'),
            now_iso_func=lambda: self.fail('targeted SQL owns updated_at'),
            db_conn_func=database.connect,
            serialize_catalog_row_func=lambda row: row,
            logger=type('Logger', (), {'warning': lambda *_args, **_kwargs: None})(),
        )

        self.assertEqual(renamed['title'], 'Titre ciblé')
        self.assertEqual(database.messages, before_messages)
        self.assertEqual(database.catalog['workspace_folder_id'], before_folder)
        self.assertEqual(database.catalog['created_at'], before_created_at)
        self.assertEqual(
            database.catalog['deleted_at'],
            datetime(2026, 9, 4, 12, 45, tzinfo=timezone.utc),
        )
        self.assertEqual(len(database.statements), 1)
        self.assertTrue(database.statements[0].startswith('UPDATE conversations SET title'))
        self.assertFalse(any('conversation_messages' in statement for statement in database.statements))

    def test_save_conversation_reports_catalog_failure_without_silent_success(self) -> None:
        result, conversation, logs = self._save(catalog_result=None, messages_result=True)

        self.assertFalse(result.ok)
        self.assertFalse(result.catalog_saved)
        self.assertTrue(result.messages_saved)
        self.assertEqual(result.reason, 'catalog_write_failed')
        self.assertEqual(result.updated_at, '2026-05-03T00:00:03Z')
        self.assertEqual(result.message_count, 2)
        self.assertEqual(conversation['updated_at'], '2026-05-03T00:00:03Z')
        self.assertTrue(any('conv_catalog_write_failed' in args[0] for level, args in logs if level == 'warning'))

    def test_save_conversation_reports_messages_failure_without_silent_success(self) -> None:
        result, _conversation, logs = self._save(catalog_result={'id': 'conv-save-result'}, messages_result=False)

        self.assertFalse(result.ok)
        self.assertTrue(result.catalog_saved)
        self.assertFalse(result.messages_saved)
        self.assertEqual(result.reason, 'messages_write_failed')
        self.assertEqual(result.message_count, 2)
        self.assertTrue(any('conv_messages_write_failed' in args[0] for level, args in logs if level == 'warning'))

    def test_atomic_save_rolls_back_catalog_when_message_write_fails(self) -> None:
        conversation_id = '11111111-1111-4111-8111-111111111111'
        conversation = {
            'id': conversation_id,
            'created_at': '2026-05-03T00:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'bonjour', 'timestamp': '2026-05-03T00:00:01Z'},
                {'role': 'assistant', 'content': 'salut', 'timestamp': '2026-05-03T00:00:02Z'},
            ],
        }
        committed = {'catalog': [], 'messages': []}
        pending = {'catalog': [], 'messages': []}
        logs = []

        class FakeCursor:
            def __init__(self):
                self.row = None
                self.rows = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params):
                compact_sql = ' '.join(sql.split())
                if compact_sql.startswith('INSERT INTO conversations'):
                    pending['catalog'] = [
                        {
                            'id': params[0],
                            'message_count': params[4],
                            'last_message_preview': params[5],
                        }
                    ]
                    self.row = {'id': params[0]}
                elif compact_sql.startswith('SELECT role, content, timestamp, summarized_by, embedded, meta'):
                    self.rows = []
                elif compact_sql.startswith('DELETE FROM conversation_messages'):
                    pending['messages'] = []

            def executemany(self, _sql, _rows):
                raise RuntimeError('message write exploded')

            def fetchone(self):
                return self.row

            def fetchall(self):
                return list(self.rows)

        class FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is not None:
                    self.rollback()
                return False

            def cursor(self, *args, **kwargs):
                return FakeCursor()

            def commit(self):
                committed['catalog'] = list(pending['catalog'])
                committed['messages'] = list(pending['messages'])

            def rollback(self):
                pending['catalog'] = []
                pending['messages'] = []

        logger = type(
            'Logger',
            (),
            {
                'info': lambda _self, *args, **_kwargs: logs.append(('info', args)),
                'warning': lambda _self, *args, **_kwargs: logs.append(('warning', args)),
            },
        )()

        def atomic_save(conv, preserve_deleted):
            return conversations_store.save_conversation_catalog_and_messages_atomic(
                conv,
                preserve_deleted=preserve_deleted,
                conversation_metadata_func=lambda item: {
                    'id': item['id'],
                    'title': 'Conversation atomique',
                    'created_at': item['created_at'],
                    'updated_at': item['updated_at'],
                    'message_count': 2,
                    'last_message_preview': 'salut',
                },
                normalize_conversation_id_func=lambda raw: str(raw),
                normalize_messages_for_storage_func=lambda messages: list(messages),
                db_conn_func=lambda: FakeConn(),
                parse_iso_to_dt_func=lambda raw: raw,
                logger=logger,
            )

        result = conversations_store.save_conversation(
            conversation,
            updated_at='2026-05-03T00:00:03Z',
            preserve_deleted=False,
            now_iso_func=lambda: '2026-05-03T00:00:04Z',
            normalize_messages_for_storage_func=lambda messages: list(messages),
            logger=logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
            upsert_conversation_catalog_func=lambda *_args, **_kwargs: self.fail('legacy catalog path used'),
            upsert_conversation_messages_func=lambda *_args, **_kwargs: self.fail('legacy messages path used'),
            atomic_save_func=atomic_save,
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.catalog_saved)
        self.assertFalse(result.messages_saved)
        self.assertEqual(result.reason, 'messages_write_failed')
        self.assertEqual(committed['catalog'], [])
        self.assertEqual(committed['messages'], [])
        self.assertTrue(any('conv_save_atomic_failed' in args[0] for level, args in logs if level == 'warning'))

    def test_save_conversation_returns_ok_when_catalog_and_messages_are_saved(self) -> None:
        result, _conversation, _logs = self._save(catalog_result={'id': 'conv-save-result'}, messages_result=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.catalog_saved)
        self.assertTrue(result.messages_saved)
        self.assertIsNone(result.reason)
        self.assertEqual(result.message_count, 2)

    def test_summary_marks_survive_message_storage_rows_and_rehydration_in_order(self) -> None:
        conversation_id = '11111111-1111-4111-8111-111111111111'
        normalized = conversations_store.normalize_messages_for_storage(
            [
                {
                    'role': 'user',
                    'content': 'old user',
                    'timestamp': '2026-09-02T10:00:00Z',
                    'summarized_by': 'summary-durable',
                },
                {
                    'role': 'assistant',
                    'content': 'old assistant',
                    'timestamp': '2026-09-02T10:01:00Z',
                    'summarized_by': 'summary-durable',
                },
                {
                    'role': 'user',
                    'content': 'recent user',
                    'timestamp': '2026-09-02T10:02:00Z',
                },
                {
                    'role': 'assistant',
                    'content': 'recent assistant',
                    'timestamp': '2026-09-02T10:03:00Z',
                },
            ],
            ts_to_iso_func=lambda raw: str(raw),
            coerce_bool_func=conversations_store.coerce_bool,
        )
        stored_rows = conversations_store.conversation_message_insert_rows(
            conversation_id,
            normalized,
            parse_iso_to_dt_func=conversations_store.parse_iso_to_dt,
        )

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, _sql, _params):
                return None

            def fetchall(self):
                return [
                    {
                        'role': row[2],
                        'content': row[3],
                        'timestamp': row[4],
                        'summarized_by': row[5],
                        'embedded': row[6],
                        'meta': None,
                    }
                    for row in stored_rows
                ]

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, **_kwargs):
                return Cursor()

        rehydrated = conversations_store.load_messages_from_db(
            conversation_id,
            normalize_conversation_id_func=lambda raw: str(raw) if raw else None,
            db_conn_func=lambda: Connection(),
            ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                raw,
                now_iso_func=lambda: self.fail('stored timestamps must stay authoritative'),
            ),
            logger=type('Logger', (), {'warning': lambda *_args, **_kwargs: None})(),
        )

        self.assertEqual([message['content'] for message in rehydrated], [
            'old user',
            'old assistant',
            'recent user',
            'recent assistant',
        ])
        self.assertEqual(rehydrated[0]['summarized_by'], 'summary-durable')
        self.assertEqual(rehydrated[1]['summarized_by'], 'summary-durable')
        self.assertNotIn('summarized_by', rehydrated[2])
        self.assertNotIn('summarized_by', rehydrated[3])


if __name__ == "__main__":
    unittest.main()
