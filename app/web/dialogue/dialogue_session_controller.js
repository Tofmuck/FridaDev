'use strict';

// Owns the semi-duplex session; D3 owns capture and chat owns its canonical final.
function createDialogueSessionController({
  capture, audioClient, getConversationId, isChatBusy, setState, submitCanonicalChatMessage,
  ttsMediaElement: audio, urlApi = URL, mode = 'full',
}) {
  if (!['full', 'local_preflight'].includes(mode)) throw new Error('dialogue_session_mode_invalid');
  if (mode === 'local_preflight' && (audioClient !== undefined || submitCanonicalChatMessage !== undefined)) {
    throw new Error('dialogue_local_transport_forbidden');
  }
  let active = false;
  let session = 0;
  let generation = 0;
  let conversationId = null;
  let phase = 'paused';
  let pending = null;
  let abort = null;
  let ready = Promise.resolve(false);
  let media = null;
  let rearming = false;
  const cleanupMedia = () => {
    const owned = media;
    if (!owned) return;
    media = null;
    for (const [type, listener] of owned.listeners) audio.removeEventListener(type, listener);
    audio.pause();
    audio.removeAttribute('src');
    audio.load(); // Cancel tasks from the previous resource before another source is installed.
    if (owned.url) urlApi.revokeObjectURL(owned.url);
  };
  const consumedBlobs = new WeakSet();

  const project = (state) => { phase = state; setState(state); };
  const invalidate = () => {
    generation += 1;
    rearming = false;
    cleanupMedia();
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

  const playFinal = (blob, operation) => {
    if (!(blob instanceof Blob) || blob.type.split(';')[0].trim().toLowerCase() !== 'audio/mpeg' || blob.size < 1
        || blob.size > 16 * 1024 * 1024) throw new Error('dialogue_tts_invalid_audio');
    const owned = { url: urlApi.createObjectURL(blob), listeners: [], played: false, ended: false };
    media = owned;
    audio.src = owned.url;
    const valid = () => media === owned && isCurrent(operation)
      && audio.src === owned.url && audio.currentSrc === owned.url;
    const listen = (type, listener) => {
      owned.listeners.push([type, listener]); audio.addEventListener(type, listener);
    };
    listen('playing', () => {
      if (!valid() || owned.ended || audio.error || audio.paused || audio.ended || audio.readyState < 3) return;
      owned.played = true; project('tts_speaking');
    });
    listen('waiting', () => {
      if (valid() && !owned.ended && audio.readyState < 3) project('tts_pending');
    });
    listen('pause', () => {
      if (valid() && !owned.ended && audio.paused) project('tts_pending');
    });
    listen('error', () => { if (valid() && audio.error) void fail(); });
    listen('ended', () => {
      if (!valid() || !audio.ended || !owned.played || owned.ended) return;
      owned.ended = true;
      cleanupMedia();
      project('tts_pending');
      rearming = true;
      // play() may settle after ended: playback cleanup must not wait on it.
      void (async () => {
        try {
          if (!isCurrent(operation)) return;
          if (isChatBusy()) { await fail(); return; }
          await capture.resume(() => isCurrent(operation));
          if (isCurrent(operation)) project('listening');
        } catch (_error) {
          if (isCurrent(operation)) await fail();
        } finally {
          if (operation === generation) rearming = false;
        }
      })();
    });
    // The network operation ends here. Keep play's rejection handled without
    // holding the next utterance hostage to a browser promise settling late.
    try {
      void Promise.resolve(audio.play()).catch(() => {
        if (media === owned && isCurrent(operation)) return fail();
      });
    } catch (_error) {
      if (media === owned && isCurrent(operation)) void fail();
    }
  };

  const consumeBlob = (blob) => {
    if (!active || pending || rearming || !['listening', 'user_speaking'].includes(phase)) return Promise.resolve();
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
        const prepared = await ready;
        await paused;
        if (!prepared) return;
        if (!isCurrent(operation)) return;
        const text = await audioClient.transcribe(blob, { signal: requestAbort.signal });
        if (!isCurrent(operation)) return;
        if (typeof text !== 'string') { await fail(); return; }
        if (!text.trim()) { project('paused'); return; }
        if (isChatBusy()) { await fail(); return; }
        project('thinking');
        const result = await submitCanonicalChatMessage(text, 'dialogue');
        if (!isCurrent(operation)) return;
        if (result?.ok !== true || typeof result.text !== 'string' || result.text.length === 0
            || Array.from(result.text).length > 16_000) { await fail(); return; }
        project('tts_pending');
        const mp3 = await audioClient.synthesize(result.text, { signal: requestAbort.signal });
        if (!isCurrent(operation)) return;
        await playFinal(mp3, operation);
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
    pending = null;
    project('listening');
    const preparation = { url: null, listeners: [] };
    media = preparation;
    // A fixed, eight-sample silent PCM WAV. Safari iPhone rejects the previous
    // one-sample file; play() still runs on the element owned by every TTS cycle.
    try {
      audio.muted = false;
      audio.src = 'data:audio/wav;base64,UklGRjQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YRAAAAAAAAAAAAAAAAAAAAAAAAAA';
      const playing = audio.play();
      ready = Promise.resolve(playing).then(() => {
        if (!active || owner !== session || media !== preparation) return false;
        cleanupMedia();
        return true;
      }, async () => {
        if (active && owner === session && media === preparation) await fail();
        return false;
      });
    } catch (_error) { ready = fail().then(() => false); }
    // The recorder keeps this callback: an old recorder cannot target a new session.
    return (event) => {
      if (!active || owner !== session) return Promise.resolve();
      // Local preflight discards the blob before any full-session work or retention.
      if (event.type === 'blob') return mode === 'full' ? consumeBlob(event.blob) : Promise.resolve();
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
    if (pending || rearming || phase !== 'paused') return;
    if (isChatBusy()) { await fail(); return; }
    const operation = ++generation;
    if (!isCurrent(operation)) return;
    rearming = true;
    try {
      const prepared = await ready;
      if (!isCurrent(operation)) return;
      if (!prepared) { await fail(); return; }
      project('listening');
      await capture.resume(() => isCurrent(operation));
    } catch (_error) {
      if (isCurrent(operation)) await fail();
    } finally {
      if (operation === generation) rearming = false;
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
  return Object.freeze({ start, whenReady: () => ready, pause, resume, stop: close, close, conversationChanged });
}

const FridaDialogueSessionController = Object.freeze({ createDialogueSessionController });
if (typeof module !== 'undefined' && module.exports) module.exports = FridaDialogueSessionController;
if (typeof window !== 'undefined') window.FridaDialogueSessionController = FridaDialogueSessionController;
