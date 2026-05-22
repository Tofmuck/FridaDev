'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const reasoningControl = require('../../../web/main_reasoning_control.js');

test('main reasoning control exposes GPT-5.1 levels only', () => {
  assert.deepEqual(
    reasoningControl.MAIN_REASONING_LEVELS.map((level) => level.value),
    ['none', 'low', 'medium', 'high'],
  );
  assert.equal(reasoningControl.normalizeReasoningLevel('xhigh'), 'high');
  assert.equal(reasoningControl.normalizeReasoningLevel('minimal'), 'high');
});

test('main reasoning control reads runtime settings and builds a global patch', () => {
  assert.equal(
    reasoningControl.readReasoningLevelFromSettings({
      payload: {
        reasoning_effort: { value: 'medium' },
      },
    }),
    'medium',
  );
  assert.deepEqual(
    reasoningControl.buildReasoningPatchPayload('low'),
    {
      reasoning_effort: {
        value: 'low',
      },
    },
  );
});

test('main reasoning control does not expose reasoning details lane', () => {
  const source = require('node:fs').readFileSync(
    require('node:path').resolve(__dirname, '../../../web/main_reasoning_control.js'),
    'utf8',
  );
  assert.equal(source.includes("updated_by: 'chat_reasoning_control'"), true);
  assert.equal(source.includes('payload: buildReasoningPatchPayload(normalized)'), true);
  assert.equal(source.includes('reasoning_details'), false);
  assert.equal(source.includes('include_reasoning'), false);
});
