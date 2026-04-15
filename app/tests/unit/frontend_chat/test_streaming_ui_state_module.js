'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  STREAMING_UI_STATE_PREPARING,
  STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT,
  STREAMING_UI_STATE_STREAMING,
  STREAMING_UI_STATE_DONE,
  STREAMING_UI_STATE_INTERRUPTED,
  STREAMING_UI_EVENT_REQUEST_STARTED,
  STREAMING_UI_EVENT_RESPONSE_OPENED,
  STREAMING_UI_EVENT_VISIBLE_CONTENT,
  STREAMING_UI_EVENT_TERMINAL_DONE,
  STREAMING_UI_EVENT_TERMINAL_ERROR,
  STREAMING_UI_EVENT_NETWORK_ERROR,
  reduceStreamingUiState,
  getStreamingUiStateMeta,
  hasVisibleAssistantContent,
} = require('../../../web/app.js');

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

test('hasVisibleAssistantContent only flips the UI once non-whitespace content is visible', () => {
  assert.equal(hasVisibleAssistantContent(''), false);
  assert.equal(hasVisibleAssistantContent(' \n\t '), false);
  assert.equal(hasVisibleAssistantContent('Bonjour'), true);
  assert.equal(hasVisibleAssistantContent(' … '), true);
});
