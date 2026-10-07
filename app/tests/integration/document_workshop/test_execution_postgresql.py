"""M5 confirmation, real publication and crash fencing on isolated PostgreSQL."""
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import threading
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict,replace
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from core import conv_store, conversation_turn_claims as claims
from core import document_workshop_actions as actions
from core.document_workshop_envelope import read_document_envelope
from core.document_markdown import serialize_markdown
from core.workspace_document_nextcloud_read_client import RemoteResource
from core import workspace_files, workspace_folders
from tests.integration.document_workshop import test_adoption_postgresql as adoption_fixture
from tests.unit.core.test_document_workshop_canonical_paths import canonical


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'), 'isolated M5 PostgreSQL required')
class ExecutionPostgresqlTests(unittest.TestCase):
    def setUp(self):
        p = patch.dict(os.environ, {'M2_PROOF_PG_SOCKET': os.environ['M5_PROOF_PG_SOCKET']})
        p.start(); self.addCleanup(p.stop)
        self.env = adoption_fixture.AdoptionPostgresqlTests(methodName='runTest')
        self.env.setUp(); self.addCleanup(self.env.doCleanups)
        self.conn = self.env.connection
        self.folder = self.env.context['workspace_folder_id']
        self.conversation = self.env.context['conversation_id']
        self.context = self.env.context['id']
        with self.conn() as conn:
            conn.execute('''ALTER TABLE conversations ADD COLUMN title text,
                ADD COLUMN created_at timestamptz, ADD COLUMN updated_at timestamptz,
                ADD COLUMN message_count integer, ADD COLUMN last_message_preview text;
                CREATE TABLE conversation_messages(conversation_id uuid REFERENCES conversations(id),
                seq integer,role text,content text,timestamp timestamptz,summarized_by text,
                embedded boolean,meta jsonb,PRIMARY KEY(conversation_id,seq));''')
        for store in (claims, actions, conv_store):
            p = patch.object(store, '_db_conn', self.conn); p.start(); self.addCleanup(p.stop)
        claims.init_db(); actions.init_db()
        with self.conn() as conn:
            conn.execute("ALTER TABLE document_actions ALTER COLUMN created_at SET DEFAULT '2000-01-01'::timestamptz")
        self.request_turn = str(uuid4())
        token = claims.acquire(conversation_id=self.conversation, turn_id=self.request_turn,
            request_fingerprint='1'*64, kind='preparation', context_id=self.context).token
        conversation = conv_store.new_conversation('Synthetic system', conversation_id=self.conversation)
        conversation['workspace_folder_id'] = self.folder
        conversation['messages'].append(dict(role='user', content='Synthetic request',
            timestamp='2026-10-06T00:00:00+00:00',meta={'client_turn_id': self.request_turn}))
        self.snapshot = conv_store.save_conversation_snapshot_in_transaction
        actions.save_initial(token, conversation, [], snapshot=self.snapshot)
        envelope = read_document_envelope(json.dumps(dict(schema_version=1,status='prepared',
            surface_text='Prepared.',proposal=dict(operation='create',format='markdown',
                relative_path='Documents/Exact  e\u0301.md',source_file_ids=[],limitations=[],canonical=canonical()))))
        conversation['messages'].append(dict(role='assistant', content='Prepared.',
            timestamp='2026-10-06T00:00:01+00:00',meta={'document_workshop':{}}))
        actions.finalize(token,conversation,envelope,[],serialize_markdown(envelope.canonical),snapshot=self.snapshot)
        self.action = actions.get_action(self.request_turn)
        self.before_claim = claims.read(self.request_turn)
        self.assertIsNotNone(importlib.util.find_spec('core.document_workshop_execution_service'),
            'M5 confirmation authority absent: prepared action has no executor')
        self.service = importlib.import_module('core.document_workshop_execution_service')
        self.store = importlib.import_module('core.document_workshop_execution_store')
        self.executor_module = importlib.import_module('core.document_workshop_executor')
        p = patch.object(self.store, '_db_conn', self.conn); p.start(); self.addCleanup(p.stop)
        self.store.init_db(); self.store.init_db()

    def body(self, **changes):
        return dict(context_id=self.context,conversation_id=self.conversation,
            workspace_folder_id=self.folder,revision_id=self.action['revision_id'],request_id=str(uuid4()))|changes

    def confirm(self, executor, body=None):
        return self.service.confirm(self.request_turn, body or self.body(), executor=executor)

    def rows(self, query, args=()):
        with self.conn() as conn:
            return conn.execute(query,args).fetchall()

    def assert_no_transaction(self):
        with self.conn() as conn:
            conn.execute('SELECT id FROM conversations WHERE id=%s::uuid FOR UPDATE NOWAIT', (self.conversation,))
            self.assertEqual(conn.execute("SELECT count(*) FROM pg_stat_activity WHERE datname='m1proof' AND state='idle in transaction'").fetchone()[0],0)

    def executor(self, client=None, **kw):
        return self.executor_module.DocumentExecutor(mutation_client=client or SyntheticDAV(self),
            storage_root=self.env.root, **kw)

    def test_two_request_ids_share_one_confirmed_execution_and_preserve_preparation_claim(self):
        client = SyntheticDAV(self, gate=True)
        executor = self.executor(client)
        first, second = self.body(), self.body()
        with ThreadPoolExecutor(2) as pool:
            request = pool.submit(self.confirm,executor,first)
            try:
                self.assertTrue(client.arrived.wait(5))
                self.assert_no_transaction()
                repeated,status = self.confirm(executor,second)
                self.assertEqual(status,200,repeated)
                self.assertEqual(repeated['action']['state'],'executing')
                self.assertEqual(self.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(1,)])
            finally:
                client.release.set()
                result,status = request.result(timeout=10)
        self.assertEqual(status,200,result)
        self.assertEqual(result['action']['state'],'succeeded')
        self.assertEqual(client.mutations,['PUT'])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(1,)])
        self.assertEqual(claims.read(self.request_turn),self.before_claim)
        repeated,status=self.confirm(executor,self.body())
        self.assertEqual(status,200); self.assertEqual(repeated['action']['state'],'succeeded')
        self.assertEqual(client.mutations,['PUT'])

    def test_success_publishes_existing_inventory_exact_names_and_one_atomic_receipt(self):
        client = SyntheticDAV(self)
        result,status = self.confirm(self.executor(client))
        self.assertEqual(status,200,result)
        self.assertEqual(result['action']['state'],'succeeded')
        items = workspace_files.list_workspace_files(self.folder)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['display_name'],'Exact  e\u0301.md')
        self.assertEqual(items[0]['original_filename'],'Exact  e\u0301.md')
        link = workspace_files.get_nextcloud_link(items[0]['id'],fail_closed=True,preserve_target_identity=True)
        self.assertEqual(link['nextcloud_relative_path'],'Documents/Exact  e\u0301.md')
        self.assertEqual(link['document_origin'],'frida')
        self.assertEqual(link['nextcloud_etag'],'"created"')
        self.assertEqual(self.rows('SELECT count(*) FROM document_revision_renders'),[(1,)])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(1,)])
        self.assertEqual(self.rows('SELECT count(*) FROM document_artifacts WHERE workspace_file_id IS NOT NULL AND current_revision_id IS NOT NULL'),[(1,)])
        self.assertEqual(claims.read(self.request_turn),self.before_claim)
        self.assert_no_transaction()

    def test_without_injected_executor_refuses_before_new_schema_or_claim(self):
        with self.conn() as conn:
            conn.execute('DROP TABLE document_execution_journal CASCADE')
        result,status=self.confirm(None)
        self.assertEqual(status,503,result)
        self.assertEqual(result['reason_code'],'document_execution_unavailable')
        self.assertEqual(actions.get_action(self.request_turn)['state'],'pending')
        self.assertEqual(self.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])

    def test_wrong_scope_or_revision_or_hostile_extra_field_mutates_nothing(self):
        client = SyntheticDAV(self)
        for field in ('context_id','conversation_id','workspace_folder_id','revision_id'):
            body=self.body(); body[field]=str(uuid4())
            result,status=self.confirm(self.executor(client),body)
            self.assertIn(status,(404,409),result)
        body=self.body(); body['relative_path']='Documents/../escape.md'
        result,status=self.confirm(self.executor(client),body)
        self.assertEqual(status,400,result)
        self.assertEqual(client.mutations,[])
        self.assertEqual(self.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])

    def test_pending_created_in_2000_remains_confirmable_without_age_limit(self):
        self.assertTrue(self.action['created_at'].startswith('2000-01-01'))
        self.assertEqual(self.confirm(self.executor())[1],200)
        self.assertEqual(self.confirm(self.executor())[0]['action']['state'],'succeeded')

    def test_injected_public_projection_is_closed_and_does_not_claim_confirmation_unavailable(self):
        projected=self.service.project_action(self.action,executor=self.executor())
        self.assertTrue(projected['capabilities']['confirm'])
        self.assertNotIn('write_confirmation_unavailable',projected['limitations'])
        self.assertEqual(projected['collections'],[])
        self.assertTrue(self.service.project_action(self.action)['capabilities']['confirm'] is False)
        self.assertIn('write_confirmation_unavailable',self.action['limitations'])
        private=self.action|dict(canonical={'private':'synthetic'},source_versions=[{'private':'synthetic'}],text='synthetic')
        projected=self.service.project_action(private,executor=self.executor())
        self.assertTrue(set(projected).isdisjoint({'canonical','source_versions','text'}))

    def captured_success(self):
        client=SyntheticDAV(self)
        executor=self.executor(client)
        original=executor.execute
        captures=[]
        executor.execute=lambda run:captures.append(run) or original(run)
        payload,status=self.confirm(executor)
        self.assertEqual(status,200,payload)
        return captures[0],client

    def proof(self,run,client):
        return self.store.publication_proof(run,result=client.result,content=client.content,
            scope_key='a'*64,storage_root=self.env.root)

    def test_publication_proof_requires_remote_identity_size_storage_bytes_and_claim_owner(self):
        run,client=self.captured_success()
        self.assertEqual(self.proof(run,client),'complete')
        file_id=self.rows('SELECT workspace_file_id FROM document_actions WHERE id=%s::uuid',(self.request_turn,))[0][0]
        updates=[("UPDATE workspace_file_nextcloud_links SET nextcloud_file_id='100'","UPDATE workspace_file_nextcloud_links SET nextcloud_file_id='99'"),
            ("UPDATE workspace_file_nextcloud_links SET nextcloud_scope_key='"+'b'*64+"'","UPDATE workspace_file_nextcloud_links SET nextcloud_scope_key='"+'a'*64+"'"),
            ('UPDATE workspace_files SET byte_size=byte_size+1','UPDATE workspace_files SET byte_size=byte_size-1'),
            ("UPDATE conversation_turn_claims SET owner_id='00000000-0000-4000-8000-000000000001' WHERE kind='confirmation'",
                "UPDATE conversation_turn_claims SET owner_id='"+run.token.owner_id+"' WHERE kind='confirmation'")]
        for update,restore in updates:
            with self.subTest(update=update):
                with self.conn() as conn:conn.execute(update)
                self.assertEqual(self.proof(run,client),'unknown')
                with self.conn() as conn:conn.execute(restore)
        key=self.rows('SELECT storage_key FROM workspace_files WHERE id=%s::uuid',(file_id,))[0][0]
        cached=self.env.root/key
        cached.write_bytes(b'x'*len(client.content))
        self.assertEqual(self.proof(run,client),'unknown')

    def test_lost_confirmation_cannot_append_remote_outcome_or_publish_or_compensate(self):
        run=self.store.begin(self.request_turn,self.body())
        self.store.intent(run)
        with self.conn() as conn:
            conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid",(run.token.turn_id,))
        client=SyntheticDAV(self)
        result=SimpleNamespace(state='known_success',reason_code='document_remote_created',http_status=201,
            resource=RemoteResource(run.target.relative_path,False,'99','"created"',3,'text/markdown'),
            creation_etag='"created"',created_collections=())
        before=self.rows('SELECT count(*) FROM document_execution_journal')
        with self.assertRaises(Exception):self.store.observe(run,'remote_outcome',result)
        self.assertEqual(self.rows('SELECT count(*) FROM document_execution_journal'),before)
        self.assertEqual(actions.get_action(self.request_turn)['state'],'remote_uncertain')
        repeated,status=self.confirm(self.executor(client))
        self.assertEqual(status,503,repeated)
        self.assertEqual(client.mutations,[])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        self.assertEqual(claims.read(self.request_turn),self.before_claim)

    def test_real_commit_with_lost_reply_is_verified_without_delete_or_second_put(self):
        client=SyntheticDAV(self)
        factory=self.conn
        lost=[]
        class LostReply:
            def __init__(inner):inner.real=factory();inner.published=False
            def __enter__(inner):return inner
            def __getattr__(inner,key):return getattr(inner.real,key)
            def execute(inner,query,args=()):
                if "SET state='succeeded',phase='complete'" in query:inner.published=True
                return inner.real.execute(query,args)
            def __exit__(inner,kind,value,tb):
                if kind is None and inner.published and not lost:
                    inner.real.commit();inner.real.close();lost.append(True)
                    raise OSError('synthetic lost commit reply')
                return inner.real.__exit__(kind,value,tb)
        with patch.object(self.store,'_db_conn',lambda:LostReply()):
            payload,status=self.confirm(self.executor(client))
        self.assertEqual(status,200,payload)
        self.assertEqual(payload['action']['state'],'succeeded')
        self.assertEqual(lost,[True])
        self.assertEqual(client.mutations,['PUT'])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(1,)])

    def test_cancel_during_remote_put_revokes_only_confirmation_and_refuses_late_outcome(self):
        client=SyntheticDAV(self)
        arrived,release=threading.Event(),threading.Event()
        original=client.create_document
        def blocked(*args,**kw):
            result=original(*args,**kw)
            arrived.set();self.assertTrue(release.wait(5));return result
        client.create_document=blocked
        with ThreadPoolExecutor(2) as pool:
            request=pool.submit(self.confirm,self.executor(client))
            try:
                self.assertTrue(arrived.wait(5))
                cancelled=actions.cancel(self.request_turn,self.context)
                self.assertEqual(cancelled['state'],'remote_uncertain')
                self.assert_no_transaction()
            finally:release.set();payload,status=request.result(timeout=10)
        self.assertEqual(status,503,payload)
        self.assertEqual(client.mutations,['PUT'])
        self.assertEqual(self.rows("SELECT count(*) FROM document_execution_journal WHERE event='remote_outcome'"),[(0,)])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        self.assertEqual(claims.read(self.request_turn),self.before_claim)

    def test_crash_after_put_intent_with_lost_claim_is_unknown_and_never_replayed(self):
        run=self.store.begin(self.request_turn,self.body())
        self.store.intent(run)
        # A client may die after sending PUT, before knowing its outcome.
        self.store.before_mutation(run,'PUT',run.target.relative_path)
        with self.conn() as conn:
            conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid",(run.token.turn_id,))
        state=actions.get_action(self.request_turn)
        self.assertEqual(state['state'],'remote_uncertain')
        self.assertIsNone(state['created_collections_count'])
        client=SyntheticDAV(self)
        self.assertEqual(self.confirm(self.executor(client))[1],503)
        self.assertEqual(client.mutations,[])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])

    def test_mounted_confirm_route_uses_real_dav_headers_sql_publication_and_readback(self):
        from flask import Flask
        from document_workshop_routes import register_document_workshop_routes
        from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_mutation_client_m5 import dav_server,creation_responses
        content=serialize_markdown(read_document_envelope(json.dumps(dict(schema_version=1,status='prepared',surface_text='Prepared.',
            proposal=dict(operation='create',format='markdown',relative_path=self.action['relative_path'],source_file_ids=[],limitations=[],canonical=canonical())))).canonical).encode()
        # inspect_create_target and create_document each perform their own fresh
        # preflight; all eight final creation responses are real urllib HTTP.
        replies=creation_responses(path=self.action['relative_path'],content=content)
        with dav_server(replies[:3]+replies) as (base,seen):
            executor=self.executor(NextcloudDocumentMutationClient(NextcloudFolderClientConfig(base,'test','synthetic')))
            app=Flask(__name__)
            register_document_workshop_routes(app,get_store=lambda:None,get_conversations=lambda:None,
                get_folders=lambda:None,get_files=lambda:None,get_executor=lambda:executor)
            with app.test_client() as browser:
                response=browser.post('/api/document-workshop/actions/'+self.request_turn+'/confirm',json=self.body())
                self.assertEqual(response.status_code,200,response.get_json())
                state=browser.get('/api/document-workshop/actions/'+self.request_turn).get_json()['action']
                self.assertEqual(state['state'],'succeeded')
                repeated=browser.post('/api/document-workshop/actions/'+self.request_turn+'/confirm',json=self.body())
                self.assertEqual(repeated.status_code,200,repeated.get_json())
        writes=[(method,path,headers,body) for method,path,headers,body in seen if method in ('PUT','MKCOL','DELETE')]
        self.assertEqual(len(writes),1)
        self.assertEqual(writes[0][0],'PUT')
        self.assertEqual(writes[0][2]['If-None-Match'],'*')
        self.assertEqual(writes[0][3],content)
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(1,)])

    def reprepare(self,*,relative_path='Documents/Exact  e\u0301.md',source_ids=(),versions=()):
        self.request_turn=str(uuid4())
        token=claims.acquire(conversation_id=self.conversation,turn_id=self.request_turn,request_fingerprint='2'*64,
            kind='preparation',context_id=self.context).token
        conversation=conv_store.load_conversation(self.conversation,'Synthetic system')
        conversation['messages'].append(dict(role='user',content='Synthetic explicit new request',timestamp='2026-10-06T00:00:02+00:00',meta={'client_turn_id':self.request_turn}))
        actions.save_initial(token,conversation,list(source_ids),snapshot=self.snapshot)
        envelope=read_document_envelope(json.dumps(dict(schema_version=1,status='prepared',surface_text='Prepared.',proposal=dict(
            operation='copy' if source_ids else 'create',format='markdown',relative_path=relative_path,
            source_file_ids=list(source_ids),limitations=[],canonical=canonical()))))
        conversation['messages'].append(dict(role='assistant',content='Prepared.',timestamp='2026-10-06T00:00:03+00:00',meta={'document_workshop':{}}))
        actions.finalize(token,conversation,envelope,list(versions),serialize_markdown(envelope.canonical),snapshot=self.snapshot)
        self.action=actions.get_action(self.request_turn)
        self.before_claim=claims.read(self.request_turn)

    def test_real_m2_fresh_source_at_confirmation_and_remote_change_refuses_put(self):
        from core import workspace_document_content_service as source_service
        from tests.unit.core.test_workspace_document_mutation_client_m5 import dav_server
        for changed in ('remote','local','matching'):
            with self.subTest(changed=changed):
                if changed!='remote':self.doCleanups();self.setUp()
                fresh=self.env.responses(path='Documents/Source.md',include_listing=False)
                replies=self.env.responses(path='Documents/Source.md')+[fresh[0]]+fresh
                replies+= [(412,{},b'')] if changed=='remote' else [fresh[0]]+fresh
                with dav_server(replies) as (base,seen):
                    reader=self.env.client(base)
                    listing,status=self.env.listing(reader);self.assertEqual(status,200,listing)
                    adopted,status=self.env.adopt(reader,listing['items'][0]['reference']);self.assertEqual(status,201,adopted)
                    file_id=adopted['workspace_file_id']
                    source=source_service.read_workspace_document_source(self.folder,file_id,reader=reader)
                    self.reprepare(source_ids=[file_id],versions=[asdict(source)])
                    if changed=='local':
                        with self.conn() as conn:conn.execute('UPDATE workspace_file_nextcloud_links SET nextcloud_etag=%s WHERE workspace_file_id=%s::uuid',('"v2"',file_id))
                    client=SyntheticDAV(self)
                    client.scope_key=lambda _:reader.scope_key('Scope')
                    executor=self.executor(client,source_reader=lambda folder,file:source_service.read_workspace_document_source(folder,file,reader=reader))
                    payload,status=self.confirm(executor)
                self.assertEqual(status,200 if changed=='matching' else 409,payload)
                self.assertEqual(client.mutations,['PUT'] if changed=='matching' else [])
                self.assertEqual([method for method,_,_,_ in seen].count('GET'),3 if changed=='matching' else 2)
                self.assertEqual(claims.read(self.request_turn),self.before_claim)

    def test_local_collision_and_scope_round_trip_prevent_confirmation_claim_and_mutation(self):
        client=SyntheticDAV(self)
        with self.conn() as conn:
            conn.execute("INSERT INTO workspace_files(id,workspace_folder_id,display_name,original_filename,storage_key,content_kind,media_kind,source_extension,status) VALUES(%s::uuid,%s::uuid,'EXACT  É.MD','EXACT  É.MD','synthetic/collision','document','text','.md','active')",
                (str(uuid4()),self.folder))
        payload,status=self.confirm(self.executor(client))
        self.assertEqual(status,409,payload)
        self.assertEqual(payload['reason_code'],'document_local_collision')
        self.assertEqual(client.mutations,[])
        self.assertEqual(self.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])
        with self.conn() as conn:
            conn.execute('UPDATE conversations SET workspace_folder_id=%s::uuid',(adoption_fixture.OTHER,))
            conn.execute('UPDATE conversations SET workspace_folder_id=%s::uuid',(self.folder,))
        payload,status=self.confirm(self.executor(client))
        self.assertEqual(status,409,payload)
        self.assertEqual(payload['action']['state'],'invalidated')
        self.assertEqual(client.mutations,[])

    def test_every_journal_failure_stops_later_effects_and_preserves_intentions(self):
        for event,writes,state in [('intent',[],'failed'),('put_intent',[],'remote_uncertain'),
                ('remote_outcome',['PUT'],'remote_uncertain'),('delete_intent',['PUT'],'remote_uncertain'),
                ('compensation_outcome',['PUT','DELETE'],'remote_uncertain')]:
            with self.subTest(event=event):
                if event!='intent':self.doCleanups();self.setUp()
                with self.conn() as conn:
                    conn.execute("CREATE FUNCTION m5_journal_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event='"+event+"' THEN RAISE EXCEPTION 'synthetic'; END IF; RETURN NEW; END $$; CREATE TRIGGER m5_journal_fault BEFORE INSERT ON document_execution_journal FOR EACH ROW EXECUTE FUNCTION m5_journal_fault()")
                    if event in ('delete_intent','compensation_outcome'):
                        conn.execute("CREATE FUNCTION m5_file_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER m5_file_fault BEFORE INSERT ON workspace_files FOR EACH ROW EXECUTE FUNCTION m5_file_fault()")
                client=SyntheticDAV(self)
                payload,status=self.confirm(self.executor(client))
                self.assertEqual(status,503,payload)
                self.assertEqual(payload['action']['state'],state)
                self.assertEqual(client.mutations,writes)
                self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])
                self.assertEqual(self.rows('SELECT count(*) FROM document_execution_journal WHERE event=%s',(event,)),[(0,)])
                self.assertEqual(claims.read(self.request_turn),self.before_claim)

    def test_real_urllib_unknown_put_result_has_one_put_no_delete_no_publication(self):
        from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_mutation_client_m5 import dav_server,creation_responses
        replies=creation_responses(path=self.action['relative_path'])
        with dav_server(replies[:3]+replies[:3]+['drop']) as (base,seen):
            payload,status=self.confirm(self.executor(NextcloudDocumentMutationClient(NextcloudFolderClientConfig(base,'test','synthetic'))))
        self.assertEqual(status,503,payload)
        self.assertEqual(payload['action']['state'],'remote_uncertain')
        self.assertEqual([method for method,_,_,_ in seen if method in ('PUT','DELETE','MKCOL')],['PUT'])
        self.assertEqual(self.rows('SELECT count(*) FROM workspace_files'),[(0,)])
        self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])

    def test_crash_after_collection_intention_never_fabricates_absence_or_collection_count(self):
        self.reprepare(relative_path='Documents/New/Output.md')
        run=self.store.begin(self.request_turn,self.body())
        self.store.intent(run)
        self.store.before_mutation(run,'MKCOL','Documents/New')
        with self.conn() as conn:conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid",(run.token.turn_id,))
        action=actions.get_action(self.request_turn)
        self.assertEqual(action['state'],'remote_uncertain')
        self.assertIsNone(action['created_collections_count'])
        self.assertEqual(self.rows("SELECT count(*) FROM document_execution_journal WHERE event='mkcol_intent'"),[(1,)])
        client=SyntheticDAV(self)
        self.assertEqual(self.confirm(self.executor(client))[1],503)
        self.assertEqual(client.mutations,[])

    def test_fake_binary_render_runs_after_claim_and_rejects_failure_pages_cleanup_and_public_formats(self):
        # Historical M5 ID/counter-cases preserved, now using the closed M8-C
        # pair/provenance/lifecycle contract rather than single arbitrary bytes.
        from core.document_rendering import RenderingSession,render_confirmed
        from tests.support.document_renderer_fake import FakeRenderer
        from tests.support.document_renderer_fixtures import ENGINE
        for case in ('failure','pages','pages_absent','pages_float','cleanup','partial','digest','revision','canonical_hash','format','valid_but_product_inactive'):
            with self.subTest(case=case):
                if case!='failure':self.doCleanups();self.setUp()
                def change(m):
                    if case in ('pages','pages_absent','pages_float'):
                        m['page_evidence']['writer_pages']=21 if case=='pages' else None if case=='pages_absent' else 1.0
                    if case=='partial':m['artifacts'].pop('pdf')
                    if case=='digest':m['artifacts']['docx']['sha256']='0'*64
                    if case=='revision':m['revision_id']=str(uuid4())
                    if case=='canonical_hash':m['canonical_sha256']='0'*64
                    if case=='format':m['format']='pdf' # undeclared competing format
                worker=FakeRenderer(result_change=change,
                    status_change=dict(status='failed',reason_code='renderer_incomplete') if case=='failure' else {},
                    release_change=dict(state='failed',reason_code='renderer_cleanup_failed',workspace_removed=False) if case=='cleanup' else {})
                original=worker.submit
                def submit(request):
                    self.assertEqual(actions.get_action(self.request_turn)['state'],'executing')
                    self.assertEqual(self.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='active'"),[(1,)])
                    return original(request)
                worker.submit=submit
                session=RenderingSession(client=worker,expected_engine=ENGINE,wait=lambda:None)
                class SyntheticBinaryExecutor(self.executor_module.DocumentExecutor):
                    def _render(inner,run):return render_confirmed(run,'docx',session).docx
                client=SyntheticDAV(self)
                payload,status=self.confirm(SyntheticBinaryExecutor(mutation_client=client,storage_root=self.env.root))
                self.assertEqual(status,503,payload)
                self.assertEqual(worker.events.count('submit'),1)
                self.assertEqual(client.mutations,[])
                self.assertEqual(self.rows('SELECT count(*) FROM document_execution_journal'),[(0,)])
                self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])

    def test_get_and_reconfirm_verify_bundle_after_lost_reply_and_cache_read_failure(self):
        from flask import Flask
        from document_workshop_routes import register_document_workshop_routes
        client=SyntheticDAV(self)
        executor=self.executor(client)
        factory=self.conn;lost=[]
        class LostReply:
            def __init__(inner):inner.real=factory();inner.published=False
            def __enter__(inner):return inner
            def __getattr__(inner,key):return getattr(inner.real,key)
            def execute(inner,query,args=()):
                if "SET state='succeeded',phase='complete'" in query:inner.published=True
                return inner.real.execute(query,args)
            def __exit__(inner,kind,value,tb):
                if kind is None and inner.published and not lost:
                    inner.real.commit();inner.real.close();lost.append(True)
                    raise OSError('synthetic lost commit reply')
                return inner.real.__exit__(kind,value,tb)
        app=Flask(__name__)
        register_document_workshop_routes(app,get_store=lambda:None,get_conversations=lambda:None,
            get_folders=lambda:None,get_files=lambda:None,get_executor=lambda:executor)
        real_open=Path.open
        def blocked(path,*a,**kw):
            if path.is_relative_to(self.env.root):raise OSError('synthetic cache read failure')
            return real_open(path,*a,**kw)
        with patch.object(self.store,'_db_conn',lambda:LostReply()),patch.object(Path,'open',blocked),app.test_client() as browser:
            confirmed=browser.post('/api/document-workshop/actions/'+self.request_turn+'/confirm',json=self.body())
            self.assertEqual(confirmed.status_code,503,confirmed.get_json())
            observed=browser.get('/api/document-workshop/actions/'+self.request_turn).get_json()['action']
            self.assertEqual(observed['state'],'remote_uncertain')
            repeated=browser.post('/api/document-workshop/actions/'+self.request_turn+'/confirm',json=self.body())
            self.assertEqual(repeated.status_code,503,repeated.get_json())
        with app.test_client() as browser:
            observed=browser.get('/api/document-workshop/actions/'+self.request_turn).get_json()['action']
            self.assertEqual(observed['state'],'succeeded')
        self.assertEqual(self.rows('SELECT state FROM document_actions WHERE id=%s::uuid',(self.request_turn,)),[('succeeded',)])
        self.assertEqual(client.mutations,['PUT'])
        self.assertEqual(lost,[True])

    def test_missing_durable_success_outcome_projects_unknown_without_replay(self):
        run,client=self.captured_success()
        self.assertTrue(self.store.verify_committed_action(self.request_turn,storage_root=self.env.root))
        with self.conn() as conn:conn.execute("DELETE FROM document_execution_journal WHERE event='remote_outcome'")
        self.assertFalse(self.store.verify_committed_action(self.request_turn,storage_root=self.env.root))
        projected=self.service.project_action(actions.get_action(self.request_turn),executor=self.executor(client))
        self.assertEqual(projected['state'],'remote_uncertain')
        repeated,status=self.confirm(self.executor(client))
        self.assertEqual(status,503,repeated)
        self.assertEqual(client.mutations,['PUT'])

    def test_each_publication_write_failure_rolls_back_all_rows_and_compensates_exact_creation(self):
        for table,operation in [('workspace_files','INSERT'),('workspace_file_nextcloud_links','INSERT'),
                ('document_revision_renders','INSERT'),('document_artifacts','UPDATE'),
                ('document_receipts','INSERT'),('document_actions','UPDATE'),('conversation_turn_claims','UPDATE')]:
            with self.subTest(table=table):
                # Rebuild a genuinely isolated schema for every SQL fault.
                if table != 'workspace_files':
                    self.doCleanups(); self.setUp()
                client=SyntheticDAV(self)
                with self.conn() as conn:
                    condition="NEW.state='succeeded'" if table in ('document_actions','conversation_turn_claims') else 'TRUE'
                    conn.execute("CREATE FUNCTION m5_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF "+condition+" THEN RAISE EXCEPTION 'synthetic'; END IF; RETURN NEW; END $$")
                    conn.execute('CREATE TRIGGER m5_fault BEFORE '+operation+' ON '+table+' FOR EACH ROW EXECUTE FUNCTION m5_fault()')
                result,status=self.confirm(self.executor(client))
                self.assertEqual(status,503,result)
                self.assertEqual(result['action']['state'],'failed')
                self.assertEqual(client.mutations,['PUT','DELETE'])
                self.assertEqual(self.rows('SELECT count(*) FROM workspace_files'),[(0,)])
                self.assertEqual(self.rows('SELECT count(*) FROM workspace_file_nextcloud_links'),[(0,)])
                self.assertEqual(self.rows('SELECT count(*) FROM document_receipts'),[(0,)])
                self.assertEqual(self.rows('SELECT count(*) FROM document_revision_renders'),[(0,)])
                self.assertEqual(self.rows('SELECT count(*) FROM document_artifacts WHERE workspace_file_id IS NOT NULL'),[(0,)])
                self.assertEqual(claims.read(self.request_turn),self.before_claim)


