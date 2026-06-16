const test = require("node:test");
const assert = require("node:assert/strict");

const {
  WORKSPACE_FOLDER_ICON_KEYS,
  WORKSPACE_FOLDER_ICON_SVGS,
  normalizeWorkspaceIconKey,
  normalizeWorkspaceFolderObservability,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
  normalizeWorkspaceFileItem,
  normalizeWorkspaceFilesPayload,
  normalizeWorkspaceFileSelectionsPayload,
  compactWorkspaceFileMeta,
  workspaceFolderDeleteConfirmationText,
  workspaceFolderNextcloudStatusLabel,
  workspaceFileStatusLabel,
  canRunWorkspaceOcr,
  canEditWorkspaceOcrMarkdown,
  groupThreadsByWorkspaceFolder,
} = require("../../../web/chat_workspace_folders.js");

test("workspace folders module exposes the allowlisted icon keys", () => {
  assert.equal(WORKSPACE_FOLDER_ICON_KEYS.includes("folder"), true);
  assert.equal(WORKSPACE_FOLDER_ICON_KEYS.includes("spark"), true);
  assert.equal(WORKSPACE_FOLDER_ICON_KEYS.includes("<svg>"), false);
  assert.equal(WORKSPACE_FOLDER_ICON_SVGS.folder.includes("workspace-folder-svg"), true);
  assert.equal(WORKSPACE_FOLDER_ICON_SVGS.spark.includes("workspace-folder-svg-mark"), true);
  assert.equal(normalizeWorkspaceIconKey("spark"), "spark");
  assert.equal(normalizeWorkspaceIconKey("<svg>"), "folder");
});

test("normalizeWorkspaceFolderItem keeps stable UI metadata only", () => {
  const folder = normalizeWorkspaceFolderItem({
    id: "folder-1",
    display_name: "  Projet   Tulu ",
    icon_key: "spark",
    description: "  visible UI ",
    sort_order: "20",
  });

  assert.deepEqual(folder, {
    id: "folder-1",
    display_name: "Projet Tulu",
    icon_key: "spark",
    icon_label: "Eclat",
    icon_svg: WORKSPACE_FOLDER_ICON_SVGS.spark,
    description: "visible UI",
    sort_order: 20,
    created_at: null,
    updated_at: null,
    deleted_at: null,
  });
});

test("normalizeWorkspaceFolderItem preserves fake Nextcloud metadata without raw internals", () => {
  const folder = normalizeWorkspaceFolderItem({
    id: "folder-1",
    display_name: "Projet Tulu",
    icon_key: "folder",
    nextcloud_logical_root: "/Frida",
    nextcloud_target_name: "Projet-Tulu",
    nextcloud_logical_path: "/Frida/Projet-Tulu",
    nextcloud_directory_ref: "workspace-folder:folder-1:abc123def456",
    nextcloud_name_hash: "abc123def456",
    nextcloud_sync_state: "pending",
    nextcloud_share_state: "expected",
    nextcloud_reason_code: "workspace_folder_sync_pending",
    nextcloud_live_checked: false,
    storage_key: "hidden/path",
    dav_url: "redacted dav url",
  });

  assert.equal(folder.nextcloud_logical_root, "/Frida");
  assert.equal(folder.nextcloud_target_name, "Projet-Tulu");
  assert.equal(folder.nextcloud_logical_path, "/Frida/Projet-Tulu");
  assert.equal(folder.nextcloud_sync_state, "pending");
  assert.equal(folder.nextcloud_share_state, "expected");
  assert.equal(folder.nextcloud_live_checked, false);
  assert.equal(folder.storage_key, undefined);
  assert.equal(folder.dav_url, undefined);
  assert.equal(JSON.stringify(folder).includes("remote.php"), false);
});

