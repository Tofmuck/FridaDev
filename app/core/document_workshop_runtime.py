"""Compose M6 execution from the existing SQL, cache and Nextcloud owners.

Resolution is lazy and read-only: imports/startup/GET never migrate or contact DAV.
Each confirmed request owns its mutator and original creation proof.
"""
import os

from . import workspace_files, workspace_document_content_service as sources
from . import document_workshop_execution_store as store
from .document_workshop_executor import DocumentExecutor
from .workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
from .workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
from .document_workshop_receipts import _PUBLIC


def get_executor():
    try:
        root = workspace_files._storage_root()
        if not root.is_dir() or not os.access(root, os.W_OK | os.X_OK):
            return None
        reader = NextcloudDocumentReadClient.from_env()
        # Probe the actual required schema, without creating it. A missing M2–M5
        # migration must refuse before consuming a confirmation or opening DAV.
        with store._db_conn() as conn:
            conn.execute('''SELECT a.confirmation_turn_id,a.confirmed_at,a.workspace_file_id,
                c.owner_id,c.generation,c.lease_until,r.request_turn_id,v.storage_key,
                j.event,l.nextcloud_relative_path,l.nextcloud_scope_key,l.observed_sha256,
                ar.current_revision_id FROM document_actions a
                JOIN conversation_turn_claims c ON c.turn_id=a.id
                LEFT JOIN document_receipts r ON r.action_id=a.id
                LEFT JOIN document_revision_renders v ON v.revision_id=a.revision_id
                LEFT JOIN document_execution_journal j ON j.action_id=a.id
                LEFT JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=a.workspace_file_id
                LEFT JOIN document_artifacts ar ON ar.id=a.artifact_id LIMIT 0''')
            # The public projection and atomic publication need the complete
            # existing rows, not just the few columns used by the joins above.
            for table, required in (
                ('document_receipts', _PUBLIC | {'nextcloud_scope_key'}),
                ('document_revision_renders', {'revision_id','format','serializer_version','content_sha256','byte_size','storage_key','created_at'}),
                ('document_execution_journal', {'id','action_id','confirmation_turn_id','owner_id','generation','event','path_sha256','canonical_sha256','content_sha256','serializer_version','state','reason_code','http_status','etag','created_collections_count','created_at'}),
                ('workspace_files', {'id','workspace_folder_id','display_name','original_filename','storage_key','content_kind','media_kind','mime_type','source_extension','byte_size','sha256','sha256_12','text_chars','text_sha256_12','image_width','image_height','status','reason_code','source_kind','source_file_id','created_at','updated_at','deleted_at'}),
                ('workspace_file_nextcloud_links', {'workspace_file_id','workspace_folder_id','nextcloud_sync_state','nextcloud_target_name','nextcloud_document_ref','nextcloud_name_hash','last_sync_at','last_sync_reason_code','last_sync_operation','nextcloud_relative_path','nextcloud_collision_key','nextcloud_scope_key','nextcloud_file_id','nextcloud_etag','observed_sha256','observed_at','document_origin'}),
                ('document_artifacts', {'id','workspace_folder_id','workspace_file_id','current_revision_id'}),
                ('document_actions', {'id','context_id','conversation_id','workspace_folder_id','revision_id','artifact_id','state','phase','operation','format','relative_path','source_file_ids','source_versions','limitations','confirmation_turn_id','confirmed_at','created_collections_count','workspace_file_id'}),
            ):
                probe = conn.execute('SELECT * FROM '+table+' LIMIT 0')
                if not required.issubset({column.name for column in probe.description}):
                    return None
            required_triggers = {
                ('conversations','workshop_scope_change'),
                ('workspace_folders','workshop_scope_change'),
                ('workspace_files','workshop_scope_change'),
                ('workspace_file_nextcloud_links','workshop_scope_change'),
                ('workspace_folder_nextcloud_links','workshop_scope_change'),
                ('document_workshop_contexts','workshop_context_authority'),
                ('document_revisions','document_revision_immutable'),
                ('document_actions','document_action_identity_immutable'),
                ('document_workshop_contexts','document_actions_context_closed'),
                ('workspace_files','document_actions_source_changed'),
                ('workspace_file_nextcloud_links','document_actions_source_changed'),
                ('document_receipts','document_execution_immutable'),
                ('document_revision_renders','document_execution_immutable'),
                ('document_execution_journal','document_execution_immutable'),
            }
            present = conn.execute('''SELECT c.relname,t.tgname FROM pg_trigger t
                JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=current_schema() AND t.tgenabled IN ('O','A')''').fetchall()
            if not required_triggers.issubset(set(present)):
                return None
            from .document_workshop_update_target import available
            supports_update=available(conn)
        return DocumentExecutor(mutation_client=NextcloudDocumentMutationClient(reader.config),supports_update=supports_update,
            storage_root=root, source_reader=lambda folder_id, file_id:
                sources.read_workspace_document_source(folder_id, file_id, reader=reader))
    except Exception:
        return None
