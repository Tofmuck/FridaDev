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

test('D6.2b pinned D3 runtime selects V5 calibration and every asset path locally', async () => {
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
    positiveSpeechThreshold: runtime.vadOptions.positiveSpeechThreshold,
    negativeSpeechThreshold: runtime.vadOptions.negativeSpeechThreshold,
    startOnLoad: runtime.vadOptions.startOnLoad,
    processorType: runtime.vadOptions.processorType,
    preSpeechPadMs: runtime.vadOptions.preSpeechPadMs,
    redemptionMs: runtime.vadOptions.redemptionMs,
    minSpeechMs: runtime.vadOptions.minSpeechMs,
    baseAssetPath: runtime.vadOptions.baseAssetPath,
    onnxWASMBasePath: runtime.vadOptions.onnxWASMBasePath,
  }, {
    model: 'v5',
    positiveSpeechThreshold: 0.4,
    negativeSpeechThreshold: 0.4,
    startOnLoad: false,
    processorType: 'AudioWorklet',
    preSpeechPadMs: 800,
    redemptionMs: 1_400,
    minSpeechMs: 400,
    baseAssetPath: 'https://frida.invalid/vendor/dialogue-vad/',
    onnxWASMBasePath: 'https://frida.invalid/vendor/dialogue-vad/',
  });

  assert.equal('minSpeechFrames' in runtime.vadOptions, false);
  assert.equal('preSpeechPadFrames' in runtime.vadOptions, false);

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

test('D6.2b V5 frame guard accepts 512 samples and enforces bounds before append', async () => {
  const forwarded = [];
  const raw = createRawMicVad({
    frameProcessor: { audioBuffer: [], pause() {} },
    handleFrameProcessorEvent(event) { forwarded.push(event); },
  });
  const runtime = dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: { MicVAD: { new: async () => raw },
      Message: { SpeechStop: 'SPEECH_STOP', FrameProcessed: 'FRAME_PROCESSED' } },
    assetBaseUrl: '/vendor/dialogue-vad/',
  });
  const adapter = await runtime.vadFactory({ maxDurationMs: 320 });
  const event = { msg: 'FRAME_PROCESSED', frame: new Float32Array(512) };
  raw.frameProcessor.audioBuffer.length = 9;
  assert.doesNotThrow(() => raw.handleFrameProcessorEvent(event));
  assert.equal(forwarded.length, 1, 'ten V5 frames exactly fit 320 ms');
  raw.frameProcessor.audioBuffer.length = 10;
  assert.throws(() => raw.handleFrameProcessorEvent(event), /duration_limit_exceeded/);
  raw.frameProcessor.audioBuffer.length = 0;
  assert.throws(() => raw.handleFrameProcessorEvent({ ...event, frame: new Float32Array(1536) }), /vad_frame_invalid/);
  assert.equal(forwarded.length, 1, 'rejected frames never reach the segmenter');
  await adapter.destroy();
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

test('non-Error inference rejection still produces a closed runtime error', async () => {
  const failures = [];
  const raw = createRawMicVad({ async processFrame() { throw null; } });
  const runtime = dialogueRuntime.createDialogueVadRuntime({
    vadRuntime: { MicVAD: { new: async () => raw }, Message: { SpeechStop: 'SPEECH_STOP' } },
    assetBaseUrl: '/vendor/dialogue-vad/',
  });
  const adapter = await runtime.vadFactory({ onRuntimeError: (code) => failures.push(code) });
  await raw.processFrame(new Float32Array(512));
  assert.deepEqual(failures, ['vad_runtime_error']);
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

test('destroy cancels an in-flight frame before buffer append and releases the model afterwards', async () => {
  const { harness } = require('./helpers/dialogue_vad_test_helpers.js');
  const gate = deferred(), entered = deferred();
  const h = harness();
  await h.recorder.arm();
  const raw = h.vads[0];
  raw.frameProcessor.modelProcessFunc = async () => {
    entered.resolve();
    await gate.promise;
    return { isSpeech: 0.9 };
  };
  const frame = raw.processFrame(new Float32Array(512));
  await entered.promise;
  const stop = h.recorder.stop();
  assert.equal(h.streams[0].track.readyState, 'ended');
  assert.equal(raw.model.releases, 0, 'do not release a running inference session');
  gate.resolve();
  await Promise.all([frame, stop]);
  assert.equal(raw.frameProcessor.audioBuffer.length, 0);
  assert.equal(raw.model.releases, 1);
  assert.deepEqual(h.events, []);
});

test('concurrent inference cannot build an unbounded queue or emit late speech after error', async () => {
  const { harness } = require('./helpers/dialogue_vad_test_helpers.js');
  const gate = deferred(), entered = deferred();
  const h = harness();
  await h.recorder.arm();
  const raw = h.vads[0];
  let calls = 0;
  raw.frameProcessor.modelProcessFunc = async () => {
    calls++;
    entered.resolve();
    await gate.promise;
    return { isSpeech: 0.9 };
  };
  const frame = raw.processFrame(new Float32Array(512));
  await entered.promise;
  await raw.processFrame(new Float32Array(512));
  assert.deepEqual(h.events, [{ type: 'error', code: 'vad_runtime_error' }]);
  assert.equal(h.streams[0].track.readyState, 'ended');
  gate.resolve();
  await frame;
  await h.recorder.stop();
  assert.equal(calls, 1);
  assert.equal(raw.frameProcessor.audioBuffer.length, 0);
  assert.equal(raw.model.releases, 1);
});
