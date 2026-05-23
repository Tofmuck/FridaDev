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
  const DEFAULT_MAX_RECORDING_MS = 150_000;
  const MAX_RECORDING_MS_LIMIT = 150_000;
  const STOP_REASONS = {
    MANUAL: "manual",
    AUTO_LIMIT: "auto_limit",
    RECORDER_ERROR: "recorder_error",
    TRACK_ENDED: "track_ended",
    UNKNOWN: "unknown",
  };
  const SAFE_STOP_REASONS = new Set(Object.values(STOP_REASONS));
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

  function normalizeMaxRecordingMs(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) return DEFAULT_MAX_RECORDING_MS;
    return Math.min(Math.round(numeric), MAX_RECORDING_MS_LIMIT);
  }

  function normalizeStopReason(value) {
    const reason = text(value);
    if (SAFE_STOP_REASONS.has(reason)) return reason;
    return STOP_REASONS.UNKNOWN;
  }

  function nowMs(rootValue) {
    const performanceNow = rootValue && rootValue.performance && rootValue.performance.now;
    if (typeof performanceNow === "function") {
      return Number(performanceNow.call(rootValue.performance)) || 0;
    }
    return Date.now();
  }

  function appendMetadataField(formData, name, value) {
    if (!formData || typeof formData.append !== "function") return;
    if (value === null || value === undefined || value === "") return;
    formData.append(name, String(value));
  }

  function buildTranscriptionMetadata(metadata) {
    const durationMs = Math.max(0, Math.round(Number(metadata && metadata.durationMs) || 0));
    const blobSizeBytes = Math.max(0, Math.round(Number(metadata && metadata.blobSizeBytes) || 0));
    const chunkCount = Math.max(0, Math.round(Number(metadata && metadata.chunkCount) || 0));
    return {
      recording_duration_ms: durationMs,
      recording_blob_size_bytes: blobSizeBytes,
      recording_chunk_count: chunkCount,
      recording_stop_reason: normalizeStopReason(metadata && metadata.stopReason),
    };
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

  function setStatusMessage(statusEl, message, isError, stateValue) {
    if (!statusEl) return;
    statusEl.textContent = message || "";
    setDataState(statusEl, isError ? STATES.ERROR : (stateValue || STATES.IDLE));
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
    const metadata = buildTranscriptionMetadata({
      ...(options && options.metadata ? options.metadata : {}),
      blobSizeBytes: audioBlob.size,
    });
    appendMetadataField(formData, "recording_duration_ms", metadata.recording_duration_ms);
    appendMetadataField(formData, "recording_blob_size_bytes", metadata.recording_blob_size_bytes);
    appendMetadataField(formData, "recording_chunk_count", metadata.recording_chunk_count);
    appendMetadataField(formData, "recording_stop_reason", metadata.recording_stop_reason);

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
    const maxRecordingMs = normalizeMaxRecordingMs(options && options.maxRecordingMs);
    const onDraftInputMode = (options && options.onDraftInputMode) || (() => {});
    const onTelemetry = (options && options.onTelemetry) || (() => {});
    const nowFn = (options && options.nowFn) || (() => nowMs(root));

    let state = STATES.IDLE;
    let recorder = null;
    let mediaStream = null;
    let pendingChunks = [];
    let autoStopTimer = null;
    let selectedMimeType = "";
    let errorMessage = "";
    let recordingStartedAtMs = 0;
    let lastStopReason = STOP_REASONS.UNKNOWN;
    let chunkCount = 0;
    let ignoreNextStopEvent = false;

    function emitTelemetry(eventName, payload) {
      if (typeof onTelemetry !== "function") return;
      try {
        onTelemetry(eventName, payload || {});
      } catch {}
    }

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

    function bindTrackEndedHandlers(stream, handler) {
      if (!stream || typeof stream.getTracks !== "function") return;
      for (const track of stream.getTracks()) {
        if (!track) continue;
        if (typeof track.addEventListener === "function") {
          track.addEventListener("ended", handler);
        } else if (!track.onended) {
          track.onended = handler;
        }
      }
    }

    function transcriptionMessage() {
      if (lastStopReason === STOP_REASONS.AUTO_LIMIT) {
        return "Limite de dictée atteinte. Transcription en cours.";
      }
      if (lastStopReason === STOP_REASONS.TRACK_ENDED) {
        return "Micro interrompu. Transcription en cours.";
      }
      return "Transcription en cours.";
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
            ? transcriptionMessage()
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

      setStatusMessage(
        statusEl,
        available ? message : "Dictée vocale indisponible sur ce navigateur",
        activeState === STATES.ERROR || !available,
        activeState,
      );
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
      const durationMs = Math.max(0, Math.round(Number(nowFn()) - recordingStartedAtMs));
      const blobType = text((recorder && recorder.mimeType) || selectedMimeType);
      const audioBlob = new BlobCtor(pendingChunks, blobType ? { type: blobType } : undefined);
      const finalChunkCount = chunkCount;
      pendingChunks = [];
      chunkCount = 0;
      stopTracks();

      if (!audioBlob || Number(audioBlob.size || 0) <= 0) {
        state = STATES.ERROR;
        errorMessage = "Aucun audio détecté";
        emitTelemetry("dictation_recording_empty", {
          recording_duration_ms: durationMs,
          recording_stop_reason: normalizeStopReason(lastStopReason),
          recording_chunk_count: finalChunkCount,
        });
        render();
        return;
      }

      state = STATES.TRANSCRIBING;
      errorMessage = "";
      emitTelemetry("dictation_recording_ready", {
        recording_duration_ms: durationMs,
        recording_blob_size_bytes: Number(audioBlob.size || 0),
        recording_chunk_count: finalChunkCount,
        recording_stop_reason: normalizeStopReason(lastStopReason),
      });
      render();

      try {
        const transcript = await transcribeBlob({
          audioBlob,
          mimeType: blobType,
          endpoint,
          fetchImpl,
          FormDataCtor,
          metadata: {
            durationMs,
            chunkCount: finalChunkCount,
            stopReason: lastStopReason,
          },
        });
        const nextDraft = joinTranscriptToDraft(getDraftValue(), transcript);
        setDraftValue(nextDraft);
        onDraftInputMode("voice");
        triggerInputEvent(textareaEl);
        focusDraft();
        state = STATES.IDLE;
        errorMessage = "";
        emitTelemetry("dictation_transcription_ok", {
          recording_duration_ms: durationMs,
          recording_blob_size_bytes: Number(audioBlob.size || 0),
          recording_chunk_count: finalChunkCount,
          recording_stop_reason: normalizeStopReason(lastStopReason),
        });
        render("");
      } catch (error) {
        state = STATES.ERROR;
        errorMessage = text(error && error.message) || "Transcription indisponible";
        emitTelemetry("dictation_transcription_error", {
          recording_duration_ms: durationMs,
          recording_blob_size_bytes: Number(audioBlob.size || 0),
          recording_chunk_count: finalChunkCount,
          recording_stop_reason: normalizeStopReason(lastStopReason),
          error_name: text(error && error.name) || "Error",
        });
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
      chunkCount = 0;
      selectedMimeType = pickSupportedMimeType(MediaRecorderCtor);
      lastStopReason = STOP_REASONS.UNKNOWN;
      ignoreNextStopEvent = false;
      recordingStartedAtMs = Number(nowFn()) || 0;

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
          chunkCount += 1;
          pendingChunks.push(chunk);
        }
      });
      bindRecorderEvent(recorder, "error", () => {
        clearTimer();
        stopTracks();
        recorder = null;
        pendingChunks = [];
        chunkCount = 0;
        lastStopReason = STOP_REASONS.RECORDER_ERROR;
        ignoreNextStopEvent = true;
        state = STATES.ERROR;
        errorMessage = "Enregistrement audio interrompu";
        emitTelemetry("dictation_recorder_error", {
          recording_stop_reason: STOP_REASONS.RECORDER_ERROR,
        });
        render();
      });
      bindRecorderEvent(recorder, "stop", () => {
        if (ignoreNextStopEvent) {
          ignoreNextStopEvent = false;
          return;
        }
        void finalizeRecording();
      });
      bindTrackEndedHandlers(mediaStream, () => {
        stopRecording(STOP_REASONS.TRACK_ENDED);
      });

      recorder.start();
      state = STATES.RECORDING;
      errorMessage = "";
      emitTelemetry("dictation_recording_started", {
        max_recording_ms: maxRecordingMs,
      });
      render();

      if (typeof setTimeoutFn === "function") {
        autoStopTimer = setTimeoutFn(() => {
          if (!recorder || recorder.state !== "recording") return;
          lastStopReason = STOP_REASONS.AUTO_LIMIT;
          state = STATES.TRANSCRIBING;
          render();
          recorder.stop();
        }, maxRecordingMs);
      }
    }

    function stopRecording(reason) {
      if (!recorder || recorder.state !== "recording") return;
      clearTimer();
      lastStopReason = normalizeStopReason(reason || STOP_REASONS.MANUAL);
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
      getState() { return state; },
      getMaxRecordingMs() { return maxRecordingMs; },
      getLastStopReason() { return lastStopReason; },
      refreshUi() {
        render();
      },
      stopRecording,
    };
  }

  return {
    STATES,
    STOP_REASONS,
    DEFAULT_MAX_RECORDING_MS,
    MAX_RECORDING_MS_LIMIT,
    buildTranscriptionMetadata,
    buildUploadFilename,
    createWhisperDictation,
    joinTranscriptToDraft,
    normalizeMaxRecordingMs,
    pickSupportedMimeType,
    transcribeBlob,
  };
});
