'use strict';

const WorkspaceGeneratedImagesPanelUi = (
  typeof window !== 'undefined' && window.FridaWorkspaceFolderGeneratedImages
    ? window.FridaWorkspaceFolderGeneratedImages
    : (typeof require !== 'undefined' ? require('./chat_workspace_folder_generated_images.js') : null)
);
const ImageGenerationOptions = (
  typeof window !== 'undefined' && window.FridaImageGeneration
    ? window.FridaImageGeneration
    : (typeof require !== 'undefined' ? require('./chat_image_generation.js') : null)
);

function createWorkspaceFolderGeneratedImagesPanelRenderer({
  threadsUl,
  getWorkspaceGeneratedImages,
  getWorkspaceGeneratedImagesStatus,
  refreshWorkspaceGeneratedImages,
  createWorkspaceGeneratedImageOnServer,
  openWorkspaceGeneratedImage,
  downloadWorkspaceGeneratedImage,
  deleteWorkspaceGeneratedImageOnServer,
  renderThreads,
  setThreadStatus,
  consoleObj,
} = {}) {
  const logger = consoleObj || (typeof console !== 'undefined' ? console : { warn() {} });

  const promptText = (message, fallback = '') => {
    if (typeof window === 'undefined' || typeof window.prompt !== 'function') return fallback;
    return window.prompt(message, fallback);
  };

  const promptImageRequest = () => {
    const prompt = promptText('Prompt image', '');
    if (prompt === null) return null;
    const cleanPrompt = String(prompt || '').trim();
    if (!cleanPrompt) {
      setThreadStatus('Prompt image requis.', true);
      return null;
    }
    const displayNameRaw = promptText('Nom affiché (optionnel)', '');
    const generatorDefault = ImageGenerationOptions?.DEFAULT_GENERATOR_KEY || 'image_generator_nano_banana';
    const generatorRaw = promptText('Modèle image', generatorDefault);
    if (generatorRaw === null) return null;
    const ratioRaw = promptText('Ratio image', '1:1');
    if (ratioRaw === null) return null;
    const sizeRaw = promptText('Taille image', '1K');
    if (sizeRaw === null) return null;
    const normalized = ImageGenerationOptions?.normalizeSelection?.({
      generatorKey: generatorRaw || generatorDefault,
      aspectRatio: ratioRaw || '1:1',
      imageSize: sizeRaw || '1K',
    }) || {
      generator_key: generatorRaw || generatorDefault,
      aspect_ratio: ratioRaw || '1:1',
      image_size: sizeRaw || '1K',
    };
    return WorkspaceGeneratedImagesPanelUi.buildWorkspaceGeneratedImagePayload({
      prompt: cleanPrompt,
      displayName: displayNameRaw === null ? '' : displayNameRaw,
      generatorKey: normalized.generator_key,
      aspectRatio: normalized.aspect_ratio,
      imageSize: normalized.image_size,
    });
  };

  const refreshImagesAndRender = async (folder) => {
    if (typeof refreshWorkspaceGeneratedImages === 'function') {
      await refreshWorkspaceGeneratedImages(folder.id);
    }
    renderThreads();
  };

  const requestCreateImage = async (folder) => {
    if (!WorkspaceGeneratedImagesPanelUi?.canLoadWorkspaceGeneratedImages?.(folder)) {
      setThreadStatus('Images disponibles après synchronisation Nextcloud.', true);
      return;
    }
    if (typeof createWorkspaceGeneratedImageOnServer !== 'function') {
      setThreadStatus('Création image indisponible.', true);
      return;
    }
    const payload = promptImageRequest();
    if (!payload) return;
    try {
      await createWorkspaceGeneratedImageOnServer(folder.id, payload);
      await refreshImagesAndRender(folder);
      setThreadStatus('Image créée dans le répertoire.');
    } catch (err) {
      logger.warn('Création image répertoire échouée', err);
      setThreadStatus(WorkspaceGeneratedImagesPanelUi.workspaceGeneratedImageUserError(err?.payload || err), true);
    }
  };

  const requestOpenImage = (folder, imageItem) => {
    if (!imageItem?.can_open) {
      setThreadStatus(WorkspaceGeneratedImagesPanelUi?.workspaceGeneratedImageActionLabel?.(imageItem, 'open') || 'Ouverture image indisponible.', true);
      return;
    }
    if (typeof openWorkspaceGeneratedImage === 'function') {
      openWorkspaceGeneratedImage(folder.id, imageItem.id);
    }
  };

  const requestDownloadImage = (folder, imageItem) => {
    if (!imageItem?.can_download) {
      setThreadStatus(WorkspaceGeneratedImagesPanelUi?.workspaceGeneratedImageActionLabel?.(imageItem, 'download') || 'Téléchargement image indisponible.', true);
      return;
    }
    if (typeof downloadWorkspaceGeneratedImage === 'function') {
      downloadWorkspaceGeneratedImage(folder.id, imageItem.id);
    }
  };

  const requestDeleteImage = async (folder, imageItem) => {
    if (!imageItem?.can_delete) {
      setThreadStatus(WorkspaceGeneratedImagesPanelUi?.workspaceGeneratedImageActionLabel?.(imageItem, 'delete') || 'Suppression image indisponible.', true);
      return;
    }
    if (typeof deleteWorkspaceGeneratedImageOnServer !== 'function') {
      setThreadStatus('Suppression image indisponible.', true);
      return;
    }
    const ok = typeof window !== 'undefined' && typeof window.confirm === 'function'
      ? window.confirm(`Supprimer l’image "${imageItem.display_name || 'Image'}" du répertoire ?`)
      : false;
    if (!ok) return;
    try {
      await deleteWorkspaceGeneratedImageOnServer(folder.id, imageItem.id);
      await refreshImagesAndRender(folder);
      setThreadStatus('Image supprimée du répertoire.');
    } catch (err) {
      logger.warn('Suppression image répertoire échouée', err);
      setThreadStatus(WorkspaceGeneratedImagesPanelUi.workspaceGeneratedImageUserError(err?.payload || err), true);
    }
  };

  const appendGeneratedImageRows = (folder) => {
    if (!threadsUl || typeof document === 'undefined') return;
    const images = typeof getWorkspaceGeneratedImages === 'function'
      ? getWorkspaceGeneratedImages(folder.id)
      : [];
    const li = document.createElement('li');
    li.className = 'workspace-folder-generated-images';

    const header = document.createElement('div');
    header.className = 'workspace-folder-generated-image-header';
    const label = document.createElement('span');
    label.textContent = 'Images';
    header.appendChild(label);

    const create = document.createElement('button');
    create.type = 'button';
    create.className = 'workspace-folder-generated-image-create';
    create.textContent = '+';
    create.title = WorkspaceGeneratedImagesPanelUi?.canLoadWorkspaceGeneratedImages?.(folder)
      ? 'Créer une image durable dans ce répertoire'
      : 'Images disponibles après synchronisation Nextcloud';
    create.disabled = !WorkspaceGeneratedImagesPanelUi?.canLoadWorkspaceGeneratedImages?.(folder);
    create.addEventListener('click', (event) => {
      event.stopPropagation();
      void requestCreateImage(folder);
    });
    header.appendChild(create);
    li.appendChild(header);

    if (!WorkspaceGeneratedImagesPanelUi?.canLoadWorkspaceGeneratedImages?.(folder)) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-generated-image-empty';
      empty.textContent = 'Images disponibles après synchronisation Nextcloud.';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }

    const imageStatus = typeof getWorkspaceGeneratedImagesStatus === 'function'
      ? getWorkspaceGeneratedImagesStatus(folder.id)
      : null;
    if (imageStatus?.status === 'error') {
      const error = document.createElement('div');
      error.className = 'workspace-folder-generated-image-error';
      error.textContent = 'Chargement des images impossible';
      if (imageStatus.reason_code) {
        error.dataset.reasonCode = String(imageStatus.reason_code);
      }
      li.appendChild(error);
      threadsUl.appendChild(li);
      return;
    }

    if (!images.length) {
      const empty = document.createElement('div');
      empty.className = 'workspace-folder-generated-image-empty';
      empty.textContent = 'Aucune image';
      li.appendChild(empty);
      threadsUl.appendChild(li);
      return;
    }

    images.forEach((imageItem) => {
      const row = document.createElement('div');
      row.className = 'workspace-folder-generated-image';
      if (imageItem.status && imageItem.status !== 'available') {
        row.dataset.status = imageItem.status;
      }

      const name = document.createElement('span');
      name.className = 'workspace-folder-generated-image-name';
      name.textContent = imageItem.display_name || 'Image';
      row.appendChild(name);

      const meta = document.createElement('span');
      meta.className = 'workspace-folder-generated-image-meta';
      meta.textContent = WorkspaceGeneratedImagesPanelUi?.compactWorkspaceGeneratedImageMeta?.(imageItem) || '';
      row.appendChild(meta);

      const state = document.createElement('span');
      state.className = 'workspace-folder-generated-image-state';
      state.textContent = imageItem.status === 'available'
        ? ''
        : (WorkspaceGeneratedImagesPanelUi?.workspaceGeneratedImageReasonLabel?.(imageItem.reason_code) || '');
      row.appendChild(state);

      [
        ['open', '↗', 'Ouvrir', imageItem.can_open, () => requestOpenImage(folder, imageItem)],
        ['download', '↓', 'Télécharger', imageItem.can_download, () => requestDownloadImage(folder, imageItem)],
        ['delete', '×', 'Supprimer', imageItem.can_delete, () => requestDeleteImage(folder, imageItem)],
      ].forEach(([action, text, title, enabled, handler]) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `workspace-folder-generated-image-action workspace-folder-generated-image-action-${action}`;
        btn.textContent = text;
        btn.title = enabled
          ? title
          : (WorkspaceGeneratedImagesPanelUi?.workspaceGeneratedImageActionLabel?.(imageItem, action) || 'Action indisponible');
        btn.disabled = !enabled;
        btn.addEventListener('click', (event) => {
          event.stopPropagation();
          if (btn.disabled) return;
          void handler();
        });
        row.appendChild(btn);
      });
      li.appendChild(row);
    });

    threadsUl.appendChild(li);
  };

  return Object.freeze({ appendGeneratedImageRows });
}

const FridaWorkspaceFolderGeneratedImagesPanel = Object.freeze({
  createWorkspaceFolderGeneratedImagesPanelRenderer,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderGeneratedImagesPanel;
}

if (typeof window !== 'undefined') {
  window.FridaWorkspaceFolderGeneratedImagesPanel = FridaWorkspaceFolderGeneratedImagesPanel;
}
