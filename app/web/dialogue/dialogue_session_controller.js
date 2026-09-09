'use strict';

// D4 owns only STT operations and their validity. D3 owns capture; chat owns its finalization.
function createDialogueSessionController({
  capture, audioClient, getConversationId, isChatBusy, setState, submitCanonicalChatMessage,
}) {
  let active = false;
  let session = 0;
  let generation = 0;
  let conversationId = null;
  let phase = 'paused';
  let pending = null;
  let abort = null;
  const consumedBlobs = new WeakSet();

  const project = (state) => { phase = state; setState(state); };
  const invalidate = () => {
    generation += 1;
    abort?.abort();
    abort = null;
  };
  const fail = () => {
    invalidate();
    project('error');
    return Promise.resolve(capture.pause());
  };
  const isCurrent = (operation) => {
    const valid = active && operation === generation && conversationId === getConversationId();
    if (!valid && active && operation === generation) void fail();
    return valid;
  };

  const consumeBlob = (blob) => {
    if (!active || pending || !['listening', 'user_speaking'].includes(phase)) return Promise.resolve();
    if (blob && typeof blob === 'object') {
      if (consumedBlobs.has(blob)) return Promise.resolve();
      consumedBlobs.add(blob);
    }
    const operation = ++generation;
    // D3 pause releases tracks synchronously, before either network request.
    const paused = capture.pause();
    if (!isCurrent(operation)) return Promise.resolve(paused);
    if (isChatBusy()) return fail();
    project('transcribing');
    const requestAbort = new AbortController();
    abort = requestAbort;
    const task = (async () => {
      try {
        await paused;
        if (!isCurrent(operation)) return;
        const text = await audioClient.transcribe(blob, { signal: requestAbort.signal });
        if (!isCurrent(operation)) return;
        if (typeof text !== 'string') { await fail(); return; }
        if (!text.trim()) { project('paused'); return; }
        if (isChatBusy()) { await fail(); return; }
        project('thinking');
        const result = await submitCanonicalChatMessage(text, 'dialogue');
        if (!isCurrent(operation)) return;
        project(result?.ok === true ? 'paused' : 'error');
      } catch (_error) {
        if (isCurrent(operation)) await fail();
      } finally {
        if (abort === requestAbort) abort = null;
      }
    })();
    pending = task;
    task.finally(() => { if (pending === task) pending = null; });
    return task;
  };

  const start = () => {
    invalidate();
    const owner = ++session;
    active = true;
    conversationId = getConversationId();
    project('listening');
    // The recorder keeps this callback: an old recorder cannot target a new session.
    return (event) => {
      if (!active || owner !== session) return Promise.resolve();
      if (event.type === 'blob') return consumeBlob(event.blob);
      if (event.type === 'error') return fail();
      if (!pending && ['listening', 'user_speaking'].includes(phase)) {
        if (event.type === 'speech-start') project('user_speaking');
        if (event.type === 'speech-end') project('listening');
      }
      return Promise.resolve();
    };
  };
  const pause = () => {
    if (!active) return Promise.resolve();
    invalidate();
    project(phase === 'error' ? 'error' : 'paused');
    return Promise.resolve(capture.pause());
  };
  const resume = async () => {
    if (!active) return;
    if (pending || phase !== 'paused') return;
    if (isChatBusy()) { await fail(); return; }
    const operation = ++generation;
    if (!isCurrent(operation)) return;
    project('listening');
    try {
      await capture.resume(() => isCurrent(operation));
    } catch (_error) {
      if (isCurrent(operation)) await fail();
    }
  };
  const close = () => {
    active = false;
    session += 1;
    invalidate();
    return Promise.resolve(capture.stop());
  };
  const conversationChanged = () => {
    if (active && conversationId !== getConversationId()) void fail();
  };
  return Object.freeze({ start, pause, resume, stop: close, close, conversationChanged });
}

const FridaDialogueSessionController = Object.freeze({ createDialogueSessionController });
if (typeof module !== 'undefined' && module.exports) module.exports = FridaDialogueSessionController;
if (typeof window !== 'undefined') window.FridaDialogueSessionController = FridaDialogueSessionController;
