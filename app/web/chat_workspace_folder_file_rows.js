'use strict';

const WorkspaceFolderFileRowUiHelpers = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolders
    ? window.FridaWorkspaceFolders
    : (typeof require !== 'undefined' ? require('./chat_workspace_folders.js') : null)
);

function createWorkspaceFolderFileRowsRenderer({
  threadsUl,
  documentObj,
  uiHelpers = WorkspaceFolderFileRowUiHelpers,
  getWorkspaceFiles,
  getWorkspaceFilesStatus,
  getCurrentThread,
  getWorkspaceFileSelections,
  onToggleSelection,
  onDeleteFile,
  onOcrFile,
  onEditOcrMarkdown,
} = {}) {
  const doc = documentObj || (typeof document !== 'undefined' ? document : null);

  const appendFileRows = (folder) => {
    const files = typeof getWorkspaceFiles === 'function' ? getWorkspaceFiles(folder.id) : [];
    const li = doc.createElement('li');
    li.className = 'workspace-folder-files';
    const fileStatus = typeof getWorkspaceFilesStatus === 'function'
      ? getWorkspaceFilesStatus(folder.id)
      : null;
    if (fileStatus?.status === 'error') {
      const error = doc.createElement('div');
      error.className = 'workspace-folder-file-error';
      error.textContent = 'Chargement des fichiers impossible';
      if (fileStatus.reason_code) {
        error.dataset.reasonCode = String(fileStatus.reason_code);
      }
      li.appendChild(error);
      threadsUl.appendChild(li);
      return;
    }
    if (!files.length) {
      const empty = doc.createElement('div');
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
      const row = doc.createElement('div');
      row.className = 'workspace-folder-file';
      if (selected) row.classList.add('selected');
      if (file.status && file.status !== 'active') {
        row.dataset.status = file.status;
      }
      if (selection?.selection_status === 'stale') {
        row.dataset.selection = 'stale';
      }

      const toggle = doc.createElement('input');
      toggle.type = 'checkbox';
      toggle.className = 'workspace-folder-file-select';
      toggle.title = 'Sélectionner pour cette conversation';
      toggle.checked = selected;
      toggle.disabled = !canSelect || file.status === 'deleted' || file.status === 'disk_missing';
      toggle.addEventListener('click', (event) => event.stopPropagation());
      toggle.addEventListener('change', (event) => {
        event.stopPropagation();
        void onToggleSelection(folder, file, toggle.checked);
      });
      row.appendChild(toggle);

      const name = doc.createElement('span');
      name.className = 'workspace-folder-file-name';
      name.textContent = file.display_name || 'fichier';
      row.appendChild(name);

      const meta = doc.createElement('span');
      meta.className = 'workspace-folder-file-meta';
      meta.textContent = uiHelpers?.compactWorkspaceFileMeta
        ? uiHelpers.compactWorkspaceFileMeta(file)
        : '';
      row.appendChild(meta);

      const statusLabel = uiHelpers?.workspaceFileStatusLabel?.(file) || '';
      if (selection?.selection_status === 'stale' || statusLabel) {
        const stale = doc.createElement('span');
        stale.className = 'workspace-folder-file-state';
        stale.textContent = selection?.selection_status === 'stale' ? 'Sélection invalide' : statusLabel;
        row.appendChild(stale);
      }

      const del = doc.createElement('button');
      del.type = 'button';
      del.className = 'workspace-folder-file-delete';
      del.textContent = '×';
      del.title = 'Supprimer le fichier';
      del.addEventListener('click', (event) => {
        event.stopPropagation();
        void onDeleteFile(folder, file);
      });
      row.appendChild(del);

      if (uiHelpers?.canRunWorkspaceOcr?.(file)) {
        const ocr = doc.createElement('button');
        ocr.type = 'button';
        ocr.className = 'workspace-folder-file-ocr';
        ocr.textContent = 'OCR';
        ocr.title = 'Extraire le texte en Markdown';
        ocr.addEventListener('click', (event) => {
          event.stopPropagation();
          void onOcrFile(folder, file);
        });
        row.appendChild(ocr);
      }

      if (uiHelpers?.canEditWorkspaceOcrMarkdown?.(file)) {
        const edit = doc.createElement('button');
        edit.type = 'button';
        edit.className = 'workspace-folder-file-edit';
        edit.textContent = 'Md';
        edit.title = 'Éditer le Markdown OCR';
        edit.addEventListener('click', (event) => {
          event.stopPropagation();
          void onEditOcrMarkdown(folder, file);
        });
        row.appendChild(edit);
      }
      li.appendChild(row);
    });
    threadsUl.appendChild(li);
  };

  return Object.freeze({ appendFileRows });
}

const FridaWorkspaceFolderFileRowsModule = Object.freeze({
  createWorkspaceFolderFileRowsRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderFileRowsModule;
}
