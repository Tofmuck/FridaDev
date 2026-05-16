'use strict';

const ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.odt', '.md', '.txt'];

function createActiveDocumentController({
  chatEl,
  composerEl,
  barEl,
  listEl,
  statusEl,
  buttonEl,
  inputEl,
  fetchFn,
  getConversationId,
  ensureConversation,
  consoleObj,
  rootStyle,
} = {}) {
  const httpFetch = fetchFn || (typeof fetch !== 'undefined' ? fetch : null);
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });
  const docStyle = rootStyle || (typeof document !== 'undefined' ? document.documentElement.style : null);
  const state = {
    items: [],
    busy: false,
    status: '',
    isError: false,
  };

  const endpoint = () => {
    const conversationId = String(typeof getConversationId === 'function' ? getConversationId() || '' : '').trim();
    if (!conversationId) return '';
    return `/api/conversations/${encodeURIComponent(conversationId)}/active-documents`;
  };

  const refreshComposerHeight = () => {
    if (!composerEl || !docStyle || typeof requestAnimationFrame !== 'function') return;
    requestAnimationFrame(() => {
      const height = Math.ceil(composerEl.getBoundingClientRect().height || 76);
      docStyle.setProperty('--ask-h', `${Math.max(76, height)}px`);
    });
  };

  const setStatus = (message, isError = false) => {
    state.status = String(message || '').trim();
    state.isError = Boolean(isError);
    render();
  };

  const render = () => {
    if (!barEl || !listEl || !statusEl || !buttonEl) return;
    const hasItems = state.items.length > 0;
    const hasStatus = Boolean(state.status);
    barEl.hidden = !(hasItems || hasStatus);
    buttonEl.classList.toggle('active', hasItems);
    buttonEl.disabled = state.busy;

    listEl.innerHTML = '';
    state.items.forEach((item) => {
      const chip = document.createElement('div');
      chip.className = 'active-document-chip';
      if (item.last_excluded_reason_code) {
        chip.dataset.tone = 'warning';
      }

      const name = document.createElement('span');
      name.className = 'active-document-name';
      name.textContent = item.filename || 'fichier actif';
      chip.appendChild(name);

      const meta = document.createElement('span');
      meta.className = 'active-document-meta';
      meta.textContent = compactDocumentMeta(item);
      chip.appendChild(meta);

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'active-document-remove';
      remove.textContent = 'Retirer';
      remove.title = `Retirer ${item.filename || 'ce document actif'}`;
      remove.addEventListener('click', () => {
        void removeDocument(item.document_id);
      });
      chip.appendChild(remove);
      listEl.appendChild(chip);
    });

    statusEl.textContent = state.status;
    statusEl.classList.toggle('is-error', state.isError);
    refreshComposerHeight();
  };

  const parseJsonResponse = async (response) => {
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok || !data || data.ok === false) {
      const err = new Error(uploadErrorLabel(data?.reason_code) || data?.error || `HTTP ${response.status}`);
      err.payload = data;
      throw err;
    }
    return data;
  };

  const refresh = async ({ quiet = true } = {}) => {
    if (!httpFetch) return;
    const url = endpoint();
    if (!url) {
      state.items = [];
      if (!quiet) setStatus('Conversation indisponible.', true);
      render();
      return;
    }
    try {
      const response = await httpFetch(url);
      const data = await parseJsonResponse(response);
      state.items = Array.isArray(data.items) ? data.items : [];
      if (!state.items.length && quiet) {
        state.status = '';
        state.isError = false;
      }
      render();
    } catch (err) {
      logger.warn('Chargement des documents actifs échoué', err);
      state.items = [];
      if (!quiet) setStatus('Documents actifs indisponibles.', true);
      render();
    }
  };

  const uploadFiles = async (files) => {
    const fileList = Array.from(files || []).filter(Boolean);
    if (!fileList.length || !httpFetch) return;
    state.busy = true;
    render();
    try {
      if (typeof ensureConversation === 'function') {
        await ensureConversation();
      }
      const url = endpoint();
      if (!url) {
        setStatus('Ouvre une conversation avant d’activer un fichier.', true);
        return;
      }

      let activated = 0;
      let lastError = '';
      for (const file of fileList) {
        const formData = new FormData();
        formData.append('file', file, file.name || 'document');
        try {
          const response = await httpFetch(url, { method: 'POST', body: formData });
          await parseJsonResponse(response);
          activated += 1;
        } catch (err) {
          lastError = uploadErrorLabel(err?.payload?.reason_code) || err.message || 'Document non activable.';
          logger.warn('Activation document actif échouée', err);
        }
      }
      await refresh();
      if (activated > 0 && !lastError) {
        setStatus(activated === 1 ? 'Document actif ajouté.' : `${activated} documents actifs ajoutés.`);
      } else if (activated > 0) {
        setStatus(`${activated} document(s) actif(s) ajouté(s). ${lastError}`, true);
      } else {
        setStatus(lastError || 'Aucun document actif ajouté.', true);
      }
    } finally {
      state.busy = false;
      if (inputEl) inputEl.value = '';
      render();
    }
  };

  const removeDocument = async (documentId) => {
    const url = endpoint();
    if (!url || !documentId || !httpFetch) return;
    state.busy = true;
    render();
    try {
      const response = await httpFetch(`${url}/${encodeURIComponent(String(documentId))}`, { method: 'DELETE' });
      await parseJsonResponse(response);
      await refresh();
      setStatus('Document actif retiré.');
    } catch (err) {
      logger.warn('Retrait document actif échoué', err);
      setStatus('Retrait impossible.', true);
    } finally {
      state.busy = false;
      render();
    }
  };

  const bind = () => {
    if (buttonEl && inputEl) {
      buttonEl.addEventListener('click', () => inputEl.click());
      inputEl.addEventListener('change', () => {
        void uploadFiles(inputEl.files);
      });
    }
    if (!chatEl) return;

    let dragDepth = 0;
    const setDrag = (active) => {
      chatEl.classList.toggle('active-document-drop-target', Boolean(active));
    };
    chatEl.addEventListener('dragenter', (event) => {
      if (!event.dataTransfer || !hasFileDrag(event.dataTransfer)) return;
      event.preventDefault();
      dragDepth += 1;
      setDrag(true);
    });
    chatEl.addEventListener('dragover', (event) => {
      if (!event.dataTransfer || !hasFileDrag(event.dataTransfer)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
      setDrag(true);
    });
    chatEl.addEventListener('dragleave', (event) => {
      if (!event.dataTransfer || !hasFileDrag(event.dataTransfer)) return;
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) setDrag(false);
    });
    chatEl.addEventListener('drop', (event) => {
      if (!event.dataTransfer || !hasFileDrag(event.dataTransfer)) return;
      event.preventDefault();
      dragDepth = 0;
      setDrag(false);
      void uploadFiles(event.dataTransfer.files);
    });
  };

  bind();
  render();
  return Object.freeze({
    refresh,
    uploadFiles,
    removeDocument,
    getState: () => ({ ...state, items: [...state.items] }),
  });
}

