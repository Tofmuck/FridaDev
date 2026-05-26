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
            "2. Labels Delta-T : [lundi 18 mai 2026 à 19h27 Europe/Paris — aujourd'hui]",
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
    if section == 'memory_arbiter_model':
        return {
            'prompt_path': {
                'label': 'ARBITER_PROMPT_PATH',
                'value': str(config.ARBITER_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'prompt_loader': {
                'label': 'ARBITER_PROMPT_RUNTIME_SOURCE',
                'value': 'memory.arbiter._load_prompt(config.ARBITER_PROMPT_PATH, "arbiter")',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'system_prompt': {
                'label': 'arbiter_prompt',
                'value': prompt_loader.read_prompt_text(str(config.ARBITER_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
            'shared_transport': {
                'label': 'OPENROUTER_SHARED_TRANSPORT',
                'value': _shared_openrouter_transport_text('main_model.title_arbiter', 'main_model.referer_arbiter'),
                'is_editable': False,
                'source': 'main_model_runtime_settings',
            },
            'benchmark_decision': {
                'label': 'ARBITER_BENCHMARK_DECISION',
                'value': 'benchmark/results/arbiter/2026-05-18-arbiter-final-tournament-summary.md',
                'is_editable': False,
                'source': 'benchmark_artifact',
            },
        }
    if section == 'identity_extractor_model':
        return {
            'prompt_path': {
                'label': 'IDENTITY_EXTRACTOR_PROMPT_PATH',
                'value': str(config.IDENTITY_EXTRACTOR_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'prompt_loader': {
                'label': 'IDENTITY_EXTRACTOR_PROMPT_RUNTIME_SOURCE',
                'value': 'memory.arbiter._load_prompt(config.IDENTITY_EXTRACTOR_PROMPT_PATH, "identity_extractor")',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'system_prompt': {
                'label': 'identity_extractor_prompt',
                'value': prompt_loader.read_prompt_text(str(config.IDENTITY_EXTRACTOR_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
            'shared_transport': {
                'label': 'OPENROUTER_SHARED_TRANSPORT',
                'value': _shared_openrouter_transport_text(
                    'main_model.title_identity_extractor',
                    'main_model.referer_identity_extractor',
                ),
                'is_editable': False,
                'source': 'main_model_runtime_settings',
            },
            'benchmark_decision': {
                'label': 'IDENTITY_EXTRACTOR_BENCHMARK_DECISION',
                'value': 'benchmark/results/identity_extractor/2026-05-18-identity-extractor-human-hermeneutic.md',
                'is_editable': False,
                'source': 'benchmark_artifact',
            },
            'transition_note': {
                'label': 'IDENTITY_EXTRACTOR_DECOUPLING',
                'value': (
                    'extract_identities() uses identity_extractor_model. '
                    'mutable_identity_judge_v2 uses identity_periodic_model; arbiter_model is no longer an '
                    'effective source for active model callers.'
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
        }
    if section == 'identity_periodic_model':
        return {
            'prompt_path': {
                'label': 'IDENTITY_MUTABLE_JUDGE_PROMPT_PATH',
                'value': str(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'prompt_loader': {
                'label': 'IDENTITY_MUTABLE_JUDGE_PROMPT_RUNTIME_SOURCE',
                'value': 'memory.mutable_identity_judge_v2.load_prompt_v2(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'system_prompt': {
                'label': 'identity_mutable_judge_prompt',
                'value': prompt_loader.read_prompt_text(str(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)),
                'is_editable': False,
                'source': 'app_prompt_file',
            },
            'legacy_prompt_path': {
                'label': 'IDENTITY_PERIODIC_AGENT_PROMPT_PATH_LEGACY',
                'value': str(config.IDENTITY_PERIODIC_AGENT_PROMPT_PATH),
                'is_editable': False,
                'source': 'legacy_pre_refactor',
            },
            'shared_transport': {
                'label': 'OPENROUTER_SHARED_TRANSPORT',
                'value': _shared_openrouter_transport_text(
                    'main_model.title_identity_periodic',
                    'main_model.referer_identity_periodic',
                ),
                'is_editable': False,
                'source': 'main_model_runtime_settings',
            },
            'benchmark_decision': {
                'label': 'IDENTITY_PERIODIC_BENCHMARK_DECISION',
                'value': 'benchmark/results/identity_periodic/2026-05-19-haiku-periodic-decision.md',
                'is_editable': False,
                'source': 'benchmark_artifact',
            },
            'doctrine': {
                'label': 'IDENTITY_MUTABLE_JUDGE_DOCTRINE',
                'value': (
                    'identity_periodic_model is the compatibility model slot for the active '
                    'mutable_identity_judge_v2 caller. The active prompt is identity_mutable_judge_v2; '
                    'identity_periodic_agent is legacy pre-refactor.'
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
        }
    if section == 'arbiter_model':
        return {
            'operator_warning': {
                'label': 'ARBITER_MODEL_TRANSITION_WARNING',
                'value': (
                    'Legacy compatibility slot: no active model caller now reads arbiter_model as its '
                    'source of truth. memory arbitration, identity extraction and mutable identity judge '
                    'all use dedicated runtime sections.'
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'active_replacements': {
                'label': 'ARBITER_MODEL_ACTIVE_REPLACEMENTS',
                'value': (
                    'memory_arbiter_model drives memory arbitration; identity_extractor_model drives '
                    'per-turn identity extraction; identity_periodic_model drives mutable_identity_judge_v2.'
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'legacy_scope': {
                'label': 'ARBITER_MODEL_LEGACY_SCOPE',
                'value': (
                    'Retained only for compatibility/backfill while older rows or clients may still '
                    'reference the section. It is not an effective source for current model payloads.'
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
        }
    if section == 'summary_model':
        return {
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
            'shared_transport': {
                'label': 'OPENROUTER_SHARED_TRANSPORT',
                'value': _shared_openrouter_transport_text('main_model.title_resumer', 'main_model.referer_resumer'),
                'is_editable': False,
                'source': 'main_model_runtime_settings',
            },
            'benchmark_decision': {
                'label': 'SUMMARY_BENCHMARK_DECISION',
                'value': 'benchmark/results/summary/2026-05-18-summary-human-final.md',
                'is_editable': False,
                'source': 'benchmark_artifact',
            },
        }
    if section == 'web_reformulation_model':
        return {
            'prompt_path': {
                'label': 'WEB_REFORMULATION_PROMPT_PATH',
                'value': str(config.WEB_REFORMULATION_PROMPT_PATH),
                'is_editable': False,
                'source': 'config_py',
            },
            'prompt_loader': {
                'label': 'WEB_REFORMULATION_PROMPT_RUNTIME_SOURCE',
                'value': 'core.prompt_loader.get_web_reformulation_prompt()',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'system_prompt': {
                'label': 'web_reformulation_system_prompt',
                'value': prompt_loader.get_web_reformulation_prompt(),
                'is_editable': False,
                'source': 'prompt_file',
            },
            'shared_transport': {
                'label': 'SHARED_OPENROUTER_TRANSPORT',
                'value': _shared_openrouter_transport_text(
                    'main_model.title_web_reformulation',
                    'main_model.referer_web_reformulation',
                ),
                'is_editable': False,
                'source': 'main_model_runtime_settings',
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
            'benchmark_decision': {
                'label': 'VALIDATION_AGENT_BENCHMARK_DECISION',
                'value': 'benchmark/results/validation_agent/2026-05-19-validation-agent-decision.md',
                'is_editable': False,
                'source': 'benchmark_artifact',
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
        return {}
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
