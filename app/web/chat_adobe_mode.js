'use strict';

const ADOBE_SPECIALIZATION_PROFILE = 'adobe';
const ADOBE_PRODUCTS = Object.freeze([
  Object.freeze({ value: 'photoshop', label: 'Photoshop' }),
  Object.freeze({ value: 'illustrator', label: 'Illustrator' }),
]);

function normalizeAdobeProduct(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return ADOBE_PRODUCTS.some((product) => product.value === normalized) ? normalized : '';
}

function adobeProductLabel(value) {
  const normalized = normalizeAdobeProduct(value);
  const product = ADOBE_PRODUCTS.find((candidate) => candidate.value === normalized);
  return product ? product.label : '';
}

function buildAdobeChatPayload(product) {
  const normalized = normalizeAdobeProduct(product);
  if (!normalized) return {};
  return {
    specialization_profile: ADOBE_SPECIALIZATION_PROFILE,
    adobe_product: normalized,
  };
}

function createAdobeModeController({
  buttonEl,
  choicesEl,
  composerEl,
  rootStyle,
  onActiveChange,
} = {}) {
  const docStyle = rootStyle || (typeof document !== 'undefined' ? document.documentElement.style : null);
  const state = {
    expanded: false,
    product: '',
  };

  const isActive = () => Boolean(state.product);

  const refreshComposerHeight = () => {
    if (!composerEl || !docStyle || typeof requestAnimationFrame !== 'function') return;
    requestAnimationFrame(() => {
      const height = Math.ceil(composerEl.getBoundingClientRect().height || 76);
      docStyle.setProperty('--ask-h', `${Math.max(76, height)}px`);
    });
  };

  const emitActiveChange = () => {
    if (typeof onActiveChange === 'function') {
      onActiveChange(isActive());
    }
  };

  const render = () => {
    const active = isActive();
    if (buttonEl) {
      buttonEl.classList.toggle('active', active);
      buttonEl.setAttribute('aria-pressed', active ? 'true' : 'false');
      buttonEl.setAttribute('aria-expanded', state.expanded ? 'true' : 'false');
      buttonEl.title = active
        ? `Mode Adobe : ${adobeProductLabel(state.product)}`
        : 'Mode Adobe';
      buttonEl.setAttribute(
        'aria-label',
        active ? `Desactiver le mode Adobe ${adobeProductLabel(state.product)}` : 'Choisir un mode Adobe',
      );
    }
    if (choicesEl) {
      const visible = state.expanded || active;
      choicesEl.hidden = !visible;
      choicesEl.dataset.activeProduct = state.product || '';
      const productButtons = choicesEl.querySelectorAll('[data-adobe-product]');
      productButtons.forEach((productButton) => {
        const value = normalizeAdobeProduct(productButton.getAttribute('data-adobe-product'));
        const selected = Boolean(value && value === state.product);
        productButton.classList.toggle('active', selected);
        productButton.setAttribute('aria-checked', selected ? 'true' : 'false');
        productButton.title = selected
          ? `Mode Adobe ${adobeProductLabel(value)} actif`
          : `Utiliser Adobe ${adobeProductLabel(value)}`;
      });
    }
    refreshComposerHeight();
  };

  const setProduct = (product) => {
    const normalized = normalizeAdobeProduct(product);
    if (!normalized) return;
    const wasActive = isActive();
    state.product = normalized;
    state.expanded = true;
    render();
    if (wasActive !== isActive() || normalized) {
      emitActiveChange();
    }
  };

  const clear = () => {
    const wasActive = isActive();
    state.product = '';
    state.expanded = false;
    render();
    if (wasActive) {
      emitActiveChange();
    }
  };

  const toggle = () => {
    if (isActive()) {
      clear();
      return;
    }
    state.expanded = !state.expanded;
    render();
  };

  if (buttonEl) {
    buttonEl.addEventListener('click', toggle);
  }
  if (choicesEl) {
    choicesEl.addEventListener('click', (event) => {
      const target = event.target && event.target.closest
        ? event.target.closest('[data-adobe-product]')
        : null;
      if (!target || !choicesEl.contains(target)) return;
      setProduct(target.getAttribute('data-adobe-product'));
    });
  }

  render();

  return Object.freeze({
    state,
    isActive,
    setProduct,
    clear,
    getPayload: () => buildAdobeChatPayload(state.product),
  });
}

const FridaAdobeMode = Object.freeze({
  ADOBE_SPECIALIZATION_PROFILE,
  ADOBE_PRODUCTS,
  normalizeAdobeProduct,
  adobeProductLabel,
  buildAdobeChatPayload,
  createAdobeModeController,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaAdobeMode;
}

if (typeof window !== 'undefined') {
  window.FridaAdobeMode = FridaAdobeMode;
}