function hasFileDrag(dataTransfer) {
  return Array.from(dataTransfer.types || []).includes('Files');
}

function compactDocumentMeta(item) {
  const parts = [];
  const ext = String(item.source_extension || '').replace(/^\./, '').toUpperCase();
  if (ext) parts.push(ext);
  const size = formatBytes(item.byte_size);
  if (size) parts.push(size);
  const chars = Number(item.text_chars || 0);
  if (chars > 0) parts.push(`${chars} caractères`);
  if (item.last_excluded_reason_code) {
    parts.push(uploadErrorLabel(item.last_excluded_reason_code));
  } else {
    parts.push('actif');
  }
  return parts.join(' · ');
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} ko`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} Mo`;
}

function uploadErrorLabel(reasonCode) {
  const labels = {
    document_type_unsupported: 'Format non pris en charge.',
    document_parse_error: 'Lecture du fichier impossible.',
    document_empty_text: 'Aucun texte lisible.',
    document_ocr_required: 'PDF scanné: OCR requis.',
    document_runtime_unavailable: 'Service documentaire indisponible.',
    document_too_large_for_turn: 'Trop gros pour ce tour.',
    document_file_missing: 'Fichier manquant.',
  };
  return labels[String(reasonCode || '')] || '';
}

const FridaActiveConversationDocuments = Object.freeze({
  ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS,
  createActiveDocumentController,
  compactDocumentMeta,
  formatBytes,
  uploadErrorLabel,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaActiveConversationDocuments;
}

if (typeof window !== 'undefined') {
  window.FridaActiveConversationDocuments = FridaActiveConversationDocuments;
}
