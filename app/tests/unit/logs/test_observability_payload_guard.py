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


if __name__ == "__main__":
    unittest.main()
