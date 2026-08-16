from __future__ import annotations

"""Prompt-time reads for active and selected workspace documents."""

from dataclasses import dataclass
from typing import Any, Mapping

from core import active_conversation_documents
from core import workspace_file_selections


def _text(value: Any) -> str:
    return str(value or '').strip()


@dataclass(frozen=True)
class ActiveDocumentsPromptRead:
    status: str
    documents: tuple[dict[str, Any], ...] = ()
    reason_code: str = ''
    error_class: str = ''


def _active_documents_for_prompt(
    *,
    conversation: Mapping[str, Any],
    active_documents_module: Any = active_conversation_documents,
    logger: Any = None,
) -> ActiveDocumentsPromptRead:
    conversation_id = _text(conversation.get('id'))
    if not conversation_id:
        return ActiveDocumentsPromptRead(status='empty')
    reader = getattr(active_documents_module, 'list_active_documents_for_prompt', None)
    if not callable(reader):
        return ActiveDocumentsPromptRead(
            status='error',
            reason_code='active_documents_reader_unavailable',
        )
    try:
        raw_documents = reader(conversation_id)
    except Exception as exc:
        if logger is not None:
            logger.warning('active_documents_prompt_read_failed id=%s err=%s', conversation_id, exc)
        return ActiveDocumentsPromptRead(
            status='error',
            reason_code='active_documents_read_error',
            error_class=exc.__class__.__name__,
        )
    documents: list[dict[str, Any]] = []
    for item in raw_documents or []:
        if isinstance(item, Mapping):
            documents.append(dict(item))
    if not documents:
        return ActiveDocumentsPromptRead(status='empty')
    return ActiveDocumentsPromptRead(status='ok', documents=tuple(documents))


def _workspace_files_for_prompt(
    *,
    conversation: Mapping[str, Any],
    workspace_file_selections_module: Any = workspace_file_selections,
    logger: Any = None,
) -> ActiveDocumentsPromptRead:
    conversation_id = _text(conversation.get('id'))
    if not conversation_id:
        return ActiveDocumentsPromptRead(status='empty')
    if not _text(conversation.get('workspace_folder_id')):
        return ActiveDocumentsPromptRead(status='empty')
    reader = getattr(workspace_file_selections_module, 'list_selected_files_for_prompt', None)
    if not callable(reader):
        return ActiveDocumentsPromptRead(
            status='error',
            reason_code='workspace_file_selection_reader_unavailable',
        )
    try:
        raw_documents = reader(conversation_id)
    except Exception as exc:
        if logger is not None:
            logger.warning('workspace_files_prompt_read_failed id=%s err=%s', conversation_id, exc)
        return ActiveDocumentsPromptRead(
            status='error',
            reason_code='workspace_files_read_error',
            error_class=exc.__class__.__name__,
        )
    documents: list[dict[str, Any]] = []
    for item in raw_documents or []:
        if isinstance(item, Mapping):
            documents.append(dict(item))
    if not documents:
        return ActiveDocumentsPromptRead(status='empty')
    return ActiveDocumentsPromptRead(status='ok', documents=tuple(documents))


def _merge_document_prompt_reads(
    active_read: ActiveDocumentsPromptRead,
    workspace_read: ActiveDocumentsPromptRead,
) -> ActiveDocumentsPromptRead:
    documents = tuple([*active_read.documents, *workspace_read.documents])
    if active_read.status == 'error':
        return ActiveDocumentsPromptRead(
            status='error',
            documents=documents,
            reason_code=active_read.reason_code or 'active_documents_read_error',
        )
    if workspace_read.status == 'error':
        return ActiveDocumentsPromptRead(
            status='error',
            documents=documents,
            reason_code=workspace_read.reason_code or 'workspace_files_read_error',
        )
    if documents:
        return ActiveDocumentsPromptRead(status='ok', documents=documents)
    return ActiveDocumentsPromptRead(status='empty')
