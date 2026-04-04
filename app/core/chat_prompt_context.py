from __future__ import annotations

from typing import Any, Mapping

from core.hermeneutic_node.inputs import time_input

_FINAL_JUDGMENT_INSTRUCTIONS = {
    'answer': 'Tu peux produire une reponse substantive normale',
    'clarify': 'Tu ne dois pas repondre directement au fond. Tu dois demander une clarification breve et explicite',
    'suspend': 'Tu ne dois pas produire de reponse substantive normale. Tu dois expliciter la suspension ou la limite presente',
}
_READ_STATE_PAGE_READ = 'page_read'
_READ_STATE_PAGE_PARTIALLY_READ = 'page_partially_read'
_READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY = 'page_not_read_crawl_empty'
_READ_STATE_PAGE_NOT_READ_ERROR = 'page_not_read_error'
_READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK = 'page_not_read_snippet_fallback'
_LIST_REQUEST_MARKERS = (
    'liste',
    'list',
    'plan',
    'etape',
    'étape',
    'etapes',
    'étapes',
    'points',
    'puces',
    'bullet',
)
_CODE_REQUEST_MARKERS = (
    'code',
    'python',
    'javascript',
    'typescript',
    'js',
    'sql',
    'bash',
    'shell',
    'regex',
    'json',
    'yaml',
    'xml',
    'html',
    'css',
    'script',
    'fonction',
    'snippet',
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


def _normalized_lower_text(value: Any) -> str:
    return _text(value).lower()


def _contains_any_marker(value: Any, markers: tuple[str, ...]) -> bool:
    haystack = _normalized_lower_text(value)
    return any(marker in haystack for marker in markers)


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
    instruction = _FINAL_JUDGMENT_INSTRUCTIONS.get(final_judgment_posture)
    directives = _stable_string_list(payload.get('pipeline_directives_final'))
    if not instruction or not directives:
        return ''

    return (
        '[JUGEMENT HERMENEUTIQUE]\n'
        f'Posture finale validee: {final_judgment_posture}.\n'
        f'Consigne hermeneutique: {instruction}.\n'
        f"Directives finales actives: {', '.join(directives)}."
    )


def inject_hermeneutic_judgment_block(
    augmented_system: str,
    hermeneutic_judgment_block: str,
) -> str:
    block = _text(hermeneutic_judgment_block)
    if not block:
        return str(augmented_system or '')
    return '\n\n'.join(part for part in [str(augmented_system or ''), block] if part)


def build_plain_text_guard_block(
    *,
    user_msg: str,
) -> str:
    wants_list = _contains_any_marker(user_msg, _LIST_REQUEST_MARKERS)
    wants_code = _contains_any_marker(user_msg, _CODE_REQUEST_MARKERS)

    lines = [
        '[CONTRAT TEXTE BRUT]',
        'Réponds pour cette surface en texte brut strict, lisible sans rendu Markdown.',
        'Interdit: titres Markdown, gras/italique Markdown, règles horizontales, blockquotes, tableaux Markdown.',
    ]
    if wants_list:
        lines.append(
            "L'utilisateur demande explicitement un plan, des étapes ou une liste: une structure textuelle minimale est autorisée, sans décoration Markdown."
        )
    else:
        lines.append(
            "Pour ce tour, n'utilise ni puces, ni listes numérotées, ni lignes commençant par `-`, `*`, `•`, `1)` ou `1.`."
        )
        lines.append('Réponds en courts paragraphes continus.')

    if wants_code:
        lines.append("L'utilisateur demande explicitement du code: un bloc de code est autorisé seulement si c'est vraiment utile.")
    else:
        lines.append("Pour ce tour, n'utilise pas de code fences ni de blocs de code.")

    return '\n'.join(lines)


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

    if read_state == _READ_STATE_PAGE_READ:
        lines.append("La lecture directe de cette page est soutenue par le runtime.")
        lines.append("Tu peux parler de lecture directe si tu restes fidele au contenu reellement injecte.")
    elif read_state == _READ_STATE_PAGE_PARTIALLY_READ:
        lines.append("La lecture directe est seulement partielle: le contenu injecte a ete tronque.")
        lines.append("Tu peux parler d'une lecture partielle ou d'un extrait tronque.")
        lines.append("N'affirme pas une lecture integrale, exhaustive ou detaillee de toute la page.")
    elif read_state == _READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK:
        lines.append("La page cible n'a pas ete lue directement. La reponse repose au mieux sur un snippet ou un extrait fallback.")
        lines.append('Interdit: "je l\'ai sous les yeux", "j\'ai lu l\'article", "dans le texte tu dis ...".')
        lines.append('Autorise seulement des formulations comme: "j\'ai trouve des elements via les resultats", "je n\'ai qu\'un extrait/snippet", "je n\'ai pas acces au texte complet".')
    elif read_state == _READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY:
        lines.append("La lecture directe de la page a echoue avec un crawl vide.")
        lines.append('Interdit: "je l\'ai sous les yeux", "j\'ai lu l\'article", "dans le texte tu dis ...".')
        lines.append("Tu dois assumer explicitement que tu n'as pas pu lire directement la page.")
    elif read_state == _READ_STATE_PAGE_NOT_READ_ERROR:
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


def apply_augmented_system(conversation: dict[str, Any], augmented_system: str) -> None:
    if conversation['messages'] and conversation['messages'][0]['role'] == 'system':
        conversation['messages'][0]['content'] = augmented_system


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
                'reason_code': None if ctx else 'no_data',
                'original_user_message': user_msg,
                'query': search_query,
                'results_count': n_results,
                'runtime': {},
                'sources': [],
                'context_block': ctx,
            }

    ctx = str(web_context_payload.get('context_block') or '')
    if not ctx:
        return web_context_payload

    for index in range(len(prompt_messages) - 1, -1, -1):
        if prompt_messages[index].get('role') == 'user':
            prompt_messages[index] = {
                'role': 'user',
                'content': ctx + '\n\nQuestion : ' + prompt_messages[index]['content'],
            }
            break

    admin_logs_module.log_event(
        'web_search',
        conversation_id=conversation_id,
        query=web_context_payload.get('query'),
        original=web_context_payload.get('original_user_message') or user_msg,
        results=web_context_payload.get('results_count'),
    )
    return web_context_payload
