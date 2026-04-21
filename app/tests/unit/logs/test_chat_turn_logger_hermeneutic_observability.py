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
        self.assertEqual(payload['inputs']['memory_retrieved']['retrieved_count'], 2)
        self.assertEqual(payload['inputs']['memory_arbitration']['status'], 'available')
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
                'prompt_block_count': 3,
                'memory_traces_injected': True,
                'memory_traces_injected_count': 2,
                'injected_candidate_ids': ['cand-user', 'cand-assistant'],
                'memory_context_injected': True,
                'memory_context_summary_count': 2,
                'context_hints_injected': True,
                'context_hints_injected_count': 2,
            },
        )
        self.assertNotIn('content', summary)
        self.assertNotIn('preview', summary)

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


if __name__ == '__main__':
    unittest.main()
