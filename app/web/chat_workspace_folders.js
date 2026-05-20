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

function normalizeWorkspaceFolderId(value) {
  const raw = String(value || '').trim();
  return raw || null;
}

function normalizeWorkspaceFolderItem(item) {
  const id = normalizeWorkspaceFolderId(item?.id || item?.folder_id);
  if (!id) return null;
  const displayName = String(item?.display_name || item?.name || '').replace(/\s+/g, ' ').trim();
  if (!displayName) return null;
  const iconKey = WORKSPACE_FOLDER_ICON_KEYS.includes(String(item?.icon_key || '').trim())
    ? String(item.icon_key).trim()
    : 'folder';
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
  normalizeWorkspaceFolderId,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
  groupThreadsByWorkspaceFolder,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolders;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolders = FridaWorkspaceFolders;
}
