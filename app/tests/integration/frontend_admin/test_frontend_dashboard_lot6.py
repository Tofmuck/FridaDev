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
        self.assertIn('id="dashboardSummariesTotal"', source)
        self.assertIn('id="dashboardSummariesBars"', source)
        self.assertIn('id="dashboardWebBars"', source)
        self.assertIn('id="dashboardConversationsTable"', source)
        self.assertIn('id="dashboardDrilldown"', source)
        self.assertIn('id="dashboardTurnsList"', source)
        self.assertIn('id="dashboardInspectionBody"', source)
        self.assertNotIn('<th scope="col">Inspection</th>', source)
        self.assertIn("Inspection traduite", source)
        self.assertEqual(scripts, ["admin_api.js", "dashboard/main.js"])
        self.assertNotIn("Lot 5", source)
        self.assertNotIn("content-free", source)
        self.assertNotIn("Frontieres", source)
        self.assertNotIn("RAW PROMPT MUST NOT LEAK", source)

    def test_dashboard_javascript_uses_dashboard_aggregates_not_log_payloads(self) -> None:
        source = (APP_DIR / "web" / "dashboard" / "main.js").read_text(encoding="utf-8")

        self.assertIn("/api/admin/dashboard/overview", source)
        self.assertIn("/api/admin/dashboard/conversations", source)
        self.assertIn("/api/admin/dashboard/turns/", source)
        self.assertIn("dashboardDrilldown", source)
        self.assertIn("dashboardInspectionBody", source)
        self.assertIn("source.coverage", source)
        self.assertIn("metric_buckets", source)
        self.assertIn("agregats persistants", source)
        self.assertIn("Tours reussis", source)
        self.assertIn("Reponses degradees", source)
        self.assertIn("Problemes rencontres", source)
        self.assertIn("Latence moyenne", source)
        self.assertIn("dashboard_metric_buckets.providers", source)
        self.assertIn("summaries_health", source)
        self.assertIn("Resumes persistants", (APP_DIR / "web" / "dashboard.html").read_text(encoding="utf-8"))
        self.assertIn("/api/admin/dashboard/turns/", source)
        self.assertIn("/content?", source)
        self.assertIn("Afficher le contenu complet", source)
        self.assertIn("dashboard-content-gate", source)
        self.assertIn("dashboard-conversation-open", source)
        self.assertNotIn("/api/admin/logs", source)
        self.assertNotIn("event_limit", source)
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

    def test_admin_surfaces_have_harmonized_navigation_and_roles(self) -> None:
        expected_links = [
            'href="/"',
            'href="/dashboard"',
            'href="/log"',
            'href="/memory-admin"',
            'href="/hermeneutic-admin"',
            'href="/identity"',
            'href="/admin"',
        ]
        surfaces = {
            "dashboard.html": ("global-dashboard", "/dashboard"),
            "log.html": ("technical-debug", "/log"),
            "memory-admin.html": ("memory-domain", "/memory-admin"),
            "hermeneutic-admin.html": ("hermeneutic-domain", "/hermeneutic-admin"),
            "identity.html": ("identity-editor", "/identity"),
            "admin.html": ("runtime-settings", "/admin"),
        }
        expected_nav = [
            ("/", "Chat"),
            ("/dashboard", "Dashboard"),
            ("/log", "Logs"),
            ("/memory-admin", "Memory Admin"),
            ("/hermeneutic-admin", "Hermeneutic Admin"),
            ("/identity", "Identity"),
            ("/admin", "Admin"),
        ]

        for filename, (role, current_href) in surfaces.items():
            with self.subTest(filename=filename):
                source = (APP_DIR / "web" / filename).read_text(encoding="utf-8")
                self.assertIn(f'data-surface-role="{role}"', source)
                self.assertIn(f'href="{current_href}" aria-current="page"', source)
                positions = [source.index(marker) for marker in expected_links]
                self.assertEqual(positions, sorted(positions))
                nav_match = re.search(
                    r'<nav class="admin-global-nav" aria-label="Navigation globale">(?P<nav>.*?)</nav>',
                    source,
                    re.S,
                )
                self.assertIsNotNone(nav_match)
                nav_html = nav_match.group("nav")
                nav_links = re.findall(
                    r'<a class="admin-nav-link" href="([^"]+)"(?: aria-current="page")?>([^<]+)</a>',
                    nav_html,
                )
                self.assertEqual(nav_links, expected_nav)
                self.assertNotIn("Actualiser", nav_html)

        chat_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        chat_nav_match = re.search(
            r'<nav class="right global-nav" aria-label="Navigation globale">(?P<nav>.*?)</nav>',
            chat_source,
            re.S,
        )
        self.assertIsNotNone(chat_nav_match)
        chat_nav_html = chat_nav_match.group("nav")
        chat_nav_links = re.findall(
            r'<a id="[^"]+" class="icon-link" title="[^"]+" href="([^"]+)"(?: aria-current="page")?>([^<]+)</a>',
            chat_nav_html,
        )
        self.assertEqual(chat_nav_links, expected_nav)
        self.assertIn('href="/" aria-current="page"', chat_nav_html)

        dashboard_source = (APP_DIR / "web" / "dashboard.html").read_text(encoding="utf-8")
        log_source = (APP_DIR / "web" / "log.html").read_text(encoding="utf-8")
        memory_source = (APP_DIR / "web" / "memory-admin.html").read_text(encoding="utf-8")
        hermeneutic_source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")
        identity_source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")

        self.assertIn("Lecture globale: pouls, conversations et inspection traduite", dashboard_source)
        self.assertIn("surface de debug technique", log_source)
        self.assertIn("Memory Admin garde le diagnostic memoire/RAG", memory_source)
        self.assertIn("Hermeneutic admin garde le diagnostic domaine", hermeneutic_source)
        self.assertIn("Identity reste la surface canonique d'edition", identity_source)


if __name__ == "__main__":
    unittest.main()
