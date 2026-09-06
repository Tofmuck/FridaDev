'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');

function makeElement(tagName = 'div') {
  const element = {
    tagName: String(tagName).toUpperCase(),
    children: [],
    className: '',
    dataset: {},
    textContent: '',
    appendChild(child) {
      element.children.push(child);
      return child;
    },
  };
  let html = '';
  Object.defineProperty(element, 'innerHTML', {
    get() { return html; },
    set(value) {
      html = String(value || '');
      if (!html) element.children = [];
    },
  });
  return element;
}

function walk(root) {
  const nodes = [];
  const visit = (node) => {
    nodes.push(node);
    (node.children || []).forEach(visit);
  };
  visit(root);
  return nodes;
}

function renderedText(root) {
  return walk(root).map((node) => node.textContent || '').filter(Boolean).join('\n');
}

function loadRenderer() {
  const modulePath = path.resolve(__dirname, '../../../web/hermeneutic_admin/render.js');
  global.document = {
    createElement: makeElement,
    createDocumentFragment: () => makeElement('fragment'),
  };
  global.window = {
    FridaAdminUiCommon: {
      renderReadonlyInfoEntries(target, entries) {
        entries.forEach(([key, item]) => {
          const row = makeElement('div');
          row.textContent = `${key}=${item.value}`;
          target.appendChild(row);
        });
      },
    },
    FridaValidationProjection: {},
  };
  delete require.cache[require.resolve(modulePath)];
  require(modulePath);
  return global.window.FridaHermeneuticAdminRender;
}

test('hermeneutic overview renders three scopes without a global current window', () => {
  const renderer = loadRenderer();
  const cards = makeElement();
  const runtimeMetrics = makeElement();
  renderer.renderOverview(cards, runtimeMetrics, {
    mode: 'enforced_all',
    mode_observation: {},
    alerts: [],
    measurement_scopes: {
      durable_window: {
        scope_kind: 'durable_window',
        window_days: 7,
        counters: { identity_accept_count: 4 },
        rates: { fallback_rate: 0.2 },
      },
      process_runtime: {
        scope_kind: 'process_runtime',
        started_at: null,
        counters: { parse_error_count: 1 },
        rates: { parse_error_rate: 0.1, fallback_rate: 0.05 },
        metrics: { arbiter_call_count: 20 },
      },
      current_log_sample: {
        scope_kind: 'current_log_file_sample',
        log_limit: 5000,
        latency_ms: { retrieve: { p50_ms: 20, p95_ms: 29 } },
      },
    },
  });

  const cardsText = renderedText(cards);
  const runtimeText = renderedText(runtimeMetrics);
  assert.match(cardsText, /Mesures durables/);
  assert.match(cardsText, /7 derniers jours/);
  assert.match(cardsText, /Processus courant/);
  assert.match(cardsText, /debut inconnu/);
  assert.match(cardsText, /Echantillon du fichier de log courant/);
  assert.match(cardsText, /au plus 5000 entrees/);
  assert.doesNotMatch(cardsText, /fenetre courante/i);
  assert.match(runtimeText, /arbiter_call_count=20/);
});
