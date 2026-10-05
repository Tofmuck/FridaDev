const test = require("node:test");
const assert = require("node:assert/strict");

const ThreadsSidebarModule = require("../../../web/chat_threads_sidebar.js");
const {
  THREADS_PAGE_SIZE,
  MAX_TITLE_LENGTH,
  WORKSPACE_CONVERSATION_DRAG_MIME,
  clampThreadTitle,
  normalizeThreadItem,
  createChatThreadsSidebar,
} = ThreadsSidebarModule;

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

function conversationPage(items, total, offset = 0, limit = THREADS_PAGE_SIZE) {
  return response(200, {
    ok: true,
    items,
    total,
    limit,
    offset,
  });
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
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
  assert.deepEqual(Object.keys(ThreadsSidebarModule), [
    "THREADS_PAGE_SIZE",
    "MAX_TITLE_LENGTH",
    "WORKSPACE_CONVERSATION_DRAG_MIME",
    "clampThreadTitle",
    "normalizeThreadItem",
    "createChatThreadsSidebar",
  ]);
});

test("workspace OCR client preserves the actual HTTP creation and update status", async () => {
  const responseStatuses = [201, 200];
  const { sidebar } = buildSidebarWithFetch(async (url, init = {}) => {
    assert.equal(String(url), "/api/workspace-folders/folder-1/files/file-1/ocr");
    assert.equal(String(init.method || "GET"), "POST");
    const status = responseStatuses.shift();
    return response(status, {
      ok: true,
      file: { id: "derived-1", source_kind: "ocr_derived", source_file_id: "file-1" },
    });
  });

  assert.deepEqual(await sidebar.ocrWorkspaceFileOnServer("folder-1", "file-1"), {
    status: 201,
    file: { id: "derived-1", source_kind: "ocr_derived", source_file_id: "file-1" },
  });
  assert.deepEqual(await sidebar.ocrWorkspaceFileOnServer("folder-1", "file-1"), {
    status: 200,
    file: { id: "derived-1", source_kind: "ocr_derived", source_file_id: "file-1" },
  });
  assert.deepEqual(responseStatuses, []);
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

test("threads sidebar loads every conversation page once and preserves server order", async () => {
  const conversations = Array.from({ length: 205 }, (_value, index) => ({
    id: `conv-${String(index + 1).padStart(3, "0")}`,
    title: `Conversation ${index + 1}`,
  }));
  const calls = [];
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    calls.push(path);
    if (path === "/api/conversations?limit=200&offset=0") {
      return conversationPage(conversations.slice(0, 200), 205, 0);
    }
    if (path === "/api/conversations?limit=200&offset=200") {
      return conversationPage(conversations.slice(200), 205, 200);
    }
    if (path === "/api/workspace-folders") {
      return response(200, { ok: true, items: [] });
    }
    if (path === "/api/conversations/conv-205/workspace-file-selections") {
      return response(200, { ok: true, selections: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });

  sidebar.saveThreads([normalizeThreadItem({ id: "conv-205", title: "Ancienne 205" })]);
  sidebar.setCurrentId("conv-205");
  sidebar.appendMessageToThread("conv-205", "assistant", "cache conservé");

  assert.equal(await sidebar.refreshThreadsFromServer({ keepSelection: true }), true);
  assert.equal(sidebar.getThreads().length, 205);
  assert.deepEqual(sidebar.getThreads().map((item) => item.id), conversations.map((item) => item.id));
  assert.equal(new Set(sidebar.getThreads().map((item) => item.id)).size, 205);
  assert.equal(sidebar.getCurrentId(), "conv-205");
  assert.equal(sidebar.getThreadById("conv-205").messages[0].content, "cache conservé");
  assert.deepEqual(calls.filter((path) => path.startsWith("/api/conversations?")), [
    "/api/conversations?limit=200&offset=0",
    "/api/conversations?limit=200&offset=200",
  ]);
});

test("threads sidebar keeps its prior state when a later conversation page fails", async () => {
  const firstPage = Array.from({ length: 200 }, (_value, index) => ({
    id: `new-${index + 1}`,
    title: `Nouvelle ${index + 1}`,
  }));
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path === "/api/conversations?limit=200&offset=0") {
      return conversationPage(firstPage, 201, 0);
    }
    if (path === "/api/conversations?limit=200&offset=200") {
      return response(503, { ok: false, reason_code: "conversation_list_failed" });
    }
    if (path === "/api/workspace-folders") {
      return response(200, { ok: true, items: [] });
    }
    throw new Error(`unexpected test url ${path}`);
  });
  const previous = [normalizeThreadItem({ id: "conv-existing", title: "Existante" })];
  sidebar.saveThreads(previous);
  sidebar.setCurrentId("conv-existing");

  assert.equal(await sidebar.refreshThreadsFromServer({ keepSelection: true }), false);
  assert.deepEqual(sidebar.getThreads(), previous);
  assert.equal(sidebar.getCurrentId(), "conv-existing");
});

