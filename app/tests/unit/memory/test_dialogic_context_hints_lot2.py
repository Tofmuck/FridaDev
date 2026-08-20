import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from admin import admin_identity_read_model_projection
from core import chat_memory_flow, conversations_prompt_window
from memory import arbiter, memory_context_read, memory_identity_write
from observability import chat_turn_logger, log_store, observability_payload_guard


VALID_HINT = {
    'subject': 'dialogue',
    'content': 'SENTINEL_HINT',
    'confidence': 0.82,
    'reason_code': 'unresolved_tension',
}


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params):
        self.calls.append((query, params))

    def fetchall(self):
        return list(self.rows)


class _Conn:
    def __init__(self, cursor):
        self.cursor_value = cursor
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1


class _LogReaderCursor:
    def __init__(self, event):
        self.event = event

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _query, _params):
        return None

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return [(
            self.event['event_id'],
            self.event['conversation_id'],
            self.event['turn_id'],
            datetime(2026, 8, 20, 18, 0, tzinfo=timezone.utc),
            self.event['stage'],
            self.event['status'],
            self.event['duration_ms'],
            self.event['payload_json'],
        )]


class _LogReaderConn:
    def __init__(self, event):
        self.event = event

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return _LogReaderCursor(self.event)


class DialogicContextHintsLot2Tests(unittest.TestCase):
    def _capture_dialogic_context_event(self, *, result, persistence_result=None):
        observed = []
        store = SimpleNamespace(
            record_dialogic_context_hints=lambda _cid, _hints: persistence_result or {
                'status': 'ok',
                'reason_code': 'dialogic_context_hints_persisted',
                'persisted_count': len(result.get('hints') or []),
            },
        )
        with (
            patch.object(log_store, 'insert_chat_log_event', side_effect=lambda event: observed.append(event) or True),
            patch.object(chat_memory_flow, '_run_periodic_identity_agent', return_value={}),
        ):
            token = chat_turn_logger.begin_turn(
                conversation_id='conv-observability-sentinel',
                user_msg='S',
                web_search_enabled=False,
            )
            try:
                chat_memory_flow.record_identity_entries_for_mode(
                    'conv-observability-sentinel',
                    [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}],
                    mode='enforced_all',
                    arbiter_module=SimpleNamespace(extract_dialogic_context_hints=lambda _turns: result),
                    memory_store_module=store,
                    admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
                )
            finally:
                chat_turn_logger.end_turn(token, final_status='ok')
        events = [event for event in observed if event['stage'] == 'dialogic_context_hint_extractor']
        self.assertEqual(len(events), 1)
        return events[0]

    def _read_event(self, event):
        return log_store.read_chat_log_events(
            limit=1,
            stage='dialogic_context_hint_extractor',
            fail_closed=True,
            conn_factory=lambda: _LogReaderConn(event),
        )['items'][0]

    def test_success_reason_code_survives_real_stage_writer(self):
        event = self._capture_dialogic_context_event(
            result={
                'status': 'ok',
                'reason_code': 'dialogic_context_hints_extracted',
                'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION,
                'prompt_kind': arbiter.DIALOGIC_CONTEXT_HINT_PROMPT_KIND,
                'hints': [VALID_HINT],
            }
        )

        self.assertEqual(event['payload_json']['reason_code'], 'dialogic_context_hints_extracted')

    def test_projection_reads_real_log_reader_payload_shape(self):
        event = self._capture_dialogic_context_event(
            result={
                'status': 'ok',
                'reason_code': 'dialogic_context_hints_extracted',
                'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION,
                'prompt_kind': arbiter.DIALOGIC_CONTEXT_HINT_PROMPT_KIND,
                'hints': [VALID_HINT, VALID_HINT],
            }
        )
        item = self._read_event(event)
        self.assertIn('payload', item)
        self.assertNotIn('payload_json', item)

        block = admin_identity_read_model_projection.build_dialogic_context_block(
            evidence={'items': [], 'total_count': 2, 'limit': 20},
            latest_activity=item,
            runtime={
                'selection': {
                    'max_items': 2,
                    'max_tokens': 120,
                    'max_age_days': 7,
                    'min_confidence': 0.6,
                }
            },
        )

        fixture_path = Path(__file__).resolve().parents[2] / 'fixtures' / 'dialogic_context_observability_lot2.json'
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
        self.assertEqual(block, fixture)
        serialized = json.dumps(block, sort_keys=True)
        self.assertNotIn('SENTINEL_HINT', serialized)
        self.assertNotIn('payload_json', serialized)

        conflicting_legacy_shape = {
            **item,
            'payload_json': {
                'reason_code': 'mutant_wrong_payload_shape',
                'hint_count': 0,
                'persisted_count': 0,
                'prompt_kind': None,
            },
        }
        self.assertEqual(
            admin_identity_read_model_projection.build_dialogic_context_block(
                evidence={'items': [], 'total_count': 2, 'limit': 20},
                latest_activity=conflicting_legacy_shape,
                runtime=block['runtime'],
            ),
            fixture,
        )
        for field, mutant_value in (
            ('reason_code', None),
            ('hint_count', 0),
            ('persisted_count', 0),
            ('prompt_kind', None),
        ):
            with self.subTest(mutant_field=field):
                mutant = json.loads(json.dumps(block))
                mutant['latest_activity'][field] = mutant_value
                with self.assertRaises(AssertionError):
                    self.assertEqual(mutant, fixture)

    def test_projection_preserves_status_reason_counts_and_prompt_kind_for_all_outcomes(self):
        cases = (
            (
                'ok',
                'dialogic_context_hints_extracted',
                [VALID_HINT, VALID_HINT],
                {'status': 'ok', 'reason_code': 'dialogic_context_hints_persisted', 'persisted_count': 2},
                2,
            ),
            ('not_selected', 'dialogic_context_no_hint', [], None, 0),
            ('failed', 'dialogic_context_transport_error', [], None, 0),
        )
        for status, reason_code, hints, persistence_result, persisted_count in cases:
            with self.subTest(status=status):
                event = self._capture_dialogic_context_event(
                    result={
                        'status': status,
                        'reason_code': reason_code,
                        'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION,
                        'prompt_kind': arbiter.DIALOGIC_CONTEXT_HINT_PROMPT_KIND,
                        'hints': hints,
                    },
                    persistence_result=persistence_result,
                )
                item = self._read_event(event)
                block = admin_identity_read_model_projection.build_dialogic_context_block(
                    evidence={'items': [], 'total_count': 0, 'limit': 20},
                    latest_activity=item,
                    runtime={},
                )
                self.assertEqual(block['latest_activity'], {
                    'present': True,
                    'status': status,
                    'reason_code': reason_code,
                    'hint_count': len(hints),
                    'persisted_count': persisted_count,
                    'prompt_kind': arbiter.DIALOGIC_CONTEXT_HINT_PROMPT_KIND,
                    'raw_content_included': False,
                })

    def test_validator_accepts_only_dialogue_and_rejects_identity_mutants(self):
        valid = {'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION, 'hints': [VALID_HINT]}
        self.assertEqual(arbiter._validate_dialogic_context_hint_output(valid), [VALID_HINT])
        for mutation in (
            {**VALID_HINT, 'subject': 'user'},
            {**VALID_HINT, 'subject': 'llm'},
            {**VALID_HINT, 'stability': 'durable'},
            {**VALID_HINT, 'verdict': 'add'},
        ):
            with self.subTest(mutation=sorted(mutation)):
                with self.assertRaises(ValueError):
                    arbiter._validate_dialogic_context_hint_output(
                        {'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION, 'hints': [mutation]}
                    )

    def test_extractor_sends_complete_pair_and_keeps_relative_context(self):
        observed = {}
        result_payload = {
            'choices': [{'message': {'content': json.dumps({
                'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION,
                'hints': [VALID_HINT],
            })}}]
        }

        def fake_post(url, *, json, headers, timeout):
            observed.update(url=url, payload=json, headers=headers, timeout=timeout)
            return _Response(result_payload)

        settings = {'model': 'openai/gpt-5.4-mini', 'temperature': 0.0, 'top_p': 1.0, 'max_tokens': 700, 'timeout_s': 10}
        logger = SimpleNamespace(
            info=lambda template, *args: observed.setdefault('logs', []).append(template % args),
            warning=lambda *_args: None,
            error=lambda *_args: None,
        )
        with (
            patch.object(arbiter, 'logger', logger),
            patch.object(arbiter, '_runtime_identity_extractor_settings', return_value=settings),
            patch.object(arbiter, '_load_prompt', return_value='dialogic_context_hint_v1 dialogue'),
            patch.object(arbiter.requests, 'post', side_effect=fake_post),
            patch.object(arbiter.llm_client, 'or_chat_completions_url', return_value='https://synthetic.invalid/v1'),
            patch.object(arbiter.llm_client, 'or_headers', return_value={'X-Frida-Caller': arbiter.DIALOGIC_CONTEXT_HINT_CALLER}),
            patch.object(arbiter.llm_client, 'with_provider_attribution', side_effect=lambda payload, caller: {**payload, 'metadata': {'frida_caller': caller}}),
        ):
            result = arbiter.extract_dialogic_context_hints([
                {'role': 'user', 'content': 'SENTINEL_USER maintenant', 'timestamp': '2026-01-01T00:00:00Z'},
                {'role': 'assistant', 'content': 'SENTINEL_ASSISTANT', 'timestamp': '2026-01-01T00:00:01Z'},
            ])

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['hints'], [VALID_HINT])
        sent = json.loads(observed['payload']['messages'][1]['content'])['dialogue_turns']
        self.assertEqual([item['role'] for item in sent], ['user', 'assistant'])
        self.assertIn('maintenant', sent[0]['content'])
        self.assertEqual(observed['payload']['metadata']['frida_caller'], arbiter.DIALOGIC_CONTEXT_HINT_CALLER)
        self.assertEqual(observed['timeout'], 10)
        self.assertTrue(any('provider_caller=dialogic_context_hint_extractor' in line for line in observed['logs']))

    def test_extractor_fail_open_distinguishes_timeout_transport_and_invalid_schema(self):
        settings = {'model': 'openai/gpt-5.4-mini', 'temperature': 0.0, 'top_p': 1.0, 'max_tokens': 700, 'timeout_s': 10}
        common = (
            patch.object(arbiter, '_runtime_identity_extractor_settings', return_value=settings),
            patch.object(arbiter, '_load_prompt', return_value='dialogic_context_hint_v1 dialogue'),
            patch.object(arbiter.llm_client, 'or_chat_completions_url', return_value='https://synthetic.invalid/v1'),
            patch.object(arbiter.llm_client, 'or_headers', return_value={}),
            patch.object(arbiter.llm_client, 'with_provider_attribution', side_effect=lambda payload, caller: payload),
        )
        for item in common:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(common)])
        with patch.object(arbiter.requests, 'post', side_effect=requests.exceptions.Timeout()):
            timeout = arbiter.extract_dialogic_context_hints([{'role': 'user', 'content': 'S'}])
        transport_before = arbiter.get_runtime_metrics()['dialogic_context_hint_transport_error_count']
        with patch.object(arbiter.requests, 'post', side_effect=requests.exceptions.ConnectionError()):
            transport = arbiter.extract_dialogic_context_hints([{'role': 'user', 'content': 'S'}])
        with patch.object(arbiter.requests, 'post', return_value=_Response({'choices': [{'message': {'content': '{}'}}]})):
            invalid = arbiter.extract_dialogic_context_hints([{'role': 'user', 'content': 'S'}])
        self.assertEqual((timeout['status'], timeout['reason_code']), ('failed', 'dialogic_context_timeout'))
        self.assertEqual((transport['status'], transport['reason_code']), ('failed', 'dialogic_context_transport_error'))
        self.assertEqual(
            arbiter.get_runtime_metrics()['dialogic_context_hint_transport_error_count'],
            transport_before + 1,
        )
        self.assertEqual((invalid['status'], invalid['reason_code']), ('failed', 'dialogic_context_schema_invalid'))

    def test_writer_persists_only_temporary_dialogue_evidence(self):
        cursor = _Cursor()
        conn = _Conn(cursor)
        result = memory_identity_write.record_dialogic_context_hints(
            'conv-sentinel', [VALID_HINT], conn_factory=lambda: conn,
            normalize_identity_content_fn=lambda value: value.lower(),
            trace_float_fn=float, logger=SimpleNamespace(error=lambda *_args: None),
        )
        self.assertEqual(result['persisted_count'], 1)
        self.assertEqual(len(cursor.calls), 1)
        params = cursor.calls[0][1]
        self.assertEqual(params[1], 'dialogue')
        self.assertEqual((params[4], params[5], params[7]), ('episodic', 'dialogic_context', 'dialogue'))
        self.assertEqual(conn.commits, 1)

    def test_reader_selects_dialogue_and_compatible_user_history(self):
        cursor = _Cursor()
        memory_context_read.get_recent_context_hints(
            conn_factory=lambda: _Conn(cursor), default_max_items=2,
            default_max_age_days=7, default_min_confidence=0.6,
            logger=SimpleNamespace(error=lambda *_args: None),
        )
        query, params = cursor.calls[0]
        self.assertIn('(subject = %s AND stability = %s AND scope = %s)', query)
        self.assertEqual(params[:6], ('dialogue', 'episodic', 'dialogue', 'user', 'episodic', 'situation'))

    def test_prompt_labels_hints_as_dialogue_never_user_profile(self):
        message = conversations_prompt_window.make_context_hints_message(
            [{**VALID_HINT, 'timestamp': ''}], '2026-01-01T00:00:00Z', 'synthetic',
            delta_t_label_func=lambda *_args: '', count_tokens_func=lambda *_args: 1,
            context_hints_max_tokens=100, context_hints_max_items=2,
        )
        self.assertIn('Dialogue:', message['content'])
        self.assertNotIn('Utilisateur:', message['content'])
        self.assertNotIn('dialogic_context_hint_v1', message['content'])
        self.assertNotIn('dialogic_context', message['content'])

    def test_post_save_boundary_uses_context_writer_and_never_legacy_identity_writer(self):
        observed = {'context_pairs': [], 'persisted': [], 'periodic_pairs': []}
        arbiter_module = SimpleNamespace(
            extract_dialogic_context_hints=lambda turns: observed['context_pairs'].append(list(turns)) or {
                'status': 'ok', 'reason_code': 'dialogic_context_hints_extracted',
                'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION,
                'prompt_kind': arbiter.DIALOGIC_CONTEXT_HINT_PROMPT_KIND, 'hints': [VALID_HINT],
            }
        )
        store = SimpleNamespace(
            record_dialogic_context_hints=lambda cid, hints: observed['persisted'].append((cid, list(hints))) or {
                'status': 'ok', 'reason_code': 'dialogic_context_hints_persisted', 'persisted_count': 1,
            },
            persist_identity_entries=lambda *_args: self.fail('legacy identity writer called'),
            add_identity=lambda *_args: self.fail('add_identity called'),
        )
        with (
            patch.object(chat_memory_flow, '_run_periodic_identity_agent', side_effect=lambda _cid, pair, **_kw: observed['periodic_pairs'].append(list(pair)) or {}),
            patch.object(chat_memory_flow.chat_turn_logger, 'emit', return_value=True),
        ):
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-sentinel', [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}],
                mode='enforced_all', arbiter_module=arbiter_module, memory_store_module=store,
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            )
        self.assertEqual(len(observed['context_pairs']), 1)
        self.assertEqual(len(observed['persisted']), 1)
        self.assertEqual(len(observed['periodic_pairs']), 1)

        failure_events = []
        failure_store = SimpleNamespace(
            record_dialogic_context_hints=lambda *_args: {
                'status': 'failed', 'reason_code': 'dialogic_context_persistence_failed', 'persisted_count': 0,
            },
            persist_identity_entries=lambda *_args: self.fail('legacy identity writer called on persistence failure'),
            add_identity=lambda *_args: self.fail('add_identity called on persistence failure'),
        )
        with (
            patch.object(chat_memory_flow, '_run_periodic_identity_agent', return_value={}),
            patch.object(
                chat_memory_flow.chat_turn_logger,
                'emit',
                side_effect=lambda stage, **fields: failure_events.append((stage, fields)) or True,
            ),
        ):
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-failed-persistence',
                [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}],
                mode='enforced_all', arbiter_module=arbiter_module, memory_store_module=failure_store,
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            )
        context_events = [fields for stage, fields in failure_events if stage == 'dialogic_context_hint_extractor']
        self.assertEqual(len(context_events), 1)
        self.assertEqual(context_events[0]['status'], 'failed')
        self.assertEqual(context_events[0]['reason_code'], 'dialogic_context_persistence_failed')
        self.assertEqual(context_events[0]['payload']['persisted_count'], 0)

    def test_content_free_observability_contract_rejects_raw_hint_mutation(self):
        payload = {
            'schema_version': arbiter.DIALOGIC_CONTEXT_HINT_SCHEMA_VERSION,
            'subject': 'dialogue', 'hint_count': 1, 'persisted_count': 1,
            'write_mode': 'temporary_dialogic_context', 'write_effect': 'prompt_context_only',
            'identity_write': False, 'mutable_authority': False, 'max_items': 4,
            'reason_code': 'dialogic_context_hints_extracted',
            'status_schema_version': 'agentic_status_v1',
        }
        self.assertTrue(observability_payload_guard.guard_payload(payload).accepted)
        self.assertFalse(observability_payload_guard.guard_payload({**payload, 'content': 'RAW_MUTANT'}).accepted)


if __name__ == '__main__':
    unittest.main()
