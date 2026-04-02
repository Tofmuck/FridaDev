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

from core.hermeneutic_node.runtime import node_state


def _output_regime(
    *,
    discursive_regime: str = "simple",
    resituation_level: str = "none",
    time_reference_mode: str = "atemporal",
) -> dict[str, str]:
    return {
        "discursive_regime": discursive_regime,
        "resituation_level": resituation_level,
        "time_reference_mode": time_reference_mode,
    }


def _state(
    *,
    conversation_id: str = "conv-1",
    updated_at: str = "2026-04-02T12:00:00Z",
    judgment_posture: str = "answer",
    last_answer_output_regime: dict[str, str] | None = None,
) -> dict[str, object]:
    payload = {
        "schema_version": "v1",
        "conversation_id": conversation_id,
        "updated_at": updated_at,
        "last_judgment_posture": judgment_posture,
    }
    if last_answer_output_regime is not None:
        payload["last_answer_output_regime"] = dict(last_answer_output_regime)
    return payload


class NodeStateTests(unittest.TestCase):
    def test_build_node_state_rejects_invalid_conversation_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_conversation_id"):
            node_state.build_node_state(
                conversation_id="",
                updated_at="2026-04-02T12:00:00Z",
                judgment_posture="answer",
                output_regime=_output_regime(discursive_regime="cadre", resituation_level="explicit"),
            )

    def test_build_node_state_rejects_invalid_updated_at(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_updated_at"):
            node_state.build_node_state(
                conversation_id="conv-1",
                updated_at="not-a-date",
                judgment_posture="answer",
                output_regime=_output_regime(discursive_regime="cadre", resituation_level="explicit"),
            )

    def test_build_node_state_rejects_invalid_judgment_posture(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_judgment_posture"):
            node_state.build_node_state(
                conversation_id="conv-1",
                updated_at="2026-04-02T12:00:00Z",
                judgment_posture="invalid",
                output_regime=_output_regime(discursive_regime="cadre", resituation_level="explicit"),
            )

    def test_build_node_state_rejects_invalid_output_regime(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_output_regime"):
            node_state.build_node_state(
                conversation_id="conv-1",
                updated_at="2026-04-02T12:00:00Z",
                judgment_posture="answer",
                output_regime={"discursive_regime": "simple"},
            )

    def test_build_node_state_rejects_invalid_existing_node_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_existing_node_state"):
            node_state.build_node_state(
                conversation_id="conv-1",
                updated_at="2026-04-02T12:00:00Z",
                judgment_posture="answer",
                output_regime=_output_regime(discursive_regime="cadre", resituation_level="explicit"),
                existing_node_state={},
            )

    def test_build_node_state_rejects_clarify_with_substantive_output_regime(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_output_regime"):
            node_state.build_node_state(
                conversation_id="conv-1",
                updated_at="2026-04-02T12:00:00Z",
                judgment_posture="clarify",
                output_regime=_output_regime(
                    discursive_regime="continuite",
                    resituation_level="light",
                    time_reference_mode="dialogue_relative",
                ),
            )

    def test_apply_output_regime_inertia_rejects_suspend_with_substantive_output_regime(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_output_regime"):
            node_state.apply_output_regime_inertia(
                conversation_id="conv-1",
                judgment_posture="suspend",
                output_regime=_output_regime(
                    discursive_regime="continuite",
                    resituation_level="light",
                    time_reference_mode="dialogue_relative",
                ),
            )

    def test_apply_output_regime_inertia_rejects_answer_with_meta_output_regime(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_output_regime"):
            node_state.apply_output_regime_inertia(
                conversation_id="conv-1",
                judgment_posture="answer",
                output_regime=_output_regime(
                    discursive_regime="meta",
                    resituation_level="none",
                    time_reference_mode="atemporal",
                ),
            )

    def test_validate_node_state_normalizes_missing_last_answer_output_regime(self) -> None:
        validated = node_state.validate_node_state(
            _state(
                judgment_posture="clarify",
            )
        )

        self.assertEqual(
            validated,
            {
                "schema_version": "v1",
                "conversation_id": "conv-1",
                "updated_at": "2026-04-02T12:00:00Z",
                "last_judgment_posture": "clarify",
                "last_answer_output_regime": None,
            },
        )

    def test_build_node_state_constructs_minimal_state_for_answer(self) -> None:
        payload = node_state.build_node_state(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            judgment_posture="answer",
            output_regime=_output_regime(
                discursive_regime="cadre",
                resituation_level="explicit",
                time_reference_mode="dialogue_relative",
            ),
        )

        self.assertEqual(
            payload,
            {
                "schema_version": "v1",
                "conversation_id": "conv-1",
                "updated_at": "2026-04-02T12:00:00Z",
                "last_judgment_posture": "answer",
                "last_answer_output_regime": {
                    "discursive_regime": "cadre",
                    "resituation_level": "explicit",
                    "time_reference_mode": "dialogue_relative",
                },
            },
        )

    def test_build_node_state_keeps_last_answer_output_regime_on_clarify(self) -> None:
        existing = _state(
            judgment_posture="answer",
            last_answer_output_regime=_output_regime(
                discursive_regime="continuite",
                resituation_level="light",
                time_reference_mode="dialogue_relative",
            ),
        )

        payload = node_state.build_node_state(
            conversation_id="conv-1",
            updated_at="2026-04-02T13:00:00Z",
            judgment_posture="clarify",
            output_regime=_output_regime(
                discursive_regime="meta",
                resituation_level="light",
                time_reference_mode="dialogue_relative",
            ),
            existing_node_state=existing,
        )

        self.assertEqual(payload["last_judgment_posture"], "clarify")
        self.assertEqual(
            payload["last_answer_output_regime"],
            existing["last_answer_output_regime"],
        )

    def test_build_node_state_keeps_last_answer_output_regime_on_suspend(self) -> None:
        existing = _state(
            judgment_posture="answer",
            last_answer_output_regime=_output_regime(
                discursive_regime="cadre",
                resituation_level="explicit",
                time_reference_mode="anchored_past",
            ),
        )

        payload = node_state.build_node_state(
            conversation_id="conv-1",
            updated_at="2026-04-02T13:00:00Z",
            judgment_posture="suspend",
            output_regime=_output_regime(
                discursive_regime="meta",
                resituation_level="none",
                time_reference_mode="atemporal",
            ),
            existing_node_state=existing,
        )

        self.assertEqual(payload["last_judgment_posture"], "suspend")
        self.assertEqual(
            payload["last_answer_output_regime"],
            existing["last_answer_output_regime"],
        )

    def test_apply_output_regime_inertia_does_not_reuse_without_prior_answer(self) -> None:
        payload = node_state.apply_output_regime_inertia(
            conversation_id="conv-1",
            judgment_posture="answer",
            output_regime=_output_regime(),
            existing_node_state=None,
        )

        self.assertEqual(
            payload,
            {
                "output_regime": _output_regime(),
                "state_used": False,
            },
        )

    def test_apply_output_regime_inertia_reuses_prior_substantive_output_regime(self) -> None:
        existing = _state(
            judgment_posture="answer",
            last_answer_output_regime=_output_regime(
                discursive_regime="continuite",
                resituation_level="light",
                time_reference_mode="dialogue_relative",
            ),
        )

        payload = node_state.apply_output_regime_inertia(
            conversation_id="conv-1",
            judgment_posture="answer",
            output_regime=_output_regime(),
            existing_node_state=existing,
        )

        self.assertEqual(
            payload,
            {
                "output_regime": {
                    "discursive_regime": "continuite",
                    "resituation_level": "light",
                    "time_reference_mode": "dialogue_relative",
                },
                "state_used": True,
            },
        )

    def test_apply_output_regime_inertia_does_not_override_marked_current_output_regime(self) -> None:
        existing = _state(
            judgment_posture="answer",
            last_answer_output_regime=_output_regime(
                discursive_regime="continuite",
                resituation_level="light",
                time_reference_mode="dialogue_relative",
            ),
        )

        payload = node_state.apply_output_regime_inertia(
            conversation_id="conv-1",
            judgment_posture="answer",
            output_regime=_output_regime(
                discursive_regime="cadre",
                resituation_level="explicit",
                time_reference_mode="atemporal",
            ),
            existing_node_state=existing,
        )

        self.assertEqual(
            payload,
            {
                "output_regime": {
                    "discursive_regime": "cadre",
                    "resituation_level": "explicit",
                    "time_reference_mode": "atemporal",
                },
                "state_used": False,
            },
        )

    def test_apply_output_regime_inertia_does_not_apply_on_clarify(self) -> None:
        existing = _state(
            judgment_posture="answer",
            last_answer_output_regime=_output_regime(
                discursive_regime="continuite",
                resituation_level="light",
                time_reference_mode="dialogue_relative",
            ),
        )

        payload = node_state.apply_output_regime_inertia(
            conversation_id="conv-1",
            judgment_posture="clarify",
            output_regime=_output_regime(
                discursive_regime="meta",
                resituation_level="none",
                time_reference_mode="atemporal",
            ),
            existing_node_state=existing,
        )

        self.assertEqual(
            payload,
            {
                "output_regime": {
                    "discursive_regime": "meta",
                    "resituation_level": "none",
                    "time_reference_mode": "atemporal",
                },
                "state_used": False,
            },
        )

    def test_apply_output_regime_inertia_rejects_cross_conversation_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_existing_node_state"):
            node_state.apply_output_regime_inertia(
                conversation_id="conv-1",
                judgment_posture="answer",
                output_regime=_output_regime(),
                existing_node_state=_state(
                    conversation_id="conv-other",
                    judgment_posture="answer",
                    last_answer_output_regime=_output_regime(
                        discursive_regime="continuite",
                        resituation_level="light",
                        time_reference_mode="dialogue_relative",
                    ),
                ),
            )

    def test_node_state_never_stores_meta_as_last_answer_output_regime(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_existing_node_state"):
            node_state.build_node_state(
                conversation_id="conv-1",
                updated_at="2026-04-02T13:00:00Z",
                judgment_posture="clarify",
                output_regime=_output_regime(
                    discursive_regime="meta",
                    resituation_level="none",
                    time_reference_mode="atemporal",
                ),
                existing_node_state=_state(
                    judgment_posture="answer",
                    last_answer_output_regime=_output_regime(
                        discursive_regime="meta",
                        resituation_level="none",
                        time_reference_mode="atemporal",
                    ),
                ),
            )

    def test_build_node_state_returns_exact_contract_fields(self) -> None:
        payload = node_state.build_node_state(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            judgment_posture="clarify",
            output_regime=_output_regime(
                discursive_regime="meta",
                resituation_level="none",
                time_reference_mode="atemporal",
            ),
        )

        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "conversation_id",
                "updated_at",
                "last_judgment_posture",
                "last_answer_output_regime",
            },
        )
        self.assertIsNone(payload["last_answer_output_regime"])


if __name__ == "__main__":
    unittest.main()
