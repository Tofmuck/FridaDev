'use strict';

const DIALOGUE_RECORDER_MIME_TYPES = Object.freeze([
  'audio/mp4',
  'audio/webm',
  'audio/ogg',
]);
const DIALOGUE_RECORDER_MAX_DURATION_MS = 300_000;
const DIALOGUE_RECORDER_MAX_BYTES = 24_000_000;
const DIALOGUE_RECORDER_TIMESLICE_MS = 250;

function createDialogueVadRecorder(options = {}) {
  const mediaDevices = options.mediaDevices
    || (typeof navigator !== 'undefined' ? navigator.mediaDevices : null);
  const MediaRecorderCtor = options.MediaRecorderCtor
    || (typeof MediaRecorder !== 'undefined' ? MediaRecorder : null);
  const BlobCtor = options.BlobCtor
    || (typeof Blob !== 'undefined' ? Blob : null);
  const documentObj = options.documentObj
    || (typeof document !== 'undefined' ? document : null);
  const vadFactory = options.vadFactory;
  const onEvent = typeof options.onEvent === 'function' ? options.onEvent : () => {};
  const setTimeoutFn = options.setTimeoutFn || setTimeout;
  const clearTimeoutFn = options.clearTimeoutFn || clearTimeout;
  const nowFn = options.nowFn || (() => (
    typeof performance !== 'undefined' && typeof performance.now === 'function'
      ? performance.now()
      : Date.now()
  ));
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
  let mediaRecorder = null;
  let selectedMimeType = '';
  let chunks = [];
  let chunkBytes = 0;
  let captureStartedAt = 0;
  let captureTimer = null;
  let speechConfirmed = false;
  let speechFinalizing = false;
  let releaseInProgress = false;
  let recorderStopPromise = null;
  let recorderStopResolve = null;
  let recorderStopTarget = null;

  const emit = (event) => {
    try {
      onEvent(Object.freeze({ ...event }));
    } catch (_error) {
      // A projection callback cannot make the microphone lifecycle unsafe.
    }
  };

  const clearCaptureTimer = () => {
    if (captureTimer == null) return;
    clearTimeoutFn(captureTimer);
    captureTimer = null;
  };

  const resetCapture = () => {
    clearCaptureTimer();
    chunks = [];
    chunkBytes = 0;
    captureStartedAt = 0;
    speechConfirmed = false;
    speechFinalizing = false;
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

  const settleRecorderStop = (targetRecorder) => {
    if (recorderStopTarget !== targetRecorder) return;
    const resolve = recorderStopResolve;
    recorderStopPromise = null;
    recorderStopResolve = null;
    recorderStopTarget = null;
    if (resolve) resolve();
  };

  const stopRecorder = async () => {
    if (recorderStopPromise) return recorderStopPromise;
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
    const targetRecorder = mediaRecorder;
    recorderStopPromise = new Promise((resolve) => {
      recorderStopResolve = resolve;
      recorderStopTarget = targetRecorder;
    });
    try {
      targetRecorder.stop();
    } catch (error) {
      settleRecorderStop(targetRecorder);
      throw error;
    }
    return recorderStopPromise;
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
    clearCaptureTimer();
    const targetStream = stream;
    const targetRecorder = mediaRecorder;
    stream = null;
    mediaRecorder = null;
    stopTracks(targetStream);
    resetCapture();
    if (targetRecorder && targetRecorder.state !== 'inactive') {
      try {
        targetRecorder.stop();
      } catch (_error) {
        // The owned tracks are already stopped and all late callbacks are stale.
      }
    }
    settleRecorderStop(targetRecorder);
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

  const startCapture = () => {
    if (!mediaRecorder || phase === 'error' || phase === 'stopped') return;
    resetCapture();
    captureStartedAt = nowFn();
    mediaRecorder.start(DIALOGUE_RECORDER_TIMESLICE_MS);
    captureTimer = setTimeoutFn(() => {
      void fail('duration_limit_exceeded');
    }, maxDurationMs + 1);
  };

  const finishRecognizedSpeech = async (speechGeneration) => {
    try {
      await stopRecorder();
    } catch (_error) {
      await fail('recorder_error');
      return;
    }
    if (speechGeneration !== generation || phase === 'error' || phase === 'stopped') {
      resetCapture();
      return;
    }
    clearCaptureTimer();

    const elapsedMs = Math.max(0, nowFn() - captureStartedAt);
    const durationMs = Math.round(elapsedMs);
    const actualMimeType = normalizeRecorderMimeType(mediaRecorder && mediaRecorder.mimeType)
      || selectedMimeType;
    if (!DIALOGUE_RECORDER_MIME_TYPES.includes(actualMimeType)) {
      await fail('recorder_mime_invalid');
      return;
    }

    let blob;
    try {
      blob = new BlobCtor(chunks, { type: actualMimeType });
    } catch (_error) {
      await fail('blob_creation_failed');
      return;
    }
    if (elapsedMs > maxDurationMs) {
      await fail('duration_limit_exceeded');
      return;
    }
    if (blob.size > maxBytes) {
      await fail('size_limit_exceeded');
      return;
    }

    emit({
      type: 'blob',
      blob,
      mimeType: actualMimeType,
      durationMs,
      sizeBytes: blob.size,
    });

    if (speechGeneration !== generation || phase === 'error' || phase === 'stopped'
        || phase === 'paused') {
      resetCapture();
      return;
    }
    phase = 'listening';
    try {
      startCapture();
    } catch (_error) {
      await fail('recorder_initialization_failed');
    }
  };

  const handleSpeechStart = (sessionGeneration) => {
    if (sessionGeneration !== generation
        || phase !== 'listening' || speechConfirmed || speechFinalizing) return;
    speechConfirmed = true;
    phase = 'speaking';
    emit({ type: 'speech-start' });
  };

  const handleSpeechEnd = (sessionGeneration) => {
    if (sessionGeneration !== generation
        || phase !== 'speaking' || !speechConfirmed || speechFinalizing) return;
    speechFinalizing = true;
    phase = 'finalizing';
    emit({ type: 'speech-end' });
    const speechGeneration = generation;
    void finishRecognizedSpeech(speechGeneration);
  };

  const handleRecorderData = (event, sessionGeneration, targetRecorder) => {
    if (sessionGeneration !== generation || targetRecorder !== mediaRecorder
        || phase === 'error' || phase === 'stopped' || phase === 'paused') return;
    const data = event && event.data;
    const size = Number(data && data.size || 0);
    if (!data || size <= 0) return;
    if (size > maxBytes - chunkBytes) {
      void fail('size_limit_exceeded');
      return;
    }
    chunks.push(data);
    chunkBytes += size;
  };

  const handleRecorderStop = (targetRecorder) => {
    settleRecorderStop(targetRecorder);
  };

  const handleRecorderError = (sessionGeneration, targetRecorder) => {
    if (sessionGeneration !== generation || targetRecorder !== mediaRecorder) return;
    void fail('recorder_error');
  };

  const handleVadRuntimeError = (sessionGeneration) => {
    if (sessionGeneration !== generation || phase === 'stopped' || phase === 'error') return;
    void fail('vad_runtime_error');
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

  const selectMimeType = () => {
    if (!MediaRecorderCtor || typeof MediaRecorderCtor.isTypeSupported !== 'function') return '';
    return DIALOGUE_RECORDER_MIME_TYPES.find((mimeType) => (
      MediaRecorderCtor.isTypeSupported(mimeType)
    )) || '';
  };

  const startSession = async (sessionGeneration) => {
    selectedMimeType = selectMimeType();
    if (!selectedMimeType || !BlobCtor || !mediaDevices
        || typeof mediaDevices.getUserMedia !== 'function'
        || typeof vadFactory !== 'function') {
      await fail('codec_unsupported');
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

    try {
      const sessionRecorder = new MediaRecorderCtor(stream, { mimeType: selectedMimeType });
      mediaRecorder = sessionRecorder;
      sessionRecorder.addEventListener('dataavailable', (event) => {
        handleRecorderData(event, sessionGeneration, sessionRecorder);
      });
      sessionRecorder.addEventListener('stop', () => handleRecorderStop(sessionRecorder));
      sessionRecorder.addEventListener('error', () => {
        handleRecorderError(sessionGeneration, sessionRecorder);
      });
      startCapture();
    } catch (_error) {
      await fail('recorder_initialization_failed');
      return;
    }

    let sessionVad = null;
    try {
      sessionVad = await vadFactory({
        ...(options.vadOptions || {}),
        startOnLoad: false,
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
        onSpeechEnd: () => handleSpeechEnd(sessionGeneration),
        onVADMisfire: () => {},
        onRuntimeError: () => handleVadRuntimeError(sessionGeneration),
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

function normalizeRecorderMimeType(value) {
  return String(value || '').split(';', 1)[0].trim().toLowerCase();
}

const FridaDialogueVadRecorder = Object.freeze({
  DIALOGUE_RECORDER_MIME_TYPES,
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
