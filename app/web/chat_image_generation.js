'use strict';

const IMAGE_GENERATORS = Object.freeze({
  image_generator_openai: Object.freeze({
    generator_key: 'image_generator_openai',
    display_name: 'OpenAI Image',
    openrouter_model_id: 'openai/gpt-5.4-image-2',
    supported_aspect_ratios: Object.freeze(['1:1', '16:9', '9:16']),
    supported_image_sizes: Object.freeze(['1K']),
    pricing_label: 'prix API observé: prompt 0.000008 / completion 0.000015; prix image non exposé',
  }),
  image_generator_nano_banana: Object.freeze({
    generator_key: 'image_generator_nano_banana',
    display_name: 'Nano Banana',
    openrouter_model_id: 'google/gemini-2.5-flash-image',
    supported_aspect_ratios: Object.freeze(['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9']),
    supported_image_sizes: Object.freeze(['1K', '2K']),
    pricing_label: 'prix API observé: image 0.0000003 / prompt 0.0000003 / completion 0.0000025',
  }),
  image_generator_recraft: Object.freeze({
    generator_key: 'image_generator_recraft',
    display_name: 'Recraft',
    openrouter_model_id: 'recraft/recraft-v4.1',
    supported_aspect_ratios: Object.freeze(['1:1', '16:9', '9:16']),
    supported_image_sizes: Object.freeze(['1K']),
    pricing_label: "prix image non exposé par l'API modèles",
  }),
  image_generator_flux: Object.freeze({
    generator_key: 'image_generator_flux',
    display_name: 'Flux',
    openrouter_model_id: 'black-forest-labs/flux.2-pro',
    supported_aspect_ratios: Object.freeze(['1:1', '16:9', '9:16']),
    supported_image_sizes: Object.freeze(['1K']),
    pricing_label: "prix image non exposé par l'API modèles",
  }),
});

const DEFAULT_GENERATOR_KEY = 'image_generator_nano_banana';
const IMAGE_GENERATION_ENDPOINT = '/api/tools/image-generation';

function imageGeneratorList() {
  return Object.values(IMAGE_GENERATORS);
}

function getGeneratorSpec(generatorKey) {
  return IMAGE_GENERATORS[String(generatorKey || '')] || IMAGE_GENERATORS[DEFAULT_GENERATOR_KEY];
}

function firstSupportedValue(values, fallback = '') {
  const list = Array.from(values || []).filter(Boolean);
  return list.length ? list[0] : fallback;
}

function normalizeSelection({ generatorKey, aspectRatio, imageSize } = {}) {
  const spec = getGeneratorSpec(generatorKey);
  return {
    generator_key: spec.generator_key,
    aspect_ratio: spec.supported_aspect_ratios.includes(aspectRatio)
      ? aspectRatio
      : firstSupportedValue(spec.supported_aspect_ratios, '1:1'),
    image_size: spec.supported_image_sizes.includes(imageSize)
      ? imageSize
      : firstSupportedValue(spec.supported_image_sizes, '1K'),
  };
}

function extensionForMimeType(mimeType) {
  const normalized = String(mimeType || '').toLowerCase();
  if (normalized.includes('jpeg') || normalized.includes('jpg')) return 'jpg';
  if (normalized.includes('webp')) return 'webp';
  if (normalized.includes('gif')) return 'gif';
  if (normalized.includes('svg')) return 'svg';
  return 'png';
}

function formatTimestampForFilename(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return 'image';
  const pad = (value) => String(value).padStart(2, '0');
  return [
    d.getFullYear(),
    pad(d.getMonth() + 1),
    pad(d.getDate()),
  ].join('') + '-' + [pad(d.getHours()), pad(d.getMinutes()), pad(d.getSeconds())].join('');
}

function buildDownloadFilename({ mimeType, date } = {}) {
  return `fridadev-image-${formatTimestampForFilename(date)}.${extensionForMimeType(mimeType)}`;
}

