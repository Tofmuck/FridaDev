"""Two synchronized M7 proofs over the real SQL, claim, Flask and DAV paths.

Only ordering and, after supervisor exit, one disposable claim's expiry are
controlled. Connections and supervisors retain their real implementations.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from functools import wraps
import hashlib
import threading
import time
from unittest.mock import patch
from uuid import uuid4

from core import conv_store, conversation_turn_claims as claims
from core import document_workshop_execution_store as execution
from core.chat_turn_reservation import ChatReservation
from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
from tests.support.document_workshop_update_dav import update_dav


class ConcurrentUpdates:
    def __init__(self, case, state, *, overlap):
        self.case, self.state, self.overlap = case, state, overlap
        self.local = threading.local()
        self.trace, self.connections, self.reservations, self.futures = [], [], [], []
        self.statuses = {}
        self.loser_ready, self.winner_done = threading.Event(), threading.Event()
        self.stack = ExitStack()
        self.pool = ThreadPoolExecutor(2, thread_name_prefix='m7-confirm-proof')
        self.started = time.monotonic_ns()

    def emit(self, event, **fields):
        self.trace.append(dict(event=event, actor=getattr(self.local, 'actor', None),
            stage=getattr(self.local, 'stage', None), ns=time.monotonic_ns()-self.started, **fields))

    def wait(self, event, name):
        self.emit('wait', barrier=name)
        self.case.assertTrue(event.wait(10), 'M7 barrier timeout: '+name+'; '+repr(self.trace))
        self.emit('pass', barrier=name)

    def staged(self, name, real):
        @wraps(real)
        def call(*args, **kwargs):
            previous = getattr(self.local, 'stage', None)
            self.local.stage = name
            try:
                return real(*args, **kwargs)
            finally:
                self.local.stage = previous
        return call

    def connected(self, real):
        @contextmanager
        def connect():
            try:
                with real() as conn:
                    self.connections.append(conn)
                    yield conn
            except BaseException as error:
                self.emit('rollback', sqlstate=getattr(error, 'sqlstate', None),
                          exception=type(error).__name__)
                raise
        return connect

    def __enter__(self):
        real_resources, real_observe = execution._resources, execution.observe
        real_update, real_init = NextcloudDocumentMutationClient.update_document, ChatReservation.__init__

        def resources(conn, row):
            value = real_resources(conn, row)
            if getattr(self.local, 'stage', None) == 'observe' and self.local.dav_status == 412:
                # This is inside the real losing observation transaction,
                # after its real NOWAIT directory lock was acquired.
                self.emit('loser_locked', pid=conn.info.backend_pid)
                if self.overlap:
                    self.loser_ready.set()
                    self.wait(self.winner_done, 'winner_return_before_loser_commit')
            return value

        def observe(run, event, result):
            if result.http_status == 204:
                self.wait(self.loser_ready, 'loser_locked' if self.overlap else 'loser_returned')
            return real_observe(run, event, result)

        def update(client, *args, **kwargs):
            result = real_update(client, *args, **kwargs)
            self.local.dav_status = result.http_status
            self.statuses[self.local.actor] = result.http_status
            self.emit('validated_dav', status=result.http_status, state=result.state)
            return result

        def reserve(reservation, *args, **kwargs):
            real_init(reservation, *args, **kwargs)
            self.reservations.append(reservation)

        for module in (execution, claims):
            self.stack.enter_context(patch.object(module, '_db_conn', self.connected(module._db_conn)))
        self.stack.enter_context(patch.object(execution, '_resources', resources))
        self.stack.enter_context(patch.object(execution, 'observe', self.staged('observe', observe)))
        self.stack.enter_context(patch.object(execution, 'finish', self.staged('finish', execution.finish)))
        self.stack.enter_context(patch.object(claims, 'finish', self.staged('claim_finish', claims.finish)))
        self.stack.enter_context(patch.object(NextcloudDocumentMutationClient, 'update_document', update))
        self.stack.enter_context(patch.object(ChatReservation, '__init__', reserve))
        return self

    def confirm(self, action):
        self.local.actor = action['id']
        response = self.case.confirm(action)
        self.emit('confirm_return', status=response.status_code)
        if self.statuses.get(action['id']) == 204:
            self.winner_done.set()
        elif not self.overlap:
            # The entire losing request has returned: observe, finish and
            # claim closure have all left their actual transactions.
            self.loser_ready.set()
        return response

    def join_supervisors(self):
        observed = []
        for reservation in self.reservations:
            reservation._thread.join(2)
            observed.append(dict(stop=reservation._stop.is_set(), alive=reservation._thread.is_alive()))
        self.emit('supervisors_joined', observed=observed)
        self.case.assertTrue(all(row['stop'] and not row['alive'] for row in observed), self.trace)

    def run(self, first, second):
        self.state['block_put'] = True
        self.state['release'].clear()
        self.futures.append(self.pool.submit(self.confirm, first))
        self.wait(self.state['arrived'], 'first_put')
        self.futures.append(self.pool.submit(self.confirm, second))
        with self.state['changed']:
            self.case.assertTrue(self.state['changed'].wait_for(
                lambda: sum(r[0] == 'PUT' for r in self.state['seen']) == 2, 5), self.trace)
        self.emit('both_puts_inflight')
        self.case.env.assert_no_transaction()
        self.state['release'].set()
        results = [future.result(timeout=10) for future in self.futures]
        self.join_supervisors()
        self.case.assertEqual(sorted(self.statuses.values()), [204, 412], self.trace)
        self.case.assertEqual(len(self.reservations), 2)
        return {action['id']: result for action, result in zip((first, second), results)}

    def __exit__(self, kind, error, traceback):
        # Release every gate before draining; keep patches/fixture connections
        # valid until requests and their actual supervisors have ended.
        self.state['release'].set()
        self.loser_ready.set()
        self.winner_done.set()
        cleanup_errors = []
        try:
            for future in self.futures:
                try:
                    future.result(timeout=10)
                except BaseException as failure:
                    cleanup_errors.append(failure)
            self.pool.shutdown(wait=True)
            try:
                self.join_supervisors()
            except BaseException as failure:
                cleanup_errors.append(failure)
            try:
                self.case.assertTrue(all(conn.closed for conn in self.connections), self.trace)
            except BaseException as failure:
                cleanup_errors.append(failure)
        finally:
            self.stack.close()
        self.emit('cleanup', errors=[type(e).__name__ for e in cleanup_errors],
                  connections_closed=all(conn.closed for conn in self.connections))
        if error:
            error.add_note('M7 trace: '+repr(self.trace))
            if cleanup_errors:
                error.add_note('M7 cleanup errors: '+repr([type(e).__name__ for e in cleanup_errors]))
        elif cleanup_errors:
            raise cleanup_errors[0]


# All columns and rows, including expired/closed leases, owners, generations,
# timestamps and the complete journal. Hashes keep synthetic canonical/message
# content out of assertion output. Clock-relative projections are separate.
_DURABLE_TABLES = (
    'workspace_folders', 'workspace_folder_nextcloud_links', 'workspace_files',
    'workspace_file_nextcloud_links', 'conversations', 'conversation_messages',
    'document_workshop_contexts', 'conversation_turn_claims', 'document_artifacts',
    'document_revisions', 'document_actions', 'document_revision_renders',
    'document_receipts', 'document_execution_journal',
)


def durable_snapshot(case):
    with case.conn() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        return {table: sorted(hashlib.sha256(row[0].encode()).hexdigest() for row in
            conn.execute('SELECT to_jsonb(t)::text FROM '+table+' t').fetchall())
            for table in _DURABLE_TABLES}


def claim_projection(case, action):
    with case.conn() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        row = conn.execute('''SELECT c.turn_id::text,c.state,c.lease_until>clock_timestamp(),a.state,a.phase
            FROM document_actions a JOIN conversation_turn_claims c ON c.turn_id=a.confirmation_turn_id
            WHERE a.id=%s::uuid''', (action['id'],)).fetchone()
    return dict(zip(('turn_id', 'claim_state', 'lease_live', 'state', 'phase'), row))


def exercise_two_updates(case, *, overlap):
    with update_dav() as (base, state), case.configured(base):
        file_id = case.adopt(base, state)
        first = case.prepare(file_id)
        other = str(uuid4())
        conversation = conv_store.new_conversation('Synthetic', conversation_id=other)
        conversation['workspace_folder_id'] = case.folder
        case.assertTrue(conv_store.save_conversation(conversation).ok)
        second = case.prepare(file_id, conversation_id=other, text='Other')
        with ConcurrentUpdates(case, state, overlap=overlap) as harness:
            responses = harness.run(first, second)
            winner = next(a for a in (first, second) if harness.statuses[a['id']] == 204)
            loser = next(a for a in (first, second) if a is not winner)
            case.assertEqual(responses[winner['id']].status_code, 200)
            case.assertEqual(responses[loser['id']].status_code, 409)

            def get(action):
                response = case.server.app.test_client().get('/api/document-workshop/actions/'+action['id'])
                case.assertEqual(response.status_code, 200)
                view = response.json['action']
                harness.emit('get_return', action_id=action['id'], state=view['state'],
                             phase=view['phase'], receipt='receipt' in view)
                return view

            dav_after_confirm = list(state['seen'])
            claims_after_confirm = case.env.rows('SELECT turn_id,owner_id,generation FROM conversation_turn_claims ORDER BY turn_id')
            loser_view = get(loser)
            case.assertEqual(loser_view['state'], 'conflict')
            case.assertNotIn('receipt', loser_view)
            if overlap:
                rejections = [e['stage'] for e in harness.trace if e['actor'] == winner['id']
                              and e['event'] == 'rollback' and e['sqlstate'] == '55P03']
                case.assertEqual(rejections, ['observe', 'finish', 'claim_finish'], harness.trace)
                before = durable_snapshot(case)
                live = claim_projection(case, winner)
                harness.emit('sql_observed', point='before_first_get', **live)
                case.assertEqual((live['claim_state'], live['lease_live'], live['state'], live['phase']),
                                 ('active', True, 'executing', 'confirmed'))
                view = get(winner)
                case.assertEqual((view['state'], view['phase']), ('executing', 'confirmed'))
                case.assertNotIn('receipt', view)
                case.assertEqual(durable_snapshot(case), before)
                after_get = claim_projection(case, winner)
                case.assertEqual(after_get, live)
                harness.emit('sql_observed', point='after_first_get', **after_get)
                harness.emit('first_get_durable_unchanged')
                # Only this identified claim, in the owned disposable DB,
                # after the real supervisor has stopped and been joined.
                with case.conn() as conn:
                    changed = conn.execute("""UPDATE conversation_turn_claims
                        SET lease_until=clock_timestamp()-interval '1 second'
                        WHERE turn_id=%s::uuid AND state='active' RETURNING turn_id::text""",
                        (live['turn_id'],)).fetchall()
                case.assertEqual(changed, [(live['turn_id'],)])
                harness.emit('artificial_expiry', turn_id=live['turn_id'])
                expired = claim_projection(case, winner)
                harness.emit('sql_observed', point='before_expired_get', **expired)
                case.assertEqual((expired['claim_state'], expired['lease_live'], expired['state']),
                                 ('active', False, 'executing'))
                view = get(winner)
                case.assertEqual((view['state'], view['phase']), ('remote_uncertain', 'interrupted'))
                terminal = claim_projection(case, winner)
                harness.emit('sql_observed', point='after_expired_get', **terminal)
                case.assertEqual(terminal['claim_state'], 'lost')
                case.assertNotIn('receipt', view)
                case.assertEqual(case.env.rows("SELECT event FROM document_execution_journal WHERE action_id=%s::uuid AND event IN ('remote_outcome','metadata_reconciliation','metadata_published')", (winner['id'],)), [])
            else:
                view = get(winner)
                case.assertEqual(view['state'], 'succeeded')
                case.assertTrue(execution.verify_committed_action(winner['id'], storage_root=case.env.env.root))
                receipt = view['receipt']
                case.assertEqual(receipt['workspace_file_id'], file_id)
                case.assertEqual(receipt['nextcloud_file_id'], '42')
                case.assertEqual(case.server.app.test_client().get(receipt['product_link']).data,
                                 b'Revised\n' if winner is first else b'Other\n')
                harness.emit('receipt_verified', action_id=winner['id'])
            case.assertEqual(state['seen'], dav_after_confirm)
            case.assertEqual(case.env.rows('SELECT turn_id,owner_id,generation FROM conversation_turn_claims ORDER BY turn_id'), claims_after_confirm)
            before, dav_before = durable_snapshot(case), list(state['seen'])
            for action in (winner, loser):
                case.confirm(action)
                get(action)
            case.assertEqual(durable_snapshot(case), before)
            case.assertEqual(state['seen'], dav_before)
            case.assertEqual(case.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE state='active'"), [(0,)])
            for table in ('workspace_files', 'workspace_file_nextcloud_links'):
                case.assertEqual(case.env.rows('SELECT count(*) FROM '+table), [(1,)])
            for table in ('document_receipts', 'document_revision_renders'):
                case.assertEqual(case.env.rows('SELECT count(*) FROM '+table), [(0 if overlap else 1,)])
            mutations = [r for r in state['seen'] if r[0] in ('PUT', 'DELETE', 'MKCOL')]
            case.assertEqual([r[0] for r in mutations], ['PUT', 'PUT'])
            case.assertEqual([r[2]['If-Match'] for r in mutations], ['"v1"', '"v1"'])
            case.assertEqual(state['version'], 2, 'exactly one distant effect')
            harness.emit('verified', receipts=0 if overlap else 1, puts=2, effects=1, replay_dav=0)
        return harness.trace
