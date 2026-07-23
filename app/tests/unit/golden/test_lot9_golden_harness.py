from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import assistant_turn_state
from core import continuity_capsule
from observability import admin_log_projection
from observability import main_payload_manifest
from observability import observability_payload_guard
from tests.support import lot9_content_free_harness
from tests.support import lot9_route_map_contract
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


EXPECTED_MANIFEST_SECTIONS = frozenset(
    {
        'assistant_output_policy',
        'budgets',
        'continuity_capsule',
        'conversation_id_present',
        'conversation_state',
        'final_response_lock',
        'hash_policy',
        'lane_conflicts',
        'lane_statuses',
        'main_model_called',
        'messages',
        'provider',
        'raw_flags',
        'runtime_settings',
        'schema_version',
        'scope',
        'turn_id_present',
        'windows',
    }
)
EXPECTED_WINDOW_SECTIONS = frozenset(
    {
        'agenda_recent_dialogue',
        'biblio_recent_dialogue',
        'conversation',
        'hermeneutic_node',
        'identity_staging',
        'memory',
        'prompt_final',
        'recent_context',
        'recent_window',
        'summary',
    }
)


def assert_manifest_capsule_contract(manifest: dict) -> None:
    if frozenset(manifest) != EXPECTED_MANIFEST_SECTIONS:
        raise AssertionError('manifest sections changed')
    if frozenset(manifest.get('windows', {})) != EXPECTED_WINDOW_SECTIONS:
        raise AssertionError('manifest windows changed')
    capsule = manifest.get('continuity_capsule', {})
    lane = manifest.get('lane_statuses', {}).get('continuity_capsule', {})
    if capsule.get('status') != lane.get('status'):
        raise AssertionError('capsule lane status mismatch')
    if capsule.get('injected_count') != lane.get('injected_count'):
        raise AssertionError('capsule lane cardinality mismatch')
    if capsule.get('injected_count') != 1:
        raise AssertionError('capsule cardinality changed')
    capsule_messages = [
        message
        for message in manifest.get('messages', ())
        if 'continuity_capsule' in message.get('logical_roles', ())
    ]
    if len(capsule_messages) != 1:
        raise AssertionError('capsule manifest message cardinality changed')
    if capsule_messages[0].get('provider_role') != 'system':
        raise AssertionError('capsule provider role changed')
    if any(value is not False for value in manifest.get('raw_flags', {}).values()):
        raise AssertionError('raw manifest flag enabled')
    if capsule.get('raw_capsule_content_included') is not False:
        raise AssertionError('raw capsule flag enabled')


