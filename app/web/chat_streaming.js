'use strict';

const STREAM_CONTROL_PREFIX = "\x1e";
const STREAM_CONTROL_KIND = "frida-stream-control";
const STREAMING_UI_STATE_PREPARING = "preparing";
const STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT = "waiting_visible_content";
const STREAMING_UI_STATE_STREAMING = "streaming";
const STREAMING_UI_STATE_DONE = "done";
const STREAMING_UI_STATE_INTERRUPTED = "interrupted";
const STREAMING_UI_EVENT_REQUEST_STARTED = "request_started";
const STREAMING_UI_EVENT_RESPONSE_OPENED = "response_opened";
const STREAMING_UI_EVENT_VISIBLE_CONTENT = "visible_content";
const STREAMING_UI_EVENT_TERMINAL_DONE = "terminal_done";
const STREAMING_UI_EVENT_TERMINAL_ERROR = "terminal_error";
const STREAMING_UI_EVENT_NETWORK_ERROR = "network_error";
const STREAM_ERROR_KIND_INTERRUPTED = "interrupted";
const STREAM_ERROR_KIND_UPSTREAM = "upstream_error";
const STREAM_ERROR_KIND_SERVER = "server_error";
const STREAM_ERROR_KIND_NETWORK = "network_error";
const STREAM_SERVER_ERROR_CODES = new Set([
  "stream_terminal_error",
  "stream_finalize_error",
  "stream_protocol_error",
  "conversation_persist_failed",
  "missing_stream_terminal",
  "multiple_stream_terminal",
  "content_after_stream_terminal",
]);
const STREAM_NETWORK_ERROR_MESSAGE_RE = /(failed to fetch|networkerror|load failed|network request failed|body stream|the network connection was lost|terminated|stream aborted)/i;
const STREAM_ERROR_META = Object.freeze({
  [STREAM_ERROR_KIND_INTERRUPTED]: {
    statusLabel: "Interrompu",
    bubbleMessage: "Réponse interrompue.",
  },
  [STREAM_ERROR_KIND_UPSTREAM]: {
    statusLabel: "Interrompu par le modèle",
    bubbleMessage: "Réponse interrompue par le modèle.",
  },
  [STREAM_ERROR_KIND_SERVER]: {
    statusLabel: "Interrompu côté serveur",
    bubbleMessage: "Réponse interrompue côté serveur.",
  },
  [STREAM_ERROR_KIND_NETWORK]: {
    statusLabel: "Connexion interrompue",
    bubbleMessage: "Connexion interrompue pendant la réponse.",
  },
});
const ASSISTANT_TURN_META_KEY = "assistant_turn";
const ASSISTANT_TURN_STATUS_INTERRUPTED = "interrupted";

const STREAMING_UI_STATE_META = Object.freeze({
  [STREAMING_UI_STATE_PREPARING]: {
    label: "Préparation…",
    tone: "pending",
    visible: true,
  },
  [STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT]: {
    label: "Réponse en attente…",
    tone: "pending",
    visible: true,
  },
  [STREAMING_UI_STATE_STREAMING]: {
    label: "Réponse en cours",
    tone: "live",
    visible: true,
  },
  [STREAMING_UI_STATE_DONE]: {
    label: "",
    tone: "done",
    visible: false,
  },
  [STREAMING_UI_STATE_INTERRUPTED]: {
    label: "Interrompu",
    tone: "error",
    visible: true,
  },
});

function reduceStreamingUiState(currentState, event) {
  if (currentState === STREAMING_UI_STATE_DONE || currentState === STREAMING_UI_STATE_INTERRUPTED) {
    return currentState;
  }
  switch (event) {
    case STREAMING_UI_EVENT_REQUEST_STARTED:
      return STREAMING_UI_STATE_PREPARING;
    case STREAMING_UI_EVENT_RESPONSE_OPENED:
      if (currentState === STREAMING_UI_STATE_STREAMING) return currentState;
      return STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT;
    case STREAMING_UI_EVENT_VISIBLE_CONTENT:
      return STREAMING_UI_STATE_STREAMING;
    case STREAMING_UI_EVENT_TERMINAL_DONE:
      return STREAMING_UI_STATE_DONE;
    case STREAMING_UI_EVENT_TERMINAL_ERROR:
    case STREAMING_UI_EVENT_NETWORK_ERROR:
      return STREAMING_UI_STATE_INTERRUPTED;
    default:
      return currentState || null;
  }
}

