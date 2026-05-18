from __future__ import annotations

import json
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

import config
from core import conversations_prompt_window
from core import conversations_store
from core.hermeneutic_node.inputs import time_input
from core.hermeneutic_node.inputs import user_turn_input
from core.hermeneutic_node.validation import validation_agent
from memory import arbiter
from memory import identity_temporal_guard
from tools import web_search
from core import stimmung_agent


TZ = "Europe/Paris"


class _NoopLogger:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None


class TemporalModelTruthClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self._timezone_patch = mock.patch.object(config, "FRIDA_TIMEZONE", TZ)
        self._timezone_patch.start()

    def tearDown(self) -> None:
        self._timezone_patch.stop()

    def _delta_label(self, ts_msg: str, ts_now: str) -> str:
        return time_input.render_delta_label(ts_msg, ts_now, timezone_name=TZ)

    def _web_runtime_patch(self):
        return mock.patch.object(
            web_search,
            "_runtime_services_value",
            side_effect=lambda field: {
                "searxng_results": 5,
                "crawl4ai_top_n": 0,
                "crawl4ai_max_chars": 400,
                "crawl4ai_explicit_url_max_chars": 400,
            }[field],
        )

    def _prompt_window_text(self, *, now_iso: str, message_ts: str) -> str:
        summary = {
            "id": "summary-closure",
            "start_ts": message_ts,
            "end_ts": message_ts,
            "content": "Résumé de clôture temporelle.",
        }
        conversation = {
            "id": "conv-temporal-closure",
            "messages": [
                {"role": "system", "content": "SYSTEM"},
                {"role": "user", "content": "Message courant de clôture.", "timestamp": message_ts},
            ],
        }

        result = conversations_prompt_window.build_prompt_messages(
            conversation,
            "test-model",
            now=now_iso,
            memory_traces=[
                {
                    "candidate_id": "trace-now",
                    "role": "user",
                    "content": "Souvenir de clôture.",
                    "timestamp": message_ts,
                    "parent_summary": summary,
                }
            ],
            context_hints=[
                {
                    "content": "Indice contextuel de clôture.",
                    "timestamp": message_ts,
                    "confidence": 0.9,
                }
            ],
            ensure_system_message_func=lambda messages: messages[0],
            get_active_summary_func=lambda _conversation_id: summary,
            summary_cutoff_iso_func=lambda _summary: None,
            message_is_after_summary_func=lambda _msg, _cutoff: True,
            make_summary_message_func=lambda item: conversations_prompt_window.make_summary_message(
                item,
                timezone_name=TZ,
            ),
            make_context_hints_message_func=lambda hints, ts_now, model: conversations_prompt_window.make_context_hints_message(
                hints,
                ts_now,
                model,
                delta_t_label_func=self._delta_label,
                count_tokens_func=lambda _messages, _model: 1,
                context_hints_max_tokens=1000,
                context_hints_max_items=5,
            ),
            make_memory_context_message_func=lambda summaries: conversations_prompt_window.make_memory_context_message(
                summaries,
                timezone_name=TZ,
            ),
            make_memory_message_func=lambda traces, ts_now: conversations_prompt_window.make_memory_message(
                traces,
                ts_now,
                delta_t_label_func=self._delta_label,
            ),
            count_tokens_func=lambda _messages, _model: 1,
            max_tokens=1000,
            now_iso_func=lambda: now_iso,
            logger=_NoopLogger(),
            admin_log_event_func=lambda *_args, **_kwargs: None,
            silence_label_func=conversations_prompt_window.silence_label,
            delta_t_label_func=self._delta_label,
        )
        return "\n".join(str(message.get("content") or "") for message in result)

    def _web_text(self, *, now_iso: str) -> str:
        with self._web_runtime_patch():
            search_material = web_search._build_search_context_material(
                "requete temporelle",
                [{"title": "A", "url": "https://a.example", "content": "snippet"}],
                now_iso=now_iso,
            )
            explicit_material = web_search._build_explicit_url_context_material(
                "https://a.example",
                "contenu lu",
                now_iso=now_iso,
            )
        reformulation_prompt = web_search.prompt_loader.get_web_reformulation_prompt().format(
            today=web_search._web_temporal_label(now_iso=now_iso)
        )
        return "\n".join(
            [
                reformulation_prompt,
                str(search_material["context_block"]),
                str(explicit_material["context_block"]),
            ]
        )

    def _validation_payload(self, *, now_iso: str, message_ts: str) -> tuple[dict, str]:
        canonical_time = time_input.build_time_input(now_utc_iso=now_iso, timezone_name=TZ)
        time_reference = validation_agent._validation_time_reference({"time_input": canonical_time})
        compacted = validation_agent._compacted_validation_dialogue_context(
            {
                "schema_version": "v1",
                "messages": [
                    {
                        "role": "user",
                        "content": "Message de validation.",
                        "timestamp": message_ts,
                    }
                ],
            },
            time_reference=time_reference,
        )
        messages = validation_agent._build_messages(
            system_prompt="SYSTEM",
            primary_verdict={"schema_version": "v1"},
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [
                    {
                        "role": "user",
                        "content": "Message de validation.",
                        "timestamp": message_ts,
                    }
                ],
            },
            canonical_inputs={"time_input": canonical_time},
            hard_guard_payload={},
        )
        return json.loads(compacted), messages[1]["content"]

    def _arbiter_payload(self, *, now_iso: str, message_ts: str) -> dict[str, str | dict]:
        return {
            "temporal_reference": arbiter._temporal_reference(now_iso),
            "recent_turn": arbiter._format_recent_turn_for_arbiter(
                {
                    "role": "user",
                    "content": "Message arbitre.",
                    "timestamp": message_ts,
                },
                now_iso=now_iso,
            ),
            "candidate_label": arbiter._temporal_label(message_ts, now_iso=now_iso),
        }

    def _semantic_lane_outputs(self, *, now_iso: str, message_ts: str) -> dict[str, str]:
        time_payload = time_input.build_time_input(now_utc_iso=now_iso, timezone_name=TZ)
        reference_block = time_input.build_time_reference_block(time_payload)
        prompt_text = self._prompt_window_text(now_iso=now_iso, message_ts=message_ts)
        web_text = self._web_text(now_iso=now_iso)
        validation_payload, validation_user_message = self._validation_payload(
            now_iso=now_iso,
            message_ts=message_ts,
        )
        arbiter_payload = self._arbiter_payload(now_iso=now_iso, message_ts=message_ts)
        summary_message = conversations_prompt_window.make_summary_message(
            {"start_ts": message_ts, "end_ts": message_ts, "content": "Résumé."},
            timezone_name=TZ,
        )
        memory_context_message = conversations_prompt_window.make_memory_context_message(
            [{"start_ts": message_ts, "end_ts": message_ts, "content": "Résumé parent.", "prompt_ref": "S1"}],
            timezone_name=TZ,
        )

        return {
            "reference_block": reference_block,
            "prompt_window": prompt_text,
            "web": web_text,
            "validation_time_reference": json.dumps(
                validation_payload["time_reference"],
                ensure_ascii=False,
                sort_keys=True,
            ),
            "validation_temporal_label": validation_payload["messages"][0]["temporal_label"],
            "validation_prompt_priority": validation_user_message,
            "arbiter_time_reference": json.dumps(
                arbiter_payload["temporal_reference"],
                ensure_ascii=False,
                sort_keys=True,
            ),
            "arbiter_recent_turn": str(arbiter_payload["recent_turn"]),
            "arbiter_candidate_label": str(arbiter_payload["candidate_label"]),
            "summary_header": summary_message["content"].splitlines()[0],
            "memory_context_header": str(memory_context_message["content"]).splitlines()[0],
        }

    def assert_lanes_share_local_day(
        self,
        *,
        now_iso: str,
        message_ts: str,
        expected_local_date: str,
        expected_human_day: str,
        forbidden_human_days: tuple[str, ...],
    ) -> None:
        outputs = self._semantic_lane_outputs(now_iso=now_iso, message_ts=message_ts)

        for lane_name, text in outputs.items():
            with self.subTest(lane=lane_name):
                self.assertTrue(
                    expected_local_date in text or expected_human_day in text,
                    msg=f"{lane_name} did not expose {expected_local_date} / {expected_human_day}: {text}",
                )
                for forbidden in forbidden_human_days:
                    self.assertNotIn(forbidden, text)

        validation_user_message = outputs["validation_prompt_priority"]
        self.assertLess(
            validation_user_message.index("temporal_reference"),
            validation_user_message.index("validation_dialogue_context"),
        )
        self.assertIn("temporal_label", validation_user_message)

    def test_midnight_matrix_all_model_lanes_share_frida_local_day(self) -> None:
        self.assert_lanes_share_local_day(
            now_iso="2026-05-17T22:05:00Z",
            message_ts="2026-05-17T22:05:00Z",
            expected_local_date="2026-05-18",
            expected_human_day="lundi 18 mai 2026",
            forbidden_human_days=("17 mai 2026", "dimanche 17 mai 2026"),
        )

    def test_dst_matrix_spring_forward_and_fall_back_keep_same_model_day(self) -> None:
        scenarios = [
            {
                "name": "spring_forward",
                "now_iso": "2026-03-29T01:30:00Z",
                "message_ts": "2026-03-29T00:30:00Z",
                "expected_local_date": "2026-03-29",
                "expected_human_day": "dimanche 29 mars 2026",
                "forbidden_human_days": ("28 mars 2026", "30 mars 2026"),
                "expected_message_label": "dimanche 29 mars 2026 à 1h30 Europe/Paris — aujourd'hui",
            },
            {
                "name": "fall_back",
                "now_iso": "2026-10-25T01:30:00Z",
                "message_ts": "2026-10-25T00:30:00Z",
                "expected_local_date": "2026-10-25",
                "expected_human_day": "dimanche 25 octobre 2026",
                "forbidden_human_days": ("24 octobre 2026", "26 octobre 2026"),
                "expected_message_label": "dimanche 25 octobre 2026 à 2h30 Europe/Paris — aujourd'hui",
            },
        ]

        for scenario in scenarios:
            with self.subTest(name=scenario["name"]):
                self.assert_lanes_share_local_day(
                    now_iso=str(scenario["now_iso"]),
                    message_ts=str(scenario["message_ts"]),
                    expected_local_date=str(scenario["expected_local_date"]),
                    expected_human_day=str(scenario["expected_human_day"]),
                    forbidden_human_days=tuple(scenario["forbidden_human_days"]),
                )
                label = time_input.render_delta_label(
                    str(scenario["message_ts"]),
                    str(scenario["now_iso"]),
                    timezone_name=TZ,
                )
                self.assertEqual(label, scenario["expected_message_label"])

    def test_validation_and_arbiter_keep_raw_utc_subordinate_to_local_labels(self) -> None:
        now_iso = "2026-05-17T22:05:00Z"
        validation_payload, validation_user_message = self._validation_payload(
            now_iso=now_iso,
            message_ts=now_iso,
        )
        arbiter_payload = self._arbiter_payload(now_iso=now_iso, message_ts=now_iso)

        self.assertEqual(validation_payload["messages"][0]["timestamp"], now_iso)
        self.assertEqual(
            validation_payload["messages"][0]["temporal_label"],
            "lundi 18 mai 2026 à 0h05 Europe/Paris — à l'instant",
        )
        self.assertLess(
            validation_user_message.index("temporal_reference"),
            validation_user_message.index("validation_dialogue_context"),
        )
        self.assertEqual(arbiter_payload["temporal_reference"]["local_date"], "2026-05-18")
        self.assertIn("lundi 18 mai 2026 à 0h05 Europe/Paris — à l'instant", str(arbiter_payload["recent_turn"]))
        self.assertEqual(
            arbiter_payload["candidate_label"],
            "lundi 18 mai 2026 à 0h05 Europe/Paris — à l'instant",
        )

    def test_identity_and_stimmung_cannot_create_temporal_day_claims(self) -> None:
        admissible, source_summary = identity_temporal_guard.admissible_turns_with_source_summary(
            [{"role": "user", "content": "Depuis hier je suis anxieux."}]
        )
        self.assertEqual(admissible, [])
        self.assertEqual(source_summary["user"]["weak_relative_source_count"], 1)
        self.assertEqual(
            arbiter._validate_identity_output(
                {
                    "entries": [
                        {
                            "subject": "user",
                            "content": "L'utilisateur est anxieux.",
                            "stability": "durable",
                            "utterance_mode": "self_description",
                            "recurrence": "first_seen",
                            "scope": "user",
                            "evidence_kind": "explicit",
                            "confidence": 0.9,
                            "reason": "paraphrase",
                        }
                    ]
                },
                source_summary=source_summary,
            ),
            [],
        )

        sanitized_pairs, periodic_summary = identity_temporal_guard.sanitized_buffer_pairs_with_source_summary(
            [
                {
                    "user": {"role": "user", "content": "Aujourd'hui je suis anxieux."},
                    "assistant": {"role": "assistant", "content": "Je note."},
                }
            ]
        )
        self.assertEqual(sanitized_pairs[0]["user"]["content"], "")
        periodic_result = arbiter._sanitize_identity_periodic_temporal_claims(
            {
                "user": {
                    "operations": [
                        {"kind": "add", "proposition": "L'utilisateur est anxieux.", "reason": "paraphrase"}
                    ]
                }
            },
            source_summary=periodic_summary,
        )
        self.assertEqual(
            periodic_result["user"]["operations"],
            [
                {
                    "kind": "no_change",
                    "proposition": "",
                    "reason": "weak relative temporal identity source rejected",
                }
            ],
        )

        recent_window = {
            "turns": [
                {
                    "turn_status": "complete",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Depuis hier je suis inquiet.",
                            "timestamp": "2026-05-17T22:05:00Z",
                        }
                    ],
                }
            ]
        }
        stimmung_messages = stimmung_agent._build_messages(
            system_prompt=stimmung_agent._load_system_prompt(),
            user_msg="Je suis inquiet.",
            recent_window_input_payload=recent_window,
        )
        stimmung_payload = "\n".join(message["content"] for message in stimmung_messages)
        self.assertIn("Tu ignores les timestamps, les delais et les gaps temporels", stimmung_payload)
        self.assertIn("Depuis hier je suis inquiet.", stimmung_payload)
        self.assertNotIn("2026-05-17T22:05:00Z", stimmung_payload)
        self.assertNotIn("17 mai 2026", stimmung_payload)

    def test_deterministic_classifier_and_invalids_close_temporal_fallbacks(self) -> None:
        for message in ("Je t'en ai parlé hier", "Depuis hier, ça me travaille"):
            with self.subTest(message=message):
                payload = user_turn_input.build_user_turn_input(
                    user_message=message,
                    recent_window_input_payload=None,
                    time_input_payload=time_input.build_time_input(
                        now_utc_iso="2026-05-17T22:05:00Z",
                        timezone_name=TZ,
                    ),
                )
                self.assertEqual(payload["qualification_temporelle"]["portee_temporelle"], "passee")
                self.assertEqual(payload["qualification_temporelle"]["ancrage_temporel"], "now")

        with self.assertRaisesRegex(conversations_store.InvalidTimestampError, "invalid_timestamp"):
            conversations_store.ts_to_iso(
                "not-a-date",
                now_iso_func=lambda: self.fail("invalid timestamp must not become now"),
            )
        with self.assertRaisesRegex(time_input.InvalidTimezoneError, "invalid_timezone"):
            time_input.build_time_input(
                now_utc_iso="2026-05-17T22:05:00Z",
                timezone_name="No/Such_Zone",
            )
        with self.assertRaisesRegex(time_input.InvalidTimezoneError, "invalid_timezone"):
            time_input.render_delta_label(
                "2026-05-17T22:05:00Z",
                "2026-05-17T22:10:00Z",
                timezone_name="No/Such_Zone",
            )


if __name__ == "__main__":
    unittest.main()
