"""Fresh complete source observation for future documentary preparation.

No source selection, prompt injection, model call or assumption of local freshness.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from . import workspace_files, workspace_folders
from . import workspace_document_adoption_store as adoption
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
from .workspace_document_source_extraction import extract_complete_source
from .workspace_nextcloud_etag import validated_strong_etag


@dataclass(frozen=True, repr=False)
class WorkspaceDocumentSource:
    workspace_folder_id: str
    workspace_file_id: str
    relative_path: str
    remote_identity: str
    etag: str
    sha256: str
    observed_at: str
    source_extension: str
    media_type: str
    byte_size: int
    text: str


def _local(folder_id,file_id,folders,files):
    folder = folders.get_workspace_folder(folder_id)
    file = files.get_workspace_file_storage_row(folder_id,file_id)
    link = files.get_nextcloud_link(file_id,fail_closed=True,preserve_target_identity=True)
    if not folder or folder.get('deleted_at') or not file or file.get('deleted_at'):
        raise DocumentWorkshopError('document_remote_missing')
    if (str(file.get('id')) != file_id or str(file.get('workspace_folder_id')) != folder_id
            or file.get('status') != 'active' or file.get('content_kind') != 'document' or file.get('media_kind') != 'text'
            or folder.get('nextcloud_sync_state') != 'linked' or not link or str(link.get('workspace_folder_id')) != folder_id
            or link.get('nextcloud_sync_state') != 'linked' or not link.get('observed_sha256')):
        raise DocumentWorkshopError('document_remote_incompatible')
    if not validated_strong_etag(link.get('nextcloud_etag')):
        raise DocumentWorkshopError('document_remote_version_invalid')
    return folder,file,link


def read_workspace_document_source(folder_id,file_id,*,reader=None,folders=workspace_folders,files=workspace_files):
    try:
        folder,file,link = _local(folder_id,file_id,folders,files)
        reader = reader if reader is not None else NextcloudDocumentReadClient.from_env()
        scope_key = reader.scope_key(folder['nextcloud_target_name'])
        if scope_key != link.get('nextcloud_scope_key'):
            raise DocumentWorkshopError('document_remote_changed')
        identity = adoption.remote_identity(scope_key,link.get('nextcloud_file_id'))
        resource = reader.stat_resource(folder['nextcloud_target_name'],link.get('nextcloud_relative_path'),expected_etag=link.get('nextcloud_etag'))
        path = adoption.check_resource(scope_key,resource)
        if resource.file_id != link['nextcloud_file_id'] or resource.byte_size != file['byte_size']:
            raise DocumentWorkshopError('document_remote_changed')
        content = reader.read_file(folder['nextcloud_target_name'],resource)
        digest = hashlib.sha256(content).hexdigest()
        if digest != link['observed_sha256']:
            raise DocumentWorkshopError('document_remote_changed')
        extraction = extract_complete_source(content,filename=path.segments[-1],media_type=resource.media_type)
        current_folder,_,current_link = _local(folder_id,file_id,folders,files)
        if (any(current_folder.get(k) != folder.get(k) for k in ('nextcloud_target_name','nextcloud_folder_ref'))
                or any(current_link.get(k) != link.get(k) for k in ('nextcloud_relative_path','nextcloud_file_id','nextcloud_scope_key','nextcloud_etag','observed_sha256'))):
            raise DocumentWorkshopError('document_remote_changed')
        return WorkspaceDocumentSource(folder_id,file_id,path.relative_path,identity,resource.etag,digest,
            datetime.now(timezone.utc).isoformat(),extraction.source_extension,extraction.media_type,len(content),extraction.text)
    except DocumentWorkshopError:
        raise
    except Exception:
        raise DocumentWorkshopError('document_source_unavailable') from None
