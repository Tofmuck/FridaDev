'use strict';

function createWorkspaceFolderSidebarRenderer({
  threadsUl,
  getWorkspaceFolders,
  refreshThreadsFromServer,
  renderThreads,
  setThreadStatus,
  createWorkspaceFolderOnServer,
  updateWorkspaceFolderOnServer,
  deleteWorkspaceFolderOnServer,
  consoleObj,
} = {}) {
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });

  const syncAndRender = async () => {
    await refreshThreadsFromServer({ keepSelection: true });
    renderThreads();
  };

  const requestCreate = async () => {
    const raw = typeof window !== 'undefined' ? window.prompt('Nom du répertoire de travail') : '';
    const displayName = String(raw || '').replace(/\s+/g, ' ').trim();
    if (!displayName) return;
    try {
      await createWorkspaceFolderOnServer(displayName);
      await syncAndRender();
    } catch (err) {
      logger.warn('Création répertoire échouée', err);
      setThreadStatus('Création du répertoire impossible.', true);
    }
  };

  const requestRename = async (folder) => {
    const rawName = typeof window !== 'undefined' ? window.prompt('Nom du répertoire', folder.display_name || '') : '';
    const displayName = String(rawName || '').replace(/\s+/g, ' ').trim();
    if (!displayName || displayName === folder.display_name) return;
    const rawDescription = typeof window !== 'undefined'
      ? window.prompt('Description courte (non injectée)', folder.description || '')
      : '';
    try {
      await updateWorkspaceFolderOnServer(folder.id, {
        display_name: displayName,
        description: String(rawDescription || '').replace(/\s+/g, ' ').trim(),
      });
      await syncAndRender();
    } catch (err) {
      logger.warn('Renommage répertoire échoué', err);
      setThreadStatus('Renommage du répertoire impossible.', true);
    }
  };

  const requestDelete = async (folder) => {
    const ok = typeof window !== 'undefined'
      ? window.confirm(`Supprimer le répertoire "${folder.display_name}" ? Les conversations resteront hors répertoire.`)
      : false;
    if (!ok) return;
    try {
      await deleteWorkspaceFolderOnServer(folder.id);
      await syncAndRender();
    } catch (err) {
      logger.warn('Suppression répertoire échouée', err);
      setThreadStatus('Suppression du répertoire impossible.', true);
    }
  };

  const reorder = async (folderId, direction) => {
    const folders = [...getWorkspaceFolders()];
    const idx = folders.findIndex((folder) => folder.id === folderId);
    const nextIdx = idx + direction;
    if (idx < 0 || nextIdx < 0 || nextIdx >= folders.length) return;
    const moved = [...folders];
    [moved[idx], moved[nextIdx]] = [moved[nextIdx], moved[idx]];
    try {
      await Promise.all(moved.map((folder, orderIdx) =>
        updateWorkspaceFolderOnServer(folder.id, { sort_order: (orderIdx + 1) * 1000 })
      ));
      await syncAndRender();
    } catch (err) {
      logger.warn('Réordonnancement répertoire échoué', err);
      setThreadStatus('Ordre des répertoires non synchronisé.', true);
    }
  };

  const appendToolbar = () => {
    const li = document.createElement('li');
    li.className = 'workspace-folder-toolbar';
    const label = document.createElement('span');
    label.textContent = 'Répertoires';
    li.appendChild(label);
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'workspace-folder-add';
    addBtn.textContent = '+';
    addBtn.title = 'Créer un répertoire';
    addBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      void requestCreate();
    });
    li.appendChild(addBtn);
    threadsUl.appendChild(li);
  };

  const appendFolderRow = (folder, folderThreads, index, appendThreadRow) => {
    const folders = getWorkspaceFolders();
    const li = document.createElement('li');
    li.className = 'workspace-folder-row';
    li.title = folder.description || folder.display_name;

    const main = document.createElement('div');
    main.className = 'workspace-folder-main';

    const icon = document.createElement('span');
    icon.className = 'workspace-folder-icon';
    icon.textContent = folder.icon_label || 'F';
    main.appendChild(icon);

    const name = document.createElement('span');
    name.className = 'workspace-folder-name';
    name.textContent = folder.display_name;
    main.appendChild(name);

    const count = document.createElement('span');
    count.className = 'workspace-folder-count';
    count.textContent = String(folderThreads.length);
    main.appendChild(count);

    [
      ['↑', 'Monter', index === 0, () => reorder(folder.id, -1)],
      ['↓', 'Descendre', index >= folders.length - 1, () => reorder(folder.id, 1)],
      ['··', 'Renommer', false, () => requestRename(folder)],
      ['×', 'Supprimer', false, () => requestDelete(folder)],
    ].forEach(([text, title, disabled, handler]) => {
      const btn = document.createElement('button');
      btn.className = 'workspace-folder-action';
      btn.title = title;
      btn.textContent = text;
      btn.disabled = Boolean(disabled);
      btn.addEventListener('click', (event) => {
        event.stopPropagation();
        void handler();
      });
      main.appendChild(btn);
    });

    li.appendChild(main);
    threadsUl.appendChild(li);

    if (!folderThreads.length) {
      const empty = document.createElement('li');
      empty.className = 'workspace-folder-empty';
      empty.textContent = 'Aucune conversation';
      threadsUl.appendChild(empty);
      return;
    }
    folderThreads.forEach((thread) => appendThreadRow(thread, true));
  };

  return Object.freeze({
    appendToolbar,
    appendFolderRow,
  });
}

const FridaWorkspaceFoldersSidebar = Object.freeze({
  createWorkspaceFolderSidebarRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFoldersSidebar;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFoldersSidebar = FridaWorkspaceFoldersSidebar;
}
