from __future__ import annotations

import hashlib
from typing import Any, Mapping

from core import assistant_output_contract
from core.web_read_state import (
    READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
    READ_STATE_PAGE_NOT_READ_ERROR,
    READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
    READ_STATE_PAGE_PARTIALLY_READ,
    READ_STATE_PAGE_READ,
)
from core.hermeneutic_node.inputs import time_input
from core.hermeneutic_node.doctrine import epistemic_regime as epistemic_doctrine
from core.hermeneutic_node.doctrine import judgment_posture as judgment_doctrine

_FINAL_JUDGMENT_INSTRUCTIONS = {
    'answer': 'Tu peux produire une reponse substantive normale',
    'clarify': 'Tu ne dois pas repondre directement au fond. Tu dois demander une clarification breve et explicite',
    'suspend': 'Tu ne dois pas produire de reponse substantive normale. Tu dois expliciter la suspension ou la limite presente',
}
_FINAL_OUTPUT_REGIME_INSTRUCTIONS = {
    'meta': "Tu peux expliciter le cadre, la limite ou la clarification de facon reflexive si c'est vraiment necessaire",
    'presence': "La sortie visible doit etre exactement `...`, sans aucun autre caractere ni ajout",
    'simple': 'Reste dans une reprise locale, sobre, dialogique et non meta',
}


def _sha256_12(value: Any) -> str:
    text = str(value or '')
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


_EXPLICIT_IDENTITY_REVELATION_PREFIXES = (
    'je suis ',
    'moi c est ',
    'mon nom est ',
    'my name is ',
    'i am ',
)


def _text(value: Any) -> str:
    return str(value or '').strip()


def _stable_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    seen: set[str] = set()
    ordered: list[str] = []
    for item in value:
        normalized = _text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _effect_mapping(
    value: Any,
    *,
    allowed_effects: tuple[str, ...],
    allowed_sources: tuple[str, ...],
    allowed_reason_codes: tuple[str, ...],
) -> dict[str, str]:
    payload = value if isinstance(value, Mapping) else {}
    if set(payload) != {'effect', 'source', 'reason_code'}:
        return {}
    effect = _text(payload.get('effect'))
    source = _text(payload.get('source'))
    reason_code = _text(payload.get('reason_code'))
    if (
        effect not in allowed_effects
        or source not in allowed_sources
        or reason_code not in allowed_reason_codes
    ):
        return {}
    return {
        'effect': effect,
        'source': source,
        'reason_code': reason_code,
    }


def _looks_like_explicit_identity_revelation(user_msg: str) -> bool:
    normalized = _text(user_msg).lower().replace("'", '’')
    normalized = normalized.replace('’', "'")
    return any(normalized.startswith(prefix.replace('’', "'")) for prefix in _EXPLICIT_IDENTITY_REVELATION_PREFIXES)


def resolve_backend_prompts(prompt_loader_module: Any) -> tuple[str, str]:
    return (
        prompt_loader_module.get_main_system_prompt(),
        prompt_loader_module.get_main_hermeneutical_prompt(),
    )


def build_augmented_system(
    *,
    system_prompt: str,
    hermeneutical_prompt: str,
    config_module: Any,
    identity_module: Any,
    now_iso: str,
) -> tuple[str, list[str]]:
    canonical_time_input = time_input.build_time_input(
        now_utc_iso=now_iso,
        timezone_name=str(config_module.FRIDA_TIMEZONE),
    )
    id_block, identity_ids = identity_module.build_identity_block()
    delta_rule = time_input.build_time_reference_block(canonical_time_input)
    parts = [p for p in [system_prompt, hermeneutical_prompt, delta_rule, id_block] if p]
    return '\n\n'.join(parts), identity_ids


