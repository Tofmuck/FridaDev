(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before log/log.js");
  }

  const elements = {
    statusBanner: document.getElementById("logStatusBanner"),
    refresh: document.getElementById("logRefresh"),
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
    exportConversation: document.getElementById("exportConversationLogs"),
    exportTurn: document.getElementById("exportTurnLogs"),
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
  const LOG_METADATA_ENDPOINT = "/api/admin/logs/chat/metadata";
  const LOG_EXPORT_MARKDOWN_ENDPOINT = "/api/admin/logs/chat/export.md";

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

  const formatMemoryPromptInjection = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return compactValue(value);
    }
    const injected = Boolean(value.injected);
    const traces = toBoundedInt(value.memory_traces_injected_count, 0, 0, 9999);
    const memoryContext = toBoundedInt(value.memory_context_summary_count, 0, 0, 9999);
    const hints = toBoundedInt(value.context_hints_injected_count, 0, 0, 9999);
    const blocks = toBoundedInt(value.prompt_block_count, 0, 0, 9999);
    return `injected=${injected} traces=${traces} memory_context=${memoryContext} hints=${hints} blocks=${blocks}`;
  };

  const payloadEntries = (payload) => {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return [];
    return Object.keys(payload)
      .sort()
      .slice(0, 12)
      .map((key) =>
        `${key}=${
          key === "memory_prompt_injection"
            ? formatMemoryPromptInjection(payload[key])
            : compactValue(payload[key])
        }`
      );
  };

  const compareEventsChronoAsc = (left, right) => {
    const leftTs = Date.parse(toText(left?.ts));
    const rightTs = Date.parse(toText(right?.ts));
    if (Number.isFinite(leftTs) && Number.isFinite(rightTs) && leftTs !== rightTs) {
      return leftTs - rightTs;
    }
    const leftId = toText(left?.event_id);
    const rightId = toText(right?.event_id);
    return leftId.localeCompare(rightId);
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

  const buildMetadataQuery = (conversationId) => {
    const query = new URLSearchParams();
    if (conversationId) query.set("conversation_id", conversationId);
    return query.toString();
  };

  const replaceSelectOptions = (selectElement, options, selectedValue) => {
    const normalizedSelected = toText(selectedValue);
    selectElement.innerHTML = "";
    for (const optionData of options) {
      const option = document.createElement("option");
      option.value = optionData.value;
      option.textContent = optionData.label;
      selectElement.appendChild(option);
    }
    if (options.some((option) => option.value === normalizedSelected)) {
      selectElement.value = normalizedSelected;
    } else if (options.length > 0) {
      selectElement.value = options[0].value;
    } else {
      selectElement.value = "";
    }
  };

  const syncScopeButtons = () => {
    const conversationId = toText(elements.conversationId.value);
    const turnId = toText(elements.turnId.value);
    elements.deleteConversation.disabled = !conversationId;
    elements.deleteTurn.disabled = !(conversationId && turnId);
    elements.exportConversation.disabled = !conversationId;
    elements.exportTurn.disabled = !(conversationId && turnId);
  };

  const renderConversationOptions = (conversations, selectedConversationId) => {
    const options = [{ value: "", label: "Toutes" }];
    for (const conversation of conversations) {
      const conversationId = toText(conversation?.conversation_id);
      if (!conversationId) continue;
      const eventsCount = Number(conversation?.events_count);
      const suffix = Number.isFinite(eventsCount) ? ` (${eventsCount})` : "";
      options.push({ value: conversationId, label: `${conversationId}${suffix}` });
    }
    replaceSelectOptions(elements.conversationId, options, selectedConversationId);
  };

  const renderTurnOptions = (turns, selectedTurnId, conversationId) => {
    const hasConversation = Boolean(toText(conversationId));
    if (!hasConversation) {
      replaceSelectOptions(elements.turnId, [{ value: "", label: "Selectionner une conversation" }], "");
      elements.turnId.disabled = true;
      return;
    }

    const options = [{ value: "", label: "Tous" }];
    for (const turn of turns) {
      const turnId = toText(turn?.turn_id);
      if (!turnId) continue;
      const eventsCount = Number(turn?.events_count);
      const suffix = Number.isFinite(eventsCount) ? ` (${eventsCount})` : "";
      options.push({ value: turnId, label: `${turnId}${suffix}` });
    }

    if (options.length === 1) {
      replaceSelectOptions(elements.turnId, [{ value: "", label: "Aucun tour" }], "");
      elements.turnId.disabled = true;
      return;
    }

    replaceSelectOptions(elements.turnId, options, selectedTurnId);
    elements.turnId.disabled = false;
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
      // Keep groups ordered by newest turns first, but display events in natural turn order.
      group.events.sort(compareEventsChronoAsc);

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

  const loadMetadata = async ({ conversationId, preserveTurnSelection = false } = {}) => {
    const requestedConversationId = toText(
      conversationId == null ? elements.conversationId.value : conversationId
    );
    const requestedTurnId = preserveTurnSelection ? toText(elements.turnId.value) : "";
    const query = buildMetadataQuery(requestedConversationId);
    const suffix = query ? `?${query}` : "";

    try {
      const response = await adminApi.fetchAdmin(`${LOG_METADATA_ENDPOINT}${suffix}`);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setStatusBanner(adminApi.errorMessage(data, `Echec metadata logs (${response.status}).`), "error");
        renderConversationOptions([], "");
        renderTurnOptions([], "", "");
        syncScopeButtons();
        return;
      }

      const conversations = Array.isArray(data.conversations) ? data.conversations : [];
      const turns = Array.isArray(data.turns) ? data.turns : [];
      const selectedConversation = toText(data.selected_conversation_id || requestedConversationId);
      renderConversationOptions(conversations, selectedConversation);
      renderTurnOptions(turns, requestedTurnId, elements.conversationId.value);
      syncScopeButtons();
    } catch (error) {
      setStatusBanner(`Erreur metadata logs: ${error?.message || error}`, "error");
      renderConversationOptions([], "");
      renderTurnOptions([], "", "");
      syncScopeButtons();
    }
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
      setStatusBanner("Suppression conversation: selectionner une conversation.", "error");
      return;
    }
    if (scope === "turn" && (!conversationId || !turnId)) {
      setStatusBanner("Suppression tour: selectionner une conversation et un tour.", "error");
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
      await loadMetadata({ conversationId, preserveTurnSelection: false });
      await loadLogs();
    } catch (error) {
      setStatusBanner(`Erreur suppression logs: ${error?.message || error}`, "error");
    }
  };

  const downloadMarkdown = async (response, fallbackFilename) => {
    const rawDisposition = toText(response.headers.get("Content-Disposition"));
    const match = /filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/i.exec(rawDisposition);
    const rawFilename = decodeURIComponent(toText((match && (match[1] || match[2])) || ""));
    const safeFilename = (rawFilename || fallbackFilename)
      .replace(/[^a-zA-Z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "") || fallbackFilename;
    const markdown = await response.text();
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const blobUrl = window.URL.createObjectURL(blob);
    const link = Object.assign(document.createElement("a"), { href: blobUrl, download: safeFilename });
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  };

  const exportLogsMarkdown = async (scope) => {
    const conversationId = toText(elements.conversationId.value);
    const turnId = toText(elements.turnId.value);

    if (scope === "conversation" && !conversationId) {
      setStatusBanner("Export conversation: selectionner une conversation.", "error");
      return;
    }
    if (scope === "turn" && (!conversationId || !turnId)) {
      setStatusBanner("Export tour: selectionner une conversation et un tour.", "error");
      return;
    }

    const query = new URLSearchParams();
    query.set("conversation_id", conversationId);
    if (scope === "turn") query.set("turn_id", turnId);
    const conv = conversationId.replace(/[^a-zA-Z0-9._-]+/g, "-") || "conversation";
    const turn = turnId.replace(/[^a-zA-Z0-9._-]+/g, "-") || "turn";
    const fallbackFilename = scope === "turn" ? `chat-logs-${conv}-${turn}.md` : `chat-logs-${conv}.md`;

    try {
      const response = await adminApi.fetchAdmin(`${LOG_EXPORT_MARKDOWN_ENDPOINT}?${query.toString()}`);
      if (!response.ok) {
        const contentType = toText(response.headers.get("Content-Type")).toLowerCase();
        if (contentType.includes("application/json")) {
          const data = await response.json();
          setStatusBanner(adminApi.errorMessage(data, `Echec export logs (${response.status}).`), "error");
        } else {
          const message = toText(await response.text()) || `Echec export logs (${response.status}).`;
          setStatusBanner(message, "error");
        }
        return;
      }

      await downloadMarkdown(response, fallbackFilename);
      setStatusBanner(`Export Markdown ok (${scope}).`, "ok");
    } catch (error) {
      setStatusBanner(`Erreur export logs: ${error?.message || error}`, "error");
    }
  };

  elements.filtersForm.addEventListener("submit", (event) => {
    event.preventDefault();
    elements.offset.value = "0";
    void loadLogs();
  });

  elements.refresh.addEventListener("click", async () => {
    await loadMetadata({ preserveTurnSelection: true });
    await loadLogs();
  });

  elements.conversationId.addEventListener("change", async () => {
    elements.turnId.value = "";
    elements.offset.value = "0";
    await loadMetadata({
      conversationId: elements.conversationId.value,
      preserveTurnSelection: false,
    });
    await loadLogs();
  });

  elements.turnId.addEventListener("change", () => {
    syncScopeButtons();
  });

  elements.resetFilters.addEventListener("click", async () => {
    elements.conversationId.value = "";
    elements.turnId.value = "";
    elements.stage.value = "";
    elements.status.value = "";
    elements.limit.value = "100";
    elements.offset.value = "0";
    await loadMetadata({ conversationId: "", preserveTurnSelection: false });
    await loadLogs();
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

  elements.deleteConversation.addEventListener("click", () => {
    void deleteLogs("conversation");
  });

  elements.deleteTurn.addEventListener("click", () => {
    void deleteLogs("turn");
  });

  elements.exportConversation.addEventListener("click", () => {
    void exportLogsMarkdown("conversation");
  });

  elements.exportTurn.addEventListener("click", () => {
    void exportLogsMarkdown("turn");
  });

  updateMeta();
  syncScopeButtons();
  void (async () => {
    await loadMetadata({ conversationId: "", preserveTurnSelection: false });
    await loadLogs();
  })();
})();
