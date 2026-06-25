'use strict';

const NOTES_STORAGE_KEY = 'frida.notesMode';

function normalizeNotesEnabled(value) {
  if (value === true) return true;
  if (value === false || value == null) return false;
  const normalized = String(value || '').trim().toLowerCase();
  return ['1', 'true', 'yes', 'on', 'enabled', 'active'].includes(normalized);
}

function normalizeNoteId(value) {
  return String(value || '').trim();
}

function normalizeWorkspaceNoteItem(item) {
  const source = item && typeof item === 'object' ? item : {};
  const user = source.note_v1_user && typeof source.note_v1_user === 'object'
    ? source.note_v1_user
    : source;
  const noteId = normalizeNoteId(user.note_id || user.id);
  if (!noteId) return null;
  return {
    id: noteId,
    note_id: noteId,
    note_ref: String(user.note_ref || ''),
    workspace_folder_id: String(user.workspace_folder_id || ''),
    title: String(user.title || 'Note'),
    status: String(user.status || ''),
    status_label: String(user.status_label || user.status || ''),
    sync_label: String(user.sync_label || user.nextcloud_sync_state || ''),
    markdown_char_count: Number(user.markdown_char_count || 0),
    updated_at: user.updated_at || user.created_at || null,
    created_at: user.created_at || null,
  };
}

function normalizeWorkspaceNotesPayload(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items.map(normalizeWorkspaceNoteItem).filter(Boolean);
}

function canLoadWorkspaceNotes(folder) {
  if (!folder || folder.deleted_at) return false;
  return String(folder.nextcloud_sync_state || '').trim() === 'linked';
}

function buildWorkspaceNotesListPath(folderId) {
  return `/api/workspace-folders/${encodeURIComponent(String(folderId || ''))}/notes`;
}

function buildWorkspaceNoteLookupPath(folderId, noteId) {
  return `${buildWorkspaceNotesListPath(folderId)}/${encodeURIComponent(String(noteId || ''))}`;
}

function buildWorkspaceNotePreparePath(folderId, noteId) {
  return `${buildWorkspaceNoteLookupPath(folderId, noteId)}/prepare`;
}

function buildNotesChatPayload({ active = false, selectedNoteId = '', selectedFolderId = '', workspaceFolderId = '' } = {}) {
  const noteId = normalizeNoteId(selectedNoteId);
  const expectedFolderId = String(workspaceFolderId || '').trim();
  const selectionFolderId = String(selectedFolderId || '').trim();
  if (!normalizeNotesEnabled(active)) {
    return { workspace_notes_mode: false };
  }
  const payload = { workspace_notes_mode: true };
  if (noteId && (!expectedFolderId || expectedFolderId === selectionFolderId)) {
    payload.workspace_note_id = noteId;
  }
  return payload;
}

function createNotesModeController({
  buttonEl,
  storage,
  storageKey = NOTES_STORAGE_KEY,
  onActiveChange,
} = {}) {
  const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
  const state = {
    active: false,
    selectedNoteId: '',
    selectedFolderId: '',
    selectedTitle: '',
  };

  try {
    state.active = normalizeNotesEnabled(store ? store.getItem(storageKey) : false);
  } catch {
    state.active = false;
  }

  const persist = () => {
    if (!store) return;
    try {
      store.setItem(storageKey, state.active ? '1' : '0');
    } catch {}
  };

  const emitActiveChange = () => {
    if (typeof onActiveChange === 'function') {
      onActiveChange(state.active);
    }
  };

  const render = () => {
    if (!buttonEl) return;
    const title = state.selectedTitle ? `Notes : ${state.selectedTitle}` : 'Notes';
    buttonEl.classList.toggle('active', state.active);
    buttonEl.setAttribute('aria-pressed', state.active ? 'true' : 'false');
    buttonEl.title = state.active ? `${title} : actif` : 'Notes : désactivé';
    buttonEl.setAttribute('aria-label', state.active ? 'Désactiver Notes' : 'Activer Notes');
  };

  const setActive = (active) => {
    const next = normalizeNotesEnabled(active);
    const changed = state.active !== next;
    state.active = next;
    persist();
    render();
    if (changed) emitActiveChange();
  };

  const setSelectedNote = (note, folder) => {
    const normalized = normalizeWorkspaceNoteItem(note);
    if (!normalized) {
      state.selectedNoteId = '';
      state.selectedFolderId = '';
      state.selectedTitle = '';
      render();
      return;
    }
    state.selectedNoteId = normalized.id;
    state.selectedFolderId = String(folder?.id || normalized.workspace_folder_id || '').trim();
    state.selectedTitle = normalized.title;
    setActive(true);
    render();
  };

  const clearSelection = () => {
    state.selectedNoteId = '';
    state.selectedFolderId = '';
    state.selectedTitle = '';
    render();
  };

  const toggle = () => setActive(!state.active);

  if (buttonEl) {
    buttonEl.addEventListener('click', toggle);
  }

  render();

  return Object.freeze({
    state,
    isActive: () => state.active,
    setActive,
    toggle,
    setSelectedNote,
    clearSelection,
    getSelectedNoteId: () => state.selectedNoteId,
    getSelectedFolderId: () => state.selectedFolderId,
    getPayload: ({ workspaceFolderId = '' } = {}) => buildNotesChatPayload({
      active: state.active,
      selectedNoteId: state.selectedNoteId,
      selectedFolderId: state.selectedFolderId,
      workspaceFolderId,
    }),
  });
}

const FridaNotesMode = Object.freeze({
  NOTES_STORAGE_KEY,
  normalizeNotesEnabled,
  normalizeNoteId,
  normalizeWorkspaceNoteItem,
  normalizeWorkspaceNotesPayload,
  canLoadWorkspaceNotes,
  buildWorkspaceNotesListPath,
  buildWorkspaceNoteLookupPath,
  buildWorkspaceNotePreparePath,
  buildNotesChatPayload,
  createNotesModeController,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaNotesMode;
}

if (typeof window !== 'undefined') {
  window.FridaNotesMode = FridaNotesMode;
}
