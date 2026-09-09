'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const streaming = require('../../../web/chat_streaming.js');

// Execute the real submission and transport together; only DOM and server boundaries are faked.
function fixture({ terminal = { event: 'done', updated_at: '2026-09-09T10:00:00Z', final_text: 'Final verrouillé' }, httpError = false } = {}) {
  const f = { nodes: [], cache: [], requests: [], hydrations: [], metadata: [], refreshes: 0,
    renderCount: 0, loads: [], states: [], threadId: 'thread-A' };
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  f.release = release;
  const makeNode = (role, text) => {
    const node = { role, bubble: { textContent: text }, wrapper: { isConnected: true } };
    f.nodes.push(node); return node;
  };
  const context = {
    ...streaming, TextDecoder, Response, JSON, console: { error() {} },
    ask: { addEventListener: (_, handler) => { f.form = handler; } },
    message: { value: '' }, currentDraftInputMode: 'keyboard', chatRequestInFlight: false,
    getCurrentId: () => f.threadId,
    getThreadById: id => ({ conversation_id: id, workspace_folder_id: '' }),
    addMsg: makeNode, createMessageNode: makeNode,
    appendMessageToThread: (...args) => f.cache.push(args),
    setCurrentDraftInputMode: mode => { context.currentDraftInputMode = mode; },
    setAssistantLoader: () => {}, syncDictationUi: () => {},
    applyAssistantStreamingUiEvent: (_, state) => f.states.push(state),
    applyAssistantStreamingFailure: () => f.states.push('interrupted'),
    isChatNearBottom: () => false, scrollToBottom: () => {},
    hasTerminalUpdatedAt: t => Boolean(t?.updated_at), setMessageNodeTimestamp: () => {},
    applyConversationTerminalMeta: (...args) => { f.metadata.push(args); return true; },
    hydrateThreadMessages: async (...args) => f.hydrations.push(args),
    refreshThreadsFromServer: async () => { f.refreshes++; },
    renderThreads: () => { f.renderCount++; }, updateExportConversationButton: () => {},
    loadThread: async id => f.loads.push(id), refreshActiveDocuments: async () => {},
    extractErrorMessage: () => 'Échec synthétique', setThreadMeta: () => {},
    adobeModeController: null, biblioModeController: null, agendaModeController: null,
    notesModeController: null, webSearchEnabled: false,
    fetch: async (url, options) => {
      f.requests.push({ url, payload: JSON.parse(options.body) }); await gate;
      if (httpError) return new Response('synthetic', { status: 503 });
      return new Response('Brouillon\x1e' + JSON.stringify({ kind: 'frida-stream-control', ...terminal }) + '\n',
        { headers: { 'Content-Type': 'text/plain' } });
    },
  };
  const source = fs.readFileSync(path.resolve(__dirname, '../../../web/app.js'), 'utf8');
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('  // ---- Envoi'), source.indexOf('  // ---- Init')), context);
  f.context = context;
  f.submit = (text, mode) => {
    assert.equal(typeof context.submitCanonicalChatMessage, 'function', 'unique canonical submit must exist');
    return context.submitCanonicalChatMessage(text, mode);
  };
  return f;
}
for (const mode of ['keyboard', 'voice', 'dialogue']) {
  test(`D4 canonical ${mode}: one user, shared busy guard, correct thread/input_mode and final lock/cache`, async () => {
    const f = fixture();
    f.context.message.value = 'brouillon conservé';
    const pending = f.submit('Texte synthétique', mode);
    assert.equal(f.context.chatRequestInFlight, true);
    await f.submit('doublon', 'dialogue');
    assert.equal(f.requests.length, 1);
    assert.deepEqual(f.requests[0], { url: '/api/chat', payload: {
      message: 'Texte synthétique', conversation_id: 'thread-A', stream: true,
      web_search: false, input_mode: mode === 'keyboard' ? 'keyboard' : 'voice',
      biblio_enabled: false, agenda_enabled: false, workspace_notes_mode: false,
    } });
    assert.equal(f.nodes.filter(n => n.role === 'user').length, 1);
    if (mode === 'dialogue') assert.equal(f.context.message.value, 'brouillon conservé');
    f.release(); const result = await pending;
    assert.equal(result.ok, true);
    assert.equal(f.context.chatRequestInFlight, false);
    assert.equal(f.nodes.at(-1).bubble.textContent, 'Final verrouillé');
    assert.deepEqual(f.cache.map(args => args.slice(0, 3)), [
      ['thread-A', 'user', 'Texte synthétique'], ['thread-A', 'assistant', 'Final verrouillé'],
    ]);
    assert.ok(f.states.includes(streaming.STREAMING_UI_EVENT_VISIBLE_CONTENT));
    assert.ok(f.states.includes(streaming.STREAMING_UI_EVENT_TERMINAL_DONE));
    assert.equal(f.metadata[0][0], 'thread-A'); assert.equal(f.refreshes, 1);
    assert.deepEqual(f.hydrations, []);
  });
}
test('D4 keyboard and Whisper form submissions execute the same canonical function', async () => {
  for (const mode of ['keyboard', 'voice']) {
    const f = fixture();
    assert.equal(typeof f.context.submitCanonicalChatMessage, 'function');
    const original = f.context.submitCanonicalChatMessage;
    const calls = [];
    f.context.submitCanonicalChatMessage = (text, inputMode) => {
      calls.push([text, inputMode]); return original(text, inputMode);
    };
    f.context.message.value = 'Synthétique'; f.context.currentDraftInputMode = mode;
    const pending = f.form({ preventDefault() {} }); f.release(); await pending;
    assert.deepEqual(calls, [['Synthétique', mode]]);
    assert.equal(f.requests.length, 1); assert.equal(f.requests[0].payload.input_mode, mode);
  }
});
for (const mode of ['keyboard', 'voice', 'dialogue']) {
  test(`D4 ${mode} preserves interrupted chat truth and rehydrates after unpersisted terminal`, async () => {
    const f = fixture({ terminal: { event: 'error', error_code: 'conversation_persist_failed' } });
    const pending = f.submit('Synthétique', mode); f.release(); const result = await pending;
    assert.equal(result.ok, false); assert.equal(f.context.chatRequestInFlight, false);
    assert.equal(f.cache.filter(args => args[1] === 'assistant').length, 0);
    assert.equal(f.hydrations.length, 1); assert.equal(f.hydrations[0][0], 'thread-A');
    assert.deepEqual(f.loads, ['thread-A']); assert.ok(f.states.includes('interrupted'));
  });
}
test('D4 canonical HTTP failure returns failure; missing timestamp still forces hydration on success', async () => {
  const f = fixture({ httpError: true }); const pending = f.submit('Synthétique', 'dialogue');
  f.release(); assert.equal((await pending).ok, false); assert.equal(f.context.chatRequestInFlight, false);
  const g = fixture({ terminal: { event: 'done' } }); const success = g.submit('Synthétique', 'keyboard');
  g.release(); assert.equal((await success).ok, true); assert.equal(g.hydrations.length, 1);
  assert.deepEqual(g.loads, ['thread-A']);
});