function createImageGenerationController({
  buttonEl,
  panelEl,
  closeButtonEl,
  formEl,
  promptEl,
  modelSelectEl,
  aspectRatioSelectEl,
  imageSizeSelectEl,
  pricingEl,
  statusEl,
  submitButtonEl,
  emptyEl,
  previewEl,
  resultEl,
  metaEl,
  downloadButtonEl,
  fetchFn,
  documentObj,
  consoleObj,
} = {}) {
  const httpFetch = fetchFn || (typeof fetch !== 'undefined' ? fetch : null);
  const doc = documentObj || (typeof document !== 'undefined' ? document : null);
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });
  const state = {
    open: false,
    busy: false,
    generatorKey: DEFAULT_GENERATOR_KEY,
    aspectRatio: '1:1',
    imageSize: '1K',
    imageDataUrl: '',
    mimeType: '',
    metaText: '',
    status: '',
    isError: false,
  };

  const setStatus = (message, isError = false) => {
    state.status = String(message || '').trim();
    state.isError = Boolean(isError);
    render();
  };

  const resetResult = () => {
    state.imageDataUrl = '';
    state.mimeType = '';
    state.metaText = '';
  };

  const syncSelectionFromControls = () => {
    const normalized = normalizeSelection({
      generatorKey: modelSelectEl ? modelSelectEl.value : state.generatorKey,
      aspectRatio: aspectRatioSelectEl ? aspectRatioSelectEl.value : state.aspectRatio,
      imageSize: imageSizeSelectEl ? imageSizeSelectEl.value : state.imageSize,
    });
    state.generatorKey = normalized.generator_key;
    state.aspectRatio = normalized.aspect_ratio;
    state.imageSize = normalized.image_size;
  };

  const renderOptions = () => {
    if (modelSelectEl && !modelSelectEl.options.length) {
      imageGeneratorList().forEach((spec) => {
        const option = doc ? doc.createElement('option') : null;
        if (!option) return;
        option.value = spec.generator_key;
        option.textContent = spec.display_name;
        modelSelectEl.appendChild(option);
      });
    }

    const spec = getGeneratorSpec(state.generatorKey);
    if (modelSelectEl) modelSelectEl.value = spec.generator_key;
    fillSelect(aspectRatioSelectEl, spec.supported_aspect_ratios, state.aspectRatio, doc);
    fillSelect(imageSizeSelectEl, spec.supported_image_sizes, state.imageSize, doc);
    if (pricingEl) pricingEl.textContent = spec.pricing_label;
  };

  const render = () => {
    syncSelectionFromControls();
    renderOptions();
    if (panelEl) panelEl.classList.toggle('hidden', !state.open);
    if (buttonEl) {
      buttonEl.classList.toggle('active', state.open);
      buttonEl.setAttribute('aria-expanded', state.open ? 'true' : 'false');
    }
    if (submitButtonEl) {
      submitButtonEl.disabled = state.busy;
      submitButtonEl.textContent = state.busy ? 'Génération…' : 'Générer';
    }
    if (statusEl) {
      statusEl.textContent = state.status;
      statusEl.classList.toggle('is-error', state.isError);
      if (state.busy) {
        statusEl.dataset.imageGenerationState = 'generating';
      } else {
        delete statusEl.dataset.imageGenerationState;
      }
    }
    if (emptyEl) {
      emptyEl.hidden = Boolean(state.imageDataUrl || state.busy);
      emptyEl.setAttribute('aria-hidden', emptyEl.hidden ? 'true' : 'false');
    }
    if (previewEl) {
      previewEl.hidden = !state.imageDataUrl;
      if (state.imageDataUrl) previewEl.src = state.imageDataUrl;
      else previewEl.removeAttribute('src');
    }
    if (resultEl) resultEl.hidden = !state.imageDataUrl;
    if (metaEl) metaEl.textContent = state.metaText;
    if (downloadButtonEl) downloadButtonEl.disabled = !state.imageDataUrl;
  };

  const open = () => {
    state.open = true;
    setStatus('');
    render();
    if (promptEl && typeof promptEl.focus === 'function') {
      window.setTimeout(() => promptEl.focus(), 0);
    }
  };

  const close = () => {
    state.open = false;
    render();
  };

  const toggle = () => {
    if (state.open) close();
    else open();
  };

  const submit = async () => {
    if (!httpFetch || state.busy) return;
    syncSelectionFromControls();
    const prompt = String(promptEl && promptEl.value || '').trim();
    if (!prompt) {
      resetResult();
      setStatus('Prompt requis.', true);
      return;
    }

    state.busy = true;
    resetResult();
    setStatus('Génération en cours.');
    try {
      const response = await httpFetch(IMAGE_GENERATION_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          generator_key: state.generatorKey,
          prompt,
          aspect_ratio: state.aspectRatio,
          image_size: state.imageSize,
        }),
      });
      let data = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }
      if (!response.ok || !data || data.ok === false) {
        throw new Error(imageGenerationErrorLabel(data));
      }
      state.imageDataUrl = String(data.image_data_url || '');
      state.mimeType = String(data.mime_type || 'image/png');
      state.metaText = compactResultMeta(data);
      setStatus('Image générée.');
    } catch (error) {
      logger.warn('Image generation failed', error);
      resetResult();
      setStatus(error && error.message ? error.message : 'Génération indisponible.', true);
    } finally {
      state.busy = false;
      render();
    }
  };

  const download = () => {
    if (!state.imageDataUrl || !doc) return false;
    const link = doc.createElement('a');
    link.href = state.imageDataUrl;
    link.download = buildDownloadFilename({ mimeType: state.mimeType });
    link.rel = 'noopener';
    doc.body.appendChild(link);
    link.click();
    link.remove();
    return true;
  };

  if (buttonEl) buttonEl.addEventListener('click', toggle);
  if (closeButtonEl) closeButtonEl.addEventListener('click', close);
  if (formEl) {
    formEl.addEventListener('submit', (event) => {
      event.preventDefault();
      void submit();
    });
  }
  if (modelSelectEl) {
    modelSelectEl.addEventListener('change', () => {
      state.generatorKey = modelSelectEl.value;
      const normalized = normalizeSelection({ generatorKey: state.generatorKey });
      state.aspectRatio = normalized.aspect_ratio;
      state.imageSize = normalized.image_size;
      render();
    });
  }
  if (aspectRatioSelectEl) {
    aspectRatioSelectEl.addEventListener('change', () => {
      state.aspectRatio = aspectRatioSelectEl.value;
    });
  }
  if (imageSizeSelectEl) {
    imageSizeSelectEl.addEventListener('change', () => {
      state.imageSize = imageSizeSelectEl.value;
    });
  }
  if (downloadButtonEl) downloadButtonEl.addEventListener('click', download);

  render();
  return Object.freeze({
    open,
    close,
    submit,
    download,
    getState: () => ({ ...state }),
  });
}

