from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from observability import dashboard_analytics
from observability.dashboard_read_model_query import _iso, _mapping, _to_int


def _translated_inspection(fact: Mapping[str, Any]) -> list[dict[str, Any]]:
    modules = []
    for module in dashboard_analytics.observable_modules():
        reason_code = dashboard_analytics.resolve_module_turn_degradation_reason(
            module.module_key,
            fact,
        )
        modules.append(
            {
                'module_key': module.module_key,
                'label_fr': module.label_fr,
                'summary_fr': dashboard_analytics.summarize_module_turn(module.module_key, fact),
                'degradation_fr': (
                    dashboard_analytics.explain_module_degradation(
                        module.module_key,
                        reason_code=reason_code,
                    )
                    if reason_code
                    else None
                ),
                'raw_content_available': False,
                'proof_level': 'compact_summary',
                'content_status_fr': (
                    'Le contenu complet n est pas charge dans cette inspection; '
                    'seuls les faits compacts materialises sont utilises.'
                ),
            }
        )
    return modules


def _classification_fr(value: Any) -> str:
    labels = {
        'complete': 'reussi',
        'degraded': 'degrade',
        'partial': 'partiel',
        'legacy_incomplete': 'historique incomplet',
    }
    return labels.get(str(value or '').strip().lower(), 'a verifier')


def _status_fr(value: Any) -> str:
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
        'resolved': 'resolu',
        'ambiguous': 'ambigu',
        'not_found': 'introuvable',
        'unknown': 'a verifier',
    }
    return labels.get(str(value or '').strip().lower(), 'a verifier')


def _yes_no(value: Any) -> str:
    return 'oui' if bool(value) else 'non'


_REASON_CODE_LABELS = {
    'assistant_final_not_saved': 'reponse finale non sauvegardee',
    'assistant_final_saved': 'reponse finale sauvegardee',
    'assistant_interrupted': 'reponse interrompue',
    'identity_block_absent': 'bloc identite absent',
    'memory_chain_snapshot_missing': 'chaine memoire non observee',
    'missing_assistant_final_persist': 'sauvegarde finale non observee',
    'missing_main_llm_call': 'appel du modele principal non observe',
    'missing_memory_chain_snapshot': 'chaine memoire non observee',
    'missing_secondary_provider_prepared': 'preparation d un modele secondaire non observee',
    'no_data': 'donnee absente',
    'not_applicable': 'module non utilise',
    'provider_missing': 'modele attendu non observe',
    'retrieve_error': 'recherche memoire en erreur',
    'runtime_error': 'erreur runtime',
    'timeout': 'delai depasse',
    'validation_error': 'validation en erreur',
    'validation_fail_open': 'validation ouverte par securite',
    'document_too_large_for_turn': 'document actif trop gros pour ce tour',
    'document_empty_text': 'document actif sans texte injectable',
    'active_documents_read_error': 'lecture des documents actifs en erreur',
    'active_documents_reader_unavailable': 'lecteur des documents actifs indisponible',
}


def _reason_codes_fr(errors: Mapping[str, Any]) -> str:
    reason_counts = _mapping(errors.get('reason_code_counts'))
    if not reason_counts:
        return 'aucune cause compacte observee'
    parts: list[str] = []
    unknown_total = 0
    for reason, count in sorted(reason_counts.items(), key=lambda item: str(item[0])):
        amount = _to_int(count)
        label = _REASON_CODE_LABELS.get(str(reason or '').strip())
        if label:
            parts.append(f'{label}: {amount}')
        else:
            unknown_total += amount
    if unknown_total:
        parts.append(
            f'{unknown_total} cause(s) technique(s) compacte(s) non traduite(s); '
            'detail disponible dans les logs techniques'
        )
    return ', '.join(parts)


