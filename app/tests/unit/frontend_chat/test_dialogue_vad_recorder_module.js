'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { harness, deferred } = require('./helpers/dialogue_vad_test_helpers.js');
const { DIALOGUE_RECORDER_MAX_DURATION_MS, DIALOGUE_RECORDER_MAX_BYTES } =
  require('../../../web/dialogue/dialogue_vad_recorder.js');

function assertReleased(h) {
  for (const stream of h.streams) {
    assert.equal(stream.track.readyState, 'ended');
    assert.equal(stream.track.stops, 1);
  }
  for (const raw of h.vads) {
    assert.equal(raw.model.releases, 1);
    assert.equal(raw.frameProcessor.audioBuffer.length, 0);
    assert.equal(raw.listening, false);
    assert.equal(raw._stream, null);
  }
  assert.equal(h.timers.size, 0);
}

test('no microphone before arm; double arm has one VAD and one identical stream', async () => {
  const h = harness();
  assert.equal(h.calls, 0);
  assert.equal(h.vads.length, 0);
  await Promise.all([h.recorder.arm(), h.recorder.arm()]);
  assert.equal(h.calls, 1);
  assert.equal(h.vads.length, 1);
  assert.equal(h.vads[0]._stream, h.streams[0]);
  assert.equal(await h.vads[0].options.getStream(), h.streams[0]);
  assert.equal(await h.vads[0].options.resumeStream(h.streams[0]), h.streams[0]);
  assert.equal(h.calls, 1);
  await h.recorder.stop();
  assertReleased(h);
});

test('WAV is mono PCM16 16000Hz with exact RIFF sizes and first/last samples', async () => {
  const h = harness({ options: { MediaRecorderCtor: class { constructor() { assert.fail('recorder forbidden'); } } } });
  await h.recorder.arm();
  h.finish(new Float32Array([-1, -0.5, 0, 0.5, 1]));
  assert.deepEqual(h.events.map((e) => e.type), ['speech-start', 'speech-end', 'blob']);
  const event = h.blobs()[0];
  const buffer = await event.blob.arrayBuffer();
  const view = new DataView(buffer);
  assert.equal(Buffer.from(buffer).toString('ascii', 0, 4), 'RIFF');
  assert.equal(Buffer.from(buffer).toString('ascii', 8, 16), 'WAVEfmt ');
  assert.equal(Buffer.from(buffer).toString('ascii', 36, 40), 'data');
  assert.deepEqual([view.getUint32(4, true), view.getUint32(16, true), view.getUint16(20, true),
    view.getUint16(22, true), view.getUint32(24, true), view.getUint32(28, true),
    view.getUint16(32, true), view.getUint16(34, true), view.getUint32(40, true)],
  [46, 16, 1, 1, 16000, 32000, 2, 16, 10]);
  assert.deepEqual(Array.from({ length: 5 }, (_, i) => view.getInt16(44 + 2 * i, true)),
    [-32768, -16384, 0, 16383, 32767]);
  assert.equal(event.durationMs, 5 / 16);
  assert.equal(event.sizeBytes, 54);
  assert.equal(event.blob.type, 'audio/wav');
  assert.equal(event.mimeType, 'audio/wav');
  assert.deepEqual(Object.keys(event).sort(), ['blob', 'durationMs', 'mimeType', 'sizeBytes', 'type']);
  await h.recorder.stop();
});

test('exact 300000ms accepted, next sample rejected, injected limits cannot raise hard ceilings', async () => {
  assert.equal(DIALOGUE_RECORDER_MAX_DURATION_MS, 300000);
  assert.equal(DIALOGUE_RECORDER_MAX_BYTES, 24000000);
  for (const samples of [4800000, 4800001]) {
    const h = harness({ options: { maxDurationMs: 999999, maxBytes: 99999999 } });
    await h.recorder.arm();
    h.finish(new Float32Array(samples));
    if (samples === 4800000) {
      assert.equal(h.blobs()[0]?.durationMs, 300000);
      assert.equal(h.blobs()[0]?.sizeBytes, 9600044);
    } else {
      assert.equal(h.blobs().length, 0);
      assert.equal(h.events.at(-1).code, 'duration_limit_exceeded');
    }
    await h.recorder.stop();
    assertReleased(h);
  }
});

