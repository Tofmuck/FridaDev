'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const modulePath = path.resolve(__dirname, '../../../web/dialogue/dialogue_session_controller.js');
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function fixture() {
  assert.ok(fs.existsSync(modulePath), 'D4 session controller must exist');
  const stt = deferred(), chat = deferred(), sttStarted = deferred(), chatStarted = deferred();
  const f = { thread: 'thread-A', busy: false, armed: true, resumes: 0, stops: 0,
    states: [], submissions: [], sttCalls: 0, stt, chat, sttStarted, chatStarted };
  f.controller = require(modulePath).createDialogueSessionController({
    capture: {
      pause: async () => { f.armed = false; },
      stop: async () => { f.armed = false; f.stops++; },
      resume: async () => { f.armed = true; f.resumes++; },
    },
    audioClient: { transcribe: async (blob, options) => {
      assert.equal(f.armed, false, 'microphone must be stopped before STT');
      f.sttCalls++; f.signal = options.signal; sttStarted.resolve(); return stt.promise;
    } },
    getConversationId: () => f.thread,
    isChatBusy: () => f.busy,
    setState: state => f.states.push(state),
    submitCanonicalChatMessage: async (text, mode) => {
      assert.equal(f.armed, false);
      f.submissions.push({ text, mode, thread: f.thread });
      chatStarted.resolve(); return chat.promise;
    },
  });
  f.event = f.controller.start();
  f.blob = () => f.event({ type: 'blob', blob: new Blob(['wav'], { type: 'audio/wav' }) });
  return f;
}
test('D4 blob → transcribing → thinking → paused, double blob ignored and no automatic microphone restart', async () => {
  const f = fixture();
  const pending = f.blob();
  await f.sttStarted.promise;
  await f.blob();
  assert.equal(f.sttCalls, 1);
  assert.deepEqual(f.states, ['listening', 'transcribing']);
  f.stt.resolve('Texte synthétique');
  await f.chatStarted.promise;
  assert.deepEqual(f.submissions, [{ text: 'Texte synthétique', mode: 'dialogue', thread: 'thread-A' }]);
  assert.deepEqual(f.states, ['listening', 'transcribing', 'thinking']);
  await f.controller.resume();
  assert.equal(f.resumes, 0);
  f.chat.resolve({ ok: true, text: 'Final verrouillé' });
  await pending;
  assert.deepEqual(f.states, ['listening', 'transcribing', 'thinking', 'paused']);
  await f.blob();
  assert.equal(f.sttCalls, 1);
  assert.equal(f.armed, false);
  assert.equal(f.resumes, 0);
});
test('D4 empty or whitespace STT creates no message; only explicit local resume can arm again', async () => {
  for (const text of ['', ' \n ']) {
    const f = fixture(); const pending = f.blob();
    await f.sttStarted.promise; f.stt.resolve(text); await pending;
    assert.deepEqual(f.submissions, []);
    assert.equal(f.states.at(-1), 'paused'); assert.equal(f.armed, false);
    await f.controller.resume();
    assert.equal(f.resumes, 1); assert.equal(f.states.at(-1), 'listening');
  }
});
test('D4 STT failure or invalid text is error without chat or automatic restart', async () => {
  for (const result of [null, 42, undefined, new Error('RAW_PRIVATE_SENTINEL')]) {
    const f = fixture(); const pending = f.blob(); await f.sttStarted.promise;
    if (result instanceof Error) f.stt.reject(result); else f.stt.resolve(result);
    await pending;
    assert.equal(f.states.at(-1), 'error'); assert.deepEqual(f.submissions, []);
    assert.equal(f.armed, false); assert.equal(f.resumes, 0);
  }
});
test('D4 busy chat refuses blob before STT and rechecks before submission', async () => {
  const f = fixture(); f.busy = true; await f.blob();
  assert.equal(f.sttCalls, 0); assert.equal(f.states.at(-1), 'error'); assert.equal(f.armed, false);
  const g = fixture(); const pending = g.blob(); await g.sttStarted.promise;
  g.busy = true; g.stt.resolve('synthétique'); await pending;
  assert.deepEqual(g.submissions, []); assert.equal(g.states.at(-1), 'error');
});
test('D4 conversation changed during STT rejects late transcript, even if it changes back', async () => {
  for (const changesBack of [false, true]) {
    const f = fixture(); const pending = f.blob(); await f.sttStarted.promise;
    f.thread = 'thread-B';
    if (changesBack) { f.controller.conversationChanged(); f.thread = 'thread-A'; }
    f.chat.resolve({ ok: true });
    f.stt.resolve('synthétique'); await pending;
    assert.deepEqual(f.submissions, []); assert.equal(f.armed, false);
    assert.equal(f.states.at(-1), 'error');
  }
});
for (const action of ['pause', 'stop', 'close']) {
  test(`D4 ${action} during STT aborts and prevents late result/error, phantom message or UI mutation`, async () => {
    for (const rejects of [false, true]) {
      const f = fixture(); const pending = f.blob(); await f.sttStarted.promise;
      await f.controller[action]();
      const states = [...f.states];
      assert.equal(f.signal.aborted, true);
      await f.controller.resume();
      assert.equal(f.resumes, 0);
      f.chat.resolve({ ok: true });
      if (rejects) f.stt.reject(new Error('RAW_PRIVATE_SENTINEL')); else f.stt.resolve('tardif');
      await pending;
      assert.deepEqual(f.submissions, []); assert.deepEqual(f.states, states);
      assert.equal(f.armed, false);
    }
  });
}
test('D4 prior session callback and result cannot affect a new session', async () => {
  const f = fixture(); const oldEvent = f.event;
  const pending = f.blob(); await f.sttStarted.promise;
  await f.controller.close(); f.event = f.controller.start();
  const states = [...f.states];
  await oldEvent({ type: 'speech-start' });
  await oldEvent({ type: 'blob', blob: new Blob(['wav']) });
  f.chat.resolve({ ok: true });
  f.stt.resolve('tardif'); await pending;
  assert.deepEqual(f.states, states); assert.deepEqual(f.submissions, []); assert.equal(f.sttCalls, 1);
});
test('D4 interrupted/failed canonical chat yields error and never retries or restarts capture', async () => {
  for (const result of [{ ok: false, reason: 'interrupted' }, undefined, new Error('synthetic')]) {
    const f = fixture(); const pending = f.blob(); await f.sttStarted.promise;
    f.stt.resolve('synthétique'); await f.chatStarted.promise;
    if (result instanceof Error) f.chat.reject(result); else f.chat.resolve(result);
    await pending;
    assert.equal(f.states.at(-1), 'error'); assert.equal(f.submissions.length, 1);
    assert.equal(f.armed, false); assert.equal(f.resumes, 0);
  }
});
test('D4 closing during canonical chat preserves its one submission but ignores its late completion', async () => {
  const f = fixture(); const pending = f.blob(); await f.sttStarted.promise;
  f.stt.resolve('synthétique'); await f.chatStarted.promise;
  await f.controller.close(); const states = [...f.states];
  f.chat.resolve({ ok: true }); await pending;
  assert.equal(f.submissions.length, 1); assert.deepEqual(f.states, states); assert.equal(f.armed, false);
});

