'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const chatTheme = require('../../../web/chat_theme.js');

function createFixture(storedTheme = null, options = {}) {
  const signals = {
    narrow: false,
    coarse: false,
    displayStandalone: false,
    navigatorStandalone: false,
    maxTouchPoints: 0,
    screenWidth: 1440,
    screenHeight: 900,
    ...options,
  };
  const attributes = new Map();
  const listeners = new Map();
  const viewListeners = new Map();
  const button = {
    dataset: {},
    setAttribute: (name, value) => attributes.set(name, String(value)),
    getAttribute: (name) => attributes.get(name) || null,
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name) => listeners.delete(name),
  };
  const meta = {
    content: '#fbf8f3',
    setAttribute(name, value) {
      if (name === 'content') this.content = String(value);
    },
  };
  const values = new Map();
  const mediaListeners = new Map();
  if (storedTheme !== null) values.set(chatTheme.STORAGE_KEY, storedTheme);
  const storage = {
    getItem: (key) => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
  };
  const queryMatches = (query) => {
    if (query === chatTheme.MOBILE_DIALOGUE_QUERY) return signals.narrow;
    if (query === chatTheme.COARSE_POINTER_QUERY) return signals.coarse;
    if (query === chatTheme.STANDALONE_DISPLAY_QUERY) return signals.displayStandalone;
    return false;
  };
  const view = {
    navigator: {
      get standalone() { return signals.navigatorStandalone; },
      get maxTouchPoints() { return signals.maxTouchPoints; },
    },
    screen: {
      get width() { return signals.screenWidth; },
      get height() { return signals.screenHeight; },
    },
    matchMedia: (query) => ({
      get matches() { return queryMatches(query); },
      addEventListener: (name, callback) => mediaListeners.set(`${query}:${name}`, callback),
      removeEventListener: (name) => mediaListeners.delete(`${query}:${name}`),
    }),
    addEventListener: (name, callback) => viewListeners.set(name, callback),
    removeEventListener: (name) => viewListeners.delete(name),
  };
  const document = {
    documentElement: { dataset: {}, style: {} },
    defaultView: view,
    getElementById: (id) => id === 'btnTheme' ? button : null,
    querySelector: (selector) => selector === 'meta[name="theme-color"]' ? meta : null,
  };
  return { document, storage, button, meta, listeners, mediaListeners, viewListeners, values, signals };
}

test('initial theme accepts only the stored dark value', () => {
  const dark = createFixture('dark');
  assert.equal(chatTheme.applyInitialTheme(dark), 'dark');
  assert.equal(dark.document.documentElement.dataset.theme, 'dark');
  assert.equal(dark.meta.content, '#0d1117');

  const invalid = createFixture('sepia');
  assert.equal(chatTheme.applyInitialTheme(invalid), 'light');
  assert.equal(invalid.meta.content, '#fbf8f3');
});

test('mobile Dialogue vivant forces only the presentation theme', () => {
  const fixture = createFixture('light', { narrow: true });
  assert.equal(chatTheme.applyInitialTheme(fixture), 'light');
  assert.equal(fixture.document.documentElement.dataset.theme, 'light');
  assert.equal(fixture.document.documentElement.dataset.presentationTheme, 'mobile-dialogue');
  assert.equal(fixture.document.documentElement.style.colorScheme, 'dark');
  assert.equal(fixture.meta.content, chatTheme.MOBILE_DIALOGUE_COLOR);
  assert.equal(fixture.values.get(chatTheme.STORAGE_KEY), 'light');
});

test('an iPhone remains in the phone presentation when landscape is wider than the breakpoint', () => {
  const fixture = createFixture('light', {
    maxTouchPoints: 5,
    screenWidth: 896,
    screenHeight: 414,
  });

  assert.equal(chatTheme.isPhonePresentation(fixture.document), true);
  chatTheme.applyInitialTheme(fixture);
  assert.equal(fixture.document.documentElement.dataset.presentationContext, 'phone');
  assert.equal(fixture.document.documentElement.dataset.presentationTheme, 'mobile-dialogue');
});

test('a large touch screen does not become the phone presentation', () => {
  const fixture = createFixture('dark', {
    coarse: true,
    maxTouchPoints: 5,
    screenWidth: 1180,
    screenHeight: 820,
  });

  assert.equal(chatTheme.isPhonePresentation(fixture.document), false);
  chatTheme.applyInitialTheme(fixture);
  assert.equal(fixture.document.documentElement.dataset.presentationContext, undefined);
  assert.equal(fixture.document.documentElement.dataset.presentationTheme, undefined);
});

test('pageshow resynchronizes the phone presentation after an authentication return', () => {
  const fixture = createFixture('light', {
    screenWidth: 896,
    screenHeight: 414,
  });
  const controller = chatTheme.createThemeController(fixture);
  assert.equal(fixture.document.documentElement.dataset.presentationTheme, undefined);

  fixture.signals.maxTouchPoints = 5;
  assert.equal(fixture.viewListeners.has('pageshow'), true);
  fixture.viewListeners.get('pageshow')({ persisted: false });
  assert.equal(fixture.document.documentElement.dataset.presentationContext, 'phone');
  assert.equal(fixture.document.documentElement.dataset.presentationTheme, 'mobile-dialogue');

  controller.destroy();
  assert.equal(fixture.viewListeners.has('pageshow'), false);
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
