(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before log/log.js");
  }

  const elements = {
    statusBanner: document.getElementById("logStatusBanner"),
    refresh: document.getElementById("logRefresh"),
    tokenButton: document.getElementById("logTokenButton"),
    clearToken: document.getElementById("logClearToken"),
    filtersForm: document.getElementById("logFiltersForm"),
    conversationId: document.getElementById("logConversationId"),
    turnId: document.getElementById("logTurnId"),
    stage: document.getElementById("logStage"),
    status: document.getElementById("logStatus"),
    limit: document.getElementById("logLimit"),
    offset: document.getElementById("logOffset"),
    resetFilters: document.getElementById("logResetFilters"),
    prevPage: document.getElementById("logPrevPage"),
    nextPage: document.getElementById("logNextPage"),
    deleteConversation: document.getElementById("deleteConversationLogs"),
    deleteTurn: document.getElementById("deleteTurnLogs"),
    groups: document.getElementById("logGroups"),
    countChip: document.getElementById("logCountChip"),
    pageChip: document.getElementById("logPageChip"),
  };

  const state = {
    limit: 100,
    offset: 0,
    total: 0,
    count: 0,
    nextOffset: null,
  };

  const toText = (value) => String(value == null ? "" : value).trim();

  const toBoundedInt = (value, fallback, min, max) => {
    const parsed = Number.parseInt(String(value ?? ""), 10);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(max, Math.max(min, parsed));
  };

  const setStatusBanner = (message, stateValue = "") => {
    elements.statusBanner.textContent = message;
    if (!stateValue) {
      delete elements.statusBanner.dataset.state;
      return;
    }
    elements.statusBanner.dataset.state = stateValue;
  };

  const compactValue = (value) => {
    if (value == null) return "null";
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "number") return String(value);
    if (typeof value === "string") {
      const cleaned = value.replace(/\s+/g, " ").trim();
      return cleaned.length > 120 ? `${cleaned.slice(0, 117)}...` : cleaned;
    }
    if (Array.isArray(value)) {
      if (!value.length) return "[]";
      const preview = value.slice(0, 3).map((entry) => compactValue(entry)).join(", ");
      return value.length > 3 ? `[${preview}, ...] (${value.length})` : `[${preview}]`;
    }
    if (typeof value === "object") {
      const keys = Object.keys(value);
      return `{${keys.slice(0, 3).join(", ")}${keys.length > 3 ? ", ..." : ""}}`;
    }
    return String(value);
  };

  const payloadEntries = (payload) => {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return [];
    return Object.keys(payload)
      .sort()
      .slice(0, 12)
      .map((key) => `${key}=${compactValue(payload[key])}`);
  };

  const readFilters = () => {
    const limit = toBoundedInt(elements.limit.value, 100, 1, 500);
    const offset = toBoundedInt(elements.offset.value, 0, 0, 1000000);
    elements.limit.value = String(limit);
    elements.offset.value = String(offset);
    return {
      conversation_id: toText(elements.conversationId.value),
      turn_id: toText(elements.turnId.value),
      stage: toText(elements.stage.value),
      status: toText(elements.status.value).toLowerCase(),
      limit,
      offset,
    };
  };

  const buildReadQuery = (filters) => {
    const query = new URLSearchParams();
    query.set("limit", String(filters.limit));
    query.set("offset", String(filters.offset));
    if (filters.conversation_id) query.set("conversation_id", filters.conversation_id);
    if (filters.turn_id) query.set("turn_id", filters.turn_id);
    if (filters.stage) query.set("stage", filters.stage);
    if (filters.status) query.set("status", filters.status);
    return query.toString();
  };

  const createChip = (text, options = {}) => {
    const chip = document.createElement("span");
    chip.className = "admin-chip";
    chip.textContent = text;
    if (options.status) {
      chip.dataset.status = options.status;
    }
    return chip;
  };

  const renderEmpty = (message) => {
    elements.groups.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    elements.groups.appendChild(empty);
  };

  const renderEvents = (items) => {
    elements.groups.innerHTML = "";
    if (!items.length) {
      renderEmpty("Aucun evenement pour ces filtres.");
      return;
    }

    const groups = new Map();
    for (const item of items) {
      const conversationId = toText(item.conversation_id) || "n/a";
      const turnId = toText(item.turn_id) || "n/a";
      const key = `${conversationId}::${turnId}`;
      if (!groups.has(key)) {
        groups.set(key, { conversationId, turnId, events: [] });
      }
      groups.get(key).events.push(item);
    }

    for (const group of groups.values()) {
      const groupSection = document.createElement("section");
      groupSection.className = "admin-readonly-group";

      const groupHead = document.createElement("div");
      groupHead.className = "admin-readonly-group-head";
      const heading = document.createElement("h4");
      heading.textContent = `${group.conversationId} / ${group.turnId}`;
      groupHead.appendChild(heading);
      groupSection.appendChild(groupHead);

      const meta = document.createElement("div");
      meta.className = "admin-card-meta";
      meta.appendChild(createChip(`events=${group.events.length}`));
      groupSection.appendChild(meta);

      const eventList = document.createElement("div");
      eventList.className = "admin-check-list";

      for (const event of group.events) {
        const row = document.createElement("article");
        row.className = "admin-check";
        const status = toText(event.status).toLowerCase();
        if (status === "ok") row.dataset.ok = "true";
        if (status === "error") row.dataset.ok = "false";

        const left = document.createElement("div");
        const stageLabel = document.createElement("strong");
        stageLabel.textContent = toText(event.stage) || "stage";
        left.appendChild(stageLabel);
        const leftMeta = document.createElement("div");
        leftMeta.className = "admin-card-meta";
        leftMeta.appendChild(createChip(status || "unknown", { status }));
        left.appendChild(leftMeta);

        const right = document.createElement("div");
        const rightMeta = document.createElement("div");
        rightMeta.className = "admin-card-meta";
        rightMeta.appendChild(createChip(toText(event.ts) || "ts=n/a"));
        if (event.duration_ms != null) {
          rightMeta.appendChild(createChip(`duration=${event.duration_ms}ms`));
        }
        right.appendChild(rightMeta);

        const payloadMeta = document.createElement("div");
        payloadMeta.className = "admin-card-meta";
        const entries = payloadEntries(event.payload);
        if (!entries.length) {
          payloadMeta.appendChild(createChip("payload=vide"));
        } else {
          for (const entry of entries) {
            payloadMeta.appendChild(createChip(entry));
          }
        }
        right.appendChild(payloadMeta);

        row.appendChild(left);
        row.appendChild(right);
        eventList.appendChild(row);
      }

      groupSection.appendChild(eventList);
      elements.groups.appendChild(groupSection);
    }
  };

  const updateMeta = () => {
    elements.countChip.textContent = `${state.count} evenement${state.count > 1 ? "s" : ""} / ${state.total}`;
    elements.pageChip.textContent = `offset ${state.offset}`;
    elements.prevPage.disabled = state.offset <= 0;
    elements.nextPage.disabled = state.nextOffset == null;
  };

  const loadLogs = async () => {
    const filters = readFilters();
    state.limit = filters.limit;
    state.offset = filters.offset;
    setStatusBanner("Chargement des logs...", "");

    try {
      const response = await adminApi.fetchAdmin(`/api/admin/logs/chat?${buildReadQuery(filters)}`);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setStatusBanner(adminApi.errorMessage(data, `Echec lecture logs (${response.status}).`), "error");
        renderEmpty("Lecture indisponible.");
        state.count = 0;
        state.total = 0;
        state.nextOffset = null;
        updateMeta();
        return;
      }

      const items = Array.isArray(data.items) ? data.items : [];
      state.count = Number(data.count) || items.length;
      state.total = Number(data.total) || items.length;
      state.nextOffset = data.next_offset == null ? null : Number(data.next_offset);
      renderEvents(items);
      updateMeta();
      if (state.count === 0) {
        setStatusBanner("Aucun evenement pour ces filtres.", "ok");
      } else {
        setStatusBanner(`Lecture ok (${state.count} evenement${state.count > 1 ? "s" : ""}).`, "ok");
      }
    } catch (error) {
      setStatusBanner(`Erreur reseau logs: ${error?.message || error}`, "error");
      renderEmpty("Lecture indisponible.");
      state.count = 0;
      state.total = 0;
      state.nextOffset = null;
      updateMeta();
    }
  };

  const deleteLogs = async (scope) => {
    const conversationId = toText(elements.conversationId.value);
    const turnId = toText(elements.turnId.value);

    if (scope === "conversation" && !conversationId) {
      setStatusBanner("Suppression conversation: renseigner conversation_id.", "error");
      return;
    }
    if (scope === "turn" && (!conversationId || !turnId)) {
      setStatusBanner("Suppression tour: renseigner conversation_id et turn_id.", "error");
      return;
    }

    const query = new URLSearchParams();
    query.set("conversation_id", conversationId);
    if (scope === "turn") query.set("turn_id", turnId);

    const confirmationLabel = scope === "turn"
      ? `Supprimer les logs du tour ${turnId} (conversation ${conversationId}) ?`
      : `Supprimer tous les logs de la conversation ${conversationId} ?`;
    if (!window.confirm(confirmationLabel)) {
      return;
    }

    try {
      const response = await adminApi.fetchAdmin(`/api/admin/logs/chat?${query.toString()}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setStatusBanner(adminApi.errorMessage(data, `Echec suppression logs (${response.status}).`), "error");
        return;
      }
      elements.offset.value = "0";
      setStatusBanner(`Suppression ok (${data.deleted_count || 0} evenement(s) supprime(s)).`, "ok");
      await loadLogs();
    } catch (error) {
      setStatusBanner(`Erreur suppression logs: ${error?.message || error}`, "error");
    }
  };

  elements.filtersForm.addEventListener("submit", (event) => {
    event.preventDefault();
    elements.offset.value = "0";
    void loadLogs();
  });

  elements.refresh.addEventListener("click", () => {
    void loadLogs();
  });

  elements.resetFilters.addEventListener("click", () => {
    elements.conversationId.value = "";
    elements.turnId.value = "";
    elements.stage.value = "";
    elements.status.value = "";
    elements.limit.value = "100";
    elements.offset.value = "0";
    void loadLogs();
  });

  elements.prevPage.addEventListener("click", () => {
    const limit = toBoundedInt(elements.limit.value, 100, 1, 500);
    const currentOffset = toBoundedInt(elements.offset.value, 0, 0, 1000000);
    elements.offset.value = String(Math.max(0, currentOffset - limit));
    void loadLogs();
  });

  elements.nextPage.addEventListener("click", () => {
    if (state.nextOffset == null) return;
    elements.offset.value = String(state.nextOffset);
    void loadLogs();
  });

  elements.tokenButton.addEventListener("click", () => {
    const current = adminApi.readToken();
    const next = window.prompt("Token admin", current || "");
    if (next == null) return;
    adminApi.writeToken(next);
    void loadLogs();
  });

  elements.clearToken.addEventListener("click", () => {
    adminApi.clearToken();
    void loadLogs();
  });

  elements.deleteConversation.addEventListener("click", () => {
    void deleteLogs("conversation");
  });

  elements.deleteTurn.addEventListener("click", () => {
    void deleteLogs("turn");
  });

  updateMeta();
  void loadLogs();
})();
