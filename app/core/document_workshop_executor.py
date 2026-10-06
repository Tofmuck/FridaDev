"""M5 request-owned execution with explicit clients; no live default mutator."""
from dataclasses import dataclass
import hashlib

from . import document_workshop_execution_store as store
from .chat_turn_reservation import ChatReservation
from .document_canonical import validate_canonical
from .document_markdown import serialize_markdown
from .document_workshop_contract import DocumentWorkshopError, validate_writer_page_count


@dataclass(frozen=True,repr=False)
class BinaryRenderEvidence:
    """Internal synthetic boundary only, not the future Writer wire contract."""
    revision_id: str
    canonical_sha256: str
    format: str
    content: bytes
    sha256: str
    page_count: int
    complete: bool
    cleanup_complete: bool


@dataclass(frozen=True)
class ExecutionResult:
    state: str
    reason_code: str|None=None


def _validated_binary(run,format,renderer):
    # This boundary cannot be reached by the public Markdown action. Internal
    # synthetic executors exercise its post-confirmation ordering in M5.
    store.check(run)
    if format not in ('docx','pdf') or not callable(renderer):
        raise DocumentWorkshopError('document_format_unavailable')
    canonical=validate_canonical(run.revision['canonical'])
    evidence=renderer(revision_id=run.action['revision_id'],canonical_sha256=run.revision['canonical_sha256'],
        canonical=canonical.as_dict(),format=format)
    store.check(run)
    if (not isinstance(evidence,BinaryRenderEvidence) or evidence.revision_id!=run.action['revision_id']
        or evidence.canonical_sha256!=run.revision['canonical_sha256'] or evidence.format!=format
        or evidence.complete is not True or evidence.cleanup_complete is not True
        or type(evidence.content) is not bytes or not 0<len(evidence.content)<=16*1024*1024
        or hashlib.sha256(evidence.content).hexdigest()!=evidence.sha256):
        raise DocumentWorkshopError('document_render_invalid')
    validate_writer_page_count(evidence.page_count)
    return evidence


class DocumentExecutor:
    def __init__(self,*,mutation_client,storage_root,source_reader=None):
        if mutation_client is None or storage_root is None:
            raise DocumentWorkshopError('document_execution_unavailable')
        self.client,self.storage_root,self.source_reader=mutation_client,storage_root,source_reader

    def _render(self,run):
        canonical=validate_canonical(run.revision['canonical'])
        content=serialize_markdown(canonical).encode('utf-8')
        if hashlib.sha256(content).hexdigest()!=run.revision['markdown_sha256']:
            raise DocumentWorkshopError('document_revision_invalid')
        return content

    def execute(self,run):
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
