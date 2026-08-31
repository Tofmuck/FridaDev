'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const modulePath = path.resolve(__dirname, '../../../web/validation_projection.js');
global.window = {};
delete require.cache[require.resolve(modulePath)];
require(modulePath);
const projection = global.window.FridaValidationProjection;

test('validation request projection renders the effective Gemini medium request only from authoritative metadata', () => {
  const request = projection.requestFromEventPayload('validation_prompt_prepared', {
    validation_request_policy_version: 'validation_request_gemini_3_7_flash_medium_v1',
    validation_transport: 'standard',
    validation_attempt_decision_source: 'primary',
    validation_reasoning_effort_requested: 'medium',
    validation_reasoning_effort_effective: 'medium',
    validation_reasoning_sent: true,
    validation_reasoning_excluded: true,
    validation_max_tokens_effective: 500,
    validation_temperature_sent: false,
    validation_top_p_sent: false,
    validation_provider_routing_sent: true,
    validation_provider_fallbacks_allowed: false,
    validation_provider_require_parameters: true,
    validation_requested_model: 'google/gemini-3.7-flash',
    observed_model: 'google/gemini-3.7-flash',
    observed_provider: 'Google AI Studio',
  });

  assert.equal(request.authoritative, true);
  assert.equal(request.requestedModel, 'google/gemini-3.7-flash');
  assert.equal(request.observedProvider, 'Google AI Studio');
  assert.equal(request.reasoningEffortEffective, 'medium');
  assert.equal(request.maxTokensEffective, 500);
  assert.equal(request.temperatureSent, false);
  assert.equal(request.topPSent, false);
  assert.equal(request.providerRoutingSent, true);
});

test('validation request projection never reinterprets historical or incoherent metadata as Gemini medium', () => {
  const historical = projection.requestFromReadModel({ request: {
    authoritative: false,
    status: 'unknown',
    reason_code: 'historical_request_policy_unobserved',
  } });
  assert.equal(historical.authoritative, false);
  assert.equal(historical.status, 'unknown');

  const mutant = projection.requestFromEventPayload('validation_prompt_prepared', {
    validation_request_policy_version: 'validation_request_gemini_3_7_flash_medium_v1',
    validation_transport: 'standard',
    validation_attempt_decision_source: 'primary',
    validation_reasoning_effort_requested: 'medium',
    validation_reasoning_effort_effective: 'high',
    validation_reasoning_sent: true,
    validation_reasoning_excluded: true,
    validation_max_tokens_effective: 500,
    validation_temperature_sent: false,
    validation_top_p_sent: false,
    validation_provider_fallbacks_allowed: false,
    validation_provider_require_parameters: true,
    validation_requested_model: 'google/gemini-3.7-flash',
  });
  assert.equal(mutant.authoritative, false);
  assert.equal(mutant.status, 'unknown');

  const legacy = projection.requestFromEventPayload('validation_prompt_prepared', {
    validation_request_policy_version: 'validation_request_gemini_3_1_flash_lite_v1',
    validation_transport: 'standard',
    validation_attempt_decision_source: 'primary',
    validation_reasoning_effort_requested: 'none',
    validation_reasoning_effort_effective: 'none',
    validation_reasoning_sent: false,
    validation_reasoning_excluded: false,
    validation_max_tokens_effective: 140,
    validation_temperature_sent: true,
    validation_top_p_sent: true,
    validation_provider_routing_sent: false,
    validation_requested_model: 'google/gemini-3.1-flash-lite',
  });
  assert.equal(legacy.authoritative, true);
  assert.equal(legacy.policyVersion, 'validation_request_gemini_3_1_flash_lite_v1');
  assert.equal(legacy.providerRoutingSent, false);
  assert.equal(legacy.providerFallbacksAllowed, null);
});

