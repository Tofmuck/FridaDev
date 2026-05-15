from __future__ import annotations

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

from observability import chat_turn_logger
from observability import hermeneutic_node_logger
from observability import log_store
from observability import prompt_injection_summary
from core import conversations_prompt_window


class ChatTurnLoggerHermeneuticObservabilityTests(unittest.TestCase):
    def test_hermeneutic_node_insertion_emits_compact_presence_quality_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-hermeneutic-insertion',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            hermeneutic_node_logger.emit_hermeneutic_node_insertion(
                time_input={
                    'schema_version': 'v1',
                    'now_utc_iso': '2026-03-31T09:30:00Z',
                    'timezone': 'Europe/Paris',
                    'now_local_iso': '2026-03-31T11:30:00+02:00',
                    'local_date': '2026-03-31',
                    'local_time': '11:30',
                    'local_weekday': 'tuesday',
                    'day_part_class': 'morning',
                    'day_part_human': 'matin',
                },
                current_mode='shadow',
                memory_retrieved={
                    'retrieved_count': 2,
                },
                memory_arbitration={
                    'status': 'available',
                    'decisions_count': 2,
                    'kept_count': 1,
                    'rejected_count': 1,
                },
                summary_input={
                    'status': 'available',
                },
                identity_input={
                    'frida': {
                        'static': {'content': 'Frida'},
                        'mutable': {
                            'content': 'Frida mutable',
                            'source_trace_id': '11111111-1111-1111-1111-111111111111',
                            'updated_by': 'identity_periodic_agent',
                            'update_reason': 'periodic_agent',
                            'updated_ts': '2026-03-30T12:00:00Z',
                        },
                    },
                    'user': {
                        'static': {'content': ''},
                        'mutable': {
                            'content': 'Utilisateur mutable',
                            'source_trace_id': '22222222-2222-2222-2222-222222222222',
                            'updated_by': 'identity_periodic_agent',
                            'update_reason': 'periodic_agent',
                            'updated_ts': '2026-03-30T12:30:00Z',
                        },
                    },
                },
                recent_context_input={
                    'messages': [{'role': 'user'}, {'role': 'assistant'}],
                },
                recent_window_input={
                    'turn_count': 1,
                    'has_in_progress_turn': False,
                    'max_recent_turns': 5,
                },
                user_turn_input={
                    'schema_version': 'v1',
                    'geste_dialogique_dominant': 'interrogation',
                    'regime_probatoire': {
                        'principe': 'maximal_possible',
                        'types_de_preuve_attendus': ['factuelle', 'dialogique'],
                        'provenances': ['dialogue_trace'],
                        'regime_de_vigilance': 'standard',
                        'composition_probatoire': 'appuyee',
                    },
                    'qualification_temporelle': {
                        'portee_temporelle': 'passee',
                        'ancrage_temporel': 'dialogue_trace',
                    },
                },
                user_turn_signals={
                    'present': True,
                    'ambiguity_present': False,
                    'underdetermination_present': True,
                    'active_signal_families': ['critere'],
                    'active_signal_families_count': 1,
                },
                stimmung_input={
                    'schema_version': 'v1',
                    'present': True,
                    'dominant_tone': 'frustration',
                    'active_tones': [
                        {'tone': 'frustration', 'strength': 6},
                        {'tone': 'confusion', 'strength': 3},
                    ],
                    'stability': 'stable',
                    'shift_state': 'steady',
                    'turns_considered': 4,
                },
                web_input={
                    'enabled': True,
                    'status': 'ok',
                    'activation_mode': 'manual',
                    'reason_code': None,
                    'results_count': 3,
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'hermeneutic_node_insertion')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'ok')
        self.assertTrue(payload['insertion_point_reached'])
        self.assertEqual(payload['mode'], 'shadow')
        self.assertTrue(payload['inputs']['time']['present'])
        self.assertEqual(payload['inputs']['time']['timezone'], 'Europe/Paris')
        self.assertEqual(payload['inputs']['time']['day_part_class'], 'morning')
        self.assertEqual(payload['inputs']['memory_retrieved']['status'], 'ok')
        self.assertEqual(payload['inputs']['memory_retrieved']['reason_code'], '')
        self.assertEqual(payload['inputs']['memory_retrieved']['retrieved_count'], 2)
        self.assertEqual(payload['inputs']['memory_arbitration']['status'], 'available')
        self.assertEqual(payload['inputs']['memory_arbitration']['reason_code'], '')
        self.assertEqual(payload['inputs']['memory_arbitration']['decisions_count'], 2)
        self.assertEqual(payload['inputs']['memory_arbitration']['kept_count'], 1)
        self.assertEqual(payload['inputs']['memory_arbitration']['rejected_count'], 1)
        self.assertEqual(payload['inputs']['summary']['status'], 'available')
        self.assertTrue(payload['inputs']['identity']['frida']['static_present'])
        self.assertFalse(payload['inputs']['identity']['user']['static_present'])
        self.assertTrue(payload['inputs']['identity']['frida']['mutable_present'])
        self.assertTrue(payload['inputs']['identity']['user']['mutable_present'])
        self.assertEqual(payload['inputs']['identity']['frida']['mutable_len'], len('Frida mutable'))
        self.assertEqual(payload['inputs']['identity']['user']['mutable_len'], len('Utilisateur mutable'))
        self.assertNotIn('dynamic_count', payload['inputs']['identity']['frida'])
        self.assertNotIn('dynamic_count', payload['inputs']['identity']['user'])
        self.assertEqual(payload['inputs']['recent_context']['messages_count'], 2)
        self.assertEqual(payload['inputs']['recent_window']['turn_count'], 1)
        self.assertFalse(payload['inputs']['recent_window']['has_in_progress_turn'])
        self.assertEqual(payload['inputs']['recent_window']['max_recent_turns'], 5)
        self.assertTrue(payload['inputs']['user_turn']['present'])
        self.assertEqual(payload['inputs']['user_turn']['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(
            payload['inputs']['user_turn']['regime_probatoire'],
            {
                'principe': 'maximal_possible',
                'types_de_preuve_attendus': ['factuelle', 'dialogique'],
                'provenances': ['dialogue_trace'],
                'regime_de_vigilance': 'standard',
            },
        )
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['portee_temporelle'], 'passee')
        self.assertEqual(
            payload['inputs']['user_turn']['qualification_temporelle']['ancrage_temporel'],
            'dialogue_trace',
        )
        self.assertNotIn('content', payload['inputs']['user_turn'])
        self.assertNotIn('content', payload['inputs']['user_turn']['regime_probatoire'])
        self.assertTrue(payload['inputs']['user_turn_signals']['present'])
        self.assertFalse(payload['inputs']['user_turn_signals']['ambiguity_present'])
        self.assertTrue(payload['inputs']['user_turn_signals']['underdetermination_present'])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families'], ['critere'])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families_count'], 1)
        self.assertTrue(payload['inputs']['stimmung']['present'])
        self.assertEqual(payload['inputs']['stimmung']['dominant_tone'], 'frustration')
        self.assertEqual(
            payload['inputs']['stimmung']['active_tones'],
            [
                {'tone': 'frustration', 'strength': 6},
                {'tone': 'confusion', 'strength': 3},
            ],
        )
        self.assertEqual(payload['inputs']['stimmung']['stability'], 'stable')
        self.assertEqual(payload['inputs']['stimmung']['shift_state'], 'steady')
        self.assertEqual(payload['inputs']['stimmung']['turns_considered'], 4)
        self.assertTrue(payload['inputs']['web']['enabled'])
        self.assertEqual(payload['inputs']['web']['status'], 'ok')
        self.assertEqual(payload['inputs']['web']['activation_mode'], 'manual')
        self.assertEqual(payload['inputs']['web']['reason_code'], '')
        self.assertEqual(payload['inputs']['web']['results_count'], 3)

    def test_memory_prompt_injection_summary_counts_effective_prompt_blocks_without_raw_content(self) -> None:
        prompt_messages = [
            {
                'role': 'system',
                'content': '[Indices contextuels recents]\n- Utilisateur: Christophe Muck (confidence: 0.91)\n- Situation: projet FridaDev (confidence: 0.62)',
            },
            {
                'role': 'system',
                'content': '[Contexte du souvenir — résumé du 2026-04-01 au 2026-04-02]\nRésumé 1\n\n[Contexte du souvenir — résumé du 2026-04-03]\nRésumé 2',
            },
            {
                'role': 'system',
                'content': '[Mémoire — souvenirs pertinents]\n[il y a 2 jours] Utilisateur : Je suis Christophe Muck\n[il y a 1 jour] Assistant : Nous travaillons sur FridaDev',
            },
        ]
        summary = prompt_injection_summary.build_memory_prompt_injection_summary(
            prompt_messages,
            memory_traces=[
                {'candidate_id': 'cand-user', 'content': 'Je suis Christophe Muck', 'parent_summary': {'id': 'summary-1'}},
                {'candidate_id': 'cand-assistant', 'content': 'Nous travaillons sur FridaDev', 'parent_summary': {'id': 'summary-2'}},
            ],
            context_hints=[
                {'content': 'Christophe Muck'},
                {'content': 'projet FridaDev'},
            ],
        )

        self.assertEqual(
            summary,
            {
                'injected': True,
                'injection_class': 'mixed',
                'injection_lanes': ['trace_memory', 'summary_context', 'context_hints'],
                'injection_lane_count': 3,
                'prompt_block_count': 3,
                'trace_memory_injected': True,
                'trace_memory_injected_count': 2,
                'summary_context_injected': True,
                'summary_context_injected_count': 2,
                'memory_traces_injected': True,
                'memory_traces_injected_count': 2,
                'injected_candidate_ids': ['cand-user', 'cand-assistant'],
                'memory_context_injected': True,
                'memory_context_summary_count': 2,
                'injected_traces_with_summary_id_count': 2,
                'injected_traces_with_parent_summary_count': 2,
                'parent_summaries_resolved_count': 2,
                'parent_summaries_injected_count': 2,
                'parent_summaries_injected': [
                    {
                        'summary_id': 'summary-1',
                        'summary_id_sha256_12': '87feb6a997ac',
                        'start_ts': None,
                        'end_ts': None,
                        'linked_trace_count': 1,
                    },
                    {
                        'summary_id': 'summary-2',
                        'summary_id_sha256_12': 'c6d4d52b0c0e',
                        'start_ts': None,
                        'end_ts': None,
                        'linked_trace_count': 1,
                    },
                ],
                'context_hints_injected': True,
                'context_hints_injected_count': 2,
            },
        )
        self.assertNotIn('content', summary)
        self.assertNotIn('preview', summary)

    def test_memory_prompt_injection_summary_classifies_lanes_independently(self) -> None:
        trace_summary = prompt_injection_summary.build_memory_prompt_injection_summary(
            [
                {
                    'role': 'system',
                    'content': conversations_prompt_window.MEMORY_TRACES_BLOCK_HEADER + '\nUtilisateur : preference durable',
                }
            ],
            memory_traces=[{'candidate_id': 'cand-trace', 'content': 'preference durable'}],
            context_hints=[],
        )
        self.assertEqual(trace_summary['injection_class'], 'trace_memory_only')
        self.assertEqual(trace_summary['injection_lanes'], ['trace_memory'])
        self.assertTrue(trace_summary['trace_memory_injected'])
        self.assertEqual(trace_summary['trace_memory_injected_count'], 1)
        self.assertFalse(trace_summary['summary_context_injected'])
        self.assertFalse(trace_summary['context_hints_injected'])

        hints_summary = prompt_injection_summary.build_memory_prompt_injection_summary(
            [
                {
                    'role': 'system',
                    'content': conversations_prompt_window.CONTEXT_HINTS_BLOCK_HEADER + '\n- Utilisateur: projet FridaDev (confidence: 0.90)',
                }
            ],
            memory_traces=[],
            context_hints=[{'content': 'projet FridaDev'}],
        )
        self.assertEqual(hints_summary['injection_class'], 'hints_only')
        self.assertEqual(hints_summary['injection_lanes'], ['context_hints'])
        self.assertFalse(hints_summary['trace_memory_injected'])
        self.assertFalse(hints_summary['summary_context_injected'])
        self.assertTrue(hints_summary['context_hints_injected'])
        self.assertEqual(hints_summary['context_hints_injected_count'], 1)

        summary_context = prompt_injection_summary.build_memory_prompt_injection_summary(
            [
                {
                    'role': 'system',
                    'content': '[Résumé de la période du 2026-04-01]\nRésumé actif',
                }
            ],
            memory_traces=[],
            context_hints=[],
        )
        self.assertEqual(summary_context['injection_class'], 'summary_context_only')
        self.assertEqual(summary_context['injection_lanes'], ['summary_context'])
        self.assertFalse(summary_context['trace_memory_injected'])
        self.assertTrue(summary_context['summary_context_injected'])
        self.assertEqual(summary_context['summary_context_injected_count'], 1)
        self.assertFalse(summary_context['memory_context_injected'])

    def test_stimmung_agent_stage_emits_compact_upstream_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-stimmung-stage',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'stimmung_agent',
                status='error',
                model='openai/gpt-5.4-nano',
                payload={
                    'present': False,
                    'dominant_tone': None,
                    'tones_count': 0,
                    'tones': [],
                    'confidence': 0.0,
                    'decision_source': 'fail_open',
                    'reason_code': 'invalid_json',
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'stimmung_agent')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'error')
        self.assertEqual(payload['model'], 'openai/gpt-5.4-nano')
        self.assertFalse(payload['present'])
        self.assertEqual(payload['tones_count'], 0)
        self.assertEqual(payload['tones'], [])
        self.assertEqual(payload['decision_source'], 'fail_open')
        self.assertEqual(payload['reason_code'], 'invalid_json')
        self.assertNotIn('user_msg', payload)
        self.assertNotIn('prompt', payload)
        self.assertNotIn('raw_output', payload)

    def test_stimmung_prompt_prepared_emits_provider_secondary_fingerprint_without_raw_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-stimmung-prepared-log',
            user_msg='tour utilisateur brut',
            web_search_enabled=False,
        )
        try:
            hermeneutic_node_logger.emit_stimmung_prompt_prepared(
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                messages=[
                    {'role': 'system', 'content': 'PROMPT SYSTEME SENSIBLE'},
                    {'role': 'user', 'content': 'fenetre locale et tour utilisateur brut'},
                ],
                recent_window_input_payload={
                    'schema_version': 'v1',
                    'turn_count': 2,
                    'max_recent_turns': 5,
                    'has_in_progress_turn': True,
                    'turns': [
                        {'messages': [{'role': 'user', 'content': 'historique brut'}]},
                        {'messages': [{'role': 'user', 'content': 'tour utilisateur brut'}]},
                    ],
                },
                temperature=0.1,
                top_p=1.0,
                max_tokens=220,
                timeout_s=10,
                context_window_turns=5,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'stimmung_prompt_prepared')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'ok')
        self.assertEqual(payload['prompt_kind'], 'stimmung_agent_secondary')
        self.assertEqual(payload['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(payload['payload_kind'], 'secondary_stimmung_agent_provider')
        self.assertEqual(payload['provider_caller'], 'stimmung_agent')
        self.assertTrue(payload['secondary_provider_payload'])
        self.assertFalse(payload['main_llm_payload'])
        self.assertEqual(payload['messages_count'], 2)
        self.assertEqual(payload['message_role_counts'], {'system': 1, 'user': 1})
        self.assertTrue(payload['system_prompt_present'])
        self.assertEqual(payload['recent_turn_count'], 2)
        self.assertEqual(payload['recent_turns_with_messages_count'], 2)
        self.assertEqual(payload['sampling']['timeout_s'], 10)

        def collect_keys(value: object) -> set[str]:
            if isinstance(value, dict):
                keys: set[str] = set()
                for key, item in value.items():
                    keys.add(str(key))
                    keys.update(collect_keys(item))
                return keys
            if isinstance(value, list):
                keys = set()
                for item in value:
                    keys.update(collect_keys(item))
                return keys
            return set()

        self.assertTrue({'prompt', 'messages', 'content', 'user_message', 'recent_window'}.isdisjoint(collect_keys(payload)))
        serialized = repr(payload)
        self.assertNotIn('PROMPT SYSTEME SENSIBLE', serialized)
        self.assertNotIn('historique brut', serialized)
        self.assertNotIn('tour utilisateur brut', serialized)

    def test_primary_node_fail_open_event_keeps_compact_cause_without_raw_exception(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-primary-fail-open',
            user_msg='message utilisateur brut a ne pas logger',
            web_search_enabled=False,
        )
        try:
            hermeneutic_node_logger.emit_primary_node(
                primary_payload={
                    'primary_verdict': {
                        'epistemic_regime': 'suspendu',
                        'proof_regime': 'source_explicite_requise',
                        'judgment_posture': 'suspend',
                        'discursive_regime': 'meta',
                        'source_conflicts': [],
                        'upstream_advisory': {
                            'recommended_judgment_posture': 'suspend',
                            'proposed_output_regime': 'meta',
                            'active_signal_families': [],
                            'constraint_present': False,
                        },
                        'audit': {
                            'fail_open': True,
                            'state_used': False,
                            'degraded_fields': ['epistemic_regime'],
                            'fallback_used': True,
                            'fallback_source': 'primary_node',
                            'node_stage': 'primary_node',
                            'reason_code': 'runtime_error',
                            'error_class': 'RuntimeError',
                        },
                    },
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'primary_node')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'error')
        self.assertTrue(payload['fail_open'])
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['fallback_source'], 'primary_node')
        self.assertEqual(payload['node_stage'], 'primary_node')
        self.assertEqual(payload['reason_code'], 'runtime_error')
        self.assertEqual(payload['error_class'], 'RuntimeError')
        self.assertEqual(payload['degraded_fields_count'], 1)
        serialized = repr(payload)
        self.assertNotIn('message utilisateur brut', serialized)
        self.assertNotIn('prompt', serialized)
        self.assertNotIn('stack', serialized)
        self.assertNotIn('traceback', serialized)


if __name__ == '__main__':
    unittest.main()
