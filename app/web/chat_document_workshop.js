'use strict';

function createDocumentWorkshopController({
  buttonEl, menuEl, inputEl, panelEl, statusEl, folderEl, bindFolderEl, sourceBarEl,
  targetEl, reloadEl, exitEl, documentObj, fetchFn, getThread,
  getFolders, getFiles, createConversation, bindFolder, closeMobileTools,
} = {}) {
  const doc = documentObj || document;
  let generation = 0;
  let visible = false;
  let busy = false;
  let context = null;
  let pendingScope = null;
  const scope = thread => ({ conversation_id: thread?.conversation_id || thread?.id || null,
    workspace_folder_id: thread?.workspace_folder_id || null });
  const signature = value => JSON.stringify(value);
  const currentScope = () => scope(getThread());
  const current = (token, expected) => visible && token === generation
    && signature(currentScope()) === signature(expected);

  function closeMenu({ restoreFocus = false } = {}) {
    menuEl.hidden = true;
    buttonEl.setAttribute('aria-expanded', 'false');
    if (restoreFocus) buttonEl.focus();
  }
  function openMenu() {
    closeMobileTools();
    menuEl.hidden = false;
    buttonEl.setAttribute('aria-expanded', 'true');
    menuEl.querySelector('button').focus();
  }
  function positionPanel() {
    const sourceHeight = sourceBarEl && !sourceBarEl.hidden
      && doc.defaultView.getComputedStyle(sourceBarEl).position === 'absolute'
      ? sourceBarEl.getBoundingClientRect().height + 8 : 0;
    panelEl.style.bottom = `calc(100% + ${sourceHeight + 8}px)`;
  }
  function render(message = '') {
    panelEl.hidden = !visible;
    if (context) panelEl.dataset.state = context.state;
    else panelEl.removeAttribute('data-state');
    statusEl.textContent = message || (context
      ? 'Édition · La préparation documentaire est indisponible. Votre brouillon est conservé.'
      : busy ? 'Ouverture du contexte…' : 'Choisissez explicitement un répertoire pour cette conversation.');
    folderEl.disabled = busy || !currentScope().conversation_id || Boolean(currentScope().workspace_folder_id);
    bindFolderEl.hidden = Boolean(currentScope().workspace_folder_id);
    bindFolderEl.disabled = busy || !currentScope().conversation_id || !folderEl.value;
    targetEl.disabled = busy || !context;
    reloadEl.disabled = busy || !context;
    positionPanel();
  }
  function populateFolders() {
    folderEl.replaceChildren();
    folderEl.appendChild(new Option('Choisir un répertoire existant', ''));
    for (const folder of getFolders()) folderEl.appendChild(new Option(folder.display_name, folder.id));
    folderEl.value = currentScope().workspace_folder_id || '';
  }
  function populateTargets(folderId, selected = '') {
    targetEl.replaceChildren();
    targetEl.appendChild(new Option('Nouveau document · aucune cible', ''));
    for (const file of getFiles(folderId)) {
      if (file.status === 'active' && file.content_kind === 'document' && file.media_kind === 'text'
          && ['.md', '.docx'].includes(file.source_extension)
          && file.document_nextcloud_sync_state === 'linked') {
        targetEl.appendChild(new Option(file.display_name, file.id));
      }
    }
    targetEl.value = selected;
  }
  function exit({ focus = true } = {}) {
    generation += 1;
    visible = false; busy = false; context = null; pendingScope = null;
    render('');
    if (focus) buttonEl.focus();
  }
  function scopeChanged() {
    if (!visible) return;
    const expected = pendingScope || (context && scope(context));
    if (expected && signature(currentScope()) !== signature(expected)) exit({ focus: false });
  }
  async function requestContext(expected, targetId = null, contextId = null) {
    const token = ++generation;
    pendingScope = expected; busy = true; context = null;
    render();
    try {
      const response = await fetchFn(contextId
        ? `/api/document-workshop/contexts/${encodeURIComponent(contextId)}`
        : '/api/document-workshop/contexts', contextId ? {} : {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...expected, target_file_id: targetId }),
      });
      const payload = await response.json();
      if (!current(token, expected)) return;
      const record = payload?.context;
      if (!response.ok || payload.ok !== true || !record?.id || record.state !== 'editing'
          || record.capabilities?.prepare !== false || signature(scope(record)) !== signature(expected)
          || (record.target_file_id || null) !== targetId || (contextId && record.id !== contextId)) {
        throw new Error('document_context_unavailable');
      }
      context = record;
      busy = false; pendingScope = null;
      populateFolders(); populateTargets(record.workspace_folder_id, record.target_file_id || '');
      render();
    } catch {
      if (!current(token, expected)) return;
      busy = false; context = null; pendingScope = expected;
      render('Impossible d’ouvrir ce contexte documentaire. Retournez au chat pour réessayer.');
    }
  }
  async function open() {
    closeMenu();
    if (visible) { statusEl.focus(); return; }
    visible = true; busy = true; context = null;
    const token = ++generation;
    let expected = currentScope();
    pendingScope = expected;
    populateFolders(); populateTargets(expected.workspace_folder_id);
    render();
    if (!expected.conversation_id) {
      const created = await createConversation(thread => {
        if (!current(token, expected)) return false;
        // The existing creation path will select precisely this identity. Its
        // synchronous selection callback must not invalidate its own opening.
        expected = scope(thread); pendingScope = expected;
        return true;
      });
      if (!created || !current(token, expected) || scope(created).conversation_id !== expected.conversation_id) {
        if (visible && token === generation) {
          busy = false;
          render('Impossible de créer la conversation. Aucun contexte n’a été ouvert.');
        }
        return;
      }
    }
    if (!current(token, expected)) return;
    busy = false;
    populateFolders();
    if (!expected.workspace_folder_id) { render(); folderEl.focus(); return; }
    await requestContext(expected);
  }
  async function associateFolder() {
    if (busy || !visible || !currentScope().conversation_id || currentScope().workspace_folder_id || !folderEl.value) return;
    const expected = currentScope(), folderId = folderEl.value, token = ++generation;
    pendingScope = expected; busy = true; render();
    try {
      const updated = await bindFolder(expected.conversation_id, folderId, () => current(token, expected));
      if (!visible || token !== generation) return;
      if (!updated || scope(updated).conversation_id !== expected.conversation_id
          || scope(updated).workspace_folder_id !== folderId
          || signature(currentScope()) !== signature(scope(updated))) throw new Error('folder_association_failed');
      pendingScope = currentScope();
      await requestContext(pendingScope);
    } catch {
      if (!visible || token !== generation) return;
      busy = false; context = null;
      render('Impossible d’associer ce répertoire. Aucun contexte n’a été ouvert.');
    }
  }
  if (sourceBarEl && typeof ResizeObserver !== 'undefined') new ResizeObserver(positionPanel).observe(sourceBarEl);
  buttonEl.addEventListener('click', () => menuEl.hidden ? openMenu() : closeMenu({ restoreFocus: true }));
  menuEl.querySelector('[data-file-action="upload"]').addEventListener('click', () => {
    closeMenu({ restoreFocus: true }); inputEl.click();
  });
  menuEl.querySelector('[data-file-action="workshop"]').addEventListener('click', () => void open());
  menuEl.addEventListener('keydown', event => {
    const buttons = Array.from(menuEl.querySelectorAll('button'));
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const index = buttons.indexOf(doc.activeElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
        : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
      buttons[next].focus();
    } else if (event.key === 'Tab') closeMenu();
  });
  doc.addEventListener('keydown', event => { if (event.key === 'Escape' && !menuEl.hidden) closeMenu({ restoreFocus: true }); });
  doc.addEventListener('click', event => {
    if (!menuEl.hidden && !menuEl.contains(event.target) && !buttonEl.contains(event.target)) closeMenu();
  });
  folderEl.addEventListener('change', () => render());
  bindFolderEl.addEventListener('click', () => void associateFolder());
  targetEl.addEventListener('change', () => {
    if (context && !busy) void requestContext(scope(context), targetEl.value || null);
  });
  reloadEl.addEventListener('click', () => {
    if (context && !busy) void requestContext(scope(context), context.target_file_id || null, context.id);
  });
  exitEl.addEventListener('click', () => exit());
  return Object.freeze({
    scopeChanged,
    blocksSubmission: () => visible,
    refuseSubmission: () => render('La préparation documentaire est indisponible. Votre brouillon est conservé ; « Retour au chat » permet l’envoi normal.'),
  });
}

const FridaDocumentWorkshop = Object.freeze({ createDocumentWorkshopController });
if (typeof module !== 'undefined' && module.exports) module.exports = FridaDocumentWorkshop;
if (typeof window !== 'undefined') window.FridaDocumentWorkshop = FridaDocumentWorkshop;
