const test = require("node:test");
const assert = require("node:assert/strict");

const ThreadsSidebarModule = require("../../../web/chat_threads_sidebar.js");

// Transport payloads deliberately follow each family's own server contract.
const artifactFamilies = [
  { name: 'Exports', path: 'exports', key: 'exports', ok: 'workspace_exports_list_ok' },
  { name: 'GeneratedImages', path: 'generated-images', key: 'generated_images', ok: 'workspace_generated_images_list_ok' },
  { name: 'Notes', path: 'notes', key: 'items', ok: 'workspace_notes_list_ok' },
];
function artifactItem(id, folder = 'folder-a') {
  return { id, workspace_folder_id: folder, title: id, display_name: id, format: 'md',
    status: 'available', can_open: true, can_download: true, can_delete: true, can_reuse_as_source: true };
}

const artifactActions = [
  { family: artifactFamilies[0], module: 'exports', factory: 'Exports', append: 'Export', css: 'export-create', label: 'Export créé dans le répertoire.' },
  { family: artifactFamilies[0], module: 'exports', factory: 'Exports', append: 'Export', css: 'export-action-reuse', label: 'Export réutilisé comme source.' },
  { family: artifactFamilies[1], module: 'generated_images', factory: 'GeneratedImages', append: 'GeneratedImage', css: 'generated-image-create', label: 'Image créée dans le répertoire.' },
  { family: artifactFamilies[1], module: 'generated_images', factory: 'GeneratedImages', append: 'GeneratedImage', css: 'generated-image-action-delete', label: 'Image supprimée du répertoire.' },
  { family: artifactFamilies[2], module: 'notes', factory: 'Notes', append: 'Note', css: 'note-create', label: 'Note créée.' },
];
for (const action of artifactActions) for (const outcome of ['ignored', 'error']) {
  test('P2-M2-02 confirmed ' + action.css + ' with ' + outcome + ' reload does not invite mutation replay', async () => {
    const family = action.family, started = deferred(), release = deferred(), finished = deferred();
    let mutated = false, first = true, selected = null;
    const notesModeController = { setSelectedNote(note) { selected = note.id; } };
    const { sidebar, folders, calls, threadsUl } = artifactHarness((readFamily, folder, init) => {
      if (init.method === 'POST' || init.method === 'DELETE') {
        mutated = true;
        const single = family.name === 'Exports' ? 'export' : family.name === 'GeneratedImages' ? 'generated_image' : 'note';
        return response(201, {ok:true, [single]:artifactItem('created', folder)});
      }
      if (!mutated) return artifactResponse(readFamily, 'original', folder);
      if (outcome === 'error') return artifactError();
      if (first) {
        first = false;
        const captured = artifactResponse(readFamily, 'created', folder);
        started.resolve();
        return release.promise.then(() => captured);
      }
      return artifactResponse(readFamily, 'newer', folder);
    }, { notesModeController });
    // Image DELETE uses the real HTTP mutation implementation, too.
    const fetchDelete = sidebar.deleteWorkspaceGeneratedImageOnServer;
    const previousWindow = global.window;
    global.window = {
      prompt(message, fallback) { return message === 'Prompt image' ? 'Synthetic image'
        : message.includes('Titre') ? 'Synthetic title' : fallback; },
      confirm() { return true; },
    };
    try {
      await sidebar['refreshWorkspace' + family.name]('folder-a');
      const module = require('../../../web/chat_workspace_folder_' + action.module + '_panel.js');
      let panel;
      const render = () => {
        threadsUl.innerHTML = '';
        panel['append' + action.append + 'Rows'](folders[0]);
      };
      panel = module['createWorkspaceFolder' + action.factory + 'PanelRenderer']({
        threadsUl, getCurrentThread: () => ({id:'conv-a', workspace_folder_id:'folder-a'}),
        ['getWorkspace' + family.name]: sidebar['getWorkspace' + family.name],
        ['getWorkspace' + family.name + 'Status']: sidebar['getWorkspace' + family.name + 'Status'],
        ['refreshWorkspace' + family.name]: sidebar['refreshWorkspace' + family.name],
        createWorkspaceExportOnServer: sidebar.createWorkspaceExportOnServer,
        createWorkspaceGeneratedImageOnServer: sidebar.createWorkspaceGeneratedImageOnServer,
        createWorkspaceNoteOnServer: sidebar.createWorkspaceNoteOnServer,
        deleteWorkspaceGeneratedImageOnServer: fetchDelete,
        renderThreads: render, notesModeController, consoleObj: {warn() {}},
        setThreadStatus: (message, isError) => finished.resolve({message, isError}),
      });
      render();
      const button = firstByClass(threadsUl, 'workspace-folder-' + action.css);
      assert.ok(button);
      button.click();
      if (outcome === 'ignored') {
        await started.promise;
        await sidebar['refreshWorkspace' + family.name]('folder-a');
        release.resolve();
      }
      const status = await finished.promise;
      assert.equal(status.message, action.label + ' Inventaire non actualisé.');
      assert.equal(status.isError, true);
      if (outcome === 'error') assert.equal(byClass(threadsUl, 'workspace-folder-' + action.append.toLowerCase().replace('generatedimage', 'generated-image') + '-error').length, 1);
      assert.equal(calls.filter(call => call.method === 'POST' || call.method === 'DELETE').length, 1);
      assertArtifact(sidebar, family, outcome === 'ignored' ? 'newer' : null, outcome === 'ignored' ? 'ok' : 'error');
      if (family.name === 'Notes') assert.equal(selected, 'created');
    } finally {
      if (previousWindow === undefined) delete global.window;
      else global.window = previousWindow;
    }
  });
}
function artifactResponse(family, id, folder = 'folder-a') {
  return response(200, { ok: true, [family.key]: id ? [{...artifactItem(id, folder),
    format: family.name === 'GeneratedImages' ? 'png' : 'md'}] : [] });
}
function artifactError() {
  return response(503, { ok: false, reason_code: 'synthetic_artifact_unavailable' });
}
function artifactHarness(onRead, { onFiles, onFolders, notesModeController } = {}) {
  const folders = ['folder-a', 'folder-b'].map(id => ({
    id, display_name: id, nextcloud_sync_state: 'linked',
  }));
  const calls = [];
  const built = buildSidebarWithFetch(async (url, init = {}) => {
    calls.push({ url, method: init.method || 'GET' });
    if (url.startsWith('/api/conversations?')) return conversationPage([], 0);
    if (url === '/api/workspace-folders') return onFolders
      ? onFolders() : response(200, { ok: true, items: folders });
    if (url.endsWith('/files') && onFiles) return onFiles(url.split('/')[3]);
    const family = artifactFamilies.find(item => url.endsWith('/' + item.path)
      || (init.method === 'DELETE' && url.includes('/' + item.path + '/')));
    if (family) return onRead(family, url.split('/')[3], init);
    return response(200, { ok: true, items: [] });
  }, notesModeController);
  built.sidebar.saveWorkspaceFolders(folders);
  return { ...built, calls, folders };
}
function assertArtifact(sidebar, family, id, status = 'ok', folder = 'folder-a') {
  assert.deepEqual(sidebar['getWorkspace' + family.name](folder).map(item => item.id), id ? [id] : []);
  const actual = sidebar['getWorkspace' + family.name + 'Status'](folder);
  assert.equal(actual.status, status);
  if (status === 'ok') assert.equal(actual.reason_code, family.ok);
  if (status === 'error') assert.equal(actual.reason_code, 'synthetic_artifact_unavailable');
}

