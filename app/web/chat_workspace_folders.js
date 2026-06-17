'use strict';

const WORKSPACE_FOLDER_ICON_KEYS = [
  'book',
  'feather',
  'star',
  'leaf',
  'folder',
  'moon',
  'circle',
  'fragment',
  'archive',
  'search',
  'note',
  'image',
  'map',
  'dialog',
  'spark',
];

function workspaceFolderIconSvg(symbolMarkup = '') {
  return `<svg class="workspace-folder-svg" viewBox="0 0 28 22" aria-hidden="true" focusable="false">
    <path class="workspace-folder-svg-back" d="M2.5 7.5h8.2l1.9 2.4h12.9v8.7c0 1.1-.8 1.9-1.9 1.9H4.4c-1.1 0-1.9-.8-1.9-1.9V7.5Z"/>
    <path class="workspace-folder-svg-tab" d="M3.4 4.2h6.9l2 2.5h12.3c.9 0 1.6.7 1.6 1.6v2.1H2.5V5.1c0-.5.4-.9.9-.9Z"/>
    <path class="workspace-folder-svg-front" d="M2.5 9.3h23v9.3c0 1.1-.8 1.9-1.9 1.9H4.4c-1.1 0-1.9-.8-1.9-1.9V9.3Z"/>
    <g class="workspace-folder-svg-mark">${symbolMarkup}</g>
  </svg>`;
}

const WORKSPACE_FOLDER_ICON_SVGS = Object.freeze({
  book: workspaceFolderIconSvg('<path d="M11.1 13.1c1.2-.6 2.6-.6 3.8 0v4.1c-1.2-.6-2.6-.6-3.8 0v-4.1Z"/><path d="M14.9 13.1c1.2-.6 2.6-.6 3.8 0v4.1c-1.2-.6-2.6-.6-3.8 0v-4.1Z"/>'),
  feather: workspaceFolderIconSvg('<path d="M11.2 17.2c3.2-.7 5.6-2.6 7-5.4-2.9-.2-5.2.9-6.7 3.1-.5.7-.7 1.5-.3 2.3Z"/><path d="M12 16.4l5.2-3.7"/>'),
  star: workspaceFolderIconSvg('<path d="m15 12.4.9 1.9 2.1.3-1.5 1.5.4 2.1-1.9-1-1.9 1 .4-2.1-1.5-1.5 2.1-.3.9-1.9Z"/>'),
  leaf: workspaceFolderIconSvg('<path d="M11.1 17.8c4.1-.2 6.9-2.4 7.8-6.2-3.9.1-6.8 2.3-7.8 6.2Z"/><path d="M12.2 16.8c1.5-1.6 3.1-2.7 5.2-3.7"/>'),
  folder: workspaceFolderIconSvg(''),
  moon: workspaceFolderIconSvg('<path d="M17.8 17.7a4.5 4.5 0 0 1-5.7-5.7 5.1 5.1 0 1 0 5.7 5.7Z"/>'),
  circle: workspaceFolderIconSvg('<circle cx="15" cy="15.2" r="3.2"/>'),
  fragment: workspaceFolderIconSvg('<path d="M11.4 13.2h3.2v2.1h-2v2.7h-1.2v-4.8Z"/><path d="M16 12.6h2.8v4.8H16v-1.2h1.6v-2.4H16v-1.2Z"/>'),
  archive: workspaceFolderIconSvg('<path d="M11.2 13.1h7.6v4.7h-7.6v-4.7Z"/><path d="M12.3 14.6h5.4"/>'),
  search: workspaceFolderIconSvg('<circle cx="14.3" cy="14.5" r="2.5"/><path d="m16.2 16.4 2 2"/>'),
  note: workspaceFolderIconSvg('<path d="M12 12.6h5.4l1.1 1.1v4.3H12v-5.4Z"/><path d="M17.4 12.6v1.2h1.1"/><path d="M13.2 15h3.5M13.2 16.8h4"/>'),
  image: workspaceFolderIconSvg('<rect x="11.5" y="12.6" width="7" height="5.1" rx=".7"/><path d="m12.5 16.8 1.7-1.7 1.2 1.1 1.1-1.3 1.1 1.9"/><circle cx="16.9" cy="13.9" r=".5"/>'),
  map: workspaceFolderIconSvg('<path d="m11.2 13.1 2.4-.9 2.8.9 2.4-.9v4.9l-2.4.9-2.8-.9-2.4.9v-4.9Z"/><path d="M13.6 12.2v4.9M16.4 13.1V18"/>'),
  dialog: workspaceFolderIconSvg('<path d="M11.5 12.8h7v4.1h-3.1l-2.3 1.4.4-1.4h-2v-4.1Z"/>'),
  spark: workspaceFolderIconSvg('<path d="M15 11.9v6.5M11.8 15.2h6.4M12.7 12.9l4.6 4.6M17.3 12.9l-4.6 4.6"/>'),
});