test("threads sidebar stops after one complete conversation page", async () => {
  const calls = [];
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    calls.push(String(url || ""));
    return conversationPage(
      [
        { id: "conv-1", title: "Une" },
        { id: "conv-2", title: "Deux" },
      ],
      2,
      0,
    );
  });

  const items = await sidebar.listConversationsFromServer();

  assert.deepEqual(items.map((item) => item.id), ["conv-1", "conv-2"]);
  assert.deepEqual(calls, ["/api/conversations?limit=200&offset=0"]);
});

test("threads sidebar rejects a short conversation page before total without looping", async () => {
  const calls = [];
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    calls.push(String(url || ""));
    return conversationPage(
      Array.from({ length: 100 }, (_value, index) => ({ id: `conv-${index + 1}` })),
      250,
      0,
    );
  });

  await assert.rejects(
    sidebar.listConversationsFromServer(),
    (err) => err?.payload?.reason_code === "conversation_list_page_inconsistent",
  );
  assert.deepEqual(calls, ["/api/conversations?limit=200&offset=0"]);
});

test("threads sidebar rejects duplicate conversations across pages", async () => {
  const firstPage = Array.from({ length: 200 }, (_value, index) => ({
    id: `conv-${index + 1}`,
  }));
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    if (path === "/api/conversations?limit=200&offset=0") {
      return conversationPage(firstPage, 201, 0);
    }
    if (path === "/api/conversations?limit=200&offset=200") {
      return conversationPage([{ id: "conv-1" }], 201, 200);
    }
    throw new Error(`unexpected test url ${path}`);
  });

  await assert.rejects(
    sidebar.listConversationsFromServer(),
    (err) => err?.payload?.reason_code === "conversation_list_page_inconsistent",
  );
});

test("thread loading keeps a late conversation response out of the current conversation view", async () => {
  installDom();
  const wrapper = makeElement("div");
  const threadsUl = makeElement("ul");
  wrapper.appendChild(threadsUl);
  const logEl = makeElement("div");
  const rendered = [];
  const slowMessages = deferred();
  const slowStarted = deferred();
  let slowMessageFetches = 0;
  const sidebar = createChatThreadsSidebar({
    threadsUl,
    logEl,
    fetchFn: async (url) => {
      const path = String(url || "");
      if (path === "/api/conversations/conv-a/messages") {
        slowMessageFetches += 1;
        slowStarted.resolve();
        return slowMessages.promise;
      }
      if (path === "/api/conversations/conv-b/messages") {
        return response(200, { ok: true, title: "B", messages: [{ role: "assistant", content: "message-b" }] });
      }
      if (path.endsWith("/workspace-file-selections")) {
        return response(200, { ok: true, selections: [] });
      }
      throw new Error(`unexpected test url ${path}`);
    },
    setHero: async () => {},
    closeSidebar: () => {},
    renderConversationMessage: (message) => rendered.push(message.content),
    scrollToBottom: () => {},
    notesModeController: {},
    consoleObj: { warn() {} },
  });
  sidebar.saveThreads([
    normalizeThreadItem({ id: "conv-a", title: "A" }),
    normalizeThreadItem({ id: "conv-b", title: "B" }),
  ]);

  sidebar.setCurrentId("conv-a");
  const loadA = sidebar.loadThread("conv-a");
  await slowStarted.promise;
  sidebar.setCurrentId("conv-b");
  await sidebar.loadThread("conv-b");
  slowMessages.resolve(response(200, {
    ok: true,
    title: "A",
    messages: [{ role: "assistant", content: "message-a" }],
  }));
  await loadA;

  assert.equal(sidebar.getCurrentId(), "conv-b");
  assert.deepEqual(rendered, ["message-b"]);

  rendered.length = 0;
  sidebar.setCurrentId("conv-a");
  await sidebar.loadThread("conv-a");
  assert.deepEqual(rendered, ["message-a"]);
  assert.equal(slowMessageFetches, 1, "the stale response may safely populate only A's indexed cache");
});

