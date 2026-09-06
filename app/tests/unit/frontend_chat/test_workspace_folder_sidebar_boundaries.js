'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

function optionalRequire(modulePath, expectedName) {
  try {
    return require(modulePath);
  } catch (error) {
    if (error?.code === 'MODULE_NOT_FOUND' && String(error.message || '').includes(expectedName)) {
      return {};
    }
    throw error;
  }
}

const { createWorkspaceFolderFileRowsRenderer } = optionalRequire(
  '../../../web/chat_workspace_folder_file_rows.js',
  'chat_workspace_folder_file_rows.js',
);
const { createWorkspaceFolderArtifactPanels } = optionalRequire(
  '../../../web/chat_workspace_folder_artifact_panels.js',
  'chat_workspace_folder_artifact_panels.js',
);
const { createWorkspaceFolderTreeRenderer } = optionalRequire(
  '../../../web/chat_workspace_folder_tree_renderer.js',
  'chat_workspace_folder_tree_renderer.js',
);
const { createWorkspaceFolderSidebarRenderer } = optionalRequire(
  '../../../web/chat_workspace_folders_sidebar.js',
  'chat_workspace_folders_sidebar.js',
);

function makeElement(tagName = 'div') {
  const classes = new Set();
  const listeners = new Map();
  const element = {
    tagName: String(tagName).toUpperCase(),
    children: [],
    className: '',
    dataset: {},
    style: {},
    textContent: '',
    disabled: false,
    checked: false,
    listeners,
    classList: {
      add(...names) {
        String(element.className || '').split(/\s+/).filter(Boolean).forEach((name) => classes.add(name));
        names.forEach((name) => classes.add(name));
        element.className = Array.from(classes).join(' ');
      },
      remove(...names) {
        String(element.className || '').split(/\s+/).filter(Boolean).forEach((name) => classes.add(name));
        names.forEach((name) => classes.delete(name));
        element.className = Array.from(classes).join(' ');
      },
      contains(name) {
        return classes.has(name)
          || String(element.className || '').split(/\s+/).filter(Boolean).includes(name);
      },
    },
    appendChild(child) {
      child.parentNode = element;
      element.children.push(child);
      return child;
    },
    addEventListener(type, handler) {
      listeners.set(type, [...(listeners.get(type) || []), handler]);
    },
    setAttribute(name, value) { element[name] = String(value); },
  };
  let html = '';
  Object.defineProperty(element, 'innerHTML', {
    get() { return html; },
    set(value) { html = String(value || ''); },
  });
  return element;
}

const documentObj = { createElement: makeElement };

function walk(root) {
  const nodes = [];
  const visit = (node) => {
    nodes.push(node);
    (node.children || []).forEach(visit);
  };
  visit(root);
  return nodes;
}

function byClass(root, className) {
  return walk(root).filter((node) => node.classList?.contains(className));
}

function click(node) {
  const event = { stopPropagation() {}, target: { closest: () => null } };
  return node.listeners.get('click')[0](event);
}

async function waitFor(predicate, message) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (predicate()) return;
    await new Promise((resolve) => setImmediate(resolve));
  }
  assert.fail(message);
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function buildOcrSidebar({ files, confirmResult = true, ocrResult }) {
  const threadsUl = makeElement('ul');
  const statuses = [];
  const confirmations = [];
  const ocrCalls = [];
  const folder = {
    id: 'folder-1',
    display_name: 'Projet',
    nextcloud_sync_state: 'local_only',
  };
  global.document = {
    body: makeElement('body'),
    createElement: makeElement,
  };
  global.window = {
    confirm(message) {
      confirmations.push(String(message || ''));
      return confirmResult;
    },
  };
  const renderer = createWorkspaceFolderSidebarRenderer({
    threadsUl,
    getWorkspaceFolders: () => [folder],
    getWorkspaceFiles: () => files,
    getWorkspaceFilesStatus: () => ({ status: 'ok' }),
    getWorkspaceExports: () => [],
    getWorkspaceExportsStatus: () => ({ status: 'ok' }),
    getWorkspaceGeneratedImages: () => [],
    getWorkspaceGeneratedImagesStatus: () => ({ status: 'ok' }),
    getWorkspaceNotes: () => [],
    getWorkspaceNotesStatus: () => ({ status: 'ok' }),
    refreshThreadsFromServer: async () => {},
    refreshWorkspaceFiles: async () => {},
    refreshWorkspaceExports: async () => {},
    refreshWorkspaceGeneratedImages: async () => {},
    refreshWorkspaceNotes: async () => {},
    renderThreads: () => {},
    setThreadStatus: (message, isError = false) => statuses.push({ message, isError }),
    ocrWorkspaceFileOnServer: (folderId, fileId) => {
      ocrCalls.push({ folderId, fileId });
      return typeof ocrResult === 'function' ? ocrResult() : ocrResult;
    },
    getCurrentThread: () => null,
    getWorkspaceFileSelections: () => [],
    bindConversationDropTarget: () => {},
    consoleObj: { warn() {} },
  });
  renderer.appendFolderRow(folder, [], 0, () => {});
  click(byClass(threadsUl, 'workspace-folder-toggle')[0]);
  threadsUl.children = [];
  renderer.appendFolderRow(folder, [], 0, () => {});
  return {
    confirmations,
    ocrButton: byClass(threadsUl, 'workspace-folder-file-ocr')[0],
    ocrCalls,
    statuses,
  };
}