class Lot9GoldenHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def test_chat_fixture_covers_non_stream_stream_and_single_persistence(self) -> None:
        for stream_req in (False, True):
            with self.subTest(stream_req=stream_req):
                case = server_chat_pipeline.exercise_chat_route_surface(
                    self.server,
                    stream_req=stream_req,
                )
                observed = case['observed']
                self.assertEqual(case['response'].status_code, 200)
                self.assertEqual(len(observed['save_calls']), 2)
                self.assertEqual(
                    [message['role'] for message in observed['save_calls'][0]['messages']],
                    ['user'],
                )
                self.assertEqual(
                    [message['role'] for message in observed['save_calls'][1]['messages']],
                    ['user', 'assistant'],
                )
                self.assertEqual(
                    sum(message['role'] == 'assistant' for message in case['conversation']['messages']),
                    1,
                )
                main_provider_calls = [
                    call
                    for call in case['provider_calls']
                    if call['model'] == 'openrouter/runtime-main-model'
                ]
                self.assertEqual(
                    main_provider_calls,
                    [
                        {
                            'model': 'openrouter/runtime-main-model',
                            'stream': stream_req,
                        }
                    ],
                )
                if stream_req:
                    self.assertEqual(case['response_bytes'].count(b'\x1e'), 1)
                    self.assertEqual(case['terminal']['event'], 'done')
                    self.assertTrue(case['terminal']['updated_at'])
                    self.assertEqual(case['visible_text'], case['assistant_text'])
                    terminal_offset = case['response_bytes'].index(b'\x1e')
                    visible = case['response_bytes'][:terminal_offset]
                    terminal = case['response_bytes'][terminal_offset:]
                    violations = (
                        visible,
                        case['response_bytes'] + terminal,
                        terminal + visible,
                    )
                    for violation in violations:
                        with self.assertRaises(AssertionError):
                            server_chat_pipeline.assert_single_done_terminal(violation)
                else:
                    self.assertEqual(case['response'].get_json()['text'], case['assistant_text'])

    def test_chat_fixture_covers_persistence_error_and_provider_free_overrides(self) -> None:
        failed = server_chat_pipeline.exercise_chat_llm_surface(
            surface='normal_stream',
            persistence='negative',
        )
        self.assertIsNone(failed['raised_exception'])
        self.assertEqual(failed['observed']['save_calls'], 1)
        self.assertEqual(failed['observed']['durable_snapshots'], [])
        self.assertEqual(failed['observed']['post_effect_sequence'], [])
        self.assertEqual(
            failed['terminal'],
            {'event': 'error', 'error_code': 'conversation_persist_failed'},
        )

        answer_override = server_chat_pipeline.exercise_chat_llm_surface(
            surface='override_non_stream',
        )
        presence_override = server_chat_pipeline.exercise_chat_llm_surface(
            surface='override_stream',
            regime='presence',
        )
        for case in (answer_override, presence_override):
            with self.subTest(regime=case['regime'], stream=case['stream_req']):
                self.assertIsNone(case['raised_exception'])
                self.assertEqual(case['observed']['post_calls'], 0)
                self.assertEqual(case['observed']['secret_calls'], 0)
                self.assertEqual(case['observed']['url_calls'], 0)
                self.assertEqual(case['observed']['save_calls'], 1)
                self.assertEqual(
                    sum(message['role'] == 'assistant' for message in case['conversation']['messages']),
                    1,
                )
        self.assertEqual(presence_override['visible_text'], '...')
        self.assertEqual(presence_override['assistant_text'], '...')
        self.assertEqual(
            presence_override['conversation']['messages'][-1]['meta'],
            assistant_turn_state.build_dialogic_presence_assistant_turn_meta(),
        )
        self.assertEqual(presence_override['terminal']['event'], 'done')

    def test_route_map_is_exact_by_family_method_endpoint_and_guard(self) -> None:
        actual = lot9_route_map_contract.route_contracts_from_app(self.server.app)
        self.assertEqual(len(actual), 122)
        lot9_route_map_contract.assert_exact_route_contract(actual)

        client = self.server.app.test_client()
        original_log_event = self.server.admin_logs.log_event
        self.server.admin_logs.log_event = lambda *_args, **_kwargs: None
        try:
            admin_denied = client.get(
                '/api/admin/lot9-synthetic-probe',
                environ_base={'REMOTE_ADDR': '198.51.100.24'},
            )
            tool_denied = client.post(
                '/api/tools/image-generation',
                json={},
                environ_base={'REMOTE_ADDR': '198.51.100.24'},
            )
        finally:
            self.server.admin_logs.log_event = original_log_event
        self.assertEqual(admin_denied.status_code, 403)
        self.assertEqual(tool_denied.status_code, 403)

    def test_route_map_validator_rejects_controlled_mutations(self) -> None:
        expected = list(lot9_route_map_contract.EXPECTED_ROUTE_CONTRACTS)
        variants = []
        variants.append(expected[1:])
        method_changed = list(expected)
        row = list(method_changed[0])
        row[1] = ('POST',)
        method_changed[0] = tuple(row)
        variants.append(method_changed)
        family_changed = list(expected)
        row = list(family_changed[0])
        row[3] = 'synthetic_wrong_family'
        family_changed[0] = tuple(row)
        variants.append(family_changed)
        guard_changed = list(expected)
        row = list(guard_changed[0])
        row[4] = lot9_route_map_contract.ADMIN_PROXY_OR_LOOPBACK
        guard_changed[0] = tuple(row)
        variants.append(guard_changed)
        variants.append(
            expected
            + [
                (
                    '/api/lot9-synthetic-added',
                    ('GET',),
                    'lot9_synthetic_added',
                    'health_and_technical_surfaces',
                    lot9_route_map_contract.PUBLIC_AUTHENTICATED,
                )
            ]
        )
        for mutated in variants:
            with self.subTest(mutated_rows=len(mutated)):
                with self.assertRaises(AssertionError):
                    lot9_route_map_contract.assert_exact_route_contract(mutated)

    def test_manifest_and_capsule_golden_is_structured_and_content_free(self) -> None:
        capsule_text = 'ARTIFICIAL_RUNTIME_CAPSULE_GOLDEN_SENTINEL'
        capsule = continuity_capsule.resolve_continuity_capsule(
            enabled=True,
            content=capsule_text,
            version='continuity_capsule_v1',
            max_chars=160,
        )
        prompt_messages = [
            {'role': 'system', 'content': 'Artificial system instruction.'},
            {'role': 'user', 'content': 'Artificial current turn.'},
        ]
        before = main_payload_manifest.capture_message_refs(prompt_messages)
        self.assertTrue(continuity_capsule.inject_continuity_capsule(prompt_messages, capsule))
        sources = main_payload_manifest.message_sources_for_new_messages(
            prompt_messages,
            before,
            logical_roles=(continuity_capsule.LOGICAL_ROLE,),
            origin=continuity_capsule.ORIGIN,
            origin_stage=continuity_capsule.ORIGIN_STAGE,
            content_kind=continuity_capsule.CONTENT_KIND,
        )
        manifest = main_payload_manifest.build_main_payload_manifest(
            conversation={
                'id': 'conv-lot9-golden',
                'messages': [{'role': 'user', 'content': 'Artificial saved turn.'}],
            },
            prompt_messages=prompt_messages,
            runtime_main_model='synthetic-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=512,
            stream_req=False,
            assistant_output_policy=SimpleNamespace(allow_structure=False, allow_code=False),
            assistant_response_override=None,
            turn_id='turn-lot9-golden',
            message_sources=sources,
            count_tokens_func=lambda messages, _model: 10 * len(messages),
            prompt_soft_token_limit=4000,
            continuity_capsule_result=capsule,
        )
        assert_manifest_capsule_contract(manifest)
        decision = observability_payload_guard.guard_payload(manifest)
        projected, _redaction = admin_log_projection.project_payload(manifest)
        self.assertTrue(decision.accepted)
        encoded = json.dumps(
            {'manifest': manifest, 'guarded': decision.payload, 'projected': projected},
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertNotIn(capsule_text, encoded)

        missing_section = copy.deepcopy(manifest)
        missing_section.pop('continuity_capsule')
        inconsistent_capsule = copy.deepcopy(manifest)
        inconsistent_capsule['continuity_capsule']['injected_count'] = 2
        raw_flag = copy.deepcopy(manifest)
        raw_flag['raw_flags']['raw_message_included'] = True
        for mutated in (missing_section, inconsistent_capsule, raw_flag):
            with self.assertRaises(AssertionError):
                assert_manifest_capsule_contract(mutated)

    def test_observability_matrix_accepts_refuses_and_redacts_expected_forms(self) -> None:
        for case in lot9_content_free_harness.OBSERVABILITY_MATRIX:
            with self.subTest(case_id=case['case_id']):
                decision = observability_payload_guard.guard_payload(case['payload'])
                projected, _redaction = admin_log_projection.project_payload(case['payload'])
                self.assertEqual(decision.accepted, case['accepted'])
                encoded = json.dumps(
                    {'guarded': decision.payload, 'projected': projected},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                self.assertNotIn(lot9_content_free_harness.SYNTHETIC_RAW_SENTINEL, encoded)

        mutated = dict(lot9_content_free_harness.OBSERVABILITY_MATRIX[0]['payload'])
        mutated['message'] = lot9_content_free_harness.SYNTHETIC_RAW_SENTINEL
        self.assertFalse(observability_payload_guard.guard_payload(mutated).accepted)

    def test_common_jsonl_smoke_is_deterministic_and_rejects_content(self) -> None:
        safe_record = {
            'schema_version': lot9_content_free_harness.SMOKE_SCHEMA_VERSION,
            'case_id': 'LOT9.CHAT.STREAM',
            'status': 'pass',
            'reason_code': 'contract_preserved',
            'checks': {
                'single_terminal': True,
                'single_assistant': True,
            },
            'counts': {
                'assistant_messages': 1,
                'terminal_events': 1,
            },
            'identifiers': ['chat', 'stream'],
        }
        encoded = lot9_content_free_harness.encode_smoke_jsonl([safe_record])
        parsed = lot9_content_free_harness.parse_smoke_jsonl(encoded)
        self.assertEqual(
            lot9_content_free_harness.encode_smoke_jsonl(parsed),
            encoded,
        )
        self.assertEqual(len(encoded.splitlines()), 1)
        self.assertIsInstance(json.loads(encoded), dict)

        violations = (
            '{not-json}',
            json.dumps({**safe_record, 'prompt': lot9_content_free_harness.SYNTHETIC_RAW_SENTINEL}),
            json.dumps(
                {
                    **safe_record,
                    'reason_code': lot9_content_free_harness.SYNTHETIC_RAW_SENTINEL,
                }
            ),
            json.dumps({**safe_record, 'reason_code': 'https://example.invalid/private'}),
            json.dumps({**safe_record, 'checks': {'single_terminal': 'yes'}}),
        )
        for violation in violations:
            with self.subTest(violation=violation[:24]):
                with self.assertRaises(ValueError):
                    lot9_content_free_harness.parse_smoke_jsonl(violation)


if __name__ == '__main__':
    unittest.main()
