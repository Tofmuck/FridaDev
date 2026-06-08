'use strict';

const AGENDA_STORAGE_KEY = 'frida.agendaMode';
const AGENDA_PAYLOAD_KEY = 'agenda_enabled';

function normalizeAgendaEnabled(value) {
  if (value === true) return true;
  if (value === false || value == null) return false;
  const normalized = String(value || '').trim().toLowerCase();
  return ['1', 'true', 'yes', 'on', 'enabled', 'active'].includes(normalized);
}

function buildAgendaChatPayload(enabled) {
  return {
    [AGENDA_PAYLOAD_KEY]: normalizeAgendaEnabled(enabled),
  };
}

function createAgendaModeController({
  buttonEl,
  storage,
  storageKey = AGENDA_STORAGE_KEY,
  onActiveChange,
} = {}) {
  const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
  const state = {
    active: false,
  };

  try {
    state.active = normalizeAgendaEnabled(store ? store.getItem(storageKey) : false);
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
    buttonEl.title = state.active ? 'Agenda : active' : 'Agenda : desactive';
    buttonEl.setAttribute(
      'aria-label',
      state.active ? 'Desactiver Agenda' : 'Activer Agenda',
    );
  };

  const setActive = (active) => {
    const next = normalizeAgendaEnabled(active);
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
    getPayload: () => buildAgendaChatPayload(state.active),
  });
}

const FridaAgendaMode = Object.freeze({
  AGENDA_STORAGE_KEY,
  AGENDA_PAYLOAD_KEY,
  normalizeAgendaEnabled,
  buildAgendaChatPayload,
  createAgendaModeController,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaAgendaMode;
}

if (typeof window !== 'undefined') {
  window.FridaAgendaMode = FridaAgendaMode;
}
