from __future__ import annotations

import copy
import json
import unittest

from core.hermeneutic_node.doctrine import epistemic_regime
from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from core.hermeneutic_node.runtime import primary_node
from core.hermeneutic_node.validation import hard_guards, validation_agent, validation_messages
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.support.stimmung_dialogic_pipeline import (
    MAIN_MODEL,
    STIMMUNG_PRIMARY_MODEL,
    STIMMUNG_FALLBACK_MODEL,
    affective_signal,
    capture_validation_request,
    double_failure,
    exercise_stimmung_dialogue,
    fallback_signal,
    primary_signal,
)


def _strong_regime_inputs() -> dict[str, object]:
    return {
        "memory_retrieved": {
            "schema_version": "v1",
            "retrieved_count": 2,
            "traces": [],
        },
        "memory_arbitration": {
            "schema_version": "v1",
            "status": "ok",
            "kept_count": 1,
            "rejected_count": 0,
            "decisions": [],
        },
        "summary_input": {
            "schema_version": "v1",
            "status": "available",
            "summary": {"id": "lot4-summary"},
        },
        "recent_window_input": {
            "schema_version": "v1",
            "turn_count": 2,
            "turns": [],
        },
        "user_turn_input": {
            "schema_version": "v1",
            "geste_dialogique_dominant": "exposition",
            "regime_probatoire": {
                "principe": "maximal_possible",
                "types_de_preuve_attendus": [],
                "provenances": ["dialogue_trace"],
                "regime_de_vigilance": "standard",
                "composition_probatoire": "isolee",
            },
            "qualification_temporelle": {
                "portee_temporelle": "atemporale",
                "ancrage_temporel": "non_ancre",
            },
        },
        "user_turn_signals": {
            "present": False,
            "ambiguity_present": False,
            "underdetermination_present": False,
            "active_signal_families": [],
            "active_signal_families_count": 0,
        },
        "web_input": {},
    }


def _assert_persistent_signal_history(
    candidate: dict[str, object],
    expected_signals: list[dict[str, object]],
) -> None:
    messages = candidate.get("messages")
    if not isinstance(messages, list):
        raise AssertionError("persistent conversation must contain a message list")
    expected_roles = ["system"] + [role for _signal in expected_signals for role in ("user", "assistant")]
    if [message.get("role") for message in messages if isinstance(message, dict)] != expected_roles:
        raise AssertionError("persistent conversation order or cardinality changed")
    users = [message for message in messages if isinstance(message, dict) and message.get("role") == "user"]
    if len(users) != len(expected_signals):
        raise AssertionError("persistent user-message cardinality changed")
    observed = [message.get("meta", {}).get("affective_turn_signal") for message in users]
    if observed != expected_signals:
        raise AssertionError("persistent Stimmung history changed content or order")


def _assert_four_turn_aggregate(candidate: dict[str, object]) -> None:
    if candidate.get("schema_version") != "v1" or candidate.get("present") is not True:
        raise AssertionError("four-turn Stimmung aggregate must be present and canonical")
    if candidate.get("turns_considered") != 4:
        raise AssertionError("Stimmung aggregate must retain exactly the four recent valid turns")


def _assert_stable_aggregate(candidate: dict[str, object]) -> None:
    _assert_four_turn_aggregate(candidate)
    if candidate.get("stability") != "stable" or candidate.get("shift_state") != "steady":
        raise AssertionError("homogeneous four-turn affect must remain stable and steady")


def _assert_transition_aggregate(candidate: dict[str, object]) -> None:
    _assert_four_turn_aggregate(candidate)
    if candidate.get("stability") != "volatile":
        raise AssertionError("the observed post-stability transition must remain volatile")


