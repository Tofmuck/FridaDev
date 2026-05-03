from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conversations_store


class ConversationsStoreSaveResultTests(unittest.TestCase):
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
                elif compact_sql.startswith('DELETE FROM conversation_messages'):
                    pending['messages'] = []

            def executemany(self, _sql, _rows):
                raise RuntimeError('message write exploded')

            def fetchone(self):
                return self.row

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


if __name__ == "__main__":
    unittest.main()
