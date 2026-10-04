"""Bounded, read-only DAV boundary for explicitly opened Documents resources.

Only server mappings build request URLs. Returned hrefs are scope evidence,
never download instructions. Missing proofs remain incompatible metadata.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import http.client
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote_to_bytes, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from xml.etree import ElementTree

from . import workspace_folder_nextcloud_client as folder_client
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import (
    _validate_document_relative_path, _validate_segment,
    validate_document_collection_path, validate_document_source_path,
)
from .workspace_nextcloud_etag import validated_strong_etag

MAX_DAV_XML_BYTES = 1024 * 1024
MAX_COLLECTION_CHILDREN = 256
MAX_SOURCE_BYTES = 40 * 1024 * 1024
DAV = "{DAV:}"
OC = "{http://owncloud.org/ns}"
_PROPFIND = (b'<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:prop>'
             b'<d:resourcetype/><oc:fileid/><d:getetag/><d:getcontentlength/>'
             b'<d:getcontenttype/></d:prop></d:propfind>')


@dataclass(frozen=True, repr=False)
class RemoteResource:
    relative_path: str
    is_collection: bool
    file_id: str
    etag: str
    byte_size: int | None
    media_type: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fail(reason="document_remote_incompatible"):
    raise DocumentWorkshopError(reason)


def _origin(parts):
    try:
        if (parts.scheme not in {"http", "https"} or not parts.hostname or
                parts.username is not None or parts.password is not None):
            _fail()
        return parts.scheme, parts.hostname.lower(), parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        _fail()


def _path_segments(path):
    if not path.startswith("/") or "//" in path:
        _fail()
    pieces = path.removesuffix("/").split("/")[1:]
    result = []
    for raw in pieces:
        if re.search(r"%(?![0-9a-fA-F]{2})", raw):
            _fail()
        try:
            value = unquote_to_bytes(raw).decode("utf-8", errors="strict")
            result.append(_validate_segment(value))
        except (UnicodeError, DocumentWorkshopError):
            _fail()
    return tuple(result)


def _one(parent, tag, *, required=True):
    matches = parent.findall(tag)
    if len(matches) > 1 or (required and not matches):
        _fail()
    return matches[0] if matches else None


def _text(node):
    if node is None:
        return ""
    if len(node):
        _fail()
    return node.text or ""


def _usable(resource):
    return (not resource.is_collection and bool(re.fullmatch(r"[0-9]{1,64}", resource.file_id))
            and bool(validated_strong_etag(resource.etag)) and type(resource.byte_size) is int
            and 0 < resource.byte_size <= MAX_SOURCE_BYTES)


class NextcloudDocumentReadClient:
    def __init__(self, config=None, *, opener=None):
        if config is None:
            try:
                config = folder_client.config_from_env()
            except folder_client.NextcloudFolderClientError:
                _fail("document_remote_unavailable")
        self.config = config
        self._base = urlsplit(config.base_url)
        self._origin = _origin(self._base)
        if self._base.query or self._base.fragment:
            _fail()
        self._base_segments = _path_segments(self._base.path) if self._base.path.rstrip("/") else ()
        _validate_segment(config.username)
        _validate_segment(config.root_name)
        self._opener = opener or build_opener(ProxyHandler({}), _NoRedirect())

    @classmethod
    def from_env(cls, environ=None):
        try:
            return cls(folder_client.config_from_env(environ))
        except folder_client.NextcloudFolderClientError:
            _fail("document_remote_unavailable")

    def _root(self, folder_name):
        return (*self._base_segments, "remote.php", "dav", "files", self.config.username,
                self.config.root_name, _validate_segment(folder_name))

    def scope_key(self, folder_name):
        parts = (self._origin, self._root(folder_name))
        return hashlib.sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def _url(self, folder_name, path):
        suffix = "/".join(quote(segment, safe="") for segment in (*self._root(folder_name), *path.segments))
        return f"{self._base.scheme}://{self._base.netloc}/{suffix}"

    def _request(self, method, url, *, headers, max_bytes):
        data = _PROPFIND if method == "PROPFIND" else None
        request = Request(url, data=data, method=method)
        credentials = f"{self.config.username}:{self.config.app_password}".encode()
        request.add_header("Authorization", "Basic " + base64.b64encode(credentials).decode("ascii"))
        request.add_header("Accept-Encoding", "identity")
        if data:
            request.add_header("Content-Type", "application/xml; charset=utf-8")
        for key, value in headers.items():
            request.add_header(key, value)
        try:
            with self._opener.open(request, timeout=12) as response:
                status = int(response.status)
                if status != (207 if method == "PROPFIND" else 200):
                    self._status_error(status)
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    _fail()
                lengths = response.headers.get_all("Content-Length", [])
                if len(lengths) > 1 or (lengths and not re.fullmatch(r"[0-9]{1,12}", lengths[0])):
                    _fail()
                chunks, consumed = [], 0
                while consumed <= max_bytes:
                    chunk = response.read(min(65536, max_bytes + 1 - consumed))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    consumed += len(chunk)
                if consumed > max_bytes:
                    _fail("document_remote_response_limit")
                if lengths and int(lengths[0]) != consumed:
                    _fail()
                return b"".join(chunks), response.headers
        except HTTPError as exc:
            status = exc.code
            exc.close()
            self._status_error(status)
        except DocumentWorkshopError:
            raise
        except (OSError, URLError, http.client.HTTPException, ValueError):
            raise DocumentWorkshopError("document_remote_unavailable") from None

    @staticmethod
    def _status_error(status):
        if status == 404:
            _fail("document_remote_missing")
        if status == 412:
            _fail("document_remote_changed")
        _fail("document_remote_unavailable")

    def _parse(self, body, folder_name, path, depth):
        if any(value < 32 and value not in (9, 10, 13) for value in body):
            _fail()
        if re.search(br"<!\s*(DOCTYPE|ENTITY)\b", body, re.IGNORECASE):
            _fail()
        try:
            root = ElementTree.fromstring(body)
        except (ElementTree.ParseError, ValueError):
            _fail()
        if root.tag != DAV + "multistatus" or any(node.tag != DAV + "response" for node in root):
            _fail()
        if len(root) > (MAX_COLLECTION_CHILDREN + 1 if depth else 1):
            _fail("document_remote_response_limit")
        expected = (*self._root(folder_name), *path.segments)
        resources, identities = {}, set()
        for response in root:
            href = _text(_one(response, DAV + "href"))
            if href != href.strip() or "?" in href or "#" in href or any(ord(char) < 32 for char in href):
                _fail()
            try:
                target = urlsplit(href)
            except ValueError:
                _fail()
            if target.query or target.fragment or (target.netloc and _origin(target) != self._origin):
                _fail()
            if target.scheme and _origin(target) != self._origin:
                _fail()
            segments = _path_segments(target.path)
            is_self = segments == expected
            if not is_self and not (depth == 1 and segments[:-1] == expected):
                _fail()
            props = {}
            for propstat in response.findall(DAV + "propstat"):
                status = _text(_one(propstat, DAV + "status"))
                if not re.fullmatch(r"HTTP/1\.[01] [1-5][0-9]{2}(?: [^\r\n]*)?", status):
                    _fail()
                prop = _one(propstat, DAV + "prop")
                if status.split(" ")[1] != "200":
                    continue
                for node in prop:
                    if node.tag in props:
                        _fail()
                    props[node.tag] = node
            resource_type = props.get(DAV + "resourcetype")
            collection = resource_type is not None and resource_type.find(DAV + "collection") is not None
            relative = "/".join(segments[len(self._root(folder_name)):])
            _validate_document_relative_path(relative, is_collection=collection)
            if is_self and depth and not collection:
                _fail()
            file_id = _text(props.get(OC + "fileid"))
            file_id = file_id if re.fullmatch(r"[0-9]{1,64}", file_id) else ""
            etag = validated_strong_etag(_text(props.get(DAV + "getetag")))
            size = _text(props.get(DAV + "getcontentlength"))
            byte_size = int(size) if re.fullmatch(r"[0-9]{1,12}", size) else None
            if resource_type is None:
                file_id, etag, byte_size = "", "", None
            media_type = _text(props.get(DAV + "getcontenttype"))
            if len(media_type) > 255 or any(ord(char) < 32 for char in media_type):
                _fail()
            if relative in resources or (file_id and file_id in identities):
                _fail()
            if file_id:
                identities.add(file_id)
            resources[relative] = RemoteResource(relative, collection, file_id, etag, byte_size, media_type)
        self_resource = resources.pop(path.relative_path, None)
        if self_resource is None:
            _fail()
        return self_resource, tuple(resources.values())

    def list_collection(self, folder_name, relative_path="Documents", expected_file_id=None):
        path = validate_document_collection_path(relative_path)
        body, _ = self._request("PROPFIND", self._url(folder_name, path), headers={"Depth": "1"}, max_bytes=MAX_DAV_XML_BYTES)
        resource, children = self._parse(body, folder_name, path, 1)
        if expected_file_id is not None and (not expected_file_id or resource.file_id != expected_file_id):
            _fail("document_remote_changed")
        return resource, children

    def stat_resource(self, folder_name, relative_path, expected_etag=None):
        path = validate_document_source_path(relative_path)
        headers = {"Depth": "0"}
        if expected_etag is not None:
            if not validated_strong_etag(expected_etag):
                _fail()
            headers["If-Match"] = expected_etag
        body, _ = self._request("PROPFIND", self._url(folder_name, path), headers=headers, max_bytes=MAX_DAV_XML_BYTES)
        resource, _ = self._parse(body, folder_name, path, 0)
        if not _usable(resource):
            _fail()
        if expected_etag is not None and resource.etag != expected_etag:
            _fail("document_remote_changed")
        return resource

    def read_file(self, folder_name, resource):
        path = validate_document_source_path(resource.relative_path)
        if not _usable(resource):
            _fail()
        before = self.stat_resource(folder_name, resource.relative_path, expected_etag=resource.etag)
        if before != resource:
            _fail("document_remote_changed")
        body, headers = self._request("GET", self._url(folder_name, path), headers={"If-Match": resource.etag},
                                      max_bytes=resource.byte_size)
        if headers.get_all("ETag", []) != [resource.etag] or len(body) != resource.byte_size:
            _fail("document_remote_changed")
        after = self.stat_resource(folder_name, resource.relative_path, expected_etag=resource.etag)
        if after != resource:
            _fail("document_remote_changed")
        return body
