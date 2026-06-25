const test = require("node:test");
const assert = require("node:assert/strict");

const {
  THREADS_PAGE_SIZE,
  MAX_TITLE_LENGTH,
  WORKSPACE_CONVERSATION_DRAG_MIME,
  clampThreadTitle,
  normalizeThreadItem,
  createChatThreadsSidebar,
} = require("../../../web/chat_threads_sidebar.js");

function makeElement(tagName = "div") {
  const listeners = new Map();
  const classes = new Set();
  const element = {
    tagName: String(tagName || "div").toUpperCase(),
    children: [],
    parentElement: null,
    style: {},
    dataset: {},
    className: "",
    textContent: "",
    tabIndex: 0,
    draggable: false,
    events: listeners,
    classList: {
      add(name) {
        for (const existing of String(element.className || "").split(/\s+/).filter(Boolean)) {
          classes.add(existing);
        }
        classes.add(name);
        element.className = Array.from(classes).join(" ");
      },
      remove(name) {
        for (const existing of String(element.className || "").split(/\s+/).filter(Boolean)) {
          classes.add(existing);
        }
        classes.delete(name);
        element.className = Array.from(classes).join(" ");
      },
      contains(name) {
        return classes.has(name);
      },
    },
    appendChild(child) {
      child.parentElement = element;
      element.children.push(child);
      return child;
    },
    insertBefore(child, before) {
      child.parentElement = element;
      const index = element.children.indexOf(before);
      if (index >= 0) {
        element.children.splice(index, 0, child);
      } else {
        element.children.push(child);
      }
      return child;
    },
    addEventListener(type, handler) {
      const key = String(type || "");
      const current = listeners.get(key) || [];
      current.push(handler);
      listeners.set(key, current);
    },
    click() {
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
  };
  let html = "";
  Object.defineProperty(element, "innerHTML", {
    get() {
      return html;
    },
    set(value) {
      html = String(value || "");
      if (!html) element.children = [];
    },
  });
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

function response(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

function buildSidebarWithFetch(fetchFn) {
  installDom();
  const wrapper = makeElement("div");
  const threadsUl = makeElement("ul");
  wrapper.appendChild(threadsUl);
  const logEl = makeElement("div");
  const statuses = [];
  const sidebar = createChatThreadsSidebar({
    threadsUl,
    logEl,
    fetchFn,
    setHero: async () => {},
    closeSidebar: () => {},
    renderConversationMessage: () => {},
    scrollToBottom: () => {},
    notesModeController: {},
    consoleObj: { warn() {} },
  });
  const originalSetStatus = sidebar.setThreadStatus;
  if (typeof originalSetStatus === "function") {
    sidebar.setThreadStatus = (message, isError = false) => {
      statuses.push({ message, isError });
      originalSetStatus(message, isError);
    };
  }
  return { sidebar, statuses, threadsUl };
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

function expandFirstFolder(threadsUl) {
  const toggle = firstByClass(threadsUl, "workspace-folder-toggle");
  assert.ok(toggle);
  toggle.click();
}

test("threads sidebar module exposes the conversations page size contract", () => {
  assert.equal(THREADS_PAGE_SIZE, 200);
  assert.equal(WORKSPACE_CONVERSATION_DRAG_MIME, "application/x-fridadev-conversation-id");
});

test("clampThreadTitle normalizes whitespace and preserves the fallback contract", () => {
  assert.equal(clampThreadTitle("  Mon   fil   "), "Mon fil");
  assert.equal(clampThreadTitle("   "), "Nouvelle conversation");
  assert.equal(clampThreadTitle("   ", ""), "");
});

test("clampThreadTitle truncates long labels without changing the max length", () => {
  const longTitle = "x".repeat(MAX_TITLE_LENGTH + 10);
  const clamped = clampThreadTitle(longTitle);

  assert.equal(clamped.length, MAX_TITLE_LENGTH + 1);
  assert.equal(clamped.endsWith("…"), true);
});

test("normalizeThreadItem keeps the stable sidebar shape and cached messages", () => {
  const cachedMessages = [{ role: "user", content: "bonjour", timestamp: null }];

  assert.deepEqual(
    normalizeThreadItem(
      {
        conversation_id: "conv-1",
        title: "  Titre ",
        created_at: "2026-05-03T10:00:00Z",
        message_count: "2",
        last_message_preview: "hello",
      },
      cachedMessages,
    ),
    {
      id: "conv-1",
      conversation_id: "conv-1",
      title: "Titre",
      messages: cachedMessages,
      created_at: "2026-05-03T10:00:00Z",
      updated_at: "2026-05-03T10:00:00Z",
      message_count: 2,
      last_message_preview: "hello",
      workspace_folder_id: null,
      deleted_at: null,
    },
  );
});

test("normalizeThreadItem keeps nullable workspace folder assignments", () => {
  const normalized = normalizeThreadItem({
    id: "conv-2",
    title: "Dans dossier",
    workspace_folder_id: "folder-1",
  });

  assert.equal(normalized.workspace_folder_id, "folder-1");
});

test("normalizeThreadItem rejects malformed conversation identifiers", () => {
  assert.equal(normalizeThreadItem({ title: "sans id" }), null);
});

test("threads sidebar keeps exports and images API errors distinct from empty lists", async () => {
  const calls = [];
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    calls.push(path);
    if (path.startsWith("/api/conversations?")) {
      return response(200, {
        ok: true,
        items: [
          {
            id: "conv-1",
            title: "Conversation",
            workspace_folder_id: "folder-1",
          },
        ],
      });
    }
    if (path === "/api/workspace-folders") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "folder-1",
            display_name: "Projet",
            nextcloud_sync_state: "linked",
            deleted_at: null,
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/files") {
      return response(200, { ok: true, files: [] });
    }
    if (path === "/api/workspace-folders/folder-1/exports") {
      return response(503, {
        ok: false,
        reason_code: "folder_export_lookup_failed",
        details: "UNSAFE_TECHNICAL_DETAIL_SENTINEL",
      });
    }
    if (path === "/api/workspace-folders/folder-1/generated-images") {
      return response(200, {
        ok: false,
        reason_code: "folder_generated_image_lookup_failed",
        details: "UNSAFE_TECHNICAL_DETAIL_SENTINEL",
      });
    }
    if (path === "/api/workspace-folders/folder-1/notes") {
      return response(200, { ok: true, notes: [] });
    }
    if (path === "/api/conversations/conv-1/workspace-file-selections") {
      return response(200, { ok: true, selections: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.equal(calls.includes("/api/workspace-folders/folder-1/exports"), true);
  assert.equal(calls.includes("/api/workspace-folders/folder-1/generated-images"), true);
  assert.deepEqual(sidebar.getWorkspaceExports("folder-1"), []);
  assert.deepEqual(sidebar.getWorkspaceGeneratedImages("folder-1"), []);
  assert.deepEqual(sidebar.getWorkspaceExportsStatus("folder-1"), {
    status: "error",
    reason_code: "folder_export_lookup_failed",
  });
  assert.deepEqual(sidebar.getWorkspaceGeneratedImagesStatus("folder-1"), {
    status: "error",
    reason_code: "folder_generated_image_lookup_failed",
  });
  assert.equal(JSON.stringify(sidebar.getWorkspaceExportsStatus("folder-1")).includes("UNSAFE_TECHNICAL_DETAIL_SENTINEL"), false);
  assert.equal(JSON.stringify(sidebar.getWorkspaceGeneratedImagesStatus("folder-1")).includes("UNSAFE_TECHNICAL_DETAIL_SENTINEL"), false);
});

test("threads sidebar keeps files API errors distinct from empty lists", async () => {
  const { sidebar, threadsUl } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path.startsWith("/api/conversations?")) {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "folder-1",
            display_name: "Projet",
            nextcloud_sync_state: "linked",
            deleted_at: null,
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/files") {
      return response(500, {
        ok: false,
        reason_code: "workspace_files_lookup_failed",
        details: "UNSAFE_TECHNICAL_DETAIL_SENTINEL",
      });
    }
    if (path === "/api/workspace-folders/folder-1/exports") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/generated-images") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/notes") {
      return response(200, { ok: true, notes: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.deepEqual(sidebar.getWorkspaceFiles("folder-1"), []);
  assert.deepEqual(sidebar.getWorkspaceFilesStatus("folder-1"), {
    status: "error",
    reason_code: "workspace_files_lookup_failed",
  });
  assert.equal(JSON.stringify(sidebar.getWorkspaceFilesStatus("folder-1")).includes("UNSAFE_TECHNICAL_DETAIL_SENTINEL"), false);

  sidebar.renderThreads();
  expandFirstFolder(threadsUl);
  assert.equal(firstByClass(threadsUl, "workspace-folder-file-empty"), null);
  const error = firstByClass(threadsUl, "workspace-folder-file-error");
  assert.ok(error);
  assert.equal(error.dataset.reasonCode, "workspace_files_lookup_failed");
  assert.match(visibleText(threadsUl), /Chargement des fichiers impossible/);
  assert.equal(visibleText(threadsUl).includes("Aucun fichier"), false);
  assert.equal(visibleText(threadsUl).includes("UNSAFE_TECHNICAL_DETAIL_SENTINEL"), false);
});

test("threads sidebar keeps normal empty files state when API returns an empty list", async () => {
  const { sidebar, threadsUl } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path.startsWith("/api/conversations?")) {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "folder-1",
            display_name: "Projet",
            nextcloud_sync_state: "linked",
            deleted_at: null,
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/files") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/exports") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/generated-images") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/notes") {
      return response(200, { ok: true, notes: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.deepEqual(sidebar.getWorkspaceFilesStatus("folder-1"), {
    status: "ok",
    reason_code: "workspace_files_list_ok",
  });
  sidebar.renderThreads();
  expandFirstFolder(threadsUl);
  assert.equal(firstByClass(threadsUl, "workspace-folder-file-error"), null);
  const empty = firstByClass(threadsUl, "workspace-folder-file-empty");
  assert.ok(empty);
  assert.equal(empty.textContent, "Aucun fichier");
});

test("threads sidebar treats malformed files payloads as load errors", async () => {
  const { sidebar, threadsUl } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path.startsWith("/api/conversations?")) {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "folder-1",
            display_name: "Projet",
            nextcloud_sync_state: "linked",
            deleted_at: null,
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/files") {
      return response(200, { ok: true, unexpected: [] });
    }
    if (path === "/api/workspace-folders/folder-1/exports") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/generated-images") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/notes") {
      return response(200, { ok: true, notes: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.deepEqual(sidebar.getWorkspaceFilesStatus("folder-1"), {
    status: "error",
    reason_code: "workspace_files_lookup_failed",
  });
  sidebar.renderThreads();
  expandFirstFolder(threadsUl);
  assert.equal(firstByClass(threadsUl, "workspace-folder-file-empty"), null);
  assert.match(visibleText(threadsUl), /Chargement des fichiers impossible/);
});

test("threads sidebar renders existing file controls when files list is ok", async () => {
  const { sidebar, threadsUl } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path.startsWith("/api/conversations?")) {
      return response(200, {
        ok: true,
        items: [
          {
            id: "conv-1",
            title: "Conversation",
            workspace_folder_id: "folder-1",
          },
        ],
      });
    }
    if (path === "/api/workspace-folders") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "folder-1",
            display_name: "Projet",
            nextcloud_sync_state: "linked",
            deleted_at: null,
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/files") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "file-1",
            workspace_folder_id: "folder-1",
            display_name: "Document visible",
            source_extension: ".pdf",
            status: "active",
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/exports") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/generated-images") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders/folder-1/notes") {
      return response(200, { ok: true, notes: [] });
    }
    if (path === "/api/conversations/conv-1/workspace-file-selections") {
      return response(200, { ok: true, selections: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.equal(sidebar.getWorkspaceFiles("folder-1").length, 1);
  assert.equal(sidebar.getWorkspaceFilesStatus("folder-1").status, "ok");
  sidebar.renderThreads();
  expandFirstFolder(threadsUl);
  assert.equal(firstByClass(threadsUl, "workspace-folder-file-error"), null);
  assert.match(visibleText(threadsUl), /Document visible/);
  assert.ok(firstByClass(threadsUl, "workspace-folder-file-select"));
  assert.ok(firstByClass(threadsUl, "workspace-folder-file-delete"));
});

test("threads sidebar treats malformed exports and images payloads as load errors", async () => {
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path.startsWith("/api/conversations?")) {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/workspace-folders") {
      return response(200, {
        ok: true,
        items: [
          {
            id: "folder-1",
            display_name: "Projet",
            nextcloud_sync_state: "linked",
            deleted_at: null,
          },
        ],
      });
    }
    if (path === "/api/workspace-folders/folder-1/files") {
      return response(200, { ok: true, files: [] });
    }
    if (path === "/api/workspace-folders/folder-1/exports") {
      return response(200, { ok: true, unexpected: [] });
    }
    if (path === "/api/workspace-folders/folder-1/generated-images") {
      return response(200, { ok: true, unexpected: [] });
    }
    if (path === "/api/workspace-folders/folder-1/notes") {
      return response(200, { ok: true, notes: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.equal(sidebar.getWorkspaceExportsStatus("folder-1").status, "error");
  assert.equal(sidebar.getWorkspaceExportsStatus("folder-1").reason_code, "folder_export_lookup_failed");
  assert.equal(sidebar.getWorkspaceGeneratedImagesStatus("folder-1").status, "error");
  assert.equal(
    sidebar.getWorkspaceGeneratedImagesStatus("folder-1").reason_code,
    "folder_generated_image_lookup_failed",
  );
});
