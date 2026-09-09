'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { harness } = require('./helpers/dialogue_vad_test_helpers.js');

test('long silence and rejected noise before speech never enter the utterance WAV or consume its duration', async () => {
  const h = harness();
  await h.recorder.arm();
  const raw = h.vads[0];
  for (let i = 0; i < 4000; i++) {
    // 384 seconds, with isolated short misfires and identifiable old samples.
    await raw.feed(i % 100 === 0 ? 0.9 : 0, -0.75);
    h.advance(96);
  }
  assert.deepEqual(h.events, [], 'waiting must neither emit nor expire');
  assert.equal(raw.frameProcessor.audioBuffer.length, 8, 'pinned ring is bounded');
  for (let i = 0; i < 8; i++) await raw.feed(0, -0.25);
  for (let i = 0; i < 5; i++) await raw.feed(0.9, 0.5);
  for (let i = 0; i < 14; i++) await raw.feed(0, 0);
  assert.deepEqual(h.events.map((e) => e.type), ['speech-start', 'speech-end', 'blob']);
  const event = h.blobs()[0];
  assert.equal(event.durationMs, 27 * 96);
  assert.equal(event.sizeBytes, 44 + 27 * 1536 * 2);
  assert.equal(event.mimeType, 'audio/wav');
  const bytes = new DataView(await event.blob.arrayBuffer());
  assert.equal(bytes.getInt16(44, true), -8192, 'bounded preroll kept');
  assert.equal(bytes.getInt16(44 + 8 * 1536 * 2, true), 16383, 'first speech frame kept');
  assert.equal(bytes.getInt16(bytes.byteLength - 2, true), 0, 'VAD ending silence kept');
  assert.equal(h.timers.size, 0, 'no arm-based deadline');
  await h.recorder.stop();
  assert.equal(raw.frameProcessor.audioBuffer.length, 0);
  assert.equal(h.streams[0].track.readyState, 'ended');
  assert.equal(raw.model.releases, 1);
});

test('utterance duration depends only on samples, not the age of arm', async () => {
  for (const age of [0, 240000, 900000]) {
    const h = harness();
    await h.recorder.arm();
    h.advance(age);
    h.finish(new Float32Array(16000));
    assert.equal(h.blobs()[0]?.durationMs, 1000);
    await h.recorder.stop();
  }
});

test('silence alone is bounded and never arms an utterance expiration', async () => {
  const h = harness();
  await h.recorder.arm();
  for (let i = 0; i < 10000; i++) { await h.vads[0].feed(0); h.advance(96); }
  assert.deepEqual(h.events, []);
  assert.equal(h.timers.size, 0);
  assert.equal(h.vads[0].frameProcessor.audioBuffer.length, 8);
  await h.recorder.stop();
});
