'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const { logFiltersSignature } = require('../../../web/log/log.js');

const BASE_FILTERS = Object.freeze({
  conversation_id: 'conv-a',
  turn_id: 'turn-a',
  stage: 'llm_call',
  status: 'ok',
  limit: 100,
  offset: 0,
});

test('log filter signature is stable and includes every visible filter', () => {
  const baseline = logFiltersSignature(BASE_FILTERS);
  assert.equal(logFiltersSignature({
    offset: 0,
    limit: 100,
    status: 'ok',
    stage: 'llm_call',
    turn_id: 'turn-a',
    conversation_id: 'conv-a',
  }), baseline);

  for (const [field, value] of Object.entries({
    conversation_id: 'conv-b',
    turn_id: 'turn-b',
    stage: 'turn_start',
    status: 'error',
    limit: 50,
    offset: 100,
  })) {
    assert.notEqual(
      logFiltersSignature({ ...BASE_FILTERS, [field]: value }),
      baseline,
      `${field} must participate in the visible-filter identity`,
    );
  }
});
