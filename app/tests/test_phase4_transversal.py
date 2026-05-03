from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
import config


class Phase4TransversalTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_runtime_settings_env_fallback_still_exposes_config_values(self) -> None:
        main_model = runtime_settings.get_main_model_settings(fetcher=lambda: {})
        arbiter_model = runtime_settings.get_arbiter_model_settings(fetcher=lambda: {})
        summary_model = runtime_settings.get_summary_model_settings(fetcher=lambda: {})
        embedding = runtime_settings.get_embedding_settings(fetcher=lambda: {})
        services = runtime_settings.get_services_settings(fetcher=lambda: {})
        resources = runtime_settings.get_resources_settings(fetcher=lambda: {})

        self.assertEqual(main_model.source, 'env')
        self.assertEqual(main_model.payload['model']['value'], config.OR_MODEL)
        self.assertEqual(main_model.payload['base_url']['value'], config.OR_BASE)
        self.assertEqual(arbiter_model.payload['model']['value'], config.ARBITER_MODEL)
        self.assertEqual(summary_model.payload['model']['value'], config.SUMMARY_MODEL)
        self.assertEqual(embedding.payload['endpoint']['value'], config.EMBED_BASE_URL)
        self.assertEqual(embedding.payload['dimensions']['value'], config.EMBED_DIM)
        self.assertEqual(embedding.payload['top_k']['value'], config.MEMORY_TOP_K)
        self.assertEqual(services.payload['searxng_url']['value'], config.SEARXNG_URL)
        self.assertEqual(services.payload['crawl4ai_url']['value'], config.CRAWL4AI_URL)
        self.assertEqual(resources.payload['llm_identity_path']['value'], config.FRIDA_LLM_IDENTITY_PATH)
        self.assertEqual(resources.payload['user_identity_path']['value'], config.FRIDA_USER_IDENTITY_PATH)

    def test_admin_logs_still_write_and_read_without_runtime_settings_dependency(self) -> None:
        original_log_path = admin_logs.LOG_PATH
        original_bootstrap_done = admin_logs._BOOTSTRAP_DONE

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / 'admin.log.jsonl'
            admin_logs.LOG_PATH = log_path
            admin_logs._BOOTSTRAP_DONE = True
            try:
                admin_logs.log_event('phase4_admin_logs_test', foo='bar')
                entries = admin_logs.read_logs(limit=10)
            finally:
                admin_logs.LOG_PATH = original_log_path
                admin_logs._BOOTSTRAP_DONE = original_bootstrap_done

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['event'], 'phase4_admin_logs_test')
        self.assertEqual(entries[0]['foo'], 'bar')

    def test_admin_logs_resolve_log_path_keeps_explicit_env_override(self) -> None:
        explicit = APP_DIR / 'tmp-admin-override.log.jsonl'
        with mock.patch.dict('os.environ', {'FRIDA_ADMIN_LOG_PATH': str(explicit)}, clear=False):
            resolved = admin_logs._resolve_log_path()

        self.assertEqual(resolved, explicit.resolve())

    def test_admin_logs_resolve_log_path_falls_back_to_repo_logs_when_container_parent_not_writable(self) -> None:
        with mock.patch.dict('os.environ', {'FRIDA_ADMIN_LOG_PATH': ''}, clear=False):
            with mock.patch.object(admin_logs, '_parent_is_writable', return_value=False):
                resolved = admin_logs._resolve_log_path()

        self.assertEqual(resolved, (APP_DIR / 'logs' / 'admin.log.jsonl').resolve())

    def test_admin_logs_resolve_log_path_keeps_container_path_when_parent_is_writable(self) -> None:
        with mock.patch.dict('os.environ', {'FRIDA_ADMIN_LOG_PATH': ''}, clear=False):
            with mock.patch.object(admin_logs, '_parent_is_writable', return_value=True):
                resolved = admin_logs._resolve_log_path()

        self.assertEqual(resolved, Path('/app/logs/admin.log.jsonl'))

    def test_run_and_compose_runtime_binding_contract_is_unchanged(self) -> None:
        run_sh = (APP_DIR / 'run.sh').read_text(encoding='utf-8')
        compose_path = APP_DIR.parent / 'docker-compose.yml'
        compose = compose_path.read_text(encoding='utf-8') if compose_path.exists() else ''
        dockerfile = (APP_DIR / 'Dockerfile').read_text(encoding='utf-8')
        config_py = (APP_DIR / 'config.py').read_text(encoding='utf-8')
        server_py = (APP_DIR / 'server.py').read_text(encoding='utf-8')

        self.assertIn('wrapper operatoire local', run_sh)
        self.assertIn('Entree canonique runtime container', run_sh)
        self.assertIn('PORT="${FRIDA_WEB_PORT:-8089}"', run_sh)
        self.assertIn('HOST="${FRIDA_WEB_HOST:-0.0.0.0}"', run_sh)
        self.assertIn('resolve_python_bin()', run_sh)
        self.assertIn('PYTHON_BIN="$(resolve_python_bin)"', run_sh)
        self.assertIn('exec "$PYTHON_BIN" server.py', run_sh)
        self.assertIn('CMD ["python", "server.py"]', dockerfile)

        self.assertIn("WEB_HOST = os.environ.get('FRIDA_WEB_HOST', '0.0.0.0').strip() or '0.0.0.0'", config_py)
        self.assertIn("WEB_PORT = _env_int('FRIDA_WEB_PORT', 8089)", config_py)
        self.assertIn('app.run(host=config.WEB_HOST, port=config.WEB_PORT)', server_py)

        if compose:
            self.assertIn('env_file:', compose)
            self.assertIn('- ./app/.env', compose)
            self.assertIn('FRIDA_WEB_PORT: "8089"', compose)
            self.assertIn('FRIDA_WEB_HOST: "0.0.0.0"', compose)
            self.assertIn('- "8093:8089"', compose)
        else:
            self.assertEqual(APP_DIR, Path('/app'))

    def test_frontend_chat_payload_contract_no_longer_serializes_history(self) -> None:
        app_js = (APP_DIR / 'web' / 'app.js').read_text(encoding='utf-8')

        self.assertNotIn('history: Array.isArray(history) ? history : [],', app_js)
        self.assertNotIn('const history = buildContextHistory(MAX_CONTEXT_TURNS);', app_js)
        self.assertIn('async function sendToServer(userText, onChunk, threadId, inputMode = "keyboard", options = {}){', app_js)
        self.assertIn('const response = await sendToServer(text, (chunk) => {', app_js)


if __name__ == '__main__':
    unittest.main()
