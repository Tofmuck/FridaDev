from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class AppPhase8Tests(unittest.TestCase):
    def test_settings_button_points_to_admin_route(self) -> None:
        source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('window.location.href = "/admin";', source)
        self.assertNotIn('window.location.href = "admin.html";', source)

    def test_admin_route_alignment_stays_server_side(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertIn('@app.get("/admin")', source)
        self.assertIn('return send_from_directory(app.static_folder, "admin.html")', source)


if __name__ == "__main__":
    unittest.main()
