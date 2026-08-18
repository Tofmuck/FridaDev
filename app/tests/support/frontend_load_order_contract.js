'use strict';

const REQUIRED_CHAT_SCRIPTS = Object.freeze([
  'whisper/whisper_dictation.js',
  'chat_streaming.js',
  'chat_workspace_folders.js',
  'chat_workspace_folder_exports.js',
  'chat_workspace_folder_exports_panel.js',
  'chat_workspace_folder_generated_images.js',
  'chat_image_generation.js',
  'chat_workspace_folder_generated_images_panel.js',
  'chat_notes_mode.js',
  'chat_workspace_folder_notes_panel.js',
  'chat_workspace_folder_artifact_panels.js',
  'chat_workspace_folder_file_rows.js',
  'chat_workspace_folder_tree_renderer.js',
  'chat_workspace_folders_sidebar.js',
  'chat_threads_folder_binding.js',
  'chat_threads_list_renderer.js',
  'chat_threads_sidebar.js',
  'chat_active_documents.js',
  'chat_copy_export.js',
  'main_reasoning_control.js',
  'chat_adobe_mode.js',
  'chat_biblio_mode.js',
  'chat_agenda_mode.js',
  'app.js',
]);

const LOAD_BEFORE = Object.freeze([
  ['chat_workspace_folders.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_workspace_folder_exports.js', 'chat_workspace_folder_exports_panel.js'],
  ['chat_workspace_folder_exports_panel.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_workspace_folder_generated_images.js', 'chat_workspace_folder_generated_images_panel.js'],
  ['chat_image_generation.js', 'chat_workspace_folder_generated_images_panel.js'],
  ['chat_workspace_folder_generated_images_panel.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_notes_mode.js', 'chat_workspace_folder_notes_panel.js'],
  ['chat_workspace_folder_notes_panel.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_workspace_folders.js', 'chat_workspace_folder_file_rows.js'],
  ['chat_workspace_folders.js', 'chat_workspace_folder_tree_renderer.js'],
  ['chat_workspace_folder_artifact_panels.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_workspace_folder_file_rows.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_workspace_folder_tree_renderer.js', 'chat_workspace_folders_sidebar.js'],
  ['chat_threads_folder_binding.js', 'chat_threads_sidebar.js'],
  ['chat_threads_list_renderer.js', 'chat_threads_sidebar.js'],
  ['chat_workspace_folders_sidebar.js', 'chat_threads_sidebar.js'],
  ['chat_workspace_folders.js', 'chat_threads_sidebar.js'],
  ...REQUIRED_CHAT_SCRIPTS
    .filter((script) => script !== 'app.js')
    .map((script) => [script, 'app.js']),
]);

const REQUIRED_GLOBALS = Object.freeze([
  'FridaWhisperDictation',
  'FridaChatStreaming',
  'FridaWorkspaceFolders',
  'FridaWorkspaceFolderExports',
  'FridaWorkspaceFolderExportsPanel',
  'FridaWorkspaceFolderGeneratedImages',
  'FridaImageGeneration',
  'FridaWorkspaceFolderGeneratedImagesPanel',
  'FridaNotesMode',
  'FridaWorkspaceFolderNotesPanel',
  'FridaWorkspaceFoldersSidebar',
  'FridaChatThreadsSidebar',
  'FridaActiveConversationDocuments',
  'FridaChatCopyExport',
  'FridaMainReasoningControl',
  'FridaAdobeMode',
  'FridaBiblioMode',
  'FridaAgendaMode',
]);

function parseScriptSources(html) {
  return Array.from(
    String(html || '').matchAll(/<script\s+[^>]*src=["']([^"']+)["'][^>]*><\/script>/gi),
    (match) => match[1],
  );
}

function validateChatScriptOrder(sources) {
  const actual = Array.from(sources || [], (value) => String(value || ''));
  const issues = [];
  for (const script of REQUIRED_CHAT_SCRIPTS) {
    const count = actual.filter((candidate) => candidate === script).length;
    if (count !== 1) issues.push(`required_script_count:${script}:${count}`);
  }
  for (const [dependency, consumer] of LOAD_BEFORE) {
    if (actual.indexOf(dependency) >= actual.indexOf(consumer)) {
      issues.push(`load_order:${dependency}:${consumer}`);
    }
  }
  return issues.sort();
}

function validateRequiredGlobalPublicationCounts(publicationCounts) {
  const counts = publicationCounts && typeof publicationCounts === 'object'
    ? publicationCounts
    : {};
  const issues = [];
  for (const globalName of REQUIRED_GLOBALS) {
    const count = Number.isInteger(counts[globalName]) ? counts[globalName] : 0;
    if (count !== 1) {
      issues.push(`required_global_publication_count:${globalName}:${count}`);
    }
  }
  return issues.sort();
}

module.exports = {
  LOAD_BEFORE,
  REQUIRED_CHAT_SCRIPTS,
  REQUIRED_GLOBALS,
  parseScriptSources,
  validateChatScriptOrder,
  validateRequiredGlobalPublicationCounts,
};
