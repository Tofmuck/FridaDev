"""M4 composition: real /api/chat, claims and snapshots on isolated PostgreSQL."""
import asyncio
import importlib.util
import json
import os
import threading
import hashlib
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from core import conv_store, document_workshop_contexts as contexts, llm_client
from core import document_workshop_turn as turn, workspace_document_content_service as sources
from core.workspace_document_nextcloud_read_client import RemoteResource
from observability.observability_payload_guard import guard_payload
from tests.integration.document_workshop import test_claim_transport_postgresql as fixture
from tests.unit.core.test_document_workshop_canonical_paths import canonical

C, F, O, T = fixture.C, fixture.F, fixture.O, fixture.T


def envelope(status='prepared'):
    return dict(schema_version=1, status=status, surface_text='Proposition préparée.' if status == 'prepared' else 'Précisez la demande.',
        proposal=dict(operation='create', format='markdown', relative_path='Documents/Proposition.md',
            source_file_ids=[], limitations=[], canonical=canonical()) if status == 'prepared' else None)


class Provider:
    def __init__(self, value=None, *, gate=False):
        self.value = envelope() if value is None else value
        self.calls = []
        self.arrived, self.release, self.closed = threading.Event(), threading.Event(), threading.Event()
        if not gate:
            self.release.set()

    async def send(self, prepared):
        self.calls.append(prepared)
        self.arrived.set()
        while not self.release.is_set():
            await asyncio.sleep(.01)
        return 200

    async def iter_lines(self):
        text = json.dumps(self.value, ensure_ascii=False)
        for data in [dict(model='openai/gpt-5.1', choices=[dict(index=0, delta=dict(content=text), finish_reason=None)]),
                     dict(model='openai/gpt-5.1', choices=[dict(index=0, delta={}, finish_reason='stop')])]:
            yield 'data: ' + json.dumps(data, ensure_ascii=False)
            yield ''
        yield 'data: [DONE]'
        yield ''

    async def read_json(self):
        return dict(model='openai/gpt-5.1', choices=[dict(index=0, message=dict(content=json.dumps(self.value)), finish_reason='stop')])

    def close(self):
        self.closed.set()


