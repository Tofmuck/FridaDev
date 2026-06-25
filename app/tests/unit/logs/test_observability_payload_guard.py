from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from observability import admin_log_projection
from observability import main_payload_manifest
from observability import observability_payload_guard


def _encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _raw_flags() -> dict[str, bool]:
    return {
        "raw_prompt_included": False,
        "raw_message_included": False,
        "raw_content_included": False,
        "raw_lane_content_included": False,
        "raw_provider_payload_included": False,
        "raw_secret_included": False,
    }


class ObservabilityPayloadGuardTests(unittest.TestCase):
    def test_content_free_payload_passes(self) -> None:
        payload = {
            "status_schema_version": "agentic_v1",
            "reason_code": "not_selected",
            "content_chars": 42,
            "message_count": 2,
            "max_tokens": 512,
            "raw_prompt_included": False,
            "raw_provider_payload_included": False,
            "nested_counts": {"ok_count": 1},
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.payload["content_chars"], 42)

    def test_dangerous_keys_and_nested_values_are_rejected_content_free(self) -> None:
        sentinel = "SENSITIVE_WRITER_SENTINEL_A"
        payload = {
            "messages": [{"role": "user", "content": sentinel}],
            "safe_count": 1,
            "nested": {
                "provider_payload": {"text": sentinel},
                "reason_code": "https://provider.example.invalid/raw?token=abc",
                "image_data_url": "data:image/png;base64,AAAA",
            },
        }

        decision = observability_payload_guard.guard_payload(payload)
        projected, _redaction = admin_log_projection.project_payload(decision.payload)
        encoded = _encoded({"guard": decision.payload, "projected": projected})

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.payload["reason_code"], observability_payload_guard.REASON_CODE)
        self.assertIn("messages_key", decision.payload["issue_classes"])
        self.assertIn("provider_payload_key", decision.payload["issue_classes"])
        self.assertIn("image_data_url_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn("provider.example.invalid", encoded)
        self.assertNotIn("data:image", encoded)

    def test_dangerous_value_under_allowlisted_key_is_rejected(self) -> None:
        payload = {
            "reason_code": "https://logs.example.invalid/private",
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("url_value", decision.payload["issue_classes"])

    def test_agenda_allowlisted_fields_still_reject_sensitive_values(self) -> None:
        payload = {
            "schema_version": "frida_agenda_lot6_pending_v1",
            "status": "active_ready",
            "reason_code": "agenda_agent_active_validated",
            "agent": {
                "validation": {
                    "plan": {
                        "window_start": "https://calendar.example.invalid/private?token=abc",
                        "calendar_id_hashes": ["safehash12"],
                        "tool_names": ["event_query_range"],
                        "content_free": True,
                    }
                },
                "model": {
                    "content_hash": "BEGIN:VCALENDAR\nBEGIN:VEVENT",
                    "status_code": 200,
                },
            },
            "read_execution": {
                "calendar_id_hashes": ["/remote.php/dav/calendars/tof/private/"],
                "event_id_hashes": ["safeevent12"],
                "redacted": True,
                "content_free": True,
            },
            "pending_execution": {
                "target_verification_tool_names": ["event_query_range"],
                "target_verification_error_class": "RuntimeError",
                "write_execution": {},
                "redacted": True,
                "content_free": True,
            },
            "content_free": True,
        }

        decision = observability_payload_guard.guard_payload(payload)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("url_value", decision.payload["issue_classes"])
        self.assertIn("raw_text_value", decision.payload["issue_classes"])
        self.assertNotIn("calendar.example.invalid", encoded)
        self.assertNotIn("BEGIN:VCALENDAR", encoded)
        self.assertNotIn("/remote.php/dav", encoded)

    def test_context_build_content_free_payload_passes(self) -> None:
        payload = {
            "estimated_context_tokens": 42,
            "prompt_soft_token_limit": 4000,
            "prompt_soft_limit_exceeded": False,
            "dialogue_messages_truncated": False,
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.payload["estimated_context_tokens"], 42)

    def test_web_search_skipped_empty_query_preview_passes(self) -> None:
        payload = {
            "enabled": False,
            "query_preview": "",
            "results_count": 0,
            "context_injected": False,
            "truncated": False,
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.payload["query_preview"], "")

    def test_web_search_non_empty_query_preview_is_rejected(self) -> None:
        sentinel = "user query text sentinel should not pass"
        payload = {
            "enabled": True,
            "query_preview": sentinel,
            "results_count": 0,
            "context_injected": False,
            "truncated": False,
        }

        decision = observability_payload_guard.guard_payload(payload)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("unsafe_string_value", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)

    def test_error_code_and_class_pass_without_message_short(self) -> None:
        payload = {
            "error_code": "upstream_error",
            "error_class": "RuntimeError",
            "message_short_chars": 4,
            "message_short_included": False,
            "raw_error_message_included": False,
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.payload["error_class"], "RuntimeError")

    def test_direct_message_short_is_still_rejected(self) -> None:
        sentinel = "raw error detail should not pass"
        payload = {
            "error_code": "upstream_error",
            "error_class": "RuntimeError",
            "message_short": sentinel,
        }

        decision = observability_payload_guard.guard_payload(payload)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("unknown_string_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)

    def test_general_payload_rejects_neutral_free_text_key(self) -> None:
        sentinel = "neutral free text sentinel should not pass"
        payload = {
            "private_sentence": sentinel,
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("unknown_string_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn("private_sentence", encoded)

    def test_general_payload_rejects_unknown_safe_code_suffix_text_keys(self) -> None:
        for key in (
            "private_requested",
            "private_code",
            "private_reason",
            "private_status",
            "private_mode",
            "private_unknown",
        ):
            with self.subTest(key=key):
                decision = observability_payload_guard.guard_payload({key: "secret_codename"})
                encoded = _encoded(decision.payload)

                self.assertFalse(decision.accepted)
                self.assertIn("unknown_string_key", decision.payload["issue_classes"])
                self.assertNotIn("secret_codename", encoded)
                self.assertNotIn(key, encoded)

    def test_general_payload_rejects_unknown_mapping_and_list_keys(self) -> None:
        payload = {
            "status_schema_version": "agentic_v1",
            "innocent_box": {"ok_count": 1},
            "innocent_list": ["safe_code"],
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("unknown_mapping_key", decision.payload["issue_classes"])
        self.assertIn("unknown_list_key", decision.payload["issue_classes"])

    def test_prompt_prepared_content_free_payload_passes(self) -> None:
        payload = {
            "messages_count": 2,
            "estimated_prompt_tokens": 64,
            "memory_items_used": 0,
            "memory_prompt_injection": {
                "injected": False,
                "injection_class": "none",
                "injection_lanes": [],
                "injection_lane_count": 0,
                "prompt_block_count": 0,
                "trace_memory_injected": False,
                "trace_memory_injected_count": 0,
                "summary_context_injected": False,
                "summary_context_injected_count": 0,
                "memory_traces_injected": False,
                "memory_traces_injected_count": 0,
                "injected_candidate_ids": [],
                "memory_context_injected": False,
                "memory_context_summary_count": 0,
                "injected_traces_with_summary_id_count": 0,
                "injected_traces_with_parent_summary_count": 0,
                "parent_summaries_resolved_count": 0,
                "parent_summaries_injected_count": 0,
                "parent_summaries_injected": [],
                "context_hints_injected": False,
                "context_hints_injected_count": 0,
            },
            "identity_prompt_injection": {
                "injected": False,
                "identity_block_present": False,
                "identity_block_chars": 0,
                "identity_block_sha256_12": None,
                "used_identity_ids_count": 0,
                "staging_included": False,
                "subjects": {"llm": {"selected_count": 0}, "user": {"selected_count": 0}},
            },
            "hermeneutic_prompt_injection": {
                "present": True,
                "chars": 42,
                "fingerprint_present": False,
                "fingerprint_included": False,
                "prompt_block_hash_included": False,
                "raw_content_included": False,
                "final_judgment_posture": "answer",
                "final_output_regime": "simple",
                "epistemic_regime": "incertain",
                "directives_count": 2,
                "source": "primary",
                "fallback": False,
                "reason_code": "",
            },
            "memory_retrieval": {
                "status": "ok",
                "reason_code": "no_data",
                "top_k_requested": 5,
                "top_k_returned": 0,
            },
            "prompt_kind": "chat_system_augmented",
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertTrue(decision.accepted)

    def test_hermeneutic_node_insertion_content_free_payload_passes(self) -> None:
        payload = {
            "insertion_point_reached": True,
            "mode": "shadow",
            "inputs": {
                "time": {"present": True, "timezone": "Europe/Paris", "day_part_class": "morning"},
                "memory_retrieved": {"present": True, "status": "ok", "reason_code": "", "retrieved_count": 0},
                "memory_arbitration": {
                    "present": True,
                    "status": "skipped",
                    "reason_code": "no_data",
                    "decisions_count": 0,
                    "kept_count": 0,
                    "rejected_count": 0,
                },
                "summary": {"present": False, "status": "missing"},
                "identity": {
                    "present": True,
                    "frida": {"static_present": True, "mutable_present": False, "mutable_len": 0},
                    "user": {"static_present": False, "mutable_present": False, "mutable_len": 0},
                },
                "recent_context": {"present": True, "messages_count": 1},
                "recent_window": {"present": True, "turn_count": 1, "has_in_progress_turn": True},
                "user_turn": {
                    "present": True,
                    "geste_dialogique_dominant": "adresse_relationnelle",
                    "regime_probatoire": {
                        "principe": "maximal_possible",
                        "types_de_preuve_attendus": [],
                        "provenances": [],
                        "regime_de_vigilance": "standard",
                    },
                    "qualification_temporelle": {
                        "portee_temporelle": "atemporale",
                        "ancrage_temporel": "non_ancre",
                    },
                },
                "user_turn_signals": {"present": True, "active_signal_families": [], "active_signal_families_count": 0},
                "stimmung": {
                    "present": True,
                    "dominant_tone": "neutralite",
                    "active_tones": [{"tone": "neutralite", "strength": 3}],
                    "stability": "emerging",
                    "shift_state": "steady",
                    "turns_considered": 1,
                },
                "web": {
                    "present": True,
                    "enabled": True,
                    "status": "ok",
                    "activation_mode": "manual",
                    "results_count": 1,
                    "explicit_url_detected": True,
                    "explicit_url_chars": 28,
                    "explicit_url_included": False,
                    "source_material_summary": [
                        {
                            "rank": 1,
                            "source_domain": "example.com",
                            "source_origin": "explicit_url",
                            "is_primary_source": True,
                            "used_in_prompt": False,
                            "used_content_kind": "none",
                            "crawl_status": "empty",
                            "url_present": True,
                            "url_chars": 28,
                            "url_included": False,
                        }
                    ],
                },
            },
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertTrue(decision.accepted)

    def test_hermeneutic_node_insertion_raw_url_is_rejected(self) -> None:
        payload = {
            "insertion_point_reached": True,
            "mode": "shadow",
            "inputs": {"web": {"explicit_url": "https://example.invalid/private"}},
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("url_key", decision.payload["issue_classes"])

    def test_validation_and_stimmung_content_free_payloads_pass(self) -> None:
        validation_payload = {
            "dialogue_messages_count": 1,
            "dialogue_truncated": False,
            "current_user_retained": True,
            "last_assistant_retained": False,
            "upstream_recommendation_posture": "clarify",
            "upstream_output_regime_proposed": "meta",
            "upstream_active_signal_families": ["referent"],
            "upstream_constraint_present": False,
            "validation_decision": "challenge",
            "final_judgment_posture": "answer",
            "final_output_regime": "simple",
            "arbiter_followed_upstream": False,
            "advisory_recommendations_followed": [],
            "advisory_recommendations_overridden": ["upstream_recommendation_posture"],
            "applied_hard_guards": [],
            "arbiter_reason_present": True,
            "arbiter_reason_chars": 12,
            "arbiter_reason_included": False,
            "projected_judgment_posture": "answer",
            "pipeline_directives_final": ["posture_answer"],
            "decision_source": "primary",
            "model": "openai/gpt-5.4-mini",
            "status_schema_version": "agentic_v1",
        }
        stimmung_payload = {
            "present": True,
            "dominant_tone": "neutralite",
            "tones_count": 1,
            "tones": [{"tone": "neutralite", "strength": 3}],
            "confidence": 0.5,
            "decision_source": "fallback",
            "model": "openai/gpt-5.4-mini",
            "status_schema_version": "agentic_v1",
        }

        self.assertTrue(observability_payload_guard.guard_payload(validation_payload).accepted)
        self.assertTrue(observability_payload_guard.guard_payload(stimmung_payload).accepted)

    def test_raw_arbiter_reason_is_rejected(self) -> None:
        payload = {
            "arbiter_reason": "lecture libre a ne jamais stocker",
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("unknown_string_key", decision.payload["issue_classes"])

    def test_generic_sha256_12_is_rejected(self) -> None:
        payload = {
            "sha256_12": "0123456789ab",
            "status_schema_version": "agentic_v1",
        }

        decision = observability_payload_guard.guard_payload(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("unknown_string_key", decision.payload["issue_classes"])

    def test_valid_main_payload_manifest_passes_writer_guard(self) -> None:
        manifest = main_payload_manifest.build_main_payload_manifest(
            conversation={"id": "conv-guard", "messages": []},
            prompt_messages=[
                {"role": "system", "content": "SENSITIVE_PROMPT_NOT_IN_MANIFEST"},
                {"role": "user", "content": "SENSITIVE_USER_NOT_IN_MANIFEST"},
            ],
            runtime_main_model="openai/gpt-5.1",
            temperature=0.4,
            top_p=1.0,
            max_tokens=512,
            stream_req=False,
            assistant_output_policy=SimpleNamespace(allow_structure=False, allow_code=False),
            assistant_response_override=None,
            turn_id="turn-guard",
            count_tokens_func=lambda messages, _model: 10 * len(messages),
        )

        decision = observability_payload_guard.guard_payload(manifest)
        encoded = _encoded(decision.payload)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.payload["schema_version"], "main_payload_manifest_v1")
        self.assertNotIn("SENSITIVE_PROMPT_NOT_IN_MANIFEST", encoded)
        self.assertNotIn("SENSITIVE_USER_NOT_IN_MANIFEST", encoded)

    def test_manifest_with_raw_content_or_true_raw_flag_is_rejected(self) -> None:
        manifest = {
            "schema_version": "main_payload_manifest_v1",
            "scope": "main_chat",
            "messages": [
                {
                    "index": 0,
                    "provider_role": "user",
                    "logical_roles": ["user_turn"],
                    "origin": "current_user_turn",
                    "origin_stage": "final_user_turn",
                    "content": "SENSITIVE_RAW_CONTENT_B",
                    "raw_content_included": True,
                }
            ],
            "raw_flags": {"raw_content_included": True},
        }

        decision = observability_payload_guard.guard_payload(manifest)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("manifest_unexpected_key", decision.payload["issue_classes"])
        self.assertIn("raw_flag_true", decision.payload["issue_classes"])
        self.assertNotIn("SENSITIVE_RAW_CONTENT_B", encoded)

    def test_manifest_rejects_neutral_text_under_prompt_budget(self) -> None:
        sentinel = "neutral budget text sentinel should not pass"
        manifest = {
            "schema_version": "main_payload_manifest_v1",
            "scope": "main_chat",
            "budgets": {
                "prompt": {
                    "message_count": 1,
                    "content_chars_total": 42,
                    "estimated_prompt_tokens": 8,
                    "max_completion_tokens": 512,
                    "private_sentence": sentinel,
                }
            },
            "raw_flags": _raw_flags(),
        }

        decision = observability_payload_guard.guard_payload(manifest)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("manifest_unexpected_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)

    def test_manifest_rejects_neutral_text_under_windows(self) -> None:
        sentinel = "neutral window text sentinel should not pass"
        manifest = {
            "schema_version": "main_payload_manifest_v1",
            "scope": "main_chat",
            "windows": {
                "recent_context": {
                    "message_count": 2,
                    "private_sentence": sentinel,
                }
            },
            "raw_flags": _raw_flags(),
        }

        decision = observability_payload_guard.guard_payload(manifest)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("manifest_unexpected_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)

    def test_manifest_rejects_neutral_text_under_runtime_settings(self) -> None:
        sentinel = "neutral runtime text sentinel should not pass"
        manifest = {
            "schema_version": "main_payload_manifest_v1",
            "scope": "main_chat",
            "runtime_settings": {
                "provider_family": "openrouter",
                "model": "openai/gpt-5.1",
                "temperature_present": True,
                "top_p_present": True,
                "max_tokens": 512,
                "stream_requested": False,
                "private_sentence": sentinel,
            },
            "raw_flags": _raw_flags(),
        }

        decision = observability_payload_guard.guard_payload(manifest)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("manifest_unexpected_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)

    def test_manifest_rejects_raw_continuity_capsule_content(self) -> None:
        sentinel = "raw continuity capsule sentinel should not pass"
        manifest = {
            "schema_version": "main_payload_manifest_v1",
            "scope": "main_chat",
            "continuity_capsule": {
                "present": True,
                "enabled": True,
                "version": "continuity_capsule_v1",
                "status": "ok",
                "reason_code": "continuity_capsule_ready",
                "content_chars": len(sentinel),
                "max_chars": 900,
                "injected_count": 1,
                "content": sentinel,
                "raw_capsule_content_included": False,
                "raw_content_included": False,
                "raw_prompt_included": False,
                "fingerprint_included": False,
            },
            "raw_flags": _raw_flags(),
        }

        decision = observability_payload_guard.guard_payload(manifest)
        encoded = _encoded(decision.payload)

        self.assertFalse(decision.accepted)
        self.assertIn("manifest_unexpected_key", decision.payload["issue_classes"])
        self.assertNotIn(sentinel, encoded)


if __name__ == "__main__":
    unittest.main()