def build_hermeneutic_judgment_block(
    *,
    validated_output: Mapping[str, Any] | None,
) -> str:
    payload = validated_output if isinstance(validated_output, Mapping) else {}
    final_judgment_posture = _text(payload.get('final_judgment_posture'))
    final_output_regime = _text(payload.get('final_output_regime'))
    instruction = _FINAL_JUDGMENT_INSTRUCTIONS.get(final_judgment_posture)
    output_regime_instruction = _FINAL_OUTPUT_REGIME_INSTRUCTIONS.get(final_output_regime)
    directives = _stable_string_list(payload.get('pipeline_directives_final'))
    epistemic_effect = _effect_mapping(
        payload.get('epistemic_effect'),
        allowed_effects=(*epistemic_doctrine.EPISTEMIC_REGIMES, 'unknown'),
        allowed_sources=epistemic_doctrine.EPISTEMIC_EFFECT_SOURCES,
        allowed_reason_codes=epistemic_doctrine.EPISTEMIC_EFFECT_REASON_CODES,
    )
    enunciation_directive = _effect_mapping(
        payload.get('enunciation_directive'),
        allowed_effects=judgment_doctrine.ENUNCIATION_EFFECTS,
        allowed_sources=judgment_doctrine.ENUNCIATION_SOURCES,
        allowed_reason_codes=judgment_doctrine.ENUNCIATION_REASON_CODES,
    )
    if not instruction or not directives or not epistemic_effect or not enunciation_directive:
        return ''

    lines = [
        '[JUGEMENT HERMENEUTIQUE]',
        f'Posture finale validee: {final_judgment_posture}.',
    ]
    if final_output_regime:
        lines.append(f'Regime final valide: {final_output_regime}.')
    lines.append(f'Consigne hermeneutique: {instruction}.')
    if output_regime_instruction:
        lines.append(f'Consigne de regime: {output_regime_instruction}.')
    lines.append(
        'Effet epistemique: '
        f"{epistemic_effect['effect']} "
        f"(source={epistemic_effect['source']}; reason_code={epistemic_effect['reason_code']})."
    )
    lines.append(
        "Effet d'enonciation: "
        f"{enunciation_directive['effect']} "
        f"(source={enunciation_directive['source']}; reason_code={enunciation_directive['reason_code']})."
    )
    if enunciation_directive['effect'] == 'delicate_expression':
        lines.append(
            "Consigne d'enonciation: adapte seulement la delicatesse, le rythme ou la prudence de formulation; "
            "ne diminue ni la certitude, ni le regime de preuve, ni la posture d'incertitude."
        )
    lines.append(f"Directives finales actives: {', '.join(directives)}.")
    return '\n'.join(lines)