test("thread loading ignores a late stale error but keeps a current error visible", async () => {
  installDom();
  const wrapper = makeElement("div");
  const threadsUl = makeElement("ul");
  wrapper.appendChild(threadsUl);
  const logEl = makeElement("div");
  const staleFailure = deferred();
  const staleStarted = deferred();
  const sidebar = createChatThreadsSidebar({
    threadsUl,
    logEl,
    fetchFn: async (url) => {
      const path = String(url || "");
      if (path === "/api/conversations/conv-a/messages") {
        staleStarted.resolve();
        return staleFailure.promise;
      }
      if (path === "/api/conversations/conv-b/messages") {
        return response(200, { ok: true, messages: [{ role: "assistant", content: "message-b" }] });
      }
      if (path === "/api/conversations/conv-c/messages") {
        throw new Error("current failure");
      }
      if (path.endsWith("/workspace-file-selections")) {
        return response(200, { ok: true, selections: [] });
      }
      throw new Error(`unexpected test url ${path}`);
    },
    setHero: async () => {},
    closeSidebar: () => {},
    renderConversationMessage: () => {},
    scrollToBottom: () => {},
    notesModeController: {},
    consoleObj: { warn() {} },
  });
  sidebar.saveThreads([
    normalizeThreadItem({ id: "conv-a", title: "A" }),
    normalizeThreadItem({ id: "conv-b", title: "B" }),
    normalizeThreadItem({ id: "conv-c", title: "C" }),
  ]);

  sidebar.setCurrentId("conv-a");
  const loadA = sidebar.loadThread("conv-a");
  await staleStarted.promise;
  sidebar.setCurrentId("conv-b");
  await sidebar.loadThread("conv-b");
  staleFailure.reject(new Error("stale failure"));
  await loadA;

  const threadStatus = wrapper.children[0];
  assert.equal(threadStatus.textContent, "");
  assert.equal(threadStatus.style.display, "none");

  sidebar.setCurrentId("conv-c");
  await sidebar.loadThread("conv-c");
  assert.equal(threadStatus.textContent, "Impossible de charger cette conversation.");
  assert.equal(threadStatus.style.display, "block");
});