def _assert_absent_stable_transition_regimes(
    absent: dict[str, object],
    stable: dict[str, object],
    transition: dict[str, object],
) -> None:
    expected_inert = {
        "epistemic_regime": "certain",
        "proof_regime": "suffisant_en_l_etat",
        "uncertainty_posture": "discrete",
    }
    expected_cautious = {
        "epistemic_regime": "probable",
        "proof_regime": "source_explicite_requise",
        "uncertainty_posture": "prudente",
    }
    if absent != expected_inert or stable != expected_inert or transition != expected_cautious:
        raise AssertionError("absent/stable/transition regime contract changed")


def _assert_caller_provenance(events: list[dict[str, object]]) -> None:
    observed = [
        (
            event.get("status"),
            event.get("payload_json", {}).get("decision_source"),
            event.get("payload_json", {}).get("model"),
            event.get("payload_json", {}).get("present"),
        )
        for event in events
    ]
    expected = [
        ("ok", "primary", STIMMUNG_PRIMARY_MODEL, True),
        ("ok", "fallback", STIMMUNG_FALLBACK_MODEL, True),
        ("error", "fail_open", STIMMUNG_FALLBACK_MODEL, False),
        ("ok", "primary", STIMMUNG_PRIMARY_MODEL, True),
    ]
    if observed != expected:
        raise AssertionError("Stimmung caller provenance contract changed")


def _validation_projection(capture: dict[str, object]) -> dict[str, object]:
    block = str(capture.get("user_content") or "").split(
        "canonical_inputs (supports secondaires de relecture contextuelle):\n",
        1,
    )[1].split("\n\nTache:\n", 1)[0].split("\n\nhard_guards", 1)[0]
    return json.loads(block)


def _assert_full_projected_stimmung(
    projection: dict[str, object],
    expected_stimmung: dict[str, object],
) -> None:
    validated = validation_messages.validate_validation_canonical_projection(projection)
    if validated["stimmung_delivery"] != {"status": "full", "reason_code": "included"}:
        raise AssertionError("valid Stimmung was not delivered in full")
    if validated["families"].get("stimmung_input") != expected_stimmung:
        raise AssertionError("delivered Stimmung differs from the canonical aggregate")


def _assert_validation_reception_claim(capture: dict[str, object], claimed_received: bool) -> None:
    projection = _validation_projection(capture)
    delivery = projection.get("stimmung_delivery") or {}
    families = projection.get("families") or {}
    actually_received = (
        delivery.get("status") == "full"
        and delivery.get("reason_code") == "included"
        and isinstance(families.get("stimmung_input"), dict)
    )
    if claimed_received is not actually_received:
        raise AssertionError("Validation reception claim contradicts captured provider material")


def _assert_main_payload_is_derived_only(messages: list[dict[str, object]]) -> None:
    serialized = json.dumps(messages, sort_keys=True)
    if "stimmung_input" in serialized or "active_tones" in serialized:
        raise AssertionError("main payload leaked raw or aggregated Stimmung material")


