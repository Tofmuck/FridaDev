'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const dialogueMode = require('../../../web/chat_dialogue_mode.js');

test('dialogue animation truth follows speech playback rather than network activity', () => {
  assert.deepEqual(dialogueMode.getDialogueStateView('listening'), {
    state: 'listening',
    label: 'ÉCOUTE ACTIVE',
    voiceActive: false,
    fridaSpeaking: false,
  });
  assert.deepEqual(dialogueMode.getDialogueStateView('user_speaking'), {
    state: 'user_speaking',
    label: 'JE T’ÉCOUTE',
    voiceActive: true,
    fridaSpeaking: false,
  });
  assert.deepEqual(dialogueMode.getDialogueStateView('transcribing'), {
    state: 'transcribing',
    label: 'TRANSCRIPTION',
    voiceActive: false,
    fridaSpeaking: false,
  });
  assert.deepEqual(dialogueMode.getDialogueStateView('thinking'), {
    state: 'thinking',
    label: 'FRIDA RÉFLÉCHIT',
    voiceActive: false,
    fridaSpeaking: false,
  });
  assert.deepEqual(dialogueMode.getDialogueStateView('tts_speaking'), {
    state: 'tts_speaking',
    label: 'FRIDA PARLE',
    voiceActive: true,
    fridaSpeaking: true,
  });
});

test('dialogue controller projects state, pause and exit without audio side effects', () => {
  const root = createFakeElement();
  const screen = createFakeElement({ hidden: true });
  const status = createFakeElement();
  const pause = createFakeElement();
  const end = createFakeElement();
  const close = createFakeElement();
  const navigation = createFakeElement();
  const events = [];
  const controller = dialogueMode.createDialogueModeController({
    rootEl: root,
    screenEl: screen,
    statusEl: status,
    pauseButtonEl: pause,
    endButtonEl: end,
    closeButtonEl: close,
    navigationButtonEl: navigation,
    onOpenNavigation: () => events.push('navigation'),
  });

  assert.equal(controller.isActive(), false);
  controller.enter();
  assert.equal(screen.hidden, false);
  assert.equal(screen.getAttribute('aria-hidden'), 'false');
  assert.equal(root.dataset.dialogueState, 'listening');
  assert.equal(root.dataset.dialogueVoiceActive, 'false');
  assert.equal(root.dataset.dialogueFridaSpeaking, 'false');
  assert.equal(status.textContent, 'ÉCOUTE ACTIVE');

  controller.setState('user_speaking');
  assert.equal(root.dataset.dialogueVoiceActive, 'true');
  assert.equal(root.dataset.dialogueFridaSpeaking, 'false');

  controller.setState('tts_speaking');
  assert.equal(root.dataset.dialogueVoiceActive, 'true');
  assert.equal(root.dataset.dialogueFridaSpeaking, 'true');

  pause.dispatch('click');
  assert.equal(root.dataset.dialogueState, 'paused');
  assert.equal(pause.getAttribute('aria-pressed'), 'true');
  pause.dispatch('click');
  assert.equal(root.dataset.dialogueState, 'listening');

  navigation.dispatch('click');
  assert.deepEqual(events, ['navigation']);
  close.dispatch('click');
  assert.equal(controller.isActive(), false);
  assert.equal(screen.hidden, true);
  assert.equal(screen.getAttribute('aria-hidden'), 'true');
  assert.equal(root.dataset.dialogueState, undefined);

  controller.enter();
  end.dispatch('click');
  assert.equal(controller.isActive(), false);
});

test('dialogue screen is integrated with an enabled product entry and no transcript', () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, '../../../web/index.html'), 'utf8');
  const appSource = fs.readFileSync(path.join(__dirname, '../../../web/app.js'), 'utf8');
  const styles = fs.readFileSync(path.join(__dirname, '../../../web/styles.css'), 'utf8');
  const moduleIndex = indexHtml.indexOf('<script src="chat_dialogue_mode.js"></script>');
  const appIndex = indexHtml.indexOf('<script src="app.js"></script>');
  const screenStart = indexHtml.indexOf('id="dialogueModeScreen"');
  const screenEnd = indexHtml.indexOf('</section>', screenStart);
  const screenHtml = indexHtml.slice(screenStart, screenEnd);

  assert.ok(screenStart > 0, 'dialogue screen should exist');
  assert.match(screenHtml, /hidden/);
  assert.match(screenHtml, /id="dialogueModeStatus"/);
  assert.match(screenHtml, /id="dialogueModePause"/);
  assert.match(screenHtml, /id="dialogueModeEnd"/);
  assert.doesNotMatch(screenHtml, /textarea|transcript/i);
  assert.ok(moduleIndex > 0 && moduleIndex < appIndex, 'dialogue module should load before app.js');
  assert.match(styles, /data-dialogue-voice-active="true"/);
  assert.match(styles, /data-dialogue-frida-speaking="true"/);
  assert.doesNotMatch(indexHtml, /id="btnDialogueMode"[^>]*disabled/);
  assert.match(indexHtml, /id="btnDialogueMode"[^>]*title="Démarrer le mode Dialogue"/);
  assert.doesNotMatch(appSource, /data-dialogue-preflight|full_canary|dialogueProductAuthorized/);
});

test('D5 buffering stops both animations without turning Pause into Resume', () => {
  const root = createFakeElement();
  const status = createFakeElement();
  const pause = createFakeElement();
  const controller = dialogueMode.createDialogueModeController({
    rootEl: root, statusEl: status, pauseButtonEl: pause,
  });
  controller.enter();
  controller.setState('tts_speaking');
  controller.setState('tts_pending');
  assert.equal(root.dataset.dialogueVoiceActive, 'false');
  assert.equal(root.dataset.dialogueFridaSpeaking, 'false');
  assert.equal(status.textContent, 'AUDIO EN ATTENTE');
  assert.equal(pause.getAttribute('aria-pressed'), 'false');
  pause.dispatch('click');
  assert.equal(controller.getState(), 'paused');
});

function createFakeElement({ hidden = false } = {}) {
  const attrs = new Map();
  const listeners = new Map();
  const classes = new Set();
  return {
    hidden,
    textContent: '',
    dataset: {},
    classList: {
      toggle(name, active) {
        if (active) classes.add(name);
        else classes.delete(name);
      },
      contains(name) {
        return classes.has(name);
      },
    },
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    removeAttribute(name) {
      attrs.delete(name);
    },
    getAttribute(name) {
      return attrs.get(name);
    },
    addEventListener(name, handler) {
      listeners.set(name, handler);
    },
    dispatch(name) {
      const handler = listeners.get(name);
      if (handler) handler({ preventDefault() {} });
    },
  };
}
