'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const dialogueVad = require('../../../web/dialogue/dialogue_vad_recorder.js');

class FakeBlob {
  constructor(parts = [], options = {}) {
    this.parts = [...parts];
    this.type = options.type || '';
    this.size = parts.reduce((total, part) => total + Number(part && part.size || 0), 0);
  }
}

class FakeMediaRecorder {
  static instances = [];
  static supportedTypes = new Set(['audio/mp4']);
  static throwOnConstruct = false;
  static throwOnStart = false;
  static throwOnStop = false;
  static suppressStopEvent = false;
  static operations = [];

  static reset() {
    this.instances = [];
    this.supportedTypes = new Set(['audio/mp4']);
    this.throwOnConstruct = false;
    this.throwOnStart = false;
    this.throwOnStop = false;
    this.suppressStopEvent = false;
    this.operations = [];
  }

  static isTypeSupported(mimeType) {
    return this.supportedTypes.has(mimeType);
  }

  constructor(stream, options = {}) {
    if (FakeMediaRecorder.throwOnConstruct) throw new Error('recorder construction failed');
    this.stream = stream;
    this.options = { ...options };
    this.mimeType = options.mimeType || '';
    this.state = 'inactive';
    this.startCalls = [];
    this.stopCalls = 0;
    this.finalData = null;
    this.listeners = new Map();
    FakeMediaRecorder.instances.push(this);
  }

  addEventListener(name, handler) {
    const handlers = this.listeners.get(name) || [];
    handlers.push(handler);
    this.listeners.set(name, handlers);
  }

  start(timeslice) {
    if (FakeMediaRecorder.throwOnStart) throw new Error('recorder start failed');
    if (this.state !== 'inactive') throw new Error('recorder already active');
    this.state = 'recording';
    this.startCalls.push(timeslice);
    FakeMediaRecorder.operations.push('recorder-start');
  }

  stop() {
    if (this.state === 'inactive') return;
    if (FakeMediaRecorder.throwOnStop) throw new Error('recorder stop failed');
    this.state = 'inactive';
    this.stopCalls += 1;
    if (FakeMediaRecorder.suppressStopEvent) return;
    queueMicrotask(() => {
      if (this.finalData) this.emit('dataavailable', { data: this.finalData });
      this.emit('stop', {});
    });
  }

  emitData(size, marker = '') {
    this.emit('dataavailable', {
      data: { size, type: this.mimeType, marker },
    });
  }

  emitError() {
    this.emit('error', { error: new Error('recorder runtime failed') });
  }

  emit(name, event) {
    for (const handler of this.listeners.get(name) || []) handler(event);
  }
}

function createTrack() {
  const listeners = new Map();
  return {
    enabled: true,
    readyState: 'live',
    stopCalls: 0,
    addEventListener(name, handler) {
      const handlers = listeners.get(name) || [];
      handlers.push(handler);
      listeners.set(name, handlers);
    },
    stop() {
      this.stopCalls += 1;
      this.enabled = false;
      this.readyState = 'ended';
    },
    endUnexpectedly() {
      this.readyState = 'ended';
      for (const handler of listeners.get('ended') || []) handler();
    },
  };
}

function createStream() {
  const tracks = [createTrack()];
  return {
    tracks,
    getTracks() {
      return tracks;
    },
  };
}

function createMediaElement({ paused = false, fail = false, remainActive = false } = {}) {
  return {
    paused,
    ended: false,
    pauseCalls: 0,
    pause() {
      this.pauseCalls += 1;
      if (fail) throw new Error('pause failed');
      if (!remainActive) this.paused = true;
    },
  };
}

function createTimerHarness() {
  let nextId = 1;
  const timers = new Map();
  return {
    setTimeoutFn(callback, delay) {
      const id = nextId++;
      timers.set(id, { callback, delay, cleared: false });
      return id;
    },
    clearTimeoutFn(id) {
      const timer = timers.get(id);
      if (timer) timer.cleared = true;
    },
    latest() {
      return [...timers.values()].at(-1);
    },
    fireLatest() {
      const timer = this.latest();
      if (timer && !timer.cleared) timer.callback();
    },
    allCleared() {
      return [...timers.values()].every((timer) => timer.cleared);
    },
  };
}

