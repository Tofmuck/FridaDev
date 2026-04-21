from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerChatCompactObservabilityContractTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
