'use strict';

const MAIN_REASONING_LEVELS = Object.freeze([
  Object.freeze({ value: 'none', label: 'aucun' }),
  Object.freeze({ value: 'low', label: 'faible' }),
  Object.freeze({ value: 'medium', label: 'moyen' }),
  Object.freeze({ value: 'high', label: 'élevé' }),
]);

const DEFAULT_MAIN_REASONING_LEVEL = 'high';
const MAIN_REASONING_ENDPOINT = '/api/admin/settings/main-model';

function normalizeReasoningLevel(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return MAIN_REASONING_LEVELS.some((level) => level.value === normalized)
    ? normalized
    : DEFAULT_MAIN_REASONING_LEVEL;
}

function reasoningLabel(value) {
  const normalized = normalizeReasoningLevel(value);
  const level = MAIN_REASONING_LEVELS.find((candidate) => candidate.value === normalized);
  return level ? level.label : DEFAULT_MAIN_REASONING_LEVEL;
}

function readReasoningLevelFromSettings(payload) {
  return normalizeReasoningLevel(payload?.payload?.reasoning_effort?.value);
}

function buildReasoningPatchPayload(value) {
  return {
    reasoning_effort: {
      value: normalizeReasoningLevel(value),
    },
  };
}

function createMainReasoningControl({
  selectEl,
  statusEl,
  fetchFn,
  consoleObj,
} = {}) {
  const httpFetch = fetchFn || (typeof fetch !== 'undefined' ? fetch : null);
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });
  const state = {
    loaded: false,
    saving: false,
    value: DEFAULT_MAIN_REASONING_LEVEL,
  };

  const setStatus = (message) => {
    if (statusEl) statusEl.textContent = message || '';
  };

  const setDisabled = (disabled) => {
    if (selectEl) selectEl.disabled = Boolean(disabled);
  };

  const render = () => {
    if (!selectEl) return;
    if (!selectEl.options.length) {
      const doc = selectEl.ownerDocument || (typeof document !== 'undefined' ? document : null);
      if (!doc) return;
      MAIN_REASONING_LEVELS.forEach((level) => {
        const option = doc.createElement('option');
        option.value = level.value;
        option.textContent = level.label;
        selectEl.appendChild(option);
      });
    }
    selectEl.value = state.value;
    selectEl.title = `Raisonnement global: ${reasoningLabel(state.value)}`;
    if (state.saving) setStatus('enregistrement');
  };

  const load = async () => {
    if (!selectEl || !httpFetch) return;
    setDisabled(true);
    try {
      const response = await httpFetch(MAIN_REASONING_ENDPOINT, { method: 'GET' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      state.value = readReasoningLevelFromSettings(data);
      state.loaded = true;
      render();
    } catch (error) {
      logger.warn?.('main_reasoning_control_load_failed', error);
      state.value = DEFAULT_MAIN_REASONING_LEVEL;
      render();
      setStatus('indisponible');
    } finally {
      setDisabled(false);
    }
  };

  const save = async (nextValue) => {
    if (!selectEl || !httpFetch) return;
    const normalized = normalizeReasoningLevel(nextValue);
    const previous = state.value;
    state.value = normalized;
    state.saving = true;
    render();
    setDisabled(true);
    try {
      const response = await httpFetch(MAIN_REASONING_ENDPOINT, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          updated_by: 'chat_reasoning_control',
          payload: buildReasoningPatchPayload(normalized),
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      state.value = readReasoningLevelFromSettings(data);
      state.loaded = true;
      setStatus('global');
    } catch (error) {
      logger.warn?.('main_reasoning_control_save_failed', error);
      state.value = previous;
      setStatus('erreur');
    } finally {
      state.saving = false;
      render();
      setDisabled(false);
    }
  };

  const bind = () => {
    if (!selectEl) return;
    render();
    selectEl.addEventListener('change', () => {
      void save(selectEl.value);
    });
  };

  bind();
  void load();

  return Object.freeze({
    state,
    load,
    save,
  });
}

const FridaMainReasoningControl = Object.freeze({
  MAIN_REASONING_LEVELS,
  DEFAULT_MAIN_REASONING_LEVEL,
  MAIN_REASONING_ENDPOINT,
  normalizeReasoningLevel,
  reasoningLabel,
  readReasoningLevelFromSettings,
  buildReasoningPatchPayload,
  createMainReasoningControl,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaMainReasoningControl;
}

if (typeof window !== 'undefined') {
  window.FridaMainReasoningControl = FridaMainReasoningControl;
}
