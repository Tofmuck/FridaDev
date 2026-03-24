from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class AdminPhase6ShellTests(unittest.TestCase):
    def test_admin_html_is_reserved_for_new_admin_shell(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")

        self.assertIn("Admin de configuration", html)
        self.assertIn('script src="admin.js"', html)
        self.assertIn('id="admin-phase6-note"', html)
        self.assertIn('id="admin-phase6-status"', html)
        self.assertIn("/api/admin/logs", html)
        self.assertIn("/api/admin/restart", html)
        self.assertIn("routes hermeneutiques backend restent hors UI admin V1", html)
        self.assertNotIn("Logs techniques", html)
        self.assertNotIn('id="rows"', html)
        self.assertNotIn('id="restart"', html)

    def test_admin_js_no_longer_contains_legacy_logs_restart_logic(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn('admin-phase6-status', source)
        self.assertIn('settings-v1-shell', source)
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

    def test_minimal_validation_tracks_phase6_admin_shell(self) -> None:
        source = (APP_DIR / "minimal_validation.py").read_text(encoding="utf-8")

        self.assertIn("Admin de configuration", source)
        self.assertIn('id="admin-phase6-status"', source)
        self.assertIn('settings-v1-shell', source)
        self.assertIn('/api/admin/logs?limit=1', source)
        self.assertIn('/api/admin/restart', (APP_DIR / "server.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