test("workspace folder observability normalizer keeps only content-free fields", () => {
  const observation = normalizeWorkspaceFolderObservability({
    kind: "frida_v1_workspace_folder",
    operation: "delete",
    status: "ok",
    status_class: "2xx",
    reason_code: "workspace_folder_delete_ok",
    folder_ref: "abc123def456",
    nextcloud_sync_state: "deleted",
    nextcloud_share_state: "unknown",
    files_preserved: true,
    files_deleted: 0,
    file_delete_requested: 0,
    file_delete_failed: 0,
    content_free: true,
    raw_content_included: false,
    server_path_included: false,
    remote_url_included: false,
    secret_included: false,
    display_name: "Projet Tulu",
    nextcloud_logical_path: "/Frida/Projet-Tulu",
    storage_key: "hidden/path",
    Authorization: "redacted",
    app_password: "hidden",
    dav_url: "redacted dav url",
  });

  assert.equal(observation.kind, "frida_v1_workspace_folder");
  assert.equal(observation.operation, "delete");
  assert.equal(observation.reason_code, "workspace_folder_delete_ok");
  assert.equal(observation.files_preserved, true);
  assert.equal(observation.files_deleted, 0);
  assert.equal(observation.display_name, undefined);
  assert.equal(observation.nextcloud_logical_path, undefined);
  assert.equal(observation.storage_key, undefined);
  assert.equal(observation.Authorization, undefined);
  assert.equal(observation.app_password, undefined);
  assert.equal(observation.dav_url, undefined);
  assert.equal(JSON.stringify(observation).includes("/Frida/Projet-Tulu"), false);
  assert.equal(JSON.stringify(observation).includes("redacted dav url"), false);
});

test("workspace folder observability normalizer parses boolean strings strictly", () => {
  const truthy = normalizeWorkspaceFolderObservability({
    content_free: "true",
    files_preserved: "1",
    nextcloud_live_checked: "yes",
    remote_url_included: "on",
  });
  const falsy = normalizeWorkspaceFolderObservability({
    raw_content_included: "false",
    server_path_included: "0",
    secret_included: "no",
    remote_url_included: "off",
    files_preserved: "",
    nextcloud_live_checked: null,
  });

  assert.equal(truthy.content_free, true);
  assert.equal(truthy.files_preserved, true);
  assert.equal(truthy.nextcloud_live_checked, true);
  assert.equal(truthy.remote_url_included, true);
  assert.equal(falsy.raw_content_included, false);
  assert.equal(falsy.server_path_included, false);
  assert.equal(falsy.secret_included, false);
  assert.equal(falsy.remote_url_included, false);
  assert.equal(falsy.files_preserved, false);
  assert.equal(falsy.nextcloud_live_checked, false);
});

test("workspace folder fake-local status labels stay sober and content-free", () => {
  assert.equal(workspaceFolderNextcloudStatusLabel({ nextcloud_sync_state: "unknown" }), "Local");
  assert.equal(workspaceFolderNextcloudStatusLabel({ nextcloud_sync_state: "pending" }), "En attente Nextcloud");
  assert.equal(workspaceFolderNextcloudStatusLabel({ nextcloud_sync_state: "conflict" }), "Conflit");
  assert.equal(workspaceFolderNextcloudStatusLabel({ nextcloud_sync_state: "error" }), "Erreur");
  assert.equal(workspaceFolderNextcloudStatusLabel({ nextcloud_sync_state: "" }), "");
});

test("workspace folder delete confirmation preserves files and documents", () => {
  const text = workspaceFolderDeleteConfirmationText({
    display_name: "Projet Tulu",
    nextcloud_logical_path: "/Frida/Projet-Tulu",
    storage_key: "hidden/path",
  });

  assert.equal(text.includes("Les fichiers et documents ne seront pas supprimés."), true);
  assert.equal(text.includes("les fichiers du répertoire seront supprimés"), false);
  assert.equal(text.includes("/Frida/Projet-Tulu"), false);
  assert.equal(text.includes("storage_key"), false);
});

test("normalizeWorkspaceFoldersPayload sorts folders by manual order", () => {
  const folders = normalizeWorkspaceFoldersPayload({
    items: [
      { id: "b", display_name: "B", sort_order: 2000 },
      { id: "a", display_name: "A", sort_order: 1000 },
    ],
  });

  assert.deepEqual(folders.map((item) => item.id), ["a", "b"]);
});

test("groupThreadsByWorkspaceFolder keeps unassigned conversations below the separator", () => {
  const folders = normalizeWorkspaceFoldersPayload({
    items: [{ id: "folder-1", display_name: "Projet", sort_order: 1000 }],
  });
  const grouped = groupThreadsByWorkspaceFolder(
    [
      { id: "conv-in", workspace_folder_id: "folder-1" },
      { id: "conv-out", workspace_folder_id: null },
      { id: "conv-stale", workspace_folder_id: "missing-folder" },
    ],
    folders,
  );

  assert.deepEqual(grouped.byFolder.get("folder-1").map((item) => item.id), ["conv-in"]);
  assert.deepEqual(grouped.outside.map((item) => item.id), ["conv-out", "conv-stale"]);
});