function createVadFactory({
  failNew = false,
  failStart = false,
  failDestroy = false,
  startGate = null,
  destroyGate = null,
  operations = [],
} = {}) {
  const instances = [];
  const factory = async (options) => {
    operations.push('vad-new');
    if (failNew) throw new Error('vad initialization failed');
    const instance = {
      options,
      stream: null,
      listening: false,
      startCalls: 0,
      pauseCalls: 0,
      destroyCalls: 0,
      async start() {
        operations.push('vad-start');
        this.startCalls += 1;
        if (failStart) throw new Error('vad start failed');
        this.stream = this.stream
          ? await options.resumeStream(this.stream)
          : await options.getStream();
        if (startGate) await startGate;
        this.listening = true;
      },
      async pause() {
        operations.push('vad-pause');
        this.pauseCalls += 1;
        if (!this.listening) return;
        await options.pauseStream(this.stream);
        this.listening = false;
      },
      async destroy() {
        operations.push('vad-destroy');
        this.destroyCalls += 1;
        if (destroyGate) await destroyGate;
        this.listening = false;
        if (failDestroy) throw new Error('vad destroy failed');
      },
      speechCandidate() {
        options.onSpeechStart();
      },
      speechStart() {
        options.onSpeechRealStart();
      },
      speechEnd() {
        options.onSpeechEnd(new Float32Array([0.1, 0.2]));
      },
      misfire() {
        options.onVADMisfire();
      },
      runtimeError() {
        options.onRuntimeError();
      },
    };
    instances.push(instance);
    return instance;
  };
  factory.instances = instances;
  return factory;
}

function createHarness(overrides = {}) {
  FakeMediaRecorder.reset();
  const operations = overrides.operations || [];
  FakeMediaRecorder.operations = operations;
  const stream = overrides.stream || createStream();
  const events = [];
  const timers = overrides.timers || createTimerHarness();
  const mediaElements = overrides.mediaElements || [];
  const vadFactory = overrides.vadFactory || createVadFactory({ operations });
  let getUserMediaCalls = 0;
  const mediaDevices = overrides.mediaDevices || {
    async getUserMedia(constraints) {
      operations.push('get-user-media');
      getUserMediaCalls += 1;
      assert.deepEqual(constraints, {
        audio: {
          channelCount: 1,
          echoCancellation: true,
          autoGainControl: true,
          noiseSuppression: true,
        },
      });
      if (overrides.permissionError) throw overrides.permissionError;
      return stream;
    },
  };
  const documentObj = overrides.documentObj || {
    querySelectorAll(selector) {
      assert.equal(selector, 'audio, video');
      return mediaElements;
    },
  };
  let now = 0;
  const recorder = dialogueVad.createDialogueVadRecorder({
    mediaDevices,
    MediaRecorderCtor: overrides.MediaRecorderCtor || FakeMediaRecorder,
    BlobCtor: FakeBlob,
    vadFactory,
    documentObj,
    ttsMediaElement: overrides.ttsMediaElement || null,
    setTimeoutFn: timers.setTimeoutFn,
    clearTimeoutFn: timers.clearTimeoutFn,
    nowFn: () => now,
    maxDurationMs: overrides.maxDurationMs,
    maxBytes: overrides.maxBytes,
    onEvent(event) {
      events.push(event);
      if (overrides.onEvent) overrides.onEvent(event);
    },
  });
  return {
    recorder,
    stream,
    events,
    timers,
    operations,
    vadFactory,
    getUserMediaCalls: () => getUserMediaCalls,
    setNow(value) {
      now = value;
    },
    mediaRecorder() {
      return FakeMediaRecorder.instances[0];
    },
    vad() {
      return vadFactory.instances[0];
    },
  };
}

async function flushAsync() {
  await new Promise((resolve) => setImmediate(resolve));
}

function eventTypes(harness) {
  return harness.events.map((event) => event.type);
}

test('does not request a microphone or construct audio machinery before arm', () => {
  const harness = createHarness();

  assert.equal(harness.getUserMediaCalls(), 0);
  assert.equal(harness.vadFactory.instances.length, 0);
  assert.equal(FakeMediaRecorder.instances.length, 0);
  assert.deepEqual(harness.events, []);
});

