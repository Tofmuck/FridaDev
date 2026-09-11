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
  const chatTheme = window.FridaChatTheme;
  if (!chatTheme) {
    throw new Error("FridaChatTheme module missing");
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
  const dialogueMode = window.FridaDialogueMode;
  if (!dialogueMode) {
    throw new Error("FridaDialogueMode module missing");
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
  const btnDialogueMode = $("#btnDialogueMode");
  // Capture served HTML authority once. Inspector edits cannot grant product access.
  const dialogueProductAuthorized = Boolean(btnDialogueMode && !btnDialogueMode.hasAttribute('disabled'));
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
  const btnSidebarClose = $("#btnSidebarClose");
  const btnMobileTools = $("#btnMobileTools");
  const currentConversationTitle = document.querySelector('.topbar .title');
  const dialogueModeScreen = $("#dialogueModeScreen");
  const dialogueModeStatus = $("#dialogueModeStatus");
  const dialogueModePause = $("#dialogueModePause");
  const dialogueModePauseLabel = $("#dialogueModePauseLabel");
  const dialogueModeEnd = $("#dialogueModeEnd");
  const dialogueModeClose = $("#dialogueModeClose");
  const dialogueModeNavigation = $("#dialogueModeNavigation");
  let composerHeightObserver = null;
  const syncComposerHeight = () => {
    if (!ask) return;
    const height = Math.ceil(ask.getBoundingClientRect().height || 76);
    document.documentElement.style.setProperty('--ask-h', `${Math.max(76, height)}px`);
  };
  if (ask) {
    syncComposerHeight();
    if (typeof ResizeObserver === 'function') {
      composerHeightObserver = new ResizeObserver(syncComposerHeight);
      composerHeightObserver.observe(ask);
    } else {
      window.addEventListener('resize', syncComposerHeight);
    }
  }
  const syncCurrentConversationTitle = (thread) => {
    if (!currentConversationTitle) return;
    currentConversationTitle.textContent = String(thread?.title || 'Nouvelle conversation');
  };
  const themeController = chatTheme.createThemeController({ document, storage: localStorage });
  const isPhoneLayout = () => themeController.isPhonePresentation();
  const syncSidebarAccessibility = () => {
    if (!sidebar) return;
    const isOpen = sidebar.classList.contains('open');
    sidebar.setAttribute('aria-hidden', isPhoneLayout() && !isOpen ? 'true' : 'false');
    if (btnMenu) btnMenu.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  };
  const openSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.add('open');
    sidebarBackdrop && sidebarBackdrop.classList.add('show');
    syncSidebarAccessibility();
  };
  const closeSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    sidebarBackdrop && sidebarBackdrop.classList.remove('show');
    syncSidebarAccessibility();
  };
  const dialogueD3TestAdapters = window.__FRIDA_DIALOGUE_D3_TEST_ADAPTERS__ || null;
  let dialogueD3Load = null;
  let dialogueD3Session = 0;
  // Loaded only after an authorized explicit session opening.
  const loadDialogueD3 = () => {
    if (!dialogueD3Load) dialogueD3Load = (async () => {
      for (const source of [
        'vendor/dialogue-vad/ort.wasm.min.js',
        'vendor/dialogue-vad/bundle.min.js',
        'dialogue/dialogue_vad_runtime.js',
        'dialogue/dialogue_vad_recorder.js',
      ]) {
        await new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = new URL(source, document.baseURI).href;
          script.onload = () => { script.onload = null; script.onerror = null; resolve(); };
          script.onerror = () => {
            script.onload = null;
            script.onerror = null;
            script.remove();
            reject(new Error('dialogue_assets_unavailable'));
          };
          document.head.appendChild(script);
        });
      }
      return window.FridaDialogueVadRuntime.createDialogueVadRuntime({
        vadRuntime: window.vad,
        assetBaseUrl: new URL('vendor/dialogue-vad/', document.baseURI).href,
      });
    })();
    return dialogueD3Load;
  };
  const dialogueD3Events = [];
  let dialogueD3Recorder = null;
  let dialogueD3Active = false;
  let dialogueD3TerminalError = false;
  let dialogueD3Operation = Promise.resolve();
  let dialogueModeController = null;
  let dialogueD4Controller = null;
  let dialogueD4Operation = Promise.resolve();

  const handleDialogueD3UnexpectedError = () => {
    dialogueD3TerminalError = true;
    const closing = dialogueD4Controller?.close();
    const stopping = dialogueD3Recorder?.stop();
    if (dialogueModeController && dialogueModeController.isActive()) {
      dialogueModeController.setState('error');
    }
    return Promise.all([closing, stopping]);
  };

  const trackDialogueD3Operation = (operation) => {
    const owner = dialogueD3Session;
    dialogueD3Operation = Promise.resolve(operation).catch(() => {
      if (dialogueD3Active && owner === dialogueD3Session) return handleDialogueD3UnexpectedError();
    });
    return dialogueD3Operation;
  };

  const queueDialogueD3Operation = (operation) => {
    const nextOperation = dialogueD3Operation
      .catch(() => {})
      .then(operation);
    return trackDialogueD3Operation(nextOperation);
  };

  const projectDialogueD3Event = (event, d4Event) => {
    const observableEvent = event.type === 'blob'
      ? {
        type: event.type,
        mimeType: event.mimeType,
        durationMs: event.durationMs,
        sizeBytes: event.sizeBytes,
      }
      : { ...event };
    dialogueD3Events.push(Object.freeze(observableEvent));
    if (dialogueD3Events.length > 32) dialogueD3Events.shift();
    if (!dialogueD3Active || !dialogueModeController) return;
    if (d4Event) {
      const operation = d4Event(event);
      if (event.type === 'blob' || event.type === 'error') {
        dialogueD4Operation = Promise.all([dialogueD4Operation, operation]).then(() => {});
      }
      return;
    }
    if (event.type === 'speech-start') {
      dialogueModeController.setState('user_speaking');
    } else if (event.type === 'speech-end' || event.type === 'blob') {
      dialogueModeController.setState('listening');
    } else if (event.type === 'error') {
      dialogueD3TerminalError = true;
      dialogueModeController.setState('error');
    }
  };

  const createDialogueD3Recorder = (runtime, d4Event, ttsMediaElement) => {
    const adapters = dialogueD3TestAdapters || {};
    return window.FridaDialogueVadRecorder.createDialogueVadRecorder({
      mediaDevices: adapters.mediaDevices,
      BlobCtor: adapters.BlobCtor,
      documentObj: document,
      ttsMediaElement: ttsMediaElement || adapters.ttsMediaElement,
      vadFactory: adapters.vadFactory || runtime.vadFactory,
      vadOptions: runtime.vadOptions,
      onEvent: (event) => projectDialogueD3Event(event, d4Event),
    });
  };

  const stopDialogueD3Capture = () => {
    if (!dialogueD3Active) return dialogueD3Operation;
    dialogueD3Active = false;
    dialogueD3Session += 1;
    const d4Closing = dialogueD4Controller?.close();
    dialogueD4Controller = null;
    const recorderToStop = dialogueD3Recorder;
    const pendingOperation = dialogueD3Operation;
    const immediateStop = recorderToStop ? recorderToStop.stop() : Promise.resolve();
    return trackDialogueD3Operation(Promise.all([
      pendingOperation.catch(() => {}),
      immediateStop,
      d4Closing,
    ]).then(() => {
      if (dialogueD3Recorder === recorderToStop) dialogueD3Recorder = null;
    }));
  };
  dialogueModeController = dialogueMode.createDialogueModeController({
    rootEl: document.documentElement,
    screenEl: dialogueModeScreen,
    backgroundEl: document.querySelector('.main'),
    statusEl: dialogueModeStatus,
    entryButtonEl: null,
    pauseButtonEl: dialogueModePause,
    pauseLabelEl: dialogueModePauseLabel,
    endButtonEl: dialogueModeEnd,
    closeButtonEl: dialogueModeClose,
    navigationButtonEl: dialogueModeNavigation,
    onOpenNavigation: openSidebar,
    onExit: stopDialogueD3Capture,
  });
  window.FridaDialogueModeController = dialogueModeController;
  const openDialogueSession = (mode) => {
    if (!['d3_local', 'full', 'local_preflight'].includes(mode)) throw new Error('dialogue_session_mode_invalid');
    if (dialogueD3Active) return dialogueD3Operation;
    dialogueD3Active = true;
    dialogueD3TerminalError = false;
    dialogueD3Events.length = 0;
    const session = ++dialogueD3Session;
    dialogueModeController.enter();
    let d4Event = null;
    let sessionController = null;
    let ttsMediaElement = null;
    if (mode !== 'd3_local') {
      // Create and prepare the owned element in the initial gesture, before any await.
      try {
        ttsMediaElement = dialogueD3TestAdapters?.createTtsMediaElement
          ? dialogueD3TestAdapters.createTtsMediaElement() : new Audio();
        sessionController = window.FridaDialogueSessionController.createDialogueSessionController({
          mode,
          ttsMediaElement,
          capture: {
            pause: () => dialogueD3Recorder?.pause(),
            stop: () => dialogueD3Recorder?.stop(),
            resume: async (isCurrent) => {
              await dialogueD3Operation;
              if (!isCurrent()) return;
              await dialogueD3Recorder?.arm();
              if (!isCurrent()) return;
              await dialogueD3Recorder?.resume();
            },
          },
          getConversationId: () => getCurrentId(),
          isChatBusy: () => chatRequestInFlight,
          setState: (state) => dialogueModeController.setState(state),
          // Local preflight receives no transport capabilities at all.
          ...(mode === 'full' ? {
            audioClient: window.FridaDialogueAudioClient.createDialogueAudioClient(),
            submitCanonicalChatMessage: (text, inputMode) => submitCanonicalChatMessage(text, inputMode),
          } : {}),
        });
        dialogueD4Controller = sessionController;
        d4Event = sessionController.start();
      } catch (_error) {
        return handleDialogueD3UnexpectedError();
      }
    }
    return queueDialogueD3Operation(async () => {
      if (sessionController && !await sessionController.whenReady()) return;
      if (!dialogueD3Active || session !== dialogueD3Session) return;
      const runtime = await loadDialogueD3();
      if (!dialogueD3Active || session !== dialogueD3Session) return;
      const recorderToArm = createDialogueD3Recorder(runtime, d4Event, ttsMediaElement);
      dialogueD3Recorder = recorderToArm;
      if (dialogueModeController.getState() === 'listening') await recorderToArm.arm();
    });
  };
  btnDialogueMode?.addEventListener('click', (event) => {
    if (!event.isTrusted || btnDialogueMode.disabled) return;
    // D6 verification only: one-shot DOM preparation, removed explicitly in D6.4.
    const marker = btnDialogueMode.getAttribute('data-dialogue-preflight');
    if (marker !== null) {
      btnDialogueMode.removeAttribute('data-dialogue-preflight');
      btnDialogueMode.disabled = true;
      if (marker === 'local_preflight') void openDialogueSession('local_preflight');
      else if (marker === 'full_canary') void openDialogueSession('full');
      return;
    }
    if (dialogueProductAuthorized) void openDialogueSession('full');
  });
  window.addEventListener('pagehide', () => dialogueModeController.exit());
  if (dialogueD3TestAdapters) {
    window.FridaDialogueD3Harness = Object.freeze({
      openAndArm({ routeToChat = false } = {}) {
        return openDialogueSession(routeToChat ? 'full' : 'd3_local');
      },
      events: () => [...dialogueD3Events],
      whenSettled: () => Promise.all([dialogueD3Operation, dialogueD4Operation]),
    });
  }
  if (dialogueModePause) {
    dialogueModePause.addEventListener('click', () => {
      if (!dialogueD3Active) return;
      if (dialogueD3TerminalError) {
        dialogueModeController.setState('error');
        return;
      }
      if (dialogueD4Controller) {
        if (dialogueModeController.getState() === 'paused') {
          dialogueD4Operation = Promise.all([dialogueD4Operation, dialogueD4Controller.pause()]).then(() => {});
        } else {
          // The visual toggle precedes this listener. Stay paused until capture really resumes.
          dialogueModeController.setState('paused');
          dialogueD4Operation = Promise.all([dialogueD4Operation, dialogueD4Controller.resume()]).then(() => {});
        }
        return;
      }
      if (dialogueModeController.getState() === 'paused') {
        // Invalidate an in-flight arm immediately, even while permission is pending.
        const pending = dialogueD3Operation;
        const pausing = dialogueD3Recorder?.pause();
        void trackDialogueD3Operation(Promise.all([pending, pausing]));
      } else {
        void queueDialogueD3Operation(async () => {
          if (!dialogueD3Active || !dialogueD3Recorder) return;
          await dialogueD3Recorder.arm();
          await dialogueD3Recorder.resume();
        });
      }
    });
  }
  const setMobileToolsExpanded = (expanded) => {
    const nextExpanded = Boolean(expanded && isPhoneLayout());
    if (ask) ask.classList.toggle('mobile-tools-expanded', nextExpanded);
    if (btnMobileTools) {
      btnMobileTools.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false');
      btnMobileTools.setAttribute('title', nextExpanded ? 'Masquer les autres outils' : 'Afficher les autres outils');
      btnMobileTools.setAttribute('aria-label', nextExpanded ? 'Masquer les autres outils' : 'Afficher les autres outils');
    }
  };
  syncSidebarAccessibility();
  if (btnMenu)         btnMenu.addEventListener('click', openSidebar);
  if (btnSidebarClose) btnSidebarClose.addEventListener('click', closeSidebar);
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
  if (btnMobileTools) {
    btnMobileTools.addEventListener('click', () => {
      setMobileToolsExpanded(btnMobileTools.getAttribute('aria-expanded') !== 'true');
    });
  }
  [btnAdobeMode, btnBiblioMode, btnNotesMode, btnAgendaMode].forEach((button) => {
    if (button) button.addEventListener('click', () => setMobileToolsExpanded(false));
  });
  const handlePresentationContextChange = (event) => {
    if (!event || event.type !== chatTheme.PRESENTATION_CONTEXT_EVENT) {
      themeController.syncPresentation();
    }
    if (!isPhoneLayout()) {
      dialogueModeController.exit();
      closeSidebar();
      setMobileToolsExpanded(false);
    } else {
      syncSidebarAccessibility();
    }
    syncComposerHeight();
  };
  window.addEventListener('resize', handlePresentationContextChange);
  window.addEventListener('pageshow', handlePresentationContextChange);
  document.addEventListener(chatTheme.PRESENTATION_CONTEXT_EVENT, handlePresentationContextChange);
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    dialogueModeController.exit();
    closeSidebar();
    setMobileToolsExpanded(false);
  });

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
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  };

  const resolveDisplayName = (role) => {
    if (role === "assistant") return "Frida";
    if (role === "user" || role === "olive") return "Vous";
    return role;
  };

  const buildBylineText = (role, timestamp = null) => {
    const hourStr = fmtHour(timestamp);
    return hourStr || resolveDisplayName(role);
  };

  const setMessageNodeTimestamp = (messageNode, role, timestamp = null) => {
    if (!messageNode || !messageNode.byline) return;
    messageNode.byline.textContent = buildBylineText(role, timestamp);
  };

  const hasTerminalUpdatedAt = (terminal) => Boolean(String(terminal && terminal.updated_at || "").trim());

  const createMessageNode = (role, text = "", timestamp = null) => {
    const wrapper = document.createElement("div");
    wrapper.className = `msg-wrapper ${role === "user" ? "me" : "assistant"}`;

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

    if (role === "assistant") {
      const identity = document.createElement("div");
      identity.className = "assistant-identity";
      identity.setAttribute("aria-hidden", "true");
      const avatar = document.createElement("span");
      avatar.className = "assistant-avatar-shell";
      const image = document.createElement("img");
      image.src = "./fridalogo.png";
      image.alt = "";
      image.width = 22;
      image.height = 22;
      const name = document.createElement("span");
      name.className = "assistant-name";
      name.textContent = "Frida";
      avatar.appendChild(image);
      identity.appendChild(avatar);
      identity.appendChild(name);
      wrapper.appendChild(identity);
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
    onCurrentThreadChange: (thread) => {
      syncCurrentConversationTitle(thread);
      dialogueD4Controller?.conversationChanged();
    },
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
    return submitCanonicalChatMessage(message.value || "", currentDraftInputMode);
  });

  async function submitCanonicalChatMessage(text, inputMode) {
    if (chatRequestInFlight) return { ok: false, reason: "busy" };
    text = typeof text === "string" ? text.trim() : "";
    if (!text) return { ok: false, reason: "empty" };
    const isDialogue = inputMode === "dialogue";
    inputMode = isDialogue || inputMode === "voice" ? "voice" : "keyboard";
    const requestThreadId = getCurrentId();

    addMsg("user", text);
    appendMessageToThread(requestThreadId, "user", text);
    if (!isDialogue) {
      message.value = "";
      setCurrentDraftInputMode("keyboard");
    }

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
      return { ok: true, text: reply };
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
      return { ok: false, reason: "chat_failed" };
    } finally {
      chatRequestInFlight = false;
      syncDictationUi();
      void refreshActiveDocuments();
    }
  }

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
