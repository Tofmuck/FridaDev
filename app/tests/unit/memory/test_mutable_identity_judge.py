from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from memory import mutable_identity_judge
from memory import mutable_identity_judge_v2


def _window_pairs() -> list[dict[str, dict[str, str]]]:
    return [
        {
            'user': {
                'role': 'user',
                'content': f'user full content {index}',
                'timestamp': f'2026-05-25T13:0{index}:00Z',
            },
            'assistant': {
                'role': 'assistant',
                'content': f'assistant full content {index}',
                'temporal_source_guard': 'weak_relative_temporal_claim_present' if index == 3 else '',
            },
        }
        for index in range(1, 6)
    ]


def _identities() -> dict[str, dict[str, str]]:
    return {
        'llm': {'static': 'Frida static', 'mutable_current': 'Frida mutable current'},
        'user': {'static': 'User static', 'mutable_current': 'User mutable current'},
    }


def _budget() -> dict[str, int]:
    return {'target_chars': 3000, 'max_chars': 3300}


def _valid_contract() -> dict[str, Any]:
    return {
        'schema_version': 'mutable_judge_v1',
        'meta': {
            'execution_status': 'complete',
            'window_pairs_count': 5,
            'window_complete': True,
        },
        'verdicts': [
            {
                'subject': 'user',
                'verdict': 'persist',
                'operation': 'add',
                'proposition': 'User keeps a durable boundary.',
                'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                'reason_code': 'explicit_self_limit_continuity',
                'continuity_kind': 'limit',
                'source_refs': ['pair_03'],
                'guard_notes': ['not_task_local'],
            },
            {
                'subject': 'llm',
                'verdict': 'no_change',
                'operation': '',
                'proposition': '',
                'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                'reason_code': 'no_mutable_identity_signal',
                'continuity_kind': 'none',
                'source_refs': [],
                'guard_notes': [],
            },
        ],
    }


def _valid_v2_contract() -> dict[str, Any]:
    return {
        'schema_version': 'mutable_judge_v2',
        'meta': {
            'execution_status': 'complete',
            'window_pairs_count': 5,
            'window_complete': True,
        },
        'verdicts': [
            {
                'subject': 'user',
                'verdict': 'add',
                'proposition': 'Tof tient une frontiere nette entre sa pensee et la voix de Frida.',
                'reason_code': 'explicit_self_limit_continuity',
                'continuity_kind': 'limit',
                'source_refs': ['pair_03'],
                'guard_notes': ['not_task_local'],
            },
            {
                'subject': 'llm',
                'verdict': 'no_change',
                'proposition': '',
                'reason_code': 'no_mutable_identity_signal',
                'continuity_kind': 'none',
                'source_refs': [],
                'guard_notes': [],
            },
        ],
    }


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


