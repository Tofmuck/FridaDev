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
  const THEME_COLORS = Object.freeze({
    [THEME_LIGHT]: '#f8f6f3',
    [THEME_DARK]: '#0b1018',
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

  function applyTheme(documentRef, value) {
    if (!documentRef || !documentRef.documentElement) return THEME_LIGHT;
    const theme = normalizeTheme(value);
    documentRef.documentElement.dataset.theme = theme;
    documentRef.documentElement.style.colorScheme = theme;
    const themeColor = documentRef.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.setAttribute('content', THEME_COLORS[theme]);
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
      setTheme,
      destroy: () => button.removeEventListener('click', onClick),
    };
  }

  return {
    STORAGE_KEY,
    THEME_LIGHT,
    THEME_DARK,
    normalizeTheme,
    applyTheme,
    applyInitialTheme,
    createThemeController,
  };
});
