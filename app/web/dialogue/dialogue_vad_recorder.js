'use strict';

const DIALOGUE_RECORDER_SAMPLE_RATE = 16_000;
const DIALOGUE_RECORDER_MIME_TYPE = 'audio/wav';
const DIALOGUE_RECORDER_MAX_DURATION_MS = 300_000;
const DIALOGUE_RECORDER_MAX_BYTES = 24_000_000;

function createDialogueVadRecorder(options = {}) {
  const mediaDevices = options.mediaDevices
    || (typeof navigator !== 'undefined' ? navigator.mediaDevices : null);
  const BlobCtor = options.BlobCtor
    || (typeof Blob !== 'undefined' ? Blob : null);
  const documentObj = options.documentObj
    || (typeof document !== 'undefined' ? document : null);
  const vadFactory = options.vadFactory;
  const onEvent = typeof options.onEvent === 'function' ? options.onEvent : () => {};
  const maxDurationMs = boundedPositiveInteger(
    options.maxDurationMs,
    DIALOGUE_RECORDER_MAX_DURATION_MS,
  );
  const maxBytes = boundedPositiveInteger(options.maxBytes, DIALOGUE_RECORDER_MAX_BYTES);

  let phase = 'idle';
  let generation = 0;
  let transitionPromise = null;
  let cleanupPromise = null;
  let pausePromise = null;
  let stopPromise = null;
  let stream = null;
  let vad = null;
  let releaseInProgress = false;

  const emit = (event) => {
    try {
      onEvent(Object.freeze({ ...event }));
    } catch (_error) {
      // A projection callback cannot make the microphone lifecycle unsafe.
    }
  };

  const stopTracks = (targetStream) => {
    if (!targetStream || typeof targetStream.getTracks !== 'function') return;
    releaseInProgress = true;
    try {
      for (const track of targetStream.getTracks()) {
        if (track && typeof track.stop === 'function' && track.readyState !== 'ended') {
          try {
            track.stop();
          } catch (_error) {
            // Continue releasing the remaining tracks.
          }
        }
      }
    } finally {
      releaseInProgress = false;
    }
  };

  const setStreamEnabled = (targetStream, enabled) => {
    if (!targetStream || typeof targetStream.getTracks !== 'function') return;
    for (const track of targetStream.getTracks()) {
      if (track && track.readyState !== 'ended') track.enabled = Boolean(enabled);
    }
  };

  const destroyVadInstance = async (targetVad) => {
    if (!targetVad || typeof targetVad.destroy !== 'function') return;
    try {
      await targetVad.destroy();
    } catch (_error) {
      // Track release below remains the final ownership boundary.
    }
  };

  const destroyVad = async () => {
    const targetVad = vad;
    vad = null;
    await destroyVadInstance(targetVad);
  };

  const performCleanup = async () => {
    const targetStream = stream;
    stream = null;
    stopTracks(targetStream);
    const vadPauseOperation = (async () => {
      if (vad && typeof vad.pause === 'function') {
        try {
          await vad.pause();
        } catch (_error) {
          // Continue through the bounded cleanup path.
        }
      }
    })();
    await vadPauseOperation;
    await destroyVad();
  };

  const cleanupResources = () => {
    if (cleanupPromise) return cleanupPromise;
    const operation = performCleanup();
    cleanupPromise = operation;
    operation.then(
      () => {
        if (cleanupPromise === operation) cleanupPromise = null;
      },
      () => {
        if (cleanupPromise === operation) cleanupPromise = null;
      },
    );
    return operation;
  };

  const fail = async (code) => {
    if (phase === 'error' || phase === 'stopped') return;
    phase = 'error';
    generation += 1;
    emit({ type: 'error', code });
    await cleanupResources();
  };

  const handleSpeechStart = (sessionGeneration) => {
    if (sessionGeneration !== generation || phase !== 'listening') return;
    phase = 'speaking';
    emit({ type: 'speech-start' });
  };

  const handleSpeechEnd = (audio, sessionGeneration) => {
    if (sessionGeneration !== generation || phase !== 'speaking') return;
    phase = 'finalizing';
    if (!(audio instanceof Float32Array) || audio.length === 0) {
      void fail('vad_audio_invalid');
      return;
    }
    const durationMs = audio.length * 1000 / DIALOGUE_RECORDER_SAMPLE_RATE;
    if (durationMs > maxDurationMs) {
      void fail('duration_limit_exceeded');
      return;
    }
    const sizeBytes = 44 + audio.length * 2;
    if (sizeBytes > maxBytes) {
      void fail('size_limit_exceeded');
      return;
    }
    // Validate the entire segment before allocating; never truncate invalid audio.
    for (const sample of audio) {
      if (!Number.isFinite(sample) || sample < -1 || sample > 1) {
        void fail('vad_audio_invalid');
        return;
      }
    }
    let blob;
    try {
      blob = new BlobCtor([encodeDialogueWav(audio)], { type: DIALOGUE_RECORDER_MIME_TYPE });
    } catch (_error) {
      void fail('blob_creation_failed');
      return;
    }
    if (blob.size > maxBytes) {
      void fail('size_limit_exceeded');
      return;
    }
    emit({ type: 'speech-end' });
    if (sessionGeneration !== generation || phase !== 'finalizing') return;
    emit({ type: 'blob', blob, mimeType: DIALOGUE_RECORDER_MIME_TYPE, durationMs, sizeBytes: blob.size });
    if (sessionGeneration === generation && phase === 'finalizing') phase = 'listening';
  };

  const handleVadRuntimeError = (sessionGeneration, code) => {
    if (sessionGeneration !== generation || phase === 'stopped' || phase === 'error') return;
    const reason = ['duration_limit_exceeded', 'size_limit_exceeded'].includes(code)
      ? code : 'vad_runtime_error';
    void fail(reason);
  };

  const handleTrackEnded = (sessionGeneration, targetStream) => {
    if (sessionGeneration === generation && targetStream === stream
        && !releaseInProgress && phase !== 'stopped' && phase !== 'error' && phase !== 'paused') {
      void fail('track_ended');
    }
  };

  const neutralizeControllableMedia = async () => {
    const elements = [];
    if (options.ttsMediaElement) elements.push(options.ttsMediaElement);
    if (documentObj && typeof documentObj.querySelectorAll === 'function') {
      elements.push(...documentObj.querySelectorAll('audio, video'));
    }
    for (const element of new Set(elements)) {
      if (!element || element.ended || element.paused === true) continue;
      if (typeof element.pause !== 'function') throw new Error('media cannot pause');
      await Promise.resolve(element.pause());
      if (element.paused !== true && element.ended !== true) {
        throw new Error('media remained active');
      }
    }
  };

  const startSession = async (sessionGeneration) => {
    if (!BlobCtor || !mediaDevices
        || typeof mediaDevices.getUserMedia !== 'function'
        || typeof vadFactory !== 'function') {
      await fail('capture_unavailable');
      return;
    }

    try {
      await neutralizeControllableMedia();
    } catch (_error) {
      await fail('media_pause_failed');
      return;
    }
    if (sessionGeneration !== generation || phase === 'stopped'
        || phase === 'paused' || phase === 'error') return;

    let acquiredStream;
    try {
      acquiredStream = await mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          autoGainControl: true,
          noiseSuppression: true,
        },
      });
    } catch (error) {
      if (sessionGeneration !== generation || phase === 'stopped') return;
      const permissionDenied = error && (
        error.name === 'NotAllowedError' || error.name === 'SecurityError'
      );
      await fail(permissionDenied ? 'microphone_permission_denied' : 'microphone_unavailable');
      return;
    }

    if (sessionGeneration !== generation || phase === 'stopped' || phase === 'error') {
      stopTracks(acquiredStream);
      return;
    }
    stream = acquiredStream;
    let ownedTracks;
    try {
      ownedTracks = typeof stream.getTracks === 'function' ? stream.getTracks() : [];
    } catch (_error) {
      ownedTracks = [];
    }
    if (!ownedTracks.length || ownedTracks.every((track) => track.readyState === 'ended')) {
      await fail('microphone_stream_invalid');
      return;
    }
    for (const track of ownedTracks) {
      if (track && typeof track.addEventListener === 'function') {
        track.addEventListener('ended', () => handleTrackEnded(sessionGeneration, acquiredStream));
      }
    }

    let sessionVad = null;
    try {
      sessionVad = await vadFactory({
        ...(options.vadOptions || {}),
        startOnLoad: false,
        submitUserSpeechOnPause: false,
        maxDurationMs,
        maxBytes,
        getStream: async () => acquiredStream,
        pauseStream: async (targetStream) => {
          setStreamEnabled(targetStream, false);
        },
        resumeStream: async (targetStream) => {
          const ownedStream = targetStream || acquiredStream;
          setStreamEnabled(ownedStream, true);
          return acquiredStream;
        },
        onSpeechStart: () => {},
        onSpeechRealStart: () => handleSpeechStart(sessionGeneration),
        onSpeechEnd: (audio) => handleSpeechEnd(audio, sessionGeneration),
        onVADMisfire: () => {},
        onRuntimeError: (code) => handleVadRuntimeError(sessionGeneration, code),
      });
      vad = sessionVad;
      if (sessionGeneration !== generation || phase === 'stopped' || phase === 'error') {
        if (vad === sessionVad) vad = null;
        await destroyVadInstance(sessionVad);
        stopTracks(acquiredStream);
        return;
      }
      phase = 'listening';
      await sessionVad.start();
      if (sessionGeneration !== generation || phase === 'stopped'
          || phase === 'paused' || phase === 'error') {
        if (vad === sessionVad) vad = null;
        await destroyVadInstance(sessionVad);
        stopTracks(acquiredStream);
      }
    } catch (_error) {
      if (sessionGeneration !== generation || phase === 'stopped'
          || phase === 'paused' || phase === 'error') {
        if (vad === sessionVad) vad = null;
        await destroyVadInstance(sessionVad);
        stopTracks(acquiredStream);
      } else {
        await fail('vad_initialization_failed');
      }
    }
  };

  const beginTransition = (allowedPhase) => {
    if (transitionPromise) return transitionPromise;
    if (phase !== allowedPhase) return Promise.resolve();
    phase = 'arming';
    generation += 1;
    const sessionGeneration = generation;
    transitionPromise = startSession(sessionGeneration).finally(() => {
      transitionPromise = null;
    });
    return transitionPromise;
  };

  const arm = () => beginTransition('idle');

  const pause = () => {
    if (stopPromise) return stopPromise;
    if (pausePromise) return pausePromise;
    if (!['arming', 'listening', 'speaking', 'finalizing'].includes(phase)) {
      return cleanupPromise || Promise.resolve();
    }
    const pendingTransition = transitionPromise;
    phase = 'paused';
    generation += 1;
    const operation = (async () => {
      await cleanupResources();
      if (pendingTransition) await pendingTransition;
    })();
    pausePromise = operation;
    operation.then(
      () => {
        if (pausePromise === operation) pausePromise = null;
      },
      () => {
        if (pausePromise === operation) pausePromise = null;
      },
    );
    return operation;
  };

  const resume = () => {
    const pendingPause = pausePromise;
    if (pendingPause) return pendingPause.then(() => beginTransition('paused'));
    return beginTransition('paused');
  };

  const stop = () => {
    if (stopPromise) return stopPromise;
    if (phase === 'stopped') return cleanupPromise || transitionPromise || Promise.resolve();
    phase = 'stopped';
    generation += 1;
    const pendingTransition = transitionPromise;
    const pendingPause = pausePromise;
    const operation = (async () => {
      if (pendingPause) await pendingPause;
      else await cleanupResources();
      if (pendingTransition) await pendingTransition;
    })();
    stopPromise = operation;
    return operation;
  };

  return Object.freeze({ arm, pause, resume, stop });
}

