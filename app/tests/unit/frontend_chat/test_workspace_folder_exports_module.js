const test = require("node:test");
const assert = require("node:assert/strict");

const WorkspaceExports = require("../../../web/chat_workspace_folder_exports.js");
const {
  createChatThreadsSidebar,
} = require("../../../web/chat_threads_sidebar.js");

function makeElement(tagName = "div") {
  const element = {
    tagName: String(tagName || "div").toUpperCase(),
    children: [],
    parentElement: null,
    style: {},
    dataset: {},
    className: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    href: "",
    rel: "",
    download: "",
    clicked: false,
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains() { return false; },
    },
    appendChild(child) {
      child.parentElement = element;
      element.children.push(child);
      return child;
    },
    insertBefore(child) {
      child.parentElement = element;
      element.children.unshift(child);
      return child;
    },
    removeChild(child) {
      element.children = element.children.filter((item) => item !== child);
      child.parentElement = null;
      return child;
    },
    remove() {
      if (element.parentElement) {
        element.parentElement.removeChild(element);
      }
    },
    addEventListener() {},
    setAttribute(name, value) {
      element[name] = value;
    },
    removeAttribute(name) {
      delete element[name];
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    click() {
      element.clicked = true;
    },
  };
  return element;
}

function installFakeDom() {
  const body = makeElement("body");
  global.document = {
    body,
    createElement: makeElement,
  };
  return body;
}

function createLifecycle(fetchFn) {
  installFakeDom();
  const wrapper = makeElement("div");
  const threadsUl = makeElement("ul");
  wrapper.appendChild(threadsUl);
  return createChatThreadsSidebar({
    threadsUl,
    logEl: makeElement("div"),
    fetchFn,
    setHero: async () => {},
    closeSidebar: () => {},
    renderConversationMessage: () => {},
    scrollToBottom: () => {},
    consoleObj: { warn() {} },
  });
}

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    },
  };
}

test("workspace export normalizer keeps user fields and strips technical internals", () => {
  const item = WorkspaceExports.normalizeWorkspaceExportItem({
    id: "export-1",
    workspace_folder_id: "folder-1",
    target_name: "Raw-target.txt",
    dav_url: "https://example.invalid/remote.php/dav/files/raw",
    etag_value: "raw-etag",
    export_content: "RAW SHOULD NOT SURVIVE",
    export_v1_technical: {
      target_name: "Raw-target.txt",
      dav_path: "/remote.php/dav/files/raw",
      content_hash: "abc123def456",
    },
    export_v1_user: {
      export_id: "export-1",
      workspace_folder_id: "folder-1",
      title: "Export visible",
      format: "txt",
      source_kind: "conversation",
      status: "available",
      status_label: "disponible",
      byte_size: 4096,
      created_at: "2026-06-19T12:00:00Z",
      can_download: true,
      can_open: true,
      can_reuse_as_source: true,
      actions: {
        download_reason_code: "folder_export_download_ok",
        open_reason_code: "folder_export_download_ok",
        reuse_as_source_reason_code: "folder_export_reuse_ok",
      },
    },
  });

  assert.equal(item.title, "Export visible");
  assert.equal(item.format, "txt");
  assert.equal(item.can_download, true);
  assert.equal(item.can_open, true);
  assert.equal(item.can_reuse_as_source, true);
  assert.equal(WorkspaceExports.compactWorkspaceExportMeta(item), "TXT · 4 ko · 19/06/2026 · disponible");
  const serialized = JSON.stringify(item);
  assert.equal(serialized.includes("Raw-target"), false);
  assert.equal(serialized.includes("remote.php"), false);
  assert.equal(serialized.includes("raw-etag"), false);
  assert.equal(serialized.includes("RAW SHOULD NOT SURVIVE"), false);
});

test("workspace export actions stay disabled for deleted or unsupported exports", () => {
  const deleted = WorkspaceExports.normalizeWorkspaceExportItem({
    id: "deleted-export",
    workspace_folder_id: "folder-1",
    export_v1_user: {
      export_id: "deleted-export",
      workspace_folder_id: "folder-1",
      title: "Supprime",
      format: "md",
      status: "deleted",
      reason_code: "folder_export_deleted",
      can_download: false,
      can_open: false,
      can_reuse_as_source: false,
      actions: {
        download_reason_code: "folder_export_deleted",
        open_reason_code: "folder_export_deleted",
        reuse_as_source_reason_code: "folder_export_deleted",
      },
    },
  });
  const pdf = WorkspaceExports.normalizeWorkspaceExportItem({
    id: "pdf-export",
    workspace_folder_id: "folder-1",
    export_v1_user: {
      export_id: "pdf-export",
      workspace_folder_id: "folder-1",
      title: "Rapport PDF",
      format: "pdf",
      status: "available",
      can_download: true,
      can_open: true,
      can_reuse_as_source: true,
      actions: {
        reuse_as_source_reason_code: "folder_export_source_format_unsupported",
      },
    },
  });

  assert.equal(deleted.can_download, false);
  assert.equal(deleted.can_open, false);
  assert.equal(deleted.can_reuse_as_source, false);
  assert.equal(pdf.can_download, true);
  assert.equal(pdf.can_open, true);
  assert.equal(pdf.can_reuse_as_source, false);
  assert.equal(
    WorkspaceExports.workspaceExportActionLabel(pdf, "reuse"),
    "Format source non reutilisable.",
  );
});