const WORKSPACE_FOLDER_ICON_LABELS = Object.freeze({
  book: 'Livre',
  feather: 'Plume',
  star: 'Etoile',
  leaf: 'Feuille',
  folder: 'Dossier',
  moon: 'Lune',
  circle: 'Cercle',
  fragment: 'Fragment',
  archive: 'Archive',
  search: 'Recherche',
  note: 'Note',
  image: 'Image',
  map: 'Carte',
  dialog: 'Dialogue',
  spark: 'Eclat',
});

const WORKSPACE_FILE_STATUS_LABELS = Object.freeze({
  active: '',
  ocr_required: 'OCR requis',
  disk_missing: 'Fichier absent',
  deleted: 'Supprimé',
  error: 'Erreur',
});

const WORKSPACE_FILE_NEXTCLOUD_STATUS_LABELS = Object.freeze({
  unknown: '',
  local_only: 'Local seulement',
  linked: 'Rangé Nextcloud',
  sync_error: 'Erreur sync',
  deleted: 'Supprimé',
});

const WORKSPACE_FILE_USAGE_STATUS_LABELS = Object.freeze({
  selected: 'Sélectionné',
  readable: 'Prêt',
  not_injected: 'Non injecté',
  pdf_text: 'PDF texte',
  pdf_visual_required: 'Lecture visuelle requise',
  visual_ready: 'Lecture visuelle prête',
  too_large: 'Trop volumineux',
  unsupported: 'Non supporté',
  unavailable: 'Indisponible',
  error: 'Erreur',
});

const WORKSPACE_FOLDER_NEXTCLOUD_STATUS_LABELS = Object.freeze({
  unknown: 'Local',
  local_only: 'Local',
  pending: 'En attente Nextcloud',
  sync_pending: 'En attente Nextcloud',
  linked: 'Synchronisé',
  conflict: 'Conflit',
  error: 'Erreur',
  sync_error: 'Erreur',
  deleted: 'Supprimé',
});

const WORKSPACE_FOLDER_OBSERVABILITY_STRING_FIELDS = Object.freeze([
  'kind',
  'operation',
  'status',
  'status_class',
  'reason_code',
  'folder_ref',
  'local_status',
  'nextcloud_name_hash',
  'nextcloud_sync_state',
  'nextcloud_share_state',
  'nextcloud_reason_code',
  'file_reason_code',
]);

const WORKSPACE_FOLDER_OBSERVABILITY_NUMBER_FIELDS = Object.freeze([
  'folder_count',
  'files_deleted',
  'file_delete_requested',
  'file_delete_failed',
  'conversations_moved_out',
]);

const WORKSPACE_FOLDER_OBSERVABILITY_BOOLEAN_FIELDS = Object.freeze([
  'content_free',
  'raw_content_included',
  'server_path_included',
  'remote_url_included',
  'secret_included',
  'nextcloud_live_checked',
  'files_preserved',
]);

