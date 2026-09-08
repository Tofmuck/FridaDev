'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const chatTheme = require('../../../web/chat_theme.js');

function createFixture(storedTheme = null) {
  const attributes = new Map();
  const listeners = new Map();
  const button = {
    dataset: {},
    setAttribute: (name, value) => attributes.set(name, String(value)),
    getAttribute: (name) => attributes.get(name) || null,
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name) => listeners.delete(name),
  };
  const meta = {
    content: '#f8f6f3',
    setAttribute(name, value) {
      if (name === 'content') this.content = String(value);
    },
  };
  const values = new Map();
  if (storedTheme !== null) values.set(chatTheme.STORAGE_KEY, storedTheme);
  const storage = {
    getItem: (key) => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
  };
  const document = {
    documentElement: { dataset: {}, style: {} },
    getElementById: (id) => id === 'btnTheme' ? button : null,
    querySelector: (selector) => selector === 'meta[name="theme-color"]' ? meta : null,
  };
  return { document, storage, button, meta, listeners, values };
}

test('initial theme accepts only the stored dark value', () => {
  const dark = createFixture('dark');
  assert.equal(chatTheme.applyInitialTheme(dark), 'dark');
  assert.equal(dark.document.documentElement.dataset.theme, 'dark');
  assert.equal(dark.meta.content, '#0b1018');

  const invalid = createFixture('sepia');
  assert.equal(chatTheme.applyInitialTheme(invalid), 'light');
  assert.equal(invalid.meta.content, '#f8f6f3');
});

test('theme controller toggles, persists and keeps accessible labels exact', () => {
  const fixture = createFixture('light');
  chatTheme.applyInitialTheme(fixture);
  const controller = chatTheme.createThemeController(fixture);

  fixture.listeners.get('click')();
  assert.equal(controller.getTheme(), 'dark');
  assert.equal(fixture.values.get(chatTheme.STORAGE_KEY), 'dark');
  assert.equal(fixture.button.getAttribute('aria-label'), 'Passer au mode clair');
  assert.equal(fixture.button.getAttribute('aria-pressed'), 'true');

  fixture.listeners.get('click')();
  assert.equal(controller.getTheme(), 'light');
  assert.equal(fixture.values.get(chatTheme.STORAGE_KEY), 'light');
  assert.equal(fixture.button.getAttribute('aria-label'), 'Passer au mode sombre');
  assert.equal(fixture.button.getAttribute('aria-pressed'), 'false');

  controller.destroy();
  assert.equal(fixture.listeners.has('click'), false);
});
