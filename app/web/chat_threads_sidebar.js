const THREADS_PAGE_SIZE = 200;
const MAX_TITLE_LENGTH = 120;
const WorkspaceFolders = (
  typeof window !== "undefined" && window.FridaWorkspaceFolders
    ? window.FridaWorkspaceFolders
    : (typeof require !== "undefined" ? require("./chat_workspace_folders.js") : null)
);
const WorkspaceFoldersSidebar = (
  typeof window !== "undefined" && window.FridaWorkspaceFoldersSidebar
    ? window.FridaWorkspaceFoldersSidebar
    : (typeof require !== "undefined" ? require("./chat_workspace_folders_sidebar.js") : null)
);
const WorkspaceFolderExports = (
  typeof window !== "undefined" && window.FridaWorkspaceFolderExports
    ? window.FridaWorkspaceFolderExports
    : (typeof require !== "undefined" ? require("./chat_workspace_folder_exports.js") : null)
);
const WorkspaceFolderGeneratedImages = (
  typeof window !== "undefined" && window.FridaWorkspaceFolderGeneratedImages
    ? window.FridaWorkspaceFolderGeneratedImages
    : (typeof require !== "undefined" ? require("./chat_workspace_folder_generated_images.js") : null)
);
const WorkspaceFolderNotes = (
  typeof window !== "undefined" && window.FridaNotesMode
    ? window.FridaNotesMode
    : (typeof require !== "undefined" ? require("./chat_notes_mode.js") : null)
);
const ThreadsFolderBinding = (
  typeof FridaChatThreadsFolderBindingModule !== "undefined"
    ? FridaChatThreadsFolderBindingModule
    : (typeof require !== "undefined" ? require("./chat_threads_folder_binding.js") : null)
);
const ThreadsListRenderer = (
  typeof FridaChatThreadsListRendererModule !== "undefined"
    ? FridaChatThreadsListRendererModule
    : (typeof require !== "undefined" ? require("./chat_threads_list_renderer.js") : null)
);
const WORKSPACE_CONVERSATION_DRAG_MIME = "application/x-fridadev-conversation-id";

function clampThreadTitle(value, fallback = "Nouvelle conversation") {
  const normalized = String(value || "").replace(/\s+/g, " ").trim();
  const base = normalized || fallback;
  return base.length > MAX_TITLE_LENGTH ? `${base.slice(0, MAX_TITLE_LENGTH).trimEnd()}…` : base;
}

function normalizeThreadItem(item, cachedMessages = null) {
  const convId = String(item?.id || item?.conversation_id || "").trim();
  if (!convId) return null;
  return {
    id: convId,
    conversation_id: convId,
    title: clampThreadTitle(item?.title, "Nouvelle conversation"),
    messages: Array.isArray(cachedMessages) ? cachedMessages : [],
    created_at: item?.created_at || null,
    updated_at: item?.updated_at || item?.created_at || null,
    message_count: Number(item?.message_count || 0),
    last_message_preview: String(item?.last_message_preview || ""),
    workspace_folder_id: WorkspaceFolders?.normalizeWorkspaceFolderId(item?.workspace_folder_id) || null,
    deleted_at: item?.deleted_at || null,
  };
}

