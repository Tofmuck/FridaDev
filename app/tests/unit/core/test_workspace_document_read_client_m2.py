"""M2 contracts against a loopback DAV server; no remote service or credentials."""
from contextlib import contextmanager
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import threading
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape

from core.document_workshop_contract import DocumentWorkshopError
from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
from core import workspace_document_paths as paths

PREFIX = "/remote.php/dav/files/test/Frida/Scope/"


def resource(path="Documents", *, collection=True, file_id="1", etag='"v1"', size=3,
             media_type="text/plain", status="HTTP/1.1 200 OK", href=None):
    return (f'<d:response><d:href>{escape(href or PREFIX + path)}</d:href>'
            f'<d:propstat><d:prop><d:resourcetype>{"<d:collection/>" if collection else ""}'
            f'</d:resourcetype><oc:fileid>{file_id}</oc:fileid><d:getetag>{escape(etag)}</d:getetag>'
            f'<d:getcontentlength>{size}</d:getcontentlength><d:getcontenttype>{media_type}</d:getcontenttype>'
            f'</d:prop><d:status>{status}</d:status></d:propstat></d:response>')


def multistatus(*resources):
    return ('<d:multistatus xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">' +
            ''.join(resources) + '</d:multistatus>').encode()


@contextmanager
def dav_server(responses):
    observed = []
    class Handler(BaseHTTPRequestHandler):
        def do_PROPFIND(self):
            self.reply()
        def do_GET(self):
            self.reply()
        def log_message(self, *_):
            pass
        def reply(self):
            observed.append((self.command, self.path, dict(self.headers)))
            size = int(self.headers.get("Content-Length", "0"))
            if size:
                self.rfile.read(size)
            response = responses.pop(0) if responses else (500, {}, b"")
            status, headers, body = response
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(body)
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


class DocumentSourcePathsM2Tests(unittest.TestCase):
    def test_sources_and_collections_reuse_exact_path_without_product_format_extension(self):
        self.assertTrue(hasattr(paths, "validate_document_source_path"), "M2 source path contract absent")
        self.assertTrue(hasattr(paths, "validate_document_collection_path"), "M2 collection path contract absent")
        for extension in ("txt", "md", "markdown", "docx", "odt", "pdf"):
            value = f"Documents/e\u0301tude/source.{extension}"
            self.assertEqual(paths.validate_document_source_path(value).relative_path, value)
        self.assertEqual(paths.validate_document_collection_path("Documents").segments, ("Documents",))
        with self.assertRaises(DocumentWorkshopError):
            paths.validate_document_path("Documents/source.odt", format="odt")

    def test_both_paths_reject_traversal_double_escape_limits_and_ambiguous_segments(self):
        self.assertTrue(hasattr(paths, "validate_document_source_path"), "M2 source path contract absent")
        invalid = ("../Documents/a.md", "/Documents/a.md", "Documents//a.md", "Documents/%2e/a.md",
                   "Documents/%252f/a.md", "Documents/../a.md", "Documents/a\\b.md", "Documents/Ａ.md",
                   "Documents/" + "x/" * 9 + "a.md", "Documents/" + "é" * 128 + ".md",
                   "Documents/" + "x" * 181 + ".md", "Documents/" + ("x" * 170 + "/") * 6 + "a.md")
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(DocumentWorkshopError):
                paths.validate_document_source_path(value)


