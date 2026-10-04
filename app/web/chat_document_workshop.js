'use strict';

const DOCUMENT_WORKSHOP_REMOTE_MESSAGES = Object.freeze({
  document_remote_identity_invalid: 'Identité distante absente ou non vérifiable. Cette ressource ne peut pas être adoptée.',
  document_remote_version_invalid: 'Version distante absente ou non vérifiable. Ce fichier ne peut pas être adopté.',
  document_remote_size_invalid: 'Taille du fichier absente ou invalide. Ce fichier ne peut pas être adopté.',
  document_type_unsupported: 'Format de fichier non pris en charge. Choisissez un autre fichier.',
  document_source_limit: 'Le fichier ou son contenu extrait dépasse les limites de lecture. Choisissez une source moins volumineuse.',
  document_remote_response_limit: 'La réponse distante dépasse les limites de lecture (taille ou nombre d’éléments). Aucun résultat partiel n’est utilisé. Choisissez une collection ou une source moins volumineuse.',
  document_ocr_required: 'Ce document nécessite une reconnaissance de texte (OCR) avant son adoption.',
  document_extraction_incomplete: 'Le texte ne peut pas être extrait intégralement. Choisissez une version dont tout le texte est lisible.',
  document_archive_invalid: 'La structure du document est invalide ou non prise en charge. Choisissez une autre version du fichier.',
  document_parse_error: 'Le fichier ne peut pas être lu dans ce format. Vérifiez le fichier ou choisissez une autre source.',
  document_empty_text: 'Aucun texte lisible n’a été trouvé dans ce fichier.',
  document_remote_incompatible: 'Les informations distantes ne permettent pas une lecture sûre de cette ressource.',
  document_path_invalid: 'Le chemin ne respecte pas les règles du répertoire Documents. Cette ressource ne peut pas être utilisée.',
  document_path_segment_limit: 'Un nom dépasse la longueur autorisée. Choisissez une autre ressource.',
  document_path_depth_limit: 'Le chemin dépasse le nombre de sous-répertoires autorisé. Choisissez une autre ressource.',
  document_path_byte_limit: 'Le chemin complet dépasse la longueur autorisée. Choisissez une autre ressource.',
  document_collection: 'Un répertoire peut être parcouru, mais ne peut pas être adopté comme fichier.',
  document_local_collision: 'Un fichier local occupe déjà ce chemin. Aucun remplacement n’est effectué. Choisissez une autre ressource.',
  document_remote_changed: 'Le fichier ou le répertoire a changé depuis sa lecture. Actualisez la collection, puis sélectionnez de nouveau la ressource.',
  document_remote_missing: 'La ressource a disparu ou a été déplacée. Actualisez la collection et choisissez explicitement une ressource.',
  document_reference_invalid: 'Cette référence de document n’est plus valide. Actualisez la collection, puis sélectionnez de nouveau la ressource.',
  document_remote_unavailable: 'La lecture distante est actuellement indisponible. Vous pouvez réessayer plus tard par une action explicite.',
  document_runtime_unavailable: 'La lecture de ce format est actuellement indisponible. Vous pouvez réessayer plus tard par une action explicite.',
  document_source_processing_failed: 'La lecture complète du document a échoué. Aucune adoption n’est confirmée.',
  document_adoption_storage_unavailable: 'L’adoption n’a pas pu être enregistrée. Actualisez la collection avant un nouvel essai explicite.',
  document_context_scope_changed: 'Le contexte documentaire a changé. Retournez au chat puis rouvrez l’atelier.',
  document_context_scope_mismatch: 'Le contexte documentaire a changé. Retournez au chat puis rouvrez l’atelier.',
  document_adoption_commit_unknown: 'Résultat de l’adoption incertain. Aucun nouvel essai automatique. Actualiser la collection pour vérifier son état.',
});

