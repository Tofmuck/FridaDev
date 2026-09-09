'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const dialogueRuntime = require('../../../web/dialogue/dialogue_vad_runtime.js');

function deferred() {
  let resolve;
  const promise = new Promise((accept) => {
    resolve = accept;
  });
  return { promise, resolve };
}

function createRawMicVad(overrides = {}) {
  const model = {
    releaseCalls: 0,
    async release() {
      this.releaseCalls += 1;
    },
  };
  const frameProcessor = {
    pauseCalls: 0,
    pause() {
      this.pauseCalls += 1;
    },
  };
  return {
    model,
    frameProcessor,
    handleFrameProcessorEvent() {},
    initializationState: 'uninitialized',
    ownsAudioContext: false,
    listening: false,
    _stream: null,
    _audioContext: null,
    _vadNode: null,
    _mediaStreamAudioSourceNode: null,
    async start() {},
    async pause() {},
    async processFrame() {},
    ...overrides,
  };
}

test('pinned D3 runtime fixes the legacy model and every asset path locally', async () => {
  const createdOptions = [];
  const raw = createRawMicVad();
  const runtime = dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: {
      MicVAD: {
        async new(options) {
          createdOptions.push(options);
          return raw;
        },
      },
      Message: { SpeechStop: 'SPEECH_STOP' },
    },
    assetBaseUrl: 'https://frida.invalid/vendor/dialogue-vad/',
  });

  assert.deepEqual({
    model: runtime.vadOptions.model,
    processorType: runtime.vadOptions.processorType,
    preSpeechPadMs: runtime.vadOptions.preSpeechPadMs,
    redemptionMs: runtime.vadOptions.redemptionMs,
    minSpeechMs: runtime.vadOptions.minSpeechMs,
    baseAssetPath: runtime.vadOptions.baseAssetPath,
    onnxWASMBasePath: runtime.vadOptions.onnxWASMBasePath,
  }, {
    model: 'legacy',
    processorType: 'AudioWorklet',
    preSpeechPadMs: 800,
    redemptionMs: 1_400,
    minSpeechMs: 400,
    baseAssetPath: 'https://frida.invalid/vendor/dialogue-vad/',
    onnxWASMBasePath: 'https://frida.invalid/vendor/dialogue-vad/',
  });

  const ort = { env: { wasm: {} } };
  runtime.vadOptions.ortConfig(ort);
  assert.deepEqual(ort.env, {
    logLevel: 'error',
    wasm: {
      numThreads: 1,
      proxy: false,
      wasmPaths: {
        wasm: 'https://frida.invalid/vendor/dialogue-vad/ort-wasm-simd-threaded.wasm',
        mjs: 'https://frida.invalid/vendor/dialogue-vad/ort-wasm-simd-threaded.mjs',
      },
    },
  });

  const adapter = await runtime.vadFactory({ marker: 'recorder callbacks' });
  assert.deepEqual(createdOptions, [{ marker: 'recorder callbacks' }]);
  await adapter.destroy();
  assert.equal(raw.model.releaseCalls, 1);

  assert.throws(() => dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: { MicVAD: { new: async () => raw }, Message: {} },
    assetBaseUrl: '/vendor/dialogue-vad/',
  }), /runtime unavailable/);
});

test('partial MicVAD start failure still releases the model and owned AudioContext', async () => {
  const audioContext = {
    state: 'running',
    closeCalls: 0,
    async close() {
      this.closeCalls += 1;
      this.state = 'closed';
    },
  };
  const raw = createRawMicVad({
    async start() {
      this.initializationState = 'initializing';
      this.ownsAudioContext = true;
      this._audioContext = audioContext;
      this.initializationState = 'errored';
      throw new Error('audioWorklet.addModule failed');
    },
  });
  const runtime = dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: {
      MicVAD: { new: async () => raw },
      Message: { SpeechStop: 'SPEECH_STOP' },
    },
    assetBaseUrl: '/vendor/dialogue-vad/',
  });
  const adapter = await runtime.vadFactory({});

  await assert.rejects(adapter.start(), /audioWorklet\.addModule failed/);
  await adapter.destroy();

  assert.equal(raw.model.releaseCalls, 1);
  assert.equal(audioContext.closeCalls, 1);
  assert.equal(raw.frameProcessor.pauseCalls, 1);
  assert.equal(raw.initializationState, 'destroyed');
});

test('inference rejection becomes one closed runtime error and is not passed to MicVAD options', async () => {
  const vendorOptions = [];
  const runtimeErrors = [];
  const raw = createRawMicVad({
    async processFrame() {
      throw new Error('private ONNX failure');
    },
  });
  const runtime = dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: {
      MicVAD: {
        async new(options) {
          vendorOptions.push(options);
          return raw;
        },
      },
      Message: { SpeechStop: 'SPEECH_STOP' },
    },
    assetBaseUrl: '/vendor/dialogue-vad/',
  });
  const adapter = await runtime.vadFactory({
    marker: 'vendor option',
    onRuntimeError: () => runtimeErrors.push('vad_runtime_error'),
  });

  await raw.processFrame(new Float32Array([0.1]));
  await raw.processFrame(new Float32Array([0.2]));

  assert.deepEqual(vendorOptions, [{ marker: 'vendor option' }]);
  assert.deepEqual(runtimeErrors, ['vad_runtime_error']);
  await adapter.destroy();
});

test('destroy waits for an in-flight start then tears down every late audio resource once', async () => {
  const startGate = deferred();
  const sourceNode = {
    disconnectCalls: 0,
    disconnect() {
      this.disconnectCalls += 1;
    },
  };
  const messages = [];
  const vadNode = {
    disconnectCalls: 0,
    disconnect() {
      this.disconnectCalls += 1;
    },
    port: {
      postMessage(message) {
        messages.push(message);
      },
    },
  };
  const audioContext = {
    state: 'running',
    closeCalls: 0,
    async close() {
      this.closeCalls += 1;
      this.state = 'closed';
    },
  };
  const raw = createRawMicVad({
    async start() {
      this.initializationState = 'initializing';
      await startGate.promise;
      this.ownsAudioContext = true;
      this._audioContext = audioContext;
      this._mediaStreamAudioSourceNode = sourceNode;
      this._vadNode = vadNode;
      this.listening = true;
      this.initializationState = 'initialized';
    },
    async pause() {
      throw new Error('public pause failed');
    },
  });
  const runtime = dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: {
      MicVAD: { new: async () => raw },
      Message: { SpeechStop: 'SPEECH_STOP' },
    },
    assetBaseUrl: '/vendor/dialogue-vad/',
  });
  const adapter = await runtime.vadFactory({});
  const startPromise = adapter.start();
  let destroySettled = false;
  const destroyPromise = adapter.destroy().then(() => {
    destroySettled = true;
  });

  await Promise.resolve();
  assert.equal(destroySettled, false);
  startGate.resolve();
  await Promise.all([startPromise, destroyPromise]);
  await adapter.destroy();

  assert.equal(sourceNode.disconnectCalls, 1);
  assert.equal(vadNode.disconnectCalls, 1);
  assert.deepEqual(messages, ['SPEECH_STOP']);
  assert.equal(raw.model.releaseCalls, 1);
  assert.equal(audioContext.closeCalls, 1);
  assert.equal(raw.frameProcessor.pauseCalls, 1);
  assert.equal(raw.initializationState, 'destroyed');
});
