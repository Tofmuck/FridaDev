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

from core import assistant_output_contract


class AssistantOutputContractTests(unittest.TestCase):
    def test_resolve_policy_keeps_ordinary_topic_turns_strict(self) -> None:
        ordinary_messages = [
            'Explique le plan Marshall.',
            'Parle-moi des points communs entre Platon et Aristote.',
            "Explique simplement ce qu'est JSON.",
            "Explique ce qu'est une fonction continue en maths.",
            'Parle-moi du CSS moderne.',
        ]

        for message in ordinary_messages:
            with self.subTest(message=message):
                policy = assistant_output_contract.resolve_assistant_output_policy(message)
                self.assertFalse(policy.allow_structure)
                self.assertFalse(policy.allow_code)

    def test_resolve_policy_allows_explicit_structure_requests(self) -> None:
        policy = assistant_output_contract.resolve_assistant_output_policy(
            'Donne-moi un plan simple en trois étapes pour préparer un exposé.',
        )

        self.assertTrue(policy.allow_structure)
        self.assertFalse(policy.allow_code)

    def test_resolve_policy_allows_explicit_code_requests(self) -> None:
        policy = assistant_output_contract.resolve_assistant_output_policy(
            'Montre-moi un exemple de code Python.',
        )

        self.assertFalse(policy.allow_structure)
        self.assertTrue(policy.allow_code)

    def test_normalize_assistant_output_flattens_bullets_and_numbering_for_ordinary_turns(self) -> None:
        text = (
            'JSON est un format.\n\n'
            '- Il est lisible.\n'
            '- Il est structuré.\n'
            '1) Il est portable.\n'
            '## Conclusion\n'
            '> Très utilisé.\n'
            '---\n'
        )

        normalized = assistant_output_contract.normalize_assistant_output(
            text,
            assistant_output_contract.AssistantOutputPolicy(),
        )

        self.assertNotIn('\n- ', normalized)
        self.assertNotIn('\n1) ', normalized)
        self.assertNotIn('##', normalized)
        self.assertNotIn('\n>\n', normalized)
        self.assertNotIn('---', normalized)
        self.assertIn('Il est lisible.', normalized)
        self.assertIn('Il est portable.', normalized)
        self.assertIn('Conclusion', normalized)

    def test_normalize_assistant_output_keeps_minimal_structure_when_explicitly_allowed(self) -> None:
        text = 'Voici un plan :\n\n1) Comprendre\n2) Structurer\n3) Réviser'
        policy = assistant_output_contract.AssistantOutputPolicy(allow_structure=True, allow_code=False)

        normalized = assistant_output_contract.normalize_assistant_output(text, policy)

        self.assertIn('1) Comprendre', normalized)
        self.assertIn('2) Structurer', normalized)

    def test_normalize_assistant_output_keeps_code_fences_when_code_is_allowed(self) -> None:
        text = '```python\nprint("hello")\n```'
        policy = assistant_output_contract.AssistantOutputPolicy(allow_structure=False, allow_code=True)

        normalized = assistant_output_contract.normalize_assistant_output(text, policy)

        self.assertIn('```python', normalized)
        self.assertIn('print("hello")', normalized)


if __name__ == '__main__':
    unittest.main()