test('D4 no stale capture event can overwrite pause or a pending STT state', async () => {
  const f = fixture(); const pending = f.blob(); await f.sttStarted.promise;
  await f.event({ type: 'speech-start' }); await f.event({ type: 'speech-end' });
  assert.equal(f.states.at(-1), 'transcribing');
  await f.controller.pause(); const states = [...f.states];
  await f.event({ type: 'speech-start' }); await f.event({ type: 'speech-end' });
  f.chat.resolve({ ok: true });
  f.stt.resolve('tardif'); await pending;
  assert.deepEqual(f.states, states);
});

test('D4 capture error stays honest after Pause/Resume instead of claiming listening on a dead recorder', async () => {
  const f = fixture();
  await f.event({ type: 'error', code: 'vad_runtime_error' });
  await f.controller.pause(); await f.controller.resume();
  assert.equal(f.states.at(-1), 'error'); assert.equal(f.resumes, 0); assert.equal(f.armed, false);
});

test('D4 duplicated blob from a completed operation is refused even after explicit local resume', async () => {
  const f = fixture();
  const event = { type: 'blob', blob: new Blob(['wav'], { type: 'audio/wav' }) };
  const pending = f.event(event); await f.sttStarted.promise; f.stt.resolve(''); await pending;
  await f.controller.resume();
  await f.event(event);
  assert.equal(f.sttCalls, 1); assert.deepEqual(f.submissions, []);
});
