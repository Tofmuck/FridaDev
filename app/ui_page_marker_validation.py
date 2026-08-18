from __future__ import annotations

from typing import Any, Dict

from ui_asset_validation_context import UiAssetContents


def validate_foundation_page_markers(assets: UiAssetContents) -> Dict[str, Any]:
    index_html = assets["index_html"]
    admin_html = assets["admin_html"]
    log_html = assets["log_html"]
    hermeneutic_admin_html = assets["hermeneutic_admin_html"]

    index_markers = [
        'src="./fridalogo.png"',
        'href="styles.css"',
        'script src="app.js"',
        'id="threads"',
        'id="log"',
        'id="message"',
        'id="btnIdentity"',
        'href="/identity"',
        'id="btnMemoryAdmin"',
        'href="/memory-admin"',
        'id="btnDashboard"',
        'href="/dashboard"',
    ]
    for marker in index_markers:
        if marker not in index_html:
            raise RuntimeError(f"marker index.html manquant: {marker}")
    index_hermeneutic_markers = [
        'id="btnHermeneuticAdmin"',
        'href="/hermeneutic-admin"',
    ]
    for marker in index_hermeneutic_markers:
        if marker not in index_html:
            raise RuntimeError(f"marker index.html hermeneutic admin manquant: {marker}")
    admin_markers = [
        "Admin de configuration",
        'href="admin.css"',
        'href="/dashboard"',
        'href="/identity"',
        'href="/memory-admin"',
        'script src="admin_api.js"',
        'script src="admin_ui_common.js"',
        'script src="admin_state.js"',
        'script src="admin_section_main_model.js"',
        'script src="admin_section_arbiter_model.js"',
        'script src="admin_section_summary_model.js"',
        'script src="admin_section_stimmung_agent_model.js"',
        'script src="admin_section_validation_agent_model.js"',
        'script src="admin_section_embedding.js"',
        'script src="admin_section_database.js"',
        'script src="admin_section_services.js"',
        'script src="admin_section_resources.js"',
        'script src="admin_settings_catalog.js"',
        'script src="admin.js"',
        'id="adminRefresh"',
        'id="adminStatusBanner"',
        'id="adminMainModelForm"',
        'id="adminMainModelValidate"',
        'id="adminMainModelSave"',
        'id="adminMainModelApiKeyReplace"',
        'id="adminMainModelSystemPromptInfo"',
        'id="adminMainModelHermeneuticalPromptInfo"',
        'id="adminMainModelReadonlyInfo"',
        "System Prompt",
        "Hermeneutical Prompt",
        'id="adminMainModelChecks"',
        'id="adminArbiterModelForm"',
        'id="adminArbiterModelValidate"',
        'id="adminArbiterModelSave"',
        'id="adminArbiterModelReadonlyInfo"',
        'id="adminArbiterModelChecks"',
        'id="adminSummaryModelForm"',
        'id="adminSummaryModelValidate"',
        'id="adminSummaryModelSave"',
        'id="adminSummaryModelReadonlyInfo"',
        'id="adminSummaryModelChecks"',
        'id="adminStimmungAgentModelForm"',
        'id="adminStimmungAgentModelValidate"',
        'id="adminStimmungAgentModelSave"',
        'id="adminStimmungAgentModelReadonlyInfo"',
        'id="adminStimmungAgentModelChecks"',
        'id="adminValidationAgentModelForm"',
        'id="adminValidationAgentModelValidate"',
        'id="adminValidationAgentModelSave"',
        'id="adminValidationAgentModelReadonlyInfo"',
        'id="adminValidationAgentModelChecks"',
        'id="adminEmbeddingForm"',
        'id="adminEmbeddingValidate"',
        'id="adminEmbeddingSave"',
        'id="adminEmbeddingTokenReplace"',
        'id="adminEmbeddingChecks"',
        'id="adminDatabaseForm"',
        'id="adminDatabaseValidate"',
        'id="adminDatabaseSave"',
        'id="adminDatabaseDsnReplace"',
        'id="adminDatabaseChecks"',
        'id="adminServicesForm"',
        'id="adminServicesValidate"',
        'id="adminServicesSave"',
        'id="adminServicesCrawl4aiTokenReplace"',
        'id="adminServicesReadonlyInfo"',
        'id="adminServicesChecks"',
        'id="adminResourcesForm"',
        'id="adminResourcesValidate"',
        'id="adminResourcesSave"',
        'id="adminResourcesChecks"',
        'id="adminSectionGrid"',
    ]
    for marker in admin_markers:
        if marker not in admin_html:
            raise RuntimeError(f"marker admin.html manquant: {marker}")
    admin_html_forbidden_markers = [
        'id="rows"',
        'id="restart"',
        "admin-old.html",
        "admin-old.js",
        "/admin-old",
    ]
    for marker in admin_html_forbidden_markers:
        if marker in admin_html:
            raise RuntimeError(f"marker admin.html legacy inattendu: {marker}")
    log_markers = [
        "Logs applicatifs",
        'href="admin.css"',
        'href="/dashboard"',
        'href="/identity"',
        'href="/admin"',
        'href="/hermeneutic-admin"',
        'href="/memory-admin"',
        'id="logRefresh"',
    ]
    for marker in log_markers:
        if marker not in log_html:
            raise RuntimeError(f"marker log.html manquant: {marker}")
    hermeneutic_admin_markers = [
        "Hermeneutic admin",
        'href="admin.css"',
        'href="/dashboard"',
        'href="/identity"',
        'href="/memory-admin"',
        'script src="admin_api.js"',
        'script src="admin_ui_common.js"',
        'script src="hermeneutic_admin/api.js"',
        'script src="hermeneutic_admin/render.js"',
        'script src="hermeneutic_admin/render_identity_read_model.js"',
        'script src="hermeneutic_admin/render_identity_static_editor.js"',
        'script src="hermeneutic_admin/render_identity_mutable_editor.js"',
        'script src="hermeneutic_admin/render_identity_governance.js"',
        'script src="hermeneutic_admin/main.js"',
        'id="hermeneuticAdminRefresh"',
        'id="hermeneuticConversationId"',
        'id="hermeneuticTurnId"',
        'id="hermeneuticTurnStages"',
        'id="hermeneuticArbiterList"',
        'id="hermeneuticIdentityStaticEditStatus"',
        'id="hermeneuticIdentityStaticEditors"',
        'id="hermeneuticIdentityMutableEditStatus"',
        'id="hermeneuticIdentityMutableEditors"',
        'id="hermeneuticIdentityGovernanceStatus"',
        'id="hermeneuticIdentityGovernanceMeta"',
        'id="hermeneuticIdentityGovernance"',
        'id="hermeneuticIdentityReadModel"',
        'id="hermeneuticIdentityList"',
        'id="hermeneuticCorrectionsList"',
        "Vue d'ensemble",
        "Diagnostic par tour",
        "Decisions arbitre",
        "Vue unifiee identity",
        "Gouvernance identity",
        "Fragments legacy d'identite",
        "static + mutable narrative",
        "Lecture + edition mutable + statique",
        "Corrections recentes",
    ]
    for marker in hermeneutic_admin_markers:
        if marker not in hermeneutic_admin_html:
            raise RuntimeError(f"marker hermeneutic-admin.html manquant: {marker}")
    return {
        "index_markers": index_markers,
        "index_hermeneutic_markers": index_hermeneutic_markers,
        "admin_markers": admin_markers,
        "log_markers": log_markers,
        "hermeneutic_admin_markers": hermeneutic_admin_markers,
        "admin_html_forbidden_markers": admin_html_forbidden_markers,
    }


