'use strict';

function createConversationFolderBinding({
  threadsUl,
  dragMime,
  isEditingThread,
  moveThreadToWorkspaceFolder,
} = {}) {
  const mime = String(dragMime || 'application/x-fridadev-conversation-id');
  const editing = typeof isEditingThread === 'function' ? isEditingThread : () => false;
  const moveThread = typeof moveThreadToWorkspaceFolder === 'function'
    ? moveThreadToWorkspaceFolder
    : () => {};

  const clearConversationDropTargets = () => {
    if (!threadsUl || typeof threadsUl.querySelectorAll !== 'function') return;
    threadsUl.querySelectorAll('.workspace-folder-drop-target, .dragging').forEach((node) => {
      node.classList.remove('workspace-folder-drop-target', 'dragging');
    });
  };

  const hasConversationDrag = (event) => {
    if (!event?.dataTransfer) return false;
    const types = Array.from(event.dataTransfer.types || []);
    return types.includes(mime) || types.includes('text/plain');
  };

  const draggedConversationId = (event) => {
    if (!event?.dataTransfer || !hasConversationDrag(event)) return '';
    return event.dataTransfer.getData(mime)
      || event.dataTransfer.getData('text/plain')
      || '';
  };

  const bindConversationDragSource = (node, conversationId) => {
    const normalizedId = String(conversationId || '').trim();
    if (!node || !normalizedId) return;
    node.addEventListener('dragstart', (event) => {
      const interactiveTarget = event.target?.closest?.('button, input, textarea, select, a');
      if (editing() || interactiveTarget || !event.dataTransfer) {
        event.preventDefault();
        return;
      }
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData(mime, normalizedId);
      event.dataTransfer.setData('text/plain', normalizedId);
      node.classList.add('dragging');
    });
    node.addEventListener('dragend', clearConversationDropTargets);
  };

  const bindConversationDropTarget = (node, folderId) => {
    if (!node) return;
    node.addEventListener('dragenter', (event) => {
      if (!hasConversationDrag(event)) return;
      event.preventDefault();
      node.classList.add('workspace-folder-drop-target');
    });
    node.addEventListener('dragover', (event) => {
      if (!hasConversationDrag(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      node.classList.add('workspace-folder-drop-target');
    });
    node.addEventListener('dragleave', () => {
      node.classList.remove('workspace-folder-drop-target');
    });
    node.addEventListener('drop', (event) => {
      const conversationId = draggedConversationId(event);
      if (!conversationId) return;
      event.preventDefault();
      clearConversationDropTargets();
      void moveThread(conversationId, folderId || null);
    });
  };

  return Object.freeze({
    bindConversationDragSource,
    bindConversationDropTarget,
    clearConversationDropTargets,
  });
}

const FridaChatThreadsFolderBindingModule = Object.freeze({
  createConversationFolderBinding,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaChatThreadsFolderBindingModule;
}
