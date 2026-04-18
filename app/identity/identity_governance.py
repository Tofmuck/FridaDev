from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import config
from memory import memory_identity_periodic_agent
from memory import memory_identity_periodic_scoring


GOVERNANCE_VERSION = 'v1'
RUNTIME_SECTION = 'identity_governance'
READ_ROUTE = '/api/admin/identity/governance'
UPDATE_ROUTE = '/api/admin/identity/governance'
SOURCE_OF_TRUTH = 'runtime_settings.identity_governance'
ACTIVE_PROMPT_CONTRACT = 'static + mutable narrative'
STAGING_STORAGE_KIND = 'identity_mutable_staging'
STAGING_SCOPE_KIND = 'conversation_scoped_latest'
LEGACY_DIAGNOSTIC_STORAGE = ['identities', 'identity_evidence', 'identity_conflicts']


@dataclass(frozen=True)
class GovernanceItemSpec:
    key: str
    label: str
    category: str
    value_type: str
    unit: str | None
    source_kind: str
    source_ref: str
    active_scope: str
    editable: bool
    editable_via: str | None
    validation: Mapping[str, Any] | None
    operator_note: str


_EDITABLE_ITEM_SPECS: tuple[GovernanceItemSpec, ...] = (
    GovernanceItemSpec(
        key='IDENTITY_MIN_CONFIDENCE',
        label='Minimum confidence',
        category='active_subpipeline_editable',
        value_type='float',
        unit='ratio',
        source_kind='runtime_settings',
        source_ref='identity_governance.IDENTITY_MIN_CONFIDENCE',
        active_scope='identity_dynamics',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 0.0, 'max': 1.0},
        operator_note='Seuil de promotion/acceptation du pipeline identity dynamics.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_DEFER_MIN_CONFIDENCE',
        label='Defer minimum confidence',
        category='active_subpipeline_editable',
        value_type='float',
        unit='ratio',
        source_kind='runtime_settings',
        source_ref='identity_governance.IDENTITY_DEFER_MIN_CONFIDENCE',
        active_scope='identity_dynamics',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 0.0, 'max': 1.0, 'lte_key': 'IDENTITY_MIN_CONFIDENCE'},
        operator_note='Seuil bas du statut deferred; doit rester <= au seuil accepted.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_MIN_RECURRENCE_FOR_DURABLE',
        label='Minimum recurrence for durable',
        category='active_subpipeline_editable',
        value_type='int',
        unit='events',
        source_kind='runtime_settings',
        source_ref='identity_governance.IDENTITY_MIN_RECURRENCE_FOR_DURABLE',
        active_scope='identity_dynamics',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max': 10, 'gte_key': 'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS'},
        operator_note='Nombre minimal d\'occurrences avant promotion durable.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_RECURRENCE_WINDOW_DAYS',
        label='Recurrence window',
        category='active_subpipeline_editable',
        value_type='int',
        unit='days',
        source_kind='runtime_settings',
        source_ref='identity_governance.IDENTITY_RECURRENCE_WINDOW_DAYS',
        active_scope='identity_dynamics',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max': 365},
        operator_note='Fenetre d\'observation des recurrences pour durable/deferred.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS',
        label='Promotion distinct conversations',
        category='active_subpipeline_editable',
        value_type='int',
        unit='conversations',
        source_kind='runtime_settings',
        source_ref='identity_governance.IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS',
        active_scope='identity_dynamics',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max': 10, 'lte_key': 'IDENTITY_MIN_RECURRENCE_FOR_DURABLE'},
        operator_note='Nombre minimal de conversations distinctes pour promotion durable.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
        label='Promotion minimum time gap',
        category='active_subpipeline_editable',
        value_type='int',
        unit='hours',
        source_kind='runtime_settings',
        source_ref='identity_governance.IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
        active_scope='identity_dynamics',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max': 168},
        operator_note='Distance minimale entre occurrences pour compter une recurrence.',
    ),
    GovernanceItemSpec(
        key='CONTEXT_HINTS_MAX_ITEMS',
        label='Context hints max items',
        category='active_runtime_editable',
        value_type='int',
        unit='items',
        source_kind='runtime_settings',
        source_ref='identity_governance.CONTEXT_HINTS_MAX_ITEMS',
        active_scope='active_prompt_runtime',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max': 10},
        operator_note='Nombre maximal d\'indices contextuels injectes dans le prompt actif.',
    ),
    GovernanceItemSpec(
        key='CONTEXT_HINTS_MAX_TOKENS',
        label='Context hints max tokens',
        category='active_runtime_editable',
        value_type='int',
        unit='tokens',
        source_kind='runtime_settings',
        source_ref='identity_governance.CONTEXT_HINTS_MAX_TOKENS',
        active_scope='active_prompt_runtime',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max_ref': 'config.MAX_TOKENS'},
        operator_note='Budget prompt des indices contextuels injectes activement.',
    ),
    GovernanceItemSpec(
        key='CONTEXT_HINTS_MAX_AGE_DAYS',
        label='Context hints max age',
        category='active_runtime_editable',
        value_type='int',
        unit='days',
        source_kind='runtime_settings',
        source_ref='identity_governance.CONTEXT_HINTS_MAX_AGE_DAYS',
        active_scope='active_prompt_runtime',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 1, 'max': 365},
        operator_note='Age maximal des indices contextuels retenus avant injection.',
    ),
    GovernanceItemSpec(
        key='CONTEXT_HINTS_MIN_CONFIDENCE',
        label='Context hints minimum confidence',
        category='active_runtime_editable',
        value_type='float',
        unit='ratio',
        source_kind='runtime_settings',
        source_ref='identity_governance.CONTEXT_HINTS_MIN_CONFIDENCE',
        active_scope='active_prompt_runtime',
        editable=True,
        editable_via=UPDATE_ROUTE,
        validation={'min': 0.0, 'max': 1.0},
        operator_note='Seuil minimal de confiance pour les indices contextuels injectes.',
    ),
)