test('byte ceiling is checked before allocation and again on the actual Blob', async () => {
  for (const samples of [8, 9]) {
    let constructions = 0;
    const h = harness({ options: { maxBytes: 60, BlobCtor: class extends Blob {
      constructor(...args) { super(...args); constructions++; }
    } } });
    await h.recorder.arm();
    h.finish(new Float32Array(samples));
    assert.equal(constructions, samples === 8 ? 1 : 0);
    assert.equal(h.blobs().length, samples === 8 ? 1 : 0);
    if (samples === 8) assert.equal(h.blobs()[0].sizeBytes, 60);
    else assert.equal(h.events.at(-1).code, 'size_limit_exceeded');
    await h.recorder.stop();
    assertReleased(h);
  }
  // PCM at 300s cannot reach 24MB: inject only Blob.size for this independent defense.
  for (const size of [24000000, 24000001]) {
    const h = harness({ options: { BlobCtor: class extends Blob { get size() { return size; } } } });
    await h.recorder.arm();
    h.finish(new Float32Array(16));
    assert.equal(h.blobs().length, size === 24000000 ? 1 : 0);
    if (size > 24000000) assert.equal(h.events.at(-1).code, 'size_limit_exceeded');
    await h.recorder.stop();
    assertReleased(h);
  }
});

test('pinned VAD buffer rejects over-limit frame before append or concatenation', async () => {
  for (const options of [{ maxDurationMs: 960 }, { maxBytes: 44 + 10 * 1536 * 2 }]) {
    const h = harness({ options });
    await h.recorder.arm();
    const raw = h.vads[0];
    for (let i = 0; i < 10; i++) await raw.feed(0.9, 0.5);
    assert.equal(raw.frameProcessor.audioBuffer.length, 10);
    await raw.feed(0.9, 0.5);
    assert.equal(h.events.at(-1).code, options.maxDurationMs ? 'duration_limit_exceeded' : 'size_limit_exceeded');
    assert.equal(h.blobs().length, 0);
    await h.recorder.stop();
    assertReleased(h);
  }
});

test('noise, misfire and end without confirmed start never emit a blob', async () => {
  const h = harness();
  await h.recorder.arm();
  const opts = h.vads[0].options;
  opts.onSpeechStart();
  opts.onVADMisfire();
  opts.onSpeechEnd(new Float32Array(16000));
  assert.deepEqual(h.events, []);
  await h.recorder.stop();
});

test('duplicate end ignored and successive utterances have independent duration and payload', async () => {
  const h = harness();
  await h.recorder.arm();
  h.finish(new Float32Array(16000).fill(0.5));
  h.vads[0].options.onSpeechEnd(new Float32Array(32000));
  h.advance(900000);
  h.finish(new Float32Array(8000).fill(-0.5));
  assert.deepEqual(h.blobs().map((e) => [e.durationMs, e.sizeBytes]), [[1000, 32044], [500, 16044]]);
  assert.equal(h.calls, 1);
  await h.recorder.stop();
});

test('pause discards partial speech; explicit resume uses a new stream and ignores stale callbacks', async () => {
  const h = harness();
  await h.recorder.arm();
  const old = h.vads[0];
  await old.feed(0.9, 0.5);
  await Promise.all([h.recorder.pause(), h.recorder.pause()]);
  assertReleased(h);
  assert.equal(h.blobs().length, 0);
  await Promise.all([h.recorder.resume(), h.recorder.resume()]);
  assert.equal(h.calls, 2);
  assert.equal(h.vads[1]._stream, h.streams[1]);
  old.options.onSpeechRealStart();
  old.options.onSpeechEnd(new Float32Array(100));
  assert.deepEqual(h.events, []);
  h.finish(new Float32Array(100));
  await Promise.all([h.recorder.stop(), h.recorder.stop()]);
  await h.recorder.arm();
  await h.recorder.resume();
  assert.equal(h.calls, 2);
  assertReleased(h);
});

test('permission and VAD failures never rearm and release every resource', async () => {
  for (const key of ['permissionError', 'newError', 'startError']) {
    const h = harness({ [key]: true });
    await h.recorder.arm();
    assert.equal(h.events.at(-1).type, 'error');
    await h.recorder.arm();
    await h.recorder.resume();
    assert.equal(h.calls, 1);
    await h.recorder.stop();
    assertReleased(h);
    assert.doesNotMatch(JSON.stringify(h.events), /private|synthetic/);
  }
});

