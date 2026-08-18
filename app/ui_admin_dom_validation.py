from __future__ import annotations

import re
from typing import Any, Dict

from ui_asset_validation_context import UiAssetContents


def validate_admin_dom(assets: UiAssetContents) -> Dict[str, Any]:
    admin_api_js = assets["admin_api_js"]
    admin_html = assets["admin_html"]
    admin_front_js = assets.admin_front_js

    legacy_admin_storage_key = "frida." + "adminToken"
    legacy_admin_header = "X-Admin" + "-Token"
    if legacy_admin_storage_key in admin_api_js:
        raise RuntimeError("stockage session token admin obsolete encore present")
    if legacy_admin_header in admin_api_js:
        raise RuntimeError("header admin token obsolete encore present")
    dom_hook_ids = sorted(set(re.findall(r'document\.getElementById\("([^"]+)"\)', admin_front_js)))
    missing_dom_hook_ids = [hook_id for hook_id in dom_hook_ids if f'id="{hook_id}"' not in admin_html]
    if missing_dom_hook_ids:
        raise RuntimeError(f"hooks DOM admin manquants dans admin.html: {missing_dom_hook_ids}")
    dynamic_getelement_templates = sorted(
        set(re.findall(r'document\.getElementById\(`([^`]*\$\{[^`]+\}[^`]*)`\)', admin_front_js))
    )
    expected_dynamic_getelement_templates = {
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
    }
    if set(dynamic_getelement_templates) != expected_dynamic_getelement_templates:
        missing = sorted(expected_dynamic_getelement_templates - set(dynamic_getelement_templates))
        extra = sorted(set(dynamic_getelement_templates) - expected_dynamic_getelement_templates)
        raise RuntimeError(
            "templates getElementById dynamiques invalides: "
            f"missing={missing}, extra={extra}"
        )
    dynamic_id_assignment_templates = sorted(
        set(re.findall(r'\.id\s*=\s*`([^`]*\$\{[^`]+\}[^`]*)`', admin_front_js))
    )
    expected_dynamic_id_assignment_templates = {
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
    }
    if set(dynamic_id_assignment_templates) != expected_dynamic_id_assignment_templates:
        missing = sorted(expected_dynamic_id_assignment_templates - set(dynamic_id_assignment_templates))
        extra = sorted(set(dynamic_id_assignment_templates) - expected_dynamic_id_assignment_templates)
        raise RuntimeError(
            "templates id dynamiques generes invalides: "
            f"missing={missing}, extra={extra}"
        )
    def _normalize_dynamic_id_template(raw: str) -> str:
        return re.sub(r"\$\{[^}]+\}", "${*}", raw)
    normalized_dynamic_getelement_templates = sorted(
        {_normalize_dynamic_id_template(template) for template in dynamic_getelement_templates}
    )
    normalized_dynamic_id_assignment_templates = sorted(
        {_normalize_dynamic_id_template(template) for template in dynamic_id_assignment_templates}
    )
    if normalized_dynamic_getelement_templates != normalized_dynamic_id_assignment_templates:
        raise RuntimeError(
            "coherence templates dynamiques getElementById/id assignee invalide: "
            f"lookup={normalized_dynamic_getelement_templates}, "
            f"generated={normalized_dynamic_id_assignment_templates}"
        )
    query_selector_matches = re.findall(
        r'document\.querySelector\("([^"]+)"\)|document\.querySelector\(`([^`]+)`\)',
        admin_front_js,
    )
    query_selectors = sorted(
        {
            selector
            for quoted_selector, template_selector in query_selector_matches
            for selector in [quoted_selector or template_selector]
            if selector
        }
    )
    expected_query_selectors = {
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
    }
    if set(query_selectors) != expected_query_selectors:
        missing = sorted(expected_query_selectors - set(query_selectors))
        extra = sorted(set(query_selectors) - expected_query_selectors)
        raise RuntimeError(
            "query selectors admin invalides: "
            f"missing={missing}, extra={extra}"
        )
    if 'class="admin-secret-card"' not in admin_html:
        raise RuntimeError("class admin-secret-card absente de admin.html")
    data_selectors = sorted(
        {
            match.group(1)
            for selector in query_selectors
            for match in [re.match(r'^\[(data-[a-z-]+)="\$\{field\}"\]$', selector)]
            if match
        }
    )
    def _camel_to_kebab(raw: str) -> str:
        return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", raw).lower()
    dataset_attrs = sorted(
        {
            f"data-{_camel_to_kebab(dataset_key)}"
            for dataset_key in re.findall(r"field\.dataset\.([a-zA-Z0-9_]+)\s*=\s*spec\.key", admin_front_js)
        }
    )
    if set(data_selectors) != set(dataset_attrs):
        missing = sorted(set(data_selectors) - set(dataset_attrs))
        extra = sorted(set(dataset_attrs) - set(data_selectors))
        raise RuntimeError(
            "dataset attrs admin invalides: "
            f"missing={missing}, extra={extra}"
        )
    field_container_ids = [
        "adminMainModelFields",
        "adminArbiterModelFields",
        "adminSummaryModelFields",
        "adminStimmungAgentModelFields",
        "adminValidationAgentModelFields",
        "adminEmbeddingFields",
        "adminDatabaseFields",
        "adminServicesFields",
        "adminResourcesFields",
    ]
    missing_field_containers = [field_id for field_id in field_container_ids if f'id="{field_id}"' not in admin_html]
    if missing_field_containers:
        raise RuntimeError(f"containers champs section manquants dans admin.html: {missing_field_containers}")
    return {
        "admin_dom_hook_ids_checked": dom_hook_ids,
        "admin_dynamic_getelement_templates_expected": sorted(expected_dynamic_getelement_templates),
        "admin_dynamic_getelement_templates_found": dynamic_getelement_templates,
        "admin_dynamic_id_assignment_templates_expected": sorted(expected_dynamic_id_assignment_templates),
        "admin_dynamic_id_assignment_templates_found": dynamic_id_assignment_templates,
        "admin_dynamic_templates_lookup_families_checked": normalized_dynamic_getelement_templates,
        "admin_dynamic_templates_generated_families_checked": normalized_dynamic_id_assignment_templates,
        "admin_query_selectors_expected": sorted(expected_query_selectors),
        "admin_query_selectors_found": query_selectors,
        "admin_data_selectors_checked": data_selectors,
        "admin_dataset_attrs_checked": dataset_attrs,
        "admin_field_containers_checked": field_container_ids,
    }


