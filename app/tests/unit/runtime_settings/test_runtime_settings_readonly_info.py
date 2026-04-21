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

from admin import runtime_settings
import config
from core import prompt_loader


class RuntimeSettingsReadonlyInfoTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_get_section_readonly_info_main_model_exposes_context_budget_prompts_and_runtime_bricks(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('main_model')

        self.assertEqual(readonly_info['system_prompt']['label'], 'SYSTEM_PROMPT')
        self.assertFalse(readonly_info['system_prompt']['is_editable'])
        self.assertEqual(readonly_info['system_prompt']['source'], 'prompt_file')
        self.assertEqual(readonly_info['system_prompt']['value'], prompt_loader.get_main_system_prompt())
        self.assertIn('Cadre de réponse', readonly_info['system_prompt']['value'])
        self.assertIn(
            'Tu aides à analyser, structurer, reformuler, documenter et faire avancer un travail intellectuel ou technique.',
            readonly_info['system_prompt']['value'],
        )
        self.assertNotIn(
            'Tu adoptes un ton clair, calme, adulte et professionnel.',
            readonly_info['system_prompt']['value'],
        )
        self.assertEqual(readonly_info['system_prompt_path']['label'], 'MAIN_SYSTEM_PROMPT_PATH')
        self.assertEqual(readonly_info['system_prompt_path']['value'], config.MAIN_SYSTEM_PROMPT_PATH)
        self.assertEqual(readonly_info['system_prompt_path']['source'], 'config_py')
        self.assertEqual(
            readonly_info['system_prompt_loader']['label'],
            'SYSTEM_PROMPT_RUNTIME_SOURCE',
        )
        self.assertEqual(
            readonly_info['system_prompt_loader']['value'],
            'core.prompt_loader.get_main_system_prompt()',
        )
        self.assertEqual(readonly_info['system_prompt_loader']['source'], 'backend_loader')
        self.assertEqual(readonly_info['hermeneutical_prompt']['label'], 'HERMENEUTICAL_PROMPT')
        self.assertFalse(readonly_info['hermeneutical_prompt']['is_editable'])
        self.assertEqual(readonly_info['hermeneutical_prompt']['source'], 'prompt_file')
        self.assertEqual(
            readonly_info['hermeneutical_prompt']['value'],
            prompt_loader.get_main_hermeneutical_prompt(),
        )
        self.assertIn(
            "Contrat d'interpretation du prompt augmente",
            readonly_info['hermeneutical_prompt']['value'],
        )
        self.assertEqual(
            readonly_info['hermeneutical_prompt_path']['label'],
            'MAIN_HERMENEUTICAL_PROMPT_PATH',
        )
        self.assertEqual(
            readonly_info['hermeneutical_prompt_path']['value'],
            config.MAIN_HERMENEUTICAL_PROMPT_PATH,
        )
        self.assertEqual(readonly_info['hermeneutical_prompt_path']['source'], 'config_py')
        self.assertEqual(
            readonly_info['hermeneutical_prompt_loader']['label'],
            'HERMENEUTICAL_PROMPT_RUNTIME_SOURCE',
        )
        self.assertEqual(
            readonly_info['hermeneutical_prompt_loader']['value'],
            'core.prompt_loader.get_main_hermeneutical_prompt()',
        )
        self.assertEqual(
            readonly_info['hermeneutical_prompt_loader']['source'],
            'backend_loader',
        )
        self.assertNotEqual(readonly_info['system_prompt']['value'], readonly_info['hermeneutical_prompt']['value'])
        self.assertEqual(
            readonly_info['hermeneutical_runtime_bricks']['label'],
            'HERMENEUTICAL_RUNTIME_BRICKS',
        )
        self.assertFalse(readonly_info['hermeneutical_runtime_bricks']['is_editable'])
        self.assertEqual(readonly_info['hermeneutical_runtime_bricks']['source'], 'runtime_contract')
        self.assertIn('[RÉFÉRENCE TEMPORELLE]', readonly_info['hermeneutical_runtime_bricks']['value'])
        self.assertIn('[Résumé de la période ...]', readonly_info['hermeneutical_runtime_bricks']['value'])
        self.assertIn('[Mémoire — souvenirs pertinents]', readonly_info['hermeneutical_runtime_bricks']['value'])
        self.assertIn('[RECHERCHE WEB — ...]', readonly_info['hermeneutical_runtime_bricks']['value'])
        self.assertEqual(readonly_info['context_max_tokens']['label'], 'FRIDA_MAX_TOKENS')
        self.assertEqual(readonly_info['context_max_tokens']['value'], config.MAX_TOKENS)
        self.assertFalse(readonly_info['context_max_tokens']['is_editable'])

    def test_get_section_readonly_info_arbiter_model_exposes_budgets_paths_and_prompts(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('arbiter_model')

        self.assertEqual(readonly_info['decision_max_tokens']['value'], 600)
        self.assertFalse(readonly_info['decision_max_tokens']['is_editable'])
        self.assertEqual(readonly_info['identity_extractor_max_tokens']['value'], 700)
        self.assertFalse(readonly_info['identity_extractor_max_tokens']['is_editable'])
        self.assertEqual(readonly_info['arbiter_prompt_path']['label'], 'ARBITER_PROMPT_PATH')
        self.assertEqual(readonly_info['arbiter_prompt_path']['value'], config.ARBITER_PROMPT_PATH)
        self.assertEqual(
            readonly_info['identity_extractor_prompt_path']['label'],
            'IDENTITY_EXTRACTOR_PROMPT_PATH',
        )
        self.assertEqual(
            readonly_info['identity_extractor_prompt_path']['value'],
            config.IDENTITY_EXTRACTOR_PROMPT_PATH,
        )
        self.assertIn('You are a conversational memory arbiter.', readonly_info['arbiter_prompt']['value'])
        self.assertIn('You are an identity evidence extractor.', readonly_info['identity_extractor_prompt']['value'])

    def test_get_section_readonly_info_summary_model_exposes_budgets_and_inline_prompt(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('summary_model')

        self.assertEqual(readonly_info['summary_target_tokens']['label'], 'SUMMARY_TARGET_TOKENS')
        self.assertEqual(readonly_info['summary_target_tokens']['value'], config.SUMMARY_TARGET_TOKENS)
        self.assertFalse(readonly_info['summary_target_tokens']['is_editable'])
        self.assertEqual(readonly_info['summary_threshold_tokens']['label'], 'SUMMARY_THRESHOLD_TOKENS')
        self.assertEqual(
            readonly_info['summary_threshold_tokens']['value'],
            config.SUMMARY_THRESHOLD_TOKENS,
        )
        self.assertEqual(readonly_info['summary_keep_turns']['label'], 'SUMMARY_KEEP_TURNS')
        self.assertEqual(readonly_info['summary_keep_turns']['value'], config.SUMMARY_KEEP_TURNS)
        self.assertFalse(readonly_info['summary_keep_turns']['is_editable'])
        self.assertEqual(readonly_info['system_prompt']['label'], 'summary_system_prompt')
        self.assertEqual(readonly_info['system_prompt']['source'], 'prompt_file')
        self.assertIn('Tu es un assistant de synthèse.', readonly_info['system_prompt']['value'])
        self.assertIn('Écris en français.', readonly_info['system_prompt']['value'])

    def test_get_section_readonly_info_stimmung_agent_model_exposes_prompt_and_shared_transport(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('stimmung_agent_model')

        self.assertEqual(readonly_info['prompt_path']['label'], 'STIMMUNG_AGENT_PROMPT_PATH')
        self.assertEqual(readonly_info['prompt_path']['value'], 'prompts/stimmung_agent.txt')
        self.assertEqual(
            readonly_info['prompt_loader']['value'],
            'core.stimmung_agent._load_system_prompt()',
        )
        self.assertIn('Tu es un classificateur affectif minimal', readonly_info['prompt_text']['value'])
        self.assertIn('main_model.title_stimmung_agent', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_stimmung_agent', readonly_info['shared_transport']['value'])
        self.assertEqual(
            readonly_info['recent_window_turn_cap']['value'],
            runtime_settings.canonical_recent_window_input.MAX_RECENT_TURNS,
        )
        self.assertEqual(readonly_info['max_context_message_chars']['value'], 220)
        self.assertEqual(readonly_info['max_current_turn_chars']['value'], 600)

    def test_get_section_readonly_info_validation_agent_model_exposes_prompt_and_contract(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('validation_agent_model')

        self.assertEqual(readonly_info['prompt_path']['label'], 'VALIDATION_AGENT_PROMPT_PATH')
        self.assertEqual(readonly_info['prompt_path']['value'], 'prompts/validation_agent.txt')
        self.assertEqual(
            readonly_info['prompt_loader']['value'],
            'core.hermeneutic_node.validation.validation_agent._load_system_prompt()',
        )
        self.assertIn('validation_dialogue_context', readonly_info['prompt_text']['value'])
        self.assertIn('main_model.title_validation_agent', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_validation_agent', readonly_info['shared_transport']['value'])
        self.assertEqual(
            readonly_info['validation_context_messages_cap']['value'],
            runtime_settings.canonical_recent_context_input.VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES,
        )
        self.assertEqual(readonly_info['validation_context_message_chars']['value'], 420)
        self.assertIn('final_judgment_posture', readonly_info['validated_output_contract']['value'])
        self.assertIn('final_output_regime', readonly_info['validated_output_contract']['value'])
        self.assertIn('arbiter_reason', readonly_info['validated_output_contract']['value'])

    def test_get_section_readonly_info_services_exposes_web_reformulation_prompt(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('services')

        self.assertEqual(readonly_info['web_reformulation_max_tokens']['value'], 40)
        self.assertFalse(readonly_info['web_reformulation_max_tokens']['is_editable'])
        self.assertEqual(readonly_info['web_reformulation_max_tokens']['source'], 'prompt_file')
        self.assertEqual(
            readonly_info['web_reformulation_system_prompt']['label'],
            'web_reformulation_system_prompt',
        )
        self.assertEqual(readonly_info['web_reformulation_system_prompt']['source'], 'prompt_file')
        self.assertIn('Nous sommes le {today}.', readonly_info['web_reformulation_system_prompt']['value'])
        self.assertIn(
            'Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.',
            readonly_info['web_reformulation_system_prompt']['value'],
        )
        self.assertIn('Maximum 8 mots.', readonly_info['web_reformulation_system_prompt']['value'])

    def test_get_section_readonly_info_identity_governance_points_to_hermeneutic_admin_surface(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('identity_governance')

        self.assertEqual(readonly_info['surface_route']['value'], '/hermeneutic-admin')
        self.assertEqual(readonly_info['read_route']['value'], '/api/admin/identity/governance')
        self.assertEqual(readonly_info['update_route']['value'], '/api/admin/identity/governance')
        self.assertIn('/hermeneutic-admin', readonly_info['operator_scope']['value'])
        self.assertFalse(readonly_info['surface_route']['is_editable'])

    def test_get_section_readonly_info_other_sections_stays_empty_in_fourth_phase12_slice(self) -> None:
        self.assertEqual(runtime_settings.get_section_readonly_info('database'), {})

    def test_get_section_readonly_info_exposed_sections_use_readonly_item_shape(self) -> None:
        expected_non_empty = {
            'main_model',
            'arbiter_model',
            'summary_model',
            'stimmung_agent_model',
            'validation_agent_model',
            'services',
            'identity_governance',
        }
        expected_empty = {
            'embedding',
            'database',
            'resources',
        }

        for section in expected_non_empty:
            readonly_info = runtime_settings.get_section_readonly_info(section)
            self.assertTrue(readonly_info, section)
            for item in readonly_info.values():
                self.assertEqual(set(item.keys()), {'label', 'value', 'is_editable', 'source'})
                self.assertFalse(item['is_editable'])

        for section in expected_empty:
            self.assertEqual(runtime_settings.get_section_readonly_info(section), {}, section)


if __name__ == '__main__':
    unittest.main()
