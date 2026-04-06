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
    def test_build_user_turn_input_for_definition_question_without_cleaned_punctuation_is_sober(self) -> None:
        bundle = user_turn_input.build_user_turn_bundle(
            user_message="C'est quoi un embedding",
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

    def test_build_user_turn_input_for_dialogue_trace_question_with_apostrophes_and_accents(self) -> None:
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
                        {'role': 'user', 'content': "Qu'est-ce qu'on s'est dit plus tôt", 'timestamp': '2026-04-01T10:00:00Z'},
                    ],
                },
            ],
        }

        payload = user_turn_input.build_user_turn_input(
            user_message="Qu'est-ce qu'on s'est dit plus tôt",
            recent_window_input_payload=recent_window_payload,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], ['dialogique'])
        self.assertEqual(payload['regime_probatoire']['provenances'], ['dialogue_trace'])
        self.assertEqual(payload['qualification_temporelle']['portee_temporelle'], 'passee')
        self.assertEqual(payload['qualification_temporelle']['ancrage_temporel'], 'dialogue_trace')

    def test_build_user_turn_input_detects_positionnement_with_french_apostrophe(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message="Je ne suis pas d'accord",
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['geste_dialogique_dominant'], 'positionnement')

    def test_build_user_turn_input_does_not_misclassify_self_identification_as_regulation(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message='Je suis Christophe Muck',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['geste_dialogique_dominant'], 'exposition')
        self.assertEqual(payload['regime_probatoire']['provenances'], [])

    def test_build_user_turn_input_does_not_treat_biodiversite_as_web_provenance(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message="Imagine que tu es une extraterrestre envoyee sur Terre pour sauver la biodiversite. Que fais-tu ?",
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['regime_probatoire']['provenances'], [])
        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], [])

    def test_build_user_turn_input_does_not_treat_faire_preuve_de_as_factuelle(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message='Il faut faire preuve de patience pour comprendre ce texte.',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], [])
        self.assertEqual(payload['regime_probatoire']['provenances'], [])

    def test_build_user_turn_input_does_not_treat_lien_a_l_autre_as_web_provenance(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message="Ce passage travaille le lien a l'autre dans une lecture atemporelle.",
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['regime_probatoire']['provenances'], [])
        self.assertEqual(payload['regime_probatoire']['regime_de_vigilance'], 'standard')

    def test_build_user_turn_input_keeps_explicit_link_request_as_web_provenance(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message='As-tu un lien ?',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['regime_probatoire']['provenances'], ['web'])
        self.assertEqual(payload['regime_probatoire']['regime_de_vigilance'], 'renforce')

    def test_build_user_turn_input_keeps_explicit_source_request_as_factuelle_and_web(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message='Donne-moi la source.',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], ['factuelle'])
        self.assertEqual(payload['regime_probatoire']['provenances'], ['web'])

    def test_build_user_turn_input_keeps_explicit_verification_request_as_factuelle(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message='Tu peux verifier cette affirmation ?',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], ['factuelle'])

    def test_build_user_turn_input_does_not_fall_back_to_exposition_for_est_ce_que_request(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message="Est-ce que tu peux vérifier ça",
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertNotEqual(payload['geste_dialogique_dominant'], 'exposition')
        self.assertIn(payload['geste_dialogique_dominant'], {'interrogation', 'orientation'})
        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], ['factuelle'])

    def test_build_user_turn_input_does_not_mark_tu_as_raison_as_argumentative(self) -> None:
        payload = user_turn_input.build_user_turn_input(
            user_message='Tu as raison',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(payload['geste_dialogique_dominant'], 'positionnement')
        self.assertEqual(payload['regime_probatoire']['types_de_preuve_attendus'], [])

    def test_build_user_turn_input_does_not_treat_repo_as_web_provenance(self) -> None:
        question_payload = user_turn_input.build_user_turn_input(
            user_message='Quel est le meilleur repo ?',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )
        orientation_payload = user_turn_input.build_user_turn_input(
            user_message='Tu peux chercher dans le repo ?',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(question_payload['regime_probatoire']['provenances'], [])
        self.assertEqual(question_payload['regime_probatoire']['regime_de_vigilance'], 'standard')
        self.assertEqual(orientation_payload['regime_probatoire']['provenances'], [])
        self.assertEqual(orientation_payload['regime_probatoire']['regime_de_vigilance'], 'standard')

    def test_build_user_turn_input_classifies_reponds_forms_as_orientation(self) -> None:
        imperative_payload = user_turn_input.build_user_turn_input(
            user_message='Réponds',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )
        deictic_payload = user_turn_input.build_user_turn_input(
            user_message='Réponds là-dessus',
            recent_window_input_payload=None,
            time_input_payload={'now_utc_iso': '2026-04-01T10:00:00Z'},
        )

        self.assertEqual(imperative_payload['geste_dialogique_dominant'], 'orientation')
        self.assertEqual(deictic_payload['geste_dialogique_dominant'], 'orientation')

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

    def test_build_user_turn_signals_keeps_referent_after_non_resolutive_context(self) -> None:
        payload = user_turn_input.build_user_turn_signals(
            user_message='Corrige ça',
            recent_window_input_payload={
                'turns': [
                    {
                        'turn_status': 'complete',
                        'messages': [
                            {'role': 'assistant', 'content': 'Salut', 'timestamp': '2026-04-01T09:00:00Z'},
                        ],
                    },
                    {
                        'turn_status': 'in_progress',
                        'messages': [
                            {'role': 'user', 'content': 'Corrige ça', 'timestamp': '2026-04-01T10:00:00Z'},
                        ],
                    },
                ],
            },
        )

        self.assertIn('referent', payload['active_signal_families'])
        self.assertTrue(payload['ambiguity_present'])

    def test_build_user_turn_signals_keeps_referent_after_long_non_resolutive_context(self) -> None:
        payload = user_turn_input.build_user_turn_signals(
            user_message='Corrige ça',
            recent_window_input_payload={
                'turns': [
                    {
                        'turn_status': 'complete',
                        'messages': [
                            {
                                'role': 'assistant',
                                'content': 'Je pense qu il faudrait revoir la methode de travail demain',
                                'timestamp': '2026-04-01T09:00:00Z',
                            },
                        ],
                    },
                    {
                        'turn_status': 'in_progress',
                        'messages': [
                            {'role': 'user', 'content': 'Corrige ça', 'timestamp': '2026-04-01T10:00:00Z'},
                        ],
                    },
                ],
            },
        )

        self.assertIn('referent', payload['active_signal_families'])
        self.assertTrue(payload['ambiguity_present'])

    def test_build_user_turn_signals_uses_resolutive_recent_window_to_avoid_gross_referent_false_positive(self) -> None:
        with_context = user_turn_input.build_user_turn_signals(
            user_message='Corrige ça',
            recent_window_input_payload={
                'turns': [
                    {
                        'turn_status': 'complete',
                        'messages': [
                            {'role': 'assistant', 'content': 'Voici le patch précédent', 'timestamp': '2026-04-01T09:00:00Z'},
                        ],
                    },
                    {
                        'turn_status': 'in_progress',
                        'messages': [
                            {'role': 'user', 'content': 'Corrige ça', 'timestamp': '2026-04-01T10:00:00Z'},
                        ],
                    },
                ],
            },
        )
        without_context = user_turn_input.build_user_turn_signals(
            user_message='Corrige ça',
            recent_window_input_payload={'turns': []},
        )

        self.assertEqual(with_context['active_signal_families'], [])
        self.assertFalse(with_context['ambiguity_present'])
        self.assertIn('referent', without_context['active_signal_families'])
        self.assertTrue(without_context['ambiguity_present'])


if __name__ == '__main__':
    unittest.main()
