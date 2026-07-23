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
} = require('../../support/frontend_load_order_contract.js');

const APP_DIR = path.resolve(__dirname, '../../..');
const WEB_DIR = path.join(APP_DIR, 'web');

function currentScriptSources() {
  return parseScriptSources(fs.readFileSync(path.join(WEB_DIR, 'index.html'), 'utf8'));
}

test('Lot 9 chat assets load once in dependency order and expose required globals', () => {
  const sources = currentScriptSources();
  assert.deepEqual(validateChatScriptOrder(sources), []);

  const context = vm.createContext({ console });
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
});

test('Lot 9 load-order validator rejects duplicate and reversed dependencies', () => {
  const sources = currentScriptSources();
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