test('arms once, shares exactly one stream and starts recorder before VAD', async () => {
  const activeAudio = createMediaElement({ paused: false });
  const activeVideo = createMediaElement({ paused: false });
  const ownedTts = createMediaElement({ paused: false });
  const harness = createHarness({ mediaElements: [activeAudio, activeVideo], ttsMediaElement: ownedTts });

  await Promise.all([harness.recorder.arm(), harness.recorder.arm()]);

  assert.equal(harness.getUserMediaCalls(), 1);
  assert.equal(harness.vadFactory.instances.length, 1);
  assert.equal(FakeMediaRecorder.instances.length, 1);
  assert.equal(harness.mediaRecorder().stream, harness.stream);
  assert.equal(harness.vad().stream, harness.stream);
  assert.equal(await harness.vad().options.getStream(), harness.stream);
  assert.deepEqual(harness.operations, [
    'get-user-media',
    'recorder-start',
    'vad-new',
    'vad-start',
  ]);
  assert.equal(harness.mediaRecorder().startCalls.length, 1);
  assert.equal(harness.vad().startCalls, 1);
  assert.equal(activeAudio.pauseCalls, 1);
  assert.equal(activeVideo.pauseCalls, 1);
  assert.equal(ownedTts.pauseCalls, 1);
});

test('selects the first exact Safari MIME supported by D1 without inventing a codec', async () => {
  const harness = createHarness();
  FakeMediaRecorder.supportedTypes = new Set(['audio/webm', 'audio/mp4']);

  await harness.recorder.arm();

  assert.equal(harness.mediaRecorder().options.mimeType, 'audio/mp4');
  assert.equal(harness.mediaRecorder().mimeType, 'audio/mp4');
  assert.equal(harness.mediaRecorder().options.mimeType.includes('codecs='), false);
  await harness.recorder.stop();
});

test('fails closed when only an unallowlisted codec-qualified MIME is supported', async () => {
  const harness = createHarness();
  FakeMediaRecorder.supportedTypes = new Set(['audio/mp4;codecs=mp4a.40.2']);

  await harness.recorder.arm();

  assert.equal(harness.getUserMediaCalls(), 0);
  assert.deepEqual(eventTypes(harness), ['error']);
  assert.equal(harness.events[0].code, 'codec_unsupported');
});

test('emits one bounded blob from recognized speech and preserves pre-roll attack audio', async () => {
  const harness = createHarness();
  await harness.recorder.arm();
  const mediaRecorder = harness.mediaRecorder();

  harness.setNow(250);
  mediaRecorder.emitData(3, 'attack');
  harness.vad().speechCandidate();
  harness.setNow(500);
  mediaRecorder.emitData(4, 'first-word');
  harness.vad().speechStart();
  harness.setNow(750);
  mediaRecorder.emitData(5, 'utterance');
  harness.setNow(1_000);
  mediaRecorder.finalData = { size: 2, type: mediaRecorder.mimeType, marker: 'tail' };
  harness.vad().speechEnd();
  await flushAsync();

  assert.deepEqual(eventTypes(harness), ['speech-start', 'speech-end', 'blob']);
  const blobEvent = harness.events[2];
  assert.equal(blobEvent.mimeType, 'audio/mp4');
  assert.equal(blobEvent.sizeBytes, 14);
  assert.equal(blobEvent.durationMs, 1_000);
  assert.equal(blobEvent.blob instanceof FakeBlob, true);
  assert.deepEqual(Object.keys(blobEvent).sort(), [
    'blob',
    'durationMs',
    'mimeType',
    'sizeBytes',
    'type',
  ]);
  assert.deepEqual(blobEvent.blob.parts.map((part) => part.marker), [
    'attack',
    'first-word',
    'utterance',
    'tail',
  ]);
  assert.equal('transcript' in blobEvent, false);
  assert.equal(mediaRecorder.startCalls.length, 2, 'the same recorder returns to bounded pre-roll capture');
  assert.equal(FakeMediaRecorder.instances.length, 1);
});

test('discards candidate noise and VAD misfires without speech or blob events', async () => {
  const harness = createHarness();
  await harness.recorder.arm();

  harness.mediaRecorder().emitData(8, 'noise');
  harness.vad().speechCandidate();
  harness.vad().misfire();
  harness.mediaRecorder().emitData(4, 'silence');
  await flushAsync();

  assert.deepEqual(harness.events, []);
  assert.equal(harness.mediaRecorder().stopCalls, 0);
});

