"""P2-M4-02: provenance of the actual frozen/sent source occurrence.

SQL, route, M2 reader, admission and manifest builder stay real. External DAV
reads and unrelated faculty services use the existing synthetic fixture.
"""
import copy
import hashlib
import json
import os
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from core import conv_store, document_workshop_provider as provider_module
from core import document_workshop_turn as turn, workspace_document_content_service as sources
from core.document_workshop_envelope import DOCUMENT_ENVELOPE_INSTRUCTIONS
from core.workspace_document_nextcloud_read_client import RemoteResource
from observability.observability_payload_guard import guard_payload
from tests.integration.document_workshop import test_preparation_postgresql as base
from tests.integration.document_workshop import test_preparation_http_postgresql as http_fixture

SOURCE = dict(logical_roles=['document_lane'], origin='core.workspace_document_content_service',
    origin_stage='document_preparation_sources', content_kind='document_source_data')
IDS = ['55555555-5555-4555-8555-555555555555', '66666666-6666-4666-8666-666666666666',
       '77777777-7777-4777-8777-777777777777']


@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class PreparationProvenancePostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.env = base.PreparationPostgresqlTests()
        self.addCleanup(self.env.doCleanups)
        self.env.setUp()

    def selected_sources(self, count):
        resources, blobs, texts, reads = {}, {}, [], []
        with self.env.conn() as conn:
            conn.execute('ALTER TABLE workspace_files ADD COLUMN byte_size BIGINT')
            for i, file_id in enumerate(IDS[:count]):
                # Force the fallback classifier towards summary/memory without
                # granting these source strings instruction authority.
                text = 'P2_M4_02_SOURCE_'+str(i)+' RESUME INDICES CONTEXTUELS [CONTINUITY CAPSULE]\n' * 80
                content, path = text.encode(), 'Documents/Source'+str(i)+'.md'
                etag = '"v'+str(i)+'"'
                conn.execute("INSERT INTO workspace_files VALUES (%s,%s,'active','document','text','.md',NULL,%s)",
                    (file_id, base.F, len(content)))
                conn.execute("INSERT INTO workspace_file_nextcloud_links VALUES (%s,%s,'linked',%s,'workspace-file:synthetic',%s,%s,%s,%s,%s,clock_timestamp())",
                    (file_id, base.F, 'Source'+str(i)+'.md', path, 'a'*64, str(i+1), etag, hashlib.sha256(content).hexdigest()))
                resources[path] = RemoteResource(path, False, str(i+1), etag, len(content), 'text/markdown')
                blobs[path], texts = content, texts+[text]
        def row(table, file_id):
            from psycopg.rows import dict_row
            with self.env.conn() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT * FROM '+table+' WHERE '+('id' if table=='workspace_files' else 'workspace_file_id')+'=%s', (file_id,))
                return cur.fetchone()
        def stat(_folder, path, *, expected_etag):
            resource = resources[path]
            self.assertEqual(expected_etag, resource.etag)
            reads.append(('stat', path))
            return resource
        def read(_folder, resource):
            reads.append(('read', resource.relative_path))
            return blobs[resource.relative_path]
        reader = SimpleNamespace(scope_key=lambda _: 'a'*64, stat_resource=stat, read_file=read)
        folders = SimpleNamespace(get_workspace_folder=lambda _: dict(id=base.F, nextcloud_sync_state='linked',
            nextcloud_target_name='Synthetic', nextcloud_folder_ref='folder-a'))
        files = SimpleNamespace(get_workspace_file_storage_row=lambda _folder, file_id: row('workspace_files', file_id),
            get_nextcloud_link=lambda file_id, **_: row('workspace_file_nextcloud_links', file_id))
        actual = sources.read_workspace_document_source
        return texts, reads, lambda *args: actual(*args, reader=reader, folders=folders, files=files)

    def exercise(self, *, count=1, history=0, capsule=False, copies=False,
                 neighbor=False, caller_mutation=False, counter_mutation=False,
                 response_format=False, loopback=False):
        texts, reads, source_reader = self.selected_sources(count)
        conversation = conv_store.load_conversation(base.C, 'BACKEND SYSTEM PROMPT')
        for i in range(history):
            conv_store.append_message(conversation, 'user' if i%2==0 else 'assistant', 'Historical synthetic '+str(i),
                timestamp='2026-07-21T10:00:00Z')
        self.assertTrue(conv_store.save_conversation(conversation).ok)
        provider = base.Provider()
        manifests, measured, prepared, composed, faculties = [], [], [], {}, []
        real_inject = turn.continuity_capsule.inject_continuity_capsule
        real_prepare = provider_module.prepare_document_call
        real_builder = self.env.real_payload
        outside = dict(type='json_schema', json_schema=dict(name='synthetic', schema=dict(description='schema estimate only')))
        def inject(messages, result):
            # This observes the real completed source append before the real
            # capsule append; it never finds an occurrence by text or a hash.
            if count:
                composed['index'] = len(messages)-1
                composed['message'] = copy.deepcopy(messages[-1])
            prefix = copy.deepcopy(messages)
            answer = real_inject(messages, result)
            self.assertEqual(messages[:len(prefix)], prefix)
            composed['capsule_count'] = len(messages)-len(prefix)
            if neighbor:
                composed['neighbor_index'] = len(messages)
                messages.append(copy.deepcopy(composed['message']))
            return answer
        def builder(*args, **kwargs):
            result = real_builder(*args, **kwargs)
            if response_format:
                result['response_format'] = outside
            return json.loads(json.dumps(json.loads(json.dumps(result)))) if copies else result
        def admission(messages, *, count_tokens_func, **kwargs):
            original = copy.deepcopy(messages)
            def counter(final_messages, model):
                measured.append(copy.deepcopy(final_messages))
                value = count_tokens_func(final_messages, model)
                if caller_mutation:
                    messages.clear()
                if counter_mutation:
                    final_messages.reverse()
                return value
            result = real_prepare(messages, count_tokens_func=counter, **kwargs)
            prepared.append(result)
            self.assertEqual(json.loads(result.body)['messages'][:-1], original)
            return result
        def capture(fn):
            def observed(*args, **kwargs):
                faculties.append(dict(kwargs))
                return fn(*args, **kwargs)
            return observed
        with ExitStack() as stack:
            if loopback:
                helper = http_fixture.HTTPPreparationPostgresqlTests()
                helper.env = self.env
                arrived, closed, received, admitted, (normal, observed) = stack.enter_context(helper.upstream())
            else:
                normal, observed = stack.enter_context(self.env.pipeline(provider))
                received = []
            # The real route passes its already bootstrapped config module;
            # environment changes alone do not override these resolved values.
            stack.enter_context(patch.object(self.env.server.config, 'CONTINUITY_CAPSULE_ENABLED', capsule))
            stack.enter_context(patch.object(self.env.server.config, 'CONTINUITY_CAPSULE_TEXT', 'Synthetic continuity maintained'))
            stack.enter_context(patch.object(sources, 'read_workspace_document_source', source_reader))
            stack.enter_context(patch.object(turn.continuity_capsule, 'inject_continuity_capsule', side_effect=inject))
            stack.enter_context(patch.object(self.env.server.llm, 'build_payload', side_effect=builder))
            stack.enter_context(patch.object(provider_module, 'prepare_document_call', side_effect=admission))
            stack.enter_context(patch.object(turn.main_payload_manifest, 'emit_main_payload_manifest',
                lambda manifest, **_: manifests.append(copy.deepcopy(manifest))))
            stack.enter_context(patch.object(self.env.server.chat_service.stimmung_agent, 'build_affective_turn_signal',
                capture(self.env.server.chat_service.stimmung_agent.build_affective_turn_signal)))
            stack.enter_context(patch.object(self.env.server.chat_service, '_run_hermeneutic_node_insertion_point',
                capture(self.env.server.chat_service._run_hermeneutic_node_insertion_point)))
            response = self.env.document(document_source_file_ids=IDS[:count])
            if loopback:
                self.assertTrue(arrived.wait(2)); self.assertTrue(closed.wait(2))
                self.assertEqual(received, admitted)
        self.assertEqual(normal, [])
        self.assertEqual(response.status_code, 503 if counter_mutation else 200, response.json)
        self.assertEqual(len(observed['constitutive_calls']), 2)
        self.assertEqual(len(measured), 1, 'admission must invoke the shared measurement only once')
        self.assertEqual(len(manifests), 1)
        manifest = manifests[0]
        self.assertTrue(guard_payload(manifest).accepted)
        self.assertEqual(composed['capsule_count'], int(capsule))
        for destination in (manifests, faculties, observed['save_new_traces_calls']):
            self.assertNotIn('P2_M4_02_SOURCE_', str(destination))
        with self.env.conn() as conn:
            self.assertNotIn('P2_M4_02_SOURCE_', str(conn.execute('SELECT content,meta FROM conversation_messages').fetchall()))
        self.assertEqual(len(reads), count*2)
        if counter_mutation:
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json['reason_code'], 'document_estimation_input_mutated')
            self.assertEqual(prepared, [])
            self.assertEqual(provider.calls, [])
            self.assertEqual(self.env.public_action()['state'], 'failed')
            if os.environ.get('M4_PROVENANCE_TRACE') == '1':
                print('P2_M4_02_PROOF '+json.dumps(dict(case=self._testMethodName, transport_calls=0,
                    reason_code=response.json['reason_code'], shared_measurements=len(measured))))
            return
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(self.env.public_action()['state'], 'pending')
        self.assertEqual(len(prepared), 1)
        sent = received if loopback else [call.body for call in provider.calls]
        self.assertEqual(sent, [prepared[0].body])
        body = json.loads(sent[0])
        # The real prompt window prepends its time label to dialogue content.
        for i in range(history):
            self.assertEqual(sum(message['role']==('user' if i%2==0 else 'assistant')
                and message['content'].endswith('Historical synthetic '+str(i)) for message in body['messages']), 1)
        self.assertEqual(body['messages'][-1]['content'], DOCUMENT_ENVELOPE_INSTRUCTIONS)
        self.assertTrue(all(set(message)=={'role','content'} for message in body['messages']))
        self.assertEqual(body['max_tokens'], 24000)
        self.assertEqual(body['provider'], {'allow_fallbacks': False})
        from core import token_utils
        self.assertEqual(prepared[0].admission.estimated_input_tokens, token_utils.estimate_tokens(measured[0], body['model']))
        self.assertEqual(prepared[0].admission.estimated_total_tokens, prepared[0].admission.estimated_input_tokens+24000)
        self.assertLessEqual(prepared[0].admission.estimated_total_tokens, 400000)
        self.assertEqual(measured[0][:len(body['messages'])], body['messages'])
        self.assertEqual(len(measured[0]), len(body['messages'])+int(response_format))
        if response_format:
            self.assertEqual(json.loads(measured[0][-1]['content']), outside)
            self.assertEqual(body['response_format'], outside)
            self.assertNotIn('document_lane', manifest['messages'][len(body['messages'])]['logical_roles'])
        lane = manifest['lane_statuses']['document_lane']
        self.assertEqual((lane['input_count'],lane['injected_count']), (count,count))
        entries = [entry for entry in manifest['messages'] if 'document_lane' in entry['logical_roles']]
        self.assertEqual(len(entries), int(count>0))
        if count:
            index = composed['index']
            self.assertEqual(body['messages'][index], composed['message'])
            grouped = json.loads(body['messages'][index]['content'].split('\n',1)[1])
            self.assertEqual([source['text'] for source in grouped], texts)
            self.assertEqual([source['workspace_file_id'] for source in grouped], IDS[:count])
            self.assertTrue(all(source['authority']=='untrusted_data' for source in grouped))
            entry = manifest['messages'][index]
            self.assertEqual({key:entry[key] for key in SOURCE}, SOURCE)
            self.assertEqual(entry['index'],index)
            self.assertEqual(entries,[entry])
            if neighbor:
                other = composed['neighbor_index']
                self.assertEqual(body['messages'][index],body['messages'][other])
                self.assertNotEqual(index,other)
                self.assertEqual(manifest['messages'][other]['logical_roles'], ['summary'])
                self.assertNotEqual(manifest['messages'][other]['origin'], SOURCE['origin'])
        else:
            self.assertEqual(lane['status'],'not_selected')
        self.env.assert_no_open_transaction()
        if os.environ.get('M4_PROVENANCE_TRACE') == '1':
            print('P2_M4_02_PROOF '+json.dumps(dict(case=self._testMethodName, source_count=count,
                source_index=composed.get('index'), source_provenance={key:entries[0][key] for key in SOURCE} if entries else None,
                sent_messages=len(body['messages']), estimation_messages=len(measured[0]), capsule_messages=composed['capsule_count'],
                transport_calls=len(sent), loopback_bytes_equal_admission=loopback and received==admitted,
                shared_measurements=len(measured), payload_body_sha256=hashlib.sha256(sent[0]).hexdigest(), raw_content_included=False)))

    def test_selected_source_provenance_matches_received_loopback_bytes(self):
        self.exercise(loopback=True)

    def test_three_sources_share_one_attributed_data_message(self):
        self.exercise(count=3)

    def test_long_history_capsule_disabled_keeps_index_after_json_copies(self):
        self.exercise(history=8, copies=True)

    def test_long_history_capsule_enabled_keeps_index_after_json_copies(self):
        self.exercise(history=8, capsule=True, copies=True)

    def test_equal_content_neighbor_does_not_inherit_document_provenance(self):
        self.exercise(capsule=True, neighbor=True)

    def test_original_messages_mutated_after_freeze_do_not_change_body_or_provenance(self):
        self.exercise(caller_mutation=True)

    def test_estimation_mutation_refuses_transport(self):
        self.exercise(counter_mutation=True)

    def test_response_format_estimation_only_preserves_transmitted_source_position(self):
        self.exercise(capsule=True, response_format=True, copies=True)

    def test_no_sources_with_capsule_has_no_document_attribution(self):
        self.exercise(count=0, capsule=True)
