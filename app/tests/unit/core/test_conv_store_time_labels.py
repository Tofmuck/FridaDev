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

    def test_delta_t_label_core_absolute_and_relative_forms(self) -> None:
        now_iso = "2026-03-28T12:00:00Z"

        self.assertEqual(
            conv_store.delta_t_label("2026-03-28T11:59:30Z", now_iso),
            "samedi 28 mars 2026 à 12h59 Europe/Paris — à l'instant",
        )
        self.assertEqual(
            conv_store.delta_t_label("2026-03-28T11:58:00Z", now_iso),
            "samedi 28 mars 2026 à 12h58 Europe/Paris — il y a 2 minutes",
        )
        self.assertEqual(
            conv_store.delta_t_label("2026-03-28T08:00:00Z", now_iso),
            "samedi 28 mars 2026 à 9h Europe/Paris — aujourd'hui",
        )
        self.assertEqual(
            conv_store.delta_t_label("2026-03-27T20:30:00Z", now_iso),
            "vendredi 27 mars 2026 à 21h30 Europe/Paris — hier",
        )

    def test_delta_t_label_distinguishes_today_and_yesterday_same_clock_time(self) -> None:
        now_iso = "2026-05-18T20:00:00Z"

        today_label = conv_store.delta_t_label("2026-05-18T17:27:00Z", now_iso)
        yesterday_label = conv_store.delta_t_label("2026-05-17T17:27:00Z", now_iso)

        self.assertEqual(today_label, "lundi 18 mai 2026 à 19h27 Europe/Paris — aujourd'hui")
        self.assertEqual(yesterday_label, "dimanche 17 mai 2026 à 19h27 Europe/Paris — hier")
        self.assertIn("19h27 Europe/Paris", today_label)
        self.assertIn("19h27 Europe/Paris", yesterday_label)

    def test_delta_t_label_keeps_absolute_date_across_midnight(self) -> None:
        now_iso = "2026-05-17T22:05:00Z"

        today_label = conv_store.delta_t_label("2026-05-17T22:02:00Z", now_iso)
        yesterday_label = conv_store.delta_t_label("2026-05-17T21:57:00Z", now_iso)

        self.assertEqual(today_label, "lundi 18 mai 2026 à 0h02 Europe/Paris — il y a 3 minutes")
        self.assertEqual(yesterday_label, "dimanche 17 mai 2026 à 23h57 Europe/Paris — il y a 8 minutes")

    def test_delta_t_label_days_and_weeks_forms(self) -> None:
        now_iso = "2026-03-28T12:00:00Z"

        self.assertEqual(
            conv_store.delta_t_label("2026-03-25T12:00:00Z", now_iso),
            "mercredi 25 mars 2026 à 13h Europe/Paris — il y a 3 jours",
        )
        self.assertEqual(
            conv_store.delta_t_label("2026-03-14T12:00:00Z", now_iso),
            "samedi 14 mars 2026 à 13h Europe/Paris — il y a 2 semaines",
        )

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
        self.assertTrue(
            user_messages[0]["content"].startswith(
                "[samedi 28 mars 2026 à 12h59 Europe/Paris — à l'instant] "
            )
        )
        self.assertTrue(
            assistant_messages[0]["content"].startswith(
                "[samedi 28 mars 2026 à 12h59 Europe/Paris — à l'instant] "
            )
        )

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
                {
                    "role": "user",
                    "content": "[samedi 28 mars 2026 à 12h59 Europe/Paris — à l'instant] Salut",
                },
            ],
        )

    def test_build_prompt_messages_keeps_recent_dialogue_when_prefix_exceeds_soft_limit(self) -> None:
        conversation = {
            "id": "conv-large-prefix",
            "messages": [
                {"role": "system", "content": "SYSTEM " * 5000, "timestamp": "2026-03-28T10:00:00Z"},
                {"role": "user", "content": "Premier message recent", "timestamp": "2026-03-28T11:55:00Z"},
                {"role": "assistant", "content": "Premiere reponse recente", "timestamp": "2026-03-28T11:56:00Z"},
                {"role": "user", "content": "Deuxieme message recent", "timestamp": "2026-03-28T11:57:00Z"},
            ],
        }
        observed_logs: list[tuple[str, dict[str, object]]] = []

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=999),
            mock.patch.object(conv_store.config, "MAX_TOKENS", 10),
            mock.patch.object(
                conv_store.admin_logs,
                "log_event",
                side_effect=lambda event, **fields: observed_logs.append((event, dict(fields))),
            ),
        ):
            result = conv_store.build_prompt_messages(
                conversation,
                model="fake-model",
                now="2026-03-28T12:00:00Z",
                memory_traces=None,
                context_hints=None,
            )

        dialogue_contents = [
            msg["content"]
            for msg in result
            if msg.get("role") in {"user", "assistant"}
        ]
        self.assertEqual(len(dialogue_contents), 3)
        self.assertTrue(any("Premier message recent" in content for content in dialogue_contents))
        self.assertTrue(any("Premiere reponse recente" in content for content in dialogue_contents))
        self.assertTrue(any("Deuxieme message recent" in content for content in dialogue_contents))

        token_window_payload = next(fields for event, fields in observed_logs if event == "token_window")
        self.assertEqual(token_window_payload["dialogue_candidate_message_count"], 3)
        self.assertEqual(token_window_payload["selected_dialogue_message_count"], 3)
        self.assertFalse(token_window_payload["dialogue_messages_truncated"])
        self.assertEqual(token_window_payload["selection_policy"], "all_dialogue_after_active_summary")
        self.assertTrue(token_window_payload["prompt_soft_limit_exceeded"])

    def test_build_prompt_messages_keeps_all_messages_after_active_summary_cutoff(self) -> None:
        conversation = {
            "id": "conv-active-summary",
            "messages": [
                {"role": "system", "content": "SYSTEM " * 5000, "timestamp": "2026-03-28T10:00:00Z"},
                {"role": "user", "content": "Ancien message resume", "timestamp": "2026-03-28T10:10:00Z"},
                {"role": "assistant", "content": "Ancienne reponse resumee", "timestamp": "2026-03-28T10:11:00Z"},
                {"role": "user", "content": "Message recent conserve", "timestamp": "2026-03-28T11:55:00Z"},
                {"role": "assistant", "content": "Reponse recente conservee", "timestamp": "2026-03-28T11:56:00Z"},
            ],
        }
        active_summary = {
            "id": "summary-1",
            "start_ts": "2026-03-28T10:00:00Z",
            "end_ts": "2026-03-28T10:30:00Z",
            "content": "Les anciens messages ont ete resumes.",
        }
        observed_logs: list[tuple[str, dict[str, object]]] = []

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=active_summary),
            mock.patch.object(conv_store, "count_tokens", return_value=999),
            mock.patch.object(conv_store.config, "MAX_TOKENS", 10),
            mock.patch.object(
                conv_store.admin_logs,
                "log_event",
                side_effect=lambda event, **fields: observed_logs.append((event, dict(fields))),
            ),
        ):
            result = conv_store.build_prompt_messages(
                conversation,
                model="fake-model",
                now="2026-03-28T12:00:00Z",
                memory_traces=None,
                context_hints=None,
            )

        contents = [msg["content"] for msg in result]
        self.assertTrue(any(content.startswith("[Résumé") for content in contents))
        self.assertFalse(any("Ancien message resume" in content for content in contents))
        self.assertFalse(any("Ancienne reponse resumee" in content for content in contents))
        self.assertTrue(any("Message recent conserve" in content for content in contents))
        self.assertTrue(any("Reponse recente conservee" in content for content in contents))

        token_window_payload = next(fields for event, fields in observed_logs if event == "token_window")
        self.assertTrue(token_window_payload["active_summary_present"])
        self.assertEqual(token_window_payload["dialogue_candidate_message_count"], 2)
        self.assertEqual(token_window_payload["selected_dialogue_message_count"], 2)
        self.assertFalse(token_window_payload["dialogue_messages_truncated"])


if __name__ == "__main__":
    unittest.main()
