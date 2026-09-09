'use strict';

const DIALOGUE_VAD_MODEL = 'legacy';
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
    processorType: DIALOGUE_VAD_PROCESSOR,
    preSpeechPadMs: DIALOGUE_VAD_PRE_SPEECH_PAD_MS,
    redemptionMs: DIALOGUE_VAD_REDEMPTION_MS,
    minSpeechMs: DIALOGUE_VAD_MIN_SPEECH_MS,
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
      ...vendorOptions
    } = micVadOptions || {};
    const micVad = await vadRuntime.MicVAD.new(vendorOptions);
    return createPinnedMicVadAdapter(micVad, vadRuntime, onRuntimeError);
  };

  return Object.freeze({ vadFactory, vadOptions });
}

function createPinnedMicVadAdapter(micVad, vadRuntime, onRuntimeError) {
  let startPromise = null;
  let destroyPromise = null;
  let destroyRequested = false;
  let runtimeFailed = false;

  if (typeof micVad.processFrame === 'function') {
    const vendorProcessFrame = micVad.processFrame.bind(micVad);
    micVad.processFrame = async (frame) => {
      if (runtimeFailed || destroyRequested) return;
      try {
        await vendorProcessFrame(frame);
      } catch (_error) {
        if (runtimeFailed || destroyRequested) return;
        runtimeFailed = true;
        if (typeof onRuntimeError === 'function') {
          try {
            onRuntimeError();
          } catch (_callbackError) {
            // The recorder owns the terminal projection; never leak a vendor rejection.
          }
        }
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

  const pause = async () => {
    if (destroyRequested || typeof micVad.pause !== 'function') return;
    await micVad.pause();
  };

  const destroy = () => {
    if (destroyPromise) return destroyPromise;
    destroyRequested = true;
    destroyPromise = (async () => {
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
