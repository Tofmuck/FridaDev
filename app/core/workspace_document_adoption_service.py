"""Explicit M2 list/adopt actions, bound to an existing M1 editing context."""
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import PurePosixPath
from threading import Lock
from uuid import uuid4

from . import document_workshop_context_service as contexts
from . import workspace_document_adoption_store as adoption
from . import workspace_folder_documents
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
from .workspace_document_source_extraction import extract_complete_source


@dataclass(frozen=True, repr=False)
class _Reference:
    folder_id: str
    scope_key: str
    resource: object


class RemoteReferences:
    """Bounded process-local opaque observations; restart/eviction closes access."""
    def __init__(self):
        self._items = OrderedDict()
        self._lock = Lock()

    def put(self, folder_id, scope_key, resource):
        reference = str(uuid4())
        with self._lock:
            self._items[reference] = _Reference(folder_id, scope_key, resource)
            while len(self._items) > 4096:
                self._items.popitem(last=False)
        return reference

    def resolve(self, reference, folder_id, scope_key):
        if not contexts._id(reference):
            raise DocumentWorkshopError('document_reference_invalid')
        with self._lock:
            record = self._items.get(reference)
        if record is None or record.folder_id != folder_id or record.scope_key != scope_key:
            raise DocumentWorkshopError('document_reference_invalid')
        return record.resource


_references = RemoteReferences()


def failure(reason, status=None):
    if status is None:
        if reason in {'document_request_invalid'}:
            status = 400
        elif reason.endswith('_missing'):
            status = 404
        elif reason in {'document_local_collision','document_remote_changed','document_reference_invalid','document_context_scope_changed','document_context_scope_mismatch'}:
            status = 409
        elif reason.endswith('_limit'):
            status = 413
        elif 'unavailable' in reason or reason == 'document_adoption_commit_unknown':
            status = 503
        else:
            status = 422
    return {'ok': False, 'category': 'collision' if reason == 'document_local_collision' else 'incompatible',
            'reason_code': reason, 'error': 'Opération documentaire indisponible.'}, status


def _scope(folder_id, data, allowed, *, store, conversations, folders, files):
    if (not contexts._id(folder_id) or type(data) is not dict or set(data) - allowed
            or not contexts._id(data.get('context_id'))):
        raise DocumentWorkshopError('document_request_invalid')
    payload, status = contexts.get_context(data['context_id'], store=store, conversations=conversations, folders=folders, files=files)
    if status != 200:
        raise DocumentWorkshopError(payload['reason_code'])
    if payload['context']['workspace_folder_id'] != folder_id:
        raise DocumentWorkshopError('document_context_scope_mismatch')
    folder = folders.get_workspace_folder(folder_id)
    if (not folder or folder.get('deleted_at') or folder.get('nextcloud_sync_state') != 'linked'
            or type(folder.get('nextcloud_target_name')) is not str or not folder['nextcloud_target_name']):
        raise DocumentWorkshopError('document_context_scope_changed')
    return folder


def _item(resource, rows, folder_id, scope_key, references):
    try:
        if resource.is_collection:
            adoption.remote_identity(scope_key, resource.file_id)
            category, reason, local = 'incompatible', 'document_collection', None
        else:
            category, reason, local = adoption.classify_resource(rows, scope_key, resource)
    except DocumentWorkshopError as exc:
        category = 'collision' if exc.reason_code == 'document_local_collision' else 'incompatible'
        reason, local = exc.reason_code, None
    result = dict(reference=references.put(folder_id,scope_key,resource), name=resource.relative_path.split('/')[-1],
                  relative_path=resource.relative_path,is_collection=resource.is_collection,category=category,reason_code=reason)
    if local:
        result['workspace_file_id'] = str(local['id'])
    if resource.byte_size is not None:
        result['byte_size'] = resource.byte_size
    if not resource.is_collection:
        result['source_extension'] = PurePosixPath(resource.relative_path).suffix.lower()
    return result


def list_remote(folder_id, data, *, store, conversations, folders, files, reader=None, references=None, adoption_store=adoption):
    references = references if references is not None else _references
    try:
        folder = _scope(folder_id,data,{'context_id','collection_ref'},store=store,conversations=conversations,folders=folders,files=files)
        reader = reader if reader is not None else NextcloudDocumentReadClient.from_env()
        scope_key = reader.scope_key(folder['nextcloud_target_name'])
        path, expected_id = 'Documents', None
        if 'collection_ref' in data:
            collection = references.resolve(data['collection_ref'],folder_id,scope_key)
            if not collection.is_collection:
                raise DocumentWorkshopError('document_reference_invalid')
            adoption.remote_identity(scope_key,collection.file_id)
            path, expected_id = collection.relative_path, collection.file_id
        rows = adoption_store.list_candidates(folder_id)
        collection, children = reader.list_collection(folder['nextcloud_target_name'],path,expected_file_id=expected_id)
        # Revalidate mutable M1/folder authority after remote I/O, before projection.
        current = _scope(folder_id,data,{'context_id','collection_ref'},store=store,conversations=conversations,folders=folders,files=files)
        if any(current.get(k) != folder.get(k) for k in ('nextcloud_target_name','nextcloud_folder_ref')):
            raise DocumentWorkshopError('document_context_scope_changed')
        items = [_item(child,rows,folder_id,scope_key,references) for child in children]
        return dict(ok=True,workspace_folder_id=folder_id,collection=dict(reference=references.put(folder_id,scope_key,collection),
                    relative_path=collection.relative_path,name=collection.relative_path.split('/')[-1]),items=items,complete=True), 200
    except DocumentWorkshopError as exc:
        return failure(exc.reason_code)
    except Exception:
        return failure('document_adoption_storage_unavailable')


def adopt_remote(folder_id, data, *, store, conversations, folders, files, reader=None, references=None, adoption_store=adoption):
    references = references if references is not None else _references
    try:
        if type(data) is not dict or set(data) != {'context_id','resource_ref'} or not contexts._id(data.get('resource_ref')):
            raise DocumentWorkshopError('document_request_invalid')
        folder = _scope(folder_id,data,{'context_id','resource_ref'},store=store,conversations=conversations,folders=folders,files=files)
        reader = reader if reader is not None else NextcloudDocumentReadClient.from_env()
        scope_key = reader.scope_key(folder['nextcloud_target_name'])
        resource = references.resolve(data['resource_ref'],folder_id,scope_key)
        path = adoption.check_resource(scope_key,resource)
        adoption.classify_resource(adoption_store.list_candidates(folder_id),scope_key,resource)
        content = reader.read_file(folder['nextcloud_target_name'],resource)
        extracted = extract_complete_source(content,filename=path.segments[-1],media_type=resource.media_type)
        result = adoption_store.publish_adoption(folder_id=folder_id,context_id=data['context_id'],folder=folder,scope_key=scope_key,
            resource=resource,content=content,extraction=extracted,storage_root=files._storage_root())
        item = dict(result['file'])
        item['document_nextcloud_link'] = {'lookup_state':'ok','nextcloud_sync_state':'linked','last_sync_operation':'observe',
                                          'last_sync_reason_code':'folder_document_list_ok'}
        item = workspace_folder_documents.apply_document_v1_projection(item,folder=folder)
        category = result['category']
        return dict(ok=True,category=category,workspace_folder_id=folder_id,workspace_file_id=item['id'],file=item), 201 if category=='adopted' else 200
    except DocumentWorkshopError as exc:
        return failure(exc.reason_code)
    except Exception:
        return failure('document_adoption_storage_unavailable')
