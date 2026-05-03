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

    def test_streaming_front_keeps_pre_body_updated_at_header_out_of_stream_contract_and_uses_terminal_metadata(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        streaming_source = (APP_DIR / "web" / "chat_streaming.js").read_text(encoding="utf-8")

        self.assertIn('if (contentType.includes("application/json")) {', app_source)
        self.assertIn('updated_at: updatedAt || (thread ? thread.updated_at : null),', app_source)
        self.assertIn('if (threadId && (convId || createdAt)) {', app_source)
        self.assertIn(
            'setThreadMeta(threadId, {\n        conversation_id: convId || (thread ? thread.conversation_id : null),\n        created_at: createdAt || (thread ? thread.created_at : null),\n      });',
            app_source,
        )
        self.assertIn('const updatedAt = String(payload.updated_at || "").trim();', streaming_source)
        self.assertIn('const hasReplyUpdatedAt = hasTerminalUpdatedAt(replyTerminal);', app_source)
        self.assertIn('applyConversationTerminalMeta(requestThreadId, replyTerminal);', app_source)

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

    def test_streaming_error_path_replaces_visible_bubble_and_caches_the_canonical_interrupted_marker(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        submit_block = app_source.split('ask.addEventListener("submit", async (e) => {', 1)[1]
        success_block, error_and_finally = submit_block.split('} catch (err) {', 1)
        catch_block, _finally_block = error_and_finally.split('} finally {', 1)

        self.assertIn('appendMessageToThread(', success_block)
        self.assertIn('const hasReplyUpdatedAt = hasTerminalUpdatedAt(replyTerminal);', success_block)
        self.assertIn('if (!hasReplyUpdatedAt && requestThreadId) {', success_block)
        self.assertIn('await hydrateThreadMessages(requestThreadId, { force: true });', success_block)
        self.assertIn('const errorMeta = getObservableStreamErrorMeta(err);', catch_block)
        self.assertIn('applyAssistantStreamingFailure(assistantNode, errorMeta);', catch_block)
        self.assertIn('assistantNode.bubble.textContent = extractErrorMessage(err);', catch_block)
        self.assertIn('if (requestThreadId && errorTerminal && errorTerminal.event === "error") {', catch_block)
        self.assertIn('appendMessageToThread(', catch_block)
        self.assertIn('buildInterruptedAssistantTurnMeta(errorTerminal.error_code || "stream_protocol_error")', catch_block)
        self.assertNotIn('await hydrateThreadMessages(requestThreadId, { force: true });', catch_block)

    def test_streaming_front_wires_observable_ux_states_without_changing_the_stream_contract(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        streaming_source = (APP_DIR / "web" / "chat_streaming.js").read_text(encoding="utf-8")
        submit_block = app_source.split('ask.addEventListener("submit", async (e) => {', 1)[1]
        send_block = app_source.split('async function sendToServer(userText, onChunk, threadId, inputMode = "keyboard", options = {}){', 1)[1]

        self.assertIn('<script src="chat_streaming.js"></script>', index_source)
        self.assertLess(
            index_source.index('<script src="chat_streaming.js"></script>'),
            index_source.index('<script src="app.js"></script>'),
        )
        self.assertIn('const STREAMING_UI_STATE_PREPARING = "preparing";', streaming_source)
        self.assertIn('const STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT = "waiting_visible_content";', streaming_source)
        self.assertIn('const STREAMING_UI_STATE_STREAMING = "streaming";', streaming_source)
        self.assertIn('const STREAMING_UI_STATE_DONE = "done";', streaming_source)
        self.assertIn('const STREAMING_UI_STATE_INTERRUPTED = "interrupted";', streaming_source)
        self.assertIn('const STREAM_ERROR_KIND_UPSTREAM = "upstream_error";', streaming_source)
        self.assertIn('const STREAM_ERROR_KIND_SERVER = "server_error";', streaming_source)
        self.assertIn('const STREAM_ERROR_KIND_NETWORK = "network_error";', streaming_source)
        self.assertIn('const ASSISTANT_TURN_META_KEY = "assistant_turn";', streaming_source)
        self.assertIn('const ASSISTANT_TURN_STATUS_INTERRUPTED = "interrupted";', streaming_source)
        self.assertIn('applyAssistantStreamingUiEvent(assistantNode, STREAMING_UI_EVENT_REQUEST_STARTED);', submit_block)
        self.assertIn('applyAssistantStreamingUiEvent(assistantNode, STREAMING_UI_EVENT_VISIBLE_CONTENT);', submit_block)
        self.assertIn('onStreamEvent(event) {', submit_block)
        self.assertIn('applyAssistantStreamingUiEvent(assistantNode, event);', submit_block)
        self.assertIn('const errorMeta = getObservableStreamErrorMeta(err);', submit_block)
        self.assertIn('applyAssistantStreamingFailure(assistantNode, errorMeta);', submit_block)
        self.assertIn('emitStreamEvent(STREAMING_UI_EVENT_RESPONSE_OPENED);', send_block)
        self.assertIn('emitStreamEvent(STREAMING_UI_EVENT_TERMINAL_DONE);', send_block)
        self.assertIn('emitStreamEvent(STREAMING_UI_EVENT_TERMINAL_ERROR);', send_block)
        self.assertIn('return { text: finalText, terminal };', send_block)
        self.assertIn('return { text, terminal };', send_block)

    def test_streaming_front_exposes_a_small_observable_error_taxonomy(self) -> None:
        streaming_source = (APP_DIR / "web" / "chat_streaming.js").read_text(encoding="utf-8")

        self.assertIn('statusLabel: "Interrompu par le modèle"', streaming_source)
        self.assertIn('bubbleMessage: "Réponse interrompue par le modèle."', streaming_source)
        self.assertIn('statusLabel: "Interrompu côté serveur"', streaming_source)
        self.assertIn('bubbleMessage: "Réponse interrompue côté serveur."', streaming_source)
        self.assertIn('statusLabel: "Connexion interrompue"', streaming_source)
        self.assertIn('bubbleMessage: "Connexion interrompue pendant la réponse."', streaming_source)
        self.assertIn('STREAM_SERVER_ERROR_CODES = new Set([', streaming_source)
        self.assertIn('errorCode === STREAM_ERROR_KIND_UPSTREAM', streaming_source)

    def test_streaming_front_rehydrates_persisted_interrupted_assistant_markers_via_message_meta(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        streaming_source = (APP_DIR / "web" / "chat_streaming.js").read_text(encoding="utf-8")

        self.assertIn('function buildInterruptedAssistantTurnMeta(errorCode) {', streaming_source)
        self.assertIn('function getPersistedAssistantTurnErrorMeta(message) {', streaming_source)
        self.assertIn('if (m.meta && typeof m.meta === "object") {', app_source)
        self.assertIn('sanitizedMessage.meta = m.meta;', app_source)
        self.assertIn('const persistedErrorMeta = getPersistedAssistantTurnErrorMeta(messageRecord);', app_source)
        self.assertIn('applyAssistantStreamingFailure(assistantNode, persistedErrorMeta);', app_source)

    def test_streaming_front_has_a_discreet_status_line_for_the_live_assistant_bubble(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
        styles_source = (APP_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('status.className = "msg-stream-status";', app_source)
        self.assertIn('status.setAttribute("aria-live", "polite");', app_source)
        self.assertIn('.msg-stream-status {', styles_source)
        self.assertIn('.msg-stream-status[data-state="streaming"] {', styles_source)
        self.assertIn('.msg-stream-status[data-state="interrupted"] {', styles_source)

    def test_streaming_front_uses_terminal_updated_at_before_falling_back_to_force_rehydration(self) -> None:
        app_source = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('const hasReplyUpdatedAt = hasTerminalUpdatedAt(replyTerminal);', app_source)
        self.assertIn('setMessageNodeTimestamp(assistantNode, "assistant", replyTerminal.updated_at);', app_source)
        self.assertIn('appendMessageToThread(', app_source)
        self.assertIn('}, requestThreadId, inputMode, {', app_source)
        self.assertIn('if (!hasReplyUpdatedAt && requestThreadId) {', app_source)
        self.assertIn('await hydrateThreadMessages(requestThreadId, { force: true });', app_source)
        self.assertIn('if (!hasReplyUpdatedAt && requestThreadId && getCurrentId() === requestThreadId) {', app_source)


if __name__ == "__main__":
    unittest.main()