class MutableIdentityJudgeTests(unittest.TestCase):
    def test_prompt_lists_canonical_continuity_and_reason_code_families(self) -> None:
        prompt = mutable_identity_judge.load_prompt()

        for continuity_kind in ('identity', 'relation', 'value', 'limit', 'posture', 'tension', 'none'):
            self.assertIn(f'`{continuity_kind}`', prompt)
        for reason_code in (
            'explicit_self_limit_continuity',
            'mutable_tightening',
            'no_mutable_identity_signal',
            'relation_tension_open',
            'project_policy_not_identity',
        ):
            self.assertIn(f'`{reason_code}`', prompt)
        self.assertIn('Technical runtime reason codes are not valid model-output', prompt)
        self.assertIn('`judge_timeout`', prompt)
        self.assertIn('`mutable_content_too_long`', prompt)
        self.assertIn('`pair_05`', prompt)
        self.assertIn('return at least one verdict for `user` and at least one verdict for `llm`', prompt)
        self.assertIn('write every non-empty human-readable identity formulation in French', prompt)
        self.assertIn('`proposition`, `target` and every `targets` item', prompt)
        self.assertIn('canonical code form', prompt)
        self.assertIn('every item must be a short code', prompt)
        self.assertIn('never write phrases', prompt)
        self.assertIn('Never produce an incomplete `persist` verdict', prompt)
        self.assertIn('`clear_obsolete` is the only', prompt)
        self.assertIn('`proposition = ""` is normal', prompt)
        self.assertIn('current_mutables.<subject>.propositions[].ref', prompt)
        self.assertIn('set `target_ref` to one current proposition ref', prompt)
        self.assertIn('set `target_refs` to at least two current proposition refs', prompt)

    def test_build_judge_input_contains_complete_window_identities_and_no_scores(self) -> None:
        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
            source_annotations={
                'source_summary': {'user': {'weak_relative_source_count': 1}},
                'raw_note': 'this annotation has raw words and must be hashed',
            },
        )

        self.assertEqual(judge_input['schema_version'], 'mutable_identity_judge_input_v1')
        self.assertEqual(len(judge_input['window_pairs']), 5)
        self.assertEqual(judge_input['window_pairs'][2]['id'], 'pair_03')
        self.assertEqual(judge_input['window_pairs'][2]['user']['content'], 'user full content 3')
        self.assertEqual(judge_input['window_pairs'][2]['assistant']['content'], 'assistant full content 3')
        self.assertEqual(
            judge_input['window_pairs'][2]['assistant']['temporal_source_guard'],
            'weak_relative_temporal_claim_present',
        )
        self.assertEqual(judge_input['identities']['llm']['static'], 'Frida static')
        self.assertEqual(judge_input['identities']['llm']['mutable_current'], 'Frida mutable current')
        self.assertEqual(judge_input['identities']['user']['static'], 'User static')
        self.assertEqual(judge_input['identities']['user']['mutable_current'], 'User mutable current')
        self.assertEqual(
            judge_input['current_mutables']['llm']['propositions'],
            [{'ref': 'llm_01', 'text': 'Frida mutable current'}],
        )
        self.assertEqual(
            judge_input['current_mutables']['user']['propositions'],
            [{'ref': 'user_01', 'text': 'User mutable current'}],
        )
        self.assertEqual(judge_input['mutable_budget'], _budget())
        self.assertTrue(judge_input['judgment_rules']['python_must_not_score_identity'])
        self.assertTrue(judge_input['judgment_rules']['static_writes_forbidden'])
        self.assertIn('persistence', judge_input['judgment_rules']['model_output_reason_codes'])
        self.assertIn('window_too_large', judge_input['judgment_rules']['technical_reason_codes_not_model_output'])
        self.assertTrue({'strength', 'frequency_norm', 'recency_norm', 'support_pairs'}.isdisjoint(_collect_keys(judge_input)))
        self.assertTrue({'memories', 'summaries', 'identity_evidence', 'candidates'}.isdisjoint(_collect_keys(judge_input)))
        self.assertEqual(set(judge_input['source_annotations']['raw_note'].keys()), {'chars', 'sha256_12'})

    def test_build_openrouter_payload_uses_mutable_judge_metadata(self) -> None:
        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
        )
        payload = mutable_identity_judge.build_openrouter_payload(
            judge_input,
            model_settings={
                'model': 'anthropic/claude-haiku-4.5',
                'temperature': 0.0,
                'top_p': 1.0,
                'max_tokens': 1400,
            },
            system_prompt='judge prompt',
        )

        self.assertEqual(payload['metadata']['frida_caller'], 'mutable_identity_judge')
        self.assertEqual(payload['metadata']['frida_slot'], 'identity_periodic_model')
        self.assertEqual(payload['trace']['generation_name'], 'FridaDev / Mutable Identity Judge')
        self.assertEqual(payload['response_format']['type'], 'json_schema')
        self.assertTrue(payload['response_format']['json_schema']['strict'])
        self.assertEqual(payload['response_format']['json_schema']['name'], 'mutable_judge_v1')
        self.assertFalse(payload['response_format']['json_schema']['schema']['additionalProperties'])
        self.assertEqual(payload['provider']['require_parameters'], True)
        verdict_schema = payload['response_format']['json_schema']['schema']['properties']['verdicts']['items']
        self.assertEqual(payload['response_format']['json_schema']['schema']['properties']['verdicts']['minItems'], 1)
        self.assertEqual(payload['provider']['order'], ['anthropic'])
        self.assertFalse(verdict_schema['additionalProperties'])
        self.assertIn('persist', verdict_schema['properties']['verdict']['enum'])
        self.assertIn('raise_tension', verdict_schema['properties']['verdict']['enum'])
        self.assertIn('clear_obsolete', verdict_schema['properties']['operation']['enum'])
        self.assertIn('', verdict_schema['properties']['operation']['enum'])
        self.assertIn('target_ref', verdict_schema['required'])
        self.assertIn('target_refs', verdict_schema['required'])
        self.assertEqual(verdict_schema['properties']['target_ref']['type'], 'string')
        self.assertEqual(verdict_schema['properties']['target_refs']['items']['type'], 'string')
        self.assertIn('pair_05', verdict_schema['properties']['source_refs']['items']['enum'])
        self.assertIn('explicit_self_limit_continuity', verdict_schema['properties']['reason_code']['enum'])
        self.assertNotIn('empty_proposition', verdict_schema['properties']['reason_code']['enum'])
        user_payload = json.loads(payload['messages'][1]['content'])
        self.assertEqual(user_payload['window_pairs'][0]['user']['content'], 'user full content 1')
        self.assertTrue({'strength', 'frequency_norm', 'recency_norm', 'support_pairs'}.isdisjoint(_collect_keys(user_payload)))

    def test_valid_contract_is_accepted_and_observability_is_content_free(self) -> None:
        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(
            _valid_contract(),
            mutable_budget=_budget(),
        )

        self.assertEqual(reason, '')
        self.assertIsNotNone(validated)
        observability = mutable_identity_judge.build_judge_observability(validated)
        self.assertEqual(observability['verdict_counts'], {'persist': 1, 'no_change': 1})
        self.assertEqual(observability['subjects_seen'], ['llm', 'user'])
        self.assertEqual(observability['subjects_touched'], ['user'])
        self.assertEqual(observability['operation_kinds'], ['add'])
        self.assertEqual(observability['source_refs_count'], 1)
        self.assertEqual(observability['guard_notes_count'], 1)
        self.assertNotIn('User keeps a durable boundary.', repr(observability))

    def test_contract_without_user_or_llm_verdict_is_rejected(self) -> None:
        payload = _valid_contract()
        payload['verdicts'] = [payload['verdicts'][0]]

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

    def test_no_change_cannot_coexist_with_other_verdict_for_same_subject(self) -> None:
        payload = _valid_contract()
        payload['verdicts'].append(
            {
                'subject': 'user',
                'verdict': 'no_change',
                'operation': '',
                'proposition': '',
                'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                'reason_code': 'no_mutable_identity_signal',
                'continuity_kind': 'none',
                'source_refs': [],
                'guard_notes': [],
            }
        )

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

    def test_raise_tension_cannot_carry_persistence_operation(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'raise_tension',
            'operation': 'add',
            'proposition': 'User has a tension.',
            'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'relation_tension_open',
            'continuity_kind': 'tension',
            'source_refs': ['pair_02'],
            'guard_notes': ['operator_surface_future'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'invalid_operation')

    def test_raise_tension_valid_contract_has_no_persistent_operation_in_observability(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'raise_tension',
            'operation': '',
            'proposition': '',
            'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'relation_tension_open',
            'continuity_kind': 'tension',
            'source_refs': ['pair_02'],
            'guard_notes': ['operator_surface_future'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertEqual(reason, '')
        observability = mutable_identity_judge.build_judge_observability(validated)
        self.assertEqual(observability['operation_kinds'], [])
        self.assertEqual(observability['persistent_operation_count'], 0)
        self.assertEqual(observability['verdict_counts']['raise_tension'], 1)

    def test_reject_defer_and_no_change_are_valid_without_persistence_fields(self) -> None:
        cases = [
            ('reject', 'task_local_not_identity', 'none'),
            ('defer', 'insufficient_context', 'posture'),
            ('no_change', 'no_mutable_identity_signal', 'none'),
        ]
        for verdict, reason_code, continuity_kind in cases:
            with self.subTest(verdict=verdict):
                payload = _valid_contract()
                payload['verdicts'][0] = {
                    'subject': 'user',
                    'verdict': verdict,
                    'operation': '',
                    'proposition': '',
                    'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                    'reason_code': reason_code,
                    'continuity_kind': continuity_kind,
                    'source_refs': ['pair_01'] if verdict != 'no_change' else [],
                    'guard_notes': ['not_persisted'] if verdict != 'no_change' else [],
                }

                validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

                self.assertEqual(reason, '')
                self.assertIsNotNone(validated)
                observability = mutable_identity_judge.build_judge_observability(validated)
                self.assertEqual(observability['operation_kinds'], [])
                self.assertEqual(observability['persistent_operation_count'], 0)
                expected_count = 2 if verdict == 'no_change' else 1
                self.assertEqual(observability['verdict_counts'][verdict], expected_count)

    def test_persist_with_invalid_operation_is_rejected(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0]['operation'] = 'raise_tension'

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'invalid_operation')

    def test_model_output_cannot_use_technical_reason_code(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0]['reason_code'] = 'judge_timeout'

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

    def test_persistent_reason_code_must_match_operation(self) -> None:
        cases = [
            ('add_cannot_use_merge_reason', 'add', 'mutable_merge'),
            ('add_cannot_use_tighten_reason', 'add', 'mutable_tightening'),
            ('add_cannot_use_clear_reason', 'add', 'mutable_obsolete_explicitly_removed'),
            ('tighten_requires_tighten_reason', 'tighten', 'explicit_self_limit_continuity'),
            ('merge_requires_merge_reason', 'merge', 'explicit_self_limit_continuity'),
            ('clear_requires_obsolete_reason', 'clear_obsolete', 'explicit_self_limit_continuity'),
        ]
        for label, operation, reason_code in cases:
            with self.subTest(label=label):
                payload = _valid_contract()
                payload['verdicts'][0]['operation'] = operation
                payload['verdicts'][0]['reason_code'] = reason_code
                if operation == 'tighten':
                    payload['verdicts'][0]['target'] = 'mut_user_01'
                if operation == 'merge':
                    payload['verdicts'][0]['target'] = ''
                    payload['verdicts'][0]['targets'] = ['mut_user_01', 'mut_user_02']
                if operation == 'clear_obsolete':
                    payload['verdicts'][0]['proposition'] = ''
                    payload['verdicts'][0]['target'] = 'mut_user_01'

                validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

                self.assertIsNone(validated)
                self.assertEqual(reason, 'invalid_operation')

    def test_clear_obsolete_allows_empty_proposition_with_target(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'clear_obsolete',
            'proposition': '',
            'target': 'User keeps a durable boundary.',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'mutable_obsolete_explicitly_removed',
            'continuity_kind': 'limit',
            'source_refs': ['pair_03'],
            'guard_notes': ['explicitly_removed'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertEqual(reason, '')
        self.assertIsNotNone(validated)
        self.assertEqual(validated['verdicts'][0]['operation'], 'clear_obsolete')
        self.assertEqual(validated['verdicts'][0]['proposition'], '')

    def test_tighten_and_merge_accept_stable_target_refs(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'tighten',
            'proposition': 'User keeps a sharper boundary.',
            'target': '',
            'targets': [],
            'target_ref': 'user_01',
            'target_refs': [],
            'reason_code': 'mutable_tightening',
            'continuity_kind': 'limit',
            'source_refs': ['pair_03'],
            'guard_notes': ['not_task_local'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertEqual(reason, '')
        self.assertEqual(validated['verdicts'][0]['target_ref'], 'user_01')

        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'merge',
            'proposition': 'User keeps a merged boundary.',
            'target': '',
            'targets': [],
            'target_ref': '',
            'target_refs': ['user_01', 'user_02'],
            'reason_code': 'mutable_merge',
            'continuity_kind': 'limit',
            'source_refs': ['pair_03'],
            'guard_notes': ['not_task_local'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertEqual(reason, '')
        self.assertEqual(validated['verdicts'][0]['target_refs'], ['user_01', 'user_02'])

    def test_target_ref_must_match_subject_prefix(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'tighten',
            'proposition': 'User keeps a sharper boundary.',
            'target': '',
            'targets': [],
            'target_ref': 'llm_01',
            'target_refs': [],
            'reason_code': 'mutable_tightening',
            'continuity_kind': 'limit',
            'source_refs': ['pair_03'],
            'guard_notes': ['not_task_local'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'target_ref_invalid')

    def test_non_persistent_verdict_cannot_use_persistence_reason_code(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'reject',
            'operation': '',
            'proposition': '',
            'target': '',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'explicit_self_limit_continuity',
            'continuity_kind': 'limit',
            'source_refs': ['pair_02'],
            'guard_notes': ['not_persisted'],
        }

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

    def test_incompatible_persistent_operations_for_same_subject_are_rejected(self) -> None:
        cases = []

        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'tighten',
            'proposition': 'User keeps a sharper boundary.',
            'target': 'mut_user_01',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'mutable_tightening',
            'continuity_kind': 'limit',
            'source_refs': ['pair_02'],
            'guard_notes': ['not_task_local'],
        }
        payload['verdicts'].append(
            {
                'subject': 'user',
                'verdict': 'persist',
                'operation': 'tighten',
                'proposition': 'User keeps the same sharper boundary.',
                'target': 'mut_user_01',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                'reason_code': 'mutable_tightening',
                'continuity_kind': 'limit',
                'source_refs': ['pair_03'],
                'guard_notes': ['not_task_local'],
            }
        )
        cases.append(payload)

        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'tighten',
            'proposition': 'User keeps a sharper boundary.',
            'target': 'mut_user_02',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'mutable_tightening',
            'continuity_kind': 'limit',
            'source_refs': ['pair_02'],
            'guard_notes': ['not_task_local'],
        }
        payload['verdicts'].append(
            {
                'subject': 'user',
                'verdict': 'persist',
                'operation': 'clear_obsolete',
                'proposition': '',
                'target': 'mut_user_02',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                'reason_code': 'mutable_obsolete_explicitly_removed',
                'continuity_kind': 'limit',
                'source_refs': ['pair_03'],
                'guard_notes': ['explicitly_removed'],
            }
        )
        cases.append(payload)

        payload = _valid_contract()
        payload['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'merge',
            'proposition': 'User keeps a merged relation posture.',
            'target': '',
            'targets': ['mut_user_03', 'mut_user_04'],
            'target_ref': '',
            'target_refs': [],
            'reason_code': 'mutable_merge',
            'continuity_kind': 'relation',
            'source_refs': ['pair_02'],
            'guard_notes': ['not_task_local'],
        }
        payload['verdicts'].append(
            {
                'subject': 'user',
                'verdict': 'persist',
                'operation': 'tighten',
                'proposition': 'User keeps a sharper relation posture.',
                'target': 'mut_user_04',
                'targets': [],
                'target_ref': '',
                'target_refs': [],
                'reason_code': 'mutable_tightening',
                'continuity_kind': 'relation',
                'source_refs': ['pair_03'],
                'guard_notes': ['not_task_local'],
            }
        )
        cases.append(payload)

        for payload in cases:
            with self.subTest(payload=payload['verdicts']):
                validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

                self.assertIsNone(validated)
                self.assertEqual(reason, 'impossible_mutation')

    def test_source_refs_and_guard_notes_must_be_content_free_codes(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0]['source_refs'] = ['je suis une source brute']

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

    def test_source_refs_are_limited_to_the_five_pair_window(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0]['source_refs'] = ['pair_99']

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

    def test_source_refs_accept_only_pair_01_to_pair_05(self) -> None:
        payload = _valid_contract()
        payload['verdicts'][0]['source_refs'] = ['pair_01', 'pair_02', 'pair_03', 'pair_04', 'pair_05']

        validated, reason = mutable_identity_judge.validate_mutable_judge_contract(payload)

        self.assertEqual(reason, '')
        self.assertIsNotNone(validated)
        self.assertEqual(validated['verdicts'][0]['source_refs'], ['pair_01', 'pair_02', 'pair_03', 'pair_04', 'pair_05'])

    def test_run_returns_skipped_on_timeout_and_invalid_json(self) -> None:
        original_get_settings = mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings
        original_load_prompt = mutable_identity_judge.load_prompt
        original_post = mutable_identity_judge.requests.post
        original_url = mutable_identity_judge.llm_client.or_chat_completions_url
        original_headers = mutable_identity_judge.llm_client.or_headers_custom
        original_log_provider = mutable_identity_judge.llm_client.log_provider_metadata

        def fake_get_settings():
            return runtime_settings.RuntimeSectionView(
                section='identity_periodic_model',
                payload=runtime_settings.build_env_seed_bundle('identity_periodic_model').payload,
                source='env',
                source_reason='empty_table',
            )

        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
        )

        mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = fake_get_settings
        mutable_identity_judge.load_prompt = lambda _prompt_path=None: 'judge prompt'
        mutable_identity_judge.llm_client.or_chat_completions_url = lambda: 'https://openrouter.test/chat/completions'
        mutable_identity_judge.llm_client.or_headers_custom = (
            lambda *, caller, referer, title: {'Authorization': f'caller={caller}', 'X-Title': title}
        )
        try:
            def timeout_post(*_args, **_kwargs):
                raise mutable_identity_judge.requests.exceptions.Timeout()

            mutable_identity_judge.requests.post = timeout_post
            timeout_result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
            self.assertEqual(timeout_result['status'], 'skipped')
            self.assertEqual(timeout_result['reason_code'], 'judge_timeout')

            class FakeResponse:
                def raise_for_status(self) -> None:
                    return None

                def json(self):
                    return {'choices': [{'message': {'content': 'not json'}}]}

            mutable_identity_judge.requests.post = lambda *_args, **_kwargs: FakeResponse()
            mutable_identity_judge.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
            invalid_result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
            self.assertEqual(invalid_result['status'], 'skipped')
            self.assertEqual(invalid_result['reason_code'], 'judge_invalid_json')

            class FencedJsonResponse:
                def raise_for_status(self) -> None:
                    return None

                def json(self):
                    return {
                        'choices': [
                            {
                                'message': {
                                    'content': '```json\n'
                                    + json.dumps(_valid_contract(), ensure_ascii=False)
                                    + '\n```'
                                }
                            }
                        ]
                    }

            mutable_identity_judge.requests.post = lambda *_args, **_kwargs: FencedJsonResponse()
            fenced_result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
            self.assertEqual(fenced_result['status'], 'ok')
            self.assertEqual(fenced_result['reason_code'], 'judge_complete')
            self.assertEqual(fenced_result['contract']['schema_version'], 'mutable_judge_v1')
        finally:
            mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = original_get_settings
            mutable_identity_judge.load_prompt = original_load_prompt
            mutable_identity_judge.requests.post = original_post
            mutable_identity_judge.llm_client.or_chat_completions_url = original_url
            mutable_identity_judge.llm_client.or_headers_custom = original_headers
            mutable_identity_judge.llm_client.log_provider_metadata = original_log_provider

    def test_run_validation_failure_reports_content_free_empty_proposition_details(self) -> None:
        original_get_settings = mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings
        original_load_prompt = mutable_identity_judge.load_prompt
        original_post = mutable_identity_judge.requests.post
        original_url = mutable_identity_judge.llm_client.or_chat_completions_url
        original_headers = mutable_identity_judge.llm_client.or_headers_custom
        original_log_provider = mutable_identity_judge.llm_client.log_provider_metadata

        def fake_get_settings():
            return runtime_settings.RuntimeSectionView(
                section='identity_periodic_model',
                payload=runtime_settings.build_env_seed_bundle('identity_periodic_model').payload,
                source='env',
                source_reason='empty_table',
            )

        invalid_contract = copy.deepcopy(_valid_contract())
        sensitive_target = 'Mutable cible sensible qui ne doit pas sortir dans observability.'
        invalid_contract['verdicts'][0] = {
            'subject': 'user',
            'verdict': 'persist',
            'operation': 'tighten',
            'proposition': '',
            'target': sensitive_target,
                'targets': [],
                'target_ref': '',
                'target_refs': [],
            'reason_code': 'mutable_tightening',
            'continuity_kind': 'limit',
            'source_refs': ['pair_02'],
            'guard_notes': ['not_task_local'],
        }

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'choices': [{'message': {'content': json.dumps(invalid_contract)}}]}

        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
        )

        mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = fake_get_settings
        mutable_identity_judge.load_prompt = lambda _prompt_path=None: 'judge prompt'
        mutable_identity_judge.requests.post = lambda *_args, **_kwargs: FakeResponse()
        mutable_identity_judge.llm_client.or_chat_completions_url = lambda: 'https://openrouter.test/chat/completions'
        mutable_identity_judge.llm_client.or_headers_custom = (
            lambda *, caller, referer, title: {'Authorization': f'caller={caller}', 'X-Title': title}
        )
        mutable_identity_judge.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
        finally:
            mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = original_get_settings
            mutable_identity_judge.load_prompt = original_load_prompt
            mutable_identity_judge.requests.post = original_post
            mutable_identity_judge.llm_client.or_chat_completions_url = original_url
            mutable_identity_judge.llm_client.or_headers_custom = original_headers
            mutable_identity_judge.llm_client.log_provider_metadata = original_log_provider

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason_code'], 'empty_proposition')
        observability = result['observability']
        self.assertEqual(observability['validation_reason'], 'empty_proposition')
        self.assertEqual(observability['invalid_verdict_index'], 1)
        self.assertEqual(observability['invalid_subject'], 'user')
        self.assertEqual(observability['invalid_verdict'], 'persist')
        self.assertEqual(observability['invalid_operation'], 'tighten')
        self.assertEqual(observability['invalid_reason_code'], 'mutable_tightening')
        self.assertEqual(observability['invalid_proposition_chars'], 0)
        self.assertEqual(observability['invalid_target_chars'], len(sensitive_target))
        self.assertEqual(observability['invalid_targets_count'], 0)
        self.assertEqual(observability['invalid_source_refs_count'], 1)
        self.assertEqual(observability['invalid_guard_notes_count'], 1)
        self.assertNotIn(sensitive_target, repr(observability))
        self.assertNotIn('proposition', set(observability.keys()))
        self.assertNotIn('target', set(observability.keys()))
        self.assertNotIn('targets', set(observability.keys()))

    def test_run_skips_window_too_large_before_provider_call_and_logs_no_text(self) -> None:
        original_get_settings = mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings
        original_load_prompt = mutable_identity_judge.load_prompt
        original_post = mutable_identity_judge.requests.post

        def fake_get_settings():
            return runtime_settings.RuntimeSectionView(
                section='identity_periodic_model',
                payload=runtime_settings.build_env_seed_bundle('identity_periodic_model').payload,
                source='env',
                source_reason='empty_table',
            )

        sensitive_text = 'SENSITIVEWINDOWTEXT-' * 7000
        pairs = _window_pairs()
        for pair in pairs:
            pair['user']['content'] = sensitive_text
            pair['assistant']['content'] = 'assistant answer'
        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=pairs,
            identities=_identities(),
            mutable_budget=_budget(),
        )
        called = {'post': False}

        def forbidden_post(*_args, **_kwargs):
            called['post'] = True
            raise AssertionError('provider must not be called for oversized window')

        mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = fake_get_settings
        mutable_identity_judge.load_prompt = lambda _prompt_path=None: 'judge prompt'
        mutable_identity_judge.requests.post = forbidden_post
        try:
            result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
        finally:
            mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = original_get_settings
            mutable_identity_judge.load_prompt = original_load_prompt
            mutable_identity_judge.requests.post = original_post

        self.assertFalse(called['post'])
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason_code'], 'window_too_large')
        observability = result['observability']
        self.assertGreater(observability['window_chars'], observability['max_window_chars'])
        self.assertIn('payload_chars', observability)
        self.assertIn('estimated_prompt_tokens', observability)
        self.assertIn('max_estimated_prompt_tokens', observability)
        self.assertNotIn('SENSITIVEWINDOWTEXT', repr(observability))

    def test_run_accepts_valid_model_contract(self) -> None:
        original_get_settings = mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings
        original_load_prompt = mutable_identity_judge.load_prompt
        original_post = mutable_identity_judge.requests.post
        original_url = mutable_identity_judge.llm_client.or_chat_completions_url
        original_headers = mutable_identity_judge.llm_client.or_headers_custom
        original_log_provider = mutable_identity_judge.llm_client.log_provider_metadata

        observed = {'payload': None, 'headers': None, 'provider_metadata': None}

        def fake_get_settings():
            return runtime_settings.RuntimeSectionView(
                section='identity_periodic_model',
                payload=runtime_settings.build_env_seed_bundle('identity_periodic_model').payload,
                source='env',
                source_reason='empty_table',
            )

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'choices': [{'message': {'content': json.dumps(_valid_contract())}}]}

        def fake_post(_url, json, headers, timeout):
            observed['payload'] = copy.deepcopy(json)
            observed['headers'] = dict(headers)
            return FakeResponse()

        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
        )

        mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = fake_get_settings
        mutable_identity_judge.load_prompt = lambda _prompt_path=None: 'judge prompt'
        mutable_identity_judge.requests.post = fake_post
        mutable_identity_judge.llm_client.or_chat_completions_url = lambda: 'https://openrouter.test/chat/completions'
        mutable_identity_judge.llm_client.or_headers_custom = (
            lambda *, caller, referer, title: {'Authorization': f'caller={caller}', 'X-Title': title}
        )
        def fake_log_provider(_logger, _event_name, provider_metadata):
            observed['provider_metadata'] = dict(provider_metadata)

        mutable_identity_judge.llm_client.log_provider_metadata = fake_log_provider
        try:
            result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
        finally:
            mutable_identity_judge.runtime_settings.get_identity_periodic_model_settings = original_get_settings
            mutable_identity_judge.load_prompt = original_load_prompt
            mutable_identity_judge.requests.post = original_post
            mutable_identity_judge.llm_client.or_chat_completions_url = original_url
            mutable_identity_judge.llm_client.or_headers_custom = original_headers
            mutable_identity_judge.llm_client.log_provider_metadata = original_log_provider

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['reason_code'], 'judge_complete')
        self.assertEqual(result['contract']['schema_version'], 'mutable_judge_v1')
        self.assertEqual(observed['payload']['metadata']['frida_caller'], 'mutable_identity_judge')
        self.assertEqual(observed['payload']['metadata']['frida_slot'], 'identity_periodic_model')
        self.assertEqual(observed['payload']['response_format']['type'], 'json_schema')
        self.assertTrue(observed['payload']['response_format']['json_schema']['strict'])
        self.assertEqual(observed['payload']['provider']['require_parameters'], True)
        self.assertEqual(observed['payload']['provider']['order'], ['anthropic'])
        self.assertEqual(observed['headers']['Authorization'], 'caller=mutable_identity_judge')
        self.assertEqual(observed['provider_metadata']['provider_caller'], 'mutable_identity_judge')
        self.assertEqual(observed['provider_metadata']['provider_title'], 'FridaDev / Mutable Identity Judge')


