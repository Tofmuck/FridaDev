const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const GeneratedImages = require("../../../web/chat_workspace_folder_generated_images.js");
const {
  createWorkspaceFolderGeneratedImagesPanelRenderer,
} = require("../../../web/chat_workspace_folder_generated_images_panel.js");

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

function installDom({ prompts = [], confirms = [] } = {}) {
  const body = makeElement("body");
  global.document = {
    body,
    createElement: makeElement,
  };
  global.window = {
    prompt: () => prompts.shift() ?? "",
    confirm: () => confirms.shift() ?? false,
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

function linkedFolder(overrides = {}) {
  return {
    id: "folder-1",
    display_name: "Projet",
    nextcloud_sync_state: "linked",
    deleted_at: null,
    ...overrides,
  };
}

function generatedImage(overrides = {}) {
  return GeneratedImages.normalizeWorkspaceGeneratedImageItem({
    generated_image_v1_user: {
      image_id: "image-1",
      workspace_folder_id: "folder-1",
      display_name: "Image visible",
      format: "png",
      mime_type: "image/png",
      byte_size: 2048,
      width: 512,
      height: 512,
      status: "available",
      status_label: "disponible",
      created_at: "2026-06-20T12:00:00Z",
      can_open: true,
      can_download: true,
      can_delete: true,
      actions: {
        open_reason_code: "folder_generated_image_open_ok",
        download_reason_code: "folder_generated_image_download_ok",
        delete_reason_code: "folder_generated_image_delete_ok",
      },
      ...overrides,
    },
  });
}

function buildPanel({
  folder = linkedFolder(),
  imagesList = [],
  imagesStatus = { status: "ok", reason_code: "workspace_generated_images_list_ok" },
  prompts = [],
  confirms = [],
} = {}) {
  installDom({ prompts, confirms });
  const threadsUl = makeElement("ul");
  const createCalls = [];
  const openCalls = [];
  const downloadCalls = [];
  const deleteCalls = [];
  const statuses = [];
  let refreshCount = 0;
  const panel = createWorkspaceFolderGeneratedImagesPanelRenderer({
    threadsUl,
    getWorkspaceGeneratedImages: () => imagesList,
    getWorkspaceGeneratedImagesStatus: () => imagesStatus,
    refreshWorkspaceGeneratedImages: async () => {
      refreshCount += 1;
      return imagesList;
    },
    createWorkspaceGeneratedImageOnServer: async (folderId, payload) => {
      createCalls.push({ folderId, payload });
      return { generated_image_v1_user: { image_id: "created-image", workspace_folder_id: folderId } };
    },
    openWorkspaceGeneratedImage: (folderId, imageId) => {
      openCalls.push({ folderId, imageId });
    },
    downloadWorkspaceGeneratedImage: (folderId, imageId) => {
      downloadCalls.push({ folderId, imageId });
    },
    deleteWorkspaceGeneratedImageOnServer: async (folderId, imageId) => {
      deleteCalls.push({ folderId, imageId });
      return { generated_image_v1_user: { image_id: imageId, workspace_folder_id: folderId } };
    },
    renderThreads: () => {},
    setThreadStatus: (message, isError = false) => {
      statuses.push({ message, isError });
    },
    consoleObj: { warn() {} },
  });
  panel.appendGeneratedImageRows(folder);
  return {
    threadsUl,
    createCalls,
    openCalls,
    downloadCalls,
    deleteCalls,
    statuses,
    refreshCount: () => refreshCount,
  };
}

function assertCreatePayloadIsClean(payload) {
  for (const key of [
    "workspace_folder_id",
    "image_id",
    "bytes",
    "base64",
    "data_url",
    "image_data_url",
    "target",
    "target_name_internal",
    "target_ref",
    "dav_url",
    "etag",
    "etag_value",
    "content_hash",
  ]) {
    assert.equal(Object.hasOwn(payload, key), false, `${key} must not be sent`);
  }
}

function scriptIndex(indexHtml, scriptName) {
  const needle = `<script src="${scriptName}"></script>`;
  const idx = indexHtml.indexOf(needle);
  assert.notEqual(idx, -1, `${scriptName} must be loaded by index.html`);
  assert.equal(indexHtml.indexOf(needle, idx + needle.length), -1, `${scriptName} must be loaded once`);
  return idx;
}

test("index loads generated images UI dependencies in browser order", () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, "../../../web/index.html"), "utf8");
  const generatedImages = scriptIndex(indexHtml, "chat_workspace_folder_generated_images.js");
  const imageGeneration = scriptIndex(indexHtml, "chat_image_generation.js");
  const generatedImagesPanel = scriptIndex(indexHtml, "chat_workspace_folder_generated_images_panel.js");
  const foldersSidebar = scriptIndex(indexHtml, "chat_workspace_folders_sidebar.js");
  const threadsSidebar = scriptIndex(indexHtml, "chat_threads_sidebar.js");

  assert.ok(generatedImages < generatedImagesPanel);
  assert.ok(imageGeneration < generatedImagesPanel);
  assert.ok(generatedImagesPanel < foldersSidebar);
  assert.ok(generatedImagesPanel < threadsSidebar);
});

