'use strict';

const WorkspaceFolderUiHelpers = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolders
    ? window.FridaWorkspaceFolders
    : (typeof require !== 'undefined' ? require('./chat_workspace_folders.js') : null)
);

function createWorkspaceFolderSidebarRenderer({
  threadsUl,
  getWorkspaceFolders,
  getWorkspaceFiles,
  refreshThreadsFromServer,
  refreshWorkspaceFiles,
  renderThreads,
  setThreadStatus,
  createWorkspaceFolderOnServer,
  updateWorkspaceFolderOnServer,
  deleteWorkspaceFolderOnServer,
  uploadWorkspaceFileOnServer,
  deleteWorkspaceFileOnServer,
  getCurrentThread,
  getWorkspaceFileSelections,
  selectWorkspaceFileOnServer,
  deselectWorkspaceFileOnServer,
  refreshWorkspaceFileSelections,
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
      ? window.confirm(`Supprimer le répertoire "${folder.display_name}" ? Les conversations resteront hors répertoire et les fichiers du répertoire seront supprimés.`)
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

  const requestUploadFile = async (folder) => {
    if (!folder?.id || typeof document === 'undefined') return;
    if (typeof uploadWorkspaceFileOnServer !== 'function' || typeof refreshWorkspaceFiles !== 'function') {
      setThreadStatus('Stockage de répertoire indisponible.', true);
      return;
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.pdf,.docx,.odt,.md,.txt,.png,.jpg,.jpeg,.webp,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.oasis.opendocument.text,image/png,image/jpeg,image/webp';
    input.className = 'sr-only';
    const cleanup = () => {
      if (input.parentNode) input.parentNode.removeChild(input);
    };
    input.addEventListener('change', async () => {
      const files = Array.from(input.files || []).filter(Boolean);
      if (!files.length) {
        cleanup();
        return;
      }
      try {
        for (const file of files) {
          await uploadWorkspaceFileOnServer(folder.id, file);
        }
        await refreshWorkspaceFiles(folder.id);
        renderThreads();
        setThreadStatus(files.length === 1 ? 'Fichier ajouté au répertoire.' : `${files.length} fichiers ajoutés au répertoire.`);
      } catch (err) {
        logger.warn('Upload fichier répertoire échoué', err);
        setThreadStatus('Ajout du fichier de répertoire impossible.', true);
      } finally {
        cleanup();
      }
    });
    document.body.appendChild(input);
    input.click();
  };

  const requestDeleteFile = async (folder, file) => {
    if (typeof deleteWorkspaceFileOnServer !== 'function' || typeof refreshWorkspaceFiles !== 'function') {
      setThreadStatus('Stockage de répertoire indisponible.', true);
      return;
    }
    const ok = typeof window !== 'undefined'
      ? window.confirm(`Supprimer le fichier "${file.display_name}" du répertoire ?`)
      : false;
    if (!ok) return;
    try {
      await deleteWorkspaceFileOnServer(folder.id, file.id);
      await refreshWorkspaceFiles(folder.id);
      const current = typeof getCurrentThread === 'function' ? getCurrentThread() : null;
      if (current?.id && typeof refreshWorkspaceFileSelections === 'function') {
        await refreshWorkspaceFileSelections(current.id);
      }
      renderThreads();
      setThreadStatus('Fichier supprimé du répertoire.');
    } catch (err) {
      logger.warn('Suppression fichier répertoire échouée', err);
      setThreadStatus('Suppression du fichier impossible.', true);
    }
  };

  const requestToggleSelection = async (folder, file, shouldSelect) => {
    const current = typeof getCurrentThread === 'function' ? getCurrentThread() : null;
    if (!current?.id || current.workspace_folder_id !== folder.id) {
      setThreadStatus('Sélection disponible seulement dans une conversation du répertoire.', true);
      renderThreads();
      return;
    }
    if (typeof selectWorkspaceFileOnServer !== 'function' || typeof deselectWorkspaceFileOnServer !== 'function') {
      setThreadStatus('Sélection de fichiers indisponible.', true);
      renderThreads();
      return;
    }
    try {
      if (shouldSelect) {
        await selectWorkspaceFileOnServer(current.id, file.id);
        setThreadStatus('Fichier sélectionné pour cette conversation.');
      } else {
        await deselectWorkspaceFileOnServer(current.id, file.id);
        setThreadStatus('Fichier décoché pour cette conversation.');
      }
      if (typeof refreshWorkspaceFileSelections === 'function') {
        await refreshWorkspaceFileSelections(current.id);
      }
      renderThreads();
    } catch (err) {
      logger.warn('Sélection fichier répertoire échouée', err);
      setThreadStatus('Sélection du fichier impossible.', true);
      renderThreads();
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
      ['+F', 'Ajouter un fichier au répertoire', false, () => requestUploadFile(folder)],
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

    appendFileRows(folder);

    if (!folderThreads.length) {
      const empty = document.createElement('li');
      empty.className = 'workspace-folder-empty';
      empty.textContent = 'Aucune conversation';
      threadsUl.appendChild(empty);
      return;
    }
    folderThreads.forEach((thread) => appendThreadRow(thread, true));
  };

  const appendFileRows = (folder) => {
    const files = typeof getWorkspaceFiles === 'function' ? getWorkspaceFiles(folder.id) : [];
    if (!files.length) return;
    const li = document.createElement('li');
    li.className = 'workspace-folder-files';
    files.forEach((file) => {
      const current = typeof getCurrentThread === 'function' ? getCurrentThread() : null;
      const selections = typeof getWorkspaceFileSelections === 'function' && current?.id
        ? getWorkspaceFileSelections(current.id)
        : [];
      const selection = selections.find((item) => item.workspace_file_id === file.id);
      const selected = Boolean(selection?.selected && selection.selection_status !== 'stale');
      const canSelect = Boolean(current?.id && current.workspace_folder_id === folder.id);
      const row = document.createElement('div');
      row.className = 'workspace-folder-file';
      if (selected) row.classList.add('selected');
      if (file.status && file.status !== 'active') {
        row.dataset.status = file.status;
      }
      if (selection?.selection_status === 'stale') {
        row.dataset.selection = 'stale';
      }

      const toggle = document.createElement('input');
      toggle.type = 'checkbox';
      toggle.className = 'workspace-folder-file-select';
      toggle.title = 'Sélectionner pour cette conversation';
      toggle.checked = selected;
      toggle.disabled = !canSelect || file.status === 'deleted' || file.status === 'disk_missing';
      toggle.addEventListener('click', (event) => event.stopPropagation());
      toggle.addEventListener('change', (event) => {
        event.stopPropagation();
        void requestToggleSelection(folder, file, toggle.checked);
      });
      row.appendChild(toggle);

      const name = document.createElement('span');
      name.className = 'workspace-folder-file-name';
      name.textContent = file.display_name || 'fichier';
      row.appendChild(name);

      const meta = document.createElement('span');
      meta.className = 'workspace-folder-file-meta';
      meta.textContent = WorkspaceFolderUiHelpers?.compactWorkspaceFileMeta
        ? WorkspaceFolderUiHelpers.compactWorkspaceFileMeta(file)
        : '';
      row.appendChild(meta);

      if (selection?.selection_status === 'stale') {
        const stale = document.createElement('span');
        stale.className = 'workspace-folder-file-state';
        stale.textContent = 'stale';
        row.appendChild(stale);
      }

      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'workspace-folder-file-delete';
      del.textContent = '×';
      del.title = 'Supprimer le fichier';
      del.addEventListener('click', (event) => {
        event.stopPropagation();
        void requestDeleteFile(folder, file);
      });
      row.appendChild(del);
      li.appendChild(row);
    });
    threadsUl.appendChild(li);
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
