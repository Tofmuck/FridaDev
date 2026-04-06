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
        self.assertIn('script src="hermeneutic_admin/main.js"', source)
        self.assertIn("Vue d'ensemble", source)
        self.assertIn("Inspection par tour", source)
        self.assertIn("Decisions arbitre", source)
        self.assertIn("Vue unifiee identity", source)
        self.assertIn("Fragments legacy d'identite", source)
        self.assertIn("static + mutable narrative", source)
        self.assertIn("identity_mutables", source)
        self.assertIn("Corrections recentes", source)
        self.assertIn('href="/admin"', source)
        self.assertIn('href="/log"', source)
        self.assertNotIn('href="/admin" target="_blank"', source)
        self.assertNotIn('href="/log" target="_blank"', source)

    def test_page_scripts_live_in_dedicated_directory_and_use_only_allowed_endpoints(self) -> None:
        html = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")
        api_source = (APP_DIR / "web" / "hermeneutic_admin" / "api.js").read_text(encoding="utf-8")
        render_source = (APP_DIR / "web" / "hermeneutic_admin" / "render.js").read_text(encoding="utf-8")
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
                "hermeneutic_admin/main.js",
            ],
        )

        combined = f"{api_source}\n{render_source}\n{main_source}"
        found_endpoints = set(
            re.findall(
                r"/api/admin/(?:hermeneutics/[a-z-]+|identity/read-model|logs/chat(?:/metadata)?)",
                combined,
            )
        )
        self.assertEqual(
            found_endpoints,
            {
                "/api/admin/hermeneutics/dashboard",
                "/api/admin/identity/read-model",
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

    def test_page_exposes_read_only_pipeline_inspection_hooks(self) -> None:
        source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")

        self.assertIn('id="hermeneuticConversationId"', source)
        self.assertIn('id="hermeneuticTurnId"', source)
        self.assertIn('id="hermeneuticTurnStages"', source)
        self.assertIn('id="hermeneuticArbiterList"', source)
        self.assertIn('id="hermeneuticIdentityReadModel"', source)
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
