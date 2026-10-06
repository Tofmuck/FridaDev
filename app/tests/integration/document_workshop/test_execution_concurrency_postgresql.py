"""M5 independent processes, authority races and composed DAV compensation."""
import multiprocessing
import os
import unittest
from dataclasses import replace
from uuid import uuid4

from core import conversation_turn_claims as claims, document_workshop_actions as actions
from tests.integration.document_workshop import test_execution_postgresql as fixture


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'),'isolated M5 PostgreSQL required')
class ExecutionConcurrencyPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.ExecutionPostgresqlTests(methodName='runTest')
        self.fx.setUp();self.addCleanup(self.fx.doCleanups)

    def test_two_processes_confirm_with_different_ids_one_owner_one_put(self):
        ctx=multiprocessing.get_context('fork')
        arrived,release=ctx.Event(),ctx.Event()
        result=ctx.Queue()
        def child():
            client=fixture.SyntheticDAV(self.fx)
            client.arrived,client.release=arrived,release
            try:
                payload,status=self.fx.confirm(self.fx.executor(client))
                result.put((os.getpid(),status,payload,client.mutations))
            except BaseException as error:result.put((os.getpid(),'error',type(error).__name__,[]))
        process=ctx.Process(target=child)
        process.start()
        try:
            self.assertTrue(arrived.wait(5))
            parent_client=fixture.SyntheticDAV(self.fx)
            repeated,status=self.fx.confirm(self.fx.executor(parent_client))
            self.assertEqual(status,200,repeated)
            self.assertEqual(repeated['action']['state'],'executing')
            self.assertEqual(parent_client.mutations,[])
            self.fx.assert_no_transaction()
            release.set()
            pid,status,payload,writes=result.get(timeout=10)
            self.assertNotEqual(pid,os.getpid())
            self.assertEqual(status,200,payload)
            self.assertEqual(payload['action']['state'],'succeeded')
            self.assertEqual(writes,['PUT'])
            process.join(5);self.assertEqual(process.exitcode,0)
        finally:
            release.set()
            if process.is_alive():process.terminate();process.join(5)
            result.close()
        self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(1,)])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(1,)])
        self.assertEqual(claims.read(self.fx.request_turn),self.fx.before_claim)

    def test_chat_or_preparation_claim_excludes_confirmation_without_changing_pending(self):
        for kind in ('chat','preparation'):
            with self.subTest(kind=kind):
                if kind!='chat':self.fx.doCleanups();self.fx.setUp()
                admission=claims.acquire(conversation_id=self.fx.conversation,turn_id=str(uuid4()),request_fingerprint='3'*64,
                    kind=kind,context_id=self.fx.context if kind=='preparation' else None)
                before=claims.read(admission.token.turn_id)
                client=fixture.SyntheticDAV(self.fx)
                payload,status=self.fx.confirm(self.fx.executor(client))
                self.assertEqual(status,409,payload)
                self.assertEqual(payload['reason_code'],'conversation_turn_conflict')
                self.assertEqual(actions.get_action(self.fx.request_turn)['state'],'pending')
                self.assertEqual(claims.read(admission.token.turn_id),before)
                self.assertEqual(claims.read(self.fx.request_turn),self.fx.before_claim)
                self.assertEqual(client.mutations,[])
                self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])

    def test_cancelled_and_superseded_pending_never_create_confirmation_claim(self):
        client=fixture.SyntheticDAV(self.fx)
        actions.cancel(self.fx.request_turn,self.fx.context)
        payload,status=self.fx.confirm(self.fx.executor(client))
        self.assertEqual(status,409,payload)
        self.assertEqual(payload['action']['state'],'cancelled')
        historical=claims.read(self.fx.request_turn)
        self.fx.reprepare(relative_path='Documents/Second.md')
        old_action,old_body=self.fx.request_turn,self.fx.body()
        self.fx.reprepare(relative_path='Documents/Third.md')
        payload,status=self.fx.service.confirm(old_action,old_body,executor=self.fx.executor(client))
        self.assertEqual(status,409,payload)
        self.assertEqual(payload['action']['state'],'superseded')
        self.assertEqual(client.mutations,[])
        self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])
        self.assertEqual(historical['state'],'succeeded')

    def test_owner_and_generation_fence_every_mkcol_put_and_compensation_intention(self):
        self.fx.reprepare(relative_path='Documents/New/Output.md')
        run=self.fx.store.begin(self.fx.request_turn,self.fx.body())
        self.fx.store.intent(run)
        before=self.fx.rows('SELECT count(*) FROM document_execution_journal')
        for token in (replace(run.token,owner_id=str(uuid4())),replace(run.token,generation=run.token.generation+1)):
            for method,path in (('MKCOL','Documents/New'),('PUT',run.target.relative_path),('DELETE',run.target.relative_path)):
                with self.subTest(method=method),self.assertRaises(Exception):
                    self.fx.store.before_mutation(replace(run,token=token),method,path,compensation=method=='DELETE')
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_execution_journal'),before)
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        self.assertEqual(claims.read(self.fx.request_turn),self.fx.before_claim)

    def test_cancel_expired_confirmation_preserves_active_successor_and_rejects_late_owner(self):
        run=self.fx.store.begin(self.fx.request_turn,self.fx.body())
        self.fx.store.intent(run)
        self.fx.store.before_mutation(run,'PUT',run.target.relative_path)
        with self.fx.conn() as conn:
            conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid",(run.token.turn_id,))
        successor=claims.acquire(conversation_id=self.fx.conversation,turn_id=str(uuid4()),
            request_fingerprint='4'*64,kind='chat').token
        before=claims.read(successor.turn_id)
        journal_before=self.fx.rows('SELECT count(*) FROM document_execution_journal')
        cancelled=actions.cancel(self.fx.request_turn,self.fx.context)
        self.assertEqual(cancelled['state'],'remote_uncertain')
        self.assertEqual(claims.read(successor.turn_id),before)
        self.assertEqual(before['state'],'active')
        self.assertEqual(claims.read(self.fx.request_turn),self.fx.before_claim)
        with self.assertRaises(Exception):self.fx.store.observe(run,'remote_outcome',fixture.SimpleNamespace(
            state='known_success',reason_code='document_remote_created',http_status=201,
            creation_etag='"created"',created_collections=()))
        with self.assertRaises(Exception):self.fx.store.before_mutation(run,'DELETE',run.target.relative_path,compensation=True)
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_execution_journal'),journal_before)
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        client=fixture.SyntheticDAV(self.fx)
        self.assertEqual(self.fx.confirm(self.fx.executor(client))[1],503)
        self.assertEqual(client.mutations,[])
        self.assertEqual(claims.read(successor.turn_id),before)

    def test_mkcol_journal_failure_precedes_collection_http_and_reports_no_remote_effect(self):
        from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_mutation_client_m5 import dav_server,collection_xml
        self.fx.reprepare(relative_path='Documents/New/Output.md')
        root=collection_xml()
        # inspect: root/list; create: root/list then parent stat/list/child404.
        replies=[(207,{},root),(207,{},root)]*3+[(404,{},b'')]
        with self.fx.conn() as conn:
            conn.execute("CREATE FUNCTION m5_mkcol_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event='mkcol_intent' THEN RAISE EXCEPTION 'synthetic'; END IF; RETURN NEW; END $$; CREATE TRIGGER m5_mkcol_fault BEFORE INSERT ON document_execution_journal FOR EACH ROW EXECUTE FUNCTION m5_mkcol_fault()")
        with dav_server(replies) as (base,seen):
            payload,status=self.fx.confirm(self.fx.executor(NextcloudDocumentMutationClient(NextcloudFolderClientConfig(base,'test','synthetic'))))
        self.assertEqual(status,503,payload)
        self.assertEqual(payload['action']['state'],'failed')
        self.assertEqual([m for m,_,_,_ in seen if m in ('MKCOL','PUT','DELETE')],[])
        self.assertEqual(self.fx.rows("SELECT count(*) FROM document_execution_journal WHERE event='intent'"),[(1,)])
        self.assertEqual(self.fx.rows("SELECT count(*) FROM document_execution_journal WHERE event='mkcol_intent'"),[(0,)])

    def test_sql_publication_rollback_real_dav_compensation_success_changed_etag_and_unknown_delete(self):
        from core.document_canonical import validate_canonical
        from core.document_markdown import serialize_markdown
        from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_mutation_client_m5 import dav_server,creation_responses,file_xml
        for case in ('absent','changed','unknown'):
            with self.subTest(case=case):
                if case!='absent':self.fx.doCleanups();self.fx.setUp()
                content=serialize_markdown(validate_canonical(fixture.canonical())).encode()
                path=self.fx.action['relative_path']
                replies=creation_responses(path,content)
                tail=[(207,{},file_xml(path,content=content,etag='"changed"' if case=='changed' else '"created-v1"'))]
                if case!='changed':tail+=['drop' if case=='unknown' else (204,{},b'')]
                with self.fx.conn() as conn:
                    conn.execute("CREATE FUNCTION m5_pub_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER m5_pub_fault BEFORE INSERT ON workspace_files FOR EACH ROW EXECUTE FUNCTION m5_pub_fault()")
                with dav_server(replies[:3]+replies+tail) as (base,seen):
                    client=NextcloudDocumentMutationClient(NextcloudFolderClientConfig(base,'test','synthetic'))
                    payload,status=self.fx.confirm(self.fx.executor(client))
                self.assertEqual(status,503,payload)
                self.assertEqual(payload['action']['state'],'failed' if case=='absent' else 'remote_uncertain')
                writes=[(m,h) for m,_,h,_ in seen if m in ('PUT','DELETE','MKCOL')]
                self.assertEqual([m for m,_ in writes],['PUT'] if case=='changed' else ['PUT','DELETE'])
                if case!='changed':self.assertEqual(writes[-1][1]['If-Match'],'"created-v1"')
                self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
                self.assertEqual(self.fx.rows('SELECT count(*) FROM workspace_files'),[(0,)])