_READONLY_ITEM_SPECS: tuple[GovernanceItemSpec, ...] = (
    GovernanceItemSpec(
        key='IDENTITY_MUTABLE_TARGET_CHARS',
        label='Mutable target chars',
        category='doctrine_locked_readonly',
        value_type='int',
        unit='chars',
        source_kind='config_py',
        source_ref='config.IDENTITY_MUTABLE_TARGET_CHARS',
        active_scope='identity_periodic_agent',
        editable=False,
        editable_via=None,
        validation={'target': 3000},
        operator_note='Cible utile du mutable canonique dans le regime periodique, visible seulement.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_MUTABLE_MAX_CHARS',
        label='Mutable max chars',
        category='doctrine_locked_readonly',
        value_type='int',
        unit='chars',
        source_kind='config_py',
        source_ref='config.IDENTITY_MUTABLE_MAX_CHARS',
        active_scope='identity_periodic_agent',
        editable=False,
        editable_via=None,
        validation={'max': 3300},
        operator_note='Plafond dur du mutable canonique dans le regime periodique, non reouvert a l edition.',
    ),
    GovernanceItemSpec(
        key='identity_extractor_max_tokens',
        label='Identity extractor max tokens',
        category='active_subpipeline_readonly',
        value_type='int',
        unit='tokens',
        source_kind='hardcoded',
        source_ref='memory.arbiter.identity_extractor.max_tokens',
        active_scope='identity_extractor',
        editable=False,
        editable_via=None,
        validation={'exact': 700},
        operator_note='Budget encore hardcode dans le sous-pipeline extracteur, visible seulement.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_DECAY_FACTOR',
        label='Identity decay factor',
        category='active_subpipeline_readonly',
        value_type='float',
        unit='ratio',
        source_kind='config_py',
        source_ref='config.IDENTITY_DECAY_FACTOR',
        active_scope='legacy_fragment_weights',
        editable=False,
        editable_via=None,
        validation={'min': 0.0, 'max': 1.0},
        operator_note='Agit encore sur la table legacy identities, mais reste read-only en Lot 5.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_TOP_N',
        label='Legacy top N',
        category='legacy_inactive_readonly',
        value_type='int',
        unit='items',
        source_kind='legacy_survivor',
        source_ref='config.IDENTITY_TOP_N',
        active_scope='inactive_legacy',
        editable=False,
        editable_via=None,
        validation=None,
        operator_note='Survivance legacy hors verite d\'injection active; non gouvernable.',
    ),
    GovernanceItemSpec(
        key='IDENTITY_MAX_TOKENS',
        label='Legacy identity max tokens',
        category='legacy_inactive_readonly',
        value_type='int',
        unit='tokens',
        source_kind='legacy_survivor',
        source_ref='config.IDENTITY_MAX_TOKENS',
        active_scope='inactive_legacy',
        editable=False,
        editable_via=None,
        validation=None,
        operator_note='Ancien budget legacy non branche sur le chemin actif static + mutable narrative.',
    ),
)

