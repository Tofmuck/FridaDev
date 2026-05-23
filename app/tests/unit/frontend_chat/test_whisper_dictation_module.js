'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const whisperDictation = require('../../../web/whisper/whisper_dictation.js');

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  toggle(name, enabled) {
    if (enabled) {
      this.values.add(name);
      return;
    }
    this.values.delete(name);
  }

  contains(name) {
    return this.values.has(name);
  }
}

class FakeBlob {
  constructor(parts = [], options = {}) {
    this.parts = parts;
    this.type = options.type || '';
    this.size = parts.reduce((total, part) => {
      if (typeof part === 'string') return total + Buffer.byteLength(part);
      if (part && typeof part.size === 'number') return total + part.size;
      if (part && typeof part.length === 'number') return total + part.length;
      return total;
    }, 0);
  }
}

class FakeFormData {
  constructor() {
    this.entries = [];
  }

  append(name, value, filename) {
    this.entries.push({ name, value, filename });
  }
}

class FakeMediaRecorder {
  static instances = [];

  static isTypeSupported(mimeType) {
    return mimeType === 'audio/webm;codecs=opus' || mimeType === 'audio/webm';
  }

  constructor(stream, options = {}) {
    this.stream = stream;
    this.state = 'inactive';
    this.mimeType = options.mimeType || 'audio/webm';
    this.listeners = new Map();
    FakeMediaRecorder.instances.push(this);
  }

  addEventListener(name, handler) {
    this.listeners.set(name, handler);
  }

  start(...args) {
    this.startArgs = args;
    this.state = 'recording';
  }

  stop() {
    this.state = 'inactive';
    const dataHandler = this.listeners.get('dataavailable');
    if (dataHandler) {
      dataHandler({ data: new FakeBlob(['audio-bytes'], { type: this.mimeType }) });
    }
    const stopHandler = this.listeners.get('stop');
    if (stopHandler) {
      stopHandler();
    }
  }

  emitError() {
    const errorHandler = this.listeners.get('error');
    if (errorHandler) {
      errorHandler({ error: new Error('recorder failed') });
    }
  }
}

