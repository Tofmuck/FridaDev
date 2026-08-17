'use strict';

function createConversationListRenderer({
  threadsUl,
  documentObj,
  getThreads,
  getWorkspaceFolders,
  getCurrentId,
  groupThreadsByWorkspaceFolder,
  workspaceFolderRenderer,
  folderBinding,
  formatTimestamp,
  isEditingThread,
  onRename,
  onDelete,
  onSelect,
} = {}) {
  const doc = documentObj || (typeof document !== 'undefined' ? document : null);
  const editing = typeof isEditingThread === 'function' ? isEditingThread : () => false;

  const appendThreadRow = (thread, currentId, nested = false) => {
    const li = doc.createElement('li');
    if (nested) li.classList.add('in-workspace-folder');
    if (thread.id === currentId) li.classList.add('active');
    li.tabIndex = 0;
    li.draggable = true;
    li.setAttribute('role', 'button');
    li.setAttribute('aria-label', thread.title || 'Conversation');
    li.dataset.conversationId = thread.id;

    const main = doc.createElement('div');
    main.className = 'thread-main';

    const titleSpan = doc.createElement('span');
    titleSpan.className = 'title';
    titleSpan.textContent = thread.title || 'Sans titre';
    main.appendChild(titleSpan);

    const editBtn = doc.createElement('button');
    editBtn.className = 'thread-edit';
    editBtn.title = 'Renommer';
    editBtn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
    editBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      onRename(li, thread.id);
    });
    main.appendChild(editBtn);

    const deleteBtn = doc.createElement('button');
    deleteBtn.className = 'thread-del';
    deleteBtn.title = 'Supprimer';
    deleteBtn.innerHTML = '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/></svg>';
    deleteBtn.addEventListener('click', async (event) => {
      event.stopPropagation();
      await onDelete(li, thread.id);
    });
    main.appendChild(deleteBtn);
    li.appendChild(main);

    const timestamp = thread.updated_at || thread.created_at;
    if (timestamp) {
      const timeSpan = doc.createElement('span');
      timeSpan.className = 'thread-time';
      timeSpan.textContent = formatTimestamp(timestamp);
      li.appendChild(timeSpan);
    }

    titleSpan.addEventListener('dblclick', (event) => {
      event.stopPropagation();
      onRename(li, thread.id);
    });
    li.addEventListener('dblclick', (event) => {
      const interactiveTarget = event.target?.closest?.('button, input, textarea, select, a');
      if (interactiveTarget) return;
      event.stopPropagation();
      onRename(li, thread.id);
    });
    li.addEventListener('click', async () => {
      if (editing()) return;
      await onSelect(thread.id);
    });
    folderBinding?.bindConversationDragSource?.(li, thread.id);

    threadsUl.appendChild(li);
    return li;
  };

  const renderThreads = () => {
    if (!threadsUl || !doc) return;
    threadsUl.innerHTML = '';
    const threads = getThreads();
    const folders = getWorkspaceFolders();
    const currentId = getCurrentId();
    const grouped = groupThreadsByWorkspaceFolder(threads, folders)
      || { byFolder: new Map(), outside: threads };
    const appendRow = (thread, nested = false) => appendThreadRow(thread, currentId, nested);

    workspaceFolderRenderer?.appendToolbar?.();
    if (!folders.length) {
      workspaceFolderRenderer?.appendNoFoldersEmpty?.();
    }
    folders.forEach((folder, index) => {
      workspaceFolderRenderer?.appendFolderRow?.(
        folder,
        grouped.byFolder.get(folder.id) || [],
        index,
        appendRow,
      );
    });
    if (folders.length) {
      const separator = doc.createElement('li');
      separator.className = 'workspace-folder-separator';
      separator.textContent = 'Conversations hors répertoire';
      folderBinding?.bindConversationDropTarget?.(separator, null);
      threadsUl.appendChild(separator);
    }
    (grouped.outside || []).forEach((thread) => appendRow(thread, false));
  };

  return Object.freeze({ renderThreads });
}

const FridaChatThreadsListRendererModule = Object.freeze({
  createConversationListRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaChatThreadsListRendererModule;
}
