"""Synthetic HTTP DAV peer for M9-A; production clients own all operations."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
from urllib.parse import quote, unquote
from tests.unit.core.test_workspace_document_read_client_m2 import resource, multistatus, PREFIX


@contextmanager
def docx_dav():
    state = dict(files={}, collections={'Documents'}, seen=[], race=False, drop=False)
    class Peer(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        do_PROPFIND = do_GET = do_PUT = do_DELETE = do_MKCOL = lambda self: self.reply()

        def node(self, path):
            if path in state['collections']:
                return resource(path, href=PREFIX+quote(path, safe='/'))
            f = state['files'][path]
            return resource(path, collection=False, file_id=f['id'], etag=f['etag'], size=len(f['content']),
                media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                href=PREFIX+quote(path, safe='/'))

        def reply(self):
            path = unquote(self.path.removeprefix(PREFIX))
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            status, data, headers = 404, b'', {}
            f = state['files'].get(path)
            if self.command == 'PUT' and state['race'] and f:
                f['etag'] = '"outside"'
            if self.headers.get('If-Match') and (not f or self.headers['If-Match'] != f['etag']):
                status = 412
            elif self.command == 'PROPFIND' and (f or path in state['collections']):
                status, data = 207, multistatus(self.node(path))
            elif self.command == 'GET' and f:
                status, data, headers = 200, f['content'], {'ETag': f['etag']}
            elif self.command == 'MKCOL':
                status = 405 if path in state['collections'] else 201
                state['collections'].add(path)
            elif self.command == 'PUT':
                if self.headers.get('If-None-Match') == '*' and f:
                    status = 412
                elif self.headers.get('If-None-Match') == '*' or f and self.headers.get('If-Match'):
                    version = f['version']+1 if f else 1
                    state['files'][path] = dict(id=f['id'] if f else str(len(state['files'])+10),
                        content=body, version=version, etag='"v'+str(version)+'"')
                    status, headers = (204 if f else 201), {'ETag': state['files'][path]['etag']}
            elif self.command == 'DELETE' and f:
                del state['files'][path]; status = 204
            state['seen'].append((self.command, path, dict(self.headers), body, status))
            if self.command == 'PUT' and state['drop'] and status in (201,204):
                self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
            self.send_response(status)
            for k,v in headers.items(): self.send_header(k,v)
            self.send_header('Content-Length',str(len(data))); self.end_headers()
            try: self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError): pass
    peer = ThreadingHTTPServer(('127.0.0.1',0),Peer)
    thread = threading.Thread(target=peer.serve_forever,daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{peer.server_port}', state
    finally: peer.shutdown(); peer.server_close(); thread.join(5)
