from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from observability import observability_payload_guard


REQUIRED_QUALITATIVE_TRAITS = frozenset(
    {
        "audit_ritual",
        "bounded_proactivity",
        "gap_repair",
        "method_continuity",
        "refusal_framing",
        "relation_presence",
        "sobriety_humor_level",
    }
)

FACT_TRAITS = frozenset(
    {
        "identity_core_fact",
        "memory_project_fact",
        "summary_task_fact",
    }
)

ARTIFICIAL_SENTINELS = (
    "ARTIFICIAL_DIALOGUE_MARKER_A",
    "ARTIFICIAL_SUMMARY_MARKER_A",
    "ARTIFICIAL_MEMORY_MARKER_A",
)


@dataclass(frozen=True)
class ContinuityCarrier:
    name: str
    carrier_kind: str
    status: str
    selected: bool
    traits: frozenset[str]
    raw_content_included: bool = False
    source_text_included: bool = False


def _encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _carrier(
    name: str,
    carrier_kind: str,
    traits: Iterable[str] = (),
    *,
    selected: bool = True,
    status: str = "ok",
) -> ContinuityCarrier:
    return ContinuityCarrier(
        name=name,
        carrier_kind=carrier_kind,
        status=status,
        selected=selected,
        traits=frozenset(traits),
    )


def _identity_stable() -> ContinuityCarrier:
    return _carrier(
        "identity_stable",
        "identity",
        {"identity_core_fact"},
    )


def _memory_project_fact(*, selected: bool = True) -> ContinuityCarrier:
    return _carrier(
        "memory_project_fact",
        "memory",
        {"memory_project_fact"},
        selected=selected,
        status="ok" if selected else "not_selected",
    )


def _summary_flattened_after_resume() -> ContinuityCarrier:
    return _carrier(
        "summary_after_resume",
        "summary",
        {"summary_task_fact", "method_continuity"},
    )


def _recent_dialogue_full_presence() -> ContinuityCarrier:
    return _carrier(
        "recent_dialogue",
        "recent_dialogue",
        REQUIRED_QUALITATIVE_TRAITS,
    )


def _continuity_capsule_candidate() -> ContinuityCarrier:
    return _carrier(
        "continuity_capsule_candidate",
        "continuity_capsule_candidate",
        REQUIRED_QUALITATIVE_TRAITS,
    )


def _lane_noops() -> tuple[ContinuityCarrier, ...]:
    return (
        _carrier("web_lane", "lane_noop", selected=False, status="not_selected"),
        _carrier("note_lane", "lane_noop", selected=False, status="not_selected"),
        _carrier("document_lane", "lane_noop", selected=False, status="not_selected"),
        _carrier("biblio_lane", "lane_noop", selected=False, status="not_selected"),
        _carrier("agenda_lane", "lane_noop", selected=False, status="not_selected"),
    )


def _selected_traits(carriers: Iterable[ContinuityCarrier]) -> frozenset[str]:
    traits: set[str] = set()
    for carrier in carriers:
        if carrier.selected:
            traits.update(carrier.traits)
    return frozenset(traits)


def _evaluate_continuity(
    carriers: Iterable[ContinuityCarrier],
    *,
    shadow_content: Mapping[str, str] | None = None,
    capsule_runtime_injected: bool = False,
) -> dict[str, object]:
    del shadow_content
    selected = tuple(carrier for carrier in carriers if carrier.selected)
    available = _selected_traits(selected)
    missing = sorted(REQUIRED_QUALITATIVE_TRAITS - available)
    capsule_candidate_selected = any(carrier.carrier_kind == "continuity_capsule_candidate" for carrier in selected)
    recent_dialogue_selected = any(carrier.carrier_kind == "recent_dialogue" for carrier in selected)
    summary_selected = any(carrier.carrier_kind == "summary" for carrier in selected)
    return {
        "status": "ok" if not missing else "failed",
        "reason_code": "continuity_fixture_passed" if not missing else "continuity_traits_missing",
        "required_trait_count": len(REQUIRED_QUALITATIVE_TRAITS),
        "available_trait_count": len(REQUIRED_QUALITATIVE_TRAITS) - len(missing),
        "missing_trait_count": len(missing),
        "missing_trait_codes": missing,
        "selected_carrier_count": len(selected),
        "summary_selected": summary_selected,
        "recent_dialogue_selected": recent_dialogue_selected,
        "continuity_capsule_candidate_selected": capsule_candidate_selected,
        "summary_flattening_detected": bool(summary_selected and not recent_dialogue_selected and missing),
        "capsule_runtime_injected": capsule_runtime_injected,
        "model_called": False,
        "provider": "none",
        "raw_content_included": False,
        "raw_prompt_included": False,
        "raw_message_included": False,
        "raw_lane_content_included": False,
        "raw_provider_payload_included": False,
        "raw_secret_included": False,
    }


def _content_free_observation(results: Iterable[Mapping[str, object]]) -> dict[str, object]:
    items = tuple(results)
    return {
        "status_schema_version": "continuity_fixture_v1",
        "scope": "continuity_fixture",
        "status": "ok" if all(item.get("status") == "ok" for item in items) else "failed",
        "reason_code": "continuity_fixture_suite_checked",
        "scenario_count": len(items),
        "failed_count": sum(1 for item in items if item.get("status") != "ok"),
        "missing_trait_count": sum(int(item.get("missing_trait_count") or 0) for item in items),
        "model_called": False,
        "capsule_runtime_injected": False,
        "content_free": True,
        "raw_content_included": False,
        "raw_prompt_included": False,
        "raw_message_included": False,
        "raw_lane_content_included": False,
        "raw_provider_payload_included": False,
        "raw_secret_included": False,
    }