class SyntheticDAV:
    """Only the network is synthetic; each boundary probes independent SQL."""
    def __init__(self, test, *, gate=False, state='known_success', compensation='absence_certain'):
        self.test,self.state,self.compensation=test,state,compensation
        self.mutations=[]
        self.arrived,self.release=threading.Event(),threading.Event()
        if not gate:self.release.set()

    def scope_key(self, _folder):return 'a'*64

    def inspect_create_target(self, _folder, target, **_):
        self.test.assert_no_transaction()
        self.arrived.set()
        self.test.assertTrue(self.release.wait(5))
        return ()

    def create_document(self, folder, target, content, *, format, confirmed_collections, before_mutation):
        self.test.assert_no_transaction()
        self.test.assertIs(before_mutation('PUT',target.relative_path),True)
        self.test.assertEqual(self.test.rows("SELECT count(*) FROM document_execution_journal WHERE event='put_intent'"),[(1,)])
        self.mutations.append('PUT')
        resource=RemoteResource(target.relative_path,False,'99','"created"',len(content),'text/markdown')
        self.content=content
        self.result=SimpleNamespace(state=self.state,reason_code='document_remote_created',http_status=201,
            resource=resource,creation_etag='"created"',created_collections=())
        return self.result

    def compensate_created_document(self, folder, target, result, *, before_mutation, format):
        self.test.assert_no_transaction()
        self.test.assertIs(before_mutation('DELETE',target.relative_path),True)
        self.mutations.append('DELETE')
        return SimpleNamespace(state=self.compensation,reason_code='document_compensation_absent',http_status=204)
