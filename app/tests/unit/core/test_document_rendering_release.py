"""AUD-02: the last acknowledged exchange is still subject to useful progress age."""
import unittest
from unittest.mock import patch
from core import document_renderer_contract as c
from core import document_rendering as rendering
from tests.support import document_renderer_fixtures as f
from tests.support.document_renderer_fake import FakeRenderer


class RenderingReleaseTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.worker = FakeRenderer()
        self.request = c.make_request(job_id=f.JOB, revision_id=f.REVISION, canonical=f.canonical(),
            canonical_sha256=c.digest(c.json_bytes(f.canonical())), format='docx', engine=f.ENGINE)
        self.session = rendering.RenderingSession(client=self.worker, expected_engine=f.ENGINE,
            monotonic=lambda: self.now, wait=lambda: None)
        self.events = []

    def delayed_release(self, delay):
        release = self.worker.cancel_release
        def delayed(request, *, cancel=False):
            self.assertFalse(cancel)
            self.assertIsNotNone(self.session.collected)
            self.events.append('snapshot_before_release')
            self.now += delay
            ack = release(request, cancel=cancel)
            c.validate_release_message(ack, request=request)
            self.events.append('valid_release_ack')
            return ack
        self.worker.cancel_release = delayed

    def assert_refused_without_replay(self, reason):
        with self.assertRaises(c.RendererError) as caught:
            self.session.collect(self.request, check=lambda: None)
        self.assertEqual(caught.exception.reason_code, reason)
        self.assertIsNotNone(self.session.collected)
        self.assertIsNone(self.session._released)
        self.assertEqual(self.worker.events, ['capabilities', 'submit', 'status', 'result', 'release'])
        events = list(self.worker.events)
        with self.assertRaises(c.RendererError) as repeated:
            self.session.collect(self.request, check=lambda: None)
        self.assertEqual(repeated.exception.reason_code, 'renderer_job_lost')
        self.assertEqual(self.worker.events, events)
        self.assertEqual(self.worker.executions, 1)

    def test_nominal_ack_is_accepted_and_reused_without_exchange(self):
        self.delayed_release(0)
        result = self.session.collect(self.request, check=lambda: None)
        self.assertEqual(result.release['state'], 'released')
        self.assertIs(result, self.session.collect(self.request, check=lambda: None))
        self.assertEqual(self.events, ['snapshot_before_release', 'valid_release_ack'])
        self.assertEqual(self.worker.events, ['capabilities', 'submit', 'status', 'result', 'release'])

    def test_ack_at_119_999_seconds_is_accepted(self):
        self.delayed_release(119.999)
        result = self.session.collect(self.request, check=lambda: None)
        self.assertEqual(result.release['workspace_removed'], True)
        self.assertEqual(self.now, 119.999)
        self.assertEqual(self.events, ['snapshot_before_release', 'valid_release_ack'])

    def test_ack_at_exact_120_seconds_is_refused_without_cache_or_replay(self):
        self.delayed_release(120)
        self.assert_refused_without_replay('renderer_inactivity')
        self.assertEqual(self.events, ['snapshot_before_release', 'valid_release_ack'])
        self.assertIsNone(self.worker.active)
        self.assertTrue(self.worker.jobs[f.JOB]['released'])

    def test_ack_beyond_120_seconds_is_refused_without_cache_or_replay(self):
        self.delayed_release(121)
        self.assert_refused_without_replay('renderer_inactivity')
        self.assertEqual(self.events, ['snapshot_before_release', 'valid_release_ack'])

    def test_release_uses_age_already_consumed_in_result(self):
        result = self.worker.result
        def delayed(request):
            self.now += 70
            return result(request)
        self.worker.result = delayed
        self.delayed_release(50)
        self.assert_refused_without_replay('renderer_inactivity')
        self.assertEqual(self.now, 120)
        self.assertEqual(self.events, ['snapshot_before_release', 'valid_release_ack'])

    def test_ack_validation_time_is_included_in_final_decision(self):
        validate = c.validate_release_message
        def delayed(*args, **kwargs):
            ack = validate(*args, **kwargs)
            self.now += 120
            self.events.append('validated_ack')
            return ack
        with patch.object(c, 'validate_release_message', delayed):
            self.assert_refused_without_replay('renderer_inactivity')
        self.assertEqual(self.events, ['validated_ack'])

    def test_final_authority_check_time_is_included_in_final_decision(self):
        checks = []
        def check():
            if 'release' in self.worker.events:
                checks.append('authority')
                if len(checks) == 2:
                    self.now += 120
        with self.assertRaises(c.RendererError) as caught:
            self.session.collect(self.request, check=check)
        self.assertEqual(caught.exception.reason_code, 'renderer_inactivity')
        self.assertEqual(checks, ['authority', 'authority'])
        self.assertIsNone(self.session._released)
        self.assertEqual(self.worker.events.count('release'), 1)
        self.assertNotIn('cancel', self.worker.events)

    def test_ack_lost_after_real_release_is_closed_without_second_cleanup(self):
        release = self.worker.cancel_release
        def lost(request, **kwargs):
            release(request, **kwargs)
            raise RuntimeError('synthetic lost acknowledgment')
        self.worker.cancel_release = lost
        self.assert_refused_without_replay('renderer_incomplete')
        self.assertIsNone(self.worker.active)

    def test_wrong_ack_identity_state_workspace_and_http_are_closed_without_retry(self):
        changes = [dict(job_id='10000000-0000-4000-8000-000000000099'), dict(request_sha256='0'*64),
            dict(state='cancelled', reason_code='renderer_cancelled'), dict(workspace_removed=False)]
        for change in changes + [None]:
            with self.subTest(change=change):
                self.setUp()
                self.worker.release_change = change or {}
                if change is None:
                    release = self.worker.cancel_release
                    def wrong_http(request, **kwargs):
                        ack = release(request, **kwargs)
                        return c.WireMessage(ack.content_type, ack.body, 503)
                    self.worker.cancel_release = wrong_http
                self.assert_refused_without_replay('renderer_incomplete')

    def test_lost_authority_after_ack_prevents_cache_without_second_cleanup(self):
        def check():
            if 'release' in self.worker.events:
                raise RuntimeError('synthetic authority lost')
        with self.assertRaisesRegex(RuntimeError, '^synthetic authority lost$'):
            self.session.collect(self.request, check=check)
        self.assertIsNone(self.session._released)
        self.assertIsNotNone(self.session.collected)
        self.assertEqual(self.worker.events, ['capabilities', 'submit', 'status', 'result', 'release'])

    def test_cleanup_failure_preserves_initial_inactivity_and_never_replays(self):
        result = self.worker.result
        release = self.worker.cancel_release
        def late(request):
            self.now += 120
            return result(request)
        def failed_cleanup(request, *, cancel=False):
            self.assertTrue(cancel)
            release(request, cancel=cancel)
            raise RuntimeError('synthetic cleanup failure')
        self.worker.result = late
        self.worker.cancel_release = failed_cleanup
        with self.assertRaises(c.RendererError) as caught:
            self.session.collect(self.request, check=lambda: None)
        self.assertEqual(caught.exception.reason_code, 'renderer_inactivity')
        self.assertIsNone(self.session.collected)
        self.assertIsNone(self.session._released)
        self.assertEqual(self.worker.events, ['capabilities', 'submit', 'status', 'result', 'cancel'])
        with self.assertRaises(c.RendererError):
            self.session.collect(self.request, check=lambda: None)
        self.assertEqual(self.worker.events.count('cancel'), 1)
        self.assertEqual(self.worker.events.count('submit'), 1)
