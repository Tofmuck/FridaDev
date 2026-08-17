from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from observability.dashboard_observable_module_domains import (
    _finalize_pipeline_metrics,
    _finalize_provider_metrics,
    _reduce_biblio_metrics,
    _reduce_documents_metrics,
    _reduce_error_metrics,
    _reduce_hermeneutic_metrics,
    _reduce_identity_metrics,
    _reduce_memory_metrics,
    _reduce_node_state_metrics,
    _reduce_persistence_metrics,
    _reduce_pipeline_metrics,
    _reduce_provider_metrics,
    _reduce_web_metrics,
    _resolve_biblio_reason,
    _resolve_documents_reason,
    _resolve_errors_reason,
    _summarize_biblio_turn,
    _summarize_documents_turn,
    _summarize_errors_turn,
    _summarize_hermeneutic_turn,
    _summarize_identity_turn,
    _summarize_memory_turn,
    _summarize_node_state_turn,
    _summarize_persistence_turn,
    _summarize_pipeline_turn,
    _summarize_providers_turn,
    _summarize_web_turn,
)
from observability.dashboard_observable_module_serialization import (
    _STATE_LABELS_FR,
    _module_to_public_dict,
    _reason_dict,
)


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

BucketMetricsReducer = Callable[[dict[str, Any], Mapping[str, Any]], None]
BucketMetricsFinalizer = Callable[[dict[str, Any]], None]
TurnSummaryRenderer = Callable[[Mapping[str, Any]], str]
TurnDegradationReasonResolver = Callable[[Mapping[str, Any]], str | None]


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
            ('ocr_applied_documents_total', 'Documents OCRises observes'),
        ),
        conversation_summary=_fields(
            ('documents_active_turns', 'Tours avec documents actifs'),
            ('modules_involved.documents', 'Documents actifs impliques'),
        ),
        turn_summary=_fields(
            ('active_count', 'Documents actifs'),
            ('injected_count', 'Documents envoyes entiers'),
            ('not_injected_count', 'Documents non envoyes'),
            ('ocr_applied_count', 'Documents OCRises'),
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
            ('active_documents_read_error', 'L etat des documents actifs n a pas pu etre lu pendant ce tour.'),
            ('active_documents_reader_unavailable', 'Le lecteur des documents actifs etait indisponible au runtime.'),
            ('document_too_large_for_turn', 'Un document actif etait trop gros pour etre envoye entier dans ce tour.'),
            ('document_empty_text', 'Un document actif ne contenait pas de texte injectable.'),
        ),
        gated_content=(),
        bucket_metrics_reducer=_reduce_documents_metrics,
        turn_summary_renderer=_summarize_documents_turn,
        turn_degradation_reason_resolver=_resolve_documents_reason,
    ),
    _module(
        module_key='biblio',
        label_fr='Biblio native',
        description_fr='Observe les consultations Catalogue Biblio, resolutions et lanes sans contenu de passage.',
        global_metrics=_fields(
            ('enabled_turns', 'Tours avec Biblio activee'),
            ('used_turns', 'Tours avec consultation Biblio'),
            ('passages_total', 'Passages Biblio observes'),
            ('skipped_total', 'Passages ignores'),
            ('lane_chars_total', 'Taille totale des lanes Biblio'),
            ('search_candidates_total', 'Candidats de recherche observes'),
            ('context_fetch_total', 'Contextes Catalogue consultes'),
            ('selected_passages_total', 'Passages selectionnes avec certitude'),
            ('ambiguous_turns', 'Tours Biblio ambigus'),
            ('librarian_agent_present_turns', 'Tours avec comparaison agent bibliothecaire observee'),
            ('librarian_agent_model_called_turns', 'Tours avec appel modele agent bibliothecaire'),
            ('librarian_agent_candidate_plan_turns', 'Tours avec plan candidat agent observe'),
            ('librarian_agent_deterministic_controlled_turns', 'Tours ou le deterministe reste controleur'),
            ('librarian_agent_used_for_response_turns', 'Tours ou l agent controle la reponse produit'),
            ('librarian_agent_product_response_changed_turns', 'Tours ou l agent modifie la reponse produit'),
            ('librarian_agent_attempts_total', 'Tentatives modele agent bibliothecaire'),
            ('librarian_agent_duration_ms_total', 'Duree totale modele agent bibliothecaire'),
            ('librarian_agent_response_chars_total', 'Taille totale des sorties modele agent'),
            ('librarian_agent_tool_call_events_total', 'Evenements outil agentique executes'),
            ('librarian_agent_validation_tool_calls_total', 'Appels outil proposes par le JSON valide'),
            ('librarian_agent_mode_counts', 'Modes agent bibliothecaire observes'),
            ('librarian_agent_status_counts', 'Etats agent bibliothecaire observes'),
            ('librarian_agent_reason_counts', 'Raisons agent bibliothecaire observees'),
            ('librarian_agent_model_status_counts', 'Etats modele agent observes'),
            ('librarian_agent_validation_status_counts', 'Etats validation JSON agent observes'),
            ('librarian_agent_tool_execution_status_counts', 'Etats execution outils agentiques'),
            ('librarian_agent_tool_name_counts', 'Noms outils agentiques allowlistes proposes'),
        ),
        conversation_summary=_fields(
            ('biblio_used_turns', 'Tours avec Biblio consultee'),
            ('biblio_passages_total', 'Passages Biblio observes'),
            ('modules_involved.biblio', 'Biblio impliquee'),
        ),
        turn_summary=_fields(
            ('used', 'Biblio consultee'),
            ('status', 'Etat Biblio'),
            ('document_status', 'Resolution document'),
            ('passage_count', 'Passages observes'),
            ('search_candidate_count', 'Candidats de recherche'),
            ('context_fetch_count', 'Contextes consultes'),
            ('selected_passage_count', 'Passages selectionnes'),
            ('ambiguous', 'Ambiguite conservee'),
            ('reason_code_counts', 'Raisons compactes'),
        ),
        human_detail=_fields(
            ('biblio_flow', 'Explique document resolu, ambiguite, passage extrait ou skip sans afficher le passage.'),
        ),
        sources=('biblio events', 'dashboard_turn_facts.biblio', 'biblio observability projection'),
        limits=(
            'N active pas l agent bibliothecaire comme controleur de reponse produit.',
            'N execute pas les outils agentiques proposes par le comparateur.',
            'Le toggle frontend Biblio et le branchement chat deterministe existent deja mais sont hors perimetre de cette observabilite.',
            'Ne contient jamais le passage, le payload Catalogue, le prompt complet, le locator brut, titre ou auteur.',
            'Les recherches de passages exposent seulement counts, endpoint kinds, ids courts, hashes courts et raisons compactes.',
            'Reste separe des documents actifs, Memory/RAG, workspace, Identity, Summary, Web et OCR.',
        ),
        degradation_reasons=(
            ('biblio_context_candidates_ambiguous', 'Plusieurs contextes Catalogue restent plausibles.'),
            ('biblio_selection_gap_too_small', 'Le meilleur passage candidat ne domine pas assez les suivants.'),
            ('biblio_selection_evidence_insufficient', 'Les signaux de ranking ne suffisent pas a selectionner un passage.'),
            ('ambiguous_document', 'Plusieurs documents Catalogue restent plausibles.'),
            ('ambiguous_locator', 'Plusieurs locators restent plausibles.'),
            ('document_not_found', 'Aucun document Catalogue compatible n a ete trouve.'),
            ('locator_not_found', 'Aucun locator compatible n a ete trouve.'),
            ('catalogue_unavailable', 'Catalogue etait indisponible ou en erreur.'),
            ('passage_too_long', 'Le passage extrait depassait la borne autorisee.'),
            ('biblio_prompt_max_total_chars_reached', 'La lane Biblio aurait depasse sa taille maximale.'),
            ('biblio_prompt_max_passages_reached', 'La lane Biblio avait atteint son nombre maximal de passages.'),
        ),
        gated_content=('Passage Biblio brut', 'Payload Catalogue brut', 'Prompt Biblio complet'),
        bucket_metrics_reducer=_reduce_biblio_metrics,
        turn_summary_renderer=_summarize_biblio_turn,
        turn_degradation_reason_resolver=_resolve_biblio_reason,
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
            ('failed_count', 'Echecs bornes'),
            ('attempt_failure_count', 'Vraies pannes'),
            ('skipped_count', 'Etapes ignorees'),
            ('disabled_count', 'Modules desactives'),
            ('not_selected_count', 'Modules non selectionnes'),
            ('not_configured_count', 'Prerequis absents'),
            ('not_applicable_count', 'Modules non concernes'),
            ('refused_count', 'Refus produit'),
            ('non_problem_status_count', 'No-op/refus non pannes'),
            ('fallback_count', 'Fallbacks'),
            ('status_counts', 'Statuts V1'),
            ('status_schema_counts', 'Schemas de statut'),
            ('reason_code_counts', 'Causes compactes'),
            ('problem_reason_code_counts', 'Causes des vraies pannes'),
            ('non_problem_reason_code_counts', 'Causes no-op/refus'),
        ),
        conversation_summary=_fields(
            ('error_count', 'Erreurs conversation'),
            ('failed_count', 'Echecs bornes conversation'),
            ('problem_count', 'Problemes conversation'),
            ('fallback_count', 'Fallbacks conversation'),
            ('last_problem_reason_code', 'Dernier probleme compact'),
        ),
        turn_summary=_fields(
            ('error_count', 'Erreurs du tour'),
            ('failed_count', 'Echecs bornes du tour'),
            ('attempt_failure_count', 'Vraies pannes du tour'),
            ('skipped_count', 'Etapes ignorees'),
            ('non_problem_status_count', 'No-op/refus non pannes'),
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
