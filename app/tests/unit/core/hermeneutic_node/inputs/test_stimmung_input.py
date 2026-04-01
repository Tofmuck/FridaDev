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

from core.hermeneutic_node.inputs import stimmung_input


def _signal(*, dominant_tone: str, tones: list[dict[str, int]]) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "present": True,
        "tones": tones,
        "dominant_tone": dominant_tone,
        "confidence": 0.8,
    }


class StimmungInputTests(unittest.TestCase):
    def test_extract_recent_affective_turn_signals_reads_message_meta_from_user_turns(self) -> None:
        messages = [
            {"role": "assistant", "content": "ignore"},
            {
                "role": "user",
                "content": "tour 1",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="neutralite",
                        tones=[{"tone": "neutralite", "strength": 3}],
                    )
                },
            },
            {
                "role": "user",
                "content": "tour 2",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="frustration",
                        tones=[
                            {"tone": "frustration", "strength": 7},
                            {"tone": "confusion", "strength": 4},
                        ],
                    )
                },
            },
        ]

        signals = stimmung_input.extract_recent_affective_turn_signals(messages=messages)

        self.assertEqual(len(signals), 2)
        self.assertEqual(signals[0]["dominant_tone"], "neutralite")
        self.assertEqual(signals[1]["dominant_tone"], "frustration")

    def test_build_stimmung_input_aggregates_recent_message_meta_signals(self) -> None:
        messages = [
            {
                "role": "user",
                "content": "tour 1",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="neutralite",
                        tones=[{"tone": "neutralite", "strength": 3}],
                    )
                },
            },
            {
                "role": "assistant",
                "content": "reponse 1",
            },
            {
                "role": "user",
                "content": "tour 2",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="frustration",
                        tones=[
                            {"tone": "frustration", "strength": 7},
                            {"tone": "confusion", "strength": 4},
                        ],
                    )
                },
            },
            {
                "role": "user",
                "content": "tour 3",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="frustration",
                        tones=[{"tone": "frustration", "strength": 6}],
                    )
                },
            },
        ]

        payload = stimmung_input.build_stimmung_input(messages=messages)

        self.assertTrue(payload["present"])
        self.assertEqual(payload["dominant_tone"], "frustration")
        self.assertEqual(
            payload["active_tones"],
            [
                {"tone": "frustration", "strength": 6},
                {"tone": "confusion", "strength": 4},
            ],
        )
        self.assertEqual(payload["stability"], "stable")
        self.assertEqual(payload["shift_state"], "steady")
        self.assertEqual(payload["turns_considered"], 3)

    def test_build_stimmung_input_uses_hysteresis_before_declaring_shift(self) -> None:
        messages = [
            {
                "role": "user",
                "content": "tour 1",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="frustration",
                        tones=[{"tone": "frustration", "strength": 6}],
                    )
                },
            },
            {
                "role": "user",
                "content": "tour 2",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="frustration",
                        tones=[{"tone": "frustration", "strength": 6}],
                    )
                },
            },
            {
                "role": "user",
                "content": "tour 3",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="confusion",
                        tones=[{"tone": "confusion", "strength": 7}],
                    )
                },
            },
        ]

        payload = stimmung_input.build_stimmung_input(messages=messages)

        self.assertTrue(payload["present"])
        self.assertEqual(payload["dominant_tone"], "frustration")
        self.assertEqual(payload["active_tones"][0], {"tone": "frustration", "strength": 6})
        self.assertEqual(payload["shift_state"], "candidate_shift")
        self.assertEqual(payload["stability"], "volatile")

    def test_build_stimmung_input_returns_missing_when_latest_user_signal_is_unavailable(self) -> None:
        messages = [
            {
                "role": "user",
                "content": "tour 1",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: _signal(
                        dominant_tone="frustration",
                        tones=[{"tone": "frustration", "strength": 6}],
                    )
                },
            },
            {
                "role": "user",
                "content": "tour 2",
                "meta": {
                    stimmung_input.SIGNAL_META_KEY: {
                        "schema_version": "v1",
                        "present": False,
                        "tones": [],
                        "dominant_tone": None,
                        "confidence": 0.0,
                    }
                },
            },
        ]

        payload = stimmung_input.build_stimmung_input(messages=messages)

        self.assertEqual(
            payload,
            {
                "schema_version": "v1",
                "present": False,
                "dominant_tone": None,
                "active_tones": [],
                "stability": "",
                "shift_state": "",
                "turns_considered": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
