from __future__ import annotations

from typing import Any, Callable, Mapping

import config
from admin.runtime_settings_spec import get_field_spec, get_section_spec
from core import prompt_loader
from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.inputs import recent_window_input as canonical_recent_window_input
from identity import identity_governance


NormalizeStoredPayload = Callable[[str, Mapping[str, Any]], dict[str, dict[str, Any]]]


def redact_payload_for_api(
    section: str,
    payload: Mapping[str, Any],
    *,
    normalize_stored_payload: NormalizeStoredPayload,
) -> dict[str, dict[str, Any]]:
    redacted: dict[str, dict[str, Any]] = {}
    for field_name, field_payload in normalize_stored_payload(section, payload).items():
        spec = get_field_spec(section, field_name)
        if spec.is_secret:
            redacted[field_name] = {
                'is_secret': True,
                'is_set': bool(field_payload.get('is_set')),
                'origin': field_payload.get('origin'),
            }
        else:
            redacted[field_name] = dict(field_payload)
    return redacted


def _secret_effective_source(section: str, field: str, payload: Mapping[str, Any]) -> str:
    spec = get_field_spec(section, field)
    if not spec.is_secret:
        raise ValueError(f'field is not secret: {section}.{field}')

    if section == 'database' and field == 'dsn':
        if str(config.FRIDA_MEMORY_DB_DSN or '').strip():
            return 'env_fallback'
        return 'db_encrypted' if bool(payload.get('is_set')) else 'missing'

    is_set = bool(payload.get('is_set'))
    if not is_set:
        return 'missing'

    origin = str(payload.get('origin') or '').strip()
    if origin == 'env_seed':
        return 'env_fallback'
    return 'db_encrypted'


def describe_secret_sources(
    section: str,
    payload: Mapping[str, Any],
    *,
    normalize_stored_payload: NormalizeStoredPayload,
) -> dict[str, str]:
    normalized = normalize_stored_payload(section, payload)
    secret_sources: dict[str, str] = {}
    for field in get_section_spec(section).fields:
        if not field.is_secret:
            continue
        secret_sources[field.key] = _secret_effective_source(
            section,
            field.key,
            normalized.get(field.key) or {},
        )
    return secret_sources


def _main_hermeneutical_runtime_bricks_text() -> str:
    return "\n".join(
        [
            "Briques runtime encadrees par le Hermeneutical Prompt :",
            "1. Repere temporel global : [RÉFÉRENCE TEMPORELLE] + \"Nous sommes le ...\"",
            "2. Labels Delta-T : [il y a ...]",
            "3. Marqueurs de silence : [— silence de X —]",
            "4. Bloc identites : [IDENTITÉ DU MODÈLE], [IDENTITÉ DE L'UTILISATEUR], lignes - [stability=...; recurrence=...; confidence=...]",
            "5. Resume actif : [Résumé de la période ...]",
            "6. Indices contextuels recents : [Indices contextuels recents]",
            "7. Contexte du souvenir : [Contexte du souvenir — résumé ...]",
            "8. Souvenirs pertinents : [Mémoire — souvenirs pertinents]",
            "9. Contexte web injecte : [RECHERCHE WEB — ...], [FIN DES RÉSULTATS WEB], \"Question :\"",
            "10. Message utilisateur final : dernier message role=user, avec ou sans prefixe \"Question :\"",
        ]
    )


def _shared_openrouter_transport_text(title_field: str, referer_field: str) -> str:
    return (
        "Transport OpenRouter partage via main_model: "
        f"base_url + {referer_field} + api_key + {title_field}."
    )


