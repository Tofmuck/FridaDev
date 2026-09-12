from __future__ import annotations

import copy
import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from biblio import observability as biblio
from core import llm_client
from core import conversations_prompt_window
from core.hermeneutic_node.inputs.memory_retrieved_input import build_memory_retrieved_input
from observability.prompt_injection_summary import build_memory_prompt_injection_summary
from observability import chat_turn_logger as logger, log_store, memory_chain_snapshot
from observability import hermeneutic_node_logger as node, observability_payload_guard as guard
from observability import turn_pipeline_memory_summary, turn_pipeline_biblio_summary, turn_pipeline_web_summary, turn_pipeline_read_model
from tests.support import observability_writer_cases as cases
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tools import web_search_runtime_events as web


class ObservabilityRealWritersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server_module_for_tests()

    def setUp(self):
        self.events = []
        self.store_patch = patch.object(log_store, 'insert_chat_log_event', side_effect=self.store)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.token = logger.begin_turn(conversation_id='fixture', user_msg='synthetic', web_search_enabled=False)
        self.addCleanup(logger.end_turn, self.token)

    def store(self, event):
        self.events.append(copy.deepcopy(event))
        return True

    def event(self, stage, status='ok'):
        event = next(e for e in reversed(self.events) if e['stage'] == stage)
        self.assertEqual(event['status'], status)
        self.assertNotEqual(event['payload_json'].get('reason_code'), guard.REASON_CODE)
        self.assertFalse(event['payload_json'].get('rejected_payload', False))
        return {**event, 'payload': event['payload_json']}

    def test_memory_candidates_decision_and_injection_survive_store_and_reader(self):
        memory_chain_snapshot.emit_memory_chain_snapshot(**cases.memory_inputs())
        event = self.event('memory_chain_snapshot')
        p = event['payload']
        self.assertEqual(len(p['retrieved_candidates']), 2)
        self.assertEqual(len(p['basket_candidates']), 1)
        self.assertNotIn('candidate_id', p['basket_candidates'][0])
        digest = p['basket_candidates'][0]['candidate_id_sha256_12']
        self.assertEqual(p['injection']['injected_candidate_id_sha256_12'], [digest])
        self.assertEqual(p['basket_candidates'][0]['arbiter_status'], 'keep')
        self.assertEqual(p['basket_candidates'][0]['semantic_relevance'], 0.9)
        summary = turn_pipeline_memory_summary.build_memory_rag_summary([event], {})
        self.assertEqual([summary[k] for k in ('retrieved', 'basket', 'kept', 'injected')], [2, 1, 1, 1])
        self.assertEqual(summary['status'], 'ok')

    def call_provider(self, caller, generation_id=cases.GENERATION_ID):
        response = SimpleNamespace(json=lambda: {
            'id': generation_id, 'model': 'openai/test', 'provider': 'Synthetic',
            'choices': [{'message': {'content': 'synthetic reply'}}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18},
        })
        proxy = self.server._RequestsChatLogProxy(SimpleNamespace(post=lambda *a, **kw: response))
        with patch.object(llm_client, 'resolve_provider_title', return_value='FridaDev/Test'), \
             patch.object(llm_client, 'main_llm_reasoning_observability_from_payload', return_value={}):
            self.assertIs(proxy.post('https://provider.invalid/chat/completions',
                                     json={'model': 'openai/test'}, timeout=60,
                                     headers={'X-Frida-Caller': caller}), response)

    def test_three_callers_preserve_attribution_status_and_tokens_without_raw_id(self):
        rows = []
        for caller in ('stimmung_agent', 'validation_agent', 'llm'):
            with self.subTest(caller=caller):
                self.call_provider(caller)
                event = self.event('llm_call')
                p = event['payload']
                self.assertEqual(p['provider_caller'], caller)
                self.assertEqual(p['provider_total_tokens'], 18)
                self.assertEqual(p['response_chars'], 15)
                self.assertNotIn('provider_generation_id', p)
                self.assertIs(p['provider_generation_id_present'], True)
                self.assertEqual(p['provider_generation_id_sha256_12'], hashlib.sha256(cases.GENERATION_ID.encode()).hexdigest()[:12])
                self.assertNotIn(cases.GENERATION_ID, json.dumps(p))
                rows.append(dict(provider_caller=p['provider_caller'], status=event['status'], calls_count=1,
                                 response_chars_total=p['response_chars'], duration_ms_total=1, duration_ms_count=1))
        metrics = log_store.build_llm_call_provider_metrics(rows)
        self.assertEqual([metrics[k] for k in ('main_llm_call_count', 'secondary_llm_call_count', 'unknown_llm_call_count')], [1, 2, 0])

    def test_biblio_state_and_transition_preserve_types_and_branch_truth(self):
        biblio.emit_biblio_event(cases.biblio_payload(), chat_turn_logger_module=logger)
        event = self.event('biblio', 'disabled')
        state = event['payload']['state']
        self.assertEqual(state['persistence_mode'], 'conversation_message_meta')
        self.assertEqual(state['last_passage_hash'], '012345abcdef')
        self.assertEqual(state['page_no'], 3)
        self.assertIsNone(state['last_result_interval_incomplete_page_no'])
        self.assertEqual(event['payload']['state_transition']['persistence_status'], 'pending_normal_conversation_save')
        summary = turn_pipeline_biblio_summary.build_biblio_summary([event])
        self.assertEqual(summary['status'], 'disabled')
        self.assertEqual(event['payload']['reason_code'], 'biblio_disabled')
        self.assertEqual(summary['reason_code_counts']['biblio_disabled'], 1)

    def test_prompt_prepared_preserves_parent_summary_period(self):
        logger.set_state('memory_prompt_injection', cases.prompt_memory_summary())
        base = SimpleNamespace(build_payload=lambda *a, **kw: {'model': 'openai/test'})
        proxy = self.server._LlmChatLogProxy(base, SimpleNamespace(estimate_tokens=lambda *a: 12))
        proxy.build_payload([], 0.2, 1, 32)
        event = self.event('prompt_prepared')
        memory = event['payload']['memory_prompt_injection']
        self.assertEqual(memory['parent_summaries_injected_count'], 1)
        parent = memory['parent_summaries_injected'][0]
        self.assertEqual(parent['start_ts'], '2026-09-01 00:00:00+00:00')
        self.assertEqual(parent['end_ts'], '2026-09-02 00:00:00+00:00')
        summary = turn_pipeline_memory_summary.build_memory_rag_summary([event], event['payload'])
        self.assertEqual(summary['parent_summaries_injected_count'], 1)

    def test_summary_candidate_reference_uses_pipeline_id_and_snapshot_hash(self):
        retrieved = build_memory_retrieved_input(retrieval_query='synthetic', top_k_requested=8,
            traces=[{'source_kind': 'summary', 'summary_id': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
                     'content': 'synthetic summary', 'score': 0.9}])
        injection = build_memory_prompt_injection_summary(
            [{'role': 'system', 'content': conversations_prompt_window.MEMORY_TRACES_BLOCK_HEADER}],
            memory_traces=retrieved['traces'])
        logger.emit('prompt_prepared', payload={'memory_prompt_injection': injection})
        event = self.event('prompt_prepared')
        self.assertEqual(event['payload']['memory_prompt_injection']['injected_candidate_ids'],
                         ['summary:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'])
        memory_chain_snapshot.emit_memory_chain_snapshot(current_mode='normal', memory_retrieved=retrieved,
            memory_arbitration={'status': 'skipped', 'reason_code': 'no_data'},
            memory_traces=retrieved['traces'], context_hints=[])
        snapshot = self.event('memory_chain_snapshot')['payload']
        self.assertNotIn('candidate_id', snapshot['retrieved_candidates'][0])
        self.assertEqual(snapshot['injection']['injection_class'], 'summary_only')

    def test_web_writer_preserves_hostname_without_url_or_content(self):
        web.emit_web_search_runtime_event(enabled=True, status='ok', reason_code=None,
            query_preview='synthetic query', results_count=4, context_block='synthetic context', sources=cases.web_sources())
        event = self.event('web_search')
        self.assertEqual(event['payload']['source_material_summary'][0]['source_domain'], 'www.source.invalid')
        self.assertEqual(event['payload']['results_count'], 4)
        self.assertNotIn('https://', json.dumps(event['payload']))
        summary = turn_pipeline_web_summary.build_web_summary([event])
        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['results_count'], 4)

    def test_insertion_writer_preserves_web_facts_without_url_or_content(self):
        sources = cases.web_sources()
        node.emit_hermeneutic_node_insertion(current_mode='normal', web_input={
            'enabled': True, 'status': 'ok', 'results_count': 4,
            'source_material_summary': web.build_source_material_summary(sources),
            'crawl4ai_extraction_summary': web.build_crawl4ai_extraction_summary(sources),
        })
        event = self.event('hermeneutic_node_insertion')
        self.assertIs(event['payload']['insertion_point_reached'], True)
        self.assertEqual(event['payload']['inputs']['web']['results_count'], 4)
        self.assertEqual(event['payload']['inputs']['web']['source_material_summary'][0]['source_domain'], 'www.source.invalid')
        self.assertNotIn('https://', json.dumps(event['payload']))
        projection = turn_pipeline_read_model.build_turn_pipeline_item([event])
        self.assertEqual(projection['stage_counts']['hermeneutic_node_insertion'], 1)
        self.assertNotIn(guard.REASON_CODE, json.dumps(projection))
        self.assertFalse(projection['flags']['raw_event_payloads_included'])

    def test_memory_context_rejects_unknown_keys_types_and_excess(self):
        for key, value in [('private_sentence', 'synthetic private text'), ('retrieval_rank', True),
                           ('retrieval_score', '0.9'), ('source_lane', {'present': True}),
                           ('source_candidate_id_sha256_12', ['a'*12]*9)]:
            with self.subTest(key=key):
                payload = cases.memory_payload()
                payload['basket_candidates'][0][key] = value
                logger.emit('memory_chain_snapshot', payload=payload)
                self.assert_rejection('memory_chain_snapshot')
        payload = cases.memory_payload()
        payload['retrieved_candidates'] *= 13
        logger.emit('memory_chain_snapshot', payload=payload)
        self.assert_rejection('memory_chain_snapshot')

    def test_nonfinite_or_oversized_scores_fail_closed_without_raising(self):
        for value in [float('nan'), float('inf'), -float('inf'), 10**400]:
            payload = cases.memory_payload()
            payload['basket_candidates'][0]['retrieval_score'] = value
            logger.emit('memory_chain_snapshot', payload=payload)
            self.assert_rejection('memory_chain_snapshot')

    def test_state_projection_failure_remains_observability_only(self):
        def broken_projection():
            raise ValueError('synthetic private detail')
        for field in ('biblio_state', 'state_transition'):
            for value in (SimpleNamespace(to_observability=broken_projection),
                          SimpleNamespace(to_observability=lambda: []), 42):
                with self.subTest(field=field, kind=type(value).__name__):
                    payload = biblio.build_biblio_event_payload(**{field: value})
                    biblio.emit_biblio_event(payload, chat_turn_logger_module=logger)
                    event = next(e for e in reversed(self.events) if e['stage'] == 'biblio')
                    self.assertEqual(event['status'], 'disabled')
                    self.assertTrue(guard.is_guard_rejection_payload(event['payload_json']))
                    self.assertNotIn('synthetic private detail', json.dumps(event))

    def test_unknown_biblio_state_keys_fail_closed_without_reaching_store(self):
        unknown_key = 'synthetic_unknown_state_fact'
        unknown_value = 'synthetic forbidden marker 9f3c'
        cases_by_field = {
            'biblio_state': ({'present': False}, 'state'),
            'state_transition': ({'changed': False}, 'state_transition'),
        }
        for field, (legitimate, payload_key) in cases_by_field.items():
            for include_legitimate in (False, True):
                projected = dict(legitimate) if include_legitimate else {}
                projected[unknown_key] = unknown_value
                for value in (projected, SimpleNamespace(to_observability=lambda projected=projected: projected)):
                    with self.subTest(field=field, include_legitimate=include_legitimate,
                                      source=type(value).__name__):
                        payload = biblio.build_biblio_event_payload(**{field: value})
                        biblio.emit_biblio_event(payload, chat_turn_logger_module=logger)
                        event = next(e for e in reversed(self.events) if e['stage'] == 'biblio')
                        encoded = json.dumps(event, sort_keys=True)
                        self.assertEqual(event['status'], 'disabled')
                        self.assertTrue(guard.is_guard_rejection_payload(event['payload_json']))
                        self.assertEqual(event['payload_json']['guarded_original_status'], 'disabled')
                        self.assertFalse(event['payload_json']['raw_content_included'])
                        self.assertNotIn(unknown_key, encoded)
                        self.assertNotIn(unknown_value, encoded)
                        self.assertNotIn(payload_key, event['payload_json'])

    def test_empty_biblio_state_projections_remain_legitimate_absence(self):
        for field, payload_key in (('biblio_state', 'state'),
                                   ('state_transition', 'state_transition')):
            for value in (None, {}):
                with self.subTest(field=field, value=value):
                    payload = biblio.build_biblio_event_payload(**{field: value})
                    biblio.emit_biblio_event(payload, chat_turn_logger_module=logger)
                    event = self.event('biblio', 'disabled')
                    self.assertEqual(event['payload'][payload_key], {})

    def test_raw_generation_identifier_has_no_legacy_write_path(self):
        logger.emit('llm_call', payload={'provider_generation_id': 'gen-lowercase'})
        self.assert_rejection('llm_call')

    def assert_rejection(self, stage):
        event = next(e for e in reversed(self.events) if e['stage'] == stage)
        p = event['payload_json']
        self.assertTrue(guard.is_guard_rejection_payload(p))
        self.assertFalse(p['raw_content_included'])
        self.assertEqual(event['status'], 'refused')
        self.assertEqual(p['guarded_original_status'], 'ok')

    def test_dangerous_values_still_rejected_at_writer_boundary(self):
        values = ['synthetic private sentence', 'https://source.invalid/x', '/tmp/private',
                  '<xml>synthetic</xml>', 'A'*120, 'sk-live-synthetic000000',
                  'Bearer synthetic', 'id-'+'a'*200, 'gen-1800000000-Abc\x00Def',
                  'gen-1800000000-Abc\nDef', 'gen-1800000000-Abc\tDef']
        for value in values:
            with self.subTest(kind=values.index(value)):
                logger.emit('llm_call', payload={'provider_generation_id': value})
                self.assert_rejection('llm_call')
                memory = cases.memory_payload()
                memory['basket_candidates'][0]['candidate_id_sha256_12'] = value
                logger.emit('memory_chain_snapshot', payload=memory)
                self.assert_rejection('memory_chain_snapshot')
                state = cases.biblio_payload()
                state['state']['persistence_mode'] = value
                logger.emit('biblio', payload=state)
                self.assert_rejection('biblio')

    def test_provider_writer_rejects_controls_and_types_before_hashing(self):
        for value in [cases.GENERATION_ID + '\n', '\t' + cases.GENERATION_ID, 123, True,
                      'https://source.invalid/x', '/tmp/private', 'A'*120, 'sk-live-synthetic000000',
                      'Bearer synthetic', '<xml/>', 'id-'+'a'*200]:
            with self.subTest(kind=type(value).__name__):
                self.call_provider('llm', value)
                self.assert_rejection('llm_call')

    def test_contextual_fields_do_not_accept_wrong_paths_or_unbounded_values(self):
        for stage, payload in [
            ('unrelated', cases.memory_payload()),
            ('unrelated', {'state': cases.biblio_payload()['state']}),
            ('llm_call', {'state': cases.biblio_payload()['state']}),
            ('web_search', {'state': {'source_domain': 'www.source.invalid'}}),
            ('prompt_prepared', {'start_ts': '2026-09-01T00:00:00Z'}),
        ]:
            with self.subTest(stage=stage):
                logger.emit(stage, payload=payload)
                self.assert_rejection(stage)
        for value in [True, {}, '2026-99-99T00:00:00Z', '2026-09-01T00:00:00Z\n', 'https://source.invalid']:
            payload = {'memory_prompt_injection': cases.prompt_memory_summary()}
            payload['memory_prompt_injection']['parent_summaries_injected'][0]['start_ts'] = value
            logger.emit('prompt_prepared', payload=payload)
            self.assert_rejection('prompt_prepared')
        for value in ['https://www.source.invalid', 'www.source.invalid/path', 'www.source.invalid:443',
                      'www.source.invalid?token=synthetic', 'www.source.invalid\n', 'www.'+'a'*64+'.invalid']:
            logger.emit('web_search', payload={'source_material_summary': [{'source_domain': value}]})
            self.assert_rejection('web_search')
        for key, value in [('page_no', True), ('present', 1), ('persistence_mode', {}),
                           ('unknown_key', 1), ('last_candidate_count', 9)]:
            payload = cases.biblio_payload()
            payload['state'][key] = value
            logger.emit('biblio', payload=payload)
            self.assert_rejection('biblio')
        deep = {'present': True}
        for _ in range(10):
            deep = {'state': deep}
        logger.emit('biblio', payload={'state': deep})
        self.assert_rejection('biblio')


if __name__ == '__main__':
    unittest.main()
