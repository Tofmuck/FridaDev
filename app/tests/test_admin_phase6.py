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
        self.assertIn('id="adminMainModelForm"', html)
        self.assertIn('id="adminMainModelValidate"', html)
        self.assertIn('id="adminMainModelSave"', html)
        self.assertIn('id="adminMainModelApiKeyReplace"', html)
        self.assertIn('id="adminMainModelSystemPromptInfo"', html)
        self.assertIn('id="adminMainModelHermeneuticalPromptInfo"', html)
        self.assertIn('id="adminMainModelReadonlyInfo"', html)
        self.assertIn("System Prompt", html)
        self.assertIn("Hermeneutical Prompt", html)
        self.assertIn("Briques, sources et budgets de repere", html)
        self.assertIn('id="adminMainModelChecks"', html)
        self.assertIn('id="adminArbiterModelForm"', html)
        self.assertIn('id="adminArbiterModelValidate"', html)
        self.assertIn('id="adminArbiterModelSave"', html)
        self.assertIn('id="adminArbiterModelReadonlyInfo"', html)
        self.assertIn('id="adminArbiterModelChecks"', html)
        self.assertIn('id="adminSummaryModelForm"', html)
        self.assertIn('id="adminSummaryModelValidate"', html)
        self.assertIn('id="adminSummaryModelSave"', html)
        self.assertIn('id="adminSummaryModelReadonlyInfo"', html)
        self.assertIn('id="adminSummaryModelChecks"', html)
        self.assertIn('id="adminEmbeddingForm"', html)
        self.assertIn('id="adminEmbeddingValidate"', html)
        self.assertIn('id="adminEmbeddingSave"', html)
        self.assertIn('id="adminEmbeddingTokenReplace"', html)
        self.assertIn('id="adminEmbeddingChecks"', html)
        self.assertIn('id="adminDatabaseForm"', html)
        self.assertIn('id="adminDatabaseValidate"', html)
        self.assertIn('id="adminDatabaseSave"', html)
        self.assertIn('id="adminDatabaseDsnReplace"', html)
        self.assertIn('id="adminDatabaseChecks"', html)
        self.assertIn('id="adminServicesForm"', html)
        self.assertIn('id="adminServicesValidate"', html)
        self.assertIn('id="adminServicesSave"', html)
        self.assertIn('id="adminServicesCrawl4aiTokenReplace"', html)
        self.assertIn('id="adminServicesReadonlyInfo"', html)
        self.assertIn('id="adminServicesChecks"', html)
        self.assertIn('id="adminResourcesForm"', html)
        self.assertIn('id="adminResourcesValidate"', html)
        self.assertIn('id="adminResourcesSave"', html)
        self.assertIn('id="adminResourcesChecks"', html)
        self.assertIn('id="adminSectionGrid"', html)
        self.assertIn("L'edition detaillee s'ouvre section par section.", html)
        self.assertIn("Le backend n'accepte que replace_value pour un secret.", html)
        self.assertIn("Modele arbitre", html)
        self.assertIn("Bloc court et fonctionnel", html)
        self.assertIn("Modele resumeur", html)
        self.assertIn("Bloc de synthese conversationnelle", html)
        self.assertIn("Embeddings", html)
        self.assertIn("Bloc memoire vectorielle", html)
        self.assertIn("Base de donnees", html)
        self.assertIn("bootstrap externe maintenu", html)
        self.assertIn("Services externes", html)
        self.assertIn("SearXNG et Crawl4AI", html)
        self.assertIn("Ressources", html)
        self.assertIn("verification directe de presence des fichiers", html)
        self.assertIn("Les autres formulaires section par section arrivent ensuite.", html)
        self.assertIn("Les routes hermeneutiques backend restent hors UI admin V1.", html)
        self.assertNotIn("Logs techniques", html)
        self.assertNotIn('id="rows"', html)
        self.assertNotIn('id="restart"', html)
        self.assertNotIn("admin-old", html)

    def test_admin_css_is_minimal_derivation_of_front_tokens(self) -> None:
        source = (APP_DIR / "web" / "admin.css").read_text(encoding="utf-8")

        self.assertIn("Derived from styles.css tokens", source)
        self.assertIn("--bg-base", source)
        self.assertIn("--accent", source)
        self.assertIn(".admin-form-grid", source)
        self.assertIn(".admin-secret-card", source)
        self.assertIn(".admin-check", source)
        self.assertIn(".admin-inline-actions", source)
        self.assertIn(".admin-readonly-stack", source)
        self.assertIn(".admin-readonly-group", source)
        self.assertNotIn(".sidebar {", source)
        self.assertNotIn(".main {", source)

    def test_admin_js_uses_runtime_status_flow_without_legacy_logs_restart_logic(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn("/api/admin/settings/status", source)
        self.assertIn("/api/admin/settings/main-model", source)
        self.assertIn("/api/admin/settings/main-model/validate", source)
        self.assertIn("/api/admin/settings/arbiter-model", source)
        self.assertIn("/api/admin/settings/arbiter-model/validate", source)
        self.assertIn("/api/admin/settings/summary-model", source)
        self.assertIn("/api/admin/settings/summary-model/validate", source)
        self.assertIn("/api/admin/settings/embedding", source)
        self.assertIn("/api/admin/settings/embedding/validate", source)
        self.assertIn("/api/admin/settings/database", source)
        self.assertIn("/api/admin/settings/database/validate", source)
        self.assertIn("/api/admin/settings/services", source)
        self.assertIn("/api/admin/settings/services/validate", source)
        self.assertIn("/api/admin/settings/resources", source)
        self.assertIn("/api/admin/settings/resources/validate", source)
        self.assertIn("frida.adminToken", source)
        self.assertIn("adminMainModelSave", source)
        self.assertIn("adminMainModelValidate", source)
        self.assertIn("adminMainModelApiKeyReplace", source)
        self.assertIn("adminMainModelSystemPromptInfo", source)
        self.assertIn("adminMainModelHermeneuticalPromptInfo", source)
        self.assertIn("adminMainModelReadonlyInfo", source)
        self.assertIn("renderReadonlyInfoCards", source)
        self.assertIn("renderReadonlyInfoEntries", source)
        self.assertIn("textarea.readOnly = true", source)
        self.assertIn("adminArbiterModelSave", source)
        self.assertIn("adminArbiterModelValidate", source)
        self.assertIn("adminArbiterModelReadonlyInfo", source)
        self.assertIn("adminSummaryModelSave", source)
        self.assertIn("adminSummaryModelValidate", source)
        self.assertIn("adminSummaryModelReadonlyInfo", source)
        self.assertIn("adminEmbeddingSave", source)
        self.assertIn("adminEmbeddingValidate", source)
        self.assertIn("adminEmbeddingTokenReplace", source)
        self.assertIn("adminDatabaseSave", source)
        self.assertIn("adminDatabaseValidate", source)
        self.assertIn("adminDatabaseDsnReplace", source)
        self.assertIn("adminServicesSave", source)
        self.assertIn("adminServicesValidate", source)
        self.assertIn("adminServicesCrawl4aiTokenReplace", source)
        self.assertIn("adminServicesReadonlyInfo", source)
        self.assertIn("adminResourcesSave", source)
        self.assertIn("adminResourcesValidate", source)
        self.assertIn("replace_value", source)
        self.assertIn("adminSectionGrid", source)
        self.assertIn("sessionStorage", source)
        self.assertNotIn("/api/admin/logs", source)
        self.assertNotIn("/api/admin/restart", source)
        self.assertNotIn("loadLogs", source)
        self.assertNotIn("restartService", source)
        self.assertNotIn("admin-old", source)

    def test_admin_js_exposes_editable_main_model_response_max_tokens(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn('key: "response_max_tokens"', source)
        self.assertIn('label: "Max tokens reponse"', source)
        self.assertIn('hint: "Budget de generation par defaut envoye au modele principal."', source)
        self.assertIn('integerFields: ["response_max_tokens"]', source)

    def test_admin_js_extracts_shared_section_helpers(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn("const renderCheckList =", source)
        self.assertIn("const setSectionControlsDisabled =", source)
        self.assertIn("const buildSectionPatchPayload =", source)
        self.assertIn("const updateSectionDirtyChip =", source)
        self.assertIn("const applySectionDraftToForm =", source)
        self.assertIn('origin === "db_seed"', source)

    def test_admin_js_reserves_env_fallback_label_for_env_seed_only(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn('if (origin === "db" || origin === "db_seed" || origin === "admin_ui") return "db";', source)
        self.assertIn('if (origin === "env_seed") return "env fallback";', source)

    def test_admin_readonly_prompt_cards_stay_out_of_edit_mode(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        readonly_block = source.split("const buildReadonlyInfoCard =", 1)[1].split(
            "const setSectionControlsDisabled =",
            1,
        )[0]

        self.assertEqual(html.count("Hors edition"), 4)
        self.assertNotIn("Invariant", html)
        self.assertNotIn("invariant", html)
        self.assertIn("textarea.readOnly = true", readonly_block)
        self.assertNotIn('createElement("input")', readonly_block)
        self.assertNotIn('createElement("button")', readonly_block)

    def test_admin_main_model_separates_system_and_hermeneutical_prompts(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn('id="adminMainModelSystemPromptInfo"', html)
        self.assertIn('id="adminMainModelHermeneuticalPromptInfo"', html)
        self.assertIn("System Prompt", html)
        self.assertIn("Hermeneutical Prompt", html)
        self.assertIn("const systemPromptEntries = readonlyInfo.system_prompt", source)
        self.assertIn("const hermeneuticalPromptEntries = readonlyInfo.hermeneutical_prompt", source)
        self.assertIn(
            'if (key === "system_prompt" || key === "hermeneutical_prompt") return;',
            source,
        )
        self.assertIn(
            "renderReadonlyInfoEntries(elements.mainModelSystemPromptInfo, systemPromptEntries);",
            source,
        )
        self.assertIn(
            "renderReadonlyInfoEntries(elements.mainModelHermeneuticalPromptInfo, hermeneuticalPromptEntries);",
            source,
        )

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
        self.assertIn('id="adminMainModelForm"', source)
        self.assertIn('id="adminMainModelSave"', source)
        self.assertIn('id="adminMainModelSystemPromptInfo"', source)
        self.assertIn('id="adminMainModelHermeneuticalPromptInfo"', source)
        self.assertIn('id="adminMainModelReadonlyInfo"', source)
        self.assertIn("response_max_tokens", source)
        self.assertIn('id="adminArbiterModelForm"', source)
        self.assertIn('id="adminArbiterModelSave"', source)
        self.assertIn('id="adminArbiterModelReadonlyInfo"', source)
        self.assertIn('id="adminSummaryModelForm"', source)
        self.assertIn('id="adminSummaryModelSave"', source)
        self.assertIn('id="adminSummaryModelReadonlyInfo"', source)
        self.assertIn('id="adminEmbeddingForm"', source)
        self.assertIn('id="adminEmbeddingSave"', source)
        self.assertIn('id="adminDatabaseForm"', source)
        self.assertIn('id="adminDatabaseSave"', source)
        self.assertIn('id="adminServicesForm"', source)
        self.assertIn('id="adminServicesSave"', source)
        self.assertIn('id="adminServicesReadonlyInfo"', source)
        self.assertIn('id="adminResourcesForm"', source)
        self.assertIn('id="adminResourcesSave"', source)
        self.assertIn("/api/admin/settings/main-model", source)
        self.assertIn("/api/admin/settings/main-model/validate", source)
        self.assertIn("/api/admin/settings/arbiter-model", source)
        self.assertIn("/api/admin/settings/arbiter-model/validate", source)
        self.assertIn("/api/admin/settings/summary-model", source)
        self.assertIn("/api/admin/settings/summary-model/validate", source)
        self.assertIn("/api/admin/settings/embedding", source)
        self.assertIn("/api/admin/settings/embedding/validate", source)
        self.assertIn("/api/admin/settings/database", source)
        self.assertIn("/api/admin/settings/database/validate", source)
        self.assertIn("/api/admin/settings/services", source)
        self.assertIn("/api/admin/settings/services/validate", source)
        self.assertIn("/api/admin/settings/resources", source)
        self.assertIn("/api/admin/settings/resources/validate", source)
        self.assertIn("/api/admin/settings/status", source)
        self.assertIn("frida.adminToken", source)
        self.assertIn('/api/admin/logs?limit=1', source)
        self.assertIn('/api/admin/restart', (APP_DIR / "server.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
