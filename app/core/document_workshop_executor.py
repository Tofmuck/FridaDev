"""M5 request-owned execution with explicit clients; no live default mutator."""
from dataclasses import dataclass
import hashlib

from . import document_workshop_execution_store as store
from .chat_turn_reservation import ChatReservation
from .document_canonical import validate_canonical
from .document_markdown import serialize_markdown
from .document_workshop_contract import DocumentWorkshopError


@dataclass(frozen=True)
class ExecutionResult:
    state: str
    reason_code: str|None=None




class DocumentExecutor:
    def __init__(self,*,mutation_client,storage_root,source_reader=None,supports_update=False):
        if mutation_client is None or storage_root is None:
            raise DocumentWorkshopError('document_execution_unavailable')
        self.client,self.storage_root,self.source_reader=mutation_client,storage_root,source_reader
        self.supports_update=supports_update

    def reconcile(self,action_id):
        from .document_workshop_update_reconciliation import reconcile
        reconcile(action_id,self)

    def _render(self,run):
        canonical=validate_canonical(run.revision['canonical'])
        content=serialize_markdown(canonical).encode('utf-8')
        if hashlib.sha256(content).hexdigest()!=run.revision['markdown_sha256']:
            raise DocumentWorkshopError('document_revision_invalid')
        return content

    def execute(self,run):
        if run.action['operation']=='update':return self._execute_update(run)
        reservation=ChatReservation(run.token)
        result=None
        publication_unknown=False
        try:
            store.check(run)
            sources=[]
            for file_id in run.action['source_file_ids']:
                if not callable(self.source_reader):raise DocumentWorkshopError('document_source_unavailable')
                sources.append(self.source_reader(run.action['workspace_folder_id'],file_id))
            store.verify_fresh_sources(run,sources)
            content=self._render(run)
            if type(content) is not bytes or hashlib.sha256(content).hexdigest()!=run.revision['markdown_sha256']:
                raise DocumentWorkshopError('document_format_unavailable')
            store.check(run)
            folder=run.folder['nextcloud_target_name']
            missing=self.client.inspect_create_target(folder,run.target,format='markdown')
            if type(missing) is not tuple or any(path not in run.collections for path in missing):
                raise DocumentWorkshopError('document_mutation_not_authorized')
            store.intent(run)
            result=self.client.create_document(folder,run.target,content,format='markdown',
                confirmed_collections=run.collections,
                before_mutation=lambda method,path:store.before_mutation(run,method,path))
            store.observe(run,'remote_outcome',result)
            store.check(run)
            if result.state!='known_success':
                store.finish(run,'remote_uncertain' if result.state=='remote_uncertain' else 'failed',result.reason_code,
                    created_collections_count=None if result.state=='remote_uncertain' else len(result.created_collections))
                return ExecutionResult('closed')
            try:
                store.publish(run,result=result,content=content,scope_key=self.client.scope_key(folder),storage_root=self.storage_root)
            except store.PublicationFailure as failure:
                if failure.ambiguous:
                    publication_unknown=True
                    proof=store.publication_proof(run,result=result,content=content,
                        scope_key=self.client.scope_key(folder),storage_root=self.storage_root)
                    if proof=='complete':return ExecutionResult('completed')
                    if proof!='absent':
                        try:store.publication_unknown(run)
                        except Exception:pass
                        return ExecutionResult('remote_uncertain','document_publication_unknown')
                    publication_unknown=False
                    store.discard(failure.prepared)
                # Definite rollback and the original, still live owner are both
                # required. A lost lease can never authorize compensating DELETE.
                store.check(run)
                compensation=self.client.compensate_created_document(folder,run.target,result,format='markdown',
                    before_mutation=lambda method,path:store.before_mutation(run,method,path,compensation=True))
                store.observe(run,'compensation_outcome',compensation)
                store.finish(run,'failed' if compensation.state=='absence_certain' else 'remote_uncertain',
                    'document_publication_failed_compensated' if compensation.state=='absence_certain' else compensation.reason_code,
                    created_collections_count=len(result.created_collections))
        except Exception as error:
            reason=error.reason_code if isinstance(error,DocumentWorkshopError) else 'document_execution_unavailable'
            # An effect may have happened even if its response or outcome commit
            # was lost. A journal intent prevents any permissive failed/absence.
            try:
                with store._db_conn() as conn:
                    intended=conn.execute('SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid LIMIT 1',
                        (run.action['id'],)).fetchone()
                store.finish(run,'remote_uncertain' if intended else 'invalidated' if reason=='document_remote_changed' else 'failed',reason,
                    created_collections_count=len(result.created_collections) if result is not None and hasattr(result,'created_collections') and result.state!='remote_uncertain' else None)
            except Exception:
                # GET requalifies a dead executing claim; no late owner gains
                # authority, including authority to append an outcome.
                try:store.reconcile(run.action['id'])
                except Exception:pass
            if publication_unknown:return ExecutionResult('remote_uncertain','document_publication_unknown')
        finally:
            reservation.stop_after_commit()
        return ExecutionResult('completed')

    def _execute_update(self,run):
        from .document_workshop_update_target import verify_fresh
        reservation=ChatReservation(run.token)
        result=None
        try:
            if not self.supports_update:raise DocumentWorkshopError('document_update_unavailable')
            store.check(run)
            if not callable(self.source_reader):raise DocumentWorkshopError('document_source_unavailable')
            observations=[self.source_reader(run.action['workspace_folder_id'],file_id) for file_id in run.action['source_file_ids']]
            store.verify_fresh_sources(run,observations)
            content=self._render(run)
            version=run.action['target_version']
            # Last complete M2 observation uses the originally prepared version.
            # It never refreshes the PUT precondition or silently adopts changes.
            target=self.source_reader(run.action['workspace_folder_id'],version['workspace_file_id'])
            verify_fresh(run.action,target)
            store.check(run);store.intent(run)
            folder=run.folder['nextcloud_target_name']
            result=self.client.update_document(folder,run.target,content,prepared_etag=version['etag'],
                expected_file_id=version['remote_file_id'],before_mutation=lambda method,path:store.before_mutation(run,method,path))
            store.observe(run,'remote_outcome',result)
            if result.state!='known_success':
                state='remote_uncertain' if result.state=='remote_uncertain' else 'conflict' if result.http_status==412 else 'failed'
                store.finish(run,state,result.reason_code,created_collections_count=0)
                return ExecutionResult('closed')
            try:
                store.publish(run,result=result,content=content,scope_key=self.client.scope_key(folder),storage_root=self.storage_root)
            except store.PublicationFailure as failure:
                if failure.ambiguous:
                    proof=store.publication_proof(run,result=result,content=content,scope_key=self.client.scope_key(folder),storage_root=self.storage_root)
                    if proof=='complete':return ExecutionResult('completed')
                # No update compensation: neither DELETE nor restoring bytes.
                store.publication_unknown(run)
                return ExecutionResult('remote_uncertain','document_publication_unknown')
        except Exception as error:
            reason=error.reason_code if isinstance(error,DocumentWorkshopError) else 'document_execution_unavailable'
            try:
                with store._db_conn() as conn:
                    intended=conn.execute("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid AND event='put_intent'",(run.action['id'],)).fetchone()
                conflict=reason in ('document_remote_changed','document_remote_missing','document_remote_incompatible',
                    'document_remote_version_invalid','document_remote_identity_invalid')
                store.finish(run,'remote_uncertain' if intended else 'conflict' if conflict else 'failed',reason,created_collections_count=0)
            except Exception:
                try:store.reconcile(run.action['id'])
                except Exception:pass
        finally:
            # A NOWAIT rejection can occur after the remote effect while the
            # original claim is still active. This request is now finished:
            # close only its own M3 owner, then observe it without replay.
            reservation.close()
            try:store.reconcile(run.action['id'])
            except Exception:pass
        return ExecutionResult('completed')
