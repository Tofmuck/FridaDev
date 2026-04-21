from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerChatHermeneuticInsertionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_chat_pipeline(self, *, conversation: dict, requests_post):
        return server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=requests_post,
        )

    def test_api_chat_keeps_hermeneutic_insertion_point_between_memory_and_prompt_build(self) -> None:
        order: list[str] = []
        conversation = {
            'id': 'conv-seam-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok seam'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_prepare = self.server.chat_service.chat_memory_flow.prepare_memory_context
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.chat_service.chat_memory_flow.prepare_memory_context = (
            lambda **_kwargs: order.append('prepare_memory_context') or ('shadow', [], [])
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = (
            lambda **_kwargs: order.append('hermeneutic_insertion_point') or None
        )
        self.server.conv_store.build_prompt_messages = (
            lambda *_args, **_kwargs: order.append('build_prompt_messages') or [{'role': 'user', 'content': 'Bonjour'}]
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.chat_memory_flow.prepare_memory_context = original_prepare
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(
            order,
            ['prepare_memory_context', 'hermeneutic_insertion_point', 'build_prompt_messages'],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_injects_hermeneutic_judgment_block_from_validated_output(self) -> None:
        conversation = {
            'id': 'conv-validated-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validated block'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'judgment_posture': 'clarify',
                'discursive_regime': 'meta',
                'pipeline_directives_provisional': ['posture_clarify', 'regime_meta'],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'challenge',
                    'final_judgment_posture': 'answer',
                    'final_output_regime': 'simple',
                    'pipeline_directives_final': ['posture_answer', 'regime_simple'],
                    'arbiter_followed_upstream': False,
                    'advisory_recommendations_followed': [],
                    'advisory_recommendations_overridden': [
                        'upstream_recommendation_posture',
                        'upstream_output_regime_proposed',
                    ],
                    'applied_hard_guards': [],
                    'arbiter_reason': 'lecture locale suffisante malgre la recommandation amont',
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
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        system_prompt = next(
            message['content']
            for message in observed_state['payload_messages']
            if message.get('role') == 'system'
        )
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: answer.', system_prompt)
        self.assertIn('Regime final valide: simple.', system_prompt)
        self.assertIn('Consigne hermeneutique: Tu peux produire une reponse substantive normale.', system_prompt)
        self.assertIn('Consigne de regime: Reste dans une reprise locale, sobre, dialogique et non meta.', system_prompt)
        self.assertIn('Directives finales actives: posture_answer, regime_simple.', system_prompt)
        self.assertNotIn('primary_verdict', system_prompt)
        self.assertNotIn('validation_dialogue_context', system_prompt)
        self.assertNotIn('justifications', system_prompt)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_injects_suspend_block_when_validation_agent_fail_opens(self) -> None:
        conversation = {
            'id': 'conv-validation-fail-open-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok fail open block'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'judgment_posture': 'answer',
                'pipeline_directives_provisional': ['posture_answer'],
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
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {'role': 'user', 'content': 'Bonjour'},
            ]
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        system_prompt = next(
            message['content']
            for message in observed_state['payload_messages']
            if message.get('role') == 'system'
        )
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: suspend.', system_prompt)
        self.assertIn('Regime final valide: simple.', system_prompt)
        self.assertIn(
            'Consigne hermeneutique: Tu ne dois pas produire de reponse substantive normale. Tu dois expliciter la suspension ou la limite presente.',
            system_prompt,
        )
        self.assertIn('Consigne de regime: Reste dans une reprise locale, sobre, dialogique et non meta.', system_prompt)
        self.assertIn('Directives finales actives: posture_suspend, regime_simple, fallback_validation.', system_prompt)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_override_logs_and_projects_answer_block_without_raw_dump(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-override-observability-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok override observability'}}]}

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
                'epistemic_regime': 'incertain',
                'proof_regime': 'source_explicite_requise',
                'judgment_posture': 'clarify',
                'discursive_regime': 'meta',
                'source_conflicts': [],
                'upstream_advisory': {
                    'schema_version': 'v1',
                    'recommended_judgment_posture': 'clarify',
                    'proposed_output_regime': 'meta',
                    'active_signal_families': ['referent'],
                    'active_signal_families_count': 1,
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
                    'validation_decision': 'challenge',
                    'final_judgment_posture': 'answer',
                    'final_output_regime': 'simple',
                    'pipeline_directives_final': ['posture_answer', 'regime_simple'],
                    'arbiter_followed_upstream': False,
                    'advisory_recommendations_followed': [],
                    'advisory_recommendations_overridden': [
                        'upstream_recommendation_posture',
                        'upstream_output_regime_proposed',
                    ],
                    'applied_hard_guards': [],
                    'arbiter_reason': 'lecture locale suffisante malgre la recommandation amont',
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
                'upstream_recommendation_posture': 'clarify',
                'upstream_output_regime_proposed': 'meta',
                'upstream_active_signal_families': ['referent'],
                'upstream_constraint_present': False,
                'validation_decision': 'challenge',
                'final_judgment_posture': 'answer',
                'final_output_regime': 'simple',
                'arbiter_followed_upstream': False,
                'advisory_recommendations_followed': [],
                'advisory_recommendations_overridden': [
                    'upstream_recommendation_posture',
                    'upstream_output_regime_proposed',
                ],
                'applied_hard_guards': [],
                'arbiter_reason': 'lecture locale suffisante malgre la recommandation amont',
                'projected_judgment_posture': 'answer',
                'pipeline_directives_final': ['posture_answer', 'regime_simple'],
                'decision_source': 'primary',
                'model': 'openai/gpt-5.4-mini',
            },
        )
        self.assertNotIn('validation_dialogue_context', validation_event['payload_json'])
        self.assertNotIn('canonical_inputs', validation_event['payload_json'])
        self.assertNotIn('justifications', validation_event['payload_json'])

        system_prompt = next(
            message['content']
            for message in observed_state['payload_messages']
            if message.get('role') == 'system'
        )
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: answer.', system_prompt)
        self.assertIn('Regime final valide: simple.', system_prompt)
        self.assertIn('Consigne hermeneutique: Tu peux produire une reponse substantive normale.', system_prompt)
        self.assertIn('Consigne de regime: Reste dans une reprise locale, sobre, dialogique et non meta.', system_prompt)
        self.assertIn('Directives finales actives: posture_answer, regime_simple.', system_prompt)
        self.assertNotIn('primary_verdict', system_prompt)
        self.assertNotIn('validation_dialogue_context', system_prompt)
        self.assertNotIn('justifications', system_prompt)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_active_summary_to_hermeneutic_insertion_point(self) -> None:
        observed = {'summary_input': None}
        conversation = {
            'id': 'conv-summary-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok summary'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-phase14',
            'conversation_id': 'conv-summary-phase14',
            'start_ts': '2026-03-20T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif de continuité',
        }

        def fake_insertion(**kwargs):
            observed['summary_input'] = kwargs.get('summary_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['summary_input']['schema_version'], 'v1')
        self.assertEqual(observed['summary_input']['status'], 'available')
        self.assertEqual(observed['summary_input']['summary']['id'], 'sum-phase14')
        self.assertEqual(observed['summary_input']['summary']['conversation_id'], 'conv-summary-phase14')
        self.assertEqual(observed['summary_input']['summary']['start_ts'], '2026-03-20T10:00:00Z')
        self.assertEqual(observed['summary_input']['summary']['end_ts'], '2026-03-24T18:00:00Z')
        self.assertEqual(observed['summary_input']['summary']['content'], 'Résumé actif de continuité')
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_identity_input_to_hermeneutic_insertion_point(self) -> None:
        observed = {'identity_input': None}
        conversation = {
            'id': 'conv-identity-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok identity'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_identity_input = self.server.identity.build_identity_input
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        self.server.identity.build_identity_input = lambda: {
            'schema_version': 'v2',
            'frida': {
                'static': {'content': 'Frida statique', 'source': '/runtime/llm_identity.txt'},
                'mutable': {
                    'content': 'Frida aime les raisonnements structurés',
                    'source_trace_id': '11111111-1111-1111-1111-111111111111',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-03-24T12:00:00Z',
                },
            },
            'user': {
                'static': {'content': 'Utilisateur statique', 'source': '/runtime/user_identity.txt'},
                'mutable': {
                    'content': 'Utilisateur prefere les réponses concises',
                    'source_trace_id': '22222222-2222-2222-2222-222222222222',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-03-25T09:30:00Z',
                },
            },
        }

        def fake_insertion(**kwargs):
            observed['identity_input'] = kwargs.get('identity_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['identity_input']['schema_version'], 'v2')
        self.assertEqual(observed['identity_input']['frida']['static']['content'], 'Frida statique')
        self.assertNotIn('staging', observed['identity_input']['frida'])
        self.assertEqual(
            observed['identity_input']['frida']['mutable']['source_trace_id'],
            '11111111-1111-1111-1111-111111111111',
        )
        self.assertEqual(
            observed['identity_input']['frida']['mutable']['updated_by'],
            'identity_periodic_agent',
        )
        self.assertEqual(observed['identity_input']['user']['static']['content'], 'Utilisateur statique')
        self.assertNotIn('staging', observed['identity_input']['user'])
        self.assertEqual(
            observed['identity_input']['user']['mutable']['source_trace_id'],
            '22222222-2222-2222-2222-222222222222',
        )
        self.assertEqual(
            observed['identity_input']['user']['mutable']['updated_by'],
            'identity_periodic_agent',
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_uses_same_static_plus_mutable_basis_for_identity_input_and_prompt_block(self) -> None:
        observed = {'identity_input': None}
        conversation = {
            'id': 'conv-identity-basis-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok same basis'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_identity_input = self.server.identity.build_identity_input
        original_build_identity_block = self.server.identity.build_identity_block
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        identity_input = {
            'schema_version': 'v2',
            'frida': {
                'static': {'content': 'Frida statique', 'source': '/runtime/llm_identity.txt'},
                'mutable': {
                    'content': 'Frida garde une voix sobre.',
                    'source_trace_id': '11111111-1111-1111-1111-111111111111',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-03-24T12:00:00Z',
                },
            },
            'user': {
                'static': {'content': 'Utilisateur statique', 'source': '/runtime/user_identity.txt'},
                'mutable': {
                    'content': 'Tof garde une orientation stable vers les architectures lisibles.',
                    'source_trace_id': '22222222-2222-2222-2222-222222222222',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-03-25T09:30:00Z',
                },
            },
        }
        identity_block = (
            "[IDENTITE ACTIVE]\n"
            "[STATIQUE]\n"
            "Frida statique\n"
            "Utilisateur statique\n"
            "[MUTABLE]\n"
            "Frida garde une voix sobre.\n"
            "Tof garde une orientation stable vers les architectures lisibles."
        )
        self.server.identity.build_identity_input = lambda: identity_input
        self.server.identity.build_identity_block = lambda: (identity_block, [])

        def fake_insertion(**kwargs):
            observed['identity_input'] = kwargs.get('identity_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        self.server.conv_store.build_prompt_messages = lambda conversation_arg, *_args, **_kwargs: [
            {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
            {'role': 'user', 'content': 'Bonjour'},
        ]
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['identity_input'], identity_input)
        system_prompt = next(
            message['content']
            for message in observed_state['payload_messages']
            if message.get('role') == 'system'
        )
        self.assertIn('BACKEND SYSTEM PROMPT', system_prompt)
        self.assertIn(identity_block, system_prompt)
        self.assertIn('Frida garde une voix sobre.', system_prompt)
        self.assertIn('Tof garde une orientation stable vers les architectures lisibles.', system_prompt)
        self.assertNotIn('identity_staging', system_prompt)
        self.assertNotIn('conversation_scoped_latest', system_prompt)
        self.assertNotIn('recent_2', system_prompt)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_identity_block_and_payload_use_same_canonical_mutables_without_legacy_ids(self) -> None:
        identity = self.server.identity
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }
        mutable_entries = {
            'llm': {
                'content': 'Frida mutable narrative retenue',
                'source_trace_id': '11111111-1111-1111-1111-111111111111',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-03-24T12:00:00Z',
            },
            'user': {
                'content': 'User mutable narrative retenue',
                'source_trace_id': '22222222-2222-2222-2222-222222222222',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-03-25T09:30:00Z',
            },
        }

        identity.load_llm_identity = lambda: 'Frida static baseline'
        identity.load_user_identity = lambda: 'User static baseline'
        identity._safe_static_identity_source = lambda field: f'data/identity/{field}.txt'
        self.server.memory_store.get_mutable_identity = lambda subject: dict(mutable_entries[subject])
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not govern active identity path'
        )
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 4
        try:
            block, used_ids = identity.build_identity_block()
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.get_identities = original_get_identities

        self.assertIn('Frida mutable narrative retenue', block)
        self.assertIn('User mutable narrative retenue', block)
        self.assertIn('Frida static baseline', block)
        self.assertIn('User static baseline', block)
        self.assertIn('[STATIQUE]', block)
        self.assertIn('[MUTABLE]', block)
        self.assertNotIn('stability=', block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['schema_version'], 'v2')
        self.assertNotIn('dynamic', payload['frida'])
        self.assertNotIn('dynamic', payload['user'])
        self.assertNotIn('staging', payload['frida'])
        self.assertNotIn('staging', payload['user'])
        self.assertEqual(payload['frida']['static']['content'], 'Frida static baseline')
        self.assertEqual(payload['user']['static']['content'], 'User static baseline')
        self.assertEqual(payload['frida']['mutable']['content'], 'Frida mutable narrative retenue')
        self.assertEqual(payload['user']['mutable']['content'], 'User mutable narrative retenue')

    def test_identity_input_loads_static_content_from_host_state_mirror_while_keeping_runtime_source(self) -> None:
        identity = self.server.identity
        originals = {
            'get_resources_settings': identity.runtime_settings.get_resources_settings,
            '_get_mutable_identity': identity._get_mutable_identity,
            'app_root': identity.static_identity_paths.APP_ROOT,
            'repo_root': identity.static_identity_paths.REPO_ROOT,
            'host_state_root': identity.static_identity_paths.HOST_STATE_ROOT,
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / 'app').mkdir()
            identity_dir = tmp_path / 'state' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            llm_text = 'Frida statique host mirror'
            user_text = 'Utilisateur statique host mirror'
            (identity_dir / 'llm_identity.txt').write_text(llm_text, encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text(user_text, encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            identity.static_identity_paths.APP_ROOT = tmp_path / 'app'
            identity.static_identity_paths.REPO_ROOT = tmp_path
            identity.static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            identity._get_mutable_identity = lambda _subject: None
            try:
                block, used_ids = identity.build_identity_block()
                payload = identity.build_identity_input()
            finally:
                identity.runtime_settings.get_resources_settings = originals['get_resources_settings']
                identity._get_mutable_identity = originals['_get_mutable_identity']
                identity.static_identity_paths.APP_ROOT = originals['app_root']
                identity.static_identity_paths.REPO_ROOT = originals['repo_root']
                identity.static_identity_paths.HOST_STATE_ROOT = originals['host_state_root']

        self.assertIn(llm_text, block)
        self.assertIn(user_text, block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['frida']['static']['content'], llm_text)
        self.assertEqual(payload['user']['static']['content'], user_text)
        self.assertEqual(payload['frida']['static']['source'], 'data/identity/llm_identity.txt')
        self.assertEqual(payload['user']['static']['source'], 'data/identity/user_identity.txt')
        self.assertNotIn('dynamic', payload['frida'])
        self.assertNotIn('dynamic', payload['user'])
        self.assertEqual(payload['frida']['mutable']['content'], '')
        self.assertEqual(payload['user']['mutable']['content'], '')

    def test_identity_input_keeps_explicit_user_mutable_revelation_available_for_next_turn(self) -> None:
        identity = self.server.identity
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }

        identity.load_llm_identity = lambda: ''
        identity.load_user_identity = lambda: ''
        identity._safe_static_identity_source = lambda _field: None
        self.server.memory_store.get_mutable_identity = lambda subject: (
            {
                'content': 'Je suis Christophe Muck',
                'source_trace_id': '22222222-2222-2222-2222-222222222222',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-04-04T19:00:00Z',
            }
            if subject == 'user'
            else None
        )
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not govern active identity path'
        )
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 32
        try:
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.get_identities = original_get_identities

        self.assertEqual(payload['user']['mutable']['content'], 'Je suis Christophe Muck')

    def test_identity_active_path_keeps_mutable_present_when_static_identity_is_large(self) -> None:
        identity = self.server.identity
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }

        identity.load_llm_identity = lambda: 'Profil statique Frida ' * 120
        identity.load_user_identity = lambda: 'Profil statique utilisateur ' * 120
        identity._safe_static_identity_source = lambda _field: None
        self.server.memory_store.get_mutable_identity = lambda subject: (
            {
                'content': 'Je suis Christophe Muck',
                'source_trace_id': '22222222-2222-2222-2222-222222222222',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-04-04T19:00:00Z',
            }
            if subject == 'user'
            else None
        )
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not govern active identity path'
        )
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 80
        try:
            block, used_ids = identity.build_identity_block()
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.get_identities = original_get_identities

        self.assertIn('Je suis Christophe Muck', block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['user']['mutable']['content'], 'Je suis Christophe Muck')

    def test_api_chat_exposes_canonical_recent_context_to_hermeneutic_insertion_point(self) -> None:
        observed = {'recent_context_input': None}
        conversation = {
            'id': 'conv-recent-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'user', 'content': 'Message ancien', 'timestamp': '2026-03-20T08:00:00Z'},
                {'role': 'assistant', 'content': 'Réponse récente', 'timestamp': '2026-03-25T09:00:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok recent'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_now_iso = self.server.chat_service._now_iso
        self.server.chat_service._now_iso = lambda: '2026-03-26T12:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-recent-phase14',
            'conversation_id': 'conv-recent-phase14',
            'start_ts': '2026-03-18T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif',
        }

        def fake_insertion(**kwargs):
            observed['recent_context_input'] = kwargs.get('recent_context_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['recent_context_input']['schema_version'], 'v1')
        self.assertEqual(
            observed['recent_context_input']['messages'],
            [
                {
                    'role': 'assistant',
                    'content': 'Réponse récente',
                    'timestamp': '2026-03-25T09:00:00Z',
                },
                {
                    'role': 'user',
                    'content': 'Bonjour',
                    'timestamp': '2026-03-26T12:00:00Z',
                },
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_rebuilds_validation_dialogue_context_when_recent_context_is_empty_after_summary_cutoff(self) -> None:
        observed = {'validation_dialogue_context': None}
        conversation = {
            'id': 'conv-validation-context-fallback-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validation context fallback'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_now_iso = self.server.chat_service._now_iso
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        self.server.chat_service._now_iso = lambda: '2026-03-26T10:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-future-cutoff-phase14',
            'conversation_id': 'conv-validation-context-fallback-phase14',
            'start_ts': '2026-03-25T08:00:00Z',
            'end_ts': '2026-03-26T12:00:00Z',
            'content': 'Résumé actif avec cutoff futur',
        }
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'incertain',
                'proof_regime': 'source_explicite_requise',
                'uncertainty_posture': 'prudente',
                'judgment_posture': 'answer',
                'discursive_regime': 'simple',
                'resituation_level': 'none',
                'time_reference_mode': 'atemporal',
                'source_priority': [['tour_utilisateur']],
                'source_conflicts': [],
                'upstream_advisory': {
                    'schema_version': 'v1',
                    'recommended_judgment_posture': 'answer',
                    'proposed_output_regime': 'simple',
                    'active_signal_families': [],
                    'active_signal_families_count': 0,
                    'constraint_present': False,
                },
                'pipeline_directives_provisional': ['posture_answer'],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }

        def fake_build_validated_output(**kwargs):
            observed['validation_dialogue_context'] = kwargs.get('validation_dialogue_context')
            return self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'confirm',
                    'final_judgment_posture': 'answer',
                    'final_output_regime': 'simple',
                    'pipeline_directives_final': ['posture_answer', 'regime_simple'],
                    'arbiter_followed_upstream': True,
                    'advisory_recommendations_followed': [
                        'upstream_recommendation_posture',
                        'upstream_output_regime_proposed',
                    ],
                    'advisory_recommendations_overridden': [],
                    'applied_hard_guards': [],
                    'arbiter_reason': 'lecture locale suffisante',
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )

        self.server.chat_service.validation_agent.build_validated_output = fake_build_validated_output
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(
            observed['validation_dialogue_context'],
            {
                'schema_version': 'v1',
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Bonjour',
                        'timestamp': '2026-03-26T10:00:00Z',
                    }
                ],
                'source_message_count': 1,
                'truncated': False,
                'current_user_retained': True,
                'last_assistant_retained': False,
            },
        )
        self.assertEqual(observed['validation_dialogue_context']['schema_version'], 'v1')
        self.assertTrue(observed['validation_dialogue_context']['messages'])
        self.assertEqual(observed['validation_dialogue_context']['messages'][-1]['role'], 'user')
        self.assertEqual(observed['validation_dialogue_context']['messages'][-1]['content'], 'Bonjour')
        self.assertFalse(observed['validation_dialogue_context']['truncated'])
        self.assertTrue(observed['validation_dialogue_context']['current_user_retained'])
        self.assertFalse(observed['validation_dialogue_context']['last_assistant_retained'])
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_keeps_validation_dialogue_context_local_when_more_than_five_messages_exist(self) -> None:
        observed = {'validation_dialogue_context': None}
        conversation = {
            'id': 'conv-validation-context-local-window-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'assistant', 'content': 'Assistant 0', 'timestamp': '2026-03-26T08:00:00Z'},
                {'role': 'user', 'content': 'User 1', 'timestamp': '2026-03-26T08:01:00Z'},
                {'role': 'assistant', 'content': 'Assistant 1', 'timestamp': '2026-03-26T08:02:00Z'},
                {'role': 'user', 'content': 'User 2', 'timestamp': '2026-03-26T08:03:00Z'},
                {'role': 'assistant', 'content': 'Assistant 2', 'timestamp': '2026-03-26T08:04:00Z'},
                {'role': 'user', 'content': 'User 3', 'timestamp': '2026-03-26T08:05:00Z'},
                {'role': 'assistant', 'content': 'Assistant 3', 'timestamp': '2026-03-26T08:06:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validation context local window'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_now_iso = self.server.chat_service._now_iso
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        self.server.chat_service._now_iso = lambda: '2026-03-26T08:07:00Z'
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'incertain',
                'proof_regime': 'source_explicite_requise',
                'uncertainty_posture': 'prudente',
                'judgment_posture': 'answer',
                'discursive_regime': 'simple',
                'resituation_level': 'none',
                'time_reference_mode': 'atemporal',
                'source_priority': [['tour_utilisateur']],
                'source_conflicts': [],
                'upstream_advisory': {
                    'schema_version': 'v1',
                    'recommended_judgment_posture': 'answer',
                    'proposed_output_regime': 'simple',
                    'active_signal_families': [],
                    'active_signal_families_count': 0,
                    'constraint_present': False,
                },
                'pipeline_directives_provisional': ['posture_answer'],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }

        def fake_build_validated_output(**kwargs):
            observed['validation_dialogue_context'] = kwargs.get('validation_dialogue_context')
            return self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'confirm',
                    'final_judgment_posture': 'answer',
                    'final_output_regime': 'simple',
                    'pipeline_directives_final': ['posture_answer', 'regime_simple'],
                    'arbiter_followed_upstream': True,
                    'advisory_recommendations_followed': [
                        'upstream_recommendation_posture',
                        'upstream_output_regime_proposed',
                    ],
                    'advisory_recommendations_overridden': [],
                    'applied_hard_guards': [],
                    'arbiter_reason': 'lecture locale suffisante',
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )

        self.server.chat_service.validation_agent.build_validated_output = fake_build_validated_output
        try:
            response = self.client.post('/api/chat', json={'message': 'User current'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(
            observed['validation_dialogue_context'],
            {
                'schema_version': 'v1',
                'messages': [
                    {'role': 'user', 'content': 'User 2', 'timestamp': '2026-03-26T08:03:00Z'},
                    {'role': 'assistant', 'content': 'Assistant 2', 'timestamp': '2026-03-26T08:04:00Z'},
                    {'role': 'user', 'content': 'User 3', 'timestamp': '2026-03-26T08:05:00Z'},
                    {'role': 'assistant', 'content': 'Assistant 3', 'timestamp': '2026-03-26T08:06:00Z'},
                    {'role': 'user', 'content': 'User current', 'timestamp': '2026-03-26T08:07:00Z'},
                ],
                'source_message_count': 8,
                'truncated': True,
                'current_user_retained': True,
                'last_assistant_retained': True,
            },
        )
        self.assertEqual(len(observed['validation_dialogue_context']['messages']), 5)
        self.assertTrue(observed['validation_dialogue_context']['truncated'])
        self.assertTrue(observed['validation_dialogue_context']['current_user_retained'])
        self.assertTrue(observed['validation_dialogue_context']['last_assistant_retained'])
        self.assertEqual(observed['validation_dialogue_context']['messages'][-1]['content'], 'User current')
        self.assertEqual(observed['validation_dialogue_context']['messages'][-2]['content'], 'Assistant 3')
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_recent_window_to_hermeneutic_insertion_point(self) -> None:
        observed = {'recent_window_input': None}
        conversation = {
            'id': 'conv-recent-window-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'user', 'content': 'Message pre-summary', 'timestamp': '2026-03-20T08:00:00Z'},
                {'role': 'user', 'content': 'Tour 1 user', 'timestamp': '2026-03-25T08:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 1 assistant', 'timestamp': '2026-03-25T08:01:00Z'},
                {'role': 'user', 'content': 'Tour 2 user', 'timestamp': '2026-03-25T09:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 2 assistant', 'timestamp': '2026-03-25T09:01:00Z'},
                {'role': 'user', 'content': 'Tour 3 user', 'timestamp': '2026-03-25T10:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 3 assistant', 'timestamp': '2026-03-25T10:01:00Z'},
                {'role': 'user', 'content': 'Tour 4 user', 'timestamp': '2026-03-25T11:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 4 assistant', 'timestamp': '2026-03-25T11:01:00Z'},
                {'role': 'user', 'content': 'Tour 5 user', 'timestamp': '2026-03-25T12:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 5 assistant', 'timestamp': '2026-03-25T12:01:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok recent window'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_now_iso = self.server.chat_service._now_iso
        self.server.chat_service._now_iso = lambda: '2026-03-26T14:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-recent-window-phase14',
            'conversation_id': 'conv-recent-window-phase14',
            'start_ts': '2026-03-18T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif',
        }

        def fake_insertion(**kwargs):
            observed['recent_window_input'] = kwargs.get('recent_window_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['recent_window_input']['schema_version'], 'v1')
        self.assertEqual(observed['recent_window_input']['max_recent_turns'], 5)
        self.assertEqual(observed['recent_window_input']['turn_count'], 5)
        self.assertTrue(observed['recent_window_input']['has_in_progress_turn'])
        self.assertEqual(
            [turn['turn_status'] for turn in observed['recent_window_input']['turns']],
            ['complete', 'complete', 'complete', 'complete', 'in_progress'],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][0]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Tour 2 user',
                    'timestamp': '2026-03-25T09:00:00Z',
                },
                {
                    'role': 'assistant',
                    'content': 'Tour 2 assistant',
                    'timestamp': '2026-03-25T09:01:00Z',
                },
            ],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][-1]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Bonjour',
                    'timestamp': '2026-03-26T14:00:00Z',
                }
            ],
        )
        self.assertNotIn(
            'Tour 1 user',
            [
                message['content']
                for turn in observed['recent_window_input']['turns']
                for message in turn['messages']
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_recent_window_keeps_initial_assistant_without_fake_user_pair(self) -> None:
        observed = {'recent_window_input': None}
        conversation = {
            'id': 'conv-recent-window-initial-assistant-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'user', 'content': 'Message pre-summary', 'timestamp': '2026-03-20T08:00:00Z'},
                {'role': 'assistant', 'content': 'Assistant post-summary initial', 'timestamp': '2026-03-25T09:00:00Z'},
                {'role': 'user', 'content': 'Question récente', 'timestamp': '2026-03-25T09:10:00Z'},
                {'role': 'assistant', 'content': 'Réponse récente', 'timestamp': '2026-03-25T09:11:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok recent assistant only'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_now_iso = self.server.chat_service._now_iso
        self.server.chat_service._now_iso = lambda: '2026-03-26T14:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-recent-window-initial-assistant-phase14',
            'conversation_id': 'conv-recent-window-initial-assistant-phase14',
            'start_ts': '2026-03-18T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif',
        }

        def fake_insertion(**kwargs):
            observed['recent_window_input'] = kwargs.get('recent_window_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['recent_window_input']['turn_count'], 3)
        self.assertTrue(observed['recent_window_input']['has_in_progress_turn'])
        self.assertEqual(
            [turn['turn_status'] for turn in observed['recent_window_input']['turns']],
            ['assistant_only', 'complete', 'in_progress'],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][0]['messages'],
            [
                {
                    'role': 'assistant',
                    'content': 'Assistant post-summary initial',
                    'timestamp': '2026-03-25T09:00:00Z',
                }
            ],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][1]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Question récente',
                    'timestamp': '2026-03-25T09:10:00Z',
                },
                {
                    'role': 'assistant',
                    'content': 'Réponse récente',
                    'timestamp': '2026-03-25T09:11:00Z',
                },
            ],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][-1]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Bonjour',
                    'timestamp': '2026-03-26T14:00:00Z',
                }
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_user_turn_input_and_signals_to_hermeneutic_insertion_point(self) -> None:
        observed = {'user_turn_input': None, 'user_turn_signals': None}
        conversation = {
            'id': 'conv-user-turn-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok user turn'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point

        def fake_insertion(**kwargs):
            observed['user_turn_input'] = kwargs.get('user_turn_input')
            observed['user_turn_signals'] = kwargs.get('user_turn_signals')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Quel est le meilleur ?'})
        finally:
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['user_turn_input']['schema_version'], 'v1')
        self.assertEqual(observed['user_turn_input']['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(observed['user_turn_input']['regime_probatoire']['principe'], 'maximal_possible')
        self.assertEqual(observed['user_turn_input']['regime_probatoire']['types_de_preuve_attendus'], [])
        self.assertEqual(observed['user_turn_input']['regime_probatoire']['regime_de_vigilance'], 'standard')
        self.assertEqual(observed['user_turn_input']['qualification_temporelle']['portee_temporelle'], 'atemporale')
        self.assertEqual(observed['user_turn_input']['qualification_temporelle']['ancrage_temporel'], 'non_ancre')
        self.assertTrue(observed['user_turn_signals']['present'])
        self.assertFalse(observed['user_turn_signals']['ambiguity_present'])
        self.assertTrue(observed['user_turn_signals']['underdetermination_present'])
        self.assertEqual(observed['user_turn_signals']['active_signal_families'], ['critere'])
        self.assertEqual(observed['user_turn_signals']['active_signal_families_count'], 1)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_runs_stimmung_agent_as_upstream_stage_without_seam_injection(self) -> None:
        observed = {'insertion_kwargs': None, 'events': []}
        conversation = {
            'id': 'conv-stimmung-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok stimmung stage'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_affective_turn_signal = self.server.chat_service.stimmung_agent.build_affective_turn_signal
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_build_affective_turn_signal(**_kwargs):
            return self.server.chat_service.stimmung_agent.StimmungAgentResult(
                signal={
                    'schema_version': 'v1',
                    'present': True,
                    'tones': [
                        {'tone': 'frustration', 'strength': 7},
                        {'tone': 'confusion', 'strength': 4},
                    ],
                    'dominant_tone': 'frustration',
                    'confidence': 0.82,
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )

        def fake_insertion(**kwargs):
            observed['insertion_kwargs'] = dict(kwargs)
            return None

        def fake_insert(event, **_kwargs):
            observed['events'].append(event)
            return True

        self.server.chat_service.stimmung_agent.build_affective_turn_signal = fake_build_affective_turn_signal
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': "C'est agaçant et je suis perdu"})
        finally:
            self.server.chat_service.stimmung_agent.build_affective_turn_signal = original_build_affective_turn_signal
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        stage_event = next(item for item in observed['events'] if item['stage'] == 'stimmung_agent')
        payload = stage_event['payload_json']
        self.assertEqual(stage_event['status'], 'ok')
        self.assertTrue(payload['present'])
        self.assertEqual(payload['dominant_tone'], 'frustration')
        self.assertEqual(payload['tones_count'], 2)
        self.assertEqual(
            payload['tones'],
            [
                {'tone': 'frustration', 'strength': 7},
                {'tone': 'confusion', 'strength': 4},
            ],
        )
        self.assertEqual(payload['confidence'], 0.82)
        self.assertEqual(payload['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(payload['decision_source'], 'primary')
        self.assertNotIn('user_msg', payload)
        self.assertNotIn('prompt', payload)
        self.assertNotIn('raw_output', payload)
        self.assertIsNotNone(observed['insertion_kwargs'])
        self.assertNotIn('affective_turn_signal', observed['insertion_kwargs'])
        self.assertIn('stimmung_input', observed['insertion_kwargs'])
        self.assertTrue(observed['insertion_kwargs']['stimmung_input']['present'])
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['dominant_tone'], 'frustration')
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['stability'], 'emerging')
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['shift_state'], 'steady')
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['turns_considered'], 1)
        self.assertIn('user_turn_input', observed['insertion_kwargs'])
        self.assertIn('user_turn_signals', observed['insertion_kwargs'])
        user_messages = [message for message in conversation['messages'] if message.get('role') == 'user']
        self.assertTrue(user_messages)
        self.assertEqual(
            user_messages[-1].get('meta', {}).get('affective_turn_signal'),
            {
                'schema_version': 'v1',
                'present': True,
                'tones': [
                    {'tone': 'frustration', 'strength': 7},
                    {'tone': 'confusion', 'strength': 4},
                ],
                'dominant_tone': 'frustration',
                'confidence': 0.82,
            },
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)


if __name__ == '__main__':
    unittest.main()
