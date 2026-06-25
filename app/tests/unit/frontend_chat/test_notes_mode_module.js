'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const notesMode = require('../../../web/chat_notes_mode.js');

test('notes mode sends a bounded workspace note payload only for the selected folder', () => {
  assert.deepEqual(notesMode.buildNotesChatPayload({ active: false }), { workspace_notes_mode: false });
  assert.deepEqual(
    notesMode.buildNotesChatPayload({
      active: true,
      selectedNoteId: 'note-1',
      selectedFolderId: 'folder-1',
      workspaceFolderId: 'folder-1',
    }),
    { workspace_notes_mode: true, workspace_note_id: 'note-1' },
  );
  assert.deepEqual(
    notesMode.buildNotesChatPayload({
      active: true,
      selectedNoteId: 'note-1',
      selectedFolderId: 'folder-1',
      workspaceFolderId: 'folder-2',
    }),
    { workspace_notes_mode: true },
  );
});

test('notes mode is rendered as a composer mode next to Agenda and loads before app', () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, '../../../web/index.html'), 'utf8');
  const notesIndex = indexHtml.indexOf('id="btnNotesMode"');
  const agendaIndex = indexHtml.indexOf('id="btnAgendaMode"');

  assert.ok(notesIndex > 0, 'Notes button should exist');
  assert.ok(agendaIndex > notesIndex, 'Agenda should stay after Notes');
  assert.ok(indexHtml.includes('class="btn-notes-mode"'));
  assert.ok(indexHtml.includes('aria-label="Activer Notes"'));
  assert.ok(indexHtml.includes('<script src="chat_notes_mode.js"></script>'));
  assert.ok(indexHtml.includes('<script src="chat_workspace_folder_notes_panel.js"></script>'));
  assert.ok(indexHtml.indexOf('chat_notes_mode.js') < indexHtml.indexOf('chat_threads_sidebar.js'));
  assert.ok(indexHtml.indexOf('chat_workspace_folder_notes_panel.js') < indexHtml.indexOf('chat_workspace_folders_sidebar.js'));
});

test('notes mode controller mirrors active and selected note state', () => {
  const events = [];
  const button = createFakeButton();
  const storage = createFakeStorage();
  const controller = notesMode.createNotesModeController({
    buttonEl: button,
    storage,
    onActiveChange: (active) => events.push(active),
  });

  assert.equal(controller.isActive(), false);
  assert.equal(button.getAttribute('aria-pressed'), 'false');

  controller.setSelectedNote({
    note_v1_user: {
      note_id: 'note-42',
      workspace_folder_id: 'folder-7',
      title: 'Plan',
    },
  });

  assert.equal(controller.isActive(), true);
  assert.equal(button.getAttribute('aria-pressed'), 'true');
  assert.equal(button.classList.has('active'), true);
  assert.equal(controller.getSelectedNoteId(), 'note-42');
  assert.deepEqual(
    controller.getPayload({ workspaceFolderId: 'folder-7' }),
    { workspace_notes_mode: true, workspace_note_id: 'note-42' },
  );
  assert.deepEqual(events, [true]);
});

function createFakeStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, String(value)),
  };
}

function createFakeButton() {
  const attrs = new Map();
  const listeners = new Map();
  const classes = new Set();
  return {
    classList: {
      toggle(name, active) {
        if (active) classes.add(name);
        else classes.delete(name);
      },
      has(name) {
        return classes.has(name);
      },
    },
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    getAttribute(name) {
      return attrs.get(name);
    },
    addEventListener(name, handler) {
      listeners.set(name, handler);
    },
    dispatch(name) {
      const handler = listeners.get(name);
      if (handler) handler({});
    },
  };
}
