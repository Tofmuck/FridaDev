(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.FridaChatTheme = api;
    if (root.document) {
      api.applyInitialTheme({ document: root.document, storage: root.localStorage });
    }
  }
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const STORAGE_KEY = 'frida.chat.theme';
  const THEME_LIGHT = 'light';
  const THEME_DARK = 'dark';
  const MOBILE_DIALOGUE_QUERY = '(max-width: 640px)';
  const COARSE_POINTER_QUERY = '(pointer: coarse)';
  const STANDALONE_DISPLAY_QUERY = '(display-mode: standalone)';
  const PHONE_SHORT_SIDE_MAX = 640;
  const PRESENTATION_CONTEXT_EVENT = 'frida:presentation-context-change';
  const MOBILE_DIALOGUE_COLOR = '#060913';
  const THEME_COLORS = Object.freeze({
    [THEME_LIGHT]: '#fbf8f3',
    [THEME_DARK]: '#0d1117',
  });

  function normalizeTheme(value) {
    return value === THEME_DARK ? THEME_DARK : THEME_LIGHT;
  }

  function readStoredTheme(storage) {
    try {
      return normalizeTheme(storage && storage.getItem(STORAGE_KEY));
    } catch (_) {
      return THEME_LIGHT;
    }
  }

  function updateThemeButton(documentRef, theme) {
    const button = documentRef && documentRef.getElementById('btnTheme');
    if (!button) return;
    const nextLabel = theme === THEME_DARK ? 'Passer au mode clair' : 'Passer au mode sombre';
    button.dataset.theme = theme;
    button.setAttribute('aria-label', nextLabel);
    button.setAttribute('title', nextLabel);
    button.setAttribute('aria-pressed', theme === THEME_DARK ? 'true' : 'false');
  }

  function getPresentationQuery(documentRef, query) {
    const view = documentRef && documentRef.defaultView;
    return view && typeof view.matchMedia === 'function'
      ? view.matchMedia(query)
      : null;
  }

  function isPhonePresentation(documentRef) {
    const view = documentRef && documentRef.defaultView;
    if (!view) return false;
    const narrowQuery = getPresentationQuery(documentRef, MOBILE_DIALOGUE_QUERY);
    if (narrowQuery && narrowQuery.matches) return true;

    const screenWidth = Number(view.screen && view.screen.width);
    const screenHeight = Number(view.screen && view.screen.height);
    const shortSide = Math.min(screenWidth, screenHeight);
    if (!Number.isFinite(shortSide) || shortSide <= 0 || shortSide > PHONE_SHORT_SIDE_MAX) {
      return false;
    }

    const coarseQuery = getPresentationQuery(documentRef, COARSE_POINTER_QUERY);
    const standaloneQuery = getPresentationQuery(documentRef, STANDALONE_DISPLAY_QUERY);
    const navigatorRef = view.navigator || {};
    const touchCapable = Number(navigatorRef.maxTouchPoints || 0) > 0
      || Boolean(coarseQuery && coarseQuery.matches);
    const standalone = navigatorRef.standalone === true
      || Boolean(standaloneQuery && standaloneQuery.matches);
    return touchCapable || standalone;
  }

  function notifyPresentationContext(documentRef, phone) {
    const view = documentRef && documentRef.defaultView;
    if (!view || typeof view.CustomEvent !== 'function' || typeof documentRef.dispatchEvent !== 'function') return;
    documentRef.dispatchEvent(new view.CustomEvent(PRESENTATION_CONTEXT_EVENT, {
      detail: { phone },
    }));
  }

  function syncPresentationTheme(documentRef, theme) {
    if (!documentRef || !documentRef.documentElement) return theme;
    const previousContext = documentRef.documentElement.dataset.presentationContext;
    const mobileDialogue = isPhonePresentation(documentRef);
    if (mobileDialogue) {
      documentRef.documentElement.dataset.presentationContext = 'phone';
      documentRef.documentElement.dataset.presentationTheme = 'mobile-dialogue';
    } else {
      delete documentRef.documentElement.dataset.presentationContext;
      delete documentRef.documentElement.dataset.presentationTheme;
    }
    const presentationTheme = mobileDialogue ? THEME_DARK : theme;
    documentRef.documentElement.style.colorScheme = presentationTheme;
    const themeColor = documentRef.querySelector('meta[name="theme-color"]');
    if (themeColor) {
      themeColor.setAttribute('content', mobileDialogue ? MOBILE_DIALOGUE_COLOR : THEME_COLORS[theme]);
    }
    const nextContext = documentRef.documentElement.dataset.presentationContext;
    if (nextContext !== previousContext) notifyPresentationContext(documentRef, mobileDialogue);
    return presentationTheme;
  }

  function applyTheme(documentRef, value) {
    if (!documentRef || !documentRef.documentElement) return THEME_LIGHT;
    const theme = normalizeTheme(value);
    documentRef.documentElement.dataset.theme = theme;
    syncPresentationTheme(documentRef, theme);
    updateThemeButton(documentRef, theme);
    return theme;
  }

  function applyInitialTheme({ document: documentRef, storage } = {}) {
    return applyTheme(documentRef, readStoredTheme(storage));
  }

  function createThemeController({ document: documentRef, storage } = {}) {
    if (!documentRef) throw new Error('theme document missing');
    const button = documentRef.getElementById('btnTheme');
    if (!button) throw new Error('theme button missing');

    let theme = applyTheme(documentRef, documentRef.documentElement.dataset.theme || readStoredTheme(storage));
    const view = documentRef.defaultView;
    const presentationQueries = [
      MOBILE_DIALOGUE_QUERY,
      COARSE_POINTER_QUERY,
      STANDALONE_DISPLAY_QUERY,
    ].map((query) => getPresentationQuery(documentRef, query)).filter(Boolean);
    const onPresentationChange = () => syncPresentationTheme(documentRef, theme);
    presentationQueries.forEach((query) => {
      if (typeof query.addEventListener === 'function') {
        query.addEventListener('change', onPresentationChange);
      } else if (typeof query.addListener === 'function') {
        query.addListener(onPresentationChange);
      }
    });
    if (view && typeof view.addEventListener === 'function') {
      view.addEventListener('pageshow', onPresentationChange);
    }
    const setTheme = (value, { persist = true } = {}) => {
      theme = applyTheme(documentRef, value);
      if (persist) {
        try {
          if (storage) storage.setItem(STORAGE_KEY, theme);
        } catch (_) {
          // Le thème reste fonctionnel même si le stockage navigateur est indisponible.
        }
      }
      return theme;
    };
    const onClick = () => setTheme(theme === THEME_DARK ? THEME_LIGHT : THEME_DARK);
    button.addEventListener('click', onClick);

    return {
      getTheme: () => theme,
      isPhonePresentation: () => isPhonePresentation(documentRef),
      syncPresentation: onPresentationChange,
      setTheme,
      destroy: () => {
        button.removeEventListener('click', onClick);
        presentationQueries.forEach((query) => {
          if (typeof query.removeEventListener === 'function') {
            query.removeEventListener('change', onPresentationChange);
          } else if (typeof query.removeListener === 'function') {
            query.removeListener(onPresentationChange);
          }
        });
        if (view && typeof view.removeEventListener === 'function') {
          view.removeEventListener('pageshow', onPresentationChange);
        }
      },
    };
  }

  return {
    STORAGE_KEY,
    THEME_LIGHT,
    THEME_DARK,
    MOBILE_DIALOGUE_QUERY,
    COARSE_POINTER_QUERY,
    STANDALONE_DISPLAY_QUERY,
    PHONE_SHORT_SIDE_MAX,
    PRESENTATION_CONTEXT_EVENT,
    MOBILE_DIALOGUE_COLOR,
    normalizeTheme,
    isPhonePresentation,
    syncPresentationTheme,
    applyTheme,
    applyInitialTheme,
    createThemeController,
  };
});