function getStreamingUiStateMeta(state, interruptionMeta = null) {
  const meta = STREAMING_UI_STATE_META[state] || null;
  if (!meta || state !== STREAMING_UI_STATE_INTERRUPTED) {
    return meta;
  }
  const statusLabel = String(interruptionMeta && interruptionMeta.statusLabel || "").trim();
  if (!statusLabel) {
    return meta;
  }
  return { ...meta, label: statusLabel };
}

function hasVisibleAssistantContent(text) {
  return /\S/u.test(String(text || ""));
}

function parseStructuredErrorPayload(err) {
  if (!err) return null;
  const raw = err && typeof err === "object" ? err.message || String(err) : String(err);
  try {
    const payload = JSON.parse(raw);
    return payload && typeof payload === "object" ? payload : null;
  } catch {
    return null;
  }
}

function getObservableStreamErrorMeta(err) {
  const payload = parseStructuredErrorPayload(err);
  const terminal = err && typeof err === "object" && err.terminal && typeof err.terminal === "object"
    ? err.terminal
    : null;
  const errorName = String(err && typeof err === "object" ? err.name || "" : "").trim();
  const errorCode = String(
    (terminal && terminal.error_code)
    || (payload && payload.code)
    || (err && typeof err === "object" ? err.code || "" : ""),
  ).trim();
  const payloadMessage = String(payload && payload.error || "").trim();
  const rawMessage = String(
    payloadMessage
    || (err && typeof err === "object" ? err.message || "" : err || ""),
  ).trim();
  let kind = STREAM_ERROR_KIND_INTERRUPTED;

  if (errorCode === STREAM_ERROR_KIND_UPSTREAM) {
    kind = STREAM_ERROR_KIND_UPSTREAM;
  } else if (
    STREAM_SERVER_ERROR_CODES.has(errorCode)
    || errorName === "FridaStreamTerminalError"
    || errorName === "FridaStreamProtocolError"
    || (errorCode && errorCode.startsWith("stream_"))
  ) {
    kind = STREAM_ERROR_KIND_SERVER;
  } else if (
    errorName === "AbortError"
    || (errorName === "TypeError" && STREAM_NETWORK_ERROR_MESSAGE_RE.test(rawMessage))
    || (!errorCode && STREAM_NETWORK_ERROR_MESSAGE_RE.test(rawMessage))
  ) {
    kind = STREAM_ERROR_KIND_NETWORK;
  }

  const baseMeta = STREAM_ERROR_META[kind] || STREAM_ERROR_META[STREAM_ERROR_KIND_INTERRUPTED];
  return {
    kind,
    errorCode: errorCode || null,
    statusLabel: baseMeta.statusLabel,
    bubbleMessage: kind === STREAM_ERROR_KIND_INTERRUPTED && payloadMessage
      ? payloadMessage
      : baseMeta.bubbleMessage,
    terminal,
  };
}

function buildInterruptedAssistantTurnMeta(errorCode) {
  const normalizedErrorCode = String(errorCode || "").trim();
  const payload = {
    status: ASSISTANT_TURN_STATUS_INTERRUPTED,
  };
  if (normalizedErrorCode) {
    payload.error_code = normalizedErrorCode;
  }
  return {
    [ASSISTANT_TURN_META_KEY]: payload,
  };
}

function getPersistedAssistantTurnErrorMeta(message) {
  if (!message || message.role !== "assistant" || !message.meta || typeof message.meta !== "object") {
    return null;
  }
  const assistantTurn = message.meta[ASSISTANT_TURN_META_KEY];
  if (!assistantTurn || typeof assistantTurn !== "object") {
    return null;
  }
  if (String(assistantTurn.status || "").trim().toLowerCase() !== ASSISTANT_TURN_STATUS_INTERRUPTED) {
    return null;
  }
  const errorCode = String(assistantTurn.error_code || "stream_protocol_error").trim();
  return getObservableStreamErrorMeta({ code: errorCode });
}

function parseStreamControlFrame(frameText) {
  const text = String(frameText || "");
  if (!text.startsWith(STREAM_CONTROL_PREFIX) || !text.endsWith("\n")) return null;
  let payload = null;
  try {
    payload = JSON.parse(text.slice(STREAM_CONTROL_PREFIX.length, -1));
  } catch {
    return null;
  }
  if (!payload || payload.kind !== STREAM_CONTROL_KIND) return null;
  const event = String(payload.event || "").trim().toLowerCase();
  if (event !== "done" && event !== "error") return null;
  const terminal = { event };
  const errorCode = String(payload.error_code || "").trim();
  if (errorCode) {
    terminal.error_code = errorCode;
  }
  const updatedAt = String(payload.updated_at || "").trim();
  if (updatedAt) {
    terminal.updated_at = updatedAt;
  }
  return terminal;
}

