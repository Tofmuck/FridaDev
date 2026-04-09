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


class FrontendIdentitySurfacePhase6Tests(unittest.TestCase):
    def test_identity_page_exists_with_expected_french_sections_and_shared_assets(self) -> None:
        source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")
        found_scripts = re.findall(r'<script\s+src="([^"]+)"></script>', source)

        self.assertIn("<title>Identity</title>", source)
        self.assertIn("<h1>Identity</h1>", source)
        self.assertIn('href="admin.css"', source)
        self.assertNotIn('href="styles.css"', source)
        self.assertIn("Pilotage canonique actif", source)
        self.assertIn("Les 4 blocs a editer en premier", source)
        self.assertIn("Source canonique, pilotage systeme et formes compilees", source)
        self.assertIn("Pilotage systeme distinct", source)
        self.assertIn("Etat courant par sujet", source)
        self.assertIn("Cette synthese compacte dit vrai", source)
        self.assertIn("Repere runtime compile utile au pilotage", source)
        self.assertIn("Voir le detail diagnostique", source)
        self.assertIn('href="/hermeneutic-admin#hermeneutic-identity-runtime-title"', source)
        self.assertIn("Seuils et limites", source)
        self.assertIn("Diagnostics / historique", source)
        self.assertIn("Ouvrir legacy, evidences, conflits et corrections", source)
        self.assertIn('id="identityDiagnosticsDisclosure"', source)
        self.assertIn('id="identityDiagnosticsSummary"', source)
        self.assertIn("Legacy, evidences et conflits", source)
        self.assertIn("Corrections recentes et sorties utiles", source)
        self.assertNotIn(">Prompt</span>", source)
        self.assertNotIn('class="admin-sublead"', source)
        self.assertIn('id="identityPilotageGrid"', source)
        self.assertIn('id="identityLlmStaticCard"', source)
        self.assertIn('id="identityLlmMutableCard"', source)
        self.assertIn('id="identityUserStaticCard"', source)
        self.assertIn('id="identityUserMutableCard"', source)
        self.assertIn('href="/"', source)
        self.assertIn('href="/admin"', source)
        self.assertIn('href="/log"', source)
        self.assertIn('href="/hermeneutic-admin"', source)
        self.assertIn('id="identityRuntimeSummary"', source)
        self.assertNotIn('id="identityStructuredRepresentation"', source)
        self.assertNotIn('id="identityInjectedRepresentation"', source)
        self.assertEqual(
            found_scripts,
            [
                "admin_api.js",
                "admin_ui_common.js",
                "hermeneutic_admin/api.js",
                "hermeneutic_admin/render.js",
                "hermeneutic_admin/render_identity_read_model.js",
                "hermeneutic_admin/render_identity_static_editor.js",
                "hermeneutic_admin/render_identity_mutable_editor.js",
                "hermeneutic_admin/render_identity_governance.js",
                "identity/api.js",
                "identity/render_identity_runtime_representations.js",
                "identity/main.js",
            ],
        )

        self.assertLess(source.index('id="identity-pilotage-title"'), source.index('id="identity-structure-title"'))
        self.assertLess(source.index('id="identity-pilotage-title"'), source.index('id="identity-current-state-title"'))
        self.assertLess(source.index('id="identity-pilotage-title"'), source.index('id="identity-runtime-summary-title"'))
        self.assertLess(source.index('id="identity-pilotage-title"'), source.index('id="identity-governance-title"'))
        self.assertLess(source.index('id="identity-governance-title"'), source.index('id="identity-diagnostics-title"'))
        self.assertLess(source.index('id="identityLlmStaticCard"'), source.index('id="identityLlmMutableCard"'))
        self.assertLess(source.index('id="identityLlmMutableCard"'), source.index('id="identityUserStaticCard"'))
        self.assertLess(source.index('id="identityUserStaticCard"'), source.index('id="identityUserMutableCard"'))
        self.assertIn('<details id="identityDiagnosticsDisclosure" class="admin-readonly-panel admin-disclosure">', source)

    def test_identity_navigation_links_exist_on_required_surfaces(self) -> None:
        index_source = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.html").read_text(encoding="utf-8")
        log_source = (APP_DIR / "web" / "log.html").read_text(encoding="utf-8")
        hermeneutic_source = (APP_DIR / "web" / "hermeneutic-admin.html").read_text(encoding="utf-8")
        identity_source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")

        self.assertIn('href="/identity"', index_source)
        self.assertIn('href="/identity"', admin_source)
        self.assertIn('href="/identity"', log_source)
        self.assertIn('href="/identity"', hermeneutic_source)
        self.assertIn('href="/"', identity_source)
        self.assertIn('href="/admin"', identity_source)
        self.assertIn('href="/log"', identity_source)
        self.assertIn('href="/hermeneutic-admin"', identity_source)

    def test_identity_page_uses_runtime_representations_route_and_files_stay_bounded(self) -> None:
        api_source = (APP_DIR / "web" / "identity" / "api.js").read_text(encoding="utf-8")
        shared_api_source = (APP_DIR / "web" / "hermeneutic_admin" / "api.js").read_text(
            encoding="utf-8"
        )
        main_source = (APP_DIR / "web" / "identity" / "main.js").read_text(encoding="utf-8")
        render_source = (
            APP_DIR / "web" / "identity" / "render_identity_runtime_representations.js"
        ).read_text(encoding="utf-8")

        combined = f"{shared_api_source}\n{api_source}\n{main_source}\n{render_source}"
        found_endpoints = set(
            re.findall(
                r"/api/admin/(?:identity/(?:read-model|runtime-representations|mutable|static|governance)|hermeneutics/corrections-export)",
                combined,
            )
        )
        self.assertEqual(
            found_endpoints,
            {
                "/api/admin/identity/read-model",
                "/api/admin/identity/runtime-representations",
                "/api/admin/identity/mutable",
                "/api/admin/identity/static",
                "/api/admin/identity/governance",
                "/api/admin/hermeneutics/corrections-export",
            },
        )
        self.assertNotIn("/api/admin/hermeneutics/identity/force-accept", combined)
        self.assertNotIn("/api/admin/hermeneutics/identity/force-reject", combined)
        self.assertNotIn("/api/admin/hermeneutics/identity/relabel", combined)
        self.assertLessEqual(len(api_source.splitlines()), 499)
        self.assertLessEqual(len(main_source.splitlines()), 499)
        self.assertLessEqual(len(render_source.splitlines()), 499)

    def test_identity_injected_meta_describes_injection_state_not_legacy_reactivation_count(self) -> None:
        main_source = (APP_DIR / "web" / "identity" / "main.js").read_text(encoding="utf-8")

        self.assertIn("Forme compilee injectee presente", main_source)
        self.assertIn("Aucune forme compilee injectee", main_source)
        self.assertIn("elements.injectedMeta.textContent = injectedMetaText(injectedBlock);", main_source)
        self.assertIn('title: "LLM statique"', main_source)
        self.assertIn('title: "LLM mutable"', main_source)
        self.assertIn('title: "User statique"', main_source)
        self.assertIn('title: "User mutable"', main_source)
        self.assertNotIn("id(s) legacy reactivés", main_source)
        self.assertNotIn("id(s) legacy reactives", main_source)

    def test_identity_runtime_render_labels_compile_and_system_guidance_distinct(self) -> None:
        render_source = (
            APP_DIR / "web" / "identity" / "render_identity_runtime_representations.js"
        ).read_text(encoding="utf-8")

        self.assertIn("compile=", render_source)
        self.assertIn("pilotage_systeme=distinct", render_source)
        self.assertIn("Projection runtime compilee pour le jugement", render_source)
        self.assertIn("Forme runtime compilee injectee", render_source)
        self.assertNotIn("prompt=", render_source)

    def test_identity_current_state_uses_summary_read_model_mode(self) -> None:
        main_source = (APP_DIR / "web" / "identity" / "main.js").read_text(encoding="utf-8")
        read_model_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_read_model.js"
        ).read_text(encoding="utf-8")

        self.assertIn('viewMode: "summary"', main_source)
        self.assertIn("renderSubjectSummary", read_model_source)
        self.assertIn(
            "Le detail editable du statique et de la mutable reste dans Pilotage canonique actif.",
            read_model_source,
        )
        self.assertIn("element(s) visibles plus bas", read_model_source)
        self.assertIn('const viewMode = toText(options.viewMode).toLowerCase() === "summary"', read_model_source)

    def test_identity_diagnostics_history_is_collapsed_by_default_with_visible_summary_counts(self) -> None:
        main_source = (APP_DIR / "web" / "identity" / "main.js").read_text(encoding="utf-8")
        html_source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")
        css_source = (APP_DIR / "web" / "admin.css").read_text(encoding="utf-8")

        self.assertIn("syncDiagnosticsSummary", main_source)
        self.assertIn("state.correctionsPayload = payload;", main_source)
        self.assertIn("legacy=", main_source)
        self.assertIn("evidences=", main_source)
        self.assertIn("conflits=", main_source)
        self.assertIn("corrections=", main_source)
        self.assertIn("Replie par defaut", html_source)
        self.assertIn("identityDiagnosticsDisclosure", html_source)
        self.assertNotIn('id="identityDiagnosticsDisclosure" class="admin-readonly-panel admin-disclosure" open', html_source)
        self.assertIn(".admin-disclosure-summary", css_source)
        self.assertIn(".admin-disclosure[open] > .admin-disclosure-summary", css_source)

    def test_identity_runtime_section_is_compact_and_points_to_hermeneutic_admin_detail(self) -> None:
        source = (APP_DIR / "web" / "identity.html").read_text(encoding="utf-8")
        main_source = (APP_DIR / "web" / "identity" / "main.js").read_text(encoding="utf-8")
        render_source = (
            APP_DIR / "web" / "identity" / "render_identity_runtime_representations.js"
        ).read_text(encoding="utf-8")

        self.assertIn("Repere runtime compile utile au pilotage", source)
        self.assertIn("Voir le detail diagnostique", source)
        self.assertIn('href="/hermeneutic-admin#hermeneutic-identity-runtime-title"', source)
        self.assertIn('id="identityRuntimeSummary"', source)
        self.assertNotIn('id="identityStructuredRepresentation"', source)
        self.assertNotIn('id="identityInjectedRepresentation"', source)
        self.assertIn("renderIdentityRuntimeSummary", main_source)
        self.assertIn("renderIdentityRuntimeSummary", render_source)
        self.assertIn("Projection jugement", render_source)
        self.assertIn("Injection reponse finale", render_source)
        self.assertNotIn("elements.structuredRepresentation", main_source)
        self.assertNotIn("elements.injectedRepresentation", main_source)

    def test_identity_top_cards_expose_operator_states_and_llm_severity_split(self) -> None:
        static_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_static_editor.js"
        ).read_text(encoding="utf-8")
        mutable_source = (
            APP_DIR / "web" / "hermeneutic_admin" / "render_identity_mutable_editor.js"
        ).read_text(encoding="utf-8")

        self.assertIn("Etat degrade: llm.static absente.", static_source)
        self.assertIn("Le noyau identitaire stable du modele doit etre present.", static_source)
        self.assertIn('`Etat: ${hasContent ? "Presente" : "Absente"}`', static_source)
        self.assertIn('`Runtime: ${loadedForRuntime ? "Charge" : "Non charge"}`', static_source)
        self.assertIn('`Injection: ${activelyInjected ? "Injecte" : "Non injecte"}`', static_source)

        self.assertIn("Absente: aucune modulation identitaire active pour le modele.", mutable_source)
        self.assertIn(
            "La mutable reste editable sans signaler un degrade critique.",
            mutable_source,
        )
        self.assertIn('`Etat: ${hasContent ? "Presente" : "Absente"}`', mutable_source)
        self.assertIn('`Runtime: ${loadedForRuntime ? "Charge" : "Non charge"}`', mutable_source)
        self.assertIn('`Injection: ${activelyInjected ? "Injecte" : "Non injecte"}`', mutable_source)
        self.assertNotIn("Etat degrade: llm.mutable", mutable_source)


if __name__ == "__main__":
    unittest.main()
