'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const imageGeneration = require('../../../web/chat_image_generation.js');

test('image generation module exposes the four V0 generators', () => {
  assert.deepEqual(
    Object.keys(imageGeneration.IMAGE_GENERATORS),
    [
      'image_generator_openai',
      'image_generator_nano_banana',
      'image_generator_recraft',
      'image_generator_flux',
    ],
  );
  assert.equal(
    imageGeneration.IMAGE_GENERATORS.image_generator_nano_banana.openrouter_model_id,
    'google/gemini-2.5-flash-image',
  );
});

test('Nano Banana V0 keeps 4K out of the frontend table', () => {
  const nano = imageGeneration.IMAGE_GENERATORS.image_generator_nano_banana;

  assert.deepEqual(nano.supported_image_sizes, ['1K', '2K']);
  assert.equal(nano.supported_image_sizes.includes('4K'), false);
});

test('normalizeSelection falls back to supported ratios and sizes per model', () => {
  assert.deepEqual(
    imageGeneration.normalizeSelection({
      generatorKey: 'image_generator_recraft',
      aspectRatio: '21:9',
      imageSize: '4K',
    }),
    {
      generator_key: 'image_generator_recraft',
      aspect_ratio: '1:1',
      image_size: '1K',
    },
  );
});

test('buildDownloadFilename derives a stable extension from mime type', () => {
  assert.equal(
    imageGeneration.buildDownloadFilename({
      mimeType: 'image/webp',
      date: new Date('2026-05-19T14:25:36Z'),
    }),
    'fridadev-image-20260519-142536.webp',
  );
});

test('compactResultMeta remains content-free and includes observed cost only', () => {
  const meta = imageGeneration.compactResultMeta({
    display_name: 'Nano Banana',
    aspect_ratio: '1:1',
    image_size: '1K',
    provider_model: 'google/gemini-2.5-flash-image',
    usage: { cost: 0.01 },
    prompt: 'SHOULD NOT APPEAR',
  });

  assert.equal(meta.includes('SHOULD NOT APPEAR'), false);
  assert.equal(meta, 'Nano Banana · 1:1 · 1K · coût observé 0.01');
});

test('pricing labels avoid pretending unknown image pricing is free', () => {
  for (const key of ['image_generator_recraft', 'image_generator_flux']) {
    const label = imageGeneration.IMAGE_GENERATORS[key].pricing_label;
    assert.match(label, /prix image non exposé/);
    assert.equal(/gratuit|free/i.test(label), false);
  }
});
