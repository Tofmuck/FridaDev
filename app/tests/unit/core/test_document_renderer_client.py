"""Actual HTTP Unix exchanges through the delivered application client."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import importlib.util
import threading
import unittest

from core import document_renderer_contract as c, document_rendering as rendering
from tests.support import document_renderer_fixtures as f
from tests.support.document_renderer_fake import FakeRenderer
from tests.support.document_renderer_unix import UnixRendererServer


class RendererUnixTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('core.document_renderer_client'), 'M8-A Unix client absent')
        self.client_module = importlib.import_module('core.document_renderer_client')
        self.request = c.make_request(job_id=f.JOB, revision_id=f.REVISION, canonical=f.canonical(),
            canonical_sha256=c.digest(c.json_bytes(f.canonical())), format='docx', engine=f.ENGINE)

    def server(self, **kwargs):
        server = UnixRendererServer(**kwargs)
        self.addCleanup(lambda: self.assertEqual(server.errors, []))
        self.addCleanup(server.close)
        return server

    def session(self, server, **kwargs):
        return rendering.RenderingSession(client=self.client_module.DocumentRendererClient(socket_path=server.path),
            expected_engine=f.ENGINE, wait=lambda: None, **kwargs)

    def test_nominal_consumes_all_five_endpoints_and_repeats_without_post(self):
        server = self.server()
        session = self.session(server)
        frozen = []
        result = session.collect(self.request, check=lambda: None, freeze=frozen.append)
        self.assertEqual(result.docx, f.docx())
        self.assertEqual(result.pdf, f.pdf())
        self.assertEqual(result.release['state'], 'released')
        self.assertEqual(frozen, [result.result])
        self.assertIs(session.collect(self.request, check=lambda: None), result)
        job = '/v1/jobs/' + f.JOB
        self.assertEqual([(m, p) for m, p, _ in server.requests],
            [('GET', '/v1/capabilities'), ('POST', '/v1/jobs'), ('GET', job), ('GET', job + '/result'), ('DELETE', job)])
        self.assertEqual(server.worker.executions, 1)
        self.assertIsNone(server.worker.active)

    def test_lost_and_truncated_submit_response_read_same_job_once(self):
        for truncate in (False, True):
            with self.subTest(truncate=truncate):
                def respond(handler, method, response):
                    if method != 'POST': return False
                    if truncate:
                        handler.wfile.write(b'HTTP/1.1 202 Accepted\r\nContent-Type: application/json\r\nContent-Length: ' +
                            str(len(response.body)).encode() + b'\r\nConnection: close\r\n\r\n' + response.body[:-1])
                    return True
                server = self.server(respond=respond)
                result = self.session(server).collect(self.request, check=lambda: None)
                self.assertEqual(result.manifest['job_id'], f.JOB)
                self.assertEqual(server.worker.events, ['capabilities', 'submit', 'status', 'result', 'release'])
                self.assertEqual(server.worker.executions, 1)
                self.doCleanups()

    def test_lost_submit_with_worker_disappearance_never_replays(self):
        def respond(handler, method, response):
            if method == 'POST':
                server.worker.restart()
                return True
        server = self.server(respond=respond)
        with self.assertRaises(c.RendererError) as caught:
            self.session(server).collect(self.request, check=lambda: None)
        self.assertEqual(caught.exception.reason_code, 'renderer_job_lost')
        self.assertEqual(server.worker.events.count('submit'), 1)
        self.assertNotIn('result', server.worker.events)

    def test_wrong_identity_revision_hash_pages_pins_and_false_ready_fail_before_freeze(self):
        changes = [lambda m: m.update(job_id='10000000-0000-4000-8000-000000000099'),
            lambda m: m.update(revision_id='10000000-0000-4000-8000-000000000099'),
            lambda m: m.update(canonical_sha256='0'*64), lambda m: m.update(request_sha256='0'*64),
            lambda m: m['artifacts']['docx'].update(sha256='0'*64),
            lambda m: m['artifacts']['docx'].update(byte_size=1),
            lambda m: m['artifacts']['pdf'].update(pdf_pages=2),
            lambda m: m['page_evidence'].update(writer_pages=21),
            lambda m: m['engine']['fonts'][0].update(sha256='0'*64),
            lambda m: m['engine'].update(writer_version='other'),
            lambda m: m['artifacts'].pop('pdf')]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                server = self.server(worker=FakeRenderer(result_change=change))
                frozen = []
                with self.assertRaises(c.RendererError):
                    self.session(server).collect(self.request, check=lambda: None, freeze=frozen.append)
                self.assertEqual(frozen, [])
                self.assertEqual(server.worker.events[-1], 'cancel')
                self.assertNotIn('release', server.worker.events)
                self.doCleanups()

    def test_capabilities_cannot_choose_the_expected_pins(self):
        server = self.server()
        expected = c.read_json(c.json_bytes(f.ENGINE))
        expected['fonts'][0]['sha256'] = '0'*64
        request = c.make_request(job_id=f.JOB, revision_id=f.REVISION, canonical=f.canonical(),
            canonical_sha256=self.request.data['canonical_sha256'], format='docx', engine=expected)
        session = rendering.RenderingSession(client=self.client_module.DocumentRendererClient(socket_path=server.path),
            expected_engine=expected)
        with self.assertRaises(c.RendererError) as caught:
            session.collect(request, check=lambda: None)
        self.assertEqual(caught.exception.reason_code, 'renderer_profile_mismatch')
        self.assertNotIn('submit', server.worker.events)

    def test_http_framing_redirect_compression_extra_body_and_truncation_rejected(self):
        faults = [b'HTTP/1.1 302 Found\r\nLocation: http://elsewhere.invalid\r\nContent-Length: 0\r\n\r\n',
            b'HTTP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n',
            b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n',
            b'HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: 0\r\n\r\n',
            b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nContent-Length: 0\r\n\r\n',
            b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\nx',
            b'HTTP/1.1 200 OK\r\nContent-Length: 34603009\r\n\r\n',
            b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nx']
        for fault in faults:
            with self.subTest(fault=fault[:60]):
                def respond(handler, method, response):
                    handler.wfile.write(fault)
                    return True
                server = self.server(respond=respond)
                with self.assertRaises(c.RendererError): self.session(server).collect(self.request, check=lambda: None)
                self.assertEqual(server.worker.events, ['capabilities'])
                self.doCleanups()

    def test_blocked_socket_cancel_and_inclusive_inactivity_close_transport(self):
        for kind in ('cancel', 'inactivity'):
            with self.subTest(kind=kind):
                now = [0]
                cancelled = threading.Event()
                def respond(handler, method, response):
                    if method == 'GET' and handler.path.endswith('/result'):
                        server.block(handler)
                        return True
                server = self.server(respond=respond)
                session = self.session(server, monotonic=lambda: now[0])
                def check():
                    if cancelled.is_set(): raise RuntimeError('synthetic authority lost')
                with ThreadPoolExecutor(1) as pool:
                    task = pool.submit(session.collect, self.request, check=check)
                    self.assertTrue(server.entered.wait(5))
                    if kind == 'cancel': cancelled.set()
                    else: now[0] = 120
                    with self.assertRaises(RuntimeError if kind == 'cancel' else c.RendererError) as caught:
                        task.result(5)
                    if kind == 'inactivity': self.assertEqual(caught.exception.reason_code, 'renderer_inactivity')
                    self.assertTrue(server.disconnected.wait(5))
                self.assertIsNone(session.collected)
                self.assertEqual(server.worker.events[-1], 'cancel')
                self.assertIsNone(server.worker.active)
                self.doCleanups()

    def test_late_result_and_late_release_cannot_be_success(self):
        for endpoint in ('result', 'release'):
            with self.subTest(endpoint=endpoint):
                now = [0]
                def respond(handler, method, response):
                    if (endpoint == 'result' and handler.path.endswith('/result') or endpoint == 'release' and method == 'DELETE'):
                        now[0] = 120
                    return False
                server = self.server(respond=respond)
                session = self.session(server, monotonic=lambda: now[0])
                with self.assertRaises(c.RendererError) as caught:
                    session.collect(self.request, check=lambda: None)
                self.assertEqual(caught.exception.reason_code, 'renderer_inactivity')
                self.assertIsNone(session._released)
                self.assertEqual(server.worker.events.count('release'), int(endpoint == 'release'))
                self.assertEqual(server.worker.events.count('cancel'), int(endpoint == 'result'))
                self.doCleanups()

    def test_release_not_acknowledged_and_cleanup_blocked_preserve_initial_error(self):
        worker = FakeRenderer(release_change=dict(state='failed', reason_code='renderer_cleanup_failed', workspace_removed=False))
        server = self.server(worker=worker)
        with self.assertRaises(c.RendererError) as caught: self.session(server).collect(self.request, check=lambda: None)
        self.assertEqual(caught.exception.reason_code, 'renderer_cleanup_failed')
        self.assertEqual(worker.events.count('release'), 1)
        self.assertNotIn('cancel', worker.events)
        self.doCleanups()
        def respond(handler, method, response):
            if method == 'DELETE':
                server.block(handler)
                return True
        server = self.server(worker=FakeRenderer(result_change=lambda m: m['page_evidence'].update(writer_pages=21)), respond=respond)
        with self.assertRaises(c.RendererError) as caught: self.session(server).collect(self.request, check=lambda: None)
        self.assertEqual(caught.exception.reason_code, 'renderer_page_limit')
        self.assertTrue(server.disconnected.wait(5))
        self.assertEqual(server.worker.events.count('cancel'), 1)

    def test_configuration_has_no_url_relative_path_or_tcp_fallback(self):
        for path in ('http://renderer.invalid', 'renderer.sock', '/tmp/../renderer.sock', '/tmp/a\x00b'):
            with self.subTest(path=path):
                with self.assertRaises(c.RendererError): self.client_module.DocumentRendererClient(socket_path=path)
        client = self.client_module.DocumentRendererClient(socket_path='/nonexistent/m8a-renderer.sock')
        with self.assertRaises(c.RendererError): client.capabilities(check=lambda: None)

    def test_real_transport_useful_progress_can_exceed_120_seconds_total(self):
        server = self.server(worker=FakeRenderer(progress=[(1,0),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1),(8,1)]))
        now = [0]
        phases = []
        session = self.session(server, monotonic=lambda: now[0])
        session._wait = lambda: now.__setitem__(0, now[0]+100)
        result = session.collect(self.request, check=lambda: None, progress=lambda value: phases.append(value['phase']))
        self.assertEqual(result.release['state'], 'released')
        self.assertEqual(now[0], 800)
        self.assertEqual(phases, ['source_inspected', 'canonical_applied', 'docx_saved', 'docx_reloaded',
            'layout_stable', 'writer_pages_measured', 'pdf_exported', 'pdf_pages_measured'])

    def test_real_transport_polls_do_not_extend_useful_progress_deadline(self):
        server = self.server(worker=FakeRenderer(progress=[(0,0)]*3))
        now = [0]
        phases = []
        session = self.session(server, monotonic=lambda: now[0])
        session._wait = lambda: now.__setitem__(0, now[0]+60)
        with self.assertRaises(c.RendererError) as caught:
            session.collect(self.request, check=lambda: None, progress=phases.append)
        self.assertEqual(caught.exception.reason_code, 'renderer_inactivity')
        self.assertEqual(now[0], 120)
        self.assertEqual(phases, [])
        self.assertNotIn('result', server.worker.events)
        self.assertEqual(server.worker.events[-1], 'cancel')

    def test_release_reply_lost_never_causes_a_second_delete_or_success(self):
        def respond(handler, method, response): return method == 'DELETE'
        server = self.server(respond=respond)
        session = self.session(server)
        with self.assertRaises(c.RendererError): session.collect(self.request, check=lambda: None)
        self.assertIsNotNone(session.collected)
        self.assertIsNone(session._released)
        self.assertIsNone(server.worker.active)
        self.assertEqual(server.worker.events.count('release'), 1)
        self.assertNotIn('cancel', server.worker.events)

    def test_no_reply_to_accepted_submit_is_cancelled_at_inclusive_deadline(self):
        now = [0]
        def respond(handler, method, response):
            if method == 'POST':
                server.block(handler)
                return True
        server = self.server(respond=respond)
        session = self.session(server, monotonic=lambda: now[0])
        with ThreadPoolExecutor(1) as pool:
            task = pool.submit(session.collect, self.request, check=lambda: None)
            self.assertTrue(server.entered.wait(5))
            now[0] = 120
            with self.assertRaises(c.RendererError) as caught: task.result(5)
            self.assertEqual(caught.exception.reason_code, 'renderer_inactivity')
            self.assertTrue(server.disconnected.wait(5))
        self.assertEqual(server.worker.events, ['capabilities', 'submit', 'cancel'])
        self.assertIsNone(server.worker.active)
