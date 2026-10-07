"""Client/session lifecycle is simulated; no transport or Writer executed."""
import importlib
import importlib.util
import unittest
from tests.support import document_renderer_fixtures as f

class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('core.document_rendering'),'M8-C orchestration absent')
        self.c=importlib.import_module('core.document_renderer_contract')
        self.m=importlib.import_module('core.document_rendering')
        from tests.support.document_renderer_fake import FakeRenderer
        self.Fake=FakeRenderer
        self.request=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=f.canonical(),
            canonical_sha256=self.c.digest(self.c.json_bytes(f.canonical())),format='docx',engine=f.ENGINE)
        self.now=0

    def session(self,worker,wait=None):
        return self.m.RenderingSession(client=worker,expected_engine=f.ENGINE,monotonic=lambda:self.now,
            wait=wait or (lambda:None))

    def test_collect_validate_freeze_then_release_and_repeat_without_reexecution(self):
        worker=self.Fake();session=self.session(worker)
        a=session.collect(self.request,check=lambda:None)
        self.assertEqual(a.docx,f.docx());self.assertEqual(a.release['state'],'released')
        self.assertEqual(worker.events,['capabilities','submit','status','result','release'])
        self.assertEqual(worker.executions,1)
        b=session.collect(self.request,check=lambda:None);self.assertIs(a,b)
        self.assertEqual(worker.executions,1);self.assertEqual(worker.events,['capabilities','submit','status','result','release'])

    def test_same_job_identity_reads_existing_and_incompatible_conflicts(self):
        worker=self.Fake();worker.submit(self.request);worker.submit(self.request)
        other=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=f.canonical(),canonical_sha256=self.request.data['canonical_sha256'],format='pdf',engine=f.ENGINE)
        conflict=worker.submit(other);self.assertEqual(conflict.http_status,409);self.assertEqual(worker.executions,1)

    def test_saturation_refuses_without_queue(self):
        worker=self.Fake();worker.submit(self.request)
        other=self.c.make_request(job_id='10000000-0000-4000-8000-000000000003',revision_id=f.REVISION,canonical=f.canonical(),canonical_sha256=self.request.data['canonical_sha256'],format='docx',engine=f.ENGINE)
        with self.assertRaises(self.c.RendererError) as caught:self.session(worker).collect(other,check=lambda:None)
        self.assertEqual(caught.exception.reason_code,'renderer_busy');self.assertEqual(worker.executions,1)

    def test_unknown_worker_state_and_reason_fail_closed(self):
        for change in (dict(status='unknown'),dict(status='failed',reason_code='private synthetic error')):
            worker=self.Fake(status_change=change)
            with self.assertRaises(self.c.RendererError):self.session(worker).collect(self.request,check=lambda:None)
            self.assertNotIn('result',worker.events)

    def test_failed_refused_cancelled_terminal_states(self):
        for status,reason in [('refused','renderer_input_invalid'),('failed','renderer_resource_limit'),('cancelled','renderer_cancelled')]:
            worker=self.Fake(status_change=dict(status=status,reason_code=reason))
            with self.assertRaises(self.c.RendererError) as caught:self.session(worker).collect(self.request,check=lambda:None)
            self.assertEqual(caught.exception.reason_code,reason);self.assertEqual(worker.events[-1],'cancel')

    def test_lost_worker_never_retries(self):
        worker=self.Fake(on_status=lambda w:w.restart())
        with self.assertRaises(self.c.RendererError) as caught:self.session(worker).collect(self.request,check=lambda:None)
        self.assertEqual(caught.exception.reason_code,'renderer_job_lost');self.assertEqual(worker.executions,1)
        self.assertEqual(worker.events.count('submit'),1)

    def test_cleanup_unacknowledged_or_wrong_job_prevents_success(self):
        for change in (dict(state='failed',reason_code='renderer_cleanup_failed',workspace_removed=False),dict(job_id='10000000-0000-4000-8000-000000000099')):
            worker=self.Fake(release_change=change);session=self.session(worker)
            with self.assertRaises(self.c.RendererError):session.collect(self.request,check=lambda:None)
            self.assertIsNotNone(session.collected);self.assertEqual(worker.events.count('result'),1)

    def test_invalid_result_cancelled_before_release_and_not_retained(self):
        worker=self.Fake(result_change=lambda m:m['artifacts']['docx'].update(sha256='0'*64));session=self.session(worker)
        with self.assertRaises(self.c.RendererError):session.collect(self.request,check=lambda:None)
        self.assertIsNone(session.collected);self.assertEqual(worker.events[-1],'cancel')

    def test_no_wall_deadline_with_monotone_useful_progress(self):
        worker=self.Fake(progress=[(1,0),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1),(8,1)])
        def wait():self.now+=100
        a=self.session(worker,wait).collect(self.request,check=lambda:None)
        self.assertEqual(a.release['state'],'released');self.assertGreater(self.now,120)

    def test_exact_inactivity_and_keepalives_do_not_renew(self):
        worker=self.Fake(progress=[(0,0)]*3)
        def wait():self.now+=60
        with self.assertRaises(self.c.RendererError) as caught:self.session(worker,wait).collect(self.request,check=lambda:None)
        self.assertEqual(self.now,120);self.assertEqual(caught.exception.reason_code,'renderer_inactivity')
        self.assertNotIn('result',worker.events)

    def test_regressing_skipped_or_inconsistent_progress_refused(self):
        for progress in ([(2,1),(1,0)],[(100,1)],[(1,True)]):
            worker=self.Fake(progress=progress)
            with self.assertRaises(self.c.RendererError):self.session(worker).collect(self.request,check=lambda:None)
            self.assertNotIn('result',worker.events)

    def test_authority_checked_before_submit_and_after_each_wait(self):
        worker=self.Fake();checks=[]
        def check():
            checks.append(len(worker.events))
            if 'status' in worker.events:raise RuntimeError('synthetic lost authority')
        with self.assertRaises(RuntimeError):self.session(worker).collect(self.request,check=check)
        self.assertEqual(worker.events[-1],'cancel');self.assertNotIn('result',worker.events)
        worker=self.Fake()
        def denied():raise RuntimeError('synthetic no authority')
        with self.assertRaises(RuntimeError):self.session(worker).collect(self.request,check=denied)
        self.assertEqual(worker.events,[])

    def test_result_late_at_inactivity_is_not_collected_or_released_as_success(self):
        worker=self.Fake();original=worker.result
        def late(request):self.now+=120;return original(request)
        worker.result=late;session=self.session(worker)
        with self.assertRaises(self.c.RendererError) as caught:session.collect(self.request,check=lambda:None)
        self.assertEqual(caught.exception.reason_code,'renderer_inactivity');self.assertIsNone(session.collected)
        self.assertEqual(worker.events[-1],'cancel')

    def test_client_exception_is_content_free_and_submit_http_matches_state(self):
        worker=self.Fake()
        def unsafe(request):raise RuntimeError('private synthetic client exception')
        worker.submit=unsafe
        with self.assertRaises(self.c.RendererError) as caught:self.session(worker).collect(self.request,check=lambda:None)
        self.assertEqual(str(caught.exception),'renderer_incomplete')
        worker=self.Fake();original=worker.submit
        def inconsistent(request):
            wire=original(request);return self.c.WireMessage(wire.content_type,wire.body,503)
        worker.submit=inconsistent
        with self.assertRaises(self.c.RendererError):self.session(worker).collect(self.request,check=lambda:None)
        self.assertNotIn('result',worker.events)

    def test_fake_terminal_result_and_delete_idempotence_are_not_ready(self):
        worker=self.Fake(status_change=dict(status='failed',reason_code='renderer_resource_limit'))
        worker.submit(self.request);worker.status(self.request)
        with self.assertRaises(self.c.RendererError) as caught:self.c.validate_result(worker.result(self.request),request=self.request,expected_engine=f.ENGINE)
        self.assertEqual(caught.exception.reason_code,'renderer_resource_limit')
        a=worker.cancel_release(self.request,cancel=True);b=worker.cancel_release(self.request,cancel=True)
        self.assertEqual(a,b);self.assertEqual(worker.executions,1)
        self.assertEqual(worker.submit(self.request).http_status,410)
        self.assertEqual(worker.status(self.request).http_status,410)

    def test_phase_regression_at_same_unit_count_is_refused(self):
        worker=self.Fake();original=worker.status;count=0
        def regress(request):
            nonlocal count
            count+=1
            if count>=3:return original(request)
            phase='canonical_applied' if count==1 else 'source_inspected'
            return worker.json(self.c.status_value(request,phase=phase,blocks_completed=0))
        worker.status=regress
        with self.assertRaises(self.c.RendererError):self.session(worker).collect(self.request,check=lambda:None)
        self.assertNotIn('result',worker.events)

    def test_conflicting_collect_does_not_cancel_or_release_legitimate_job(self):
        worker=self.Fake();worker.submit(self.request)
        other=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=f.canonical(),canonical_sha256=self.request.data['canonical_sha256'],format='pdf',engine=f.ENGINE)
        with self.assertRaises(self.c.RendererError) as caught:self.session(worker).collect(other,check=lambda:None)
        self.assertEqual(caught.exception.reason_code,'renderer_job_conflict')
        self.assertNotIn('cancel',worker.events);self.assertEqual(worker.active,f.JOB)
        self.assertEqual(worker.executions,1)
        self.assertEqual(worker.status(self.request).http_status,200)
        self.c.validate_result(worker.result(self.request),request=self.request,expected_engine=f.ENGINE)

    def test_wrong_request_cannot_get_result_or_release_existing_job(self):
        worker=self.Fake();worker.submit(self.request)
        other=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=f.canonical(),canonical_sha256=self.request.data['canonical_sha256'],format='pdf',engine=f.ENGINE)
        for call in (worker.status,worker.result,worker.cancel_release):
            reply=call(other);self.assertEqual(reply.http_status,409)
            self.assertEqual(worker.active,f.JOB)
        self.assertEqual(worker.executions,1)

    def test_http_cleanup_error_never_becomes_successful_release_or_cancel(self):
        worker=self.Fake();original=worker.cancel_release
        def wrong(request,**kw):
            w=original(request,**kw);return self.c.WireMessage(w.content_type,w.body,503)
        worker.cancel_release=wrong
        with self.assertRaises(self.c.RendererError):self.session(worker).collect(self.request,check=lambda:None)
        self.assertEqual(worker.events.count('release'),1)
        # Standalone acknowledgment validator also rejects HTTP/body mismatches.
        for cancel in (False,True):
            w=worker.json(self.c.release_value(self.request,cancel=cancel),503)
            with self.assertRaises(self.c.RendererError):self.c.validate_release_message(w,request=self.request,cancel=cancel)

    def test_submit_accepted_with_response_lost_is_abandoned_once(self):
        worker=self.Fake();original=worker.submit
        def lost(request):
            original(request);raise RuntimeError('synthetic response lost')
        worker.submit=lost
        with self.assertRaises(self.c.RendererError):self.session(worker).collect(self.request,check=lambda:None)
        self.assertEqual(worker.executions,1);self.assertEqual(worker.events.count('cancel'),1)
        self.assertIsNone(worker.active);self.assertNotIn('result',worker.events)

    def test_useful_multiblock_progress_has_no_total_wall_deadline(self):
        value=f.canonical();value['blocks']+=f.canonical('Second block')['blocks']
        request=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=value,canonical_sha256=self.c.digest(self.c.json_bytes(value)),format='docx',engine=f.ENGINE)
        worker=self.Fake(progress=[(1,0),(2,1),(3,2),(4,2),(5,2),(6,2),(7,2),(8,2),(9,2)])
        def wait():self.now+=100
        result=self.session(worker,wait).collect(request,check=lambda:None)
        self.assertEqual(result.release['state'],'released');self.assertEqual(worker.executions,1)
        self.assertEqual(self.now,900)
