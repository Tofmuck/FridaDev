from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerChatSyntheticLogsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_chat_pipeline(self, *, conversation: dict, requests_post, **kwargs):
        return server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=requests_post,
            **kwargs,
        )

    def test_api_chat_emits_primary_node_and_validation_agent_synthetic_log_events(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-hermeneutic-stages-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok hermeneutic stages'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'ouvert',
                'proof_regime': 'source_explicite_requise',
                'judgment_posture': 'clarify',
                'discursive_regime': 'meta',
                'source_conflicts': [{'kind': 'memory_conflict'}, {'kind': 'web_conflict'}],
                'upstream_advisory': {
                    'schema_version': 'v1',
                    'recommended_judgment_posture': 'clarify',
                    'proposed_output_regime': 'meta',
                    'active_signal_families': ['referent', 'ancrage_de_source'],
                    'active_signal_families_count': 2,
                    'constraint_present': True,
                },
                'audit': {'fail_open': False, 'state_used': True, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'clarify',
                    'final_judgment_posture': 'clarify',
                    'final_output_regime': 'meta',
                    'pipeline_directives_final': ['posture_clarify', 'regime_meta'],
                    'arbiter_followed_upstream': True,
                    'advisory_recommendations_followed': [
                        'upstream_recommendation_posture',
                        'upstream_output_regime_proposed',
                    ],
                    'advisory_recommendations_overridden': [],
                    'applied_hard_guards': [],
                    'arbiter_reason': 'ambiguite maintenue apres relecture',
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )
        )
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {'role': 'user', 'content': 'Bonjour'},
            ]
        )

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        stages = [item['stage'] for item in observed_events]
        self.assertIn('stimmung_agent', stages)
        self.assertIn('hermeneutic_node_insertion', stages)
        self.assertIn('primary_node', stages)
        self.assertIn('validation_agent', stages)

        insertion_event = next(item for item in observed_events if item['stage'] == 'hermeneutic_node_insertion')
        self.assertEqual(
            insertion_event['payload_json']['inputs']['user_turn']['regime_probatoire'],
            {
                'principe': 'maximal_possible',
                'types_de_preuve_attendus': [],
                'provenances': [],
                'regime_de_vigilance': 'standard',
            },
        )
        self.assertNotIn('content', insertion_event['payload_json']['inputs']['user_turn'])

        primary_event = next(item for item in observed_events if item['stage'] == 'primary_node')
        self.assertEqual(primary_event['status'], 'ok')
        self.assertEqual(
            primary_event['payload_json'],
            {
                'upstream_recommendation_posture': 'clarify',
                'upstream_output_regime_proposed': 'meta',
                'upstream_active_signal_families': ['referent', 'ancrage_de_source'],
                'upstream_constraint_present': True,
                'epistemic_regime': 'ouvert',
                'proof_regime': 'source_explicite_requise',
                'source_conflicts_count': 2,
                'fail_open': False,
                'state_used': True,
                'degraded_fields_count': 0,
            },
        )

        validation_event = next(item for item in observed_events if item['stage'] == 'validation_agent')
        self.assertEqual(validation_event['status'], 'ok')
        self.assertEqual(
            validation_event['payload_json'],
            {
                'dialogue_messages_count': 1,
                'dialogue_truncated': False,
                'current_user_retained': True,
                'last_assistant_retained': False,
                'upstream_recommendation_posture': 'clarify',
                'upstream_output_regime_proposed': 'meta',
                'upstream_active_signal_families': ['referent', 'ancrage_de_source'],
                'upstream_constraint_present': True,
                'validation_decision': 'clarify',
                'final_judgment_posture': 'clarify',
                'final_output_regime': 'meta',
                'arbiter_followed_upstream': True,
                'advisory_recommendations_followed': [
                    'upstream_recommendation_posture',
                    'upstream_output_regime_proposed',
                ],
                'advisory_recommendations_overridden': [],
                'applied_hard_guards': [],
                'arbiter_reason': 'ambiguite maintenue apres relecture',
                'projected_judgment_posture': 'clarify',
                'pipeline_directives_final': ['posture_clarify', 'regime_meta'],
                'decision_source': 'primary',
                'model': 'openai/gpt-5.4-mini',
            },
        )
        system_prompt = next(
            message['content']
            for message in observed_state['payload_messages']
            if message.get('role') == 'system'
        )
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: clarify.', system_prompt)
        self.assertIn('Regime final valide: meta.', system_prompt)
        self.assertIn(
            'Consigne hermeneutique: Tu ne dois pas repondre directement au fond. Tu dois demander une clarification breve et explicite.',
            system_prompt,
        )
        self.assertIn(
            "Consigne de regime: Tu peux expliciter le cadre, la limite ou la clarification de facon reflexive si c'est vraiment necessaire.",
            system_prompt,
        )
        self.assertIn('Directives finales actives: posture_clarify, regime_meta.', system_prompt)

        for payload in (primary_event['payload_json'], validation_event['payload_json']):
            self.assertNotIn('primary_verdict', payload)
            self.assertNotIn('validated_output', payload)
            self.assertNotIn('validation_dialogue_context', payload)
            self.assertNotIn('justifications', payload)
            self.assertNotIn('canonical_inputs', payload)
            self.assertNotIn('prompt', payload)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_persist_response_reports_error_when_messages_are_not_saved(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-persist-response-error-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok non persistable'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
            save_conversation_result=lambda _conversation, **kwargs: SimpleNamespace(
                ok=not kwargs.get('updated_at'),
                catalog_saved=True,
                messages_saved=not kwargs.get('updated_at'),
                updated_at=kwargs.get('updated_at'),
                message_count=len(_conversation.get('messages', [])),
                reason='messages_write_failed' if kwargs.get('updated_at') else None,
            ),
        )
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'sauvegarde conversationnelle impossible',
                'reason': 'messages_write_failed',
            },
        )
        persist_event = next(
            item
            for item in reversed(observed_events)
            if item['stage'] == 'persist_response' and item['status'] == 'error'
        )
        self.assertEqual(persist_event['status'], 'error')
        self.assertEqual(
            persist_event['payload_json'],
            {
                'conversation_saved': False,
                'catalog_saved': True,
                'messages_saved': False,
                'message_count': 3,
                'messages_written': 0,
                'reason': 'messages_write_failed',
            },
        )
        self.assertEqual(len(observed_state['save_new_traces_calls']), 0)

    def test_api_chat_emits_hard_guard_name_effect_and_final_posture_in_validation_logs(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-hard-guard-log-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok hard guard stages'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'a_verifier',
                'proof_regime': 'verification_externe_requise',
                'judgment_posture': 'answer',
                'discursive_regime': 'simple',
                'source_conflicts': [],
                'upstream_advisory': {
                    'schema_version': 'v1',
                    'recommended_judgment_posture': 'answer',
                    'proposed_output_regime': 'simple',
                    'active_signal_families': [],
                    'active_signal_families_count': 0,
                    'constraint_present': False,
                },
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'clarify',
                    'final_judgment_posture': 'clarify',
                    'final_output_regime': 'simple',
                    'pipeline_directives_final': ['posture_clarify', 'regime_simple'],
                    'arbiter_followed_upstream': False,
                    'advisory_recommendations_followed': ['upstream_output_regime_proposed'],
                    'advisory_recommendations_overridden': ['upstream_recommendation_posture'],
                    'applied_hard_guards': ['external_verification_missing'],
                    'hard_guard_effect': 'answer_forbidden',
                    'arbiter_reason': 'je peux cadrer sans verifier maintenant',
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )
        )
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {'role': 'user', 'content': 'Bonjour'},
            ]
        )

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        validation_event = next(item for item in observed_events if item['stage'] == 'validation_agent')
        self.assertEqual(validation_event['status'], 'ok')
        self.assertEqual(
            validation_event['payload_json'],
            {
                'dialogue_messages_count': 1,
                'dialogue_truncated': False,
                'current_user_retained': True,
                'last_assistant_retained': False,
                'upstream_recommendation_posture': 'answer',
                'upstream_output_regime_proposed': 'simple',
                'upstream_active_signal_families': [],
                'upstream_constraint_present': False,
                'validation_decision': 'clarify',
                'final_judgment_posture': 'clarify',
                'final_output_regime': 'simple',
                'arbiter_followed_upstream': False,
                'advisory_recommendations_followed': ['upstream_output_regime_proposed'],
                'advisory_recommendations_overridden': ['upstream_recommendation_posture'],
                'applied_hard_guards': ['external_verification_missing'],
                'hard_guard_effect': 'answer_forbidden',
                'arbiter_reason': 'je peux cadrer sans verifier maintenant',
                'projected_judgment_posture': 'clarify',
                'pipeline_directives_final': ['posture_clarify', 'regime_simple'],
                'decision_source': 'primary',
                'model': 'openai/gpt-5.4-mini',
            },
        )
        system_prompt = next(
            message['content']
            for message in observed_state['payload_messages']
            if message.get('role') == 'system'
        )
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: clarify.', system_prompt)
        self.assertIn('Regime final valide: simple.', system_prompt)
        self.assertIn(
            'Consigne hermeneutique: Tu ne dois pas repondre directement au fond. Tu dois demander une clarification breve et explicite.',
            system_prompt,
        )
        self.assertIn('Consigne de regime: Reste dans une reprise locale, sobre, dialogique et non meta.', system_prompt)
        self.assertIn('Directives finales actives: posture_clarify, regime_simple.', system_prompt)
        self.assertNotIn('validation_dialogue_context', validation_event['payload_json'])
        self.assertNotIn('canonical_inputs', validation_event['payload_json'])
        self.assertNotIn('justifications', validation_event['payload_json'])
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_validation_agent_error_stage_without_raw_payload_dump(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-validation-error-stage-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validation error stage'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'ouvert',
                'proof_regime': 'source_explicite_requise',
                'judgment_posture': 'answer',
                'discursive_regime': 'simple',
                'source_conflicts': [],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'suspend',
                    'final_judgment_posture': 'suspend',
                    'final_output_regime': 'simple',
                    'pipeline_directives_final': ['posture_suspend', 'regime_simple', 'fallback_validation'],
                    'arbiter_followed_upstream': False,
                    'advisory_recommendations_followed': ['upstream_output_regime_proposed'],
                    'advisory_recommendations_overridden': ['upstream_recommendation_posture'],
                    'applied_hard_guards': [],
                    'arbiter_reason': 'validation fail-open (timeout)',
                },
                status='error',
                model='openai/gpt-5.4-nano',
                decision_source='fail_open',
                reason_code='timeout',
            )
        )

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        validation_event = next(item for item in observed_events if item['stage'] == 'validation_agent')
        self.assertEqual(validation_event['status'], 'error')
        self.assertEqual(
            validation_event['payload_json'],
            {
                'dialogue_messages_count': 1,
                'dialogue_truncated': False,
                'current_user_retained': True,
                'last_assistant_retained': False,
                'upstream_recommendation_posture': 'answer',
                'upstream_output_regime_proposed': 'simple',
                'upstream_active_signal_families': [],
                'upstream_constraint_present': False,
                'validation_decision': 'suspend',
                'final_judgment_posture': 'suspend',
                'final_output_regime': 'simple',
                'arbiter_followed_upstream': False,
                'advisory_recommendations_followed': ['upstream_output_regime_proposed'],
                'advisory_recommendations_overridden': ['upstream_recommendation_posture'],
                'applied_hard_guards': [],
                'arbiter_reason': 'validation fail-open (timeout)',
                'projected_judgment_posture': 'suspend',
                'pipeline_directives_final': ['posture_suspend', 'regime_simple', 'fallback_validation'],
                'decision_source': 'fail_open',
                'reason_code': 'timeout',
                'model': 'openai/gpt-5.4-nano',
            },
        )
        self.assertNotIn('validation_dialogue_context', validation_event['payload_json'])
        self.assertNotIn('validated_output', validation_event['payload_json'])
        self.assertNotIn('primary_verdict', validation_event['payload_json'])
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)


if __name__ == '__main__':
    unittest.main()