function createButton() {
  const listeners = new Map();
  return {
    disabled: false,
    title: '',
    dataset: {},
    attributes: {},
    classList: new FakeClassList(),
    addEventListener(name, handler) {
      listeners.set(name, handler);
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    click() {
      const handler = listeners.get('click');
      if (handler) handler({ preventDefault() {} });
    },
  };
}

function createStatus() {
  return {
    textContent: '',
    dataset: {},
    classList: new FakeClassList(),
    setAttribute() {},
  };
}

function createTextarea(initialValue = '') {
  return {
    value: initialValue,
    focusCount: 0,
    selection: null,
    dispatchCount: 0,
    focus() {
      this.focusCount += 1;
    },
    setSelectionRange(start, end) {
      this.selection = { start, end };
    },
    dispatchEvent() {
      this.dispatchCount += 1;
      return true;
    },
  };
}

function createStream() {
  const listeners = new Map();
  const tracks = [
    {
      stopCount: 0,
      stop() { this.stopCount += 1; },
      addEventListener(name, handler) {
        listeners.set(name, handler);
      },
      emit(name) {
        const handler = listeners.get(name);
        if (handler) handler();
      },
    },
  ];
  return {
    tracks,
    getTracks() {
      return tracks;
    },
  };
}

function jsonResponse(statusCode, payload) {
  return {
    ok: statusCode >= 200 && statusCode < 300,
    status: statusCode,
    text: async () => JSON.stringify(payload),
  };
}

function flushAsync() {
  return new Promise((resolve) => setImmediate(resolve));
}

function createTimerHarness() {
  const calls = [];
  return {
    calls,
    setTimeoutFn(callback, delay) {
      calls.push({ callback, delay, cleared: false });
      return calls.length;
    },
    clearTimeoutFn(timerId) {
      if (calls[timerId - 1]) {
        calls[timerId - 1].cleared = true;
      }
    },
    fireLatest() {
      const call = calls[calls.length - 1];
      if (call && !call.cleared) call.callback();
    },
  };
}

test('default long dictation limit is bounded to 150 seconds', () => {
  assert.equal(whisperDictation.DEFAULT_MAX_RECORDING_MS, 150_000);
  assert.equal(whisperDictation.MAX_RECORDING_MS_LIMIT, 150_000);
  assert.equal(whisperDictation.normalizeMaxRecordingMs(undefined), 150_000);
  assert.equal(whisperDictation.normalizeMaxRecordingMs(120_000), 120_000);
  assert.equal(whisperDictation.normalizeMaxRecordingMs(999_999), 150_000);
});

test('joinTranscriptToDraft keeps clean paragraph separation', () => {
  assert.equal(
    whisperDictation.joinTranscriptToDraft('Bonjour', 'voici le transcript'),
    'Bonjour\n\nvoici le transcript',
  );
  assert.equal(
    whisperDictation.joinTranscriptToDraft('Bonjour\n', 'voici le transcript'),
    'Bonjour\nvoici le transcript',
  );
  assert.equal(
    whisperDictation.joinTranscriptToDraft('', 'voici le transcript'),
    'voici le transcript',
  );
});

test('createWhisperDictation reinjects the transcript into the existing draft', async () => {
  FakeMediaRecorder.instances = [];
  const buttonEl = createButton();
  const statusEl = createStatus();
  const textareaEl = createTextarea('Bonjour');
  const stream = createStream();
  const fetchCalls = [];
  const observedInputModes = [];

  const controller = whisperDictation.createWhisperDictation({
    buttonEl,
    statusEl,
    textareaEl,
    mediaDevices: {
      async getUserMedia() {
        return stream;
      },
    },
    MediaRecorderCtor: FakeMediaRecorder,
    BlobCtor: FakeBlob,
    FormDataCtor: FakeFormData,
    fetchImpl: async (url, options) => {
      fetchCalls.push({ url, options });
      return jsonResponse(200, { ok: true, text: 'voici le transcript', input_mode: 'voice' });
    },
    onDraftInputMode: (value) => {
      observedInputModes.push(value);
    },
    isBusy: () => false,
    setTimeoutFn: () => 1,
    clearTimeoutFn: () => {},
    nowFn: () => 0,
  });

  assert.equal(controller.getState(), 'idle');
  buttonEl.click();
  await flushAsync();

  assert.equal(controller.getState(), 'recording');
  assert.equal(buttonEl.dataset.dictationState, 'recording');
  assert.equal(statusEl.textContent, 'Enregistrement en cours.');
  assert.equal(statusEl.dataset.dictationState, 'recording');

  buttonEl.click();
  await flushAsync();
  await flushAsync();

  assert.equal(controller.getState(), 'idle');
  assert.equal(statusEl.dataset.dictationState, 'idle');
  assert.equal(textareaEl.value, 'Bonjour\n\nvoici le transcript');
  assert.equal(textareaEl.focusCount, 1);
  assert.deepEqual(textareaEl.selection, {
    start: textareaEl.value.length,
    end: textareaEl.value.length,
  });
  assert.equal(textareaEl.dispatchCount, 1);
  assert.equal(stream.tracks[0].stopCount, 1);
  assert.equal(fetchCalls.length, 1);
  assert.equal(fetchCalls[0].url, '/api/chat/transcribe');
  assert.equal(fetchCalls[0].options.method, 'POST');
  assert.equal(fetchCalls[0].options.body.entries[0].name, 'file');
  assert.equal(fetchCalls[0].options.body.entries[0].filename, 'dictation.webm');
  assert.deepEqual(
    fetchCalls[0].options.body.entries.slice(1),
    [
      { name: 'recording_duration_ms', value: '0', filename: undefined },
      { name: 'recording_blob_size_bytes', value: '11', filename: undefined },
      { name: 'recording_chunk_count', value: '1', filename: undefined },
      { name: 'recording_stop_reason', value: 'manual', filename: undefined },
    ],
  );
  assert.equal(controller.getLastStopReason(), 'manual');
  assert.deepEqual(FakeMediaRecorder.instances[0].startArgs, []);
  assert.deepEqual(observedInputModes, ['voice']);
});

test('createWhisperDictation preserves the draft when transcription fails', async () => {
  FakeMediaRecorder.instances = [];
  const buttonEl = createButton();
  const statusEl = createStatus();
  const textareaEl = createTextarea('Draft existant');
  const stream = createStream();

  const controller = whisperDictation.createWhisperDictation({
    buttonEl,
    statusEl,
    textareaEl,
    mediaDevices: {
      async getUserMedia() {
        return stream;
      },
    },
    MediaRecorderCtor: FakeMediaRecorder,
    BlobCtor: FakeBlob,
    FormDataCtor: FakeFormData,
    fetchImpl: async () => jsonResponse(504, { ok: false, error: 'transcription timeout' }),
    isBusy: () => false,
    setTimeoutFn: () => 1,
    clearTimeoutFn: () => {},
  });

  buttonEl.click();
  await flushAsync();
  buttonEl.click();
  await flushAsync();
  await flushAsync();

  assert.equal(controller.getState(), 'error');
  assert.equal(textareaEl.value, 'Draft existant');
  assert.equal(statusEl.textContent, 'transcription timeout');
  assert.equal(statusEl.dataset.dictationState, 'error');
  assert.equal(buttonEl.dataset.dictationState, 'error');
  assert.equal(stream.tracks[0].stopCount, 1);
});

test('createWhisperDictation marks duration-limit stops distinctly', async () => {
  FakeMediaRecorder.instances = [];
  const buttonEl = createButton();
  const statusEl = createStatus();
  const textareaEl = createTextarea('Avant');
  const stream = createStream();
  const timers = createTimerHarness();
  const fetchCalls = [];
  const telemetry = [];
  let now = 0;
  let resolveFetch;

  const controller = whisperDictation.createWhisperDictation({
    buttonEl,
    statusEl,
    textareaEl,
    mediaDevices: {
      async getUserMedia() {
        return stream;
      },
    },
    MediaRecorderCtor: FakeMediaRecorder,
    BlobCtor: FakeBlob,
    FormDataCtor: FakeFormData,
    fetchImpl: async (url, options) => {
      fetchCalls.push({ url, options });
      return new Promise((resolve) => {
        resolveFetch = () => resolve(jsonResponse(200, { ok: true, text: 'transcript long', input_mode: 'voice' }));
      });
    },
    isBusy: () => false,
    setTimeoutFn: timers.setTimeoutFn,
    clearTimeoutFn: timers.clearTimeoutFn,
    nowFn: () => now,
    onTelemetry: (eventName, payload) => {
      telemetry.push({ eventName, payload });
    },
  });

  buttonEl.click();
  await flushAsync();
  assert.equal(controller.getState(), 'recording');
  assert.equal(controller.getMaxRecordingMs(), 150_000);
  assert.equal(timers.calls[0].delay, 150_000);

  now = 150_000;
  timers.fireLatest();
  await flushAsync();

  assert.equal(controller.getState(), 'transcribing');
  assert.equal(controller.getLastStopReason(), 'auto_limit');
  assert.equal(statusEl.textContent, 'Limite de dictée atteinte. Transcription en cours.');
  assert.equal(statusEl.dataset.dictationState, 'transcribing');
  assert.equal(fetchCalls.length, 1);
  assert.deepEqual(
    fetchCalls[0].options.body.entries.slice(1),
    [
      { name: 'recording_duration_ms', value: '150000', filename: undefined },
      { name: 'recording_blob_size_bytes', value: '11', filename: undefined },
      { name: 'recording_chunk_count', value: '1', filename: undefined },
      { name: 'recording_stop_reason', value: 'auto_limit', filename: undefined },
    ],
  );
  assert.ok(JSON.stringify(telemetry).includes('"recording_stop_reason":"auto_limit"'));
  assert.ok(!JSON.stringify(telemetry).includes('transcript long'));

  resolveFetch();
  await flushAsync();
  await flushAsync();

  assert.equal(controller.getState(), 'idle');
  assert.equal(textareaEl.value, 'Avant\n\ntranscript long');
});

test('createWhisperDictation marks track-ended interruption distinctly', async () => {
  FakeMediaRecorder.instances = [];
  const buttonEl = createButton();
  const statusEl = createStatus();
  const textareaEl = createTextarea('Avant');
  const stream = createStream();
  let now = 0;
  let resolveFetch;

  const controller = whisperDictation.createWhisperDictation({
    buttonEl,
    statusEl,
    textareaEl,
    mediaDevices: {
      async getUserMedia() {
        return stream;
      },
    },
    MediaRecorderCtor: FakeMediaRecorder,
    BlobCtor: FakeBlob,
    FormDataCtor: FakeFormData,
    fetchImpl: async () => new Promise((resolve) => {
      resolveFetch = () => resolve(jsonResponse(200, { ok: true, text: 'suite', input_mode: 'voice' }));
    }),
    isBusy: () => false,
    setTimeoutFn: () => 1,
    clearTimeoutFn: () => {},
    nowFn: () => now,
  });

  buttonEl.click();
  await flushAsync();
  now = 42_000;
  stream.tracks[0].emit('ended');
  await flushAsync();

  assert.equal(controller.getState(), 'transcribing');
  assert.equal(controller.getLastStopReason(), 'track_ended');
  assert.equal(statusEl.textContent, 'Micro interrompu. Transcription en cours.');
  assert.equal(statusEl.dataset.dictationState, 'transcribing');

  resolveFetch();
  await flushAsync();
  await flushAsync();
  assert.equal(textareaEl.value, 'Avant\n\nsuite');
});

test('createWhisperDictation keeps draft and reports recorder errors without upload', async () => {
  FakeMediaRecorder.instances = [];
  const buttonEl = createButton();
  const statusEl = createStatus();
  const textareaEl = createTextarea('Draft existant');
  const stream = createStream();
  let fetchCalls = 0;

  const controller = whisperDictation.createWhisperDictation({
    buttonEl,
    statusEl,
    textareaEl,
    mediaDevices: {
      async getUserMedia() {
        return stream;
      },
    },
    MediaRecorderCtor: FakeMediaRecorder,
    BlobCtor: FakeBlob,
    FormDataCtor: FakeFormData,
    fetchImpl: async () => {
      fetchCalls += 1;
      return jsonResponse(200, { ok: true, text: 'ignored', input_mode: 'voice' });
    },
    isBusy: () => false,
    setTimeoutFn: () => 1,
    clearTimeoutFn: () => {},
  });

  buttonEl.click();
  await flushAsync();
  FakeMediaRecorder.instances[0].emitError();
  await flushAsync();
  FakeMediaRecorder.instances[0].stop();
  await flushAsync();

  assert.equal(controller.getState(), 'error');
  assert.equal(controller.getLastStopReason(), 'recorder_error');
  assert.equal(statusEl.textContent, 'Enregistrement audio interrompu');
  assert.equal(statusEl.dataset.dictationState, 'error');
  assert.equal(textareaEl.value, 'Draft existant');
  assert.equal(fetchCalls, 0);
});

test('createWhisperDictation disables the microphone while chat streaming is busy', async () => {
  FakeMediaRecorder.instances = [];
  const buttonEl = createButton();
  const statusEl = createStatus();
  const textareaEl = createTextarea('');
  let getUserMediaCalls = 0;

  whisperDictation.createWhisperDictation({
    buttonEl,
    statusEl,
    textareaEl,
    mediaDevices: {
      async getUserMedia() {
        getUserMediaCalls += 1;
        return createStream();
      },
    },
    MediaRecorderCtor: FakeMediaRecorder,
    BlobCtor: FakeBlob,
    FormDataCtor: FakeFormData,
    fetchImpl: async () => jsonResponse(200, { ok: true, text: 'bonjour', input_mode: 'voice' }),
    isBusy: () => true,
  });

  assert.equal(buttonEl.disabled, true);
  assert.equal(buttonEl.dataset.dictationState, 'busy');
  assert.equal(statusEl.dataset.dictationState, 'busy');
  buttonEl.click();
  await flushAsync();
  assert.equal(getUserMediaCalls, 0);
});
