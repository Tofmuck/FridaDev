from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


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
    ),
)


FUTURE_OBSERVABLE_MODULES: tuple[ObservableModule, ...] = (
    _module(
        module_key='documents',
        label_fr='Documents',
        description_fr='Module futur pour lecture, selection et injection documentaire.',
        global_metrics=_fields(
            ('documents_requested_count', 'Demandes documentaires'),
            ('documents_used_count', 'Documents utilises'),
            ('documents_error_count', 'Problemes documentaires'),
        ),
        conversation_summary=_fields(
            ('documents_used_turns', 'Tours avec documents'),
        ),
        turn_summary=_fields(
            ('requested', 'Recherche documentaire demandee'),
            ('used_count', 'Documents utilises'),
            ('injected_count', 'Passages injectes'),
        ),
        human_detail=_fields(
            ('document_flow', 'Explique quels documents ont ete utilises sans afficher leur contenu.'),
        ),
        sources=('future document events', 'future document artifacts'),
        limits=('Contrat reserve: aucun event documentaire n est materialise dans le Lot 3.'),
        degradation_reasons=(
            ('document_unavailable', 'Le document attendu n est pas disponible.'),
            ('document_injection_missing', 'Aucun passage documentaire n a ete injecte.'),
        ),
        gated_content=('Document complet', 'Passages documentaires injectes'),
        future=True,
    ),
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
