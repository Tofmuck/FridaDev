from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class AppPhase8Tests(unittest.TestCase):
    def test_settings_button_points_to_admin_route(self) -> None:
        html_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        js_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="btnSettings"', html_source)
        self.assertIn('class="icon-link"', html_source)
        self.assertIn('href="/admin"', html_source)
        self.assertNotIn('href="admin.html"', html_source)
        self.assertNotIn('window.location.href = "/admin";', js_source)
        self.assertNotIn('window.location.href = "admin.html";', js_source)

    def test_admin_route_alignment_stays_server_side(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertIn('@app.get("/admin")', source)
        self.assertIn('return send_from_directory(app.static_folder, "admin.html")', source)

    def test_session_storage_drops_sampling_fields(self) -> None:
        source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('localStorage.setItem("frida.settings", JSON.stringify(cfg));', source)
        self.assertIn("max_tokens: Number(max_tokens.value)", source)
        self.assertNotIn("temperature: Number(temperature.value)", source)
        self.assertNotIn("top_p: Number(top_p.value)", source)
        self.assertNotIn("cfg.temperature", source)
        self.assertNotIn("cfg.top_p", source)
        self.assertNotIn("temperature.value", source)
        self.assertNotIn("top_p.value", source)
        self.assertNotIn("syncRangeBadges", source)

    def test_chat_request_keeps_session_only_controls(self) -> None:
        source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("max_tokens: cfg.max_tokens,", source)
        self.assertNotIn("system: cfg.system,", source)
        self.assertNotIn("const SYSTEM_PROMPT =", source)
        self.assertNotIn("temperature: cfg.temperature,", source)
        self.assertNotIn("top_p: cfg.top_p,", source)

    def test_session_panel_requalifies_sampling_and_max_tokens(self) -> None:
        source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn("<h3>Reglages de session</h3>", source)
        self.assertIn("`temperature` et `top_p` sont maintenant portes par la configuration globale des modeles dans l'admin.", source)
        self.assertIn("Reglage de session local, hors admin V1.", source)
        self.assertNotIn('id="temperature"', source)
        self.assertNotIn('id="temperatureVal"', source)
        self.assertNotIn('id="top_p"', source)
        self.assertNotIn('id="toppVal"', source)
        self.assertIn('id="max_tokens"', source)
        self.assertNotIn('id="system"', source)
        self.assertIn("Le prompt systeme global est maintenant porte par le backend et visible dans l'admin.", source)

    def test_admin_ui_keeps_max_tokens_and_system_prompt_out_of_v1(self) -> None:
        source = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")

        self.assertNotIn('id="max_tokens"', source)
        self.assertNotIn('id="system"', source)
        self.assertNotIn("Prompt système", source)

    def test_main_front_exposes_no_legacy_logs_restart_entry(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertNotIn("/api/admin/logs", app_source)
        self.assertNotIn("/api/admin/restart", app_source)
        self.assertNotIn("admin-old", app_source)
        self.assertNotIn("Logs admin", index_source)
        self.assertNotIn("Restart", index_source)
        self.assertNotIn("admin-old", index_source)


if __name__ == "__main__":
    unittest.main()
