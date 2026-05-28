from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as client


class CatalogueClientTests(unittest.TestCase):
    def test_config_defaults_match_catalogue_contract(self) -> None:
        settings = client.get_catalogue_client_config(SimpleNamespace())

        self.assertEqual(settings.base_url, "http://platform-doc-pipeline-api:8090")
        self.assertEqual(settings.timeout_s, 8)

    def test_health_ok_uses_get_only(self) -> None:
        fake = FakeRequests(FakeResponse({"status": "ok", "database": "reachable"}))
        api = _client(fake)

        result = api.health()

        self.assertEqual(result.endpoint_kind, client.ENDPOINT_HEALTH)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.payload["status"], "ok")
        self.assertGreaterEqual(result.duration_ms, 20)
        self.assertEqual(fake.calls[0]["method"], "GET")
        self.assertEqual(fake.calls[0]["url"], "http://catalogue.example/api/health")
        self.assertEqual(fake.calls[0]["timeout"], 11)

    def test_catalog_ok_reports_count_without_content(self) -> None:
        fake = FakeRequests(FakeResponse({"count": 1, "total": 2, "items": [{"id": "doc-a"}]}))
        api = _client(fake)

        result = api.catalog(q="platon", limit=50, offset=3)

        self.assertEqual(result.result_count, 1)
        self.assertEqual(result.to_observability()["result_count"], 1)
        self.assertNotIn("items", result.to_observability())
        self.assertEqual(fake.calls[0]["params"], {"q": "platon", "limit": 50, "offset": 3})

    def test_document_ok_quotes_doc_id_without_path_injection(self) -> None:
        fake = FakeRequests(FakeResponse({"document": {"id": "abc"}}))
        api = _client(fake)

        result = api.document("../settings?x=1")

        self.assertEqual(result.endpoint_kind, client.ENDPOINT_DOCUMENT)
        self.assertEqual(fake.calls[0]["url"], "http://catalogue.example/api/doc/..%2Fsettings%3Fx%3D1")

    def test_metadata_ok_keeps_doc_id_short(self) -> None:
        fake = FakeRequests(FakeResponse({"document": {"id": "dabfe4a7-extra"}, "human_metadata": {}}))
        api = _client(fake)

        result = api.metadata("dabfe4a7-extra")

        self.assertEqual(result.endpoint_kind, client.ENDPOINT_METADATA)
        self.assertEqual(result.doc_id_short, "dabfe4a7")
        self.assertEqual(fake.calls[0]["url"], "http://catalogue.example/api/doc/dabfe4a7-extra/metadata")

    def test_locate_and_context_are_get_with_expected_params(self) -> None:
        fake = FakeRequests(
            [
                FakeResponse({"count": 1, "matches": [{"label": "126b"}]}),
                FakeResponse({"text": "passage content must not enter observability"}),
            ]
        )
        api = _client(fake)

        locate = api.locate("doc-1", "126b", kind="stephanus", limit=20)
        context = api.context("doc-1", page_no=12, para_no=3, window_chars=900)

        self.assertEqual(locate.endpoint_kind, client.ENDPOINT_LOCATE)
        self.assertEqual(context.endpoint_kind, client.ENDPOINT_CONTEXT)
        self.assertEqual(fake.calls[0]["params"], {"kind": "stephanus", "label": "126b", "limit": 20})
        self.assertEqual(fake.calls[1]["params"], {"page_no": 12, "para_no": 3, "char_offset": 0, "window_chars": 900})
        self.assertEqual(context.content_chars, len("passage content must not enter observability"))
        self.assertNotIn("passage content", str(context.to_observability()))

    def test_search_ok_reports_results_count(self) -> None:
        fake = FakeRequests(FakeResponse({"results": [{"id": 1}, {"id": 2}]}))
        api = _client(fake)

        result = api.search("theetete", limit=2)

        self.assertEqual(result.endpoint_kind, client.ENDPOINT_SEARCH)
        self.assertEqual(result.result_count, 2)
        self.assertEqual(fake.calls[0]["params"], {"q": "theetete", "limit": 2})

    def test_not_found_is_content_free(self) -> None:
        fake = FakeRequests(FakeResponse({"detail": "Document not found with private title"}, status_code=404))
        api = _client(fake)

        with self.assertRaises(client.CatalogueNotFound) as ctx:
            api.document("private-doc-id")

        self.assertEqual(ctx.exception.reason_code, client.REASON_NOT_FOUND)
        self.assertNotIn("private title", str(ctx.exception))
        self.assertEqual(ctx.exception.to_observability()["doc_id_short"], "private-")

    def test_timeout_is_reported_without_response_content(self) -> None:
        fake = FakeRequests(TimeoutError("slow upstream with private detail"))
        api = _client(fake)

        with self.assertRaises(client.CatalogueTimeout) as ctx:
            api.health()

        self.assertEqual(ctx.exception.reason_code, client.REASON_TIMEOUT)
        self.assertNotIn("private detail", str(ctx.exception))

    def test_invalid_json_is_reported_without_body(self) -> None:
        fake = FakeRequests(FakeResponse({"ignored": True}, json_error=ValueError("body has private text")))
        api = _client(fake)

        with self.assertRaises(client.CatalogueInvalidJson) as ctx:
            api.health()

        self.assertEqual(ctx.exception.reason_code, client.REASON_INVALID_JSON)
        self.assertNotIn("private text", str(ctx.exception))

    def test_unexpected_status_is_content_free(self) -> None:
        fake = FakeRequests(FakeResponse({"detail": "private server body"}, status_code=418))
        api = _client(fake)

        with self.assertRaises(client.CatalogueUnexpectedStatus) as ctx:
            api.health()

        self.assertEqual(ctx.exception.reason_code, client.REASON_UNEXPECTED_STATUS)
        self.assertNotIn("private server body", str(ctx.exception))

    def test_service_unavailable_status_is_content_free(self) -> None:
        fake = FakeRequests(FakeResponse({"detail": "down"}, status_code=503))
        api = _client(fake)

        with self.assertRaises(client.CatalogueServiceUnavailable) as ctx:
            api.health()

        self.assertEqual(ctx.exception.reason_code, client.REASON_SERVICE_UNAVAILABLE)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_forbids_delete_route_before_network(self) -> None:
        fake = FakeRequests(FakeResponse({"ok": True}))
        api = _client(fake)

        with self.assertRaises(client.CatalogueForbiddenMethod):
            api._request("DELETE", "/doc/doc-1", endpoint_kind="delete", doc_id="doc-1")

        self.assertEqual(fake.calls, [])

    def test_forbids_put_metadata_before_network(self) -> None:
        fake = FakeRequests(FakeResponse({"ok": True}))
        api = _client(fake)

        with self.assertRaises(client.CatalogueForbiddenMethod):
            api._request("PUT", "/doc/doc-1/metadata", endpoint_kind="metadata", doc_id="doc-1")

        self.assertEqual(fake.calls, [])

    def test_forbids_settings_and_progress_mutators_before_network(self) -> None:
        fake = FakeRequests(FakeResponse({"ok": True}))
        api = _client(fake)

        forbidden = [
            ("PUT", "/settings"),
            ("POST", "/settings/reset"),
            ("POST", "/progress/recent/clear"),
        ]
        for method, path in forbidden:
            with self.subTest(method=method, path=path):
                with self.assertRaises(client.CatalogueForbiddenMethod):
                    api._request(method, path, endpoint_kind="mutator")

        self.assertEqual(fake.calls, [])

    def test_forbids_non_allowlisted_get_routes_before_network(self) -> None:
        fake = FakeRequests(FakeResponse({"ok": True}))
        api = _client(fake)

        for path in ["/settings", "/progress/recent/clear", "/doc/doc-1/with-files", "/doc/doc-1/export"]:
            with self.subTest(path=path):
                with self.assertRaises(client.CatalogueForbiddenRoute):
                    api._request("GET", path, endpoint_kind="forbidden")

        self.assertEqual(fake.calls, [])

    def test_public_methods_only_emit_get_calls(self) -> None:
        fake = FakeRequests([FakeResponse({"status": "ok"}), FakeResponse({"items": []}), FakeResponse({"document": {}})])
        api = _client(fake)

        api.health()
        api.catalog()
        api.document("doc-1")

        self.assertEqual([call["method"] for call in fake.calls], ["GET", "GET", "GET"])

    def test_invalid_base_url_is_rejected(self) -> None:
        with self.assertRaises(client.CatalogueInvalidBaseUrl):
            client.CatalogueClient(config=client.CatalogueClientConfig(base_url="file:///tmp/catalogue", timeout_s=8))


def _client(fake: "FakeRequests") -> client.CatalogueClient:
    return client.CatalogueClient(
        config=client.CatalogueClientConfig(base_url="http://catalogue.example/api", timeout_s=11),
        requests_module=fake,
        monotonic=_monotonic(1.0, 1.025, 1.050, 1.075, 1.100),
    )


def _monotonic(*values: float):
    remaining = list(values)
    last = values[-1] if values else 0.0

    def next_value() -> float:
        if remaining:
            return remaining.pop(0)
        return last

    return next_value


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, object],
        *,
        status_code: int = 200,
        json_error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self) -> dict[str, object]:
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeRequests:
    def __init__(self, responses: FakeResponse | list[FakeResponse] | Exception) -> None:
        self.responses = responses if isinstance(responses, list) else [responses]
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, *, params: dict[str, object], timeout: int) -> FakeResponse:
        self.calls.append({"method": "GET", "url": url, "params": dict(params), "timeout": timeout})
        if not self.responses:
            raise AssertionError("unexpected network call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


if __name__ == "__main__":
    unittest.main()
