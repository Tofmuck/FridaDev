const test = require("node:test");
const assert = require("node:assert/strict");

const WorkspaceExports = require("../../../web/chat_workspace_folder_exports.js");
const {
  createWorkspaceFolderExportsPanelRenderer,
} = require("../../../web/chat_workspace_folder_exports_panel.js");

function makeElement(tagName = "div") {
  const listeners = new Map();
  const element = {
    tagName: String(tagName || "div").toUpperCase(),
    children: [],
    parentElement: null,
    style: {},
    dataset: {},
    className: "",
    textContent: "",
    type: "",
    title: "",
    disabled: false,
    value: "",
    events: listeners,
    appendChild(child) {
      child.parentElement = element;
      element.children.push(child);
      return child;
    },
    removeChild(child) {
      element.children = element.children.filter((item) => item !== child);
      child.parentElement = null;
      return child;
    },
    addEventListener(type, handler) {
      const key = String(type || "");
      const current = listeners.get(key) || [];
      current.push(handler);
      listeners.set(key, current);
    },
    click() {
      if (element.disabled) return;
      for (const handler of listeners.get("click") || []) {
        handler({
          stopPropagation() {},
          preventDefault() {},
          target: element,
        });
      }
    },
    setAttribute(name, value) {
      element[name] = value;
    },
    removeAttribute(name) {
      delete element[name];
    },
  };
  return element;
}

function installDom() {
  const body = makeElement("body");
  global.document = {
    body,
    createElement: makeElement,
  };
  return body;
}

function walk(node) {
  const items = [];
  const visit = (current) => {
    if (!current) return;
    items.push(current);
    for (const child of current.children || []) visit(child);
  };
  visit(node);
  return items;
}

function byClass(root, className) {
  return walk(root).filter((node) =>
    String(node.className || "").split(/\s+/).includes(className)
  );
}

function firstByClass(root, className) {
  return byClass(root, className)[0] || null;
}

function visibleText(root) {
  return walk(root).map((node) => String(node.textContent || "")).join(" ");
}

async function flushAsync() {
  await new Promise((resolve) => setImmediate(resolve));
  await Promise.resolve();
}

function buildPanel({
  folder = linkedFolder(),
  currentThread = currentConversation(),
  exportsList = [],
  exportsStatus = { status: "ok", reason_code: "workspace_exports_list_ok" },
  prompts = [],
} = {}) {
  installDom();
  const threadsUl = makeElement("ul");
  const createCalls = [];
  const openCalls = [];
  const downloadCalls = [];
  const statuses = [];
  let refreshCount = 0;
  global.window = {
    prompt: () => prompts.shift() ?? "",
  };
  const panel = createWorkspaceFolderExportsPanelRenderer({
    threadsUl,
    getWorkspaceExports: () => exportsList,
    getWorkspaceExportsStatus: () => exportsStatus,
    refreshWorkspaceExports: async () => {
      refreshCount += 1;
      return exportsList;
    },
    createWorkspaceExportOnServer: async (folderId, payload) => {
      createCalls.push({ folderId, payload });
      return { export_v1_user: { export_id: "created-export", workspace_folder_id: folderId } };
    },
    openWorkspaceExport: (folderId, exportId) => {
      openCalls.push({ folderId, exportId });
    },
    downloadWorkspaceExport: (folderId, exportId) => {
      downloadCalls.push({ folderId, exportId });
    },
    getCurrentThread: () => currentThread,
    renderThreads: () => {},
    setThreadStatus: (message, isError = false) => {
      statuses.push({ message, isError });
    },
    consoleObj: { warn() {} },
  });
  panel.appendExportRows(folder);
  return {
    threadsUl,
    createCalls,
    openCalls,
    downloadCalls,
    statuses,
    refreshCount: () => refreshCount,
  };
}

function linkedFolder(overrides = {}) {
  return {
    id: "folder-1",
    display_name: "Projet",
    nextcloud_sync_state: "linked",
    deleted_at: null,
    ...overrides,
  };
}

function currentConversation(overrides = {}) {
  return {
    id: "conversation-1",
    workspace_folder_id: "folder-1",
    title: "Conversation",
    ...overrides,
  };
}

