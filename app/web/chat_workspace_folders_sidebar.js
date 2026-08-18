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
const WorkspaceFolderArtifactPanels = (
  typeof FridaWorkspaceFolderArtifactPanelsModule !== 'undefined'
    ? FridaWorkspaceFolderArtifactPanelsModule
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_artifact_panels.js') : null)
);
const WorkspaceFolderFileRows = (
  typeof FridaWorkspaceFolderFileRowsModule !== 'undefined'
    ? FridaWorkspaceFolderFileRowsModule
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_file_rows.js') : null)
);
const WorkspaceFolderTreeRenderer = (
  typeof FridaWorkspaceFolderTreeRendererModule !== 'undefined'
    ? FridaWorkspaceFolderTreeRendererModule
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_tree_renderer.js') : null)
);

function createWorkspaceFolderSidebarRenderer({
  threadsUl,
  getWorkspaceFolders,
  getWorkspaceFiles,
  getWorkspaceFilesStatus,
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
  const artifactPanels = WorkspaceFolderArtifactPanels.createWorkspaceFolderArtifactPanels({
    notesPanel,
    exportsPanel,
    generatedImagesPanel,
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

  const fileRowsRenderer = WorkspaceFolderFileRows.createWorkspaceFolderFileRowsRenderer({
    threadsUl,
    getWorkspaceFiles,
    getWorkspaceFilesStatus,
    getCurrentThread,
    getWorkspaceFileSelections,
    onToggleSelection: requestToggleSelection,
    onDeleteFile: requestDeleteFile,
    onOcrFile: requestOcrFile,
    onEditOcrMarkdown: requestEditOcrMarkdown,
  });
  const folderTreeRenderer = WorkspaceFolderTreeRenderer.createWorkspaceFolderTreeRenderer({
    threadsUl,
    getWorkspaceFolders,
    isFolderCollapsed,
    toggleFolderCollapsed,
    onCreate: requestCreate,
    onReorder: reorder,
    onUploadFile: requestUploadFile,
    onRename: requestRename,
    onDelete: requestDelete,
    fileRowsRenderer,
    artifactPanels,
    bindConversationDropTarget,
  });
  const {
    appendToolbar,
    appendNoFoldersEmpty,
    appendFolderRow,
  } = folderTreeRenderer;

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
