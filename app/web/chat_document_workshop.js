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

const DOCUMENT_WORKSHOP_PHASE_LABELS = Object.freeze({
  preparing: 'Préparation en cours', user_saved: 'Demande enregistrée',
  summary_ready: 'Contexte du dialogue préparé', identity_ready: 'Contexte du dialogue préparé',
  memory_ready: 'Contexte du dialogue préparé', stimmung_ready: 'Contexte du dialogue préparé',
  hermeneutic_ready: 'Contexte du dialogue préparé', dialogue_ready: 'Contexte du dialogue préparé',
  source_read: 'Source lue', sources_ready: 'Sources préparées', payload_prepared: 'Demande documentaire préparée',
  admitted: 'Demande documentaire admise', provider_content: 'Réception du document',
  provider_finished: 'Document reçu', canonical_validated: 'Document validé',
});
const DOCUMENT_WORKSHOP_LIMITATION_LABELS = Object.freeze({
  markdown_pagination_reader_dependent: 'La pagination dépend du lecteur Markdown.',
  markdown_style_reader_dependent: 'La mise en forme dépend du lecteur Markdown.',
  write_confirmation_unavailable: 'L’écriture du document est indisponible.',
  docx_pdf_unavailable: 'Les formats DOCX et PDF sont indisponibles.',
  update_unavailable: 'La modification d’un document existant est indisponible.',
});
const preparationLabel = record => record.phase
  ? `${DOCUMENT_WORKSHOP_PHASE_LABELS[record.phase] || 'Préparation en cours'} · ${record.received_content_codepoints || 0} caractères reçus`
  : 'Préparation demandée · relecture de l’état serveur';

