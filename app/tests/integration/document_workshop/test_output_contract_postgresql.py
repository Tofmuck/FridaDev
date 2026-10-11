"""Real mounted assembly, admission, HTTP/SSE and isolated durable projection."""
import hashlib
import json
import os
import unittest
from unittest.mock import patch

from observability import chat_turn_logger, log_store
from observability.observability_payload_guard import guard_payload
from tests.integration.document_workshop import test_preparation_http_postgresql as http
from tests.integration.document_workshop import test_preparation_postgresql as base


@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class OutputContractPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.http = http.HTTPPreparationPostgresqlTests()
        self.http.setUp()
        self.addCleanup(self.http.doCleanups)
        self.env = self.http.env

    def test_real_assembly_schema_routing_measurement_and_exact_revision(self):
        manifests, estimates = [], []
        real_counter = self.env.server.token_utils.estimate_tokens
        def counted(messages, model):
            result = real_counter(messages, model)
            estimates.append((json.loads(json.dumps(messages)), result))
            return result
        with self.http.upstream() as (arrived, closed, received, admitted, (normal, _)), \
             patch.object(self.env.server.token_utils, 'estimate_tokens', counted), \
             patch('core.document_workshop_turn.main_payload_manifest.emit_main_payload_manifest',
                   side_effect=lambda value, **_: manifests.append(value)):
            response = self.env.document()
            self.assertTrue(arrived.wait(2)); self.assertTrue(closed.wait(2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(received), 1); self.assertEqual(received, admitted)
        self.assertEqual(normal, [])
        body = json.loads(received[0])
        self.assertTrue('response_format' in body, 'documentary response_format missing')
        fmt = body['response_format']
        self.assertEqual(fmt['type'], 'json_schema')
        self.assertIs(fmt['json_schema']['strict'], True)
        self.assertEqual(body['provider'], dict(allow_fallbacks=False, require_parameters=True))
        self.assertEqual(body['model'], 'openai/gpt-5.1')
        self.assertEqual(body['max_tokens'], 24000)
        self.assertEqual(body['reasoning'], dict(effort='medium', exclude=True))
        self.assertTrue(body['stream']); self.assertTrue(body['stream_options']['include_usage'])
        for absent in ('temperature', 'top_p', 'stop', 'tools', 'plugins'):
            self.assertNotIn(absent, body)
        measured = [(messages, n) for messages, n in estimates
                    if len(messages) == len(body['messages']) + 1 and messages[:-1] == body['messages']]
        self.assertEqual(len(measured), 1)
        messages, estimate = measured[0]
        self.assertEqual(json.loads(messages[-1]['content']), fmt)
        self.assertEqual(len(manifests), 1)
        manifest = manifests[0]
        self.assertTrue(guard_payload(manifest, stage='main_payload_manifest').accepted)
        for change in (dict(strict='PRIVATE_SENTINEL'), dict(response_format_sha256_12='PRIVATE_SENTINEL'),
                       dict(content='PRIVATE_SENTINEL'), dict(estimation_only_messages=2)):
            altered = dict(manifest, document_output_contract=manifest['document_output_contract'] | change)
            decision = guard_payload(altered, stage='main_payload_manifest')
            self.assertFalse(decision.accepted)
            self.assertNotIn('PRIVATE_', str(decision.payload))
        self.assertEqual(len(manifest['messages']), len(body['messages']))
        self.assertFalse(manifest['runtime_settings']['temperature_present'])
        self.assertFalse(manifest['runtime_settings']['top_p_present'])
        self.assertEqual(manifest['budgets']['prompt']['estimated_prompt_tokens'], estimate)
        evidence = manifest['document_output_contract']
        self.assertEqual(evidence['response_format_sha256_12'], hashlib.sha256(messages[-1]['content'].encode()).hexdigest()[:12])
        self.assertTrue(evidence['estimate_includes_response_format'])
        self.assertEqual(evidence['estimation_only_messages'], 1)
        with self.env.conn() as conn:
            rows = conn.execute('SELECT canonical FROM document_revisions').fetchall()
            self.assertEqual(rows, [(base.envelope()['proposal']['canonical'],)])
            for table in ('document_execution_journal', 'document_receipts', 'workspace_files'):
                if conn.execute('SELECT to_regclass(%s)', (table,)).fetchone()[0]:
                    self.assertEqual(conn.execute('SELECT count(*) FROM ' + table).fetchone()[0], 0)

    def rejected(self, *, broken_sink=False):
        value = base.envelope(); value['proposal']['limitations'] = ['PRIVATE_ENVELOPE_SENTINEL']
        wire = ''.join('data: ' + json.dumps(dict(model='openai/gpt-5.1', choices=[
            dict(index=0, delta=delta, finish_reason=reason)])) + '\n\n'
            for delta, reason in ((dict(content=json.dumps(value)), None), ({}, 'stop')))
        wire = (wire + 'data: [DONE]\n\n').encode()
        log_store.init_log_storage(conn_factory=self.env.conn)
        insert = log_store.insert_chat_log_event
        traces, diagnostics = [], []
        def persist(event):
            if event['stage'] == 'turn_start': traces.append(chat_turn_logger.current_turn_id())
            return insert(event, conn_factory=self.env.conn)
        emit = chat_turn_logger.emit
        def observe(stage, **kw):
            if 'envelope_rejection' in kw.get('payload', {}):
                diagnostics.append(kw['payload'])
                if broken_sink: raise RuntimeError('PRIVATE_SINK_SENTINEL')
            return emit(stage, **kw)
        with self.http.upstream(wire=wire) as (arrived, closed, received, admitted, (normal, _)), \
             patch.object(log_store, 'insert_chat_log_event', persist), \
             patch.object(chat_turn_logger, 'emit', observe):
            response = self.env.document()
            self.assertTrue(arrived.wait(2)); self.assertTrue(closed.wait(2))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json['reason_code'], 'document_envelope_invalid')
        self.assertEqual(len(received), 1); self.assertEqual(received, admitted); self.assertEqual(normal, [])
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]['envelope_rejection'], 'limitation_code')
        self.assertEqual(len(traces), 1)
        with self.env.conn() as conn:
            events = conn.execute("SELECT conversation_id,payload_json FROM observability.chat_log_events "
                                  "WHERE turn_id=%s AND stage='document_preparation'", (traces[0],)).fetchall()
            selected = [(c, p) for c, p in events if 'envelope_rejection' in p]
            self.assertEqual(len(selected), 0 if broken_sink else 1)
            if selected:
                conversation, payload = selected[0]
                self.assertEqual(conversation, base.C)
                self.assertEqual(payload['action_id'], base.T)
                self.assertEqual(payload['context_id'], self.env.context['id'])
                self.assertEqual(payload['envelope_rejection'], 'limitation_code')
                self.assertEqual(payload['reason_code'], 'document_envelope_invalid')
            self.assertNotIn('PRIVATE_', json.dumps(events))
            self.assertNotIn('PRIVATE_', json.dumps(diagnostics))
            self.assertEqual(conn.execute('SELECT state,reason_code FROM document_actions').fetchall(),
                             [('failed', 'document_envelope_invalid')])
            self.assertEqual(conn.execute('SELECT state FROM conversation_turn_claims').fetchall(), [('failed',)])
            for table in ('document_revisions', 'document_execution_journal', 'document_receipts', 'workspace_files'):
                if conn.execute('SELECT to_regclass(%s)', (table,)).fetchone()[0]:
                    self.assertEqual(conn.execute('SELECT count(*) FROM ' + table).fetchone()[0], 0)

    def test_envelope_rejection_is_durable_and_content_free(self):
        self.rejected()

    def test_diagnostic_sink_failure_preserves_rejection_and_close(self):
        self.rejected(broken_sink=True)