test('pause releases its stream, explicit resume creates one new shared cycle, and stop cleans it', async () => {
  const streams = [createStream(), createStream()];
  let getUserMediaCalls = 0;
  const harness = createHarness({
    stream: streams[0],
    mediaDevices: {
      async getUserMedia() {
        const nextStream = streams[getUserMediaCalls];
        getUserMediaCalls += 1;
        return nextStream;
      },
    },
  });
  await harness.recorder.arm();
  const mediaRecorder = harness.mediaRecorder();
  harness.vad().speechStart();
  mediaRecorder.emitData(5, 'discarded-on-pause');

  await harness.recorder.pause();

  assert.equal(streams[0].tracks[0].readyState, 'ended');
  assert.equal(streams[0].tracks[0].stopCalls, 1);
  assert.equal(harness.vad().pauseCalls, 1);
  assert.equal(harness.vad().destroyCalls, 1);
  assert.equal(mediaRecorder.state, 'inactive');
  assert.deepEqual(eventTypes(harness), ['speech-start']);

  await Promise.all([harness.recorder.resume(), harness.recorder.resume()]);

  assert.equal(getUserMediaCalls, 2);
  assert.equal(FakeMediaRecorder.instances.length, 2);
  assert.equal(harness.vadFactory.instances.length, 2);
  assert.equal(FakeMediaRecorder.instances[1].stream, streams[1]);
  assert.equal(harness.vadFactory.instances[1].stream, streams[1]);

  await harness.recorder.stop();

  assert.equal(streams[1].tracks[0].stopCalls, 1);
  assert.equal(harness.vadFactory.instances[1].destroyCalls, 1);
  assert.equal(FakeMediaRecorder.instances[1].state, 'inactive');
  assert.equal(harness.timers.allCleared(), true);
});

test('duration overflow emits error, no blob, and performs terminal cleanup', async () => {
  const harness = createHarness({ maxDurationMs: 1_000 });
  await harness.recorder.arm();
  harness.vad().speechStart();

  assert.equal(harness.timers.latest().delay, 1_001);
  harness.setNow(1_001);
  harness.timers.fireLatest();
  await flushAsync();

  assert.deepEqual(eventTypes(harness), ['speech-start', 'error']);
  assert.equal(harness.events[1].code, 'duration_limit_exceeded');
  assert.equal(harness.stream.tracks[0].stopCalls, 1);
  assert.equal(harness.vad().destroyCalls, 1);
  assert.equal(harness.mediaRecorder().state, 'inactive');

  await harness.recorder.resume();
  assert.equal(harness.getUserMediaCalls(), 1, 'error never rearms implicitly');
});

test('exact duration limit is accepted but any final chunk beyond it is rejected', async () => {
  const accepted = createHarness({ maxDurationMs: 1_000 });
  await accepted.recorder.arm();
  accepted.vad().speechStart();
  accepted.mediaRecorder().finalData = {
    size: 1,
    type: accepted.mediaRecorder().mimeType,
    marker: 'exact-duration-tail',
  };
  accepted.setNow(1_000);
  accepted.vad().speechEnd();
  await flushAsync();
  assert.equal(accepted.events.find((event) => event.type === 'blob').durationMs, 1_000);
  await accepted.recorder.stop();

  const rejected = createHarness({ maxDurationMs: 1_000 });
  await rejected.recorder.arm();
  rejected.vad().speechStart();
  rejected.mediaRecorder().finalData = {
    size: 1,
    type: rejected.mediaRecorder().mimeType,
    marker: 'late-duration-tail',
  };
  rejected.setNow(1_001);
  rejected.vad().speechEnd();
  await flushAsync();

  assert.deepEqual(eventTypes(rejected), ['speech-start', 'speech-end', 'error']);
  assert.equal(rejected.events.at(-1).code, 'duration_limit_exceeded');
  assert.equal(rejected.events.some((event) => event.type === 'blob'), false);
  assert.equal(rejected.stream.tracks[0].stopCalls, 1);

  const fractionallyLate = createHarness({ maxDurationMs: 1_000 });
  await fractionallyLate.recorder.arm();
  fractionallyLate.vad().speechStart();
  fractionallyLate.mediaRecorder().finalData = {
    size: 1,
    type: fractionallyLate.mediaRecorder().mimeType,
    marker: 'fractionally-late-tail',
  };
  fractionallyLate.setNow(1_000.4);
  fractionallyLate.vad().speechEnd();
  await flushAsync();
  assert.equal(fractionallyLate.events.some((event) => event.type === 'blob'), false);
  assert.equal(fractionallyLate.events.at(-1).code, 'duration_limit_exceeded');
});

