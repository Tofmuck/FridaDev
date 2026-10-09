"""AUD-02 under real confirmation/claim: late ack must fail before format gate."""
import os
import unittest
from unittest.mock import patch
from core import document_renderer_contract as c
from core import document_rendering as rendering
from core import document_workshop_actions as actions
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.support import document_renderer_fixtures as f
from tests.support.document_renderer_fake import FakeRenderer


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'), 'isolated M5 PostgreSQL required')
class RendererReleasePostgresqlTests(unittest.TestCase):
    def exercise(self, before_release, during_release, late):
        fx = fixture.ExecutionPostgresqlTests(methodName='runTest')
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        now = [0]
        worker = FakeRenderer()
        session = rendering.RenderingSession(client=worker, expected_engine=f.ENGINE,
            monotonic=lambda: now[0], wait=lambda: None)
        events = []
        submit, result, release = worker.submit, worker.result, worker.cancel_release
        validate, validate_ack = c.validate_result, c.validate_release_message
        def submitted(request):
            self.assertEqual(actions.get_action(fx.request_turn)['state'], 'executing')
            self.assertEqual(fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='active'"), [(1,)])
            fx.assert_no_transaction()
            events.append('claim_active')
            return submit(request)
        def fetched(request):
            now[0] += before_release
            events.append('result')
            return result(request)
        def checked(*args, **kwargs):
            value = validate(*args, **kwargs)
            events.append('validated')
            return value
        def released(request, *, cancel=False):
            self.assertFalse(cancel)
            self.assertIsNotNone(session.collected)
            events.append('snapshot_before_release')
            now[0] += during_release
            ack = release(request, cancel=cancel)
            events.append('release_ack_received')
            return ack
        def ack_checked(*args, **kwargs):
            ack = validate_ack(*args, **kwargs)
            events.append('release_ack_validated')
            return ack
        worker.submit, worker.result, worker.cancel_release = submitted, fetched, released
        class Executor(fx.executor_module.DocumentExecutor):
            def _render(inner, run):
                try:
                    value = rendering.render_confirmed(run, 'docx', session)
                except c.DocumentWorkshopError as error:
                    self.assertEqual(error.reason_code, 'document_render_invalid')
                    self.assertIsNone(error.__cause__)
                    events.append('render_refused')
                    raise
                events.append('binary_returned')
                return value.docx
        dav = fixture.SyntheticDAV(fx)
        executor = Executor(mutation_client=dav, storage_root=fx.env.root)
        with patch.object(c, 'validate_result', checked), patch.object(c, 'validate_release_message', ack_checked):
            payload, status = fx.confirm(executor)
        self.assertEqual(events, ['claim_active', 'result', 'validated', 'snapshot_before_release',
            'release_ack_received', 'release_ack_validated', 'render_refused' if late else 'binary_returned'])
        self.assertEqual(worker.events, ['capabilities', 'submit', 'status', 'result', 'release'])
        self.assertEqual(status, 503)
        self.assertEqual(payload['action']['state'], 'failed')
        self.assertEqual(payload['reason_code'], 'document_render_invalid' if late else 'document_format_unavailable')
        self.assertIsNotNone(session.collected)
        self.assertEqual(session._released is None, late)
        self.assertIsNone(worker.active)
        self.assertEqual(dav.mutations, [])
        self.assertEqual(fx.rows('SELECT count(*) FROM document_receipts'), [(0,)])
        self.assertEqual(fx.rows('SELECT count(*) FROM document_execution_journal'), [(0,)])
        self.assertEqual(fx.rows('SELECT count(*) FROM document_revision_renders'), [(0,)])
        self.assertEqual(fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='active'"), [(0,)])
        self.assertEqual(fixture.claims.read(fx.request_turn), fx.before_claim)
        previous = list(worker.events)
        repeated, repeated_status = fx.confirm(executor)
        self.assertEqual(repeated_status, 503)
        self.assertEqual(repeated['reason_code'], payload['reason_code'])
        self.assertEqual(worker.events, previous)
        self.assertEqual(dav.mutations, [])

    def test_exact_and_later_ack_refused_before_format_gate_under_real_claim(self):
        for before, during in ((0, 120), (0, 121), (70, 50)):
            with self.subTest(before_release=before, during_release=during):
                self.exercise(before, during, True)
                self.doCleanups()

    def test_ack_before_limit_reaches_existing_format_gate_under_real_claim(self):
        self.exercise(70, 49.999, False)