function normalizeWorkspaceFolderId(value) {
  const raw = String(value || '').trim();
  return raw || null;
}

function normalizeWorkspaceIconKey(value) {
  const key = String(value || '').trim().toLowerCase();
  return WORKSPACE_FOLDER_ICON_KEYS.includes(key) ? key : 'folder';
}

function parseWorkspaceFolderObservabilityBool(value) {
  if (value === true || value === 1) return true;
  if (value === false || value === 0 || value === null || value === undefined) return false;
  const raw = String(value).trim().toLowerCase();
  return raw === 'true' || raw === '1' || raw === 'yes' || raw === 'on';
}

function normalizeWorkspaceFolderObservability(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const observation = {};
  for (const field of WORKSPACE_FOLDER_OBSERVABILITY_STRING_FIELDS) {
    const raw = String(value[field] || '').replace(/\s+/g, ' ').trim();
    if (raw) observation[field] = raw;
  }
  for (const field of WORKSPACE_FOLDER_OBSERVABILITY_NUMBER_FIELDS) {
    if (value[field] !== undefined) observation[field] = Number(value[field] || 0);
  }
  for (const field of WORKSPACE_FOLDER_OBSERVABILITY_BOOLEAN_FIELDS) {
    if (value[field] !== undefined) observation[field] = parseWorkspaceFolderObservabilityBool(value[field]);
  }
  return Object.keys(observation).length ? observation : null;
}

function normalizeWorkspaceFolderItem(item) {
  const id = normalizeWorkspaceFolderId(item?.id || item?.folder_id);
  if (!id) return null;
  const displayName = String(item?.display_name || item?.name || '').replace(/\s+/g, ' ').trim();
  if (!displayName) return null;
  const iconKey = normalizeWorkspaceIconKey(item?.icon_key);
  const folder = {
    id,
    display_name: displayName,
    icon_key: iconKey,
    icon_label: WORKSPACE_FOLDER_ICON_LABELS[iconKey] || WORKSPACE_FOLDER_ICON_LABELS.folder,
    icon_svg: WORKSPACE_FOLDER_ICON_SVGS[iconKey] || WORKSPACE_FOLDER_ICON_SVGS.folder,
    description: String(item?.description || '').replace(/\s+/g, ' ').trim(),
    sort_order: Number(item?.sort_order || 0),
    created_at: item?.created_at || null,
    updated_at: item?.updated_at || item?.created_at || null,
    deleted_at: item?.deleted_at || null,
  };
  if (
    item?.local_status !== undefined
    || item?.nextcloud_sync_state !== undefined
    || item?.nextcloud_logical_path !== undefined
    || item?.nextcloud_directory_ref !== undefined
  ) {
    folder.local_status = String(item?.local_status || (folder.deleted_at ? 'deleted' : 'active')).trim();
    folder.nextcloud_logical_root = String(item?.nextcloud_logical_root || '').trim();
    folder.nextcloud_target_name = String(item?.nextcloud_target_name || '').replace(/\s+/g, ' ').trim();
    folder.nextcloud_logical_path = String(item?.nextcloud_logical_path || '').replace(/\s+/g, ' ').trim();
    folder.nextcloud_directory_ref = String(item?.nextcloud_directory_ref || '').trim();
    folder.nextcloud_name_hash = String(item?.nextcloud_name_hash || '').trim();
    folder.nextcloud_sync_state = String(item?.nextcloud_sync_state || 'unknown').trim();
    folder.nextcloud_share_state = String(item?.nextcloud_share_state || 'unknown').trim();
    folder.nextcloud_reason_code = String(item?.nextcloud_reason_code || '').trim();
    folder.nextcloud_live_checked = Boolean(item?.nextcloud_live_checked);
  }
  const observability = normalizeWorkspaceFolderObservability(item?.observability);
  if (observability) folder.observability = observability;
  return folder;
}