test('size overflow emits error without truncating or emitting a blob', async () => {
  const harness = createHarness({ maxBytes: 10 });
  await harness.recorder.arm();
  harness.vad().speechStart();
  harness.mediaRecorder().emitData(11, 'oversized');
  await flushAsync();

  assert.deepEqual(eventTypes(harness), ['speech-start', 'error']);
  assert.equal(harness.events[1].code, 'size_limit_exceeded');
  assert.equal(harness.stream.tracks[0].stopCalls, 1);
  assert.equal(harness.mediaRecorder().state, 'inactive');
});

test('exact size limit is accepted but a final stop chunk over the limit is rejected', async () => {
  const accepted = createHarness({ maxBytes: 10 });
  await accepted.recorder.arm();
  accepted.vad().speechStart();
  accepted.mediaRecorder().emitData(10, 'exact-limit');
  accepted.vad().speechEnd();
  await flushAsync();
  assert.equal(accepted.events.find((event) => event.type === 'blob').sizeBytes, 10);
  await accepted.recorder.stop();

  const rejected = createHarness({ maxBytes: 10 });
  await rejected.recorder.arm();
  rejected.vad().speechStart();
  rejected.mediaRecorder().emitData(10, 'before-tail');
  rejected.mediaRecorder().finalData = {
    size: 1,
    type: rejected.mediaRecorder().mimeType,
    marker: 'final-tail-over-limit',
  };
  rejected.vad().speechEnd();
  await flushAsync();

  assert.deepEqual(eventTypes(rejected), ['speech-start', 'speech-end', 'error']);
  assert.equal(rejected.events.at(-1).code, 'size_limit_exceeded');
  assert.equal(rejected.events.some((event) => event.type === 'blob'), false);
  assert.equal(rejected.stream.tracks[0].stopCalls, 1);
});

test('double speech end and double arm cannot produce duplicate blobs or machinery', async () => {
  const harness = createHarness();
  await Promise.all([harness.recorder.arm(), harness.recorder.arm()]);
  harness.vad().speechStart();
  harness.mediaRecorder().emitData(6, 'single');
  harness.vad().speechEnd();
  harness.vad().speechEnd();
  await flushAsync();

  assert.equal(harness.getUserMediaCalls(), 1);
  assert.equal(harness.vadFactory.instances.length, 1);
  assert.equal(FakeMediaRecorder.instances.length, 1);
  assert.equal(harness.events.filter((event) => event.type === 'speech-end').length, 1);
  assert.equal(harness.events.filter((event) => event.type === 'blob').length, 1);
});

test('successive utterances produce isolated blobs on the same recorder', async () => {
  const harness = createHarness();
  await harness.recorder.arm();
  const mediaRecorder = harness.mediaRecorder();

  harness.vad().speechStart();
  mediaRecorder.emitData(3, 'first');
  harness.vad().speechEnd();
  await flushAsync();

  harness.vad().speechStart();
  mediaRecorder.emitData(4, 'second');
  harness.vad().speechEnd();
  await flushAsync();

  const blobs = harness.events.filter((event) => event.type === 'blob');
  assert.equal(blobs.length, 2);
  assert.deepEqual(blobs[0].blob.parts.map((part) => part.marker), ['first']);
  assert.deepEqual(blobs[1].blob.parts.map((part) => part.marker), ['second']);
  assert.equal(FakeMediaRecorder.instances.length, 1);
});

test('a blob consumer can stop synchronously without a phantom recorder restart', async () => {
  let harness;
  harness = createHarness({
    onEvent(event) {
      if (event.type === 'blob') void harness.recorder.stop();
    },
  });
  await harness.recorder.arm();
  harness.vad().speechStart();
  harness.mediaRecorder().emitData(4, 'complete');
  harness.vad().speechEnd();
  await flushAsync();

  assert.deepEqual(eventTypes(harness), ['speech-start', 'speech-end', 'blob']);
  assert.equal(harness.mediaRecorder().startCalls.length, 1);
  assert.equal(harness.stream.tracks[0].stopCalls, 1);
});

