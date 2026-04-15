(function (root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.FridaWhisperDictation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  const STATES = {
    IDLE: "idle",
    RECORDING: "recording",
    TRANSCRIBING: "transcribing",
    ERROR: "error",
    BUSY: "busy",
  };

  const DEFAULT_ENDPOINT = "/api/chat/transcribe";
  const DEFAULT_MAX_RECORDING_MS = 60_000;
  const PREFERRED_MIME_TYPES = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];

  function text(value) {
    return String(value || "").trim();
  }

  function joinTranscriptToDraft(currentDraft, transcript) {
    const cleanTranscript = text(transcript);
    if (!cleanTranscript) return String(currentDraft || "");

    const existingDraft = String(currentDraft || "");
    if (!existingDraft.trim()) return cleanTranscript;
    if (/\n\s*$/.test(existingDraft)) {
      return `${existingDraft}${cleanTranscript}`;
    }
    return `${existingDraft.trimEnd()}\n\n${cleanTranscript}`;
  }

  function pickSupportedMimeType(MediaRecorderCtor) {
    if (!MediaRecorderCtor || typeof MediaRecorderCtor.isTypeSupported !== "function") {
      return "";
    }
    for (const mimeType of PREFERRED_MIME_TYPES) {
      if (MediaRecorderCtor.isTypeSupported(mimeType)) {
        return mimeType;
      }
    }
    return "";
  }

  function buildUploadFilename(mimeType) {
    const normalized = text(mimeType).toLowerCase();
    if (normalized.includes("webm")) return "dictation.webm";
    if (normalized.includes("mp4") || normalized.includes("mpeg")) return "dictation.mp4";
    if (normalized.includes("ogg")) return "dictation.ogg";
    if (normalized.includes("wav")) return "dictation.wav";
    return "dictation.bin";
  }

  function toggleClass(element, className, enabled) {
    if (!element || !element.classList || typeof element.classList.toggle !== "function") return;
    element.classList.toggle(className, Boolean(enabled));
  }

  function setDataState(element, value) {
    if (!element) return;
    if (element.dataset) {
      element.dataset.dictationState = value;
      return;
    }
    if (typeof element.setAttribute === "function") {
      element.setAttribute("data-dictation-state", value);
    }
  }

  function setStatusMessage(statusEl, message, isError) {
    if (!statusEl) return;
    statusEl.textContent = message || "";
    setDataState(statusEl, isError ? STATES.ERROR : STATES.IDLE);
    toggleClass(statusEl, "is-visible", Boolean(message));
    toggleClass(statusEl, "is-error", Boolean(isError));
  }

  function buildButtonLabel(state, supported) {
    if (!supported) return "Dictée vocale indisponible";
    if (state === STATES.RECORDING) return "Arrêter la dictée";
    if (state === STATES.TRANSCRIBING) return "Transcription en cours";
    if (state === STATES.BUSY) return "Réponse en cours, dictée indisponible";
    if (state === STATES.ERROR) return "Relancer la dictée";
    return "Lancer la dictée";
  }

  function browserErrorMessage(error) {
    const name = String(error && error.name ? error.name : "");
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      return "Accès au micro refusé";
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      return "Aucun micro disponible";
    }
    if (name === "NotReadableError" || name === "TrackStartError") {
      return "Micro indisponible";
    }
    return "Micro indisponible";
  }

  async function parseTranscriptionResponse(response) {
    let rawText = "";
    try {
      rawText = await response.text();
    } catch {
      rawText = "";
    }

    let payload = null;
    if (rawText) {
      try {
        payload = JSON.parse(rawText);
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      throw new Error((payload && payload.error) || text(rawText) || `HTTP ${response.status}`);
    }
    if (!payload || payload.ok === false) {
      throw new Error((payload && payload.error) || "Réponse transcription invalide");
    }

    const transcript = text(payload.text);
    if (!transcript) {
      throw new Error("Transcript vide");
    }
    return transcript;
  }

  async function transcribeBlob(options) {
    const audioBlob = options && options.audioBlob;
    if (!audioBlob || Number(audioBlob.size || 0) <= 0) {
      throw new Error("Aucun audio détecté");
    }

    const endpoint = text(options && options.endpoint) || DEFAULT_ENDPOINT;
    const fetchImpl = options && options.fetchImpl;
    const FormDataCtor = options && options.FormDataCtor;
    if (typeof fetchImpl !== "function" || typeof FormDataCtor !== "function") {
      throw new Error("Dictée vocale indisponible");
    }

    const mimeType = text((options && options.mimeType) || audioBlob.type);
    const formData = new FormDataCtor();
    formData.append("file", audioBlob, buildUploadFilename(mimeType));

    const response = await fetchImpl(endpoint, {
      method: "POST",
      body: formData,
    });
    return parseTranscriptionResponse(response);
  }

  function triggerInputEvent(element) {
    if (!element || typeof element.dispatchEvent !== "function" || typeof root.Event !== "function") {
      return;
    }
    try {
      element.dispatchEvent(new root.Event("input", { bubbles: true }));
    } catch {}
  }

  function createWhisperDictation(options) {
    const buttonEl = options && options.buttonEl;
    const statusEl = options && options.statusEl;
    const textareaEl = options && options.textareaEl;
    const fetchImpl = (options && options.fetchImpl) || (root.fetch ? root.fetch.bind(root) : null);
    const mediaDevices = (options && options.mediaDevices) || (root.navigator && root.navigator.mediaDevices);
    const MediaRecorderCtor = (options && options.MediaRecorderCtor) || root.MediaRecorder;
    const FormDataCtor = (options && options.FormDataCtor) || root.FormData;
    const BlobCtor = (options && options.BlobCtor) || root.Blob;
    const setTimeoutFn = (options && options.setTimeoutFn) || root.setTimeout;
    const clearTimeoutFn = (options && options.clearTimeoutFn) || root.clearTimeout;
    const getDraftValue = (options && options.getDraftValue) || (() => (textareaEl ? textareaEl.value || "" : ""));
    const setDraftValue = (options && options.setDraftValue) || ((nextValue) => {
      if (textareaEl) textareaEl.value = nextValue;
    });
    const focusDraft = (options && options.focusDraft) || (() => {
      if (!textareaEl || typeof textareaEl.focus !== "function") return;
      textareaEl.focus();
      if (typeof textareaEl.setSelectionRange === "function") {
        const end = String(textareaEl.value || "").length;
        textareaEl.setSelectionRange(end, end);
      }
    });
    const isBusy = (options && options.isBusy) || (() => false);
    const endpoint = (options && options.endpoint) || DEFAULT_ENDPOINT;
    const maxRecordingMs = Number((options && options.maxRecordingMs) || DEFAULT_MAX_RECORDING_MS);

    let state = STATES.IDLE;
    let recorder = null;
    let mediaStream = null;
    let pendingChunks = [];
    let autoStopTimer = null;
    let selectedMimeType = "";
    let errorMessage = "";

    function supported() {
      return Boolean(
        buttonEl &&
        fetchImpl &&
        mediaDevices &&
        typeof mediaDevices.getUserMedia === "function" &&
        MediaRecorderCtor &&
        FormDataCtor &&
        BlobCtor
      );
    }

    function visualState() {
      if (state === STATES.IDLE && isBusy()) return STATES.BUSY;
      return state;
    }

    function clearTimer() {
      if (autoStopTimer && typeof clearTimeoutFn === "function") {
        clearTimeoutFn(autoStopTimer);
      }
      autoStopTimer = null;
    }

    function stopTracks() {
      if (!mediaStream || typeof mediaStream.getTracks !== "function") {
        mediaStream = null;
        return;
      }
      for (const track of mediaStream.getTracks()) {
        if (track && typeof track.stop === "function") {
          track.stop();
        }
      }
      mediaStream = null;
    }

    function render(messageOverride) {
      const activeState = visualState();
      const available = supported();
      const label = buildButtonLabel(activeState, available);
      const message = typeof messageOverride === "string"
        ? messageOverride
        : activeState === STATES.RECORDING
          ? "Enregistrement en cours."
          : activeState === STATES.TRANSCRIBING
            ? "Transcription en cours."
            : activeState === STATES.BUSY
              ? "Réponse assistant en cours."
              : activeState === STATES.ERROR
                ? errorMessage
                : "";

      if (buttonEl) {
        buttonEl.disabled = !available || activeState === STATES.BUSY || activeState === STATES.TRANSCRIBING;
        if (activeState === STATES.RECORDING) {
          buttonEl.disabled = false;
        }
        buttonEl.title = label;
        if (typeof buttonEl.setAttribute === "function") {
          buttonEl.setAttribute("aria-label", label);
          buttonEl.setAttribute("aria-pressed", activeState === STATES.RECORDING ? "true" : "false");
        }
        setDataState(buttonEl, activeState);
      }

      setStatusMessage(statusEl, available ? message : "Dictée vocale indisponible sur ce navigateur", activeState === STATES.ERROR || !available);
    }

    function bindRecorderEvent(target, eventName, handler) {
      if (!target) return;
      if (typeof target.addEventListener === "function") {
        target.addEventListener(eventName, handler);
        return;
      }
      target[`on${eventName}`] = handler;
    }

    async function finalizeRecording() {
      const blobType = text((recorder && recorder.mimeType) || selectedMimeType);
      const audioBlob = new BlobCtor(pendingChunks, blobType ? { type: blobType } : undefined);
      pendingChunks = [];
      stopTracks();

      if (!audioBlob || Number(audioBlob.size || 0) <= 0) {
        state = STATES.ERROR;
        errorMessage = "Aucun audio détecté";
        render();
        return;
      }

      state = STATES.TRANSCRIBING;
      errorMessage = "";
      render();

      try {
        const transcript = await transcribeBlob({
          audioBlob,
          mimeType: blobType,
          endpoint,
          fetchImpl,
          FormDataCtor,
        });
        const nextDraft = joinTranscriptToDraft(getDraftValue(), transcript);
        setDraftValue(nextDraft);
        triggerInputEvent(textareaEl);
        focusDraft();
        state = STATES.IDLE;
        errorMessage = "";
        render("");
      } catch (error) {
        state = STATES.ERROR;
        errorMessage = text(error && error.message) || "Transcription indisponible";
        render();
      } finally {
        recorder = null;
      }
    }

    async function startRecording() {
      if (!supported()) {
        state = STATES.ERROR;
        errorMessage = "Dictée vocale indisponible sur ce navigateur";
        render();
        return;
      }
      if (isBusy()) {
        state = STATES.IDLE;
        render();
        return;
      }

      try {
        mediaStream = await mediaDevices.getUserMedia({ audio: true });
      } catch (error) {
        stopTracks();
        state = STATES.ERROR;
        errorMessage = browserErrorMessage(error);
        render();
        return;
      }

      pendingChunks = [];
      selectedMimeType = pickSupportedMimeType(MediaRecorderCtor);

      try {
        recorder = selectedMimeType ? new MediaRecorderCtor(mediaStream, { mimeType: selectedMimeType }) : new MediaRecorderCtor(mediaStream);
      } catch {
        stopTracks();
        recorder = null;
        state = STATES.ERROR;
        errorMessage = "Enregistrement audio indisponible";
        render();
        return;
      }

      bindRecorderEvent(recorder, "dataavailable", (event) => {
        const chunk = event && event.data;
        if (chunk && Number(chunk.size || 0) > 0) {
          pendingChunks.push(chunk);
        }
      });
      bindRecorderEvent(recorder, "error", () => {
        clearTimer();
        stopTracks();
        recorder = null;
        pendingChunks = [];
        state = STATES.ERROR;
        errorMessage = "Enregistrement audio interrompu";
        render();
      });
      bindRecorderEvent(recorder, "stop", () => {
        void finalizeRecording();
      });

      recorder.start();
      state = STATES.RECORDING;
      errorMessage = "";
      render();

      if (typeof setTimeoutFn === "function") {
        autoStopTimer = setTimeoutFn(() => {
          if (!recorder || recorder.state !== "recording") return;
          state = STATES.TRANSCRIBING;
          render();
          recorder.stop();
        }, Number.isFinite(maxRecordingMs) ? maxRecordingMs : DEFAULT_MAX_RECORDING_MS);
      }
    }

    function stopRecording() {
      if (!recorder || recorder.state !== "recording") return;
      clearTimer();
      state = STATES.TRANSCRIBING;
      render();
      recorder.stop();
    }

    async function handleButtonClick() {
      if (visualState() === STATES.BUSY || !supported()) {
        render();
        return;
      }
      if (state === STATES.RECORDING) {
        stopRecording();
        return;
      }
      await startRecording();
    }

    if (buttonEl && typeof buttonEl.addEventListener === "function") {
      buttonEl.addEventListener("click", () => {
        void handleButtonClick();
      });
    }

    render();

    return {
      getState() {
        return state;
      },
      refreshUi() {
        render();
      },
      stopRecording,
    };
  }

  return {
    STATES,
    buildUploadFilename,
    createWhisperDictation,
    joinTranscriptToDraft,
    pickSupportedMimeType,
    transcribeBlob,
  };
});
