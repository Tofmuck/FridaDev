'use strict';

const WORKSPACE_GENERATED_IMAGE_FORMATS = Object.freeze(['png', 'jpeg', 'webp']);

const WORKSPACE_GENERATED_IMAGE_REASON_LABELS = Object.freeze({
  folder_generated_image_folder_not_linked: 'Images disponibles après synchronisation Nextcloud.',
  folder_generated_image_folder_deleted: 'Dossier supprimé.',
  folder_generated_image_prompt_missing: 'Prompt requis.',
  folder_generated_image_prompt_too_large: 'Prompt trop long.',
  folder_generated_image_generator_unsupported: 'Modèle image indisponible.',
  folder_generated_image_aspect_ratio_unsupported: 'Ratio non pris en charge.',
  folder_generated_image_size_unsupported: 'Taille non prise en charge.',
  folder_generated_image_provider_timeout: 'Génération trop longue.',
  folder_generated_image_provider_error_redacted: 'Génération image impossible.',
  folder_generated_image_provider_no_image: 'Aucune image renvoyée.',
  folder_generated_image_data_url_invalid: 'Image renvoyée invalide.',
  folder_generated_image_data_url_too_large: 'Image renvoyée trop volumineuse.',
  folder_generated_image_format_unsupported: 'Format image non supporté.',
  folder_generated_image_mime_invalid: 'Type image invalide.',
  folder_generated_image_too_large: 'Image trop volumineuse.',
  folder_generated_image_dimensions_invalid: 'Dimensions image invalides.',
  folder_generated_image_name_conflict: 'Une image existe déjà avec ce nom.',
  folder_generated_image_lookup_failed: 'Lecture des images indisponible.',
  folder_generated_image_not_found: 'Image introuvable.',
  folder_generated_image_deleted: 'Image supprimée.',
  folder_generated_image_not_linked: 'Image non liée à Nextcloud.',
  folder_generated_image_access_not_prepared: 'Accès image non préparé.',
  folder_generated_image_download_ok: 'Action disponible.',
  folder_generated_image_open_ok: 'Action disponible.',
  folder_generated_image_delete_ok: 'Action disponible.',
  folder_generated_image_delete_failed_redacted: 'Suppression image impossible.',
  folder_generated_image_local_persistence_failed: 'Suppression distante faite, état local non mis à jour.',
});

function normalizeWorkspaceGeneratedImageId(value) {
  const raw = String(value || '').trim();
  return raw || null;
}

function normalizeWorkspaceGeneratedImageFormat(value) {
  const raw = String(value || '').trim().toLowerCase().replace(/^\./, '');
  if (raw === 'jpg') return 'jpeg';
  return WORKSPACE_GENERATED_IMAGE_FORMATS.includes(raw) ? raw : '';
}

function normalizeGeneratedImageDisplayName(value, fallback = 'Image générée') {
  const name = String(value || '').replace(/\s+/g, ' ').trim();
  const safe = name || fallback;
  return safe.length > 160 ? safe.slice(0, 160).trimEnd() : safe;
}

function parseGeneratedImageBool(value) {
  if (value === true || value === 1) return true;
  if (value === false || value === 0 || value === null || value === undefined) return false;
  const raw = String(value).trim().toLowerCase();
  return raw === 'true' || raw === '1' || raw === 'yes' || raw === 'on';
}

function normalizeWorkspaceGeneratedImageItem(item) {
  const user = item?.generated_image_v1_user && typeof item.generated_image_v1_user === 'object'
    ? item.generated_image_v1_user
    : item || {};
  const actions = user.actions && typeof user.actions === 'object' ? user.actions : {};
  const id = normalizeWorkspaceGeneratedImageId(user.image_id || item?.id || item?.image_id);
  const workspaceFolderId = normalizeWorkspaceGeneratedImageId(user.workspace_folder_id || item?.workspace_folder_id);
  if (!id || !workspaceFolderId) return null;
  return {
    id,
    image_id: id,
    workspace_folder_id: workspaceFolderId,
    display_name: normalizeGeneratedImageDisplayName(user.display_name || item?.display_name),
    format: normalizeWorkspaceGeneratedImageFormat(user.format || item?.image_format || item?.format),
    mime_type: String(user.mime_type || item?.mime_type || '').replace(/\s+/g, ' ').trim(),
    byte_size: Number(user.byte_size || item?.byte_size || 0),
    width: Number(user.width || item?.width || 0),
    height: Number(user.height || item?.height || 0),
    generator_key: String(user.generator_key || item?.generator_key || '').trim(),
    provider_model: String(user.provider_model || item?.provider_model || '').trim(),
    aspect_ratio: String(user.aspect_ratio || item?.aspect_ratio || '').trim(),
    image_size: String(user.image_size || item?.image_size || '').trim(),
    status: String(user.status || item?.local_state || '').trim(),
    status_label: String(user.status_label || '').replace(/\s+/g, ' ').trim(),
    sync_label: String(user.sync_label || '').replace(/\s+/g, ' ').trim(),
    reason_code: String(user.reason_code || item?.reason_code || '').trim(),
    created_at: user.created_at || item?.created_at || null,
    updated_at: user.updated_at || item?.updated_at || user.created_at || item?.created_at || null,
    deleted_at: user.deleted_at || item?.deleted_at || null,
    can_open: parseGeneratedImageBool(user.can_open),
    can_download: parseGeneratedImageBool(user.can_download),
    can_delete: parseGeneratedImageBool(user.can_delete),
    open_reason_code: String(actions.open_reason_code || '').trim(),
    download_reason_code: String(actions.download_reason_code || '').trim(),
    delete_reason_code: String(actions.delete_reason_code || '').trim(),
  };
}

