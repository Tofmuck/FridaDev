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
class FakeAudio extends EventTarget {
  constructor() { super(); this.src = ''; this.currentSrc = ''; this.paused = true; this.ended = false; this.readyState = 4; this.error = null; this.plays = 0; }
  play() { this.plays++; this.currentSrc = this.src; this.paused = false; this.ended = false; return this.playResult || Promise.resolve(); }
  pause() { this.paused = true; }
  removeAttribute(name) { if (name === 'src') this.src = ''; }
  load() { this.currentSrc = this.src; this.ended = false; this.error = null; }
  emit(type) { this.dispatchEvent(new Event(type)); }
}
function fixture(options = {}) {
  assert.ok(fs.existsSync(modulePath), 'D4 session controller must exist');
  const stt = deferred(), chat = deferred(), sttStarted = deferred(), chatStarted = deferred();
  const f = { audio: options.audio || new FakeAudio(), urls: [], revoked: [], synthCalls: [], thread: 'thread-A', busy: false, armed: true, resumes: 0, stops: 0,
    states: [], submissions: [], sttCalls: 0, stt, chat, sttStarted, chatStarted };
  f.controller = require(modulePath).createDialogueSessionController({
    ttsMediaElement: f.audio,
    urlApi: { createObjectURL: () => { const url = `blob:synthetic-${f.urls.length}`; f.urls.push(url); return url; }, revokeObjectURL: url => f.revoked.push(url) },
    capture: {
      pause: async () => { f.armed = false; },
      stop: async () => { f.armed = false; f.stops++; },
      resume: async (isCurrent) => { if (f.resumeGate) await f.resumeGate.promise; if (isCurrent()) { f.armed = true; f.resumes++; } },
    },
    audioClient: { synthesize: async (text, opts) => { f.synthCalls.push(text); f.ttsSignal = opts.signal; return f.tts ? f.tts.promise : new Blob(['mp3'], { type: 'audio/mpeg' }); }, transcribe: async (blob, options) => {
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
test('D5 primes synchronously, consumes exact canonical final once and rearms only after actual playing then ended', async () => {
  const f = fixture();
  assert.equal(f.audio.plays, 1); assert.match(f.audio.src, /^data:audio\/wav;base64,/);
  await f.controller.whenReady();
  assert.equal(f.audio.src, '');
  const pending = f.blob(); await f.sttStarted.promise;
  await f.blob(); assert.equal(f.sttCalls, 1);
  f.stt.resolve('Texte synthétique'); await f.chatStarted.promise;
  assert.equal(f.synthCalls.length, 0);
  const exact = '  e\u0301 😀\n'; f.chat.resolve({ ok: true, text: exact }); await pending;
  assert.deepEqual(f.synthCalls, [exact]); assert.equal(f.states.at(-1), 'tts_pending');
  f.audio.ended = true; f.audio.emit('ended'); assert.equal(f.resumes, 0);
  f.audio.ended = false; f.audio.emit('playing'); assert.equal(f.states.at(-1), 'tts_speaking');
  f.audio.readyState = 2; f.audio.emit('waiting'); assert.equal(f.states.at(-1), 'tts_pending');
  f.audio.readyState = 4; f.audio.emit('playing');
  f.audio.paused = true; f.audio.emit('pause'); assert.equal(f.states.at(-1), 'tts_pending');
  f.audio.ended = true; f.audio.emit('ended'); await new Promise(setImmediate);
  assert.equal(f.resumes, 1); assert.equal(f.states.at(-1), 'listening');
  f.audio.emit('ended'); assert.equal(f.resumes, 1); assert.deepEqual(f.revoked, f.urls);
  await f.blob(); f.audio.emit('playing'); f.audio.ended = true; f.audio.emit('ended');
  await new Promise(setImmediate); assert.equal(f.resumes, 2); assert.equal(f.urls.length, 2);
  assert.deepEqual(f.revoked, f.urls);
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

test('D5 initial play refusal prevents capture readiness and remains terminal', async () => {
  const audio = new FakeAudio(); audio.playResult = Promise.reject(new Error('refused'));
  const f = fixture({ audio }); assert.equal(await f.controller.whenReady(), false);
  assert.equal(f.states.at(-1), 'error'); await f.controller.resume(); assert.equal(f.resumes, 0);
});
for (const action of ['pause', 'close', 'conversationChanged']) {
  test(`D5 ${action} invalidates late synthesis and playback`, async () => {
    const f = fixture(); await f.controller.whenReady(); f.tts = deferred();
    const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
    f.chat.resolve({ ok: true, text: 'final' }); await new Promise(setImmediate);
    if (action === 'conversationChanged') f.thread = 'thread-B';
    await f.controller[action](); const states = [...f.states];
    assert.equal(f.ttsSignal.aborted, true); f.tts.resolve(new Blob(['mp3'], { type: 'audio/mpeg' })); await pending;
    assert.equal(f.urls.length, 0); f.audio.emit('playing'); f.audio.ended = true; f.audio.emit('ended');
    assert.deepEqual(f.states, states); assert.equal(f.resumes, 0);
  });
}
test('D5 pause during ended rearm cannot revive microphone; cleanup is unique', async () => {
  const f = fixture(); await f.controller.whenReady(); const pending = f.blob();
  await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  f.chat.resolve({ ok: true, text: 'final' }); await pending; f.resumeGate = deferred();
  f.audio.emit('playing'); f.audio.ended = true; f.audio.emit('ended');
  await f.controller.pause(); f.resumeGate.resolve(); await new Promise(setImmediate);
  assert.equal(f.resumes, 0); assert.equal(f.armed, false); assert.equal(f.states.at(-1), 'paused');
  await f.controller.close(); assert.deepEqual(f.revoked, f.urls);
});
test('D5 media corruption fails terminally without losing canonical submission', async () => {
  const f = fixture(); await f.controller.whenReady(); const pending = f.blob();
  await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  f.chat.resolve({ ok: true, text: 'final' }); await pending;
  f.audio.error = { code: 3 }; f.audio.emit('error'); await new Promise(setImmediate);
  assert.equal(f.states.at(-1), 'error'); assert.equal(f.submissions.length, 1);
  await f.controller.resume(); assert.equal(f.resumes, 0); assert.deepEqual(f.revoked, f.urls);
});

test('D5 ended can complete and accept next utterance while old play promise is unsettled', async () => {
  const f = fixture(); await f.controller.whenReady(); const play = deferred(); f.audio.playResult = play.promise;
  const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  f.chat.resolve({ ok: true, text: 'final' }); await new Promise(setImmediate);
  f.audio.emit('playing'); f.audio.ended = true; f.audio.emit('ended'); await new Promise(setImmediate);
  assert.equal(f.resumes, 1);
  const second = f.blob(); await new Promise(setImmediate); assert.equal(f.sttCalls, 2);
  await f.controller.close(); play.reject(new Error('late')); await pending; await second;
  assert.equal(f.states.at(-1), 'tts_pending'); assert.deepEqual(f.revoked, f.urls);
});
for (const value of ['', null, 42, 'a'.repeat(16_001)]) {
  test(`D5 refuses invalid canonical final (${typeof value}/${value?.length}) before TTS`, async () => {
    const f = fixture(); await f.controller.whenReady(); const pending = f.blob();
    await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
    f.chat.resolve({ ok: true, text: value }); await pending;
    assert.equal(f.states.at(-1), 'error'); assert.deepEqual(f.synthCalls, []);
    assert.equal(f.submissions.length, 1); assert.equal(f.resumes, 0);
  });
}
test('D5 obsolete media events do not mutate a new source or restart capture', async () => {
  const f = fixture(); await f.controller.whenReady(); const pending = f.blob();
  await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  f.chat.resolve({ ok: true, text: 'final' }); await pending;
  f.audio.currentSrc = 'blob:obsolete';
  f.audio.emit('playing'); f.audio.ended = true; f.audio.emit('ended'); f.audio.error = { code: 3 }; f.audio.emit('error');
  assert.equal(f.states.at(-1), 'tts_pending'); assert.equal(f.resumes, 0);
  f.audio.currentSrc = f.audio.src; f.audio.ended = false; f.audio.error = null;
  f.audio.emit('ended'); f.audio.emit('pause'); f.audio.emit('waiting');
  assert.equal(f.states.at(-1), 'tts_pending'); assert.equal(f.resumes, 0);
  await f.controller.close(); assert.deepEqual(f.revoked, f.urls);
});

test('D5 cancelled preparation cannot bypass readiness through explicit resume', async () => {
  const audio = new FakeAudio(); const preparation = deferred(); audio.playResult = preparation.promise;
  const f = fixture({ audio }); await f.controller.pause(); const resumed = f.controller.resume();
  preparation.resolve(); await resumed;
  assert.equal(f.resumes, 0); assert.equal(f.states.at(-1), 'error'); assert.equal(f.armed, false);
});

for (const action of ['pause', 'close', 'conversationChanged']) {
  test(`D5 ${action} during active playback stops reader immediately and ignores late play rejection`, async () => {
    const f = fixture(); await f.controller.whenReady(); const play = deferred(); f.audio.playResult = play.promise;
    const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
    f.chat.resolve({ ok: true, text: 'final' }); await pending; f.audio.emit('playing');
    if (action === 'conversationChanged') f.thread = 'thread-B';
    const cleanup = f.controller[action](); assert.equal(f.audio.paused, true); assert.equal(f.audio.src, '');
    await cleanup; const states = [...f.states]; play.reject(new Error('late'));
    f.audio.emit('playing'); f.audio.ended = true; f.audio.emit('ended'); await new Promise(setImmediate);
    assert.deepEqual(f.states, states); assert.equal(f.resumes, 0); assert.deepEqual(f.revoked, f.urls);
  });
}
test('D5 refused TTS play stops audio and becomes terminal', async () => {
  const f = fixture(); await f.controller.whenReady(); const play = deferred(); f.audio.playResult = play.promise;
  const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  f.chat.resolve({ ok: true, text: 'final' }); await pending; play.reject(new Error('refused'));
  await new Promise(setImmediate); assert.equal(f.states.at(-1), 'error');
  assert.equal(f.audio.paused, true); assert.deepEqual(f.revoked, f.urls);
  await f.controller.resume(); assert.equal(f.resumes, 0); assert.equal(f.submissions.length, 1);
});
for (const mp3 of [new Blob([], { type: 'audio/mpeg' }), new Blob(['bad'], { type: 'text/plain' }), null]) {
  test('D5 invalid synthesized blob never becomes an object URL or a second play', async () => {
    const f = fixture(); await f.controller.whenReady(); f.tts = deferred();
    const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
    f.chat.resolve({ ok: true, text: 'final' }); f.tts.resolve(mp3); await pending;
    assert.equal(f.states.at(-1), 'error'); assert.equal(f.audio.plays, 1); assert.equal(f.urls.length, 0);
    assert.equal(f.submissions.length, 1); assert.equal(f.resumes, 0);
  });
}
test('D5 failed synthesis preserves written submission, stops capture, and never retries', async () => {
  const f = fixture(); await f.controller.whenReady(); f.tts = deferred();
  const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  f.chat.resolve({ ok: true, text: 'final' }); await new Promise(setImmediate); f.tts.reject(new Error('unavailable')); await pending;
  assert.equal(f.states.at(-1), 'error'); assert.equal(f.submissions.length, 1); assert.equal(f.synthCalls.length, 1);
  await f.controller.resume(); assert.equal(f.resumes, 0); assert.equal(f.armed, false);
});

test('D5 canonical FEFF and Unicode are passed byte-for-byte; base MP3 MIME parameters accepted', async () => {
  const f = fixture(); await f.controller.whenReady(); f.tts = deferred();
  const pending = f.blob(); await f.sttStarted.promise; f.stt.resolve('input'); await f.chatStarted.promise;
  const exact = '\uFEFF'; f.chat.resolve({ ok: true, text: exact });
  f.tts.resolve(new Blob(['mp3'], { type: 'audio/mpeg; charset=binary' })); await pending;
  assert.deepEqual(f.synthCalls, [exact]); assert.equal(f.states.at(-1), 'tts_pending');
  f.audio.error = { code: 3 }; f.audio.emit('playing'); assert.equal(f.states.at(-1), 'tts_pending');
  await f.controller.close(); assert.deepEqual(f.revoked, f.urls);
});
