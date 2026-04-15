from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store


class ConvStoreTimeLabelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._timezone_patcher = mock.patch.object(conv_store.config, "FRIDA_TIMEZONE", "Europe/Paris")
        self._timezone_patcher.start()

    def tearDown(self) -> None:
        self._timezone_patcher.stop()

    def test_delta_t_label_core_relative_forms(self) -> None:
        now_iso = "2026-03-28T12:00:00Z"

        self.assertEqual(conv_store.delta_t_label("2026-03-28T11:59:30Z", now_iso), "à l'instant")
        self.assertEqual(conv_store.delta_t_label("2026-03-28T11:58:00Z", now_iso), "il y a 2 minutes")
        self.assertEqual(conv_store.delta_t_label("2026-03-28T08:00:00Z", now_iso), "aujourd'hui à 9h")
        self.assertEqual(conv_store.delta_t_label("2026-03-27T20:30:00Z", now_iso), "hier à 21h30")

    def test_delta_t_label_days_and_weeks_forms(self) -> None:
        now_iso = "2026-03-28T12:00:00Z"

        self.assertEqual(conv_store.delta_t_label("2026-03-25T12:00:00Z", now_iso), "il y a 3 jours")
        self.assertEqual(conv_store.delta_t_label("2026-03-14T12:00:00Z", now_iso), "il y a 2 semaines")

    def test_silence_label_core_forms(self) -> None:
        self.assertEqual(
            conv_store._silence_label("2026-03-28T12:00:00Z", "2026-03-28T12:00:20Z"),
            "[— silence de quelques secondes —]",
        )
        self.assertEqual(
            conv_store._silence_label("2026-03-28T12:00:00Z", "2026-03-28T12:05:00Z"),
            "[— silence de 5 minutes —]",
        )
        self.assertEqual(
            conv_store._silence_label("2026-03-28T12:00:00Z", "2026-03-28T15:00:00Z"),
            "[— silence de 3 heures —]",
        )
        self.assertEqual(
            conv_store._silence_label("2026-03-27T12:00:00Z", "2026-03-28T12:00:00Z"),
            "[— silence d'un jour —]",
        )
        self.assertEqual(
            conv_store._silence_label("2026-03-25T12:00:00Z", "2026-03-28T12:00:00Z"),
            "[— silence de 3 jours —]",
        )

    def test_build_prompt_messages_injects_delta_and_silence_markers(self) -> None:
        conversation = {
            "id": "conv-time-labels",
            "messages": [
                {"role": "system", "content": "SYSTEM", "timestamp": "2026-03-28T11:00:00Z"},
                {"role": "user", "content": "Salut", "timestamp": "2026-03-28T11:59:30Z"},
                {"role": "assistant", "content": "Bonjour", "timestamp": "2026-03-28T11:59:40Z"},
            ],
        }

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=1),
            mock.patch.object(conv_store.admin_logs, "log_event", return_value=None),
        ):
            result = conv_store.build_prompt_messages(
                conversation,
                model="fake-model",
                now="2026-03-28T12:00:00Z",
                memory_traces=None,
                context_hints=None,
            )

        contents = [msg.get("content", "") for msg in result]
        self.assertIn("[— silence de quelques secondes —]", contents)

        user_messages = [msg for msg in result if msg.get("role") == "user"]
        assistant_messages = [msg for msg in result if msg.get("role") == "assistant"]
        self.assertTrue(user_messages)
        self.assertTrue(assistant_messages)
        self.assertTrue(user_messages[0]["content"].startswith("[à l'instant] "))
        self.assertTrue(assistant_messages[0]["content"].startswith("[à l'instant] "))

        silence_idx = contents.index("[— silence de quelques secondes —]")
        assistant_idx = next(i for i, msg in enumerate(result) if msg.get("role") == "assistant")
        self.assertLess(silence_idx, assistant_idx)

    def test_build_prompt_messages_skips_persisted_interrupted_assistant_markers(self) -> None:
        conversation = {
            "id": "conv-interrupted-marker",
            "messages": [
                {"role": "system", "content": "SYSTEM", "timestamp": "2026-03-28T11:00:00Z"},
                {"role": "user", "content": "Salut", "timestamp": "2026-03-28T11:59:30Z"},
                {
                    "role": "assistant",
                    "content": "",
                    "timestamp": "2026-03-28T11:59:40Z",
                    "meta": {
                        "assistant_turn": {
                            "status": "interrupted",
                            "error_code": "upstream_error",
                        }
                    },
                },
            ],
        }

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=1),
            mock.patch.object(conv_store.admin_logs, "log_event", return_value=None),
        ):
            result = conv_store.build_prompt_messages(
                conversation,
                model="fake-model",
                now="2026-03-28T12:00:00Z",
                memory_traces=None,
                context_hints=None,
            )

        self.assertEqual(
            result,
            [
                {"role": "system", "content": "SYSTEM"},
                {"role": "user", "content": "[à l'instant] Salut"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