function createStreamTerminalError(terminal) {
  const errorCode = terminal && terminal.error_code ? terminal.error_code : "stream_terminal_error";
  const errorMeta = getObservableStreamErrorMeta({
    name: "FridaStreamTerminalError",
    code: errorCode,
    terminal: terminal || null,
  });
  const error = new Error(JSON.stringify({
    error: errorMeta.bubbleMessage,
    code: errorCode,
  }));
  error.name = "FridaStreamTerminalError";
  error.code = errorCode;
  error.observableKind = errorMeta.kind;
  error.terminal = terminal || null;
  return error;
}

function createStreamProtocolError(code) {
  const errorCode = String(code || "stream_protocol_error");
  const errorMeta = getObservableStreamErrorMeta({
    name: "FridaStreamProtocolError",
    code: errorCode,
  });
  const error = new Error(JSON.stringify({
    error: errorMeta.bubbleMessage,
    code: errorCode,
  }));
  error.name = "FridaStreamProtocolError";
  error.code = errorCode;
  error.observableKind = errorMeta.kind;
  return error;
}

function createStreamControlParser({ onContent } = {}) {
  let pending = "";
  let terminal = null;
  let terminalSeen = false;

  const emitContent = (text) => {
    if (!text) return;
    if (typeof onContent === "function") {
      onContent(text);
    }
  };

  return {
    push(chunk) {
      const text = String(chunk || "");
      if (!text) return;
      pending += text;
      while (pending) {
        const markerIndex = pending.indexOf(STREAM_CONTROL_PREFIX);
        if (markerIndex < 0) {
          emitContent(pending);
          pending = "";
          return;
        }
        if (markerIndex > 0) {
          emitContent(pending.slice(0, markerIndex));
          pending = pending.slice(markerIndex);
        }
        const newlineIndex = pending.indexOf("\n", STREAM_CONTROL_PREFIX.length);
        if (newlineIndex < 0) {
          return;
        }
        const frameText = pending.slice(0, newlineIndex + 1);
        pending = pending.slice(newlineIndex + 1);
        const parsed = parseStreamControlFrame(frameText);
        if (!parsed) {
          emitContent(frameText);
          continue;
        }
        if (terminalSeen) {
          throw createStreamProtocolError("multiple_stream_terminal");
        }
        terminalSeen = true;
        terminal = parsed;
        if (pending) {
          throw createStreamProtocolError("content_after_stream_terminal");
        }
      }
    },
    finish() {
      if (pending) {
        const markerIndex = pending.indexOf(STREAM_CONTROL_PREFIX);
        if (markerIndex < 0) {
          emitContent(pending);
          pending = "";
        } else if (markerIndex > 0) {
          emitContent(pending.slice(0, markerIndex));
          pending = pending.slice(markerIndex);
        }
      }
      if (!terminalSeen) {
        throw createStreamProtocolError("missing_stream_terminal");
      }
      if (pending) {
        throw createStreamProtocolError("content_after_stream_terminal");
      }
      return terminal;
    },
  };
}

const FridaChatStreaming = Object.freeze({
  STREAM_CONTROL_PREFIX,
  STREAM_CONTROL_KIND,
  STREAMING_UI_STATE_PREPARING,
  STREAMING_UI_STATE_WAITING_VISIBLE_CONTENT,
  STREAMING_UI_STATE_STREAMING,
  STREAMING_UI_STATE_DONE,
  STREAMING_UI_STATE_INTERRUPTED,
  STREAMING_UI_EVENT_REQUEST_STARTED,
  STREAMING_UI_EVENT_RESPONSE_OPENED,
  STREAMING_UI_EVENT_VISIBLE_CONTENT,
  STREAMING_UI_EVENT_TERMINAL_DONE,
  STREAMING_UI_EVENT_TERMINAL_ERROR,
  STREAMING_UI_EVENT_NETWORK_ERROR,
  STREAM_ERROR_KIND_INTERRUPTED,
  STREAM_ERROR_KIND_UPSTREAM,
  STREAM_ERROR_KIND_SERVER,
  STREAM_ERROR_KIND_NETWORK,
  ASSISTANT_TURN_META_KEY,
  ASSISTANT_TURN_STATUS_INTERRUPTED,
  parseStreamControlFrame,
  createStreamControlParser,
  createStreamTerminalError,
  createStreamProtocolError,
  getObservableStreamErrorMeta,
  buildInterruptedAssistantTurnMeta,
  getPersistedAssistantTurnErrorMeta,
  reduceStreamingUiState,
  getStreamingUiStateMeta,
  hasVisibleAssistantContent,
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = FridaChatStreaming;
}

if (typeof window !== "undefined") {
  window.FridaChatStreaming = FridaChatStreaming;
}
