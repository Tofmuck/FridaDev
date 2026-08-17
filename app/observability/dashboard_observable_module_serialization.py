from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from observability.dashboard_observable_modules import ObservableModule


_STATE_LABELS_FR = {
    'success': 'Fonctionne',
    'degraded': 'Degrade',
    'error': 'Erreur',
    'skipped': 'Ignore',
    'not_applicable': 'Non concerne',
}


def _module_pairs_to_dict(pairs: Sequence[tuple[str, str]]) -> dict[str, str]:
    return {str(key): str(label) for key, label in pairs}


def _reason_dict(module: ObservableModule) -> dict[str, str]:
    return _module_pairs_to_dict(module.degradation_reasons)


def _module_to_public_dict(module: ObservableModule) -> dict[str, object]:
    return {
        'module_key': module.module_key,
        'label_fr': module.label_fr,
        'description_fr': module.description_fr,
        'calculation_version': module.calculation_version,
        'global_metrics': _module_pairs_to_dict(module.global_metrics),
        'conversation_summary': _module_pairs_to_dict(module.conversation_summary),
        'turn_summary': _module_pairs_to_dict(module.turn_summary),
        'human_detail': _module_pairs_to_dict(module.human_detail),
        'states': {
            state: _STATE_LABELS_FR.get(state, 'Etat inconnu')
            for state in module.states
        },
        'content_free_rules': list(module.content_free_rules),
        'sources': list(module.sources),
        'limits': list(module.limits),
        'degradation_reasons': _reason_dict(module),
        'gated_content': list(module.gated_content),
        'bucket_metrics': {
            'reducer_declared': module.bucket_metrics_reducer is not None,
            'finalizer_declared': module.bucket_metrics_finalizer is not None,
        },
        'turn_summary_renderer_declared': module.turn_summary_renderer is not None,
        'turn_degradation_reason_resolver_declared': module.turn_degradation_reason_resolver is not None,
        'future': bool(module.future),
    }
