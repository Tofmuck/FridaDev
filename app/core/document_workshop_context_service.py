"""M1 scope authority: local inventories only; no source extraction or DAV."""
from uuid import UUID

from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import validate_document_path


def _id(value):
    if type(value) is not str:
        return None
    try:
        return str(UUID(value))
    except ValueError:
        return None


def _failure(reason, status):
    return {'ok': False, 'reason_code': reason, 'error': 'Contexte documentaire indisponible.'}, status


def _scope(fields, *, conversations, folders, files):
    conversation = conversations.get_conversation_summary(fields['conversation_id'])
    folder = folders.get_workspace_folder(fields['workspace_folder_id'])
    if not conversation or conversation.get('deleted_at') or not folder or folder.get('deleted_at'):
        raise DocumentWorkshopError('document_context_resource_missing')
    if str(conversation.get('id')) != fields['conversation_id'] or str(folder.get('id')) != fields['workspace_folder_id'] \
            or str(conversation.get('workspace_folder_id')) != fields['workspace_folder_id']:
        raise DocumentWorkshopError('document_context_scope_mismatch')
    target_id = fields.get('target_file_id')
    if not target_id:
        return dict(target_file_id=None, target_relative_path=None, target_document_ref=None, target_remote_identity=None)
    target = files.get_workspace_file_storage_row(fields['workspace_folder_id'], target_id)
    if not target or target.get('deleted_at'):
        raise DocumentWorkshopError('document_context_target_missing')
    extension = target.get('source_extension')
    if str(target.get('id')) != target_id or str(target.get('workspace_folder_id')) != fields['workspace_folder_id'] \
            or target.get('status') != 'active' or target.get('content_kind') != 'document' \
            or target.get('media_kind') != 'text' or extension not in ('.md', '.docx'):
        raise DocumentWorkshopError('document_context_target_ineligible')
    link = files.get_nextcloud_link(target_id, fail_closed=True, preserve_target_identity=True)
    if not link or str(link.get('workspace_folder_id')) != fields['workspace_folder_id'] \
            or link.get('nextcloud_sync_state') != 'linked' or type(link.get('nextcloud_document_ref')) is not str \
            or not link['nextcloud_document_ref']:
        raise DocumentWorkshopError('document_context_target_ineligible')
    # Raw verified inventory metadata, never display-name sanitizer or frontend URL.
    relative_path = link.get('nextcloud_relative_path')
    if relative_path is None:
        name = link.get('nextcloud_target_name')
        if type(name) is not str or '/' in name:
            raise DocumentWorkshopError('document_context_target_ineligible')
        relative_path = 'Documents/' + name
    path = validate_document_path(relative_path, format='markdown' if extension == '.md' else 'docx')
    identity = None
    if link.get('nextcloud_file_id') is not None or link.get('nextcloud_scope_key') is not None:
        from .workspace_document_adoption_store import remote_identity
        identity = remote_identity(link.get('nextcloud_scope_key'), link.get('nextcloud_file_id'))
    return dict(target_file_id=target_id, target_relative_path=path.relative_path,
                target_document_ref=link['nextcloud_document_ref'], target_remote_identity=identity)


def _public(record):
    return {key: record[key] for key in ('id', 'conversation_id', 'workspace_folder_id',
            'target_file_id', 'target_relative_path', 'state', 'created_at')} | {'capabilities': {'prepare': False}}


def _scope_error(exc):
    reason = exc.reason_code
    status = 404 if reason.endswith('_missing') else 409
    if reason.startswith('document_path_') or reason.endswith('_ineligible'):
        status = 422
    return _failure(reason, status)


def create_context(data, *, store, conversations, folders, files):
    if type(data) is not dict or set(data) - {'conversation_id', 'workspace_folder_id', 'target_file_id'}:
        return _failure('document_context_request_invalid', 400)
    fields = {key: _id(data.get(key)) for key in ('conversation_id', 'workspace_folder_id')}
    target = data.get('target_file_id')
    if not all(fields.values()) or (target is not None and not _id(target)):
        return _failure('document_context_request_invalid', 400)
    fields['target_file_id'] = _id(target) if target is not None else None
    try:
        scope = _scope(fields, conversations=conversations, folders=folders, files=files)
        record = store.create_context(**(fields | scope))
        if not record:
            return _failure('document_context_scope_changed', 409)
        return {'ok': True, 'context': _public(record)}, 201
    except DocumentWorkshopError as exc:
        return _scope_error(exc)
    except Exception:
        return _failure('document_context_storage_unavailable', 503)


def get_context(context_id, *, store, conversations, folders, files):
    context_id = _id(context_id)
    if not context_id:
        return _failure('document_context_request_invalid', 400)
    try:
        record = store.get_context(context_id)
        if not record:
            return _failure('document_context_missing', 404)
        scope = _scope(record, conversations=conversations, folders=folders, files=files)
        if record['state'] != 'editing' or any(scope[key] != record.get(key) for key in scope):
            return _failure('document_context_scope_changed', 409)
        return {'ok': True, 'context': _public(record)}, 200
    except DocumentWorkshopError as exc:
        return _scope_error(exc)
    except Exception:
        return _failure('document_context_storage_unavailable', 503)
