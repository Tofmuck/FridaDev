const test = require("node:test");
const assert = require("node:assert/strict");

const GeneratedImages = require("../../../web/chat_workspace_folder_generated_images.js");
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

function assertNoGlobalGeneratedImageRoute(path) {
  assert.equal(path.startsWith("/api/generated-images"), false);
  assert.equal(path.startsWith("/api/images"), false);
  assert.equal(path.startsWith("/api/tools/image-generation"), false);
}

test("generated image normalizer keeps user fields and strips technical internals", () => {
  const item = GeneratedImages.normalizeWorkspaceGeneratedImageItem({
    id: "image-1",
    workspace_folder_id: "folder-1",
    target_name_internal: "UNSAFE_TARGET_SENTINEL",
    target_ref: "UNSAFE_TARGET_REF_SENTINEL",
    dav_url: "UNSAFE_DAV_SENTINEL",
    etag_value: "UNSAFE_ETAG_SENTINEL",
    content_hash: "UNSAFE_CONTENT_HASH_SENTINEL",
    prompt: "UNSAFE_PROMPT_SENTINEL",
    image_data_url: "data:image/png;base64,UNSAFE_DATA_URL_SENTINEL",
    generated_image_v1_user: {
      image_id: "image-1",
      workspace_folder_id: "folder-1",
      display_name: "Image visible",
      format: "png",
      mime_type: "image/png",
      byte_size: 4096,
      width: 640,
      height: 480,
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
    },
  });

  assert.equal(item.display_name, "Image visible");
  assert.equal(item.format, "png");
  assert.equal(item.mime_type, "image/png");
  assert.equal(item.can_open, true);
  assert.equal(item.can_download, true);
  assert.equal(item.can_delete, true);
  assert.equal(
    GeneratedImages.compactWorkspaceGeneratedImageMeta(item),
    "PNG · 640 x 480 px · 4 ko · 20/06/2026 · disponible",
  );
  const serialized = JSON.stringify(item);
  for (const forbidden of [
    "UNSAFE_TARGET_SENTINEL",
    "UNSAFE_TARGET_REF_SENTINEL",
    "UNSAFE_DAV_SENTINEL",
    "UNSAFE_ETAG_SENTINEL",
    "UNSAFE_CONTENT_HASH_SENTINEL",
    "UNSAFE_PROMPT_SENTINEL",
    "UNSAFE_DATA_URL_SENTINEL",
  ]) {
    assert.equal(serialized.includes(forbidden), false, `${forbidden} must not survive`);
  }
});

test("generated image route builders use only workspace-folder namespaced routes", () => {
  const list = GeneratedImages.buildWorkspaceGeneratedImagesListPath("folder 1");
  const lookup = GeneratedImages.buildWorkspaceGeneratedImageLookupPath("folder 1", "image/1");
  const open = GeneratedImages.buildWorkspaceGeneratedImageContentPath("folder 1", "image/1", "open");
  const download = GeneratedImages.buildWorkspaceGeneratedImageContentPath("folder 1", "image/1", "download");

  assert.equal(list, "/api/workspace-folders/folder%201/generated-images");
  assert.equal(lookup, "/api/workspace-folders/folder%201/generated-images/image%2F1");
  assert.equal(open, "/api/workspace-folders/folder%201/generated-images/image%2F1/open");
  assert.equal(download, "/api/workspace-folders/folder%201/generated-images/image%2F1/download");
  for (const path of [list, lookup, open, download]) {
    assertNoGlobalGeneratedImageRoute(path);
  }
});

test("generated image create payload stays scoped and transient", () => {
  const payload = GeneratedImages.buildWorkspaceGeneratedImagePayload({
    prompt: "Prompt visible only in request",
    generatorKey: "image_generator_nano_banana",
    aspectRatio: "1:1",
    imageSize: "1K",
    displayName: "Image durable",
  });

  assert.deepEqual(payload, {
    prompt: "Prompt visible only in request",
    generator_key: "image_generator_nano_banana",
    aspect_ratio: "1:1",
    image_size: "1K",
    display_name: "Image durable",
  });
  for (const forbidden of [
    "workspace_folder_id",
    "image_id",
    "bytes",
    "base64",
    "data_url",
    "image_data_url",
    "target_name_internal",
    "target_ref",
    "dav_url",
    "etag_value",
    "content_hash",
  ]) {
    assert.equal(Object.hasOwn(payload, forbidden), false, `${forbidden} must not be sent`);
  }
});

