"""P2-M4-01: action-local cancellation through Flask and real SQL authority."""
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
import hashlib

from core import conversation_turn_claims as claims
from tests.integration.document_workshop import test_preparation_postgresql as fixture
from tests.integration.document_workshop import test_preparation_failures_postgresql as failure_fixture
from tests.integration.document_workshop import test_preparation_http_postgresql as http_fixture

A = fixture.T
B = fixture.O
N = '55555555-5555-4555-8555-555555555555'


@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class ActionCancellationPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.env = fixture.PreparationPostgresqlTests()
        self.addCleanup(self.env.doCleanups)
        self.env.setUp()
        self.actions = self.env.actions

    def rows(self, query, args=()):
        with self.env.conn() as independent:
            return independent.execute(query, args).fetchall()

    def cancel(self, action=A, *, context=None):
        with self.env.server.app.test_client() as client:
            return client.post('/api/document-workshop/actions/' + action + '/cancel',
                json={'context_id': self.env.context['id'] if context is None else context})

    def get(self, action):
        with self.env.server.app.test_client() as client:
            response = client.get('/api/document-workshop/actions/' + action)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()['action']

    def authority(self, action):
        return self.rows('''SELECT state,owner_id,generation,lease_until,outcome,finished_at
            FROM conversation_turn_claims WHERE turn_id=%s::uuid''', (action,))[0]

    def context_state(self):
        return self.rows('SELECT state FROM document_workshop_contexts WHERE id=%s::uuid',
            (self.env.context['id'],))[0][0]

    def immutable_proposal(self, action=A):
        return self.rows('''SELECT a.revision_id,a.artifact_id,a.operation,a.format,a.relative_path,
            a.source_file_ids,a.source_versions,a.limitations,r.canonical,r.canonical_sha256,r.markdown_sha256
            FROM document_actions a JOIN document_revisions r ON r.id=a.revision_id WHERE a.id=%s::uuid''',
            (action,))[0]

    def roles(self):
        return self.rows("SELECT role,content FROM conversation_messages WHERE role<>'system' ORDER BY seq")

    def assert_no_idle_transactions(self):
        # An active provider's authority monitor legitimately takes short SQL
        # locks. A NOWAIT probe at that instant would test its scheduling.
        self.assertEqual(self.rows("""SELECT count(*) FROM pg_stat_activity WHERE datname='m1proof'
            AND state='idle in transaction' AND clock_timestamp()-state_change>interval '100 milliseconds'""")[0][0], 0)

    def prepare_a(self):
        provider = fixture.Provider()
        with self.env.pipeline(provider) as (normal, _):
            response = self.env.document(identity=A, message='Prepare proposal A')
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(normal, [])
        return provider

    @contextmanager
    def sql_fault(self, table, condition):
        helper = failure_fixture.PreparationFailuresPostgresqlTests()
        helper.env, helper.actions = self.env, self.actions
        with helper.fault(table, 'UPDATE', condition):
            yield

    def scenario_old_pending_during_successor(self, *, cancel_old):
        first, successor = fixture.Provider(), fixture.Provider(gate=True)
        transports = iter((first, successor))
        with self.env.pipeline(None, transport_factory=lambda: next(transports)) as (normal, _), ThreadPoolExecutor(1) as pool:
            first_response = self.env.document(identity=A, message='Prepare proposal A')
            self.assertEqual(first_response.status_code, 200, first_response.get_json())
            before_a, proposal_a = self.authority(A), self.immutable_proposal(A)
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            try:
                self.assertTrue(successor.arrived.wait(5), 'B did not reach its documentary provider')
                self.assert_no_idle_transactions()
                before_b = self.authority(B)
                if cancel_old:
                    cancellation = self.cancel(A)
                instant = dict(context=self.context_state(), a=self.get(A),
                    # Raw reads observe B without get_action normalizing its state.
                    b_state=self.rows('SELECT state FROM document_actions WHERE id=%s::uuid', (B,))[0][0],
                    b_claim=self.authority(B), a_claim=self.authority(A),
                    b_transport_closed=successor.closed.is_set())
            finally:
                successor.release.set()
                response = request.result(timeout=10)
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.assertTrue(first.closed.is_set())
        self.assertTrue(successor.closed.is_set())
        instant['result_status'] = response.status_code
        instant['final_b_state'] = self.get(B)['state']
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(before_a[0], 'succeeded')
        self.assertEqual(before_b[0], 'active')
        self.assertEqual(instant['a_claim'], before_a)
        self.assertEqual(instant['context'], 'editing', instant)
        self.assertEqual(instant['b_state'], 'preparing', instant)
        self.assertEqual(instant['b_claim'], before_b, instant)
        self.assertFalse(instant['b_transport_closed'], instant)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.get(B)['state'], 'pending')
        self.assertEqual(self.authority(B)[0], 'succeeded')
        self.assertEqual(self.context_state(), 'editing')
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 2)
        self.assertEqual(self.rows("SELECT id FROM document_actions WHERE state='pending'")[0][0].hex,
            B.replace('-', ''))
        self.assertEqual(self.rows('SELECT count(*) FROM workspace_files')[0][0], 0)
        self.env.assert_no_open_transaction()
        if cancel_old:
            self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
            self.assertEqual(cancellation.get_json()['action']['state'], 'cancelled')
            self.assertEqual(instant['a']['state'], 'cancelled')
            self.assertEqual(self.get(A)['state'], 'cancelled')
            # Repeating an old terminal cancellation after B's commit must not
            # touch B, either proposal, or the durable transcript.
            action_a, action_b, claim_b = self.get(A), self.get(B), self.authority(B)
            messages = self.rows('SELECT * FROM conversation_messages ORDER BY seq')
            revisions = self.rows('SELECT * FROM document_revisions ORDER BY id')
            repeated = self.cancel(A)
            self.assertEqual(repeated.status_code, 200, repeated.get_json())
            self.assertEqual(repeated.get_json()['action'], action_a)
            self.assertEqual(self.get(B), action_b)
            self.assertEqual(self.authority(A), before_a)
            self.assertEqual(self.authority(B), claim_b)
            self.assertEqual(self.rows('SELECT * FROM conversation_messages ORDER BY seq'), messages)
            self.assertEqual(self.rows('SELECT * FROM document_revisions ORDER BY id'), revisions)
            self.assertEqual(self.context_state(), 'editing')
        else:
            self.assertEqual(instant['a']['state'], 'pending')
            self.assertEqual(self.get(A)['state'], 'superseded')

    def test_cancel_old_pending_preserves_preparing_successor_authority_and_result(self):
        self.scenario_old_pending_during_successor(cancel_old=True)

    def test_without_cancel_successor_supersedes_old_pending(self):
        self.scenario_old_pending_during_successor(cancel_old=False)

    def test_cancel_old_pending_preserves_concurrent_normal_chat(self):
        first = self.prepare_a()
        before_a, proposal_a = self.authority(A), self.immutable_proposal(A)
        arrived, release = threading.Event(), threading.Event()
        normal_calls = []
        def normal_provider(*_, **__):
            normal_calls.append(1)
            arrived.set()
            self.assertTrue(release.wait(10))
            return fixture.fixture.SyntheticResponse()
        unexpected_document = fixture.Provider()
        with self.env.pipeline_base(normal_provider), \
             patch.object(fixture.turn, 'DocumentHTTPTransport', lambda: unexpected_document), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.post, identity=B, message='Normal request B')
            try:
                self.assertTrue(arrived.wait(5))
                before_b = self.authority(B)
                cancellation = self.cancel(A)
                instant_context, instant_b = self.context_state(), self.authority(B)
                instant_a = self.authority(A)
            finally:
                release.set()
                response = request.result(timeout=10)
        self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
        self.assertEqual(instant_context, 'editing')
        self.assertEqual(instant_b, before_b)
        self.assertEqual(instant_a, before_a)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.authority(B)[0], 'succeeded')
        self.assertEqual(self.get(A)['state'], 'cancelled')
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(normal_calls, [1])
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(unexpected_document.calls, [])
        self.assertEqual(self.rows('SELECT count(*) FROM document_actions')[0][0], 1)
        self.env.assert_no_open_transaction()

    def test_cancel_preparing_successor_preserves_old_pending_and_fences_late_result(self):
        first = self.prepare_a()
        before_a, proposal_a, action_a = self.authority(A), self.immutable_proposal(A), self.get(A)
        successor = failure_fixture.LateProvider(gate=True)
        with self.env.pipeline(successor) as (normal, _), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            try:
                self.assertTrue(successor.arrived.wait(5))
                cancellation = self.cancel(B)
                self.assertTrue(successor.closed.wait(5))
                instant_context, instant_a = self.context_state(), self.get(A)
            finally:
                successor.release.set()
                response = request.result(timeout=10)
        self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
        self.assertEqual(cancellation.get_json()['action']['state'], 'cancelled')
        self.assertEqual(instant_context, 'editing')
        self.assertEqual(instant_a, action_a)
        self.assertEqual(self.get(A), action_a)
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(self.authority(A), before_a)
        self.assertEqual(self.authority(B)[0], 'cancelled')
        self.assertTrue(successor.late_returned.is_set())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['reason_code'], 'conversation_claim_lost')
        self.assertEqual(self.roles(), [('user', 'Prepare proposal A'), ('assistant', 'Proposition préparée.'),
            ('user', 'Prepare proposal B')])
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 1)
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    def test_cancel_preparing_successor_closes_real_http_socket_without_cancelling_old_pending(self):
        first = self.prepare_a()
        before_a, proposal_a, action_a = self.authority(A), self.immutable_proposal(A), self.get(A)
        helper = http_fixture.HTTPPreparationPostgresqlTests()
        helper.env = self.env
        with helper.upstream(blocked=True) as (arrived, closed, received, admitted, (normal, _)), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            self.assertTrue(arrived.wait(5))
            cancellation = self.cancel(B)
            self.assertTrue(closed.wait(5), 'server did not observe EOF/reset from cancellation of B')
            response = request.result(timeout=5)
        self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(received, admitted)
        self.assertEqual(len(first.calls) + len(received), 2)
        self.assertEqual(normal, [])
        self.assertEqual(self.context_state(), 'editing')
        self.assertEqual(self.get(A), action_a)
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(self.authority(A), before_a)
        self.assertEqual(self.get(B)['state'], 'cancelled')
        self.assertEqual(self.authority(B)[0], 'cancelled')
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 1)
        self.env.assert_no_open_transaction()

    def test_cancel_pending_is_idempotent_and_preserves_succeeded_claim_and_revision(self):
        provider = self.prepare_a()
        before_claim, before_proposal = self.authority(A), self.immutable_proposal(A)
        first, repeated = self.cancel(A), self.cancel(A)
        self.assertEqual(first.status_code, 200, first.get_json())
        self.assertEqual(repeated.status_code, 200, repeated.get_json())
        self.assertEqual(repeated.get_json(), first.get_json())
        self.assertEqual(first.get_json()['action']['state'], 'cancelled')
        self.assertEqual(self.authority(A), before_claim)
        self.assertEqual(self.immutable_proposal(A), before_proposal)
        self.assertEqual(self.context_state(), 'editing')
        self.assertEqual(len(provider.calls), 1)

    def test_all_terminal_cancellations_are_idempotent_and_preserve_successor(self):
        # Every documented terminal action is a no-op at the HTTP boundary.
        # SQL is used only to select the terminal fixture state, before B exists.
        for state in ('clarify', 'refuse', 'failed', 'cancelled', 'invalidated', 'superseded', 'interrupted', 'lost'):
            with self.subTest(state=state):
                if state != 'clarify':
                    self.env.doCleanups()
                    self.setUp()
                first = self.prepare_a()
                with self.env.conn() as conn:
                    conn.execute('UPDATE document_actions SET state=%s WHERE id=%s::uuid', (state, A))
                action_a, before_a, proposal_a = self.get(A), self.authority(A), self.immutable_proposal(A)
                successor = fixture.Provider(gate=True)
                with self.env.pipeline(successor) as (normal, _), ThreadPoolExecutor(1) as pool:
                    request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
                    try:
                        self.assertTrue(successor.arrived.wait(5))
                        before_b = self.authority(B)
                        first_cancel, repeated = self.cancel(A), self.cancel(A)
                        instant_b, instant_context = self.authority(B), self.context_state()
                    finally:
                        successor.release.set()
                        response = request.result(timeout=10)
                self.assertEqual(first_cancel.status_code, 200, first_cancel.get_json())
                self.assertEqual(first_cancel.get_json()['action'], action_a)
                self.assertEqual(repeated.get_json(), first_cancel.get_json())
                self.assertEqual(instant_b, before_b)
                self.assertEqual(instant_context, 'editing')
                self.assertEqual(self.authority(A), before_a)
                self.assertEqual(self.immutable_proposal(A), proposal_a)
                self.assertEqual(self.get(A), action_a)
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual(self.get(B)['state'], 'pending')
                self.assertEqual(len(first.calls) + len(successor.calls), 2)
                self.assertEqual(normal, [])

    def test_absent_action_and_wrong_context_do_not_mutate_preparing_successor(self):
        first = self.prepare_a()
        action_a, claim_a = self.get(A), self.authority(A)
        successor = fixture.Provider(gate=True)
        with self.env.pipeline(successor) as (normal, _), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            try:
                self.assertTrue(successor.arrived.wait(5))
                before_b = self.authority(B)
                for action, context in ((N, self.env.context['id']), (A, N)):
                    with self.subTest(action=action, context=context):
                        response = self.cancel(action, context=context)
                        self.assertEqual(response.status_code, 404, response.get_json())
                        self.assertEqual(response.get_json()['reason_code'], 'document_action_missing')
                        self.assertEqual(self.authority(B), before_b)
                        self.assertEqual(self.authority(A), claim_a)
                        self.assertEqual(self.get(A), action_a)
                        self.assertEqual(self.context_state(), 'editing')
            finally:
                successor.release.set()
                result = request.result(timeout=10)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])

    def cancellation_rollback(self, table, *, preparing):
        first = self.prepare_a()
        action_a, claim_a, proposal_a = self.get(A), self.authority(A), self.immutable_proposal(A)
        successor = fixture.Provider(gate=True)
        target = B if preparing else A
        field = 'turn_id' if table == 'conversation_turn_claims' else 'id'
        condition = "NEW." + field + "='" + target + "'::uuid AND NEW.state='cancelled'"
        with self.env.pipeline(successor) as (normal, _), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            try:
                self.assertTrue(successor.arrived.wait(5))
                claim_b = self.authority(B)
                with self.sql_fault(table, condition):
                    response = self.cancel(target)
                self.assertEqual(response.status_code, 503, response.get_json())
                self.assertEqual(response.get_json()['reason_code'], 'document_action_storage_unavailable')
                self.assertNotIn('synthetic M4 boundary refusal', str(response.get_json()))
                self.assertEqual(self.get(A), action_a)
                self.assertEqual(self.authority(A), claim_a)
                self.assertEqual(self.authority(B), claim_b)
                self.assertEqual(self.rows('SELECT state FROM document_actions WHERE id=%s::uuid', (B,))[0][0], 'preparing')
                self.assertEqual(self.context_state(), 'editing')
                self.assertEqual(self.immutable_proposal(A), proposal_a)
                self.assert_no_idle_transactions()
            finally:
                successor.release.set()
                result = request.result(timeout=10)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(self.get(A)['state'], 'superseded')
        self.assertEqual(self.get(B)['state'], 'pending')
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 2)
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    def test_cancel_preparing_claim_update_failure_rolls_back_action_and_authority(self):
        self.cancellation_rollback('conversation_turn_claims', preparing=True)

    def test_cancel_preparing_action_update_failure_rolls_back_claim_and_authority(self):
        self.cancellation_rollback('document_actions', preparing=True)

    def test_cancel_pending_action_update_failure_preserves_successor_and_context(self):
        self.cancellation_rollback('document_actions', preparing=False)

    def cancel_with_external_lock(self, table, column, identity, *, historical):
        first = self.prepare_a()
        action_a, claim_a, proposal_a = self.get(A), self.authority(A), self.immutable_proposal(A)
        successor = fixture.Provider(gate=True)
        pause_checks, resume_checks = threading.Event(), threading.Event()
        def defer_check(function):
            def checked(*args, **kwargs):
                # Defer competing supervision SQL until the synthetic lock is
                # released. Every deferred check then executes its real store
                # code; cancellation and its SQL locks are never simulated.
                if pause_checks.is_set():
                    self.assertTrue(resume_checks.wait(5))
                return function(*args, **kwargs)
            return checked
        with self.env.pipeline(successor) as (normal, _), \
             patch.object(self.actions, 'check_active', defer_check(self.actions.check_active)), \
             patch.object(self.actions, 'project_progress', defer_check(self.actions.project_progress)), ThreadPoolExecutor(2) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            cancellation = None
            try:
                self.assertTrue(successor.arrived.wait(5))
                claim_b = self.authority(B)
                pause_checks.set()
                with self.env.conn() as holder:
                    holder.execute('SELECT '+column+' FROM '+table+' WHERE '+column+'=%s::uuid FOR UPDATE', (identity,))
                    cancellation = pool.submit(self.cancel, A if historical else B)
                    # The row remains held here. A blocking FOR UPDATE would
                    # reach the store's five-second statement timeout instead.
                    cancelled = cancellation.result(timeout=2)
                    instant_a, instant_b, instant_context = self.get(A), self.authority(B), self.context_state()
                    instant_action_b = self.rows('SELECT state FROM document_actions WHERE id=%s::uuid', (B,))[0][0]
            finally:
                resume_checks.set()
                successor.release.set()
                result = request.result(timeout=10)
                if cancellation is not None:
                    cancellation.result(timeout=10)
        self.assertEqual(cancelled.status_code, 200 if historical else 503, cancelled.get_json())
        if historical:
            self.assertEqual(cancelled.get_json()['action']['state'], 'cancelled')
            self.assertEqual(instant_a['state'], 'cancelled')
        else:
            self.assertEqual(cancelled.get_json()['reason_code'], 'document_action_storage_unavailable')
            self.assertEqual(instant_a, action_a)
        self.assertEqual(instant_b, claim_b)
        self.assertEqual(instant_action_b, 'preparing')
        self.assertEqual(instant_context, 'editing')
        self.assertEqual(self.authority(A), claim_a)
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(self.get(A)['state'], 'cancelled' if historical else 'superseded')
        self.assertEqual(self.get(B)['state'], 'pending')
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    def test_cancel_preparing_claim_lock_conflicts_without_partial_mutation(self):
        self.cancel_with_external_lock('conversation_turn_claims', 'turn_id', B, historical=False)

    def test_cancel_preparing_action_lock_conflicts_without_partial_mutation(self):
        self.cancel_with_external_lock('document_actions', 'id', B, historical=False)

    def test_cancel_pending_does_not_lock_or_change_historical_succeeded_claim(self):
        self.cancel_with_external_lock('conversation_turn_claims', 'turn_id', A, historical=True)

    def test_cancel_expired_old_preparation_preserves_lost_claim_and_new_successor(self):
        old = failure_fixture.LateProvider(gate=True)
        successor = fixture.Provider(gate=True)
        transports = iter((old, successor))
        with self.env.pipeline(None, transport_factory=lambda: next(transports)) as (normal, _), ThreadPoolExecutor(2) as pool:
            old_request = pool.submit(self.env.document, identity=A, message='Prepare proposal A')
            self.assertTrue(old.arrived.wait(5))
            with self.env.conn() as conn:
                conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid", (A,))
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            try:
                self.assertTrue(successor.arrived.wait(5))
                before_a, before_b = self.authority(A), self.authority(B)
                self.assertEqual(before_a[0], 'lost')
                cancellation = self.cancel(A)
                instant_a, instant_b, instant_context = self.authority(A), self.authority(B), self.context_state()
            finally:
                old.release.set(); successor.release.set()
                old_result, result = old_request.result(timeout=10), request.result(timeout=10)
        self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
        self.assertIn(cancellation.get_json()['action']['state'], ('cancelled', 'lost'))
        self.assertEqual(instant_a, before_a)
        self.assertEqual(instant_b, before_b)
        self.assertEqual(instant_context, 'editing')
        self.assertEqual(old_result.status_code, 503)
        self.assertTrue(old.closed.is_set())
        self.assertTrue(old.late_returned.is_set())
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(self.get(B)['state'], 'pending')
        self.assertEqual(self.authority(A), before_a)
        self.assertEqual(len(old.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    def commit_race(self, target):
        first = self.prepare_a()
        proposal_a, claim_a = self.immutable_proposal(A), self.authority(A)
        staged, release, cancel_arrived = threading.Event(), threading.Event(), threading.Event()
        identities = {}
        real_finalize, real_lock = self.actions.finalize, claims._conversation
        def staged_finalize(*args, **kwargs):
            snapshot = kwargs['snapshot']
            def staged_snapshot(conversation, conn):
                snapshot(conversation, conn)
                staged.set()
                self.assertTrue(release.wait(10))
            return real_finalize(*args, **(kwargs | {'snapshot': staged_snapshot}))
        def observed_lock(conn, conversation, **kwargs):
            if threading.get_ident() == identities.get('cancel'):
                cancel_arrived.set()
            return real_lock(conn, conversation, **kwargs)
        def cancelling():
            identities['cancel'] = threading.get_ident()
            return self.cancel(target)
        successor = fixture.Provider()
        with self.env.pipeline(successor) as (normal, _), patch.object(self.actions, 'finalize', staged_finalize), \
             patch.object(claims, '_conversation', observed_lock), ThreadPoolExecutor(2) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            self.assertTrue(staged.wait(5))
            cancellation = pool.submit(cancelling)
            try:
                self.assertTrue(cancel_arrived.wait(5))
                self.assertFalse(cancellation.done())
                self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 1)
                self.assertEqual(self.rows('SELECT state FROM document_actions WHERE id=%s::uuid', (A,))[0][0], 'pending')
                self.assertEqual(self.rows('SELECT state FROM document_actions WHERE id=%s::uuid', (B,))[0][0], 'preparing')
            finally:
                release.set()
                result, cancelled = request.result(timeout=10), cancellation.result(timeout=10)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(cancelled.status_code, 200, cancelled.get_json())
        self.assertEqual(self.context_state(), 'editing')
        self.assertEqual(self.get(A)['state'], 'superseded')
        self.assertEqual(self.get(B)['state'], 'pending' if target == A else 'cancelled')
        self.assertEqual(cancelled.get_json()['action']['state'], 'superseded' if target == A else 'cancelled')
        self.assertEqual(self.authority(A), claim_a)
        self.assertEqual(self.authority(B)[0], 'succeeded')
        self.assertEqual(self.authority(B)[4], 'succeeded')
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 2)
        self.assertEqual([r for r, _ in self.roles()], ['user', 'assistant', 'user', 'assistant'])
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    def test_cancel_old_pending_waits_for_successor_commit_then_is_terminal_noop(self):
        self.commit_race(A)

    def test_cancel_successor_waits_for_commit_and_preserves_completed_claim(self):
        self.commit_race(B)

    def test_cancel_successor_before_final_transaction_prevents_commit_and_preserves_old_pending(self):
        first = self.prepare_a()
        action_a, claim_a, proposal_a = self.get(A), self.authority(A), self.immutable_proposal(A)
        parsed, release = threading.Event(), threading.Event()
        parsed_envelopes = []
        real_finalize = self.actions.finalize
        def before_transaction(*args, **kwargs):
            parsed_envelopes.append((args[2].status, args[2].canonical is not None, bool(args[4])))
            parsed.set()
            self.assertTrue(release.wait(10))
            return real_finalize(*args, **kwargs)
        successor = fixture.Provider()
        with self.env.pipeline(successor) as (normal, _), patch.object(self.actions, 'finalize', before_transaction), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B')
            try:
                self.assertTrue(parsed.wait(5))
                self.assertTrue(successor.closed.is_set())
                self.env.assert_no_open_transaction()
                cancellation = self.cancel(B)
                instant_a, instant_claim_a = self.get(A), self.authority(A)
                instant_claim_b, instant_context = self.authority(B), self.context_state()
            finally:
                release.set()
                result = request.result(timeout=10)
        self.assertEqual(parsed_envelopes, [('prepared', True, True)])
        self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
        self.assertEqual(cancellation.get_json()['action']['state'], 'cancelled')
        self.assertEqual(instant_a, action_a)
        self.assertEqual(instant_claim_a, claim_a)
        self.assertEqual(instant_claim_b[0], 'cancelled')
        self.assertEqual(instant_context, 'editing')
        self.assertEqual(result.status_code, 503)
        self.assertEqual(self.get(A), action_a)
        self.assertEqual(self.authority(A), claim_a)
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(self.get(B)['state'], 'cancelled')
        self.assertEqual(self.authority(B), instant_claim_b)
        self.assertEqual(self.rows('SELECT count(*) FROM document_artifacts')[0][0], 1)
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 1)
        self.assertEqual([r for r, _ in self.roles()], ['user', 'assistant', 'user'])
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    @contextmanager
    def real_source(self):
        content = b'Synthetic documentary source.\n'
        digest = hashlib.sha256(content).hexdigest()
        with self.env.conn() as conn:
            conn.execute('ALTER TABLE workspace_files ADD COLUMN byte_size bigint')
            conn.execute("INSERT INTO workspace_files VALUES (%s,%s,'active','document','text','.md',NULL,%s)", (N, fixture.F, len(content)))
            conn.execute("INSERT INTO workspace_file_nextcloud_links VALUES (%s,%s,'linked','Source.md','workspace-file:synthetic','Documents/Source.md',%s,'1',%s,%s,clock_timestamp())",
                (N, fixture.F, 'a'*64, '"v1"', digest))
        def row(table, column, value):
            from psycopg.rows import dict_row
            with self.env.conn() as conn, conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute('SELECT * FROM '+table+' WHERE '+column+'=%s::uuid', (value,))
                return cursor.fetchone()
        calls = []
        resource = fixture.RemoteResource('Documents/Source.md', False, '1', '"v1"', len(content), 'text/markdown')
        reader = SimpleNamespace(scope_key=lambda _: 'a'*64,
            stat_resource=lambda *a, **kw: calls.append('stat') or resource,
            read_file=lambda *_: calls.append('read') or content)
        folders = SimpleNamespace(get_workspace_folder=lambda _: dict(id=fixture.F, nextcloud_sync_state='linked',
            nextcloud_target_name='Synthetic', nextcloud_folder_ref='folder-a'))
        files = SimpleNamespace(get_workspace_file_storage_row=lambda folder, file: row('workspace_files','id',file),
            get_nextcloud_link=lambda file, **_: row('workspace_file_nextcloud_links','workspace_file_id',file))
        actual_read = fixture.sources.read_workspace_document_source
        with patch.object(fixture.sources, 'read_workspace_document_source',
            lambda *a: actual_read(*a, reader=reader, folders=folders, files=files)):
            yield calls

    def invalidation_after_local_cancel(self, *, source):
        first = self.prepare_a()
        claim_a = self.authority(A)
        successor = failure_fixture.LateProvider(gate=True)
        with self.env.pipeline(successor) as (normal, _), ThreadPoolExecutor(1) as pool:
            request = pool.submit(self.env.document, identity=B, message='Prepare proposal B',
                document_source_file_ids=[N] if source else [])
            try:
                self.assertTrue(successor.arrived.wait(5))
                cancellation = self.cancel(A)
                self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
                self.assertEqual(self.context_state(), 'editing')
                with self.env.conn() as conn:
                    if source:
                        conn.execute('UPDATE workspace_file_nextcloud_links SET nextcloud_etag=%s WHERE workspace_file_id=%s::uuid', ('"v2"', N))
                    else:
                        conn.execute('UPDATE conversations SET workspace_folder_id=%s::uuid WHERE id=%s::uuid', (fixture.O, fixture.C))
                        conn.execute('UPDATE conversations SET workspace_folder_id=%s::uuid WHERE id=%s::uuid', (fixture.F, fixture.C))
                self.assertTrue(successor.closed.wait(5))
            finally:
                successor.release.set()
                result = request.result(timeout=10)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(self.context_state(), 'invalidated')
        self.assertEqual(self.get(A)['state'], 'cancelled')
        self.assertEqual(self.authority(A), claim_a)
        self.assertEqual(self.get(B)['state'], 'invalidated')
        self.assertEqual(self.authority(B)[0], 'invalidated')
        self.assertTrue(successor.late_returned.is_set())
        self.assertEqual(self.rows('SELECT count(*) FROM document_revisions')[0][0], 1)
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()

    def test_action_local_cancel_preserves_scope_round_trip_invalidation_trigger(self):
        self.invalidation_after_local_cancel(source=False)

    def test_action_local_cancel_preserves_selected_source_change_invalidation_trigger(self):
        with self.real_source() as reads:
            self.invalidation_after_local_cancel(source=True)
        self.assertEqual(reads, ['stat', 'read'])

    def test_new_explicit_turn_after_pending_cancel_preserves_repeat_identity_without_replay(self):
        first, successor = fixture.Provider(), fixture.Provider()
        transports = iter((first, successor))
        with self.env.pipeline(None, transport_factory=lambda: next(transports)) as (normal, _):
            initial = self.env.document(identity=A, message='Prepare proposal A')
            self.assertEqual(initial.status_code, 200, initial.get_json())
            before_a, proposal_a = self.authority(A), self.immutable_proposal(A)
            cancelled = self.cancel(A)
            self.assertEqual(cancelled.status_code, 200, cancelled.get_json())
            messages = self.roles()
            repeated = self.env.document(identity=A, message='Prepare proposal A')
            self.assertEqual(repeated.status_code, 409, repeated.get_json())
            self.assertEqual(repeated.get_json()['reason_code'], 'conversation_turn_repeated')
            self.assertEqual(repeated.get_json()['turn']['state'], 'succeeded')
            self.assertEqual(self.roles(), messages)
            self.assertEqual(len(first.calls), 1)
            self.assertEqual(successor.calls, [])
            response = self.env.document(identity=B, message='Prepare proposal B explicitly')
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.context_state(), 'editing')
        self.assertEqual(self.get(A)['state'], 'cancelled')
        self.assertEqual(self.authority(A), before_a)
        self.assertEqual(self.immutable_proposal(A), proposal_a)
        self.assertEqual(self.get(B)['state'], 'pending')
        self.assertEqual(len(first.calls) + len(successor.calls), 2)
        self.assertEqual(normal, [])
