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


class FrontendMemoryAdminPhase10eTests(unittest.TestCase):
    def test_page_exists_with_dedicated_memory_sections_and_shared_assets(self) -> None:
        source = (APP_DIR / "web" / "memory-admin.html").read_text(encoding="utf-8")
        found_scripts = re.findall(r'<script\s+src="([^"]+)"></script>', source)

        self.assertIn("<title>Memory Admin</title>", source)
        self.assertIn("<h1>Memory Admin</h1>", source)
        self.assertIn('href="admin.css"', source)
        self.assertIn("Surface dediee a l observabilite memoire / RAG", source)
        self.assertIn("Etat memoire durable", source)
        self.assertIn("Retrieval, embeddings et couverture recente", source)
        self.assertIn("Panier pre-arbitre, arbitre et runtime process-local", source)
        self.assertIn("Injection memoire et lecture recente", source)
        self.assertIn("Details memory/RAG par tour", source)
        self.assertIn("Decisions arbitre persistees", source)
        self.assertIn("persistance durable, agregat calcule, runtime process-local et historique logs", source)
        self.assertIn('href="/admin"', source)
        self.assertIn('href="/log"', source)
        self.assertIn('href="/identity"', source)
        self.assertIn('href="/hermeneutic-admin"', source)
        self.assertIn('href="/memory-admin"', source)
        self.assertEqual(
            found_scripts,
            [
                "admin_api.js",
                "admin_ui_common.js",
                "memory_admin/api.js",
                "memory_admin/render_overview.js",
                "memory_admin/render_turns.js",
                "memory_admin/main.js",
            ],
        )

    def test_page_scripts_live_in_dedicated_directory_and_use_only_allowed_endpoints(self) -> None:
        api_source = (APP_DIR / "web" / "memory_admin" / "api.js").read_text(encoding="utf-8")
        overview_source = (APP_DIR / "web" / "memory_admin" / "render_overview.js").read_text(
            encoding="utf-8"
        )
        turns_source = (APP_DIR / "web" / "memory_admin" / "render_turns.js").read_text(encoding="utf-8")
        main_source = (APP_DIR / "web" / "memory_admin" / "main.js").read_text(encoding="utf-8")

        combined = f"{api_source}\n{overview_source}\n{turns_source}\n{main_source}"
        found_endpoints = set(
            re.findall(
                r"/api/admin/(?:memory/dashboard|logs/chat(?:/metadata)?|hermeneutics/arbiter-decisions)",
                combined,
            )
        )
        self.assertEqual(
            found_endpoints,
            {
                "/api/admin/memory/dashboard",
                "/api/admin/logs/chat",
                "/api/admin/logs/chat/metadata",
                "/api/admin/hermeneutics/arbiter-decisions",
            },
        )
        self.assertNotIn("/api/admin/hermeneutics/dashboard", combined)
        self.assertNotIn("/api/admin/identity/read-model", combined)
        self.assertLessEqual(len(api_source.splitlines()), 499)
        self.assertLessEqual(len(overview_source.splitlines()), 499)
        self.assertLessEqual(len(turns_source.splitlines()), 499)
        self.assertLessEqual(len(main_source.splitlines()), 499)

    def test_memory_admin_navigation_link_is_present_on_required_surfaces(self) -> None:
        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        log_source = (APP_DIR / "web" / "log.html").read_text(encoding="utf-8")
        hermeneutic_source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")
        identity_source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")
        memory_admin_source = (APP_DIR / "web" / "memory-admin.html").read_text(encoding="utf-8")

        self.assertIn('id="btnMemoryAdmin"', index_source)
        self.assertIn('href="/memory-admin"', index_source)
        self.assertIn('href="/memory-admin"', admin_source)
        self.assertIn('href="/memory-admin"', log_source)
        self.assertIn('href="/memory-admin"', hermeneutic_source)
        self.assertIn('href="/memory-admin"', identity_source)
        self.assertIn('href="/memory-admin"', memory_admin_source)


if __name__ == "__main__":
    unittest.main()