class Lot4StimmungCausalGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def test_real_coordinator_store_functions_round_trip_and_aggregate_four_primary_signals(self) -> None:
        signal = affective_signal("apaisement", 7)
        result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(signal) for _ in range(4)],
        )

        self.assertEqual(len(result["chat_response_calls"]), 4)
        self.assertEqual(len(result["caller_events"]), 4)
        self.assertEqual(
            [event["payload_json"]["model"] for event in result["caller_events"]],
            [STIMMUNG_PRIMARY_MODEL] * 4,
        )
        self.assertEqual(len(set(result["reload_object_ids"])), len(result["reload_object_ids"]))
        self.assertEqual(result["repeated_reloads"][0], result["repeated_reloads"][1])
        self.assertEqual(result["node_calls"][-1]["stimmung_input"]["turns_considered"], 4)
        self.assertEqual(result["node_calls"][-1]["stimmung_input"]["stability"], "stable")

        user_messages = [
            message
            for message in result["durable"]["messages"]
            if message.get("role") == "user"
        ]
        self.assertEqual(len(user_messages), 4)
        self.assertEqual(
            [message["meta"]["affective_turn_signal"] for message in user_messages],
            [signal] * 4,
        )
        self.assertEqual(len(result["durable_snapshots"]), 4)
        self.assertEqual(result["stored_message_row_count"], 9)

    def test_json_and_stream_share_the_same_store_fake_signal_history_without_duplication(self) -> None:
        signals = [
            affective_signal("curiosite", 5),
            affective_signal("curiosite", 6),
            affective_signal("curiosite", 7),
            affective_signal("curiosite", 8),
        ]
        json_result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(signal) for signal in signals],
            stream=False,
        )
        stream_result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(signal) for signal in signals],
            stream=True,
        )

        def persisted_signal_history(result):
            return [
                message["meta"]["affective_turn_signal"]
                for message in result["durable"]["messages"]
                if message.get("role") == "user"
            ]

        self.assertEqual(persisted_signal_history(json_result), signals)
        self.assertEqual(persisted_signal_history(stream_result), signals)
        self.assertEqual(json_result["node_calls"][-1]["stimmung_input"], stream_result["node_calls"][-1]["stimmung_input"])
        json_projection = _validation_projection(
            {"user_content": json_result["validation_messages"][-1][1]["content"]}
        )
        stream_projection = _validation_projection(
            {"user_content": stream_result["validation_messages"][-1][1]["content"]}
        )
        self.assertEqual(json_projection, stream_projection)
        _assert_full_projected_stimmung(
            json_projection,
            json_result["node_calls"][-1]["stimmung_input"],
        )
        self.assertTrue(
            all(response["terminal"]["event"] == "done" for response in stream_result["responses"])
        )
        self.assertEqual(len(json_result["base_observed"]["save_calls"]), 4)
        self.assertEqual(len(stream_result["base_observed"]["save_calls"]), 4)

    def test_multi_turn_corpus_observes_shift_alternation_neutral_return_and_invalid_middle(self) -> None:
        transition = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                *[primary_signal(affective_signal("apaisement", 7)) for _ in range(3)],
                *[primary_signal(affective_signal("colere", 9)) for _ in range(3)],
            ],
        )
        self.assertEqual(transition["node_calls"][2]["stimmung_input"]["stability"], "stable")
        self.assertEqual(transition["node_calls"][3]["stimmung_input"]["stability"], "volatile")
        self.assertEqual(transition["node_calls"][3]["stimmung_input"]["turns_considered"], 4)

        reversed_transition = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                primary_signal(affective_signal("colere", 9)),
                *[primary_signal(affective_signal("apaisement", 7)) for _ in range(3)],
            ],
        )
        self.assertNotEqual(
            transition["node_calls"][3]["stimmung_input"],
            reversed_transition["node_calls"][-1]["stimmung_input"],
        )
        self.assertEqual(
            reversed_transition["node_calls"][-1]["stimmung_input"]["dominant_tone"],
            "apaisement",
        )

        alternation = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                primary_signal(affective_signal("apaisement", 7)),
                primary_signal(affective_signal("colere", 9)),
                primary_signal(affective_signal("apaisement", 7)),
                primary_signal(affective_signal("colere", 9)),
            ],
        )
        alternating_states = [call["stimmung_input"] for call in alternation["node_calls"]]
        self.assertTrue(any(item["stability"] == "volatile" for item in alternating_states))
        self.assertTrue(any(item["shift_state"] == "candidate_shift" for item in alternating_states))
        self.assertFalse(
            alternating_states[-1]["stability"] == "stable"
            and alternating_states[-1]["shift_state"] == "steady"
        )

        neutral_return = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                *[primary_signal(affective_signal("colere", 9)) for _ in range(3)],
                primary_signal(affective_signal("neutralite", 5)),
                primary_signal(affective_signal("neutralite", 7)),
                primary_signal(affective_signal("neutralite", 9)),
            ],
        )
        self.assertEqual(neutral_return["node_calls"][3]["stimmung_input"]["stability"], "volatile")
        self.assertEqual(neutral_return["node_calls"][-1]["stimmung_input"]["dominant_tone"], "neutralite")
        self.assertEqual(neutral_return["node_calls"][-1]["stimmung_input"]["stability"], "emerging")

        invalid_middle = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(affective_signal("apaisement", 7)) for _ in range(5)],
            corrupt_signal_after_turns=[3],
        )
        self.assertEqual(invalid_middle["node_calls"][3]["stimmung_input"]["turns_considered"], 3)
        self.assertNotIn(
            "lot4_invalid",
            json.dumps(invalid_middle["node_calls"][3]["stimmung_input"], sort_keys=True),
        )

        invalid_latest = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(affective_signal("apaisement", 7)) for _ in range(4)],
            corrupt_signal_after_turns=[4],
        )
        rebuilt = canonical_stimmung_input.build_stimmung_input(
            messages=invalid_latest["durable"]["messages"]
        )
        self.assertFalse(rebuilt["present"])
        self.assertEqual(rebuilt["turns_considered"], 0)

    def test_stable_signal_is_inert_but_shift_makes_the_primary_regime_cautious(self) -> None:
        common = _strong_regime_inputs()
        absent = {
            "schema_version": "v1",
            "present": False,
            "dominant_tone": None,
            "active_tones": [],
            "stability": "",
            "shift_state": "",
            "turns_considered": 0,
        }
        stable = {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "apaisement",
            "active_tones": [{"tone": "apaisement", "strength": 7}],
            "stability": "stable",
            "shift_state": "steady",
            "turns_considered": 4,
        }
        volatile = {
            **stable,
            "dominant_tone": "colere",
            "active_tones": [{"tone": "colere", "strength": 9}],
            "stability": "volatile",
            "shift_state": "candidate_shift",
        }

        absent_regime = epistemic_regime.build_epistemic_regime(**common, stimmung_input=absent)
        stable_regime = epistemic_regime.build_epistemic_regime(**common, stimmung_input=stable)
        volatile_regime = epistemic_regime.build_epistemic_regime(**common, stimmung_input=volatile)

        self.assertEqual(absent_regime, stable_regime)
        self.assertEqual(
            stable_regime,
            {
                "epistemic_regime": "certain",
                "proof_regime": "suffisant_en_l_etat",
                "uncertainty_posture": "discrete",
            },
        )
        self.assertEqual(
            volatile_regime,
            {
                "epistemic_regime": "probable",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "prudente",
            },
        )

    def test_stimmung_does_not_create_presence_clarify_suspend_or_override_hard_guards(self) -> None:
        user_turn = {
            "schema_version": "v1",
            "geste_dialogique_dominant": "exposition",
            "regime_probatoire": {
                "principe": "maximal_possible",
                "types_de_preuve_attendus": [],
                "provenances": [],
                "regime_de_vigilance": "standard",
                "composition_probatoire": "isolee",
            },
            "qualification_temporelle": {
                "portee_temporelle": "atemporale",
                "ancrage_temporel": "non_ancre",
            },
        }
        signals = {
            "present": True,
            "ambiguity_present": False,
            "underdetermination_present": False,
            "active_signal_families": [],
            "active_signal_families_count": 0,
        }
        volatile = {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "colere",
            "active_tones": [{"tone": "colere", "strength": 9}],
            "stability": "volatile",
            "shift_state": "candidate_shift",
            "turns_considered": 4,
        }
        primary = primary_node.build_primary_node(
            conversation_id="conv-lot4-primary",
            updated_at="2026-08-28T09:00:00Z",
            time_input={
                "schema_version": "v1",
                "now_utc_iso": "2026-08-28T09:00:00Z",
                "timezone": "UTC",
                "now_local_iso": "2026-08-28T09:00:00+00:00",
                "local_date": "2026-08-28",
                "local_time": "09:00",
                "local_weekday": "friday",
                "day_part_class": "morning",
                "day_part_human": "matin",
            },
            user_turn_input=user_turn,
            user_turn_signals=signals,
            stimmung_input=volatile,
            web_input={
                "schema_version": "v1",
                "enabled": True,
                "status": "skipped",
                "reason_code": None,
                "original_user_message": "",
                "query": None,
                "results_count": 0,
                "runtime": {},
                "sources": [],
                "context_block": "",
            },
        )["primary_verdict"]
        self.assertFalse(primary["audit"]["fail_open"], primary)
        self.assertEqual(primary["judgment_posture"], "answer")
        self.assertEqual(primary["discursive_regime"], "simple")
        self.assertNotIn(primary["judgment_posture"], {"clarify", "suspend"})
        self.assertNotEqual(primary["discursive_regime"], "presence")

        guard_primary = dict(primary, proof_regime="verification_externe_requise")
        canonical = {"web_input": {"status": "error", "sources": []}, "stimmung_input": volatile}
        guarded = hard_guards.evaluate_hard_guards(
            primary_verdict=guard_primary,
            canonical_inputs=canonical,
        )
        unguarded_stimmung = hard_guards.evaluate_hard_guards(
            primary_verdict=guard_primary,
            canonical_inputs={"web_input": canonical["web_input"]},
        )
        self.assertEqual(guarded, unguarded_stimmung)
        self.assertTrue(guarded.answer_forbidden)
        self.assertEqual(guarded.allowed_postures, ("clarify", "suspend"))

    def test_validation_capture_preserves_complete_stimmung_independent_of_neighbor_volume_and_names(self) -> None:
        stimmung = {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "apaisement",
            "active_tones": [{"tone": "apaisement", "strength": 7}],
            "stability": "stable",
            "shift_state": "steady",
            "turns_considered": 4,
        }

        small = _validation_projection(capture_validation_request({"stimmung_input": stimmung}))
        near_bound = _validation_projection(
            capture_validation_request({"aaa_padding": "x" * 520, "stimmung_input": stimmung})
        )
        beyond_bound = _validation_projection(
            capture_validation_request({"aaa_padding": "x" * 800, "stimmung_input": stimmung})
        )
        renamed_neighbor = _validation_projection(
            capture_validation_request({"zzz_padding": "x" * 800, "stimmung_input": stimmung})
        )

        for projection in (small, near_bound, beyond_bound, renamed_neighbor):
            _assert_full_projected_stimmung(projection, stimmung)
            self.assertEqual(projection["projection_version"], "validation_canonical_inputs_v1")
            self.assertEqual(
                projection["stimmung_delivery"],
                {"status": "full", "reason_code": "included"},
            )
            self.assertEqual(projection["families"]["stimmung_input"], stimmung)
            self.assertLessEqual(
                len(json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
                validation_agent.MAX_CANONICAL_INPUTS_JSON_CHARS,
            )
            self.assertNotIn("preview", projection)
            self.assertNotIn("truncated", projection)
        self.assertEqual(near_bound, beyond_bound)
        self.assertEqual(beyond_bound, renamed_neighbor)

        suppressed_mutant = copy.deepcopy(beyond_bound)
        del suppressed_mutant["families"]["stimmung_input"]
        with self.assertRaises((AssertionError, ValueError)):
            _assert_full_projected_stimmung(suppressed_mutant, stimmung)

        duplicated_mutant = copy.deepcopy(beyond_bound)
        duplicated_mutant["omitted_families"].append("stimmung_input")
        with self.assertRaises((AssertionError, ValueError)):
            _assert_full_projected_stimmung(duplicated_mutant, stimmung)

        displaced_mutant = copy.deepcopy(beyond_bound)
        displaced_mutant["stimmung_input"] = displaced_mutant["families"].pop("stimmung_input")
        with self.assertRaises((AssertionError, ValueError)):
            _assert_full_projected_stimmung(displaced_mutant, stimmung)

        lexical_prefix_mutant = {"truncated": True, "preview": json.dumps(beyond_bound)[:500]}
        with self.assertRaises((AssertionError, ValueError)):
            _assert_full_projected_stimmung(lexical_prefix_mutant, stimmung)

        inverted_priority_mutant = copy.deepcopy(beyond_bound)
        inverted_priority_mutant["families"] = {"time_input": {"schema_version": "v1"}}
        inverted_priority_mutant["omitted_families"] = ["stimmung_input"]
        inverted_priority_mutant["stimmung_delivery"] = {
            "status": "absent",
            "reason_code": "contract_budget_exceeded",
        }
        with self.assertRaises((AssertionError, ValueError)):
            _assert_full_projected_stimmung(inverted_priority_mutant, stimmung)

        partial_mutant = copy.deepcopy(beyond_bound)
        partial_mutant["stimmung_delivery"]["status"] = "partial"
        with self.assertRaises((AssertionError, ValueError)):
            _assert_full_projected_stimmung(partial_mutant, stimmung)

        transverse = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(affective_signal("apaisement", 7)) for _ in range(4)],
        )
        prepared = [
            event
            for event in transverse["events"]
            if event.get("stage") == "validation_prompt_prepared"
        ][-1]
        prepared_payload = prepared["payload_json"]
        self.assertEqual(prepared_payload["canonical_projection_version"], "validation_canonical_inputs_v1")
        self.assertEqual(prepared_payload["stimmung_delivery_status"], "full")
        self.assertEqual(prepared_payload["stimmung_delivery_reason_code"], "included")
        self.assertLessEqual(
            prepared_payload["canonical_projection_chars"],
            prepared_payload["canonical_projection_budget_chars"],
        )
        actual_projection = _validation_projection(
            {"user_content": transverse["validation_messages"][-1][1]["content"]}
        )
        self.assertEqual(actual_projection["stimmung_delivery"]["status"], "full")
        self.assertIn("stimmung_input", actual_projection["families"])

    def test_main_model_receives_only_derived_judgment_and_can_lose_the_causal_difference(self) -> None:
        stable = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(affective_signal("apaisement", 7)) for _ in range(4)],
        )
        transition = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                *[primary_signal(affective_signal("apaisement", 7)) for _ in range(3)],
                primary_signal(affective_signal("colere", 9)),
            ],
        )
        stable_primary = stable["node_calls"][-1]["primary_payload"]["primary_verdict"]
        transition_primary = transition["node_calls"][-1]["primary_payload"]["primary_verdict"]
        self.assertNotEqual(
            stable_primary["uncertainty_posture"],
            transition_primary["uncertainty_posture"],
        )

        stable_main = json.dumps(stable["main_messages"][-1], sort_keys=True)
        transition_main = json.dumps(transition["main_messages"][-1], sort_keys=True)
        for serialized in (stable_main, transition_main):
            self.assertIn("[JUGEMENT HERMENEUTIQUE]", serialized)
            self.assertIn("Posture finale validee", serialized)
            self.assertNotIn("stimmung_input", serialized)
            self.assertNotIn("active_tones", serialized)
            self.assertNotIn("dominant_tone", serialized)
            self.assertNotIn("apaisement", serialized)
            self.assertNotIn("colere", serialized)
        stable_block = [
            item["content"]
            for item in stable["main_messages"][-1]
            if item["role"] == "system" and "[JUGEMENT HERMENEUTIQUE]" in item["content"]
        ][0]
        transition_block = [
            item["content"]
            for item in transition["main_messages"][-1]
            if item["role"] == "system" and "[JUGEMENT HERMENEUTIQUE]" in item["content"]
        ][0]
        self.assertEqual(stable_block, transition_block)
        self.assertEqual(
            [call["model"] for call in stable["provider_calls"] if call["model"] == MAIN_MODEL],
            [MAIN_MODEL] * 4,
        )

    def test_primary_fallback_and_fail_open_provenance_remain_distinct(self) -> None:
        fallback = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                primary_signal(affective_signal("apaisement", 7)),
                fallback_signal(affective_signal("colere", 8)),
                double_failure(),
                primary_signal(affective_signal("neutralite", 6)),
            ],
        )
        events = fallback["caller_events"]
        self.assertEqual(
            [event["payload_json"]["decision_source"] for event in events],
            ["primary", "fallback", "fail_open", "primary"],
        )
        self.assertEqual(
            [event["payload_json"]["model"] for event in events],
            [STIMMUNG_PRIMARY_MODEL, STIMMUNG_FALLBACK_MODEL, STIMMUNG_FALLBACK_MODEL, STIMMUNG_PRIMARY_MODEL],
        )
        self.assertEqual([event["status"] for event in events], ["ok", "ok", "error", "ok"])
        self.assertFalse(events[2]["payload_json"]["present"])
        self.assertEqual(fallback["node_calls"][2]["stimmung_input"]["present"], False)
        self.assertEqual(len(fallback["base_observed"]["save_calls"]), 4)
        self.assertTrue(
            all(call["validated_output"].get("final_output_regime") != "presence" for call in fallback["node_calls"])
        )

        absent = exercise_stimmung_dialogue(
            self.server,
            outcomes=[double_failure() for _ in range(4)],
        )
        self.assertTrue(all(not call["stimmung_input"]["present"] for call in absent["node_calls"]))
        self.assertTrue(all(event["status"] == "error" for event in absent["caller_events"]))
        self.assertTrue(
            all(event["payload_json"]["decision_source"] == "fail_open" for event in absent["caller_events"])
        )

    def test_persistence_and_aggregation_assertions_reject_controlled_mutations(self) -> None:
        signals = [
            affective_signal("curiosite", 5),
            affective_signal("apaisement", 6),
            affective_signal("frustration", 7),
            affective_signal("colere", 8),
            affective_signal("anxiete", 9),
        ]
        result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(signal) for signal in signals],
        )

        _assert_persistent_signal_history(result["durable"], signals)
        removed = copy.deepcopy(result["durable"])
        [message for message in removed["messages"] if message.get("role") == "user"][1]["meta"].pop(
            "affective_turn_signal"
        )
        with self.assertRaises(AssertionError):
            _assert_persistent_signal_history(removed, signals)

        duplicated = copy.deepcopy(result["durable"])
        duplicated["messages"].append(
            copy.deepcopy([message for message in duplicated["messages"] if message.get("role") == "user"][2])
        )
        with self.assertRaises(AssertionError):
            _assert_persistent_signal_history(duplicated, signals)

        reversed_history = copy.deepcopy(result["durable"])
        reversed_users = [message for message in reversed_history["messages"] if message.get("role") == "user"]
        reversed_signals = list(reversed([message["meta"]["affective_turn_signal"] for message in reversed_users]))
        for message, signal in zip(reversed_users, reversed_signals):
            message["meta"]["affective_turn_signal"] = signal
        with self.assertRaises(AssertionError):
            _assert_persistent_signal_history(reversed_history, signals)

        expected_aggregate = result["node_calls"][-1]["stimmung_input"]
        _assert_four_turn_aggregate(expected_aggregate)
        self.assertEqual(
            canonical_stimmung_input.extract_recent_affective_turn_signals(
                messages=result["durable"]["messages"]
            ),
            signals[-4:],
        )
        fifth_retained = dict(expected_aggregate, turns_considered=5)
        with self.assertRaises(AssertionError):
            _assert_four_turn_aggregate(fifth_retained)

        stable_result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[primary_signal(affective_signal("apaisement", 7)) for _ in range(4)],
        )
        stable_aggregate = stable_result["node_calls"][-1]["stimmung_input"]
        _assert_stable_aggregate(stable_aggregate)
        stable_as_volatile = dict(stable_aggregate, stability="volatile")
        with self.assertRaises(AssertionError):
            _assert_stable_aggregate(stable_as_volatile)

        transition_result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                *[primary_signal(affective_signal("apaisement", 7)) for _ in range(3)],
                primary_signal(affective_signal("colere", 9)),
            ],
        )
        transition_aggregate = transition_result["node_calls"][-1]["stimmung_input"]
        _assert_transition_aggregate(transition_aggregate)
        transition_ignored = dict(transition_aggregate, stability="stable", shift_state="steady")
        with self.assertRaises(AssertionError):
            _assert_transition_aggregate(transition_ignored)

        duplicated_reload = copy.deepcopy(result["repeated_reloads"][0])
        duplicated_reload["messages"].append(copy.deepcopy(duplicated_reload["messages"][-1]))
        with self.assertRaises(AssertionError):
            _assert_persistent_signal_history(duplicated_reload, signals)

    def test_downstream_assertions_reject_controlled_provenance_and_payload_mutations(self) -> None:
        stimmung = {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "apaisement",
            "active_tones": [{"tone": "apaisement", "strength": 7}],
            "stability": "stable",
            "shift_state": "steady",
            "turns_considered": 4,
        }
        absent_stimmung = {
            **stimmung,
            "present": False,
            "dominant_tone": None,
            "active_tones": [],
            "stability": "",
            "shift_state": "",
            "turns_considered": 0,
        }
        transition_stimmung = {
            **stimmung,
            "dominant_tone": "colere",
            "active_tones": [{"tone": "colere", "strength": 9}],
            "stability": "volatile",
            "shift_state": "candidate_shift",
        }
        absent_regime = epistemic_regime.build_epistemic_regime(
            **_strong_regime_inputs(),
            stimmung_input=absent_stimmung,
        )
        stable_regime = epistemic_regime.build_epistemic_regime(
            **_strong_regime_inputs(),
            stimmung_input=stimmung,
        )
        transition_regime = epistemic_regime.build_epistemic_regime(
            **_strong_regime_inputs(),
            stimmung_input=transition_stimmung,
        )
        _assert_absent_stable_transition_regimes(absent_regime, stable_regime, transition_regime)
        stable_caution_mutant = {
            "epistemic_regime": "probable",
            "proof_regime": "source_explicite_requise",
            "uncertainty_posture": "prudente",
        }
        with self.assertRaises(AssertionError):
            _assert_absent_stable_transition_regimes(
                absent_regime,
                stable_caution_mutant,
                transition_regime,
            )

        retained_capture = capture_validation_request(
            {"aaa_padding": "x" * 800, "stimmung_input": stimmung}
        )
        _assert_validation_reception_claim(retained_capture, True)
        with self.assertRaises(AssertionError):
            _assert_validation_reception_claim(retained_capture, False)

        result = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                primary_signal(affective_signal("apaisement", 7)),
                fallback_signal(affective_signal("colere", 8)),
                double_failure(),
                primary_signal(affective_signal("neutralite", 6)),
            ],
        )
        main_payload = copy.deepcopy(result["main_messages"][-1])

        _assert_main_payload_is_derived_only(main_payload)
        main_payload.append({"role": "system", "content": json.dumps({"stimmung_input": stimmung})})
        with self.assertRaises(AssertionError):
            _assert_main_payload_is_derived_only(main_payload)

        _assert_caller_provenance(result["caller_events"])
        fallback_mutant = copy.deepcopy(result["caller_events"])
        fallback_mutant[1]["payload_json"]["decision_source"] = "primary"
        with self.assertRaises(AssertionError):
            _assert_caller_provenance(fallback_mutant)

        fail_open_mutant = copy.deepcopy(result["caller_events"])
        fail_open_mutant[2]["status"] = "ok"
        fail_open_mutant[2]["payload_json"]["decision_source"] = "primary"
        fail_open_mutant[2]["payload_json"]["present"] = True
        with self.assertRaises(AssertionError):
            _assert_caller_provenance(fail_open_mutant)


if __name__ == "__main__":
    unittest.main()
