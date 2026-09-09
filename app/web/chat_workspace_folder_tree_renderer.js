'use strict';

const WorkspaceFolderTreeUiHelpers = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolders
    ? window.FridaWorkspaceFolders
    : (typeof require !== 'undefined' ? require('./chat_workspace_folders.js') : null)
);
const WorkspaceFolderTreeSidebarIcons = (
  typeof window !== 'undefined' && window.FridaChatSidebarIcons
    ? window.FridaChatSidebarIcons
    : (typeof require !== 'undefined' ? require('./chat_sidebar_icons.js') : null)
);

function createWorkspaceFolderTreeRenderer({
  threadsUl,
  documentObj,
  uiHelpers = WorkspaceFolderTreeUiHelpers,
  getWorkspaceFolders,
  isFolderCollapsed,
  toggleFolderCollapsed,
  onCreate,
  onReorder,
  onUploadFile,
  onRename,
  onDelete,
  fileRowsRenderer,
  artifactPanels,
  bindConversationDropTarget,
} = {}) {
  const doc = documentObj || (typeof document !== 'undefined' ? document : null);

  const appendToolbar = () => {
    const li = doc.createElement('li');
    li.className = 'workspace-folder-toolbar';
    const label = doc.createElement('span');
    label.textContent = 'DOSSIERS';
    li.appendChild(label);
    const addBtn = doc.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'workspace-folder-add';
    WorkspaceFolderTreeSidebarIcons?.setSidebarButtonIcon?.(addBtn, doc, 'plus');
    addBtn.title = 'Créer un répertoire';
    addBtn.setAttribute('aria-label', 'Créer un répertoire');
    addBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      void onCreate();
    });
    li.appendChild(addBtn);
    threadsUl.appendChild(li);
  };

  const appendNoFoldersEmpty = () => {
    const empty = doc.createElement('li');
    empty.className = 'workspace-folder-empty workspace-folder-empty-global';
    empty.textContent = 'Aucun répertoire';
    threadsUl.appendChild(empty);
  };

  const appendFolderRow = (folder, folderThreads, index, appendThreadRow) => {
    const folders = getWorkspaceFolders();
    const li = doc.createElement('li');
    const collapsed = isFolderCollapsed(folder.id);
    const conversationCount = folderThreads.length;
    const conversationLabel = `${conversationCount} conversation${conversationCount === 1 ? '' : 's'}`;
    const syncLabel = uiHelpers?.workspaceFolderNextcloudStatusLabel?.(folder) || '';
    const accessibleDetails = [folder.display_name, conversationLabel, syncLabel].filter(Boolean).join(' · ');
    const hoverDetails = [folder.description || folder.display_name, conversationLabel, syncLabel].filter(Boolean).join(' · ');
    li.className = 'workspace-folder-row';
    if (collapsed) li.classList.add('workspace-folder-collapsed');
    li.title = hoverDetails;
    li.setAttribute('aria-label', accessibleDetails);
    li.dataset.workspaceFolderId = folder.id;

    const main = doc.createElement('div');
    main.className = 'workspace-folder-main';

    const toggle = doc.createElement('button');
    toggle.type = 'button';
    toggle.className = 'workspace-folder-toggle';
    toggle.title = collapsed ? 'Déplier le répertoire' : 'Replier le répertoire';
    toggle.setAttribute('aria-label', toggle.title);
    toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    WorkspaceFolderTreeSidebarIcons?.setSidebarButtonIcon?.(toggle, doc, collapsed ? 'chevron-right' : 'chevron-down');
    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      toggleFolderCollapsed(folder.id);
    });
    main.appendChild(toggle);

    const icon = doc.createElement('span');
    icon.className = 'workspace-folder-icon';
    icon.title = folder.icon_label || 'Dossier';
    icon.innerHTML = folder.icon_svg || '';
    if (!icon.innerHTML) icon.textContent = folder.icon_label || 'Dossier';
    main.appendChild(icon);

    const name = doc.createElement('span');
    name.className = 'workspace-folder-name';
    name.textContent = folder.display_name;
    main.appendChild(name);

    const actions = doc.createElement('span');
    actions.className = 'workspace-folder-actions';
    const actionSpecs = [
      ['chevron-up', 'Monter', index === 0, () => onReorder(folder.id, -1)],
      ['chevron-down', 'Descendre', index >= folders.length - 1, () => onReorder(folder.id, 1)],
      ['pencil', 'Renommer', false, () => onRename(folder)],
      ['paperclip', 'Ajouter un fichier au répertoire', false, () => onUploadFile(folder)],
      ['trash-2', 'Supprimer', false, () => onDelete(folder)],
    ];
    if (artifactPanels?.requestCreateNote) {
      actionSpecs.splice(4, 0, [
        'notebook-pen',
        'Créer une note dans le répertoire',
        false,
        () => artifactPanels.requestCreateNote(folder),
      ]);
    }
    actionSpecs.forEach(([iconName, title, disabled, handler]) => {
      const btn = doc.createElement('button');
      btn.className = 'workspace-folder-action';
      btn.title = title;
      btn.setAttribute('aria-label', title);
      WorkspaceFolderTreeSidebarIcons?.setSidebarButtonIcon?.(btn, doc, iconName);
      btn.disabled = Boolean(disabled);
      btn.addEventListener('click', (event) => {
        event.stopPropagation();
        void handler();
      });
      actions.appendChild(btn);
    });
    main.appendChild(actions);

    li.appendChild(main);
    li.addEventListener('click', (event) => {
      if (event.target?.closest?.('button, input, textarea, select, a')) return;
      toggleFolderCollapsed(folder.id);
    });
    if (typeof bindConversationDropTarget === 'function') {
      bindConversationDropTarget(li, folder.id);
    }
    threadsUl.appendChild(li);

    if (collapsed) return;

    if (!folderThreads.length) {
      const empty = doc.createElement('li');
      empty.className = 'workspace-folder-empty';
      empty.textContent = 'Aucune conversation';
      threadsUl.appendChild(empty);
    } else {
      folderThreads.forEach((thread) => appendThreadRow(thread, true));
    }

    fileRowsRenderer?.appendFileRows?.(folder);
    artifactPanels?.appendRows?.(folder);
  };

  return Object.freeze({ appendToolbar, appendNoFoldersEmpty, appendFolderRow });
}

const FridaWorkspaceFolderTreeRendererModule = Object.freeze({
  createWorkspaceFolderTreeRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderTreeRendererModule;
}
