"""M5 mutations on a synthetic loopback DAV peer, never an operator service."""
from contextlib import contextmanager
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import socket
import threading
import unittest
from unittest.mock import patch
from urllib.parse import quote

from core.document_workshop_contract import DocumentWorkshopError
from core.workspace_document_paths import DocumentTargetPath, validate_document_path
from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
from tests.unit.core.test_workspace_document_read_client_m2 import resource, multistatus, PREFIX


CONTENT = b"# Synthetic document\n"
CREATION_ETAG = '"created-v1"'


def collection_xml(path="Documents", *, file_id="1", **kwargs):
    return multistatus(resource(path, file_id=file_id, **kwargs))


def file_xml(path="Documents/X.md", *, content=CONTENT, file_id="2", etag=CREATION_ETAG, **kwargs):
    return multistatus(resource(path, collection=False, file_id=file_id, etag=etag,
                                size=len(content), href=PREFIX + quote(path, safe="/"), **kwargs))


def creation_responses(path="Documents/X.md", content=CONTENT, *, etag=CREATION_ETAG):
    """Exact no-subcollection success sequence shared by SQL/HTTP integration."""
    root, file = collection_xml(), file_xml(path, content=content, etag=etag)
    return [(207, {}, root), (207, {}, root), (404, {}, b""),
            (201, {"ETag": etag}, b""), (207, {}, file), (207, {}, file),
            (200, {"ETag": etag, "Content-Length": str(len(content))}, content), (207, {}, file)]


