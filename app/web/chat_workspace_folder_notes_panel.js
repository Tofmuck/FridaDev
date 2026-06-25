'use strict';

const NotesMode = (
  typeof window !== 'undefined' && window.FridaNotesMode
    ? window.FridaNotesMode
    : (typeof require !== 'undefined' ? require('./chat_notes_mode.js') : null)
);

function noteMeta(note) {
  const bits = [];
  if (note.sync_label) bits.push(note.sync_label);
  if (Number.isFinite(note.markdown_char_count) && note.markdown_char_count > 0) {
    bits.push(`${note.markdown_char_count} car.`);
  }
  if (note.updated_at) bits.push(String(note.updated_at).slice(0, 10));
  return bits.join(' · ');
}

function createWorkspaceFolderNotesPanelRenderer({
  threadsUl,
  getWorkspaceNotes,
  getWorkspaceNotesStatus,
  refreshWorkspaceNotes,
  createWorkspaceNoteOnServer,
  prepareWorkspaceNoteOnServer,
  getCurrentThread,
  notesModeController,
  renderThreads,
  setThreadStatus,
  consoleObj,
} = {}) {
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });
  const status = (message, isError = false) => {
    if (typeof setThreadStatus === 'function') setThreadStatus(message, isError);
  };

  const warn = (message, err) => {
    const reason = err?.payload?.reason_code || err?.payload?.error || err?.status || err?.name || 'unknown_error';
    logger.warn(message, { reason_code: String(reason) });
  };

  const rerender = () => {
    if (typeof renderThreads === 'function') renderThreads();
  };

  const currentBelongsToFolder = (folder) => {
    const current = typeof getCurrentThread === 'function' ? getCurrentThread() : null;
    return Boolean(current?.id && current.workspace_folder_id === folder.id);
  };

  const requestCreateNote = async (folder) => {
    if (!NotesMode?.canLoadWorkspaceNotes?.(folder)) {
      status('Notes disponibles après liaison Nextcloud du répertoire.', true);
      return;
    }
    if (typeof createWorkspaceNoteOnServer !== 'function' || typeof refreshWorkspaceNotes !== 'function') {
      status('Création de note indisponible.', true);
      return;
    }
    const title = typeof window !== 'undefined'
      ? String(window.prompt('Titre de la note') || '').trim()
      : '';
    if (!title) return;
    try {
      const note = await createWorkspaceNoteOnServer(folder.id, { title, markdown: '' });
      if (note && notesModeController?.setSelectedNote) {
        notesModeController.setSelectedNote(note, folder);
      }
      await refreshWorkspaceNotes(folder.id);
      rerender();
      status('Note créée et prête pour le mode Notes.');
    } catch (err) {
      warn('Création note répertoire échouée', err);
      status('Création de la note impossible.', true);
      rerender();
    }
  };

  const requestPrepareNote = async (folder, note) => {
    if (!currentBelongsToFolder(folder)) {
      status('Mode Notes disponible seulement dans une conversation du répertoire.', true);
      rerender();
      return;
    }
    if (typeof prepareWorkspaceNoteOnServer !== 'function') {
      status('Préparation de note indisponible.', true);
      rerender();
      return;
    }
    try {
      await prepareWorkspaceNoteOnServer(folder.id, note.id);
      notesModeController?.setSelectedNote?.(note, folder);
      status('Note préparée pour le prochain tour.');
      rerender();
    } catch (err) {
      warn('Préparation note répertoire échouée', err);
      status('Préparation de la note impossible.', true);
      rerender();
    }
  };

  const requestSelectNote = (folder, note) => {
    if (!currentBelongsToFolder(folder)) {
      status('Sélection de note disponible seulement dans une conversation du répertoire.', true);
      rerender();
      return;
    }
    notesModeController?.setSelectedNote?.(note, folder);
    status('Note sélectionnée pour le mode Notes.');
    rerender();
  };

  const appendNoteRows = (folder) => {
    const li = document.createElement('li');
    li.className = 'workspace-folder-notes';

    const header = document.createElement('div');
    header.className = 'workspace-folder-note-header';
    header.textContent = 'Notes';
    const create = document.createElement('button');
    create.type = 'button';
    create.className = 'workspace-folder-note-create';
    create.textContent = '+N';
    create.title = 'Créer une note';
    create.disabled = !NotesMode?.canLoadWorkspaceNotes?.(folder);
    create.addEventListener('click', (event) => {
      event.stopPropagation();
      void requestCreateNote(folder);
    });
    header.appendChild(create);
    li.appendChild(header);

    if (!NotesMode?.canLoadWorkspaceNotes?.(folder)) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-note-empty';
      empty.textContent = 'Notes disponibles après liaison Nextcloud';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }

    const noteStatus = typeof getWorkspaceNotesStatus === 'function'
      ? getWorkspaceNotesStatus(folder.id)
      : null;
    if (noteStatus?.status === 'error') {
      const error = document.createElement('div');
      error.className = 'workspace-folder-note-error';
      error.textContent = 'Chargement des notes impossible';
      if (noteStatus.reason_code) {
        error.dataset.reasonCode = noteStatus.reason_code;
      }
      li.appendChild(error);
      threadsUl.appendChild(li);
      return;
    }

    const notes = typeof getWorkspaceNotes === 'function' ? getWorkspaceNotes(folder.id) : [];
    if (!notes.length) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-note-empty';
      empty.textContent = 'Aucune note';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }

    notes.forEach((note) => {
      const selected = notesModeController?.getSelectedNoteId?.() === note.id
        && notesModeController?.getSelectedFolderId?.() === folder.id;
      const row = document.createElement('div');
      row.className = 'workspace-folder-note';
      if (selected) row.classList.add('selected');

      const name = document.createElement('span');
      name.className = 'workspace-folder-note-name';
      name.textContent = note.title || 'Note';
      row.appendChild(name);

      const meta = document.createElement('span');
      meta.className = 'workspace-folder-note-meta';
      meta.textContent = noteMeta(note);
      row.appendChild(meta);

      const select = document.createElement('button');
      select.type = 'button';
      select.className = 'workspace-folder-note-action workspace-folder-note-action-select';
      select.textContent = selected ? '✓' : 'Utiliser';
      select.title = 'Utiliser cette note comme contexte';
      select.addEventListener('click', (event) => {
        event.stopPropagation();
        requestSelectNote(folder, note);
      });
      row.appendChild(select);

      const prepare = document.createElement('button');
      prepare.type = 'button';
      prepare.className = 'workspace-folder-note-action workspace-folder-note-action-prepare';
      prepare.textContent = 'Préparer';
      prepare.title = 'Préparer cette note pour Frida';
      prepare.addEventListener('click', (event) => {
        event.stopPropagation();
        void requestPrepareNote(folder, note);
      });
      row.appendChild(prepare);

      li.appendChild(row);
    });

    threadsUl.appendChild(li);
  };

  return Object.freeze({
    appendNoteRows,
    requestCreateNote,
  });
}

const FridaWorkspaceFolderNotesPanel = Object.freeze({
  createWorkspaceFolderNotesPanelRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderNotesPanel;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolderNotesPanel = FridaWorkspaceFolderNotesPanel;
}