def inject_hermeneutic_judgment_block(
    augmented_system: str,
    hermeneutic_judgment_block: str,
) -> str:
    block = _text(hermeneutic_judgment_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def build_direct_identity_revelation_guard_block(
    *,
    user_msg: str,
    user_turn_input: Mapping[str, Any] | None,
    user_turn_signals: Mapping[str, Any] | None,
) -> str:
    turn_payload = user_turn_input if isinstance(user_turn_input, Mapping) else {}
    signal_payload = user_turn_signals if isinstance(user_turn_signals, Mapping) else {}
    gesture = _text(turn_payload.get('geste_dialogique_dominant'))
    if gesture != 'exposition':
        return ''
    if not _looks_like_explicit_identity_revelation(user_msg):
        return ''
    if bool(signal_payload.get('ambiguity_present')) or bool(signal_payload.get('underdetermination_present')):
        return ''
    if _stable_string_list(signal_payload.get('active_signal_families')):
        return ''

    return (
        '[GARDE DE REVELATION IDENTITAIRE]\n'
        "Le tour utilisateur contient une revelation identitaire explicite et non ambigue.\n"
        "Traite cette revelation comme operative des maintenant.\n"
        "N'ajoute pas de question de clarification bureaucratique ou de recadrage si l'utilisateur n'a rien demande d'autre.\n"
        "Accuse reception simplement, sans requalifier le tour en demande de cadrage."
    )


def inject_direct_identity_revelation_guard_block(
    augmented_system: str,
    direct_identity_revelation_guard_block: str,
) -> str:
    block = _text(direct_identity_revelation_guard_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def build_voice_transcription_guard_block(
    *,
    input_mode: Any,
) -> str:
    if _text(input_mode) != 'voice':
        return ''

    return (
        '[GARDE DE LECTURE VOCALE]\n'
        "Le tour utilisateur courant provient d'une transcription vocale.\n"
        "Lis ce tour avec une tolerance locale aux hesitations, repetitions, reprises, ponctuation faible ou relachements de formulation.\n"
        "N'interprete pas a lui seul ces scories d'oralite comme un manque de rigueur, de clarte ou de densite.\n"
        "Un tour vocal peut rester phatique, exploratoire ou approximatif sans etre vide de sens.\n"
        "Ce signal reste faible et local au tour courant: le transcript peut aussi avoir ete retouche au clavier et rester partiellement mixte."
    )


def inject_voice_transcription_guard_block(
    augmented_system: str,
    voice_transcription_guard_block: str,
) -> str:
    block = _text(voice_transcription_guard_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def build_plain_text_guard_block(
    *,
    user_msg: str,
    output_policy: assistant_output_contract.AssistantOutputPolicy | None = None,
) -> str:
    policy = output_policy or assistant_output_contract.resolve_assistant_output_policy(user_msg)
    return assistant_output_contract.build_plain_text_guard_block(policy)


def inject_plain_text_guard_block(
    augmented_system: str,
    plain_text_guard_block: str,
) -> str:
    block = _text(plain_text_guard_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def build_web_reading_guard_block(
    *,
    web_input: Mapping[str, Any] | None,
) -> str:
    payload = web_input if isinstance(web_input, Mapping) else {}
    read_state = _text(payload.get('read_state'))
    if not read_state:
        return ''

    explicit_url = _text(payload.get('explicit_url'))
    lines = ['[GARDE DE LECTURE WEB]']
    if explicit_url:
        lines.append(f'URL cible: {explicit_url}')
    lines.append(f'read_state: {read_state}.')

    if read_state == READ_STATE_PAGE_READ:
        lines.append("La lecture directe de cette page est soutenue par le runtime.")
        lines.append("Tu peux parler de lecture directe si tu restes fidele au contenu reellement injecte.")
    elif read_state == READ_STATE_PAGE_PARTIALLY_READ:
        lines.append("La lecture directe est seulement partielle: le contenu injecte a ete tronque.")
        lines.append("Tu peux parler d'une lecture partielle ou d'un extrait tronque.")
        lines.append("N'affirme pas une lecture integrale, exhaustive ou detaillee de toute la page.")
    elif read_state == READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK:
        lines.append("La page cible n'a pas ete lue directement. La reponse repose au mieux sur un snippet ou un extrait fallback.")
        lines.append('Interdit: "je l\'ai sous les yeux", "j\'ai lu l\'article", "dans le texte tu dis ...".')
        lines.append('Autorise seulement des formulations comme: "j\'ai trouve des elements via les resultats", "je n\'ai qu\'un extrait/snippet", "je n\'ai pas acces au texte complet".')
    elif read_state == READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY:
        lines.append("La lecture directe de la page a echoue avec un crawl vide.")
        lines.append('Interdit: "je l\'ai sous les yeux", "j\'ai lu l\'article", "dans le texte tu dis ...".')
        lines.append("Tu dois assumer explicitement que tu n'as pas pu lire directement la page.")
    elif read_state == READ_STATE_PAGE_NOT_READ_ERROR:
        lines.append("La lecture directe de la page a echoue a cause d'une erreur de crawl.")
        lines.append('Interdit: "je l\'ai sous les yeux", "j\'ai lu l\'article", "dans le texte tu dis ...".')
        lines.append("Tu dois assumer explicitement que tu n'as pas pu lire directement la page.")
    else:
        return ''

    return '\n'.join(lines)


def inject_web_reading_guard_block(
    augmented_system: str,
    web_reading_guard_block: str,
) -> str:
    block = _text(web_reading_guard_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def build_web_evidence_guard_block(
    *,
    web_input: Mapping[str, Any] | None,
) -> str:
    payload = web_input if isinstance(web_input, Mapping) else {}
    evidence = payload.get('web_evidence')
    evidence_payload = evidence if isinstance(evidence, Mapping) else {}
    status = _text(evidence_payload.get('web_evidence_status'))
    if not status or status in {'not_applicable', 'sufficient'}:
        return ''
    reason_codes = _stable_string_list(evidence_payload.get('web_evidence_reason_codes'))
    guidance_codes = _stable_string_list(evidence_payload.get('web_evidence_guidance_codes'))
    if not reason_codes and not bool(evidence_payload.get('web_evidence_requires_caveat', False)):
        return ''

    lines = [
        '[GARDE DE PREUVE WEB]',
        f'evidence_status: {status}.',
    ]
    if reason_codes:
        lines.append(f"reason_codes: {', '.join(reason_codes)}.")
    if guidance_codes:
        lines.append(f"guidance_codes: {', '.join(guidance_codes)}.")
    lines.extend(
        [
            "Ce signal est un contrat de prudence, pas une reponse d'echec prefabriquee.",
            "Tu peux repondre avec le materiau disponible, mais tu dois formuler naturellement les limites qui touchent la conclusion.",
            "N'invente pas une solidite documentaire que le runtime web ne montre pas.",
            "Ne transforme pas ce signal en refus automatique ou en mutisme.",
            "Tu peux proposer une reformulation ou une relance si cela aide vraiment.",
            "Ne demande une URL que si elle est vraiment pertinente; ce n'est pas le reflexe par defaut.",
            "Aucun fallback externe OpenRouter, Exa ou Parallel n'a ete utilise.",
        ]
    )
    return '\n'.join(lines)


def inject_web_evidence_guard_block(
    augmented_system: str,
    web_evidence_guard_block: str,
) -> str:
    block = _text(web_evidence_guard_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def apply_augmented_system(conversation: dict[str, Any], augmented_system: str) -> None:
    if conversation['messages'] and conversation['messages'][0]['role'] == 'system':
        conversation['messages'][0]['content'] = augmented_system


def has_usable_web_context(
    web_context_payload: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(web_context_payload, Mapping):
        return False
    activation_mode = str(web_context_payload.get('activation_mode') or '').strip()
    status = str(web_context_payload.get('status') or '').strip()
    context_block = str(web_context_payload.get('context_block') or '').strip()
    context_injected = web_context_payload.get('context_injected')
    return (
        activation_mode in {'manual', 'auto'}
        and status == 'ok'
        and bool(context_block)
        and (context_injected is None or context_injected is True)
    )


def inject_web_context(
    prompt_messages: list[dict[str, Any]],
    *,
    user_msg: str,
    conversation_id: str,
    web_search_module: Any,
    admin_logs_module: Any,
    web_context_payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if web_context_payload is None:
        build_context_payload = getattr(web_search_module, 'build_context_payload', None)
        if callable(build_context_payload):
            web_context_payload = build_context_payload(user_msg)
        else:
            ctx, search_query, n_results = web_search_module.build_context(user_msg)
            web_context_payload = {
                'enabled': True,
                'status': 'ok' if ctx else 'skipped',
                'activation_mode': 'manual',
                'reason_code': None if ctx else 'no_data',
                'original_user_message': user_msg,
                'query': search_query,
                'results_count': n_results,
                'runtime': {},
                'sources': [],
                'context_block': ctx,
            }

    injection_result = dict(web_context_payload)
    injection_result['main_prompt_context_injected'] = False
    if not has_usable_web_context(web_context_payload):
        return injection_result
    ctx = str(web_context_payload.get('context_block') or '')

    for index in range(len(prompt_messages) - 1, -1, -1):
        if prompt_messages[index].get('role') == 'user':
            prompt_messages[index] = {
                'role': 'user',
                'content': ctx + '\n\nQuestion : ' + prompt_messages[index]['content'],
            }
            injection_result['main_prompt_context_injected'] = True
            break
    if not injection_result['main_prompt_context_injected']:
        return injection_result

    query_text = str(web_context_payload.get('query') or '')
    original_text = str(web_context_payload.get('original_user_message') or user_msg or '')
    admin_logs_module.log_event(
        'web_search',
        conversation_id=conversation_id,
        query_present=bool(query_text.strip()),
        query_chars=len(query_text),
        query_sha256_12=_sha256_12(query_text),
        original_user_message_chars=len(original_text),
        original_user_message_sha256_12=_sha256_12(original_text),
        search_profile=str(web_context_payload.get('search_profile') or ''),
        query_plan_kind=str(web_context_payload.get('query_plan_kind') or ''),
        query_count=web_context_payload.get('query_count'),
        secondary_query_count=web_context_payload.get('secondary_query_count'),
        deduped_result_count=web_context_payload.get('deduped_result_count'),
        searxng_profile_params_kind=str(web_context_payload.get('searxng_profile_params_kind') or ''),
        searxng_profile_params_policy=str(web_context_payload.get('searxng_profile_params_policy') or ''),
        searxng_categories=list(web_context_payload.get('searxng_categories') or []),
        searxng_engines=list(web_context_payload.get('searxng_engines') or []),
        searxng_time_range=str(web_context_payload.get('searxng_time_range') or ''),
        searxng_language=str(web_context_payload.get('searxng_language') or ''),
        searxng_safesearch=str(web_context_payload.get('searxng_safesearch') or ''),
        web_discovery_provider=str(web_context_payload.get('web_discovery_provider') or ''),
        web_discovery_provider_requested=str(web_context_payload.get('web_discovery_provider_requested') or ''),
        web_discovery_provider_effective=str(web_context_payload.get('web_discovery_provider_effective') or ''),
        web_discovery_external_used=bool(web_context_payload.get('web_discovery_external_used', False)),
        web_discovery_external_provider=str(web_context_payload.get('web_discovery_external_provider') or ''),
        web_discovery_external_error_kind=str(web_context_payload.get('web_discovery_external_error_kind') or ''),
        web_discovery_reason_codes=list(web_context_payload.get('web_discovery_reason_codes') or []),
        rerank_applied=bool(web_context_payload.get('rerank_applied', False)),
        rerank_policy=str(web_context_payload.get('rerank_policy') or ''),
        rerank_input_count=web_context_payload.get('rerank_input_count'),
        rerank_output_count=web_context_payload.get('rerank_output_count'),
        rerank_profile=str(web_context_payload.get('rerank_profile') or ''),
        rerank_top_domains_before=list(web_context_payload.get('rerank_top_domains_before') or []),
        rerank_top_domains_after=list(web_context_payload.get('rerank_top_domains_after') or []),
        rerank_reason_counts=dict(web_context_payload.get('rerank_reason_counts') or {}),
        rerank_promoted_count=web_context_payload.get('rerank_promoted_count'),
        rerank_downranked_count=web_context_payload.get('rerank_downranked_count'),
        results=web_context_payload.get('results_count'),
    )
    return injection_result
