"""Closed HTTP/1.1 AF_UNIX adapter. Configuration and authority belong to Frida.

One connection per exchange, exact Content-Length through EOF. No discovery,
TCP, redirects, retries or binary validation here; M8-C remains the validator.
"""
import errno
from pathlib import PurePosixPath
import re
import select
import socket

from . import document_renderer_contract as c
from .document_workshop_http_transport import DocumentHTTPTransport, MAX_HEADER_BYTES


class RendererTransportLost(c.RendererError):
    """An unproved exchange, distinguishable only for same-ID POST recovery."""


class DocumentRendererClient:
    def __init__(self, *, socket_path):
        if (type(socket_path) is not str or not socket_path.startswith('/') or '\x00' in socket_path
                or '..' in PurePosixPath(socket_path).parts):
            c.fail('renderer_input_invalid')
        self._socket_path = socket_path

    @staticmethod
    def _ready(sock, *, write, check):
        # The existing session supplies both M3 authority and useful-progress
        # checks. They keep running even when the peer sends no bytes or EOF.
        while True:
            check()
            readers, writers, _ = select.select([] if write else [sock], [sock] if write else [], [], .1)
            check()
            if readers or writers:
                return

    def _exchange(self, method, path, *, body=b'', content_type=None, identity=None, limit, check):
        check()
        headers = [method + ' ' + path + ' HTTP/1.1', 'Host: writer-renderer',
            'Connection: close', 'Accept-Encoding: identity', 'Content-Length: ' + str(len(body))]
        if content_type is not None: headers.append('Content-Type: ' + content_type)
        if identity is not None: headers.append('X-Frida-Request-SHA256: ' + c.sha(identity))
        head = ('\r\n'.join(headers) + '\r\n\r\n').encode('ascii')
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.setblocking(False)
                error = sock.connect_ex(self._socket_path)
                if error:
                    if error not in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
                        raise RendererTransportLost()
                    self._ready(sock, write=True, check=check)
                    if sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR): raise RendererTransportLost()
                for data in (head, body):
                    view = memoryview(data)
                    while view:
                        self._ready(sock, write=True, check=check)
                        try: count = sock.send(view[:65536])
                        except BlockingIOError: continue
                        if not count: raise RendererTransportLost()
                        view = view[count:]

                def receive(size):
                    while True:
                        self._ready(sock, write=False, check=check)
                        try: return sock.recv(size)
                        except BlockingIOError: continue

                pending = bytearray()
                while b'\r\n\r\n' not in pending:
                    if len(pending) >= MAX_HEADER_BYTES: c.fail('renderer_resource_limit')
                    data = receive(min(4096, MAX_HEADER_BYTES - len(pending)))
                    if not data: raise RendererTransportLost()
                    pending.extend(data)
                end = pending.index(b'\r\n\r\n')
                lines = bytes(pending[:end]).split(b'\r\n')
                match = re.fullmatch(br'HTTP/1\.1 ([0-9]{3})(?: [\x20-\x7e]*)?', lines[0])
                if not match or not 200 <= int(match[1]) <= 599 or 300 <= int(match[1]) < 400: c.fail()
                status = int(match[1]); fields = {}
                for line in lines[1:]:
                    try: name, value = DocumentHTTPTransport._header(line + b'\r\n')
                    except c.DocumentWorkshopError: c.fail()
                    if name in fields: c.fail()
                    fields[name] = value
                if b'transfer-encoding' in fields or fields.get(b'content-encoding', b'identity') != b'identity': c.fail()
                raw = fields.get(b'content-length', b'')
                if re.fullmatch(br'0|[1-9][0-9]{0,8}', raw) is None: c.fail()
                size = int(raw); c.check_size(size, limit)
                media = fields.get(b'content-type', b'').decode('ascii')
                received = pending[end+4:]
                while True:
                    if len(received) > size: c.fail()
                    # One byte beyond the declared body detects surplus data;
                    # EOF is mandatory, including for an exactly sized body.
                    data = receive(min(65536, size - len(received) + 1))
                    if not data:
                        if len(received) != size: raise RendererTransportLost()
                        check()
                        return c.WireMessage(media, bytes(received), status)
                    received.extend(data)
        except OSError:
            raise RendererTransportLost() from None
        except UnicodeError:
            c.fail()

    @staticmethod
    def _job_path(request):
        if type(request) is not c.RenderRequest: c.fail('renderer_input_invalid')
        return '/v1/jobs/' + c.identifier(request.data['job_id'])

    def capabilities(self, *, check):
        return self._exchange('GET', '/v1/capabilities', limit=c.MAX_JSON_BYTES, check=check)

    def submit(self, request, *, check):
        self._job_path(request)
        wire = request.wire
        return self._exchange('POST', '/v1/jobs', body=wire.body, content_type=wire.content_type,
            limit=c.MAX_JSON_BYTES, check=check)

    def status(self, request, *, check):
        return self._exchange('GET', self._job_path(request), identity=request.identity, limit=c.MAX_JSON_BYTES, check=check)

    def result(self, request, *, check):
        return self._exchange('GET', self._job_path(request) + '/result', identity=request.identity, limit=c.MAX_RESULT_BYTES, check=check)

    def cancel_release(self, request, *, cancel=False, check):
        wire = c.delete_message(request, cancel=cancel)
        return self._exchange('DELETE', self._job_path(request), body=wire.body, content_type=wire.content_type,
            identity=request.identity, limit=c.MAX_JSON_BYTES, check=check)