function exportItem(overrides = {}) {
  return WorkspaceExports.normalizeWorkspaceExportItem({
    export_v1_user: {
      export_id: "export-1",
      workspace_folder_id: "folder-1",
      title: "Export visible",
      format: "md",
      status: "available",
      status_label: "disponible",
      byte_size: 2048,
      created_at: "2026-06-19T12:00:00Z",
      can_download: true,
      can_open: true,
      can_reuse_as_source: true,
      actions: {
        download_reason_code: "folder_export_download_ok",
        open_reason_code: "folder_export_download_ok",
        reuse_as_source_reason_code: "folder_export_reuse_ok",
      },
      ...overrides,
    },
  });
}

function assertCreatePayloadIsClean(payload) {
  for (const key of [
    "messages",
    "conversation_messages",
    "export_id",
    "content",
    "export_content",
    "export_bytes",
    "workspace_folder_id",
  ]) {
    assert.equal(Object.hasOwn(payload, key), false, `${key} must not be sent`);
  }
}

test("exports panel enables conversation creation only for linked folder current conversation", async () => {
  const rendered = buildPanel({
    prompts: ["txt", "Titre conversation"],
  });
  const createButton = firstByClass(rendered.threadsUl, "workspace-folder-export-create");

  assert.ok(createButton);
  assert.equal(createButton.disabled, false);
  createButton.click();
  await flushAsync();

  assert.equal(rendered.createCalls.length, 1);
  assert.equal(rendered.createCalls[0].folderId, "folder-1");
  assert.deepEqual(rendered.createCalls[0].payload, {
    source_kind: "conversation",
    conversation_id: "conversation-1",
    explicit_source: true,
    export_format: "txt",
    title: "Titre conversation",
  });
  assertCreatePayloadIsClean(rendered.createCalls[0].payload);
  assert.equal(rendered.refreshCount(), 1);
});

test("exports panel disables conversation creation outside the current linked folder", async () => {
  const noConversation = buildPanel({ currentThread: null, prompts: ["md", "Nope"] });
  const otherFolder = buildPanel({
    currentThread: currentConversation({ workspace_folder_id: "other-folder" }),
    prompts: ["md", "Nope"],
  });
  const localFolder = buildPanel({
    folder: linkedFolder({ nextcloud_sync_state: "local_only" }),
    prompts: ["md", "Nope"],
  });

  for (const rendered of [noConversation, otherFolder, localFolder]) {
    const createButton = firstByClass(rendered.threadsUl, "workspace-folder-export-create");
    assert.equal(createButton.disabled, true);
    createButton.click();
    await flushAsync();
    assert.equal(rendered.createCalls.length, 0);
  }
});

test("exports panel open and download buttons call only explicit namespaced action callbacks", () => {
  const rendered = buildPanel({
    exportsList: [exportItem()],
  });

  firstByClass(rendered.threadsUl, "workspace-folder-export-action-open").click();
  firstByClass(rendered.threadsUl, "workspace-folder-export-action-download").click();

  assert.deepEqual(rendered.openCalls, [{ folderId: "folder-1", exportId: "export-1" }]);
  assert.deepEqual(rendered.downloadCalls, [{ folderId: "folder-1", exportId: "export-1" }]);
  assert.equal(rendered.createCalls.length, 0);
});

test("exports panel keeps normal empty state when API returns an empty list", () => {
  const rendered = buildPanel({
    exportsList: [],
    exportsStatus: { status: "ok", reason_code: "workspace_exports_list_ok" },
  });

  assert.equal(firstByClass(rendered.threadsUl, "workspace-folder-export-error"), null);
  const empty = firstByClass(rendered.threadsUl, "workspace-folder-export-empty");
  assert.ok(empty);
  assert.equal(empty.textContent, "Aucun export");
});

test("exports panel renders API errors as visible errors instead of empty lists", () => {
  const rendered = buildPanel({
    exportsList: [],
    exportsStatus: {
      status: "error",
      reason_code: "folder_export_lookup_failed",
      details: "UNSAFE_TECHNICAL_DETAIL_SENTINEL",
    },
  });

  assert.equal(firstByClass(rendered.threadsUl, "workspace-folder-export-empty"), null);
  const error = firstByClass(rendered.threadsUl, "workspace-folder-export-error");
  assert.ok(error);
  assert.equal(error.dataset.reasonCode, "folder_export_lookup_failed");
  assert.match(visibleText(rendered.threadsUl), /Chargement des exports impossible/);
  assert.equal(visibleText(rendered.threadsUl).includes("Aucun export"), false);
  assert.equal(visibleText(rendered.threadsUl).includes("UNSAFE_TECHNICAL_DETAIL_SENTINEL"), false);
});

