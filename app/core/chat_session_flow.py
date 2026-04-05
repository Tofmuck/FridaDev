from __future__ import annotations

from typing import Any, Mapping


ChatError = tuple[dict[str, Any], int]


def resolve_chat_session(
    data: Mapping[str, Any],
    *,
    system_prompt: str,
    conv_store_module: Any,
    memory_store_module: Any,
    logger: Any,
) -> tuple[dict[str, Any] | None, ChatError | None]:
    user_msg = (data.get('message') or '').strip()
    conversation_id_raw = data.get('conversation_id')
    stream_req = bool(data.get('stream'))
    web_search_on = bool(data.get('web_search'))

    if not user_msg:
        return None, ({'ok': False, 'error': 'message vide'}, 400)

    conversation_id = conv_store_module.normalize_conversation_id(conversation_id_raw)
    if conversation_id:
        conversation = conv_store_module.load_conversation(conversation_id, system_prompt)
        if not conversation:
            return None, ({'ok': False, 'error': 'conversation introuvable'}, 404)
    else:
        if conversation_id_raw:
            logger.info('conv_id_invalid raw=%s', conversation_id_raw)
        conversation = conv_store_module.new_conversation(system_prompt)
        conv_store_module.save_conversation(conversation)
        logger.info(
            'conv_created id=%s path=%s',
            conversation['id'],
            conv_store_module.conversation_path(conversation['id']),
        )
        memory_store_module.decay_identities()

    return (
        {
            'user_msg': user_msg,
            'conversation': conversation,
            'stream_req': stream_req,
            'web_search_on': web_search_on,
        },
        None,
    )


def conversation_headers(conversation: Mapping[str, Any], updated_at: str) -> dict[str, str]:
    return {
        'X-Conversation-Id': str(conversation['id']),
        'X-Conversation-Created-At': str(conversation['created_at']),
        'X-Conversation-Updated-At': str(updated_at),
    }


def conversation_stream_headers(conversation: Mapping[str, Any]) -> dict[str, str]:
    return {
        'X-Conversation-Id': str(conversation['id']),
        'X-Conversation-Created-At': str(conversation['created_at']),
    }
