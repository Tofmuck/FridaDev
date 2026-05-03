'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  STREAM_CONTROL_PREFIX,
  createStreamControlParser,
  createStreamTerminalError,
  getObservableStreamErrorMeta,
} = require('../../../web/chat_streaming.js');

test('createStreamControlParser keeps visible prose clean and returns done terminal across chunk boundaries', () => {
  let visibleText = '';
  const parser = createStreamControlParser({
    onContent(chunk) {
      visibleText += chunk;
    },
  });

  parser.push('Bon');
  parser.push('jour');
  parser.push(`${STREAM_CONTROL_PREFIX}{"kind":"frida-stream-control","event":"done","updated_at":"2026-04-15T16:55:00`);
  parser.push('Z"}\n');

  const terminal = parser.finish();
  assert.equal(visibleText, 'Bonjour');
  assert.deepEqual(terminal, { event: 'done', updated_at: '2026-04-15T16:55:00Z' });
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
  parser.push('error","updated_at":"2026-04-15T16:56:00Z"}\n');

  const terminal = parser.finish();
  assert.equal(visibleText, 'Segment 1. Segment 2.');
  assert.deepEqual(terminal, {
    event: 'error',
    error_code: 'upstream_error',
    updated_at: '2026-04-15T16:56:00Z',
  });
  assert.equal(visibleText.includes('upstream_error'), false);
  assert.equal(visibleText.includes(STREAM_CONTROL_PREFIX), false);

  const err = createStreamTerminalError(terminal);
  assert.equal(err.name, 'FridaStreamTerminalError');
  assert.equal(err.observableKind, 'upstream_error');
  assert.match(err.message, /Réponse interrompue par le modèle/);
  assert.equal(err.terminal.updated_at, '2026-04-15T16:56:00Z');
});

test('createStreamControlParser surfaces missing terminal as a server-side stream interruption', () => {
  let visibleText = '';
  const parser = createStreamControlParser({
    onContent(chunk) {
      visibleText += chunk;
    },
  });

  parser.push('Segment partiel.');

  let err = null;
  try {
    parser.finish();
  } catch (caught) {
    err = caught;
  }
  assert.ok(err);
  assert.equal(visibleText, 'Segment partiel.');
  assert.equal(err.name, 'FridaStreamProtocolError');
  assert.equal(err.observableKind, 'server_error');
  assert.deepEqual(getObservableStreamErrorMeta(err), {
    kind: 'server_error',
    errorCode: 'missing_stream_terminal',
    statusLabel: 'Interrompu côté serveur',
    bubbleMessage: 'Réponse interrompue côté serveur.',
    terminal: null,
  });
});
