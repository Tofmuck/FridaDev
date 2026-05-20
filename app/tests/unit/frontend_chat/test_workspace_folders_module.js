const test = require("node:test");
const assert = require("node:assert/strict");

const {
  WORKSPACE_FOLDER_ICON_KEYS,
  normalizeWorkspaceFolderItem,
  normalizeWorkspaceFoldersPayload,
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
