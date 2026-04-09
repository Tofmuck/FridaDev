from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class FrontendHermeneuticAdminPhase6Tests(unittest.TestCase):
    def test_page_exists_with_expected_title_sections_and_shared_assets(self) -> None:
        source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")

        self.assertIn("<title>Hermeneutic admin</title>", source)
        self.assertIn("<h1>Hermeneutic admin</h1>", source)
        self.assertIn('href="admin.css"', source)
        self.assertIn('script src="admin_api.js"', source)
        self.assertIn('script src="admin_ui_common.js"', source)
        self.assertIn('script src="hermeneutic_admin/api.js"', source)
        self.assertIn('script src="hermeneutic_admin/render.js"', source)
        self.assertIn('script src="hermeneutic_admin/render_identity_read_model.js"', source)
        self.assertIn('script src="hermeneutic_admin/render_identity_static_editor.js"', source)
        self.assertIn('script src="hermeneutic_admin/render_identity_mutable_editor.js"', source)
        self.assertIn('script src="hermeneutic_admin/render_identity_governance.js"', source)
        self.assertIn('script src="hermeneutic_admin/main.js"', source)
        self.assertIn("Vue d'ensemble", source)
        self.assertIn("Inspection par tour", source)
        self.assertIn("Decisions arbitre", source)
        self.assertIn("Vue unifiee identity", source)
        self.assertIn("edition mutable + statique", source)
        self.assertIn("edition mutable", source)
        self.assertIn("pilotage systeme reste distinct", source)
        self.assertIn("Representations runtime identity", source)
        self.assertIn("Identity</a> n'en garde qu'un rappel compact", source)
        self.assertIn("Gouvernance identity", source)
        self.assertIn("IDENTITY_TOP_N", source)
        self.assertIn("Fragments legacy d'identite", source)
        self.assertIn("static + mutable narrative", source)
        self.assertIn("identity_mutables", source)
        self.assertIn("Corrections recentes", source)
        self.assertIn('href="/admin"', source)
        self.assertIn('href="/log"', source)
        self.assertIn('href="/identity"', source)
        self.assertIn('id="hermeneuticAdminModeMetaNote"', source)
        self.assertNotIn('href="/admin" target="_blank"', source)
        self.assertNotIn('href="/log" target="_blank"', source)

    def test_page_scripts_live_in_dedicated_directory_and_use_only_allowed_endpoints(self) -> None:
        html = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")
        api_source = (APP_DIR / "web" / "hermeneutic_admin" / "api.js").read_text(encoding="utf-8")
        render_source = (APP_DIR / "web" / "hermeneutic_admin" / "render.js").read_text(encoding="utf-8")
        identity_render_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_read_model.js"
        ).read_text(encoding="utf-8")
        identity_static_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_static_editor.js"
        ).read_text(encoding="utf-8")
        identity_edit_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_mutable_editor.js"
        ).read_text(encoding="utf-8")
        identity_governance_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_governance.js"
        ).read_text(encoding="utf-8")
        main_source = (APP_DIR / "web" / "hermeneutic_admin" / "main.js").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        log_source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")

        found_scripts = re.findall(r'<script\s+src="([^"]+)"></script>', html)
        self.assertEqual(
            found_scripts,
            [
                "admin_api.js",
                "admin_ui_common.js",
                "hermeneutic_admin/api.js",
                "hermeneutic_admin/render.js",
                "hermeneutic_admin/render_identity_read_model.js",
                "hermeneutic_admin/render_identity_static_editor.js",
                "hermeneutic_admin/render_identity_mutable_editor.js",
                "hermeneutic_admin/render_identity_governance.js",
                "identity/render_identity_runtime_representations.js",
                "hermeneutic_admin/main.js",
            ],
        )

        combined = (
            f"{api_source}\n{render_source}\n{identity_render_source}\n"
            f"{identity_static_source}\n{identity_edit_source}\n"
            f"{identity_governance_source}\n{main_source}"
        )
        found_endpoints = set(
            re.findall(
                r"/api/admin/(?:hermeneutics/[a-z-]+|identity/(?:read-model|runtime-representations|mutable|static|governance)|logs/chat(?:/metadata)?)",
                combined,
            )
        )
        self.assertEqual(
            found_endpoints,
            {
                "/api/admin/hermeneutics/dashboard",
                "/api/admin/identity/read-model",
                "/api/admin/identity/runtime-representations",
                "/api/admin/identity/mutable",
                "/api/admin/identity/static",
                "/api/admin/identity/governance",
                "/api/admin/hermeneutics/identity-candidates",
                "/api/admin/hermeneutics/arbiter-decisions",
                "/api/admin/hermeneutics/corrections-export",
                "/api/admin/logs/chat",
                "/api/admin/logs/chat/metadata",
            },
        )
        self.assertNotIn("/api/admin/hermeneutics/dashboard", admin_source)
        self.assertNotIn("/api/admin/hermeneutics/dashboard", log_source)
        self.assertNotIn("/api/admin/logs/chat/metadata", admin_source)
        self.assertNotIn("/api/admin/hermeneutics/identity/force-accept", combined)
        self.assertNotIn("/api/admin/hermeneutics/identity/force-reject", combined)
        self.assertNotIn("/api/admin/hermeneutics/identity/relabel", combined)
        self.assertIn("FridaHermeneuticIdentityReadModelRender", identity_render_source)
        self.assertIn("FridaHermeneuticIdentityStaticEditor", identity_static_source)
        self.assertIn("FridaHermeneuticIdentityMutableEditor", identity_edit_source)
        self.assertIn("FridaHermeneuticIdentityGovernance", identity_governance_source)
        self.assertIn("FridaHermeneuticIdentityReadModelRender", render_source)
        self.assertIn("fetchIdentityRuntimeRepresentations", api_source)
        self.assertIn("mode_observation", render_source)
        self.assertIn("Observe depuis", main_source)
        self.assertIn("bascule exacte", render_source)
        self.assertIn("compile=", render_source)
        self.assertNotIn("prompt=", render_source)
        self.assertIn("Repères runtime et compilation active", identity_render_source)
        self.assertIn("pilotage_systeme=distinct", identity_render_source)
        self.assertLessEqual(len(render_source.splitlines()), 499)
        self.assertLessEqual(len(api_source.splitlines()), 499)
        self.assertLessEqual(len(main_source.splitlines()), 499)
        self.assertLessEqual(len(identity_render_source.splitlines()), 499)
        self.assertLessEqual(len(identity_static_source.splitlines()), 499)
        self.assertLessEqual(len(identity_edit_source.splitlines()), 499)
        self.assertLessEqual(len(identity_governance_source.splitlines()), 499)

    def test_page_exposes_read_only_pipeline_inspection_hooks(self) -> None:
        source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")

        self.assertIn('id="hermeneuticConversationId"', source)
        self.assertIn('id="hermeneuticTurnId"', source)
        self.assertIn('id="hermeneuticTurnStages"', source)
        self.assertIn('id="hermeneuticArbiterList"', source)
        self.assertIn('id="hermeneuticIdentityStaticEditStatus"', source)
        self.assertIn('id="hermeneuticIdentityStaticEditors"', source)
        self.assertIn('id="hermeneuticIdentityMutableEditStatus"', source)
        self.assertIn('id="hermeneuticIdentityMutableEditors"', source)
        self.assertIn('id="hermeneuticIdentityGovernanceStatus"', source)
        self.assertIn('id="hermeneuticIdentityGovernanceMeta"', source)
        self.assertIn('id="hermeneuticIdentityGovernance"', source)
        self.assertIn('id="hermeneuticIdentityReadModel"', source)
        self.assertIn('id="hermeneuticIdentityRuntimeMeta"', source)
        self.assertIn('id="hermeneuticIdentityStructuredRepresentation"', source)
        self.assertIn('id="hermeneuticIdentityInjectedRepresentation"', source)
        self.assertIn('id="hermeneuticIdentityList"', source)
        self.assertIn('id="hermeneuticCorrectionsList"', source)
        self.assertIn("stimmung_agent", source)
        self.assertIn("hermeneutic_node_insertion", source)
        self.assertIn("primary_node", source)
        self.assertIn("validation_agent", source)
        self.assertIn('id="hermeneuticIdentityLegacyNote"', source)
        self.assertNotIn("force_accept", source)
        self.assertNotIn("force_reject", source)
        self.assertNotIn("relabel", source)


if __name__ == "__main__":
    unittest.main()
