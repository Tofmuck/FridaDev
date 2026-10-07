"""AUD-01 refused by real validation under confirmation/claim, before DAV gate."""
import os
import unittest
from unittest.mock import patch
from core import document_renderer_contract as c
from core import document_rendering as rendering
from core import document_workshop_actions as actions
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.support import document_renderer_fixtures as f
from tests.support import document_renderer_structure_fixtures as s
from tests.support.document_renderer_fake import FakeRenderer


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'), 'isolated M5 PostgreSQL required')
class RendererStructurePostgresqlTests(unittest.TestCase):
    def test_structure_refusal_under_confirmation_claim_before_product_format_gate(self):
        for name, xml in s.INVALID_AUD01.items():
            with self.subTest(name=name):
                fx = fixture.ExecutionPostgresqlTests(methodName='runTest')
                fx.setUp()
                try:
                    worker = FakeRenderer()
                    session = rendering.RenderingSession(client=worker, expected_engine=f.ENGINE, wait=lambda: None)
                    events = []
                    submit = worker.submit
                    def submitted(request):
                        self.assertEqual(actions.get_action(fx.request_turn)['state'], 'executing')
                        self.assertEqual(fx.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation' AND state='active'"), [(1,)])
                        fx.assert_no_transaction()
                        events.append('claim_active')
                        return submit(request)
                    def result(request):
                        worker.events.append('result')
                        events.append('result')
                        return s.pair(c, request, xml)[0]
                    validate = c.validate_result
                    def checked(*args, **kw):
                        try:
                            value = validate(*args, **kw)
                        except c.RendererError as error:
                            self.assertEqual(error.reason_code, 'renderer_source_unsupported')
                            events.append('validation_refused')
                            raise
                        events.append('validation_accepted')
                        return value
                    release = worker.cancel_release
                    def abandoned(request, *, cancel=False):
                        self.assertTrue(cancel)
                        self.assertEqual(request.data['job_id'], next(iter(worker.jobs)))
                        self.assertEqual(request.identity, worker.jobs[request.data['job_id']]['identity'])
                        events.append('abandon')
                        return release(request, cancel=cancel)
                    worker.submit = submitted
                    worker.result = result
                    worker.cancel_release = abandoned
                    class Executor(fx.executor_module.DocumentExecutor):
                        def _render(inner, run):
                            value = rendering.render_confirmed(run, 'docx', session)
                            events.append('binary_returned')
                            return value.docx
                    dav = fixture.SyntheticDAV(fx)
                    with patch.object(c, 'validate_result', checked):
                        payload, status = fx.confirm(Executor(mutation_client=dav, storage_root=fx.env.root))
                    self.assertEqual(events, ['claim_active', 'result', 'validation_refused', 'abandon'])
                    self.assertEqual(worker.events, ['capabilities', 'submit', 'status', 'result', 'cancel'])
                    self.assertEqual(status, 503)
                    self.assertIsNone(session.collected)
                    self.assertEqual(dav.mutations, [])
                    self.assertEqual(fx.rows('SELECT count(*) FROM document_receipts'), [(0,)])
                    self.assertEqual(fx.rows('SELECT count(*) FROM document_execution_journal'), [(0,)])
                finally:
                    fx.doCleanups()