function createDocumentWorkshopController({
  buttonEl, menuEl, inputEl, panelEl, statusEl, folderEl, bindFolderEl, sourceBarEl,
  targetEl, reloadEl, exitEl, browseEl, remoteEl, remoteStatusEl, remotePathEl,
  remoteListEl, remoteRootEl, remoteBackEl, remoteRefreshEl, documentObj, fetchFn, getThread,
  getFolders, getFiles, refreshFiles, createConversation, bindFolder, closeMobileTools,
  actionEl, dialogueButtonEl, getSourceFileIds = () => [], storageObj,
} = {}) {
  const doc = documentObj || document;
  const storage = storageObj || doc.defaultView.sessionStorage;
  const attemptKey = 'frida.document-workshop.attempt';
  const confirmationKey = 'frida.document-workshop.confirmations';
  let generation = 0;
  let visible = false;
  let busy = false;
  let context = null;
  let pendingScope = null;
  let remoteGeneration = 0;
  let remoteTrail = [];
  let listing = false;
  let adoptionInFlight = false;
  let action = null;
  let pollTimer = null;
  let cancellationInFlight = false;
  let submissionSettled = false;
  let actionReadSerial = 0;
  const cancellationGenerations = new Map();
  const cards = new Map();
  const executionReads = new Map();
  const receiptInventories = new Map();
  // Local evidence of an attempted click only; it grants no server authority.
  // Keep every consumed action through navigation/refresh, including a POST
  // that never reached the server. Reads may establish state, never replay it.
  const confirmations = new Map();
  let confirmationStorageAvailable = true;
  try {
    const records = JSON.parse(storage.getItem(confirmationKey));
    if (Array.isArray(records)) for (const record of records) {
      const keys = ['action_id', 'context_id', 'conversation_id', 'workspace_folder_id', 'revision_id', 'request_id', 'state'];
      if (record && keys.every(key => typeof record[key] === 'string' && record[key].length <= 128)
          && Object.keys(record).length === keys.length && ['attempted', 'unknown', 'observed'].includes(record.state)) {
        confirmations.set(record.action_id, record);
      }
    }
    storage.setItem(confirmationKey, JSON.stringify([...confirmations.values()]));
  } catch { confirmationStorageAvailable = false; }
  // A departed/uncertain adoption can still publish. Keep only the affected
  // folder IDs until an explicit read refreshes their existing shared inventory.
  const inventoriesToRefresh = new Set();
  const scope = thread => ({ conversation_id: thread?.conversation_id || thread?.id || null,
    workspace_folder_id: thread?.workspace_folder_id || null });
  const signature = value => JSON.stringify(value);
  const currentScope = () => scope(getThread());
  const current = (token, expected) => visible && token === generation
    && signature(currentScope()) === signature(expected);

  function saveAttempt(record = action) {
    if (!context) return;
    try {
      storage.setItem(attemptKey, JSON.stringify({ context_id: context.id,
        conversation_id: context.conversation_id, workspace_folder_id: context.workspace_folder_id,
        action_id: record?.id || null, state: record?.state || 'editing' }));
    } catch { /* A storage failure grants no server authority. */ }
  }
  function stopPolling() {
    if (pollTimer !== null) doc.defaultView.clearTimeout(pollTimer);
    pollTimer = null;
  }
  function saveConfirmations() {
    try { storage.setItem(confirmationKey, JSON.stringify([...confirmations.values()])); return true; }
    catch { confirmationStorageAvailable = false; return false; }
  }
  function validAction(record, expected, contextId, actionId) {
    return record && record.id === actionId && record.context_id === contextId
      && signature(scope(record)) === signature(expected)
      && ['preparing', 'pending', 'clarify', 'refuse', 'failed', 'cancelled', 'invalidated',
        'superseded', 'interrupted', 'lost', 'executing', 'succeeded', 'remote_uncertain', 'conflict'].includes(record.state);
  }
  function receiptLink(record) {
    const receipt = record.receipt;
    if (record.state !== 'succeeded' || !receipt || receipt.action_id !== record.id
        || receipt.conversation_id !== record.conversation_id || receipt.workspace_folder_id !== record.workspace_folder_id
        || receipt.revision_id !== record.revision_id || receipt.relative_path !== record.relative_path
        || receipt.publication_evidence !== 'historical' || typeof receipt.workspace_file_id !== 'string'
        || !receipt.workspace_file_id || receipt.workspace_file_id.length > 128) return null;
    const path = `/api/workspace-folders/${encodeURIComponent(receipt.workspace_folder_id)}/files/${encodeURIComponent(receipt.workspace_file_id)}/content`;
    return receipt.product_link === path ? path : null;
  }
  function renderPublished(record) {
    for (const [container, reference] of cards) {
      if (!container.isConnected) { cards.delete(container); continue; }
      if (reference.action_id === record.id) renderAction(container, record);
    }
    if (action?.id === record.id) render();
  }
  async function refreshReceiptInventory(record) {
    if (!receiptLink(record) || receiptInventories.has(record.id)) return;
    receiptInventories.set(record.id, 'refreshing');
    const folderId = record.workspace_folder_id;
    try {
      // Receipt identities own the refresh, never the thread at response time.
      const files = await refreshFiles(folderId, () => true, { preserveInventoryOnError: true });
      const complete = Array.isArray(files) && files.some(file => file.id === record.receipt.workspace_file_id);
      receiptInventories.set(record.id, complete ? 'updated' : 'unavailable');
    } catch { receiptInventories.set(record.id, 'unavailable'); }
    if (signature(currentScope()) === signature(scope(record))) {
      // A fresh context can have opened while this receipt's inventory GET was
      // pending. Reproject the shared inventory without selecting the receipt.
      if (visible && context?.state === 'editing' && context.workspace_folder_id === folderId) {
        populateTargets(folderId, context.target_file_id || '');
      }
      renderPublished(record);
    }
  }
  function watchExecution(record) {
    const existing = executionReads.get(record.id);
    if (record.state !== 'executing') {
      if (existing) doc.defaultView.clearTimeout(existing.timer);
      executionReads.delete(record.id); return;
    }
    if (existing) return;
    const expected = scope(record), cancellation = cancellationGenerations.get(record.id);
    const read = { timer: null };
    executionReads.set(record.id, read);
    const mayRead = () => executionReads.get(record.id) === read
      && signature(currentScope()) === signature(expected)
      && cancellation === cancellationGenerations.get(record.id)
      && ((visible && action?.id === record.id) || [...cards].some(([node, ref]) => node.isConnected && ref.action_id === record.id));
    read.timer = doc.defaultView.setTimeout(async () => {
      if (!mayRead()) { executionReads.delete(record.id); return; }
      try {
        const response = await fetchFn(`/api/document-workshop/actions/${encodeURIComponent(record.id)}`);
        const payload = await response.json();
        if (!mayRead()) return;
        if (!response.ok || payload?.ok !== true || !validAction(payload.action, expected, record.context_id, record.id)) return;
        executionReads.delete(record.id);
        publishAction(payload.action);
      } catch { /* Read unavailable: retain state and the explicit Reload action. */ }
      finally {
        if (executionReads.get(record.id) === read) {
          const continueReading = mayRead();
          executionReads.delete(record.id);
          if (continueReading) watchExecution(record);
        }
      }
    }, 750);
  }
  function renderAction(container, record) {
    container.replaceChildren();
    if (!record) return;
    const card = doc.createElement('section');
    card.className = 'document-action-card'; card.dataset.state = record.state;
    card.setAttribute('aria-label', 'Préparation documentaire');
    const status = doc.createElement('div'); status.setAttribute('role', 'status');
    status.textContent = record.state === 'preparing'
      ? preparationLabel(record)
      : record.state === 'pending' && confirmations.has(record.id)
        ? confirmations.get(record.id).state === 'attempted'
          ? 'Confirmation engagée · état à vérifier.'
          : 'Confirmation non établie côté serveur. Aucun nouvel envoi automatique.'
      : ({ pending: 'Document préparé', cancelled: 'Préparation annulée', failed: confirmations.has(record.id) || record.confirmation_turn_id ? 'Exécution documentaire échouée' : 'Préparation échouée',
        invalidated: 'Préparation invalidée', superseded: 'Préparation remplacée', interrupted: 'Tour interrompu',
        lost: 'Préparation perdue', clarify: 'Précision nécessaire', refuse: 'Préparation refusée',
        executing: 'Exécution engagée', conflict: 'Conflit : la cible a changé. Aucun changement concurrent n’a été écrasé.',
        succeeded: receiptLink(record) ? record.operation === 'update' ? 'Fichier modifié' : 'Document créé' : 'Publication documentaire à vérifier.',
        remote_uncertain: 'Résultat distant incertain. Aucun nouvel envoi automatique.' })[record.state];
    card.appendChild(status);
    const link = receiptLink(record);
    if (link) {
      const detail = doc.createElement('div'); detail.textContent = record.receipt.relative_path; card.appendChild(detail);
      const open = doc.createElement('a'); open.href = link; open.dataset.documentReceiptLink = '';
      open.textContent = 'Télécharger le document'; open.rel = 'noopener'; card.appendChild(open);
      if (receiptInventories.get(record.id) === 'unavailable') {
        const notice = doc.createElement('div'); notice.textContent = 'Inventaire non actualisé.'; card.appendChild(notice);
      }
    }
    if (['failed', 'remote_uncertain'].includes(record.state)) {
      const count = record.created_collections_count;
      let notice = '';
      if (Number.isInteger(count) && count > 0) {
        notice = `Création${count > 1 ? 's observées' : ' observée'} : ${count} sous-répertoire${count > 1 ? 's' : ''}. Des sous-répertoires peuvent subsister, éventuellement vides ; leur état reste à vérifier.`;
      } else if (record.state === 'remote_uncertain' && count == null && record.collections?.length) {
        notice = 'Des sous-répertoires peuvent subsister ; leur création n’a pas pu être vérifiée.';
      } else if (record.state === 'remote_uncertain' && count === 0 && record.collections?.length) {
        notice = 'Des sous-répertoires peuvent subsister ; leur état reste à vérifier.';
      }
      if (notice) {
        const detail = doc.createElement('div'); detail.textContent = notice; card.appendChild(detail);
      }
    }
    if (record.state === 'pending') {
      if (record.operation === 'update') {
        const detail = doc.createElement('div');
        detail.textContent = 'Modification de la cible sélectionnée · même nom et même identité. Une version modifiée provoque un conflit ; aucune restauration automatique. Nextcloud Versions reste l’autorité de récupération.';
        card.appendChild(detail);
      }
      const limitations = (record.limitations || []).map(code => DOCUMENT_WORKSHOP_LIMITATION_LABELS[code] || 'Limite documentaire non précisée.');
      for (const value of [record.name, record.format, record.relative_path,
        ...(record.collections || []).map(path => `Sous-répertoire susceptible d’être créé : ${path}`), ...limitations]) {
        if (typeof value !== 'string' || !value) continue;
        const detail = doc.createElement('div'); detail.textContent = value; card.appendChild(detail);
      }
      if (!confirmations.has(record.id)) {
        const available = record.capabilities?.confirm === true && confirmationStorageAvailable;
        const confirm = doc.createElement('button'); confirm.type = 'button'; confirm.disabled = !available;
        confirm.dataset.documentConfirm = ''; confirm.textContent = available ? record.operation === 'update' ? 'Modifier le fichier' : 'Confirmer la création' : 'Écriture indisponible';
        if (available) confirm.addEventListener('click', () => void confirmAction(record));
        card.appendChild(confirm);
      }
    }
    if (['preparing', 'pending', 'executing'].includes(record.state) && record.capabilities?.cancel === true) {
      const cancel = doc.createElement('button'); cancel.type = 'button'; cancel.dataset.documentCancel = '';
      cancel.textContent = 'Annuler la préparation'; cancel.disabled = cancellationInFlight;
      cancel.addEventListener('click', () => void cancelAction(record)); card.appendChild(cancel);
    }
    container.appendChild(card);
  }
  function publishAction(record) {
    const marker = confirmations.get(record.id);
    if (marker && record.state !== 'pending') {
      marker.state = 'observed'; saveConfirmations();
    }
    if (context?.id === record.context_id && action?.id === record.id) {
      action = record; saveAttempt();
      if (record.operation === 'update' && receiptLink(record)) {
        // The authorized SQL publication closes this old target context through
        // the real triggers. A new request needs an explicit new context.
        context = { ...context, state: 'invalidated', capabilities: { ...context.capabilities, prepare: false } };
      }
    }
    for (const [container, reference] of cards) {
      if (!container.isConnected) { cards.delete(container); continue; }
      if (reference.action_id === record.id) renderAction(container, record);
    }
    render();
    watchExecution(record);
    void refreshReceiptInventory(record);
  }
  async function confirmAction(record) {
    const expected = currentScope();
    if (record.state !== 'pending' || record.capabilities?.confirm !== true || !confirmationStorageAvailable || confirmations.has(record.id)
        || signature(scope(record)) !== signature(expected) || typeof record.revision_id !== 'string') return;
    const token = generation;
    const marker = { action_id: record.id, context_id: record.context_id, ...expected,
      revision_id: record.revision_id, request_id: doc.defaultView.crypto.randomUUID(), state: 'attempted' };
    confirmations.set(record.id, marker);
    const markerSaved = saveConfirmations();
    cancellationGenerations.set(record.id, (cancellationGenerations.get(record.id) || 0) + 1);
    const cancellation = cancellationGenerations.get(record.id);
    if (action?.id === record.id) {
      actionReadSerial += 1;
      stopPolling();
    }
    // Consume every card synchronously before fetch, including detached buttons
    // retained by a double-click/keyboard event and later pending re-renders.
    for (const [container, reference] of cards) {
      if (reference.action_id === record.id && container.isConnected) renderAction(container, record);
    }
    if (action?.id === record.id) render();
    if (!markerSaved) {
      marker.state = 'unknown';
      if (visible) render('Confirmation non envoyée : stockage de tentative indisponible.');
      return;
    }
    const stillHere = () => token === generation && signature(currentScope()) === signature(expected)
      && cancellation === cancellationGenerations.get(record.id);
    try {
      const response = await fetchFn(`/api/document-workshop/actions/${encodeURIComponent(record.id)}/confirm`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_id: marker.context_id, conversation_id: marker.conversation_id,
          workspace_folder_id: marker.workspace_folder_id, revision_id: marker.revision_id, request_id: marker.request_id }),
      });
      const payload = await response.json();
      if (!stillHere()) {
        // A late publication belongs to the confirmed origin. Refresh its
        // common inventory without rendering into the newly selected thread.
        if (response.ok && payload?.ok === true && validAction(payload.action, expected, record.context_id, record.id)) {
          void refreshReceiptInventory(payload.action);
        }
        return;
      }
      if (!response.ok || payload?.ok !== true || !validAction(payload.action, expected, record.context_id, record.id)) {
        throw new Error('document_confirmation_unavailable');
      }
      marker.state = payload.action.state === 'pending' ? 'unknown' : 'observed'; saveConfirmations();
      publishAction(payload.action);
    } catch {
      marker.state = 'unknown'; saveConfirmations();
      if (!stillHere()) return;
      // This read is deliberately independent of workshop visibility: a card
      // in the canonical transcript may be confirmed after the panel is closed.
      try {
        const response = await fetchFn(`/api/document-workshop/actions/${encodeURIComponent(record.id)}`);
        const payload = await response.json();
        if (stillHere() && response.ok && payload?.ok === true
            && validAction(payload.action, expected, record.context_id, record.id)) {
          publishAction(payload.action); return;
        }
      } catch { /* Unknown remains unknown; there is no POST retry. */ }
      if (stillHere()) {
        for (const [container, reference] of cards) {
          if (reference.action_id === record.id && container.isConnected) renderAction(container, record);
        }
        if (visible && action?.id === record.id) render('Confirmation non confirmée. Relisez l’état ; aucun nouvel envoi automatique.');
      }
    }
  }
  async function readAction() {
    if (!context || !action || !visible) return;
    stopPolling();
    const token = generation, expected = scope(context), contextId = context.id, actionId = action.id;
    const serial = ++actionReadSerial, cancellation = cancellationGenerations.get(actionId);
    const validRead = () => current(token, expected) && context?.id === contextId && action?.id === actionId
      && serial === actionReadSerial && cancellation === cancellationGenerations.get(actionId);
    try {
      const response = await fetchFn(`/api/document-workshop/actions/${encodeURIComponent(actionId)}`);
      const payload = await response.json();
      if (!validRead()) return;
      if (response.status === 404) {
        // The initial user/action transaction may not have committed yet.
        // A targeted context read observes it; neither read replays the turn.
        const contextResponse = await fetchFn(`/api/document-workshop/contexts/${encodeURIComponent(contextId)}`);
        const contextPayload = await contextResponse.json();
        if (!validRead()) return;
        if (!contextResponse.ok || contextPayload?.ok !== true) throw new Error('document_state_unavailable');
        const record = contextPayload.context?.preparation;
        if (validAction(record, expected, contextId, actionId)) publishAction(record);
        else if (submissionSettled) {
          saveAttempt({ id: actionId, state: 'unknown' });
          action = null;
          render('Préparation absente ou non confirmée. Relisez le contexte ; aucun tour ne sera rejoué.');
          return;
        }
      } else {
        if (!response.ok || payload?.ok !== true || !validAction(payload.action, expected, contextId, actionId)) {
          throw new Error('document_state_unavailable');
        }
        publishAction(payload.action);
      }
      if (action.state === 'preparing') pollTimer = doc.defaultView.setTimeout(() => void readAction(), 750);
    } catch {
      if (validRead()) {
        render('État de préparation indisponible. Relisez le contexte ; aucun tour ne sera rejoué.');
      }
    }
  }
  async function cancelAction(record) {
    if (cancellationInFlight || !['preparing', 'pending', 'executing'].includes(record.state)) return;
    const token = generation, expected = currentScope();
    cancellationGenerations.set(record.id, (cancellationGenerations.get(record.id) || 0) + 1);
    if (action?.id === record.id) stopPolling();
    let notice = '';
    cancellationInFlight = true;
    if (visible) render();
    try {
      const response = await fetchFn(`/api/document-workshop/actions/${encodeURIComponent(record.id)}/cancel`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_id: record.context_id }),
      });
      const payload = await response.json();
      if (token !== generation || signature(currentScope()) !== signature(expected)) return;
      if (!response.ok || payload?.ok !== true || !validAction(payload.action, expected, record.context_id, record.id)) {
        throw new Error('document_cancel_unavailable');
      }
      publishAction(payload.action);
    } catch {
      if (token === generation && signature(currentScope()) === signature(expected) && visible) {
        notice = 'Annulation non confirmée. Relisez l’état avant un nouvel essai explicite.';
      }
    } finally {
      cancellationInFlight = false;
      if (token === generation && signature(currentScope()) === signature(expected) && visible) render(notice);
    }
  }

  async function renderMessage(wrapper, messageRecord) {
    const reference = messageRecord?.meta?.document_workshop;
    if (!reference?.context_id || !reference.action_id || !wrapper) return;
    const token = generation, expected = currentScope();
    const cancellation = cancellationGenerations.get(reference.action_id);
    const validNode = () => token === generation && wrapper.isConnected
      && cancellation === cancellationGenerations.get(reference.action_id) && signature(currentScope()) === signature(expected);
    try {
      const response = await fetchFn(`/api/document-workshop/actions/${encodeURIComponent(reference.action_id)}`);
      const payload = await response.json();
      if (!validNode() || !response.ok || payload?.ok !== true
          || !validAction(payload.action, expected, reference.context_id, reference.action_id)) return;
      // The user and assistant carry the same references. Show one card, under
      // the assistant when present, or the durable user for an interrupted turn.
      for (const [container, existing] of cards) {
        if (!container.isConnected) { cards.delete(container); continue; }
        if (existing.action_id !== reference.action_id) continue;
        if (existing.role === 'assistant' || messageRecord.role !== 'assistant') return;
        container.remove(); cards.delete(container);
      }
      const container = doc.createElement('div');
      cards.set(container, { ...reference, role: messageRecord.role });
      wrapper.appendChild(container); renderAction(container, payload.action);
      watchExecution(payload.action);
      void refreshReceiptInventory(payload.action);
    } catch { /* No invented action, success or transcript after a failed reread. */ }
  }

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
    if (action) panelEl.dataset.actionState = action.state;
    else delete panelEl.dataset.actionState;
    statusEl.textContent = message || (context
      ? context.state !== 'editing' ? 'Cette préparation est terminée. Rouvrez l’atelier ou choisissez explicitement une cible pour une nouvelle demande. Votre brouillon est conservé.'
      : action?.state === 'preparing' ? preparationLabel(action)
      : context.capabilities.prepare === true
        ? context.capabilities.confirm === true
          ? context.capabilities.update === true
            ? 'Édition · Décrivez votre demande dans le compositeur. Markdown · création, copie ou modification de la cible sélectionnée après confirmation.'
            : 'Édition · Décrivez votre demande dans le compositeur. Markdown · création ou copie après confirmation.'
          : 'Édition · Décrivez votre demande dans le compositeur. Markdown · création ou copie ; écriture indisponible.'
        : 'Édition · La préparation documentaire est indisponible. Votre brouillon est conservé.'
      : busy ? 'Ouverture du contexte…' : 'Choisissez explicitement un répertoire pour cette conversation.');
    if (actionEl) renderAction(actionEl, action);
    if (dialogueButtonEl) {
      dialogueButtonEl.disabled = visible;
      dialogueButtonEl.title = visible ? 'Dialogue indisponible pendant l’atelier documentaire' : 'Ouvrir le mode Dialogue';
    }
    folderEl.disabled = busy || !currentScope().conversation_id || Boolean(currentScope().workspace_folder_id);
    bindFolderEl.hidden = Boolean(currentScope().workspace_folder_id);
    bindFolderEl.disabled = busy || !currentScope().conversation_id || !folderEl.value;
    contextControls();
    positionPanel();
  }
  function contextControls() {
    targetEl.disabled = busy || !context || adoptionInFlight || ['preparing', 'executing'].includes(action?.state);
    reloadEl.disabled = busy || !context || adoptionInFlight;
    browseEl.disabled = busy || !context || adoptionInFlight || listing || ['preparing', 'executing'].includes(action?.state);
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
    stopPolling();
    visible = false; busy = false; context = null; pendingScope = null; action = null;
    resetRemote();
    if (focus) { try { storage.removeItem(attemptKey); } catch {} }
    render('');
    if (focus) buttonEl.focus();
  }
  function scopeChanged() {
    if (!visible) { void restoreAttempt(); return; }
    const expected = pendingScope || (context && scope(context));
    if (expected && signature(currentScope()) !== signature(expected)) exit({ focus: false });
  }
  async function requestContext(expected, targetId, contextId = null) {
    const token = ++generation;
    stopPolling(); action = null;
    pendingScope = expected; busy = true; context = null;
    resetRemote();
    render();
    try {
      const response = await fetchFn(contextId
        ? `/api/document-workshop/contexts/${encodeURIComponent(contextId)}`
        : '/api/document-workshop/contexts', contextId ? {} : {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...expected, target_file_id: targetId || null }),
      });
      const payload = await response.json();
      if (!current(token, expected)) return;
      const record = payload?.context;
      if (!response.ok || payload.ok !== true || !record?.id || record.state !== 'editing'
          || ![true, false].includes(record.capabilities?.prepare) || signature(scope(record)) !== signature(expected)
          || (targetId !== undefined && (record.target_file_id || null) !== targetId) || (contextId && record.id !== contextId)) {
        throw new Error('document_context_unavailable');
      }
      context = record;
      if (record.preparation && validAction(record.preparation, expected, record.id, record.preparation.id)) action = record.preparation;
      busy = false; pendingScope = null;
      populateFolders(); populateTargets(record.workspace_folder_id, record.target_file_id || '');
      render();
      saveAttempt();
      if (action?.state === 'preparing') void readAction();
      if (action) { watchExecution(action); void refreshReceiptInventory(action); }
    } catch {
      if (!current(token, expected)) return;
      busy = false; context = null; pendingScope = expected;
      render('Impossible d’ouvrir ce contexte documentaire. Retournez au chat pour réessayer.');
    }
  }
  async function restoreAttempt() {
    let marker;
    try { marker = JSON.parse(storage.getItem(attemptKey)); } catch { return; }
    if (!marker?.context_id || signature(scope(marker)) !== signature(currentScope())) return;
    visible = true;
    await requestContext(currentScope(), undefined, marker.context_id);
    if (context && !action && marker.action_id && ['preparing', 'pending', 'unknown'].includes(marker.state)) {
      submissionSettled = marker.state === 'unknown';
      action = { id: marker.action_id, context_id: context.id, ...scope(context), state: 'preparing',
        capabilities: { confirm: false, cancel: true } };
      render(); void readAction();
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
        const files = await refreshFiles(expected.workspace_folder_id, () => remoteCurrent(token, expected, contextId, navigation));
        if (!remoteCurrent(token, expected, contextId, navigation)) return;
        if (files === null) throw new Error('workspace_inventory_not_published');
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
      const files = await refreshFiles(expected.workspace_folder_id, isCurrent);
      if (!isCurrent()) return;
      if (files === null) throw new Error('workspace_inventory_not_published');
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
    if (action && receiptInventories.get(action.id) === 'unavailable') receiptInventories.delete(action.id);
    if (context && !busy) void requestContext(scope(context), context.target_file_id || null, context.id);
  });
  exitEl.addEventListener('click', () => exit());
  return Object.freeze({
    scopeChanged,
    renderMessage,
    blocksSubmission: () => visible,
    prepareSubmission({ inputMode, incompatibleModes = false } = {}) {
      if (!visible) return null;
      if (context && context.state !== 'editing') {
        return { ok: false, reason: 'document_context_scope_changed',
          message: 'Rouvrez l’atelier ou choisissez explicitement une cible pour une nouvelle demande. Votre brouillon est conservé.' };
      }
      if (inputMode === 'dialogue' || incompatibleModes) {
        return { ok: false, reason: 'document_mode_incompatible',
          message: 'Mode incompatible : désactivez les autres outils pour préparer le document. Votre brouillon est conservé.' };
      }
      if (busy || adoptionInFlight || !context || context.capabilities.prepare !== true || ['preparing', 'executing'].includes(action?.state)) {
        return { ok: false, reason: 'document_preparation_unavailable' };
      }
      if (context.target_file_id && context.capabilities.update !== true) {
        return { ok: false, reason: 'document_update_unavailable',
          message: 'La modification d’une cible est indisponible. Choisissez « Nouveau document » ; votre brouillon est conservé.' };
      }
      return { ok: true, contextId: context.id, sourceFileIds: getSourceFileIds(context.conversation_id) };
    },
    beginSubmission(clientTurnId) {
      submissionSettled = false;
      action = { id: clientTurnId, context_id: context.id, ...scope(context), state: 'preparing',
        capabilities: { confirm: false, cancel: true } };
      saveAttempt(); render(); void readAction();
    },
    finishSubmission(clientTurnId) {
      if (action?.id !== clientTurnId) return Promise.resolve();
      submissionSettled = true;
      return readAction();
    },
    refuseSubmission: result => render(result?.message || 'La préparation documentaire est indisponible. Votre brouillon est conservé ; « Retour au chat » permet l’envoi normal.'),
  });
}

const FridaDocumentWorkshop = Object.freeze({ createDocumentWorkshopController });
if (typeof module !== 'undefined' && module.exports) module.exports = FridaDocumentWorkshop;
if (typeof window !== 'undefined') window.FridaDocumentWorkshop = FridaDocumentWorkshop;