def _summary_parent_line(rag: Mapping[str, Any]) -> str:
    traces_with_summary_id = _to_int(rag.get('injected_traces_with_summary_id_count'))
    parent_injected_count = _to_int(rag.get('parent_summaries_injected_count'))
    legacy_parent_count = _to_int(rag.get('memory_context_summary_count'))
    parent_summaries = [
        _mapping(item)
        for item in (rag.get('parent_summaries_injected') or [])
        if isinstance(item, Mapping)
    ]
    if traces_with_summary_id <= 0 and parent_injected_count <= 0:
        if legacy_parent_count > 0:
            return (
                f'{legacy_parent_count} resume(s) parent(s) ont accompagne la memoire injectee, '
                'mais le lien trace -> summary_id -> fenetre du resume parent n est pas materialise '
                'dans ces faits compacts.'
            )
        return (
            'Aucune trace memoire injectee avec summary_id parent n est prouvee dans ces faits compacts.'
        )
    if parent_injected_count <= 0:
        return (
            f'{traces_with_summary_id} trace(s) memoire injectee(s) portent un summary_id, '
            'mais aucun resume parent injecte correspondant n est prouve dans ces faits compacts.'
        )

    windows: list[str] = []
    for item in parent_summaries[:3]:
        proof = str(item.get('summary_id_sha256_12') or item.get('summary_id') or 'id non materialise')
        start_ts = _iso(item.get('start_ts')) or str(item.get('start_ts') or '').strip() or 'debut inconnu'
        end_ts = _iso(item.get('end_ts')) or str(item.get('end_ts') or '').strip() or 'fin inconnue'
        linked = _to_int(item.get('linked_trace_count'))
        windows.append(f'{proof}: {start_ts} -> {end_ts}, {linked} trace(s) liee(s)')
    suffix = ''
    if len(parent_summaries) > 3:
        suffix = f'; {len(parent_summaries) - 3} resume(s) parent(s) supplementaire(s) non detaille(s)'
    detail = '; '.join(windows) if windows else 'fenetres non materialisees'
    return (
        f'{traces_with_summary_id} trace(s) memoire injectee(s) etaient liee(s) a un summary_id; '
        f'{parent_injected_count} resume(s) parent(s) correspondant(s) ont ete injecte(s) avec ces traces. '
        f'Fenetres: {detail}{suffix}.'
    )


def _first_present_int(mapping: Mapping[str, Any], *keys: str) -> tuple[int, bool]:
    for key in keys:
        if key in mapping:
            return _to_int(mapping.get(key)), True
    return 0, False


def _debug_links(fact: Mapping[str, Any]) -> list[dict[str, str]]:
    conversation_id = quote(str(fact.get('conversation_id') or ''), safe='')
    turn_id = quote(str(fact.get('turn_id') or ''), safe='')
    query = f'conversation_id={conversation_id}&turn_id={turn_id}'
    return [
        {'label_fr': 'Logs techniques', 'href': f'/log?{query}'},
        {'label_fr': 'Memory Admin', 'href': '/memory-admin'},
        {'label_fr': 'Hermeneutic Admin', 'href': '/hermeneutic-admin'},
        {'label_fr': 'Identity', 'href': '/identity'},
    ]


def _document_story_lines(documents: Mapping[str, Any]) -> list[str]:
    active_count = _to_int(documents.get('active_count'))
    injected_count = _to_int(documents.get('injected_count'))
    not_injected_count = _to_int(documents.get('not_injected_count'))
    status = str(documents.get('status') or '').strip().lower()
    read_status = str(documents.get('read_status') or '').strip().lower()
    if status == 'error' or read_status == 'error':
        reason = str(
            documents.get('read_reason_code')
            or documents.get('reason_code')
            or 'active_documents_read_error'
        ).strip()
        label = _REASON_CODE_LABELS.get(reason, 'raison compacte disponible')
        return [
            'Erreur de lecture des documents actifs de conversation sur ce tour.',
            f'Raison compacte: {reason} ({label}).',
            'Aucun document actif n est affirme present par cette erreur de lecture.',
            'Aucun texte de document actif n est affiche dans cette inspection ordinaire.',
        ]
    if active_count <= 0:
        return ['Aucun document actif de conversation n est observe sur ce tour.']

    lines = [
        f'{active_count} document(s) actif(s) de conversation observe(s).',
        f'{injected_count} document(s) envoye(s) entiers au modele.',
        f'{not_injected_count} document(s) non envoye(s) dans ce tour.',
    ]
    for item in [
        _mapping(raw_item)
        for raw_item in (documents.get('documents') or [])
        if isinstance(raw_item, Mapping)
    ][:5]:
        filename = str(item.get('filename') or 'document')
        ext = str(item.get('source_extension') or '').strip()
        reason = str(item.get('reason_code') or '').strip()
        if item.get('injected'):
            status = 'envoye entier'
        elif reason == 'document_too_large_for_turn':
            status = 'non envoye: trop gros pour ce tour'
        elif reason:
            status = f'non envoye: {_REASON_CODE_LABELS.get(reason, "raison compacte disponible")}'
        else:
            status = 'non envoye'
        lines.append(
            f'{filename} ({ext or "type inconnu"}, {_to_int(item.get("byte_size"))} octets, '
            f'{_to_int(item.get("text_chars"))} caracteres'
            f'{", OCRise" if item.get("ocr_applied") else ""}): {status}.'
        )
    if active_count > 5:
        lines.append(f'{active_count - 5} document(s) supplementaire(s) non detaille(s).')
    lines.append('Aucun texte de document actif n est affiche dans cette inspection ordinaire.')
    return lines


