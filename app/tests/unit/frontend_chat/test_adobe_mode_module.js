'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const adobeMode = require('../../../web/chat_adobe_mode.js');

test('adobe mode accepts only explicit Photoshop or Illustrator products', () => {
  assert.equal(adobeMode.normalizeAdobeProduct('photoshop'), 'photoshop');
  assert.equal(adobeMode.normalizeAdobeProduct('Illustrator'), 'illustrator');
  assert.equal(adobeMode.normalizeAdobeProduct('auto'), '');
  assert.equal(adobeMode.normalizeAdobeProduct(''), '');
});

test('adobe mode builds the backend payload only when a product is selected', () => {
  assert.deepEqual(adobeMode.buildAdobeChatPayload(''), {});
  assert.deepEqual(adobeMode.buildAdobeChatPayload('auto'), {});
  assert.deepEqual(adobeMode.buildAdobeChatPayload('photoshop'), {
    specialization_profile: 'adobe',
    adobe_product: 'photoshop',
  });
  assert.deepEqual(adobeMode.buildAdobeChatPayload('illustrator'), {
    specialization_profile: 'adobe',
    adobe_product: 'illustrator',
  });
});

test('adobe mode exposes no auto product', () => {
  assert.deepEqual(
    adobeMode.ADOBE_PRODUCTS.map((product) => product.value),
    ['photoshop', 'illustrator'],
  );
});
