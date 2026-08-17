from __future__ import annotations

from typing import Any, Mapping, Sequence


_TRUE_TOKENS = {'1', 'true', 'yes', 'y', 'on'}
_FALSE_TOKENS = {'0', 'false', 'no', 'n', 'off'}


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


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value == 1
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
    return False


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
    _add_metric_count(metrics, 'ocr_applied_documents_total', _to_int(documents.get('ocr_applied_count')))
    _add_metric_count(metrics, 'ocr_duration_ms_total', _to_int(documents.get('ocr_duration_ms_total')))
    ocr_engine_counts = _mapping(documents.get('ocr_engine_counts'))
    for engine, count in ocr_engine_counts.items():
        _add_metric_label(metrics, 'ocr_engine_counts', engine, _to_int(count))
    reason_counts = _mapping(documents.get('reason_code_counts'))
    for reason, count in reason_counts.items():
        _add_metric_label(metrics, 'reason_code_counts', reason, _to_int(count))


def _reduce_biblio_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    biblio = _mapping(fact.get('biblio'))
    librarian_agent = _mapping(biblio.get('librarian_agent'))
    _add_metric_label(metrics, 'status_counts', biblio.get('status'))
    _add_metric_count(metrics, 'enabled_turns', 1 if biblio.get('enabled') else 0)
    _add_metric_count(metrics, 'used_turns', 1 if biblio.get('used') else 0)
    _add_metric_count(metrics, 'passages_total', _to_int(biblio.get('passage_count')))
    _add_metric_count(metrics, 'skipped_total', _to_int(biblio.get('skipped_count')))
    _add_metric_count(metrics, 'lane_chars_total', _to_int(biblio.get('lane_chars')))
    _add_metric_count(metrics, 'search_candidates_total', _to_int(biblio.get('search_candidate_count')))
    _add_metric_count(metrics, 'context_fetch_total', _to_int(biblio.get('context_fetch_count')))
    _add_metric_count(metrics, 'selected_passages_total', _to_int(biblio.get('selected_passage_count')))
    _add_metric_count(metrics, 'ambiguous_turns', 1 if biblio.get('ambiguous') else 0)
    _add_metric_count(metrics, 'ranking_available_turns', 1 if biblio.get('ranking_available') else 0)
    document_status = biblio.get('document_status')
    if document_status:
        _add_metric_label(metrics, 'document_status_counts', document_status)
    passage_status = biblio.get('passage_status')
    if passage_status:
        _add_metric_label(metrics, 'passage_status_counts', passage_status)
    for endpoint_kind in biblio.get('endpoint_kinds') or []:
        _add_metric_label(metrics, 'endpoint_kind_counts', endpoint_kind)
    for reason in biblio.get('selection_reason_codes') or []:
        _add_metric_label(metrics, 'selection_reason_counts', reason)
    reason_counts = _mapping(biblio.get('reason_code_counts'))
    for reason, count in reason_counts.items():
        _add_metric_label(metrics, 'reason_code_counts', reason, _to_int(count))
    agent_present = _to_bool(librarian_agent.get('present'))
    if agent_present:
        _add_metric_count(metrics, 'librarian_agent_present_turns', 1)
        _add_metric_count(metrics, 'librarian_agent_model_called_turns', 1 if _to_bool(librarian_agent.get('model_called')) else 0)
        _add_metric_count(
            metrics,
            'librarian_agent_candidate_plan_turns',
            1 if _to_bool(librarian_agent.get('candidate_plan_present')) else 0,
        )
        _add_metric_count(
            metrics,
            'librarian_agent_deterministic_controlled_turns',
            1 if _to_bool(librarian_agent.get('deterministic_controller')) else 0,
        )
        _add_metric_count(
            metrics,
            'librarian_agent_used_for_response_turns',
            1 if _to_bool(librarian_agent.get('used_for_response')) else 0,
        )
        _add_metric_count(
            metrics,
            'librarian_agent_product_response_changed_turns',
            1 if _to_bool(librarian_agent.get('product_response_changed')) else 0,
        )
        _add_metric_count(metrics, 'librarian_agent_attempts_total', _to_int(librarian_agent.get('attempt_count')))
        _add_metric_count(metrics, 'librarian_agent_duration_ms_total', _to_int(librarian_agent.get('duration_ms')))
        _add_metric_count(metrics, 'librarian_agent_response_chars_total', _to_int(librarian_agent.get('response_chars')))
        _add_metric_count(
            metrics,
            'librarian_agent_tool_call_events_total',
            _to_int(librarian_agent.get('tool_call_event_count')),
        )
        _add_metric_count(
            metrics,
            'librarian_agent_validation_tool_calls_total',
            _to_int(librarian_agent.get('validation_tool_call_count')),
        )
        _add_metric_label(metrics, 'librarian_agent_mode_counts', librarian_agent.get('mode'))
        _add_metric_label(metrics, 'librarian_agent_status_counts', librarian_agent.get('status'))
        _add_metric_label(metrics, 'librarian_agent_reason_counts', librarian_agent.get('reason_code'))
        _add_metric_label(metrics, 'librarian_agent_model_status_counts', librarian_agent.get('model_status'))
        _add_metric_label(metrics, 'librarian_agent_validation_status_counts', librarian_agent.get('validation_status'))
        _add_metric_label(metrics, 'librarian_agent_tool_execution_status_counts', librarian_agent.get('tool_execution_status'))
        for tool_name in librarian_agent.get('validation_tool_names') or []:
            _add_metric_label(metrics, 'librarian_agent_tool_name_counts', tool_name)


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
    _add_metric_count(metrics, 'failed_count', _to_int(errors.get('failed_count')))
    _add_metric_count(metrics, 'attempt_failure_count', _to_int(errors.get('attempt_failure_count')))
    _add_metric_count(metrics, 'problem_count', _to_int(errors.get('problem_count')))
    _add_metric_count(metrics, 'skipped_count', _to_int(errors.get('skipped_count')))
    _add_metric_count(metrics, 'disabled_count', _to_int(errors.get('disabled_count')))
    _add_metric_count(metrics, 'not_selected_count', _to_int(errors.get('not_selected_count')))
    _add_metric_count(metrics, 'not_configured_count', _to_int(errors.get('not_configured_count')))
    _add_metric_count(metrics, 'not_applicable_count', _to_int(errors.get('not_applicable_count')))
    _add_metric_count(metrics, 'refused_count', _to_int(errors.get('refused_count')))
    _add_metric_count(metrics, 'non_problem_status_count', _to_int(errors.get('non_problem_status_count')))
    _add_metric_count(metrics, 'fallback_count', _to_int(errors.get('fallback_count')))
    status_counts = _mapping(errors.get('status_counts'))
    for status, count in status_counts.items():
        _add_metric_label(metrics, 'status_counts', status, _to_int(count))
    reason_counts = _mapping(errors.get('reason_code_counts'))
    for reason, count in reason_counts.items():
        _add_metric_label(metrics, 'reason_code_counts', reason, _to_int(count))
    problem_reason_counts = _mapping(errors.get('problem_reason_code_counts'))
    for reason, count in problem_reason_counts.items():
        _add_metric_label(metrics, 'problem_reason_code_counts', reason, _to_int(count))
    non_problem_reason_counts = _mapping(errors.get('non_problem_reason_code_counts'))
    for reason, count in non_problem_reason_counts.items():
        _add_metric_label(metrics, 'non_problem_reason_code_counts', reason, _to_int(count))
    status_schema = _mapping(fact.get('status_schema')) or _mapping(_mapping(fact.get('flags')).get('status_schema'))
    _add_metric_count(metrics, 'v1_event_count', _to_int(status_schema.get('v1_event_count')))
    _add_metric_count(metrics, 'legacy_event_count', _to_int(status_schema.get('legacy_event_count')))
    for schema, count in _mapping(status_schema.get('schema_counts')).items():
        _add_metric_label(metrics, 'status_schema_counts', schema, _to_int(count))
    source_kind = str(status_schema.get('source_kind') or '').strip()
    if source_kind:
        _add_metric_label(metrics, 'status_schema_source_kind_counts', source_kind, 1)


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
    ocr_count = _to_int(documents.get('ocr_applied_count'))
    ocr_sentence = f' {ocr_count} etaient OCRise(s).' if ocr_count else ''
    status = str(documents.get('status') or '').strip().lower()
    read_status = str(documents.get('read_status') or '').strip().lower()
    if status == 'error' or read_status == 'error':
        reason = str(
            documents.get('read_reason_code')
            or documents.get('reason_code')
            or 'active_documents_read_error'
        ).strip()
        return (
            'La lecture des documents actifs de conversation a echoue pour ce tour; '
            f'raison compacte: {reason}.'
        )
    if active_count <= 0:
        return 'Aucun document actif de conversation n est observe sur ce tour.'
    if injected_count and not_injected_count == 0:
        return f'{injected_count} document(s) actif(s) ont ete envoyes entiers au modele.{ocr_sentence}'
    if too_large_count:
        return (
            f'{active_count} document(s) actif(s) etaient presents; '
            f'{too_large_count} etaient trop gros pour ce tour.{ocr_sentence}'
        )
    if not_injected_count:
        return (
            f'{active_count} document(s) actif(s) etaient presents; '
            f'{not_injected_count} n ont pas ete envoyes dans ce tour.{ocr_sentence}'
        )
    return f'{active_count} document(s) actif(s) etaient visibles sur ce tour.{ocr_sentence}'