function createDocumentWorkshopController({
  buttonEl, menuEl, inputEl, panelEl, statusEl, folderEl, bindFolderEl, sourceBarEl,
  targetEl, reloadEl, exitEl, browseEl, remoteEl, remoteStatusEl, remotePathEl,
  remoteListEl, remoteRootEl, remoteBackEl, remoteRefreshEl, documentObj, fetchFn, getThread,
  getFolders, getFiles, refreshFiles, createConversation, bindFolder, closeMobileTools,
} = {}) {
  const doc = documentObj || document;
  let generation = 0;
  let visible = false;
  let busy = false;
  let context = null;
  let pendingScope = null;
  let remoteGeneration = 0;
  let remoteTrail = [];
  let listing = false;
  let adoptionInFlight = false;
  // A departed/uncertain adoption can still publish. Keep only the affected
  // folder IDs until an explicit read refreshes their existing shared inventory.
  const inventoriesToRefresh = new Set();
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
    contextControls();
    positionPanel();
  }
  function contextControls() {
    targetEl.disabled = busy || !context || adoptionInFlight;
    reloadEl.disabled = busy || !context || adoptionInFlight;
    browseEl.disabled = busy || !context || adoptionInFlight || listing;
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
        targetEl.appendChild(new Option(file.document_relative_path || file.display_name, file.id));
      }
    }
    targetEl.value = selected;
  }
  function exit({ focus = true } = {}) {
    generation += 1;
    visible = false; busy = false; context = null; pendingScope = null;
    resetRemote();
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
    resetRemote();
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

  function resetRemote() {
    remoteGeneration += 1;
    remoteTrail = []; listing = false;
    remoteEl.hidden = true;
    remoteListEl.replaceChildren(); remotePathEl.textContent = ''; remoteStatusEl.textContent = '';
  }
  function remoteCurrent(token, expected, contextId, navigation) {
    return current(token, expected) && context?.id === contextId && navigation === remoteGeneration;
  }
  function remoteControls() {
    remoteRootEl.disabled = adoptionInFlight;
    remoteBackEl.disabled = adoptionInFlight || remoteTrail.length < 2;
    remoteRefreshEl.disabled = adoptionInFlight || listing;
    for (const button of remoteListEl.querySelectorAll('button')) button.disabled = adoptionInFlight || listing;
    contextControls();
  }
  function remoteReasonMessage(reason, fallback) {
    return typeof reason === 'string' && Object.hasOwn(DOCUMENT_WORKSHOP_REMOTE_MESSAGES, reason)
      ? DOCUMENT_WORKSHOP_REMOTE_MESSAGES[reason] : fallback;
  }
  function remoteRow(item) {
    const row = doc.createElement('li');
    const path = doc.createElement('span');
    path.className = 'document-remote-resource'; path.textContent = item.relative_path;
    row.appendChild(path);
    const label = doc.createElement('span');
    label.textContent = ({ already_linked: 'Déjà lié', adoptable: 'Adoptable',
      collision: 'Collision locale', incompatible: 'Incompatible' })[item.category] || 'Incompatible';
    const navigable = item.is_collection === true && item.reason_code === 'document_collection';
    if (navigable) label.textContent = 'Répertoire';
    row.appendChild(label);
    if (!navigable && ['incompatible', 'collision'].includes(item.category)) {
      const explanation = doc.createElement('span');
      explanation.textContent = remoteReasonMessage(item.reason_code,
        'Cette ressource ne peut pas être adoptée. Choisissez un autre fichier.');
      row.appendChild(explanation);
    }
    if (navigable || (item.is_collection === false && ['adoptable', 'already_linked'].includes(item.category))) {
      const button = doc.createElement('button'); button.type = 'button';
      const action = navigable ? 'Ouvrir' : item.category === 'already_linked' ? 'Actualiser l’adoption' : 'Adopter';
      button.textContent = action; button.setAttribute('aria-label', `${action} ${item.name}`);
      button.addEventListener('click', () => {
        if (adoptionInFlight || listing) return;
        if (navigable) void listRemote([...remoteTrail, { reference: item.reference, relative_path: item.relative_path }]);
        else void adoptRemote(item, row);
      });
      row.appendChild(button);
    }
    return row;
  }
  async function listRemote(trail = []) {
    if (!context || busy || adoptionInFlight) return;
    const token = generation, expected = scope(context), contextId = context.id;
    const navigation = ++remoteGeneration;
    listing = true; remoteEl.hidden = false; remoteListEl.replaceChildren();
    remoteStatusEl.textContent = 'Lecture de la collection…'; remoteControls();
    const query = new URLSearchParams({ context_id: contextId });
    if (trail.length) query.set('collection_ref', trail.at(-1).reference);
    let failureReason = null;
    try {
      const response = await fetchFn(`/api/workspace-folders/${encodeURIComponent(expected.workspace_folder_id)}/documents/remote?${query}`);
      const payload = await response.json();
      if (!remoteCurrent(token, expected, contextId, navigation)) return;
      if (!response.ok || payload?.ok !== true) failureReason = payload?.reason_code;
      if (!response.ok || payload.ok !== true || payload.complete !== true
          || payload.workspace_folder_id !== expected.workspace_folder_id
          || typeof payload.collection?.reference !== 'string' || typeof payload.collection?.relative_path !== 'string'
          || !Array.isArray(payload.items) || payload.items.some(item => !item || typeof item.reference !== 'string'
            || typeof item.name !== 'string' || typeof item.relative_path !== 'string')) throw new Error('remote_list_unavailable');
      // A user-requested refresh can reconcile an uncertain publication or a
      // failed inventory read; it never replays the adoption POST.
      if (inventoriesToRefresh.has(expected.workspace_folder_id)) {
        await refreshFiles(expected.workspace_folder_id, () => remoteCurrent(token, expected, contextId, navigation));
        if (!remoteCurrent(token, expected, contextId, navigation)) return;
        inventoriesToRefresh.delete(expected.workspace_folder_id);
        populateTargets(expected.workspace_folder_id, context.target_file_id || '');
        if (context.target_file_id) {
          await requestContext(expected, context.target_file_id, contextId);
          return;
        }
      }
      remoteTrail = [...trail.slice(0, -1), payload.collection];
      remotePathEl.textContent = payload.collection.relative_path;
      remoteListEl.replaceChildren(...payload.items.map(remoteRow));
      remoteStatusEl.textContent = payload.items.length ? 'Collection complète. Adoptez explicitement un fichier pour l’ajouter à l’inventaire.' : 'Collection complète, aucun document.';
    } catch {
      if (!remoteCurrent(token, expected, contextId, navigation)) return;
      remoteListEl.replaceChildren();
      remoteStatusEl.textContent = remoteReasonMessage(failureReason, inventoriesToRefresh.has(expected.workspace_folder_id)
        ? 'Impossible d’actualiser la liste complète et l’inventaire. Actualiser pour réessayer, sans rejouer l’adoption.'
        : 'Impossible d’obtenir la liste complète : collection indisponible ou limite de lecture atteinte. Actualiser pour réessayer.');
    } finally {
      if (remoteCurrent(token, expected, contextId, navigation)) { listing = false; remoteControls(); }
    }
  }
  async function adoptRemote(item, row) {
    if (!context || busy || listing || adoptionInFlight) return;
    const token = generation, expected = scope(context), contextId = context.id, navigation = remoteGeneration;
    const targetId = context.target_file_id || null;
    const isCurrent = () => remoteCurrent(token, expected, contextId, navigation);
    adoptionInFlight = true; inventoriesToRefresh.add(expected.workspace_folder_id);
    remoteStatusEl.textContent = 'Lecture et adoption du fichier…'; remoteControls();
    let published = false;
    try {
      const response = await fetchFn(`/api/workspace-folders/${encodeURIComponent(expected.workspace_folder_id)}/documents/adopt`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_id: contextId, resource_ref: item.reference }),
      });
      const payload = await response.json();
      if (!isCurrent()) return;
      if (!response.ok || payload.ok !== true || payload.workspace_folder_id !== expected.workspace_folder_id || !payload.workspace_file_id) {
        remoteListEl.replaceChildren();
        remoteStatusEl.textContent = remoteReasonMessage(payload?.reason_code,
          'Adoption non confirmée. Actualiser la collection avant tout nouvel essai explicite.');
        return;
      }
      published = true;
      await refreshFiles(expected.workspace_folder_id, isCurrent);
      if (!isCurrent()) return;
      inventoriesToRefresh.delete(expected.workspace_folder_id);
      populateTargets(expected.workspace_folder_id, targetId || '');
      remoteStatusEl.textContent = 'Adoption enregistrée. Inventaire actualisé ; aucune source ni cible sélectionnée automatiquement.';
      row.replaceWith(remoteRow({ ...item, category: 'already_linked', workspace_file_id: payload.workspace_file_id }));
      // An existing target keeps its identity, but its frozen remote path may
      // have changed. Only the server context reread can validate it again.
      if (targetId) await requestContext(expected, targetId, contextId);
    } catch {
      if (!isCurrent()) return;
      remoteListEl.replaceChildren();
      remoteStatusEl.textContent = published
        ? 'Adoption enregistrée, inventaire indisponible. Actualiser la collection ; aucune adoption ne sera rejouée automatiquement.'
        : 'Résultat de l’adoption incertain. Actualiser la collection ; aucun nouvel essai automatique.';
    } finally {
      adoptionInFlight = false;
      if (visible) remoteControls();
    }
  }
  browseEl.addEventListener('click', () => void listRemote());
  remoteRootEl.addEventListener('click', () => void listRemote());
  remoteBackEl.addEventListener('click', () => { if (remoteTrail.length > 1) void listRemote(remoteTrail.slice(0, -1)); });
  remoteRefreshEl.addEventListener('click', () => void listRemote(remoteTrail));
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
