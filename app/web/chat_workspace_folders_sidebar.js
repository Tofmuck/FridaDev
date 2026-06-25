'use strict';

const WorkspaceFolderUiHelpers = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolders
    ? window.FridaWorkspaceFolders
    : (typeof require !== 'undefined' ? require('./chat_workspace_folders.js') : null)
);
const WorkspaceFolderExportsPanel = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolderExportsPanel
    ? window.FridaWorkspaceFolderExportsPanel
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_exports_panel.js') : null)
);
const WorkspaceFolderGeneratedImagesPanel = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolderGeneratedImagesPanel
    ? window.FridaWorkspaceFolderGeneratedImagesPanel
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_generated_images_panel.js') : null)
);
const WorkspaceFolderNotesPanel = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolderNotesPanel
    ? window.FridaWorkspaceFolderNotesPanel
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_notes_panel.js') : null)
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
  ocrWorkspaceFileOnServer,
  readWorkspaceOcrMarkdownOnServer,
  saveWorkspaceOcrMarkdownOnServer,
  getWorkspaceExports,
  getWorkspaceExportsStatus,
  refreshWorkspaceExports,
  createWorkspaceExportOnServer,
  openWorkspaceExport,
  downloadWorkspaceExport,
  getWorkspaceGeneratedImages,
  getWorkspaceGeneratedImagesStatus,
  refreshWorkspaceGeneratedImages,
  createWorkspaceGeneratedImageOnServer,
  openWorkspaceGeneratedImage,
  downloadWorkspaceGeneratedImage,
  deleteWorkspaceGeneratedImageOnServer,
  getWorkspaceNotes,
  getWorkspaceNotesStatus,
  refreshWorkspaceNotes,
  createWorkspaceNoteOnServer,
  prepareWorkspaceNoteOnServer,
  getCurrentThread,
  notesModeController,
  getWorkspaceFileSelections,
  selectWorkspaceFileOnServer,
  deselectWorkspaceFileOnServer,
  refreshWorkspaceFileSelections,
  bindConversationDropTarget,
  consoleObj,
} = {}) {
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });
  const iconKeys = WorkspaceFolderUiHelpers?.WORKSPACE_FOLDER_ICON_KEYS || ['folder'];
  const normalizeIconKey = WorkspaceFolderUiHelpers?.normalizeWorkspaceIconKey || ((value) => String(value || 'folder').trim() || 'folder');
  const expandedFolderIds = new Set();
  const exportsPanel = WorkspaceFolderExportsPanel?.createWorkspaceFolderExportsPanelRenderer?.({
    threadsUl,
    getWorkspaceExports,
    getWorkspaceExportsStatus,
    refreshWorkspaceExports,
    createWorkspaceExportOnServer,
    openWorkspaceExport,
    downloadWorkspaceExport,
    getCurrentThread,
    renderThreads,
    setThreadStatus,
    consoleObj: logger,
  });
  const generatedImagesPanel = WorkspaceFolderGeneratedImagesPanel?.createWorkspaceFolderGeneratedImagesPanelRenderer?.({
    threadsUl,
    getWorkspaceGeneratedImages,
    getWorkspaceGeneratedImagesStatus,
    refreshWorkspaceGeneratedImages,
    createWorkspaceGeneratedImageOnServer,
    openWorkspaceGeneratedImage,
    downloadWorkspaceGeneratedImage,
    deleteWorkspaceGeneratedImageOnServer,
    renderThreads,
    setThreadStatus,
    consoleObj: logger,
  });
  const notesPanel = WorkspaceFolderNotesPanel?.createWorkspaceFolderNotesPanelRenderer?.({
    threadsUl,
    getWorkspaceNotes,
    getWorkspaceNotesStatus,
    refreshWorkspaceNotes,
    createWorkspaceNoteOnServer,
    prepareWorkspaceNoteOnServer,
    getCurrentThread,
    notesModeController,
    renderThreads,
    setThreadStatus,
    consoleObj: logger,
  });

  const isFolderCollapsed = (folderId) => {
    const normalized = String(folderId || '');
    return normalized ? !expandedFolderIds.has(normalized) : false;
  };
  const toggleFolderCollapsed = (folderId) => {
    const normalized = String(folderId || '');
    if (!normalized) return;
    if (expandedFolderIds.has(normalized)) {
      expandedFolderIds.delete(normalized);
    } else {
      expandedFolderIds.add(normalized);
    }
    renderThreads();
  };

  const syncAndRender = async () => {
    await refreshThreadsFromServer({ keepSelection: true });
    renderThreads();
  };

  const requestCreate = async () => {
    const raw = typeof window !== 'undefined' ? window.prompt('Nom du répertoire de travail') : '';
    const displayName = String(raw || '').replace(/\s+/g, ' ').trim();
    if (!displayName) return;
    const rawIcon = typeof window !== 'undefined'
      ? window.prompt(`Icône (${iconKeys.join(', ')})`, 'folder')
      : 'folder';
    try {
      await createWorkspaceFolderOnServer(displayName, normalizeIconKey(rawIcon));
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
    const rawIcon = typeof window !== 'undefined'
      ? window.prompt(`Icône (${iconKeys.join(', ')})`, folder.icon_key || 'folder')
      : folder.icon_key || 'folder';
    try {
      await updateWorkspaceFolderOnServer(folder.id, {
        display_name: displayName,
        icon_key: normalizeIconKey(rawIcon),
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
      ? window.confirm(
        WorkspaceFolderUiHelpers?.workspaceFolderDeleteConfirmationText?.(folder)
        || `Supprimer le répertoire "${folder.display_name}" ?`
      )
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

  const requestOcrFile = async (folder, file) => {
    if (typeof ocrWorkspaceFileOnServer !== 'function' || typeof refreshWorkspaceFiles !== 'function') {
      setThreadStatus('OCR de répertoire indisponible.', true);
      return;
    }
    try {
      await ocrWorkspaceFileOnServer(folder.id, file.id);
      await refreshWorkspaceFiles(folder.id);
      renderThreads();
      setThreadStatus('Markdown OCR créé dans le répertoire.');
    } catch (err) {
      logger.warn('OCR fichier répertoire échoué', err);
      setThreadStatus('OCR du fichier impossible.', true);
    }
  };

  const requestEditOcrMarkdown = async (folder, file) => {
    if (
      typeof readWorkspaceOcrMarkdownOnServer !== 'function'
      || typeof saveWorkspaceOcrMarkdownOnServer !== 'function'
      || typeof refreshWorkspaceFiles !== 'function'
    ) {
      setThreadStatus('Édition OCR indisponible.', true);
      return;
    }
    try {
      const payload = await readWorkspaceOcrMarkdownOnServer(folder.id, file.id);
      openOcrMarkdownEditor({
        folder,
        file,
        content: String(payload?.content || ''),
      });
    } catch (err) {
      logger.warn('Lecture Markdown OCR échouée', err);
      setThreadStatus('Ouverture du Markdown OCR impossible.', true);
    }
  };

  const openOcrMarkdownEditor = ({ folder, file, content }) => {
    if (typeof document === 'undefined') return;
    const overlay = document.createElement('div');
    overlay.className = 'workspace-ocr-editor-overlay';
    const panel = document.createElement('div');
    panel.className = 'workspace-ocr-editor-panel';

    const title = document.createElement('div');
    title.className = 'workspace-ocr-editor-title';
    title.textContent = file.display_name || 'OCR Markdown';
    panel.appendChild(title);

    const note = document.createElement('div');
    note.className = 'workspace-ocr-editor-note';
    note.textContent = 'Extraction OCR imparfaite, surtout pour le manuscrit.';
    panel.appendChild(note);

    const textarea = document.createElement('textarea');
    textarea.className = 'workspace-ocr-editor-textarea';
    textarea.value = String(content || '');
    textarea.spellcheck = true;
    panel.appendChild(textarea);

    const actions = document.createElement('div');
    actions.className = 'workspace-ocr-editor-actions';

    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.textContent = 'Annuler';
    cancel.addEventListener('click', () => overlay.remove());
    actions.appendChild(cancel);

    const save = document.createElement('button');
    save.type = 'button';
    save.className = 'workspace-ocr-editor-save';
    save.textContent = 'Enregistrer';
    save.addEventListener('click', async () => {
      save.disabled = true;
      try {
        await saveWorkspaceOcrMarkdownOnServer(folder.id, file.id, textarea.value);
        await refreshWorkspaceFiles(folder.id);
        overlay.remove();
        renderThreads();
        setThreadStatus('Markdown OCR enregistré.');
      } catch (err) {
        save.disabled = false;
        logger.warn('Sauvegarde Markdown OCR échouée', err);
        setThreadStatus('Sauvegarde du Markdown OCR impossible.', true);
      }
    });
    actions.appendChild(save);
    panel.appendChild(actions);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    textarea.focus();
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

  const appendNoFoldersEmpty = () => {
    const empty = document.createElement('li');
    empty.className = 'workspace-folder-empty workspace-folder-empty-global';
    empty.textContent = 'Aucun répertoire';
    threadsUl.appendChild(empty);
  };

  const appendFolderRow = (folder, folderThreads, index, appendThreadRow) => {
    const folders = getWorkspaceFolders();
    const li = document.createElement('li');
    const collapsed = isFolderCollapsed(folder.id);
    li.className = 'workspace-folder-row';
    if (collapsed) li.classList.add('workspace-folder-collapsed');
    li.title = folder.description || folder.display_name;
    li.dataset.workspaceFolderId = folder.id;

    const main = document.createElement('div');
    main.className = 'workspace-folder-main';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'workspace-folder-toggle';
    toggle.title = collapsed ? 'Déplier le répertoire' : 'Replier le répertoire';
    toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    toggle.textContent = collapsed ? '▸' : '▾';
    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      toggleFolderCollapsed(folder.id);
    });
    main.appendChild(toggle);

    const icon = document.createElement('span');
    icon.className = 'workspace-folder-icon';
    icon.title = folder.icon_label || 'Dossier';
    icon.innerHTML = folder.icon_svg || '';
    if (!icon.innerHTML) icon.textContent = folder.icon_label || 'Dossier';
    main.appendChild(icon);

    const name = document.createElement('span');
    name.className = 'workspace-folder-name';
    name.textContent = folder.display_name;
    main.appendChild(name);

    const count = document.createElement('span');
    count.className = 'workspace-folder-count';
    count.textContent = String(folderThreads.length);
    main.appendChild(count);

    const syncLabel = WorkspaceFolderUiHelpers?.workspaceFolderNextcloudStatusLabel?.(folder) || '';
    if (syncLabel) {
      const sync = document.createElement('span');
      sync.className = 'workspace-folder-sync-state';
      sync.textContent = syncLabel;
      sync.title = syncLabel;
      main.appendChild(sync);
    }

    const actions = document.createElement('span');
    actions.className = 'workspace-folder-actions';
    const actionSpecs = [
      ['↑', 'Monter', index === 0, () => reorder(folder.id, -1)],
      ['↓', 'Descendre', index >= folders.length - 1, () => reorder(folder.id, 1)],
      ['+F', 'Ajouter un fichier au répertoire', false, () => requestUploadFile(folder)],
      ['··', 'Renommer', false, () => requestRename(folder)],
      ['×', 'Supprimer', false, () => requestDelete(folder)],
    ];
    if (notesPanel?.requestCreateNote) {
      actionSpecs.splice(3, 0, ['+N', 'Créer une note dans le répertoire', false, () => notesPanel.requestCreateNote(folder)]);
    }
    actionSpecs.forEach(([text, title, disabled, handler]) => {
      const btn = document.createElement('button');
      btn.className = 'workspace-folder-action';
      btn.title = title;
      btn.textContent = text;
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

    appendFileRows(folder);
    notesPanel?.appendNoteRows(folder);
    exportsPanel?.appendExportRows(folder);
    generatedImagesPanel?.appendGeneratedImageRows(folder);

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
    const li = document.createElement('li');
    li.className = 'workspace-folder-files';
    if (!files.length) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-file-empty';
      empty.textContent = 'Aucun fichier';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }
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

      const statusLabel = WorkspaceFolderUiHelpers?.workspaceFileStatusLabel?.(file) || '';
      if (selection?.selection_status === 'stale' || statusLabel) {
        const stale = document.createElement('span');
        stale.className = 'workspace-folder-file-state';
        stale.textContent = selection?.selection_status === 'stale' ? 'Sélection invalide' : statusLabel;
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

      if (WorkspaceFolderUiHelpers?.canRunWorkspaceOcr?.(file)) {
        const ocr = document.createElement('button');
        ocr.type = 'button';
        ocr.className = 'workspace-folder-file-ocr';
        ocr.textContent = 'OCR';
        ocr.title = 'Extraire le texte en Markdown';
        ocr.addEventListener('click', (event) => {
          event.stopPropagation();
          void requestOcrFile(folder, file);
        });
        row.appendChild(ocr);
      }

      if (WorkspaceFolderUiHelpers?.canEditWorkspaceOcrMarkdown?.(file)) {
        const edit = document.createElement('button');
        edit.type = 'button';
        edit.className = 'workspace-folder-file-edit';
        edit.textContent = 'Md';
        edit.title = 'Éditer le Markdown OCR';
        edit.addEventListener('click', (event) => {
          event.stopPropagation();
          void requestEditOcrMarkdown(folder, file);
        });
        row.appendChild(edit);
      }
      li.appendChild(row);
    });
    threadsUl.appendChild(li);
  };

  return Object.freeze({
    appendToolbar,
    appendNoFoldersEmpty,
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
