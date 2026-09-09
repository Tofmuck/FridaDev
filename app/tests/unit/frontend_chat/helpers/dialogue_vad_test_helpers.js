'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const recorderModule = require('../../../../web/dialogue/dialogue_vad_recorder.js');
const runtimeModule = require('../../../../web/dialogue/dialogue_vad_runtime.js');

// Exercise the shipped distribution, not a copy of its segmentation algorithm.
const context = { console, Float32Array };
context.self = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.resolve(__dirname,
  '../../../../web/vendor/dialogue-vad/bundle.min.js'), 'utf8'), context);
const vendor = context.vad;

function deferred() {
  let resolve;
  const promise = new Promise((accept) => { resolve = accept; });
  return { promise, resolve };
}

function harness(overrides = {}) {
  const state = { now: 0, calls: 0, streams: [], vads: [], events: [], timers: new Map() };
  const runtime = runtimeModule.createDialogueVadRuntime({
    vadRuntime: { ...vendor, MicVAD: { async new(options) {
      state.factoryEntered = true;
      options = { ...vendor.getDefaultRealTimeVADOptions('legacy'), ...options };
      if (overrides.newGate) await overrides.newGate.promise;
      if (overrides.newError) throw new Error('synthetic VAD initialization');
      const model = { probability: 0, releases: 0, async release() { this.releases++; } };
      const fp = new vendor.FrameProcessor(async () => ({ isSpeech: model.probability }),
        () => {}, options, 96);
      const raw = new vendor.MicVAD(options, fp, model, 1536);
      raw.starts = 0;
      raw.start = async () => {
        raw.starts++;
        raw._stream = await options.getStream();
        if (overrides.startGate) await overrides.startGate.promise;
        if (overrides.startError) throw new Error('synthetic VAD start');
        raw.listening = true;
        fp.resume();
      };
      raw.pause = async () => {
        raw.listening = false;
        fp.pause(raw.handleFrameProcessorEvent);
        if (raw._stream) await options.pauseStream(raw._stream);
        if (overrides.pauseGate) await overrides.pauseGate.promise;
      };
      raw.feed = async (probability, value = 0) => {
        model.probability = probability;
        await raw.processFrame(new Float32Array(1536).fill(value));
      };
      state.vads.push(raw);
      return raw;
    } } },
    assetBaseUrl: '/vendor/dialogue-vad/',
  });
  state.recorder = recorderModule.createDialogueVadRecorder({
    ...runtime,
    mediaDevices: { async getUserMedia() {
      state.calls++;
      if (overrides.permissionGate) await overrides.permissionGate.promise;
      if (overrides.permissionError) throw Object.assign(new Error('private'), { name: 'NotAllowedError' });
      const track = new EventTarget();
      Object.assign(track, { readyState: 'live', enabled: true, stops: 0,
        stop() { this.stops++; this.readyState = 'ended'; this.enabled = false; } });
      const stream = { track, getTracks: () => [track] };
      state.streams.push(stream);
      return stream;
    } },
    documentObj: { querySelectorAll: () => overrides.media || [] },
    // Old implementation is deliberately exercisable by the red witnesses.
    MediaRecorderCtor: class {
      static isTypeSupported() { return true; }
      constructor() { this.state = 'inactive'; this.listeners = {}; this.mimeType = 'audio/mp4'; }
      addEventListener(name, callback) { this.listeners[name] = callback; }
      start() { this.state = 'recording'; }
      stop() { this.state = 'inactive'; this.listeners.stop?.(); }
    },
    nowFn: () => state.now,
    setTimeoutFn: (callback, delay) => { const id = {}; state.timers.set(id, { callback, at: state.now + delay }); return id; },
    clearTimeoutFn: (id) => state.timers.delete(id),
    onEvent: (event) => { state.events.push(event); overrides.onEvent?.(event, state); },
    ...overrides.options,
  });
  state.advance = (ms) => {
    state.now += ms;
    for (const [id, timer] of [...state.timers]) {
      if (timer.at <= state.now) { state.timers.delete(id); timer.callback(); }
    }
  };
  state.finish = (audio) => {
    const options = state.vads.at(-1).options;
    options.onSpeechRealStart();
    options.onSpeechEnd(audio);
  };
  state.blobs = () => state.events.filter((e) => e.type === 'blob');
  return state;
}

module.exports = { deferred, harness, vendor };
