from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


MODULE_CONTRACT_VERSION = 'dashboard_observable_modules_v1'
ANALYTICS_CALCULATION_VERSION = 'dashboard_analytics_v1'
FUTURE_MODULE_CALCULATION_VERSION = 'dashboard_observable_module_contract_v1'

_COMMON_STATES = (
    'success',
    'degraded',
    'error',
    'skipped',
    'not_applicable',
)

_STATE_LABELS_FR = {
    'success': 'Fonctionne',
    'degraded': 'Degrade',
    'error': 'Erreur',
    'skipped': 'Ignore',
    'not_applicable': 'Non concerne',
}

BucketMetricsReducer = Callable[[dict[str, Any], Mapping[str, Any]], None]
BucketMetricsFinalizer = Callable[[dict[str, Any]], None]
TurnSummaryRenderer = Callable[[Mapping[str, Any]], str]
TurnDegradationReasonResolver = Callable[[Mapping[str, Any]], str | None]


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _status_label(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    labels = {
        'ok': 'reussi',
        'success': 'reussi',
        'saved': 'sauvegarde',
        'complete': 'complet',
        'degraded': 'degrade',
        'partial': 'partiel',
        'legacy_incomplete': 'historique incomplet',
        'error': 'en erreur',
        'failed': 'en erreur',
        'skipped': 'ignore',
        'not_applicable': 'non utilise',
        'missing': 'non observe',
        'unknown': 'a verifier',
    }
    return labels.get(normalized, 'a verifier')


def _classification_label(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    labels = {
        'complete': 'complet',
        'degraded': 'degrade',
        'partial': 'partiel',
        'legacy_incomplete': 'issu d un historique incomplet',
    }
    return labels.get(normalized, 'a verifier')


def _inc(mapping: dict[str, int], key: Any, amount: int = 1) -> None:
    normalized = str(key or 'unknown').strip() or 'unknown'
    mapping[normalized] = int(mapping.get(normalized, 0)) + int(amount)


def _add_metric_count(metrics: dict[str, Any], key: str, amount: int = 1) -> None:
    metrics[key] = _to_int(metrics.get(key)) + int(amount)


def _add_metric_label(metrics: dict[str, Any], group_key: str, label: Any, amount: int = 1) -> None:
    group = metrics.setdefault(group_key, {})
    if isinstance(group, dict):
        _inc(group, label, amount)


def _percentile(values: Sequence[int], percentile: float) -> int | None:
    safe = sorted(int(value) for value in values if value is not None)
    if not safe:
        return None
    if len(safe) == 1:
        return safe[0]
    position = (len(safe) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(safe) - 1)
    weight = position - lower
    return int(round(safe[lower] * (1 - weight) + safe[upper] * weight))


def _reduce_pipeline_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    _add_metric_label(metrics, 'classification_counts', fact.get('classification'))
    _add_metric_count(metrics, 'score_total', _to_int(fact.get('score')))
    _add_metric_count(metrics, 'score_count')
    flags = _mapping(fact.get('flags'))
    if bool(flags.get('events_truncated')):
        _add_metric_count(metrics, 'events_truncated_turns')


def _finalize_pipeline_metrics(metrics: dict[str, Any]) -> None:
    score_count = _to_int(metrics.get('score_count'))
    if score_count:
        metrics['score_avg'] = round(_to_float(metrics.get('score_total')) / float(score_count), 3)


def _reduce_persistence_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    persistence = _mapping(fact.get('persistence'))
    _add_metric_label(metrics, 'status_counts', persistence.get('status'))
    _add_metric_count(metrics, 'assistant_final_present_count', 1 if persistence.get('assistant_final_present') else 0)
    _add_metric_count(metrics, 'assistant_final_saved_count', 1 if persistence.get('assistant_final_saved') else 0)
    _add_metric_count(metrics, 'assistant_interrupted_count', 1 if persistence.get('assistant_interrupted') else 0)


def _reduce_memory_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    rag = _mapping(fact.get('rag'))
    _add_metric_label(metrics, 'source_kind_counts', rag.get('source_kind'))
    _add_metric_count(metrics, 'retrieved_total', _to_int(rag.get('retrieved')))
    _add_metric_count(metrics, 'basket_total', _to_int(rag.get('basket')))
    _add_metric_count(metrics, 'kept_total', _to_int(rag.get('kept')))
    _add_metric_count(metrics, 'rejected_total', _to_int(rag.get('rejected')))
    _add_metric_count(metrics, 'injected_total', _to_int(rag.get('injected')))
    _add_metric_count(metrics, 'context_hints_total', _to_int(rag.get('context_hints')))
    _add_metric_count(metrics, 'snapshot_present_turns', 1 if rag.get('source_kind') == 'memory_chain_snapshot' else 0)
    _add_metric_count(metrics, 'legacy_fallback_turns', 1 if rag.get('legacy_reason_code') else 0)


def _reduce_web_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    web = _mapping(fact.get('web'))
    _add_metric_label(metrics, 'status_counts', web.get('status'))
    _add_metric_count(metrics, 'requested_turns', 1 if web.get('requested') else 0)
    _add_metric_count(metrics, 'success_turns', 1 if web.get('success') else 0)
    _add_metric_count(metrics, 'skipped_turns', 1 if web.get('skipped') else 0)
    _add_metric_count(metrics, 'error_turns', 1 if web.get('error') else 0)
    _add_metric_count(metrics, 'injected_turns', 1 if web.get('injected') else 0)
    _add_metric_count(metrics, 'results_total', _to_int(web.get('results_count')))
    _add_metric_count(metrics, 'injected_chars_total', _to_int(web.get('injected_chars')))


def _reduce_documents_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    documents = _mapping(fact.get('documents'))
    active_count = _to_int(documents.get('active_count'))
    injected_count = _to_int(documents.get('injected_count'))
    not_injected_count = _to_int(documents.get('not_injected_count'))
    _add_metric_label(metrics, 'status_counts', documents.get('status'))
    _add_metric_count(metrics, 'active_turns', 1 if active_count > 0 else 0)
    _add_metric_count(metrics, 'active_documents_total', active_count)
    _add_metric_count(metrics, 'injected_documents_total', injected_count)
    _add_metric_count(metrics, 'not_injected_documents_total', not_injected_count)
    _add_metric_count(metrics, 'too_large_documents_total', _to_int(documents.get('too_large_count')))
    _add_metric_count(metrics, 'empty_documents_total', _to_int(documents.get('empty_count')))
    reason_counts = _mapping(documents.get('reason_code_counts'))
    for reason, count in reason_counts.items():
        _add_metric_label(metrics, 'reason_code_counts', reason, _to_int(count))


def _reduce_provider_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    providers = _mapping(fact.get('providers'))
    main = _mapping(providers.get('main'))
    secondary = _mapping(providers.get('secondary'))
    _add_metric_count(metrics, 'main_call_present_count', 1 if bool(main.get('present')) else 0)
    _add_metric_label(metrics, 'main_status_counts', main.get('status'))
    _add_metric_count(metrics, 'main_response_chars_total', _to_int(main.get('response_chars')))
    duration = main.get('duration_ms')
    if duration is not None:
        values = metrics.setdefault('_main_duration_ms_values', [])
        if isinstance(values, list):
            values.append(_to_int(duration))
        _add_metric_count(metrics, 'main_duration_ms_total', _to_int(duration))
        _add_metric_count(metrics, 'main_duration_ms_count')
    secondary_call_count = 0
    for item in secondary.values():
        summary = _mapping(item)
        secondary_call_count += _to_int(summary.get('llm_call_events_count'))
        _add_metric_label(metrics, 'secondary_status_counts', summary.get('status'))
    _add_metric_count(metrics, 'secondary_llm_call_count', secondary_call_count)


def _finalize_provider_metrics(metrics: dict[str, Any]) -> None:
    duration_values = metrics.pop('_main_duration_ms_values', None)
    if isinstance(duration_values, list):
        metrics['main_duration_ms_p50'] = _percentile(duration_values, 0.50)
        metrics['main_duration_ms_p95'] = _percentile(duration_values, 0.95)


def _reduce_identity_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    identity = _mapping(fact.get('identity'))
    _add_metric_label(metrics, 'status_counts', identity.get('status'))
    _add_metric_count(metrics, 'block_present_turns', 1 if identity.get('block_present') else 0)
    _add_metric_count(metrics, 'chars_total', _to_int(identity.get('chars')))


def _reduce_hermeneutic_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    hermeneutic = _mapping(fact.get('hermeneutic'))
    _add_metric_label(metrics, 'status_counts', hermeneutic.get('status'))
    _add_metric_count(metrics, 'block_present_turns', 1 if hermeneutic.get('block_present') else 0)
    _add_metric_count(metrics, 'fallback_turns', 1 if hermeneutic.get('fallback') else 0)


def _reduce_node_state_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    node_state = _mapping(fact.get('node_state'))
    _add_metric_count(metrics, 'read_present_count', 1 if node_state.get('read_present') else 0)
    _add_metric_count(metrics, 'read_valid_count', 1 if node_state.get('read_valid') else 0)
    _add_metric_count(metrics, 'write_attempted_count', 1 if node_state.get('write_attempted') else 0)
    _add_metric_count(metrics, 'write_succeeded_count', 1 if node_state.get('write_succeeded') else 0)
    _add_metric_count(metrics, 'write_changed_count', 1 if node_state.get('write_changed') else 0)
    _add_metric_count(metrics, 'fail_open_count', 1 if node_state.get('fail_open') else 0)


def _reduce_error_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    errors = _mapping(fact.get('errors'))
    _add_metric_count(metrics, 'error_count', _to_int(errors.get('error_count')))
    _add_metric_count(metrics, 'skipped_count', _to_int(errors.get('skipped_count')))
    _add_metric_count(metrics, 'fallback_count', _to_int(errors.get('fallback_count')))
    reason_counts = _mapping(errors.get('reason_code_counts'))
    for reason, count in reason_counts.items():
        _add_metric_label(metrics, 'reason_code_counts', reason, _to_int(count))


def _summarize_pipeline_turn(fact: Mapping[str, Any]) -> str:
    return (
        f"Le tour est {_classification_label(fact.get('classification'))}, "
        f"avec un score de {_to_int(fact.get('score'))}."
    )


def _summarize_persistence_turn(fact: Mapping[str, Any]) -> str:
    persistence = _mapping(fact.get('persistence'))
    if persistence.get('assistant_final_saved'):
        return 'La reponse finale assistant est sauvegardee.'
    return 'La sauvegarde finale assistant n est pas confirmee.'


def _summarize_memory_turn(fact: Mapping[str, Any]) -> str:
    rag = _mapping(fact.get('rag'))
    return (
        'La memoire a trouve '
        f"{_to_int(rag.get('retrieved'))} elements, en a garde {_to_int(rag.get('kept'))}, "
        f"et en a injecte {_to_int(rag.get('injected'))}."
    )


def _summarize_web_turn(fact: Mapping[str, Any]) -> str:
    web = _mapping(fact.get('web'))
    if web.get('requested'):
        return f"La recherche web a ete demandee et son resultat est {_status_label(web.get('status'))}."
    return 'La recherche web n a pas ete demandee pour ce tour.'


def _summarize_documents_turn(fact: Mapping[str, Any]) -> str:
    documents = _mapping(fact.get('documents'))
    active_count = _to_int(documents.get('active_count'))
    injected_count = _to_int(documents.get('injected_count'))
    not_injected_count = _to_int(documents.get('not_injected_count'))
    too_large_count = _to_int(documents.get('too_large_count'))
    if active_count <= 0:
        return 'Aucun document actif de conversation n est observe sur ce tour.'
    if injected_count and not_injected_count == 0:
        return f'{injected_count} document(s) actif(s) ont ete envoyes entiers au modele.'
    if too_large_count:
        return (
            f'{active_count} document(s) actif(s) etaient presents; '
            f'{too_large_count} etaient trop gros pour ce tour.'
        )
    if not_injected_count:
        return (
            f'{active_count} document(s) actif(s) etaient presents; '
            f'{not_injected_count} n ont pas ete envoyes dans ce tour.'
        )
    return f'{active_count} document(s) actif(s) etaient visibles sur ce tour.'


def _summarize_providers_turn(fact: Mapping[str, Any]) -> str:
    main = _mapping(_mapping(fact.get('providers')).get('main'))
    if main.get('present'):
        return f"Le modele principal a ete consulte et son appel est {_status_label(main.get('status'))}."
    return 'L appel au modele principal n est pas observe.'


def _summarize_identity_turn(fact: Mapping[str, Any]) -> str:
    identity = _mapping(fact.get('identity'))
    if identity.get('block_present'):
        return 'Le modele principal a recu un bloc identite.'
    return 'Aucun bloc identite n est observe dans les donnees compactes.'


def _summarize_hermeneutic_turn(fact: Mapping[str, Any]) -> str:
    hermeneutic = _mapping(fact.get('hermeneutic'))
    if hermeneutic.get('block_present'):
        return 'Le jugement hermeneutique est present dans les donnees compactes.'
    return 'Le jugement hermeneutique n est pas observe dans les donnees compactes.'


def _summarize_node_state_turn(fact: Mapping[str, Any]) -> str:
    node_state = _mapping(fact.get('node_state'))
    if node_state.get('read_present') or node_state.get('write_attempted'):
        return 'L etat du noeud a ete relu ou mis a jour pendant le tour.'
    return 'Aucune lecture ou ecriture du node_state n est observee.'


def _summarize_errors_turn(fact: Mapping[str, Any]) -> str:
    errors = _mapping(fact.get('errors'))
    problems = _to_int(errors.get('error_count')) + _to_int(errors.get('fallback_count'))
    if problems:
        return f"{problems} probleme(s) compact(s) sont visibles sur ce tour."
    return 'Aucun probleme compact n est visible sur ce tour.'


def _resolve_errors_reason(fact: Mapping[str, Any]) -> str | None:
    reason_counts = _mapping(_mapping(fact.get('errors')).get('reason_code_counts'))
    return next(iter(reason_counts.keys()), None)


def _resolve_documents_reason(fact: Mapping[str, Any]) -> str | None:
    reason_counts = _mapping(_mapping(fact.get('documents')).get('reason_code_counts'))
    for reason in ('document_too_large_for_turn', 'document_empty_text'):
        if _to_int(reason_counts.get(reason)) > 0:
            return reason
    return next(iter(reason_counts.keys()), None)


@dataclass(frozen=True)
class ObservableModule:
    module_key: str
    label_fr: str
    description_fr: str
    calculation_version: str
    global_metrics: tuple[tuple[str, str], ...]
    conversation_summary: tuple[tuple[str, str], ...]
    turn_summary: tuple[tuple[str, str], ...]
    human_detail: tuple[tuple[str, str], ...]
    states: tuple[str, ...]
    content_free_rules: tuple[str, ...]
    sources: tuple[str, ...]
    limits: tuple[str, ...]
    degradation_reasons: tuple[tuple[str, str], ...] = ()
    gated_content: tuple[str, ...] = ()
    future: bool = False
    bucket_metrics_reducer: BucketMetricsReducer | None = None
    bucket_metrics_finalizer: BucketMetricsFinalizer | None = None
    turn_summary_renderer: TurnSummaryRenderer | None = None
    turn_degradation_reason_resolver: TurnDegradationReasonResolver | None = None


def _fields(*items: tuple[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(items)


def _rules(*items: str) -> tuple[str, ...]:
    return tuple(items)


def _module(
    *,
    module_key: str,
    label_fr: str,
    description_fr: str,
    global_metrics: tuple[tuple[str, str], ...],
    conversation_summary: tuple[tuple[str, str], ...],
    turn_summary: tuple[tuple[str, str], ...],
    human_detail: tuple[tuple[str, str], ...],
    sources: tuple[str, ...],
    limits: tuple[str, ...],
    degradation_reasons: tuple[tuple[str, str], ...],
    gated_content: tuple[str, ...] = (),
    future: bool = False,
    bucket_metrics_reducer: BucketMetricsReducer | None = None,
    bucket_metrics_finalizer: BucketMetricsFinalizer | None = None,
    turn_summary_renderer: TurnSummaryRenderer | None = None,
    turn_degradation_reason_resolver: TurnDegradationReasonResolver | None = None,
) -> ObservableModule:
    return ObservableModule(
        module_key=module_key,
        label_fr=label_fr,
        description_fr=description_fr,
        calculation_version=(
            FUTURE_MODULE_CALCULATION_VERSION if future else ANALYTICS_CALCULATION_VERSION
        ),
        global_metrics=global_metrics,
        conversation_summary=conversation_summary,
        turn_summary=turn_summary,
        human_detail=human_detail,
        states=_COMMON_STATES,
        content_free_rules=_rules(
            'Aucun contenu brut par defaut.',
            'Les libelles exposent des statuts, counts, durees, codes et references.',
            'Les contenus complets restent reserves au gate explicite.',
        ),
        sources=sources,
        limits=limits,
        degradation_reasons=degradation_reasons,
        gated_content=gated_content,
        future=future,
        bucket_metrics_reducer=bucket_metrics_reducer,
        bucket_metrics_finalizer=bucket_metrics_finalizer,
        turn_summary_renderer=turn_summary_renderer,
        turn_degradation_reason_resolver=turn_degradation_reason_resolver,
    )


INITIAL_OBSERVABLE_MODULES: tuple[ObservableModule, ...] = (
    _module(
        module_key='pipeline',
        label_fr='Parcours du tour',
        description_fr='Suit si le tour est complet, degrade, partiel ou ancien.',
        global_metrics=_fields(
            ('classification_counts', 'Repartition des tours'),
            ('score_avg', 'Score moyen de completude'),
            ('events_truncated_turns', 'Tours avec trace tronquee'),
        ),
        conversation_summary=_fields(
            ('turns_count', 'Tours observes'),
            ('last_classification', 'Dernier etat visible'),
            ('last_problem_reason_code', 'Dernier probleme compact'),
        ),
        turn_summary=_fields(
            ('classification', 'Etat du tour'),
            ('score', 'Completude du tour'),
            ('source_event_count', 'Events sources observes'),
        ),
        human_detail=_fields(
            ('timeline_health', 'Explique si le tour contient les etapes attendues.'),
            ('source_limits', 'Signale les traces anciennes ou incompletes.'),
        ),
        sources=('dashboard_turn_facts', 'turn_pipeline_read_model', 'chat_log_events'),
        limits=('Ne reconstruit pas le sens du contenu modele sans artefact gate.',),
        degradation_reasons=(
            ('legacy_incomplete', 'Le tour vient d une trace ancienne ou incomplete.'),
            ('events_truncated', 'La trace du tour a ete tronquee avant inspection complete.'),
        ),
        bucket_metrics_reducer=_reduce_pipeline_metrics,
        bucket_metrics_finalizer=_finalize_pipeline_metrics,
        turn_summary_renderer=_summarize_pipeline_turn,
    ),
    _module(
        module_key='persistence',
        label_fr='Reponse sauvegardee',
        description_fr='Verifie que la reponse finale assistant a ete persistee.',
        global_metrics=_fields(
            ('assistant_final_present_count', 'Reponses finales observees'),
            ('assistant_final_saved_count', 'Reponses finales sauvegardees'),
            ('assistant_interrupted_count', 'Reponses interrompues'),
        ),
        conversation_summary=_fields(
            ('persistence_counts', 'Etats de sauvegarde'),
            ('last_turn_id', 'Dernier tour connu'),
        ),
        turn_summary=_fields(
            ('assistant_final_present', 'Reponse finale presente'),
            ('assistant_final_saved', 'Reponse finale sauvegardee'),
            ('assistant_interrupted', 'Reponse interrompue'),
        ),
        human_detail=_fields(
            ('save_status', 'Explique si la reponse finale est bien conservee.'),
        ),
        sources=('persist_response events', 'dashboard_turn_facts.persistence'),
        limits=('Ne contient pas le texte de la reponse sauvegardee.',),
        degradation_reasons=(
            ('assistant_final_missing', 'La reponse finale n est pas confirmee dans la persistence.'),
            ('assistant_interrupted', 'La reponse semble interrompue avant sauvegarde finale.'),
        ),
        gated_content=('Reponse assistant complete',),
        bucket_metrics_reducer=_reduce_persistence_metrics,
        turn_summary_renderer=_summarize_persistence_turn,
    ),
    _module(
        module_key='memory',
        label_fr='Memoire utilisee',
        description_fr='Resume la chaine memoire: trouve, garde, rejete, injecte.',
        global_metrics=_fields(
            ('retrieved_total', 'Souvenirs trouves'),
            ('basket_total', 'Souvenirs candidats'),
            ('kept_total', 'Souvenirs gardes'),
            ('rejected_total', 'Souvenirs rejetes'),
            ('injected_total', 'Souvenirs injectes'),
        ),
        conversation_summary=_fields(
            ('memory_used_turns', 'Tours avec memoire'),
            ('modules_involved.memory', 'Memoire impliquee'),
        ),
        turn_summary=_fields(
            ('retrieved', 'Souvenirs trouves'),
            ('kept', 'Souvenirs gardes'),
            ('injected', 'Souvenirs injectes'),
            ('source_kind', 'Source du signal memoire'),
        ),
        human_detail=_fields(
            ('rag_funnel', 'Explique le passage trouve vers garde puis injecte.'),
            ('legacy_status', 'Signale si la trace memoire est ancienne ou partielle.'),
        ),
        sources=('memory_chain_snapshot', 'dashboard_turn_facts.rag', 'prompt_prepared fallback'),
        limits=('Ne contient pas le texte exact des souvenirs ni le bloc memoire injecte.',),
        degradation_reasons=(
            ('memory_chain_snapshot_missing', 'La chaine memoire detaillee n est pas disponible pour ce tour.'),
            ('legacy_memory_fallback', 'La memoire est lue depuis un ancien signal moins precis.'),
        ),
        gated_content=('Souvenirs exacts', 'Bloc memoire injecte', 'Trace memoire complete'),
        bucket_metrics_reducer=_reduce_memory_metrics,
        turn_summary_renderer=_summarize_memory_turn,
    ),
    _module(
        module_key='web',
        label_fr='Recherche web',
        description_fr='Indique si le web a ete demande, reussi, ignore ou injecte.',
        global_metrics=_fields(
            ('requested_turns', 'Recherches demandees'),
            ('success_turns', 'Recherches reussies'),
            ('skipped_turns', 'Recherches ignorees'),
            ('error_turns', 'Recherches en erreur'),
            ('injected_turns', 'Resultats injectes'),
        ),
        conversation_summary=_fields(
            ('web_requested_turns', 'Tours avec demande web'),
            ('web_success_turns', 'Tours avec web reussi'),
            ('web_injected_turns', 'Tours avec web injecte'),
        ),
        turn_summary=_fields(
            ('requested', 'Recherche demandee'),
            ('success', 'Recherche reussie'),
            ('injected', 'Information web injectee'),
            ('results_count', 'Resultats comptes'),
        ),
        human_detail=_fields(
            ('web_path', 'Explique pourquoi le web a servi ou non.'),
        ),
        sources=('web_search events', 'dashboard_turn_facts.web'),
        limits=('Ne contient pas la requete ni les resultats bruts.',),
        degradation_reasons=(
            ('web_error', 'La recherche web a rencontre une erreur.'),
            ('web_skipped', 'La recherche web a ete ignoree pour ce tour.'),
            ('web_not_injected', 'La recherche web n a pas produit de contenu injecte.'),
        ),
        gated_content=('Requete web exacte', 'Resultats web complets', 'Contexte web injecte'),
        bucket_metrics_reducer=_reduce_web_metrics,
        turn_summary_renderer=_summarize_web_turn,
    ),
    _module(
        module_key='documents',
        label_fr='Documents actifs',
        description_fr='Indique les fichiers temporaires fournis par l utilisateur et injectes ou exclus du tour.',
        global_metrics=_fields(
            ('active_turns', 'Tours avec document actif'),
            ('active_documents_total', 'Documents actifs observes'),
            ('injected_documents_total', 'Documents envoyes entiers'),
            ('not_injected_documents_total', 'Documents non envoyes'),
            ('too_large_documents_total', 'Documents trop gros pour le tour'),
        ),
        conversation_summary=_fields(
            ('documents_active_turns', 'Tours avec documents actifs'),
            ('modules_involved.documents', 'Documents actifs impliques'),
        ),
        turn_summary=_fields(
            ('active_count', 'Documents actifs'),
            ('injected_count', 'Documents envoyes entiers'),
            ('not_injected_count', 'Documents non envoyes'),
            ('reason_code_counts', 'Raisons compactes'),
        ),
        human_detail=_fields(
            ('active_document_flow', 'Explique quels documents actifs ont ete envoyes ou exclus sans afficher leur texte.'),
        ),
        sources=('active_documents events', 'dashboard_turn_facts.documents', 'active_conversation_documents'),
        limits=(
            'Concerne seulement les documents actifs temporaires fournis par l utilisateur.',
            'Ne couvre pas la future Biblio native ni les passages documentaires Catalogue.',
            'Ne contient jamais le texte complet du fichier.',
        ),
        degradation_reasons=(
            ('document_too_large_for_turn', 'Un document actif etait trop gros pour etre envoye entier dans ce tour.'),
            ('document_empty_text', 'Un document actif ne contenait pas de texte injectable.'),
            ('document_parse_error', 'Un document n a pas pu etre lu lors de l activation.'),
            ('manual_remove', 'Un document actif a ete retire manuellement.'),
        ),
        gated_content=(),
        bucket_metrics_reducer=_reduce_documents_metrics,
        turn_summary_renderer=_summarize_documents_turn,
        turn_degradation_reason_resolver=_resolve_documents_reason,
    ),
    _module(
        module_key='providers',
        label_fr='Modeles consultes',
        description_fr='Separe le modele principal des appels secondaires.',
        global_metrics=_fields(
            ('main_call_present_count', 'Appels modele principal'),
            ('main_status_counts', 'Etats du modele principal'),
            ('secondary_llm_call_count', 'Appels secondaires'),
            ('main_duration_ms_p50', 'Latence principale p50'),
            ('main_duration_ms_p95', 'Latence principale p95'),
        ),
        conversation_summary=_fields(
            ('modules_involved.providers', 'Modeles impliques'),
        ),
        turn_summary=_fields(
            ('main.present', 'Modele principal appele'),
            ('main.status', 'Etat du modele principal'),
            ('secondary', 'Agents secondaires'),
        ),
        human_detail=_fields(
            ('provider_roles', 'Explique qui a ete consulte et pourquoi.'),
            ('latency_status', 'Resume les temps de reponse visibles.'),
        ),
        sources=('llm_call events', 'prepared provider events', 'dashboard_turn_facts.providers'),
        limits=('Ne contient pas les prompts ni reponses completes des providers.',),
        degradation_reasons=(
            ('main_provider_error', 'Le modele principal a signale une erreur.'),
            ('secondary_provider_error', 'Un modele secondaire a signale une erreur.'),
            ('main_call_missing', 'L appel au modele principal n est pas observe.'),
        ),
        gated_content=('Payload modele principal', 'Payloads providers secondaires', 'Reponses providers completes'),
        bucket_metrics_reducer=_reduce_provider_metrics,
        bucket_metrics_finalizer=_finalize_provider_metrics,
        turn_summary_renderer=_summarize_providers_turn,
    ),
    _module(
        module_key='identity',
        label_fr='Identite',
        description_fr='Indique si le bloc identite a participe au contexte.',
        global_metrics=_fields(
            ('block_present_turns', 'Tours avec bloc identite'),
            ('status_counts', 'Etats identite'),
            ('chars_total', 'Volume identite observe'),
        ),
        conversation_summary=_fields(
            ('modules_involved.identity', 'Identite impliquee'),
        ),
        turn_summary=_fields(
            ('block_present', 'Bloc identite present'),
            ('status', 'Etat identite'),
            ('chars', 'Taille du bloc identite'),
        ),
        human_detail=_fields(
            ('identity_presence', 'Explique si l identite etait presente ou absente.'),
        ),
        sources=('prompt_prepared identity summary', 'identity observability', 'dashboard_turn_facts.identity'),
        limits=('Ne contient pas le texte identitaire canonique ou injecte.',),
        degradation_reasons=(
            ('identity_block_missing', 'Le bloc identite attendu n est pas observe.'),
            ('identity_legacy_signal', 'Le signal identite vient d une trace ancienne ou partielle.'),
        ),
        gated_content=('Bloc identite injecte', 'Identity complete liee au tour'),
        bucket_metrics_reducer=_reduce_identity_metrics,
        turn_summary_renderer=_summarize_identity_turn,
    ),
    _module(
        module_key='hermeneutic',
        label_fr='Jugement hermeneutique',
        description_fr='Indique si le jugement hermeneutique a ete lu ou injecte.',
        global_metrics=_fields(
            ('block_present_turns', 'Tours avec jugement'),
            ('fallback_turns', 'Tours en fallback'),
            ('status_counts', 'Etats hermeneutiques'),
        ),
        conversation_summary=_fields(
            ('modules_involved.hermeneutic', 'Hermeneutique impliquee'),
        ),
        turn_summary=_fields(
            ('block_present', 'Jugement present'),
            ('fallback', 'Fallback hermeneutique'),
            ('status', 'Etat hermeneutique'),
        ),
        human_detail=_fields(
            ('judgement_status', 'Explique si le jugement a ete disponible.'),
        ),
        sources=('primary_node events', 'hermeneutic observability', 'dashboard_turn_facts.hermeneutic'),
        limits=('Ne contient pas le texte exact du jugement ou des replies runtime.'),
        degradation_reasons=(
            ('hermeneutic_fallback', 'Le jugement hermeneutique a fonctionne en mode fallback.'),
            ('hermeneutic_block_missing', 'Le jugement hermeneutique n est pas observe dans le contexte.'),
        ),
        gated_content=('Jugement hermeneutique complet', 'Replies runtime hermeneutiques'),
        bucket_metrics_reducer=_reduce_hermeneutic_metrics,
        turn_summary_renderer=_summarize_hermeneutic_turn,
    ),
    _module(
        module_key='node_state',
        label_fr='Etat du noeud',
        description_fr='Resume la lecture et l ecriture du node_state.',
        global_metrics=_fields(
            ('read_present_count', 'Lectures observees'),
            ('read_valid_count', 'Lectures valides'),
            ('write_attempted_count', 'Ecritures tentees'),
            ('write_succeeded_count', 'Ecritures reussies'),
            ('fail_open_count', 'Fail-open observes'),
        ),
        conversation_summary=_fields(
            ('modules_involved.node_state', 'Etat du noeud implique'),
        ),
        turn_summary=_fields(
            ('read_present', 'Etat relu'),
            ('read_valid', 'Lecture valide'),
            ('write_succeeded', 'Ecriture reussie'),
            ('fail_open', 'Fail-open'),
        ),
        human_detail=_fields(
            ('state_flow', 'Explique si l etat a ete relu puis mis a jour.'),
        ),
        sources=('primary_node events', 'dashboard_turn_facts.node_state'),
        limits=('Ne contient pas de contenu textuel du noeud au-dela des statuts compacts.',),
        degradation_reasons=(
            ('node_state_fail_open', 'L etat du noeud est passe en mode fail-open.'),
            ('node_state_write_failed', 'La mise a jour de l etat du noeud a echoue.'),
        ),
        gated_content=('Detail complet futur du node_state'),
        bucket_metrics_reducer=_reduce_node_state_metrics,
        turn_summary_renderer=_summarize_node_state_turn,
    ),
    _module(
        module_key='errors',
        label_fr='Problemes rencontres',
        description_fr='Regroupe erreurs, skips et fallbacks visibles.',
        global_metrics=_fields(
            ('error_count', 'Erreurs'),
            ('skipped_count', 'Etapes ignorees'),
            ('fallback_count', 'Fallbacks'),
            ('reason_code_counts', 'Causes compactes'),
        ),
        conversation_summary=_fields(
            ('error_count', 'Erreurs conversation'),
            ('fallback_count', 'Fallbacks conversation'),
            ('last_problem_reason_code', 'Dernier probleme compact'),
        ),
        turn_summary=_fields(
            ('error_count', 'Erreurs du tour'),
            ('skipped_count', 'Etapes ignorees'),
            ('fallback_count', 'Fallbacks du tour'),
        ),
        human_detail=_fields(
            ('probable_cause', 'Traduit la cause la plus probable en francais.'),
        ),
        sources=('dashboard_turn_facts.errors', 'chat_log_events status/reason_code'),
        limits=('Ne contient pas de traceback brut ni de message libre complet.',),
        degradation_reasons=(
            ('stage_error', 'Une etape du tour a signale une erreur.'),
            ('fallback_used', 'Un fallback a ete utilise pour continuer le tour.'),
        ),
        bucket_metrics_reducer=_reduce_error_metrics,
        turn_summary_renderer=_summarize_errors_turn,
        turn_degradation_reason_resolver=_resolve_errors_reason,
    ),
)


FUTURE_OBSERVABLE_MODULES: tuple[ObservableModule, ...] = (
    _module(
        module_key='images',
        label_fr='Images',
        description_fr='Module futur pour generation ou analyse d images.',
        global_metrics=_fields(
            ('image_requests_count', 'Demandes image'),
            ('image_success_count', 'Images reussies'),
            ('image_error_count', 'Problemes image'),
        ),
        conversation_summary=_fields(
            ('image_turns', 'Tours avec image'),
        ),
        turn_summary=_fields(
            ('requested', 'Image demandee'),
            ('success', 'Image reussie'),
            ('artifact_count', 'Artefacts image'),
        ),
        human_detail=_fields(
            ('image_flow', 'Explique la demande et le resultat image sans exposer le media par defaut.'),
        ),
        sources=('future image events', 'future image artifacts'),
        limits=('Contrat reserve: aucun event image n est materialise dans le Lot 3.'),
        degradation_reasons=(
            ('image_generation_error', 'La generation d image a echoue.'),
            ('image_artifact_missing', 'L artefact image attendu n est pas disponible.'),
        ),
        gated_content=('Image complete', 'Prompt image complet', 'Artefact image source'),
        future=True,
    ),
)


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


def observable_modules(
    *,
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> tuple[ObservableModule, ...]:
    modules = list(INITIAL_OBSERVABLE_MODULES)
    if include_future:
        modules.extend(FUTURE_OBSERVABLE_MODULES)
    modules.extend(extra_modules)

    seen: set[str] = set()
    for module in modules:
        key = str(module.module_key or '').strip()
        if not key:
            raise ValueError('observable module key is required')
        if key in seen:
            raise ValueError(f'duplicate observable module key: {key}')
        seen.add(key)
    return tuple(modules)


def observable_module_keys(
    *,
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> tuple[str, ...]:
    return tuple(
        module.module_key
        for module in observable_modules(
            include_future=include_future,
            extra_modules=extra_modules,
        )
    )


def get_observable_module(
    module_key: str,
    *,
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> ObservableModule:
    normalized = str(module_key or '').strip()
    for module in observable_modules(
        include_future=include_future,
        extra_modules=extra_modules,
    ):
        if module.module_key == normalized:
            return module
    raise KeyError(normalized)


def explain_module_degradation(
    module_key: str,
    *,
    reason_code: str | None = None,
    state: str = 'degraded',
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> str:
    module = get_observable_module(
        module_key,
        include_future=include_future,
        extra_modules=extra_modules,
    )
    reasons = _reason_dict(module)
    normalized_reason = str(reason_code or '').strip()
    if normalized_reason and normalized_reason in reasons:
        return reasons[normalized_reason]
    state_label = _STATE_LABELS_FR.get(str(state or '').strip(), 'Etat a verifier')
    return f"{module.label_fr}: {state_label}. La cause exacte doit etre ouverte dans le detail technique."


def summarize_module_turn(
    module_key: str,
    fact: Mapping[str, Any],
    *,
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> str:
    module = get_observable_module(
        module_key,
        include_future=include_future,
        extra_modules=extra_modules,
    )
    if module.turn_summary_renderer:
        return module.turn_summary_renderer(fact)
    return f"{module.label_fr}: module declare, sans resume specialise pour ce tour."


def resolve_module_turn_degradation_reason(
    module_key: str,
    fact: Mapping[str, Any],
    *,
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> str | None:
    module = get_observable_module(
        module_key,
        include_future=include_future,
        extra_modules=extra_modules,
    )
    if module.turn_degradation_reason_resolver:
        return module.turn_degradation_reason_resolver(fact)
    return None


def build_dashboard_module_catalog(
    *,
    include_future: bool = False,
    extra_modules: Sequence[ObservableModule] = (),
) -> dict[str, object]:
    modules = observable_modules(
        include_future=include_future,
        extra_modules=extra_modules,
    )
    return {
        'kind': 'dashboard_observable_module_catalog',
        'contract_version': MODULE_CONTRACT_VERSION,
        'module_keys': [module.module_key for module in modules],
        'modules': [_module_to_public_dict(module) for module in modules],
        'redaction': {
            'raw_content_stored': False,
            'raw_labels_from_runtime_content': False,
        },
    }