def get_section_readonly_info(section: str) -> dict[str, dict[str, Any]]:
    get_section_spec(section)
    if section == 'main_model':
        return {
            'system_prompt': {
                'label': 'SYSTEM_PROMPT',
                'value': prompt_loader.get_main_system_prompt(),
                'is_editable': False,
                'source': 'prompt_file',
            },
            'system_prompt_path': {
                'label': 'MAIN_SYSTEM_PROMPT_PATH',
                'value': str(config.MAIN_SYSTEM_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'system_prompt_loader': {
                'label': 'SYSTEM_PROMPT_RUNTIME_SOURCE',
                'value': 'core.prompt_loader.get_main_system_prompt()',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'hermeneutical_prompt': {
                'label': 'HERMENEUTICAL_PROMPT',
                'value': prompt_loader.get_main_hermeneutical_prompt(),
                'is_editable': False,
                'source': 'prompt_file',
            },
            'hermeneutical_prompt_path': {
                'label': 'MAIN_HERMENEUTICAL_PROMPT_PATH',
                'value': str(config.MAIN_HERMENEUTICAL_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'hermeneutical_prompt_loader': {
                'label': 'HERMENEUTICAL_PROMPT_RUNTIME_SOURCE',
                'value': 'core.prompt_loader.get_main_hermeneutical_prompt()',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'hermeneutical_runtime_bricks': {
                'label': 'HERMENEUTICAL_RUNTIME_BRICKS',
                'value': _main_hermeneutical_runtime_bricks_text(),
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'context_max_tokens': {
                'label': 'FRIDA_MAX_TOKENS',
                'value': int(config.MAX_TOKENS),
                'is_editable': False,
                'source': 'config_py',
            },
        }
    if section == 'arbiter_model':
        return {
            'decision_max_tokens': {
                'label': 'decision_max_tokens',
                'value': 600,
                'is_editable': False,
                'source': 'memory_arbiter_py',
            },
            'identity_extractor_max_tokens': {
                'label': 'identity_extractor_max_tokens',
                'value': 700,
                'is_editable': False,
                'source': 'memory_arbiter_py',
            },
            'arbiter_prompt_path': {
                'label': 'ARBITER_PROMPT_PATH',
                'value': str(config.ARBITER_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'identity_extractor_prompt_path': {
                'label': 'IDENTITY_EXTRACTOR_PROMPT_PATH',
                'value': str(config.IDENTITY_EXTRACTOR_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'arbiter_prompt': {
                'label': 'arbiter_prompt',
                'value': prompt_loader.read_prompt_text(str(config.ARBITER_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
            'identity_extractor_prompt': {
                'label': 'identity_extractor_prompt',
                'value': prompt_loader.read_prompt_text(str(config.IDENTITY_EXTRACTOR_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
        }
    if section == 'summary_model':
        return {
            'summary_target_tokens': {
                'label': 'SUMMARY_TARGET_TOKENS',
                'value': int(config.SUMMARY_TARGET_TOKENS),
                'is_editable': False,
                'source': 'config_py',
            },
            'summary_threshold_tokens': {
                'label': 'SUMMARY_THRESHOLD_TOKENS',
                'value': int(config.SUMMARY_THRESHOLD_TOKENS),
                'is_editable': False,
                'source': 'config_py',
            },
            'summary_keep_turns': {
                'label': 'SUMMARY_KEEP_TURNS',
                'value': int(config.SUMMARY_KEEP_TURNS),
                'is_editable': False,
                'source': 'config_py',
            },
            'system_prompt': {
                'label': 'summary_system_prompt',
                'value': prompt_loader.get_summary_system_prompt(),
                'is_editable': False,
                'source': 'prompt_file',
            },
        }
    if section == 'stimmung_agent_model':
        return {
            'prompt_path': {
                'label': 'STIMMUNG_AGENT_PROMPT_PATH',
                'value': 'prompts/stimmung_agent.txt',
                'is_editable': False,
                'source': 'runtime_component',
            },
            'prompt_loader': {
                'label': 'STIMMUNG_AGENT_PROMPT_RUNTIME_SOURCE',
                'value': 'core.stimmung_agent._load_system_prompt()',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'prompt_text': {
                'label': 'stimmung_agent_prompt',
                'value': prompt_loader.read_prompt_text('prompts/stimmung_agent.txt'),
                'is_editable': False,
                'source': 'prompt_file',
            },
            'shared_transport': {
                'label': 'SHARED_OPENROUTER_TRANSPORT',
                'value': _shared_openrouter_transport_text(
                    'main_model.title_stimmung_agent',
                    'main_model.referer_stimmung_agent',
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'recent_window_turn_cap': {
                'label': 'STIMMUNG_CONTEXT_WINDOW_TURNS',
                'value': int(canonical_recent_window_input.MAX_RECENT_TURNS),
                'is_editable': False,
                'source': 'runtime_component',
            },
            'max_context_message_chars': {
                'label': 'STIMMUNG_MAX_CONTEXT_MESSAGE_CHARS',
                'value': 220,
                'is_editable': False,
                'source': 'runtime_component',
            },
            'max_current_turn_chars': {
                'label': 'STIMMUNG_MAX_CURRENT_TURN_CHARS',
                'value': 600,
                'is_editable': False,
                'source': 'runtime_component',
            },
        }
    if section == 'validation_agent_model':
        return {
            'prompt_path': {
                'label': 'VALIDATION_AGENT_PROMPT_PATH',
                'value': 'prompts/validation_agent.txt',
                'is_editable': False,
                'source': 'runtime_component',
            },
            'prompt_loader': {
                'label': 'VALIDATION_AGENT_PROMPT_RUNTIME_SOURCE',
                'value': 'core.hermeneutic_node.validation.validation_agent._load_system_prompt()',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'prompt_text': {
                'label': 'validation_agent_prompt',
                'value': prompt_loader.read_prompt_text('prompts/validation_agent.txt'),
                'is_editable': False,
                'source': 'prompt_file',
            },
            'shared_transport': {
                'label': 'SHARED_OPENROUTER_TRANSPORT',
                'value': _shared_openrouter_transport_text(
                    'main_model.title_validation_agent',
                    'main_model.referer_validation_agent',
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'validation_context_messages_cap': {
                'label': 'VALIDATION_CONTEXT_MESSAGES_CAP',
                'value': canonical_recent_context_input.VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES,
                'is_editable': False,
                'source': 'runtime_component',
            },
            'validation_context_message_chars': {
                'label': 'VALIDATION_CONTEXT_MESSAGE_CHARS',
                'value': 420,
                'is_editable': False,
                'source': 'runtime_component',
            },
            'validated_output_contract': {
                'label': 'VALIDATED_OUTPUT_ARBITER_CONTRACT',
                'value': '{"schema_version":"v1","final_judgment_posture":"answer|clarify|suspend","final_output_regime":"simple|meta","arbiter_reason":"raison_courte_lisible"}',
                'is_editable': False,
                'source': 'runtime_contract',
            },
        }
    if section == 'services':
        return {
            'web_reformulation_max_tokens': {
                'label': 'web_reformulation_max_tokens',
                'value': 40,
                'is_editable': False,
                'source': 'prompt_file',
            },
            'web_reformulation_system_prompt': {
                'label': 'web_reformulation_system_prompt',
                'value': prompt_loader.get_web_reformulation_prompt(),
                'is_editable': False,
                'source': 'prompt_file',
            },
        }
    if section == 'identity_governance':
        return {
            'surface_route': {
                'label': 'IDENTITY_GOVERNANCE_SURFACE',
                'value': '/hermeneutic-admin',
                'is_editable': False,
                'source': 'surface_contract',
            },
            'read_route': {
                'label': 'IDENTITY_GOVERNANCE_READ_ROUTE',
                'value': identity_governance.READ_ROUTE,
                'is_editable': False,
                'source': 'surface_contract',
            },
            'update_route': {
                'label': 'IDENTITY_GOVERNANCE_UPDATE_ROUTE',
                'value': identity_governance.UPDATE_ROUTE,
                'is_editable': False,
                'source': 'surface_contract',
            },
            'operator_scope': {
                'label': 'IDENTITY_GOVERNANCE_OPERATOR_SCOPE',
                'value': (
                    "Section runtime dediee aux seuils identity gouvernables. "
                    "La lecture/edition operateur reste portee par /hermeneutic-admin, "
                    "pas par la facade /admin generique."
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
        }
    return {}
