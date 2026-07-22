from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Tuple

from core import prompt_loader


def list_conversations(
    args: Mapping[str, Any],
    *,
    conv_store_module: Any,
) -> Dict[str, Any]:
    raw_limit = str(args.get('limit', '100') or '100').strip()
    raw_offset = str(args.get('offset', '0') or '0').strip()
    raw_include_deleted = str(args.get('include_deleted', '') or '').strip().lower()

    try:
        limit = int(raw_limit)
    except ValueError:
        limit = 100

    try:
        offset = int(raw_offset)
    except ValueError:
        offset = 0

    include_deleted = raw_include_deleted in {'1', 'true', 'yes', 'on'}

    payload = conv_store_module.list_conversations(
        limit=limit,
        offset=offset,
        include_deleted=include_deleted,
    )
    return {'ok': True, **payload}


def create_conversation(
    data: Mapping[str, Any],
    *,
    conv_store_module: Any,
    get_main_system_prompt: Callable[[], str],
) -> Tuple[Dict[str, Any], int]:
    title = str(data.get('title') or '').strip()
    system_prompt = get_main_system_prompt()
    try:
        system_prompt = prompt_loader.require_usable_prompt_text(
            system_prompt,
            prompt_id='main_system',
        )
    except prompt_loader.RequiredPromptUnavailable as exc:
        return (
            {
                'ok': False,
                'error': 'service temporairement indisponible',
                'reason_code': 'critical_prompt_unavailable',
                'prompt_id': exc.prompt_id,
            },
            503,
        )

    conversation = conv_store_module.new_conversation(system_prompt, title=title)
    conv_store_module.save_conversation(conversation)

    summary = conv_store_module.get_conversation_summary(conversation['id']) or {
        'id': conversation['id'],
        'title': conversation.get('title') or 'Nouvelle conversation',
        'created_at': conversation.get('created_at'),
        'updated_at': conversation.get('updated_at'),
        'message_count': 0,
        'last_message_preview': '',
        'deleted_at': None,
    }
    return {'ok': True, 'conversation_id': conversation['id'], 'conversation': summary}, 201


def get_conversation_messages(
    conversation_id: str,
    *,
    conv_store_module: Any,
) -> Tuple[Dict[str, Any], int]:
    conv_id = conv_store_module.normalize_conversation_id(conversation_id)
    if not conv_id:
        return {'ok': False, 'error': 'conversation_id invalide'}, 400

    conversation = conv_store_module.read_conversation(conv_id, '')
    if not conversation:
        return {'ok': False, 'error': 'conversation introuvable'}, 404

    summary = conv_store_module.get_conversation_summary(conv_id, include_deleted=True)
    if summary is None:
        summary = {
            'title': conversation.get('title') or 'Nouvelle conversation',
            'created_at': conversation.get('created_at'),
            'updated_at': conversation.get('updated_at'),
            'message_count': sum(
                1
                for msg in conversation.get('messages', [])
                if str(msg.get('role') or '').strip() in {'user', 'assistant'}
            ),
            'last_message_preview': '',
            'deleted_at': None,
        }

    return (
        {
            'ok': True,
            'conversation_id': conv_id,
            'title': summary.get('title') or 'Nouvelle conversation',
            'created_at': summary.get('created_at') or conversation.get('created_at'),
            'updated_at': summary.get('updated_at') or conversation.get('updated_at'),
            'deleted_at': summary.get('deleted_at'),
            'messages': conversation.get('messages', []),
        },
        200,
    )


def patch_conversation(
    conversation_id: str,
    data: Mapping[str, Any],
    *,
    conv_store_module: Any,
    workspace_folders_module: Any | None = None,
    workspace_file_selections_module: Any | None = None,
) -> Tuple[Dict[str, Any], int]:
    conv_id = conv_store_module.normalize_conversation_id(conversation_id)
    if not conv_id:
        return {'ok': False, 'error': 'conversation_id invalide'}, 400

    has_title = 'title' in data
    has_workspace_folder = 'workspace_folder_id' in data
    if not has_title and not has_workspace_folder:
        return {'ok': False, 'error': 'champ modifiable requis'}, 400

    summary = None
    if has_title:
        title = str(data.get('title') or '').strip()
        if not title:
            return {'ok': False, 'error': 'title requis'}, 400
        summary = conv_store_module.rename_conversation(conv_id, title)
        if summary is None:
            return {'ok': False, 'error': 'conversation introuvable'}, 404

    if has_workspace_folder:
        if workspace_folders_module is None:
            return {'ok': False, 'error': 'workspace folders indisponibles'}, 500
        raw_folder_id = data.get('workspace_folder_id')
        folder_id = None
        if raw_folder_id not in (None, ''):
            folder_id = workspace_folders_module.normalize_workspace_folder_id(str(raw_folder_id))
            if not folder_id:
                return {'ok': False, 'error': 'workspace_folder_id invalide'}, 400
            if workspace_folders_module.get_workspace_folder(folder_id) is None:
                return {'ok': False, 'error': 'répertoire introuvable'}, 404
        summary = conv_store_module.set_conversation_workspace_folder(conv_id, folder_id)
        if summary is None:
            return {'ok': False, 'error': 'conversation introuvable'}, 404
        clear_stale = getattr(workspace_file_selections_module, 'clear_stale_selections_for_conversation', None)
        if callable(clear_stale):
            clear_stale(conv_id, workspace_folder_id=summary.get('workspace_folder_id'))

    return {'ok': True, 'conversation': summary}, 200


def delete_conversation(
    conversation_id: str,
    *,
    conv_store_module: Any,
) -> Tuple[Dict[str, Any], int]:
    conv_id = conv_store_module.normalize_conversation_id(conversation_id)
    if not conv_id:
        return {'ok': False, 'error': 'conversation_id invalide'}, 400

    if not conv_store_module.soft_delete_conversation(conv_id):
        return {'ok': False, 'error': 'conversation introuvable'}, 404
    return {'ok': True, 'conversation_id': conv_id}, 200
