"""P3-M6-AUD-03: causal admission/drain/resume around the fixture's row lock."""
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from tests.integration.document_workshop import test_action_cancellation_postgresql as fixture


@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class ActionCancellationPausePostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ActionCancellationPostgresqlTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()

    def assert_quiet_before_external_lock(self, checks, pid):
        # Shared by the positive and deliberately unsynchronized negative proof.
        self.assertEqual(checks.snapshot()['active'], 0,
                         'supervision still active before external lock')
        with self.case.env.conn() as conn:
            self.assertEqual(conn.execute('''SELECT count(*) FROM pg_stat_activity
                WHERE pid=%s AND xact_start IS NOT NULL''', (pid,)).fetchone()[0], 0,
                'supervision transaction still open before external lock')

    def prove_pause(self, *, omit_drain):
        env, actions = self.case.env, self.case.actions
        provider = fixture.fixture.Provider(gate=True)
        entered, release_store = threading.Event(), threading.Event()
        pause_waiting, deferred = threading.Event(), threading.Event()
        acquired, release_lock, lock_finished = (threading.Event() for _ in range(3))
        store_returned, resumed_store = threading.Event(), threading.Event()
        owner, deferred_threads, resumed_threads = {}, set(), set()
        real_authority = actions._authority

        def authority(conn, token):
            result = real_authority(conn, token)
            if (threading.current_thread().name == 'document-preparation'
                    and provider.arrived.is_set() and not entered.is_set()):
                owner['pid'] = conn.info.backend_pid
                entered.set()
                self.assertTrue(release_store.wait(5), 'admitted real store was not released')
            return result

        def audit_store(function):
            def call(*args, **kwargs):
                result = function(*args, **kwargs)
                # The original function has exited its SQL context here.
                name = threading.current_thread().name
                if name == 'document-preparation' and entered.is_set():
                    store_returned.set()
                if lock_finished.is_set() and name in deferred_threads:
                    resumed_threads.add(name)
                    resumed_store.set()
                return result
            return call

        with env.pipeline(provider) as (normal, _), \
             patch.object(actions, '_authority', authority), \
             patch.object(actions, 'project_progress', audit_store(actions.project_progress)), \
             patch.object(actions, 'check_active', audit_store(actions.check_active)), \
             self.case.external_lock_supervision_pause() as checks, \
             ThreadPoolExecutor(2) as pool:
            real_wait = checks.condition.wait_for
            def observe_wait(predicate, timeout):
                if threading.current_thread().name == 'external-lock-proof':
                    pause_waiting.set()
                    # Negative injection affects only the drain, never admission
                    # or the real stores. It cannot reach the row-lock effect.
                    if omit_drain:
                        return True
                elif checks.snapshot()['paused']:
                    deferred_threads.add(threading.current_thread().name)
                    deferred.set()
                return real_wait(predicate, timeout)

            def lock_window():
                threading.current_thread().name = 'external-lock-proof'
                try:
                    checks.pause()
                    self.assert_quiet_before_external_lock(checks, owner['pid'])
                    self.assertTrue(store_returned.is_set(), 'real admitted store did not return')
                    with env.conn() as holder:
                        holder.execute('SELECT id FROM document_actions WHERE id=%s::uuid FOR UPDATE',
                                       (fixture.B,))
                        acquired.set()
                        self.assertTrue(release_lock.wait(5), 'external row lock was not released')
                finally:
                    # The holder's SQL context exits before any deferred store.
                    lock_finished.set()
                    checks.resume()

            request = pool.submit(env.document, identity=fixture.B, message='Synthetic pause proof')
            window = None
            try:
                self.assertTrue(provider.arrived.wait(5)); self.assertTrue(entered.wait(5))
                with env.conn() as conn:
                    self.assertEqual(conn.execute('SELECT xact_start IS NOT NULL FROM pg_stat_activity WHERE pid=%s',
                                                  (owner['pid'],)).fetchone(), (True,))
                with patch.object(checks.condition, 'wait_for', observe_wait):
                    window = pool.submit(lock_window)
                    self.assertTrue(pause_waiting.wait(5))
                    if omit_drain:
                        with self.assertRaisesRegex(AssertionError, 'supervision still active before external lock'):
                            window.result(timeout=5)
                        self.assertFalse(acquired.is_set(), 'negative calibration reached an external SQL effect')
                        release_store.set()
                        self.assertTrue(store_returned.wait(5))
                    else:
                        self.assertTrue(checks.snapshot()['paused'])
                        self.assertGreater(checks.snapshot()['active'], 0)
                        self.assertFalse(acquired.is_set(), 'row lock preceded the admitted store return')
                        release_store.set()
                        self.assertTrue(acquired.wait(5))
                        self.assert_quiet_before_external_lock(checks, owner['pid'])
                        self.assertTrue(store_returned.is_set())
                        # The same live watchdog can now reach its next store.
                        # Waiting before releasing its admitted call would assume
                        # an independent concurrent control and can deadlock.
                        self.assertTrue(deferred.wait(5), 'no real control arrived at paused admission')
                        self.assertFalse(resumed_store.is_set(), 'deferred store ran inside the row-lock window')
                        release_lock.set()
                        window.result(timeout=5)
                        self.assertTrue(resumed_store.wait(5), 'deferred control did not execute its real store')
                        self.assertTrue(deferred_threads & resumed_threads)
            finally:
                release_store.set(); release_lock.set(); checks.resume()
                try:
                    if window is not None:
                        # Join before releasing the provider; the expected
                        # negative exception was already inspected above.
                        window.exception(timeout=5)
                finally:
                    # A failed/timed-out window must also release the exchange.
                    provider.release.set()
                    response = request.result(timeout=10)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.case.get(fixture.B)['state'], 'pending')
        self.assertEqual(len(provider.calls), 1); self.assertEqual(normal, [])
        env.assert_no_open_transaction()
        print('P3_M6_AUD_03_PAUSE '+json.dumps(dict(case=self._testMethodName,
            omitted_drain=omit_drain, real_admitted_transaction=True,
            drain_rejected_before_effect=omit_drain and not acquired.is_set(),
            row_lock_after_store_return=not omit_drain and acquired.is_set(),
            real_deferred_control_resumed=bool(deferred_threads & resumed_threads),
            request_http=response.status_code, provider_calls=len(provider.calls), raw_content_included=False)))

    def test_pause_drains_real_transaction_defers_admission_and_resumes_real_store(self):
        self.prove_pause(omit_drain=False)

    def test_same_probe_rejects_omitted_drain_before_external_sql_effect(self):
        self.prove_pause(omit_drain=True)