function sourcePdf() {
  return {
    id: 'source-pdf',
    workspace_folder_id: 'folder-1',
    display_name: 'scan.pdf',
    mime_type: 'application/pdf',
    source_extension: '.pdf',
    status: 'ocr_required',
    source_kind: 'upload',
  };
}

function derivedMarkdown() {
  return {
    id: 'derived-md',
    workspace_folder_id: 'folder-1',
    display_name: 'scan.ocr.md',
    mime_type: 'text/markdown',
    source_extension: '.md',
    status: 'active',
    source_kind: 'ocr_derived',
    source_file_id: 'source-pdf',
  };
}

test('first workspace OCR posts once without replacement warning and reports creation', async (t) => {
  t.after(() => {
    delete global.document;
    delete global.window;
  });
  const ui = buildOcrSidebar({
    files: [sourcePdf()],
    ocrResult: Promise.resolve({ status: 201, file: derivedMarkdown() }),
  });

  click(ui.ocrButton);
  await waitFor(() => ui.statuses.length > 0, 'first OCR did not publish its final status');

  assert.equal(ui.confirmations.length, 0);
  assert.deepEqual(ui.ocrCalls, [{ folderId: 'folder-1', fileId: 'source-pdf' }]);
  assert.deepEqual(ui.statuses.at(-1), {
    message: 'Markdown OCR créé dans le répertoire.',
    isError: false,
  });
});

test('cancelled workspace re-OCR warns about manual corrections and sends no POST', async (t) => {
  t.after(() => {
    delete global.document;
    delete global.window;
  });
  const ui = buildOcrSidebar({
    files: [sourcePdf(), derivedMarkdown()],
    confirmResult: false,
    ocrResult: Promise.resolve({ status: 200, file: derivedMarkdown() }),
  });

  click(ui.ocrButton);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(ui.confirmations.length, 1);
  assert.match(ui.confirmations[0], /remplacera le Markdown OCR actuel/i);
  assert.match(ui.confirmations[0], /corrections manuelles/i);
  assert.deepEqual(ui.ocrCalls, []);
  assert.deepEqual(ui.statuses, []);
});

test('confirmed workspace re-OCR sends one POST and reports the HTTP 200 update', async (t) => {
  t.after(() => {
    delete global.document;
    delete global.window;
  });
  const pending = deferred();
  const ui = buildOcrSidebar({
    files: [sourcePdf(), derivedMarkdown()],
    confirmResult: true,
    ocrResult: () => pending.promise,
  });

  click(ui.ocrButton);
  click(ui.ocrButton);
  assert.equal(ui.confirmations.length, 1);
  assert.deepEqual(ui.ocrCalls, [{ folderId: 'folder-1', fileId: 'source-pdf' }]);
  pending.resolve({ status: 200, file: derivedMarkdown() });
  await waitFor(() => ui.statuses.length > 0, 're-OCR did not publish its final status');

  assert.deepEqual(ui.statuses.at(-1), {
    message: 'Markdown OCR mis à jour dans le répertoire.',
    isError: false,
  });
});

test('failed workspace OCR never publishes a creation or update success', async (t) => {
  t.after(() => {
    delete global.document;
    delete global.window;
  });
  const ui = buildOcrSidebar({
    files: [sourcePdf()],
    ocrResult: Promise.reject(new Error('synthetic OCR failure')),
  });

  click(ui.ocrButton);
  await waitFor(() => ui.statuses.length > 0, 'failed OCR did not publish its error status');

  assert.equal(ui.statuses.some(({ message }) => /créé|mis à jour/i.test(message)), false);
  assert.deepEqual(ui.statuses.at(-1), {
    message: 'OCR du fichier impossible.',
    isError: true,
  });
});

