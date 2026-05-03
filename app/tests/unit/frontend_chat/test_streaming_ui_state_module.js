'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  STREAMING_UI_STATE_PREPARING,
  STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT,
  STREAMING_UI_STATE_STREAMING,
  STREAMING_UI_STATE_DONE,
  STREAMING_UI_STATE_INTERRUPTED,
  STREAM_ERROR_KIND_INTERRUPTED,
  STREAM_ERROR_KIND_UPSTREAM,
  STREAM_ERROR_KIND_SERVER,
  STREAM_ERROR_KIND_NETWORK,
  ASSISTANT_TURN_META_KEY,
  ASSISTANT_TURN_STATUS_INTERRUPTED,
  STREAMING_UI_EVENT_REQUEST_STARTED,
  STREAMING_UI_EVENT_RESPONSE_OPENED,
  STREAMING_UI_EVENT_VISIBLE_CONTENT,
  STREAMING_UI_EVENT_TERMINAL_DONE,
  STREAMING_UI_EVENT_TERMINAL_ERROR,
  STREAMING_UI_EVENT_NETWORK_ERROR,
  buildInterruptedAssistantTurnMeta,
  getPersistedAssistantTurnErrorMeta,
  reduceStreamingUiState,
  getStreamingUiStateMeta,
  getObservableStreamErrorMeta,
  hasVisibleAssistantContent,
} = require('../../../web/chat_streaming.js');

test('reduceStreamingUiState covers the normal preparing-to-done lifecycle', () => {
  let state = null;

  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_REQUEST_STARTED);
  assert.equal(state, STREAMING_UI_STATE_PREPARING);
  assert.deepEqual(getStreamingUiStateMeta(state), {
    label: 'Préparation…',
    tone: 'pending',
    visible: true,
  });

  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_RESPONSE_OPENED);
  assert.equal(state, STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT);
  assert.deepEqual(getStreamingUiStateMeta(state), {
    label: 'Réponse en attente…',
    tone: 'pending',
    visible: true,
  });

  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_VISIBLE_CONTENT);
  assert.equal(state, STREAMING_UI_STATE_STREAMING);
  assert.deepEqual(getStreamingUiStateMeta(state), {
    label: 'Réponse en cours',
    tone: 'live',
    visible: true,
  });

  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_TERMINAL_DONE);
  assert.equal(state, STREAMING_UI_STATE_DONE);
  assert.deepEqual(getStreamingUiStateMeta(state), {
    label: '',
    tone: 'done',
    visible: false,
  });
});

test('reduceStreamingUiState keeps interrupted as the terminal state for terminal and network errors', () => {
  let state = reduceStreamingUiState(null, STREAMING_UI_EVENT_REQUEST_STARTED);
  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_RESPONSE_OPENED);
  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_TERMINAL_ERROR);

  assert.equal(state, STREAMING_UI_STATE_INTERRUPTED);
  assert.deepEqual(getStreamingUiStateMeta(state), {
    label: 'Interrompu',
    tone: 'error',
    visible: true,
  });

  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_NETWORK_ERROR);
  assert.equal(state, STREAMING_UI_STATE_INTERRUPTED);

  state = reduceStreamingUiState(state, STREAMING_UI_EVENT_TERMINAL_DONE);
  assert.equal(state, STREAMING_UI_STATE_INTERRUPTED);
});

test('getStreamingUiStateMeta can keep interrupted while exposing a more precise visible label', () => {
  assert.deepEqual(
    getStreamingUiStateMeta(STREAMING_UI_STATE_INTERRUPTED, {
      statusLabel: 'Connexion interrompue',
    }),
    {
      label: 'Connexion interrompue',
      tone: 'error',
      visible: true,
    },
  );
});

test('getObservableStreamErrorMeta distinguishes upstream, server, network and fallback interruptions', () => {
  assert.deepEqual(
    getObservableStreamErrorMeta({
      name: 'FridaStreamTerminalError',
      code: 'upstream_error',
      terminal: { event: 'error', error_code: 'upstream_error' },
    }),
    {
      kind: STREAM_ERROR_KIND_UPSTREAM,
      errorCode: 'upstream_error',
      statusLabel: 'Interrompu par le modèle',
      bubbleMessage: 'Réponse interrompue par le modèle.',
      terminal: { event: 'error', error_code: 'upstream_error' },
    },
  );

  assert.deepEqual(
    getObservableStreamErrorMeta({
      name: 'FridaStreamProtocolError',
      code: 'stream_finalize_error',
    }),
    {
      kind: STREAM_ERROR_KIND_SERVER,
      errorCode: 'stream_finalize_error',
      statusLabel: 'Interrompu côté serveur',
      bubbleMessage: 'Réponse interrompue côté serveur.',
      terminal: null,
    },
  );

  assert.deepEqual(
    getObservableStreamErrorMeta(new TypeError('Failed to fetch')),
    {
      kind: STREAM_ERROR_KIND_NETWORK,
      errorCode: null,
      statusLabel: 'Connexion interrompue',
      bubbleMessage: 'Connexion interrompue pendant la réponse.',
      terminal: null,
    },
  );

  assert.deepEqual(
    getObservableStreamErrorMeta(new Error(JSON.stringify({
      error: 'Conversation introuvable.',
    }))),
    {
      kind: STREAM_ERROR_KIND_INTERRUPTED,
      errorCode: null,
      statusLabel: 'Interrompu',
      bubbleMessage: 'Conversation introuvable.',
      terminal: null,
    },
  );
});

test('buildInterruptedAssistantTurnMeta and getPersistedAssistantTurnErrorMeta keep interrupted assistant markers explicit', () => {
  assert.deepEqual(
    buildInterruptedAssistantTurnMeta('upstream_error'),
    {
      [ASSISTANT_TURN_META_KEY]: {
        status: ASSISTANT_TURN_STATUS_INTERRUPTED,
        error_code: 'upstream_error',
      },
    },
  );

  assert.deepEqual(
    getPersistedAssistantTurnErrorMeta({
      role: 'assistant',
      content: '',
      meta: buildInterruptedAssistantTurnMeta('stream_finalize_error'),
    }),
    {
      kind: STREAM_ERROR_KIND_SERVER,
      errorCode: 'stream_finalize_error',
      statusLabel: 'Interrompu côté serveur',
      bubbleMessage: 'Réponse interrompue côté serveur.',
      terminal: null,
    },
  );

  assert.equal(
    getPersistedAssistantTurnErrorMeta({
      role: 'assistant',
      content: 'Bonjour',
      meta: { [ASSISTANT_TURN_META_KEY]: { status: 'complete' } },
    }),
    null,
  );
});

test('hasVisibleAssistantContent only flips the UI once non-whitespace content is visible', () => {
  assert.equal(hasVisibleAssistantContent(''), false);
  assert.equal(hasVisibleAssistantContent(' \n\t '), false);
  assert.equal(hasVisibleAssistantContent('Bonjour'), true);
  assert.equal(hasVisibleAssistantContent(' … '), true);
});
