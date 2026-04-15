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

    def test_hermeneutic_admin_link_opens_in_new_tab_from_chat_surface(self) -> None:
        html_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        js_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="btnHermeneuticAdmin"', html_source)
        self.assertIn('href="/hermeneutic-admin"', html_source)
        self.assertIn('target="_blank"', html_source)
        self.assertIn('rel="noopener noreferrer"', html_source)
        self.assertNotIn('window.location.href = "/hermeneutic-admin";', js_source)
        self.assertNotIn('window.open("/hermeneutic-admin"', js_source)

    def test_admin_route_alignment_stays_server_side(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertIn('@app.get("/admin")', source)
        self.assertIn('return send_from_directory(app.static_folder, "admin.html")', source)

    def test_main_front_no_longer_persists_legacy_max_tokens_session_override(self) -> None:
        source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('localStorage.removeItem("frida.settings");', source)
        self.assertNotIn('localStorage.setItem("frida.settings", JSON.stringify(cfg));', source)
        self.assertNotIn('localStorage.getItem("frida.settings")', source)
        self.assertNotIn("temperature: Number(temperature.value)", source)
        self.assertNotIn("top_p: Number(top_p.value)", source)
        self.assertNotIn("cfg.temperature", source)
        self.assertNotIn("cfg.top_p", source)
        self.assertNotIn("temperature.value", source)
        self.assertNotIn("top_p.value", source)
        self.assertNotIn("syncRangeBadges", source)

    def test_chat_request_no_longer_sends_first_party_max_tokens_override(self) -> None:
        source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("max_tokens: cfg.max_tokens,", source)
        self.assertNotIn("const currentSettings = () =>", source)
        self.assertNotIn("system: cfg.system,", source)
        self.assertNotIn("MAX_CONTEXT_MESSAGES", source)
        self.assertNotIn("const SYSTEM_PROMPT =", source)
        self.assertNotIn("temperature: cfg.temperature,", source)
        self.assertNotIn("top_p: cfg.top_p,", source)
        self.assertNotIn('const panel = $("#panel");', source)

    def test_frontend_keeps_backend_as_prompt_source_of_truth(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertNotIn("const SYSTEM_PROMPT =", app_source)
        self.assertNotIn("system: cfg.system,", app_source)
        self.assertNotIn("cfg.system", app_source)
        self.assertNotIn('id="system"', index_source)
        self.assertIn(
            "Le prompt systeme global est maintenant porte par le backend et visible dans l'admin.",
            index_source,
        )

    def test_main_chat_renders_messages_as_plain_text_without_markdown_renderer(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("bubble.innerText = text;", app_source)
        self.assertNotIn("bubble.innerHTML =", app_source)
        self.assertNotIn("marked(", app_source)
        self.assertNotIn("markdown-it", app_source)

    def test_streaming_front_no_longer_uses_pre_body_updated_at_header_as_final_metadata(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('if (contentType.includes("application/json")) {', app_source)
        self.assertIn('updated_at: updatedAt || (thread ? thread.updated_at : null),', app_source)
        self.assertIn('if (threadId && (convId || createdAt)) {', app_source)
        self.assertIn(
            'setThreadMeta(threadId, {\n        conversation_id: convId || (thread ? thread.conversation_id : null),\n        created_at: createdAt || (thread ? thread.created_at : null),\n      });',
            app_source,
        )

    def test_session_panel_points_main_llm_response_budget_to_admin_runtime(self) -> None:
        source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn("<h3>Reglages de session</h3>", source)
        self.assertIn("`temperature` et `top_p` sont maintenant portes par la configuration globale des modeles dans l'admin.", source)
        self.assertIn("Le budget de reponse du LLM principal est maintenant porte par <code>main_model.response_max_tokens</code> dans l'admin.", source)
        self.assertNotIn('id="temperature"', source)
        self.assertNotIn('id="temperatureVal"', source)
        self.assertNotIn('id="top_p"', source)
        self.assertNotIn('id="toppVal"', source)
        self.assertNotIn('id="max_tokens"', source)
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

    def test_streaming_error_path_replaces_visible_bubble_without_appending_assistant_to_thread_cache(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        submit_block = app_source.split('ask.addEventListener("submit", async (e) => {', 1)[1]
        success_block, error_and_finally = submit_block.split('} catch (err) {', 1)
        catch_block, _finally_block = error_and_finally.split('} finally {', 1)

        self.assertIn('appendToThread("assistant", assistantNode.bubble.textContent);', success_block)
        self.assertIn('await hydrateThreadMessages(activeThreadId, { force: true });', success_block)
        self.assertIn('assistantNode.bubble.textContent = extractErrorMessage(err);', catch_block)
        self.assertNotIn('appendToThread("assistant", assistantNode.bubble.textContent);', catch_block)
        self.assertNotIn('await hydrateThreadMessages(activeThreadId, { force: true });', catch_block)
        self.assertNotIn('messageCache.set(', catch_block)


if __name__ == "__main__":
    unittest.main()