test('controllable media must certainly pause before microphone acquisition', async () => {
  for (const failure of ['throw', 'active', 'none']) {
    const media = { paused: false, ended: false, pause() {
      if (failure === 'throw') throw new Error('private');
      if (failure === 'none') this.paused = true;
    } };
    const h = harness({ media: [media], options: { ttsMediaElement: media } });
    await h.recorder.arm();
    assert.equal(h.calls, failure === 'none' ? 1 : 0);
    if (failure !== 'none') assert.equal(h.events.at(-1).code, 'media_pause_failed');
    await h.recorder.stop();
    assertReleased(h);
  }
});

test('stop during media pause or permission prevents late VAD initialization', async () => {
  for (const atMedia of [true, false]) {
    const gate = deferred(), entered = deferred();
    const media = { paused: false, async pause() { entered.resolve(); await gate.promise; this.paused = true; } };
    const h = harness(atMedia ? { media: [media] } : { permissionGate: gate });
    const arming = h.recorder.arm();
    if (atMedia) await entered.promise;
    else while (!h.calls) await Promise.resolve();
    const stopping = h.recorder.stop();
    gate.resolve();
    await Promise.all([arming, stopping]);
    assert.equal(h.vads.length, 0);
    assert.equal(h.calls, atMedia ? 0 : 1);
    assertReleased(h);
  }
});

test('late VAD creation or start is destroyed before stop completes', async () => {
  for (const key of ['newGate', 'startGate']) {
    const gate = deferred();
    const h = harness({ [key]: gate });
    const arming = h.recorder.arm();
    while (!h.factoryEntered || (key === 'startGate' && !h.vads[0]?.starts)) await Promise.resolve();
    const stopping = h.recorder.stop();
    assert.equal(h.streams[0].track.readyState, 'ended');
    gate.resolve();
    await Promise.all([arming, stopping]);
    assertReleased(h);
  }
});

test('concurrent pause, resume and stop await shared cleanup without rearming', async () => {
  const gate = deferred();
  const h = harness({ pauseGate: gate });
  await h.recorder.arm();
  const pause = h.recorder.pause(), resume = h.recorder.resume(), stop = h.recorder.stop();
  let settled = false;
  stop.then(() => { settled = true; });
  await Promise.resolve();
  assert.equal(settled, false);
  assert.equal(h.calls, 1);
  gate.resolve();
  await Promise.all([pause, resume, stop]);
  assert.equal(h.calls, 1);
  assertReleased(h);
});

test('invalid audio and Blob creation failure emit closed errors without output', async () => {
  for (const audio of [null, [], new Float32Array(), new Float32Array([NaN]), new Float32Array([2])]) {
    const h = harness();
    await h.recorder.arm();
    h.finish(audio);
    assert.equal(h.events.at(-1).code, 'vad_audio_invalid');
    assert.equal(h.blobs().length, 0);
    await h.recorder.stop();
    assertReleased(h);
  }
  const h = harness({ options: { BlobCtor: class { constructor() { throw new Error('private'); } } } });
  await h.recorder.arm();
  h.finish(new Float32Array(16));
  assert.equal(h.events.at(-1).code, 'blob_creation_failed');
  await h.recorder.stop();
  assertReleased(h);
});

test('track failure and reentrant stop cannot produce ghost blobs', async () => {
  const h = harness();
  await h.recorder.arm();
  h.streams[0].track.dispatchEvent(new Event('ended'));
  assert.equal(h.events.at(-1).code, 'track_ended');
  await h.recorder.stop();
  assertReleased(h);
  const reentrant = harness({ onEvent(event, state) { if (event.type === 'speech-end') void state.recorder.stop(); } });
  await reentrant.recorder.arm();
  reentrant.finish(new Float32Array(16));
  assert.equal(reentrant.blobs().length, 0);
  await reentrant.recorder.stop();
  assertReleased(reentrant);
});

test('capture has no fetch, provider, Whisper, recorder or content persistence path', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../../../web/dialogue/dialogue_vad_recorder.js'), 'utf8');
  assert.doesNotMatch(source, /\bfetch\s*\(|XMLHttpRequest|MediaRecorder|Whisper|localStorage|sessionStorage|\/api\/|transcript/);
});
