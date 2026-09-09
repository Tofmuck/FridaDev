'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const modulePath = path.resolve(__dirname, '../../../web/dialogue/dialogue_audio_client.js');
function client(fetchFn) {
  assert.ok(fs.existsSync(modulePath), 'D4 STT client must exist');
  return require(modulePath).createDialogueAudioClient({ fetchFn });
}
const wav = () => new Blob(['synthetic WAV'], { type: 'audio/wav' });
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json; charset=utf-8' },
});

test('D4 valid WAV sends exactly one multipart audio file, preserves text and empty success', async () => {
  for (const text of ['Texte synthétique', '', '  ']) {
    let calls = 0;
    const blob = wav();
    const abort = new AbortController();
    const api = client(async (url, options) => {
      calls++;
      assert.equal(url, '/api/chat/dialogue/transcribe');
      assert.equal(options.method, 'POST');
      assert.equal(options.signal, abort.signal);
      assert.equal(options.headers, undefined, 'browser owns multipart boundary');
      assert.ok(options.body instanceof FormData);
      assert.deepEqual([...options.body.keys()], ['audio']);
      const file = options.body.get('audio');
      assert.match(file.name, /\.wav$/);
      assert.equal(file.type, 'audio/wav');
      assert.equal(file.size, blob.size);
      assert.deepEqual(await file.arrayBuffer(), await blob.arrayBuffer());
      return json({ ok: true, text });
    });
    assert.equal(await api.transcribe(blob, { signal: abort.signal }), text);
    assert.equal(calls, 1);
  }
});

test('D4 invalid blob fails before fetch, inclusive 24000000 byte boundary', async () => {
  let calls = 0;
  const api = client(async () => { calls++; return json({ ok: true, text: '' }); });
  for (const blob of [undefined, null, {}, { type: 'audio/wav', size: 1 },
    new Blob([], { type: 'audio/wav' }), new Blob(['x'], { type: 'audio/webm' }),
    new Blob(['x'], { type: 'audio/wav; codecs=pcm' }),
    new Blob([new Uint8Array(24_000_001)], { type: 'audio/wav' })]) {
    await assert.rejects(api.transcribe(blob), { message: 'dialogue_stt_invalid_audio' });
  }
  assert.equal(calls, 0);
  await api.transcribe(new Blob([new Uint8Array(24_000_000)], { type: 'audio/wav' }));
  assert.equal(calls, 1);
});

for (const status of [400, 401, 403, 422, 429, 500, 502, 503]) {
  test(`D4 HTTP ${status} exposes no raw error and never retries`, async () => {
    let calls = 0;
    const api = client(async () => { calls++; return json({ error: 'RAW_PRIVATE_SENTINEL' }, status); });
    await assert.rejects(api.transcribe(wav()), { message: 'dialogue_stt_unavailable' });
    assert.equal(calls, 1);
  });
}
for (const response of [
  () => new Response('RAW_PRIVATE_SENTINEL', { headers: { 'Content-Type': 'application/json' } }),
  () => new Response('{"ok":true,"text":"RAW_PRIVATE_SENTINEL"}', { headers: { 'Content-Type': 'text/plain' } }),
  ...[null, [], {}, { ok: false, text: 'RAW_PRIVATE_SENTINEL' }, { ok: 1, text: 'x' },
    { ok: true }, { ok: true, text: 3 }, { ok: true, text: null }].map(data => () => json(data)),
]) {
  test('D4 malformed response fails closed without raw content or retry', async () => {
    let calls = 0;
    const api = client(async () => { calls++; return response(); });
    await assert.rejects(api.transcribe(wav()), { message: 'dialogue_stt_unavailable' });
    assert.equal(calls, 1);
  });
}
test('D4 transport and abort are sanitized; pre-aborted operation never fetches', async () => {
  for (const error of [new Error('RAW_PRIVATE_SENTINEL'), new DOMException('RAW_PRIVATE_SENTINEL', 'AbortError')]) {
    let calls = 0;
    const api = client(async () => { calls++; throw error; });
    await assert.rejects(api.transcribe(wav()), { message: 'dialogue_stt_unavailable' });
    assert.equal(calls, 1);
  }
  let calls = 0;
  const abort = new AbortController();
  abort.abort();
  await assert.rejects(client(async () => { calls++; }).transcribe(wav(), { signal: abort.signal }),
    { message: 'dialogue_stt_unavailable' });
  assert.equal(calls, 0);
});
