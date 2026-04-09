from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from identity import mutable_identity_validation


class MutableIdentityValidationTests(unittest.TestCase):
    def test_accepts_narrative_identity_text(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Frida garde une voix sobre, precise et calme, avec une continuite relationnelle stable.'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, 'ok')

    def test_rejects_prompt_like_operator_instruction(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Tu dois verifier les sources et citer chaque point important.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_prompt_like_operator_instruction')

    def test_rejects_prompt_like_runtime_meta(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Cette mutable doit rappeler la source de verite runtime et la garde admin.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_prompt_like_runtime_meta')


if __name__ == '__main__':
    unittest.main()
