'use strict';

function createWorkspaceFolderArtifactPanels({
  notesPanel,
  exportsPanel,
  generatedImagesPanel,
} = {}) {
  const appendRows = (folder) => {
    notesPanel?.appendNoteRows?.(folder);
    exportsPanel?.appendExportRows?.(folder);
    generatedImagesPanel?.appendGeneratedImageRows?.(folder);
  };
  const requestCreateNote = typeof notesPanel?.requestCreateNote === 'function'
    ? (folder) => notesPanel.requestCreateNote(folder)
    : null;

  return Object.freeze({ appendRows, requestCreateNote });
}

const FridaWorkspaceFolderArtifactPanelsModule = Object.freeze({
  createWorkspaceFolderArtifactPanels,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaWorkspaceFolderArtifactPanelsModule;
}