for (const family of artifactFamilies) {
  for (const releaseBefore of [true, false]) {
    test('P2-M2-02 ' + family.name + ' collected A waits for B; release ' + (releaseBefore ? 'before' : 'after') + ' individual A', async () => {
      const waitingB = deferred(), releaseB = deferred();
      let current = 'old-a', held = false;
      const { sidebar } = artifactHarness((readFamily, folder) => {
        if (readFamily !== family) return artifactResponse(readFamily, null);
        if (folder === 'folder-b' && !held) {
          held = true;
          const captured = artifactResponse(family, 'old-b', folder);
          waitingB.resolve();
          return releaseB.promise.then(() => captured);
        }
        return artifactResponse(family, current, folder);
      });
      const global = sidebar.refreshThreadsFromServer();
      await waitingB.promise;
      if (releaseBefore) { releaseB.resolve(); assert.equal(await global, true); }
      current = 'new-a';
      await sidebar['refreshWorkspace' + family.name]('folder-a');
      assertArtifact(sidebar, family, 'new-a');
      if (!releaseBefore) { releaseB.resolve(); assert.equal(await global, true); }
      assertArtifact(sidebar, family, 'new-a');
    });
  }

  for (const newer of ['individual', 'global']) for (const oldError of [false, true]) {
    test('P2-M2-02 ' + family.name + ' old individual ' + (oldError ? 'error' : 'success') + ' after newer ' + newer, async () => {
      const started = deferred(), release = deferred();
      let first = true;
      const { sidebar } = artifactHarness((readFamily, folder) => {
        if (readFamily !== family || folder !== 'folder-a') return artifactResponse(readFamily, null);
        if (first) {
          first = false;
          const captured = oldError ? artifactError() : artifactResponse(family, 'old');
          started.resolve();
          return release.promise.then(() => captured);
        }
        return artifactResponse(family, 'new');
      });
      const old = sidebar['refreshWorkspace' + family.name]('folder-a');
      await started.promise;
      if (newer === 'global') assert.equal(await sidebar.refreshThreadsFromServer(), true);
      else await sidebar['refreshWorkspace' + family.name]('folder-a');
      release.resolve();
      assert.equal(await old, null);
      assertArtifact(sidebar, family, 'new');
    });
  }

  for (const newer of ['individual', 'global']) {
    test('P2-M2-02 ' + family.name + ' old success cannot mask newer ' + newer + ' error', async () => {
      const started = deferred(), release = deferred();
      let first = true;
      const { sidebar } = artifactHarness((readFamily, folder) => {
        if (readFamily !== family || folder !== 'folder-a') return artifactResponse(readFamily, null);
        if (first) {
          first = false;
          const captured = artifactResponse(family, 'old');
          started.resolve();
          return release.promise.then(() => captured);
        }
        return artifactError();
      });
      const old = sidebar['refreshWorkspace' + family.name]('folder-a');
      await started.promise;
      if (newer === 'global') assert.equal(await sidebar.refreshThreadsFromServer(), true);
      else await assert.rejects(sidebar['refreshWorkspace' + family.name]('folder-a'));
      release.resolve();
      assert.equal(await old, null);
      assertArtifact(sidebar, family, null, 'error');
    });
  }

  test('P2-M2-02 ' + family.name + ' old global error waiting B cannot erase newer A success', async () => {
    const waitingB = deferred(), releaseB = deferred();
    let newer = false, held = false;
    const { sidebar } = artifactHarness((readFamily, folder) => {
      if (readFamily !== family) return artifactResponse(readFamily, null);
      if (folder === 'folder-a') return newer ? artifactResponse(family, 'new') : artifactError();
      if (!held) {
        held = true;
        const captured = artifactResponse(family, null);
        waitingB.resolve();
        return releaseB.promise.then(() => captured);
      }
      return artifactResponse(family, null);
    });
    const global = sidebar.refreshThreadsFromServer();
    await waitingB.promise;
    newer = true;
    await sidebar['refreshWorkspace' + family.name]('folder-a');
    releaseB.resolve();
    assert.equal(await global, true);
    assertArtifact(sidebar, family, 'new');
  });

  for (const phase of ['Files', 'own-family']) {
    test('P2-M2-02 ' + family.name + ' older global paused in ' + phase + ' cannot reacquire authority', async () => {
      const started = deferred(), release = deferred();
      let blocked = false;
      const hold = captured => {
        blocked = true;
        started.resolve();
        return release.promise.then(() => captured);
      };
      const { sidebar, calls } = artifactHarness((readFamily, folder) => {
        const captured = artifactResponse(readFamily, 'global-old', folder);
        if (phase === 'own-family' && readFamily === family && folder === 'folder-a' && !blocked) return hold(captured);
        return artifactResponse(readFamily, blocked ? 'new' : 'global-old', folder);
      }, {
        onFiles: folder => phase === 'Files' && folder === 'folder-a' && !blocked
          ? hold(response(200, { ok: true, items: [] })) : response(200, { ok: true, items: [] }),
      });
      const old = sidebar.refreshThreadsFromServer();
      await started.promise;
      await sidebar['refreshWorkspace' + family.name]('folder-a');
      const before = calls.filter(c => c.url === '/api/workspace-folders/folder-a/' + family.path).length;
      release.resolve();
      assert.equal(await old, true);
      assertArtifact(sidebar, family, 'new');
      assert.equal(calls.filter(c => c.url === '/api/workspace-folders/folder-a/' + family.path).length, before,
        'A superseded deferred phase must not launch a new read');
    });
  }

  test('P2-M2-02 ' + family.name + ' overlapping globaux preserve the latest generation', async () => {
    const started = deferred(), release = deferred();
    let first = true;
    const { sidebar } = artifactHarness((readFamily, folder) => {
      if (readFamily === family && folder === 'folder-a' && first) {
        first = false;
        const captured = artifactResponse(family, 'old');
        started.resolve();
        return release.promise.then(() => captured);
      }
      return artifactResponse(readFamily, 'new', folder);
    });
    const old = sidebar.refreshThreadsFromServer();
    await started.promise;
    assert.equal(await sidebar.refreshThreadsFromServer(), true);
    release.resolve();
    assert.equal(await old, false);
    for (const readFamily of artifactFamilies) assertArtifact(sidebar, readFamily, 'new');
  });

  test('P2-M2-02 ' + family.name + ' A is independent of B, other families and Files', async () => {
    const started = deferred(), release = deferred();
    const { sidebar } = artifactHarness((readFamily, folder) => {
      const captured = artifactResponse(readFamily, 'kept', folder);
      if (readFamily === family && folder === 'folder-a') {
        started.resolve();
        return release.promise.then(() => captured);
      }
      return captured;
    });
    const pending = sidebar['refreshWorkspace' + family.name]('folder-a');
    await started.promise;
    await sidebar['refreshWorkspace' + family.name]('folder-b');
    for (const other of artifactFamilies.filter(item => item !== family)) await sidebar['refreshWorkspace' + other.name]('folder-a');
    await sidebar.refreshWorkspaceFiles('folder-a');
    release.resolve();
    assert.ok(Array.isArray(await pending));
    assertArtifact(sidebar, family, 'kept');
    assertArtifact(sidebar, family, 'kept', 'ok', 'folder-b');
    for (const other of artifactFamilies.filter(item => item !== family)) assertArtifact(sidebar, other, 'kept');
    assert.equal(sidebar.getWorkspaceFilesStatus('folder-a').status, 'ok');
  });

  for (const reappear of [false, true]) for (const oldError of [false, true]) {
    test('P2-M2-02 ' + family.name + ' removed lifetime rejects old ' + (oldError ? 'error' : 'success') + (reappear ? ' after reappearance' : ''), async () => {
      const started = deferred(), release = deferred();
      const { sidebar, folders } = artifactHarness((readFamily, folder) => {
        if (readFamily !== family || folder !== 'folder-a') return artifactResponse(readFamily, null);
        const captured = oldError ? artifactError() : artifactResponse(family, 'old');
        started.resolve();
        return release.promise.then(() => captured);
      });
      const old = sidebar['refreshWorkspace' + family.name]('folder-a');
      await started.promise;
      sidebar.saveWorkspaceFolders(folders.filter(folder => folder.id !== 'folder-a'));
      if (reappear) sidebar.saveWorkspaceFolders(folders);
      release.resolve();
      assert.equal(await old, null);
      assertArtifact(sidebar, family, null, 'unknown');
    });
  }

  test('P2-M2-02 ' + family.name + ' confirmed empty global invalidates pending read', async () => {
    const started = deferred(), release = deferred();
    const { sidebar } = artifactHarness((readFamily, folder) => {
      const captured = artifactResponse(readFamily, 'old', folder);
      started.resolve();
      return release.promise.then(() => captured);
    }, { onFolders: () => response(200, { ok: true, items: [] }) });
    const old = sidebar['refreshWorkspace' + family.name]('folder-a');
    await started.promise;
    assert.equal(await sidebar.refreshThreadsFromServer(), true);
    release.resolve();
    assert.equal(await old, null);
    assertArtifact(sidebar, family, null, 'unknown');
  });

  test('P2-M2-02 ' + family.name + ' empty, current error, explicit recovery and not_applicable', async () => {
    let state = 'empty';
    const { sidebar, folders, calls } = artifactHarness((readFamily, folder) =>
      readFamily === family && state === 'error' ? artifactError() : artifactResponse(readFamily, state === 'new' ? 'new' : null, folder));
    assert.deepEqual(await sidebar['refreshWorkspace' + family.name]('folder-a'), []);
    assertArtifact(sidebar, family, null);
    state = 'error';
    await assert.rejects(sidebar['refreshWorkspace' + family.name]('folder-a'));
    assertArtifact(sidebar, family, null, 'error');
    state = 'new';
    assert.equal((await sidebar['refreshWorkspace' + family.name]('folder-a'))[0].id, 'new');
    assertArtifact(sidebar, family, 'new');
    for (const folder of folders) folder.nextcloud_sync_state = 'local_only';
    sidebar.saveWorkspaceFolders(folders);
    const before = calls.length;
    assert.deepEqual(await sidebar['refreshWorkspace' + family.name]('folder-a'), []);
    assertArtifact(sidebar, family, null, 'not_applicable');
    assert.equal(calls.length, before);
    assert.equal(await sidebar.refreshThreadsFromServer(), true);
    assertArtifact(sidebar, family, null, 'not_applicable');
  });

  test('P2-M2-02 ' + family.name + ' listing failure preserves an individual read authority', async () => {
    const started = deferred(), release = deferred();
    const { sidebar } = artifactHarness((readFamily, folder) => {
      const captured = artifactResponse(readFamily, 'kept', folder);
      started.resolve();
      return release.promise.then(() => captured);
    }, { onFolders: () => response(503, { ok: false, reason_code: 'synthetic_folders_unavailable' }) });
    const pending = sidebar['refreshWorkspace' + family.name]('folder-a');
    await started.promise;
    assert.equal(await sidebar.refreshThreadsFromServer(), false);
    release.resolve();
    assert.ok(Array.isArray(await pending));
    assertArtifact(sidebar, family, 'kept');
    assert.equal(sidebar.getWorkspaceFolders().length, 2);
  });

  test('P2-M2-02 ' + family.name + ' absent folder refuses publication', async () => {
    const { sidebar, calls } = artifactHarness((readFamily, folder) => artifactResponse(readFamily, 'unexpected', folder));
    assert.equal(await sidebar['refreshWorkspace' + family.name]('absent'), null);
    assertArtifact(sidebar, family, null, 'unknown', 'absent');
    assert.equal(calls.length, 0);
  });

  test('P2-M2-02 ' + family.name + ' a previous family phase cannot supersede its newer individual read', async () => {
    const started = deferred(), release = deferred();
    const previous = artifactFamilies[artifactFamilies.indexOf(family) - 1];
    let held = false;
    const hold = captured => { held = true; started.resolve(); return release.promise.then(() => captured); };
    const { sidebar, calls } = artifactHarness((readFamily, folder) => {
      const captured = artifactResponse(readFamily, 'global-old', folder);
      if (readFamily === previous && folder === 'folder-b' && !held) return hold(captured);
      return artifactResponse(readFamily, held ? 'new' : 'global-old', folder);
    }, { onFiles: folder => !previous && folder === 'folder-b' && !held
      ? hold(response(200, {ok:true, items:[]})) : response(200, {ok:true, items:[]}) });
    const global = sidebar.refreshThreadsFromServer();
    await started.promise;
    await sidebar['refreshWorkspace' + family.name]('folder-a');
    const count = calls.filter(call => call.url.endsWith('/folder-a/' + family.path)).length;
    release.resolve();
    assert.equal(await global, true);
    assert.equal(calls.filter(call => call.url.endsWith('/folder-a/' + family.path)).length, count);
    assertArtifact(sidebar, family, 'new');
  });

  test('P2-M2-02 ' + family.name + ' collected global success must preserve a newer error', async () => {
    const started = deferred(), release = deferred();
    let newer = false;
    const { sidebar } = artifactHarness((readFamily, folder) => {
      const captured = readFamily === family && folder === 'folder-a' && newer
        ? artifactError() : artifactResponse(readFamily, 'old', folder);
      if (readFamily === family && folder === 'folder-b' && !newer) {
        started.resolve(); return release.promise.then(() => captured);
      }
      return captured;
    });
    const global = sidebar.refreshThreadsFromServer();
    await started.promise;
    newer = true;
    await assert.rejects(sidebar['refreshWorkspace' + family.name]('folder-a'));
    release.resolve();
    assert.equal(await global, true);
    assertArtifact(sidebar, family, null, 'error');
  });

  test('P2-M2-02 ' + family.name + ' context guard cannot invalidate or publish another valid read', async () => {
    const started = deferred(), release = deferred();
    const { sidebar, calls } = artifactHarness((readFamily, folder) => {
      started.resolve();
      const captured = artifactResponse(readFamily, 'kept', folder);
      return release.promise.then(() => captured);
    });
    let current = true;
    const pending = sidebar['refreshWorkspace' + family.name]('folder-a', () => current);
    await started.promise;
    const refused = sidebar['refreshWorkspace' + family.name]('folder-a', () => false);
    const count = calls.length;
    current = false;
    release.resolve();
    assert.equal(await refused, null);
    assert.equal(count, 1);
    assert.equal(await pending, null);
    assertArtifact(sidebar, family, null, 'unknown');
  });
}
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

function buildSidebarWithFetch(fetchFn, notesModeController = {}) {
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
    notesModeController,
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