ITEM_SPECS: tuple[GovernanceItemSpec, ...] = _EDITABLE_ITEM_SPECS + _READONLY_ITEM_SPECS
EDITABLE_KEYS: tuple[str, ...] = tuple(item.key for item in _EDITABLE_ITEM_SPECS)

_HARDCODED_VALUES: dict[str, Any] = {
    'identity_extractor_max_tokens': 700,
}


def _config_value(key: str) -> Any:
    if key in _HARDCODED_VALUES:
        return _HARDCODED_VALUES[key]
    return getattr(config, key)


def _coerce_value(spec: GovernanceItemSpec, value: Any) -> Any:
    if spec.value_type == 'int':
        return int(value)
    if spec.value_type == 'float':
        return float(value)
    return value


def _runtime_section_view(
    *,
    runtime_settings_module: Any = None,
    fetcher: Any = None,
) -> Any:
    if runtime_settings_module is None:
        from admin import runtime_settings as runtime_settings_module
    return runtime_settings_module.get_runtime_section(RUNTIME_SECTION, fetcher=fetcher)


def editable_runtime_values(
    *,
    runtime_settings_module: Any = None,
    fetcher: Any = None,
) -> dict[str, Any]:
    view = _runtime_section_view(runtime_settings_module=runtime_settings_module, fetcher=fetcher)
    return editable_values_from_view(view)