class MutableIdentityJudgeV2DormantTests(unittest.TestCase):
    def test_v2_contract_accepts_add_only_and_is_content_free(self) -> None:
        validated, reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(_valid_v2_contract())

        self.assertEqual(reason, '')
        self.assertIsNotNone(validated)
        observability = mutable_identity_judge_v2.build_judge_observability_v2(validated)
        self.assertEqual(observability['schema_version'], 'mutable_judge_v2')
        self.assertEqual(observability['contract_status'], 'dormant_until_lot_b')
        self.assertEqual(observability['verdict_counts'], {'add': 1, 'no_change': 1})
        self.assertEqual(observability['subjects_touched'], ['user'])
        self.assertEqual(observability['operation_kinds'], [])
        self.assertNotIn('frontiere nette', repr(observability))

    def test_v2_refuses_verdicts_outside_no_change_and_add(self) -> None:
        for verdict in ('persist', 'reject', 'defer', 'raise_tension'):
            with self.subTest(verdict=verdict):
                payload = _valid_v2_contract()
                payload['verdicts'][0]['verdict'] = verdict

                validated, reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(payload)

                self.assertIsNone(validated)
                self.assertEqual(reason, 'invalid_verdict')

    def test_v2_no_change_cannot_coexist_with_add_for_same_subject(self) -> None:
        payload = _valid_v2_contract()
        payload['verdicts'].append(
            {
                'subject': 'user',
                'verdict': 'no_change',
                'proposition': '',
                'reason_code': 'already_covered_by_mutable',
                'continuity_kind': 'none',
                'source_refs': [],
                'guard_notes': [],
            }
        )

        validated, reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'invalid_verdict')

    def test_v2_refuses_manager_fields_and_schema_omits_them(self) -> None:
        manager_fields = {'operation', 'target', 'targets', 'target_ref', 'target_refs'}
        payload = _valid_v2_contract()
        payload['verdicts'][0]['operation'] = 'tighten'

        validated, reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(payload)

        self.assertIsNone(validated)
        self.assertEqual(reason, 'schema_invalid')

        response_format = mutable_identity_judge_v2.build_openrouter_payload_v2(
            {'schema_version': 'mutable_identity_judge_input_v1', 'window_pairs': []},
            model_settings={
                'model': 'anthropic/claude-haiku-4.5',
                'temperature': 0.0,
                'top_p': 1.0,
                'max_tokens': 1400,
            },
            system_prompt='judge prompt v2',
        )['response_format']
        schema_keys = _collect_keys(response_format)
        self.assertEqual(response_format['type'], 'json_schema')
        self.assertTrue(response_format['json_schema']['strict'])
        self.assertEqual(response_format['json_schema']['name'], 'mutable_judge_v2')
        self.assertFalse(response_format['json_schema']['schema']['additionalProperties'])
        self.assertTrue(manager_fields.isdisjoint(schema_keys))

    def test_v2_payload_keeps_structured_output_provider_require_parameters_and_anthropic_order(self) -> None:
        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
        )
        payload = mutable_identity_judge_v2.build_openrouter_payload_v2(
            judge_input,
            model_settings={
                'model': 'anthropic/claude-haiku-4.5',
                'temperature': 0.0,
                'top_p': 1.0,
                'max_tokens': 1400,
            },
            system_prompt='judge prompt v2',
        )

        self.assertEqual(payload['response_format']['type'], 'json_schema')
        self.assertTrue(payload['response_format']['json_schema']['strict'])
        self.assertEqual(payload['response_format']['json_schema']['name'], 'mutable_judge_v2')
        self.assertEqual(payload['provider']['require_parameters'], True)
        self.assertEqual(payload['provider']['order'], ['anthropic'])
        self.assertEqual(payload['metadata']['frida_contract_status'], 'dormant_until_lot_b')
        verdict_schema = payload['response_format']['json_schema']['schema']['properties']['verdicts']['items']
        self.assertEqual(set(verdict_schema['properties']['verdict']['enum']), {'add', 'no_change'})
        self.assertNotIn('operation', verdict_schema['properties'])
        self.assertIn('explicit_frida_limit_continuity', verdict_schema['properties']['reason_code']['enum'])
        self.assertNotIn('mutable_tightening', verdict_schema['properties']['reason_code']['enum'])
        self.assertEqual(mutable_identity_judge_v2.JUDGE_WINDOW_MAX_CHARS, 32_000)
        self.assertEqual(mutable_identity_judge_v2.JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT, 12_000)

    def test_v2_prompt_contains_ontology_rules_and_examples(self) -> None:
        prompt = mutable_identity_judge_v2.load_prompt_v2()

        for phrase in (
            'You do not summarize.',
            'You do not psychologize.',
            'You do not maintain a knowledge base.',
            'You do not clean the canon.',
            'You do not rewrite the existing canon.',
            'You seek only declarations of being.',
            'Frida est...',
            'Frida tient...',
            'Frida refuse...',
            'Tof traite... comme...',
            'already covered by static or mutable_current',
        ):
            self.assertIn(phrase, prompt)
        self.assertIn('Never output `operation`.', prompt)
        self.assertIn('Never output `target`, `targets`, `target_ref`, or `target_refs`.', prompt)

    def test_v2_is_dormant_and_active_runtime_payload_remains_v1(self) -> None:
        judge_input = mutable_identity_judge.build_judge_input(
            window_pairs=_window_pairs(),
            identities=_identities(),
            mutable_budget=_budget(),
        )
        active_payload = mutable_identity_judge.build_openrouter_payload(
            judge_input,
            model_settings={
                'model': 'anthropic/claude-haiku-4.5',
                'temperature': 0.0,
                'top_p': 1.0,
                'max_tokens': 1400,
            },
            system_prompt='judge prompt',
        )

        self.assertEqual(mutable_identity_judge.SCHEMA_VERSION, 'mutable_judge_v1')
        self.assertEqual(active_payload['response_format']['json_schema']['name'], 'mutable_judge_v1')
        active_verdict_schema = active_payload['response_format']['json_schema']['schema']['properties']['verdicts']['items']
        self.assertIn('operation', active_verdict_schema['required'])
        self.assertIn('target_ref', active_verdict_schema['required'])
        self.assertIn('persist', active_verdict_schema['properties']['verdict']['enum'])
        self.assertNotEqual(mutable_identity_judge_v2.SCHEMA_VERSION, mutable_identity_judge.SCHEMA_VERSION)


if __name__ == '__main__':
    unittest.main()
