'use strict';

const WORKSPACE_EXPORT_FORMATS = Object.freeze(['md', 'txt', 'docx', 'pdf']);
const WORKSPACE_EXPORT_TEXT_SOURCE_FORMATS = Object.freeze(['md', 'txt']);

const WORKSPACE_EXPORT_REASON_LABELS = Object.freeze({
  folder_export_folder_not_linked: 'Exports disponibles apres synchronisation Nextcloud.',
  folder_export_folder_deleted: 'Dossier supprime.',
  folder_export_name_invalid: 'Nom d export invalide.',
  folder_export_name_conflict: 'Un export existe deja avec ce nom.',
  folder_export_client_export_id_forbidden: 'Identifiant reserve au serveur.',
  folder_export_not_found: 'Export introuvable.',
  folder_export_deleted: 'Export supprime.',
  folder_export_not_linked: 'Export non lie a Nextcloud.',
  folder_export_access_not_prepared: 'Acces export non prepare.',
  folder_export_source_missing: 'Source d export manquante.',
  folder_export_source_ambiguous: 'Source d export ambigue.',
  folder_export_source_unsupported: 'Source d export non supportee.',
  folder_export_source_unavailable: 'Source d export indisponible.',
  folder_export_source_not_prepared: 'Source d export non preparee.',
  folder_export_source_format_unsupported: 'Format source non reutilisable.',
  folder_export_source_read_unavailable: 'Lecture source impossible.',
  folder_export_source_read_too_large: 'Source trop volumineuse.',
  folder_export_format_unsupported: 'Format d export non supporte.',
  folder_export_dependency_unavailable: 'Moteur d export indisponible.',
  folder_export_too_large: 'Export trop volumineux.',
  folder_export_generation_failed_redacted: 'Generation export impossible.',
  folder_export_lookup_failed: 'Lecture des exports indisponible.',
  folder_export_download_ok: 'Action disponible.',
  folder_export_reuse_ok: 'Action disponible.',
});

function normalizeWorkspaceExportId(value) {
  const raw = String(value || '').trim();
  return raw || null;
}

function normalizeWorkspaceExportFormat(value) {
  const raw = String(value || '').trim().toLowerCase().replace(/^\./, '');
  if (raw === 'markdown') return 'md';
  if (raw === 'text') return 'txt';
  return WORKSPACE_EXPORT_FORMATS.includes(raw) ? raw : '';
}

function normalizeWorkspaceExportTitle(value, fallback = 'Export') {
  const title = String(value || '').replace(/\s+/g, ' ').trim();
  const safe = title || fallback;
  return safe.length > 160 ? safe.slice(0, 160).trimEnd() : safe;
}

function parseWorkspaceExportBool(value) {
  if (value === true || value === 1) return true;
  if (value === false || value === 0 || value === null || value === undefined) return false;
  const raw = String(value).trim().toLowerCase();
  return raw === 'true' || raw === '1' || raw === 'yes' || raw === 'on';
}

function normalizeWorkspaceExportItem(item) {
  const user = item?.export_v1_user && typeof item.export_v1_user === 'object'
    ? item.export_v1_user
    : item || {};
  const actions = user.actions && typeof user.actions === 'object' ? user.actions : {};
  const id = normalizeWorkspaceExportId(user.export_id || item?.id || item?.export_id);
  const workspaceFolderId = normalizeWorkspaceExportId(user.workspace_folder_id || item?.workspace_folder_id);
  if (!id || !workspaceFolderId) return null;
  const format = normalizeWorkspaceExportFormat(user.format || item?.export_format || item?.format);
  const canDownload = parseWorkspaceExportBool(user.can_download);
  const canOpen = parseWorkspaceExportBool(user.can_open);
  const canReuseFromServer = parseWorkspaceExportBool(user.can_reuse_as_source);
  return {
    id,
    export_id: id,
    workspace_folder_id: workspaceFolderId,
    title: normalizeWorkspaceExportTitle(user.title || item?.title, 'Export'),
    format,
    source_kind: String(user.source_kind || item?.source_kind || '').trim(),
    status: String(user.status || item?.local_state || '').trim(),
    status_label: String(user.status_label || '').replace(/\s+/g, ' ').trim(),
    sync_label: String(user.sync_label || '').replace(/\s+/g, ' ').trim(),
    reason_code: String(user.reason_code || item?.reason_code || '').trim(),
    byte_size: Number(user.byte_size || item?.byte_size || 0),
    char_count: Number(user.char_count || item?.char_count || 0),
    created_at: user.created_at || item?.created_at || null,
    updated_at: user.updated_at || item?.updated_at || user.created_at || item?.created_at || null,
    deleted_at: user.deleted_at || item?.deleted_at || null,
    can_download: canDownload,
    can_open: canOpen,
    can_reuse_as_source: canReuseFromServer && WORKSPACE_EXPORT_TEXT_SOURCE_FORMATS.includes(format),
    download_reason_code: String(actions.download_reason_code || '').trim(),
    open_reason_code: String(actions.open_reason_code || '').trim(),
    reuse_as_source_reason_code: String(actions.reuse_as_source_reason_code || '').trim(),
  };
}