def validate_identity_page_markers(assets: UiAssetContents) -> Dict[str, Any]:
    identity_html = assets["identity_html"]

    identity_markers = [
        "Identity",
        'href="admin.css"',
        'href="/dashboard"',
        'href="/admin"',
        'href="/log"',
        'href="/hermeneutic-admin"',
        'href="/memory-admin"',
        "Les 4 blocs a editer en premier",
        "Source canonique, pilotage systeme et formes compilees",
        "Etat courant par sujet",
        "Repere runtime compile utile au pilotage",
        "Caps, budgets et legacy",
        "Legacy, evidences et conflits",
        "Corrections recentes et sorties utiles",
        'script src="identity/api.js"',
        'script src="identity/render_identity_runtime_representations.js"',
        'script src="identity/main.js"',
    ]
    for marker in identity_markers:
        if marker not in identity_html:
            raise RuntimeError(f"marker identity.html manquant: {marker}")
    return {"identity_markers": identity_markers}


def validate_memory_admin_page_markers(assets: UiAssetContents) -> Dict[str, Any]:
    memory_admin_html = assets["memory_admin_html"]

    memory_admin_markers = [
        "Memory Admin",
        'href="admin.css"',
        'href="/dashboard"',
        'href="/admin"',
        'href="/log"',
        'href="/identity"',
        'href="/hermeneutic-admin"',
        'href="/memory-admin"',
        'script src="memory_admin/api.js"',
        'script src="memory_admin/render_overview.js"',
        'script src="memory_admin/render_turns.js"',
        'script src="memory_admin/main.js"',
        "Etat memoire durable",
        "Retrieval, embeddings et couverture recente",
        "Panier pre-arbitre, arbitre et runtime process-local",
        "Injection memoire et lecture recente",
        "Details memory/RAG par tour",
        "Decisions arbitre persistees",
        "persistance durable, agregat calcule, runtime process-local et historique logs",
    ]
    for marker in memory_admin_markers:
        if marker not in memory_admin_html:
            raise RuntimeError(f"marker memory-admin.html manquant: {marker}")
    return {"memory_admin_markers": memory_admin_markers}