test("generated images panel creates durable image only for linked folders", async () => {
  const rendered = buildPanel({
    prompts: [
      "Prompt transient sentinel",
      "Image user name",
      "image_generator_nano_banana",
      "1:1",
      "1K",
    ],
  });
  const createButton = firstByClass(rendered.threadsUl, "workspace-folder-generated-image-create");

  assert.ok(createButton);
  assert.equal(createButton.disabled, false);
  createButton.click();
  await flushAsync();

  assert.equal(rendered.createCalls.length, 1);
  assert.equal(rendered.createCalls[0].folderId, "folder-1");
  assert.deepEqual(rendered.createCalls[0].payload, {
    prompt: "Prompt transient sentinel",
    generator_key: "image_generator_nano_banana",
    aspect_ratio: "1:1",
    image_size: "1K",
    display_name: "Image user name",
  });
  assertCreatePayloadIsClean(rendered.createCalls[0].payload);
  assert.equal(visibleText(rendered.threadsUl).includes("Prompt transient sentinel"), false);
  assert.equal(rendered.refreshCount(), 1);
});

test("generated images panel normalizes generator options through image generation module", async () => {
  const rendered = buildPanel({
    prompts: [
      "Prompt transient sentinel",
      "Image user name",
      "image_generator_recraft",
      "21:9",
      "4K",
    ],
  });

  firstByClass(rendered.threadsUl, "workspace-folder-generated-image-create").click();
  await flushAsync();

  assert.equal(rendered.createCalls.length, 1);
  assert.deepEqual(rendered.createCalls[0].payload, {
    prompt: "Prompt transient sentinel",
    generator_key: "image_generator_recraft",
    aspect_ratio: "1:1",
    image_size: "1K",
    display_name: "Image user name",
  });
  assertCreatePayloadIsClean(rendered.createCalls[0].payload);
});

test("generated images panel disables creation for non linked folders", async () => {
  const rendered = buildPanel({
    folder: linkedFolder({ nextcloud_sync_state: "local_only" }),
    prompts: ["Should not be prompted"],
  });
  const createButton = firstByClass(rendered.threadsUl, "workspace-folder-generated-image-create");

  assert.equal(createButton.disabled, true);
  createButton.click();
  await flushAsync();

  assert.equal(rendered.createCalls.length, 0);
  assert.equal(visibleText(rendered.threadsUl).includes("Images disponibles"), true);
});

test("generated images panel open and download use explicit action callbacks only", () => {
  const rendered = buildPanel({
    imagesList: [generatedImage()],
  });

  firstByClass(rendered.threadsUl, "workspace-folder-generated-image-action-open").click();
  firstByClass(rendered.threadsUl, "workspace-folder-generated-image-action-download").click();

  assert.deepEqual(rendered.openCalls, [{ folderId: "folder-1", imageId: "image-1" }]);
  assert.deepEqual(rendered.downloadCalls, [{ folderId: "folder-1", imageId: "image-1" }]);
});

test("generated images panel keeps normal empty state when API returns an empty list", () => {
  const rendered = buildPanel({
    imagesList: [],
    imagesStatus: { status: "ok", reason_code: "workspace_generated_images_list_ok" },
  });

  assert.equal(firstByClass(rendered.threadsUl, "workspace-folder-generated-image-error"), null);
  const empty = firstByClass(rendered.threadsUl, "workspace-folder-generated-image-empty");
  assert.ok(empty);
  assert.equal(empty.textContent, "Aucune image");
});