function normalizeWorkspaceExportsPayload(payload) {
  const items = Array.isArray(payload?.exports)
    ? payload.exports
    : (Array.isArray(payload?.items) ? payload.items : []);
  return items.map(normalizeWorkspaceExportItem).filter(Boolean);
}

function formatWorkspaceExportBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} ko`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} Mo`;
}

function formatWorkspaceExportDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

function compactWorkspaceExportMeta(item) {
  const parts = [];
  const format = normalizeWorkspaceExportFormat(item?.format);
  if (format) parts.push(format.toUpperCase());
  const size = formatWorkspaceExportBytes(item?.byte_size);
  if (size) parts.push(size);
  const date = formatWorkspaceExportDate(item?.created_at || item?.updated_at);
  if (date) parts.push(date);
  const status = String(item?.status_label || item?.sync_label || '').replace(/\s+/g, ' ').trim();
  if (status) parts.push(status);
  return parts.join(' · ');
}

function workspaceExportReasonLabel(reasonCode) {
  const reason = String(reasonCode || '').trim();
  return WORKSPACE_EXPORT_REASON_LABELS[reason] || 'Action export impossible.';
}

function workspaceExportActionReason(item, action) {
  if (action === 'download') return item?.download_reason_code || item?.reason_code || '';
  if (action === 'open') return item?.open_reason_code || item?.reason_code || '';
  if (action === 'reuse') return item?.reuse_as_source_reason_code || item?.reason_code || '';
  return item?.reason_code || '';
}

function workspaceExportActionLabel(item, action) {
  return workspaceExportReasonLabel(workspaceExportActionReason(item, action));
}

function canLoadWorkspaceExports(folder) {
  return Boolean(
    folder
    && !folder.deleted_at
    && String(folder.nextcloud_sync_state || '').trim() === 'linked'
  );
}

function encodeWorkspaceExportSegment(value) {
  return encodeURIComponent(String(value || '').trim());
}

function buildWorkspaceExportsListPath(folderId) {
  return `/api/workspace-folders/${encodeWorkspaceExportSegment(folderId)}/exports`;
}

function buildWorkspaceExportLookupPath(folderId, exportId) {
  return `${buildWorkspaceExportsListPath(folderId)}/${encodeWorkspaceExportSegment(exportId)}`;
}

function buildWorkspaceExportContentPath(folderId, exportId, action) {
  const mode = action === 'open' ? 'open' : 'download';
  return `${buildWorkspaceExportLookupPath(folderId, exportId)}/${mode}`;
}

function buildConversationExportPayload({ conversationId, exportFormat = 'md', title = '' } = {}) {
  const fmt = normalizeWorkspaceExportFormat(exportFormat) || 'md';
  return {
    source_kind: 'conversation',
    conversation_id: String(conversationId || '').trim(),
    explicit_source: true,
    export_format: fmt,
    title: normalizeWorkspaceExportTitle(title, 'Export conversation'),
  };
}

function buildReuseExportPayload({ sourceExportId, exportFormat = 'md', title = '' } = {}) {
  const fmt = normalizeWorkspaceExportFormat(exportFormat) || 'md';
  return {
    source_kind: 'export',
    source_export_id: String(sourceExportId || '').trim(),
    explicit_source: true,
    export_format: fmt,
    title: normalizeWorkspaceExportTitle(title, 'Export reutilise'),
  };
}

function workspaceExportUserError(payloadOrReason) {
  const reason = typeof payloadOrReason === 'string'
    ? payloadOrReason
    : String(payloadOrReason?.reason_code || payloadOrReason?.export?.reason_code || '').trim();
  return workspaceExportReasonLabel(reason);
}

const FridaWorkspaceFolderExports = Object.freeze({
  WORKSPACE_EXPORT_FORMATS,
  WORKSPACE_EXPORT_TEXT_SOURCE_FORMATS,
  WORKSPACE_EXPORT_REASON_LABELS,
  normalizeWorkspaceExportId,
  normalizeWorkspaceExportFormat,
  normalizeWorkspaceExportTitle,
  normalizeWorkspaceExportItem,
  normalizeWorkspaceExportsPayload,
  formatWorkspaceExportBytes,
  compactWorkspaceExportMeta,
  workspaceExportReasonLabel,
  workspaceExportActionLabel,
  canLoadWorkspaceExports,
  buildWorkspaceExportsListPath,
  buildWorkspaceExportLookupPath,
  buildWorkspaceExportContentPath,
  buildConversationExportPayload,
  buildReuseExportPayload,
  workspaceExportUserError,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderExports;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolderExports = FridaWorkspaceFolderExports;
}
