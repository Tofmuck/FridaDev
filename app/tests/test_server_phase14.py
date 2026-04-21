from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerPhase14ChatServiceTests(unittest.TestCase):
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

    def test_api_chat_emits_hermeneutic_node_insertion_observability_payload(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-observability-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok observability'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
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

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        event = next(item for item in observed_events if item['stage'] == 'hermeneutic_node_insertion')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'ok')
        self.assertTrue(payload['insertion_point_reached'])
        self.assertEqual(payload['mode'], str(self.server.config.HERMENEUTIC_MODE))
        self.assertTrue(payload['inputs']['time']['present'])
        self.assertEqual(payload['inputs']['time']['timezone'], str(self.server.config.FRIDA_TIMEZONE))
        self.assertTrue(payload['inputs']['time']['day_part_class'])
        self.assertEqual(payload['inputs']['memory_retrieved']['retrieved_count'], 0)
        self.assertEqual(payload['inputs']['memory_arbitration']['status'], 'skipped')
        self.assertEqual(payload['inputs']['memory_arbitration']['decisions_count'], 0)
        self.assertEqual(payload['inputs']['summary']['status'], 'missing')
        self.assertFalse(payload['inputs']['identity']['frida']['mutable_present'])
        self.assertFalse(payload['inputs']['identity']['user']['mutable_present'])
        self.assertEqual(payload['inputs']['recent_context']['messages_count'], 1)
        self.assertEqual(payload['inputs']['recent_window']['turn_count'], 1)
        self.assertTrue(payload['inputs']['recent_window']['has_in_progress_turn'])
        self.assertEqual(payload['inputs']['recent_window']['max_recent_turns'], 5)
        self.assertTrue(payload['inputs']['user_turn']['present'])
        self.assertEqual(payload['inputs']['user_turn']['geste_dialogique_dominant'], 'adresse_relationnelle')
        self.assertEqual(
            payload['inputs']['user_turn']['regime_probatoire'],
            {
                'principe': 'maximal_possible',
                'types_de_preuve_attendus': [],
                'provenances': [],
                'regime_de_vigilance': 'standard',
            },
        )
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['portee_temporelle'], 'atemporale')
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['ancrage_temporel'], 'non_ancre')
        self.assertNotIn('content', payload['inputs']['user_turn'])
        self.assertTrue(payload['inputs']['user_turn_signals']['present'])
        self.assertFalse(payload['inputs']['user_turn_signals']['ambiguity_present'])
        self.assertFalse(payload['inputs']['user_turn_signals']['underdetermination_present'])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families'], [])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families_count'], 0)
        self.assertTrue(payload['inputs']['stimmung']['present'])
        self.assertEqual(payload['inputs']['stimmung']['dominant_tone'], 'neutralite')
        self.assertEqual(payload['inputs']['stimmung']['active_tones'], [{'tone': 'neutralite', 'strength': 3}])
        self.assertEqual(payload['inputs']['stimmung']['stability'], 'emerging')
        self.assertEqual(payload['inputs']['stimmung']['shift_state'], 'steady')
        self.assertEqual(payload['inputs']['stimmung']['turns_considered'], 1)
        self.assertFalse(payload['inputs']['web']['enabled'])
        self.assertEqual(payload['inputs']['web']['status'], 'skipped')
        self.assertEqual(payload['inputs']['web']['activation_mode'], 'not_requested')
        self.assertEqual(payload['inputs']['web']['reason_code'], 'not_applicable')
        self.assertEqual(payload['inputs']['web']['results_count'], 0)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_prompt_prepared_memory_prompt_injection_without_raw_content(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-prompt-injection-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok prompt injection'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
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

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        prompt_event = next(item for item in observed_events if item['stage'] == 'prompt_prepared')
        payload = prompt_event['payload_json']
        self.assertEqual(payload['prompt_kind'], 'chat_system_augmented')
        self.assertEqual(payload['messages_count'], 1)
        self.assertEqual(payload['memory_items_used'], 0)
        self.assertEqual(
            payload['memory_prompt_injection'],
            {
                'injected': False,
                'prompt_block_count': 0,
                'memory_traces_injected': False,
                'memory_traces_injected_count': 0,
                'injected_candidate_ids': [],
                'memory_context_injected': False,
                'memory_context_summary_count': 0,
                'context_hints_injected': False,
                'context_hints_injected_count': 0,
            },
        )
        self.assertNotIn('messages', payload)
        self.assertNotIn('prompt', payload)
        self.assertNotIn('content', payload)
        self.assertNotIn('memory_traces', payload)
        self.assertNotIn('context_hints', payload)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_web_observability_payload_without_raw_web_content(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-web-observability-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok web observability'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.ws.build_context_payload = lambda _user_msg, **_kwargs: {
            'enabled': True,
            'status': 'ok',
            'reason_code': None,
            'original_user_message': 'Bonjour',
            'query': 'query test',
            'results_count': 2,
            'explicit_url_detected': True,
            'explicit_url': 'https://example.com/article',
            'read_state': 'page_not_read_snippet_fallback',
            'primary_source_kind': 'explicit_url',
            'primary_read_attempted': True,
            'primary_read_status': 'empty',
            'primary_read_filter': 'raw',
            'primary_read_raw_fallback_used': True,
            'fallback_used': True,
            'collection_path': 'explicit_url_fallback_search',
            'runtime': {
                'searxng_results': 5,
                'crawl4ai_top_n': 2,
                'crawl4ai_max_chars': 1500,
            },
            'used_content_kinds': ['search_snippet'],
            'injected_chars': len('Snippet fallback'),
            'context_chars': len('WEB CONTEXT'),
            'source_material_summary': [
                {
                    'rank': 1,
                    'url': 'https://example.com/article',
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'crawl_status': 'empty',
                    'content_chars': 0,
                    'truncated': False,
                },
                {
                    'rank': 2,
                    'url': 'https://fallback.example/article',
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'crawl_status': 'not_attempted',
                    'content_chars': len('Snippet fallback'),
                    'truncated': False,
                },
            ],
            'sources': [
                {
                    'rank': 1,
                    'title': 'URL explicite utilisateur',
                    'url': 'https://example.com/article',
                    'source_domain': 'example.com',
                    'search_snippet': '',
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'content_used': '',
                    'truncated': False,
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'crawl_status': 'empty',
                },
                {
                    'rank': 2,
                    'title': 'Titre fallback',
                    'url': 'https://fallback.example/article',
                    'source_domain': 'fallback.example',
                    'search_snippet': 'Snippet fallback',
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'content_used': 'Snippet fallback',
                    'truncated': False,
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'crawl_status': 'not_attempted',
                },
            ],
            'context_block': 'WEB CONTEXT',
        }
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'web_search': True})
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])

        insertion_event = next(item for item in observed_events if item['stage'] == 'hermeneutic_node_insertion')
        web_payload = insertion_event['payload_json']['inputs']['web']
        self.assertTrue(web_payload['enabled'])
        self.assertEqual(web_payload['status'], 'ok')
        self.assertEqual(web_payload['activation_mode'], 'manual')
        self.assertEqual(web_payload['reason_code'], '')
        self.assertEqual(web_payload['results_count'], 2)
        self.assertTrue(web_payload['explicit_url_detected'])
        self.assertEqual(web_payload['explicit_url'], 'https://example.com/article')
        self.assertEqual(web_payload['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(web_payload['primary_read_status'], 'empty')
        self.assertEqual(web_payload['primary_read_filter'], 'raw')
        self.assertTrue(web_payload['primary_read_raw_fallback_used'])
        self.assertTrue(web_payload['fallback_used'])
        self.assertEqual(web_payload['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(web_payload['used_content_kinds'], ['search_snippet'])
        self.assertEqual(web_payload['injected_chars'], len('Snippet fallback'))
        self.assertEqual(web_payload['context_chars'], len('WEB CONTEXT'))
        self.assertEqual(
            web_payload['source_material_summary'],
            [
                {
                    'rank': 1,
                    'url': 'https://example.com/article',
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'crawl_status': 'empty',
                    'content_chars': 0,
                    'truncated': False,
                },
                {
                    'rank': 2,
                    'url': 'https://fallback.example/article',
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'crawl_status': 'not_attempted',
                    'content_chars': len('Snippet fallback'),
                    'truncated': False,
                },
            ],
        )
        self.assertNotIn('context_block', web_payload)
        self.assertNotIn('sources', web_payload)
        self.assertNotIn('Snippet fallback', str(web_payload))
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

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

    def test_api_chat_keeps_contract_invalid_raw_conversation_id_creates_new_conversation(self) -> None:
        observed = {'normalized_raw': None, 'new_conversation_calls': 0, 'load_called': False}
        conversation = {
            'id': 'conv-invalid-raw-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok phase14'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_new_conversation = self.server.conv_store.new_conversation
        original_load_conversation = self.server.conv_store.load_conversation
        self.server.conv_store.normalize_conversation_id = lambda raw: observed.update({'normalized_raw': raw}) or None
        self.server.conv_store.new_conversation = (
            lambda _system: observed.update({'new_conversation_calls': observed['new_conversation_calls'] + 1}) or conversation
        )

        def fake_load_conversation(*_args, **_kwargs):
            observed['load_called'] = True
            return None

        self.server.conv_store.load_conversation = fake_load_conversation
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'conversation_id': '@@bad@@'})
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.new_conversation = original_new_conversation
            self.server.conv_store.load_conversation = original_load_conversation
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(response.get_json()['conversation_id'], 'conv-invalid-raw-phase14')
        self.assertEqual(response.headers.get('X-Conversation-Id'), 'conv-invalid-raw-phase14')
        self.assertEqual(response.headers.get('X-Conversation-Created-At'), '2026-03-26T00:00:00Z')
        self.assertTrue(response.headers.get('X-Conversation-Updated-At'))
        self.assertEqual(observed['normalized_raw'], '@@bad@@')
        self.assertEqual(observed['new_conversation_calls'], 1)
        self.assertFalse(observed['load_called'])
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)


if __name__ == '__main__':
    unittest.main()
