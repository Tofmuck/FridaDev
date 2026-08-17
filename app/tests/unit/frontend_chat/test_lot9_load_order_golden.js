'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const {
  REQUIRED_GLOBALS,
  parseScriptSources,
  validateChatScriptOrder,
  validateRequiredGlobalPublicationCounts,
} = require('../../support/frontend_load_order_contract.js');

const APP_DIR = path.resolve(__dirname, '../../..');
const WEB_DIR = path.join(APP_DIR, 'web');

function currentScriptSources() {
  return parseScriptSources(fs.readFileSync(path.join(WEB_DIR, 'index.html'), 'utf8'));
}

function installRequiredGlobalPublicationCounters(context) {
  const counts = Object.fromEntries(REQUIRED_GLOBALS.map((globalName) => [globalName, 0]));
  const values = new Map();
  for (const globalName of REQUIRED_GLOBALS) {
    Object.defineProperty(context, globalName, {
      configurable: true,
      enumerable: true,
      get: () => values.get(globalName),
      set: (value) => {
        counts[globalName] += 1;
        values.set(globalName, value);
      },
    });
  }
  return counts;
}

test('Lot 9 chat assets load once in dependency order and expose required globals', () => {
  const sources = currentScriptSources();
  assert.deepEqual(validateChatScriptOrder(sources), []);

  const context = vm.createContext({ console });
  const publicationCounts = installRequiredGlobalPublicationCounters(context);
  context.window = context;
  context.globalThis = context;
  context.document = undefined;
  for (const source of sources) {
    const scriptText = fs.readFileSync(path.join(WEB_DIR, source), 'utf8');
    vm.runInContext(scriptText, context, { filename: source });
  }
  for (const globalName of REQUIRED_GLOBALS) {
    assert.equal(typeof context[globalName], 'object', `${globalName} must be available`);
  }
  assert.equal(vm.runInContext('typeof FridaChatThreadsFolderBindingModule', context), 'object');
  assert.equal(vm.runInContext('typeof FridaChatThreadsListRendererModule', context), 'object');
  assert.equal(context.FridaChatThreadsFolderBindingModule, undefined);
  assert.equal(context.FridaChatThreadsListRendererModule, undefined);
  assert.deepEqual(validateRequiredGlobalPublicationCounts(publicationCounts), []);
});

test('Lot 9 load-order validator rejects missing, duplicate and reversed dependencies', () => {
  const sources = currentScriptSources();
  const missing = sources.filter((source) => source !== 'chat_streaming.js');
  assert.ok(
    validateChatScriptOrder(missing).some((issue) =>
      issue.startsWith('required_script_count:chat_streaming.js:0')
    ),
  );

  const duplicated = [...sources, 'chat_streaming.js'];
  assert.ok(
    validateChatScriptOrder(duplicated).some((issue) =>
      issue.startsWith('required_script_count:chat_streaming.js:2')
    ),
  );

  const reversed = [...sources];
  const dependencyIndex = reversed.indexOf('chat_workspace_folders_sidebar.js');
  const consumerIndex = reversed.indexOf('chat_threads_sidebar.js');
  [reversed[dependencyIndex], reversed[consumerIndex]] = [
    reversed[consumerIndex],
    reversed[dependencyIndex],
  ];
  assert.ok(
    validateChatScriptOrder(reversed).includes(
      'load_order:chat_workspace_folders_sidebar.js:chat_threads_sidebar.js',
    ),
  );
});

test('Lot 9 global publication validator rejects missing and duplicate assignments', () => {
  const publicationCounts = Object.fromEntries(
    REQUIRED_GLOBALS.map((globalName) => [globalName, 1]),
  );
  publicationCounts.FridaChatStreaming = 0;
  publicationCounts.FridaNotesMode = 2;

  assert.deepEqual(validateRequiredGlobalPublicationCounts(publicationCounts), [
    'required_global_publication_count:FridaChatStreaming:0',
    'required_global_publication_count:FridaNotesMode:2',
  ]);
});

test('Lot 9 shared script realm rejects a controlled top-level redeclaration', () => {
  const context = vm.createContext({});
  vm.runInContext('const Lot9ControlledBinding = 1;', context);

  assert.throws(
    () => vm.runInContext('const Lot9ControlledBinding = 2;', context),
    { name: 'SyntaxError' },
  );
});