class NextcloudDocumentReadClientM2Tests(unittest.TestCase):
    def setUp(self):
        name = "core.workspace_document_nextcloud_read_client"
        self.assertIsNotNone(importlib.util.find_spec(name), "M2 bounded DAV reader contract absent")
        self.module = __import__(name, fromlist=["NextcloudDocumentReadClient"])

    def client(self, base):
        return self.module.NextcloudDocumentReadClient(NextcloudFolderClientConfig(base, "test", "synthetic"))

    def test_depth_one_is_complete_nonrecursive_and_immutable(self):
        body = multistatus(resource(), resource("Documents/Nested", collection=True, file_id="2"),
                           resource("Documents/a.txt", collection=False, file_id="3"))
        with dav_server([(207, {}, body)]) as (base, seen):
            root, children = self.client(base).list_collection("Scope")
        self.assertEqual(root.relative_path, "Documents")
        self.assertEqual([x.relative_path for x in children], ["Documents/Nested", "Documents/a.txt"])
        self.assertIsInstance(children, tuple)
        self.assertEqual([(x[0], x[2]["Depth"]) for x in seen], [("PROPFIND", "1")])
        self.assertNotIn("a.txt", repr(children))
        with self.assertRaises((AttributeError, TypeError)):
            children[0].file_id = "changed"

    def test_listing_never_executes_returned_hrefs(self):
        invalid = ("https://other.invalid" + PREFIX + "Documents/a.txt", PREFIX + "Notes/a.txt",
                   PREFIX + "Documents/a/b.txt", PREFIX.rstrip('/'), PREFIX + "Documents/%2f.txt",
                   PREFIX + "Documents/%252f.txt", PREFIX + "Documents/%2e%2e", PREFIX + "Documents/%ff.txt",
                   PREFIX + "Documents/a.txt?download=1", PREFIX + "Documents/a.txt#x", "http://[invalid/")
        for href in invalid:
            with self.subTest(href=href), dav_server([(207, {}, multistatus(resource(), resource(
                    collection=False, file_id="2", href=href)))]) as (base, seen):
                with self.assertRaises(DocumentWorkshopError):
                    self.client(base).list_collection("Scope")
                self.assertEqual(len(seen), 1)

    def test_xml_duplicates_invalid_status_entities_and_not_collection_rejected(self):
        cases = [multistatus(resource(), resource()), multistatus(resource(collection=False)),
                 multistatus(resource(status="HTTP/1.1 404 Missing")), b"<invalid>",
                 b'<!DOCTYPE x [<!ENTITY a "x">]><d:multistatus xmlns:d="DAV:">&a;</d:multistatus>',
                 multistatus(resource(), resource("Documents/a.txt", collection=False, file_id="1"))]
        for body in cases:
            with self.subTest(length=len(body)), dav_server([(207, {}, body)]) as (base, _):
                with self.assertRaises(DocumentWorkshopError):
                    self.client(base).list_collection("Scope")

    def test_r4_empty_query_fragment_and_userinfo_are_refused(self):
        for syntax in ("query", "fragment", "userinfo"):
            replies = []
            with self.subTest(syntax=syntax), dav_server(replies) as (base, seen):
                href = (base.replace("://", "://@") if syntax == "userinfo" else "") + PREFIX + "Documents/a.txt"
                href += "?" if syntax == "query" else "#" if syntax == "fragment" else ""
                replies.append((207, {}, multistatus(resource(), resource("Documents/a.txt", collection=False,
                    file_id="2", href=href))))
                with self.assertRaises(DocumentWorkshopError):
                    self.client(base).list_collection("Scope")
                self.assertEqual(len(seen), 1)

    def test_listing_entry_and_real_body_bounds_refuse_without_prefix_success(self):
        cases = [multistatus(resource(), *[resource(f"Documents/f{i}.txt", collection=False,
                  file_id=str(i + 2)) for i in range(257)]), b" " * (1024 * 1024 + 1)]
        for body in cases:
            with self.subTest(length=len(body)), dav_server([(207, {}, body)]) as (base, _):
                with self.assertRaises(DocumentWorkshopError):
                    self.client(base).list_collection("Scope")

    def test_redirect_even_same_origin_is_not_followed(self):
        with dav_server([(302, {"Location": PREFIX + "Documents"}, b"")]) as (base, seen):
            with self.assertRaises(DocumentWorkshopError):
                self.client(base).list_collection("Scope")
        self.assertEqual(len(seen), 1)

    def test_scope_uses_mapping_and_instance_identity_but_not_password(self):
        first = self.client("http://example.invalid/base")
        second = self.module.NextcloudDocumentReadClient(NextcloudFolderClientConfig(
            "http://example.invalid/base", "test", "different"))
        self.assertEqual(first.scope_key("Scope"), second.scope_key("Scope"))
        self.assertNotEqual(first.scope_key("Scope"), first.scope_key("Other"))
        self.assertNotEqual(first.scope_key("Scope"), self.client("http://example.invalid/other").scope_key("Scope"))
        self.assertEqual(len(first.scope_key("Scope")), 64)

    def test_missing_metadata_is_preserved_as_incompatible_and_never_downloaded(self):
        body = multistatus(resource(file_id="", etag=""), resource("Documents/a.txt", collection=False,
                           file_id="", etag='W/"v1"', size="invalid"))
        with dav_server([(207, {}, body)]) as (base, seen):
            client = self.client(base)
            root, children = client.list_collection("Scope")
            self.assertEqual(root.file_id, "")
            self.assertEqual((children[0].file_id, children[0].etag, children[0].byte_size), ("", "", None))
            with self.assertRaises(DocumentWorkshopError):
                client.read_file("Scope", children[0])
            self.assertEqual(len(seen), 1)

    def test_unknown_extension_remains_incompatible_inventory_not_a_global_listing_failure(self):
        body = multistatus(resource(), resource("Documents/a.exe", collection=False, file_id="2"))
        with dav_server([(207, {}, body)]) as (base, seen):
            client = self.client(base)
            _, children = client.list_collection("Scope")
            self.assertEqual(children[0].relative_path, "Documents/a.exe")
            with self.assertRaises(DocumentWorkshopError):
                client.read_file("Scope", children[0])
            self.assertEqual(len(seen), 1)

    def test_selected_collection_identity_is_checked_before_it_can_be_navigated(self):
        with dav_server([(207, {}, multistatus(resource()))]) as (base, _):
            with self.assertRaises(DocumentWorkshopError) as error:
                self.client(base).list_collection("Scope", expected_file_id="99")
            self.assertEqual(error.exception.reason_code, "document_remote_changed")

    def test_environment_proxy_is_disabled_and_source_bound_stops_before_transport(self):
        with patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "no_proxy": ""}), \
                dav_server([(207, {}, multistatus(resource()))]) as (base, seen):
            client = self.client(base)
            client.list_collection("Scope")
            item = self.module.RemoteResource("Documents/a.txt", False, "2", '"v1"', 40 * 1024 * 1024 + 1, "text/plain")
            with self.assertRaises(DocumentWorkshopError):
                client.read_file("Scope", item)
            self.assertEqual(len(seen), 1)

    def test_maximum_children_accepted_and_depth_zero_rejects_extra_resource(self):
        body = multistatus(resource(), *[resource(f"Documents/f{i}.txt", collection=False, file_id=str(i + 2))
                                        for i in range(256)])
        bad_stat = multistatus(resource("Documents/a.txt", collection=False),
                              resource("Documents/b.txt", collection=False, file_id="2"))
        with dav_server([(207, {}, body), (207, {}, bad_stat)]) as (base, seen):
            client = self.client(base)
            self.assertEqual(len(client.list_collection("Scope")[1]), 256)
            with self.assertRaises(DocumentWorkshopError):
                client.stat_resource("Scope", "Documents/a.txt")
            self.assertEqual([x[2]["Depth"] for x in seen], ["1", "0"])

    def test_download_is_one_conditional_get_between_two_conditional_identity_checks(self):
        xml = multistatus(resource("Documents/a.txt", collection=False, file_id="2"))
        with dav_server([(207, {}, xml), (200, {"ETag": '"v1"', "Content-Length": "3"}, b"abc"),
                         (207, {}, xml)]) as (base, seen):
            item = self.module.RemoteResource("Documents/a.txt", False, "2", '"v1"', 3, "text/plain")
            self.assertEqual(self.client(base).read_file("Scope", item), b"abc")
        self.assertEqual([x[0] for x in seen], ["PROPFIND", "GET", "PROPFIND"])
        self.assertTrue(all(x[2]["If-Match"] == '"v1"' for x in seen))
        self.assertTrue(all(x[1] == PREFIX + "Documents/a.txt" for x in seen))

    def test_changed_prestat_prevents_download_and_changed_poststat_prevents_adoption(self):
        good = multistatus(resource("Documents/a.txt", collection=False, file_id="2"))
        for field in ({"file_id": "3"}, {"etag": '"v2"'}, {"size": 4}):
            bad = multistatus(resource("Documents/a.txt", collection=False, **{"file_id": "2", **field}))
            for post in (False, True):
                replies = [(207, {}, good), (200, {"ETag": '"v1"'}, b"abc"), (207, {}, bad)] if post else [(207, {}, bad)]
                with self.subTest(field=field, post=post), dav_server(replies) as (base, seen):
                    item = self.module.RemoteResource("Documents/a.txt", False, "2", '"v1"', 3, "text/plain")
                    with self.assertRaises(DocumentWorkshopError):
                        self.client(base).read_file("Scope", item)
                    self.assertEqual(len(seen), 3 if post else 1)

    def test_get_wrong_etag_encoding_partial_truncated_or_excess_never_retries(self):
        xml = multistatus(resource("Documents/a.txt", collection=False, file_id="2"))
        cases = [(206, {"ETag": '"v1"'}, b"abc"), (412, {}, b""), (404, {}, b""),
                 (200, {"ETag": '"v2"'}, b"abc"), (200, {"ETag": 'W/"v1"'}, b"abc"),
                 (200, {"ETag": '"v1"', "Content-Encoding": "gzip"}, b"abc"),
                 (200, {"ETag": '"v1"', "Content-Length": "4"}, b"abc"),
                 (200, {"ETag": '"v1"'}, b"ab"), (200, {"ETag": '"v1"'}, b"abcd")]
        for reply in cases:
            with self.subTest(status=reply[0], headers=reply[1]), dav_server([(207, {}, xml), reply]) as (base, seen):
                item = self.module.RemoteResource("Documents/a.txt", False, "2", '"v1"', 3, "text/plain")
                with self.assertRaises(DocumentWorkshopError):
                    self.client(base).read_file("Scope", item)
                self.assertEqual([x[0] for x in seen], ["PROPFIND", "GET"])
