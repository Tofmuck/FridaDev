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

    def assertPromptContentGate(self, item, *, expected_text: str, expected_path: str = '') -> None:
        self.assertFalse(item['is_editable'])
        self.assertIn(item['source'], {'prompt_file', 'app_prompt_file'})
        self.assertTrue(item['content_gate']['required'])
        self.assertFalse(item['content_gate']['raw_content_included'])
        self.assertEqual(item['content_gate']['reason_code'], 'admin_prompt_content_gate_required')
        value = item['value']
        self.assertEqual(value['status'], 'content_gate_required')
        self.assertTrue(value['present'])
        self.assertEqual(value['char_count'], len(expected_text))
        self.assertEqual(value['line_count'], len(expected_text.splitlines()))
        self.assertEqual(value['reason_code'], 'admin_prompt_content_gate_required')
        self.assertFalse(value['raw_content_included'])
        self.assertIn('/readonly-info/', value['content_endpoint'])
        if expected_path:
            self.assertEqual(value['path'], expected_path)
        self.assertNotIn(expected_text[:80], repr(item))

    def test_get_section_readonly_info_main_model_exposes_context_budget_prompts_and_runtime_bricks(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('main_model')
        main_system_prompt = prompt_loader.get_main_system_prompt()
        main_hermeneutical_prompt = prompt_loader.get_main_hermeneutical_prompt()

        self.assertEqual(readonly_info['system_prompt']['label'], 'SYSTEM_PROMPT')
        self.assertPromptContentGate(
            readonly_info['system_prompt'],
            expected_text=main_system_prompt,
            expected_path=config.MAIN_SYSTEM_PROMPT_PATH,
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
        self.assertPromptContentGate(
            readonly_info['hermeneutical_prompt'],
            expected_text=main_hermeneutical_prompt,
            expected_path=config.MAIN_HERMENEUTICAL_PROMPT_PATH,
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
        self.assertNotEqual(
            readonly_info['system_prompt']['value']['char_count'],
            readonly_info['hermeneutical_prompt']['value']['char_count'],
        )
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

    def test_get_section_readonly_info_memory_arbiter_model_exposes_prompt_transport_and_benchmark(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('memory_arbiter_model')

        self.assertEqual(readonly_info['prompt_path']['label'], 'ARBITER_PROMPT_PATH')
        self.assertEqual(readonly_info['prompt_path']['value'], config.ARBITER_PROMPT_PATH)
        self.assertPromptContentGate(
            readonly_info['system_prompt'],
            expected_text=prompt_loader.read_prompt_text(str(config.ARBITER_PROMPT_PATH)),
            expected_path=config.ARBITER_PROMPT_PATH,
        )
        self.assertIn('main_model.title_arbiter', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_arbiter', readonly_info['shared_transport']['value'])
        self.assertEqual(
            readonly_info['benchmark_decision']['value'],
            'benchmark/results/arbiter/2026-05-18-arbiter-final-tournament-summary.md',
        )

    def test_get_section_readonly_info_content_is_separate_from_metadata_gate(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('main_model')
        main_system_prompt = prompt_loader.get_main_system_prompt()
        self.assertNotIn(main_system_prompt[:80], repr(readonly_info['system_prompt']))

        content = runtime_settings.get_section_readonly_info_content('main_model', 'system_prompt')

        self.assertEqual(content['section'], 'main_model')
        self.assertEqual(content['key'], 'system_prompt')
        self.assertEqual(content['content'], main_system_prompt)
        self.assertEqual(content['metadata']['char_count'], len(content['content']))
        self.assertTrue(content['content_gate']['acknowledged'])

    def test_get_section_readonly_info_arbiter_model_documents_identity_legacy_scope(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('arbiter_model')

        self.assertIn('no active model caller', readonly_info['operator_warning']['value'])
        self.assertIn(
            'identity_periodic_model drives mutable_identity_judge',
            readonly_info['active_replacements']['value'],
        )
        self.assertIn('not an effective source', readonly_info['legacy_scope']['value'])

    def test_get_section_readonly_info_identity_extractor_model_exposes_prompt_transport_and_benchmark(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('identity_extractor_model')

        self.assertEqual(
            readonly_info['prompt_path']['label'],
            'IDENTITY_EXTRACTOR_PROMPT_PATH',
        )
        self.assertEqual(readonly_info['prompt_path']['value'], config.IDENTITY_EXTRACTOR_PROMPT_PATH)
        self.assertPromptContentGate(
            readonly_info['system_prompt'],
            expected_text=prompt_loader.read_prompt_text(str(config.IDENTITY_EXTRACTOR_PROMPT_PATH)),
            expected_path=config.IDENTITY_EXTRACTOR_PROMPT_PATH,
        )
        self.assertIn('main_model.title_identity_extractor', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_identity_extractor', readonly_info['shared_transport']['value'])
        self.assertEqual(
            readonly_info['benchmark_decision']['value'],
            'benchmark/results/identity_extractor/2026-05-18-identity-extractor-human-hermeneutic.md',
        )
        self.assertIn('extract_dialogic_context_hints()', readonly_info['transition_note']['value'])
        self.assertIn('never write Identity', readonly_info['transition_note']['value'])
        self.assertIn('sole mutable canon writer', readonly_info['transition_note']['value'])

    def test_get_section_readonly_info_identity_periodic_model_exposes_prompt_transport_and_decision(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('identity_periodic_model')

        self.assertEqual(readonly_info['active_module']['value'], 'mutable_identity_judge_v2_add_only')
        self.assertEqual(readonly_info['runtime_slot']['value'], 'identity_periodic_model')
        self.assertEqual(readonly_info['model_field']['value'], 'identity_periodic_model.model')
        self.assertEqual(readonly_info['caller']['value'], 'mutable_identity_judge')
        self.assertEqual(readonly_info['contract']['value'], 'mutable_judge_v2')
        self.assertEqual(readonly_info['prompt_kind']['value'], 'mutable_identity_judge_v2')
        self.assertIn('json_schema strict=true', readonly_info['structured_output']['value'])
        self.assertIn('add/no_change ontologique', readonly_info['runtime_role']['value'])
        self.assertEqual(
            readonly_info['prompt_path']['label'],
            'IDENTITY_MUTABLE_JUDGE_PROMPT_PATH',
        )
        self.assertEqual(readonly_info['prompt_path']['value'], config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)
        self.assertEqual(
            readonly_info['prompt_loader']['value'],
            'memory.mutable_identity_judge_v2.load_prompt_v2(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)',
        )
        self.assertEqual(
            readonly_info['legacy_prompt_path']['value'],
            config.IDENTITY_PERIODIC_AGENT_PROMPT_PATH,
        )
        self.assertPromptContentGate(
            readonly_info['system_prompt'],
            expected_text=prompt_loader.read_prompt_text(str(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)),
            expected_path=config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH,
        )
        self.assertIn('main_model.title_identity_periodic', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_identity_periodic', readonly_info['shared_transport']['value'])
        self.assertEqual(
            readonly_info['benchmark_decision']['label'],
            'MUTABLE_IDENTITY_JUDGE_GPT52_MODEL_DECISION',
        )
        self.assertEqual(
            readonly_info['benchmark_decision']['value'],
            'app/docs/todo-done/validations/mutable-identity-judge-final-validation-2026-05-25.md',
        )
        self.assertEqual(readonly_info['benchmark_decision']['source'], 'validation_artifact')
        self.assertEqual(
            readonly_info['legacy_benchmark_decision']['label'],
            'IDENTITY_PERIODIC_HAIKU_BENCHMARK_DECISION_LEGACY',
        )
        self.assertEqual(
            readonly_info['legacy_benchmark_decision']['value'],
            'benchmark/results/identity_periodic/2026-05-19-haiku-periodic-decision.md',
        )
        self.assertEqual(readonly_info['legacy_benchmark_decision']['source'], 'legacy_pre_gpt52_cutover')
        self.assertIn('compatibility model slot', readonly_info['doctrine']['value'])

    def test_get_section_readonly_info_summary_model_exposes_prompt_transport_and_benchmark_decision(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('summary_model')

        self.assertNotIn('summary_target_tokens', readonly_info)
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
        self.assertPromptContentGate(
            readonly_info['system_prompt'],
            expected_text=prompt_loader.get_summary_system_prompt(),
            expected_path=config.SUMMARY_SYSTEM_PROMPT_PATH,
        )
        self.assertIn('main_model.title_resumer', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_resumer', readonly_info['shared_transport']['value'])
        self.assertEqual(
            readonly_info['benchmark_decision']['value'],
            'benchmark/results/summary/2026-05-18-summary-human-final.md',
        )

    def test_get_section_readonly_info_stimmung_agent_model_exposes_prompt_and_shared_transport(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('stimmung_agent_model')

        self.assertEqual(readonly_info['prompt_path']['label'], 'STIMMUNG_AGENT_PROMPT_PATH')
        self.assertEqual(readonly_info['prompt_path']['value'], 'prompts/stimmung_agent.txt')
        self.assertEqual(
            readonly_info['prompt_loader']['value'],
            'core.stimmung_agent._load_system_prompt()',
        )
        self.assertPromptContentGate(
            readonly_info['prompt_text'],
            expected_text=prompt_loader.read_prompt_text('prompts/stimmung_agent.txt'),
            expected_path='prompts/stimmung_agent.txt',
        )
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
        self.assertPromptContentGate(
            readonly_info['prompt_text'],
            expected_text=prompt_loader.read_prompt_text('prompts/validation_agent.txt'),
            expected_path='prompts/validation_agent.txt',
        )
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

    def test_get_section_readonly_info_web_reformulation_model_exposes_prompt_and_transport(self) -> None:
        readonly_info = runtime_settings.get_section_readonly_info('web_reformulation_model')
        reformulation_prompt = prompt_loader.get_web_reformulation_prompt()

        self.assertEqual(readonly_info['prompt_path']['value'], runtime_settings.config.WEB_REFORMULATION_PROMPT_PATH)
        self.assertIn('main_model', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.title_web_reformulation', readonly_info['shared_transport']['value'])
        self.assertIn('main_model.referer_web_reformulation', readonly_info['shared_transport']['value'])
        self.assertPromptContentGate(
            readonly_info['system_prompt'],
            expected_text=reformulation_prompt,
            expected_path=runtime_settings.config.WEB_REFORMULATION_PROMPT_PATH,
        )
        self.assertEqual(
            readonly_info['system_prompt']['label'],
            'web_reformulation_system_prompt',
        )
        self.assertEqual(readonly_info['system_prompt']['source'], 'prompt_file')

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
            'identity_extractor_model',
            'memory_arbiter_model',
            'summary_model',
            'web_reformulation_model',
            'stimmung_agent_model',
            'validation_agent_model',
            'identity_governance',
        }
        expected_empty = {
            'biblio_librarian_agent',
            'embedding',
            'database',
            'services',
            'resources',
        }

        for section in expected_non_empty:
            readonly_info = runtime_settings.get_section_readonly_info(section)
            self.assertTrue(readonly_info, section)
            for item in readonly_info.values():
                self.assertTrue(
                    set(item.keys()).issuperset({'label', 'value', 'is_editable', 'source'}),
                    item,
                )
                self.assertFalse(item['is_editable'])

        for section in expected_empty:
            self.assertEqual(runtime_settings.get_section_readonly_info(section), {}, section)


if __name__ == '__main__':
    unittest.main()