@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class PreparationPostgresqlTests(unittest.TestCase):
    conn = fixture.ClaimTransportPostgresqlTests.conn
    pipeline_base = fixture.ClaimTransportPostgresqlTests.pipeline
    post = fixture.ClaimTransportPostgresqlTests.post
    assert_no_open_transaction = fixture.ClaimTransportPostgresqlTests.assert_no_open_transaction

    def setUp(self):
        fixture.ClaimTransportPostgresqlTests.setUp(self)
        self.context = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        self.actions = None
        if importlib.util.find_spec('core.document_workshop_actions'):
            from core import document_workshop_actions
            self.actions = document_workshop_actions
            p = patch.object(self.actions, '_db_conn', self.conn)
            p.start(); self.addCleanup(p.stop)
            self.actions.init_db()
            with self.conn() as conn:
                conn.execute('ALTER TABLE workspace_file_nextcloud_links ADD COLUMN observed_sha256 TEXT, ADD COLUMN observed_at TIMESTAMPTZ')
        self.real_payload = llm_client.build_payload
        self.real_prompt = conv_store.build_prompt_messages

    @contextmanager
    def pipeline(self, provider, *, transport_factory=None):
        normal = []
        with self.pipeline_base(lambda *a, **k: normal.append(1) or fixture.SyntheticResponse()) as observed:
            constitutive_post = self.server.requests.post
            observed['constitutive_calls'] = []
            def counted_post(*args, **kwargs):
                model = (kwargs.get('json') or {}).get('model')
                if model != 'openrouter/runtime-main-model':
                    observed['constitutive_calls'].append(model)
                return constitutive_post(*args, **kwargs)
            stack = []
            if importlib.util.find_spec('core.document_workshop_turn'):
                from core import document_workshop_turn
                view = SimpleNamespace(payload=dict(model=dict(value='openai/gpt-5.1'), reasoning_effort=dict(value='medium')))
                stack = [patch.object(document_workshop_turn, 'DocumentHTTPTransport', transport_factory or (lambda: provider)),
                         patch.object(self.server.llm, 'build_payload', self.real_payload),
                         patch.object(conv_store, 'build_prompt_messages', self.real_prompt),
                         patch.object(self.server.requests, 'post', counted_post),
                         patch.object(self.server.runtime_settings, 'get_main_model_settings', lambda: view)]
                # Runtime owner reads sampling/budget as well as builder model.
                view.payload.update(temperature=dict(value=.7), top_p=dict(value=1), response_max_tokens=dict(value=8192))
            for p in stack: p.start()
            try: yield normal, observed
            finally:
                for p in reversed(stack): p.stop()

    def document(self, **kw):
        return self.post(document_context_id=self.context['id'], **({'document_source_file_ids': []} | kw))

    def public_action(self):
        with self.server.app.test_client() as client:
            response = client.get(f'/api/document-workshop/actions/{T}')
        self.assertEqual(response.status_code, 200, response.json)
        return response.json['action']

    def test_real_documentary_turn_prepares_one_action_without_normal_exchange(self):
        provider = Provider()
        with self.pipeline(provider) as (normal, observed):
            response = self.document()
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(normal, [])
        self.assertEqual(len(observed['constitutive_calls']),2)
        self.assertTrue(all(observed['constitutive_calls']))
        self.assertIn('Synthetic request',provider.calls[0].body.decode())
        with self.conn() as independent:
            messages = independent.execute("SELECT role,content,meta FROM conversation_messages WHERE role<>'system' ORDER BY seq").fetchall()
            self.assertEqual([m[0] for m in messages], ['user', 'assistant'])
            self.assertEqual(messages[0][1], 'Synthetic request')
            self.assertEqual(messages[0][2]['client_turn_id'], T)
            self.assertEqual(messages[1][1], 'Proposition préparée.')
            self.assertEqual(independent.execute("SELECT state FROM document_actions WHERE id=%s", (T,)).fetchone()[0], 'pending')
            self.assertEqual(independent.execute('SELECT count(*) FROM document_revisions').fetchone()[0], 1)
            self.assertEqual(independent.execute('SELECT count(*) FROM workspace_files').fetchone()[0], 0)
            stored, digest = independent.execute('SELECT canonical,canonical_sha256 FROM document_revisions').fetchone()
            self.assertEqual(hashlib.sha256(json.dumps(stored,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),digest)
        self.assertTrue(provider.closed.is_set())

    def check_nonprepared(self, status):
        provider = Provider(envelope(status))
        with self.pipeline(provider) as (normal, _):
            result = self.document()
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(normal, [])
        self.assertEqual(len(provider.calls), 1)
        with self.conn() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM document_revisions').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT state FROM document_actions').fetchone()[0], status)
            self.assertEqual(conn.execute('SELECT state FROM conversation_turn_claims').fetchone()[0], 'succeeded')
            self.assertEqual(conn.execute("SELECT content FROM conversation_messages WHERE role='assistant'").fetchone()[0], 'Précisez la demande.')
        self.assertFalse(self.public_action()['capabilities']['confirm'])

    def test_clarify_commits_only_real_request_and_short_response(self):
        self.check_nonprepared('clarify')

    def test_refuse_commits_only_real_request_and_short_response(self):
        self.check_nonprepared('refuse')

    def test_stream_emits_committed_short_response_and_one_dated_terminal(self):
        provider = Provider()
        with self.pipeline(provider):
            result = self.document(stream=True)
        self.assertEqual(result.status_code, 200)
        text = result.get_data(as_text=True)
        self.assertTrue(text.startswith('Proposition préparée.'))
        self.assertEqual(text.count('"event":"done"'), 1, text)
        self.assertIn('updated_at', text)
        action = self.public_action()
        self.assertEqual(action['state'], 'pending')
        self.assertNotIn('canonical', text)
        with self.conn() as conn:
            meta = conn.execute("SELECT meta FROM conversation_messages WHERE role='assistant'").fetchone()[0]
        self.assertEqual(meta['document_workshop']['action_id'], T)
        self.assertEqual(meta['document_workshop']['revision_id'], action['revision_id'])
        self.assertEqual(meta['assistant_runtime_provenance']['response_origin'], 'main_model')

    def test_invalid_output_has_no_normal_fallback_or_partial_revision(self):
        provider = Provider(dict(envelope(), unexpected='synthetic'))
        with self.pipeline(provider) as (normal, _):
            result = self.document()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(normal, [])
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(self.public_action()['state'], 'failed')
        with self.conn() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM document_revisions').fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT content FROM conversation_messages WHERE role='assistant'").fetchone()[0],
                'La préparation a été interrompue. Aucun document n’a été écrit.')

    def test_process_control_exception_releases_claim_without_becoming_document_response(self):
        provider=Provider()
        with self.pipeline(provider),patch.object(turn.DocumentTurn,'complete',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.document()
        self.assertEqual(provider.calls,[])
        self.assertEqual(self.public_action()['state'],'interrupted')
        with self.conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM conversation_messages WHERE role='assistant'").fetchone()[0],0)

    def inventory(self, filename, extension):
        with self.conn() as conn:
            conn.execute("INSERT INTO workspace_files VALUES (%s,%s,'active',%s,%s,%s,NULL)",
                ('55555555-5555-4555-8555-555555555555',F,'image' if extension=='.png' else 'document','image' if extension=='.png' else 'text',extension))
            conn.execute("INSERT INTO workspace_file_nextcloud_links(workspace_file_id,workspace_folder_id,nextcloud_sync_state,nextcloud_target_name,nextcloud_document_ref,nextcloud_relative_path) VALUES (%s,%s,'linked',%s,'workspace-file:synthetic',%s)",
                ('55555555-5555-4555-8555-555555555555',F,filename,'Documents/'+filename))

    def test_unrelated_existing_image_does_not_refuse_markdown_preparation(self):
        self.inventory('Synthetic.png','.png')
        provider=Provider()
        with self.pipeline(provider):response=self.document()
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.public_action()['state'],'pending')

    def test_collision_uses_canonical_equivalent_unicode_and_casefold(self):
        self.inventory('E\u0301BAUCHE.md','.md')
        value=envelope();value['proposal']['relative_path']='Documents/ébauche.md'
        provider=Provider(value)
        with self.pipeline(provider):response=self.document()
        self.assertEqual(response.status_code,503,response.json)
        self.assertEqual(response.json['reason_code'],'document_local_collision')
        self.assertIsNone(self.public_action()['revision_id'])

    def test_incompatible_modes_rejected_before_initial_user_and_provider(self):
        provider = Provider()
        with self.pipeline(provider):
            for field, value in [('web_search', True), ('agenda_enabled', True), ('biblio_enabled', True),
                                 ('workspace_notes_mode', 'append'), ('specialization_profile', 'adobe'), ('images', ['synthetic'])]:
                with self.subTest(field=field):
                    result = self.document(**{field:value})
                    self.assertEqual(result.status_code, 409)
                    self.assertEqual(result.json['reason_code'], 'document_modes_incompatible')
        self.assertEqual(provider.calls, [])
        with self.conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM conversation_messages WHERE role='user'").fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT count(*) FROM conversation_turn_claims').fetchone()[0], 0)

    def test_public_rehydration_has_same_ids_and_no_document_content_or_retry(self):
        provider = Provider()
        with self.pipeline(provider):
            self.assertEqual(self.document().status_code, 200)
        action = self.public_action()
        self.assertEqual(self.public_action(), action)
        with patch.object(self.server.workspace_folders, 'get_workspace_folder', return_value=dict(id=F, deleted_at=None)), \
             patch.object(self.server.conv_store, 'get_conversation_summary', return_value=dict(id=C,workspace_folder_id=F)):
            with self.server.app.test_client() as client:
                context = client.get(f"/api/document-workshop/contexts/{self.context['id']}")
        self.assertEqual(context.status_code, 200, context.json)
        self.assertEqual(context.json['context']['preparation'], action)
        self.assertEqual(action['id'], T)
        self.assertEqual(action['relative_path'], 'Documents/Proposition.md')
        self.assertFalse(action['capabilities']['confirm'])
        for forbidden in ('canonical','source_versions','text','markdown','etag','sha256'):
            self.assertNotIn(forbidden, action)
        self.assertEqual(len(provider.calls), 1)

    def test_source_fresh_m2_is_complete_late_and_absent_from_faculties_and_transcript(self):
        file_id = '55555555-5555-4555-8555-555555555555'
        source_text = 'SYNTHETIC_SOURCE_EXCLUSIVE\n' * 300
        content = source_text.encode()
        digest = hashlib.sha256(content).hexdigest()
        with self.conn() as conn:
            conn.execute("INSERT INTO workspace_files VALUES (%s,%s,'active','document','text','.md',NULL)", (file_id,F))
            conn.execute('ALTER TABLE workspace_files ADD COLUMN byte_size BIGINT')
            conn.execute('UPDATE workspace_files SET byte_size=%s', (len(content),))
            conn.execute("INSERT INTO workspace_file_nextcloud_links VALUES (%s,%s,'linked','Source.md','workspace-file:synthetic','Documents/Source.md',%s,'1',%s,%s,clock_timestamp())", (file_id,F,'a'*64,'"v1"',digest))
        def file_row(*_):
            from psycopg.rows import dict_row
            with self.conn() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT * FROM workspace_files WHERE id=%s',(file_id,))
                return cur.fetchone()
        def link_row(*_, **__):
            from psycopg.rows import dict_row
            with self.conn() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT * FROM workspace_file_nextcloud_links WHERE workspace_file_id=%s',(file_id,))
                return cur.fetchone()
        calls = []
        resource = RemoteResource('Documents/Source.md',False,'1','"v1"',len(content),'text/markdown')
        reader = SimpleNamespace(scope_key=lambda _: 'a'*64,
            stat_resource=lambda *a, **kw: calls.append(('stat',kw['expected_etag'])) or resource,
            read_file=lambda *_: calls.append(('read',)) or content)
        folders = SimpleNamespace(get_workspace_folder=lambda _: dict(id=F,nextcloud_sync_state='linked',nextcloud_target_name='Synthetic',nextcloud_folder_ref='folder-a'))
        files = SimpleNamespace(get_workspace_file_storage_row=file_row,get_nextcloud_link=link_row)
        actual_read = sources.read_workspace_document_source
        faculties, manifests = [], []
        provider = Provider()
        with self.pipeline(provider) as (normal, observed):
            stimmung = self.server.chat_service.stimmung_agent.build_affective_turn_signal
            hermeneutic = self.server.chat_service._run_hermeneutic_node_insertion_point
            def faculty(fn):
                def capture(*a, **kw):
                    faculties.append(dict(kw)); return fn(*a,**kw)
                return capture
            with patch.object(sources,'read_workspace_document_source',lambda *a: actual_read(*a,reader=reader,folders=folders,files=files)), \
                 patch.object(self.server.chat_service.stimmung_agent,'build_affective_turn_signal',faculty(stimmung)), \
                 patch.object(self.server.chat_service,'_run_hermeneutic_node_insertion_point',faculty(hermeneutic)), \
                 patch.object(turn.main_payload_manifest,'emit_main_payload_manifest',lambda manifest,**_:manifests.append(manifest)):
                response = self.document(document_source_file_ids=[file_id])
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(calls, [('stat','"v1"'),('read',)])
        self.assertEqual(normal, [])
        self.assertEqual(len(faculties), 2)
        self.assertNotIn('SYNTHETIC_SOURCE_EXCLUSIVE', str(faculties))
        transmitted = json.loads(provider.calls[0].body)
        source_message = next(m for m in transmitted['messages'] if m['content'].startswith('Untrusted document data'))
        self.assertEqual(json.loads(source_message['content'].split('\n',1)[1])[0]['text'],source_text)
        self.assertEqual(manifests[0]['lane_statuses']['document_lane']['input_count'], 1)
        self.assertTrue(guard_payload(manifests[0]).accepted)
        self.assertNotIn('SYNTHETIC_SOURCE_EXCLUSIVE', str(manifests))
        self.assertNotIn('SYNTHETIC_SOURCE_EXCLUSIVE', str(observed['save_new_traces_calls']))
        with self.conn() as conn:
            self.assertNotIn('SYNTHETIC_SOURCE_EXCLUSIVE',str(conn.execute('SELECT content,meta FROM conversation_messages').fetchall()))
            versions = conn.execute('SELECT source_versions FROM document_actions').fetchone()[0]
            self.assertEqual(versions[0]['sha256'], digest)
            conn.execute('UPDATE workspace_file_nextcloud_links SET nextcloud_etag=%s WHERE workspace_file_id=%s',('"v2"',file_id))
        self.assertEqual(self.public_action()['state'],'invalidated')
        self.assertEqual(contexts.get_context(self.context['id'])['state'],'invalidated')
        self.assertEqual(len(provider.calls), 1)