def editable_values_from_view(view: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    spec_by_key = {item.key: item for item in _EDITABLE_ITEM_SPECS}
    for key in EDITABLE_KEYS:
        raw_payload = view.payload.get(key) or {}
        raw_value = raw_payload.get('value', _config_value(key))
        values[key] = _coerce_value(spec_by_key[key], raw_value)
    return values


def governed_value_for_runtime(
    key: str,
    *,
    config_module: Any = config,
    runtime_settings_module: Any = None,
) -> Any:
    if key not in EDITABLE_KEYS:
        return getattr(config_module, key)
    if config_module is not config:
        return getattr(config_module, key)
    try:
        return editable_runtime_values(runtime_settings_module=runtime_settings_module)[key]
    except Exception:
        return getattr(config_module, key)


def context_hints_max_items(*, runtime_settings_module: Any = None) -> int:
    return int(governed_value_for_runtime('CONTEXT_HINTS_MAX_ITEMS', runtime_settings_module=runtime_settings_module))


def context_hints_max_tokens(*, runtime_settings_module: Any = None) -> int:
    return int(governed_value_for_runtime('CONTEXT_HINTS_MAX_TOKENS', runtime_settings_module=runtime_settings_module))


def context_hints_max_age_days(*, runtime_settings_module: Any = None) -> int:
    return int(governed_value_for_runtime('CONTEXT_HINTS_MAX_AGE_DAYS', runtime_settings_module=runtime_settings_module))


def context_hints_min_confidence(*, runtime_settings_module: Any = None) -> float:
    return float(governed_value_for_runtime('CONTEXT_HINTS_MIN_CONFIDENCE', runtime_settings_module=runtime_settings_module))


def identity_decay_factor() -> float:
    return float(config.IDENTITY_DECAY_FACTOR)


def list_item_specs() -> tuple[GovernanceItemSpec, ...]:
    return ITEM_SPECS


def build_regime_section_payloads(
    *,
    runtime_settings_module: Any = None,
    fetcher: Any = None,
) -> list[dict[str, Any]]:
    view = _runtime_section_view(runtime_settings_module=runtime_settings_module, fetcher=fetcher)
    runtime_values = editable_values_from_view(view)
    return [
        {
            'key': 'active_canon_contract',
            'label': 'Canon actif et frontieres',
            'classification': 'active_readonly',
            'active_scope': 'active_prompt_runtime',
            'source_kind': 'runtime_contract',
            'source_ref': 'identity.build_identity_input + identity.build_identity_block',
            'editable': False,
            'operator_note': (
                'Le canon actif injecte reste static + mutable narrative. '
                'Le staging conversation-scoped reste hors injection active et hors edition gouvernance.'
            ),
            'details': {
                'active_prompt_contract': ACTIVE_PROMPT_CONTRACT,
                'active_canon_layers': ['static', 'mutable'],
                'editable_content_routes': [
                    '/api/admin/identity/static',
                    '/api/admin/identity/mutable',
                ],
                'staging_included_in_active_canon': False,
            },
        },
        {
            'key': 'staging_contract',
            'label': 'Staging conversation-scoped',
            'classification': 'active_readonly',
            'active_scope': 'identity_periodic_agent',
            'source_kind': 'periodic_agent_contract',
            'source_ref': 'memory_identity_periodic_agent.BUFFER_TARGET_PAIRS',
            'editable': False,
            'operator_note': (
                'Le staging actif reste un snapshot conversationnel recent, observe seulement. '
                'Il ne constitue ni un canon global ni un espace editable depuis cette surface.'
            ),
            'details': {
                'storage_kind': STAGING_STORAGE_KIND,
                'scope_kind': STAGING_SCOPE_KIND,
                'buffer_target_pairs': int(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
                'actively_injected': False,
                'editable_via_governance': False,
            },
        },
        {
            'key': 'scoring_contract',
            'label': 'Scoring et verdicts actifs',
            'classification': 'active_readonly',
            'active_scope': 'identity_periodic_scoring',
            'source_kind': 'python_contract',
            'source_ref': 'memory_identity_periodic_scoring',
            'editable': False,
            'operator_note': (
                'Le scoring local reste Python deterministe. Les seuils de force locale et les seuils de durabilite '
                'sont visibles ici sans etre reduits a de simples caps caracteres.'
            ),
            'details': {
                'engine': 'python_deterministic',
                'operation_kinds': ['add', 'tighten', 'merge', 'raise_conflict'],
                'local_strength_reject_below': float(memory_identity_periodic_scoring.REJECT_THRESHOLD),
                'local_strength_accept_from': float(memory_identity_periodic_scoring.ACCEPT_THRESHOLD),
                'durable_defer_from': float(runtime_values['IDENTITY_DEFER_MIN_CONFIDENCE']),
                'durable_accept_from': float(runtime_values['IDENTITY_MIN_CONFIDENCE']),
            },
        },
        {
            'key': 'promotion_and_suspension_contract',
            'label': 'Promotion et suspension automatiques',
            'classification': 'active_readonly',
            'active_scope': 'identity_periodic_apply',
            'source_kind': 'periodic_apply_contract',
            'source_ref': 'memory_identity_periodic_apply.apply_periodic_agent_contract',
            'editable': False,
            'operator_note': (
                'Les propositions acceptees peuvent promouvoir la mutable vers le statique. '
                'La suspension automatique bloque la canonisation quand la saturation ou un edit operateur recent du statique l imposent.'
            ),
            'details': {
                'promotion_from_layer': 'mutable',
                'promotion_to_layer': 'static',
                'promotion_requires_min_recurrence': int(runtime_values['IDENTITY_MIN_RECURRENCE_FOR_DURABLE']),
                'promotion_requires_distinct_conversations': int(
                    runtime_values['IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS']
                ),
                'promotion_requires_time_gap_hours': int(
                    runtime_values['IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS']
                ),
                'promotion_reason_code': 'promoted_to_static',
                'auto_suspension_flag': 'auto_canonization_suspended',
                'auto_suspension_reason_codes': ['double_saturation', 'static_recent_operator_edit_guard'],
            },
        },
        {
            'key': 'mutable_budget_contract',
            'label': 'Budget mutable doctrinal verrouille',
            'classification': 'doctrine_locked',
            'active_scope': 'identity_periodic_agent',
            'source_kind': 'config_py',
            'source_ref': 'config.IDENTITY_MUTABLE_TARGET_CHARS + config.IDENTITY_MUTABLE_MAX_CHARS',
            'editable': False,
            'operator_note': (
                'Les caps 3000/3300 bornent seulement la mutable canonique. '
                'Ils ne resumant ni le staging, ni le scoring, ni la promotion, ni la suspension.'
            ),
            'details': {
                'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
                'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
                'applies_only_to': 'mutable_canonical_only',
                'governs_entire_identity_regime': False,
            },
        },
        {
            'key': 'legacy_identity_contract',
            'label': 'Legacy identity inactif',
            'classification': 'legacy_inactive',
            'active_scope': 'inactive_legacy',
            'source_kind': 'legacy_diagnostic_contract',
            'source_ref': 'persist_identity_entries + identities + identity_evidence + identity_conflicts',
            'editable': False,
            'operator_note': (
                'Le legacy identity reste relisible pour diagnostic et historique seulement. '
                'Il ne pilote plus le canon actif, le staging ni l injection runtime.'
            ),
            'details': {
                'pipeline_status': 'legacy_diagnostic_only',
                'storage': list(LEGACY_DIAGNOSTIC_STORAGE),
                'actively_injected': False,
                'editable_via_governance': False,
            },
        },
    ]


def item_value(
    key: str,
    *,
    runtime_settings_module: Any = None,
    fetcher: Any = None,
) -> Any:
    if key in EDITABLE_KEYS:
        return editable_runtime_values(
            runtime_settings_module=runtime_settings_module,
            fetcher=fetcher,
        )[key]
    return _config_value(key)


def build_item_payloads(
    *,
    runtime_settings_module: Any = None,
    fetcher: Any = None,
) -> list[dict[str, Any]]:
    view = _runtime_section_view(runtime_settings_module=runtime_settings_module, fetcher=fetcher)
    runtime_values = editable_values_from_view(view)
    items: list[dict[str, Any]] = []
    for spec in ITEM_SPECS:
        current_value = runtime_values[spec.key] if spec.key in runtime_values else _config_value(spec.key)
        item = {
            'key': spec.key,
            'label': spec.label,
            'category': spec.category,
            'current_value': current_value,
            'value_type': spec.value_type,
            'unit': spec.unit,
            'source_kind': spec.source_kind,
            'source_ref': spec.source_ref,
            'active_scope': spec.active_scope,
            'editable': spec.editable,
            'editable_via': spec.editable_via,
            'validation': dict(spec.validation or {}),
            'operator_note': spec.operator_note,
        }
        if spec.key in runtime_values:
            item['source_state'] = view.source
            item['source_reason'] = view.source_reason
        items.append(item)
    return items


def summarize_items(items: list[Mapping[str, Any]]) -> dict[str, Any]:
    safe_items = [item for item in items if isinstance(item, Mapping)]
    return {
        'editable_count': sum(1 for item in safe_items if bool(item.get('editable'))),
        'readonly_count': sum(1 for item in safe_items if not bool(item.get('editable'))),
        'legacy_inactive_count': sum(1 for item in safe_items if str(item.get('category') or '') == 'legacy_inactive_readonly'),
        'doctrine_locked_count': sum(1 for item in safe_items if str(item.get('category') or '') == 'doctrine_locked_readonly'),
        'active_readonly_count': sum(
            1
            for item in safe_items
            if str(item.get('category') or '') in {'active_subpipeline_readonly', 'active_runtime_readonly'}
        ),
        'active_runtime_count': sum(1 for item in safe_items if str(item.get('category') or '').startswith('active_runtime')),
        'active_subpipeline_count': sum(1 for item in safe_items if str(item.get('category') or '').startswith('active_subpipeline')),
    }


def summarize_regime_sections(sections: list[Mapping[str, Any]]) -> dict[str, Any]:
    safe_sections = [section for section in sections if isinstance(section, Mapping)]
    return {
        'regime_section_count': len(safe_sections),
        'regime_active_readonly_count': sum(
            1 for section in safe_sections if str(section.get('classification') or '') == 'active_readonly'
        ),
        'regime_doctrine_locked_count': sum(
            1 for section in safe_sections if str(section.get('classification') or '') == 'doctrine_locked'
        ),
        'regime_legacy_inactive_count': sum(
            1 for section in safe_sections if str(section.get('classification') or '') == 'legacy_inactive'
        ),
    }
