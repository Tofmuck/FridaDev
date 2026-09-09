'use strict';

const ConversationListSidebarIcons = (
  typeof window !== 'undefined' && window.FridaChatSidebarIcons
    ? window.FridaChatSidebarIcons
    : (typeof require !== 'undefined' ? require('./chat_sidebar_icons.js') : null)
);

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

    const kindIcon = ConversationListSidebarIcons?.createSidebarIcon?.(
      doc,
      nested ? 'message-circle' : (thread.id === currentId ? 'circle-dot' : 'circle'),
      'thread-kind-icon',
    );
    if (kindIcon) main.appendChild(kindIcon);

    const titleSpan = doc.createElement('span');
    titleSpan.className = 'title';
    titleSpan.textContent = thread.title || 'Sans titre';
    main.appendChild(titleSpan);

    const editBtn = doc.createElement('button');
    editBtn.className = 'thread-edit';
    editBtn.title = 'Renommer';
    editBtn.setAttribute('aria-label', 'Renommer');
    ConversationListSidebarIcons?.setSidebarButtonIcon?.(editBtn, doc, 'pencil');
    editBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      onRename(li, thread.id);
    });
    main.appendChild(editBtn);

    const deleteBtn = doc.createElement('button');
    deleteBtn.className = 'thread-del';
    deleteBtn.title = 'Supprimer';
    deleteBtn.setAttribute('aria-label', 'Supprimer');
    ConversationListSidebarIcons?.setSidebarButtonIcon?.(deleteBtn, doc, 'trash-2');
    deleteBtn.addEventListener('click', async (event) => {
      event.stopPropagation();
      await onDelete(li, thread.id);
    });
    main.appendChild(deleteBtn);
    if (nested) {
      const dragIcon = ConversationListSidebarIcons?.createSidebarIcon?.(doc, 'grip-vertical', 'thread-drag-icon');
      if (dragIcon) main.appendChild(dragIcon);
    }
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
      separator.textContent = 'CONVERSATIONS';
      separator.title = 'Conversations hors répertoire';
      separator.setAttribute('aria-label', 'Conversations hors répertoire');
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