def _turn_story(fact: Mapping[str, Any]) -> dict[str, Any]:
    rag = _mapping(fact.get('rag'))
    providers = _mapping(fact.get('providers'))
    main_provider = _mapping(providers.get('main'))
    secondary = _mapping(providers.get('secondary'))
    identity = _mapping(fact.get('identity'))
    hermeneutic = _mapping(fact.get('hermeneutic'))
    web = _mapping(fact.get('web'))
    documents = _mapping(fact.get('documents'))
    biblio = _mapping(fact.get('biblio'))
    librarian_agent = _mapping(biblio.get('librarian_agent'))
    node_state = _mapping(fact.get('node_state'))
    persistence = _mapping(fact.get('persistence'))
    errors = _mapping(fact.get('errors'))
    flags = _mapping(fact.get('flags'))
    content_availability = _mapping(fact.get('content_availability'))
    classification = str(fact.get('classification') or 'legacy_incomplete')
    source_event_count = _to_int(fact.get('source_event_count'))
    error_count = _to_int(errors.get('error_count'))
    failed_count = _to_int(errors.get('failed_count'))
    fallback_count = _to_int(errors.get('fallback_count'))
    attempt_failure_count = _to_int(errors.get('attempt_failure_count')) or error_count + failed_count
    problem_count = _to_int(errors.get('problem_count')) or attempt_failure_count + fallback_count
    non_problem_status_count = _to_int(errors.get('non_problem_status_count')) or sum(
        _to_int(errors.get(key))
        for key in (
            'skipped_count',
            'disabled_count',
            'not_selected_count',
            'not_configured_count',
            'not_applicable_count',
            'refused_count',
        )
    )
    problem_reason_errors = dict(errors)
    if errors.get('problem_reason_code_counts'):
        problem_reason_errors['reason_code_counts'] = errors.get('problem_reason_code_counts')

    context_parts: list[str] = []
    if identity.get('block_present'):
        context_parts.append(f"un bloc identite ({_to_int(identity.get('chars'))} caracteres observes)")
    else:
        context_parts.append('pas de bloc identite observe')
    if _to_int(rag.get('injected')) > 0:
        context_parts.append(f"{_to_int(rag.get('injected'))} element(s) memoire injecte(s)")
    else:
        context_parts.append('aucun element memoire injecte observe')
    summary_active = bool(rag.get('conversation_summary_active_present'))
    summary_in_prompt = bool(rag.get('conversation_summary_in_prompt'))
    summary_count = _to_int(rag.get('conversation_summary_count'))
    if summary_active and summary_in_prompt:
        context_parts.append('un resume actif de conversation injecte')
        summary_line = f'Resume de conversation present et injecte ({summary_count or 1} resume observe).'
    elif summary_active:
        context_parts.append('un resume actif de conversation non injecte')
        summary_line = 'Resume de conversation actif observe, mais non injecte dans le prompt principal.'
    elif rag.get('conversation_summary_event_present') is True:
        context_parts.append('aucun resume actif de conversation observe')
        summary_line = 'Aucun resume de conversation actif sur ce tour.'
    else:
        context_parts.append('etat du resume de conversation non materialise')
        summary_line = 'Etat du resume de conversation non materialise dans ces faits compacts.'
    parent_summary_line = _summary_parent_line(rag)
    if hermeneutic.get('block_present'):
        context_parts.append('un jugement hermeneutique observe')
    else:
        context_parts.append('pas de jugement hermeneutique observe')
    if web.get('injected'):
        context_parts.append('un contexte web injecte')
    else:
        context_parts.append('pas de contexte web injecte observe')
    document_status = str(documents.get('status') or '').strip().lower()
    document_read_status = str(documents.get('read_status') or '').strip().lower()
    if document_status == 'error' or document_read_status == 'error':
        context_parts.append('lecture des documents actifs en erreur')
    elif _to_int(documents.get('injected_count')) > 0:
        context_parts.append(f"{_to_int(documents.get('injected_count'))} document(s) actif(s) injecte(s) entier(s)")
    elif _to_int(documents.get('active_count')) > 0:
        context_parts.append('document actif observe mais non injecte')
    else:
        context_parts.append('pas de document actif observe')
    if biblio.get('used') and _to_int(biblio.get('passage_count')) > 0:
        context_parts.append(f"{_to_int(biblio.get('passage_count'))} passage(s) Biblio observe(s)")
    elif biblio.get('used'):
        context_parts.append('Biblio consultee sans passage injecte observe')
    else:
        context_parts.append('pas de consultation Biblio observee')
    if librarian_agent.get('present'):
        context_parts.append('comparaison agent bibliothecaire observee')

    embeddings_requested, embeddings_requested_present = _first_present_int(
        rag,
        'embeddings_requested',
        'embedding_requested_count',
        'embeddings_requested_count',
    )
    embeddings_succeeded, embeddings_succeeded_present = _first_present_int(
        rag,
        'embeddings_succeeded',
        'embedding_success_count',
        'embeddings_success_count',
    )
    if embeddings_requested_present or embeddings_succeeded_present:
        embeddings_line = f'{embeddings_requested} embeddings demandes, {embeddings_succeeded} reussis.'
    else:
        embeddings_line = (
            'Aucun compteur embeddings n est disponible dans cette synthese; '
            'aucun vecteur ni bloc massif n est affiche.'
        )

    proof_lines = [
        (
            'Le tour est materialise depuis '
            f'{source_event_count} etape(s) compacte(s); le texte exact recu par Frida n est pas affiche ici.'
        ),
        (
            'Le contexte modele exact n est pas reconstructible depuis ces seuls faits compacts '
            'quand seuls presence, counts, longueurs ou hashes sont disponibles.'
        ),
        (
            'Le contenu complet n est pas precharge ici; il peut etre demande volontairement '
            'avec l action Afficher le contenu complet.'
        ),
    ]
    if content_availability:
        prompt_manifest_available = bool(content_availability.get('prompt_manifest_available'))
        proof_lines.append(
            'Manifeste de prompt disponible: '
            f'{_yes_no(prompt_manifest_available)}.'
        )
    if bool(flags.get('events_truncated')):
        proof_lines.append('La trace source du tour est signalee comme tronquee.')

    sections = [
        {
            'key': 'received',
            'label_fr': 'Ce que Frida a recu',
            'items': [
                'Une demande utilisateur est representee par ce tour.',
                'La lecture reste traduite et sans contenu brut: le texte exact de la demande n est pas affiche.',
            ],
        },
        {
            'key': 'pipeline',
            'label_fr': 'Parcours du tour',
            'items': [
                f"Etat du tour: {_classification_fr(classification)}.",
                f"Score de completude: {_to_int(fact.get('score'))}.",
                f"Etapes compactes observees: {source_event_count}.",
                f"Reponse finale sauvegardee: {_yes_no(persistence.get('assistant_final_saved'))}.",
                f"Reponse interrompue: {_yes_no(persistence.get('assistant_interrupted'))}.",
            ],
        },
        {
            'key': 'model_context',
            'label_fr': 'Ce que le modele a recu, en lecture traduite',
            'items': [
                'Composition compacte observee: ' + '; '.join(context_parts) + '.',
                f"Modele principal observe: {_yes_no(main_provider.get('present'))}; etat: {_status_fr(main_provider.get('status'))}.",
                f"Modeles secondaires consultes: {_to_int(sum(_to_int(_mapping(item).get('llm_call_events_count')) for item in secondary.values()))}.",
            ],
        },
        {
            'key': 'modules',
            'label_fr': 'Modules',
            'items': [
                (
                    f"Memoire: {_to_int(rag.get('retrieved'))} trouve(s), "
                    f"{_to_int(rag.get('basket'))} candidat(s), {_to_int(rag.get('kept'))} garde(s), "
                    f"{_to_int(rag.get('rejected'))} rejete(s), {_to_int(rag.get('injected'))} injecte(s)."
                ),
                summary_line,
                parent_summary_line,
                f"Identite: bloc present {_yes_no(identity.get('block_present'))}, etat {_status_fr(identity.get('status'))}.",
                f"Hermeneutique: jugement present {_yes_no(hermeneutic.get('block_present'))}, fallback {_yes_no(hermeneutic.get('fallback'))}.",
                (
                    f"Node state: relu {_yes_no(node_state.get('read_present'))}, "
                    f"lecture valide {_yes_no(node_state.get('read_valid'))}, "
                    f"ecriture tentee {_yes_no(node_state.get('write_attempted'))}, "
                    f"ecriture reussie {_yes_no(node_state.get('write_succeeded'))}."
                ),
                (
                    f"Web: demande {_yes_no(web.get('requested'))}, reussi {_yes_no(web.get('success'))}, "
                    f"injecte {_yes_no(web.get('injected'))}, resultats comptes {_to_int(web.get('results_count'))}."
                ),
                *_document_story_lines(documents),
                (
                    f"Biblio: consultee {_yes_no(biblio.get('used'))}, etat {_status_fr(biblio.get('status'))}, "
                    f"document {_status_fr(biblio.get('document_status'))}, passages {_to_int(biblio.get('passage_count'))}, "
                    f"candidats {_to_int(biblio.get('search_candidate_count'))}, "
                    f"contextes {_to_int(biblio.get('context_fetch_count'))}, "
                    f"selectionnes {_to_int(biblio.get('selected_passage_count'))}, "
                    f"ambigue {_yes_no(biblio.get('ambiguous'))}."
                ),
                (
                    f"Agent Biblio: present {_yes_no(librarian_agent.get('present'))}, "
                    f"mode {str(librarian_agent.get('mode') or 'non observe')}, "
                    f"modele appele {_yes_no(librarian_agent.get('model_called'))}, "
                    f"plan candidat {_yes_no(librarian_agent.get('candidate_plan_present'))}, "
                    f"controleur deterministe {_yes_no(librarian_agent.get('deterministic_controller'))}, "
                    f"utilise pour reponse {_yes_no(librarian_agent.get('used_for_response'))}, "
                    f"outils agentiques {str(librarian_agent.get('tool_execution_status') or 'not_executed')}."
                ),
                f"Persistence: etat {_status_fr(persistence.get('status'))}.",
            ],
        },
        {
            'key': 'problems',
            'label_fr': 'Problemes et degradations',
            'items': [
                f"Erreurs compactes: {error_count}.",
                f"Echecs bornes compacts: {failed_count}.",
                f"Vraies pannes compactes: {attempt_failure_count}.",
                f"Skips compacts: {_to_int(errors.get('skipped_count'))}.",
                f"No-op/refus compacts non pannes: {non_problem_status_count}.",
                f"Fallbacks compacts: {fallback_count}.",
                f"Problemes compacts actionnables: {problem_count}.",
                f"Causes compactes: {_reason_codes_fr(problem_reason_errors)}.",
            ],
        },
        {
            'key': 'massive_data',
            'label_fr': 'Donnees massives resumees',
            'items': [
                embeddings_line,
                'Les grands blocs, vecteurs, contenus complets des modeles, textes memoire, identite et web ne sont pas dumps dans cette inspection.',
            ],
        },
        {
            'key': 'proof_limits',
            'label_fr': 'Preuves et limites',
            'items': proof_lines,
        },
    ]
    return {
        'kind': 'dashboard_turn_story',
        'title_fr': 'Inspection traduite du tour',
        'summary_fr': (
            f"Tour {_classification_fr(classification)} avec {attempt_failure_count} vraie(s) panne(s) "
            f"et {fallback_count} fallback(s) compacts."
        ),
        'sections': sections,
        'debug_links': _debug_links(fact),
        'proof_level': 'translated_compact_inspection',
        'content_status_fr': (
            'Contenu complet non charge; utilisez Afficher le contenu complet pour verifier ce qui est '
            'disponible, partiel, seulement prouve par empreinte, ou non reconstructible.'
        ),
        'redaction': {'raw_content_included': False},
    }


build_document_story_lines = _document_story_lines
build_translated_inspection = _translated_inspection
build_turn_story = _turn_story