function boundedPositiveInteger(value, ceiling) {
  if (value == null) return ceiling;
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return ceiling;
  return Math.min(Math.floor(number), ceiling);
}

// Fixed-format D3 encoder: one mono PCM16 RIFF/WAVE, no codec negotiation.
function encodeDialogueWav(audio) {
  const buffer = new ArrayBuffer(44 + audio.length * 2);
  const view = new DataView(buffer);
  for (const [offset, word] of [[0, 'RIFF'], [8, 'WAVE'], [12, 'fmt '], [36, 'data']]) {
    for (let i = 0; i < word.length; i++) view.setUint8(offset + i, word.charCodeAt(i));
  }
  view.setUint32(4, buffer.byteLength - 8, true);
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, DIALOGUE_RECORDER_SAMPLE_RATE, true);
  view.setUint32(28, DIALOGUE_RECORDER_SAMPLE_RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  view.setUint32(40, audio.length * 2, true);
  for (let i = 0; i < audio.length; i++) {
    view.setInt16(44 + i * 2, audio[i] * (audio[i] < 0 ? 32768 : 32767), true);
  }
  return buffer;
}

const FridaDialogueVadRecorder = Object.freeze({
  DIALOGUE_RECORDER_MIME_TYPE,
  DIALOGUE_RECORDER_MAX_DURATION_MS,
  DIALOGUE_RECORDER_MAX_BYTES,
  createDialogueVadRecorder,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaDialogueVadRecorder;
}

if (typeof window !== 'undefined') {
  window.FridaDialogueVadRecorder = FridaDialogueVadRecorder;
}
