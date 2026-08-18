from __future__ import annotations

import inspect
import shutil
import sys
import tempfile
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
        sections = {}
        for section in runtime_settings.list_sections():
            payload = {}
            for field in runtime_settings.get_section_spec(section).fields:
                if field.is_secret:
                    payload[field.key] = {
                        "is_secret": True,
                        "is_set": False,
                        "origin": "env_seed",
                    }
            sections[section] = {
                "section": section,
                "payload": payload,
                "source": "env",
                "source_reason": "empty_table",
            }
        return {
            "ok": True,
            "sections": sections,
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
            section: section_payload["payload"]
            for section, section_payload in self._fake_admin_settings_payload()["sections"].items()
        }

        minimal_validation._assert_masked_secret_fields(section_payloads)

        section_payloads["agenda_agent"].pop("caldav_app_password")
        with self.assertRaisesRegex(
            RuntimeError,
            r"payload secret manquant pour agenda_agent\.caldav_app_password",
        ):
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
        self.assertIn("dashboard_html", details["files"])
        self.assertIn("log_html", details["files"])
        self.assertIn("hermeneutic_admin_html", details["files"])
        self.assertIn("identity_html", details["files"])
        self.assertIn("memory_admin_html", details["files"])
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
        self.assertIn("admin_settings_catalog_js", details["files"])
        self.assertIn("admin_js", details["files"])
        self.assertIn("hermeneutic_admin_api_js", details["files"])
        self.assertIn("hermeneutic_admin_render_js", details["files"])
        self.assertIn("hermeneutic_admin_render_identity_governance_js", details["files"])
        self.assertIn("hermeneutic_admin_main_js", details["files"])
        self.assertIn("identity_api_js", details["files"])
        self.assertIn("identity_render_runtime_representations_js", details["files"])
        self.assertIn("identity_main_js", details["files"])
        self.assertIn("memory_admin_api_js", details["files"])
        self.assertIn("memory_admin_render_overview_js", details["files"])
        self.assertIn("memory_admin_render_turns_js", details["files"])
        self.assertIn("memory_admin_main_js", details["files"])
        self.assertIn("dashboard_styles_css", details["files"])
        self.assertIn("dashboard_main_js", details["files"])
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
        self.assertEqual(
            details["memory_admin_script_srcs"],
            details["memory_admin_script_order"],
        )
        self.assertEqual(details["dashboard_script_srcs"], details["dashboard_script_order"])
        self.assertEqual(
            details["memory_admin_endpoints_found"],
            details["memory_admin_endpoints_expected"],
        )
        self.assertEqual(
            details["dashboard_endpoints_found"],
            details["dashboard_endpoints_expected"],
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
        self.assertNotIn('target="_blank"', details["index_hermeneutic_markers"])
        self.assertIn('href="/dashboard"', details["index_markers"])
        self.assertIn('href="/identity"', details["index_markers"])
        self.assertIn('href="/memory-admin"', details["index_markers"])
        self.assertIn("Dashboard long terme", details["dashboard_markers"])
        self.assertIn("/api/admin/logs", details["dashboard_forbidden_markers"])
        self.assertIn("Hermeneutic admin", details["hermeneutic_admin_markers"])
        self.assertIn("Logs applicatifs", details["log_markers"])
        self.assertIn("Les 4 blocs a editer en premier", details["identity_markers"])
        self.assertIn("Caps, budgets et legacy", details["identity_markers"])
        self.assertNotIn("Seuils et limites", details["identity_markers"])
        self.assertIn("Memory Admin", details["memory_admin_markers"])
        self.assertIn("admin_old_html", details["legacy_admin_assets_absent"])
        self.assertIn("admin_old_js", details["legacy_admin_assets_absent"])
        self.assertIn('id="rows"', details["admin_html_forbidden_markers"])
        self.assertIn('id="restart"', details["admin_html_forbidden_markers"])
        self.assertIn("/api/admin/logs", details["admin_js_forbidden_markers"])
        self.assertIn("/api/admin/restart", details["admin_js_forbidden_markers"])

    def test_check_ui_assets_delegates_to_named_responsibility_validators(self) -> None:
        from ui_asset_validation import check_ui_assets

        self.assertEqual(
            minimal_validation._check_ui_assets(),
            check_ui_assets(APP_DIR / "web"),
        )
        source = inspect.getsource(minimal_validation._check_ui_assets)
        self.assertNotIn("read_text", source)
        self.assertNotIn("re.findall", source)
        self.assertNotIn(".exists()", source)

    def test_check_ui_assets_rejects_admin_load_order_mutation_after_delegation(self) -> None:
        from ui_asset_validation import check_ui_assets

        with tempfile.TemporaryDirectory() as temp_dir:
            web_dir = Path(temp_dir) / "web"
            shutil.copytree(APP_DIR / "web", web_dir)
            admin_html_path = web_dir / "admin.html"
            admin_html = admin_html_path.read_text(encoding="utf-8")
            first = '<script src="admin_api.js"></script>'
            second = '<script src="admin_ui_common.js"></script>'
            mutated = admin_html.replace(first, "__SECOND__", 1)
            mutated = mutated.replace(second, first, 1).replace("__SECOND__", second, 1)
            self.assertNotEqual(mutated, admin_html)
            admin_html_path.write_text(mutated, encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "ordre scripts admin invalide"):
                check_ui_assets(web_dir)

    def test_check_ui_assets_preserves_first_failure_order_across_validators(self) -> None:
        from ui_asset_validation import check_ui_assets

        with tempfile.TemporaryDirectory() as temp_dir:
            web_dir = Path(temp_dir) / "web"
            shutil.copytree(APP_DIR / "web", web_dir)
            admin_html_path = web_dir / "admin.html"
            admin_html = admin_html_path.read_text(encoding="utf-8")
            admin_html_path.write_text(
                admin_html.replace('id="adminMainModelSave"', 'id="syntheticMissingHook"', 1),
                encoding="utf-8",
            )
            hermeneutic_api_path = web_dir / "hermeneutic_admin" / "api.js"
            hermeneutic_api = hermeneutic_api_path.read_text(encoding="utf-8")
            hermeneutic_api_path.write_text(
                hermeneutic_api.replace(
                    "/api/admin/hermeneutics/dashboard",
                    "/synthetic/missing/dashboard",
                    1,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "hooks DOM admin manquants"):
                check_ui_assets(web_dir)

    def test_check_api_smoke_verifies_admin_route_and_admin_old_absence(self) -> None:
        original_http_json = minimal_validation._http_json
        calls = []

        def fake_http_json(method: str, url: str, **kwargs):
            calls.append((method, url))
            if url.endswith("/"):
                return _FakeResponse(200, text="Frida")
            if url.endswith("/admin"):
                return _FakeResponse(200, text="Admin de configuration")
            if url == "http://frida.test/dashboard":
                return _FakeResponse(200, text="Dashboard long terme")
            if url.endswith("/log"):
                return _FakeResponse(200, text="Logs applicatifs")
            if url.endswith("/hermeneutic-admin"):
                return _FakeResponse(200, text="Hermeneutic admin")
            if url.endswith("/identity"):
                return _FakeResponse(200, text="Identity")
            if url.endswith("/memory-admin"):
                return _FakeResponse(200, text="Memory Admin")
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
            if url.endswith("/api/admin/memory/dashboard"):
                return _FakeResponse(
                    200,
                    payload={
                        "ok": True,
                        "surface": {"name": "Memory Admin"},
                    },
                )
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
        self.assertEqual(details["dashboard_status"], 200)
        self.assertEqual(details["log_status"], 200)
        self.assertEqual(details["hermeneutic_admin_status"], 200)
        self.assertEqual(details["identity_status"], 200)
        self.assertEqual(details["memory_admin_status"], 200)
        self.assertEqual(details["admin_old_status"], 404)
        self.assertEqual(details["admin_settings_status"], 200)
        self.assertEqual(details["admin_resources_status"], 200)
        self.assertEqual(details["admin_resources_patch_status"], 200)
        self.assertEqual(details["admin_resources_invalid_patch_status"], 400)
        self.assertEqual(details["identity_governance_status"], 200)
        self.assertEqual(details["identity_governance_invalid_patch_status"], 400)
        self.assertEqual(details["identity_runtime_representations_status"], 200)
        self.assertEqual(details["memory_dashboard_status"], 200)
        self.assertIn(("GET", "http://frida.test/admin"), calls)
        self.assertIn(("GET", "http://frida.test/dashboard"), calls)
        self.assertIn(("GET", "http://frida.test/log"), calls)
        self.assertIn(("GET", "http://frida.test/hermeneutic-admin"), calls)
        self.assertIn(("GET", "http://frida.test/identity"), calls)
        self.assertIn(("GET", "http://frida.test/memory-admin"), calls)
        self.assertIn(("GET", "http://frida.test/admin-old"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/settings"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/settings/resources"), calls)
        self.assertIn(("PATCH", "http://frida.test/api/admin/settings/resources"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/identity/governance"), calls)
        self.assertIn(("POST", "http://frida.test/api/admin/identity/governance"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/identity/runtime-representations"), calls)
        self.assertIn(("GET", "http://frida.test/api/admin/memory/dashboard"), calls)

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
            if url == "http://frida.test/dashboard":
                return _FakeResponse(200, text="Dashboard long terme")
            if url.endswith("/log"):
                return _FakeResponse(200, text="Logs applicatifs")
            if url.endswith("/hermeneutic-admin"):
                return _FakeResponse(200, text="Hermeneutic admin")
            if url.endswith("/identity"):
                return _FakeResponse(200, text="Identity")
            if url.endswith("/memory-admin"):
                return _FakeResponse(200, text="Memory Admin")
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
            if url.endswith("/api/admin/memory/dashboard"):
                return _FakeResponse(
                    200,
                    payload={
                        "ok": True,
                        "surface": {"name": "Memory Admin"},
                    },
                )
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
        self.assertEqual(details["memory_dashboard_status"], 200)
        self.assertEqual(len(admin_headers), 9)
        self.assertEqual(admin_headers, [{}, {}, {}, {}, {}, {}, {}, {}, {}])
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