test('file rows keep API error distinct from a normal empty list', () => {
  assert.equal(typeof createWorkspaceFolderFileRowsRenderer, 'function');

  const errorList = makeElement('ul');
  const errorRenderer = createWorkspaceFolderFileRowsRenderer({
    threadsUl: errorList,
    documentObj,
    getWorkspaceFiles: () => [],
    getWorkspaceFilesStatus: () => ({ status: 'error', reason_code: 'workspace_files_lookup_failed' }),
  });
  errorRenderer.appendFileRows({ id: 'folder-1' });

  assert.equal(byClass(errorList, 'workspace-folder-file-empty').length, 0);
  assert.equal(byClass(errorList, 'workspace-folder-file-error').length, 1);
  assert.equal(byClass(errorList, 'workspace-folder-file-error')[0].dataset.reasonCode, 'workspace_files_lookup_failed');

  const emptyList = makeElement('ul');
  const emptyRenderer = createWorkspaceFolderFileRowsRenderer({
    threadsUl: emptyList,
    documentObj,
    getWorkspaceFiles: () => [],
    getWorkspaceFilesStatus: () => ({ status: 'ok', reason_code: 'workspace_files_list_ok' }),
  });
  emptyRenderer.appendFileRows({ id: 'folder-1' });

  assert.equal(byClass(emptyList, 'workspace-folder-file-error').length, 0);
  assert.equal(byClass(emptyList, 'workspace-folder-file-empty')[0].textContent, 'Aucun fichier');
});

test('file rows preserve selection state and delegate each available action once', async () => {
  assert.equal(typeof createWorkspaceFolderFileRowsRenderer, 'function');

  const threadsUl = makeElement('ul');
  const actions = [];
  const files = [
    { id: 'file-ocr', display_name: 'scan.pdf', status: 'ocr_required' },
    { id: 'file-md', display_name: 'scan.ocr.md', status: 'active', source_kind: 'ocr_derived' },
  ];
  const renderer = createWorkspaceFolderFileRowsRenderer({
    threadsUl,
    documentObj,
    uiHelpers: {
      compactWorkspaceFileMeta: (file) => `meta:${file.id}`,
      workspaceFileStatusLabel: (file) => (file.id === 'file-ocr' ? 'OCR requis' : ''),
      canRunWorkspaceOcr: (file) => file.id === 'file-ocr',
      canEditWorkspaceOcrMarkdown: (file) => file.id === 'file-md',
    },
    getWorkspaceFiles: () => files,
    getWorkspaceFilesStatus: () => ({ status: 'ok' }),
    getCurrentThread: () => ({ id: 'conv-1', workspace_folder_id: 'folder-1' }),
    getWorkspaceFileSelections: () => [{
      workspace_file_id: 'file-ocr',
      selected: true,
      selection_status: 'active',
    }],
    onToggleSelection: (_folder, file, selected) => actions.push(['select', file.id, selected]),
    onDeleteFile: (_folder, file) => actions.push(['delete', file.id]),
    onOcrFile: (_folder, file) => actions.push(['ocr', file.id]),
    onEditOcrMarkdown: (_folder, file) => actions.push(['edit', file.id]),
  });
  renderer.appendFileRows({ id: 'folder-1' });

  const rows = byClass(threadsUl, 'workspace-folder-file');
  assert.equal(rows.length, 2);
  assert.equal(rows[0].classList.contains('selected'), true);
  const toggles = byClass(threadsUl, 'workspace-folder-file-select');
  assert.equal(toggles[0].checked, true);
  assert.equal(toggles[0].disabled, false);
  toggles[0].checked = false;
  await toggles[0].listeners.get('change')[0]({ stopPropagation() {} });
  await click(byClass(threadsUl, 'workspace-folder-file-delete')[0]);
  await click(byClass(threadsUl, 'workspace-folder-file-ocr')[0]);
  await click(byClass(threadsUl, 'workspace-folder-file-edit')[0]);

  assert.deepEqual(actions, [
    ['select', 'file-ocr', false],
    ['delete', 'file-ocr'],
    ['ocr', 'file-ocr'],
    ['edit', 'file-md'],
  ]);
});