def validate_admin_frontend_markers(assets: UiAssetContents) -> Dict[str, Any]:
    admin_front_js = assets.admin_front_js

    admin_js_markers = [
        "/api/admin/settings/status",
        "/api/admin/settings/main-model",
        "/api/admin/settings/main-model/validate",
        "/api/admin/settings/arbiter-model",
        "/api/admin/settings/arbiter-model/validate",
        "/api/admin/settings/identity-extractor-model",
        "/api/admin/settings/identity-extractor-model/validate",
        "/api/admin/settings/identity-periodic-model",
        "/api/admin/settings/identity-periodic-model/validate",
        "/api/admin/settings/memory-arbiter-model",
        "/api/admin/settings/memory-arbiter-model/validate",
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
        "window.FridaAdminState",
        "createAdminState",
        "initializeAdminSectionDrafts",
        "adminMainModelSave",
        "adminMainModelApiKeyReplace",
        "adminMainModelSystemPromptInfo",
        "adminMainModelHermeneuticalPromptInfo",
        "adminMainModelReadonlyInfo",
        "hermeneutical_prompt",
        "renderReadonlyInfoEntries",
        "renderReadonlyInfoCards",
        "applyFieldError",
        "createMainModelSectionController",
        "createArbiterModelSectionController",
        "createSummaryModelSectionController",
        "createStimmungAgentModelSectionController",
        "createValidationAgentModelSectionController",
        "createEmbeddingSectionController",
        "createDatabaseSectionController",
        "createServicesSectionController",
        "createResourcesSectionController",
        "response_max_tokens",
        "adminArbiterModelSave",
        "adminArbiterModelReadonlyInfo",
        "adminSummaryModelSave",
        "adminSummaryModelReadonlyInfo",
        "adminStimmungAgentModelSave",
        "adminStimmungAgentModelReadonlyInfo",
        "adminValidationAgentModelSave",
        "adminValidationAgentModelReadonlyInfo",
        "adminEmbeddingSave",
        "adminEmbeddingTokenReplace",
        "adminDatabaseSave",
        "adminDatabaseDsnReplace",
        "adminServicesSave",
        "adminServicesCrawl4aiTokenReplace",
        "adminServicesReadonlyInfo",
        "crawl4ai_explicit_url_max_chars",
        "adminResourcesSave",
        "adminSectionGrid",
    ]
    for marker in admin_js_markers:
        if marker not in admin_front_js:
            raise RuntimeError(f"marker admin frontend manquant: {marker}")
    admin_js_forbidden_markers = [
        "/api/admin/logs",
        "/api/admin/restart",
        "loadLogs",
        "restartService",
        "admin-old",
    ]
    for marker in admin_js_forbidden_markers:
        if marker in admin_front_js:
            raise RuntimeError(f"marker admin frontend legacy inattendu: {marker}")
    return {
        "admin_js_markers": admin_js_markers,
        "admin_js_forbidden_markers": admin_js_forbidden_markers,
    }
