(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before dashboard/main.js");
  }

  const DASHBOARD_OVERVIEW_ENDPOINT = "/api/admin/dashboard/overview";
  const DASHBOARD_CONVERSATIONS_ENDPOINT = "/api/admin/dashboard/conversations";
  const CONVERSATION_LIMIT = 12;

  const elements = {
    form: document.getElementById("dashboardWindowForm"),
    primaryWindows: document.getElementById("dashboardPrimaryWindows"),
    secondaryWindow: document.getElementById("dashboardSecondaryWindow"),
    customRange: document.getElementById("dashboardCustomRange"),
    customFrom: document.getElementById("dashboardCustomFrom"),
    customTo: document.getElementById("dashboardCustomTo"),
    refresh: document.getElementById("dashboardRefresh"),
    statusBanner: document.getElementById("dashboardStatusBanner"),
    sourceChip: document.getElementById("dashboardSourceChip"),
    coverageText: document.getElementById("dashboardCoverageText"),
    coverageDetails: document.getElementById("dashboardCoverageDetails"),
    windowChip: document.getElementById("dashboardWindowChip"),
    pulseCards: document.getElementById("dashboardPulseCards"),
    turnsTotal: document.getElementById("dashboardTurnsTotal"),
    classificationBars: document.getElementById("dashboardClassificationBars"),
    memoryTotal: document.getElementById("dashboardMemoryTotal"),
    memoryBars: document.getElementById("dashboardMemoryBars"),
    webTotal: document.getElementById("dashboardWebTotal"),
    webBars: document.getElementById("dashboardWebBars"),
    latencyChip: document.getElementById("dashboardLatencyChip"),
    latencyCards: document.getElementById("dashboardLatencyCards"),
    conversationCount: document.getElementById("dashboardConversationCount"),
    conversationsEmpty: document.getElementById("dashboardConversationsEmpty"),
    conversationsTable: document.getElementById("dashboardConversationsTable"),
    conversationsBody: document.getElementById("dashboardConversationsBody"),
  };

  const state = {
    window: "24h",
    lastOverview: null,
    lastConversations: null,
  };

  const WINDOW_LABELS = Object.freeze({
    "24h": "24 h",
    "7d": "7 j",
    "30d": "30 j",
    "90d": "90 jours",
    today: "Aujourd'hui",
    yesterday: "Hier",
    custom: "Periode personnalisee",
  });

  const CLASSIFICATION_LABELS = Object.freeze({
    complete: "Tours reussis",
    degraded: "Reponses degradees",
    partial: "Tours partiels",
    legacy_incomplete: "Historique incomplet",
  });

  const SOURCE_LABELS = Object.freeze({
    ok: "Periode complete",
    partially_materialized: "Donnees partielles",
    not_materialized: "Donnees absentes",
    degraded: "Lecture degradee",
    empty: "Aucune donnee",
  });

  const toInt = (value) => {
    const parsed = Number.parseInt(String(value ?? ""), 10);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const toText = (value) => String(value == null ? "" : value).trim();

  const mapping = (value) => {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  };

  const formatCount = (value, singular, plural = `${singular}s`) => {
    const count = toInt(value);
    return `${count} ${count === 1 ? singular : plural}`;
  };

  const formatMs = (value) => {
    const amount = toInt(value);
    if (!amount) return "Non mesure";
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)} s`;
    return `${amount} ms`;
  };

  const formatDateTime = (value) => {
    const text = toText(value);
    if (!text) return "Date inconnue";
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return "Date inconnue";
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  const isoFromDatetimeLocal = (value) => {
    const text = toText(value);
    if (!text) return "";
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return "";
    return date.toISOString();
  };

  const setStatusBanner = (message, stateValue = "") => {
    if (!elements.statusBanner) return;
    elements.statusBanner.textContent = message;
    if (stateValue) {
      elements.statusBanner.dataset.state = stateValue;
    } else {
      delete elements.statusBanner.dataset.state;
    }
  };

  const sourceSeverity = (source) => {
    const status = toText(mapping(source).status);
    if (status === "ok") return "ok";
    if (status === "partially_materialized") return "warning";
    if (status === "not_materialized" || status === "degraded") return "error";
    return "warning";
  };

  const humanSourceLabel = (source) => {
    const status = toText(mapping(source).status);
    return SOURCE_LABELS[status] || "Couverture a verifier";
  };

  const buildQuery = () => {
    const query = new URLSearchParams();
    if (state.window === "custom") {
      const tsFrom = isoFromDatetimeLocal(elements.customFrom?.value);
      const tsTo = isoFromDatetimeLocal(elements.customTo?.value);
      if (!tsFrom || !tsTo) {
        throw new Error("Choisir un debut et une fin pour la periode personnalisee.");
      }
      query.set("ts_from", tsFrom);
      query.set("ts_to", tsTo);
      return query;
    }
    query.set("window", state.window);
    return query;
  };

  const readJson = async (response, fallbackMessage) => {
    let payload = {};
    try {
      payload = await adminApi.readJson(response);
    } catch (_error) {
      payload = {};
    }
    if (!response.ok || payload.ok === false) {
      throw new Error(adminApi.errorMessage(payload, fallbackMessage));
    }
    return payload;
  };

  const fetchDashboardPayloads = async () => {
    const query = buildQuery();
    const overviewUrl = `${DASHBOARD_OVERVIEW_ENDPOINT}?${query.toString()}`;
    const conversationsQuery = new URLSearchParams(query);
    conversationsQuery.set("limit", String(CONVERSATION_LIMIT));
    conversationsQuery.set("offset", "0");
    const conversationsUrl = `${DASHBOARD_CONVERSATIONS_ENDPOINT}?${conversationsQuery.toString()}`;

    const [overviewResponse, conversationsResponse] = await Promise.all([
      adminApi.fetchAdmin(overviewUrl),
      adminApi.fetchAdmin(conversationsUrl),
    ]);
    const [overview, conversations] = await Promise.all([
      readJson(overviewResponse, "Lecture du pouls impossible."),
      readJson(conversationsResponse, "Lecture des conversations impossible."),
    ]);
    return { overview, conversations };
  };

  const clearNode = (node) => {
    if (node) node.replaceChildren();
  };

  const metricCard = ({ label, value, note, stateValue = "" }) => {
    const card = document.createElement("article");
    card.className = "dashboard-metric-card";
    if (stateValue) card.dataset.state = stateValue;
    const labelNode = document.createElement("span");
    labelNode.className = "dashboard-metric-label";
    labelNode.textContent = label;
    const valueNode = document.createElement("strong");
    valueNode.textContent = value;
    const noteNode = document.createElement("p");
    noteNode.textContent = note;
    card.append(labelNode, valueNode, noteNode);
    return card;
  };

  const renderMetricCards = (overview) => {
    const pulse = mapping(overview.pulse);
    const modules = mapping(overview.module_totals);
    const providers = mapping(mapping(modules.providers).metrics);
    const web = mapping(mapping(modules.web).metrics);
    const classification = mapping(pulse.classification_counts);
    const successful = toInt(classification.complete);
    const degraded = toInt(classification.degraded) + toInt(classification.partial);
    const problems = toInt(pulse.problems_count);
    const p95 = providers.main_duration_ms_p95;
    const webUseful = toInt(web.injected_turns ?? pulse.web_injected_turns);

    elements.pulseCards.replaceChildren(
      metricCard({
        label: "Tours reussis",
        value: String(successful),
        note: "Reponses completes sur la periode.",
        stateValue: successful ? "good" : "",
      }),
      metricCard({
        label: "Reponses degradees",
        value: String(degraded),
        note: "Tours a lire avec prudence.",
        stateValue: degraded ? "warn" : "good",
      }),
      metricCard({
        label: "Problemes rencontres",
        value: String(problems),
        note: "Erreurs et gardes degradees.",
        stateValue: problems ? "warn" : "good",
      }),
      metricCard({
        label: "Latence p95",
        value: formatMs(p95),
        note: "Modele principal, quand mesure.",
      }),
      metricCard({
        label: "Memoire utilisee",
        value: String(toInt(pulse.memory_injected_total)),
        note: "Elements injectes dans les tours.",
      }),
      metricCard({
        label: "Recherche web utile",
        value: String(webUseful),
        note: "Tours avec contenu web injecte.",
      }),
    );
  };

  const barRow = ({ label, value, total, stateValue = "" }) => {
    const row = document.createElement("div");
    row.className = "dashboard-bar-row";
    if (stateValue) row.dataset.state = stateValue;
    const top = document.createElement("div");
    top.className = "dashboard-bar-top";
    const labelNode = document.createElement("span");
    labelNode.textContent = label;
    const valueNode = document.createElement("strong");
    valueNode.textContent = String(toInt(value));
    top.append(labelNode, valueNode);
    const track = document.createElement("div");
    track.className = "dashboard-bar-track";
    const fill = document.createElement("span");
    fill.style.width = total > 0 ? `${Math.max(3, Math.round((toInt(value) / total) * 100))}%` : "0%";
    track.appendChild(fill);
    row.append(top, track);
    return row;
  };

  const renderBars = (target, rows, emptyMessage) => {
    clearNode(target);
    const total = rows.reduce((acc, row) => acc + toInt(row.value), 0);
    if (!total) {
      const empty = document.createElement("p");
      empty.className = "dashboard-empty-inline";
      empty.textContent = emptyMessage;
      target.appendChild(empty);
      return;
    }
    rows.forEach((row) => {
      target.appendChild(barRow({ ...row, total }));
    });
  };

  const renderSignals = (overview) => {
    const pulse = mapping(overview.pulse);
    const modules = mapping(overview.module_totals);
    const classification = mapping(pulse.classification_counts);
    const memory = mapping(mapping(modules.memory).metrics);
    const web = mapping(mapping(modules.web).metrics);
    const providers = mapping(mapping(modules.providers).metrics);

    elements.turnsTotal.textContent = formatCount(pulse.turns_observed, "tour");
    renderBars(
      elements.classificationBars,
      [
        { label: CLASSIFICATION_LABELS.complete, value: classification.complete, stateValue: "good" },
        { label: CLASSIFICATION_LABELS.degraded, value: classification.degraded, stateValue: "warn" },
        { label: CLASSIFICATION_LABELS.partial, value: classification.partial, stateValue: "warn" },
        { label: CLASSIFICATION_LABELS.legacy_incomplete, value: classification.legacy_incomplete },
      ],
      "Aucun tour observe dans cette periode.",
    );

    elements.memoryTotal.textContent = formatCount(memory.injected_total, "element");
    renderBars(
      elements.memoryBars,
      [
        { label: "Trouves", value: memory.retrieved_total },
        { label: "Gardes", value: memory.kept_total },
        { label: "Injectes", value: memory.injected_total, stateValue: "good" },
      ],
      "Aucun signal memoire observe.",
    );

    elements.webTotal.textContent = formatCount(web.requested_turns, "demande");
    renderBars(
      elements.webBars,
      [
        { label: "Demande", value: web.requested_turns },
        { label: "Reussie", value: web.success_turns, stateValue: "good" },
        { label: "Injectee", value: web.injected_turns, stateValue: "good" },
        { label: "En erreur", value: web.error_turns, stateValue: "warn" },
      ],
      "Aucune recherche web observee.",
    );

    const p50 = providers.main_duration_ms_p50;
    const p95 = providers.main_duration_ms_p95;
    elements.latencyChip.textContent = p95 ? `p95 ${formatMs(p95)}` : "Non mesure";
    elements.latencyCards.replaceChildren(
      metricCard({ label: "p50", value: formatMs(p50), note: "Milieu des appels principaux." }),
      metricCard({ label: "p95", value: formatMs(p95), note: "Appels principaux les plus lents." }),
    );
  };

  const renderSource = (overview) => {
    const source = mapping(overview.source);
    const coverage = mapping(source.coverage);
    const windowPayload = mapping(overview.window);
    const severity = sourceSeverity(source);
    const label = humanSourceLabel(source);
    elements.sourceChip.textContent = label;
    elements.sourceChip.dataset.status = severity === "ok" ? "present" : "degraded";
    elements.coverageText.textContent =
      severity === "ok"
        ? `${WINDOW_LABELS[windowPayload.key] || "Periode"} couverte par les agregats persistants.`
        : `${label}: les chiffres doivent etre lus avec prudence.`;
    const materializedStart = formatDateTime(coverage.materialized_window_start);
    const materializedEnd = formatDateTime(coverage.materialized_window_end);
    elements.coverageDetails.textContent =
      coverage.status === "absent"
        ? "Aucune materialisation couvrante n'est disponible pour cette periode."
        : `Periode materialisee: ${materializedStart} -> ${materializedEnd}.`;
    elements.windowChip.textContent = windowPayload.label_fr || WINDOW_LABELS[state.window] || "Periode";
    setStatusBanner(
      severity === "ok" ? "Lecture a jour depuis les agregats persistants." : elements.coverageText.textContent,
      severity,
    );
  };

  const conversationLabel = (item) => {
    const rawLabel = toText(item.display_label);
    const rawId = toText(item.conversation_id);
    if (rawLabel && rawLabel !== rawId && !rawLabel.startsWith("conv-")) {
      return rawLabel;
    }
    const latest = toText(item.latest_ts) || toText(item.first_ts);
    if (latest) return `Conversation du ${formatDateTime(latest)}`;
    return "Conversation sans date";
  };

  const conversationState = (item) => {
    const counts = mapping(item.classification_counts);
    const problems = toInt(item.error_count) + toInt(item.fallback_count);
    if (problems || toInt(counts.degraded) || toInt(counts.partial)) {
      return { label: "A inspecter", status: "degraded" };
    }
    if (toInt(counts.complete)) {
      return { label: "Stable", status: "present" };
    }
    if (toInt(counts.legacy_incomplete)) {
      return { label: "Historique partiel", status: "missing" };
    }
    return { label: "Aucune activite", status: "missing" };
  };

  const cell = (text, className = "") => {
    const td = document.createElement("td");
    if (className) td.className = className;
    td.textContent = text;
    return td;
  };

  const renderConversations = (payload) => {
    const items = Array.isArray(payload.items) ? payload.items : [];
    elements.conversationCount.textContent = formatCount(payload.total ?? items.length, "conversation");
    elements.conversationsBody.replaceChildren();
    elements.conversationsEmpty.hidden = Boolean(items.length);
    elements.conversationsTable.hidden = !items.length;
    if (!items.length) return;

    const fragment = document.createDocumentFragment();
    items.forEach((item) => {
      const row = document.createElement("tr");
      const labelTd = cell("");
      const label = document.createElement("strong");
      label.textContent = conversationLabel(item);
      const note = document.createElement("span");
      note.className = "dashboard-muted";
      note.textContent = toText(item.latest_ts) ? `Derniere activite ${formatDateTime(item.latest_ts)}` : "Activite datee indisponible";
      labelTd.append(label, note);

      const stateInfo = conversationState(item);
      const stateTd = cell("");
      const badge = document.createElement("span");
      badge.className = "admin-chip";
      badge.dataset.status = stateInfo.status;
      badge.textContent = stateInfo.label;
      stateTd.appendChild(badge);

      const problems = toInt(item.error_count) + toInt(item.fallback_count);
      row.append(
        labelTd,
        stateTd,
        cell(String(toInt(item.turns_count)), "dashboard-number-cell"),
        cell(String(toInt(item.memory_used_turns)), "dashboard-number-cell"),
        cell(`${toInt(item.web_injected_turns)} / ${toInt(item.web_requested_turns)}`, "dashboard-number-cell"),
        cell(String(problems), "dashboard-number-cell"),
        cell(formatDateTime(item.latest_ts)),
      );
      fragment.appendChild(row);
    });
    elements.conversationsBody.appendChild(fragment);
  };

  const renderEmptyOverview = () => {
    elements.pulseCards.replaceChildren(
      metricCard({ label: "Tours reussis", value: "0", note: "Aucune activite observee." }),
      metricCard({ label: "Reponses degradees", value: "0", note: "Aucune activite observee." }),
      metricCard({ label: "Problemes rencontres", value: "0", note: "Aucune activite observee." }),
      metricCard({ label: "Latence p95", value: "Non mesure", note: "Aucun appel mesure." }),
      metricCard({ label: "Memoire utilisee", value: "0", note: "Aucun signal memoire." }),
      metricCard({ label: "Recherche web utile", value: "0", note: "Aucun signal web." }),
    );
    renderBars(elements.classificationBars, [], "Aucun tour observe dans cette periode.");
    renderBars(elements.memoryBars, [], "Aucun signal memoire observe.");
    renderBars(elements.webBars, [], "Aucune recherche web observee.");
    elements.latencyCards.replaceChildren(
      metricCard({ label: "p50", value: "Non mesure", note: "Aucun appel principal." }),
      metricCard({ label: "p95", value: "Non mesure", note: "Aucun appel principal." }),
    );
  };

  const renderDashboard = ({ overview, conversations }) => {
    state.lastOverview = overview;
    state.lastConversations = conversations;
    renderSource(overview);
    renderMetricCards(overview);
    renderSignals(overview);
    renderConversations(conversations);
  };

  const loadDashboard = async () => {
    try {
      setStatusBanner("Chargement des agregats persistants...", "");
      const payloads = await fetchDashboardPayloads();
      renderDashboard(payloads);
    } catch (error) {
      renderEmptyOverview();
      renderConversations({ items: [], total: 0 });
      elements.sourceChip.textContent = "Lecture impossible";
      elements.sourceChip.dataset.status = "failed";
      elements.coverageText.textContent = error instanceof Error ? error.message : "Lecture impossible.";
      elements.coverageDetails.textContent = "Aucune donnee brute n'a ete chargee.";
      setStatusBanner(elements.coverageText.textContent, "error");
    }
  };

  const syncWindowControls = () => {
    elements.primaryWindows?.querySelectorAll("[data-window]").forEach((button) => {
      const active = button.dataset.window === state.window;
      button.classList.toggle("admin-btn-primary", active);
      button.classList.toggle("admin-btn-secondary", !active);
      if (active) {
        button.setAttribute("aria-pressed", "true");
      } else {
        button.setAttribute("aria-pressed", "false");
      }
    });
    if (elements.secondaryWindow && ["today", "yesterday", "90d", "custom"].includes(state.window)) {
      elements.secondaryWindow.value = state.window;
    } else if (elements.secondaryWindow) {
      elements.secondaryWindow.value = "";
    }
    if (elements.customRange) {
      elements.customRange.hidden = state.window !== "custom";
    }
  };

  const boot = () => {
    syncWindowControls();
    elements.primaryWindows?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-window]");
      if (!button) return;
      state.window = button.dataset.window || "24h";
      syncWindowControls();
      loadDashboard();
    });
    elements.secondaryWindow?.addEventListener("change", () => {
      const selected = toText(elements.secondaryWindow.value);
      if (!selected) return;
      state.window = selected;
      syncWindowControls();
      if (selected !== "custom") {
        loadDashboard();
      }
    });
    elements.form?.addEventListener("submit", (event) => {
      event.preventDefault();
      loadDashboard();
    });
    loadDashboard();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
