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

  start() {
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
  const tracks = [
    { stopCount: 0, stop() { this.stopCount += 1; } },
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
    isBusy: () => false,
    setTimeoutFn: () => 1,
    clearTimeoutFn: () => {},
  });

  assert.equal(controller.getState(), 'idle');
  buttonEl.click();
  await flushAsync();

  assert.equal(controller.getState(), 'recording');
  assert.equal(buttonEl.dataset.dictationState, 'recording');
  assert.equal(statusEl.textContent, 'Enregistrement en cours.');

  buttonEl.click();
  await flushAsync();
  await flushAsync();

  assert.equal(controller.getState(), 'idle');
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
  assert.equal(buttonEl.dataset.dictationState, 'error');
  assert.equal(stream.tracks[0].stopCount, 1);
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
  buttonEl.click();
  await flushAsync();
  assert.equal(getUserMediaCalls, 0);
});
