'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const agendaMode = require('../../../web/chat_agenda_mode.js');

test('agenda mode always sends an explicit backend toggle state', () => {
  assert.deepEqual(agendaMode.buildAgendaChatPayload(false), { agenda_enabled: false });
  assert.deepEqual(agendaMode.buildAgendaChatPayload(true), { agenda_enabled: true });
  assert.deepEqual(agendaMode.buildAgendaChatPayload('1'), { agenda_enabled: true });
  assert.deepEqual(agendaMode.buildAgendaChatPayload('off'), { agenda_enabled: false });
});

test('agenda toggle is rendered next to Biblio with the shared composer grammar', () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, '../../../web/index.html'), 'utf8');
  const biblioIndex = indexHtml.indexOf('id="btnBiblioMode"');
  const agendaIndex = indexHtml.indexOf('id="btnAgendaMode"');

  assert.ok(biblioIndex > 0, 'Biblio button should exist');
  assert.ok(agendaIndex > biblioIndex, 'Agenda button should sit after Biblio');
  assert.ok(indexHtml.includes('class="btn-agenda-mode"'));
  assert.ok(indexHtml.includes('aria-label="Activer Agenda"'));
  assert.ok(indexHtml.includes('<script src="chat_agenda_mode.js"></script>'));
});

test('agenda mode controller mirrors active state on the button', () => {
  const events = [];
  const button = createFakeButton();
  const storage = createFakeStorage();
  const controller = agendaMode.createAgendaModeController({
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
  assert.deepEqual(controller.getPayload(), { agenda_enabled: true });
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
