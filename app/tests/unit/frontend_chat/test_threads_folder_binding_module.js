'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

function loadModule() {
  try {
    return require('../../../web/chat_threads_folder_binding.js');
  } catch (error) {
    if (error && error.code === 'MODULE_NOT_FOUND'
        && String(error.message || '').includes('chat_threads_folder_binding.js')) {
      return {};
    }
    throw error;
  }
}

const { createConversationFolderBinding } = loadModule();
const DRAG_MIME = 'application/x-fridadev-conversation-id';

function makeNode() {
  const listeners = new Map();
  const classes = new Set();
  return {
    listeners,
    classList: {
      add(...names) { names.forEach((name) => classes.add(name)); },
      remove(...names) { names.forEach((name) => classes.delete(name)); },
      contains(name) { return classes.has(name); },
    },
    addEventListener(type, handler) {
      listeners.set(type, [...(listeners.get(type) || []), handler]);
    },
  };
}

function makeDataTransfer(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    effectAllowed: '',
    dropEffect: '',
    get types() { return Array.from(data.keys()); },
    getData(type) { return data.get(type) || ''; },
    setData(type, value) { data.set(type, value); },
  };
}

test('folder binding publishes drag data and moves the dropped conversation once', () => {
  assert.equal(typeof createConversationFolderBinding, 'function');

  const source = makeNode();
  const target = makeNode();
  const staleTarget = makeNode();
  staleTarget.classList.add('workspace-folder-drop-target', 'dragging');
  const moves = [];
  const threadsUl = {
    querySelectorAll() { return [source, target, staleTarget]; },
  };
  const binding = createConversationFolderBinding({
    threadsUl,
    dragMime: DRAG_MIME,
    isEditingThread: () => false,
    moveThreadToWorkspaceFolder: (conversationId, folderId) => {
      moves.push([conversationId, folderId]);
    },
  });

  binding.bindConversationDragSource(source, 'conv-1');
  const dataTransfer = makeDataTransfer();
  let prevented = false;
  source.listeners.get('dragstart')[0]({
    target: { closest: () => null },
    dataTransfer,
    preventDefault() { prevented = true; },
  });

  assert.equal(prevented, false);
  assert.equal(dataTransfer.effectAllowed, 'move');
  assert.equal(dataTransfer.getData(DRAG_MIME), 'conv-1');
  assert.equal(dataTransfer.getData('text/plain'), 'conv-1');
  assert.equal(source.classList.contains('dragging'), true);

  binding.bindConversationDropTarget(target, 'folder-1');
  let dropPrevented = false;
  target.listeners.get('drop')[0]({
    dataTransfer,
    preventDefault() { dropPrevented = true; },
  });

  assert.equal(dropPrevented, true);
  assert.deepEqual(moves, [['conv-1', 'folder-1']]);
  assert.equal(source.classList.contains('dragging'), false);
  assert.equal(staleTarget.classList.contains('workspace-folder-drop-target'), false);
});

test('folder binding rejects interactive or editing drag sources', () => {
  assert.equal(typeof createConversationFolderBinding, 'function');

  for (const scenario of [
    { editing: false, interactive: true },
    { editing: true, interactive: false },
  ]) {
    const source = makeNode();
    const binding = createConversationFolderBinding({
      threadsUl: { querySelectorAll: () => [] },
      dragMime: DRAG_MIME,
      isEditingThread: () => scenario.editing,
      moveThreadToWorkspaceFolder: () => {
        throw new Error('move must not run');
      },
    });
    binding.bindConversationDragSource(source, 'conv-blocked');
    const dataTransfer = makeDataTransfer();
    let prevented = false;

    source.listeners.get('dragstart')[0]({
      target: { closest: () => (scenario.interactive ? {} : null) },
      dataTransfer,
      preventDefault() { prevented = true; },
    });

    assert.equal(prevented, true);
    assert.equal(dataTransfer.types.length, 0);
    assert.equal(source.classList.contains('dragging'), false);
  }
});
