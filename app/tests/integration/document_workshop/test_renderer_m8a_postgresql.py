"""Real confirmation/M3/SQL composed with the delivered HTTP Unix client."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import threading
import unittest
import os
from dataclasses import replace
from uuid import uuid4
from unittest.mock import patch

from core import document_renderer_contract as c, document_rendering as rendering
from core import document_workshop_actions as actions
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.support import document_renderer_fixtures as f
from tests.support.document_renderer_fake import FakeRenderer
from tests.support.document_renderer_unix import UnixRendererServer


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'), 'isolated M5 PostgreSQL required')
class RendererAdapterPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('core.document_renderer_store'), 'M8-A durable snapshots absent')
        from core.document_renderer_client import DocumentRendererClient
        self.Client = DocumentRendererClient
        self.fx = fixture.ExecutionPostgresqlTests(methodName='runTest')
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.snapshots = __import__('core.document_renderer_store', fromlist=['persist'])

    def setup_renderer(self, **kwargs):
        self.server = UnixRendererServer(**kwargs)
        server = self.server
        self.addCleanup(lambda: self.assertEqual(server.errors, []))
        self.addCleanup(server.close)
        self.session = rendering.RenderingSession(client=self.Client(socket_path=self.server.path),
            expected_engine=f.ENGINE, wait=lambda: None)
        self.dav = fixture.SyntheticDAV(self.fx)
        self.returned = []
        session, returned = self.session, self.returned
        class Executor(self.fx.executor_module.DocumentExecutor):
            def _render(inner, run):
                value = rendering.render_confirmed(run, 'docx', session)
                returned.append(value)
                return value.docx
        self.executor = Executor(mutation_client=self.dav, storage_root=self.fx.env.root)

    def zero_mutations(self):
        self.assertEqual(self.dav.mutations, [])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'), [(0,)])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_execution_journal'), [(0,)])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_revision_renders'), [(0,)])

    def count(self):
        return self.fx.rows('SELECT count(*) FROM document_renderer_snapshots')[0][0]

    def test_snapshot_committed_before_release_bound_to_action_revision_and_confirmation(self):
        observed = []
        def respond(handler, method, response):
            if method == 'DELETE':
                self.fx.assert_no_transaction()
                row = self.fx.rows('SELECT action_id::text,revision_id::text,confirmation_turn_id::text,request_sha256,manifest,docx,pdf FROM document_renderer_snapshots')[0]
                self.assertEqual(row[:3], (self.fx.request_turn, self.fx.action['revision_id'], self.server.request.data['job_id']))
                self.assertEqual(row[3], self.server.request.identity)
                self.assertEqual(row[4], self.session.collected.manifest_bytes)
                self.assertEqual(row[5:], (f.docx(), f.pdf()))
                self.zero_mutations()
                observed.append('durable_before_ack')
        self.setup_renderer(respond=respond)
        payload, status = self.fx.confirm(self.executor)
        self.assertEqual(status, 503)
        self.assertEqual(payload['reason_code'], 'document_format_unavailable')
        self.assertEqual(observed, ['durable_before_ack'])
        self.assertEqual(len(self.returned), 1)
        self.assertEqual(self.returned[0].release['state'], 'released')
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.server.errors, [])
        self.zero_mutations()
        self.assertEqual(fixture.claims.read(self.fx.request_turn), self.fx.before_claim)

    def test_double_confirmation_during_blocked_result_has_one_job_and_one_snapshot(self):
        def respond(handler, method, response):
            if handler.path.endswith('/result'):
                self.server.entered.set()
                if not self.server.resume.wait(5): raise AssertionError('missing deterministic release')
        self.setup_renderer(respond=respond)
        with ThreadPoolExecutor(1) as pool:
            first = pool.submit(self.fx.confirm, self.executor)
            try:
                self.assertTrue(self.server.entered.wait(5))
                self.fx.assert_no_transaction()
                repeated, status = self.fx.confirm(self.executor)
                self.assertEqual(status, 200)
                self.assertEqual(repeated['action']['state'], 'executing')
                self.assertEqual(self.server.worker.events.count('submit'), 1)
                self.assertEqual(self.count(), 0)
            finally:
                self.server.resume.set()
                payload, status = first.result(10)
        self.assertEqual(status, 503)
        self.assertEqual(payload['reason_code'], 'document_format_unavailable')
        self.assertEqual(self.count(), 1)
        previous = list(self.server.requests)
        self.fx.confirm(self.executor)
        self.assertEqual(self.server.requests, previous)
        self.assertEqual(self.server.worker.executions, 1)
        self.zero_mutations()

    def invalidate(self, kind):
        if kind == 'cancel':
            actions.cancel(self.fx.request_turn, self.fx.context)
        else:
            with self.fx.conn() as conn:
                if kind == 'scope': conn.execute('UPDATE conversations SET workspace_folder_id=NULL WHERE id=%s::uuid', (self.fx.conversation,))
                elif kind == 'lease': conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE kind='confirmation'")
                elif kind == 'generation': conn.execute('UPDATE conversations SET turn_generation=turn_generation+1 WHERE id=%s::uuid', (self.fx.conversation,))
                elif kind == 'revision':
                    # Isolated corruption injection only. Normal SQL rejects
                    # this edit through the existing immutable trigger.
                    conn.execute('ALTER TABLE document_revisions DISABLE TRIGGER document_revision_immutable')
                    conn.execute("UPDATE document_revisions SET canonical_sha256=%s WHERE id=%s::uuid", ('0'*64, self.fx.action['revision_id']))
                    conn.execute('ALTER TABLE document_revisions ENABLE TRIGGER document_revision_immutable')
                else: raise AssertionError('unknown invalidation')

    def test_authority_loss_interrupts_blocked_transport_and_discards_late_result(self):
        for kind in ('cancel', 'scope', 'lease', 'generation', 'revision'):
            with self.subTest(kind=kind):
                if kind != 'cancel': self.doCleanups(); self.setUp()
                late = threading.Event()
                def respond(handler, method, response):
                    if handler.path.endswith('/result'):
                        self.server.block(handler)
                        late.set()
                        handler.reply(response)
                        return True
                self.setup_renderer(respond=respond)
                with ThreadPoolExecutor(1) as pool:
                    task = pool.submit(self.fx.confirm, self.executor)
                    self.assertTrue(self.server.entered.wait(5))
                    self.fx.assert_no_transaction()
                    self.invalidate(kind)
                    payload, status = task.result(10)
                    self.assertTrue(self.server.disconnected.wait(5))
                    self.assertTrue(late.wait(5))
                self.assertIn(status, (200, 409, 503))
                if status == 200:
                    # Existing M5 may project executing until this still-active
                    # stale claim expires. It must never mean renderer success.
                    self.assertEqual(payload['action']['state'], 'executing')
                self.assertNotEqual(payload.get('action', {}).get('state'), 'succeeded')
                self.assertEqual(self.returned, [])
                self.assertIsNone(self.session.collected)
                self.assertEqual(self.count(), 0)
                self.assertEqual(self.server.worker.events.count('cancel'), 1)
                self.assertIsNone(self.server.worker.active)
                self.zero_mutations()

    def test_lost_submit_recovers_state_then_persists_without_second_post(self):
        def respond(handler, method, response): return method == 'POST'
        self.setup_renderer(respond=respond)
        payload, status = self.fx.confirm(self.executor)
        self.assertEqual((status, payload['reason_code']), (503, 'document_format_unavailable'))
        self.assertEqual(self.server.worker.events, ['capabilities', 'submit', 'status', 'result', 'release'])
        self.assertEqual(self.count(), 1)
        self.zero_mutations()

    def test_invalid_ready_hash_pages_or_worker_loss_precedes_snapshot_and_mutation(self):
        cases = ('hash', 'pages', 'false_ready', 'lost', 'truncated')
        for case in cases:
            with self.subTest(case=case):
                if case != cases[0]: self.doCleanups(); self.setUp()
                change = {'hash': lambda m: m.update(request_sha256='0'*64),
                    'pages': lambda m: m['page_evidence'].update(writer_pages=21),
                    'false_ready': lambda m: m['artifacts'].pop('pdf')}.get(case)
                def respond(handler, method, response):
                    if case == 'lost' and method == 'POST':
                        self.server.worker.restart()
                        return True
                    if case == 'truncated' and handler.path.endswith('/result'):
                        handler.wfile.write(b'HTTP/1.1 200 OK\r\nContent-Type: ' + response.content_type.encode() +
                            b'\r\nContent-Length: ' + str(len(response.body)).encode() + b'\r\n\r\n' + response.body[:-1])
                        return True
                self.setup_renderer(worker=FakeRenderer(result_change=change), respond=respond)
                payload, status = self.fx.confirm(self.executor)
                self.assertEqual(status, 503)
                self.assertIn(payload['reason_code'], ('document_render_invalid', 'document_page_limit'))
                self.assertEqual(self.count(), 0)
                self.assertEqual(self.returned, [])
                self.assertEqual(self.server.worker.events.count('submit'), 1)
                self.zero_mutations()

    def test_snapshot_insert_rollback_cancels_once_without_release_or_partial_row(self):
        self.setup_renderer()
        with self.fx.conn() as conn:
            conn.execute("""CREATE FUNCTION reject_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic_snapshot_failure'; END $$;
                CREATE TRIGGER reject_snapshot BEFORE INSERT ON document_renderer_snapshots
                FOR EACH ROW EXECUTE FUNCTION reject_snapshot()""")
        payload, status = self.fx.confirm(self.executor)
        self.assertEqual(status, 503)
        self.assertEqual(payload['reason_code'], 'document_execution_unavailable')
        self.assertEqual(self.count(), 0)
        self.assertEqual(self.server.worker.events.count('cancel'), 1)
        self.assertNotIn('release', self.server.worker.events)
        self.assertEqual(self.returned, [])
        self.fx.assert_no_transaction()
        self.zero_mutations()

    def test_release_refused_keeps_snapshot_without_success_or_second_cleanup(self):
        self.setup_renderer(worker=FakeRenderer(release_change=dict(state='failed', reason_code='renderer_cleanup_failed', workspace_removed=False)))
        payload, status = self.fx.confirm(self.executor)
        self.assertEqual((status, payload['reason_code']), (503, 'document_render_invalid'))
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.returned, [])
        self.assertIsNone(self.session._released)
        self.assertEqual(self.server.worker.events.count('release'), 1)
        self.assertNotIn('cancel', self.server.worker.events)
        self.zero_mutations()

    def test_fencing_at_release_ack_preserves_snapshot_but_never_returns_success(self):
        def respond(handler, method, response):
            if method == 'DELETE': self.invalidate('generation')
        self.setup_renderer(respond=respond)
        payload, status = self.fx.confirm(self.executor)
        self.assertIn(status, (200, 409, 503))
        if status == 200: self.assertEqual(payload['action']['state'], 'executing')
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.returned, [])
        self.assertIsNone(self.session._released)
        self.assertIsNone(self.server.worker.active)
        self.assertEqual(self.server.worker.events.count('release'), 1)
        self.assertNotIn('cancel', self.server.worker.events)
        self.zero_mutations()

    def test_snapshot_is_immutable(self):
        self.setup_renderer()
        self.fx.confirm(self.executor)
        import psycopg
        with self.assertRaises(psycopg.errors.RaiseException):
            with self.fx.conn() as conn:
                conn.execute("UPDATE document_renderer_snapshots SET manifest='changed'::bytea")
        self.assertEqual(self.count(), 1)
        self.zero_mutations()

    def test_wrong_owner_or_generation_cannot_persist_a_validated_snapshot(self):
        self.setup_renderer()
        run = self.fx.store.begin(self.fx.request_turn, self.fx.body())
        request = c.make_request(job_id=run.token.turn_id, revision_id=run.action['revision_id'],
            canonical=run.revision['canonical'], canonical_sha256=run.revision['canonical_sha256'], format='docx', engine=f.ENGINE)
        manifest, docx, pdf = f.result(c, request)
        result = c.validate_result(f.response(c, manifest, docx, pdf), request=request, expected_engine=f.ENGINE)
        for token in (replace(run.token, owner_id=str(uuid4())), replace(run.token, generation=run.token.generation+1)):
            with self.assertRaises(fixture.claims.ClaimError):
                self.snapshots.persist(replace(run, token=token), request, result)
        self.assertEqual(self.count(), 0)
        self.assertEqual(self.server.requests, [])
        self.zero_mutations()

    def test_unchanged_markdown_does_not_require_renderer_schema_or_socket(self):
        self.setup_renderer()
        with self.fx.conn() as conn: conn.execute('DROP TABLE document_renderer_snapshots')
        with patch.object(rendering, 'render_confirmed', side_effect=AssertionError('Markdown called Writer')):
            payload, status = self.fx.confirm(self.fx.executor(self.dav))
        self.assertEqual(status, 200)
        self.assertEqual(payload['action']['state'], 'succeeded')
        self.assertEqual(self.dav.mutations, ['PUT'])
        self.assertEqual(self.server.requests, [])
