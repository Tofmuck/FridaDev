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


class FrontendDashboardLot6Tests(unittest.TestCase):
    def test_dashboard_page_renders_first_screen_without_lot_labels(self) -> None:
        source = (APP_DIR / "web" / "dashboard.html").read_text(encoding="utf-8")
        scripts = re.findall(r'<script\s+src="([^"]+)"></script>', source)

        self.assertIn("<title>Dashboard long terme</title>", source)
        self.assertIn("<h1>Dashboard long terme</h1>", source)
        self.assertIn('class="admin-page dashboard-page"', source)
        self.assertIn('data-dashboard-screen="overview"', source)
        self.assertIn('id="dashboardPrimaryWindows"', source)
        self.assertIn('data-window="24h"', source)
        self.assertIn('data-window="7d"', source)
        self.assertIn('data-window="30d"', source)
        self.assertIn('<option value="today">', source)
        self.assertIn('<option value="yesterday">', source)
        self.assertIn('<option value="90d">', source)
        self.assertIn('<option value="custom">', source)
        self.assertIn("Frida maintenant", source)
        self.assertIn("A surveiller", source)
        self.assertIn('id="dashboardPulseCards"', source)
        self.assertIn('id="dashboardTrendCards"', source)
        self.assertIn('id="dashboardClassificationBars"', source)
        self.assertIn('id="dashboardMemoryBars"', source)
        self.assertIn('id="dashboardWebBars"', source)
        self.assertIn('id="dashboardConversationsTable"', source)
        self.assertEqual(scripts, ["admin_api.js", "dashboard/main.js"])
        self.assertNotIn("Lot 5", source)
        self.assertNotIn("content-free", source)
        self.assertNotIn("Frontieres", source)
        self.assertNotIn("Afficher le contenu complet", source)

    def test_dashboard_javascript_uses_dashboard_aggregates_not_log_payloads(self) -> None:
        source = (APP_DIR / "web" / "dashboard" / "main.js").read_text(encoding="utf-8")

        self.assertIn("/api/admin/dashboard/overview", source)
        self.assertIn("/api/admin/dashboard/conversations", source)
        self.assertIn("source.coverage", source)
        self.assertIn("metric_buckets", source)
        self.assertIn("agregats persistants", source)
        self.assertIn("Tours reussis", source)
        self.assertIn("Reponses degradees", source)
        self.assertIn("Problemes rencontres", source)
        self.assertIn("Latence moyenne", source)
        self.assertIn("dashboard_metric_buckets.providers", source)
        self.assertNotIn("/api/admin/logs", source)
        self.assertNotIn("event_limit", source)
        self.assertNotIn("Afficher le contenu complet", source)
        self.assertNotIn("prompt principal", source)
        self.assertNotIn("Latence p95", source)
        self.assertNotIn("providers.main_duration_ms_p95", source)

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