test('callbacks from a released paused cycle cannot affect the resumed cycle', async () => {
  const streams = [createStream(), createStream()];
  let streamIndex = 0;
  const harness = createHarness({
    stream: streams[0],
    mediaDevices: {
      async getUserMedia() {
        return streams[streamIndex++];
      },
    },
  });
  await harness.recorder.arm();
  const oldVad = harness.vadFactory.instances[0];
  const oldRecorder = FakeMediaRecorder.instances[0];
  await harness.recorder.pause();
  await harness.recorder.resume();

  oldVad.speechStart();
  oldVad.speechEnd();
  oldRecorder.emitData(9, 'late-old-data');
  oldRecorder.emitError();
  await flushAsync();

  assert.deepEqual(harness.events, []);
  assert.equal(FakeMediaRecorder.instances[1].state, 'recording');
  await harness.recorder.stop();
});

test('permission, VAD and recorder failures are closed errors with complete cleanup', async (t) => {
  await t.test('permission failure', async () => {
    const denied = new Error('denied');
    denied.name = 'NotAllowedError';
    const harness = createHarness({ permissionError: denied });
    await harness.recorder.arm();
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'microphone_permission_denied');
    assert.equal(FakeMediaRecorder.instances.length, 0);
  });

  await t.test('VAD initialization failure', async () => {
    const operations = [];
    const vadFactory = createVadFactory({ failNew: true, operations });
    const harness = createHarness({ vadFactory, operations });
    await harness.recorder.arm();
    await flushAsync();
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'vad_initialization_failed');
    assert.equal(harness.stream.tracks[0].stopCalls, 1);
    assert.equal(harness.mediaRecorder().state, 'inactive');
  });

  await t.test('VAD start failure', async () => {
    const operations = [];
    const vadFactory = createVadFactory({ failStart: true, operations });
    const harness = createHarness({ vadFactory, operations });
    await harness.recorder.arm();
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'vad_initialization_failed');
    assert.equal(harness.stream.tracks[0].stopCalls, 1);
    assert.equal(harness.vad().destroyCalls, 1);
    assert.equal(harness.mediaRecorder().state, 'inactive');
  });

  await t.test('recorder construction failure', async () => {
    FakeMediaRecorder.throwOnConstruct = true;
    const harness = createHarness();
    FakeMediaRecorder.throwOnConstruct = true;
    await harness.recorder.arm();
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'recorder_initialization_failed');
    assert.equal(harness.stream.tracks[0].stopCalls, 1);
    assert.equal(harness.vadFactory.instances.length, 0);
  });

  await t.test('recorder start failure', async () => {
    const harness = createHarness();
    FakeMediaRecorder.throwOnStart = true;
    await harness.recorder.arm();
    await flushAsync();
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'recorder_initialization_failed');
    assert.equal(harness.stream.tracks[0].stopCalls, 1);
    assert.equal(harness.vadFactory.instances.length, 0);
  });

  await t.test('recorder runtime failure', async () => {
    const harness = createHarness();
    await harness.recorder.arm();
    harness.mediaRecorder().emitError();
    await flushAsync();
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'recorder_error');
    assert.equal(harness.stream.tracks[0].stopCalls, 1);
    assert.equal(harness.vad().destroyCalls, 1);
  });
});

test('refuses microphone access when any controllable active media cannot certainly pause', async () => {
  for (const media of [
    createMediaElement({ paused: false, fail: true }),
    createMediaElement({ paused: false, remainActive: true }),
  ]) {
    const harness = createHarness({ mediaElements: [media] });
    await harness.recorder.arm();
    assert.equal(harness.getUserMediaCalls(), 0);
    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'media_pause_failed');
  }
});

test('stop during pending permission invalidates late stream without constructing VAD or recorder', async () => {
  let resolveStream;
  let gumCalls = 0;
  const lateStream = createStream();
  const harness = createHarness({
    mediaDevices: {
      async getUserMedia() {
        gumCalls += 1;
        return new Promise((resolve) => { resolveStream = resolve; });
      },
    },
  });

  const armPromise = harness.recorder.arm();
  await flushAsync();
  const stopPromise = harness.recorder.stop();
  resolveStream(lateStream);
  await Promise.all([armPromise, stopPromise]);

  assert.equal(gumCalls, 1);
  assert.equal(lateStream.tracks[0].stopCalls, 1);
  assert.equal(harness.vadFactory.instances.length, 0);
  assert.equal(FakeMediaRecorder.instances.length, 0);
  assert.deepEqual(harness.events, []);
});