test('artifact panel composition preserves Notes Exports Images order and note creation', () => {
  assert.equal(typeof createWorkspaceFolderArtifactPanels, 'function');

  const calls = [];
  const panels = createWorkspaceFolderArtifactPanels({
    notesPanel: {
      appendNoteRows: (folder) => calls.push(['notes', folder.id]),
      requestCreateNote: (folder) => calls.push(['create-note', folder.id]),
    },
    exportsPanel: {
      appendExportRows: (folder) => calls.push(['exports', folder.id]),
    },
    generatedImagesPanel: {
      appendGeneratedImageRows: (folder) => calls.push(['images', folder.id]),
    },
  });

  panels.appendRows({ id: 'folder-1' });
  panels.requestCreateNote({ id: 'folder-1' });

  assert.deepEqual(calls, [
    ['notes', 'folder-1'],
    ['exports', 'folder-1'],
    ['images', 'folder-1'],
    ['create-note', 'folder-1'],
  ]);
});

test('folder tree keeps collapsed children absent and expanded children ordered', () => {
  assert.equal(typeof createWorkspaceFolderTreeRenderer, 'function');

  const folder = { id: 'folder-1', display_name: 'Projet', icon_label: 'Dossier' };
  const threadsUl = makeElement('ul');
  const childOrder = [];
  let collapsed = true;
  const renderer = createWorkspaceFolderTreeRenderer({
    threadsUl,
    documentObj,
    getWorkspaceFolders: () => [folder],
    isFolderCollapsed: () => collapsed,
    toggleFolderCollapsed: () => {},
    fileRowsRenderer: { appendFileRows: () => childOrder.push('files') },
    artifactPanels: { appendRows: () => childOrder.push('artifacts'), requestCreateNote: null },
    bindConversationDropTarget: () => {},
  });

  renderer.appendFolderRow(folder, [{ id: 'conv-1' }], 0, () => childOrder.push('thread'));
  assert.deepEqual(childOrder, []);
  assert.equal(byClass(threadsUl, 'workspace-folder-collapsed').length, 1);

  collapsed = false;
  renderer.appendFolderRow(folder, [{ id: 'conv-1' }], 0, () => childOrder.push('thread'));
  assert.deepEqual(childOrder, ['files', 'artifacts', 'thread']);
});

test('folder tree delegates enabled folder actions exactly once', async () => {
  assert.equal(typeof createWorkspaceFolderTreeRenderer, 'function');

  const folder = { id: 'folder-1', display_name: 'Projet', icon_label: 'Dossier' };
  const other = { id: 'folder-2', display_name: 'Autre', icon_label: 'Dossier' };
  const threadsUl = makeElement('ul');
  const actions = [];
  const renderer = createWorkspaceFolderTreeRenderer({
    threadsUl,
    documentObj,
    getWorkspaceFolders: () => [folder, other],
    isFolderCollapsed: () => true,
    toggleFolderCollapsed: () => actions.push(['toggle']),
    onCreate: () => actions.push(['create']),
    onReorder: (_id, direction) => actions.push(['reorder', direction]),
    onUploadFile: () => actions.push(['upload']),
    onRename: () => actions.push(['rename']),
    onDelete: () => actions.push(['delete']),
    fileRowsRenderer: { appendFileRows() {} },
    artifactPanels: {
      appendRows() {},
      requestCreateNote: () => actions.push(['note']),
    },
    bindConversationDropTarget: () => {},
  });

  renderer.appendToolbar();
  renderer.appendFolderRow(folder, [], 0, () => {});
  await click(byClass(threadsUl, 'workspace-folder-add')[0]);
  const folderActions = byClass(threadsUl, 'workspace-folder-action');
  assert.deepEqual(folderActions.map((button) => [button.title, button.disabled]), [
    ['Monter', true],
    ['Descendre', false],
    ['Ajouter un fichier au répertoire', false],
    ['Créer une note dans le répertoire', false],
    ['Renommer', false],
    ['Supprimer', false],
  ]);
  for (const title of [
    'Descendre',
    'Ajouter un fichier au répertoire',
    'Créer une note dans le répertoire',
    'Renommer',
    'Supprimer',
  ]) {
    await click(folderActions.find((button) => button.title === title));
  }

  assert.deepEqual(actions, [
    ['create'],
    ['reorder', 1],
    ['upload'],
    ['note'],
    ['rename'],
    ['delete'],
  ]);
});