test("exports panel disabled open and download buttons do not call actions", () => {
  const rendered = buildPanel({
    exportsList: [exportItem({
      can_download: false,
      can_open: false,
      actions: {
        download_reason_code: "folder_export_not_linked",
        open_reason_code: "folder_export_not_linked",
        reuse_as_source_reason_code: "folder_export_reuse_ok",
      },
    })],
  });

  const openButton = firstByClass(rendered.threadsUl, "workspace-folder-export-action-open");
  const downloadButton = firstByClass(rendered.threadsUl, "workspace-folder-export-action-download");
  assert.equal(openButton.disabled, true);
  assert.equal(downloadButton.disabled, true);
  openButton.click();
  downloadButton.click();

  assert.deepEqual(rendered.openCalls, []);
  assert.deepEqual(rendered.downloadCalls, []);
});

test("exports panel reuse sends explicit source export payload only when enabled", async () => {
  const rendered = buildPanel({
    exportsList: [exportItem()],
    prompts: ["docx", "Titre reuse"],
  });

  firstByClass(rendered.threadsUl, "workspace-folder-export-action-reuse").click();
  await flushAsync();

  assert.equal(rendered.createCalls.length, 1);
  assert.deepEqual(rendered.createCalls[0].payload, {
    source_kind: "export",
    source_export_id: "export-1",
    explicit_source: true,
    export_format: "docx",
    title: "Titre reuse",
  });
  assertCreatePayloadIsClean(rendered.createCalls[0].payload);
});

test("exports panel disables reuse for pdf docx and server-denied exports", async () => {
  const pdf = exportItem({ export_id: "pdf-export", format: "pdf" });
  const docx = exportItem({ export_id: "docx-export", format: "docx" });
  const denied = exportItem({
    export_id: "denied-export",
    format: "md",
    can_reuse_as_source: false,
    actions: { reuse_as_source_reason_code: "folder_export_not_linked" },
  });
  const rendered = buildPanel({
    exportsList: [pdf, docx, denied],
    prompts: ["md", "Nope"],
  });
  const reuseButtons = byClass(rendered.threadsUl, "workspace-folder-export-action-reuse");

  assert.equal(reuseButtons.length, 3);
  for (const button of reuseButtons) {
    assert.equal(button.disabled, true);
    button.click();
  }
  await flushAsync();
  assert.equal(rendered.createCalls.length, 0);
});

test("exports panel renders no raw technical export fields", () => {
  const rendered = buildPanel({
    exportsList: [
      WorkspaceExports.normalizeWorkspaceExportItem({
        target_name: "UNSAFE_TARGET_SENTINEL",
        dav_url: "UNSAFE_DAV_SENTINEL",
        etag_value: "UNSAFE_ETAG_SENTINEL",
        xml_payload: "UNSAFE_XML_SENTINEL",
        export_content: "UNSAFE_CONTENT_SENTINEL",
        export_bytes: "UNSAFE_BINARY_SENTINEL",
        secret: "UNSAFE_PRIVATE_SENTINEL",
        export_v1_user: {
          export_id: "safe-export",
          workspace_folder_id: "folder-1",
          title: "Safe export",
          format: "md",
          status: "available",
          can_download: true,
          can_open: true,
          can_reuse_as_source: true,
          actions: {
            download_reason_code: "folder_export_download_ok",
            open_reason_code: "folder_export_download_ok",
            reuse_as_source_reason_code: "folder_export_reuse_ok",
          },
        },
      }),
    ],
  });

  const text = visibleText(rendered.threadsUl);
  assert.equal(text.includes("Safe export"), true);
  for (const forbidden of [
    "UNSAFE_TARGET_SENTINEL",
    "UNSAFE_DAV_SENTINEL",
    "UNSAFE_ETAG_SENTINEL",
    "UNSAFE_XML_SENTINEL",
    "UNSAFE_CONTENT_SENTINEL",
    "UNSAFE_BINARY_SENTINEL",
    "UNSAFE_PRIVATE_SENTINEL",
  ]) {
    assert.equal(text.includes(forbidden), false, `${forbidden} must not render`);
  }
});
