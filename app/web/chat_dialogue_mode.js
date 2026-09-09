'use strict';

const DIALOGUE_STATE_VIEWS = Object.freeze({
  listening: Object.freeze({
    state: 'listening',
    label: 'ÉCOUTE ACTIVE',
    voiceActive: false,
    fridaSpeaking: false,
  }),
  user_speaking: Object.freeze({
    state: 'user_speaking',
    label: 'JE T’ÉCOUTE',
    voiceActive: true,
    fridaSpeaking: false,
  }),
  transcribing: Object.freeze({
    state: 'transcribing',
    label: 'TRANSCRIPTION',
    voiceActive: false,
    fridaSpeaking: false,
  }),
  thinking: Object.freeze({
    state: 'thinking',
    label: 'FRIDA RÉFLÉCHIT',
    voiceActive: false,
    fridaSpeaking: false,
  }),
  tts_speaking: Object.freeze({
    state: 'tts_speaking',
    label: 'FRIDA PARLE',
    voiceActive: true,
    fridaSpeaking: true,
  }),
  paused: Object.freeze({
    state: 'paused',
    label: 'EN PAUSE',
    voiceActive: false,
    fridaSpeaking: false,
  }),
  error: Object.freeze({
    state: 'error',
    label: 'INDISPONIBLE',
    voiceActive: false,
    fridaSpeaking: false,
  }),
});

function getDialogueStateView(state) {
  const key = String(state || '').trim().toLowerCase();
  const view = DIALOGUE_STATE_VIEWS[key];
  if (!view) {
    throw new TypeError(`Unsupported dialogue state: ${key || '(empty)'}`);
  }
  return { ...view };
}

function createDialogueModeController({
  rootEl,
  screenEl,
  backgroundEl,
  statusEl,
  entryButtonEl,
  pauseButtonEl,
  pauseLabelEl,
  endButtonEl,
  closeButtonEl,
  navigationButtonEl,
  onOpenNavigation,
  onExit,
} = {}) {
  const state = {
    active: false,
    current: 'listening',
  };

  const setRootData = (name, value) => {
    if (!rootEl || !rootEl.dataset) return;
    if (value == null) delete rootEl.dataset[name];
    else rootEl.dataset[name] = String(value);
  };

  const render = () => {
    const view = getDialogueStateView(state.current);
    if (screenEl) {
      screenEl.hidden = !state.active;
      screenEl.setAttribute('aria-hidden', state.active ? 'false' : 'true');
      screenEl.dataset.dialogueState = view.state;
    }
    if (statusEl) statusEl.textContent = view.label;
    if (backgroundEl) {
      if (state.active) {
        backgroundEl.setAttribute('inert', '');
        backgroundEl.setAttribute('aria-hidden', 'true');
      } else {
        backgroundEl.removeAttribute('inert');
        backgroundEl.removeAttribute('aria-hidden');
      }
    }
    if (pauseButtonEl) {
      const paused = view.state === 'paused';
      pauseButtonEl.setAttribute('aria-pressed', paused ? 'true' : 'false');
      pauseButtonEl.setAttribute('aria-label', paused ? 'Reprendre le dialogue' : 'Mettre le dialogue en pause');
    }
    if (pauseLabelEl) {
      pauseLabelEl.textContent = view.state === 'paused' ? 'Reprendre' : 'Mettre en pause';
    }
    if (!state.active) {
      setRootData('dialogueModeActive', null);
      setRootData('dialogueState', null);
      setRootData('dialogueVoiceActive', null);
      setRootData('dialogueFridaSpeaking', null);
      return;
    }
    setRootData('dialogueModeActive', 'true');
    setRootData('dialogueState', view.state);
    setRootData('dialogueVoiceActive', view.voiceActive ? 'true' : 'false');
    setRootData('dialogueFridaSpeaking', view.fridaSpeaking ? 'true' : 'false');
  };

  const setState = (nextState) => {
    const view = getDialogueStateView(nextState);
    state.current = view.state;
    render();
  };

  const enter = () => {
    state.active = true;
    state.current = 'listening';
    render();
  };

  const exit = () => {
    const wasActive = state.active;
    state.active = false;
    state.current = 'listening';
    render();
    if (wasActive && typeof onExit === 'function') onExit();
  };

  const togglePause = () => {
    if (!state.active) return;
    setState(state.current === 'paused' ? 'listening' : 'paused');
  };

  if (entryButtonEl) entryButtonEl.addEventListener('click', enter);
  if (pauseButtonEl) pauseButtonEl.addEventListener('click', togglePause);
  if (endButtonEl) endButtonEl.addEventListener('click', exit);
  if (closeButtonEl) closeButtonEl.addEventListener('click', exit);
  if (navigationButtonEl) {
    navigationButtonEl.addEventListener('click', () => {
      if (state.active && typeof onOpenNavigation === 'function') onOpenNavigation();
    });
  }

  render();

  return Object.freeze({
    state,
    enter,
    exit,
    setState,
    togglePause,
    isActive: () => state.active,
    getState: () => state.current,
  });
}

const FridaDialogueMode = Object.freeze({
  DIALOGUE_STATE_VIEWS,
  getDialogueStateView,
  createDialogueModeController,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaDialogueMode;
}

if (typeof window !== 'undefined') {
  window.FridaDialogueMode = FridaDialogueMode;
}