def _summarize_biblio_turn(fact: Mapping[str, Any]) -> str:
    biblio = _mapping(fact.get('biblio'))
    if not biblio.get('event_present'):
        return 'Aucune consultation Biblio n est observee sur ce tour.'
    if not biblio.get('used'):
        return 'La Biblio etait visible en observabilite mais aucun passage n a ete consulte.'
    status = str(biblio.get('status') or '').strip().lower()
    reason_counts = _mapping(biblio.get('reason_code_counts'))
    preferred_ambiguity_reason = next(
        (
            reason
            for reason in (
                'biblio_context_candidates_ambiguous',
                'selection_gap_too_small',
                'selection_evidence_insufficient',
            )
            if _to_int(reason_counts.get(reason)) > 0
        ),
        None,
    )
    reason = str(
        preferred_ambiguity_reason
        or biblio.get('passage_reason_code')
        or biblio.get('document_reason_code')
        or biblio.get('confidence_reason_code')
        or ''
    ).strip()
    if status == 'ambiguous':
        passage_count = _to_int(biblio.get('passage_count'))
        context_count = _to_int(biblio.get('context_fetch_count'))
        selected_count = _to_int(biblio.get('selected_passage_count'))
        return (
            'La Biblio a ete consultee mais la resolution est ambigue; '
            f'{passage_count} passage(s) candidat(s), {context_count} contexte(s) consulte(s), '
            f'{selected_count} selection certaine; raison compacte: {reason or "unknown"}.'
        )
    if status in {'error', 'not_found'}:
        return f'La Biblio a ete consultee sans passage injectable; raison compacte: {reason or status}.'
    passage_count = _to_int(biblio.get('passage_count'))
    if passage_count > 0:
        return f'La Biblio a ete consultee; {passage_count} passage(s) de bibliotheque sont observes en lane compacte.'
    return 'La Biblio a ete consultee, sans passage injecte dans les signaux compacts.'


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
    problems = (
        _to_int(errors.get('problem_count'))
        or _to_int(errors.get('error_count')) + _to_int(errors.get('failed_count')) + _to_int(errors.get('fallback_count'))
    )
    if problems:
        return f"{problems} probleme(s) compact(s) sont visibles sur ce tour."
    return 'Aucun probleme compact n est visible sur ce tour.'