test('dialogic effects preserve epistemic certainty while exposing a distinct transition directive', () => {
  const stable = projection.dialogicEffectsFromEventPayload('primary_node', {
    epistemic_effect: 'certain',
    epistemic_source: 'epistemic_inputs',
    epistemic_reason_code: 'sufficient_independent_support',
    enunciation_effect: 'none',
    enunciation_source: 'stimmung',
    enunciation_reason_code: 'stimmung_stable',
  });
  const transition = projection.dialogicEffectsFromReadModel({
    authoritative: true,
    status: 'success',
    epistemic_effect: 'certain',
    epistemic_source: 'epistemic_inputs',
    epistemic_reason_code: 'sufficient_independent_support',
    enunciation_effect: 'delicate_expression',
    enunciation_source: 'stimmung',
    enunciation_reason_code: 'affective_transition',
  });

  assert.equal(stable.authoritative, true);
  assert.equal(stable.epistemicEffect, 'certain');
  assert.equal(stable.enunciationEffect, 'none');
  assert.equal(transition.authoritative, true);
  assert.equal(transition.epistemicEffect, 'certain');
  assert.equal(transition.enunciationEffect, 'delicate_expression');
});

test('dialogic effects distinguish absent, legacy unknown, and fail-open states', () => {
  const absent = projection.dialogicEffectsFromEventPayload('validation_agent', {
    epistemic_effect: 'probable',
    epistemic_source: 'epistemic_inputs',
    epistemic_reason_code: 'limited_independent_support',
    enunciation_effect: 'none',
    enunciation_source: 'not_applicable',
    enunciation_reason_code: 'stimmung_absent',
  });
  const legacy = projection.dialogicEffectsFromEventPayload('validation_agent', {});
  const failOpen = projection.dialogicEffectsFromEventPayload('primary_node', {
    epistemic_effect: 'unknown',
    epistemic_source: 'fail_open',
    epistemic_reason_code: 'runtime_error',
    enunciation_effect: 'unknown',
    enunciation_source: 'fail_open',
    enunciation_reason_code: 'runtime_error',
  });

  assert.equal(absent.status, 'success');
  assert.equal(absent.enunciationSource, 'not_applicable');
  assert.equal(legacy.authoritative, false);
  assert.equal(legacy.status, 'unknown');
  assert.equal(failOpen.authoritative, true);
  assert.equal(failOpen.status, 'fail_open');
  assert.equal(failOpen.reasonCode, 'runtime_error');
});

test('dialogic effects reject causal mutations and cannot fabricate factual caution', () => {
  const stimmungAsEpistemicSource = projection.dialogicEffectsFromEventPayload('primary_node', {
    epistemic_effect: 'probable',
    epistemic_source: 'stimmung',
    epistemic_reason_code: 'affective_transition',
    enunciation_effect: 'delicate_expression',
    enunciation_source: 'stimmung',
    enunciation_reason_code: 'affective_transition',
  });
  const confusedReasons = projection.dialogicEffectsFromEventPayload('validation_agent', {
    epistemic_effect: 'certain',
    epistemic_source: 'epistemic_inputs',
    epistemic_reason_code: 'affective_transition',
    enunciation_effect: 'delicate_expression',
    enunciation_source: 'epistemic_inputs',
    enunciation_reason_code: 'sufficient_independent_support',
  });
  const inconsistentCertainty = projection.dialogicEffectsFromEventPayload('primary_node', {
    epistemic_effect: 'certain',
    epistemic_source: 'epistemic_inputs',
    epistemic_reason_code: 'limited_independent_support',
    enunciation_effect: 'none',
    enunciation_source: 'stimmung',
    enunciation_reason_code: 'stimmung_stable',
  });
  const fabricatedSuccess = projection.dialogicEffectsFromReadModel({
    authoritative: true,
    status: 'success',
    epistemic_effect: 'unknown',
    epistemic_source: 'fail_open',
    epistemic_reason_code: 'runtime_error',
    enunciation_effect: 'unknown',
    enunciation_source: 'fail_open',
    enunciation_reason_code: 'runtime_error',
  });

  for (const mutant of [
    stimmungAsEpistemicSource, confusedReasons, inconsistentCertainty, fabricatedSuccess,
  ]) {
    assert.equal(mutant.authoritative, false);
    assert.equal(mutant.status, 'unknown');
    assert.equal(mutant.epistemicEffect, 'unknown');
  }
});
