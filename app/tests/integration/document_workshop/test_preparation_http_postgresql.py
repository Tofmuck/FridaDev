"""Mounted chat + PostgreSQL authority + consumed, physically closed HTTP socket."""
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import psycopg
from core import document_workshop_turn as turn
from core.document_workshop_http_transport import DocumentHTTPTransport
from core.document_workshop_progress import DocumentPreparation
from tests.integration.document_workshop import test_preparation_postgresql as base

@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'),'isolated PostgreSQL proof required')
class HTTPPreparationPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.env=base.PreparationPostgresqlTests()
        self.env.setUp();self.addCleanup(self.env.doCleanups)

    @contextmanager
    def upstream(self, *, blocked=False, keepalive=False, transport_type=DocumentHTTPTransport):
        arrived, closed=threading.Event(),threading.Event()
        received, admitted=[],[]
        value=base.envelope()
        frames=[]
        for choices in ([dict(index=0,delta=dict(content=json.dumps(value,ensure_ascii=False)),finish_reason=None)],
                        [dict(index=0,delta={},finish_reason='stop')]):
            frames.append('data: '+json.dumps(dict(model='openai/gpt-5.1',choices=choices),ensure_ascii=False)+'\n\n')
        wire=(''.join(frames)+'data: [DONE]\n\n').encode()
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*_):pass
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200);self.send_header('Content-Type','text/event-stream')
                if not blocked:self.send_header('Content-Length',str(len(wire)))
                self.end_headers()
                if blocked:
                    self.wfile.write(b': keepalive\n\n' if keepalive else wire[:16]);self.wfile.flush()
                else:self.wfile.write(wire);self.wfile.flush()
                arrived.set()
                self.connection.settimeout(4)
                try:
                    if self.connection.recv(1)==b'':closed.set()
                except ConnectionResetError:closed.set()
                self.close_connection=True
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        class AuditedTransport(transport_type):
            async def send(self,prepared):
                admitted.append(prepared.body)
                return await super().send(prepared)
        try:
            with self.env.pipeline(None,transport_factory=AuditedTransport) as observed, \
                 patch.object(self.env.server.llm,'or_chat_completions_url',lambda:f'http://127.0.0.1:{server.server_port}/v1/chat/completions'):
                yield arrived,closed,received,admitted,observed
        finally:
            server.shutdown();server.server_close();worker.join(2)

    def test_exact_admitted_http_bytes_consume_sse_and_commit_before_close(self):
        with self.upstream() as (arrived,closed,received,admitted,(normal,_)):
            response=self.env.document(stream=True)
            self.assertTrue(arrived.wait(2));self.assertTrue(closed.wait(2))
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        self.assertEqual(received,admitted)
        self.assertEqual(len(received),1);self.assertEqual(normal,[])
        payload=json.loads(received[0])
        self.assertEqual(payload['max_tokens'],24000)
        self.assertIn('Synthetic request',str(payload['messages']))
        self.assertEqual(self.env.public_action()['state'],'pending')

    @contextmanager
    def held_supervisor_authority(self, provider_arrived):
        """Hold one real watchdog transaction after its locks, only until probe.

        Neither the HTTP request nor the async authority guard is gated. Two
        completed watchdog store calls prove supervision on both sides of this
        single rendezvous; their events are set after the real SQL commit.
        """
        held,release,continued=threading.Event(),threading.Event(),threading.Event()
        owner,completed={},[]
        actions=self.env.actions
        real_authority=actions._authority
        def authority(conn,token):
            result=real_authority(conn,token)
            if (threading.current_thread().name=='document-preparation'
                    and provider_arrived.is_set() and not held.is_set()):
                owner['pid']=conn.info.backend_pid
                held.set()
                if not release.wait(3):raise AssertionError('supervisor probe was not released')
            return result
        def observe_completion(real):
            def call(*args,**kwargs):
                result=real(*args,**kwargs)
                if threading.current_thread().name=='document-preparation' and held.is_set():
                    completed.append(1)
                    if len(completed)>=2:continued.set()
                return result
            return call
        try:
            with patch.object(actions,'_authority',authority), \
                 patch.object(actions,'project_progress',observe_completion(actions.project_progress)), \
                 patch.object(actions,'check_active',observe_completion(actions.check_active)):
                yield held,release,continued,owner
        finally:
            release.set()

    def cancel(self):
        with self.env.server.app.test_client() as client:
            return client.post(f'/api/document-workshop/actions/{base.T}/cancel',
                               json=dict(context_id=self.env.context['id']))

    def test_other_request_cancels_consumed_socket_and_prevents_late_commit(self):
        with self.upstream(blocked=True) as (arrived,closed,received,admitted,(normal,_)), \
             self.held_supervisor_authority(arrived) as (held,release,continued,owner), ThreadPoolExecutor(1) as pool:
            request=pool.submit(self.env.document)
            try:
                self.assertTrue(arrived.wait(3));self.assertTrue(held.wait(3))
                with self.env.conn() as conn:
                    self.assertEqual(conn.execute('SELECT xact_start IS NOT NULL FROM pg_stat_activity WHERE pid=%s',
                                                  (owner['pid'],)).fetchone(),(True,))
                # Calibration: the historical NOWAIT rejects this legitimate
                # supervision lock, while the request-owned probe must pass.
                with self.assertRaises(psycopg.errors.LockNotAvailable), self.env.conn() as conn:
                    conn.execute('SELECT id FROM conversations WHERE id=%s FOR UPDATE NOWAIT',(base.C,))
                self.env.assert_no_open_transaction()
                release.set()
                self.assertTrue(continued.wait(3),'real watchdog did not resume and commit')
                self.env.assert_no_open_transaction()
            finally:
                release.set()
                cancel=self.cancel()
            self.assertEqual(cancel.status_code,200,cancel.json)
            self.assertTrue(closed.wait(3),'server did not observe EOF/reset')
            response=request.result(timeout=3)
        self.assertEqual(response.status_code,503)
        self.assertEqual(len(received),1);self.assertEqual(received,admitted);self.assertEqual(normal,[])
        self.assertEqual(self.env.public_action()['state'],'cancelled')
        with self.env.conn() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM document_revisions').fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM conversation_messages WHERE role='assistant'").fetchone()[0],0)

    def test_request_transaction_probe_rejects_transaction_held_during_real_http_wait(self):
        env=self.env
        held=threading.Event()
        class HoldingRequestTransactionTransport(DocumentHTTPTransport):
            async def iter_lines(self):
                # Deliberate test-only defect on the request's own thread. No
                # conversation lock: only transaction lifetime is under test.
                with env.conn() as conn:
                    conn.execute('SELECT 1')
                    held.set()
                    async for line in super().iter_lines():yield line
        with self.upstream(blocked=True,transport_type=HoldingRequestTransactionTransport) as \
             (arrived,closed,received,admitted,(normal,_)), ThreadPoolExecutor(1) as pool:
            request=pool.submit(env.document)
            try:
                self.assertTrue(arrived.wait(3));self.assertTrue(held.wait(3))
                with self.assertRaisesRegex(AssertionError,'request transaction'):
                    env.assert_no_open_transaction()
            finally:
                cancel=self.cancel()
            self.assertEqual(cancel.status_code,200,cancel.json)
            self.assertTrue(closed.wait(3),'negative control did not close physical HTTP')
            response=request.result(timeout=3)
        self.assertEqual(response.status_code,503)
        self.assertEqual(len(received),1);self.assertEqual(received,admitted);self.assertEqual(normal,[])
        self.assertEqual(env.public_action()['state'],'cancelled')
        env.assert_no_open_transaction()
        with env.conn() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM document_revisions').fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM conversation_messages WHERE role='assistant'").fetchone()[0],0)

    def test_keepalive_only_does_not_renew_inactivity_and_closes_real_socket(self):
        clock=[0.]
        with patch.object(turn,'DocumentPreparation',lambda:DocumentPreparation(monotonic=lambda:clock[0])), \
             self.upstream(blocked=True,keepalive=True) as (arrived,closed,received,admitted,(normal,_)), ThreadPoolExecutor(1) as pool:
            request=pool.submit(self.env.document)
            self.assertTrue(arrived.wait(3));clock[0]=120.
            self.assertTrue(closed.wait(3),'inactivity did not abort consumed HTTP connection')
            response=request.result(timeout=3)
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json['reason_code'],'document_inactivity')
        self.assertEqual(self.env.public_action()['state'],'failed')
        self.assertEqual(normal,[]);self.assertEqual(len(received),1);self.assertEqual(received,admitted)
