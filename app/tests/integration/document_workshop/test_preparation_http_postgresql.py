"""Mounted chat + PostgreSQL authority + consumed, physically closed HTTP socket."""
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
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
    def upstream(self, *, blocked=False, keepalive=False):
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
        class AuditedTransport(DocumentHTTPTransport):
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

    def test_other_request_cancels_consumed_socket_and_prevents_late_commit(self):
        with self.upstream(blocked=True) as (arrived,closed,received,admitted,(normal,_)), ThreadPoolExecutor(1) as pool:
            request=pool.submit(self.env.document)
            self.assertTrue(arrived.wait(3))
            self.env.assert_no_open_transaction()
            with self.env.server.app.test_client() as client:
                cancel=client.post(f'/api/document-workshop/actions/{base.T}/cancel',json=dict(context_id=self.env.context['id']))
            self.assertEqual(cancel.status_code,200,cancel.json)
            self.assertTrue(closed.wait(3),'server did not observe EOF/reset')
            response=request.result(timeout=3)
        self.assertEqual(response.status_code,503)
        self.assertEqual(len(received),1);self.assertEqual(received,admitted);self.assertEqual(normal,[])
        self.assertEqual(self.env.public_action()['state'],'cancelled')
        with self.env.conn() as conn:
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
