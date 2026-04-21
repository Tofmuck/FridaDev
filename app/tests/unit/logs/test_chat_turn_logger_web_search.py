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
from observability import log_store
from tools import web_search


class ChatTurnLoggerWebSearchTests(unittest.TestCase):
    def test_web_search_build_context_emits_ok_and_skipped(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_format_context = web_search._format_context

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        try:
            token_ok = chat_turn_logger.begin_turn(
                conversation_id='conv-web-ok',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query ok'
            web_search.search = lambda _query: [{'title': 'A', 'url': 'https://a', 'content': 'x'}]
            web_search._format_context = lambda _query, _results: 'CTX OK'
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('CTX OK', 'query ok', 1))
                chat_turn_logger.end_turn(token_ok, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context

            token_skip = chat_turn_logger.begin_turn(
                conversation_id='conv-web-skip',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query none'
            web_search.search = lambda _query: []
            web_search._format_context = lambda _query, _results: ''
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('', 'query none', 0))
                chat_turn_logger.end_turn(token_skip, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context

            token_truncated = chat_turn_logger.begin_turn(
                conversation_id='conv-web-truncated',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query truncated'
            web_search.search = lambda _query: [{'title': 'A', 'url': 'https://a', 'content': 'x'}]
            web_search._format_context = lambda _query, _results: 'CTX [...contenu tronqué]'
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('CTX [...contenu tronqué]', 'query truncated', 1))
                chat_turn_logger.end_turn(token_truncated, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context
        finally:
            log_store.insert_chat_log_event = original_insert

        web_search_events = [event for event in observed if event['stage'] == 'web_search']
        self.assertGreaterEqual(len(web_search_events), 3)
        statuses = {event['status'] for event in web_search_events}
        self.assertIn('ok', statuses)
        self.assertIn('skipped', statuses)
        for event in web_search_events:
            payload = event['payload_json']
            self.assertEqual(payload.get('prompt_kind'), 'chat_web_reformulation')
            self.assertIn('enabled', payload)
            self.assertIn('query_preview', payload)
            self.assertIn('results_count', payload)
            self.assertIn('context_injected', payload)
            self.assertIn('truncated', payload)
            self.assertLessEqual(len(str(payload.get('query_preview') or '')), 120)
            self.assertNotIn('context', payload)
            self.assertNotIn('results', payload)

        skipped_events = [event for event in web_search_events if event['status'] == 'skipped']
        self.assertTrue(skipped_events)
        self.assertTrue(all(event['payload_json'].get('reason_code') == 'no_data' for event in skipped_events))
        truncated_event = next(
            event for event in web_search_events
            if event['payload_json'].get('query_preview') == 'query truncated'
        )
        self.assertTrue(truncated_event['payload_json']['truncated'])

    def test_web_search_build_context_payload_exposes_structured_sources(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_crawl_with_status = web_search.crawl_with_status
        original_runtime_services_value = web_search._runtime_services_value

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search.reformulate = lambda _msg: 'query structuree'
        web_search.search = lambda _query: [
            {'title': 'Source A', 'url': 'https://a.example/article', 'content': 'snippet a'},
            {'title': 'Source B', 'url': 'https://b.example/article', 'content': 'snippet b' * 200},
        ]
        web_search.crawl_with_status = (
            lambda url: {'status': 'success', 'markdown': 'markdown a', 'error_class': None}
            if 'a.example' in url
            else {'status': 'empty', 'markdown': '', 'error_class': None}
        )
        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 1,
            'crawl4ai_max_chars': 20,
        }[field]
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-structured',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            payload = web_search.build_context_payload('bonjour')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search.crawl_with_status = original_crawl_with_status
            web_search._runtime_services_value = original_runtime_services_value

        self.assertTrue(payload['enabled'])
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['query'], 'query structuree')
        self.assertEqual(payload['results_count'], 2)
        self.assertFalse(payload['explicit_url_detected'])
        self.assertIsNone(payload['read_state'])
        self.assertEqual(payload['primary_source_kind'], 'search')
        self.assertFalse(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'not_attempted')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'search_only')
        self.assertEqual(payload['runtime']['searxng_results'], 5)
        self.assertEqual(payload['runtime']['crawl4ai_top_n'], 1)
        self.assertEqual(payload['runtime']['crawl4ai_max_chars'], 20)
        self.assertEqual(payload['sources'][0]['rank'], 1)
        self.assertEqual(payload['sources'][0]['source_domain'], 'a.example')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'crawl_markdown')
        self.assertTrue(payload['sources'][0]['used_in_prompt'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'success')
        self.assertEqual(payload['sources'][1]['used_content_kind'], 'search_snippet')
        self.assertTrue(payload['sources'][1]['truncated'])
        self.assertEqual(payload['used_content_kinds'], ['crawl_markdown', 'search_snippet'])
        self.assertEqual(payload['injected_chars'], len(payload['sources'][0]['content_used']) + len(payload['sources'][1]['content_used']))
        self.assertEqual(payload['context_chars'], len(payload['context_block']))
        self.assertEqual(payload['source_material_summary'][0]['used_content_kind'], 'crawl_markdown')
        self.assertEqual(payload['source_material_summary'][1]['used_content_kind'], 'search_snippet')
        self.assertTrue(payload['context_block'].startswith('[RECHERCHE WEB'))

        web_event = next(event for event in observed if event['stage'] == 'web_search')
        self.assertEqual(web_event['status'], 'ok')
        self.assertEqual(web_event['payload_json']['results_count'], 2)
        self.assertTrue(web_event['payload_json']['truncated'])
        self.assertFalse(web_event['payload_json']['explicit_url_detected'])
        self.assertIsNone(web_event['payload_json']['read_state'])
        self.assertEqual(web_event['payload_json']['primary_read_status'], 'not_attempted')
        self.assertFalse(web_event['payload_json']['fallback_used'])
        self.assertEqual(web_event['payload_json']['collection_path'], 'search_only')
        self.assertEqual(web_event['payload_json']['used_content_kinds'], ['crawl_markdown', 'search_snippet'])
        self.assertEqual(web_event['payload_json']['injected_chars'], payload['injected_chars'])
        self.assertEqual(web_event['payload_json']['context_chars'], len(payload['context_block']))
        self.assertEqual(
            web_event['payload_json']['source_material_summary'],
            payload['source_material_summary'],
        )
        self.assertNotIn('context_block', web_event['payload_json'])
        self.assertNotIn('sources', web_event['payload_json'])
        self.assertNotIn('content_used', str(web_event['payload_json']))
        self.assertNotIn('snippet a', str(web_event['payload_json']))
        self.assertNotIn('snippet b', str(web_event['payload_json']))

    def test_web_search_build_context_payload_logs_explicit_url_primary_path(self) -> None:
        observed: list[dict[str, Any]] = []
        explicit_url = 'https://example.com/article'
        original_insert = log_store.insert_chat_log_event
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_runtime_services_value = web_search._runtime_services_value

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search._crawl_markdown_with_status = lambda url, *, filter_type='fit', query=None: {
            'status': 'success',
            'markdown': 'contenu primaire',
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(
            AssertionError('generic search should not run on explicit URL direct success')
        )
        web_search.search = lambda _query: (_ for _ in ()).throw(
            AssertionError('search should not run on explicit URL direct success')
        )
        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 50,
        }[field]
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-explicit-url',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            payload = web_search.build_context_payload(f'lis cette page: {explicit_url}')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._runtime_services_value = original_runtime_services_value

        self.assertTrue(payload['explicit_url_detected'])
        self.assertEqual(payload['read_state'], 'page_read')
        self.assertEqual(payload['primary_source_kind'], 'explicit_url')
        self.assertTrue(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'success')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])

        web_event = next(event for event in observed if event['stage'] == 'web_search')
        self.assertEqual(web_event['status'], 'ok')
        self.assertEqual(web_event['payload_json']['prompt_kind'], 'chat_web_explicit_url')
        self.assertTrue(web_event['payload_json']['explicit_url_detected'])
        self.assertEqual(web_event['payload_json']['explicit_url'], explicit_url)
        self.assertEqual(web_event['payload_json']['read_state'], 'page_read')
        self.assertEqual(web_event['payload_json']['primary_source_kind'], 'explicit_url')
        self.assertTrue(web_event['payload_json']['primary_read_attempted'])
        self.assertEqual(web_event['payload_json']['primary_read_status'], 'success')
        self.assertEqual(web_event['payload_json']['primary_read_filter'], 'fit')
        self.assertFalse(web_event['payload_json']['primary_read_raw_fallback_used'])
        self.assertFalse(web_event['payload_json']['fallback_used'])
        self.assertEqual(web_event['payload_json']['collection_path'], 'explicit_url_direct')
        self.assertEqual(web_event['payload_json']['used_content_kinds'], ['crawl_markdown'])
        self.assertEqual(web_event['payload_json']['injected_chars'], len(payload['sources'][0]['content_used']))
        self.assertEqual(web_event['payload_json']['context_chars'], len(payload['context_block']))
        self.assertEqual(
            web_event['payload_json']['source_material_summary'],
            payload['source_material_summary'],
        )
        self.assertNotIn('context_block', web_event['payload_json'])
        self.assertNotIn('sources', web_event['payload_json'])
        self.assertNotIn('content_used', str(web_event['payload_json']))
        self.assertNotIn('contenu primaire', str(web_event['payload_json']))

    def test_web_search_build_context_payload_logs_explicit_url_fallback_material_summary(self) -> None:
        observed: list[dict[str, Any]] = []
        explicit_url = 'https://example.com/article'
        original_insert = log_store.insert_chat_log_event
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_runtime_services_value = web_search._runtime_services_value

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'empty',
            'markdown': '',
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: 'requete fallback'
        web_search.search = lambda _query: [
            {
                'title': 'Source fallback',
                'url': 'https://fallback.example/article',
                'content': 'resume fallback',
            }
        ]
        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 80,
        }[field]
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-explicit-url-fallback',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            payload = web_search.build_context_payload(f'lis cette page: {explicit_url}')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._runtime_services_value = original_runtime_services_value

        web_event = next(event for event in observed if event['stage'] == 'web_search')
        self.assertEqual(web_event['status'], 'ok')
        self.assertEqual(web_event['payload_json']['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(web_event['payload_json']['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(web_event['payload_json']['primary_read_status'], 'empty')
        self.assertEqual(web_event['payload_json']['primary_read_filter'], 'raw')
        self.assertTrue(web_event['payload_json']['primary_read_raw_fallback_used'])
        self.assertEqual(web_event['payload_json']['used_content_kinds'], ['search_snippet'])
        self.assertEqual(web_event['payload_json']['injected_chars'], payload['injected_chars'])
        self.assertEqual(web_event['payload_json']['context_chars'], len(payload['context_block']))
        self.assertEqual(
            web_event['payload_json']['source_material_summary'],
            [
                {
                    'rank': 1,
                    'url': explicit_url,
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
                    'content_chars': len(payload['sources'][1]['content_used']),
                    'truncated': False,
                },
            ],
        )
        self.assertNotIn('context_block', web_event['payload_json'])
        self.assertNotIn('sources', web_event['payload_json'])
        self.assertNotIn('content_used', str(web_event['payload_json']))
        self.assertNotIn('resume fallback', str(web_event['payload_json']))

    def test_web_search_build_context_emits_error_event(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(RuntimeError('reformulation boom'))
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-error',
            user_msg='message source',
            web_search_enabled=True,
        )
        try:
            context, query, count = web_search.build_context('message source')
            self.assertEqual((context, query, count), ('', 'message source', 0))
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            web_search.reformulate = original_reformulate
            log_store.insert_chat_log_event = original_insert

        error_event = next(event for event in observed if event['stage'] == 'web_search' and event['status'] == 'error')
        payload = error_event['payload_json']
        self.assertEqual(payload.get('prompt_kind'), 'chat_web_reformulation')
        self.assertTrue(payload.get('enabled'))
        self.assertEqual(payload.get('results_count'), 0)
        self.assertFalse(payload.get('context_injected'))
        self.assertIn('error_class', payload)
        self.assertEqual(payload.get('query_preview'), 'message source')
        self.assertNotIn('context', payload)
        self.assertNotIn('results', payload)
        logger_error_event = next(event for event in observed if event['stage'] == 'error' and event['status'] == 'error')
        self.assertEqual(logger_error_event['payload_json']['message_short'], 'reformulation boom')


if __name__ == '__main__':
    unittest.main()