test("generated images load only for active linked folders", () => {
  assert.equal(
    GeneratedImages.canLoadWorkspaceGeneratedImages({
      id: "folder-1",
      nextcloud_sync_state: "linked",
      deleted_at: null,
    }),
    true,
  );
  assert.equal(
    GeneratedImages.canLoadWorkspaceGeneratedImages({
      id: "folder-2",
      nextcloud_sync_state: "local_only",
      deleted_at: null,
    }),
    false,
  );
  assert.equal(
    GeneratedImages.canLoadWorkspaceGeneratedImages({
      id: "folder-3",
      nextcloud_sync_state: "linked",
      deleted_at: "2026-06-20T12:00:00Z",
    }),
    false,
  );
});

test("threads lifecycle lists creates opens downloads and deletes generated images through folder namespace", async () => {
  const calls = [];
  const lifecycle = createLifecycle(async (url, options = {}) => {
    calls.push({ url, options });
    if (options.method === "POST") {
      return jsonResponse({
        ok: true,
        generated_image: {
          generated_image_v1_user: {
            image_id: "image-created",
            workspace_folder_id: "folder-1",
            display_name: "Created",
            format: "png",
          },
        },
      });
    }
    if (options.method === "DELETE") {
      return jsonResponse({
        ok: true,
        generated_image: {
          generated_image_v1_user: {
            image_id: "image-1",
            workspace_folder_id: "folder-1",
            display_name: "Deleted",
            format: "png",
          },
        },
      });
    }
    return jsonResponse({
      ok: true,
      generated_images: [{
        generated_image_v1_user: {
          image_id: "image-1",
          workspace_folder_id: "folder-1",
          display_name: "Listed",
          format: "png",
          can_open: true,
          can_download: true,
          can_delete: true,
          actions: {
            open_reason_code: "folder_generated_image_open_ok",
            download_reason_code: "folder_generated_image_download_ok",
            delete_reason_code: "folder_generated_image_delete_ok",
          },
        },
      }],
    });
  });
  const opened = [];
  global.window = {
    open: (href, target, features) => opened.push({ href, target, features }),
  };

  const listed = await lifecycle.listWorkspaceGeneratedImagesFromServer("folder-1");
  const payload = GeneratedImages.buildWorkspaceGeneratedImagePayload({
    prompt: "Prompt transient",
    generatorKey: "image_generator_nano_banana",
    aspectRatio: "1:1",
    imageSize: "1K",
    displayName: "Created",
  });
  await lifecycle.createWorkspaceGeneratedImageOnServer("folder-1", payload);
  const openPath = lifecycle.openWorkspaceGeneratedImage("folder-1", "image-1");
  const downloadPath = lifecycle.downloadWorkspaceGeneratedImage("folder-1", "image-1");
  await lifecycle.deleteWorkspaceGeneratedImageOnServer("folder-1", "image-1");

  assert.equal(listed.length, 1);
  assert.equal(calls[0].url, "/api/workspace-folders/folder-1/generated-images");
  assert.equal(calls[1].url, "/api/workspace-folders/folder-1/generated-images");
  assert.equal(calls[1].options.method, "POST");
  const body = JSON.parse(calls[1].options.body);
  assert.equal(body.prompt, "Prompt transient");
  assert.equal(body.generator_key, "image_generator_nano_banana");
  assert.equal(Object.hasOwn(body, "workspace_folder_id"), false);
  assert.equal(Object.hasOwn(body, "image_id"), false);
  assert.equal(openPath, "/api/workspace-folders/folder-1/generated-images/image-1/open");
  assert.deepEqual(opened, [{
    href: "/api/workspace-folders/folder-1/generated-images/image-1/open",
    target: "_blank",
    features: "noopener",
  }]);
  assert.equal(downloadPath, "/api/workspace-folders/folder-1/generated-images/image-1/download");
  assert.equal(calls[2].url, "/api/workspace-folders/folder-1/generated-images/image-1");
  assert.equal(calls[2].options.method, "DELETE");
  for (const call of calls) {
    assertNoGlobalGeneratedImageRoute(String(call.url));
  }
  assertNoGlobalGeneratedImageRoute(openPath);
  assertNoGlobalGeneratedImageRoute(downloadPath);
});
