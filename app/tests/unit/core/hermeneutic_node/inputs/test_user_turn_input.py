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

from core.hermeneutic_node.inputs import user_turn_input


class UserTurnInputTests(unittest.TestCase):
    def test_build_user_turn_input_for_definition_question_is_sober(self) -> None:
        bundle = user_turn_input.build_user_turn_bundle(
            user_message="C'est quoi un embedding ?",
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(bundle['user_turn']['schema_version'], 'v1')
        self.assertEqual(bundle['user_turn']['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(bundle['user_turn']['regime_probatoire']['principe'], 'maximal_possible')
        self.assertEqual(bundle['user_turn']['regime_probatoire']['types_de_preuve_attendus'], [])
        self.assertEqual(bundle['user_turn']['regime_probatoire']['provenances'], [])
        self.assertEqual(bundle['user_turn']['regime_probatoire']['regime_de_vigilance'], 'standard')
        self.assertEqual(bundle['user_turn']['regime_probatoire']['composition_probatoire'], 'isolee')
        self.assertEqual(bundle['user_turn']['qualification_temporelle']['portee_temporelle'], 'atemporale')
        self.assertEqual(bundle['user_turn']['qualification_temporelle']['ancrage_temporel'], 'non_ancre')
        self.assertTrue(bundle['user_turn_signals']['present'])
        self.assertFalse(bundle['user_turn_signals']['ambiguity_present'])
        self.assertFalse(bundle['user_turn_signals']['underdetermination_present'])
        self.assertEqual(bundle['user_turn_signals']['active_signal_families'], [])
        self.assertEqual(bundle['user_turn_signals']['active_signal_families_count'], 0)

    def test_build_user_turn_input_for_dialogue_trace_question(self) -> None:
        recent_window_payload = {
            'schema_version': 'v1',
            'max_recent_turns': 5,
            'turn_count': 2,
            'has_in_progress_turn': True,
            'turns': [
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'On parlait du plan', 'timestamp': '2026-04-01T09:00:00Z'},
                        {'role': 'assistant', 'content': 'Oui, du plan de lot', 'timestamp': '2026-04-01T09:01:00Z'},
                    ],
                },
                {
                    'turn_status': 'in_progress',
                    'messages': [
                        {'role': 'user', 'content': "Qu'est-ce qu'on s'est dit plus tot ?", 'timestamp': '2026-04-01T10:00:00Z'},
                    ],
                },
            ],
        }

        payload = user_turn_input.build_user_turn_input(
            user_message="Qu'est-ce qu'on s'est dit plus tot ?",
            recent_window_input_payload=recent_window_payload,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], ['dialogique'])
        self.assertEqual(payload['regime_probatoire']['provenances'], ['dialogue_trace'])
        self.assertEqual(payload['qualification_temporelle']['portee_temporelle'], 'passee')
        self.assertEqual(payload['qualification_temporelle']['ancrage_temporel'], 'dialogue_trace')

    def test_build_user_turn_signals_detects_underdetermined_criterion(self) -> None:
        payload = user_turn_input.build_user_turn_signals(
            user_message='Quel est le meilleur ?',
            recent_window_input_payload=None,
        )

        self.assertTrue(payload['present'])
        self.assertFalse(payload['ambiguity_present'])
        self.assertTrue(payload['underdetermination_present'])
        self.assertEqual(payload['active_signal_families'], ['critere'])
        self.assertEqual(payload['active_signal_families_count'], 1)

    def test_build_user_turn_signals_uses_recent_window_to_avoid_gross_referent_false_positive(self) -> None:
        with_context = user_turn_input.build_user_turn_signals(
            user_message='Corrige ca',
            recent_window_input_payload={
                'turns': [
                    {
                        'turn_status': 'complete',
                        'messages': [
                            {'role': 'assistant', 'content': 'Voici le patch precedent', 'timestamp': '2026-04-01T09:00:00Z'},
                        ],
                    },
                    {
                        'turn_status': 'in_progress',
                        'messages': [
                            {'role': 'user', 'content': 'Corrige ca', 'timestamp': '2026-04-01T10:00:00Z'},
                        ],
                    },
                ],
            },
        )
        without_context = user_turn_input.build_user_turn_signals(
            user_message='Corrige ca',
            recent_window_input_payload={'turns': []},
        )

        self.assertEqual(with_context['active_signal_families'], [])
        self.assertFalse(with_context['ambiguity_present'])
        self.assertIn('referent', without_context['active_signal_families'])
        self.assertTrue(without_context['ambiguity_present'])


if __name__ == '__main__':
    unittest.main()
