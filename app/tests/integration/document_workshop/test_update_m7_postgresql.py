"""M7 real SQL stores, Flask service and stateful HTTP DAV; synthetic data only."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from core import conv_store, document_workshop_contexts as contexts, document_workshop_actions as actions
from core import workspace_document_adoption_store as adoption, workspace_document_content_service as sources
from core import workspace_files, workspace_folders, document_workshop_runtime as runtime
from core import conversation_turn_claims as claims, document_workshop_execution_store as execution
from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_envelope import read_document_envelope
from core.document_canonical import validate_canonical
from core.document_markdown import serialize_markdown
from core.workspace_document_source_extraction import extract_complete_source
from core.workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.unit.core.test_document_workshop_canonical_paths import canonical
from tests.support.document_workshop_update_dav import update_dav
from tests.support.server_test_bootstrap import load_server_module_for_tests


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'),'dedicated PostgreSQL required')
class UpdateM7PostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.env=fixture.ExecutionPostgresqlTests('runTest');self.env.setUp();self.addCleanup(self.env.doCleanups)
        self.conn=self.env.conn;self.folder=self.env.folder;self.conversation=self.env.conversation
        self.server=load_server_module_for_tests()
        self.migration=Path(__file__).parents[3]/'core/sql/document_workshop_update_m7.sql'
        if self.migration.exists():
            with self.conn() as db:db.execute(self.migration.read_text())
        self.password=self.env.env.root/'synthetic-password';self.password.write_text('synthetic-only')

    def configured(self,base):
        return patch.dict(os.environ,dict(FRIDA_NEXTCLOUD_BASE_URL=base,FRIDA_NEXTCLOUD_USERNAME='test',
            FRIDA_NEXTCLOUD_ROOT_NAME='Frida',FRIDA_NEXTCLOUD_APP_PASSWORD_FILE=str(self.password)))

    def adopt(self,base,state):
        self.reader=NextcloudDocumentReadClient(NextcloudFolderClientConfig(base,'test','synthetic'))
        resource=self.reader.stat_resource('Scope',state['path']);content=self.reader.read_file('Scope',resource)
        result=adoption.publish_adoption(folder_id=self.folder,context_id=self.env.context,
            folder=workspace_folders.get_workspace_folder(self.folder),scope_key=self.reader.scope_key('Scope'),
            resource=resource,content=content,extraction=extract_complete_source(content,filename='Exact.md',media_type='text/markdown'),
            storage_root=self.env.env.root)
        return result['file']['id']

    def prepare(self,file_id,*,text='Revised',path=None,conversation_id=None):
        conversation_id=conversation_id or self.conversation
        link=workspace_files.get_nextcloud_link(file_id,fail_closed=True,preserve_target_identity=True)
        context=contexts.create_context(conversation_id=conversation_id,workspace_folder_id=self.folder,
            target_file_id=file_id,target_relative_path=link['nextcloud_relative_path'],target_document_ref=link['nextcloud_document_ref'],
            target_remote_identity=link['nextcloud_scope_key']+':'+link['nextcloud_file_id'])
        action_id=str(uuid4())
        token=self.env.store.claims.acquire(conversation_id=conversation_id,turn_id=action_id,
            request_fingerprint='a'*64,kind='preparation',context_id=context['id']).token
        conversation=conv_store.load_conversation(conversation_id,'Synthetic system')
        conversation['messages'].append(dict(role='user',content='Explicit synthetic update request',timestamp='2026-10-07T00:00:00Z',meta={'client_turn_id':action_id}))
        actions.save_initial(token,conversation,[],snapshot=self.env.snapshot)
        try:
            envelope=read_document_envelope(json.dumps(dict(schema_version=1,status='prepared',surface_text='Update prepared.',
                proposal=dict(operation='update',format='markdown',relative_path=path or link['nextcloud_relative_path'],
                    source_file_ids=[],limitations=[],canonical=canonical(text)))))
        except Exception as error:self.fail('M7 update envelope unavailable: '+type(error).__name__)
        target=sources.read_workspace_document_source(self.folder,file_id,reader=self.reader)
        conversation['messages'].append(dict(role='assistant',content=envelope.surface_text,timestamp='2026-10-07T00:00:01Z',meta={'document_workshop':{}}))
        actions.finalize(token,conversation,envelope,[],serialize_markdown(envelope.canonical),snapshot=self.env.snapshot,target_source=target)
        return actions.get_action(action_id)

    def confirm(self,action):
        body=dict(context_id=action['context_id'],conversation_id=action['conversation_id'],workspace_folder_id=action['workspace_folder_id'],
            revision_id=action['revision_id'],request_id=str(uuid4()))
        return self.server.app.test_client().post('/api/document-workshop/actions/'+action['id']+'/confirm',json=body)

    def test_migration_preserves_history_is_idempotent_and_never_runs_on_get(self):
        self.assertTrue(self.migration.exists(),'explicit M7 migration absent')
        before=self.env.rows('SELECT id,state,revision_id FROM document_actions')
        with self.conn() as db:db.execute(self.migration.read_text())
        self.assertEqual(before,self.env.rows('SELECT id,state,revision_id FROM document_actions'))

    def test_external_update_retains_identity_and_creation_origin_and_downloads_current_revision(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);before=workspace_files.get_workspace_file_storage_row(self.folder,file_id)
            action=self.prepare(file_id);result=self.confirm(action)
            self.assertEqual(result.status_code,200,result.json)
            receipt=result.json['action']['receipt'];self.assertEqual(receipt['operation'],'update')
            self.assertEqual(receipt['workspace_file_id'],file_id);self.assertEqual(receipt['nextcloud_file_id'],'42')
            self.assertEqual(receipt['creation_author'],'external');self.assertEqual(receipt['revision_author'],'frida')
            after=workspace_files.get_workspace_file_storage_row(self.folder,file_id)
            for key in ('id','display_name','original_filename','source_kind','created_at'):self.assertEqual(before[key],after[key],key)
            self.assertEqual(workspace_files.get_nextcloud_link(file_id,preserve_target_identity=True)['document_origin'],'external')
            self.assertEqual(self.server.app.test_client().get(receipt['product_link']).data,b'Revised\n')
            self.assertEqual(self.env.rows('SELECT count(*) FROM workspace_files'),[(1,)])
            self.assertEqual(self.env.rows('SELECT count(*) FROM workspace_file_nextcloud_links'),[(1,)])
            self.assertEqual([r[0] for r in state['seen'] if r[0] in ('PUT','DELETE','MKCOL')],['PUT'])

    def test_change_between_prepare_and_confirm_is_conflict_without_put(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));state.update(etag='"outside"',content=b'Outside\n')
            result=self.confirm(action);self.assertEqual(result.status_code,409,result.json)
            self.assertEqual(result.json['action']['state'],'conflict')
            self.assertEqual([r for r in state['seen'] if r[0]=='PUT'],[]);self.assertEqual(state['content'],b'Outside\n')

    def test_change_after_prelecture_is_conflict_412_without_compensation(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));state['concurrent_before_put']=True
            result=self.confirm(action);self.assertEqual(result.status_code,409,result.json)
            self.assertEqual(result.json['action']['state'],'conflict');self.assertEqual(state['content'],b'Concurrent\n')
            puts=[r for r in state['seen'] if r[0]=='PUT'];self.assertEqual(len(puts),1);self.assertEqual(puts[0][2]['If-Match'],'"v1"')
            self.assertFalse(any(r[0] in ('DELETE','MKCOL') for r in state['seen']))

    def test_successive_updates_keep_old_receipts_and_unique_file_current_download(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);first=self.prepare(file_id);r1=self.confirm(first)
            self.assertEqual(r1.status_code,200,r1.json);receipt=r1.json['action']['receipt']
            second=self.prepare(file_id,text='Second');r2=self.confirm(second);self.assertEqual(r2.status_code,200,r2.json)
            old=self.server.app.test_client().get('/api/document-workshop/actions/'+first['id']).json['action']
            self.assertEqual(old['state'],'succeeded');self.assertEqual(old['receipt'],receipt)
            self.assertEqual(self.server.app.test_client().get(receipt['product_link']).data,b'Second\n')
            self.assertEqual(self.env.rows('SELECT count(*) FROM workspace_files'),[(1,)])
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(2,)])
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),2)

    def fail_publication(self):
        with self.conn() as db:
            db.execute("CREATE FUNCTION proof_fail_update() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rollback'; END $$")
            db.execute('CREATE TRIGGER proof_fail_update BEFORE INSERT ON document_revision_renders FOR EACH ROW EXECUTE FUNCTION proof_fail_update()')

    def restore_publication(self):
        with self.conn() as db:db.execute('DROP TRIGGER proof_fail_update ON document_revision_renders; DROP FUNCTION proof_fail_update()')

    def test_real_rollback_after_put_then_get_repairs_metadata_with_new_authority_without_put(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);action=self.prepare(file_id);self.fail_publication()
            result=self.confirm(action);self.assertEqual(result.status_code,503,result.json)
            self.assertEqual(state['content'],b'Revised\n');self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(0,)])
            self.assertEqual(workspace_files.get_workspace_file_storage_row(self.folder,file_id)['sha256'],hashlib.sha256(b'Original\n').hexdigest())
            self.restore_publication()
            refreshed=self.server.app.test_client().get('/api/document-workshop/actions/'+action['id'])
            self.assertEqual(refreshed.json['action']['state'],'succeeded',refreshed.json)
            self.assertEqual(refreshed.json['action']['receipt']['workspace_file_id'],file_id)
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='succeeded'"),[(1,)])
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='interrupted'"),[(1,)])
            self.assertFalse(any(r[0] in ('DELETE','MKCOL') for r in state['seen']));self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)

    def test_new_remote_change_before_reconciliation_preserves_unknown_and_never_attributes_new_bytes(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));self.fail_publication();self.assertEqual(self.confirm(action).status_code,503)
            self.restore_publication();state.update(etag='"later"',content=b'Later external\n')
            refreshed=self.server.app.test_client().get('/api/document-workshop/actions/'+action['id'])
            self.assertEqual(refreshed.json['action']['state'],'remote_uncertain');self.assertNotIn('receipt',refreshed.json['action'])
            self.assertEqual(state['content'],b'Later external\n');self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(0,)])
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)

    def test_lost_dav_reply_cannot_become_success_from_matching_bytes_and_repeated_confirm_never_puts(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));state['drop_put']=True
            result=self.confirm(action);self.assertEqual(result.status_code,503,result.json)
            self.assertEqual(state['content'],b'Revised\n')
            for _ in range(2):
                view=self.server.app.test_client().get('/api/document-workshop/actions/'+action['id']).json['action']
                self.assertEqual(view['state'],'remote_uncertain');self.assertNotIn('receipt',view)
                self.assertEqual(self.confirm(action).status_code,503)
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)

    def test_missing_m7_constraint_disables_update_before_any_effect(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state))
            with self.conn() as db:db.execute('ALTER TABLE document_actions DROP CONSTRAINT document_update_target_shape')
            executor=runtime.get_executor();self.assertIsNotNone(executor);self.assertFalse(executor.supports_update)
            self.assertEqual(self.confirm(action).status_code,503)
            self.assertFalse(any(r[0]=='PUT' for r in state['seen']))

    def test_current_mime_corruption_is_not_a_complete_publication(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);action=self.prepare(file_id);self.assertEqual(self.confirm(action).status_code,200)
            with self.conn() as db:db.execute("UPDATE workspace_files SET mime_type='text/plain' WHERE id=%s::uuid",(file_id,))
            self.assertFalse(execution.verify_committed_action(action['id'],storage_root=self.env.env.root))
            self.assertEqual(self.server.app.test_client().get('/api/document-workshop/actions/'+action['id']).json['action']['state'],'remote_uncertain')

    def test_legacy_constraint_under_same_name_disables_update_before_put(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state))
            with self.conn() as db:
                db.execute("ALTER TABLE document_receipts DROP CONSTRAINT document_receipts_creation_author_check; ALTER TABLE document_receipts ADD CONSTRAINT document_receipts_creation_author_check CHECK (creation_author='frida')")
            self.assertFalse(runtime.get_executor().supports_update)
            self.assertEqual(self.confirm(action).status_code,503)
            self.assertFalse(any(r[0]=='PUT' for r in state['seen']))

    def test_explicit_target_path_cannot_be_replaced_by_model_proposal(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state)
            with self.assertRaisesRegex(DocumentWorkshopError,'document_update_target_invalid'):
                self.prepare(file_id,path='Documents/Other.md')
            self.assertEqual(self.env.rows("SELECT count(*) FROM document_actions WHERE operation='update' AND state='pending'"),[(0,)])
            self.assertFalse(any(r[0] in ('PUT','MKCOL','DELETE') for r in state['seen']))

    def assert_changed_target(self,**change):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));state.update(change)
            response=self.confirm(action);self.assertEqual(response.status_code,409,response.json)
            self.assertEqual(response.json['action']['state'],'conflict');self.assertNotIn('receipt',response.json['action'])
            self.assertFalse(any(r[0] in ('PUT','MKCOL','DELETE') for r in state['seen']))

    def test_missing_target_never_creates_replacement(self):self.assert_changed_target(missing=True)
    def test_replaced_identity_at_same_path_never_overwrites(self):self.assert_changed_target(file_id='999')
    def test_missing_etag_never_overwrites(self):self.assert_changed_target(etag='')
    def test_weak_etag_never_overwrites(self):self.assert_changed_target(etag='W/"v1"')
    def test_invalid_remote_identity_never_overwrites(self):self.assert_changed_target(file_id='')

    def test_two_conversations_old_version_real_triggers_invalidate_other_action(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);first=self.prepare(file_id)
            other=str(uuid4());conversation=conv_store.new_conversation('Synthetic',conversation_id=other)
            conversation['workspace_folder_id']=self.folder;self.assertTrue(conv_store.save_conversation(conversation).ok)
            second=self.prepare(file_id,conversation_id=other,text='Other')
            self.assertEqual(self.confirm(first).status_code,200)
            stale=actions.get_action(second['id']);self.assertEqual(stale['state'],'invalidated')
            self.assertEqual(contexts.get_context(second['context_id'])['state'],'invalidated')
            self.assertEqual(self.confirm(second).status_code,409)
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(1,)])

    def test_target_snapshot_immutable_and_cancel_a_preserves_b(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);first=self.prepare(file_id);second=self.prepare(file_id,text='Second')
            with self.assertRaises(Exception),self.conn() as db:
                db.execute("UPDATE document_actions SET target_version=jsonb_set(target_version,'{etag}','\"other\"') WHERE id=%s::uuid",(second['id'],))
            actions.cancel(first['id'],first['context_id']);self.assertEqual(actions.get_action(second['id'])['state'],'pending')
            self.assertEqual(self.confirm(first).status_code,409);self.assertEqual(self.confirm(second).status_code,200)
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)

    def test_rollback_at_final_link_update_has_no_partial_publication_then_repairs(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);action=self.prepare(file_id)
            with self.conn() as db:
                db.execute("CREATE FUNCTION proof_late_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic late rollback'; END $$; CREATE TRIGGER proof_late_fail BEFORE UPDATE ON workspace_file_nextcloud_links FOR EACH ROW EXECUTE FUNCTION proof_late_fail()")
            self.assertEqual(self.confirm(action).status_code,503)
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(0,)])
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_revision_renders'),[(0,)])
            self.assertEqual(self.env.rows('SELECT current_revision_id FROM document_artifacts WHERE workspace_file_id=%s::uuid',(file_id,)),[(None,)])
            self.assertEqual(workspace_files.get_workspace_file_storage_row(self.folder,file_id)['sha256'],hashlib.sha256(b'Original\n').hexdigest())
            with self.conn() as db:db.execute('DROP TRIGGER proof_late_fail ON workspace_file_nextcloud_links; DROP FUNCTION proof_late_fail()')
            self.assertEqual(self.server.app.test_client().get('/api/document-workshop/actions/'+action['id']).json['action']['state'],'succeeded')
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)

    def test_current_corrupt_cache_refuses_download_and_historical_receipt(self):
        with update_dav() as (base,state),self.configured(base):
            file_id=self.adopt(base,state);first=self.prepare(file_id);self.assertEqual(self.confirm(first).status_code,200)
            second=self.prepare(file_id,text='Second');response=self.confirm(second);self.assertEqual(response.status_code,200)
            row=workspace_files.get_workspace_file_storage_row(self.folder,file_id)
            from core import workspace_files_store
            workspace_files_store.workspace_file_path(self.env.env.root,row['storage_key']).write_bytes(b'Corrupt\n')
            self.assertFalse(execution.verify_committed_action(first['id'],storage_root=self.env.env.root))
            self.assertFalse(execution.verify_committed_action(second['id'],storage_root=self.env.env.root))
            self.assertNotEqual(self.server.app.test_client().get(response.json['action']['receipt']['product_link']).status_code,200)

    def test_raw_http_cannot_change_target_revision_or_add_force_fields(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state))
            body={k:action[k] for k in ('context_id','conversation_id','workspace_folder_id','revision_id')};body['request_id']=str(uuid4())
            route='/api/document-workshop/actions/'+action['id']+'/confirm'
            for key,value in (('revision_id',str(uuid4())),('context_id',str(uuid4())),('force',True),('etag','"later"')):
                invalid=body|{key:value};result=self.server.app.test_client().post(route,json=invalid)
                self.assertIn(result.status_code,(400,409),result.json)
            self.assertEqual(actions.get_action(action['id'])['state'],'pending');self.assertFalse(any(r[0]=='PUT' for r in state['seen']))

    def test_lease_loss_at_real_dav_gate_fences_late_owner_and_never_compensates(self):
        from concurrent.futures import ThreadPoolExecutor
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));state['block_put']=True;state['release'].clear()
            with ThreadPoolExecutor(1) as pool:
                future=pool.submit(self.confirm,action)
                try:
                    self.assertTrue(state['arrived'].wait(5));self.env.assert_no_transaction()
                    with self.conn() as db:db.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE kind='confirmation' AND state='active'")
                    current=self.server.app.test_client().get('/api/document-workshop/actions/'+action['id']).json['action']
                    self.assertEqual(current['state'],'remote_uncertain')
                finally:state['release'].set()
                response=future.result(timeout=10);self.assertEqual(response.status_code,503)
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(0,)])
            self.assertEqual([r[0] for r in state['seen'] if r[0] in ('PUT','DELETE','MKCOL')],['PUT'])
            self.assertEqual(self.confirm(action).status_code,503)

    def repaired(self,base,state):
        action=self.prepare(self.adopt(base,state));self.fail_publication();self.assertEqual(self.confirm(action).status_code,503)
        self.restore_publication();self.assertEqual(self.server.app.test_client().get('/api/document-workshop/actions/'+action['id']).json['action']['state'],'succeeded')
        return action

    def test_repair_proof_requires_its_own_durable_intention(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.repaired(base,state)
            # Corrupt only this disposable proof DB; product triggers stay on.
            with self.conn() as db:
                db.execute("ALTER TABLE document_execution_journal DISABLE TRIGGER document_execution_immutable; DELETE FROM document_execution_journal WHERE event='metadata_reconciliation'; ALTER TABLE document_execution_journal ENABLE TRIGGER document_execution_immutable")
            self.assertFalse(execution.verify_committed_action(action['id'],storage_root=self.env.env.root))

    def test_repair_proof_requires_fingerprint_bound_to_original_action(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.repaired(base,state)
            with self.conn() as db:
                db.execute("UPDATE conversation_turn_claims SET request_fingerprint=%s WHERE turn_id IN (SELECT confirmation_turn_id FROM document_execution_journal WHERE event='metadata_published')",('f'*64,))
            self.assertFalse(execution.verify_committed_action(action['id'],storage_root=self.env.env.root))

    def test_two_inflight_conversations_same_version_at_most_one_publication(self):
        from tests.support.document_workshop_m7_concurrency import exercise_two_updates
        exercise_two_updates(self, overlap=False)

    def test_two_inflight_updates_nowait_keep_live_claim_until_expiry_then_uncertain(self):
        from tests.support.document_workshop_m7_concurrency import exercise_two_updates
        exercise_two_updates(self, overlap=True)

    def test_interruption_before_effect_cannot_authorize_late_executor(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));data={k:action[k] for k in ('context_id','conversation_id','workspace_folder_id','revision_id')}
            data['request_id']=str(uuid4());run=execution.begin(action['id'],data)
            claims.finish(run.token,'interrupted');runtime.get_executor().execute(run)
            self.assertEqual(actions.get_action(action['id'])['state'],'failed')
            self.assertFalse(any(r[0]=='PUT' for r in state['seen']))
            self.assertEqual(self.confirm(action).status_code,503)

    def test_failed_journal_put_intent_prevents_http_effect(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state))
            with self.conn() as db:db.execute("CREATE FUNCTION proof_intent_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event='put_intent' THEN RAISE EXCEPTION 'synthetic'; END IF; RETURN NEW; END $$; CREATE TRIGGER proof_intent_fail BEFORE INSERT ON document_execution_journal FOR EACH ROW EXECUTE FUNCTION proof_intent_fail()")
            self.assertEqual(self.confirm(action).status_code,503);self.assertFalse(any(r[0]=='PUT' for r in state['seen']))
            self.assertEqual(actions.get_action(action['id'])['state'],'failed')

    def test_repair_expired_new_claim_does_not_restore_old_owner(self):
        with update_dav() as (base,state),self.configured(base):
            action=self.prepare(self.adopt(base,state));self.fail_publication();self.assertEqual(self.confirm(action).status_code,503)
            self.restore_publication();reader=NextcloudDocumentReadClient.stat_resource
            def expire_repair(client,*args,**kwargs):
                with self.conn() as db:db.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE kind='confirmation' AND state='active'")
                return reader(client,*args,**kwargs)
            with patch.object(NextcloudDocumentReadClient,'stat_resource',expire_repair):
                response=self.server.app.test_client().get('/api/document-workshop/actions/'+action['id'])
            self.assertEqual(response.json['action']['state'],'remote_uncertain')
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(0,)])
            self.assertEqual(self.server.app.test_client().get('/api/document-workshop/actions/'+action['id']).json['action']['state'],'remote_uncertain')
            self.assertEqual(len([r for r in state['seen'] if r[0]=='PUT']),1)
