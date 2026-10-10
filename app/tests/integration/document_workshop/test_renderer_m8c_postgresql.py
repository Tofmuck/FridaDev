"""M8-C real confirmation/claim fences; simulated renderer only, no binary DAV."""
import importlib
import importlib.util
import os
import unittest
from dataclasses import replace
from uuid import uuid4
from unittest.mock import patch
from core import document_workshop_actions as actions
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.support import document_renderer_fixtures as f

@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'),'isolated M5 PostgreSQL required')
class RendererPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('core.document_rendering'),'M8-C guard raccord absent')
        self.fx=fixture.ExecutionPostgresqlTests(methodName='runTest');self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.c=importlib.import_module('core.document_renderer_contract');self.m=importlib.import_module('core.document_rendering')
        from tests.support.document_renderer_fake import FakeRenderer
        self.worker=FakeRenderer();self.session=self.m.RenderingSession(client=self.worker,expected_engine=f.ENGINE,wait=lambda:None)

    def zero(self):
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_execution_journal'),[(0,)])

    def confirmed_run(self):return self.fx.store.begin(self.fx.request_turn,self.fx.body())

    def test_before_confirmation_zero_submit_and_no_mutation(self):
        with self.assertRaises(Exception):self.m.render_confirmed(None,'docx',self.session)
        self.assertEqual(self.worker.events,[]);self.zero()

    def test_invalid_confirmation_zero_submit_and_no_claim(self):
        class Executor:
            def execute(inner,run):self.fail('invalid confirmation reached execution')
        payload,status=self.fx.confirm(Executor(),self.fx.body(revision_id=str(uuid4())))
        self.assertEqual(status,409);self.assertEqual(self.worker.events,[])
        self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)]);self.zero()

    def test_owner_and_generation_invalid_zero_submit(self):
        run=self.confirmed_run()
        for token in (replace(run.token,owner_id=str(uuid4())),replace(run.token,generation=run.token.generation+1)):
            with self.assertRaises(Exception):self.m.render_confirmed(replace(run,token=token),'docx',self.session)
            self.assertEqual(self.worker.events,[])
        self.zero()

    def test_claim_render_validate_freeze_release_exact_order_and_binary_refusal(self):
        events=[];worker=self.worker
        original=worker.submit
        def submit(request):
            self.assertEqual(actions.get_action(self.fx.request_turn)['state'],'executing')
            self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='active'"),[(1,)])
            self.fx.assert_no_transaction();events.append('claim_active');return original(request)
        worker.submit=submit
        validate=self.c.validate_result
        def checked(*args,**kwargs):
            result=validate(*args,**kwargs);events.append('validated');return result
        release=worker.cancel_release
        def released(request,**kw):
            self.assertIsNotNone(self.session.collected);self.assertIsInstance(self.session.collected.docx,bytes)
            events.append('bytes_frozen');ack=release(request,**kw);events.append('release_ack');return ack
        worker.cancel_release=released
        m=self.m;session=self.session
        class Executor(self.fx.executor_module.DocumentExecutor):
            def _render(inner,run):return m.render_confirmed(run,'docx',session).docx
        client=fixture.SyntheticDAV(self.fx)
        with patch.object(self.c,'validate_result',checked):payload,status=self.fx.confirm(Executor(mutation_client=client,storage_root=self.fx.env.root))
        self.assertEqual(events,['claim_active','validated','bytes_frozen','release_ack'])
        self.assertEqual(status,503);self.assertEqual(client.mutations,[]);self.zero()

    def test_cancellation_scope_lease_and_revision_loss_during_render(self):
        for kind in ('cancel','scope','lease','revision'):
            if kind!='cancel':self.doCleanups();self.setUp()
            run=self.confirmed_run()
            def invalidate(worker):
                self.fx.assert_no_transaction()
                if kind=='cancel':actions.cancel(self.fx.request_turn,self.fx.context)
                else:
                    with self.fx.conn() as conn:
                        if kind=='scope':conn.execute('UPDATE conversations SET workspace_folder_id=NULL WHERE id=%s::uuid',(self.fx.conversation,))
                        if kind=='lease':conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid",(run.token.turn_id,))
                        if kind=='revision':conn.execute("UPDATE document_revisions SET canonical_sha256=%s WHERE id=%s::uuid",('0'*64,run.action['revision_id']))
            self.worker.on_status=invalidate
            with self.assertRaises(Exception):self.m.render_confirmed(run,'docx',self.session)
            self.assertNotIn('result',self.worker.events);self.assertEqual(self.worker.events[-1],'cancel');self.zero()

    def test_public_binary_actions_refused_before_claim_despite_valid_worker_capabilities(self):
        for fmt in ('docx','pdf'):
            if fmt!='docx':self.doCleanups();self.setUp()
            import psycopg
            with self.assertRaises(psycopg.errors.RaiseException):
                with self.fx.conn() as conn:conn.execute('UPDATE document_actions SET format=%s WHERE id=%s::uuid',(fmt,self.fx.request_turn))
            client=fixture.SyntheticDAV(self.fx);payload,status=self.fx.confirm(self.fx.executor(client),self.fx.body()|{'format':fmt})
            self.assertEqual(status,400);self.assertEqual(self.worker.events,[]);self.assertEqual(client.mutations,[])
            self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)]);self.zero()

    def test_markdown_direct_never_calls_renderer_and_mutates_once(self):
        client=fixture.SyntheticDAV(self.fx)
        with patch.object(self.m,'render_confirmed',side_effect=AssertionError('Markdown used renderer')):
            payload,status=self.fx.confirm(self.fx.executor(client))
        self.assertEqual(status,200);self.assertEqual(client.mutations,['PUT']);self.assertEqual(self.worker.events,[])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(1,)])

    def test_causal_detector_catches_renderer_before_real_confirmation_guard(self):
        # Build only snapshots of the pending action, with a counterfeit token;
        # the real M3/M5 guard must refuse before touching the worker.
        from core import conversation_turn_claims as claims
        with self.fx.conn() as conn:
            row=actions._read(conn,self.fx.request_turn)
            folder=self.fx.store._resources(conn,row);revision=self.fx.store._revision(conn,row)
        token=claims.TurnClaim(str(uuid4()),self.fx.conversation,str(uuid4()),1,self.fx.context)
        run=self.fx.store.ConfirmedExecution(token,self.fx.store._json(row),self.fx.store._json(revision),self.fx.store._json(folder))
        with self.assertRaises(Exception):self.m.render_confirmed(run,'docx',self.session)
        self.assertEqual(self.worker.events,[])
        with patch.object(self.fx.store,'check',lambda run:None):
            # M8-A's guarded SQL progress/snapshot may stop this counterfeit
            # owner later. The causal detector concerns the *earlier* submit;
            # keep those new SQL fences active in the mutant as well.
            try:self.m.render_confirmed(run,'docx',self.session)
            except (claims.ClaimError,self.c.DocumentWorkshopError):pass
            with self.assertRaises(AssertionError):
                self.assertEqual(self.worker.events,[],'calibration detects submission before confirmation')
        self.assertEqual(self.worker.events.count('submit'),1)
        self.assertEqual(self.fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])
        self.zero()
