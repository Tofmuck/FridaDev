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


class FrontendDashboardLot5Tests(unittest.TestCase):
    def test_dashboard_page_exists_with_shared_assets_and_no_data_widgets(self) -> None:
        source = (APP_DIR / "web" / "dashboard.html").read_text(encoding="utf-8")
        scripts = re.findall(r'<script\s+src="([^"]+)"></script>', source)

        self.assertIn("<title>Dashboard long terme</title>", source)
        self.assertIn("<h1>Dashboard long terme</h1>", source)
        self.assertIn('class="admin-page dashboard-page"', source)
        self.assertIn('href="admin.css"', source)
        self.assertIn('href="dashboard/styles.css"', source)
        self.assertIn('data-dashboard-skeleton="lot5"', source)
        self.assertIn('id="dashboardStatusBanner"', source)
        self.assertIn('id="dashboardGlobalSlot"', source)
        self.assertIn('id="dashboardConversationsSlot"', source)
        self.assertIn("Pouls global", source)
        self.assertIn("Conversations", source)
        self.assertIn("Agregats persistants", source)
        self.assertIn("Action explicite", source)
        self.assertEqual(scripts, ["dashboard/main.js"])
        self.assertNotIn("/api/admin/dashboard/overview", source)
        self.assertNotIn("/api/admin/dashboard/conversations", source)
        self.assertNotIn("Afficher le contenu complet", source)

    def test_dashboard_javascript_is_minimal_inert_and_content_free(self) -> None:
        source = (APP_DIR / "web" / "dashboard" / "main.js").read_text(encoding="utf-8")

        self.assertIn("dashboard_skeleton_lot5", source)
        self.assertIn("fridaDashboardSkeleton", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("/api/admin/dashboard", source)
        self.assertNotIn("Afficher le contenu complet", source)

    def test_dashboard_navigation_is_present_on_chat_and_admin_surfaces(self) -> None:
        paths = [
            APP_DIR / "web" / "index.html",
            APP_DIR / "web" / "admin.html",
            APP_DIR / "web" / "log.html",
            APP_DIR / "web" / "memory-admin.html",
            APP_DIR / "web" / "hermeneutic-admin.html",
            APP_DIR / "web" / "identity.html",
            APP_DIR / "web" / "dashboard.html",
        ]

        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn('href="/dashboard"', source)

        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="btnDashboard"', index_source)
        self.assertIn('class="icon-link"', index_source)


if __name__ == "__main__":
    unittest.main()
