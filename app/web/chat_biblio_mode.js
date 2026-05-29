'use strict';

const BIBLIO_STORAGE_KEY = 'frida.biblioMode';
const BIBLIO_PAYLOAD_KEY = 'biblio_enabled';

function normalizeBiblioEnabled(value) {
  if (value === true) return true;
  if (value === false || value == null) return false;
  const normalized = String(value || '').trim().toLowerCase();
  return ['1', 'true', 'yes', 'on', 'enabled', 'active'].includes(normalized);
}

function buildBiblioChatPayload(enabled) {
  return {
    [BIBLIO_PAYLOAD_KEY]: normalizeBiblioEnabled(enabled),
  };
}

function createBiblioModeController({
  buttonEl,
  storage,
  storageKey = BIBLIO_STORAGE_KEY,
  onActiveChange,
} = {}) {
  const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
  const state = {
    active: false,
  };

  try {
    state.active = normalizeBiblioEnabled(store ? store.getItem(storageKey) : false);
  } catch {
    state.active = false;
  }

  const persist = () => {
    if (!store) return;
    try {
      store.setItem(storageKey, state.active ? '1' : '0');
    } catch {}
  };

  const emitActiveChange = () => {
    if (typeof onActiveChange === 'function') {
      onActiveChange(state.active);
    }
  };

  const render = () => {
    if (!buttonEl) return;
    buttonEl.classList.toggle('active', state.active);
    buttonEl.setAttribute('aria-pressed', state.active ? 'true' : 'false');
    buttonEl.title = state.active ? 'Biblio : activée' : 'Biblio : désactivée';
    buttonEl.setAttribute(
      'aria-label',
      state.active ? 'Désactiver Biblio' : 'Activer Biblio',
    );
  };

  const setActive = (active) => {
    const next = normalizeBiblioEnabled(active);
    const changed = state.active !== next;
    state.active = next;
    persist();
    render();
    if (changed) emitActiveChange();
  };

  const toggle = () => setActive(!state.active);

  if (buttonEl) {
    buttonEl.addEventListener('click', toggle);
  }

  render();

  return Object.freeze({
    state,
    isActive: () => state.active,
    setActive,
    toggle,
    getPayload: () => buildBiblioChatPayload(state.active),
  });
}

const FridaBiblioMode = Object.freeze({
  BIBLIO_STORAGE_KEY,
  BIBLIO_PAYLOAD_KEY,
  normalizeBiblioEnabled,
  buildBiblioChatPayload,
  createBiblioModeController,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaBiblioMode;
}

if (typeof window !== 'undefined') {
  window.FridaBiblioMode = FridaBiblioMode;
}