class ContinuityPayloadFixtureTests(unittest.TestCase):
    def test_long_conversation_can_preserve_presence_from_recent_dialogue_without_capsule(self) -> None:
        result = _evaluate_continuity(
            (
                _identity_stable(),
                _memory_project_fact(),
                _summary_flattened_after_resume(),
                _recent_dialogue_full_presence(),
                *_lane_noops(),
            ),
            shadow_content={"dialogue": ARTIFICIAL_SENTINELS[0]},
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["missing_trait_count"], 0)
        self.assertTrue(result["recent_dialogue_selected"])
        self.assertFalse(result["continuity_capsule_candidate_selected"])
        self.assertFalse(result["capsule_runtime_injected"])
        self.assertNotIn(ARTIFICIAL_SENTINELS[0], _encoded(result))

    def test_new_conversation_without_memory_or_lanes_loses_presence_until_candidate_capsule(self) -> None:
        without_capsule = _evaluate_continuity(
            (
                _identity_stable(),
                _memory_project_fact(selected=False),
                *_lane_noops(),
            ),
            shadow_content={"memory": ARTIFICIAL_SENTINELS[2]},
        )
        with_candidate = _evaluate_continuity(
            (
                _identity_stable(),
                _memory_project_fact(selected=False),
                _continuity_capsule_candidate(),
                *_lane_noops(),
            )
        )

        self.assertEqual(without_capsule["status"], "failed")
        self.assertGreater(without_capsule["missing_trait_count"], 0)
        self.assertFalse(without_capsule["recent_dialogue_selected"])
        self.assertFalse(without_capsule["continuity_capsule_candidate_selected"])
        self.assertEqual(with_candidate["status"], "ok")
        self.assertEqual(with_candidate["missing_trait_count"], 0)
        self.assertTrue(with_candidate["continuity_capsule_candidate_selected"])
        self.assertFalse(with_candidate["capsule_runtime_injected"])
        self.assertNotIn(ARTIFICIAL_SENTINELS[2], _encoded({"before": without_capsule, "after": with_candidate}))

    def test_post_summary_fixture_detects_flattened_voice_and_candidate_restores_minimum(self) -> None:
        summary_only = _evaluate_continuity(
            (
                _identity_stable(),
                _summary_flattened_after_resume(),
            ),
            shadow_content={"summary": ARTIFICIAL_SENTINELS[1]},
        )
        restored_by_candidate = _evaluate_continuity(
            (
                _identity_stable(),
                _summary_flattened_after_resume(),
                _continuity_capsule_candidate(),
            )
        )

        self.assertEqual(summary_only["status"], "failed")
        self.assertTrue(summary_only["summary_selected"])
        self.assertTrue(summary_only["summary_flattening_detected"])
        self.assertIn("relation_presence", summary_only["missing_trait_codes"])
        self.assertIn("refusal_framing", summary_only["missing_trait_codes"])
        self.assertIn("sobriety_humor_level", summary_only["missing_trait_codes"])
        self.assertEqual(restored_by_candidate["status"], "ok")
        self.assertEqual(restored_by_candidate["missing_trait_count"], 0)
        self.assertFalse(restored_by_candidate["capsule_runtime_injected"])
        self.assertNotIn(ARTIFICIAL_SENTINELS[1], _encoded({"before": summary_only, "after": restored_by_candidate}))

    def test_candidate_capsule_is_distinct_from_identity_memory_and_summary(self) -> None:
        capsule = _continuity_capsule_candidate()
        carriers = (_identity_stable(), _memory_project_fact(), _summary_flattened_after_resume(), capsule)

        self.assertEqual(capsule.carrier_kind, "continuity_capsule_candidate")
        self.assertFalse(capsule.raw_content_included)
        self.assertFalse(capsule.source_text_included)
        self.assertFalse(capsule.traits & FACT_TRAITS)
        self.assertTrue(REQUIRED_QUALITATIVE_TRAITS <= capsule.traits)
        self.assertEqual(
            {carrier.carrier_kind for carrier in carriers},
            {"identity", "memory", "summary", "continuity_capsule_candidate"},
        )

    def test_qualitative_fixture_observation_is_content_free_and_guard_accepted(self) -> None:
        passing = _evaluate_continuity((_recent_dialogue_full_presence(),))
        failing = _evaluate_continuity((_summary_flattened_after_resume(),))
        observation = _content_free_observation((passing, failing))

        decision = observability_payload_guard.guard_payload(observation)
        encoded = _encoded({"observation": observation, "guarded": decision.payload})

        self.assertTrue(decision.accepted)
        self.assertEqual(observation["status_schema_version"], "continuity_fixture_v1")
        self.assertEqual(observation["scenario_count"], 2)
        self.assertEqual(observation["failed_count"], 1)
        self.assertTrue(observation["content_free"])
        self.assertFalse(observation["capsule_runtime_injected"])
        self.assertFalse(observation["raw_content_included"])
        self.assertFalse(observation["raw_prompt_included"])
        self.assertFalse(observation["raw_message_included"])
        self.assertFalse(observation["raw_lane_content_included"])
        self.assertFalse(observation["raw_provider_payload_included"])
        self.assertFalse(observation["raw_secret_included"])
        for sentinel in ARTIFICIAL_SENTINELS:
            self.assertNotIn(sentinel, encoded)


if __name__ == "__main__":
    unittest.main()