test("threads sidebar keeps exports and images API errors distinct from empty lists", async () => {
  const calls = [];
  const { sidebar } = buildSidebarWithFetch(async (url) => {
    const path = String(url || "");
    calls.push(path);
    if (path.startsWith("/api/conversations?")) {
      return conversationPage(
        [
          {
            id: "conv-1",
            title: "Conversation",
            workspace_folder_id: "folder-1",
          },
        ],
        1,
      );
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
      return conversationPage([], 0);
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
      return conversationPage([], 0);
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
      return conversationPage([], 0);
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
      return conversationPage(
        [
          {
            id: "conv-1",
            title: "Conversation",
            workspace_folder_id: "folder-1",
          },
        ],
        1,
      );
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
      return conversationPage([], 0);
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

// Publication ordering uses controlled responses, never wall-clock sleeps.
function inventoryFileResponse(id, folderId = 'folder-a') {
  return response(200, { ok: true, items: id ? [{
    id, workspace_folder_id: folderId, display_name: `${id}.md`,
    source_extension: '.md', status: 'active', content_kind: 'document', media_kind: 'text',
  }] : [] });
}
function inventoryErrorResponse() {
  return response(503, { ok: false, reason_code: 'workspace_files_lookup_failed' });
}
function inventoryHarness(onFiles, onFolders) {
  const folders = ['folder-a', 'folder-b'].map(id => ({ id, display_name: id, nextcloud_sync_state: 'linked' }));
  const calls = [];
  const { sidebar } = buildSidebarWithFetch(async url => {
    const path = String(url);
    if (path.startsWith('/api/conversations?')) return conversationPage([], 0);
    if (path === '/api/workspace-folders') return onFolders ? onFolders() : response(200, { ok: true, items: folders });
    if (path.endsWith('/files')) {
      const folderId = path.split('/')[3];
      calls.push(folderId);
      return onFiles(folderId);
    }
    return response(200, { ok: true, items: [] });
  });
  sidebar.saveWorkspaceFolders(folders);
  return { sidebar, folders, calls };
}
function assertInventory(sidebar, id, status = 'ok') {
  assert.deepEqual(sidebar.getWorkspaceFiles('folder-a').map(file => file.id), id ? [id] : []);
  assert.deepEqual(sidebar.getWorkspaceFilesStatus('folder-a'), {
    status, reason_code: status === 'ok' ? 'workspace_files_list_ok' : 'workspace_files_lookup_failed',
  });
}

for (const failure of [false, true]) {
  test(`P2-M2-03 distinguishes ${failure ? '503 error' : 'valid empty list'}`, async () => {
    const folders = ['folder-a', 'folder-b'].map(id => ({
      id, display_name: id, nextcloud_sync_state: 'linked',
    }));
    let second = false;
    const { sidebar, threadsUl } = buildSidebarWithFetch(async url => {
      if (url.startsWith('/api/conversations?')) return conversationPage([], 0);
      if (url === '/api/workspace-folders') {
        if (!second) return response(200, { ok: true, items: folders });
        return failure
          ? response(503, { ok: false, reason_code: 'synthetic_folders_unavailable' })
          : response(200, { ok: true, items: [] });
      }
      if (url.endsWith('/files')) return response(200, {
        ok: true, items: [{
          id: 'file-a', workspace_folder_id: url.split('/')[3],
          display_name: 'synthetic.md', content_kind: 'document',
          media_kind: 'text', status: 'active',
        }],
      });
      return response(200, { ok: true, items: [] });
    });
    assert.equal(await sidebar.refreshThreadsFromServer(), true);
    assert.equal(sidebar.getWorkspaceFolders().length, 2);
    assert.equal(sidebar.getWorkspaceFiles('folder-a').length, 1);
    second = true;
    const accepted = await sidebar.refreshThreadsFromServer();
    console.log(JSON.stringify({ finding: 'P2-M2-03', failure, accepted,
      folders: sidebar.getWorkspaceFolders().length, files: sidebar.getWorkspaceFiles('folder-a').length }));
    assert.equal(accepted, !failure);
    assert.equal(sidebar.getWorkspaceFolders().length, failure ? 2 : 0);
    assert.equal(sidebar.getWorkspaceFiles('folder-a').length, failure ? 1 : 0);
    sidebar.renderThreads();
    if (!failure) assert.ok(firstByClass(threadsUl, 'workspace-folder-empty-global'));
  });
}

// This harness changes HTTP responses only; all reads/publications use the owner.
function folderListingHarness() {
  const folders = ['folder-a', 'folder-b'].map(id => ({ id, display_name: id, nextcloud_sync_state: 'linked' }));
  const state = { listing: () => response(200, { ok: true, items: folders }), calls: [], onFiles: null };
  const built = buildSidebarWithFetch(async (url, init = {}) => {
    state.calls.push({ url, method: init.method || 'GET' });
    if (url.startsWith('/api/conversations?')) return conversationPage([
      { id: 'conv-a', title: 'A', workspace_folder_id: 'folder-a' },
      { id: 'conv-b', title: 'B', workspace_folder_id: 'folder-b' },
    ], 2);
    if (url === '/api/workspace-folders') return state.listing();
    if (url.endsWith('/messages')) return response(200, { ok: true, messages: [] });
    if (url.endsWith('/workspace-file-selections')) return response(200, { ok: true, items: [
      { file_id: 'file-a', conversation_id: url.split('/')[3], workspace_folder_id: 'folder-a', selected: true },
    ] });
    const folderId = url.split('/')[3];
    if (url.endsWith('/files')) return state.onFiles ? state.onFiles(folderId) : inventoryFileResponse('file-a', folderId);
    return response(200, { ok: true, items: [{
      id: `${url.split('/').pop()}-${folderId}`, workspace_folder_id: folderId,
      title: 'Synthetic', display_name: 'Synthetic', format: 'md', status: 'active',
    }] });
  });
  return { ...built, state, folders, status: built.threadsUl.parentElement.children[0] };
}

function folderListingSnapshot(sidebar) {
  return {
    folders: sidebar.getWorkspaceFolders(), threads: sidebar.getThreads(), current: sidebar.getCurrentId(),
    selections: sidebar.getWorkspaceFileSelections(sidebar.getCurrentId()),
    inventories: ['folder-a', 'folder-b'].map(id => [
      sidebar.getWorkspaceFiles(id), sidebar.getWorkspaceFilesStatus(id),
      sidebar.getWorkspaceExports(id), sidebar.getWorkspaceExportsStatus(id),
      sidebar.getWorkspaceGeneratedImages(id), sidebar.getWorkspaceGeneratedImagesStatus(id),
      sidebar.getWorkspaceNotes(id), sidebar.getWorkspaceNotesStatus(id),
    ]),
  };
}

const invalidFolderListings = [
  ['503', () => response(503, { ok: false, reason_code: 'synthetic_folders_unavailable' })],
  ['network rejection', () => Promise.reject(new Error('Synthetic network failure'))],
  ['unreadable JSON', () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('Synthetic JSON failure'); } })],
  ['ok false', () => response(200, { ok: false, items: [] })],
  ['ok absent', () => response(200, { items: [] })],
  ['ok nonboolean', () => response(200, { ok: 'true', items: [] })],
  ['items absent', () => response(200, { ok: true })],
  ['items null', () => response(200, { ok: true, items: null })],
  ['items object', () => response(200, { ok: true, items: {} })],
  ['array payload', () => response(200, [])],
  ['unusable folder row', () => response(200, { ok: true, items: [{ id: 'folder-a' }] })],
  ['object folder id', () => response(200, { ok: true, items: [{ id: {}, display_name: 'Synthetic' }] })],
  ['object folder name', () => response(200, { ok: true, items: [{ id: 'folder-a', display_name: {} }] })],
  ['partially unusable rows', () => response(200, { ok: true, items: [{ id: 'folder-a', display_name: 'A' }, null] })],
];
for (const [label, listing] of invalidFolderListings) {
  test(`P2-M2-03 ${label} preserves known memberships, every inventory, status and selection`, async () => {
    const { sidebar, state, status } = folderListingHarness();
    assert.equal(await sidebar.refreshThreadsFromServer(), true);
    sidebar.setCurrentId('conv-b');
    await sidebar.refreshWorkspaceFileSelections('conv-b');
    const before = folderListingSnapshot(sidebar);
    assert.equal(before.inventories[0].filter(Array.isArray).every(items => items.length === 1), true);
    const calls = state.calls.length;
    state.listing = listing;
    assert.equal(await sidebar.refreshThreadsFromServer(), false);
    assert.deepEqual(folderListingSnapshot(sidebar), before);
    assert.equal(status.textContent, 'Mode hors ligne.');
    assert.equal(status.style.display, 'block');
    assert.equal(status.style.color, '#b85050');
    assert.equal(state.calls.slice(calls).length, 2, 'Failed membership read must not reload inventories or selections');
  });
}

test('P2-M2-03 first load failure publishes no conversations or invented memberships', async () => {
  const { sidebar, state, status, threadsUl } = folderListingHarness();
  state.listing = invalidFolderListings[0][1];
  assert.equal(await sidebar.refreshThreadsFromServer({ keepSelection: false }), false);
  assert.deepEqual(sidebar.getThreads(), []);
  assert.deepEqual(sidebar.getWorkspaceFolders(), []);
  assert.equal(sidebar.getCurrentId(), null);
  assert.equal(sidebar.getWorkspaceFilesStatus('folder-a').status, 'unknown');
  assert.equal(status.textContent, 'Mode hors ligne.');
  assert.equal(state.calls.some(call => call.method !== 'GET'), false);
  sidebar.renderThreads();
  assert.equal(firstByClass(threadsUl, 'workspace-folder-empty-global'), null);
});

test('P2-M2-03 explicit successful refresh resumes and clears the failure', async () => {
  const { sidebar, state, status, folders } = folderListingHarness();
  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  state.listing = invalidFolderListings[0][1];
  assert.equal(await sidebar.refreshThreadsFromServer(), false);
  assert.equal(status.style.display, 'block');
  state.listing = () => response(200, { ok: true, items: folders });
  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  assert.equal(sidebar.getWorkspaceFolders().length, 2);
  assert.equal(status.style.display, 'none');
  assert.equal(state.calls.some(call => call.method !== 'GET'), false);
});

test('P2-M2-03 failed listing does not invalidate an independent in-flight Files read', async () => {
  const { sidebar, state } = folderListingHarness();
  await sidebar.refreshThreadsFromServer();
  const held = deferred(), started = deferred();
  const captured = inventoryFileResponse('new-file');
  state.onFiles = () => { started.resolve(); return held.promise; };
  const files = sidebar.refreshWorkspaceFiles('folder-a');
  await started.promise;
  state.listing = invalidFolderListings[0][1];
  const accepted = await sidebar.refreshThreadsFromServer();
  held.resolve(captured);
  assert.equal(accepted, false);
  assert.ok(Array.isArray(await files));
  assertInventory(sidebar, 'new-file');
});

test('P2-M2-03 confirmed removal drops only absent inventories and invalidates their pending Files reads', async () => {
  const { sidebar, state, folders } = folderListingHarness();
  await sidebar.refreshThreadsFromServer();
  const beforeB = folderListingSnapshot(sidebar).inventories[1];
  const held = deferred(), started = deferred();
  const captured = inventoryFileResponse('old-a');
  state.onFiles = id => id === 'folder-a' ? (started.resolve(), held.promise) : inventoryFileResponse('file-a', id);
  const old = sidebar.refreshWorkspaceFiles('folder-a');
  await started.promise;
  state.listing = () => response(200, { ok: true, items: [folders[1]] });
  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  held.resolve(captured);
  assert.equal(await old, null);
  assert.deepEqual(sidebar.getWorkspaceFolders().map(folder => folder.id), ['folder-b']);
  assert.deepEqual(sidebar.getWorkspaceFiles('folder-a'), []);
  for (const getStatus of ['getWorkspaceFilesStatus', 'getWorkspaceExportsStatus', 'getWorkspaceGeneratedImagesStatus', 'getWorkspaceNotesStatus']) {
    assert.equal(sidebar[getStatus]('folder-a').status, 'unknown');
  }
  for (const getItems of ['getWorkspaceExports', 'getWorkspaceGeneratedImages', 'getWorkspaceNotes']) {
    assert.deepEqual(sidebar[getItems]('folder-a'), []);
  }
  assert.deepEqual(folderListingSnapshot(sidebar).inventories[1], beforeB);
});

for (const oldFailure of [false, true]) {
  test(`P2-M2-03 old listing ${oldFailure ? 'error after success' : 'success after confirmed empty'} has no publication authority`, async () => {
    const { sidebar, state, status, folders } = folderListingHarness();
    await sidebar.refreshThreadsFromServer();
    const held = deferred(), started = deferred();
    const captured = oldFailure ? invalidFolderListings[0][1]() : response(200, { ok: true, items: folders });
    state.listing = () => { started.resolve(); return held.promise; };
    const old = sidebar.refreshThreadsFromServer();
    await started.promise;
    state.listing = () => response(200, { ok: true, items: oldFailure ? folders : [] });
    assert.equal(await sidebar.refreshThreadsFromServer(), true);
    const before = folderListingSnapshot(sidebar);
    held.resolve(captured);
    assert.equal(await old, false);
    assert.deepEqual(folderListingSnapshot(sidebar), before);
    assert.equal(status.style.display, 'none');
  });
}

test('P2-M2-03 confirmed conversation deletion retains refresh failure through reload without replay or rollback', async () => {
  let conversations = [
    { id: 'conv-a', title: 'A', workspace_folder_id: 'folder-a' },
    { id: 'conv-b', title: 'B', workspace_folder_id: 'folder-a' },
  ];
  let deleted = false, deletes = 0;
  const { sidebar, threadsUl } = buildSidebarWithFetch(async (url, init = {}) => {
    if (init.method === 'DELETE') {
      deletes++;
      deleted = true;
      conversations = conversations.filter(item => item.id !== 'conv-a');
      return response(200, { ok: true });
    }
    if (url.startsWith('/api/conversations?')) return conversationPage(conversations, conversations.length);
    if (url === '/api/workspace-folders') return deleted ? invalidFolderListings[0][1]() : response(200, {
      ok: true, items: [{ id: 'folder-a', display_name: 'A', nextcloud_sync_state: 'linked' }],
    });
    return response(200, { ok: true, items: [], messages: [] });
  });
  await sidebar.refreshThreadsFromServer();
  sidebar.renderThreads();
  expandFirstFolder(threadsUl);
  const button = firstByClass(threadsUl, 'thread-del');
  assert.ok(button);
  await button.events.get('click')[0]({ stopPropagation() {} });
  assert.equal(deletes, 1);
  assert.equal(sidebar.getCurrentId(), 'conv-b');
  assert.deepEqual(sidebar.getThreads().map(thread => thread.id), ['conv-b']);
  assert.equal(threadsUl.parentElement.children[0].textContent, 'Mode hors ligne.');
});

for (const mode of ['individual', 'global']) for (const error of [false, true]) {
  test(`P2-M2-01 older ${mode} ${error ? 'error' : 'success'} cannot replace a newer publication`, async () => {
    const held = deferred(), started = deferred();
    let first = true;
    const { sidebar } = inventoryHarness(folderId => {
      if (folderId !== 'folder-a') return inventoryFileResponse(null, folderId);
      if (first) { first = false; started.resolve(); return held.promise; }
      return inventoryFileResponse('adopted-file');
    });
    const oldPayload = error ? inventoryErrorResponse() : inventoryFileResponse('old-file');
    const oldRead = mode === 'individual' ? sidebar.refreshWorkspaceFiles('folder-a') : sidebar.refreshThreadsFromServer();
    await started.promise;
    await sidebar.refreshWorkspaceFiles('folder-a');
    held.resolve(oldPayload);
    const result = await oldRead;
    assertInventory(sidebar, 'adopted-file');
    if (mode === 'individual') assert.equal(result, null, 'Ignored inventory reads must not acknowledge publication');
  });
}

for (const oldError of [false, true]) {
  test(`P2-M2-01 global result A collected before B waits cannot replace newer A (${oldError ? 'error' : 'success'})`, async () => {
    const heldB = deferred(), startedB = deferred();
    let firstA = true;
    const { sidebar } = inventoryHarness(folderId => {
      if (folderId === 'folder-b') { startedB.resolve(); return heldB.promise; }
      if (firstA) { firstA = false; return oldError ? inventoryErrorResponse() : inventoryFileResponse('old-file'); }
      return inventoryFileResponse('adopted-file');
    });
    const globalRead = sidebar.refreshThreadsFromServer();
    await startedB.promise; // A's result is already consumed, before publication of the original global batch.
    await sidebar.refreshWorkspaceFiles('folder-a');
    heldB.resolve(inventoryFileResponse(null, 'folder-b'));
    await globalRead;
    assertInventory(sidebar, 'adopted-file');
  });
}

for (const newMode of ['individual', 'global']) for (const newError of [false, true]) {
  test(`P2-M2-01 newer ${newMode} ${newError ? 'error' : 'success'} remains authoritative over older individual success`, async () => {
    const held = deferred();
    let first = true;
    const { sidebar } = inventoryHarness(folderId => {
      if (folderId !== 'folder-a') return inventoryFileResponse(null, folderId);
      if (first) { first = false; return held.promise; }
      return newError ? inventoryErrorResponse() : inventoryFileResponse('current-file');
    });
    const oldRead = sidebar.refreshWorkspaceFiles('folder-a');
    if (newMode === 'global') await sidebar.refreshThreadsFromServer();
    else if (newError) await assert.rejects(sidebar.refreshWorkspaceFiles('folder-a'));
    else await sidebar.refreshWorkspaceFiles('folder-a');
    held.resolve(inventoryFileResponse('old-file'));
    await oldRead;
    assertInventory(sidebar, newError ? null : 'current-file', newError ? 'error' : 'ok');
  });
}

for (const mode of ['individual', 'global']) {
  test(`P2-M2-01 current ${mode} error and empty inventory keep their real status`, async () => {
    let next = inventoryFileResponse('current-file');
    const { sidebar } = inventoryHarness(folderId => folderId === 'folder-a' ? next : inventoryFileResponse(null, folderId));
    const refresh = () => mode === 'individual' ? sidebar.refreshWorkspaceFiles('folder-a') : sidebar.refreshThreadsFromServer();
    await refresh();
    assertInventory(sidebar, 'current-file');
    next = inventoryErrorResponse();
    if (mode === 'individual') await assert.rejects(refresh(), err => err.payload?.reason_code === 'workspace_files_lookup_failed');
    else assert.equal(await refresh(), true);
    assertInventory(sidebar, null, 'error');
    next = inventoryFileResponse(null);
    const result = await refresh();
    if (mode === 'individual') assert.deepEqual(result, [], 'A published empty inventory is successful');
    assertInventory(sidebar, null);
  });
}

for (const error of [false, true]) {
  test(`P2-M2-01 context invalidation ignores late ${error ? 'error' : 'success'} without changing files or status`, async () => {
    const held = deferred();
    let slow = false, current = true;
    const { sidebar } = inventoryHarness(() => slow ? held.promise : inventoryFileResponse('current-file'));
    await sidebar.refreshWorkspaceFiles('folder-a');
    slow = true;
    const read = sidebar.refreshWorkspaceFiles('folder-a', () => current);
    current = false;
    held.resolve(error ? inventoryErrorResponse() : inventoryFileResponse('old-file'));
    assert.equal(await read, null);
    assertInventory(sidebar, 'current-file');
  });
}

test('P2-M2-01 a B error does not invalidate A and an already invalid caller cannot supersede it', async () => {
  const heldA = deferred();
  const { sidebar, calls } = inventoryHarness(folderId => folderId === 'folder-a' ? heldA.promise : inventoryErrorResponse());
  const readA = sidebar.refreshWorkspaceFiles('folder-a');
  const invalidRead = sidebar.refreshWorkspaceFiles('folder-a', () => false);
  await assert.rejects(sidebar.refreshWorkspaceFiles('folder-b'));
  heldA.resolve(inventoryFileResponse('current-file'));
  assert.equal(await invalidRead, null);
  assert.equal((await readA)[0].id, 'current-file');
  assertInventory(sidebar, 'current-file');
  assert.equal(sidebar.getWorkspaceFilesStatus('folder-b').status, 'error');
  assert.deepEqual(calls, ['folder-a', 'folder-b']);
});

for (const mode of ['individual', 'global']) {
  test(`P2-M2-01 deleting A while ${mode} waits cannot resurrect its files or status`, async () => {
    const held = deferred(), started = deferred();
    const { sidebar, folders } = inventoryHarness(folderId => {
      if (folderId !== 'folder-a') return inventoryFileResponse(null, folderId);
      started.resolve(); return held.promise;
    });
    const read = mode === 'individual' ? sidebar.refreshWorkspaceFiles('folder-a') : sidebar.refreshThreadsFromServer();
    await started.promise;
    sidebar.saveWorkspaceFolders(folders.filter(folder => folder.id !== 'folder-a'));
    held.resolve(inventoryFileResponse('old-file'));
    await read;
    assert.deepEqual(sidebar.getWorkspaceFiles('folder-a'), []);
    assert.equal(sidebar.getWorkspaceFilesStatus('folder-a').status, 'unknown');
    const before = sidebar.getWorkspaceFolders();
    assert.equal(await sidebar.refreshWorkspaceFiles('folder-a'), null);
    assert.deepEqual(sidebar.getWorkspaceFolders(), before);
  });
}

test('P2-M2-01 a newer global folder deletion wins over an older folder listing', async () => {
  const oldFolders = deferred(), started = deferred();
  let first = true;
  const { sidebar, folders, calls } = inventoryHarness(() => inventoryFileResponse('old-file'), () => {
    if (first) { first = false; started.resolve(); return oldFolders.promise; }
    return response(200, { ok: true, items: [] });
  });
  const oldRead = sidebar.refreshThreadsFromServer();
  await started.promise;
  assert.equal(await sidebar.refreshThreadsFromServer(), true);
  oldFolders.resolve(response(200, { ok: true, items: folders }));
  assert.equal(await oldRead, false);
  assert.deepEqual(sidebar.getWorkspaceFolders(), []);
  assert.deepEqual(sidebar.getWorkspaceFiles('folder-a'), []);
  assert.equal(sidebar.getWorkspaceFilesStatus('folder-a').status, 'unknown');
  assert.deepEqual(calls, [], 'Obsolete folder membership must not start an inventory read');
});

test('P2-M2-01 a deleted and reintroduced A cannot accept a previous lifetime response', async () => {
  const held = deferred();
  const { sidebar, folders } = inventoryHarness(() => held.promise);
  const oldRead = sidebar.refreshWorkspaceFiles('folder-a');
  sidebar.saveWorkspaceFolders([]);
  sidebar.saveWorkspaceFolders(folders);
  held.resolve(inventoryFileResponse('old-file'));
  assert.equal(await oldRead, null);
  assert.deepEqual(sidebar.getWorkspaceFiles('folder-a'), []);
  assert.equal(sidebar.getWorkspaceFilesStatus('folder-a').status, 'unknown');
});

for (const error of [false, true]) {
  test(`P2-M2-01 global batch waiting on A ${error ? 'error' : 'success'} must not start an obsolete B read`, async () => {
    const heldA = deferred(), startedA = deferred();
    const { sidebar, calls } = inventoryHarness(folderId => {
      if (folderId === 'folder-a') { startedA.resolve(); return heldA.promise; }
      return inventoryFileResponse('new-b', folderId);
    });
    const globalRead = sidebar.refreshThreadsFromServer();
    await startedA.promise;
    await sidebar.refreshWorkspaceFiles('folder-b');
    heldA.resolve(error ? inventoryErrorResponse() : inventoryFileResponse('new-a'));
    await globalRead;
    assertInventory(sidebar, error ? null : 'new-a', error ? 'error' : 'ok');
    assert.deepEqual(sidebar.getWorkspaceFiles('folder-b').map(file => file.id), ['new-b']);
    assert.equal(sidebar.getWorkspaceFilesStatus('folder-b').status, 'ok');
    assert.deepEqual(calls, ['folder-a', 'folder-b'], 'The superseded global B request must not perform I/O');
  });
}
