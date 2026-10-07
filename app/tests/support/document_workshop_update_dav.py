"""Stateful local DAV peer: actual version/identity/precondition effects."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
from urllib.parse import quote, unquote

from tests.unit.core.test_workspace_document_read_client_m2 import resource, multistatus


@contextmanager
def update_dav(*, folder='Scope', content=b'Original\n', file_id='42', etag='"v1"', path='Documents/Exact.md'):
    prefix='/remote.php/dav/files/test/Frida/'+quote(folder,safe='')+'/'
    state=dict(content=content,file_id=file_id,etag=etag,path=path,seen=[],version=1,
               missing=False,concurrent_before_put=False,drop_put=False,block_put=False)
    arrived,release=threading.Event(),threading.Event();release.set()
    changed=threading.Condition()
    remote_lock=threading.Lock()
    state.update(arrived=arrived,release=release,changed=changed)
    class DAV(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        do_PROPFIND=do_GET=do_PUT=do_DELETE=do_MKCOL=lambda self:self.reply()
        def reply(self):
            body=self.rfile.read(int(self.headers.get('Content-Length',0)))
            relative=unquote(self.path.removeprefix(prefix))
            with changed:
                state['seen'].append((self.command,relative,dict(self.headers),body));changed.notify_all()
            if self.command=='PUT' and state['block_put']:
                arrived.set()
                if not release.wait(10):raise RuntimeError('owned proof gate timeout')
            if self.command=='PUT' and state['concurrent_before_put']:
                state.update(content=b'Concurrent\n',etag='"concurrent"')
            with remote_lock:
                status,headers,data=404,{},b''
                exists=relative==path and not state['missing']
                if self.headers.get('If-Match') is not None and (not exists or self.headers['If-Match']!=state['etag']):
                    status=412
                elif self.command=='PROPFIND' and exists:
                    node=resource(path,collection=False,file_id=state['file_id'],etag=state['etag'],
                        size=len(state['content']),media_type='text/markdown',href=prefix+quote(path,safe='/'))
                    status,data=207,multistatus(node)
                elif self.command=='GET' and exists:
                    status,headers,data=200,{'ETag':state['etag']},state['content']
                elif self.command=='PUT' and exists:
                    # This server would overwrite without If-Match. Tests must
                    # catch that product bug from the received final request.
                    state['version']+=1
                    state.update(content=body,etag='"v'+str(state['version'])+'"')
                    status,headers=204,{'ETag':state['etag']}
                    if state['drop_put']:
                        self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            self.send_response(status)
            for key,value in headers.items():self.send_header(key,value)
            self.send_header('Content-Length',str(len(data)));self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
    peer=ThreadingHTTPServer(('127.0.0.1',0),DAV)
    worker=threading.Thread(target=lambda:peer.serve_forever(poll_interval=.01),daemon=True);worker.start()
    try:yield f'http://127.0.0.1:{peer.server_port}',state
    finally:release.set();peer.shutdown();peer.server_close();worker.join(5)
