"""Inactive M5 DAV mutations for one confirmed, server-resolved execution.

Configuration is explicit. M0 owns paths, M2 owns scope and conditional reads.
The executor owns durable intents/fencing before every individual HTTP effect.
This client never updates, retries, follows redirects or deletes collections.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import http.client
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request

from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_nextcloud_read_client import (
    MAX_DAV_XML_BYTES, MAX_SOURCE_BYTES, NextcloudDocumentReadClient, RemoteResource,
)
from .workspace_document_paths import (
    DocumentTargetPath, validate_document_collection_path, validate_document_path,
)
from .workspace_nextcloud_etag import validated_strong_etag

_MEDIA_TYPES = {
    "markdown": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}
# A redirect can describe the result of an operation already processed. Not
# following it prevents another request, but cannot prove the first had no effect.
_REJECTED_STATUSES = {400, 401, 403, 404, 405, 409, 412, 423}


@dataclass(frozen=True, repr=False)
class CreatedDocumentResult:
    state: str
    reason_code: str
    http_status: int = 0
    resource: RemoteResource | None = None
    creation_etag: str = ""
    created_collections: tuple[str, ...] = ()

    @property
    def ok(self):
        return self.state == "known_success"


@dataclass(frozen=True, repr=False)
class CompensationResult:
    state: str
    reason_code: str
    http_status: int = 0

    @property
    def ok(self):
        return self.state == "absence_certain"


class _UnknownMutation(Exception):
    def __init__(self, http_status):
        self.http_status = http_status


def _fail(reason):
    raise DocumentWorkshopError(reason)


def _target(value, format):
    if type(value) is not DocumentTargetPath:
        _fail("document_path_invalid")
    verified = validate_document_path(value.relative_path, format=format)
    if verified != value:
        _fail("document_path_invalid")
    return verified


def _ancestors(target):
    return tuple("/".join(target.segments[:index]) for index in range(2, len(target.segments)))


def _collision_key(path):
    return unicodedata.normalize("NFC", path).casefold()


def _authorize(callback, method, relative_path):
    try:
        accepted = callback(method, relative_path)
    except DocumentWorkshopError:
        raise
    except Exception:
        _fail("document_mutation_not_authorized")
    if accepted is not True:
        _fail("document_mutation_not_authorized")


class NextcloudDocumentMutationClient:
    """Explicitly injected per execution; never a default runtime capability."""

    def __init__(self, config, *, opener=None):
        if config is None:
            _fail("document_remote_unavailable")
        self._reader = NextcloudDocumentReadClient(config, opener=opener)
        self._creation_proof = None

    def scope_key(self, folder_name):
        return self._reader.scope_key(folder_name)

    def _stat_collection(self, folder_name, relative_path):
        path = validate_document_collection_path(relative_path)
        body, _ = self._reader._request("PROPFIND", self._reader._url(folder_name, path),
                                        headers={"Depth": "0"}, max_bytes=MAX_DAV_XML_BYTES)
        resource, _ = self._reader._parse(body, folder_name, path, 0)
        if not resource.is_collection or not resource.file_id:
            _fail("document_remote_incompatible")
        return resource

    def _children(self, folder_name, parent):
        _, children = self._reader.list_collection(folder_name, parent.relative_path,
                                                   expected_file_id=parent.file_id)
        return children

    @staticmethod
    def _matching_child(children, path):
        matches = [child for child in children if _collision_key(child.relative_path) == _collision_key(path)]
        if len(matches) > 1 or (matches and matches[0].relative_path != path):
            _fail("document_target_collision")
        return matches[0] if matches else None

    def _file_absent(self, folder_name, target, parent):
        if self._matching_child(self._children(folder_name, parent), target.relative_path) is not None:
            _fail("document_target_collision")
        try:
            self._reader.stat_resource(folder_name, target.relative_path)
        except DocumentWorkshopError as exc:
            if exc.reason_code == "document_remote_missing":
                return
            raise
        _fail("document_target_collision")

    def inspect_create_target(self, folder_name, target, *, format="markdown"):
        target = _target(target, format)
        # A linked mapping alone cannot establish an absent parent outside
        # Documents. Its existing root is always verified, never created here.
        parent = self._stat_collection(folder_name, "Documents")
        ancestors = _ancestors(target)
        for index, path in enumerate(ancestors):
            child = self._matching_child(self._children(folder_name, parent), path)
            if child is None:
                return ancestors[index:]
            if not child.is_collection or not child.file_id:
                _fail("document_target_collision")
            parent = self._stat_collection(folder_name, path)
            if parent.file_id != child.file_id:
                _fail("document_remote_changed")
        self._file_absent(folder_name, target, parent)
        return ()

    def _mutation_request(self, method, folder_name, path, *, data=None, headers=None):
        request = Request(self._reader._url(folder_name, path), data=data, method=method)
        config = self._reader.config
        credentials = f"{config.username}:{config.app_password}".encode()
        request.add_header("Authorization", "Basic " + base64.b64encode(credentials).decode("ascii"))
        request.add_header("Accept-Encoding", "identity")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with self._reader._opener.open(request, timeout=12) as response:
                return int(response.status), response.headers
        except HTTPError as exc:
            status, response_headers = int(exc.code), exc.headers
            exc.close()
            return status, response_headers
        except (OSError, URLError, http.client.HTTPException, ValueError):
            raise _UnknownMutation(0) from None

    def _create_collection(self, folder_name, relative_path, callback, created):
        path = validate_document_collection_path(relative_path)
        parent_path = "/".join(path.segments[:-1])
        parent = self._stat_collection(folder_name, parent_path)
        listed = self._matching_child(self._children(folder_name, parent), relative_path)
        if listed is not None and (not listed.is_collection or not listed.file_id):
            _fail("document_target_collision")
        try:
            existing = self._stat_collection(folder_name, relative_path)
        except DocumentWorkshopError as exc:
            if exc.reason_code != "document_remote_missing":
                raise
            existing = None
        if listed is not None:
            if existing is None or existing.file_id != listed.file_id:
                _fail("document_remote_changed")
            return
        if existing is not None:
            _fail("document_remote_changed")
        _authorize(callback, "MKCOL", relative_path)
        status, _ = self._mutation_request("MKCOL", folder_name, path)
        if status != 201:
            if status not in _REJECTED_STATUSES:
                raise _UnknownMutation(status)
            _fail("document_collection_conflict")
        created.append(relative_path)
        self._stat_collection(folder_name, relative_path)

    def create_document(self, folder_name, target, content, *, format="markdown",
                        confirmed_collections, before_mutation):
        target = _target(target, format)
        if type(content) is not bytes or not 0 < len(content) <= MAX_SOURCE_BYTES:
            _fail("document_output_invalid")
        if (type(confirmed_collections) is not tuple or confirmed_collections != _ancestors(target)
                or not callable(before_mutation)):
            _fail("document_mutation_not_authorized")
        created, status, etag = [], 0, ""
        try:
            missing = self.inspect_create_target(folder_name, target, format=format)
            for path in missing:
                self._create_collection(folder_name, path, before_mutation, created)
            if missing:
                parent = self._stat_collection(folder_name, "/".join(target.segments[:-1]))
                self._file_absent(folder_name, target, parent)
            _authorize(before_mutation, "PUT", target.relative_path)
            status, headers = self._mutation_request("PUT", folder_name, target, data=content,
                                                     headers={"If-None-Match": "*", "Content-Type": _MEDIA_TYPES[format]})
            if status != 201:
                if status not in _REJECTED_STATUSES:
                    raise _UnknownMutation(status)
                _fail("document_target_collision" if status in {405, 409, 412, 423} else "document_remote_unavailable")
            etags = headers.get_all("ETag", [])
            etag = validated_strong_etag(etags[0]) if len(etags) == 1 else ""
            if not etag:
                raise _UnknownMutation(status)
            resource = self._reader.stat_resource(folder_name, target.relative_path, expected_etag=etag)
            if resource.byte_size != len(content):
                _fail("document_remote_changed")
            if self._reader.read_file(folder_name, resource) != content:
                _fail("document_remote_changed")
        except _UnknownMutation as exc:
            return CreatedDocumentResult("remote_uncertain", "document_remote_mutation_uncertain",
                                          exc.http_status, None, etag, tuple(created))
        except DocumentWorkshopError as exc:
            return CreatedDocumentResult("remote_uncertain" if status == 201 else "known_failure",
                                          exc.reason_code, status, None, etag, tuple(created))
        result = CreatedDocumentResult("known_success", "document_remote_created", status, resource, etag, tuple(created))
        # The original instance alone grants immediate compensation authority.
        # It is never reconstructed from a journal, URL or later observation.
        self._creation_proof = (result, folder_name, target)
        return result

    def compensate_created_document(self, folder_name, target, created, *, before_mutation, format="markdown"):
        target = _target(target, format)
        proof = self._creation_proof
        if (proof is None or proof[0] is not created or proof[1:] != (folder_name, target)
                or not callable(before_mutation) or not created.ok or created.resource is None
                or not validated_strong_etag(created.creation_etag)
                or created.resource.relative_path != target.relative_path
                or created.resource.etag != created.creation_etag):
            return CompensationResult("preserved", "document_compensation_ownership_unverified")
        # No repeated compensation, including after a lost DELETE response.
        self._creation_proof = None
        try:
            current = self._reader.stat_resource(folder_name, target.relative_path, expected_etag=created.creation_etag)
        except DocumentWorkshopError as exc:
            if exc.reason_code == "document_remote_missing":
                return CompensationResult("absence_certain", "document_compensation_missing", 404)
            return CompensationResult("preserved", exc.reason_code)
        if current != created.resource:
            return CompensationResult("preserved", "document_remote_changed")
        try:
            _authorize(before_mutation, "DELETE", target.relative_path)
        except DocumentWorkshopError as exc:
            return CompensationResult("preserved", exc.reason_code)
        try:
            status, _ = self._mutation_request("DELETE", folder_name, target,
                                              headers={"If-Match": created.creation_etag})
        except _UnknownMutation as exc:
            return CompensationResult("remote_uncertain", "document_compensation_uncertain", exc.http_status)
        if status in {204, 404}:
            return CompensationResult("absence_certain", "document_compensation_absent", status)
        if status == 412:
            return CompensationResult("preserved", "document_remote_changed", status)
        return CompensationResult("remote_uncertain", "document_compensation_uncertain", status)