@contextmanager
def dav_server(responses):
    """Record the received body/headers; 'drop' loses a reply after receipt."""
    observed = []

    class Handler(BaseHTTPRequestHandler):
        do_PROPFIND = do_GET = do_MKCOL = do_PUT = do_DELETE = lambda self: self.reply()

        def log_message(self, *_):
            pass

        def reply(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            observed.append((self.command, self.path, dict(self.headers), body))
            reply = responses.pop(0) if responses else (500, {}, b"")
            if reply == "drop":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            status, headers, content = reply
            self.send_response(status)
            for key, value in (headers.items() if isinstance(headers, dict) else headers):
                self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", observed
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class DocumentMutationClientM5Tests(unittest.TestCase):
    def setUp(self):
        name = "core.workspace_document_nextcloud_mutation_client"
        self.assertIsNotNone(importlib.util.find_spec(name), "M5 bounded mutator absent")
        self.module = __import__(name, fromlist=["NextcloudDocumentMutationClient"])
        self.authorized = []

    def client(self, base):
        return self.module.NextcloudDocumentMutationClient(NextcloudFolderClientConfig(base, "test", "synthetic"))

    def authorize(self, method, path):
        self.authorized.append((method, path))
        return True

    def create(self, client, path="Documents/X.md", content=CONTENT, **kwargs):
        format = kwargs.pop("format", "markdown")
        target = validate_document_path(path, format=format)
        collections = tuple("/".join(target.segments[:i]) for i in range(2, len(target.segments)))
        return client.create_document("Scope", target, content, format=format, confirmed_collections=collections,
                                      before_mutation=self.authorize, **kwargs)

    @staticmethod
    def mutations(seen):
        return [request for request in seen if request[0] in {"MKCOL", "PUT", "DELETE"}]

    def test_create_exact_bytes_conditional_headers_and_version_identity_checks(self):
        with dav_server(creation_responses()) as (base, seen):
            result = self.create(self.client(base))
        self.assertEqual(result.state, "known_success")
        self.assertTrue(result.ok)
        self.assertEqual(result.creation_etag, CREATION_ETAG)
        self.assertEqual((result.resource.file_id, result.resource.byte_size), ("2", len(CONTENT)))
        self.assertEqual(result.created_collections, ())
        self.assertEqual(self.authorized, [("PUT", "Documents/X.md")])
        self.assertEqual([x[0] for x in seen], ["PROPFIND", "PROPFIND", "PROPFIND", "PUT",
                                                "PROPFIND", "PROPFIND", "GET", "PROPFIND"])
        put = self.mutations(seen)[0]
        self.assertEqual(put[1], PREFIX + "Documents/X.md")
        self.assertEqual(put[2]["If-None-Match"], "*")
        self.assertEqual(put[2]["Content-Type"], "text/markdown; charset=utf-8")
        self.assertEqual(put[3], CONTENT)
        self.assertTrue(all(x[2]["If-Match"] == CREATION_ETAG for x in seen[4:]))
        self.assertNotIn("Documents", repr(result))
        with self.assertRaises((AttributeError, TypeError)):
            result.state = "changed"

    def test_unicode_filename_encoded_per_segment_without_normalization(self):
        path = "Documents/e\u0301tude finale.md"
        with dav_server(creation_responses(path)) as (base, seen):
            self.assertTrue(self.create(self.client(base), path).ok)
        self.assertEqual(self.mutations(seen)[0][1], PREFIX + "Documents/e%CC%81tude%20finale.md")
        self.assertEqual(self.authorized, [("PUT", path)])

    def test_binary_boundary_only_places_already_validated_fake_bytes_with_fixed_media_type(self):
        for format, media in (("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                              ("pdf", "application/pdf")):
            path, content = f"Documents/X.{format}", b"synthetic-renderer-result"
            with self.subTest(format=format), dav_server(creation_responses(path, content)) as (base, seen):
                self.assertTrue(self.create(self.client(base), path, content, format=format).ok)
                self.assertEqual(self.mutations(seen)[0][2]["Content-Type"], media)
                self.assertEqual(self.mutations(seen)[0][3], content)

    def test_config_required_and_no_environment_factory_or_runtime_default(self):
        self.assertFalse(hasattr(self.module.NextcloudDocumentMutationClient, "from_env"))
        with patch("core.workspace_folder_nextcloud_client.config_from_env", side_effect=AssertionError):
            with self.assertRaises((TypeError, DocumentWorkshopError)):
                self.module.NextcloudDocumentMutationClient(None)

    def test_forged_target_and_unconfirmed_collections_refused_before_io(self):
        bad = DocumentTargetPath("Documents/X.md", "forged", ("Documents", "X.md"))
        valid = validate_document_path("Documents/A/X.md", format="markdown")
        with dav_server([]) as (base, seen):
            client = self.client(base)
            for target, collections in ((bad, ()), (valid, ()), (valid, ("Documents/A", "Documents/B")),
                                         (valid, ("Documents", "Documents/A"))):
                with self.subTest(collections=collections), self.assertRaises(DocumentWorkshopError):
                    client.create_document("Scope", target, CONTENT, confirmed_collections=collections,
                                           before_mutation=self.authorize)
            self.assertEqual(seen, [])
            self.assertEqual(self.authorized, [])

    def test_invalid_content_is_rejected_before_reads_or_mutations(self):
        with dav_server([]) as (base, seen):
            for content in (b"", bytearray(CONTENT), "private", b"x" * (40 * 1024 * 1024 + 1)):
                with self.subTest(kind=type(content).__name__), self.assertRaises(DocumentWorkshopError):
                    self.create(self.client(base), content=content)
            self.assertEqual(seen, [])

    def test_stat_error_and_invalid_root_never_become_absence(self):
        cases = [(500, {}, b""), (403, {}, b""), (404, {}, b""), (207, {}, b"<invalid>"),
                 (207, {}, collection_xml(file_id="")), (207, {}, collection_xml(collection=False))]
        for reply in cases:
            with self.subTest(status=reply[0]), dav_server([reply]) as (base, seen):
                result = self.create(self.client(base))
                self.assertEqual(result.state, "known_failure")
                self.assertEqual(self.mutations(seen), [])
        self.assertEqual(self.authorized, [])

    def test_target_stat_error_never_becomes_absence_even_with_an_empty_parent_listing(self):
        for reply in ((503, {}, b""), (412, {}, b""), (207, {}, b"<invalid>")):
            replies = creation_responses()[:2] + [reply]
            with self.subTest(status=reply[0]), dav_server(replies) as (base, seen):
                self.assertEqual(self.create(self.client(base)).state, "known_failure")
                self.assertEqual(self.mutations(seen), [])

    def test_nfc_casefold_collision_and_noncollection_ancestor_block_all_mutations(self):
        cases = [("Documents/x.MD", False, "Documents/X.md"),
                 ("Documents/étude.md", False, "Documents/e\u0301tude.md"),
                 ("Documents/A", False, "Documents/A/X.md"),
                 ("Documents/a", True, "Documents/A/X.md")]
        for existing, collection, target in cases:
            root = collection_xml()
            listing = multistatus(resource(), resource(existing, collection=collection, file_id="2"))
            with self.subTest(existing=existing), dav_server([(207, {}, root), (207, {}, listing)]) as (base, seen):
                result = self.create(self.client(base), target)
                self.assertEqual(result.state, "known_failure")
                self.assertEqual(result.reason_code, "document_target_collision")
                self.assertEqual(self.mutations(seen), [])

    def test_missing_collection_inspection_uses_only_confirmable_path_and_reads(self):
        target = validate_document_path("Documents/A/B/X.md", format="markdown")
        with dav_server([(207, {}, collection_xml()), (207, {}, collection_xml())]) as (base, seen):
            self.assertEqual(self.client(base).inspect_create_target("Scope", target),
                             ("Documents/A", "Documents/A/B"))
            self.assertEqual(self.mutations(seen), [])

    def test_missing_collections_have_verified_parents_and_explicit_404_before_each_mkcol(self):
        root, a, b = collection_xml(), collection_xml("Documents/A", file_id="3"), collection_xml("Documents/A/B", file_id="4")
        path = "Documents/A/B/X.md"
        file = file_xml(path)
        replies = [(207, {}, root), (207, {}, root),
                   (207, {}, root), (207, {}, root), (404, {}, b""), (201, {}, b""), (207, {}, a),
                   (207, {}, a), (207, {}, a), (404, {}, b""), (201, {}, b""), (207, {}, b),
                   (207, {}, b), (207, {}, b), (404, {}, b""), (201, {"ETag": CREATION_ETAG}, b""),
                   (207, {}, file), (207, {}, file), (200, {"ETag": CREATION_ETAG}, CONTENT), (207, {}, file)]
        with dav_server(replies) as (base, seen):
            result = self.create(self.client(base), path)
        self.assertTrue(result.ok)
        self.assertEqual(result.created_collections, ("Documents/A", "Documents/A/B"))
        self.assertEqual(self.authorized, [("MKCOL", "Documents/A"), ("MKCOL", "Documents/A/B"), ("PUT", path)])
        self.assertEqual([(x[0], x[1]) for x in self.mutations(seen)],
                         [("MKCOL", PREFIX + "Documents/A"), ("MKCOL", PREFIX + "Documents/A/B"), ("PUT", PREFIX + path)])
        for index, request in enumerate(seen):
            if request[0] == "MKCOL":
                self.assertEqual(seen[index - 1][0:2], ("PROPFIND", request[1]))
                self.assertEqual(seen[index - 1][2]["Depth"], "0")

    def test_existing_confirmed_collection_is_verified_and_not_created(self):
        root, a = collection_xml(), collection_xml("Documents/A", file_id="3")
        listing = multistatus(resource(), resource("Documents/A", file_id="3"))
        path, file = "Documents/A/X.md", file_xml("Documents/A/X.md")
        replies = [(207, {}, root), (207, {}, listing), (207, {}, a), (207, {}, a), (404, {}, b""),
                   (201, {"ETag": CREATION_ETAG}, b""), (207, {}, file), (207, {}, file),
                   (200, {"ETag": CREATION_ETAG}, CONTENT), (207, {}, file)]
        with dav_server(replies) as (base, seen):
            result = self.create(self.client(base), path)
        self.assertTrue(result.ok)
        self.assertEqual(result.created_collections, ())
        self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])

    def test_mkcol_stat_error_never_triggers_creation_and_created_empty_collections_retained(self):
        root, a = collection_xml(), collection_xml("Documents/A", file_id="3")
        for bad_stat in ((500, {}, b""), (207, {}, b"<invalid>")):
            replies = [(207, {}, root), (207, {}, root), (207, {}, root), (207, {}, root), bad_stat]
            with self.subTest(status=bad_stat[0]), dav_server(replies) as (base, seen):
                result = self.create(self.client(base), "Documents/A/X.md")
                self.assertEqual(result.state, "known_failure")
                self.assertEqual(self.mutations(seen), [])
        replies = [(207, {}, root), (207, {}, root), (207, {}, root), (207, {}, root),
                   (404, {}, b""), (201, {}, b""), (207, {}, a), (500, {}, b"")]
        with dav_server(replies) as (base, seen):
            result = self.create(self.client(base), "Documents/A/X.md")
            self.assertEqual(result.created_collections, ("Documents/A",))
            self.assertEqual([x[0] for x in self.mutations(seen)], ["MKCOL"])

    def test_lost_mkcol_response_is_uncertain_and_never_followed_by_put_or_delete(self):
        root = collection_xml()
        for reply in ("drop", (303, {"Location": PREFIX + "Documents/Other"}, b""),
                      (307, {"Location": PREFIX + "Documents/Other"}, b"")):
            replies = [(207, {}, root), (207, {}, root), (207, {}, root), (207, {}, root), (404, {}, b""), reply]
            with self.subTest(reply=reply if reply == "drop" else reply[0]), dav_server(replies) as (base, seen):
                result = self.create(self.client(base), "Documents/A/X.md")
                self.assertEqual(result.state, "remote_uncertain")
                self.assertEqual(result.created_collections, ())
                self.assertEqual([x[0] for x in self.mutations(seen)], ["MKCOL"])
                self.assertFalse(any("Other" in x[1] for x in seen))

    def test_fencing_failure_after_mkcol_retains_empty_collection_and_prevents_put(self):
        root, a = collection_xml(), collection_xml("Documents/A", file_id="3")
        replies = [(207, {}, root), (207, {}, root), (207, {}, root), (207, {}, root), (404, {}, b""),
                   (201, {}, b""), (207, {}, a), (207, {}, a), (207, {}, a), (404, {}, b"")]
        with dav_server(replies) as (base, seen):
            target = validate_document_path("Documents/A/X.md", format="markdown")
            result = self.client(base).create_document("Scope", target, CONTENT, confirmed_collections=("Documents/A",),
                                                       before_mutation=lambda method, _: method == "MKCOL")
            self.assertEqual(result.state, "known_failure")
            self.assertEqual(result.created_collections, ("Documents/A",))
            self.assertEqual([x[0] for x in self.mutations(seen)], ["MKCOL"])

    def test_authorization_callback_must_succeed_strictly_before_effect(self):
        target = validate_document_path("Documents/X.md", format="markdown")
        for value in (None, False, 1, "true"):
            with self.subTest(value=value), dav_server(creation_responses()[:3]) as (base, seen):
                result = self.client(base).create_document("Scope", target, CONTENT, confirmed_collections=(),
                                                           before_mutation=lambda *_: value)
                self.assertEqual(result.state, "known_failure")
                self.assertEqual(self.mutations(seen), [])

    def test_callback_exception_is_content_free_and_does_not_mutate(self):
        target = validate_document_path("Documents/X.md", format="markdown")
        def bad_callback(*_):
            raise RuntimeError("synthetic-private-data")
        with dav_server(creation_responses()[:3]) as (base, seen):
            result = self.client(base).create_document("Scope", target, CONTENT, confirmed_collections=(),
                                                       before_mutation=bad_callback)
        self.assertEqual(result.reason_code, "document_mutation_not_authorized")
        self.assertEqual(self.mutations(seen), [])
        self.assertNotIn("private", repr(result))

    def test_put_412_is_a_known_conflict_without_retry_or_compensation(self):
        replies = creation_responses()[:3] + [(412, {}, b"")]
        with dav_server(replies) as (base, seen):
            result = self.create(self.client(base))
        self.assertEqual((result.state, result.reason_code), ("known_failure", "document_target_collision"))
        self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])

    def test_put_absent_weak_duplicate_etag_never_grants_ownership(self):
        for headers in ({}, {"ETag": 'W/"created-v1"'}, [("ETag", CREATION_ETAG), ("ETag", CREATION_ETAG)]):
            with self.subTest(headers=headers), dav_server(creation_responses()[:3] + [(201, headers, b"")]) as (base, seen):
                client = self.client(base)
                result = self.create(client)
                self.assertEqual(result.state, "remote_uncertain")
                compensation = client.compensate_created_document("Scope", validate_document_path("Documents/X.md", format="markdown"),
                                                                  result, before_mutation=self.authorize)
                self.assertEqual(compensation.state, "preserved")
                self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])

    def test_put_etag_size_identity_and_bytes_must_be_verifiable_before_success(self):
        variants = [file_xml(etag='"different"'), file_xml(file_id=""), file_xml(content=b"changed bytes")]
        for xml in variants:
            replies = creation_responses()[:4] + [(207, {}, xml)]
            with self.subTest(xml_size=len(xml)), dav_server(replies) as (base, seen):
                client = self.client(base)
                result = self.create(client)
                self.assertEqual(result.state, "remote_uncertain")
                self.assertEqual(client.compensate_created_document("Scope", validate_document_path("Documents/X.md", format="markdown"),
                                                                   result, before_mutation=self.authorize).state, "preserved")
                self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])
        replies = creation_responses()
        replies[6] = (200, {"ETag": CREATION_ETAG}, b"x" * len(CONTENT))
        with dav_server(replies) as (base, seen):
            result = self.create(self.client(base))
            self.assertEqual(result.state, "remote_uncertain")
            self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])

    def test_network_result_lost_after_put_body_received_is_unknown_not_replayed(self):
        with dav_server(creation_responses()[:3] + ["drop"]) as (base, seen):
            result = self.create(self.client(base))
        self.assertEqual(result.state, "remote_uncertain")
        self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])
        self.assertEqual(self.mutations(seen)[0][3], CONTENT)

    def test_redirect_and_environment_proxy_are_never_used(self):
        for status in (303, 307):
            with self.subTest(status=status), patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "no_proxy": ""}), \
                    dav_server(creation_responses()[:3] + [(status, {"Location": PREFIX + "Documents/Other.md"}, b"")]) as (base, seen):
                result = self.create(self.client(base))
                self.assertEqual(result.state, "remote_uncertain")
                self.assertEqual(result.http_status, status)
                self.assertEqual(len(seen), 4)
                self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])
                self.assertEqual(self.mutations(seen)[0][3], CONTENT)
                self.assertFalse(any("Other" in x[1] for x in seen))

    def test_compensation_204_and_404_are_certain_absence_exact_conditional_delete(self):
        for status in (204, 404):
            replies = creation_responses() + [(207, {}, file_xml()), (status, {}, b"")]
            with self.subTest(status=status), dav_server(replies) as (base, seen):
                client = self.client(base)
                created = self.create(client)
                result = client.compensate_created_document("Scope", validate_document_path("Documents/X.md", format="markdown"),
                                                            created, before_mutation=self.authorize)
                self.assertEqual(result.state, "absence_certain")
                self.assertTrue(result.ok)
                delete = self.mutations(seen)[-1]
                self.assertEqual((delete[0], delete[1], delete[2]["If-Match"]),
                                 ("DELETE", PREFIX + "Documents/X.md", CREATION_ETAG))

    def test_compensation_202_and_lost_reply_are_unknown_not_retried(self):
        for reply in ((202, {}, b""), "drop"):
            with self.subTest(reply=reply), dav_server(creation_responses() + [(207, {}, file_xml()), reply]) as (base, seen):
                client, target = self.client(base), validate_document_path("Documents/X.md", format="markdown")
                created = self.create(client)
                self.assertEqual(client.compensate_created_document("Scope", target, created,
                                                                   before_mutation=self.authorize).state, "remote_uncertain")
                self.assertEqual(client.compensate_created_document("Scope", target, created,
                                                                   before_mutation=self.authorize).state, "preserved")
                self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT", "DELETE"])

    def test_already_absent_compensation_target_is_certain_without_any_delete(self):
        with dav_server(creation_responses() + [(404, {}, b"")]) as (base, seen):
            client = self.client(base)
            created = self.create(client)
            result = client.compensate_created_document("Scope", validate_document_path("Documents/X.md", format="markdown"),
                                                        created, before_mutation=self.authorize)
            self.assertEqual(result.state, "absence_certain")
            self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])
            self.assertEqual(self.authorized, [("PUT", "Documents/X.md")])

    def test_changed_etag_or_identity_blocks_delete_and_412_preserves_resource(self):
        cases = [[(207, {}, file_xml(etag='"changed"'))], [(207, {}, file_xml(file_id="3"))],
                 [(412, {}, b"")], [(207, {}, file_xml()), (412, {}, b"")]]
        for tail in cases:
            with self.subTest(length=len(tail)), dav_server(creation_responses() + tail) as (base, seen):
                client = self.client(base)
                created = self.create(client)
                result = client.compensate_created_document("Scope", validate_document_path("Documents/X.md", format="markdown"),
                                                            created, before_mutation=self.authorize)
                self.assertEqual(result.state, "preserved")
                self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"] + (["DELETE"] if len(tail) == 2 else []))

    def test_compensation_rejects_foreign_reconstructed_or_transposed_proof_without_io(self):
        with dav_server(creation_responses()) as (base, seen):
            client, target = self.client(base), validate_document_path("Documents/X.md", format="markdown")
            created = self.create(client)
            forged = self.module.CreatedDocumentResult(created.state, created.reason_code, created.http_status,
                                                       created.resource, created.creation_etag, created.created_collections)
            for owner, path, proof in ((self.client(base), target, created), (client, target, forged),
                                       (client, validate_document_path("Documents/Other.md", format="markdown"), created)):
                with self.subTest(owner=owner is client, path=path is target):
                    result = owner.compensate_created_document("Scope", path, proof, before_mutation=self.authorize)
                    self.assertEqual(result.state, "preserved")
            self.assertEqual(len(seen), 8)
            self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])

    def test_compensation_requires_current_fencing_callback_and_never_deletes_collections(self):
        with dav_server(creation_responses() + [(207, {}, file_xml())]) as (base, seen):
            client, target = self.client(base), validate_document_path("Documents/X.md", format="markdown")
            created = self.create(client)
            result = client.compensate_created_document("Scope", target, created, before_mutation=lambda *_: False)
            self.assertEqual(result.state, "preserved")
            self.assertEqual([x[0] for x in self.mutations(seen)], ["PUT"])
            with self.assertRaises(DocumentWorkshopError):
                client.compensate_created_document("Scope", DocumentTargetPath("Documents", "documents", ("Documents",)),
                                                    created, before_mutation=self.authorize)