function normalizeWorkspaceFoldersPayload(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items
    .map(normalizeWorkspaceFolderItem)
    .filter(Boolean)
    .sort((a, b) => (a.sort_order - b.sort_order) || a.display_name.localeCompare(b.display_name));
}

function normalizeWorkspaceFileItem(item) {
  const id = String(item?.id || item?.file_id || '').trim();
  const folderId = normalizeWorkspaceFolderId(item?.workspace_folder_id);
  if (!id || !folderId) return null;
  const displayName = String(item?.display_name || item?.original_filename || 'fichier')
    .replace(/\s+/g, ' ')
    .trim() || 'fichier';
  const userProjection = normalizeWorkspaceDocumentUserProjection(item?.document_v1_user);
  const nextcloudSyncState = normalizeWorkspaceFileNextcloudState(
    userProjection?.nextcloud_sync_state || item?.document_nextcloud_sync_state,
  );
  const file = {
    id,
    workspace_folder_id: folderId,
    display_name: displayName,
    original_filename: String(item?.original_filename || displayName).replace(/\s+/g, ' ').trim(),
    content_kind: String(item?.content_kind || 'document').trim(),
    media_kind: String(item?.media_kind || 'text').trim(),
    mime_type: String(item?.mime_type || '').trim(),
    source_extension: String(item?.source_extension || '').trim(),
    byte_size: Number(item?.byte_size || 0),
    text_chars: Number(item?.text_chars || 0),
    image_width: Number(item?.image_width || 0),
    image_height: Number(item?.image_height || 0),
    status: String(item?.status || 'active').trim(),
    reason_code: String(item?.reason_code || '').trim(),
    source_kind: String(item?.source_kind || 'upload').trim(),
    source_file_id: item?.source_file_id ? String(item.source_file_id).trim() : null,
    created_at: item?.created_at || null,
    updated_at: item?.updated_at || item?.created_at || null,
    deleted_at: item?.deleted_at || null,
    document_v1_status: String(item?.document_v1_status || userProjection?.document_status || '').trim(),
    document_v1_readiness: String(item?.document_v1_readiness || userProjection?.readiness || '').trim(),
    document_v1_reason_code: String(item?.document_v1_reason_code || userProjection?.reason_code || '').trim(),
    document_nextcloud_sync_state: nextcloudSyncState,
    document_nextcloud_status_label: workspaceFileNextcloudStatusLabel({ document_nextcloud_sync_state: nextcloudSyncState }),
  };
  if (userProjection) file.document_v1_user = userProjection;
  return file;
}

function normalizeWorkspaceFilesPayload(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items.map(normalizeWorkspaceFileItem).filter(Boolean);
}

function normalizeWorkspaceFileSelectionItem(item) {
  const file = normalizeWorkspaceFileItem(item?.file || item);
  const fileId = String(item?.workspace_file_id || file?.id || item?.file_id || '').trim();
  const conversationId = String(item?.conversation_id || '').trim();
  const usage = normalizeWorkspaceFileUsage(item?.document_v1_usage);
  const selected = item?.selected === undefined ? true : parseWorkspaceFolderObservabilityBool(item.selected);
  if (!fileId) return null;
  return {
    conversation_id: conversationId || null,
    workspace_file_id: fileId,
    workspace_folder_id: normalizeWorkspaceFolderId(item?.workspace_folder_id || file?.workspace_folder_id),
    selected,
    selection_status: String(item?.selection_status || 'selected').trim(),
    reason_code: String(item?.reason_code || '').trim(),
    selected_at: item?.selected_at || null,
    updated_at: item?.updated_at || item?.selected_at || null,
    document_v1_usage: usage,
    usage_status: usage?.usage_status || '',
    usage_readiness: usage?.readiness || '',
    usage_reason_code: usage?.reason_code || '',
    usage_status_label: workspaceFileUsageStatusLabel(usage),
    file,
  };
}

