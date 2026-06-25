'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const NotesMode = require('../../../web/chat_notes_mode.js');
const {
  createWorkspaceFolderNotesPanelRenderer,
} = require('../../../web/chat_workspace_folder_notes_panel.js');

function makeElement(tagName = 'div') {
  const listeners = new Map();
  const classes = new Set();
  const element = {
    tagName: String(tagName || 'div').toUpperCase(),
    children: [],
    parentElement: null,
    style: {},
    dataset: {},
    className: '',
    textContent: '',
    type: '',
    title: '',
    disabled: false,
    value: '',
    events: listeners,
    classList: {
      add(name) {
        classes.add(name);
        element.className = Array.from(classes).join(' ');
      },
      remove(name) {
        classes.delete(name);
        element.className = Array.from(classes).join(' ');
      },
      contains(name) {
        return classes.has(name);
      },
    },
    appendChild(child) {
      child.parentElement = element;
      element.children.push(child);
      return child;
    },
    addEventListener(type, handler) {
      const key = String(type || '');
      const current = listeners.get(key) || [];
      current.push(handler);
      listeners.set(key, current);
    },
    click() {
      if (element.disabled) return;
      for (const handler of listeners.get('click') || []) {
        handler({
          stopPropagation() {},
          preventDefault() {},
          target: element,
        });
      }
    },
    setAttribute(name, value) {
      element[name] = value;
    },
  };
  return element;
}

function installDom() {
  global.document = {
    createElement: makeElement,
  };
}

function walk(node) {
  const items = [];
  const visit = (current) => {
    if (!current) return;
    items.push(current);
    for (const child of current.children || []) visit(child);
  };
  visit(node);
  return items;
}

function byClass(root, className) {
  return walk(root).filter((node) =>
    String(node.className || '').split(/\s+/).includes(className)
  );
}

function firstByClass(root, className) {
  return byClass(root, className)[0] || null;
}

function visibleText(root) {
  return walk(root).map((node) => String(node.textContent || '')).join(' ');
}

async function flushAsync() {
  await new Promise((resolve) => setImmediate(resolve));
  await Promise.resolve();
}

function linkedFolder(overrides = {}) {
  return {
    id: 'folder-1',
    display_name: 'Projet',
    nextcloud_sync_state: 'linked',
    deleted_at: null,
    ...overrides,
  };
}

function noteItem(overrides = {}) {
  return NotesMode.normalizeWorkspaceNoteItem({
    note_v1_user: {
      note_id: 'note-1',
      workspace_folder_id: 'folder-1',
      title: 'Note visible',
      sync_label: 'synchro',
      markdown_char_count: 120,
      ...overrides,
    },
  });
}

function buildPanel({
  folder = linkedFolder(),
  notes = [],
  noteStatus = { status: 'ok', reason_code: 'workspace_notes_list_ok' },
  currentThread = { id: 'conv-1', workspace_folder_id: 'folder-1' },
  prompts = [],
} = {}) {
  installDom();
  const threadsUl = makeElement('ul');
  const created = [];
  const prepared = [];
  const selected = [];
  const statuses = [];
  let refreshCount = 0;
  global.window = {
    prompt: () => prompts.shift() ?? '',
  };
  const notesController = {
    setSelectedNote(note, selectedFolder) {
      selected.push({ note, folder: selectedFolder });
    },
    getSelectedNoteId: () => selected[selected.length - 1]?.note?.id || '',
    getSelectedFolderId: () => selected[selected.length - 1]?.folder?.id || '',
  };
  const panel = createWorkspaceFolderNotesPanelRenderer({
    threadsUl,
    getWorkspaceNotes: () => notes,
    getWorkspaceNotesStatus: () => noteStatus,
    refreshWorkspaceNotes: async () => {
      refreshCount += 1;
      return notes;
    },
    createWorkspaceNoteOnServer: async (folderId, payload) => {
      created.push({ folderId, payload });
      return noteItem({ note_id: 'created-note', title: payload.title });
    },
    prepareWorkspaceNoteOnServer: async (folderId, noteId) => {
      prepared.push({ folderId, noteId });
      return { ok: true };
    },
    getCurrentThread: () => currentThread,
    notesModeController: notesController,
    renderThreads: () => {},
    setThreadStatus: (message, isError = false) => statuses.push({ message, isError }),
    consoleObj: { warn() {} },
  });
  panel.appendNoteRows(folder);
  return {
    threadsUl,
    created,
    prepared,
    selected,
    statuses,
    refreshCount: () => refreshCount,
  };
}

test('notes panel renders API errors as visible errors instead of empty lists', () => {
  const rendered = buildPanel({
    noteStatus: { status: 'error', reason_code: 'workspace_notes_store_unavailable' },
  });

  assert.equal(firstByClass(rendered.threadsUl, 'workspace-folder-note-empty'), null);
  const error = firstByClass(rendered.threadsUl, 'workspace-folder-note-error');
  assert.ok(error);
  assert.equal(error.dataset.reasonCode, 'workspace_notes_store_unavailable');
  assert.match(visibleText(rendered.threadsUl), /Chargement des notes impossible/);
});

test('notes panel creates an empty note through the existing backend route contract', async () => {
  const rendered = buildPanel({ prompts: ['Plan Lot 5B'] });
  const create = firstByClass(rendered.threadsUl, 'workspace-folder-note-create');

  create.click();
  await flushAsync();

  assert.equal(rendered.created.length, 1);
  assert.deepEqual(rendered.created[0], {
    folderId: 'folder-1',
    payload: { title: 'Plan Lot 5B', markdown: '' },
  });
  assert.equal(rendered.refreshCount(), 1);
  assert.equal(rendered.selected[0].note.id, 'created-note');
});

test('notes panel prepares and selects a note only inside the current folder conversation', async () => {
  const rendered = buildPanel({ notes: [noteItem()] });
  const prepare = firstByClass(rendered.threadsUl, 'workspace-folder-note-action-prepare');
  const select = firstByClass(rendered.threadsUl, 'workspace-folder-note-action-select');

  select.click();
  prepare.click();
  await flushAsync();

  assert.equal(rendered.selected.length, 2);
  assert.deepEqual(rendered.prepared, [{ folderId: 'folder-1', noteId: 'note-1' }]);
  assert.equal(rendered.statuses.some((item) => item.message.includes('Note préparée')), true);

  const outside = buildPanel({
    notes: [noteItem()],
    currentThread: { id: 'conv-2', workspace_folder_id: 'other-folder' },
  });
  firstByClass(outside.threadsUl, 'workspace-folder-note-action-select').click();
  assert.equal(outside.selected.length, 0);
  assert.equal(outside.statuses[0].isError, true);
});