def _resolve_errors_reason(fact: Mapping[str, Any]) -> str | None:
    errors = _mapping(fact.get('errors'))
    reason_counts = _mapping(errors.get('problem_reason_code_counts'))
    if not reason_counts and (
        _to_int(errors.get('error_count'))
        or _to_int(errors.get('failed_count'))
        or _to_int(errors.get('fallback_count'))
    ):
        reason_counts = _mapping(errors.get('reason_code_counts'))
    return next(iter(reason_counts.keys()), None)


def _resolve_documents_reason(fact: Mapping[str, Any]) -> str | None:
    reason_counts = _mapping(_mapping(fact.get('documents')).get('reason_code_counts'))
    for reason in (
        'active_documents_read_error',
        'active_documents_reader_unavailable',
        'document_too_large_for_turn',
        'document_empty_text',
    ):
        if _to_int(reason_counts.get(reason)) > 0:
            return reason
    return next(iter(reason_counts.keys()), None)


def _resolve_biblio_reason(fact: Mapping[str, Any]) -> str | None:
    reason_counts = _mapping(_mapping(fact.get('biblio')).get('reason_code_counts'))
    for reason in (
        'biblio_context_candidates_ambiguous',
        'selection_gap_too_small',
        'selection_evidence_insufficient',
        'ambiguous_document',
        'ambiguous_locator',
        'document_not_found',
        'locator_not_found',
        'catalogue_unavailable',
        'passage_too_long',
        'biblio_prompt_max_total_chars_reached',
        'biblio_prompt_max_passages_reached',
    ):
        if _to_int(reason_counts.get(reason)) > 0:
            return reason
    return next(iter(reason_counts.keys()), None)
