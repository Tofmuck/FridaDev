from __future__ import annotations

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


class FrontendLogsPhase5Tests(unittest.TestCase):
    def test_index_exposes_log_entry_next_to_admin(self) -> None:
        html = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="btnLogs"', html)
        self.assertIn('href="/log"', html)
        self.assertIn('id="btnSettings"', html)
        self.assertIn('href="/admin"', html)
        self.assertNotIn('href="log.html"', html)

    def test_log_page_reuses_admin_css_and_dedicated_log_js(self) -> None:
        source = (APP_DIR / "web" / "log.html").read_text(encoding="utf-8")

        self.assertIn('class="admin-page"', source)
        self.assertIn('href="admin.css"', source)
        self.assertIn('script src="admin_api.js"', source)
        self.assertIn('script src="log/log.js"', source)
        self.assertIn('id="logFiltersForm"', source)
        self.assertIn('id="deleteConversationLogs"', source)
        self.assertIn('id="deleteTurnLogs"', source)
        self.assertNotIn("all_logs", source)
        self.assertNotIn("delete all logs", source.lower())

    def test_log_js_uses_admin_logs_chat_read_and_delete_only(self) -> None:
        source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn("/api/admin/logs/chat", source)
        self.assertIn('method: "DELETE"', source)
        self.assertIn('deleteLogs("conversation")', source)
        self.assertIn('deleteLogs("turn")', source)
        self.assertNotIn("all_logs", source)
        self.assertNotIn("/api/admin/logs/chat", admin_source)

    def test_log_js_sorts_events_inside_turn_in_chronological_order(self) -> None:
        source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")

        self.assertIn("const compareEventsChronoAsc", source)
        self.assertIn("Date.parse(toText(left?.ts))", source)
        self.assertIn("Date.parse(toText(right?.ts))", source)
        self.assertIn("group.events.sort(compareEventsChronoAsc)", source)

    def test_server_exposes_log_static_route(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertIn('@app.get("/log")', source)
        self.assertIn('return send_from_directory(app.static_folder, "log.html")', source)


if __name__ == "__main__":
    unittest.main()
