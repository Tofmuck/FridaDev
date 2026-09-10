'use strict';

const DIALOGUE_VAD_MODEL = 'v5';
const DIALOGUE_VAD_FRAME_SAMPLES = 512;
const DIALOGUE_VAD_PROCESSOR = 'AudioWorklet';
const DIALOGUE_VAD_PRE_SPEECH_PAD_MS = 800;
const DIALOGUE_VAD_REDEMPTION_MS = 1_400;
const DIALOGUE_VAD_MIN_SPEECH_MS = 400;

function createDialogueVadRuntime(options = {}) {
  const vadRuntime = options.vadRuntime;
  const assetBaseUrl = String(options.assetBaseUrl || '');
  if (!vadRuntime || !vadRuntime.MicVAD
      || typeof vadRuntime.MicVAD.new !== 'function'
      || !vadRuntime.Message || !vadRuntime.Message.SpeechStop
      || !assetBaseUrl.endsWith('/')) {
    throw new Error('Dialogue VAD runtime unavailable');
  }

  const vadOptions = Object.freeze({
    model: DIALOGUE_VAD_MODEL,
    positiveSpeechThreshold: 0.4,
    negativeSpeechThreshold: 0.4,
    startOnLoad: false,
    processorType: DIALOGUE_VAD_PROCESSOR,
    preSpeechPadMs: DIALOGUE_VAD_PRE_SPEECH_PAD_MS,
    redemptionMs: DIALOGUE_VAD_REDEMPTION_MS,
    minSpeechMs: DIALOGUE_VAD_MIN_SPEECH_MS,
    submitUserSpeechOnPause: false,
    baseAssetPath: assetBaseUrl,
    onnxWASMBasePath: assetBaseUrl,
    ortConfig(ort) {
      ort.env.logLevel = 'error';
      ort.env.wasm.numThreads = 1;
      ort.env.wasm.proxy = false;
      ort.env.wasm.wasmPaths = {
        wasm: `${assetBaseUrl}ort-wasm-simd-threaded.wasm`,
        mjs: `${assetBaseUrl}ort-wasm-simd-threaded.mjs`,
      };
    },
  });

  const vadFactory = async (micVadOptions) => {
    const {
      onRuntimeError,
      maxDurationMs = 300_000,
      maxBytes = 24_000_000,
      ...vendorOptions
    } = micVadOptions || {};
    const micVad = await vadRuntime.MicVAD.new(vendorOptions);
    return createPinnedMicVadAdapter(micVad, vadRuntime, onRuntimeError, {
      maxDurationMs: Math.min(maxDurationMs, 300_000),
      maxBytes: Math.min(maxBytes, 24_000_000),
    });
  };

  return Object.freeze({ vadFactory, vadOptions });
}

