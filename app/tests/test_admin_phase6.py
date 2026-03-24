from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class AdminPhase7FoundationTests(unittest.TestCase):
    def test_admin_html_uses_phase7_foundation_layout(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")

        self.assertIn("Admin de configuration", html)
        self.assertIn('href="admin.css"', html)
        self.assertIn('script src="admin.js"', html)
        self.assertIn('id="adminRefresh"', html)
        self.assertIn('id="adminTokenButton"', html)
        self.assertIn('id="adminStatusBanner"', html)
        self.assertIn('id="adminSectionGrid"', html)
        self.assertIn("L'edition detaillee arrive par tranches.", html)
        self.assertIn("Les routes hermeneutiques backend restent hors UI admin V1.", html)
        self.assertNotIn("Logs techniques", html)
        self.assertNotIn('id="rows"', html)
        self.assertNotIn('id="restart"', html)

    def test_admin_css_is_minimal_derivation_of_front_tokens(self) -> None:
        source = (APP_DIR / "web" / "admin.css").read_text(encoding="utf-8")

        self.assertIn("Derived from styles.css tokens", source)
        self.assertIn("--bg-base", source)
        self.assertIn("--accent", source)
        self.assertNotIn(".sidebar {", source)
        self.assertNotIn(".main {", source)

    def test_admin_js_uses_runtime_status_flow_without_legacy_logs_restart_logic(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn("/api/admin/settings/status", source)
        self.assertIn("frida.adminToken", source)
        self.assertIn("adminSectionGrid", source)
        self.assertIn("sessionStorage", source)
        self.assertNotIn("/api/admin/logs", source)
        self.assertNotIn("/api/admin/restart", source)
        self.assertNotIn("loadLogs", source)
        self.assertNotIn("restartService", source)

    def test_admin_old_assets_are_not_present(self) -> None:
        self.assertFalse((APP_DIR / "web" / "admin-old.html").exists())
        self.assertFalse((APP_DIR / "web" / "admin-old.js").exists())

    def test_server_does_not_expose_admin_old_route(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertNotIn('@app.get("/admin-old")', source)
        self.assertNotIn("admin-old.html", source)

    def test_minimal_validation_tracks_phase7_foundation(self) -> None:
        source = (APP_DIR / "minimal_validation.py").read_text(encoding="utf-8")

        self.assertIn("Admin de configuration", source)
        self.assertIn('href="admin.css"', source)
        self.assertIn('id="adminStatusBanner"', source)
        self.assertIn("/api/admin/settings/status", source)
        self.assertIn("frida.adminToken", source)
        self.assertIn('/api/admin/logs?limit=1', source)
        self.assertIn('/api/admin/restart', (APP_DIR / "server.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
