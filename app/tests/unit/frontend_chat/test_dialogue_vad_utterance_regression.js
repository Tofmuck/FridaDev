'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { harness } = require('./helpers/dialogue_vad_test_helpers.js');

test('long silence and rejected noise before speech never enter the utterance WAV or consume its duration', async () => {
  const h = harness();
  await h.recorder.arm();
  const raw = h.vads[0];
  for (let i = 0; i < 12000; i++) {
    // 384 seconds, with isolated short misfires and identifiable old samples.
    await raw.feed(i % 300 === 0 ? 0.9 : 0, -0.75);
    h.advance(32);
  }
  assert.deepEqual(h.events, [], 'waiting must neither emit nor expire');
  assert.equal(raw.frameProcessor.audioBuffer.length, 25, 'pinned ring is bounded');
  for (let i = 0; i < 25; i++) await raw.feed(0, -0.25);
  for (let i = 0; i < 15; i++) await raw.feed(0.9, 0.5);
  for (let i = 0; i < 43; i++) await raw.feed(0, 0);
  assert.deepEqual(h.events.map((e) => e.type), ['speech-start', 'speech-end', 'blob']);
  const event = h.blobs()[0];
  assert.equal(event.durationMs, 83 * 32);
  assert.equal(event.sizeBytes, 44 + 83 * 512 * 2);
  assert.equal(event.mimeType, 'audio/wav');
  const bytes = new DataView(await event.blob.arrayBuffer());
  assert.equal(bytes.byteLength, 85036);
  assert.equal(bytes.getUint32(4, true), 85028);
  assert.equal(bytes.getUint16(20, true), 1, 'PCM');
  assert.equal(bytes.getUint16(22, true), 1, 'mono');
  assert.equal(bytes.getUint32(24, true), 16000);
  assert.equal(bytes.getUint32(28, true), 32000);
  assert.equal(bytes.getUint16(32, true), 2);
  assert.equal(bytes.getUint16(34, true), 16);
  assert.equal(bytes.getUint32(40, true), 83 * 512 * 2);
  for (let sample = 0; sample < 83 * 512; sample++) {
    const expected = sample < 25 * 512 ? -8192 : sample < 40 * 512 ? 16383 : 0;
    assert.equal(bytes.getInt16(44 + sample * 2, true), expected, `PCM sample ${sample}`);
  }
  assert.equal(bytes.getInt16(44, true), -8192, 'bounded preroll kept');
  assert.equal(bytes.getInt16(44 + 25 * 512 * 2, true), 16383, 'first speech frame kept');
  assert.equal(bytes.getInt16(bytes.byteLength - 2, true), 0, 'VAD ending silence kept');
  assert.equal(h.timers.size, 0, 'no arm-based deadline');
  await h.recorder.stop();
  assert.equal(raw.frameProcessor.audioBuffer.length, 0);
  assert.equal(h.streams[0].track.readyState, 'ended');
  assert.equal(raw.model.releases, 1);
});

test('V5 pinned segmentation uses probability 0.4 and millisecond-derived 25/43/12 frames', async () => {
  for (const speechFrames of [11, 12]) {
    const h = harness();
    await h.recorder.arm();
    const raw = h.vads[0], fp = raw.frameProcessor;
    assert.equal(raw.options.model, 'v5');
    assert.equal(raw.frameSamples, 512);
    assert.equal(fp.msPerFrame, 32);
    assert.deepEqual([fp.preSpeechPadFrames, fp.redemptionFrames, fp.minSpeechFrames], [25, 43, 12]);
    // Only model probabilities are controlled: large PCM is rejected, tiny PCM accepted.
    // This tests segmentation, not acoustic classification of these synthetic samples.
    for (let i = 0; i < 30; i++) await raw.feed(0.399, 0.75);
    assert.deepEqual(h.events, []);
    for (let i = 0; i < speechFrames; i++) await raw.feed(0.4, 0.0001);
    assert.deepEqual(h.events.map(e => e.type), speechFrames === 12 ? ['speech-start'] : []);
    for (let i = 0; i < 42; i++) await raw.feed(0.399, 0);
    assert.equal(h.blobs().length, 0, '42 frames cannot close redemption');
    await raw.feed(0.399, 0);
    if (speechFrames === 11) assert.deepEqual(h.events, [], 'sub-minimum misfire is discarded');
    else {
      assert.deepEqual(h.events.map(e => e.type), ['speech-start', 'speech-end', 'blob']);
      assert.equal(h.blobs()[0].durationMs, 80 * 32);
      assert.equal(h.blobs()[0].sizeBytes, 44 + 80 * 512 * 2);
    }
    await h.recorder.stop();
    assert.equal(h.streams[0].track.readyState, 'ended');
    assert.equal(fp.audioBuffer.length, 0);
  }
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
  for (let i = 0; i < 30000; i++) { await h.vads[0].feed(0); h.advance(32); }
  assert.deepEqual(h.events, []);
  assert.equal(h.timers.size, 0);
  assert.equal(h.vads[0].frameProcessor.audioBuffer.length, 25);
  await h.recorder.stop();
});