test('stop while controllable media is still pausing never reaches microphone acquisition', async () => {
  let resolvePause;
  const media = createMediaElement({ paused: false });
  media.pause = async function pause() {
    this.pauseCalls += 1;
    await new Promise((resolve) => { resolvePause = resolve; });
    this.paused = true;
  };
  const harness = createHarness({ mediaElements: [media] });

  const armPromise = harness.recorder.arm();
  await flushAsync();
  const stopPromise = harness.recorder.stop();
  resolvePause();
  await Promise.all([armPromise, stopPromise]);

  assert.equal(harness.getUserMediaCalls(), 0);
  assert.equal(FakeMediaRecorder.instances.length, 0);
  assert.equal(harness.vadFactory.instances.length, 0);
  assert.deepEqual(harness.events, []);
});

test('stop during VAD start performs a second terminal release after initialization settles', async () => {
  let resolveVadStart;
  const startGate = new Promise((resolve) => { resolveVadStart = resolve; });
  const vadFactory = createVadFactory({ startGate, destroyGate: startGate });
  const harness = createHarness({ vadFactory });

  const armPromise = harness.recorder.arm();
  await flushAsync();
  assert.equal(harness.vad().startCalls, 1);
  const stopPromise = harness.recorder.stop();
  await flushAsync();
  assert.equal(harness.vad().destroyCalls, 1);
  assert.equal(harness.stream.tracks[0].readyState, 'ended');
  assert.equal(harness.stream.tracks[0].stopCalls, 1);
  resolveVadStart();
  await Promise.all([armPromise, stopPromise]);

  assert.equal(harness.vad().listening, false);
  assert.ok(harness.vad().destroyCalls >= 2);
  assert.equal(harness.stream.tracks[0].stopCalls, 1);
  assert.equal(harness.mediaRecorder().state, 'inactive');
  harness.vad().speechStart();
  assert.deepEqual(harness.events, []);
});

test('pause and stop destroy a VAD instance returned while shared cleanup is already in flight', async () => {
  for (const method of ['pause', 'stop']) {
    let releaseFactory;
    let markFactoryEntered;
    const factoryGate = new Promise((resolve) => { releaseFactory = resolve; });
    const factoryEntered = new Promise((resolve) => { markFactoryEntered = resolve; });
    const baseFactory = createVadFactory();
    const gatedFactory = async (options) => {
      const instance = await baseFactory(options);
      markFactoryEntered();
      await factoryGate;
      return instance;
    };
    gatedFactory.instances = baseFactory.instances;
    const harness = createHarness({ vadFactory: gatedFactory });

    const armPromise = harness.recorder.arm();
    await factoryEntered;
    const releasePromise = harness.recorder[method]();
    releaseFactory();
    await Promise.all([armPromise, releasePromise]);

    assert.equal(baseFactory.instances[0].startCalls, 0);
    assert.equal(baseFactory.instances[0].destroyCalls, 1, `${method} must destroy late VAD`);
    assert.equal(harness.stream.tracks[0].readyState, 'ended');
    assert.equal(harness.mediaRecorder().state, 'inactive');
  }
});

test('repeated stop and pause calls await the same in-flight cleanup', async () => {
  for (const method of ['pause', 'stop']) {
    let releaseDestroy;
    const destroyGate = new Promise((resolve) => { releaseDestroy = resolve; });
    const vadFactory = createVadFactory({ destroyGate });
    const harness = createHarness({ vadFactory });
    await harness.recorder.arm();

    const first = harness.recorder[method]();
    let secondSettled = false;
    const second = harness.recorder[method]().then(() => {
      secondSettled = true;
    });
    await flushAsync();

    assert.equal(secondSettled, false, `${method} must remain awaitable during cleanup`);
    assert.equal(harness.stream.tracks[0].readyState, 'ended');
    assert.equal(harness.vad().destroyCalls, 1);
    releaseDestroy();
    await Promise.all([first, second]);
    assert.equal(secondSettled, true);
  }
});

test('resume requested during pause waits for cleanup then creates exactly one new shared cycle', async () => {
  let releaseDestroy;
  const destroyGate = new Promise((resolve) => { releaseDestroy = resolve; });
  const streams = [createStream(), createStream()];
  let getUserMediaCalls = 0;
  const vadFactory = createVadFactory({ destroyGate });
  const harness = createHarness({
    vadFactory,
    mediaDevices: {
      async getUserMedia() {
        return streams[getUserMediaCalls++];
      },
    },
  });
  await harness.recorder.arm();

  const pausePromise = harness.recorder.pause();
  const resumePromise = harness.recorder.resume();
  await flushAsync();

  assert.equal(getUserMediaCalls, 1);
  assert.equal(FakeMediaRecorder.instances.length, 1);
  releaseDestroy();
  await Promise.all([pausePromise, resumePromise]);

  assert.equal(getUserMediaCalls, 2);
  assert.equal(FakeMediaRecorder.instances.length, 2);
  assert.equal(vadFactory.instances.length, 2);
  assert.equal(FakeMediaRecorder.instances[1].stream, streams[1]);
  assert.equal(vadFactory.instances[1].stream, streams[1]);
  await harness.recorder.stop();
});

