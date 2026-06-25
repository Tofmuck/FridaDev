'use strict';

const WorkspaceFolderExportsPanelUi = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolderExports
    ? window.FridaWorkspaceFolderExports
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_exports.js') : null)
);

function createWorkspaceFolderExportsPanelRenderer({
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
  consoleObj,
} = {}) {
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });

  const promptExportFormat = (defaultFormat = 'md') => {
    const fallback = WorkspaceFolderExportsPanelUi?.normalizeWorkspaceExportFormat?.(defaultFormat) || 'md';
    const raw = typeof window !== 'undefined'
      ? window.prompt('Format export (md, txt, docx, pdf)', fallback)
      : fallback;
    if (raw === null) return '';
    const format = WorkspaceFolderExportsPanelUi?.normalizeWorkspaceExportFormat?.(raw) || '';
    if (!format) {
      setThreadStatus('Format export non supporté.', true);
      return '';
    }
    return format;
  };

  const promptExportTitle = (fallback) => {
    const raw = typeof window !== 'undefined'
      ? window.prompt('Titre de l’export', fallback || 'Export')
      : fallback || 'Export';
    if (raw === null) return null;
    return WorkspaceFolderExportsPanelUi?.normalizeWorkspaceExportTitle?.(raw, fallback || 'Export') || 'Export';
  };

  const canCreateConversationExport = (folder) => {
    const current = typeof getCurrentThread === 'function' ? getCurrentThread() : null;
    return Boolean(
      current?.id
      && current.workspace_folder_id === folder?.id
      && WorkspaceFolderExportsPanelUi?.canLoadWorkspaceExports?.(folder)
    );
  };

  const refreshExportsAndRender = async (folder) => {
    if (typeof refreshWorkspaceExports === 'function') {
      await refreshWorkspaceExports(folder.id);
    }
    renderThreads();
  };

  const requestCreateConversationExport = async (folder) => {
    const current = typeof getCurrentThread === 'function' ? getCurrentThread() : null;
    if (!WorkspaceFolderExportsPanelUi?.canLoadWorkspaceExports?.(folder)) {
      setThreadStatus('Exports disponibles après synchronisation Nextcloud.', true);
      return;
    }
    if (!current?.id || current.workspace_folder_id !== folder.id) {
      setThreadStatus('Création export disponible depuis une conversation du répertoire.', true);
      return;
    }
    if (typeof createWorkspaceExportOnServer !== 'function') {
      setThreadStatus('Création export indisponible.', true);
      return;
    }
    const format = promptExportFormat('md');
    if (!format) return;
    const title = promptExportTitle(`Conversation ${format.toUpperCase()}`);
    if (title === null) return;
    const payload = WorkspaceFolderExportsPanelUi.buildConversationExportPayload({
      conversationId: current.id,
      exportFormat: format,
      title,
    });
    try {
      await createWorkspaceExportOnServer(folder.id, payload);
      await refreshExportsAndRender(folder);
      setThreadStatus('Export créé dans le répertoire.');
    } catch (err) {
      logger.warn('Création export répertoire échouée', err);
      setThreadStatus(WorkspaceFolderExportsPanelUi.workspaceExportUserError(err?.payload || err), true);
    }
  };

  const requestReuseExport = async (folder, exportItem) => {
    if (!WorkspaceFolderExportsPanelUi?.canLoadWorkspaceExports?.(folder)) {
      setThreadStatus('Exports disponibles après synchronisation Nextcloud.', true);
      return;
    }
    if (!exportItem?.can_reuse_as_source) {
      setThreadStatus(WorkspaceFolderExportsPanelUi?.workspaceExportActionLabel?.(exportItem, 'reuse') || 'Export non réutilisable.', true);
      return;
    }
    if (typeof createWorkspaceExportOnServer !== 'function') {
      setThreadStatus('Réutilisation export indisponible.', true);
      return;
    }
    const format = promptExportFormat(exportItem.format || 'md');
    if (!format) return;
    const title = promptExportTitle(`${exportItem.title || 'Export'} - copie`);
    if (title === null) return;
    const payload = WorkspaceFolderExportsPanelUi.buildReuseExportPayload({
      sourceExportId: exportItem.id,
      exportFormat: format,
      title,
    });
    try {
      await createWorkspaceExportOnServer(folder.id, payload);
      await refreshExportsAndRender(folder);
      setThreadStatus('Export réutilisé comme source.');
    } catch (err) {
      logger.warn('Réutilisation export échouée', err);
      setThreadStatus(WorkspaceFolderExportsPanelUi.workspaceExportUserError(err?.payload || err), true);
    }
  };

  const requestOpenExport = (folder, exportItem) => {
    if (!exportItem?.can_open) {
      setThreadStatus(WorkspaceFolderExportsPanelUi?.workspaceExportActionLabel?.(exportItem, 'open') || 'Ouverture export indisponible.', true);
      return;
    }
    if (typeof openWorkspaceExport === 'function') {
      openWorkspaceExport(folder.id, exportItem.id);
    }
  };

  const requestDownloadExport = (folder, exportItem) => {
    if (!exportItem?.can_download) {
      setThreadStatus(WorkspaceFolderExportsPanelUi?.workspaceExportActionLabel?.(exportItem, 'download') || 'Téléchargement export indisponible.', true);
      return;
    }
    if (typeof downloadWorkspaceExport === 'function') {
      downloadWorkspaceExport(folder.id, exportItem.id);
    }
  };

  const appendExportRows = (folder) => {
    if (!threadsUl || typeof document === 'undefined') return;
    const exportsList = typeof getWorkspaceExports === 'function' ? getWorkspaceExports(folder.id) : [];
    const li = document.createElement('li');
    li.className = 'workspace-folder-exports';

    const header = document.createElement('div');
    header.className = 'workspace-folder-export-header';
    const label = document.createElement('span');
    label.textContent = 'Exports';
    header.appendChild(label);

    const create = document.createElement('button');
    create.type = 'button';
    create.className = 'workspace-folder-export-create';
    create.textContent = '+';
    create.title = canCreateConversationExport(folder)
      ? 'Créer un export depuis cette conversation'
      : 'Créer depuis une conversation ouverte du répertoire';
    create.disabled = !canCreateConversationExport(folder);
    create.addEventListener('click', (event) => {
      event.stopPropagation();
      void requestCreateConversationExport(folder);
    });
    header.appendChild(create);
    li.appendChild(header);

    if (!WorkspaceFolderExportsPanelUi?.canLoadWorkspaceExports?.(folder)) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-export-empty';
      empty.textContent = 'Exports disponibles après synchronisation Nextcloud.';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }

    const exportStatus = typeof getWorkspaceExportsStatus === 'function'
      ? getWorkspaceExportsStatus(folder.id)
      : null;
    if (exportStatus?.status === 'error') {
      const error = document.createElement('div');
      error.className = 'workspace-folder-export-error';
      error.textContent = 'Chargement des exports impossible';
      if (exportStatus.reason_code) {
        error.dataset.reasonCode = String(exportStatus.reason_code);
      }
      li.appendChild(error);
      threadsUl.appendChild(li);
      return;
    }

    if (!exportsList.length) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-export-empty';
      empty.textContent = 'Aucun export';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }

    exportsList.forEach((exportItem) => {
      const row = document.createElement('div');
      row.className = 'workspace-folder-export';
      if (exportItem.status && exportItem.status !== 'available') {
        row.dataset.status = exportItem.status;
      }

      const name = document.createElement('span');
      name.className = 'workspace-folder-export-name';
      name.textContent = exportItem.title || 'Export';
      row.appendChild(name);

      const meta = document.createElement('span');
      meta.className = 'workspace-folder-export-meta';
      meta.textContent = WorkspaceFolderExportsPanelUi?.compactWorkspaceExportMeta?.(exportItem) || '';
      row.appendChild(meta);

      const state = document.createElement('span');
      state.className = 'workspace-folder-export-state';
      state.textContent = exportItem.status === 'available'
        ? ''
        : (WorkspaceFolderExportsPanelUi?.workspaceExportReasonLabel?.(exportItem.reason_code) || '');
      row.appendChild(state);

      [
        ['open', '↗', 'Ouvrir', exportItem.can_open, () => requestOpenExport(folder, exportItem)],
        ['download', '↓', 'Télécharger', exportItem.can_download, () => requestDownloadExport(folder, exportItem)],
        ['reuse', '↺', 'Réutiliser comme source', exportItem.can_reuse_as_source, () => requestReuseExport(folder, exportItem)],
      ].forEach(([action, text, title, enabled, handler]) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `workspace-folder-export-action workspace-folder-export-action-${action}`;
        btn.textContent = text;
        btn.title = enabled
          ? title
          : (WorkspaceFolderExportsPanelUi?.workspaceExportActionLabel?.(exportItem, action) || 'Action indisponible');
        btn.disabled = !enabled;
        btn.addEventListener('click', (event) => {
          event.stopPropagation();
          if (btn.disabled) return;
          void handler();
        });
        row.appendChild(btn);
      });
      li.appendChild(row);
    });

    threadsUl.appendChild(li);
  };

  return Object.freeze({ appendExportRows });
}

const FridaWorkspaceFolderExportsPanel = Object.freeze({
  createWorkspaceFolderExportsPanelRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderExportsPanel;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolderExportsPanel = FridaWorkspaceFolderExportsPanel;
}
