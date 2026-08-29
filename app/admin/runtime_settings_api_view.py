from __future__ import annotations

from typing import Any, Callable, Mapping

import config
from admin.runtime_settings_spec import get_field_spec, get_section_spec
from core import prompt_loader
from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.inputs import recent_window_input as canonical_recent_window_input
from identity import identity_governance
from memory import mutable_identity_judge_common, mutable_identity_judge_v2


NormalizeStoredPayload = Callable[[str, Mapping[str, Any]], dict[str, dict[str, Any]]]

PROMPT_CONTENT_GATE_REASON_CODE = 'admin_prompt_content_gate_required'

_SECTION_ROUTES = {
    'main_model': 'main-model',
    'memory_arbiter_model': 'memory-arbiter-model',
    'identity_extractor_model': 'identity-extractor-model',
    'identity_periodic_model': 'identity-periodic-model',
    'summary_model': 'summary-model',
    'web_reformulation_model': 'web-reformulation-model',
    'stimmung_agent_model': 'stimmung-agent-model',
    'validation_agent_model': 'validation-agent-model',
}


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


def _line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines()) or 1


def _prompt_content_endpoint(section: str, key: str) -> str:
    section_route = _SECTION_ROUTES.get(section, section.replace('_', '-'))
    return f'/api/admin/settings/{section_route}/readonly-info/{key}/content'


def _prompt_metadata_entry(
    section: str,
    key: str,
    *,
    label: str,
    text: str,
    source: str,
    path: str,
    loader: str,
) -> dict[str, Any]:
    metadata = {
        'status': 'content_gate_required',
        'present': bool(text),
        'char_count': len(text),
        'line_count': _line_count(text),
        'source': source,
        'path': path,
        'loader': loader,
        'reason_code': PROMPT_CONTENT_GATE_REASON_CODE,
        'raw_content_included': False,
        'content_endpoint': _prompt_content_endpoint(section, key),
    }
    return {
        'label': label,
        'value': metadata,
        'is_editable': False,
        'source': source,
        'content_gate': {
            'required': True,
            'reason_code': PROMPT_CONTENT_GATE_REASON_CODE,
            'method': 'POST',
            'endpoint': metadata['content_endpoint'],
            'raw_content_included': False,
        },
    }


def _prompt_content_specs() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        ('main_model', 'system_prompt'): {
            'label': 'SYSTEM_PROMPT',
            'source': 'prompt_file',
            'path': str(config.MAIN_SYSTEM_PROMPT_PATH),
            'loader': 'core.prompt_loader.get_main_system_prompt()',
            'load': prompt_loader.get_main_system_prompt,
        },
        ('main_model', 'hermeneutical_prompt'): {
            'label': 'HERMENEUTICAL_PROMPT',
            'source': 'prompt_file',
            'path': str(config.MAIN_HERMENEUTICAL_PROMPT_PATH),
            'loader': 'core.prompt_loader.get_main_hermeneutical_prompt()',
            'load': prompt_loader.get_main_hermeneutical_prompt,
        },
        ('memory_arbiter_model', 'system_prompt'): {
            'label': 'arbiter_prompt',
            'source': 'app_prompt_file',
            'path': str(config.ARBITER_PROMPT_PATH),
            'loader': 'memory.arbiter._load_prompt(config.ARBITER_PROMPT_PATH, "arbiter")',
            'load': lambda: prompt_loader.read_prompt_text(str(config.ARBITER_PROMPT_PATH)),
        },
        ('identity_extractor_model', 'system_prompt'): {
            'label': 'dialogic_context_hint_extractor_prompt',
            'source': 'app_prompt_file',
            'path': str(config.IDENTITY_EXTRACTOR_PROMPT_PATH),
            'loader': 'memory.arbiter._load_prompt(config.IDENTITY_EXTRACTOR_PROMPT_PATH, "dialogic_context_hint_extractor")',
            'load': lambda: prompt_loader.read_prompt_text(str(config.IDENTITY_EXTRACTOR_PROMPT_PATH)),
        },
        ('identity_periodic_model', 'system_prompt'): {
            'label': 'identity_mutable_judge_prompt',
            'source': 'app_prompt_file',
            'path': str(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH),
            'loader': 'memory.mutable_identity_judge_v2.load_prompt_v2(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)',
            'load': lambda: prompt_loader.read_prompt_text(str(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)),
        },
        ('summary_model', 'system_prompt'): {
            'label': 'summary_system_prompt',
            'source': 'prompt_file',
            'path': str(config.SUMMARY_SYSTEM_PROMPT_PATH),
            'loader': 'core.prompt_loader.get_summary_system_prompt()',
            'load': prompt_loader.get_summary_system_prompt,
        },
        ('web_reformulation_model', 'system_prompt'): {
            'label': 'web_reformulation_system_prompt',
            'source': 'prompt_file',
            'path': str(config.WEB_REFORMULATION_PROMPT_PATH),
            'loader': 'core.prompt_loader.get_web_reformulation_prompt()',
            'load': prompt_loader.get_web_reformulation_prompt,
        },
        ('stimmung_agent_model', 'prompt_text'): {
            'label': 'stimmung_agent_prompt',
            'source': 'prompt_file',
            'path': 'prompts/stimmung_agent.txt',
            'loader': 'core.stimmung_agent._load_system_prompt()',
            'load': lambda: prompt_loader.read_prompt_text('prompts/stimmung_agent.txt'),
        },
        ('validation_agent_model', 'prompt_text'): {
            'label': 'validation_agent_prompt',
            'source': 'prompt_file',
            'path': 'prompts/validation_agent.txt',
            'loader': 'core.hermeneutic_node.validation.validation_agent._load_system_prompt()',
            'load': lambda: prompt_loader.read_prompt_text('prompts/validation_agent.txt'),
        },
    }


