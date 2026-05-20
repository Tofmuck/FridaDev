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

const WORKSPACE_FOLDER_ICON_LABELS = Object.freeze({
  book: 'B',
  feather: 'P',
  star: '*',
  leaf: 'L',
  folder: 'F',
  moon: 'M',
  circle: 'O',
  fragment: 'K',
  archive: 'A',
  search: 'Q',
  note: 'N',
  image: 'I',
  map: 'C',
  dialog: 'D',
  spark: '+',
});

const WORKSPACE_FILE_STATUS_LABELS = Object.freeze({
  active: '',
  ocr_required: 'OCR requis',
  disk_missing: 'Fichier absent',
  deleted: 'Supprimé',
  error: 'Erreur',
});

function normalizeWorkspaceFolderId(value) {
  const raw = String(value || '').trim();
  return raw || null;
}

function normalizeWorkspaceIconKey(value) {
  const key = String(value || '').trim().toLowerCase();
  return WORKSPACE_FOLDER_ICON_KEYS.includes(key) ? key : 'folder';
}

function normalizeWorkspaceFolderItem(item) {
  const id = normalizeWorkspaceFolderId(item?.id || item?.folder_id);
  if (!id) return null;
  const displayName = String(item?.display_name || item?.name || '').replace(/\s+/g, ' ').trim();
  if (!displayName) return null;
  const iconKey = normalizeWorkspaceIconKey(item?.icon_key);
  return {
    id,
    display_name: displayName,
    icon_key: iconKey,
    icon_label: WORKSPACE_FOLDER_ICON_LABELS[iconKey] || WORKSPACE_FOLDER_ICON_LABELS.folder,
    description: String(item?.description || '').replace(/\s+/g, ' ').trim(),
    sort_order: Number(item?.sort_order || 0),
    created_at: item?.created_at || null,
    updated_at: item?.updated_at || item?.created_at || null,
    deleted_at: item?.deleted_at || null,
  };
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
  return {
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
  };
}

function normalizeWorkspaceFilesPayload(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items.map(normalizeWorkspaceFileItem).filter(Boolean);
}

function normalizeWorkspaceFileSelectionItem(item) {
  const file = normalizeWorkspaceFileItem(item?.file || item);
  const fileId = String(item?.workspace_file_id || file?.id || item?.file_id || '').trim();
  const conversationId = String(item?.conversation_id || '').trim();
  if (!fileId) return null;
  return {
    conversation_id: conversationId || null,
    workspace_file_id: fileId,
    workspace_folder_id: normalizeWorkspaceFolderId(item?.workspace_folder_id || file?.workspace_folder_id),
    selected: Boolean(item?.selected !== false),
    selection_status: String(item?.selection_status || 'selected').trim(),
    reason_code: String(item?.reason_code || '').trim(),
    selected_at: item?.selected_at || null,
    updated_at: item?.updated_at || item?.selected_at || null,
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
  WORKSPACE_FILE_STATUS_LABELS,
  normalizeWorkspaceFolderId,
  normalizeWorkspaceIconKey,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
  normalizeWorkspaceFileItem,
  normalizeWorkspaceFilesPayload,
  normalizeWorkspaceFileSelectionItem,
  normalizeWorkspaceFileSelectionsPayload,
  formatWorkspaceFileBytes,
  compactWorkspaceFileMeta,
  workspaceFileStatusLabel,
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
