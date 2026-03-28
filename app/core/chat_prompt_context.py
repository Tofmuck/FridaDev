from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo


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
    tz_paris = ZoneInfo(config_module.FRIDA_TIMEZONE)
    now_raw = datetime.fromisoformat(str(now_iso).replace("Z", "+00:00"))
    if now_raw.tzinfo is None:
        now_raw = now_raw.replace(tzinfo=timezone.utc)
    now_paris = now_raw.astimezone(tz_paris)
    now_human = now_paris.strftime('%A %d %B %Y à %H:%M')
    now_canonical = now_paris.isoformat(timespec='seconds')
    id_block, identity_ids = identity_module.build_identity_block()
    delta_rule = (
        '[RÉFÉRENCE TEMPORELLE]\n'
        f"NOW: {now_canonical}\n"
        f"TIMEZONE: {config_module.FRIDA_TIMEZONE}\n\n"
        f"Nous sommes le {now_human}. C'est ton 'maintenant'.\n"
        "Les messages ci-dessous sont horodatés relativement à ce maintenant (ex : 'il y a 2 jours').\n"
        'Les marqueurs [— silence de X —] indiquent une interruption de la conversation. '
        "Tu n'as pas à les mentionner, mais tu peux en tenir compte dans ton ton si c'est pertinent.\n"
        "Ne mentionne jamais spontanément la date ou l'heure dans tes réponses, "
        'sauf si on te le demande explicitement.'
    )
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
) -> None:
    ctx, search_query, n_results = web_search_module.build_context(user_msg)
    if not ctx:
        return

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
        query=search_query,
        original=user_msg,
        results=n_results,
    )
