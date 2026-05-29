'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const biblioMode = require('../../../web/chat_biblio_mode.js');

test('biblio mode always sends an explicit backend toggle state', () => {
  assert.deepEqual(biblioMode.buildBiblioChatPayload(false), { biblio_enabled: false });
  assert.deepEqual(biblioMode.buildBiblioChatPayload(true), { biblio_enabled: true });
  assert.deepEqual(biblioMode.buildBiblioChatPayload('1'), { biblio_enabled: true });
  assert.deepEqual(biblioMode.buildBiblioChatPayload('off'), { biblio_enabled: false });
});

test('biblio toggle is rendered next to Adobe with the shared composer grammar', () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, '../../../web/index.html'), 'utf8');
  const adobeIndex = indexHtml.indexOf('id="btnAdobeMode"');
  const biblioIndex = indexHtml.indexOf('id="btnBiblioMode"');

  assert.ok(adobeIndex > 0, 'Adobe button should exist');
  assert.ok(biblioIndex > adobeIndex, 'Biblio button should sit after Adobe');
  assert.ok(indexHtml.includes('class="btn-biblio-mode"'));
  assert.ok(indexHtml.includes('aria-label="Activer Biblio"'));
  assert.ok(indexHtml.includes('<script src="chat_biblio_mode.js"></script>'));
});

test('biblio mode controller mirrors active state on the button', () => {
  const events = [];
  const button = createFakeButton();
  const storage = createFakeStorage();
  const controller = biblioMode.createBiblioModeController({
    buttonEl: button,
    storage,
    onActiveChange: (active) => events.push(active),
  });

  assert.equal(controller.isActive(), false);
  assert.equal(button.getAttribute('aria-pressed'), 'false');

  button.dispatch('click');

  assert.equal(controller.isActive(), true);
  assert.equal(button.getAttribute('aria-pressed'), 'true');
  assert.equal(button.classList.has('active'), true);
  assert.deepEqual(controller.getPayload(), { biblio_enabled: true });
  assert.deepEqual(events, [true]);
});

function createFakeStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, String(value)),
  };
}

function createFakeButton() {
  const attrs = new Map();
  const listeners = new Map();
  const classes = new Set();
  return {
    classList: {
      toggle(name, active) {
        if (active) classes.add(name);
        else classes.delete(name);
      },
      has(name) {
        return classes.has(name);
      },
    },
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    getAttribute(name) {
      return attrs.get(name);
    },
    addEventListener(name, handler) {
      listeners.set(name, handler);
    },
    dispatch(name) {
      const handler = listeners.get(name);
      if (handler) handler({});
    },
  };
}