test("workspace export route builders never use a global exports route", () => {
  const list = WorkspaceExports.buildWorkspaceExportsListPath("folder 1");
  const open = WorkspaceExports.buildWorkspaceExportContentPath("folder 1", "export/1", "open");
  const download = WorkspaceExports.buildWorkspaceExportContentPath("folder 1", "export/1", "download");

  assert.equal(list, "/api/workspace-folders/folder%201/exports");
  assert.equal(open, "/api/workspace-folders/folder%201/exports/export%2F1/open");
  assert.equal(download, "/api/workspace-folders/folder%201/exports/export%2F1/download");
  assert.equal(list.startsWith("/api/exports"), false);
  assert.equal(open.startsWith("/api/exports"), false);
  assert.equal(download.startsWith("/api/exports"), false);
});

test("workspace export create payloads are explicit and content-free", () => {
  const conversation = WorkspaceExports.buildConversationExportPayload({
    conversationId: "conversation-1",
    exportFormat: "docx",
    title: "Conversation",
  });
  const reuse = WorkspaceExports.buildReuseExportPayload({
    sourceExportId: "export-1",
    exportFormat: "md",
    title: "Reuse",
  });

  assert.deepEqual(conversation, {
    source_kind: "conversation",
    conversation_id: "conversation-1",
    explicit_source: true,
    export_format: "docx",
    title: "Conversation",
  });
  assert.deepEqual(reuse, {
    source_kind: "export",
    source_export_id: "export-1",
    explicit_source: true,
    export_format: "md",
    title: "Reuse",
  });
  for (const payload of [conversation, reuse]) {
    assert.equal(Object.hasOwn(payload, "export_id"), false);
    assert.equal(Object.hasOwn(payload, "messages"), false);
    assert.equal(Object.hasOwn(payload, "conversation_messages"), false);
    assert.equal(Object.hasOwn(payload, "content"), false);
    assert.equal(Object.hasOwn(payload, "workspace_folder_id"), false);
  }
});

test("workspace export errors render sober labels without technical details", () => {
  const conflict = WorkspaceExports.workspaceExportUserError({
    reason_code: "folder_export_name_conflict",
    error: "Raw target_name /remote.php/dav/files/raw with ETag secret",
  });
  const unknownUnsafe = WorkspaceExports.workspaceExportUserError({
    reason_code: "unknown",
    error: "remote.php target_name raw content",
  });

  assert.equal(conflict, "Un export existe deja avec ce nom.");
  assert.equal(unknownUnsafe, "Action export impossible.");
  assert.equal(conflict.includes("remote.php"), false);
  assert.equal(unknownUnsafe.includes("target_name"), false);
});

test("threads lifecycle lists and creates exports through the folder namespace", async () => {
  const calls = [];
  const lifecycle = createLifecycle(async (url, options = {}) => {
    calls.push({ url, options });
    if (options.method === "POST") {
      return jsonResponse({
        ok: true,
        export: {
          export_v1_user: {
            export_id: "export-created",
            workspace_folder_id: "folder-1",
            title: "Created",
            format: "md",
          },
        },
      });
    }
    return jsonResponse({
      ok: true,
      exports: [{
        export_v1_user: {
          export_id: "export-1",
          workspace_folder_id: "folder-1",
          title: "Listed",
          format: "md",
          can_download: true,
          can_open: true,
          can_reuse_as_source: true,
          actions: {
            download_reason_code: "folder_export_download_ok",
            open_reason_code: "folder_export_download_ok",
            reuse_as_source_reason_code: "folder_export_reuse_ok",
          },
        },
      }],
    });
  });

  const listed = await lifecycle.listWorkspaceExportsFromServer("folder-1");
  const payload = WorkspaceExports.buildReuseExportPayload({
    sourceExportId: "export-1",
    exportFormat: "txt",
    title: "Reuse listed",
  });
  await lifecycle.createWorkspaceExportOnServer("folder-1", payload);

  assert.equal(listed.length, 1);
  assert.equal(calls[0].url, "/api/workspace-folders/folder-1/exports");
  assert.equal(calls[1].url, "/api/workspace-folders/folder-1/exports");
  assert.equal(calls[1].options.method, "POST");
  const body = JSON.parse(calls[1].options.body);
  assert.equal(body.source_kind, "export");
  assert.equal(body.source_export_id, "export-1");
  assert.equal(body.explicit_source, true);
  assert.equal(Object.hasOwn(body, "export_id"), false);
  assert.equal(Object.hasOwn(body, "messages"), false);
  assert.equal(calls.some((call) => String(call.url).startsWith("/api/exports")), false);
});

test("threads lifecycle open and download use namespaced content routes", () => {
  const opened = [];
  global.window = {
    open: (href, target, features) => opened.push({ href, target, features }),
  };
  const lifecycle = createLifecycle(async () => jsonResponse({ ok: true, exports: [] }));
  const body = global.document.body;

  const openPath = lifecycle.openWorkspaceExport("folder-1", "export-1");
  const downloadPath = lifecycle.downloadWorkspaceExport("folder-1", "export-1");

  assert.equal(openPath, "/api/workspace-folders/folder-1/exports/export-1/open");
  assert.deepEqual(opened, [{
    href: "/api/workspace-folders/folder-1/exports/export-1/open",
    target: "_blank",
    features: "noopener",
  }]);
  assert.equal(downloadPath, "/api/workspace-folders/folder-1/exports/export-1/download");
  assert.equal(body.children.some((child) => child.href === downloadPath), false);
  assert.equal(openPath.startsWith("/api/exports"), false);
  assert.equal(downloadPath.startsWith("/api/exports"), false);
});
