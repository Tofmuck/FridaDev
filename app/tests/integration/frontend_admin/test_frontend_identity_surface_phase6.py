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


class FrontendIdentitySurfacePhase6Tests(unittest.TestCase):
    def test_identity_page_exists_with_expected_french_sections_and_shared_assets(self) -> None:
        source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")
        found_scripts = re.findall(r'<script\s+src="([^"]+)"></script>', source)

        self.assertIn("<title>Identity</title>", source)
        self.assertIn("<h1>Identity</h1>", source)
        self.assertIn('href="admin.css"', source)
        self.assertNotIn('href="styles.css"', source)
        self.assertIn("Comment l'identite circule", source)
        self.assertIn("Etat courant par sujet", source)
        self.assertIn("Fiche identite pour le jugement", source)
        self.assertIn("Texte identity injecte au modele", source)
        self.assertIn("Editer le statique canonique", source)
        self.assertIn("Editer la mutable canonique", source)
        self.assertIn("Seuils et limites", source)
        self.assertIn("Legacy, evidences et conflits", source)
        self.assertIn("Corrections recentes et sorties utiles", source)
        self.assertIn('href="/"', source)
        self.assertIn('href="/admin"', source)
        self.assertIn('href="/log"', source)
        self.assertIn('href="/hermeneutic-admin"', source)
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
                "identity/api.js",
                "identity/render_identity_runtime_representations.js",
                "identity/main.js",
            ],
        )

    def test_identity_navigation_links_exist_on_required_surfaces(self) -> None:
        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        log_source = (APP_DIR / "web" / "log.html").read_text(encoding="utf-8")
        hermeneutic_source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")
        identity_source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")

        self.assertIn('href="/identity"', index_source)
        self.assertIn('href="/identity"', admin_source)
        self.assertIn('href="/identity"', log_source)
        self.assertIn('href="/identity"', hermeneutic_source)
        self.assertIn('href="/"', identity_source)
        self.assertIn('href="/admin"', identity_source)
        self.assertIn('href="/log"', identity_source)
        self.assertIn('href="/hermeneutic-admin"', identity_source)

    def test_identity_page_uses_runtime_representations_route_and_files_stay_bounded(self) -> None:
        api_source = (APP_DIR / "web" / "identity" / "api.js").read_text(encoding="utf-8")
        shared_api_source = (APP_DIR / "web" / "hermeneutic_admin" / "api.js").read_text(
            encoding="utf-8"
        )
        main_source = (APP_DIR / "web" / "identity" / "main.js").read_text(encoding="utf-8")
        render_source = (
            APP_DIR / "web" / "identity" / "render_identity_runtime_representations.js"
        ).read_text(encoding="utf-8")

        combined = f"{shared_api_source}\n{api_source}\n{main_source}\n{render_source}"
        found_endpoints = set(
            re.findall(
                r"/api/admin/(?:identity/(?:read-model|runtime-representations|mutable|static|governance)|hermeneutics/corrections-export)",
                combined,
            )
        )
        self.assertEqual(
            found_endpoints,
            {
                "/api/admin/identity/read-model",
                "/api/admin/identity/runtime-representations",
                "/api/admin/identity/mutable",
                "/api/admin/identity/static",
                "/api/admin/identity/governance",
                "/api/admin/hermeneutics/corrections-export",
            },
        )
        self.assertNotIn("/api/admin/hermeneutics/identity/force-accept", combined)
        self.assertNotIn("/api/admin/hermeneutics/identity/force-reject", combined)
        self.assertNotIn("/api/admin/hermeneutics/identity/relabel", combined)
        self.assertLessEqual(len(api_source.splitlines()), 499)
        self.assertLessEqual(len(main_source.splitlines()), 499)
        self.assertLessEqual(len(render_source.splitlines()), 499)


if __name__ == "__main__":
    unittest.main()
