'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  STREAM_CONTROL_PREFIX,
  createStreamControlParser,
  createStreamTerminalError,
} = require('../../../web/app.js');

test('createStreamControlParser keeps visible prose clean and returns done terminal across chunk boundaries', () => {
  let visibleText = '';
  const parser = createStreamControlParser({
    onContent(chunk) {
      visibleText += chunk;
    },
  });

  parser.push('Bon');
  parser.push('jour');
  parser.push(`${STREAM_CONTROL_PREFIX}{"kind":"frida-stream-control","event":"do`);
  parser.push('ne"}\n');

  const terminal = parser.finish();
  assert.equal(visibleText, 'Bonjour');
  assert.deepEqual(terminal, { event: 'done' });
  assert.equal(visibleText.includes('frida-stream-control'), false);
  assert.equal(visibleText.includes(STREAM_CONTROL_PREFIX), false);
});

test('createStreamControlParser keeps error terminal out of visible prose and preserves the error payload', () => {
  let visibleText = '';
  const parser = createStreamControlParser({
    onContent(chunk) {
      visibleText += chunk;
    },
  });

  parser.push('Segment 1. ');
  parser.push('Segment 2.');
  parser.push(`${STREAM_CONTROL_PREFIX}{"kind":"frida-stream-control","event":"error","error_code":"upstream_`);
  parser.push('error"}\n');

  const terminal = parser.finish();
  assert.equal(visibleText, 'Segment 1. Segment 2.');
  assert.deepEqual(terminal, { event: 'error', error_code: 'upstream_error' });
  assert.equal(visibleText.includes('upstream_error'), false);
  assert.equal(visibleText.includes(STREAM_CONTROL_PREFIX), false);

  const err = createStreamTerminalError(terminal);
  assert.equal(err.name, 'FridaStreamTerminalError');
  assert.match(err.message, /Réponse interrompue/);
});
