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


class AdminPhase7FoundationTests(unittest.TestCase):
    def test_admin_topbar_links_keep_admin_navigation_in_same_window(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")

        self.assertIn('href="/log"', html)
        self.assertIn('href="/hermeneutic-admin"', html)
        self.assertNotIn('href="/hermeneutic-admin" target="_blank"', html)
        self.assertNotIn('href="/log" target="_blank"', html)

    def test_admin_html_uses_phase7_foundation_layout(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")

        self.assertIn("Admin de configuration", html)
        self.assertIn('href="admin.css"', html)
        self.assertIn('script src="admin_api.js"', html)
        self.assertIn('script src="admin_ui_common.js"', html)
        self.assertIn('script src="admin_state.js"', html)
        self.assertIn('script src="admin_section_main_model.js"', html)
        self.assertIn('script src="admin_section_arbiter_model.js"', html)
        self.assertIn('script src="admin_section_summary_model.js"', html)
        self.assertIn('script src="admin_section_stimmung_agent_model.js"', html)
        self.assertIn('script src="admin_section_validation_agent_model.js"', html)
        self.assertIn('script src="admin_section_embedding.js"', html)
        self.assertIn('script src="admin_section_database.js"', html)
        self.assertIn('script src="admin_section_services.js"', html)
        self.assertIn('script src="admin_section_resources.js"', html)
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
        self.assertIn('id="adminStimmungAgentModelForm"', html)
        self.assertIn('id="adminStimmungAgentModelValidate"', html)
        self.assertIn('id="adminStimmungAgentModelSave"', html)
        self.assertIn('id="adminStimmungAgentModelReadonlyInfo"', html)
        self.assertIn('id="adminStimmungAgentModelChecks"', html)
        self.assertIn('id="adminValidationAgentModelForm"', html)
        self.assertIn('id="adminValidationAgentModelValidate"', html)
        self.assertIn('id="adminValidationAgentModelSave"', html)
        self.assertIn('id="adminValidationAgentModelReadonlyInfo"', html)
        self.assertIn('id="adminValidationAgentModelChecks"', html)
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
        self.assertIn("Agent Stimmung", html)
        self.assertIn("Bloc affectif amont", html)
        self.assertIn("Agent de validation", html)
        self.assertIn("Bloc de relecture aval", html)
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

    def test_admin_html_scripts_are_complete_and_loaded_in_dependency_order(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        found_scripts = re.findall(r'<script\s+src="([^"]+)"></script>', html)
        expected_scripts = [
            "admin_api.js",
            "admin_ui_common.js",
            "admin_state.js",
            "admin_section_main_model.js",
            "admin_section_arbiter_model.js",
            "admin_section_summary_model.js",
            "admin_section_stimmung_agent_model.js",
            "admin_section_validation_agent_model.js",
            "admin_section_embedding.js",
            "admin_section_database.js",
            "admin_section_services.js",
            "admin_section_resources.js",
            "admin.js",
        ]
        self.assertEqual(found_scripts, expected_scripts)

    def test_admin_front_consumes_exact_admin_settings_endpoints_and_dom_hooks(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        admin_api_source = (APP_DIR / "web" / "admin_api.js").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        main_model_source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")
        arbiter_source = (APP_DIR / "web" / "admin_section_arbiter_model.js").read_text(encoding="utf-8")
        summary_source = (APP_DIR / "web" / "admin_section_summary_model.js").read_text(encoding="utf-8")
        stimmung_agent_source = (APP_DIR / "web" / "admin_section_stimmung_agent_model.js").read_text(encoding="utf-8")
        validation_agent_source = (APP_DIR / "web" / "admin_section_validation_agent_model.js").read_text(encoding="utf-8")
        embedding_source = (APP_DIR / "web" / "admin_section_embedding.js").read_text(encoding="utf-8")
        database_source = (APP_DIR / "web" / "admin_section_database.js").read_text(encoding="utf-8")
        services_source = (APP_DIR / "web" / "admin_section_services.js").read_text(encoding="utf-8")
        resources_source = (APP_DIR / "web" / "admin_section_resources.js").read_text(encoding="utf-8")
        source_all = (
            f"{admin_api_source}\n{admin_source}\n{main_model_source}\n{arbiter_source}\n{summary_source}\n"
            f"{stimmung_agent_source}\n{validation_agent_source}\n{embedding_source}\n"
            f"{database_source}\n{services_source}\n{resources_source}"
        )

        found_endpoints = set(re.findall(r"/api/admin/settings(?:/[a-z-]+(?:/validate)?)?", source_all))
        self.assertEqual(
            found_endpoints,
            {
                "/api/admin/settings",
                "/api/admin/settings/status",
                "/api/admin/settings/main-model",
                "/api/admin/settings/main-model/validate",
                "/api/admin/settings/arbiter-model",
                "/api/admin/settings/arbiter-model/validate",
                "/api/admin/settings/summary-model",
                "/api/admin/settings/summary-model/validate",
                "/api/admin/settings/stimmung-agent-model",
                "/api/admin/settings/stimmung-agent-model/validate",
                "/api/admin/settings/validation-agent-model",
                "/api/admin/settings/validation-agent-model/validate",
                "/api/admin/settings/embedding",
                "/api/admin/settings/embedding/validate",
                "/api/admin/settings/database",
                "/api/admin/settings/database/validate",
                "/api/admin/settings/services",
                "/api/admin/settings/services/validate",
                "/api/admin/settings/resources",
                "/api/admin/settings/resources/validate",
            },
        )

        self.assertIn('const TOKEN_KEY = "frida.adminToken";', admin_api_source)
        self.assertIn('headers.set("X-Admin-Token", token);', admin_api_source)
        self.assertIn('title_identity_extractor', admin_source)
        self.assertIn("Titre extracteur d'identite", admin_source)

        dom_hook_ids = set(re.findall(r'document\.getElementById\("([^"]+)"\)', source_all))
        missing_dom_hook_ids = sorted(hook_id for hook_id in dom_hook_ids if f'id="{hook_id}"' not in html)
        self.assertEqual(missing_dom_hook_ids, [])

        dynamic_getelement_templates = set(
            re.findall(r'document\.getElementById\(`([^`]*\$\{[^`]+\}[^`]*)`\)', source_all)
        )
        self.assertEqual(
            dynamic_getelement_templates,
            {
                "adminMainModel-${field}",
                "adminMainModelFieldError-${field}",
                "adminMainModelSource-${spec.key}",
                "adminArbiterModel-${field}",
                "adminArbiterModelFieldError-${field}",
                "adminArbiterModelSource-${spec.key}",
                "adminSummaryModel-${field}",
                "adminSummaryModelFieldError-${field}",
                "adminSummaryModelSource-${spec.key}",
                "adminStimmungAgentModel-${field}",
                "adminStimmungAgentModelFieldError-${field}",
                "adminStimmungAgentModelSource-${spec.key}",
                "adminValidationAgentModel-${field}",
                "adminValidationAgentModelFieldError-${field}",
                "adminValidationAgentModelSource-${spec.key}",
                "adminEmbedding-${field}",
                "adminEmbeddingFieldError-${field}",
                "adminEmbeddingSource-${spec.key}",
                "adminDatabase-${field}",
                "adminDatabaseFieldError-${field}",
                "adminDatabaseSource-${spec.key}",
                "adminServices-${field}",
                "adminServicesFieldError-${field}",
                "adminServicesSource-${spec.key}",
                "adminResources-${field}",
                "adminResourcesFieldError-${field}",
                "adminResourcesSource-${spec.key}",
            },
        )

        dynamic_id_assignment_templates = set(
            re.findall(r'\.id\s*=\s*`([^`]*\$\{[^`]+\}[^`]*)`', source_all)
        )
        self.assertEqual(
            dynamic_id_assignment_templates,
            {
                "adminMainModel-${spec.key}",
                "adminMainModelFieldError-${spec.key}",
                "adminMainModelSource-${spec.key}",
                "adminArbiterModel-${spec.key}",
                "adminArbiterModelFieldError-${spec.key}",
                "adminArbiterModelSource-${spec.key}",
                "adminSummaryModel-${spec.key}",
                "adminSummaryModelFieldError-${spec.key}",
                "adminSummaryModelSource-${spec.key}",
                "adminStimmungAgentModel-${spec.key}",
                "adminStimmungAgentModelFieldError-${spec.key}",
                "adminStimmungAgentModelSource-${spec.key}",
                "adminValidationAgentModel-${spec.key}",
                "adminValidationAgentModelFieldError-${spec.key}",
                "adminValidationAgentModelSource-${spec.key}",
                "adminEmbedding-${spec.key}",
                "adminEmbeddingFieldError-${spec.key}",
                "adminEmbeddingSource-${spec.key}",
                "adminDatabase-${spec.key}",
                "adminDatabaseFieldError-${spec.key}",
                "adminDatabaseSource-${spec.key}",
                "adminServices-${spec.key}",
                "adminServicesFieldError-${spec.key}",
                "adminServicesSource-${spec.key}",
                "adminResources-${spec.key}",
                "adminResourcesFieldError-${spec.key}",
                "adminResourcesSource-${spec.key}",
            },
        )

        normalize_template = lambda raw: re.sub(r"\$\{[^}]+\}", "${*}", raw)
        self.assertEqual(
            {normalize_template(template) for template in dynamic_getelement_templates},
            {normalize_template(template) for template in dynamic_id_assignment_templates},
        )

        query_selector_matches = re.findall(
            r'document\.querySelector\("([^"]+)"\)|document\.querySelector\(`([^`]+)`\)',
            source_all,
        )
        query_selectors = {
            selector
            for quoted_selector, template_selector in query_selector_matches
            for selector in [quoted_selector or template_selector]
            if selector
        }
        self.assertEqual(
            query_selectors,
            {
                ".admin-secret-card",
                '[data-field="${field}"]',
                '[data-arbiter-field="${field}"]',
                '[data-summary-field="${field}"]',
                '[data-stimmung-agent-field="${field}"]',
                '[data-validation-agent-field="${field}"]',
                '[data-embedding-field="${field}"]',
                '[data-database-field="${field}"]',
                '[data-services-field="${field}"]',
                '[data-resources-field="${field}"]',
            },
        )

        data_selectors = {
            match.group(1)
            for selector in query_selectors
            for match in [re.match(r'^\[(data-[a-z-]+)="\$\{field\}"\]$', selector)]
            if match
        }
        self.assertEqual(
            data_selectors,
            {
                "data-field",
                "data-arbiter-field",
                "data-summary-field",
                "data-stimmung-agent-field",
                "data-validation-agent-field",
                "data-embedding-field",
                "data-database-field",
                "data-services-field",
                "data-resources-field",
            },
        )

        self.assertIn('field.dataset.field = spec.key;', main_model_source)
        self.assertIn('field.dataset.arbiterField = spec.key;', arbiter_source)
        self.assertIn('field.dataset.summaryField = spec.key;', summary_source)
        self.assertIn('field.dataset.stimmungAgentField = spec.key;', stimmung_agent_source)
        self.assertIn('field.dataset.validationAgentField = spec.key;', validation_agent_source)
        self.assertIn('field.dataset.embeddingField = spec.key;', embedding_source)
        self.assertIn('field.dataset.databaseField = spec.key;', database_source)
        self.assertIn('field.dataset.servicesField = spec.key;', services_source)
        self.assertIn('field.dataset.resourcesField = spec.key;', resources_source)

        self.assertIn('document.querySelector(".admin-secret-card")', main_model_source)
        self.assertIn('document.getElementById("adminEmbeddingSecretCard")', embedding_source)
        self.assertIn('document.getElementById("adminDatabaseSecretCard")', database_source)
        self.assertIn('document.getElementById("adminServicesSecretCard")', services_source)

    def test_admin_js_uses_runtime_status_flow_without_legacy_logs_restart_logic(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        api_source = (APP_DIR / "web" / "admin_api.js").read_text(encoding="utf-8")
        ui_source = (APP_DIR / "web" / "admin_ui_common.js").read_text(encoding="utf-8")
        state_source = (APP_DIR / "web" / "admin_state.js").read_text(encoding="utf-8")
        main_model_source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")
        arbiter_source = (APP_DIR / "web" / "admin_section_arbiter_model.js").read_text(encoding="utf-8")
        summary_source = (APP_DIR / "web" / "admin_section_summary_model.js").read_text(encoding="utf-8")
        stimmung_agent_source = (APP_DIR / "web" / "admin_section_stimmung_agent_model.js").read_text(encoding="utf-8")
        validation_agent_source = (APP_DIR / "web" / "admin_section_validation_agent_model.js").read_text(encoding="utf-8")
        embedding_source = (APP_DIR / "web" / "admin_section_embedding.js").read_text(encoding="utf-8")
        database_source = (APP_DIR / "web" / "admin_section_database.js").read_text(encoding="utf-8")
        services_source = (APP_DIR / "web" / "admin_section_services.js").read_text(encoding="utf-8")
        resources_source = (APP_DIR / "web" / "admin_section_resources.js").read_text(encoding="utf-8")
        source_all = (
            f"{api_source}\n{ui_source}\n{state_source}\n{main_model_source}\n{arbiter_source}\n"
            f"{summary_source}\n{stimmung_agent_source}\n{validation_agent_source}\n{embedding_source}\n"
            f"{database_source}\n{services_source}\n{resources_source}\n{source}"
        )

        self.assertIn("/api/admin/settings/status", source_all)
        self.assertIn("/api/admin/settings/main-model", source_all)
        self.assertIn("/api/admin/settings/main-model/validate", source_all)
        self.assertIn("/api/admin/settings/arbiter-model", source_all)
        self.assertIn("/api/admin/settings/arbiter-model/validate", source_all)
        self.assertIn("/api/admin/settings/summary-model", source_all)
        self.assertIn("/api/admin/settings/summary-model/validate", source_all)
        self.assertIn("/api/admin/settings/embedding", source_all)
        self.assertIn("/api/admin/settings/embedding/validate", source_all)
        self.assertIn("/api/admin/settings/database", source_all)
        self.assertIn("/api/admin/settings/database/validate", source_all)
        self.assertIn("/api/admin/settings/services", source_all)
        self.assertIn("/api/admin/settings/services/validate", source_all)
        self.assertIn("/api/admin/settings/resources", source_all)
        self.assertIn("/api/admin/settings/resources/validate", source_all)
        self.assertIn("frida.adminToken", source_all)
        self.assertIn("adminMainModelSave", source)
        self.assertIn("adminMainModelValidate", source)
        self.assertIn("adminMainModelApiKeyReplace", source)
        self.assertIn("adminMainModelSystemPromptInfo", source)
        self.assertIn("adminMainModelHermeneuticalPromptInfo", source)
        self.assertIn("adminMainModelReadonlyInfo", source)
        self.assertIn("renderReadonlyInfoCards", source)
        self.assertIn("renderReadonlyInfoEntries", source)
        self.assertIn("textarea.readOnly = true", source_all)
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
        self.assertIn("sessionStorage", source_all)
        self.assertNotIn("/api/admin/logs", source)
        self.assertNotIn("/api/admin/restart", source)
        self.assertNotIn("loadLogs", source)
        self.assertNotIn("restartService", source)
        self.assertNotIn("admin-old", source)

    def test_admin_api_module_isolated_from_render_layer(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        api_source = (APP_DIR / "web" / "admin_api.js").read_text(encoding="utf-8")
        ui_source = (APP_DIR / "web" / "admin_ui_common.js").read_text(encoding="utf-8")
        state_source = (APP_DIR / "web" / "admin_state.js").read_text(encoding="utf-8")
        main_model_source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")
        arbiter_source = (APP_DIR / "web" / "admin_section_arbiter_model.js").read_text(encoding="utf-8")
        summary_source = (APP_DIR / "web" / "admin_section_summary_model.js").read_text(encoding="utf-8")
        stimmung_agent_source = (APP_DIR / "web" / "admin_section_stimmung_agent_model.js").read_text(encoding="utf-8")
        validation_agent_source = (APP_DIR / "web" / "admin_section_validation_agent_model.js").read_text(encoding="utf-8")
        embedding_source = (APP_DIR / "web" / "admin_section_embedding.js").read_text(encoding="utf-8")
        database_source = (APP_DIR / "web" / "admin_section_database.js").read_text(encoding="utf-8")
        services_source = (APP_DIR / "web" / "admin_section_services.js").read_text(encoding="utf-8")
        resources_source = (APP_DIR / "web" / "admin_section_resources.js").read_text(encoding="utf-8")
        source_all = (
            f"{api_source}\n{ui_source}\n{state_source}\n{main_model_source}\n{arbiter_source}\n"
            f"{summary_source}\n{embedding_source}\n{database_source}\n{services_source}\n{resources_source}\n{source}"
        )

        self.assertIn("window.FridaAdminApi", source)
        self.assertIn("window.FridaAdminUiCommon", source)
        self.assertIn("window.FridaAdminState", source)
        self.assertIn("window.FridaAdminMainModelSection", source)
        self.assertIn("window.FridaAdminArbiterModelSection", source)
        self.assertIn("window.FridaAdminSummaryModelSection", source)
        self.assertIn("window.FridaAdminStimmungAgentModelSection", source)
        self.assertIn("window.FridaAdminValidationAgentModelSection", source)
        self.assertIn("window.FridaAdminEmbeddingSection", source)
        self.assertIn("window.FridaAdminDatabaseSection", source)
        self.assertIn("window.FridaAdminServicesSection", source)
        self.assertIn("window.FridaAdminResourcesSection", source)
        self.assertIn("const sectionRoutes = adminApi.sectionRoutes;", source)
        self.assertIn("const {", source)
        self.assertIn("renderCheckList", source)
        self.assertIn("applyFieldError", source)
        self.assertIn("adminApi.fetchStatus()", source)
        self.assertIn("adminApi.fetchSection(", source_all)
        self.assertIn("adminApi.patchSection(", source_all)
        self.assertIn("adminApi.validateSection(", source_all)

        self.assertIn("const TOKEN_KEY = \"frida.adminToken\";", api_source)
        self.assertIn('headers.set("X-Admin-Token", token);', api_source)
        self.assertIn("const fetchAggregatedSettings =", api_source)
        self.assertIn("const fetchStatus =", api_source)
        self.assertIn("const fetchSection =", api_source)
        self.assertIn("const patchSection =", api_source)
        self.assertIn("const validateSection =", api_source)
        self.assertIn("window.FridaAdminUiCommon = Object.freeze({", ui_source)
        self.assertIn("const renderCheckList =", ui_source)
        self.assertIn("const renderReadonlyInfoCards =", ui_source)
        self.assertIn("const applyFieldError =", ui_source)
        self.assertIn("const createAdminState = () => ({", state_source)
        self.assertIn("const initializeAdminSectionDrafts = (state, draftFactories = {}) => {", state_source)
        self.assertIn("window.FridaAdminState = Object.freeze({", state_source)
        self.assertIn("const createMainModelSectionController = ({", main_model_source)
        self.assertIn("const runMainModelValidation = async (payload) => {", main_model_source)
        self.assertIn("const saveMainModelSection = async () => {", main_model_source)
        self.assertIn("window.FridaAdminMainModelSection = Object.freeze({", main_model_source)
        self.assertIn("const createArbiterModelSectionController = ({", arbiter_source)
        self.assertIn("const runArbiterValidation = async (payload) => {", arbiter_source)
        self.assertIn("const saveArbiterSection = async () => {", arbiter_source)
        self.assertIn("window.FridaAdminArbiterModelSection = Object.freeze({", arbiter_source)
        self.assertIn("const createSummaryModelSectionController = ({", summary_source)
        self.assertIn("const runSummaryValidation = async (payload) => {", summary_source)
        self.assertIn("const saveSummarySection = async () => {", summary_source)
        self.assertIn("window.FridaAdminSummaryModelSection = Object.freeze({", summary_source)
        self.assertIn("const createStimmungAgentModelSectionController = ({", stimmung_agent_source)
        self.assertIn("const runStimmungAgentValidation = async (payload) => {", stimmung_agent_source)
        self.assertIn("const saveStimmungAgentSection = async () => {", stimmung_agent_source)
        self.assertIn("window.FridaAdminStimmungAgentModelSection = Object.freeze({", stimmung_agent_source)
        self.assertIn("const createValidationAgentModelSectionController = ({", validation_agent_source)
        self.assertIn("const runValidationAgentValidation = async (payload) => {", validation_agent_source)
        self.assertIn("const saveValidationAgentSection = async () => {", validation_agent_source)
        self.assertIn("window.FridaAdminValidationAgentModelSection = Object.freeze({", validation_agent_source)
        self.assertIn("const createEmbeddingSectionController = ({", embedding_source)
        self.assertIn("const runEmbeddingValidation = async (payload) => {", embedding_source)
        self.assertIn("const saveEmbeddingSection = async () => {", embedding_source)
        self.assertIn("window.FridaAdminEmbeddingSection = Object.freeze({", embedding_source)
        self.assertIn("const createDatabaseSectionController = ({", database_source)
        self.assertIn("const runDatabaseValidation = async (payload) => {", database_source)
        self.assertIn("const saveDatabaseSection = async () => {", database_source)
        self.assertIn("window.FridaAdminDatabaseSection = Object.freeze({", database_source)
        self.assertIn("const createServicesSectionController = ({", services_source)
        self.assertIn("const runServicesValidation = async (payload) => {", services_source)
        self.assertIn("const saveServicesSection = async () => {", services_source)
        self.assertIn("window.FridaAdminServicesSection = Object.freeze({", services_source)
        self.assertIn("const createResourcesSectionController = ({", resources_source)
        self.assertIn("const runResourcesValidation = async (payload) => {", resources_source)
        self.assertIn("const saveResourcesSection = async () => {", resources_source)
        self.assertIn("window.FridaAdminResourcesSection = Object.freeze({", resources_source)

    def test_admin_js_exposes_editable_main_model_response_max_tokens(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        main_model_source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")
        source_all = f"{source}\n{main_model_source}"

        self.assertIn('key: "response_max_tokens"', source)
        self.assertIn('label: "Max tokens reponse"', source)
        self.assertIn('hint: "Budget de generation par defaut envoye au modele principal."', source)
        self.assertIn('integerFields: ["response_max_tokens"]', source_all)

    def test_admin_state_module_uses_plain_object_slices_without_store_framework(self) -> None:
        source = (APP_DIR / "web" / "admin_state.js").read_text(encoding="utf-8")

        self.assertIn("const createSectionStateSlice = () => ({", source)
        self.assertIn("loaded: false", source)
        self.assertIn("view: null", source)
        self.assertIn("baseline: null", source)
        self.assertIn("draft: null", source)
        self.assertIn("mainModel: createSectionStateSlice()", source)
        self.assertIn("stimmungAgentModel: createSectionStateSlice()", source)
        self.assertIn("validationAgentModel: createSectionStateSlice()", source)
        self.assertIn("resources: createSectionStateSlice()", source)
        self.assertIn("const initializeAdminSectionDrafts = (state, draftFactories = {}) => {", source)
        self.assertNotIn("EventEmitter", source)
        self.assertNotIn("Proxy", source)
        self.assertNotIn("class ", source)

    def test_admin_js_extracts_shared_section_helpers(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        ui_source = (APP_DIR / "web" / "admin_ui_common.js").read_text(encoding="utf-8")

        self.assertIn("const renderCheckList =", ui_source)
        self.assertIn("const renderReadonlyInfoEntries =", ui_source)
        self.assertIn("const renderReadonlyInfoCards =", ui_source)
        self.assertIn("const applyFieldError =", ui_source)
        self.assertIn("const setSectionControlsDisabled =", source)
        self.assertIn("const buildSectionPatchPayload =", source)
        self.assertIn("const updateSectionDirtyChip =", source)
        self.assertIn("const applySectionDraftToForm =", source)
        self.assertIn("const state = createAdminState();", source)
        self.assertIn("initializeAdminSectionDrafts(state, {", source)
        self.assertNotIn("const state = {", source)
        self.assertIn("mainModelSection.bindMainModelSectionEvents();", source)
        self.assertIn("mainModelSection.loadMainModelSection(),", source)
        self.assertNotIn("const saveMainModelSection = async () => {", source)
        self.assertNotIn("const runMainModelValidation = async (payload) => {", source)
        self.assertIn("arbiterModelSection.bindArbiterModelSectionEvents();", source)
        self.assertIn("arbiterModelSection.loadArbiterModelSection(),", source)
        self.assertNotIn("const saveArbiterSection = async () => {", source)
        self.assertNotIn("const runArbiterValidation = async (payload) => {", source)
        self.assertIn("summaryModelSection.bindSummaryModelSectionEvents();", source)
        self.assertIn("summaryModelSection.loadSummaryModelSection(),", source)
        self.assertNotIn("const saveSummarySection = async () => {", source)
        self.assertNotIn("const runSummaryValidation = async (payload) => {", source)
        self.assertIn("stimmungAgentModelSection.bindStimmungAgentModelSectionEvents();", source)
        self.assertIn("stimmungAgentModelSection.loadStimmungAgentModelSection(),", source)
        self.assertIn("validationAgentModelSection.bindValidationAgentModelSectionEvents();", source)
        self.assertIn("validationAgentModelSection.loadValidationAgentModelSection(),", source)
        self.assertIn("embeddingSection.bindEmbeddingSectionEvents();", source)
        self.assertIn("embeddingSection.loadEmbeddingSection(),", source)
        self.assertNotIn("const saveEmbeddingSection = async () => {", source)
        self.assertNotIn("const runEmbeddingValidation = async (payload) => {", source)
        self.assertIn("databaseSection.bindDatabaseSectionEvents();", source)
        self.assertIn("databaseSection.loadDatabaseSection(),", source)
        self.assertNotIn("const saveDatabaseSection = async () => {", source)
        self.assertNotIn("const runDatabaseValidation = async (payload) => {", source)
        self.assertIn("servicesSection.bindServicesSectionEvents();", source)
        self.assertIn("servicesSection.loadServicesSection(),", source)
        self.assertNotIn("const saveServicesSection = async () => {", source)
        self.assertNotIn("const runServicesValidation = async (payload) => {", source)
        self.assertIn("resourcesSection.bindResourcesSectionEvents();", source)
        self.assertIn("resourcesSection.loadResourcesSection(),", source)
        self.assertNotIn(
            "const bindResourcesSectionEvents = () => resourcesSection.bindResourcesSectionEvents();",
            source,
        )
        self.assertNotIn("const loadResourcesSection = async () => resourcesSection.loadResourcesSection();", source)
        self.assertIn('origin === "db_seed"', source)

    def test_admin_js_reserves_env_fallback_label_for_env_seed_only(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn('if (origin === "db" || origin === "db_seed" || origin === "admin_ui") return "db";', source)
        self.assertIn('if (origin === "env_seed") return "env fallback";', source)

    def test_admin_error_mapping_helpers_are_centralized_and_keep_secret_specific_hosts(self) -> None:
        source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        ui_source = (APP_DIR / "web" / "admin_ui_common.js").read_text(encoding="utf-8")
        main_model_source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")
        arbiter_source = (APP_DIR / "web" / "admin_section_arbiter_model.js").read_text(encoding="utf-8")
        summary_source = (APP_DIR / "web" / "admin_section_summary_model.js").read_text(encoding="utf-8")
        stimmung_agent_source = (APP_DIR / "web" / "admin_section_stimmung_agent_model.js").read_text(encoding="utf-8")
        validation_agent_source = (APP_DIR / "web" / "admin_section_validation_agent_model.js").read_text(encoding="utf-8")
        embedding_source = (APP_DIR / "web" / "admin_section_embedding.js").read_text(encoding="utf-8")
        database_source = (APP_DIR / "web" / "admin_section_database.js").read_text(encoding="utf-8")
        services_source = (APP_DIR / "web" / "admin_section_services.js").read_text(encoding="utf-8")
        resources_source = (APP_DIR / "web" / "admin_section_resources.js").read_text(encoding="utf-8")
        section_sources = (
            main_model_source,
            arbiter_source,
            summary_source,
            stimmung_agent_source,
            validation_agent_source,
            embedding_source,
            database_source,
            services_source,
            resources_source,
        )

        self.assertIn("const clearSectionFieldErrors =", ui_source)
        self.assertIn("const applySectionLocalFieldErrors =", ui_source)
        self.assertIn("const applySectionBackendFieldError =", ui_source)
        self.assertIn("const collectSectionFailedChecks =", ui_source)
        self.assertIn("clearSectionFieldErrors,", ui_source)
        self.assertIn("applySectionLocalFieldErrors,", ui_source)
        self.assertIn("applySectionBackendFieldError,", ui_source)
        self.assertIn("collectSectionFailedChecks,", ui_source)
        self.assertIn("clearSectionFieldErrors,", source)
        self.assertIn("applySectionLocalFieldErrors,", source)
        self.assertIn("applySectionBackendFieldError,", source)
        self.assertIn("collectSectionFailedChecks,", source)

        for section_source in section_sources:
            self.assertIn("clearSectionFieldErrors({", section_source)
            self.assertIn("applySectionLocalFieldErrors(errors, ", section_source)
            self.assertIn("applySectionBackendFieldError({", section_source)
            self.assertIn("return collectSectionFailedChecks(", section_source)

        self.assertIn('sectionKey: "main_model"', main_model_source)
        self.assertIn('secretField: "api_key"', main_model_source)
        self.assertIn('document.querySelector(".admin-secret-card")', main_model_source)

        self.assertIn('sectionKey: "embedding"', embedding_source)
        self.assertIn('secretField: "token"', embedding_source)
        self.assertIn('document.getElementById("adminEmbeddingSecretCard")', embedding_source)
        self.assertIn('sectionKey: "stimmung_agent_model"', stimmung_agent_source)
        self.assertIn('sectionKey: "validation_agent_model"', validation_agent_source)

        self.assertIn('sectionKey: "database"', database_source)
        self.assertIn('secretField: "dsn"', database_source)
        self.assertIn('document.getElementById("adminDatabaseSecretCard")', database_source)

        self.assertIn('sectionKey: "services"', services_source)
        self.assertIn('secretField: "crawl4ai_token"', services_source)
        self.assertIn('document.getElementById("adminServicesSecretCard")', services_source)

    def test_admin_readonly_prompt_cards_stay_out_of_edit_mode(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        ui_source = (APP_DIR / "web" / "admin_ui_common.js").read_text(encoding="utf-8")

        readonly_block = ui_source.split("const buildReadonlyInfoCard =", 1)[1].split(
            "const renderReadonlyInfoEntries =",
            1,
        )[0]

        self.assertEqual(html.count("Hors edition"), 6)
        self.assertNotIn("Invariant", html)
        self.assertNotIn("invariant", html)
        self.assertIn("textarea.readOnly = true", readonly_block)
        self.assertNotIn('createElement("input")', readonly_block)
        self.assertNotIn('createElement("button")', readonly_block)

    def test_admin_main_model_separates_system_and_hermeneutical_prompts(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")

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

    def test_admin_main_model_prompt_panels_stay_ordered_and_marker_friendly(self) -> None:
        html = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        source = (APP_DIR / "web" / "admin_section_main_model.js").read_text(encoding="utf-8")
        ui_source = (APP_DIR / "web" / "admin_ui_common.js").read_text(encoding="utf-8")
        source_all = f"{ui_source}\n{source}"

        self.assertLess(html.index("System Prompt"), html.index("Hermeneutical Prompt"))
        self.assertLess(html.index("Hermeneutical Prompt"), html.index("Briques, sources et budgets de repere"))
        self.assertIn('id="adminMainModelReadonlyInfo"', html)
        self.assertIn("Briques, sources et budgets de repere", html)
        self.assertIn("textarea.readOnly = true", source_all)
        self.assertIn("textarea.value = value", source_all)
        self.assertIn("target.replaceChildren(fragment);", source_all)

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
        self.assertIn('script src="admin_ui_common.js"', source)
        self.assertIn('script src="admin_state.js"', source)
        self.assertIn('script src="admin_section_main_model.js"', source)
        self.assertIn('script src="admin_section_arbiter_model.js"', source)
        self.assertIn('script src="admin_section_summary_model.js"', source)
        self.assertIn('script src="admin_section_stimmung_agent_model.js"', source)
        self.assertIn('script src="admin_section_validation_agent_model.js"', source)
        self.assertIn('script src="admin_section_embedding.js"', source)
        self.assertIn('script src="admin_section_database.js"', source)
        self.assertIn('script src="admin_section_services.js"', source)
        self.assertIn('script src="admin_section_resources.js"', source)
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
        self.assertIn('id="adminStimmungAgentModelForm"', source)
        self.assertIn('id="adminStimmungAgentModelSave"', source)
        self.assertIn('id="adminStimmungAgentModelReadonlyInfo"', source)
        self.assertIn('id="adminValidationAgentModelForm"', source)
        self.assertIn('id="adminValidationAgentModelSave"', source)
        self.assertIn('id="adminValidationAgentModelReadonlyInfo"', source)
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
        self.assertIn("/api/admin/settings/stimmung-agent-model", source)
        self.assertIn("/api/admin/settings/stimmung-agent-model/validate", source)
        self.assertIn("/api/admin/settings/validation-agent-model", source)
        self.assertIn("/api/admin/settings/validation-agent-model/validate", source)
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