function normalizeWorkspaceFileSelectionsPayload(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items.map(normalizeWorkspaceFileSelectionItem).filter(Boolean);
}

function formatWorkspaceFileBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} ko`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} Mo`;
}

function compactWorkspaceFileMeta(item) {
  const parts = [];
  const ext = String(item?.source_extension || '').replace(/^\./, '').toUpperCase();
  if (ext) parts.push(ext);
  const size = formatWorkspaceFileBytes(item?.byte_size);
  if (size) parts.push(size);
  if (item?.media_kind === 'image' && item.image_width && item.image_height) {
    parts.push(`${Number(item.image_width)} x ${Number(item.image_height)} px`);
  } else if (Number(item?.text_chars || 0) > 0) {
    parts.push(`${Number(item.text_chars)} caractères`);
  }
  if (item?.source_kind === 'ocr_derived') {
    parts.push('OCR Markdown');
  }
  if (item?.status === 'ocr_required') {
    parts.push('OCR requis');
  } else if (item?.status === 'disk_missing') {
    parts.push('Fichier absent du disque');
  }
  return parts.join(' · ');
}

function workspaceFileStatusLabel(item) {
  const status = String(item?.status || 'active').trim();
  if (WORKSPACE_FILE_STATUS_LABELS[status] !== undefined) {
    return WORKSPACE_FILE_STATUS_LABELS[status];
  }
  return status && status !== 'active' ? 'Etat fichier' : '';
}

function workspaceFileNextcloudStatusLabel(item) {
  const status = normalizeWorkspaceFileNextcloudState(
    item?.document_nextcloud_sync_state || item?.document_v1_user?.nextcloud_sync_state,
  );
  if (WORKSPACE_FILE_NEXTCLOUD_STATUS_LABELS[status] !== undefined) {
    return WORKSPACE_FILE_NEXTCLOUD_STATUS_LABELS[status];
  }
  return '';
}

function workspaceFileUsageStatusLabel(item) {
  const status = String(item?.usage_status || '').trim();
  if (WORKSPACE_FILE_USAGE_STATUS_LABELS[status] !== undefined) {
    return WORKSPACE_FILE_USAGE_STATUS_LABELS[status];
  }
  return status ? 'Etat lecture' : '';
}

function normalizeWorkspaceFileUsage(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return {
    source: String(value.source || '').trim(),
    conversation_id: String(value.conversation_id || '').trim() || null,
    workspace_file_id: String(value.workspace_file_id || '').trim(),
    workspace_folder_id: normalizeWorkspaceFolderId(value.workspace_folder_id),
    selected: parseWorkspaceFolderObservabilityBool(value.selected),
    usage_status: String(value.usage_status || '').trim(),
    readiness: String(value.readiness || '').trim(),
    selection_status: String(value.selection_status || '').trim(),
    reason_code: String(value.reason_code || '').trim(),
    last_injected_turn_id: String(value.last_injected_turn_id || '').trim(),
    last_excluded_turn_id: String(value.last_excluded_turn_id || '').trim(),
    last_excluded_reason_code: String(value.last_excluded_reason_code || '').trim(),
  };
}

function workspaceFolderNextcloudStatusLabel(item) {
  const status = String(item?.nextcloud_sync_state || '').trim();
  if (!status) return '';
  if (WORKSPACE_FOLDER_NEXTCLOUD_STATUS_LABELS[status] !== undefined) {
    return WORKSPACE_FOLDER_NEXTCLOUD_STATUS_LABELS[status];
  }
  return '';
}

function workspaceFolderDeleteConfirmationText(item) {
  const displayName = String(item?.display_name || item?.name || 'ce répertoire').replace(/\s+/g, ' ').trim();
  const label = displayName || 'ce répertoire';
  return `Supprimer le répertoire "${label}" ? Les conversations resteront hors répertoire. Les fichiers et documents ne seront pas supprimés.`;
}

