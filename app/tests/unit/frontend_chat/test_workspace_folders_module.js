const test = require("node:test");
const assert = require("node:assert/strict");

const {
  WORKSPACE_FOLDER_ICON_KEYS,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
  normalizeWorkspaceFileItem,
  normalizeWorkspaceFilesPayload,
  normalizeWorkspaceFileSelectionsPayload,
  compactWorkspaceFileMeta,
  groupThreadsByWorkspaceFolder,
} = require("../../../web/chat_workspace_folders.js");

test("workspace folders module exposes the allowlisted icon keys", () => {
  assert.equal(WORKSPACE_FOLDER_ICON_KEYS.includes("folder"), true);
  assert.equal(WORKSPACE_FOLDER_ICON_KEYS.includes("spark"), true);
  assert.equal(WORKSPACE_FOLDER_ICON_KEYS.includes("<svg>"), false);
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
    icon_label: "+",
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
