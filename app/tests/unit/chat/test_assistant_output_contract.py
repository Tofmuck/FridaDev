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

    def test_normalize_assistant_output_keeps_simple_lists_but_removes_markdown_decoration(self) -> None:
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

        self.assertIn('\n- Il est lisible.', normalized)
        self.assertIn('\n1) Il est portable.', normalized)
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

    def test_normalize_assistant_output_preserves_authorized_code_body_and_normalizes_outer_prose(self) -> None:
        text = (
            '## **Exemple**\n\n'
            '> _Avant._\n\n'
            '```python\n'
            'foo_bar_baz = a * b * c\n'
            'def f(*args, **kwargs):\n'
            '    return __name__, args, kwargs\n'
            '\n'
            '\n'
            '```\n\n'
            '---\n'
            '**Après.**'
        )
        policy = assistant_output_contract.AssistantOutputPolicy(allow_code=True)

        normalized = assistant_output_contract.normalize_assistant_output(text, policy)

        self.assertEqual(
            normalized,
            'Exemple\n\n'
            'Avant.\n\n'
            '```python\n'
            'foo_bar_baz = a * b * c\n'
            'def f(*args, **kwargs):\n'
            '    return __name__, args, kwargs\n'
            '\n'
            '\n'
            '```\n\n'
            'Après.',
        )

    def test_normalize_assistant_output_handles_empty_unclosed_and_multiple_authorized_fences(self) -> None:
        policy = assistant_output_contract.AssistantOutputPolicy(allow_code=True)
        cases = (
            ('empty', 'Avant.\n```python\n```\nAprès.'),
            (
                'unclosed',
                'Avant.\n```python\n  foo_bar = a * b\n\n',
            ),
            (
                'multiple',
                '```python\nfoo_bar = a * b\n```\nEntre **les blocs**.\n```bash\nprintf "%s\\n" "$HOME"\n```',
            ),
            (
                'shorter_nested_fence',
                '````python\nfirst_body = ok\n```\nfoo_bar_baz = a * b * c\n````',
            ),
            (
                'indented_non_closing_fence',
                '```python\n    ```not-a-close\nfoo_bar_baz = a * b * c\n```',
            ),
            (
                'indented_opening_fence',
                'Avant.\n    ```python\n  foo_bar = a * b\n    ```\nAprès.',
            ),
        )

        for name, text in cases:
            with self.subTest(name=name):
                expected = text.replace('**les blocs**', 'les blocs')
                self.assertEqual(
                    assistant_output_contract.normalize_assistant_output(text, policy),
                    expected,
                )

    def test_normalize_assistant_output_normalizes_crlf_without_changing_authorized_code(self) -> None:
        text = (
            '**Avant.**\r\n'
            '```python\r\n'
            '  foo_bar = a * b\r\n'
            '\r\n'
            '```\r\n'
            '_Après._'
        )

        normalized = assistant_output_contract.normalize_assistant_output(
            text,
            assistant_output_contract.AssistantOutputPolicy(allow_code=True),
        )

        self.assertEqual(
            normalized,
            'Avant.\n```python\n  foo_bar = a * b\n\n```\nAprès.',
        )

    def test_normalize_assistant_output_removes_fenced_code_block_body_when_code_is_not_allowed(self) -> None:
        text = 'Avant.\n\n```json\n{\n  "nom": "Dupont"\n}\n```\n\nAprès.'

        normalized = assistant_output_contract.normalize_assistant_output(
            text,
            assistant_output_contract.AssistantOutputPolicy(),
        )

        self.assertEqual(normalized, 'Avant.\n\nAprès.')
        self.assertNotIn('```', normalized)
        self.assertNotIn('"nom"', normalized)

    def test_normalize_assistant_output_never_leaks_empty_unclosed_or_multiple_forbidden_fences(self) -> None:
        cases = (
            ('empty', 'Avant.\n```python\n```\nAprès.', 'Avant.\nAprès.'),
            ('unclosed', 'Avant.\n```python\nsecret_value = a * b\nAprès.', 'Avant.'),
            (
                'multiple',
                'Avant.\n```python\nfirst_secret = 1\n```\nEntre.\n```bash\nsecond_secret=2\n```\nAprès.',
                'Avant.\nEntre.\nAprès.',
            ),
            (
                'indented',
                'Avant.\n    ```python\nsecret_value = 1\n    ```\nAprès.',
                'Avant.\nAprès.',
            ),
        )

        for name, text, expected in cases:
            with self.subTest(name=name):
                normalized = assistant_output_contract.normalize_assistant_output(
                    text,
                    assistant_output_contract.AssistantOutputPolicy(),
                )
                self.assertEqual(normalized, expected)
                self.assertNotIn('secret', normalized)
                self.assertNotIn('```', normalized)


if __name__ == '__main__':
    unittest.main()