function normalizeWorkspaceGeneratedImagesPayload(payload) {
  const items = Array.isArray(payload?.generated_images)
    ? payload.generated_images
    : (Array.isArray(payload?.items) ? payload.items : []);
  return items.map(normalizeWorkspaceGeneratedImageItem).filter(Boolean);
}

function formatGeneratedImageBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} ko`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} Mo`;
}

function formatGeneratedImageDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

function compactWorkspaceGeneratedImageMeta(item) {
  const parts = [];
  const format = normalizeWorkspaceGeneratedImageFormat(item?.format);
  if (format) parts.push(format.toUpperCase());
  if (item?.width && item?.height) parts.push(`${Number(item.width)} x ${Number(item.height)} px`);
  const size = formatGeneratedImageBytes(item?.byte_size);
  if (size) parts.push(size);
  const date = formatGeneratedImageDate(item?.created_at || item?.updated_at);
  if (date) parts.push(date);
  const status = String(item?.status_label || item?.sync_label || '').replace(/\s+/g, ' ').trim();
  if (status) parts.push(status);
  return parts.join(' · ');
}

function workspaceGeneratedImageReasonLabel(reasonCode) {
  const reason = String(reasonCode || '').trim();
  return WORKSPACE_GENERATED_IMAGE_REASON_LABELS[reason] || 'Action image impossible.';
}

function workspaceGeneratedImageActionReason(item, action) {
  if (action === 'open') return item?.open_reason_code || item?.reason_code || '';
  if (action === 'download') return item?.download_reason_code || item?.reason_code || '';
  if (action === 'delete') return item?.delete_reason_code || item?.reason_code || '';
  return item?.reason_code || '';
}

function workspaceGeneratedImageActionLabel(item, action) {
  return workspaceGeneratedImageReasonLabel(workspaceGeneratedImageActionReason(item, action));
}

function canLoadWorkspaceGeneratedImages(folder) {
  return Boolean(
    folder
    && !folder.deleted_at
    && String(folder.nextcloud_sync_state || '').trim() === 'linked'
  );
}

function encodeGeneratedImageSegment(value) {
  return encodeURIComponent(String(value || '').trim());
}

function buildWorkspaceGeneratedImagesListPath(folderId) {
  return `/api/workspace-folders/${encodeGeneratedImageSegment(folderId)}/generated-images`;
}

function buildWorkspaceGeneratedImageLookupPath(folderId, imageId) {
  return `${buildWorkspaceGeneratedImagesListPath(folderId)}/${encodeGeneratedImageSegment(imageId)}`;
}

function buildWorkspaceGeneratedImageContentPath(folderId, imageId, action) {
  const mode = action === 'open' ? 'open' : 'download';
  return `${buildWorkspaceGeneratedImageLookupPath(folderId, imageId)}/${mode}`;
}

function buildWorkspaceGeneratedImagePayload({
  prompt,
  generatorKey = '',
  aspectRatio = '',
  imageSize = '',
  displayName = '',
} = {}) {
  const payload = {
    prompt: String(prompt || '').trim(),
  };
  const generator = String(generatorKey || '').trim();
  const ratio = String(aspectRatio || '').trim();
  const size = String(imageSize || '').trim();
  const name = normalizeGeneratedImageDisplayName(displayName, '');
  if (generator) payload.generator_key = generator;
  if (ratio) payload.aspect_ratio = ratio;
  if (size) payload.image_size = size;
  if (name) payload.display_name = name;
  return payload;
}

function workspaceGeneratedImageUserError(payloadOrReason) {
  const reason = typeof payloadOrReason === 'string'
    ? payloadOrReason
    : String(payloadOrReason?.reason_code || payloadOrReason?.generated_image?.reason_code || '').trim();
  return workspaceGeneratedImageReasonLabel(reason);
}

const FridaWorkspaceFolderGeneratedImages = Object.freeze({
  WORKSPACE_GENERATED_IMAGE_FORMATS,
  WORKSPACE_GENERATED_IMAGE_REASON_LABELS,
  normalizeWorkspaceGeneratedImageId,
  normalizeWorkspaceGeneratedImageFormat,
  normalizeGeneratedImageDisplayName,
  normalizeWorkspaceGeneratedImageItem,
  normalizeWorkspaceGeneratedImagesPayload,
  formatGeneratedImageBytes,
  compactWorkspaceGeneratedImageMeta,
  workspaceGeneratedImageReasonLabel,
  workspaceGeneratedImageActionLabel,
  canLoadWorkspaceGeneratedImages,
  buildWorkspaceGeneratedImagesListPath,
  buildWorkspaceGeneratedImageLookupPath,
  buildWorkspaceGeneratedImageContentPath,
  buildWorkspaceGeneratedImagePayload,
  workspaceGeneratedImageUserError,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderGeneratedImages;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolderGeneratedImages = FridaWorkspaceFolderGeneratedImages;
}
