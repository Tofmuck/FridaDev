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

from core import main_llm_reasoning


class MainLlmReasoningTests(unittest.TestCase):
    def test_supported_reasoning_efforts_are_gpt51_specific(self) -> None:
        self.assertEqual(
            main_llm_reasoning.SUPPORTED_REASONING_EFFORTS,
            ('none', 'low', 'medium', 'high'),
        )
        self.assertEqual(main_llm_reasoning.normalize_reasoning_effort('minimal'), 'high')
        self.assertEqual(main_llm_reasoning.normalize_reasoning_effort('xhigh'), 'high')

    def test_resolves_supported_gpt51_payload_with_hidden_reasoning(self) -> None:
        resolution = main_llm_reasoning.resolve_main_llm_reasoning(
            model='openai/gpt-5.1',
            runtime_payload={
                'reasoning_effort': {
                    'value': 'medium',
                },
            },
        )

        self.assertTrue(resolution.sent)
        self.assertEqual(
            main_llm_reasoning.reasoning_request_payload(resolution),
            {'effort': 'medium', 'exclude': True},
        )
        self.assertEqual(
            main_llm_reasoning.reasoning_observability_fields(resolution),
            {
                'main_llm_reasoning_effort_requested': 'medium',
                'main_llm_reasoning_effort_effective': 'medium',
                'main_llm_reasoning_policy_kind': 'gpt51_openrouter_reasoning_effort_v1',
                'main_llm_reasoning_hidden': True,
                'main_llm_reasoning_reason_code': 'reasoning_effort_sent',
            },
        )

    def test_non_gpt51_model_does_not_send_reasoning(self) -> None:
        resolution = main_llm_reasoning.resolve_main_llm_reasoning(
            model='openai/gpt-5.4-mini',
            runtime_payload={
                'reasoning_effort': {
                    'value': 'high',
                },
            },
        )

        self.assertFalse(resolution.sent)
        self.assertIsNone(main_llm_reasoning.reasoning_request_payload(resolution))
        self.assertEqual(resolution.effective_effort, 'not_sent')
        self.assertEqual(resolution.reason_code, 'model_not_reasoning_effort_compatible')


if __name__ == '__main__':
    unittest.main()
