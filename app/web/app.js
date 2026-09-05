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
  const activeConversationDocuments = window.FridaActiveConversationDocuments;
  if (!activeConversationDocuments) {
    throw new Error("FridaActiveConversationDocuments module missing");
  }
  const chatCopyExport = window.FridaChatCopyExport;
  if (!chatCopyExport) {
    throw new Error("FridaChatCopyExport module missing");
  }
  const mainReasoningControl = window.FridaMainReasoningControl;
  if (!mainReasoningControl) {
    throw new Error("FridaMainReasoningControl module missing");
  }
  const imageGeneration = window.FridaImageGeneration;
  if (!imageGeneration) {
    throw new Error("FridaImageGeneration module missing");
  }
  const adobeMode = window.FridaAdobeMode;
  if (!adobeMode) {
    throw new Error("FridaAdobeMode module missing");
  }
  const biblioMode = window.FridaBiblioMode;
  if (!biblioMode) {
    throw new Error("FridaBiblioMode module missing");
  }
  const agendaMode = window.FridaAgendaMode;
  if (!agendaMode) {
    throw new Error("FridaAgendaMode module missing");
  }
  const notesMode = window.FridaNotesMode;
  if (!notesMode) {
    throw new Error("FridaNotesMode module missing");
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
    resolveStreamedAssistantText,
  } = chatStreaming;
  const $ = (sel) => document.querySelector(sel);

  // ---- DOM refs
  const hero = $("#hero");
  const log = $("#log");
  const chatEl = document.querySelector('.chat');
  const ask = $("#ask");
  const message = $("#message");
  const btnMic = $("#btnMic");
  const btnActiveDocument = $("#btnActiveDocument");
  const btnImageGeneration = $("#btnImageGeneration");
  const btnAdobeMode = $("#btnAdobeMode");
  const btnBiblioMode = $("#btnBiblioMode");
  const btnAgendaMode = $("#btnAgendaMode");
  const btnNotesMode = $("#btnNotesMode");
  const adobeProductChoices = $("#adobeProductChoices");
  const btnExportConversation = $("#btnExportConversation");
  const activeDocumentFileInput = $("#activeDocumentFileInput");
  const activeDocumentsBar = $("#activeDocumentsBar");
  const activeDocumentsList = $("#activeDocumentsList");
  const activeDocumentsStatus = $("#activeDocumentsStatus");
  const btnWebSearch = $("#btnWebSearch");
  const dictationStatus = $("#dictationStatus");
  const imageGenerationPanel = $("#imageGenerationPanel");
  const imageGenerationClose = $("#imageGenerationClose");
  const imageGenerationForm = $("#imageGenerationForm");
  const imageGenerationPrompt = $("#imageGenerationPrompt");
  const imageGenerationModel = $("#imageGenerationModel");
  const imageGenerationAspectRatio = $("#imageGenerationAspectRatio");
  const imageGenerationSize = $("#imageGenerationSize");
  const imageGenerationPricing = $("#imageGenerationPricing");
  const imageGenerationStatus = $("#imageGenerationStatus");
  const imageGenerationSubmit = $("#imageGenerationSubmit");
  const imageGenerationEmpty = $("#imageGenerationEmpty");
  const imageGenerationResult = $("#imageGenerationResult");
  const imageGenerationPreview = $("#imageGenerationPreview");
  const imageGenerationMeta = $("#imageGenerationMeta");
  const imageGenerationDownload = $("#imageGenerationDownload");
  const mainReasoningLevel = $("#mainReasoningLevel");
  const mainReasoningStatus = $("#mainReasoningStatus");
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
  let adobeModeController = null;
  let biblioModeController = null;
  let agendaModeController = null;
  let notesModeController = null;
  const isAdobeModeActive = () => Boolean(adobeModeController && adobeModeController.isActive());
  const updateWebSearchBtn = () => {
    if (!btnWebSearch) return;
    const adobeActive = isAdobeModeActive();
    btnWebSearch.disabled = adobeActive;
    btnWebSearch.classList.toggle("active", webSearchEnabled);
    btnWebSearch.title = adobeActive
      ? "Recherche web indisponible en mode Adobe"
      : (webSearchEnabled ? "Recherche web : activée" : "Recherche web : désactivée");
    btnWebSearch.setAttribute("aria-pressed", webSearchEnabled && !adobeActive ? "true" : "false");
  };
  if (btnWebSearch) {
    updateWebSearchBtn();
    btnWebSearch.addEventListener("click", () => {
      if (isAdobeModeActive()) return;
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

  const isChatNearBottom = (threshold = 96) => {
    if (!chatEl) return true;
    const distance = chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight;
    return distance <= threshold;
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
    const metaRow = document.createElement("div");
    metaRow.className = "msg-meta-row";
    metaRow.appendChild(by);
    metaRow.appendChild(chatCopyExport.createCopyButton({
      getText: () => bubble.innerText || bubble.textContent || "",
    }));
    wrapper.appendChild(metaRow);
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

  const setAssistantLoader = (assistantNode, enabled) => {
    if (!assistantNode || !assistantNode.bubble || !assistantNode.bubble.classList) return;
    assistantNode.bubble.classList.toggle("assistant-loader", Boolean(enabled));
    if (enabled) {
      assistantNode.bubble.setAttribute("aria-label", "Réponse en préparation");
    } else {
      assistantNode.bubble.removeAttribute("aria-label");
    }
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

  notesModeController = notesMode.createNotesModeController({
    buttonEl: btnNotesMode,
  });

  const threadsLifecycle = chatThreadsSidebar.createChatThreadsSidebar({
    threadsUl,
    logEl: log,
    fetchFn: fetch,
    setHero,
    closeSidebar,
    renderConversationMessage,
    scrollToBottom,
    notesModeController,
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

  const updateExportConversationButton = () => {
    if (!btnExportConversation) return;
    const hasThread = Boolean(getCurrentId());
    btnExportConversation.disabled = !hasThread;
    btnExportConversation.title = hasThread
      ? "Exporter la conversation en Markdown"
      : "Aucune conversation à exporter";
  };

  const exportCurrentConversation = async () => {
    const currentId = getCurrentId();
    if (!currentId || !btnExportConversation) return;
    btnExportConversation.disabled = true;
    try {
      const messages = await hydrateThreadMessages(currentId, { force: true });
      const thread = getThreadById(currentId);
      const markdown = chatCopyExport.buildConversationMarkdown({
        messages,
        exportedAt: new Date(),
      });
      const filename = chatCopyExport.buildMarkdownFilename(thread?.updated_at || new Date());
      const downloaded = chatCopyExport.downloadMarkdownFile({ markdown, filename });
      if (!downloaded) {
        throw new Error("download_unavailable");
      }
      btnExportConversation.disabled = false;
      btnExportConversation.title = "Conversation exportée";
      window.setTimeout(updateExportConversationButton, 1300);
    } catch (err) {
      console.error(err);
      btnExportConversation.disabled = false;
      btnExportConversation.title = "Export indisponible";
      window.setTimeout(updateExportConversationButton, 1800);
    }
  };

  if (btnExportConversation) {
    btnExportConversation.addEventListener("click", () => {
      void exportCurrentConversation();
    });
  }

  const activeDocumentsController = activeConversationDocuments.createActiveDocumentController({
    chatEl,
    composerEl: ask,
    barEl: activeDocumentsBar,
    listEl: activeDocumentsList,
    statusEl: activeDocumentsStatus,
    buttonEl: btnActiveDocument,
    inputEl: activeDocumentFileInput,
    fetchFn: fetch,
    getConversationId: () => {
      const thread = getThreadById(getCurrentId());
      return thread ? thread.conversation_id : getCurrentId();
    },
    ensureConversation: async () => {
      if (!getCurrentId()) {
        await newThread();
      }
    },
    consoleObj: console,
  });

  const refreshActiveDocuments = (options = {}) => activeDocumentsController.refresh(options);

  imageGeneration.createImageGenerationController({
    buttonEl: btnImageGeneration,
    panelEl: imageGenerationPanel,
    closeButtonEl: imageGenerationClose,
    formEl: imageGenerationForm,
    promptEl: imageGenerationPrompt,
    modelSelectEl: imageGenerationModel,
    aspectRatioSelectEl: imageGenerationAspectRatio,
    imageSizeSelectEl: imageGenerationSize,
    pricingEl: imageGenerationPricing,
    statusEl: imageGenerationStatus,
    submitButtonEl: imageGenerationSubmit,
    emptyEl: imageGenerationEmpty,
    previewEl: imageGenerationPreview,
    resultEl: imageGenerationResult,
    metaEl: imageGenerationMeta,
    downloadButtonEl: imageGenerationDownload,
    fetchFn: fetch,
    consoleObj: console,
  });

  mainReasoningControl.createMainReasoningControl({
    selectEl: mainReasoningLevel,
    statusEl: mainReasoningStatus,
    fetchFn: fetch,
    consoleObj: console,
  });

  adobeModeController = adobeMode.createAdobeModeController({
    buttonEl: btnAdobeMode,
    choicesEl: adobeProductChoices,
    composerEl: ask,
    onActiveChange(active) {
      if (active && webSearchEnabled) {
        webSearchEnabled = false;
        localStorage.setItem("frida.webSearch", "0");
      }
      updateWebSearchBtn();
    },
  });
  biblioModeController = biblioMode.createBiblioModeController({
    buttonEl: btnBiblioMode,
  });
  agendaModeController = agendaMode.createAgendaModeController({
    buttonEl: btnAgendaMode,
  });
  updateWebSearchBtn();

  // ---- Nouveau chat
  newChatBtn.addEventListener("click", async () => {
    await newThread();
    await refreshActiveDocuments();
    updateExportConversationButton();
  });

  if (threadsUl) {
    threadsUl.addEventListener("click", () => {
      window.setTimeout(() => {
        void refreshActiveDocuments();
        updateExportConversationButton();
      }, 0);
    });
  }

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
    if (chatRequestInFlight) return;
    const text = (message.value || "").trim();
    if (!text) return;
    const inputMode = currentDraftInputMode;
    const requestThreadId = getCurrentId();

    addMsg("user", text);
    appendMessageToThread(requestThreadId, "user", text);
    message.value = "";
    setCurrentDraftInputMode("keyboard");

    const assistantNode = createMessageNode("assistant", "");
    setAssistantLoader(assistantNode, true);
    let assistantText = "";

    applyAssistantStreamingUiEvent(assistantNode, STREAMING_UI_EVENT_REQUEST_STARTED);
    chatRequestInFlight = true;
    syncDictationUi();
    try {
      const response = await sendToServer(text, (chunk) => {
        if (!chunk) return;
        const shouldStickToBottom = isChatNearBottom();
        assistantText += chunk;
        assistantNode.bubble.textContent = assistantText;
        if (hasVisibleAssistantContent(assistantText)) {
          setAssistantLoader(assistantNode, false);
          applyAssistantStreamingUiEvent(assistantNode, STREAMING_UI_EVENT_VISIBLE_CONTENT);
        }
        if (shouldStickToBottom) {
          scrollToBottom(false);
        }
      }, requestThreadId, inputMode, {
        onStreamEvent(event) {
          applyAssistantStreamingUiEvent(assistantNode, event);
        },
      });
      const reply = response && typeof response.text === "string" ? response.text : "";
      const replyTerminal = response && response.terminal ? response.terminal : null;
      const hasReplyUpdatedAt = hasTerminalUpdatedAt(replyTerminal);
      const shouldStickToBottom = isChatNearBottom();

      assistantText = reply;
      setAssistantLoader(assistantNode, false);
      assistantNode.bubble.textContent = assistantText || "(vide)";
      if (hasReplyUpdatedAt) {
        setMessageNodeTimestamp(assistantNode, "assistant", replyTerminal.updated_at);
      }
      if (assistantText) {
        appendMessageToThread(
          requestThreadId,
          "assistant",
          assistantText,
          hasReplyUpdatedAt ? replyTerminal.updated_at : null,
        );
      }
      applyConversationTerminalMeta(requestThreadId, replyTerminal);
      if (!hasReplyUpdatedAt && requestThreadId) {
        await hydrateThreadMessages(requestThreadId, { force: true });
      }
      await refreshThreadsFromServer({ keepSelection: true });
      renderThreads();
      updateExportConversationButton();
      if (!hasReplyUpdatedAt && requestThreadId && getCurrentId() === requestThreadId) {
        await loadThread(requestThreadId);
      } else if (shouldStickToBottom) {
        scrollToBottom(true);
      }
    } catch (err) {
      const errorMeta = getObservableStreamErrorMeta(err);
      const errorTerminal = err && typeof err === "object" ? err.terminal || null : null;
      let rehydratedAfterUnpersistedTerminalError = false;
      if (applyConversationTerminalMeta(requestThreadId, errorTerminal)) {
        renderThreads();
        updateExportConversationButton();
      }
      if (requestThreadId && errorTerminal && errorTerminal.event === "error" && hasTerminalUpdatedAt(errorTerminal)) {
        appendMessageToThread(
          requestThreadId,
          "assistant",
          "",
          errorTerminal.updated_at || null,
          buildInterruptedAssistantTurnMeta(errorTerminal.error_code || "stream_protocol_error"),
        );
        renderThreads();
      } else if (requestThreadId && errorTerminal && errorTerminal.event === "error") {
        try {
          await hydrateThreadMessages(requestThreadId, { force: true });
          await refreshThreadsFromServer({ keepSelection: true });
          renderThreads();
          updateExportConversationButton();
          if (getCurrentId() === requestThreadId) {
            await loadThread(requestThreadId);
            rehydratedAfterUnpersistedTerminalError = true;
          }
        } catch (hydrateErr) {
          console.error(hydrateErr);
        }
      }
      const visibleAssistantNode = rehydratedAfterUnpersistedTerminalError && !assistantNode.wrapper.isConnected
        ? createMessageNode("assistant", "")
        : assistantNode;
      setAssistantLoader(visibleAssistantNode, false);
      applyAssistantStreamingFailure(visibleAssistantNode, errorMeta);
      visibleAssistantNode.bubble.textContent = extractErrorMessage(err);
      console.error(err);
    } finally {
      chatRequestInFlight = false;
      syncDictationUi();
      void refreshActiveDocuments();
    }
  });

  // ---- Endpoint réseau
  async function sendToServer(userText, onChunk, threadId, inputMode = "keyboard", options = {}){
    const thread = threadId ? getThreadById(threadId) : null;
    const adobePayload = adobeModeController ? adobeModeController.getPayload() : {};
    const biblioPayload = biblioModeController ? biblioModeController.getPayload() : { biblio_enabled: false };
    const agendaPayload = agendaModeController ? agendaModeController.getPayload() : { agenda_enabled: false };
    const notesPayload = notesModeController
      ? notesModeController.getPayload({ workspaceFolderId: thread ? thread.workspace_folder_id : "" })
      : { workspace_notes_mode: false };
    const adobeActive = Boolean(adobePayload.specialization_profile);
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
        web_search: adobeActive ? false : webSearchEnabled,
        input_mode: inputMode === "voice" ? "voice" : "keyboard",
        ...biblioPayload,
        ...agendaPayload,
        ...notesPayload,
        ...adobePayload,
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
    return { text: resolveStreamedAssistantText(finalText, terminal), terminal };
  }

  // ---- Init
  const bootstrapApp = async () => {
    const loaded = await refreshThreadsFromServer({ keepSelection: false });
    renderThreads();
    updateExportConversationButton();

    if (!loaded) {
      log.innerHTML = '';
      await setHero();
      return;
    }

    const current = getCurrentId();
    if (current) {
      await loadThread(current);
      await refreshActiveDocuments();
      updateExportConversationButton();
    } else {
      await newThread();
      await refreshActiveDocuments();
      updateExportConversationButton();
    }
  };

  void bootstrapApp();
})();