function createChatThreadsSidebar({
  threadsUl,
  logEl,
  fetchFn,
  setHero,
  closeSidebar,
  renderConversationMessage,
  scrollToBottom,
  notesModeController,
  consoleObj,
} = {}) {
  const httpFetch = fetchFn || (typeof fetch !== "undefined" ? fetch : null);
  const logger = consoleObj || (typeof console !== "undefined" ? console : { warn() {} });
  let editingThreadId = null;
  let threadsState = [];
  let foldersState = [];
  let workspaceFilesState = new Map();
  let workspaceFilesStatusState = new Map();
  let workspaceExportsState = new Map();
  let workspaceExportsStatusState = new Map();
  let workspaceGeneratedImagesState = new Map();
  let workspaceGeneratedImagesStatusState = new Map();
  let workspaceNotesState = new Map();
  let workspaceNotesStatusState = new Map();
  let workspaceFileSelectionsState = new Map();
  let currentThreadId = null;
  let threadLoadEpoch = 0;
  const messageCache = new Map();

  const threadStatus = document.createElement("div");
  threadStatus.className = "threads-status";
  threadStatus.style.fontSize = "11px";
  threadStatus.style.opacity = "0.82";
  threadStatus.style.padding = "6px 10px 2px";
  threadStatus.style.display = "none";
  if (threadsUl && threadsUl.parentElement) {
    threadsUl.parentElement.insertBefore(threadStatus, threadsUl);
  }

  const setThreadStatus = (message, isError = false) => {
    if (!threadStatus) return;
    const textMsg = String(message || "").trim();
    if (!textMsg) {
      threadStatus.textContent = "";
      threadStatus.style.display = "none";
      return;
    }
    threadStatus.textContent = textMsg;
    threadStatus.style.color = isError ? "#b85050" : "rgba(25,23,20,0.55)";
    threadStatus.style.display = "block";
  };

  const normalizeThread = (item) => {
    const convId = String(item?.id || item?.conversation_id || "").trim();
    const cachedMessages = convId ? messageCache.get(convId) : null;
    return normalizeThreadItem(item, cachedMessages);
  };

  const getThreads = () => threadsState;
  const saveThreads = (arr) => {
    threadsState = Array.isArray(arr) ? arr : [];
  };
  const getWorkspaceFolders = () => foldersState;
  const saveWorkspaceFolders = (arr) => {
    foldersState = Array.isArray(arr) ? arr : [];
  };
  const getWorkspaceFiles = (folderId) => workspaceFilesState.get(String(folderId || "")) || [];
  const getWorkspaceFilesStatus = (folderId) =>
    workspaceFilesStatusState.get(String(folderId || "")) || { status: "unknown", reason_code: "workspace_files_not_loaded" };
  const getWorkspaceExports = (folderId) => workspaceExportsState.get(String(folderId || "")) || [];
  const getWorkspaceExportsStatus = (folderId) =>
    workspaceExportsStatusState.get(String(folderId || "")) || { status: "unknown", reason_code: "workspace_exports_not_loaded" };
  const getWorkspaceGeneratedImages = (folderId) =>
    workspaceGeneratedImagesState.get(String(folderId || "")) || [];
  const getWorkspaceGeneratedImagesStatus = (folderId) =>
    workspaceGeneratedImagesStatusState.get(String(folderId || "")) || { status: "unknown", reason_code: "workspace_generated_images_not_loaded" };
  const getWorkspaceNotes = (folderId) => workspaceNotesState.get(String(folderId || "")) || [];
  const getWorkspaceNotesStatus = (folderId) =>
    workspaceNotesStatusState.get(String(folderId || "")) || { status: "unknown", reason_code: "workspace_notes_not_loaded" };
  const getWorkspaceFileSelections = (conversationId) =>
    workspaceFileSelectionsState.get(String(conversationId || "")) || [];
  const saveWorkspaceFilesEntries = (entries) => {
    workspaceFilesState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceFilesStatusEntries = (entries) => {
    workspaceFilesStatusState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceExportsEntries = (entries) => {
    workspaceExportsState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceExportsStatusEntries = (entries) => {
    workspaceExportsStatusState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceGeneratedImagesEntries = (entries) => {
    workspaceGeneratedImagesState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceGeneratedImagesStatusEntries = (entries) => {
    workspaceGeneratedImagesStatusState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceNotesEntries = (entries) => {
    workspaceNotesState = new Map(Array.isArray(entries) ? entries : []);
  };
  const saveWorkspaceNotesStatusEntries = (entries) => {
    workspaceNotesStatusState = new Map(Array.isArray(entries) ? entries : []);
  };
  const getCurrentId = () => currentThreadId;
  const setCurrentId = (id) => {
    currentThreadId = id || null;
  };
  const getThreadById = (id) => getThreads().find((x) => x.id === id);
  const setThreadMeta = (id, patch) => {
    const threads = getThreads();
    const t = threads.find((x) => x.id === id);
    if (!t || !patch || typeof patch !== "object") return;
    Object.assign(t, patch);
    saveThreads([...threads]);
  };

  const applyConversationTerminalMeta = (threadId, terminal) => {
    const updatedAt = String(terminal && terminal.updated_at || "").trim();
    if (!threadId || !updatedAt) return false;
    setThreadMeta(threadId, { updated_at: updatedAt });
    return true;
  };

  const formatTimestamp = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  async function parseServerResponse(res) {
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) {
      const msg = data?.error || `HTTP ${res.status}`;
      const err = new Error(msg);
      err.payload = data;
      err.status = res.status;
      throw err;
    }
    if (!data || data.ok === false) {
      const err = new Error(data?.error || "Réponse serveur invalide");
      err.payload = data;
      throw err;
    }
    return data;
  }

  function makeContentFreeListError(reasonCode, message = "Réponse liste invalide") {
    const err = new Error(message);
    err.payload = { reason_code: String(reasonCode || "list_payload_invalid") };
    return err;
  }

  function listErrorReason(err, fallbackReasonCode) {
    return String(err?.payload?.reason_code || err?.status || fallbackReasonCode || "list_error");
  }

  async function listConversationsFromServer(limit = THREADS_PAGE_SIZE, offset = 0) {
    const res = await httpFetch(`/api/conversations?limit=${encodeURIComponent(String(limit))}&offset=${encodeURIComponent(String(offset))}`);
    const data = await parseServerResponse(res);
    return Array.isArray(data.items) ? data.items : [];
  }

  async function listWorkspaceFoldersFromServer() {
    const res = await httpFetch("/api/workspace-folders");
    const data = await parseServerResponse(res);
    return WorkspaceFolders?.normalizeWorkspaceFoldersPayload(data) || [];
  }

  async function listWorkspaceFilesFromServer(folderId) {
    const res = await httpFetch(`/api/workspace-folders/${encodeURIComponent(folderId)}/files`);
    const data = await parseServerResponse(res);
    if (!Array.isArray(data?.items)) {
      throw makeContentFreeListError("workspace_files_lookup_failed");
    }
    return WorkspaceFolders?.normalizeWorkspaceFilesPayload(data) || [];
  }

  async function listWorkspaceExportsFromServer(folderId) {
    const res = await httpFetch(WorkspaceFolderExports.buildWorkspaceExportsListPath(folderId));
    const data = await parseServerResponse(res);
    if (!Array.isArray(data?.exports) && !Array.isArray(data?.items)) {
      throw makeContentFreeListError("folder_export_lookup_failed");
    }
    return WorkspaceFolderExports?.normalizeWorkspaceExportsPayload(data) || [];
  }

  async function listWorkspaceGeneratedImagesFromServer(folderId) {
    const res = await httpFetch(
      WorkspaceFolderGeneratedImages.buildWorkspaceGeneratedImagesListPath(folderId),
    );
    const data = await parseServerResponse(res);
    if (!Array.isArray(data?.generated_images) && !Array.isArray(data?.items)) {
      throw makeContentFreeListError("folder_generated_image_lookup_failed");
    }
    return WorkspaceFolderGeneratedImages?.normalizeWorkspaceGeneratedImagesPayload(data) || [];
  }

  async function listWorkspaceNotesFromServer(folderId) {
    const res = await httpFetch(WorkspaceFolderNotes.buildWorkspaceNotesListPath(folderId));
    const data = await parseServerResponse(res);
    return WorkspaceFolderNotes?.normalizeWorkspaceNotesPayload(data) || [];
  }

  async function listWorkspaceFileSelectionsFromServer(conversationId) {
    const res = await httpFetch(`/api/conversations/${encodeURIComponent(conversationId)}/workspace-file-selections`);
    const data = await parseServerResponse(res);
    return WorkspaceFolders?.normalizeWorkspaceFileSelectionsPayload(data) || [];
  }

  async function createConversationOnServer(title = "Nouvelle conversation") {
    const res = await httpFetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    const data = await parseServerResponse(res);
    return data.conversation || null;
  }

  async function renameConversationOnServer(conversationId, title) {
    const res = await httpFetch(`/api/conversations/${encodeURIComponent(conversationId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    const data = await parseServerResponse(res);
    return data.conversation || null;
  }

  async function moveConversationToWorkspaceFolderOnServer(conversationId, folderId) {
    const res = await httpFetch(`/api/conversations/${encodeURIComponent(conversationId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_folder_id: folderId || null }),
    });
    const data = await parseServerResponse(res);
    return data.conversation || null;
  }

  async function createWorkspaceFolderOnServer(displayName, iconKey = "folder") {
    const res = await httpFetch("/api/workspace-folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: displayName, icon_key: iconKey || "folder" }),
    });
    const data = await parseServerResponse(res);
    return data.folder || null;
  }

  async function updateWorkspaceFolderOnServer(folderId, patch) {
    const res = await httpFetch(`/api/workspace-folders/${encodeURIComponent(folderId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch || {}),
    });
    const data = await parseServerResponse(res);
    return data.folder || null;
  }

  async function deleteWorkspaceFolderOnServer(folderId) {
    const res = await httpFetch(`/api/workspace-folders/${encodeURIComponent(folderId)}`, {
      method: "DELETE",
    });
    const data = await parseServerResponse(res);
    return data.folder || null;
  }

  async function uploadWorkspaceFileOnServer(folderId, file) {
    const formData = new FormData();
    formData.append("file", file, file?.name || "fichier");
    const res = await httpFetch(`/api/workspace-folders/${encodeURIComponent(folderId)}/files`, {
      method: "POST",
      body: formData,
    });
    const data = await parseServerResponse(res);
    return data.file || null;
  }

  async function deleteWorkspaceFileOnServer(folderId, fileId) {
    const res = await httpFetch(
      `/api/workspace-folders/${encodeURIComponent(folderId)}/files/${encodeURIComponent(fileId)}`,
      { method: "DELETE" },
    );
    const data = await parseServerResponse(res);
    return data.file || null;
  }

  async function ocrWorkspaceFileOnServer(folderId, fileId) {
    const res = await httpFetch(
      `/api/workspace-folders/${encodeURIComponent(folderId)}/files/${encodeURIComponent(fileId)}/ocr`,
      { method: "POST" },
    );
    const data = await parseServerResponse(res);
    return data.file || null;
  }

  async function readWorkspaceOcrMarkdownOnServer(folderId, fileId) {
    const res = await httpFetch(
      `/api/workspace-folders/${encodeURIComponent(folderId)}/files/${encodeURIComponent(fileId)}/ocr-markdown`,
    );
    const data = await parseServerResponse(res);
    return data;
  }

  async function saveWorkspaceOcrMarkdownOnServer(folderId, fileId, content) {
    const res = await httpFetch(
      `/api/workspace-folders/${encodeURIComponent(folderId)}/files/${encodeURIComponent(fileId)}/ocr-markdown`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: String(content || "") }),
      },
    );
    const data = await parseServerResponse(res);
    return data.file || null;
  }

  async function createWorkspaceExportOnServer(folderId, payload) {
    const res = await httpFetch(WorkspaceFolderExports.buildWorkspaceExportsListPath(folderId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await parseServerResponse(res);
    return data.export || null;
  }

  async function createWorkspaceGeneratedImageOnServer(folderId, payload) {
    const res = await httpFetch(
      WorkspaceFolderGeneratedImages.buildWorkspaceGeneratedImagesListPath(folderId),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      },
    );
    const data = await parseServerResponse(res);
    return data.generated_image || null;
  }

  async function createWorkspaceNoteOnServer(folderId, payload) {
    const res = await httpFetch(WorkspaceFolderNotes.buildWorkspaceNotesListPath(folderId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await parseServerResponse(res);
    return data.note || null;
  }

  async function prepareWorkspaceNoteOnServer(folderId, noteId) {
    const res = await httpFetch(WorkspaceFolderNotes.buildWorkspaceNotePreparePath(folderId, noteId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    return parseServerResponse(res);
  }

  function openWorkspaceExport(folderId, exportId) {
    const href = WorkspaceFolderExports.buildWorkspaceExportContentPath(folderId, exportId, "open");
    if (typeof window !== "undefined" && typeof window.open === "function") {
      window.open(href, "_blank", "noopener");
    }
    return href;
  }

  function downloadWorkspaceExport(folderId, exportId) {
    const href = WorkspaceFolderExports.buildWorkspaceExportContentPath(folderId, exportId, "download");
    if (typeof document !== "undefined") {
      const link = document.createElement("a");
      link.href = href;
      link.rel = "noopener";
      link.download = "";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
    } else if (typeof window !== "undefined" && window.location) {
      window.location.href = href;
    }
    return href;
  }

  function openWorkspaceGeneratedImage(folderId, imageId) {
    const href = WorkspaceFolderGeneratedImages.buildWorkspaceGeneratedImageContentPath(
      folderId,
      imageId,
      "open",
    );
    if (typeof window !== "undefined" && typeof window.open === "function") {
      window.open(href, "_blank", "noopener");
    }
    return href;
  }

  function downloadWorkspaceGeneratedImage(folderId, imageId) {
    const href = WorkspaceFolderGeneratedImages.buildWorkspaceGeneratedImageContentPath(
      folderId,
      imageId,
      "download",
    );
    if (typeof document !== "undefined") {
      const link = document.createElement("a");
      link.href = href;
      link.rel = "noopener";
      link.download = "";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
    } else if (typeof window !== "undefined" && window.location) {
      window.location.href = href;
    }
    return href;
  }

  async function deleteWorkspaceGeneratedImageOnServer(folderId, imageId) {
    const res = await httpFetch(
      WorkspaceFolderGeneratedImages.buildWorkspaceGeneratedImageLookupPath(folderId, imageId),
      { method: "DELETE" },
    );
    const data = await parseServerResponse(res);
    return data.generated_image || null;
  }

  async function selectWorkspaceFileOnServer(conversationId, fileId) {
    const res = await httpFetch(`/api/conversations/${encodeURIComponent(conversationId)}/workspace-file-selections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: fileId }),
    });
    const data = await parseServerResponse(res);
    return data.selection || null;
  }

  async function deselectWorkspaceFileOnServer(conversationId, fileId) {
    const res = await httpFetch(
      `/api/conversations/${encodeURIComponent(conversationId)}/workspace-file-selections/${encodeURIComponent(fileId)}`,
      { method: "DELETE" },
    );
    await parseServerResponse(res);
    return true;
  }

  async function deleteConversationOnServer(conversationId) {
    const res = await httpFetch(`/api/conversations/${encodeURIComponent(conversationId)}`, {
      method: "DELETE",
    });
    await parseServerResponse(res);
  }

  async function fetchConversationMessagesFromServer(conversationId) {
    const res = await httpFetch(`/api/conversations/${encodeURIComponent(conversationId)}/messages`);
    return parseServerResponse(res);
  }

  const syncThreadFromServer = (payload) => {
    const normalized = normalizeThread(payload);
    if (!normalized) return null;

    const threads = getThreads();
    const idx = threads.findIndex((x) => x.id === normalized.id);
    if (idx >= 0) {
      const current = threads[idx];
      const merged = {
        ...current,
        ...normalized,
        messages: Array.isArray(current.messages) ? current.messages : normalized.messages,
      };
      threads[idx] = merged;
      saveThreads([...threads]);
      return merged;
    }

    saveThreads([normalized, ...threads]);
    return normalized;
  };

  const refreshThreadsFromServer = async ({ keepSelection = true } = {}) => {
    const previousCurrent = keepSelection ? getCurrentId() : null;
    try {
      const [items, folders] = await Promise.all([
        listConversationsFromServer(),
        listWorkspaceFoldersFromServer().catch((err) => {
          logger.warn("Impossible de charger les répertoires", err);
          return [];
        }),
      ]);
      const mapped = [];
      for (const item of items) {
        const normalized = normalizeThread(item);
        if (normalized) mapped.push(normalized);
      }
      saveThreads(mapped);
      saveWorkspaceFolders(folders);
      const fileEntries = [];
      const fileStatusEntries = [];
      for (const folder of folders) {
        try {
          fileEntries.push([folder.id, await listWorkspaceFilesFromServer(folder.id)]);
          fileStatusEntries.push([folder.id, {
            status: "ok",
            reason_code: "workspace_files_list_ok",
          }]);
        } catch (err) {
          const reason = listErrorReason(err, "workspace_files_lookup_failed");
          logger.warn("Impossible de charger les fichiers du répertoire", { reason_code: reason });
          fileEntries.push([folder.id, []]);
          fileStatusEntries.push([folder.id, {
            status: "error",
            reason_code: reason,
          }]);
        }
      }
      saveWorkspaceFilesEntries(fileEntries);
      saveWorkspaceFilesStatusEntries(fileStatusEntries);
      const exportEntries = [];
      const exportStatusEntries = [];
      for (const folder of folders) {
        if (!WorkspaceFolderExports?.canLoadWorkspaceExports?.(folder)) {
          exportEntries.push([folder.id, []]);
          exportStatusEntries.push([folder.id, {
            status: "not_applicable",
            reason_code: "folder_export_folder_not_linked",
          }]);
          continue;
        }
        try {
          exportEntries.push([folder.id, await listWorkspaceExportsFromServer(folder.id)]);
          exportStatusEntries.push([folder.id, {
            status: "ok",
            reason_code: "workspace_exports_list_ok",
          }]);
        } catch (err) {
          const reason = listErrorReason(err, "folder_export_lookup_failed");
          logger.warn("Impossible de charger les exports du répertoire", { reason_code: reason });
          exportEntries.push([folder.id, []]);
          exportStatusEntries.push([folder.id, {
            status: "error",
            reason_code: reason,
          }]);
        }
      }
      saveWorkspaceExportsEntries(exportEntries);
      saveWorkspaceExportsStatusEntries(exportStatusEntries);
      const generatedImageEntries = [];
      const generatedImageStatusEntries = [];
      for (const folder of folders) {
        if (!WorkspaceFolderGeneratedImages?.canLoadWorkspaceGeneratedImages?.(folder)) {
          generatedImageEntries.push([folder.id, []]);
          generatedImageStatusEntries.push([folder.id, {
            status: "not_applicable",
            reason_code: "folder_generated_image_folder_not_linked",
          }]);
          continue;
        }
        try {
          generatedImageEntries.push([folder.id, await listWorkspaceGeneratedImagesFromServer(folder.id)]);
          generatedImageStatusEntries.push([folder.id, {
            status: "ok",
            reason_code: "workspace_generated_images_list_ok",
          }]);
        } catch (err) {
          const reason = listErrorReason(err, "folder_generated_image_lookup_failed");
          logger.warn("Impossible de charger les images du répertoire", { reason_code: reason });
          generatedImageEntries.push([folder.id, []]);
          generatedImageStatusEntries.push([folder.id, {
            status: "error",
            reason_code: reason,
          }]);
        }
      }
      saveWorkspaceGeneratedImagesEntries(generatedImageEntries);
      saveWorkspaceGeneratedImagesStatusEntries(generatedImageStatusEntries);
      const noteEntries = [];
      const noteStatusEntries = [];
      for (const folder of folders) {
        if (!WorkspaceFolderNotes?.canLoadWorkspaceNotes?.(folder)) {
          noteEntries.push([folder.id, []]);
          noteStatusEntries.push([folder.id, {
            status: "not_applicable",
            reason_code: "workspace_notes_folder_not_linked",
          }]);
          continue;
        }
        try {
          noteEntries.push([folder.id, await listWorkspaceNotesFromServer(folder.id)]);
          noteStatusEntries.push([folder.id, {
            status: "ok",
            reason_code: "workspace_notes_list_ok",
          }]);
        } catch (err) {
          const reason = err?.payload?.reason_code || err?.status || "workspace_notes_list_error";
          logger.warn("Impossible de charger les notes du répertoire", { reason_code: String(reason) });
          noteEntries.push([folder.id, []]);
          noteStatusEntries.push([folder.id, {
            status: "error",
            reason_code: String(reason),
          }]);
        }
      }
      saveWorkspaceNotesEntries(noteEntries);
      saveWorkspaceNotesStatusEntries(noteStatusEntries);
      if (previousCurrent && mapped.some((x) => x.id === previousCurrent)) {
        setCurrentId(previousCurrent);
      } else {
        setCurrentId(mapped[0]?.id || null);
      }
      if (getCurrentId()) {
        await refreshWorkspaceFileSelections(getCurrentId());
      }
      setThreadStatus("");
      return true;
    } catch (err) {
      logger.warn("Impossible de charger les conversations", err);
      setThreadStatus("Mode hors ligne.", true);
      return false;
    }
  };

  const moveThreadToWorkspaceFolder = async (threadOrId, folderId) => {
    const thread = typeof threadOrId === "string" ? getThreadById(threadOrId) : threadOrId;
    if (!thread?.id) return;
    const nextFolderId = folderId || null;
    if ((thread.workspace_folder_id || null) === nextFolderId) return;
    try {
      const updated = await moveConversationToWorkspaceFolderOnServer(thread.id, nextFolderId);
      if (updated) syncThreadFromServer(updated);
      await refreshWorkspaceFileSelections(thread.id);
      await refreshThreadsFromServer({ keepSelection: true });
      renderThreads();
    } catch (err) {
      logger.warn("Déplacement conversation échoué", err);
      setThreadStatus("Déplacement non synchronisé.", true);
      renderThreads();
    }
  };

  const conversationFolderBinding = ThreadsFolderBinding.createConversationFolderBinding({
    threadsUl,
    dragMime: WORKSPACE_CONVERSATION_DRAG_MIME,
    isEditingThread: () => Boolean(editingThreadId),
    moveThreadToWorkspaceFolder,
  });
  const {
    bindConversationDropTarget,
  } = conversationFolderBinding;

  const refreshWorkspaceFiles = async (folderId) => {
    const normalized = WorkspaceFolders?.normalizeWorkspaceFolderId(folderId);
    if (!normalized) return [];
    try {
      const files = await listWorkspaceFilesFromServer(normalized);
      workspaceFilesState.set(normalized, files);
      workspaceFilesStatusState.set(normalized, {
        status: "ok",
        reason_code: "workspace_files_list_ok",
      });
      return files;
    } catch (err) {
      workspaceFilesState.set(normalized, []);
      workspaceFilesStatusState.set(normalized, {
        status: "error",
        reason_code: listErrorReason(err, "workspace_files_lookup_failed"),
      });
      throw err;
    }
  };

  const refreshWorkspaceExports = async (folderId) => {
    const normalized = WorkspaceFolders?.normalizeWorkspaceFolderId(folderId);
    if (!normalized) return [];
    const folder = getWorkspaceFolders().find((item) => item.id === normalized);
    if (!WorkspaceFolderExports?.canLoadWorkspaceExports?.(folder)) {
      workspaceExportsState.set(normalized, []);
      workspaceExportsStatusState.set(normalized, {
        status: "not_applicable",
        reason_code: "folder_export_folder_not_linked",
      });
      return [];
    }
    try {
      const exportsList = await listWorkspaceExportsFromServer(normalized);
      workspaceExportsState.set(normalized, exportsList);
      workspaceExportsStatusState.set(normalized, {
        status: "ok",
        reason_code: "workspace_exports_list_ok",
      });
      return exportsList;
    } catch (err) {
      workspaceExportsState.set(normalized, []);
      workspaceExportsStatusState.set(normalized, {
        status: "error",
        reason_code: listErrorReason(err, "folder_export_lookup_failed"),
      });
      throw err;
    }
  };

  const refreshWorkspaceGeneratedImages = async (folderId) => {
    const normalized = WorkspaceFolders?.normalizeWorkspaceFolderId(folderId);
    if (!normalized) return [];
    const folder = getWorkspaceFolders().find((item) => item.id === normalized);
    if (!WorkspaceFolderGeneratedImages?.canLoadWorkspaceGeneratedImages?.(folder)) {
      workspaceGeneratedImagesState.set(normalized, []);
      workspaceGeneratedImagesStatusState.set(normalized, {
        status: "not_applicable",
        reason_code: "folder_generated_image_folder_not_linked",
      });
      return [];
    }
    try {
      const images = await listWorkspaceGeneratedImagesFromServer(normalized);
      workspaceGeneratedImagesState.set(normalized, images);
      workspaceGeneratedImagesStatusState.set(normalized, {
        status: "ok",
        reason_code: "workspace_generated_images_list_ok",
      });
      return images;
    } catch (err) {
      workspaceGeneratedImagesState.set(normalized, []);
      workspaceGeneratedImagesStatusState.set(normalized, {
        status: "error",
        reason_code: listErrorReason(err, "folder_generated_image_lookup_failed"),
      });
      throw err;
    }
  };

  const refreshWorkspaceNotes = async (folderId) => {
    const normalized = WorkspaceFolders?.normalizeWorkspaceFolderId(folderId);
    if (!normalized) return [];
    const folder = getWorkspaceFolders().find((item) => item.id === normalized);
    if (!WorkspaceFolderNotes?.canLoadWorkspaceNotes?.(folder)) {
      workspaceNotesState.set(normalized, []);
      workspaceNotesStatusState.set(normalized, {
        status: "not_applicable",
        reason_code: "workspace_notes_folder_not_linked",
      });
      return [];
    }
    try {
      const notes = await listWorkspaceNotesFromServer(normalized);
      workspaceNotesState.set(normalized, notes);
      workspaceNotesStatusState.set(normalized, {
        status: "ok",
        reason_code: "workspace_notes_list_ok",
      });
      return notes;
    } catch (err) {
      const reason = err?.payload?.reason_code || err?.status || "workspace_notes_list_error";
      workspaceNotesState.set(normalized, []);
      workspaceNotesStatusState.set(normalized, {
        status: "error",
        reason_code: String(reason),
      });
      throw err;
    }
  };

  const refreshWorkspaceFileSelections = async (conversationId) => {
    const normalized = String(conversationId || "").trim();
    if (!normalized) return [];
    try {
      const selections = await listWorkspaceFileSelectionsFromServer(normalized);
      workspaceFileSelectionsState.set(normalized, selections);
      return selections;
    } catch (err) {
      logger.warn("Impossible de charger les sélections de fichiers", err);
      workspaceFileSelectionsState.set(normalized, []);
      return [];
    }
  };

  const workspaceFolderRenderer = WorkspaceFoldersSidebar?.createWorkspaceFolderSidebarRenderer({
    threadsUl,
    getWorkspaceFolders,
    getWorkspaceFiles,
    getWorkspaceFilesStatus,
    getWorkspaceExports,
    getWorkspaceExportsStatus,
    getWorkspaceGeneratedImages,
    getWorkspaceGeneratedImagesStatus,
    getWorkspaceNotes,
    getWorkspaceNotesStatus,
    refreshThreadsFromServer,
    refreshWorkspaceFiles,
    refreshWorkspaceExports,
    refreshWorkspaceGeneratedImages,
    refreshWorkspaceNotes,
    renderThreads: () => renderThreads(),
    setThreadStatus,
    createWorkspaceFolderOnServer,
    updateWorkspaceFolderOnServer,
    deleteWorkspaceFolderOnServer,
    uploadWorkspaceFileOnServer,
    deleteWorkspaceFileOnServer,
    ocrWorkspaceFileOnServer,
    readWorkspaceOcrMarkdownOnServer,
    saveWorkspaceOcrMarkdownOnServer,
    createWorkspaceExportOnServer,
    openWorkspaceExport,
    downloadWorkspaceExport,
    createWorkspaceGeneratedImageOnServer,
    createWorkspaceNoteOnServer,
    prepareWorkspaceNoteOnServer,
    openWorkspaceGeneratedImage,
    downloadWorkspaceGeneratedImage,
    deleteWorkspaceGeneratedImageOnServer,
    getCurrentThread: () => getThreadById(getCurrentId()),
    getWorkspaceFileSelections,
    selectWorkspaceFileOnServer,
    deselectWorkspaceFileOnServer,
    refreshWorkspaceFileSelections,
    notesModeController,
    bindConversationDropTarget,
    consoleObj: logger,
  });

  const deleteThread = async (li, threadId) => {
    li.style.opacity = "0";
    li.style.transform = "translateX(-6px)";

    const previous = [...getThreads()];
    saveThreads(previous.filter((item) => item.id !== threadId));
    messageCache.delete(threadId);
    if (getCurrentId() === threadId) {
      setCurrentId(getThreads()[0]?.id || null);
    }

    await new Promise((resolve) => setTimeout(resolve, 200));
    renderThreads();

    try {
      await deleteConversationOnServer(threadId);
      await refreshThreadsFromServer({ keepSelection: true });
      renderThreads();

      const selected = getCurrentId();
      if (selected) {
        await loadThread(selected);
      } else {
        logEl.innerHTML = "";
        await setHero();
      }
    } catch (err) {
      logger.warn("Suppression serveur échouée", err);
      saveThreads(previous);
      if (!getCurrentId() && previous.length) setCurrentId(previous[0].id);
      setThreadStatus("Suppression non synchronisée.", true);
      renderThreads();
    }
  };

  const selectThread = async (threadId) => {
    setCurrentId(threadId);
    await loadThread(threadId);
    renderThreads();
    closeSidebar();
  };

  const conversationListRenderer = ThreadsListRenderer.createConversationListRenderer({
    threadsUl,
    documentObj: document,
    getThreads,
    getWorkspaceFolders,
    getCurrentId,
    groupThreadsByWorkspaceFolder: (threads, folders) => (
      WorkspaceFolders?.groupThreadsByWorkspaceFolder(threads, folders)
      || { byFolder: new Map(), outside: threads }
    ),
    workspaceFolderRenderer,
    folderBinding: conversationFolderBinding,
    formatTimestamp,
    isEditingThread: () => Boolean(editingThreadId),
    onRename: (li, threadId) => startInlineRename(li, threadId),
    onDelete: deleteThread,
    onSelect: selectThread,
  });
  const renderThreads = () => conversationListRenderer.renderThreads();

  async function startInlineRename(li, threadId) {
    if (editingThreadId) return;
    editingThreadId = threadId;
    li.classList.add("editing");

    const threads = getThreads();
    const idx = threads.findIndex((x) => x.id === threadId);
    if (idx === -1) {
      editingThreadId = null;
      li.classList.remove("editing");
      return;
    }

    const main = li.querySelector(".thread-main");
    const titleSpan = li.querySelector(".title");
    if (!main || !titleSpan) {
      editingThreadId = null;
      li.classList.remove("editing");
      return;
    }

    const input = document.createElement("input");
    input.type = "text";
    input.className = "rename-input";
    input.value = titleSpan.textContent || "Nouvelle conversation";
    input.setAttribute("aria-label", "Renommer la conversation");

    const btns = main.querySelectorAll(".thread-edit, .thread-del");
    btns.forEach((b) => { b.style.visibility = "hidden"; });

    main.replaceChild(input, titleSpan);
    input.focus();
    input.select();

    let handled = false;
    const restore = () => {
      if (input.parentNode === main) {
        main.replaceChild(titleSpan, input);
      }
      btns.forEach((b) => { b.style.visibility = ""; });
      li.classList.remove("editing");
      editingThreadId = null;
    };

    const commit = async () => {
      if (handled) return;
      handled = true;
      const next = clampThreadTitle(input.value || "", "");
      const previousTitle = threads[idx].title || "Nouvelle conversation";
      restore();
      if (!next || next === previousTitle) return;

      threads[idx].title = next;
      saveThreads([...threads]);
      renderThreads();

      try {
        const updated = await renameConversationOnServer(threadId, next);
        if (updated) {
          syncThreadFromServer(updated);
          renderThreads();
        }
      } catch (err) {
        logger.warn("Rename conversation échoué", err);
        setThreadMeta(threadId, { title: previousTitle });
        setThreadStatus("Renommage non synchronisé.", true);
        renderThreads();
      }
    };

    const cancel = () => {
      if (handled) return;
      handled = true;
      restore();
    };

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        void commit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        cancel();
      }
    });
    input.addEventListener("blur", () => void commit());
  }

  const newThread = async () => {
    try {
      const created = await createConversationOnServer("Nouvelle conversation");
      const normalized = normalizeThread(created);
      if (!normalized) {
        throw new Error("Conversation invalide");
      }

      messageCache.set(normalized.id, []);
      syncThreadFromServer(normalized);
      setCurrentId(normalized.id);
      logEl.innerHTML = "";
      await setHero();
      renderThreads();
      closeSidebar();
    } catch (err) {
      logger.warn("Création conversation échouée", err);
      setThreadStatus("Impossible de créer une conversation.", true);
    }
  };

  const hydrateThreadMessages = async (conversationId, { force = false } = {}) => {
    if (!conversationId) return [];
    if (!force && messageCache.has(conversationId)) {
      const cached = messageCache.get(conversationId) || [];
      const thread = getThreadById(conversationId);
      if (thread) {
        thread.messages = cached;
        saveThreads([...getThreads()]);
      }
      return cached;
    }

    const data = await fetchConversationMessagesFromServer(conversationId);
    const messages = Array.isArray(data.messages) ? data.messages : [];
    const sanitized = messages
      .filter((m) => m && typeof m.content === "string")
      .map((m) => {
        const sanitizedMessage = {
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || null,
        };
        if (m.meta && typeof m.meta === "object") {
          sanitizedMessage.meta = m.meta;
        }
        return sanitizedMessage;
      });

    messageCache.set(conversationId, sanitized);

    const thread = getThreadById(conversationId);
    if (thread) {
      thread.messages = sanitized;
      thread.title = clampThreadTitle(data.title || thread.title || "Nouvelle conversation");
      thread.created_at = data.created_at || thread.created_at;
      thread.updated_at = data.updated_at || thread.updated_at;
      thread.message_count = sanitized.filter((m) => m.role === "user" || m.role === "assistant").length;
      saveThreads([...getThreads()]);
    }

    return sanitized;
  };

  const loadThread = async (id) => {
    const requestEpoch = ++threadLoadEpoch;
    const isCurrentRequest = () => requestEpoch === threadLoadEpoch && getCurrentId() === id;
    const t = getThreadById(id);
    logEl.innerHTML = "";
    await setHero();
    if (!isCurrentRequest()) return;
    if (!t) return;

    try {
      await hydrateThreadMessages(id);
      if (!isCurrentRequest()) return;
      await refreshWorkspaceFileSelections(id);
      if (!isCurrentRequest()) return;
      setThreadStatus("");
    } catch (err) {
      if (!isCurrentRequest()) return;
      logger.warn("Chargement conversation échoué", err);
      setThreadStatus("Impossible de charger cette conversation.", true);
      return;
    }

    if (!isCurrentRequest()) return;
    const refreshed = getThreadById(id);
    (refreshed?.messages || []).forEach((m) => {
      if (m.role !== "user" && m.role !== "assistant") return;
      renderConversationMessage(m);
    });

    scrollToBottom(false);
  };

  const appendMessageToThread = (threadId, role, content, timestamp = null, meta = null) => {
    const id = threadId || null;
    if (!id) return;
    const thread = getThreadById(id);
    if (!thread) return;

    const existing = Array.isArray(messageCache.get(id)) ? messageCache.get(id) : [];
    const nextMessage = { role, content, timestamp };
    if (meta && typeof meta === "object") {
      nextMessage.meta = meta;
    }
    const nextMessages = [...existing, nextMessage];
    messageCache.set(id, nextMessages);

    thread.messages = nextMessages;
    thread.updated_at = timestamp || new Date().toISOString();
    thread.message_count = nextMessages.filter((m) => m.role === "user" || m.role === "assistant").length;
    if (role === "user") {
      thread.last_message_preview = String(content || "").slice(0, 180);
    }
    saveThreads([...getThreads()]);
  };

  const appendToThread = (role, content, timestamp = null, meta = null) => {
    appendMessageToThread(getCurrentId(), role, content, timestamp, meta);
  };

  return Object.freeze({
    getThreads,
    saveThreads,
    getWorkspaceFolders,
    saveWorkspaceFolders,
    getWorkspaceFiles,
    getWorkspaceFilesStatus,
    getWorkspaceExports,
    getWorkspaceExportsStatus,
    getWorkspaceFileSelections,
    getWorkspaceNotes,
    getWorkspaceNotesStatus,
    getCurrentId,
    setCurrentId,
    getThreadById,
    setThreadMeta,
    applyConversationTerminalMeta,
    listConversationsFromServer,
    listWorkspaceFoldersFromServer,
    listWorkspaceFileSelectionsFromServer,
    createConversationOnServer,
    createWorkspaceFolderOnServer,
    updateWorkspaceFolderOnServer,
    deleteWorkspaceFolderOnServer,
    listWorkspaceFilesFromServer,
    listWorkspaceExportsFromServer,
    listWorkspaceNotesFromServer,
    uploadWorkspaceFileOnServer,
    deleteWorkspaceFileOnServer,
    ocrWorkspaceFileOnServer,
    readWorkspaceOcrMarkdownOnServer,
    saveWorkspaceOcrMarkdownOnServer,
    createWorkspaceExportOnServer,
    createWorkspaceNoteOnServer,
    prepareWorkspaceNoteOnServer,
    openWorkspaceExport,
    downloadWorkspaceExport,
    getWorkspaceGeneratedImages,
    getWorkspaceGeneratedImagesStatus,
    listWorkspaceGeneratedImagesFromServer,
    createWorkspaceGeneratedImageOnServer,
    openWorkspaceGeneratedImage,
    downloadWorkspaceGeneratedImage,
    deleteWorkspaceGeneratedImageOnServer,
    selectWorkspaceFileOnServer,
    deselectWorkspaceFileOnServer,
    renameConversationOnServer,
    moveConversationToWorkspaceFolderOnServer,
    deleteConversationOnServer,
    fetchConversationMessagesFromServer,
    syncThreadFromServer,
    refreshThreadsFromServer,
    refreshWorkspaceExports,
    refreshWorkspaceGeneratedImages,
    refreshWorkspaceNotes,
    refreshWorkspaceFileSelections,
    renderThreads,
    startInlineRename,
    newThread,
    hydrateThreadMessages,
    loadThread,
    appendMessageToThread,
    appendToThread,
  });
}

const FridaChatThreadsSidebar = Object.freeze({
  THREADS_PAGE_SIZE,
  MAX_TITLE_LENGTH,
  WORKSPACE_CONVERSATION_DRAG_MIME,
  clampThreadTitle,
  normalizeThreadItem,
  createChatThreadsSidebar,
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = FridaChatThreadsSidebar;
}

if (typeof window !== "undefined") {
  window.FridaChatThreadsSidebar = FridaChatThreadsSidebar;
}
