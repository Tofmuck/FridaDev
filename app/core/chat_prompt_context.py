from __future__ import annotations

from typing import Any, Mapping

from core.hermeneutic_node.inputs import time_input


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
