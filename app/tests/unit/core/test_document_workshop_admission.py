from __future__ import annotations

import copy
import importlib
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import llm_client, token_utils
from tests.unit.core.test_document_workshop_canonical_paths import canonical


class DocumentAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("core.document_workshop_admission"), "M0 admission interface absent")
        self.module = importlib.import_module("core.document_workshop_admission")
        self.error = importlib.import_module("core.document_workshop_contract").DocumentWorkshopError
        self.view = SimpleNamespace(payload={
            "model": {"value": "openai/gpt-5.1"},
            "reasoning_effort": {"value": "medium"},
            "base_url": {"value": "https://provider.invalid/api/v1/"},
        })
        self.settings_patch = patch.object(llm_client.runtime_settings, "get_main_model_settings", return_value=self.view)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.headers_patch = patch.object(llm_client, "or_headers", return_value={"Authorization": "synthetic", "Content-Type": "application/json"})
        self.headers = self.headers_patch.start()
        self.addCleanup(self.headers_patch.stop)

    def prepare(self, messages=None, counter=token_utils.estimate_tokens, **kwargs):
        return self.module.prepare_document_call(
            messages or [{"role": "system", "content": "Instruction documentaire synthétique"}, {"role": "user", "content": "Demande synthétique"}],
            count_tokens_func=counter, **kwargs,
        )

    def test_exact_estimated_threshold_and_output_reservation(self):
        call = self.prepare(counter=lambda messages, model: 376000)
        self.assertEqual(call.admission.estimated_input_tokens, 376000)
        self.assertEqual(call.admission.estimated_total_tokens, 400000)
        for estimate in (376001, 400000):
            with self.assertRaises(self.error) as raised:
                self.prepare(counter=lambda messages, model: estimate)
            self.assertEqual(raised.exception.reason_code, "document_estimated_context_limit")
        self.assertEqual(self.headers.call_count, 1)

    def test_counter_error_invalid_unavailable_and_mutation_fail_closed(self):
        for counter in (None, lambda *_: None, lambda *_: True, lambda *_: -1, lambda *_: 0, lambda *_: "1", lambda *_: 1.5):
            with self.subTest(kind=type(counter).__name__):
                with self.assertRaises(self.error) as raised:
                    self.prepare(counter=counter)
                self.assertEqual(raised.exception.reason_code, "document_estimation_unavailable")
        def broken(*_):
            raise RuntimeError("synthetic private exception must never escape")
        with self.assertRaises(self.error) as raised:
            self.prepare(counter=broken)
        self.assertEqual(str(raised.exception), "document_estimation_unavailable")
        def mutating(messages, model):
            messages.clear()
            return 1
        with self.assertRaises(self.error) as raised:
            self.prepare(counter=mutating)
        self.assertEqual(raised.exception.reason_code, "document_estimation_input_mutated")
        self.headers.assert_not_called()

    def test_complete_messages_counted_with_real_shared_callable(self):
        messages = [
            {"role": "system", "content": "Prompt documentaire synthétique"},
            {"role": "user", "content": "Dialogue entier, e\u0301 𐐀,   espaces !!!"},
            {"role": "assistant", "content": "Réponse antérieure synthétique"},
            {"role": "user", "content": json.dumps({"source_pages": 35, "source_text": "source entière " * 200, "source_version": "v1"}, ensure_ascii=False)},
            {"role": "system", "content": json.dumps({"selected_folder": "synthetic", "metadata": {"version": 2}})},
        ]
        original = copy.deepcopy(messages)
        measured = []
        def shared(messages, model):
            measured.append((copy.deepcopy(messages), model))
            return token_utils.estimate_tokens(messages, model)
        call = self.prepare(messages=messages, counter=shared)
        transmitted = json.loads(call.body)
        self.assertEqual(transmitted["messages"][:5], original)
        self.assertIn("schema_version", transmitted["messages"][-1]["content"])
        self.assertEqual(measured, [(transmitted["messages"], "openai/gpt-5.1")])
        self.assertEqual(call.admission.estimated_input_tokens, token_utils.estimate_tokens(transmitted["messages"], "openai/gpt-5.1"))
        self.assertEqual(transmitted["max_tokens"], 24000)
        self.assertEqual(transmitted["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(transmitted["provider"], {"allow_fallbacks": False})
        self.assertEqual(transmitted["metadata"]["frida_slot"], "main_model")
        self.assertEqual(call.url, "https://provider.invalid/api/v1/chat/completions")
        self.assertNotIn("synthetic", repr(call))
        # Source pages are informational; no output page guard runs on sources.
        messages[-2]["content"] = "replacement " * 200000
        self.assertEqual(json.loads(call.body)["messages"][:5], original)

    def test_new_sources_and_metadata_change_estimate_and_can_refuse(self):
        small = self.prepare().admission.estimated_input_tokens
        for content in ("source " * 3000, json.dumps({"metadata": "version " * 3000})):
            extended = [{"role": "user", "content": "Demande"}, {"role": "system", "content": content}]
            self.assertGreater(self.prepare(messages=extended).admission.estimated_input_tokens, small)
        with self.assertRaises(self.error) as raised:
            self.prepare(messages=[{"role": "user", "content": "source " * 300000}])
        self.assertEqual(raised.exception.reason_code, "document_estimated_context_limit")

    def test_adversarial_unicode_spaces_and_punctuation_follow_shared_estimate(self):
        for text in (" " * 1000, "!" * 1000, "é e\u0301 𐐀 👨\u200d👩" * 1000):
            call = self.prepare(messages=[{"role": "user", "content": text}])
            payload = json.loads(call.body)
            self.assertEqual(call.admission.estimated_input_tokens, token_utils.estimate_tokens(payload["messages"], payload["model"]))
            self.assertEqual(payload["messages"][0]["content"], text)

    def test_model_outside_contract_is_not_replaced_and_secrets_not_resolved(self):
        self.view.payload["model"]["value"] = "openai/another-model"
        with self.assertRaises(self.error) as raised:
            self.prepare()
        self.assertEqual(raised.exception.reason_code, "document_model_outside_contract")
        self.headers.assert_not_called()

    def test_normal_builder_preserves_default_and_legitimate_override(self):
        from admin import runtime_settings
        # Exercise the actual provider constructor with the normal/default value
        # and a legitimate non-default budget; no global budget rewrite.
        default = runtime_settings.build_env_seed_bundle("main_model").payload["response_max_tokens"]["value"]
        self.assertEqual(default, 8192)
        for max_tokens in (default, 12345):
            payload = llm_client.build_payload([{"role": "user", "content": "synthetic"}], 0.7, 1.0, max_tokens)
            self.assertEqual(payload["max_tokens"], max_tokens)
            self.assertEqual(payload["reasoning"], {"effort": "medium", "exclude": True})

    def test_textual_response_schema_outside_messages_has_explicit_estimate_adapter(self):
        original = llm_client.build_payload
        outside = {"type": "json_schema", "json_schema": {"name": "synthetic", "schema": {"description": "complete schema instructions " * 100}}}
        def builder(*args, **kwargs):
            return {**original(*args, **kwargs), "response_format": outside}
        seen = []
        def counter(messages, model):
            seen.extend(copy.deepcopy(messages))
            return token_utils.estimate_tokens(messages, model)
        with patch.object(llm_client, "build_payload", side_effect=builder):
            call = self.prepare(counter=counter)
        payload = json.loads(call.body)
        self.assertEqual(seen[:-1], payload["messages"])
        self.assertEqual(json.loads(seen[-1]["content"]), outside)
        self.assertEqual(call.admission.estimated_input_tokens, token_utils.estimate_tokens(seen, payload["model"]))

    def test_hidden_extra_payload_or_multimodal_input_is_refused(self):
        with self.assertRaises(self.error):
            self.prepare(messages=[{"role": "user", "content": [{"type": "image_url"}]}])
        original = llm_client.build_payload
        with patch.object(llm_client, "build_payload", side_effect=lambda *args, **kwargs: {**original(*args, **kwargs), "tools": []}):
            with self.assertRaises(self.error) as raised:
                self.prepare()
        self.assertEqual(raised.exception.reason_code, "document_payload_invalid")
        with self.assertRaises(self.error) as raised:
            self.prepare(messages=[{"role": [], "content": "synthetic"}])
        self.assertEqual(raised.exception.reason_code, "document_payload_invalid")

    def test_one_complete_envelope_schema_is_counted_before_send(self):
        from core.document_canonical import CANONICAL_INSTRUCTIONS
        call = self.prepare(messages=[{"role": "user", "content": "Préparer un document synthétique."}])
        messages = json.loads(call.body)["messages"]
        self.assertEqual(len(messages), 2)
        instructions = messages[-1]["content"]
        self.assertIn('status', instructions)
        self.assertIn('surface_text', instructions)
        self.assertIn('proposal', instructions)
        self.assertIn('prepared', instructions)
        self.assertIn('clarify', instructions)
        self.assertIn('refuse', instructions)
        self.assertIn('canonical', instructions)
        self.assertIn('page_break', instructions)
        self.assertNotIn(CANONICAL_INSTRUCTIONS, instructions)
        self.assertEqual(call.admission.estimated_input_tokens, token_utils.estimate_tokens(messages, "openai/gpt-5.1"))


if __name__ == "__main__":
    unittest.main()
