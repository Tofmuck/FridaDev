const test = require("node:test");
const assert = require("node:assert/strict");

const {
  WORKSPACE_FOLDER_ICON_KEYS,
  WORKSPACE_FOLDER_ICON_SVGS,
  normalizeWorkspaceIconKey,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
  normalizeWorkspaceFileItem,
  normalizeWorkspaceFilesPayload,
  normalizeWorkspaceFileSelectionsPayload,
  compactWorkspaceFileMeta,
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