function fillSelect(selectEl, values, selectedValue, doc) {
  if (!selectEl || !doc) return;
  selectEl.innerHTML = '';
  Array.from(values || []).forEach((value) => {
    const option = doc.createElement('option');
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  });
  if (Array.from(values || []).includes(selectedValue)) {
    selectEl.value = selectedValue;
  }
}

function imageGenerationErrorLabel(data) {
  const code = String(data && data.error_code || '').trim();
  if (code === 'invalid_prompt') return 'Prompt requis.';
  if (code === 'invalid_aspect_ratio' || code === 'invalid_image_size') return 'Format non pris en charge.';
  if (code === 'invalid_generator') return 'Modèle indisponible.';
  if (code === 'timeout') return 'Génération trop longue.';
  if (code === 'no_image') return 'Aucune image renvoyée.';
  if (code === 'invalid_image_data_url') return 'Image renvoyée invalide.';
  return String(data && data.message || '').trim() || 'Génération indisponible.';
}

function compactResultMeta(data) {
  const parts = [];
  const displayName = String(data && data.display_name || '').trim();
  const aspectRatio = String(data && data.aspect_ratio || '').trim();
  const imageSize = String(data && data.image_size || '').trim();
  if (displayName) parts.push(displayName);
  if (aspectRatio) parts.push(aspectRatio);
  if (imageSize) parts.push(imageSize);
  const usage = data && typeof data.usage === 'object' && data.usage ? data.usage : {};
  if (usage.cost !== undefined && usage.cost !== null) {
    parts.push(`coût observé ${usage.cost}`);
  }
  return parts.join(' · ');
}

const FridaImageGeneration = Object.freeze({
  IMAGE_GENERATORS,
  DEFAULT_GENERATOR_KEY,
  IMAGE_GENERATION_ENDPOINT,
  imageGeneratorList,
  getGeneratorSpec,
  normalizeSelection,
  extensionForMimeType,
  buildDownloadFilename,
  compactResultMeta,
  createImageGenerationController,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaImageGeneration;
}

if (typeof window !== 'undefined') {
  window.FridaImageGeneration = FridaImageGeneration;
}
