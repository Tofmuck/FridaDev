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
            'Frida garde une voix sobre, precise et calme, avec une tenue stable.'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, 'ok')

    def test_accepts_identity_tone_statement(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Frida garde un ton sobre et precis.'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, 'ok')

    def test_rejects_prompt_like_operator_instruction_in_french(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Tu dois verifier les sources et citer chaque point important.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_prompt_like_operator_instruction')

    def test_rejects_prompt_like_operator_instruction_in_english(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'You must verify sources and cite each important point.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_prompt_like_operator_instruction')

    def test_rejects_prompt_like_format_policy_in_english(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Always answer in plain text.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_prompt_like_format_policy')

    def test_rejects_prompt_like_format_policy_in_french(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Il faut repondre en markdown.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_prompt_like_format_policy')

    def test_accepts_user_interest_in_runtime_and_pipelines(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Tof aime discuter du runtime, des pipelines et des architectures complexes.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_conversational_preference')

    def test_accepts_durable_technical_orientation_when_it_is_descriptive(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Tof garde une attention stable aux architectures lisibles et aux structures techniques coherentes.'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, 'ok')

    def test_accepts_strong_relational_posture_when_it_stays_identity_focused(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Frida garde une presence sobre et non intrusive.'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, 'ok')

    def test_accepts_multiline_identity_block_with_pronoun_continuations(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            "Tof est attentif aux conditions reelles d'un dialogue et a sa continuite dans le temps.\n"
            "Il travaille avec une exigence marquee de precision, de sobriete et de justesse relationnelle.\n"
            "Il traite volontiers la voix de l'echange, ses reprises et ses seuils comme des objets de reflexion a part entiere.\n"
            "Il part souvent du contexte concret et sensible avant d'aller vers l'interpretation ou la mise en forme."
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason_code, 'ok')

    def test_rejects_conversational_comfort_statement(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Tof se sent rassure quand on reformule calmement les reponses.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_conversational_preference')

    def test_rejects_utilitarian_framing(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Frida garde des reperes utiles pour mieux repondre au prochain tour.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_utilitarian_framing')

    def test_rejects_weak_relational_positioning(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Frida cherche une proximite rassurante dans l echange.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_weak_relational_positioning')

    def test_rejects_sentence_that_is_not_a_declarative_identity_statement(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Le dialogue revient souvent sur le runtime et les pipelines.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_not_identity_statement')

    def test_rejects_multiline_block_when_one_proposition_is_conversational_preference(self) -> None:
        result = mutable_identity_validation.validate_mutable_identity_content(
            'Tof garde une attention stable aux architectures lisibles.\n'
            'Il prefere des reponses courtes et directes.'
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, 'mutable_content_conversational_preference')


if __name__ == '__main__':
    unittest.main()
