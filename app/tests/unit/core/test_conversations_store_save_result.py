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

    def test_save_conversation_returns_ok_when_catalog_and_messages_are_saved(self) -> None:
        result, _conversation, _logs = self._save(catalog_result={'id': 'conv-save-result'}, messages_result=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.catalog_saved)
        self.assertTrue(result.messages_saved)
        self.assertIsNone(result.reason)
        self.assertEqual(result.message_count, 2)


if __name__ == "__main__":
    unittest.main()