function createPinnedMicVadAdapter(micVad, vadRuntime, onRuntimeError, limits) {
  let startPromise = null;
  let destroyPromise = null;
  let destroyRequested = false;
  let runtimeFailed = false;
  let framePromise = null;

  const reportFailure = (code) => {
    if (runtimeFailed || destroyRequested) return;
    runtimeFailed = true;
    try {
      if (typeof onRuntimeError === 'function') onRuntimeError(code);
    } catch (_error) {
      // Projection cannot leak an inference rejection.
    }
  };
  const vendorHandleEvent = micVad.handleFrameProcessorEvent.bind(micVad);
  micVad.handleFrameProcessorEvent = (event) => {
    if (destroyRequested || runtimeFailed) throw new Error('vad_cancelled');
    if (event.msg === vadRuntime.Message.FrameProcessed) {
      // 0.0.30 emits FrameProcessed BEFORE appending to audioBuffer or concatenating.
      // V5 has exactly 512 samples/frame at 16kHz; silence keeps only 25 frames.
      const frames = micVad.frameProcessor.audioBuffer;
      if (!Array.isArray(frames) || event.frame.length !== DIALOGUE_VAD_FRAME_SAMPLES) throw new Error('vad_frame_invalid');
      const samples = frames.length * DIALOGUE_VAD_FRAME_SAMPLES + event.frame.length;
      if (samples / 16 > limits.maxDurationMs) throw new Error('duration_limit_exceeded');
      if (44 + samples * 2 > limits.maxBytes) throw new Error('size_limit_exceeded');
    }
    vendorHandleEvent(event);
  };

  if (typeof micVad.processFrame === 'function') {
    const vendorProcessFrame = micVad.processFrame.bind(micVad);
    micVad.processFrame = async (frame) => {
      if (runtimeFailed || destroyRequested) return;
      // Never accumulate an unbounded queue if local inference falls behind.
      if (framePromise) {
        reportFailure('vad_runtime_error');
        return;
      }
      const operation = Promise.resolve().then(() => vendorProcessFrame(frame));
      framePromise = operation;
      try {
        await operation;
      } catch (error) {
        const code = error && error.message;
        reportFailure(['duration_limit_exceeded', 'size_limit_exceeded'].includes(code)
          ? code : 'vad_runtime_error');
      } finally {
        if (framePromise === operation) framePromise = null;
      }
    };
  }

  const start = () => {
    if (destroyRequested) return Promise.reject(new Error('Dialogue VAD already destroyed'));
    if (!startPromise) {
      startPromise = Promise.resolve().then(() => micVad.start());
    }
    return startPromise;
  };

  // D3 pause releases the whole session; there is no suspended graph to reuse.
  const pause = () => destroy();

  const destroy = () => {
    if (destroyPromise) return destroyPromise;
    destroyRequested = true;
    destroyPromise = (async () => {
      if (framePromise) {
        try { await framePromise; } catch (_error) { /* Closed by processFrame. */ }
      }
      if (startPromise) {
        try {
          await startPromise;
        } catch (_error) {
          // A partial start still owns its model and possibly an AudioContext.
        }
      }

      const sourceNode = micVad._mediaStreamAudioSourceNode;
      const vadNode = micVad._vadNode;
      const audioContext = micVad._audioContext;
      const model = micVad.model;
      const startWasAttempted = Boolean(startPromise);
      let publicPauseCompleted = false;

      micVad.initializationState = 'destroyed';
      if (vadNode && vadNode.port && typeof vadNode.port.postMessage === 'function') {
        try {
          vadNode.port.postMessage(vadRuntime.Message.SpeechStop);
        } catch (_error) {
          // Continue with graph, model and context release.
        }
      }
      if (micVad.listening && typeof micVad.pause === 'function') {
        try {
          await micVad.pause();
          publicPauseCompleted = true;
        } catch (_error) {
          // The pinned MicVAD cleanup is all-or-nothing; finish each resource below.
        }
      }
      if (!publicPauseCompleted) safeDisconnect(sourceNode);
      safeDisconnect(vadNode);
      if (!publicPauseCompleted && startWasAttempted
          && micVad.frameProcessor && typeof micVad.frameProcessor.pause === 'function') {
        try {
          micVad.frameProcessor.pause(micVad.handleFrameProcessorEvent);
        } catch (_error) {
          // Continue releasing the model and owned context.
        }
      }
      if (model && typeof model.release === 'function') {
        try {
          await model.release();
        } catch (_error) {
          // Closing an owned AudioContext must not depend on model release succeeding.
        }
      }
      if (micVad.ownsAudioContext && audioContext
          && audioContext.state !== 'closed' && typeof audioContext.close === 'function') {
        try {
          await audioContext.close();
        } catch (_error) {
          // All controllable release paths have now been attempted.
        }
      }

      micVad.listening = false;
      micVad._stream = null;
      micVad._mediaStreamAudioSourceNode = null;
      micVad._vadNode = null;
      micVad._audioContext = null;
    })();
    return destroyPromise;
  };

  return Object.freeze({ start, pause, destroy });
}

function safeDisconnect(node) {
  if (!node || typeof node.disconnect !== 'function') return;
  try {
    node.disconnect();
  } catch (_error) {
    // A previously disconnected node is already safe.
  }
}

const FridaDialogueVadRuntime = Object.freeze({
  DIALOGUE_VAD_MODEL,
  DIALOGUE_VAD_PROCESSOR,
  DIALOGUE_VAD_PRE_SPEECH_PAD_MS,
  DIALOGUE_VAD_REDEMPTION_MS,
  DIALOGUE_VAD_MIN_SPEECH_MS,
  createDialogueVadRuntime,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaDialogueVadRuntime;
}

if (typeof window !== 'undefined') {
  window.FridaDialogueVadRuntime = FridaDialogueVadRuntime;
}
