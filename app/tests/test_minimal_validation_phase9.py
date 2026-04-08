from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import minimal_validation
import config
from admin import runtime_settings


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


class MinimalValidationPhase9Tests(unittest.TestCase):
    @staticmethod
    def _fake_admin_settings_payload():
        return {
            "ok": True,
            "sections": {
                "main_model": {
                    "section": "main_model",
                    "payload": {
                        "model": {"value": "openrouter/test-main", "origin": "env_seed"},
                        "api_key": {"is_secret": True, "is_set": True, "origin": "env_seed"},
                    },
                    "source": "env",
                    "source_reason": "empty_table",
                },
                "arbiter_model": {"section": "arbiter_model", "payload": {}, "source": "env", "source_reason": "empty_table"},
                "summary_model": {"section": "summary_model", "payload": {}, "source": "env", "source_reason": "empty_table"},
                "stimmung_agent_model": {
                    "section": "stimmung_agent_model",
                    "payload": {},
                    "source": "env",
                    "source_reason": "empty_table",
                },
                "validation_agent_model": {
                    "section": "validation_agent_model",
                    "payload": {},
                    "source": "env",
                    "source_reason": "empty_table",
                },
                "embedding": {
                    "section": "embedding",
                    "payload": {
                        "endpoint": {"value": "https://embed.example", "origin": "env_seed"},
                        "token": {"is_secret": True, "is_set": True, "origin": "env_seed"},
                    },
                    "source": "env",
                    "source_reason": "empty_table",
                },
                "database": {
                    "section": "database",
                    "payload": {
                        "backend": {"value": "postgresql", "origin": "env_seed"},
                        "dsn": {"is_secret": True, "is_set": False, "origin": "env_seed"},
                    },
                    "source": "env",
                    "source_reason": "empty_table",
                },
                "services": {
                    "section": "services",
                    "payload": {
                        "searxng_url": {"value": "http://127.0.0.1:8080", "origin": "env_seed"},
                        "crawl4ai_token": {"is_secret": True, "is_set": True, "origin": "env_seed"},
                    },
                    "source": "env",
                    "source_reason": "empty_table",
                },
                "resources": {"section": "resources", "payload": {}, "source": "env", "source_reason": "empty_table"},
                "identity_governance": {
                    "section": "identity_governance",
                    "payload": {
                        "CONTEXT_HINTS_MAX_ITEMS": {"value": 2, "origin": "env_seed"},
                    },
                    "source": "env",
                    "source_reason": "empty_table",
                },
            },
        }

    @staticmethod
    def _fake_resources_payload(origin: str):
        return {
            "ok": True,
            "section": "resources",
            "payload": {
                "llm_identity_path": {"value": "data/identity/llm_identity.txt", "origin": origin},
                "user_identity_path": {"value": "data/identity/user_identity.txt", "origin": origin},
            },
        }

    def test_assert_masked_secret_fields_accepts_redacted_secret_payloads(self) -> None:
        section_payloads = {
            "main_model": {
                "model": {"value": "openrouter/test", "origin": "db"},
                "api_key": {"is_secret": True, "is_set": True, "origin": "db"},
            },
            "arbiter_model": {},
            "summary_model": {},
            "embedding": {
                "endpoint": {"value": "https://embed.example", "origin": "db"},
                "token": {"is_secret": True, "is_set": True, "origin": "db"},
            },
            "database": {
                "backend": {"value": "postgresql", "origin": "db"},
                "dsn": {"is_secret": True, "is_set": False, "origin": "db"},
            },
            "services": {
                "searxng_url": {"value": "http://127.0.0.1:8080", "origin": "db"},
                "crawl4ai_token": {"is_secret": True, "is_set": True, "origin": "db"},
            },
            "resources": {},
            "identity_governance": {},
        }

        minimal_validation._assert_masked_secret_fields(section_payloads)

    def test_build_non_secret_patch_payload_keeps_only_value_fields(self) -> None:
        patch_payload = minimal_validation._build_non_secret_patch_payload(
            {
                "llm_identity_path": {"value": "data/identity/llm.txt", "origin": "env_seed"},
                "user_identity_path": {"value": "data/identity/user.txt", "origin": "env_seed"},
                "api_key": {"is_secret": True, "is_set": True, "origin": "db"},
            }
        )

        self.assertEqual(
            patch_payload,
            {
                "llm_identity_path": {"value": "data/identity/llm.txt"},
                "user_identity_path": {"value": "data/identity/user.txt"},
            },
        )

    def test_check_ui_assets_requires_new_admin_assets_and_rejects_legacy_assets(self) -> None:
        details = minimal_validation._check_ui_assets()

        self.assertIn("admin_html", details["files"])
        self.assertIn("log_html", details["files"])
        self.assertIn("hermeneutic_admin_html", details["files"])
        self.assertIn("identity_html", details["files"])
        self.assertIn("admin_ui_common_js", details["files"])
        self.assertIn("admin_state_js", details["files"])
        self.assertIn("admin_section_main_model_js", details["files"])
        self.assertIn("admin_section_arbiter_model_js", details["files"])
        self.assertIn("admin_section_summary_model_js", details["files"])
        self.assertIn("admin_section_stimmung_agent_model_js", details["files"])
        self.assertIn("admin_section_validation_agent_model_js", details["files"])
        self.assertIn("admin_section_embedding_js", details["files"])
        self.assertIn("admin_section_database_js", details["files"])
        self.assertIn("admin_section_services_js", details["files"])
        self.assertIn("admin_section_resources_js", details["files"])
        self.assertIn("admin_js", details["files"])
        self.assertIn("hermeneutic_admin_api_js", details["files"])
        self.assertIn("hermeneutic_admin_render_js", details["files"])
        self.assertIn("hermeneutic_admin_render_identity_governance_js", details["files"])
        self.assertIn("hermeneutic_admin_main_js", details["files"])
        self.assertIn("identity_api_js", details["files"])
        self.assertIn("identity_render_runtime_representations_js", details["files"])
        self.assertIn("identity_main_js", details["files"])
        self.assertEqual(details["admin_script_srcs"], details["admin_script_order"])
        self.assertEqual(
            details["admin_settings_endpoints_found"],
            details["admin_settings_endpoints_expected"],
        )
        self.assertEqual(
            details["hermeneutic_admin_script_srcs"],
            details["hermeneutic_admin_script_order"],
        )
        self.assertEqual(
            details["hermeneutic_admin_endpoints_found"],
            details["hermeneutic_admin_endpoints_expected"],
        )
        self.assertEqual(
            details["identity_script_srcs"],
            details["identity_script_order"],
        )
        self.assertEqual(
            details["identity_endpoints_found"],
            details["identity_endpoints_expected"],
        )
        self.assertIn("adminMainModelSave", details["admin_dom_hook_ids_checked"])
        self.assertIn("adminEmbeddingSecretCard", details["admin_dom_hook_ids_checked"])
        self.assertIn("adminDatabaseSecretCard", details["admin_dom_hook_ids_checked"])
        self.assertIn("adminServicesSecretCard", details["admin_dom_hook_ids_checked"])
        self.assertEqual(
            details["admin_dynamic_getelement_templates_found"],
            details["admin_dynamic_getelement_templates_expected"],
        )
        self.assertEqual(
            details["admin_dynamic_id_assignment_templates_found"],
            details["admin_dynamic_id_assignment_templates_expected"],
        )
        self.assertEqual(
            details["admin_dynamic_templates_lookup_families_checked"],
            details["admin_dynamic_templates_generated_families_checked"],
        )
        self.assertEqual(
            details["admin_query_selectors_found"],
            details["admin_query_selectors_expected"],
        )
        self.assertEqual(
            details["admin_data_selectors_checked"],
            details["admin_dataset_attrs_checked"],
        )
        self.assertIn("adminStimmungAgentModelFields", details["admin_field_containers_checked"])
        self.assertIn("adminValidationAgentModelFields", details["admin_field_containers_checked"])
        self.assertIn('target="_blank"', details["index_hermeneutic_markers"])
        self.assertIn('href="/identity"', details["index_markers"])
        self.assertIn("Hermeneutic admin", details["hermeneutic_admin_markers"])
        self.assertIn("Logs applicatifs", details["log_markers"])
        self.assertIn("Fiche identite pour le jugement", details["identity_markers"])
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
            if url.endswith("/log"):
                return _FakeResponse(200, text="Logs applicatifs")
            if url.endswith("/hermeneutic-admin"):
                return _FakeResponse(200, text="Hermeneutic admin")
            if url.endswith("/identity"):
                return _FakeResponse(200, text="Fiche identite pour le jugement")
            if url.endswith("/admin-old"):
                return _FakeResponse(404, text="not found")
            if url.endswith("/api/conversations?limit=1"):
                return _FakeResponse(200, payload={"ok": True, "items": []})
            if url.endswith("/api/admin/settings"):
                return _FakeResponse(200, payload=self._fake_admin_settings_payload())
            if url.endswith("/api/admin/settings/resources"):
                if method == "GET":
                    return _FakeResponse(200, payload=self._fake_resources_payload("env_seed"))
                if method == "PATCH":
                    if kwargs.get("json", {}).get("payload", {}).get("llm_identity_path", {}).get("value") == 123:
                        return _FakeResponse(
                            400,
                            payload={
                                "ok": False,
                                "error": "invalid text value for resources.llm_identity_path",
                            },
                        )
                    return _FakeResponse(200, payload=self._fake_resources_payload("admin_ui"))
            if url.endswith("/api/admin/identity/governance"):
                if method == "GET":
                    return _FakeResponse(
                        200,
                        payload={
                            "ok": True,
                            "governance_version": "v1",
                            "items": [],
                        },
                    )
                if method == "POST":
                    return _FakeResponse(
                        400,
                        payload={
                            "ok": False,
                            "validation_error": "governance_key_readonly",
                        },
                    )
            if url.endswith("/api/admin/identity/runtime-representations"):
                return _FakeResponse(
                    200,
                    payload={
                        "ok": True,
                        "representations_version": "v1",
                    },
                )
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
        self.assertEqual(details["log_status"], 200)
        self.assertEqual(details["hermeneutic_admin_status"], 200)
        self.assertEqual(details["identity_status"], 200)
        self.assertEqual(details["admin_old_status"], 404)
        self.assertEqual(details["admin_settings_status"], 200)
        self.assertEqual(details["admin_resources_status"], 200)
        self.assertEqual(details["admin_resources_patch_status"], 200)
        self.assertEqual(details["admin_resources_invalid_patch_status"], 400)
        self.assertEqual(details["identity_governance_status"], 200)
        self.assertEqual(details["identity_governance_invalid_patch_status"], 400)
        self.assertEqual(details["identity_runtime_representations_status"], 200)
        self.assertIn(("GET", "http://frida.test/admin"), calls)
        self.assertIn(("GET", "http://frida.test/log"), calls)
        self.assertIn(("GET", "http://frida.test/hermeneutic-admin"), calls)
        self.assertIn(("GET", "http://frida.test/identity"), calls)
        self.assertIn(("GET", "http://frida.test/admin-old"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/settings"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/settings/resources"), calls)
        self.assertIn(("PATCH", "http://frida.test/api/admin/settings/resources"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/identity/governance"), calls)
        self.assertIn(("POST", "http://frida.test/api/admin/identity/governance"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/identity/runtime-representations"), calls)

    def test_check_api_smoke_calls_admin_endpoints_without_admin_token_header(self) -> None:
        original_http_json = minimal_validation._http_json
        admin_headers = []
        patch_payloads = []

        def fake_http_json(method: str, url: str, **kwargs):
            headers = kwargs.get("headers") or {}
            if "/api/admin/" in url:
                admin_headers.append(headers)
            if method == "PATCH" and url.endswith("/api/admin/settings/resources"):
                patch_payloads.append(kwargs.get("json"))
            if url.endswith("/"):
                return _FakeResponse(200, text="Frida")
            if url.endswith("/admin"):
                return _FakeResponse(200, text="Admin de configuration")
            if url.endswith("/log"):
                return _FakeResponse(200, text="Logs applicatifs")
            if url.endswith("/hermeneutic-admin"):
                return _FakeResponse(200, text="Hermeneutic admin")
            if url.endswith("/identity"):
                return _FakeResponse(200, text="Fiche identite pour le jugement")
            if url.endswith("/admin-old"):
                return _FakeResponse(404, text="not found")
            if url.endswith("/api/conversations?limit=1"):
                return _FakeResponse(200, payload={"ok": True, "items": []})
            if url.endswith("/api/admin/settings"):
                return _FakeResponse(200, payload=self._fake_admin_settings_payload())
            if url.endswith("/api/admin/settings/resources"):
                if method == "GET":
                    return _FakeResponse(200, payload=self._fake_resources_payload("env_seed"))
                if method == "PATCH":
                    if kwargs.get("json", {}).get("payload", {}).get("llm_identity_path", {}).get("value") == 123:
                        return _FakeResponse(
                            400,
                            payload={
                                "ok": False,
                                "error": "invalid text value for resources.llm_identity_path",
                            },
                        )
                    return _FakeResponse(200, payload=self._fake_resources_payload("admin_ui"))
            if url.endswith("/api/admin/identity/governance"):
                if method == "GET":
                    return _FakeResponse(
                        200,
                        payload={
                            "ok": True,
                            "governance_version": "v1",
                            "item_count": 15,
                        },
                    )
                if method == "POST":
                    return _FakeResponse(
                        400,
                        payload={
                            "ok": False,
                            "validation_error": "governance_key_readonly",
                        },
                    )
            if url.endswith("/api/admin/identity/runtime-representations"):
                return _FakeResponse(
                    200,
                    payload={
                        "ok": True,
                        "representations_version": "v1",
                    },
                )
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

        self.assertEqual(details["admin_settings_status"], 200)
        self.assertEqual(details["admin_resources_patch_status"], 200)
        self.assertEqual(details["admin_resources_invalid_patch_status"], 400)
        self.assertEqual(details["identity_runtime_representations_status"], 200)
        self.assertEqual(len(admin_headers), 8)
        self.assertEqual(admin_headers, [{}, {}, {}, {}, {}, {}, {}, {}])
        self.assertEqual(
            patch_payloads,
            [
                {
                    "updated_by": "minimal_validation",
                    "payload": {
                        "llm_identity_path": {"value": "data/identity/llm_identity.txt"},
                        "user_identity_path": {"value": "data/identity/user_identity.txt"},
                    },
                },
                {
                    "updated_by": "minimal_validation",
                    "payload": {
                        "llm_identity_path": {"value": 123},
                    },
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
