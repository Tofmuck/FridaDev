'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

function loadModule() {
  try {
    return require('../../../web/chat_threads_list_renderer.js');
  } catch (error) {
    if (error && error.code === 'MODULE_NOT_FOUND'
        && String(error.message || '').includes('chat_threads_list_renderer.js')) {
      return {};
    }
    throw error;
  }
}

const { createConversationListRenderer } = loadModule();

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
      child.parentElement = element;
      element.children.push(child);
      return child;
    },
    addEventListener(type, handler) {
      listeners.set(type, [...(listeners.get(type) || []), handler]);
    },
    setAttribute(name, value) { element[name] = value; },
  };
  let html = '';
  Object.defineProperty(element, 'innerHTML', {
    get() { return html; },
    set(value) {
      html = String(value || '');
      if (!html) element.children = [];
    },
  });
  return element;
}

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

test('conversation list renderer delegates folder rows and renders outside conversations', () => {
  assert.equal(typeof createConversationListRenderer, 'function');

  const threadsUl = makeElement('ul');
  const dragSources = [];
  const dropTargets = [];
  const nested = { id: 'conv-nested', title: 'Dans dossier', updated_at: 'STAMP', workspace_folder_id: 'folder-1' };
  const outside = { id: 'conv-outside', title: 'Hors dossier', workspace_folder_id: null };
  const folder = { id: 'folder-1', display_name: 'Projet' };
  const renderer = createConversationListRenderer({
    threadsUl,
    documentObj: { createElement: makeElement },
    getThreads: () => [nested, outside],
    getWorkspaceFolders: () => [folder],
    getCurrentId: () => 'conv-nested',
    groupThreadsByWorkspaceFolder: () => ({
      byFolder: new Map([['folder-1', [nested]]]),
      outside: [outside],
    }),
    workspaceFolderRenderer: {
      appendToolbar() { threadsUl.appendChild(makeElement('toolbar')); },
      appendFolderRow(_folder, rows, _index, appendThreadRow) {
        rows.forEach((thread) => appendThreadRow(thread, true));
      },
    },
    folderBinding: {
      bindConversationDragSource(node, conversationId) { dragSources.push([node, conversationId]); },
      bindConversationDropTarget(node, folderId) { dropTargets.push([node, folderId]); },
    },
    formatTimestamp: (value) => `formatted:${value}`,
    isEditingThread: () => false,
    onRename: () => {},
    onDelete: () => {},
    onSelect: () => {},
  });

  renderer.renderThreads();

  const rows = walk(threadsUl).filter((node) => node.dataset?.conversationId);
  assert.deepEqual(rows.map((node) => node.dataset.conversationId), ['conv-nested', 'conv-outside']);
  assert.equal(rows[0].classList.contains('active'), true);
  assert.equal(rows[0].classList.contains('in-workspace-folder'), true);
  assert.equal(rows[1].classList.contains('active'), false);
  assert.deepEqual(byClass(rows[0], 'title').map((node) => node.textContent), ['Dans dossier']);
  assert.deepEqual(byClass(rows[0], 'thread-time').map((node) => node.textContent), ['formatted:STAMP']);
  assert.deepEqual(dragSources.map((entry) => entry[1]), ['conv-nested', 'conv-outside']);
  assert.equal(dropTargets.length, 1);
  assert.equal(dropTargets[0][1], null);
  assert.equal(dropTargets[0][0].classList.contains('workspace-folder-separator'), true);
});

test('conversation list renderer forwards rename delete and selection actions exactly once', async () => {
  assert.equal(typeof createConversationListRenderer, 'function');

  const threadsUl = makeElement('ul');
  const actions = [];
  const thread = { id: 'conv-1', title: 'Conversation', workspace_folder_id: null };
  const renderer = createConversationListRenderer({
    threadsUl,
    documentObj: { createElement: makeElement },
    getThreads: () => [thread],
    getWorkspaceFolders: () => [],
    getCurrentId: () => null,
    groupThreadsByWorkspaceFolder: () => ({ byFolder: new Map(), outside: [thread] }),
    workspaceFolderRenderer: { appendToolbar() {}, appendNoFoldersEmpty() {} },
    folderBinding: {
      bindConversationDragSource() {},
      bindConversationDropTarget() {},
    },
    formatTimestamp: () => '',
    isEditingThread: () => false,
    onRename: (_row, conversationId) => { actions.push(['rename', conversationId]); },
    onDelete: async (_row, conversationId) => { actions.push(['delete', conversationId]); },
    onSelect: async (conversationId) => { actions.push(['select', conversationId]); },
  });
  renderer.renderThreads();

  const row = walk(threadsUl).find((node) => node.dataset?.conversationId === 'conv-1');
  const edit = byClass(row, 'thread-edit')[0];
  const remove = byClass(row, 'thread-del')[0];
  edit.listeners.get('click')[0]({ stopPropagation() {} });
  await remove.listeners.get('click')[0]({ stopPropagation() {} });
  await row.listeners.get('click')[0]();

  assert.deepEqual(actions, [
    ['rename', 'conv-1'],
    ['delete', 'conv-1'],
    ['select', 'conv-1'],
  ]);
});