test("workspace file payloads stay content-free and compact", () => {
  const file = normalizeWorkspaceFileItem({
    id: "file-1",
    workspace_folder_id: "folder-1",
    display_name: "  Capture  ",
    original_filename: "capture.png",
    media_kind: "image",
    source_extension: ".png",
    byte_size: 4096,
    image_width: 80,
    image_height: 64,
    storage_key: "SHOULD NOT SURVIVE",
    text: "RAW SHOULD NOT RENDER",
  });

  assert.equal(file.display_name, "Capture");
  assert.equal(file.storage_key, undefined);
  assert.equal(file.text, undefined);
  assert.equal(compactWorkspaceFileMeta(file), "PNG · 4 ko · 80 x 64 px");
});

test("workspace files payload normalizer handles OCR-required metadata", () => {
  const files = normalizeWorkspaceFilesPayload({
    items: [{
      id: "file-ocr",
      workspace_folder_id: "folder-1",
      display_name: "scan.pdf",
      source_extension: ".pdf",
      byte_size: 2048,
      status: "ocr_required",
    }],
  });

  assert.equal(files.length, 1);
  assert.equal(compactWorkspaceFileMeta(files[0]), "PDF · 2 ko · OCR requis");
  assert.equal(workspaceFileStatusLabel(files[0]), "OCR requis");
  assert.equal(canRunWorkspaceOcr(files[0]), true);
});

test("workspace file status labels stay human and content-free", () => {
  const missing = normalizeWorkspaceFileItem({
    id: "missing",
    workspace_folder_id: "folder-1",
    display_name: "scan.pdf",
    source_extension: ".pdf",
    status: "disk_missing",
    reason_code: "workspace_file_disk_missing",
    storage_key: "_workspace_files/folder-1/missing.pdf",
  });

  assert.equal(workspaceFileStatusLabel(missing), "Fichier absent");
  assert.equal(JSON.stringify(missing).includes("_workspace_files"), false);
});

test("workspace OCR markdown derivatives are editable metadata-only files", () => {
  const files = normalizeWorkspaceFilesPayload({
    items: [{
      id: "file-ocr-md",
      workspace_folder_id: "folder-1",
      display_name: "scan.ocr.md",
      source_extension: ".md",
      byte_size: 4096,
      text_chars: 128,
      status: "active",
      source_kind: "ocr_derived",
      source_file_id: "source-file",
      text_content: "RAW OCR SHOULD NOT SURVIVE",
    }],
  });

  assert.equal(files.length, 1);
  assert.equal(files[0].source_file_id, "source-file");
  assert.equal(files[0].text_content, undefined);
  assert.equal(compactWorkspaceFileMeta(files[0]), "MD · 4 ko · 128 caractères · OCR Markdown");
  assert.equal(canRunWorkspaceOcr(files[0]), false);
  assert.equal(canEditWorkspaceOcrMarkdown(files[0]), true);
});

test("workspace OCR action is available for supported source images", () => {
  const files = normalizeWorkspaceFilesPayload({
    items: [{
      id: "image-1",
      workspace_folder_id: "folder-1",
      display_name: "photo.jpg",
      media_kind: "image",
      mime_type: "image/jpeg",
      source_extension: ".jpg",
      byte_size: 4096,
      image_width: 1200,
      image_height: 900,
      status: "active",
      source_kind: "upload",
    }],
  });

  assert.equal(canRunWorkspaceOcr(files[0]), true);
  assert.equal(canEditWorkspaceOcrMarkdown(files[0]), false);
});

test("workspace OCR action stays limited to supported source media", () => {
  const files = normalizeWorkspaceFilesPayload({
    items: [{
      id: "text-ocr",
      workspace_folder_id: "folder-1",
      display_name: "note.txt",
      mime_type: "text/plain",
      source_extension: ".txt",
      status: "ocr_required",
    }],
  });

  assert.equal(canRunWorkspaceOcr(files[0]), false);
});

test("workspace file selection payloads are conversation scoped and content-free", () => {
  const selections = normalizeWorkspaceFileSelectionsPayload({
    items: [{
      conversation_id: "conv-1",
      workspace_file_id: "file-1",
      workspace_folder_id: "folder-1",
      selected: true,
      selection_status: "selected",
      reason_code: "",
      file: {
        id: "file-1",
        workspace_folder_id: "folder-1",
        display_name: "note.md",
        source_extension: ".md",
        byte_size: 12,
        storage_key: "hidden/path",
        text_content: "RAW",
      },
    }],
  });

  assert.equal(selections.length, 1);
  assert.equal(selections[0].conversation_id, "conv-1");
  assert.equal(selections[0].workspace_file_id, "file-1");
  assert.equal(selections[0].selected, true);
  assert.equal(selections[0].file.storage_key, undefined);
  assert.equal(selections[0].file.text_content, undefined);
});
