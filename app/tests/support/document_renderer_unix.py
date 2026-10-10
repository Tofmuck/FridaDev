"""Synthetic M8-C server on a real AF_UNIX socket; no Writer or DAV."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import socketserver
import tempfile
import threading

from core import document_renderer_contract as c
from tests.support import document_renderer_fixtures as f
from tests.support.document_renderer_fake import FakeRenderer


class UnixRendererServer:
    def __init__(self, *, worker=None, respond=None):
        self.worker = worker or FakeRenderer()
        self.respond = respond
        self.requests = []
        self.errors = []
        self.entered = threading.Event()
        self.disconnected = threading.Event()
        self.resume = threading.Event()
        self._temporary = tempfile.TemporaryDirectory(prefix='renderer-unix-')
        self.path = str(Path(self._temporary.name) / 'renderer.sock')
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def do_GET(self): self.exchange('GET')
            def do_POST(self): self.exchange('POST')
            def do_DELETE(self): self.exchange('DELETE')

            def exchange(self, method):
                self.connection.settimeout(5)
                try:
                    assert self.request_version == 'HTTP/1.1'
                    assert self.headers['Host'] == 'writer-renderer'
                    assert self.headers['Connection'] == 'close'
                    assert self.headers['Accept-Encoding'] == 'identity'
                    assert 'Transfer-Encoding' not in self.headers
                    size = int(self.headers.get('Content-Length', '0'))
                    body = self.rfile.read(size)
                    assert len(body) == size
                    identity = self.headers.get('X-Frida-Request-SHA256')
                    owner.requests.append((method, self.path, identity))
                    if self.path == '/v1/capabilities':
                        assert method == 'GET' and size == 0
                        response = owner.worker.capabilities()
                    elif self.path == '/v1/jobs':
                        assert method == 'POST'
                        request = c.read_request(c.WireMessage(self.headers['Content-Type'], body), expected_engine=f.ENGINE)
                        owner.request = request
                        response = owner.worker.submit(request)
                    else:
                        request = owner.request
                        assert identity == request.identity
                        assert self.path in ('/v1/jobs/' + request.data['job_id'], '/v1/jobs/' + request.data['job_id'] + '/result')
                        if method == 'DELETE':
                            assert self.headers['Content-Type'] == 'application/json'
                            intent = c.validate_delete(c.read_json(body), request=request)
                            response = owner.worker.cancel_release(request, cancel=intent == 'cancel')
                        else:
                            assert method == 'GET' and size == 0
                            response = (owner.worker.result if self.path.endswith('/result') else owner.worker.status)(request)
                    if owner.respond and owner.respond(self, method, response):
                        return
                    self.reply(response)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as error:
                    owner.errors.append(type(error).__name__)
                finally:
                    self.close_connection = True

            def reply(self, response):
                self.send_response(response.http_status)
                self.send_header('Content-Type', response.content_type)
                self.send_header('Content-Length', str(len(response.body)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(response.body)
                self.wfile.flush()

        class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
            daemon_threads = False
            block_on_close = True

        self.server = Server(self.path, Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()

    def block(self, handler):
        """Wait for the *client* to close the blocked exchange, without a timer."""
        self.entered.set()
        if handler.connection.recv(1) == b'':
            self.disconnected.set()

    def close(self):
        self.resume.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        self._temporary.cleanup()
