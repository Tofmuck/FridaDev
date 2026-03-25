from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import minimal_validation


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


class MinimalValidationPhase9Tests(unittest.TestCase):
    def test_check_ui_assets_requires_new_admin_assets_and_rejects_legacy_assets(self) -> None:
        details = minimal_validation._check_ui_assets()

        self.assertIn("admin_html", details["files"])
        self.assertIn("admin_js", details["files"])
        self.assertIn("admin_old_html", details["legacy_admin_assets_absent"])
        self.assertIn("admin_old_js", details["legacy_admin_assets_absent"])
        self.assertIn('id="rows"', details["admin_html_forbidden_markers"])
        self.assertIn('id="restart"', details["admin_html_forbidden_markers"])
        self.assertIn("/api/admin/logs", details["admin_js_forbidden_markers"])
        self.assertIn("/api/admin/restart", details["admin_js_forbidden_markers"])

    def test_check_api_smoke_verifies_admin_route_and_admin_old_absence(self) -> None:
        original_http_json = minimal_validation._http_json
        calls = []

        def fake_http_json(method: str, url: str, **kwargs):
            calls.append((method, url))
            if url.endswith("/"):
                return _FakeResponse(200, text="Frida")
            if url.endswith("/admin"):
                return _FakeResponse(200, text="Admin de configuration")
            if url.endswith("/admin-old"):
                return _FakeResponse(404, text="not found")
            if url.endswith("/api/conversations?limit=1"):
                return _FakeResponse(200, payload={"ok": True, "items": []})
            if url.endswith("/api/admin/logs?limit=1"):
                return _FakeResponse(200, payload={"ok": True, "logs": []})
            if "/api/conversations/" in url and url.endswith("/messages"):
                return _FakeResponse(404, payload={"ok": False, "error": "conversation introuvable"})
            raise AssertionError(f"unexpected request: {method} {url}")

        minimal_validation._http_json = fake_http_json
        try:
            details = minimal_validation._check_api_smoke("http://frida.test")
        finally:
            minimal_validation._http_json = original_http_json

        self.assertEqual(details["root_status"], 200)
        self.assertEqual(details["admin_status"], 200)
        self.assertEqual(details["admin_old_status"], 404)
        self.assertIn(("GET", "http://frida.test/admin"), calls)
        self.assertIn(("GET", "http://frida.test/admin-old"), calls)


if __name__ == "__main__":
    unittest.main()
