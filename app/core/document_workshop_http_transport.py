"""One owned HTTP/1.1 documentary exchange, with interruptible socket I/O.

M0 owns admission, inactivity and provider semantics. This adapter sends its
frozen bytes once and only bounds/decodes the HTTP response. It never retries,
redirects, decompresses or retains an upstream error message.
"""
from __future__ import annotations

import asyncio
import codecs
import re
import ssl
from typing import AsyncIterator
from urllib.parse import urlsplit

from .document_canonical import strict_json_loads
from .document_workshop_admission import PreparedDocumentCall
from .document_workshop_contract import DocumentWorkshopError, PREPARATION_INACTIVITY_SECONDS

# Network bounds leave room for the canonical, envelope and provider framing.
# They neither replace the content limits nor truncate a valid response.
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_HEADER_BYTES = 64 * 1024
_READ_BYTES = 64 * 1024
_TOKEN = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_STATUS = re.compile(rb"HTTP/1\.[01] ([0-9]{3})(?: [\x20-\x7e]*)?\r\n\Z")
_CHUNK_SIZE = re.compile(rb"[0-9A-Fa-f]+\Z")


def _invalid() -> None:
    raise DocumentWorkshopError("document_provider_protocol_invalid")


class DocumentHTTPTransport:
    """Request-local transport; constructed inside the owning asyncio loop."""

    def __init__(self):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connect_task: asyncio.Task | None = None
        self._started = False
        self._closed = False
        self._body_started = False
        self._headers: dict[bytes, bytes] | None = None
        self._remaining: int | None = None
        self._chunked = False
        self._response_bytes = 0

    def _check(self) -> None:
        if self._closed:
            raise DocumentWorkshopError("document_transport_closed")

    def close(self) -> None:
        """Abort now, including blocked headers/body or an unfinished connect."""
        self._closed = True
        if self._connect_task is not None:
            if not self._connect_task.done():
                self._connect_task.cancel()
            elif not self._connect_task.cancelled():
                try:
                    _, writer = self._connect_task.result()
                    writer.transport.abort()
                except Exception:
                    pass
        if self._writer is not None:
            self._writer.transport.abort()

    async def wait_closed(self) -> None:
        """Drain cancellation/connection cleanup after synchronous abort."""
        if self._connect_task is not None:
            await asyncio.gather(self._connect_task, return_exceptions=True)
        if self._writer is not None:
            try:
                await self._writer.wait_closed()
            except Exception:
                pass

    @staticmethod
    def _request(prepared: PreparedDocumentCall):
        if type(prepared.body) is not bytes or type(prepared.url) is not str:
            _invalid()
        if any(ord(char) <= 32 or ord(char) == 127 for char in prepared.url):
            _invalid()
        parts = urlsplit(prepared.url)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None or parts.fragment):
            _invalid()
        port = parts.port or (443 if parts.scheme == "https" else 80)
        hostname = parts.hostname.encode("idna").decode("ascii")
        authority = ("[" + hostname + "]") if ":" in hostname else hostname
        if parts.port is not None:
            authority += ":" + str(port)
        target = parts.path or "/"
        if parts.query:
            target += "?" + parts.query
        request = ["POST " + target + " HTTP/1.1", "Host: " + authority,
                   "Content-Length: " + str(len(prepared.body)), "Connection: close",
                   "Accept-Encoding: identity"]
        names = {"host", "content-length", "connection", "accept-encoding", "transfer-encoding"}
        for name, value in prepared.headers:
            if type(name) is not str or type(value) is not str:
                _invalid()
            encoded_name = name.encode("ascii")
            if (not _TOKEN.fullmatch(encoded_name) or name.lower() in names
                    or any(ord(char) < 32 or ord(char) == 127 for char in value)):
                _invalid()
            names.add(name.lower())
            request.append(name + ": " + value)
        head = ("\r\n".join(request) + "\r\n\r\n").encode("latin-1")
        if len(head) > MAX_HEADER_BYTES:
            raise DocumentWorkshopError("document_provider_network_limit")
        return hostname, port, parts.scheme == "https", head

    async def send(self, prepared: PreparedDocumentCall) -> int:
        self._check()
        if self._started:
            _invalid()
        self._started = True
        try:
            hostname, port, secure, head = self._request(prepared)
            context = ssl.create_default_context() if secure else None
            if context is not None:
                context.set_alpn_protocols(["http/1.1"])
            self._connect_task = asyncio.create_task(asyncio.open_connection(
                hostname, port, ssl=context, server_hostname=hostname if secure else None,
                # Align the TLS-only technical alarm with M0; its independent
                # watchdog may abort earlier from the last useful progress.
                ssl_handshake_timeout=PREPARATION_INACTIVITY_SECONDS if secure else None,
                limit=MAX_HEADER_BYTES))
            try:
                self._reader, self._writer = await self._connect_task
            finally:
                self._connect_task = None
            self._check()
            self._writer.write(head)
            self._writer.write(prepared.body)
            await self._writer.drain()
            self._check()
            status, self._headers = await self._read_headers()
            self._set_framing()
            return status
        except asyncio.CancelledError:
            self.close()
            raise
        except DocumentWorkshopError:
            self.close()
            raise
        except Exception:
            self.close()
            raise DocumentWorkshopError("document_provider_error") from None

    async def _readline(self) -> bytes:
        self._check()
        try:
            line = await self._reader.readuntil(b"\r\n")
        except asyncio.LimitOverrunError:
            raise DocumentWorkshopError("document_provider_network_limit") from None
        except asyncio.IncompleteReadError:
            self._check()
            _invalid()
        self._check()
        self._account(len(line))
        if len(line) > MAX_HEADER_BYTES:
            raise DocumentWorkshopError("document_provider_network_limit")
        return line

    def _account(self, size: int) -> None:
        # Account for response status/headers, chunk extensions/terminators and
        # trailers as well as content: framing cannot evade the network bound.
        self._response_bytes += size
        if self._response_bytes > MAX_RESPONSE_BYTES:
            raise DocumentWorkshopError("document_provider_network_limit")

    @staticmethod
    def _header(line: bytes) -> tuple[bytes, bytes]:
        if b":" not in line or line[:1] in {b" ", b"\t"}:
            _invalid()
        name, value = line[:-2].split(b":", 1)
        if (not _TOKEN.fullmatch(name)
                or any(char < 32 and char != 9 or char == 127 for char in value)):
            _invalid()
        return name.lower(), value.strip(b" \t")

    async def _read_headers(self) -> tuple[int, dict[bytes, bytes]]:
        status_line = await self._readline()
        match = _STATUS.fullmatch(status_line)
        if match is None or not 200 <= int(match[1]) <= 599:
            _invalid()
        total = len(status_line)
        headers = {}
        while True:
            line = await self._readline()
            total += len(line)
            if total > MAX_HEADER_BYTES:
                raise DocumentWorkshopError("document_provider_network_limit")
            if line == b"\r\n":
                return int(match[1]), headers
            name, value = self._header(line)
            if name in headers:
                # Non-framing duplicate fields (e.g. Set-Cookie) are irrelevant;
                # framing/type duplication cannot silently choose one authority.
                if name in {b"content-length", b"transfer-encoding", b"content-encoding", b"content-type"}:
                    _invalid()
            else:
                headers[name] = value

    def _set_framing(self) -> None:
        headers = self._headers
        if headers.get(b"content-encoding", b"identity").lower() != b"identity":
            _invalid()
        transfer = headers.get(b"transfer-encoding")
        length = headers.get(b"content-length")
        if transfer is not None:
            if transfer.lower() != b"chunked" or length is not None:
                _invalid()
            self._chunked = True
        elif length is not None:
            if not length or not length.isdigit():
                _invalid()
            self._remaining = int(length)
            if self._remaining > MAX_RESPONSE_BYTES:
                raise DocumentWorkshopError("document_provider_network_limit")

    async def _read(self, size: int) -> bytes:
        self._check()
        data = await self._reader.read(size)
        self._check()
        self._account(len(data))
        return data

    async def _exactly(self, size: int) -> bytes:
        self._check()
        try:
            data = await self._reader.readexactly(size)
        except asyncio.IncompleteReadError:
            self._check()
            _invalid()
        self._check()
        self._account(len(data))
        return data

    async def _body(self, content_type: bytes) -> AsyncIterator[bytes]:
        self._check()
        if self._headers is None or self._body_started:
            _invalid()
        self._body_started = True
        if self._headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower() != content_type:
            _invalid()
        received = 0
        try:
            while True:
                if self._chunked:
                    line = await self._readline()
                    size_text, *extensions = line[:-2].split(b";", 1)
                    if not _CHUNK_SIZE.fullmatch(size_text) or any(c < 32 or c > 126 for c in b"".join(extensions)):
                        _invalid()
                    size = int(size_text, 16)
                    if size == 0:
                        trailer_bytes = 0
                        while True:
                            trailer = await self._readline()
                            trailer_bytes += len(trailer)
                            if trailer_bytes > MAX_HEADER_BYTES:
                                raise DocumentWorkshopError("document_provider_network_limit")
                            if trailer == b"\r\n":
                                return
                            name, _ = self._header(trailer)
                            if name in {b"content-length", b"transfer-encoding", b"content-encoding", b"content-type"}:
                                _invalid()
                    if received + size > MAX_RESPONSE_BYTES:
                        raise DocumentWorkshopError("document_provider_network_limit")
                    remaining = size
                    while remaining:
                        data = await self._exactly(min(remaining, _READ_BYTES))
                        remaining -= len(data)
                        received += len(data)
                        yield data
                    if await self._exactly(2) != b"\r\n":
                        _invalid()
                else:
                    if self._remaining == 0:
                        return
                    allowance = MAX_RESPONSE_BYTES - self._response_bytes + 1
                    size = min(_READ_BYTES, allowance)
                    if self._remaining is not None:
                        size = min(size, self._remaining)
                    data = await self._read(size)
                    if not data:
                        if self._remaining is not None:
                            _invalid()
                        return
                    received += len(data)
                    if received > MAX_RESPONSE_BYTES:
                        raise DocumentWorkshopError("document_provider_network_limit")
                    if self._remaining is not None:
                        self._remaining -= len(data)
                    yield data
        except asyncio.CancelledError:
            self.close()
            raise
        except DocumentWorkshopError:
            self.close()
            raise
        except Exception:
            self.close()
            raise DocumentWorkshopError("document_provider_error") from None

    async def read_json(self) -> object:
        try:
            parts = [part async for part in self._body(b"application/json")]
            self._check()
            return strict_json_loads(b"".join(parts).decode("utf-8", errors="strict"))
        except (UnicodeError, DocumentWorkshopError) as error:
            self.close()
            if isinstance(error, DocumentWorkshopError) and error.reason_code != "document_canonical_invalid":
                raise
            raise DocumentWorkshopError("document_provider_protocol_invalid") from None

    async def iter_lines(self) -> AsyncIterator[str]:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        pending = ""
        try:
            async for part in self._body(b"text/event-stream"):
                pending += decoder.decode(part)
                while True:
                    match = re.search(r"[\r\n]", pending)
                    if match is None or (match[0] == "\r" and match.end() == len(pending)):
                        break
                    end = match.end()
                    if pending[match.start():end + 1] == "\r\n":
                        end += 1
                    yield pending[:match.start()]
                    pending = pending[end:]
            pending += decoder.decode(b"", final=True)
            self._check()
            if pending.endswith("\r"):
                yield pending[:-1]
            elif pending:
                yield pending
        except UnicodeError:
            self.close()
            raise DocumentWorkshopError("document_provider_protocol_invalid") from None
        except DocumentWorkshopError:
            self.close()
            raise