test("generated images panel renders API errors as visible errors instead of empty lists", () => {
  const rendered = buildPanel({
    imagesList: [],
    imagesStatus: {
      status: "error",
      reason_code: "folder_generated_image_lookup_failed",
      details: "UNSAFE_TECHNICAL_DETAIL_SENTINEL",
    },
  });

  assert.equal(firstByClass(rendered.threadsUl, "workspace-folder-generated-image-empty"), null);
  const error = firstByClass(rendered.threadsUl, "workspace-folder-generated-image-error");
  assert.ok(error);
  assert.equal(error.dataset.reasonCode, "folder_generated_image_lookup_failed");
  assert.match(visibleText(rendered.threadsUl), /Chargement des images impossible/);
  assert.equal(visibleText(rendered.threadsUl).includes("Aucune image"), false);
  assert.equal(visibleText(rendered.threadsUl).includes("UNSAFE_TECHNICAL_DETAIL_SENTINEL"), false);
});

test("generated images panel disabled actions do not call callbacks", () => {
  const rendered = buildPanel({
    imagesList: [generatedImage({
      can_open: false,
      can_download: false,
      can_delete: false,
      actions: {
        open_reason_code: "folder_generated_image_access_not_prepared",
        download_reason_code: "folder_generated_image_access_not_prepared",
        delete_reason_code: "folder_generated_image_access_not_prepared",
      },
    })],
  });

  for (const button of byClass(rendered.threadsUl, "workspace-folder-generated-image-action")) {
    assert.equal(button.disabled, true);
    button.click();
  }

  assert.deepEqual(rendered.openCalls, []);
  assert.deepEqual(rendered.downloadCalls, []);
  assert.deepEqual(rendered.deleteCalls, []);
});

test("generated images panel delete requires confirmation and refreshes on success", async () => {
  const cancelled = buildPanel({
    imagesList: [generatedImage()],
    confirms: [false],
  });
  firstByClass(cancelled.threadsUl, "workspace-folder-generated-image-action-delete").click();
  await flushAsync();
  assert.deepEqual(cancelled.deleteCalls, []);

  const confirmed = buildPanel({
    imagesList: [generatedImage()],
    confirms: [true],
  });
  firstByClass(confirmed.threadsUl, "workspace-folder-generated-image-action-delete").click();
  await flushAsync();

  assert.deepEqual(confirmed.deleteCalls, [{ folderId: "folder-1", imageId: "image-1" }]);
  assert.equal(confirmed.refreshCount(), 1);
});

test("generated images panel renders no raw technical fields", () => {
  const rendered = buildPanel({
    imagesList: [
      GeneratedImages.normalizeWorkspaceGeneratedImageItem({
        target_name_internal: "UNSAFE_TARGET_SENTINEL",
        target_ref: "UNSAFE_TARGET_REF_SENTINEL",
        dav_url: "UNSAFE_DAV_SENTINEL",
        etag_value: "UNSAFE_ETAG_SENTINEL",
        content_hash: "UNSAFE_CONTENT_HASH_SENTINEL",
        prompt: "UNSAFE_PROMPT_SENTINEL",
        image_data_url: "data:image/png;base64,UNSAFE_DATA_URL_SENTINEL",
        generated_image_v1_user: {
          image_id: "safe-image",
          workspace_folder_id: "folder-1",
          display_name: "Safe image",
          format: "webp",
          mime_type: "image/webp",
          byte_size: 1024,
          width: 320,
          height: 240,
          status: "available",
          can_open: true,
          can_download: true,
          can_delete: true,
          actions: {
            open_reason_code: "folder_generated_image_open_ok",
            download_reason_code: "folder_generated_image_download_ok",
            delete_reason_code: "folder_generated_image_delete_ok",
          },
        },
      }),
    ],
  });

  const text = visibleText(rendered.threadsUl);
  assert.equal(text.includes("Safe image"), true);
  for (const forbidden of [
    "UNSAFE_TARGET_SENTINEL",
    "UNSAFE_TARGET_REF_SENTINEL",
    "UNSAFE_DAV_SENTINEL",
    "UNSAFE_ETAG_SENTINEL",
    "UNSAFE_CONTENT_HASH_SENTINEL",
    "UNSAFE_PROMPT_SENTINEL",
    "UNSAFE_DATA_URL_SENTINEL",
    "data:image",
    "base64",
  ]) {
    assert.equal(text.includes(forbidden), false, `${forbidden} must not render`);
  }
});