test('missing recorder stop event stays bounded and explicit pause still completes cleanup', async () => {
  const finalizing = createHarness({ maxDurationMs: 1_000 });
  await finalizing.recorder.arm();
  FakeMediaRecorder.suppressStopEvent = true;
  finalizing.vad().speechStart();
  finalizing.setNow(500);
  finalizing.vad().speechEnd();
  await flushAsync();

  assert.deepEqual(eventTypes(finalizing), ['speech-start', 'speech-end']);
  finalizing.setNow(1_001);
  finalizing.timers.fireLatest();
  await flushAsync();
  assert.deepEqual(eventTypes(finalizing), ['speech-start', 'speech-end', 'error']);
  assert.equal(finalizing.events.at(-1).code, 'duration_limit_exceeded');
  assert.equal(finalizing.stream.tracks[0].readyState, 'ended');
  assert.equal(finalizing.vad().destroyCalls, 1);

  const pausing = createHarness();
  await pausing.recorder.arm();
  FakeMediaRecorder.suppressStopEvent = true;
  let pauseSettled = false;
  const pausePromise = pausing.recorder.pause().then(() => {
    pauseSettled = true;
  });
  await flushAsync();

  assert.equal(pauseSettled, true);
  assert.equal(pausing.stream.tracks[0].readyState, 'ended');
  assert.equal(pausing.vad().destroyCalls, 1);
  await pausePromise;
});

test('recorder stop exception is terminal and never emits an incomplete blob', async () => {
  const harness = createHarness();
  await harness.recorder.arm();
  harness.vad().speechStart();
  harness.mediaRecorder().emitData(4, 'incomplete');
  FakeMediaRecorder.throwOnStop = true;
  harness.vad().speechEnd();
  await flushAsync();

  assert.deepEqual(eventTypes(harness), ['speech-start', 'speech-end', 'error']);
  assert.equal(harness.events.at(-1).code, 'recorder_error');
  assert.equal(harness.events.some((event) => event.type === 'blob'), false);
  assert.equal(harness.stream.tracks[0].readyState, 'ended');
  assert.equal(harness.vad().destroyCalls, 1);
});

test('unexpected track end is terminal and every dependency remains fetch-free', async () => {
  const originalFetch = globalThis.fetch;
  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new Error('network forbidden');
  };
  try {
    const harness = createHarness();
    await harness.recorder.arm();
    harness.stream.tracks[0].endUnexpectedly();
    await flushAsync();

    assert.deepEqual(eventTypes(harness), ['error']);
    assert.equal(harness.events[0].code, 'track_ended');
    assert.equal(harness.stream.tracks[0].readyState, 'ended');
    assert.equal(harness.vad().destroyCalls, 1);
    assert.equal(fetchCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('VAD inference failure is terminal, closed and fully releases local capture', async () => {
  const harness = createHarness();
  await harness.recorder.arm();

  harness.vad().runtimeError();
  harness.vad().runtimeError();
  await flushAsync();

  assert.deepEqual(eventTypes(harness), ['error']);
  assert.equal(harness.events[0].code, 'vad_runtime_error');
  assert.equal(harness.stream.tracks[0].readyState, 'ended');
  assert.equal(harness.mediaRecorder().state, 'inactive');
  assert.equal(harness.vad().destroyCalls, 1);
});

test('cleanup still releases the recorder and tracks when VAD destroy fails', async () => {
  const vadFactory = createVadFactory({ failDestroy: true });
  const harness = createHarness({ vadFactory });
  await harness.recorder.arm();

  await harness.recorder.stop();

  assert.equal(harness.vad().destroyCalls, 1);
  assert.equal(harness.mediaRecorder().state, 'inactive');
  assert.equal(harness.stream.tracks[0].stopCalls, 1);
  assert.deepEqual(harness.events, []);
});