def validate_dashboard_page_markers(assets: UiAssetContents) -> Dict[str, Any]:
    dashboard_html = assets["dashboard_html"]
    dashboard_main_js = assets["dashboard_main_js"]

    dashboard_markers = [
        "Dashboard long terme",
        'href="admin.css"',
        'href="dashboard/styles.css"',
        'href="/dashboard"',
        'href="/log"',
        'href="/memory-admin"',
        'href="/hermeneutic-admin"',
        'href="/identity"',
        'data-dashboard-screen="overview"',
        'id="dashboardPrimaryWindows"',
        'id="dashboardStatusBanner"',
        'id="dashboardPulseCards"',
        'id="dashboardTrendCards"',
        'id="dashboardConversationsTable"',
        'id="dashboardDrilldown"',
        'id="dashboardTurnsList"',
        'id="dashboardInspectionBody"',
        'data-window="24h"',
        'data-window="7d"',
        'data-window="30d"',
        'script src="admin_api.js"',
        'script src="dashboard/main.js"',
    ]
    for marker in dashboard_markers:
        if marker not in dashboard_html:
            raise RuntimeError(f"marker dashboard.html manquant: {marker}")
    dashboard_js_markers = [
        "Tours reussis",
        "Reponses degradees",
        "Problemes rencontres",
        "Latence moyenne",
        "Memoire utilisee",
        "Recherche web utile",
        "source.coverage",
        "metric_buckets",
        "dashboard_metric_buckets.providers",
        "agregats persistants",
        "dashboardDrilldown",
        "dashboardInspectionBody",
        "Afficher le contenu complet",
        "/content?",
    ]
    for marker in dashboard_js_markers:
        if marker not in dashboard_main_js:
            raise RuntimeError(f"marker dashboard/main.js manquant: {marker}")
    dashboard_forbidden_markers = [
        "/api/admin/logs",
        "prompt principal",
        "payload modele principal",
        "Lot 5",
        "content-free",
        "Frontieres",
    ]
    for marker in dashboard_forbidden_markers:
        if marker in dashboard_html or marker in dashboard_main_js:
            raise RuntimeError(f"marker dashboard Lot 6/gate inattendu: {marker}")
    return {
        "dashboard_markers": dashboard_markers,
        "dashboard_forbidden_markers": dashboard_forbidden_markers,
    }
