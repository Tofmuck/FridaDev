(() => {
  if (typeof document === "undefined") return;
  const chatStreaming = window.FridaChatStreaming;
  if (!chatStreaming) {
    throw new Error("FridaChatStreaming module missing");
  }
  const chatThreadsSidebar = window.FridaChatThreadsSidebar;
  if (!chatThreadsSidebar) {
    throw new Error("FridaChatThreadsSidebar module missing");
  }
  const {
    STREAMING_UI_STATE_INTERRUPTED,
    STREAMING_UI_EVENT_REQUEST_STARTED,
    STREAMING_UI_EVENT_RESPONSE_OPENED,
    STREAMING_UI_EVENT_VISIBLE_CONTENT,
    STREAMING_UI_EVENT_TERMINAL_DONE,
    STREAMING_UI_EVENT_TERMINAL_ERROR,
    createStreamControlParser,
    createStreamTerminalError,
    getObservableStreamErrorMeta,
    buildInterruptedAssistantTurnMeta,
    getPersistedAssistantTurnErrorMeta,
    reduceStreamingUiState,
    getStreamingUiStateMeta,
    hasVisibleAssistantContent,
  } = chatStreaming;
  const $ = (sel) => document.querySelector(sel);

  // ---- DOM refs
  const hero = $("#hero");
  const log = $("#log");
  const chatEl = document.querySelector('.chat');
  const ask = $("#ask");
  const message = $("#message");
  const btnMic = $("#btnMic");
  const btnWebSearch = $("#btnWebSearch");
  const dictationStatus = $("#dictationStatus");
  const newChatBtn = $("#newChat");
  const threadsUl = $("#threads");
  // Mobile sidebar
  const sidebar = document.querySelector('.sidebar');
  const sidebarBackdrop = $("#sidebarBackdrop");
  const btnMenu = $("#btnMenu");
  const openSidebar  = () => { sidebar.classList.add('open');    sidebarBackdrop && sidebarBackdrop.classList.add('show'); };
  const closeSidebar = () => { sidebar.classList.remove('open'); sidebarBackdrop && sidebarBackdrop.classList.remove('show'); };
  if (btnMenu)         btnMenu.addEventListener('click', openSidebar);
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

  // ---- Web search toggle
  let webSearchEnabled = localStorage.getItem("frida.webSearch") === "1";
  const updateWebSearchBtn = () => {
    if (!btnWebSearch) return;
    btnWebSearch.classList.toggle("active", webSearchEnabled);
    btnWebSearch.title = webSearchEnabled ? "Recherche web : activée" : "Recherche web : désactivée";
  };
  if (btnWebSearch) {
    updateWebSearchBtn();
    btnWebSearch.addEventListener("click", () => {
      webSearchEnabled = !webSearchEnabled;
      localStorage.setItem("frida.webSearch", webSearchEnabled ? "1" : "0");
      updateWebSearchBtn();
    });
  }
  try {
    localStorage.removeItem("frida.settings");
  } catch {}
  // ---- Helpers
  const fmtDateFR = (d = new Date()) =>
    d.toLocaleDateString("fr-FR", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

  const scrollToBottom = (smooth = true) => {
    if (!chatEl) return;
    chatEl.scrollTo({ top: chatEl.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  };

  const extractErrorMessage = (err) => {
    return getObservableStreamErrorMeta(err).bubbleMessage;
  };

  const focusMessageDraft = () => {
    if (!message) return;
    message.focus();
    if (typeof message.setSelectionRange === "function") {
      const end = String(message.value || "").length;
      message.setSelectionRange(end, end);
    }
  };

  const fmtHour = (value) => {
    if (!value) return null;
    const d = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return `${d.getHours()}h${String(d.getMinutes()).padStart(2, '0')}`;
  };

  const resolveDisplayName = (role) => {
    if (role === "assistant") return "Frida";
    if (role === "user" || role === "olive") return "Vous";
    return role;
  };

  const buildBylineText = (role, timestamp = null) => {
    const hourStr = fmtHour(timestamp);
    return hourStr ? `${resolveDisplayName(role)} · ${hourStr}` : resolveDisplayName(role);
  };

  const setMessageNodeTimestamp = (messageNode, role, timestamp = null) => {
    if (!messageNode || !messageNode.byline) return;
    messageNode.byline.textContent = buildBylineText(role, timestamp);
  };

  const hasTerminalUpdatedAt = (terminal) => Boolean(String(terminal && terminal.updated_at || "").trim());

  const createMessageNode = (role, text = "", timestamp = null) => {
    const wrapper = document.createElement("div");
    wrapper.className = `msg-wrapper ${role === "user" ? "me" : ""}`;

    const bubble = document.createElement("div");
    bubble.className = `msg ${role === "user" ? "me" : ""}`;
    bubble.innerText = text;

    const by = document.createElement("div");
    by.className = "byline";
    by.textContent = buildBylineText(role, timestamp);

    let status = null;
    if (role === "assistant") {
      status = document.createElement("div");
      status.className = "msg-stream-status";
      status.hidden = true;
      status.setAttribute("aria-live", "polite");
    }

    wrapper.appendChild(bubble);
    if (status) {
      wrapper.appendChild(status);
    }
    wrapper.appendChild(by);
    log.appendChild(wrapper);

    scrollToBottom(true);
    return { wrapper, bubble, status, byline: by, streamingState: null };
  };

  const setHero = async () => {
    const dateStr = fmtDateFR();
    hero.textContent = `${dateStr}.`;
  };

  const addMsg = (role, text, timestamp = null) => createMessageNode(role, text, timestamp);

  const renderConversationMessage = (messageRecord) => {
    const role = String(messageRecord && messageRecord.role || "");
    const timestamp = messageRecord && messageRecord.timestamp ? messageRecord.timestamp : null;
    const persistedErrorMeta = getPersistedAssistantTurnErrorMeta(messageRecord);
    if (persistedErrorMeta) {
      const assistantNode = createMessageNode("assistant", persistedErrorMeta.bubbleMessage, timestamp);
      applyAssistantStreamingFailure(assistantNode, persistedErrorMeta);
      return assistantNode;
    }
    return addMsg(role, String(messageRecord && messageRecord.content || ""), timestamp);
  };

  const renderAssistantStreamingUiState = (assistantNode, state) => {
    if (!assistantNode || !assistantNode.status) return;
    const meta = getStreamingUiStateMeta(state, assistantNode.streamingErrorMeta || null);
    assistantNode.status.textContent = meta && meta.visible ? meta.label : "";
    assistantNode.status.hidden = !(meta && meta.visible);
    if (meta && meta.visible) {
      assistantNode.status.dataset.state = state;
      assistantNode.status.dataset.tone = meta.tone;
    } else {
      delete assistantNode.status.dataset.state;
      delete assistantNode.status.dataset.tone;
    }
  };

  const applyAssistantStreamingUiEvent = (assistantNode, event) => {
    if (!assistantNode) return null;
    const nextState = reduceStreamingUiState(assistantNode.streamingState || null, event);
    if (nextState !== STREAMING_UI_STATE_INTERRUPTED) {
      assistantNode.streamingErrorMeta = null;
    }
    if (nextState === assistantNode.streamingState) {
      return nextState;
    }
    assistantNode.streamingState = nextState;
    renderAssistantStreamingUiState(assistantNode, nextState);
    return nextState;
  };

  const applyAssistantStreamingFailure = (assistantNode, errorMeta) => {
    if (!assistantNode) return null;
    assistantNode.streamingErrorMeta = errorMeta || getObservableStreamErrorMeta(null);
    assistantNode.streamingState = STREAMING_UI_STATE_INTERRUPTED;
    renderAssistantStreamingUiState(assistantNode, STREAMING_UI_STATE_INTERRUPTED);
    return assistantNode.streamingState;
  };

  let chatRequestInFlight = false;
  let dictationController = null;
  let currentDraftInputMode = "keyboard";

  const syncDictationUi = () => {
    if (!dictationController || typeof dictationController.refreshUi !== "function") return;
    dictationController.refreshUi();
  };

  const setCurrentDraftInputMode = (nextMode) => {
    currentDraftInputMode = nextMode === "voice" ? "voice" : "keyboard";
  };

  const threadsLifecycle = chatThreadsSidebar.createChatThreadsSidebar({
    threadsUl,
    logEl: log,
    fetchFn: fetch,
    setHero,
    closeSidebar,
    renderConversationMessage,
    scrollToBottom,
    consoleObj: console,
  });
  const {
    getCurrentId,
    getThreadById,
    setThreadMeta,
    applyConversationTerminalMeta,
    refreshThreadsFromServer,
    renderThreads,
    newThread,
    hydrateThreadMessages,
    loadThread,
    appendMessageToThread,
  } = threadsLifecycle;

  // ---- Nouveau chat
  newChatBtn.addEventListener("click", () => { void newThread(); });

  if (window.FridaWhisperDictation && btnMic && message) {
    dictationController = window.FridaWhisperDictation.createWhisperDictation({
      buttonEl: btnMic,
      statusEl: dictationStatus,
      textareaEl: message,
      endpoint: "/api/chat/transcribe",
      getDraftValue: () => message.value || "",
      setDraftValue: (nextValue) => {
        message.value = nextValue;
      },
      focusDraft: focusMessageDraft,
      isBusy: () => chatRequestInFlight,
      onDraftInputMode: setCurrentDraftInputMode,
    });
    syncDictationUi();
  }

  if (message) {
    message.addEventListener("input", () => {
      if (!(message.value || "").trim()) {
        setCurrentDraftInputMode("keyboard");
      }
    });
  }

  // ---- Envoi
  ask.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = (message.value || "").trim();
    if (!text) return;
    const inputMode = currentDraftInputMode;
    const requestThreadId = getCurrentId();

    addMsg("user", text);
    appendMessageToThread(requestThreadId, "user", text);
    message.value = "";
    setCurrentDraftInputMode("keyboard");

    const assistantNode = createMessageNode("assistant", "…");
    let assistantText = "";

    applyAssistantStreamingUiEvent(assistantNode, STREAMING_UI_EVENT_REQUEST_STARTED);
    chatRequestInFlight = true;
    syncDictationUi();
    try {
      const response = await sendToServer(text, (chunk) => {
        if (!chunk) return;
        assistantText += chunk;
        assistantNode.bubble.textContent = assistantText;
        if (hasVisibleAssistantContent(assistantText)) {
          applyAssistantStreamingUiEvent(assistantNode, STREAMING_UI_EVENT_VISIBLE_CONTENT);
        }
        scrollToBottom(false);
      }, requestThreadId, inputMode, {
        onStreamEvent(event) {
          applyAssistantStreamingUiEvent(assistantNode, event);
        },
      });
      const reply = response && typeof response.text === "string" ? response.text : "";
      const replyTerminal = response && response.terminal ? response.terminal : null;
      const hasReplyUpdatedAt = hasTerminalUpdatedAt(replyTerminal);

      assistantText = reply || assistantText;
      assistantNode.bubble.textContent = assistantText || "(vide)";
      if (hasReplyUpdatedAt) {
        setMessageNodeTimestamp(assistantNode, "assistant", replyTerminal.updated_at);
      }
      appendMessageToThread(
        requestThreadId,
        "assistant",
        assistantNode.bubble.textContent,
        hasReplyUpdatedAt ? replyTerminal.updated_at : null,
      );
      applyConversationTerminalMeta(requestThreadId, replyTerminal);
      if (!hasReplyUpdatedAt && requestThreadId) {
        await hydrateThreadMessages(requestThreadId, { force: true });
      }
      await refreshThreadsFromServer({ keepSelection: true });
      renderThreads();
      if (!hasReplyUpdatedAt && requestThreadId && getCurrentId() === requestThreadId) {
        await loadThread(requestThreadId);
      } else {
        scrollToBottom(true);
      }
    } catch (err) {
      const errorMeta = getObservableStreamErrorMeta(err);
      const errorTerminal = err && typeof err === "object" ? err.terminal || null : null;
      if (applyConversationTerminalMeta(requestThreadId, errorTerminal)) {
        renderThreads();
      }
      if (requestThreadId && errorTerminal && errorTerminal.event === "error") {
        appendMessageToThread(
          requestThreadId,
          "assistant",
          "",
          errorTerminal.updated_at || null,
          buildInterruptedAssistantTurnMeta(errorTerminal.error_code || "stream_protocol_error"),
        );
        renderThreads();
      }
      applyAssistantStreamingFailure(assistantNode, errorMeta);
      assistantNode.bubble.textContent = extractErrorMessage(err);
      console.error(err);
    } finally {
      chatRequestInFlight = false;
      syncDictationUi();
    }
  });

  // ---- Endpoint réseau
  async function sendToServer(userText, onChunk, threadId, inputMode = "keyboard", options = {}){
    const thread = threadId ? getThreadById(threadId) : null;
    const emitStreamEvent = (event) => {
      if (typeof options?.onStreamEvent === "function") {
        options.onStreamEvent(event);
      }
    };
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: userText,
        conversation_id: thread ? thread.conversation_id : null,
        stream: true,
        web_search: webSearchEnabled,
        input_mode: inputMode === "voice" ? "voice" : "keyboard",
      })
    });

    if (!res.ok) {
      let errText = "";
      try {
        errText = await res.text();
      } catch {}
      throw new Error(errText || "HTTP " + res.status);
    }

    const contentType = res.headers.get("content-type") || "";
    const convId = res.headers.get("X-Conversation-Id");
    const createdAt = res.headers.get("X-Conversation-Created-At");
    const updatedAt = res.headers.get("X-Conversation-Updated-At");
    emitStreamEvent(STREAMING_UI_EVENT_RESPONSE_OPENED);
    if (contentType.includes("application/json")) {
      if (threadId && (convId || createdAt || updatedAt)) {
        setThreadMeta(threadId, {
          conversation_id: convId || (thread ? thread.conversation_id : null),
          created_at: createdAt || (thread ? thread.created_at : null),
          updated_at: updatedAt || (thread ? thread.updated_at : null),
        });
        renderThreads();
      }
      const data = await res.json();
      if (!data.ok) {
        throw new Error(data.error || "Réponse serveur invalide");
      }
      const text = data.text || "";
      if (threadId && data.conversation_id) {
        setThreadMeta(threadId, {
          conversation_id: data.conversation_id,
          created_at: data.created_at || (thread ? thread.created_at : null),
          updated_at: data.updated_at || (thread ? thread.updated_at : null),
        });
        renderThreads();
      }
      if (typeof onChunk === "function" && text) onChunk(text);
      emitStreamEvent(STREAMING_UI_EVENT_TERMINAL_DONE);
      const terminal = { event: "done" };
      const terminalUpdatedAt = String(data.updated_at || updatedAt || "").trim();
      if (terminalUpdatedAt) {
        terminal.updated_at = terminalUpdatedAt;
      }
      return { text, terminal };
    }

    if (threadId && (convId || createdAt)) {
      setThreadMeta(threadId, {
        conversation_id: convId || (thread ? thread.conversation_id : null),
        created_at: createdAt || (thread ? thread.created_at : null),
      });
      renderThreads();
    }

    if (!res.body) {
      emitStreamEvent(STREAMING_UI_EVENT_TERMINAL_DONE);
      return { text: "", terminal: { event: "done" } };
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8", { fatal: false });
    let finalText = "";
    const parser = createStreamControlParser({
      onContent(chunk) {
        finalText += chunk;
        if (typeof onChunk === "function") onChunk(chunk);
      },
    });

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true })
        .replace(/\r/g, "");
      if (!chunk) continue;
      parser.push(chunk);
    }

    const tail = decoder.decode();
    if (tail) {
      const cleanTail = tail.replace(/\r/g, "");
      parser.push(cleanTail);
    }

    const terminal = parser.finish();
    if (!terminal || terminal.event !== "done") {
      emitStreamEvent(STREAMING_UI_EVENT_TERMINAL_ERROR);
      throw createStreamTerminalError(terminal);
    }

    emitStreamEvent(STREAMING_UI_EVENT_TERMINAL_DONE);
    return { text: finalText, terminal };
  }

  // ---- Init
  const bootstrapApp = async () => {
    const loaded = await refreshThreadsFromServer({ keepSelection: false });
    renderThreads();

    if (!loaded) {
      log.innerHTML = '';
      await setHero();
      return;
    }

    const current = getCurrentId();
    if (current) {
      await loadThread(current);
    } else {
      await newThread();
    }
  };

  void bootstrapApp();
})();