function canRunWorkspaceOcr(item) {
  const mime = String(item?.mime_type || '').split(';', 1)[0].trim().toLowerCase();
  const ext = String(item?.source_extension || '').trim().toLowerCase();
  if (String(item?.status || '') === 'deleted' || String(item?.status || '') === 'disk_missing') return false;
  if (String(item?.source_kind || '') === 'ocr_derived') return false;
  if (String(item?.media_kind || '') === 'image' && ['image/png', 'image/jpeg', 'image/webp'].includes(mime)) {
    return true;
  }
  return mime === 'application/pdf' || ext === '.pdf';
}

function canEditWorkspaceOcrMarkdown(item) {
  return String(item?.source_kind || '') === 'ocr_derived'
    && String(item?.source_extension || '').trim().toLowerCase() === '.md'
    && String(item?.status || 'active') === 'active';
}

function normalizeWorkspaceDocumentUserProjection(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const nextcloudSyncState = normalizeWorkspaceFileNextcloudState(value.nextcloud_sync_state);
  return {
    display_name: String(value.display_name || '').replace(/\s+/g, ' ').trim(),
    document_status: String(value.document_status || '').trim(),
    readiness: String(value.readiness || '').trim(),
    reason_code: String(value.reason_code || '').trim(),
    nextcloud_sync_state: nextcloudSyncState,
    nextcloud_status_label: String(
      value.nextcloud_status_label || workspaceFileNextcloudStatusLabel({ document_nextcloud_sync_state: nextcloudSyncState }),
    ).replace(/\s+/g, ' ').trim(),
    nextcloud_reason_code: String(value.nextcloud_reason_code || '').trim(),
  };
}

function normalizeWorkspaceFileNextcloudState(value) {
  const state = String(value || '').trim();
  return WORKSPACE_FILE_NEXTCLOUD_STATUS_LABELS[state] !== undefined ? state : 'unknown';
}

function groupThreadsByWorkspaceFolder(threads, folders) {
  const folderIds = new Set((folders || []).map((folder) => folder.id));
  const byFolder = new Map();
  for (const folder of folders || []) {
    byFolder.set(folder.id, []);
  }
  const outside = [];
  for (const thread of threads || []) {
    const folderId = normalizeWorkspaceFolderId(thread?.workspace_folder_id);
    if (folderId && folderIds.has(folderId)) {
      byFolder.get(folderId).push(thread);
    } else {
      outside.push(thread);
    }
  }
  return { byFolder, outside };
}

const FridaWorkspaceFolders = Object.freeze({
  WORKSPACE_FOLDER_ICON_KEYS,
  WORKSPACE_FOLDER_ICON_LABELS,
  WORKSPACE_FOLDER_ICON_SVGS,
  WORKSPACE_FILE_STATUS_LABELS,
  WORKSPACE_FILE_NEXTCLOUD_STATUS_LABELS,
  WORKSPACE_FILE_USAGE_STATUS_LABELS,
  WORKSPACE_FOLDER_NEXTCLOUD_STATUS_LABELS,
  normalizeWorkspaceFolderId,
  normalizeWorkspaceIconKey,
  normalizeWorkspaceFolderObservability,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
  normalizeWorkspaceFileItem,
  normalizeWorkspaceFilesPayload,
  normalizeWorkspaceFileSelectionItem,
  normalizeWorkspaceFileSelectionsPayload,
  formatWorkspaceFileBytes,
  compactWorkspaceFileMeta,
  workspaceFileStatusLabel,
  workspaceFileNextcloudStatusLabel,
  workspaceFileUsageStatusLabel,
  workspaceFolderNextcloudStatusLabel,
  workspaceFolderDeleteConfirmationText,
  canRunWorkspaceOcr,
  canEditWorkspaceOcrMarkdown,
  groupThreadsByWorkspaceFolder,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolders;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolders = FridaWorkspaceFolders;
}
