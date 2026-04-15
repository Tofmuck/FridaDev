from __future__ import annotations

import inspect
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

from core import chat_prompt_context
from core.hermeneutic_node.inputs import time_input


class ChatPromptContextTests(unittest.TestCase):
    def test_lot2_keeps_chat_prompt_context_free_of_input_mode_transport_logic(self) -> None:
        source = inspect.getsource(chat_prompt_context)

        self.assertNotIn('input_mode', source)
        self.assertNotIn('orality_hint', source)

    def test_build_time_input_exposes_canonical_time_fields(self) -> None:
        payload = time_input.build_time_input(
            now_utc_iso='2026-01-15T08:15:00Z',
            timezone_name='Europe/Paris',
        )

        self.assertEqual(payload['schema_version'], 'v1')
        self.assertEqual(payload['now_utc_iso'], '2026-01-15T08:15:00Z')
        self.assertEqual(payload['timezone'], 'Europe/Paris')
        self.assertEqual(payload['now_local_iso'], '2026-01-15T09:15:00+01:00')
        self.assertEqual(payload['local_date'], '2026-01-15')
        self.assertEqual(payload['local_time'], '09:15')
        self.assertEqual(payload['local_weekday'], 'thursday')
        self.assertEqual(payload['day_part_class'], 'morning')
        self.assertEqual(payload['day_part_human'], 'matin')

    def test_resolve_backend_prompts_uses_prompt_loader_authority(self) -> None:
        loader = SimpleNamespace(
            get_main_system_prompt=lambda: 'BACKEND SYSTEM PROMPT',
            get_main_hermeneutical_prompt=lambda: 'BACKEND HERMENEUTICAL PROMPT',
        )

        system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(loader)

        self.assertEqual(system_prompt, 'BACKEND SYSTEM PROMPT')
        self.assertEqual(hermeneutical_prompt, 'BACKEND HERMENEUTICAL PROMPT')

    def test_build_augmented_system_keeps_expected_order(self) -> None:
        identity_module = SimpleNamespace(
            build_identity_block=lambda: ('[IDENTITY BLOCK]', ['id-a', 'id-b']),
        )
        config_module = SimpleNamespace(FRIDA_TIMEZONE='Europe/Paris')

        augmented_system, identity_ids = chat_prompt_context.build_augmented_system(
            system_prompt='BACKEND SYSTEM PROMPT',
            hermeneutical_prompt='BACKEND HERMENEUTICAL PROMPT',
            config_module=config_module,
            identity_module=identity_module,
            now_iso='2026-01-15T08:15:00Z',
        )

        self.assertEqual(identity_ids, ['id-a', 'id-b'])
        self.assertIn('BACKEND SYSTEM PROMPT', augmented_system)
        self.assertIn('BACKEND HERMENEUTICAL PROMPT', augmented_system)
        self.assertIn('[RÉFÉRENCE TEMPORELLE]', augmented_system)
        self.assertIn('[IDENTITY BLOCK]', augmented_system)
        self.assertLess(
            augmented_system.index('BACKEND SYSTEM PROMPT'),
            augmented_system.index('BACKEND HERMENEUTICAL PROMPT'),
        )
        self.assertLess(
            augmented_system.index('BACKEND HERMENEUTICAL PROMPT'),
            augmented_system.index('[RÉFÉRENCE TEMPORELLE]'),
        )
        self.assertLess(
            augmented_system.index('[RÉFÉRENCE TEMPORELLE]'),
            augmented_system.index('[IDENTITY BLOCK]'),
        )
        self.assertIn("NOW: 2026-01-15T09:15:00+01:00", augmented_system)
        self.assertIn("TIMEZONE: Europe/Paris", augmented_system)
        self.assertIn("09:15", augmented_system)
        self.assertNotIn("heure de Paris", augmented_system)
        self.assertIn("n'affirme jamais que tu n'y as pas acces", augmented_system)
        self.assertIn("ce matin, cet apres-midi, ce soir, cette nuit", augmented_system)
        self.assertIn("privilegie le relatif puis ajoute un absolu court", augmented_system)

    def test_build_hermeneutic_judgment_block_covers_answer_clarify_and_suspend(self) -> None:
        expected = {
            'answer': 'Tu peux produire une reponse substantive normale.',
            'clarify': 'Tu ne dois pas repondre directement au fond. Tu dois demander une clarification breve et explicite.',
            'suspend': 'Tu ne dois pas produire de reponse substantive normale. Tu dois expliciter la suspension ou la limite presente.',
        }

        for posture, instruction in expected.items():
            with self.subTest(posture=posture):
                block = chat_prompt_context.build_hermeneutic_judgment_block(
                    validated_output={
                        'schema_version': 'v1',
                        'validation_decision': 'confirm',
                        'final_judgment_posture': posture,
                        'pipeline_directives_final': [f'posture_{posture}'],
                    }
                )
                self.assertIn('[JUGEMENT HERMENEUTIQUE]', block)
                self.assertIn(f'Posture finale validee: {posture}.', block)
                self.assertIn(f'Consigne hermeneutique: {instruction}', block)
                self.assertIn(f'Directives finales actives: posture_{posture}.', block)

    def test_inject_hermeneutic_judgment_block_appends_after_augmented_system(self) -> None:
        base_system = 'BASE SYSTEM'
        judgment_block = '[JUGEMENT HERMENEUTIQUE]\nPosture finale validee: clarify.'

        augmented = chat_prompt_context.inject_hermeneutic_judgment_block(base_system, judgment_block)

        self.assertTrue(augmented.startswith('BASE SYSTEM'))
        self.assertTrue(augmented.endswith('Posture finale validee: clarify.'))
        self.assertLess(augmented.index('BASE SYSTEM'), augmented.index('[JUGEMENT HERMENEUTIQUE]'))

    def test_build_direct_identity_revelation_guard_block_marks_explicit_non_ambiguous_revelation(self) -> None:
        block = chat_prompt_context.build_direct_identity_revelation_guard_block(
            user_msg='Je suis Christophe Muck',
            user_turn_input={'geste_dialogique_dominant': 'exposition'},
            user_turn_signals={
                'ambiguity_present': False,
                'underdetermination_present': False,
                'active_signal_families': [],
            },
        )

        self.assertIn('[GARDE DE REVELATION IDENTITAIRE]', block)
        self.assertIn('revelation identitaire explicite et non ambigue', block)
        self.assertIn("N'ajoute pas de question de clarification bureaucratique", block)

    def test_build_direct_identity_revelation_guard_block_stays_silent_when_revelation_is_ambiguous(self) -> None:
        block = chat_prompt_context.build_direct_identity_revelation_guard_block(
            user_msg='Je suis Christophe Muck',
            user_turn_input={'geste_dialogique_dominant': 'exposition'},
            user_turn_signals={
                'ambiguity_present': True,
                'underdetermination_present': False,
                'active_signal_families': ['referent'],
            },
        )

        self.assertEqual(block, '')

    def test_build_plain_text_guard_block_for_default_turn_forbids_markdown_lists_and_code_fences(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg='Explique simplement la différence entre la mémoire vive et le disque dur.',
        )

        self.assertIn('[CONTRAT TEXTE BRUT]', block)
        self.assertIn('texte brut strict', block)
        self.assertIn("n'utilise ni puces, ni listes numérotées", block)
        self.assertIn('Réponds en courts paragraphes continus.', block)
        self.assertIn("n'utilise pas de code fences", block)

    def test_build_plain_text_guard_block_does_not_treat_plan_marshall_as_explicit_format_request(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg='Explique le plan Marshall.',
        )

        self.assertIn("n'utilise ni puces, ni listes numérotées", block)
        self.assertIn("n'utilise pas de code fences", block)
        self.assertNotIn("demande explicitement un plan, des étapes ou une liste", block)

    def test_build_plain_text_guard_block_does_not_treat_topic_points_as_explicit_format_request(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg='Parle-moi des points communs entre Platon et Aristote.',
        )

        self.assertIn("n'utilise ni puces, ni listes numérotées", block)
        self.assertIn("n'utilise pas de code fences", block)
        self.assertNotIn("demande explicitement un plan, des étapes ou une liste", block)

    def test_build_plain_text_guard_block_does_not_treat_json_topic_as_explicit_code_request(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg="Explique simplement ce qu'est JSON.",
        )

        self.assertIn("n'utilise ni puces, ni listes numérotées", block)
        self.assertIn("n'utilise pas de code fences", block)
        self.assertNotIn("demande explicitement du code", block)

    def test_build_plain_text_guard_block_does_not_treat_math_function_topic_as_explicit_code_request(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg="Explique ce qu'est une fonction continue en maths.",
        )

        self.assertIn("n'utilise ni puces, ni listes numérotées", block)
        self.assertIn("n'utilise pas de code fences", block)
        self.assertNotIn("demande explicitement du code", block)

    def test_build_plain_text_guard_block_allows_minimal_structure_when_user_explicitly_requests_steps(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg='Donne-moi un plan en quatre étapes pour préparer un exposé.',
        )

        self.assertIn("demande explicitement un plan, des étapes ou une liste", block)
        self.assertNotIn("n'utilise ni puces, ni listes numérotées", block)
        self.assertIn("n'utilise pas de code fences", block)

    def test_build_plain_text_guard_block_allows_code_only_when_user_explicitly_requests_it(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg='Montre-moi un exemple de code Python pour lire un fichier JSON.',
        )

        self.assertIn("demande explicitement du code", block)
        self.assertNotIn("n'utilise pas de code fences", block)

    def test_build_plain_text_guard_block_allows_bash_command_when_explicitly_requested(self) -> None:
        block = chat_prompt_context.build_plain_text_guard_block(
            user_msg='Donne-moi la commande bash pour lister les fichiers.',
        )

        self.assertIn("demande explicitement du code", block)
        self.assertNotIn("n'utilise pas de code fences", block)

    def test_inject_plain_text_guard_block_appends_after_augmented_system(self) -> None:
        augmented = chat_prompt_context.inject_plain_text_guard_block(
            'BASE SYSTEM',
            '[CONTRAT TEXTE BRUT]\nRéponds en texte brut strict.',
        )

        self.assertTrue(augmented.startswith('BASE SYSTEM'))
        self.assertIn('[CONTRAT TEXTE BRUT]', augmented)
        self.assertLess(augmented.index('BASE SYSTEM'), augmented.index('[CONTRAT TEXTE BRUT]'))

    def test_build_web_reading_guard_block_for_snippet_fallback_forbids_direct_reading_claims(self) -> None:
        block = chat_prompt_context.build_web_reading_guard_block(
            web_input={
                'explicit_url': 'https://example.com/article',
                'read_state': 'page_not_read_snippet_fallback',
            }
        )

        self.assertIn('[GARDE DE LECTURE WEB]', block)
        self.assertIn('read_state: page_not_read_snippet_fallback.', block)
        self.assertIn("La page cible n'a pas ete lue directement.", block)
        self.assertIn("je l'ai sous les yeux", block)
        self.assertIn("j'ai lu l'article", block)
        self.assertIn("je n'ai qu'un extrait/snippet", block)

    def test_build_web_reading_guard_block_for_crawl_empty_forbids_direct_reading_claims(self) -> None:
        block = chat_prompt_context.build_web_reading_guard_block(
            web_input={
                'explicit_url': 'https://example.com/article',
                'read_state': 'page_not_read_crawl_empty',
            }
        )

        self.assertIn('read_state: page_not_read_crawl_empty.', block)
        self.assertIn('crawl vide', block)
        self.assertIn("je l'ai sous les yeux", block)
        self.assertIn("Tu dois assumer explicitement que tu n'as pas pu lire directement la page.", block)

    def test_build_web_reading_guard_block_for_page_read_allows_direct_reading(self) -> None:
        block = chat_prompt_context.build_web_reading_guard_block(
            web_input={
                'explicit_url': 'https://example.com/article',
                'read_state': 'page_read',
            }
        )

        self.assertIn('read_state: page_read.', block)
        self.assertIn('La lecture directe de cette page est soutenue par le runtime.', block)
        self.assertIn('Tu peux parler de lecture directe', block)
        self.assertNotIn("je l'ai sous les yeux", block)

    def test_build_web_reading_guard_block_for_partial_read_requires_nuance(self) -> None:
        block = chat_prompt_context.build_web_reading_guard_block(
            web_input={
                'explicit_url': 'https://example.com/article',
                'read_state': 'page_partially_read',
            }
        )

        self.assertIn('read_state: page_partially_read.', block)
        self.assertIn("Tu peux parler d'une lecture partielle ou d'un extrait tronque.", block)
        self.assertIn("N'affirme pas une lecture integrale, exhaustive ou detaillee de toute la page.", block)

    def test_inject_web_reading_guard_block_appends_after_augmented_system(self) -> None:
        augmented = chat_prompt_context.inject_web_reading_guard_block(
            'BASE SYSTEM',
            '[GARDE DE LECTURE WEB]\nread_state: page_not_read_snippet_fallback.',
        )

        self.assertTrue(augmented.startswith('BASE SYSTEM'))
        self.assertIn('[GARDE DE LECTURE WEB]', augmented)
        self.assertLess(augmented.index('BASE SYSTEM'), augmented.index('[GARDE DE LECTURE WEB]'))

    def test_apply_augmented_system_overwrites_first_system_message_only(self) -> None:
        conversation = {
            'messages': [
                {'role': 'system', 'content': 'old system'},
                {'role': 'user', 'content': 'hello'},
            ]
        }

        chat_prompt_context.apply_augmented_system(conversation, 'new augmented system')

        self.assertEqual(conversation['messages'][0]['content'], 'new augmented system')
        self.assertEqual(conversation['messages'][1]['content'], 'hello')

    def test_inject_web_context_targets_last_user_message_and_logs_event(self) -> None:
        prompt_messages = [
            {'role': 'user', 'content': 'first user'},
            {'role': 'assistant', 'content': 'assistant'},
            {'role': 'user', 'content': 'last user'},
        ]
        observed_logs = []

        web_search_module = SimpleNamespace(
            build_context=lambda _user_msg: ('WEB CONTEXT', 'query test', 3),
        )
        admin_logs_module = SimpleNamespace(
            log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)),
        )

        chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg='Bonjour',
            conversation_id='conv-ctx',
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(prompt_messages[0]['content'], 'first user')
        self.assertEqual(prompt_messages[2]['content'], 'WEB CONTEXT\n\nQuestion : last user')
        self.assertEqual(len(observed_logs), 1)
        event, payload = observed_logs[0]
        self.assertEqual(event, 'web_search')
        self.assertEqual(payload['conversation_id'], 'conv-ctx')
        self.assertEqual(payload['query'], 'query test')
        self.assertEqual(payload['original'], 'Bonjour')
        self.assertEqual(payload['results'], 3)
        self.assertNotIn('ticketmaster', payload)

    def test_inject_web_context_skips_when_no_context(self) -> None:
        prompt_messages = [{'role': 'user', 'content': 'last user'}]
        observed_logs = []

        web_search_module = SimpleNamespace(
            build_context=lambda _user_msg: ('', 'query ignored', 0),
        )
        admin_logs_module = SimpleNamespace(
            log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)),
        )

        chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg='Bonjour',
            conversation_id='conv-ctx',
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(prompt_messages[0]['content'], 'last user')
        self.assertEqual(observed_logs, [])


if __name__ == '__main__':
    unittest.main()
