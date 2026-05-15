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
    cockpitCards: document.getElementById("logCockpitCards"),
    cockpitSourceChip: document.getElementById("logCockpitSourceChip"),
    cockpitWindowChip: document.getElementById("logCockpitWindowChip"),
    turns: document.getElementById("logTurns"),
    turnCountChip: document.getElementById("logTurnCountChip"),
    turnSourceChip: document.getElementById("logTurnSourceChip"),
  };

  const state = {
    limit: 100,
    offset: 0,
    total: 0,
    count: 0,
    nextOffset: null,
  };
  const LOG_METADATA_ENDPOINT = "/api/admin/logs/chat/metadata";
  const LOG_METRICS_ENDPOINT = "/api/admin/logs/chat/metrics";
  const LOG_TURNS_ENDPOINT = "/api/admin/logs/chat/turns";
  const LOG_EXPORT_MARKDOWN_ENDPOINT = "/api/admin/logs/chat/export.md";
  const METRICS_EVENT_LIMIT = 2000;
  const METRIC_VISUAL_SOURCES = Object.freeze({
    classification: "checklist.classification_counts",
    providers: "llm_call_provider_metrics",
    rag: "rag_funnel",
    web: "web",
    anomalies: "errors_by_stage/skipped_by_stage/fallback_fail_open.by_stage",
  });
  const BLOCKED_PAYLOAD_KEYS = new Set([
    "canonical_inputs",
    "content",
    "context_block",
    "identity",
    "identity_text",
    "memory",
    "memory_trace",
    "memory_traces",
    "messages",
    "prompt",
    "query",
    "raw_identity",
    "raw_query",
    "result_snippet",
    "search_snippet",
  ]);
  const BLOCKED_METRIC_LABELS = new Set([
    "canonical_inputs",
    "content",
    "context_block",
    "messages",
    "prompt",
    "query",
    "raw_identity",
    "raw_query",
  ]);

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
      return `array[${value.length}]`;
    }
    if (typeof value === "object") {
      return `object[${Object.keys(value).length}]`;
    }
    return String(value);
  };

  const formatMemoryPromptInjection = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return compactValue(value);
    }
    const injected = Boolean(value.injected);
    const lane = toText(value.injection_class) || "unknown";
    const traces = toBoundedInt(value.trace_memory_injected_count ?? value.memory_traces_injected_count, 0, 0, 9999);
    const memoryContext = toBoundedInt(value.summary_context_injected_count ?? value.memory_context_summary_count, 0, 0, 9999);
    const hints = toBoundedInt(value.context_hints_injected_count, 0, 0, 9999);
    const blocks = toBoundedInt(value.prompt_block_count, 0, 0, 9999);
    return `injected=${injected} lane=${lane} traces=${traces} summary_context=${memoryContext} hints=${hints} blocks=${blocks}`;
  };

  const payloadEntries = (payload) => {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return [];
    return Object.keys(payload)
      .sort()
      .filter((key) => !BLOCKED_PAYLOAD_KEYS.has(key))
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

  const buildMetricsQuery = () => {
    const query = new URLSearchParams();
    query.set("event_limit", String(METRICS_EVENT_LIMIT));
    return query.toString();
  };

  const buildTurnsQuery = (filters) => {
    const query = new URLSearchParams();
    query.set("limit", String(Math.min(filters.limit, 100)));
    query.set("offset", String(filters.offset));
    if (filters.conversation_id) query.set("conversation_id", filters.conversation_id);
    if (filters.turn_id) query.set("turn_id", filters.turn_id);
    return query.toString();
  };

  const buildMetadataQuery = (conversationId) => {
    const query = new URLSearchParams();
    if (conversationId) query.set("conversation_id", conversationId);
    return query.toString();
  };

  const readInitialFiltersFromLocation = () => {
    const params = new URLSearchParams(window.location.search || "");
    return {
      conversation_id: toText(params.get("conversation_id")),
      turn_id: toText(params.get("turn_id")),
      stage: toText(params.get("stage")),
      status: toText(params.get("status")).toLowerCase(),
      limit: toBoundedInt(params.get("limit"), 100, 1, 500),
      offset: toBoundedInt(params.get("offset"), 0, 0, 1000000),
    };
  };

  const applyInitialFiltersFromLocation = () => {
    const filters = readInitialFiltersFromLocation();
    if (filters.stage) elements.stage.value = filters.stage;
    if (filters.status) elements.status.value = filters.status;
    elements.limit.value = String(filters.limit);
    elements.offset.value = String(filters.offset);
    return filters;
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

  const appendChip = (parent, text, status = "") => {
    parent.appendChild(createChip(text, status ? { status } : {}));
  };

  const statusTone = (value) => {
    const status = toText(value).toLowerCase();
    if (["ok", "complete", "saved", "present", "success"].includes(status)) return status;
    if (["degraded", "partial", "skipped", "interrupted", "not_saved"].includes(status)) return status;
    if (["error", "legacy_incomplete", "missing", "absent", "failed"].includes(status)) return status;
    return "";
  };

  const safeCount = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const sanitizeMetricLabel = (value) => {
    const text = toText(value).toLowerCase();
    if (!text) return "unknown";
    if (BLOCKED_METRIC_LABELS.has(text)) return "redacted_label";
    if (!/^[a-z0-9_:-]{1,48}$/.test(text)) return "unknown";
    return text;
  };

  const sumObjectValues = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return 0;
    return Object.values(value).reduce((total, entry) => total + safeCount(entry), 0);
  };

  const shortId = (value) => {
    const text = toText(value);
    if (text.length <= 18) return text || "n/a";
    return `${text.slice(0, 8)}...${text.slice(-6)}`;
  };

  const metricWindowText = (source, metrics) =>
    `fenetre events=${safeCount(source.events_read ?? metrics?.events_count)} / ${safeCount(source.events_total ?? metrics?.events_count)}; limit=${METRICS_EVENT_LIMIT}`;

  const createMiniBars = (rows, options = {}) => {
    const container = document.createElement("div");
    container.className = "log-mini-bars";
    const normalizedRows = rows
      .map((row) => ({
        label: sanitizeMetricLabel(row.label),
        value: safeCount(row.value),
        status: row.status || "",
      }))
      .filter((row) => options.showZero || row.value > 0);

    if (!normalizedRows.length) {
      const empty = document.createElement("p");
      empty.className = "log-mini-empty";
      empty.textContent = options.emptyMessage || "Aucun signal dans la fenetre.";
      container.appendChild(empty);
      return container;
    }

    const maxValue = Math.max(
      1,
      safeCount(options.maxValue),
      ...normalizedRows.map((row) => row.value),
    );

    for (const row of normalizedRows) {
      const line = document.createElement("div");
      line.className = "log-mini-bar-row";
      if (row.status) line.dataset.status = row.status;

      const label = document.createElement("span");
      label.className = "log-mini-bar-label";
      label.textContent = row.label;
      line.appendChild(label);

      const track = document.createElement("span");
      track.className = "log-mini-bar-track";
      const fill = document.createElement("span");
      fill.className = "log-mini-bar-fill";
      fill.style.width = row.value > 0 ? `${Math.max(2, Math.round((row.value / maxValue) * 100))}%` : "0";
      track.appendChild(fill);
      line.appendChild(track);

      const value = document.createElement("span");
      value.className = "log-mini-bar-value";
      value.textContent = String(row.value);
      line.appendChild(value);
      container.appendChild(line);
    }

    return container;
  };

  const objectMetricRows = (source, prefix, status) => {
    if (!source || typeof source !== "object" || Array.isArray(source)) return [];
    return Object.entries(source)
      .map(([key, value]) => ({
        label: `${prefix}:${sanitizeMetricLabel(key)}`,
        value: safeCount(value),
        status,
      }))
      .filter((row) => row.value > 0)
      .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label));
  };

  const rowsOrEmpty = (rows) => (rows.some((row) => safeCount(row.value) > 0) ? rows : []);

  const createMetricCard = (title, chips, options = {}) => {
    const card = document.createElement("article");
    card.className = "admin-card";
    const head = document.createElement("div");
    head.className = "admin-card-head";
    const heading = document.createElement("h3");
    heading.textContent = title;
    head.appendChild(heading);
    if (options.source) {
      const source = document.createElement("span");
      source.className = "admin-card-source";
      source.textContent = options.source;
      source.title = options.source;
      head.appendChild(source);
    }
    card.appendChild(head);
    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    for (const chip of chips) {
      if (!chip) continue;
      appendChip(meta, chip.text, chip.status || "");
    }
    card.appendChild(meta);
    if (options.body) {
      card.appendChild(options.body);
    }
    if (options.note) {
      const note = document.createElement("p");
      note.className = "log-mini-note";
      note.textContent = options.note;
      card.appendChild(note);
    }
    return card;
  };

  const renderCockpitEmpty = (message, stateValue = "") => {
    elements.cockpitCards.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    if (stateValue) empty.dataset.state = stateValue;
    elements.cockpitCards.appendChild(empty);
  };

  const renderTurnsEmpty = (message) => {
    elements.turns.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    elements.turns.appendChild(empty);
  };

  const renderEmpty = (message) => {
    elements.groups.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    elements.groups.appendChild(empty);
  };

  const renderCockpit = (metrics) => {
    const source = metrics?.source || {};
    const checklist = metrics?.checklist || {};
    const classes = checklist.classification_counts || {};
    const llm = metrics?.llm_call_provider_metrics || {};
    const web = metrics?.web || {};
    const rag = metrics?.rag_funnel || {};
    const fallback = metrics?.fallback_fail_open || {};
    const errorsByStage = metrics?.errors_by_stage || {};
    const skippedByStage = metrics?.skipped_by_stage || {};
    const eventsTruncated = Boolean(source.events_truncated);

    elements.cockpitCards.innerHTML = "";
    elements.cockpitSourceChip.textContent = eventsTruncated ? "source tronquee" : "source complete";
    elements.cockpitSourceChip.dataset.status = eventsTruncated ? "degraded" : "ok";
    elements.cockpitWindowChip.textContent = `events=${safeCount(source.events_read ?? metrics?.events_count)} / ${safeCount(source.events_total ?? metrics?.events_count)}`;
    const observedTurns = safeCount(metrics?.turns_observed_count);
    const sourceWindow = metricWindowText(source, metrics);
    const classRows = [
      { label: "complete", value: classes.complete, status: "complete" },
      { label: "degraded", value: classes.degraded, status: "degraded" },
      { label: "partial", value: classes.partial, status: "partial" },
      { label: "legacy_incomplete", value: classes.legacy_incomplete, status: "legacy_incomplete" },
      { label: "unknown", value: classes.unknown, status: safeCount(classes.unknown) ? "degraded" : "" },
    ];
    const providerRows = [
      { label: "main", value: llm.main_llm_call_count, status: safeCount(llm.main_llm_call_count) ? "ok" : "" },
      { label: "secondary", value: llm.secondary_llm_call_count },
      { label: "unknown", value: llm.unknown_llm_call_count, status: safeCount(llm.unknown_llm_call_count) ? "degraded" : "" },
    ];
    const ragRows = [
      { label: "retrieved", value: rag.retrieved_candidates_total },
      { label: "basket", value: rag.basketed_candidates_total },
      { label: "kept", value: rag.kept_candidates_total },
      { label: "injected", value: rag.injected_candidates_total, status: safeCount(rag.injected_candidates_total) ? "ok" : "" },
    ];
    const webRows = [
      { label: "requested", value: web.requested_turns },
      { label: "success", value: web.successful_count, status: "ok" },
      { label: "injected", value: web.injected_turns, status: safeCount(web.injected_turns) ? "ok" : "" },
      { label: "skipped", value: web.skipped_count, status: safeCount(web.skipped_count) ? "skipped" : "" },
      { label: "error", value: web.error_count, status: safeCount(web.error_count) ? "error" : "" },
    ];
    const anomalyRows = [
      ...objectMetricRows(errorsByStage, "error", "error"),
      ...objectMetricRows(skippedByStage, "skip", "skipped"),
      ...objectMetricRows(fallback.by_stage, "fallback", "degraded"),
    ]
      .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label))
      .slice(0, 6);

    const cards = [
      createMetricCard(
        "Etat global",
        [
          { text: `tours=${safeCount(metrics?.turns_observed_count)}` },
          { text: `complete=${safeCount(classes.complete)}`, status: "complete" },
          { text: `degraded=${safeCount(classes.degraded)}`, status: "degraded" },
          { text: `partial=${safeCount(classes.partial)}`, status: "partial" },
          { text: `legacy=${safeCount(classes.legacy_incomplete)}`, status: "legacy_incomplete" },
        ],
        {
          source: METRIC_VISUAL_SOURCES.classification,
          body: createMiniBars(observedTurns > 0 ? rowsOrEmpty(classRows) : [], {
            maxValue: observedTurns,
            showZero: true,
            emptyMessage: "Aucun tour observe dans la fenetre.",
          }),
          note: `source=${METRIC_VISUAL_SOURCES.classification}; ${sourceWindow}; semantics=classification par tour observe.`,
        },
      ),
      createMetricCard(
        "Providers",
        [
          { text: `main=${safeCount(llm.main_llm_call_count)}`, status: safeCount(llm.main_llm_call_count) ? "ok" : "" },
          { text: `secondary=${safeCount(llm.secondary_llm_call_count)}` },
          { text: `unknown=${safeCount(llm.unknown_llm_call_count)}`, status: safeCount(llm.unknown_llm_call_count) ? "degraded" : "" },
        ],
        {
          source: METRIC_VISUAL_SOURCES.providers,
          body: createMiniBars(rowsOrEmpty(providerRows), {
            showZero: true,
            emptyMessage: "Aucun appel provider observe.",
          }),
          note: `source=${METRIC_VISUAL_SOURCES.providers}; ${sourceWindow}; semantics=appels LLM par provider_caller.`,
        },
      ),
      createMetricCard(
        "RAG",
        [
          { text: `retrieved=${safeCount(rag.retrieved_candidates_total)}` },
          { text: `basket=${safeCount(rag.basketed_candidates_total)}` },
          { text: `kept=${safeCount(rag.kept_candidates_total)}` },
          { text: `injected=${safeCount(rag.injected_candidates_total)}`, status: safeCount(rag.injected_candidates_total) ? "ok" : "" },
          { text: `legacy=${safeCount(rag.prompt_fallback_turns)}`, status: safeCount(rag.prompt_fallback_turns) ? "degraded" : "" },
        ],
        {
          source: METRIC_VISUAL_SOURCES.rag,
          body: createMiniBars(rowsOrEmpty(ragRows), {
            showZero: true,
            emptyMessage: "Aucun signal RAG observe.",
          }),
          note: `source=${METRIC_VISUAL_SOURCES.rag}; ${sourceWindow}; semantics=candidats retrieved -> basket -> kept -> injected.`,
        },
      ),
      createMetricCard(
        "Web",
        [
          { text: `requested=${safeCount(web.requested_turns)}` },
          { text: `ok=${safeCount(web.successful_count)}`, status: "ok" },
          { text: `injected=${safeCount(web.injected_turns)}`, status: safeCount(web.injected_turns) ? "ok" : "" },
          { text: `skipped=${safeCount(web.skipped_count)}`, status: "skipped" },
          { text: `error=${safeCount(web.error_count)}`, status: safeCount(web.error_count) ? "error" : "" },
        ],
        {
          source: METRIC_VISUAL_SOURCES.web,
          body: createMiniBars(rowsOrEmpty(webRows), {
            showZero: true,
            emptyMessage: "Web non sollicite dans la fenetre.",
          }),
          note: `source=${METRIC_VISUAL_SOURCES.web}; ${sourceWindow}; semantics=tours web demandes, succes, injection, skips et erreurs.`,
        },
      ),
      createMetricCard(
        "Erreurs / skips",
        [
          { text: `fallback=${safeCount(fallback.total_count)}`, status: safeCount(fallback.total_count) ? "degraded" : "" },
          { text: `stage_errors=${sumObjectValues(errorsByStage)}`, status: sumObjectValues(errorsByStage) ? "error" : "" },
          { text: `stage_skips=${sumObjectValues(skippedByStage)}`, status: sumObjectValues(skippedByStage) ? "skipped" : "" },
        ],
        {
          source: METRIC_VISUAL_SOURCES.anomalies,
          body: createMiniBars(anomalyRows, {
            emptyMessage: "Aucune erreur, skip ou fallback dans la fenetre.",
          }),
          note: `source=${METRIC_VISUAL_SOURCES.anomalies}; ${sourceWindow}; semantics=top stages avec erreur, skip ou fallback.`,
        },
      ),
    ];

    for (const card of cards) {
      elements.cockpitCards.appendChild(card);
    }

    if (eventsTruncated) {
      const warning = document.createElement("p");
      warning.className = "admin-status";
      warning.dataset.state = "error";
      warning.textContent = "Fenetre metrics tronquee: les compteurs ne couvrent que les events lus.";
      elements.cockpitCards.appendChild(warning);
    }
  };

  const appendTurnText = (parent, label, value, status = "") => {
    appendChip(parent, `${label}=${value}`, statusTone(status));
  };

  const renderTurnRows = (items) => {
    elements.turns.innerHTML = "";
    if (!items.length) {
      renderTurnsEmpty("Aucun tour pour ces filtres.");
      return;
    }

    const table = document.createElement("table");
    table.className = "log-turn-table";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    for (const label of ["Conversation / tour", "Etat", "Persistence", "Providers", "RAG", "Identity / Hermeneutic", "Web / erreurs", "Latest"]) {
      const th = document.createElement("th");
      th.textContent = label;
      headRow.appendChild(th);
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const item of items) {
      const row = document.createElement("tr");
      const persistence = item?.persistence || {};
      const providers = item?.providers || {};
      const mainProvider = providers.main || {};
      const secondary = providers.secondary || {};
      const rag = item?.rag || {};
      const identity = item?.identity || {};
      const hermeneutic = item?.hermeneutic || {};
      const nodeState = hermeneutic.node_state || {};
      const web = item?.web || {};
      const errors = item?.errors || {};

      const scopeCell = document.createElement("td");
      const scope = document.createElement("div");
      scope.className = "log-turn-scope";
      const conv = document.createElement("strong");
      conv.title = toText(item?.conversation_id);
      conv.textContent = shortId(item?.conversation_id);
      const turn = document.createElement("span");
      turn.title = toText(item?.turn_id);
      turn.textContent = shortId(item?.turn_id);
      scope.appendChild(conv);
      scope.appendChild(turn);
      scopeCell.appendChild(scope);
      row.appendChild(scopeCell);

      const stateCell = document.createElement("td");
      const stateMeta = document.createElement("div");
      stateMeta.className = "log-turn-cell";
      appendChip(stateMeta, toText(item?.classification) || "unknown", statusTone(item?.classification));
      appendTurnText(stateMeta, "score", safeCount(item?.score));
      if (item?.flags?.events_truncated) appendChip(stateMeta, "events tronques", "degraded");
      stateCell.appendChild(stateMeta);
      row.appendChild(stateCell);

      const persistCell = document.createElement("td");
      const persistMeta = document.createElement("div");
      persistMeta.className = "log-turn-cell";
      appendChip(persistMeta, toText(persistence.status) || "missing", statusTone(persistence.status));
      appendTurnText(persistMeta, "final", persistence.assistant_final_saved ? "saved" : "absent", persistence.assistant_final_saved ? "saved" : "missing");
      if (persistence.assistant_interrupted) appendChip(persistMeta, "interrupted", "interrupted");
      persistCell.appendChild(persistMeta);
      row.appendChild(persistCell);

      const providersCell = document.createElement("td");
      const providersMeta = document.createElement("div");
      providersMeta.className = "log-turn-cell";
      appendTurnText(providersMeta, "main", toText(mainProvider.status) || "missing", mainProvider.status);
      appendTurnText(providersMeta, "chars", safeCount(mainProvider.response_chars));
      for (const key of ["stimmung", "validation", "web_reformulation"]) {
        const provider = secondary[key] || {};
        appendTurnText(providersMeta, key, toText(provider.status) || "n/a", provider.status);
      }
      providersCell.appendChild(providersMeta);
      row.appendChild(providersCell);

      const ragCell = document.createElement("td");
      const ragMeta = document.createElement("div");
      ragMeta.className = "log-turn-cell";
      appendTurnText(ragMeta, "retrieved", safeCount(rag.retrieved));
      appendTurnText(ragMeta, "basket", rag.basket == null ? "n/a" : safeCount(rag.basket));
      appendTurnText(ragMeta, "kept", rag.kept == null ? "n/a" : safeCount(rag.kept));
      appendTurnText(ragMeta, "injected", safeCount(rag.injected), safeCount(rag.injected) ? "ok" : "");
      if (rag.legacy_reason_code) appendChip(ragMeta, "legacy", "degraded");
      ragCell.appendChild(ragMeta);
      row.appendChild(ragCell);

      const blocksCell = document.createElement("td");
      const blocksMeta = document.createElement("div");
      blocksMeta.className = "log-turn-cell";
      appendTurnText(blocksMeta, "identity", toText(identity.status) || "missing", identity.status);
      appendTurnText(blocksMeta, "id_chars", safeCount(identity.chars));
      appendTurnText(blocksMeta, "herm", toText(hermeneutic.status) || "missing", hermeneutic.status);
      appendTurnText(blocksMeta, "node_read", nodeState.read_valid ? "ok" : "miss", nodeState.read_valid ? "ok" : "degraded");
      appendTurnText(blocksMeta, "node_write", nodeState.write_succeeded ? "ok" : "skip", nodeState.write_succeeded ? "ok" : "skipped");
      blocksCell.appendChild(blocksMeta);
      row.appendChild(blocksCell);

      const webCell = document.createElement("td");
      const webMeta = document.createElement("div");
      webMeta.className = "log-turn-cell";
      appendTurnText(webMeta, "web", toText(web.status) || "n/a", web.status);
      appendTurnText(webMeta, "requested", web.requested ? "yes" : "no");
      appendTurnText(webMeta, "errors", safeCount(errors.error_count), safeCount(errors.error_count) ? "error" : "");
      appendTurnText(webMeta, "fallbacks", safeCount(errors.fallback_count), safeCount(errors.fallback_count) ? "degraded" : "");
      webCell.appendChild(webMeta);
      row.appendChild(webCell);

      const latestCell = document.createElement("td");
      latestCell.textContent = toText(item?.latest_ts) || "n/a";
      row.appendChild(latestCell);

      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    elements.turns.appendChild(table);
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

  const loadMetadata = async ({ conversationId, turnId, preserveTurnSelection = false } = {}) => {
    const requestedConversationId = toText(
      conversationId == null ? elements.conversationId.value : conversationId
    );
    const requestedTurnId = turnId != null
      ? toText(turnId)
      : (preserveTurnSelection ? toText(elements.turnId.value) : "");
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

  const loadCockpitMetrics = async () => {
    try {
      const response = await adminApi.fetchAdmin(`${LOG_METRICS_ENDPOINT}?${buildMetricsQuery()}`);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        elements.cockpitSourceChip.textContent = "metrics indisponibles";
        elements.cockpitSourceChip.dataset.status = "error";
        renderCockpitEmpty(adminApi.errorMessage(data, `Echec metrics (${response.status}).`), "error");
        return;
      }
      renderCockpit(data);
    } catch (error) {
      elements.cockpitSourceChip.textContent = "metrics erreur";
      elements.cockpitSourceChip.dataset.status = "error";
      renderCockpitEmpty(`Erreur metrics: ${error?.message || error}`, "error");
    }
  };

  const loadTurnPipeline = async () => {
    const filters = readFilters();
    try {
      const response = await adminApi.fetchAdmin(`${LOG_TURNS_ENDPOINT}?${buildTurnsQuery(filters)}`);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        elements.turnCountChip.textContent = "0 tour";
        elements.turnSourceChip.textContent = "turns indisponibles";
        elements.turnSourceChip.dataset.status = "error";
        renderTurnsEmpty(adminApi.errorMessage(data, `Echec tours (${response.status}).`));
        return;
      }
      const items = Array.isArray(data.items) ? data.items : [];
      elements.turnCountChip.textContent = `${Number(data.count) || items.length} tour${items.length > 1 ? "s" : ""} / ${Number(data.total) || items.length}`;
      elements.turnSourceChip.textContent = data?.source?.turns_truncated ? "fenetre tronquee" : "read-model";
      elements.turnSourceChip.dataset.status = data?.source?.turns_truncated ? "degraded" : "ok";
      renderTurnRows(items);
    } catch (error) {
      elements.turnCountChip.textContent = "0 tour";
      elements.turnSourceChip.textContent = "turns erreur";
      elements.turnSourceChip.dataset.status = "error";
      renderTurnsEmpty(`Erreur tours: ${error?.message || error}`);
    }
  };

  const loadCockpit = async () => {
    await Promise.all([loadCockpitMetrics(), loadTurnPipeline()]);
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
      await Promise.all([loadCockpit(), loadLogs()]);
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
    void loadCockpit();
    void loadLogs();
  });

  elements.refresh.addEventListener("click", async () => {
    await loadMetadata({ preserveTurnSelection: true });
    await Promise.all([loadCockpit(), loadLogs()]);
  });

  elements.conversationId.addEventListener("change", async () => {
    elements.turnId.value = "";
    elements.offset.value = "0";
    await loadMetadata({
      conversationId: elements.conversationId.value,
      preserveTurnSelection: false,
    });
    await Promise.all([loadCockpit(), loadLogs()]);
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
    await Promise.all([loadCockpit(), loadLogs()]);
  });

  elements.prevPage.addEventListener("click", () => {
    const limit = toBoundedInt(elements.limit.value, 100, 1, 500);
    const currentOffset = toBoundedInt(elements.offset.value, 0, 0, 1000000);
    elements.offset.value = String(Math.max(0, currentOffset - limit));
    void loadCockpit();
    void loadLogs();
  });

  elements.nextPage.addEventListener("click", () => {
    if (state.nextOffset == null) return;
    elements.offset.value = String(state.nextOffset);
    void loadCockpit();
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
    const initialFilters = applyInitialFiltersFromLocation();
    await loadMetadata({
      conversationId: initialFilters.conversation_id,
      turnId: initialFilters.turn_id,
      preserveTurnSelection: true,
    });
    await Promise.all([loadCockpit(), loadLogs()]);
  })();
})();
