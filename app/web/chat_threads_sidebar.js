const THREADS_PAGE_SIZE = 200;
const MAX_TITLE_LENGTH = 120;

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
  consoleObj,
} = {}) {
  const httpFetch = fetchFn || (typeof fetch !== "undefined" ? fetch : null);
  const logger = consoleObj || (typeof console !== "undefined" ? console : { warn() {} });
  let editingThreadId = null;
  let threadsState = [];
  let currentThreadId = null;
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
      throw new Error(msg);
    }
    if (!data || data.ok === false) {
      throw new Error(data?.error || "Réponse serveur invalide");
    }
    return data;
  }

  async function listConversationsFromServer(limit = THREADS_PAGE_SIZE, offset = 0) {
    const res = await httpFetch(`/api/conversations?limit=${encodeURIComponent(String(limit))}&offset=${encodeURIComponent(String(offset))}`);
    const data = await parseServerResponse(res);
    return Array.isArray(data.items) ? data.items : [];
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
      const items = await listConversationsFromServer();
      const mapped = [];
      for (const item of items) {
        const normalized = normalizeThread(item);
        if (normalized) mapped.push(normalized);
      }
      saveThreads(mapped);
      if (previousCurrent && mapped.some((x) => x.id === previousCurrent)) {
        setCurrentId(previousCurrent);
      } else {
        setCurrentId(mapped[0]?.id || null);
      }
      setThreadStatus("");
      return true;
    } catch (err) {
      logger.warn("Impossible de charger les conversations", err);
      setThreadStatus("Mode hors ligne.", true);
      return false;
    }
  };

  const renderThreads = () => {
    threadsUl.innerHTML = "";
    const threads = getThreads();
    const current = getCurrentId();

    threads.forEach((t) => {
      const li = document.createElement("li");
      if (t.id === current) li.classList.add("active");
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      li.setAttribute("aria-label", t.title || "Conversation");

      const main = document.createElement("div");
      main.className = "thread-main";

      const titleSpan = document.createElement("span");
      titleSpan.className = "title";
      titleSpan.textContent = t.title || "Sans titre";
      main.appendChild(titleSpan);

      const editBtn = document.createElement("button");
      editBtn.className = "thread-edit";
      editBtn.title = "Renommer";
      editBtn.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;
      editBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        startInlineRename(li, t.id);
      });
      main.appendChild(editBtn);

      const delBtn = document.createElement("button");
      delBtn.className = "thread-del";
      delBtn.title = "Supprimer";
      delBtn.innerHTML = `<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/></svg>`;
      delBtn.addEventListener("click", async (e) => {
        e.stopPropagation();

        li.style.opacity = "0";
        li.style.transform = "translateX(-6px)";

        const previous = [...getThreads()];
        saveThreads(previous.filter((x) => x.id !== t.id));
        messageCache.delete(t.id);
        if (getCurrentId() === t.id) {
          setCurrentId(getThreads()[0]?.id || null);
        }

        await new Promise((r) => setTimeout(r, 200));
        renderThreads();

        try {
          await deleteConversationOnServer(t.id);
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
      });
      main.appendChild(delBtn);

      li.appendChild(main);

      const ts = t.updated_at || t.created_at;
      if (ts) {
        const timeSpan = document.createElement("span");
        timeSpan.className = "thread-time";
        timeSpan.textContent = formatTimestamp(ts);
        li.appendChild(timeSpan);
      }

      titleSpan.addEventListener("dblclick", (ev) => {
        ev.stopPropagation();
        startInlineRename(li, t.id);
      });

      li.addEventListener("click", async () => {
        if (editingThreadId) return;
        setCurrentId(t.id);
        await loadThread(t.id);
        renderThreads();
        closeSidebar();
      });

      threadsUl.appendChild(li);
    });
  };

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
    const t = getThreadById(id);
    logEl.innerHTML = "";
    await setHero();
    if (!t) return;

    try {
      await hydrateThreadMessages(id);
      setThreadStatus("");
    } catch (err) {
      logger.warn("Chargement conversation échoué", err);
      setThreadStatus("Impossible de charger cette conversation.", true);
      return;
    }

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
    getCurrentId,
    setCurrentId,
    getThreadById,
    setThreadMeta,
    applyConversationTerminalMeta,
    listConversationsFromServer,
    createConversationOnServer,
    renameConversationOnServer,
    deleteConversationOnServer,
    fetchConversationMessagesFromServer,
    syncThreadFromServer,
    refreshThreadsFromServer,
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