def _prompt_content_spec(section: str, key: str) -> dict[str, Any]:
    specs = _prompt_content_specs()
    try:
        return specs[(section, key)]
    except KeyError as exc:
        raise KeyError(f'unknown readonly content gate: {section}.{key}') from exc


def _prompt_readonly_entry(section: str, key: str) -> dict[str, Any]:
    spec = _prompt_content_spec(section, key)
    text = str(spec['load']() or '')
    return _prompt_metadata_entry(
        section,
        key,
        label=str(spec['label']),
        text=text,
        source=str(spec['source']),
        path=str(spec['path']),
        loader=str(spec['loader']),
    )


def get_section_readonly_info_content(section: str, key: str) -> dict[str, Any]:
    get_section_spec(section)
    spec = _prompt_content_spec(section, key)
    text = str(spec['load']() or '')
    metadata = _prompt_metadata_entry(
        section,
        key,
        label=str(spec['label']),
        text=text,
        source=str(spec['source']),
        path=str(spec['path']),
        loader=str(spec['loader']),
    )['value']
    return {
        'section': section,
        'key': key,
        'content': text,
        'metadata': metadata,
        'content_gate': {
            'acknowledged': True,
            'reason_code': PROMPT_CONTENT_GATE_REASON_CODE,
            'raw_content_included': True,
        },
    }


