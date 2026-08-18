from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class UiAssetContents:
    values: Mapping[str, str]

    def __getitem__(self, name: str) -> str:
        return self.values[name]

    def _join(self, names: tuple[str, ...]) -> str:
        return "\n".join(self.values[name] for name in names)

    @property
    def admin_front_js(self) -> str:
        return self._join(
            (
                "admin_api_js",
                "admin_ui_common_js",
                "admin_state_js",
                "admin_section_main_model_js",
                "admin_section_arbiter_model_js",
                "admin_section_summary_model_js",
                "admin_section_stimmung_agent_model_js",
                "admin_section_validation_agent_model_js",
                "admin_section_embedding_js",
                "admin_section_database_js",
                "admin_section_services_js",
                "admin_section_resources_js",
                "admin_settings_catalog_js",
                "admin_js",
            )
        )

    @property
    def hermeneutic_admin_front_js(self) -> str:
        return self._join(
            (
                "hermeneutic_admin_api_js",
                "hermeneutic_admin_render_js",
                "hermeneutic_admin_render_identity_read_model_js",
                "hermeneutic_admin_render_identity_static_editor_js",
                "hermeneutic_admin_render_identity_mutable_editor_js",
                "hermeneutic_admin_render_identity_governance_js",
                "hermeneutic_admin_main_js",
            )
        )

    @property
    def identity_front_js(self) -> str:
        return self._join(
            (
                "hermeneutic_admin_api_js",
                "hermeneutic_admin_render_js",
                "hermeneutic_admin_render_identity_read_model_js",
                "hermeneutic_admin_render_identity_static_editor_js",
                "hermeneutic_admin_render_identity_mutable_editor_js",
                "hermeneutic_admin_render_identity_governance_js",
                "identity_api_js",
                "identity_render_runtime_representations_js",
                "identity_main_js",
            )
        )

    @property
    def memory_admin_front_js(self) -> str:
        return self._join(
            (
                "memory_admin_api_js",
                "memory_admin_render_overview_js",
                "memory_admin_render_turns_js",
                "memory_admin_main_js",
            )
        )
