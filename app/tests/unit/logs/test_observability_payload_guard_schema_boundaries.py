from __future__ import annotations

import unittest

from observability import observability_payload_guard
from observability import observability_payload_guard_manifest_schema
from observability import observability_payload_guard_safe_code_policy
from observability import observability_payload_guard_stage_schema


class ObservabilityPayloadGuardSchemaBoundariesTests(unittest.TestCase):
    def test_safe_code_policy_preserves_tokenlike_default_deny(self) -> None:
        policy = observability_payload_guard_safe_code_policy

        self.assertTrue(policy._is_safe_code_text("provider_timeout"))
        self.assertTrue(
            policy._is_safe_code_text(
                "openai/gpt-5.4-mini",
                allow_model=True,
            )
        )
        self.assertFalse(policy._is_safe_code_text("sk-synthetic123456"))
        self.assertEqual(
            policy._dangerous_value_class("reason_code", "xoxb-synthetic123"),
            "token_like_value",
        )
        self.assertEqual(policy._dangerous_key_class("message"), "message_key")
        self.assertEqual(policy._dangerous_key_class("raw_content_included"), "")

    def test_manifest_rules_remain_context_scoped_and_default_deny(self) -> None:
        schema = observability_payload_guard_manifest_schema

        self.assertTrue(
            schema._is_main_payload_manifest(
                {"schema_version": "main_payload_manifest_v1"}
            )
        )
        self.assertIn("lane_statuses", schema._manifest_allowed_keys("top"))
        self.assertNotIn("private_sentence", schema._manifest_allowed_keys("top"))
        self.assertIn(
            "retrieval_reason_code",
            schema._manifest_allowed_keys("window:memory"),
        )
        self.assertNotIn(
            "retrieval_reason_code",
            schema._manifest_allowed_keys("window:agenda_recent_dialogue"),
        )
        self.assertEqual(
            schema._manifest_child_context("windows", "memory"),
            "window:memory",
        )

    def test_stage_schema_allowlists_remain_bounded_and_default_deny(self) -> None:
        schema = observability_payload_guard_stage_schema

        self.assertTrue(schema._is_safe_general_text_key("reason_code"))
        self.assertFalse(schema._is_safe_general_text_key("private_sentence"))
        self.assertTrue(
            schema._is_safe_general_text_value("provider_model", "openai/gpt-5.4-mini")
        )
        self.assertFalse(
            schema._is_safe_general_text_value("reason_code", "sk-synthetic123456")
        )
        self.assertTrue(schema._is_safe_general_scalar_key("candidate_count"))
        self.assertTrue(schema._is_safe_general_container_key("reason_code_counts"))
        self.assertFalse(schema._is_safe_general_container_key("private_sentence"))

    def test_guard_payload_remains_the_only_complete_validation_entrypoint(self) -> None:
        modules = (
            observability_payload_guard,
            observability_payload_guard_manifest_schema,
            observability_payload_guard_safe_code_policy,
            observability_payload_guard_stage_schema,
        )

        self.assertEqual(
            [module.__name__ for module in modules if hasattr(module, "guard_payload")],
            ["observability.observability_payload_guard"],
        )

        policy_modules = modules[1:]
        policy_prefixes = (
            "_DANGEROUS_",
            "_GENERAL_",
            "_MANIFEST_",
            "_QUALIFIED_",
            "_SAFE_",
            "_TOKEN_LIKE_",
        )
        policy_names = {
            name
            for module in policy_modules
            for name in vars(module)
            if name.startswith(policy_prefixes)
        }
        for name in policy_names:
            with self.subTest(policy_name=name):
                self.assertEqual(
                    sum(name in vars(module) for module in policy_modules),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
