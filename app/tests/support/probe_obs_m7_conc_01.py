"""Explicit diagnostic CLI for OBS-M7-CONC-01; never a discovered test.

Requires an owned, disposable M5_PROOF_PG_SOCKET database: the unchanged M7
fixture recreates its public schema. Run control and overlap sequentially.
Only overlap changes the release point of the loser's real observation lock.
No imports of application modules, connections or threads occur at import.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from functools import wraps
import json
import os
import threading
import time
from unittest.mock import patch
from uuid import uuid4


def diagnose(scenario):
    if not os.environ.get('M5_PROOF_PG_SOCKET'):
        raise RuntimeError('explicit disposable proof database required')
    from core import conversation_turn_claims as claims
    from core import conv_store
    from core import document_workshop_execution_store as store
    from core import document_workshop_update_reconciliation as repair
    from core.chat_turn_reservation import ChatReservation
    from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
    from tests.integration.document_workshop.test_update_m7_postgresql import UpdateM7PostgresqlTests
    from tests.support.document_workshop_update_dav import update_dav

    origin = time.monotonic_ns()
    trace, mutex, local = [], threading.Lock(), threading.local()
    actors, reservations, statuses = {}, {}, {}
    loser_ready, winner_done = threading.Event(), threading.Event()

    def emit(event, **fields):
        with mutex:
            trace.append(dict(seq=len(trace), monotonic_ns=time.monotonic_ns()-origin,
                              actor=getattr(local, 'actor', 'observer'),
                              stage=getattr(local, 'stage', None), event=event, **fields))

    def error_fields(error):
        return dict(exception=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None),
                    reason_code=getattr(error, 'reason_code', None))

    def wait(event, name):
        emit('barrier_wait', barrier=name)
        if not event.wait(10):
            raise AssertionError('diagnostic barrier timed out: '+name)
        emit('barrier_pass', barrier=name)

    case = UpdateM7PostgresqlTests('runTest')
    try:
        case.setUp()
        # Independent read-only transactions. No claim.read/get_action here:
        # both can expire/reconcile rows and would erase the pre-GET evidence.
        def snapshot(label):
            with case.conn() as conn:
                conn.execute('SET TRANSACTION READ ONLY')
                rows = conn.execute('''SELECT a.id::text,a.state,a.phase,
                    c.turn_id::text,c.owner_id::text,c.generation,c.state,
                    c.lease_until::text,c.lease_until>clock_timestamp(),
                    c.outcome,(SELECT count(*) FROM document_receipts r WHERE r.action_id=a.id)
                    FROM document_actions a LEFT JOIN conversation_turn_claims c
                    ON c.turn_id=a.confirmation_turn_id WHERE a.id=ANY(%s::uuid[])
                    ORDER BY a.id''', (list(actors),)).fetchall()
                journals = conn.execute('''SELECT action_id::text,event,state,http_status
                    FROM document_execution_journal WHERE action_id=ANY(%s::uuid[])
                    ORDER BY created_at,id''', (list(actors),)).fetchall()
                counts = {table: conn.execute('SELECT count(*) FROM '+table).fetchone()[0]
                          for table in ('workspace_files', 'workspace_file_nextcloud_links',
                                        'document_receipts', 'document_revision_renders',
                                        'conversation_turn_claims')}
            result = dict(actions=[dict(zip(('action_id','state','phase','turn_id','owner_id',
                'generation','claim_state','lease_until','lease_live','outcome','receipts'), row))
                for row in rows], journal=journals, counts=counts)
            emit('sql_snapshot', label=label, snapshot=result)
            return result

        def lock_snapshot(conn):
            with case.conn() as observer:
                observer.execute('SET TRANSACTION READ ONLY')
                locks = observer.execute('''SELECT pid,locktype,mode,granted,
                    relation::regclass::text,transactionid::text
                    FROM pg_locks WHERE pid=%s ORDER BY locktype,mode''',
                    (conn.info.backend_pid,)).fetchall()
                activity = observer.execute('''SELECT pid,state,backend_xid::text
                    FROM pg_stat_activity WHERE pid=%s''', (conn.info.backend_pid,)).fetchall()
            emit('lock_owner_snapshot', pid=conn.info.backend_pid, locks=locks, activity=activity)

        def traced(name, method):
            @wraps(method)
            def call(*args, **kwargs):
                previous = getattr(local, 'stage', None)
                local.stage = name
                emit('enter')
                try:
                    value = method(*args, **kwargs)
                    emit('return')
                    return value
                except BaseException as error:
                    emit('raise', **error_fields(error))
                    raise
                finally:
                    local.stage = previous
            return call

        def connection_trace(name, factory):
            @contextmanager
            def connect():
                pid = None
                try:
                    with factory() as conn:
                        pid = conn.info.backend_pid
                        emit('transaction_enter', store=name, pid=pid)
                        yield conn
                    emit('transaction_commit', store=name, pid=pid)
                except BaseException as error:
                    emit('transaction_rollback', store=name, pid=pid, **error_fields(error))
                    raise
            return connect

        real_resources, real_observe = store._resources, store.observe
        real_mutation = NextcloudDocumentMutationClient._mutation_request
        real_update = NextcloudDocumentMutationClient.update_document
        real_init, real_renew = ChatReservation.__init__, ChatReservation._renew
        real_close = ChatReservation.close

        def resources(conn, row):
            emit('resources_lock_attempt', pid=conn.info.backend_pid)
            try:
                value = real_resources(conn, row)
            except BaseException as error:
                emit('resources_lock_refused', pid=conn.info.backend_pid, **error_fields(error))
                raise
            emit('resources_lock_acquired', pid=conn.info.backend_pid)
            if getattr(local, 'stage', None) == 'observe' and getattr(local, 'dav_status', None) == 412:
                lock_snapshot(conn)
                if scenario == 'overlap':
                    loser_ready.set()
                    wait(winner_done, 'winner_http_return_before_loser_observation_commit')
            return value

        def observe(run, event, result):
            if result.http_status == 204:
                wait(loser_ready, 'loser_lock_held' if scenario == 'overlap' else 'loser_http_return_lock_released')
            return real_observe(run, event, result)

        def mutation(client, method, *args, **kwargs):
            emit('dav_request', method=method,
                 if_match=(kwargs.get('headers') or {}).get('If-Match'))
            value = real_mutation(client, method, *args, **kwargs)
            emit('dav_response', method=method, status=value[0], etags=value[1].get_all('ETag', []))
            return value

        def update(client, *args, **kwargs):
            value = real_update(client, *args, **kwargs)
            local.dav_status = value.http_status
            statuses[local.actor] = value.http_status
            emit('dav_validated_result', status=value.http_status, state=value.state,
                 etag=value.creation_etag, reason_code=value.reason_code)
            return value

        def reserve(reservation, token, *args, **kwargs):
            real_init(reservation, token, *args, **kwargs)
            reservations[token.conversation_id] = reservation
            emit('reservation_started', turn_id=token.turn_id, owner_id=token.owner_id,
                 generation=token.generation, lease_seconds=claims.LEASE_SECONDS,
                 renew_seconds=claims.RENEW_SECONDS)

        def renew_loop(reservation):
            local.actor = actors_by_conversation[reservation.token.conversation_id]
            try:
                return real_renew(reservation)
            finally:
                emit('supervisor_exit', turn_id=reservation.token.turn_id,
                     stop=reservation._stop.is_set(), lost=reservation._lost)

        def close(reservation):
            emit('reservation_close_enter', turn_id=reservation.token.turn_id)
            value = real_close(reservation)
            emit('reservation_close_return', turn_id=reservation.token.turn_id,
                 stop=reservation._stop.is_set(), closed=reservation._closed, lost=reservation._lost)
            return value

        with update_dav() as (base, state), case.configured(base), ExitStack() as stack:
            file_id = case.adopt(base, state)
            first = case.prepare(file_id)
            other = str(uuid4())
            conversation = conv_store.new_conversation('Synthetic', conversation_id=other)
            conversation['workspace_folder_id'] = case.folder
            assert conv_store.save_conversation(conversation).ok
            second = case.prepare(file_id, conversation_id=other, text='Other')
            actors.update({first['id']:'A', second['id']:'B'})
            actors_by_conversation = {first['conversation_id']:'A',second['conversation_id']:'B'}
            emit('prepared', actions=actors, file_id=file_id)
            for module in (store, claims):
                stack.enter_context(patch.object(module, '_db_conn', connection_trace(module.__name__, module._db_conn)))
            stack.enter_context(patch.object(store, '_resources', resources))
            stack.enter_context(patch.object(store, 'observe', traced('observe', observe)))
            for name in ('begin', 'finish', 'publish', 'reconcile'):
                stack.enter_context(patch.object(store, name, traced(name, getattr(store,name))))
            for name in ('finish', 'renew', 'read'):
                stack.enter_context(patch.object(claims, name, traced('claim_'+name, getattr(claims,name))))
            stack.enter_context(patch.object(repair, 'reconcile', traced('metadata_reconcile', repair.reconcile)))
            stack.enter_context(patch.object(NextcloudDocumentMutationClient, '_mutation_request', mutation))
            stack.enter_context(patch.object(NextcloudDocumentMutationClient, 'update_document', update))
            stack.enter_context(patch.object(ChatReservation, '__init__', reserve))
            stack.enter_context(patch.object(ChatReservation, '_renew', renew_loop))
            stack.enter_context(patch.object(ChatReservation, 'close', close))

            def confirm(action, *, replay=False):
                local.actor = actors[action['id']]
                emit('http_confirm_enter', action_id=action['id'], replay=replay)
                response = case.confirm(action)
                projected = (response.json or {}).get('action') or {}
                emit('http_confirm_return', action_id=action['id'], replay=replay,
                     status=response.status_code, state=projected.get('state'),
                     phase=projected.get('phase'), receipt=bool(projected.get('receipt')),
                     reason_code=(response.json or {}).get('reason_code'))
                if not replay:
                    if statuses.get(local.actor) == 204:
                        winner_done.set()
                    elif scenario == 'control':
                        loser_ready.set()
                return response

            state['block_put'] = True
            state['release'].clear()
            with ThreadPoolExecutor(2) as pool:
                a = pool.submit(confirm, first)
                try:
                    wait(state['arrived'], 'first_put_arrived')
                    b = pool.submit(confirm, second)
                    with state['changed']:
                        if not state['changed'].wait_for(lambda: sum(r[0]=='PUT' for r in state['seen'])==2, 5):
                            raise AssertionError('two PUTs did not arrive')
                    emit('two_puts_arrived', if_matches=[r[2].get('If-Match') for r in state['seen'] if r[0]=='PUT'])
                    case.env.assert_no_transaction()
                    snapshot('before_dav_release')
                finally:
                    emit('dav_barrier_release')
                    state['release'].set()
                responses = [a.result(timeout=10), b.result(timeout=10)]
            local.actor = 'observer'
            for reservation in reservations.values():
                # Only join after the real requests have stopped their own
                # supervisor; never stop/suspend or otherwise alter renewal.
                assert reservation._stop.is_set()
                reservation._thread.join(timeout=2)
                assert not reservation._thread.is_alive()
            ended = snapshot('both_http_returned_supervisors_exited')
            assert sum(r.status_code==200 for r in responses) <= 1
            assert sorted(statuses.values()) == [204,412]
            assert ended['counts']['workspace_files'] == ended['counts']['workspace_file_nextcloud_links'] == 1
            assert ended['counts']['document_receipts'] == (0 if scenario=='overlap' else 1)
            winner = next(action for action in (first,second) if statuses[actors[action['id']]]==204)
            loser = next(action for action in (first,second) if action is not winner)

            def get(action, label):
                local.actor = actors[action['id']]
                before = snapshot(label+'_before_get')
                emit('http_get_enter', action_id=action['id'], label=label)
                response = case.server.app.test_client().get('/api/document-workshop/actions/'+action['id'])
                assert response.status_code == 200
                projected = response.json['action']
                emit('http_get_return', action_id=action['id'], label=label,
                     status=response.status_code, state=projected['state'], phase=projected['phase'],
                     receipt=bool(projected.get('receipt')))
                after = snapshot(label+'_after_get')
                return projected,before,after

            view, before, after = get(winner, 'winner_first')
            loser_view, _, _ = get(loser, 'loser_first')
            local.actor = 'observer'
            assert loser_view['state'] == 'conflict'
            historical_assertion_would_fail = view['state'] not in ('succeeded','conflict','remote_uncertain')
            assert historical_assertion_would_fail == (scenario=='overlap')
            try:
                case.assertIn(view['state'], ('succeeded','conflict','remote_uncertain'))
            except AssertionError:
                assert scenario == 'overlap'
                emit('historical_assertion_red', action_id=winner['id'], observed_state=view['state'],
                     assertion='assertIn(state, (succeeded, conflict, remote_uncertain))')
            else:
                assert scenario == 'control'
                emit('historical_assertion_green', action_id=winner['id'], observed_state=view['state'])
            if scenario == 'overlap':
                assert view['state']=='executing' and view['phase']=='confirmed' and not view.get('receipt')
                winner_row = next(row for row in before['actions'] if row['action_id']==winner['id'])
                assert winner_row['claim_state']=='active' and winner_row['lease_live']
                assert before == after  # First GET cannot close a still-live claim.
                winner_actor = actors[winner['id']]
                for stage in ('observe', 'finish', 'claim_finish'):
                    assert any(e['actor']==winner_actor and e['stage']==stage
                               and e['event']=='transaction_rollback' and e.get('sqlstate')=='55P03'
                               for e in trace)
                assert not any(e['actor']==winner_actor and e['stage']=='publish' for e in trace)
                lock_event = next(e for e in trace if e['event']=='lock_owner_snapshot')
                assert lock_event['actor']==actors[loser['id']]
                assert lock_event['activity'][0][1]=='idle in transaction'
                assert lock_event['activity'][0][2] is not None
                # Artificial boundary in the disposable DB, after supervisor
                # exit. Product lease/clock/renewal are never patched.
                emit('artificial_lease_expiry_enter', turn_id=winner_row['turn_id'])
                with case.conn() as conn:
                    conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s::uuid AND state='active'", (winner_row['turn_id'],))
                emit('artificial_lease_expiry_commit', turn_id=winner_row['turn_id'])
                view, expired_before, expired_after = get(winner, 'winner_expired')
                assert next(row for row in expired_before['actions'] if row['action_id']==winner['id'])['state']=='executing'
                assert view['state']=='remote_uncertain' and not view.get('receipt')
                assert next(row for row in expired_after['actions'] if row['action_id']==winner['id'])['claim_state']=='lost'
                # No durable successful remote_outcome => metadata-only repair
                # cannot attribute the observed bytes to this claim.
                assert not any(row[0]==winner['id'] and row[1]=='remote_outcome' for row in expired_after['journal'])
            else:
                assert view['state']=='succeeded' and view.get('receipt')
            before_replay = snapshot('before_replay')
            seen_before = len(state['seen'])
            for action in (winner,loser):
                confirm(action, replay=True)
            local.actor = 'observer'
            final = snapshot('after_replay')
            assert before_replay == final
            assert len(state['seen']) == seen_before
            assert all(row['claim_state']!='active' for row in final['actions'])
            mutations = [r[0] for r in state['seen'] if r[0] in ('PUT','DELETE','MKCOL')]
            assert mutations == ['PUT','PUT'] and state['version']==2
            assert all(r[2]['If-Match']=='"v1"' for r in state['seen'] if r[0]=='PUT')
            assert final['counts']['document_receipts']==final['counts']['document_revision_renders']==(0 if scenario=='overlap' else 1)
            emit('invariants_verified', mutations=mutations, remote_version=state['version'],
                 remote_effects=state['version']-1, receipts=final['counts']['document_receipts'],
                 active_claims=0, replay_dav_calls=0, historical_assertion_would_fail=historical_assertion_would_fail)
        return dict(scenario=scenario, passed=True, trace=trace)
    finally:
        case.doCleanups()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=('control','overlap'), required=True)
    args = parser.parse_args()
    print(json.dumps(diagnose(args.scenario), ensure_ascii=False))


if __name__ == '__main__':
    main()