def get_section_readonly_info(section: str) -> dict[str, dict[str, Any]]:
    get_section_spec(section)
    if section == 'main_model':
        return {
            'system_prompt': _prompt_readonly_entry('main_model', 'system_prompt'),
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
            'hermeneutical_prompt': _prompt_readonly_entry('main_model', 'hermeneutical_prompt'),
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
            'system_prompt': _prompt_readonly_entry('memory_arbiter_model', 'system_prompt'),
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
                'label': 'DIALOGIC_CONTEXT_HINT_PROMPT_RUNTIME_SOURCE',
                'value': 'memory.arbiter._load_prompt(config.IDENTITY_EXTRACTOR_PROMPT_PATH, "dialogic_context_hint_extractor")',
                'is_editable': False,
                'source': 'backend_loader',
            },
            'system_prompt': _prompt_readonly_entry('identity_extractor_model', 'system_prompt'),
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
                'label': 'DIALOGIC_CONTEXT_HINT_RUNTIME_ROLE',
                'value': (
                    'identity_extractor_model is a compatibility slot for extract_dialogic_context_hints(). '
                    'Its outputs are temporary dialogue context only and never write Identity; '
                    'mutable_identity_judge_v2 remains the sole mutable canon writer.'
                ),
                'is_editable': False,
                'source': 'runtime_contract',
            },
        }
    if section == 'identity_periodic_model':
        return {
            'active_module': {
                'label': 'MUTABLE_IDENTITY_JUDGE_ACTIVE_MODULE',
                'value': 'mutable_identity_judge_v2_add_only',
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'runtime_slot': {
                'label': 'MUTABLE_IDENTITY_JUDGE_RUNTIME_SLOT',
                'value': mutable_identity_judge_common.MODEL_SLOT,
                'is_editable': False,
                'source': 'runtime_settings_slot',
            },
            'model_field': {
                'label': 'MUTABLE_IDENTITY_JUDGE_MODEL_FIELD',
                'value': f'{mutable_identity_judge_common.MODEL_SLOT}.model',
                'is_editable': False,
                'source': 'runtime_settings_slot',
            },
            'caller': {
                'label': 'MUTABLE_IDENTITY_JUDGE_CALLER',
                'value': mutable_identity_judge_common.CALLER,
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'contract': {
                'label': 'MUTABLE_IDENTITY_JUDGE_CONTRACT',
                'value': mutable_identity_judge_v2.SCHEMA_VERSION,
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'prompt_kind': {
                'label': 'MUTABLE_IDENTITY_JUDGE_PROMPT_KIND',
                'value': mutable_identity_judge_v2.PROMPT_KIND,
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'structured_output': {
                'label': 'MUTABLE_IDENTITY_JUDGE_STRUCTURED_OUTPUT',
                'value': 'response_format=json_schema strict=true; provider.require_parameters=true',
                'is_editable': False,
                'source': 'openrouter_payload_contract',
            },
            'runtime_role': {
                'label': 'MUTABLE_IDENTITY_JUDGE_RUNTIME_ROLE',
                'value': '5 paires completes -> add/no_change ontologique -> identity_mutables',
                'is_editable': False,
                'source': 'runtime_contract',
            },
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
            'system_prompt': _prompt_readonly_entry('identity_periodic_model', 'system_prompt'),
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
                'label': 'MUTABLE_IDENTITY_JUDGE_GPT52_MODEL_DECISION',
                'value': 'app/docs/todo-done/validations/mutable-identity-judge-final-validation-2026-05-25.md',
                'is_editable': False,
                'source': 'validation_artifact',
            },
            'legacy_benchmark_decision': {
                'label': 'IDENTITY_PERIODIC_HAIKU_BENCHMARK_DECISION_LEGACY',
                'value': 'benchmark/results/identity_periodic/2026-05-19-haiku-periodic-decision.md',
                'is_editable': False,
                'source': 'legacy_pre_gpt52_cutover',
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
                    'memory_arbiter_model drives memory arbitration; identity_extractor_model configures '
                    'the per-turn dialogic context extractor; identity_periodic_model drives '
                    'mutable_identity_judge_v2.'
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
            'system_prompt': _prompt_readonly_entry('summary_model', 'system_prompt'),
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
            'system_prompt': _prompt_readonly_entry('web_reformulation_model', 'system_prompt'),
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
            'prompt_text': _prompt_readonly_entry('stimmung_agent_model', 'prompt_text'),
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
            'prompt_text': _prompt_readonly_entry('validation_agent_model', 'prompt_text'),
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
                'value': 'benchmark/results/validation_agent/2026-08-29-lot4c1-validation-primary-models.jsonl',
                'is_editable': False,
                'source': 'benchmark_artifact',
            },
            'request_policy': {
                'label': 'VALIDATION_AGENT_REQUEST_POLICY',
                'value': 'validation_request_gemini_3_7_flash_medium_v1',
                'is_editable': False,
                'source': 'runtime_contract',
            },
            'fallback_max_tokens': {
                'label': 'VALIDATION_AGENT_FALLBACK_MAX_TOKENS',
                'value': 140,
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
