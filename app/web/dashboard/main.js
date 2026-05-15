(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before dashboard/main.js");
  }

  const DASHBOARD_OVERVIEW_ENDPOINT = "/api/admin/dashboard/overview";
  const DASHBOARD_CONVERSATIONS_ENDPOINT = "/api/admin/dashboard/conversations";
  const CONVERSATION_LIMIT = 12;
  const TURN_LIMIT = 20;

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
    trendCards: document.getElementById("dashboardTrendCards"),
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
    drilldown: document.getElementById("dashboardDrilldown"),
    drilldownStatus: document.getElementById("dashboardDrilldownStatus"),
    drilldownEmpty: document.getElementById("dashboardDrilldownEmpty"),
    drilldownBody: document.getElementById("dashboardDrilldownBody"),
    selectedConversation: document.getElementById("dashboardSelectedConversation"),
    turnsCount: document.getElementById("dashboardTurnsCount"),
    turnsList: document.getElementById("dashboardTurnsList"),
    inspectionStatus: document.getElementById("dashboardInspectionStatus"),
    inspectionEmpty: document.getElementById("dashboardInspectionEmpty"),
    inspectionBody: document.getElementById("dashboardInspectionBody"),
  };

  const state = {
    window: "24h",
    lastOverview: null,
    lastConversations: null,
    lastTurns: [],
    selectedConversation: null,
    selectedTurn: null,
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

  const formatBucketLabel = (value) => {
    const text = toText(value);
    if (!text) return "periode inconnue";
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return "periode inconnue";
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
    }).format(date);
  };

  const formatTrendCount = (value, singular, plural = `${singular}s`) => {
    return formatCount(value, singular, plural);
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

  const fetchConversationTurns = async (conversationId) => {
    const query = buildQuery();
    query.set("limit", String(TURN_LIMIT));
    query.set("offset", "0");
    const url = `${DASHBOARD_CONVERSATIONS_ENDPOINT}/${encodeURIComponent(conversationId)}/turns?${query.toString()}`;
    const response = await adminApi.fetchAdmin(url);
    return readJson(response, "Lecture des tours impossible.");
  };

  const fetchTurnInspection = async ({ conversationId, turnId }) => {
    const query = buildQuery();
    query.set("conversation_id", conversationId);
    const url = `/api/admin/dashboard/turns/${encodeURIComponent(turnId)}/inspection?${query.toString()}`;
    const response = await adminApi.fetchAdmin(url);
    return readJson(response, "Lecture du tour impossible.");
  };

  const fetchTurnContent = async ({ conversationId, turnId }) => {
    const query = buildQuery();
    query.set("conversation_id", conversationId);
    const url = `/api/admin/dashboard/turns/${encodeURIComponent(turnId)}/content?${query.toString()}`;
    const response = await adminApi.fetchAdmin(url);
    return readJson(response, "Ouverture du contenu complet impossible.");
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

  const overviewBuckets = (overview, moduleKey) => {
    const buckets = Array.isArray(overview.metric_buckets) ? overview.metric_buckets : [];
    return buckets
      .filter((bucket) => toText(bucket.module_key) === moduleKey)
      .sort((left, right) => toText(left.bucket_start).localeCompare(toText(right.bucket_start)));
  };

  const latencySummary = (overview) => {
    const latency = mapping(overview.latency);
    if (latency.main_duration_ms_avg != null || latency.main_duration_ms_count != null) {
      return latency;
    }
    let total = 0;
    let count = 0;
    overviewBuckets(overview, "providers").forEach((bucket) => {
      const metrics = mapping(bucket.metrics);
      total += toInt(metrics.main_duration_ms_total);
      count += toInt(metrics.main_duration_ms_count);
    });
    return {
      source_kind: "dashboard_metric_buckets.providers",
      main_duration_ms_avg: count ? Math.round(total / count) : null,
      main_duration_ms_count: count,
      semantics_fr: "Moyenne calculee depuis total/count des buckets providers.",
    };
  };

  const seriesFromBuckets = (overview, moduleKey, valueFn) => {
    return overviewBuckets(overview, moduleKey)
      .map((bucket) => {
        const metrics = mapping(bucket.metrics);
        return {
          label: formatBucketLabel(bucket.bucket_start),
          value: Math.max(0, toInt(valueFn(metrics, bucket))),
        };
      })
      .filter((point) => Number.isFinite(point.value));
  };

  const sparkline = (series, title) => {
    if (!series.length) {
      const empty = document.createElement("p");
      empty.className = "dashboard-empty-inline";
      empty.textContent = "Aucune donnee materialisee pour cette courbe.";
      return empty;
    }

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "dashboard-sparkline");
    svg.setAttribute("viewBox", "0 0 100 36");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", title);

    const values = series.map((point) => point.value);
    const max = Math.max(...values, 1);
    const points = values.map((value, index) => {
      const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
      const y = 32 - (value / max) * 28;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    });

    const baseline = document.createElementNS("http://www.w3.org/2000/svg", "line");
    baseline.setAttribute("x1", "0");
    baseline.setAttribute("x2", "100");
    baseline.setAttribute("y1", "32");
    baseline.setAttribute("y2", "32");
    baseline.setAttribute("class", "dashboard-sparkline-baseline");
    svg.appendChild(baseline);

    const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    polyline.setAttribute("points", points.join(" "));
    polyline.setAttribute("class", "dashboard-sparkline-line");
    svg.appendChild(polyline);
    return svg;
  };

  const trendSummary = (items) => {
    const dl = document.createElement("dl");
    dl.className = "dashboard-trend-summary";
    items.forEach(({ label, value }) => {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      dl.append(dt, dd);
    });
    return dl;
  };

  const trendCard = ({ title, note, series, summary }) => {
    const card = document.createElement("article");
    card.className = "dashboard-trend-card";
    const heading = document.createElement("div");
    heading.className = "dashboard-trend-head";
    const titleNode = document.createElement("h4");
    titleNode.textContent = title;
    const noteNode = document.createElement("p");
    noteNode.textContent = note;
    heading.append(titleNode, noteNode);
    card.append(heading, sparkline(series, title), trendSummary(summary));
    return card;
  };

  const renderTrends = (overview) => {
    clearNode(elements.trendCards);
    const pipelineSeries = seriesFromBuckets(overview, "pipeline", (metrics) => {
      const counts = mapping(metrics.classification_counts);
      return toInt(counts.degraded) + toInt(counts.partial) + toInt(counts.legacy_incomplete);
    });
    const memorySeries = seriesFromBuckets(overview, "memory", (metrics) => metrics.injected_total);
    const webSeries = seriesFromBuckets(overview, "web", (metrics) => metrics.injected_turns);
    const latencySeries = seriesFromBuckets(overview, "providers", (metrics) => {
      const count = toInt(metrics.main_duration_ms_count);
      return count ? Math.round(toInt(metrics.main_duration_ms_total) / count) : 0;
    });
    const latency = latencySummary(overview);

    const sumValues = (series) => series.reduce((acc, point) => acc + toInt(point.value), 0);
    const maxValue = (series) => (series.length ? Math.max(...series.map((point) => toInt(point.value))) : 0);
    const latestValue = (series) => (series.length ? toInt(series.at(-1).value) : 0);

    elements.trendCards.append(
      trendCard({
        title: "Reponses a surveiller",
        note: "Tours degrades, partiels ou historiques incomplets.",
        series: pipelineSeries,
        summary: [
          { label: "Total", value: formatTrendCount(sumValues(pipelineSeries), "tour") },
          { label: "Dernier point", value: formatTrendCount(latestValue(pipelineSeries), "tour") },
          { label: "Pic", value: formatTrendCount(maxValue(pipelineSeries), "tour") },
        ],
      }),
      trendCard({
        title: "Memoire injectee",
        note: "Elements memoire injectes par periode materialisee.",
        series: memorySeries,
        summary: [
          { label: "Total", value: formatTrendCount(sumValues(memorySeries), "element") },
          { label: "Dernier point", value: formatTrendCount(latestValue(memorySeries), "element") },
          { label: "Pic", value: formatTrendCount(maxValue(memorySeries), "element") },
        ],
      }),
      trendCard({
        title: "Web utile",
        note: "Tours avec contenu web injecte.",
        series: webSeries,
        summary: [
          { label: "Total", value: formatTrendCount(sumValues(webSeries), "tour") },
          { label: "Dernier point", value: formatTrendCount(latestValue(webSeries), "tour") },
          { label: "Pic", value: formatTrendCount(maxValue(webSeries), "tour") },
        ],
      }),
      trendCard({
        title: "Latence moyenne",
        note: "Moyenne par periode, depuis les buckets providers.",
        series: latencySeries,
        summary: [
          { label: "Fenetre", value: formatMs(latency.main_duration_ms_avg) },
          { label: "Appels", value: formatTrendCount(latency.main_duration_ms_count, "appel") },
          { label: "Pic moyenne", value: formatMs(maxValue(latencySeries)) },
        ],
      }),
    );
  };

  const renderMetricCards = (overview) => {
    const pulse = mapping(overview.pulse);
    const modules = mapping(overview.module_totals);
    const web = mapping(mapping(modules.web).metrics);
    const classification = mapping(pulse.classification_counts);
    const successful = toInt(classification.complete);
    const degraded = toInt(classification.degraded) + toInt(classification.partial);
    const problems = toInt(pulse.problems_count);
    const latency = latencySummary(overview);
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
        label: "Latence moyenne",
        value: formatMs(latency.main_duration_ms_avg),
        note: `${formatCount(latency.main_duration_ms_count, "appel")} mesure depuis les buckets.`,
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
    const latency = latencySummary(overview);

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

    elements.latencyChip.textContent = latency.main_duration_ms_avg ? `moy. ${formatMs(latency.main_duration_ms_avg)}` : "Non mesure";
    elements.latencyCards.replaceChildren(
      metricCard({
        label: "Moyenne fenetre",
        value: formatMs(latency.main_duration_ms_avg),
        note: "Total/count des buckets providers.",
      }),
      metricCard({
        label: "Pic p95 bucket",
        value: formatMs(latency.bucket_p95_ms_max),
        note: "Maximum des p95 par periode, pas p95 global.",
      }),
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

  const statusBadge = (label, status = "") => {
    const badge = document.createElement("span");
    badge.className = "admin-chip";
    if (status) badge.dataset.status = status;
    badge.textContent = label;
    return badge;
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
      const inspectButton = document.createElement("button");
      inspectButton.className = "admin-btn admin-btn-secondary dashboard-small-action dashboard-conversation-open";
      inspectButton.type = "button";
      inspectButton.dataset.conversationId = toText(item.conversation_id);
      inspectButton.textContent = "Ouvrir";
      labelTd.append(label, note, inspectButton);

      const stateInfo = conversationState(item);
      const stateTd = cell("");
      stateTd.appendChild(statusBadge(stateInfo.label, stateInfo.status));

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

  const resetDrilldown = () => {
    state.selectedConversation = null;
    state.selectedTurn = null;
    state.lastTurns = [];
    if (elements.drilldownStatus) elements.drilldownStatus.textContent = "Aucune selection";
    if (elements.drilldownEmpty) {
      elements.drilldownEmpty.hidden = false;
      elements.drilldownEmpty.textContent = "Selectionnez une conversation pour voir ses tours recents, puis ouvrez un tour pour lire son recit traduit.";
    }
    if (elements.drilldownBody) elements.drilldownBody.hidden = true;
    clearNode(elements.turnsList);
    clearNode(elements.inspectionBody);
    if (elements.turnsCount) elements.turnsCount.textContent = "0 tour";
    if (elements.selectedConversation) elements.selectedConversation.textContent = "";
    if (elements.inspectionStatus) elements.inspectionStatus.textContent = "Aucun tour";
    if (elements.inspectionEmpty) {
      elements.inspectionEmpty.hidden = false;
      elements.inspectionEmpty.textContent = "Selectionnez un tour pour lire ce qui est prouve, resume ou non reconstructible.";
    }
    if (elements.inspectionBody) elements.inspectionBody.hidden = true;
  };

  const selectedConversationLabel = (conversationId) => {
    const items = Array.isArray(state.lastConversations?.items) ? state.lastConversations.items : [];
    const item = items.find((candidate) => toText(candidate.conversation_id) === conversationId);
    return item ? conversationLabel(item) : "Conversation selectionnee";
  };

  const turnState = (item) => {
    const classification = toText(item.classification);
    if (classification === "complete") return { label: "Stable", status: "present" };
    if (classification === "degraded" || classification === "partial") return { label: "A inspecter", status: "degraded" };
    if (classification === "legacy_incomplete") return { label: "Historique partiel", status: "missing" };
    return { label: "A verifier", status: "missing" };
  };

  const turnTitle = (item) => {
    const ts = toText(item.latest_ts) || toText(item.first_ts);
    return ts ? `Tour du ${formatDateTime(ts)}` : "Tour sans date";
  };

  const renderTurns = (payload) => {
    const items = Array.isArray(payload.items) ? payload.items : [];
    state.lastTurns = items;
    elements.turnsCount.textContent = formatCount(payload.total ?? items.length, "tour");
    clearNode(elements.turnsList);
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "dashboard-empty-inline";
      empty.textContent = "Aucun tour observe dans cette conversation sur la periode choisie.";
      elements.turnsList.appendChild(empty);
      return;
    }

    const fragment = document.createDocumentFragment();
    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "dashboard-turn-button";
      button.dataset.turnId = toText(item.turn_id);
      button.dataset.conversationId = toText(item.conversation_id);
      if (state.selectedTurn === button.dataset.turnId) button.dataset.selected = "true";

      const head = document.createElement("span");
      head.className = "dashboard-turn-head";
      const title = document.createElement("strong");
      title.textContent = turnTitle(item);
      const info = turnState(item);
      head.append(title, statusBadge(info.label, info.status));

      const details = document.createElement("span");
      details.className = "dashboard-turn-details";
      const rag = mapping(item.rag);
      const web = mapping(item.web);
      const errors = mapping(item.errors);
      details.textContent = [
        `${formatCount(item.source_event_count, "event")}`,
        `memoire injectee ${toInt(rag.injected)}`,
        `web ${web.injected ? "injecte" : "non injecte"}`,
        `${toInt(errors.error_count) + toInt(errors.fallback_count)} probleme(s)`,
      ].join(" · ");

      button.append(head, details);
      fragment.appendChild(button);
    });
    elements.turnsList.appendChild(fragment);
  };

  const appendParagraphList = (container, items) => {
    const list = document.createElement("ul");
    list.className = "dashboard-story-list";
    items.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = toText(item);
      list.appendChild(li);
    });
    container.appendChild(list);
  };

  const contentStatusLabel = (status) => {
    const labels = {
      exact_available: "Contenu exact disponible",
      partial_available: "Contenu partiel disponible",
      fingerprint_only: "Empreinte seule disponible",
      not_reconstructible: "Non reconstructible",
      blocked_sensitive: "Bloque par garde secret",
    };
    return labels[toText(status)] || "A verifier";
  };

  const renderContentEvidence = (container, evidence) => {
    const entries = Object.entries(mapping(evidence));
    if (!entries.length) return;
    const list = document.createElement("dl");
    list.className = "dashboard-content-evidence";
    entries.slice(0, 8).forEach(([key, value]) => {
      const dt = document.createElement("dt");
      dt.textContent = key;
      const dd = document.createElement("dd");
      dd.textContent = typeof value === "object" ? JSON.stringify(value) : toText(value);
      list.append(dt, dd);
    });
    container.appendChild(list);
  };

  const renderContentGatePayload = (target, payload) => {
    clearNode(target);
    const availability = mapping(payload.availability);
    const summary = document.createElement("p");
    summary.className = "dashboard-inspection-summary";
    summary.textContent = `${contentStatusLabel(availability.status)}. ${
      toText(availability.warning_fr) || "Contenu charge uniquement apres action explicite."
    }`;
    target.appendChild(summary);

    if (mapping(payload.audit).attempted) {
      const audit = document.createElement("p");
      audit.className = "dashboard-muted";
      audit.textContent = mapping(payload.audit).stored
        ? "Action auditee par un evenement compact, sans contenu brut."
        : "Audit compact tente; stockage non confirme.";
      target.appendChild(audit);
    }

    const items = Array.isArray(payload.items) ? payload.items : [];
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "dashboard-empty-inline";
      empty.textContent = "Aucune source de contenu complet n est disponible pour ce tour.";
      target.appendChild(empty);
      return;
    }

    const list = document.createElement("div");
    list.className = "dashboard-content-items";
    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "dashboard-content-item";
      card.dataset.status = toText(item.status);
      const heading = document.createElement("h6");
      heading.textContent = toText(item.label_fr) || "Source";
      const status = document.createElement("span");
      status.className = "admin-chip";
      status.textContent = toText(item.status_fr) || contentStatusLabel(item.status);
      const explanation = document.createElement("p");
      explanation.textContent = toText(item.explanation_fr) || "Disponibilite a verifier.";
      card.append(heading, status, explanation);

      if (item.content_text) {
        const details = document.createElement("details");
        details.className = "dashboard-content-details";
        const summaryNode = document.createElement("summary");
        summaryNode.textContent = "Ouvrir ce contenu";
        const pre = document.createElement("pre");
        pre.textContent = toText(item.content_text);
        details.append(summaryNode, pre);
        card.appendChild(details);
      } else {
        renderContentEvidence(card, mapping(item.source).evidence);
      }

      const meta = document.createElement("p");
      meta.className = "dashboard-muted";
      const chars = item.content_chars == null ? "taille non disponible" : `${toInt(item.content_chars)} caracteres`;
      const hash = toText(item.content_sha256_12);
      meta.textContent = hash ? `${chars}; hash ${hash}.` : chars;
      card.appendChild(meta);
      list.appendChild(card);
    });
    target.appendChild(list);
  };

  const renderContentGate = (payload, container) => {
    const gate = mapping(payload.content_gate);
    if (gate.action_available !== true) return;

    const block = document.createElement("article");
    block.className = "dashboard-story-section dashboard-content-gate";
    const heading = document.createElement("h5");
    heading.textContent = "Contenu complet volontaire";
    const warning = document.createElement("p");
    warning.className = "dashboard-warning-text";
    warning.textContent =
      toText(gate.warning_fr) ||
      "Action volontaire: peut afficher du contenu brut si un artefact exact existe. Aucun contenu n est precharge.";
    const button = document.createElement("button");
    button.className = "admin-btn admin-btn-secondary dashboard-content-action";
    button.type = "button";
    button.textContent = toText(gate.action_label_fr) || "Afficher le contenu complet";
    const body = document.createElement("div");
    body.className = "dashboard-content-body";
    body.hidden = true;

    button.addEventListener("click", async () => {
      const item = mapping(payload.item);
      const conversationId = toText(payload.conversation_id) || toText(item.conversation_id);
      const turnId = toText(payload.turn_id) || toText(item.turn_id);
      if (!conversationId || !turnId) return;
      button.disabled = true;
      body.hidden = false;
      body.textContent = "Ouverture volontaire en cours...";
      try {
        const contentPayload = await fetchTurnContent({ conversationId, turnId });
        renderContentGatePayload(body, contentPayload);
      } catch (error) {
        body.textContent = error instanceof Error ? error.message : "Contenu complet indisponible.";
      } finally {
        button.disabled = false;
      }
    });

    block.append(heading, warning, button, body);
    container.appendChild(block);
  };

  const renderStory = (payload) => {
    clearNode(elements.inspectionBody);
    const story = mapping(payload.story);
    const item = mapping(payload.item);
    const title = document.createElement("h4");
    title.textContent = story.title_fr || turnTitle(item);
    const summary = document.createElement("p");
    summary.className = "dashboard-inspection-summary";
    summary.textContent = story.summary_fr || "Inspection traduite disponible depuis les faits compacts.";
    elements.inspectionBody.append(title, summary);
    if (story.content_status_fr) {
      const contentStatus = document.createElement("p");
      contentStatus.className = "dashboard-muted";
      contentStatus.textContent = toText(story.content_status_fr);
      elements.inspectionBody.appendChild(contentStatus);
    }

    const sections = Array.isArray(story.sections) ? story.sections : [];
    sections.forEach((section) => {
      const block = document.createElement("article");
      block.className = "dashboard-story-section";
      const heading = document.createElement("h5");
      heading.textContent = toText(section.label_fr) || "Section";
      block.appendChild(heading);
      appendParagraphList(block, Array.isArray(section.items) ? section.items : []);
      elements.inspectionBody.appendChild(block);
    });

    const modules = Array.isArray(payload.modules) ? payload.modules : [];
    if (modules.length) {
      const modulesBlock = document.createElement("article");
      modulesBlock.className = "dashboard-story-section dashboard-module-grid";
      const heading = document.createElement("h5");
      heading.textContent = "Lecture par module";
      modulesBlock.appendChild(heading);
      const grid = document.createElement("div");
      grid.className = "dashboard-module-cards";
      modules.forEach((module) => {
        const card = document.createElement("section");
        card.className = "dashboard-module-card";
        const name = document.createElement("strong");
        name.textContent = toText(module.label_fr) || "Module";
        const summaryText = document.createElement("p");
        summaryText.textContent = toText(module.summary_fr) || "Aucun resume disponible.";
        card.append(name, summaryText);
        if (module.degradation_fr) {
          const degradation = document.createElement("p");
          degradation.className = "dashboard-warning-text";
          degradation.textContent = toText(module.degradation_fr);
          card.appendChild(degradation);
        }
        const status = document.createElement("span");
        status.className = "dashboard-muted";
        status.textContent = toText(module.content_status_fr) || "Contenu complet non charge dans cette inspection.";
        card.appendChild(status);
        grid.appendChild(card);
      });
      modulesBlock.appendChild(grid);
      elements.inspectionBody.appendChild(modulesBlock);
    }

    const links = Array.isArray(story.debug_links) ? story.debug_links : [];
    if (links.length) {
      const nav = document.createElement("nav");
      nav.className = "dashboard-debug-links";
      nav.setAttribute("aria-label", "Liens de diagnostic");
      links.forEach((link) => {
        const anchor = document.createElement("a");
        anchor.className = "admin-btn admin-btn-secondary admin-btn-link";
        anchor.href = toText(link.href) || "#";
        anchor.textContent = toText(link.label_fr) || "Detail";
        nav.appendChild(anchor);
      });
      elements.inspectionBody.appendChild(nav);
    }

    renderContentGate(payload, elements.inspectionBody);

    elements.inspectionStatus.textContent = "Tour ouvert";
    elements.inspectionEmpty.hidden = true;
    elements.inspectionBody.hidden = false;
  };

  const loadTurnInspection = async ({ conversationId, turnId }) => {
    state.selectedTurn = turnId;
    elements.inspectionStatus.textContent = "Chargement";
    elements.inspectionEmpty.hidden = false;
    elements.inspectionEmpty.textContent = "Lecture du recit traduit...";
    elements.inspectionBody.hidden = true;
    clearNode(elements.inspectionBody);
    renderTurns({ items: state.lastTurns, total: state.lastTurns.length });
    try {
      const payload = await fetchTurnInspection({ conversationId, turnId });
      renderStory(payload);
    } catch (error) {
      elements.inspectionStatus.textContent = "Erreur";
      elements.inspectionEmpty.hidden = false;
      elements.inspectionEmpty.textContent = error instanceof Error ? error.message : "Inspection indisponible.";
    }
  };

  const loadConversation = async (conversationId) => {
    state.selectedConversation = conversationId;
    state.selectedTurn = null;
    elements.drilldownStatus.textContent = "Chargement";
    elements.drilldownEmpty.hidden = true;
    elements.drilldownBody.hidden = false;
    elements.selectedConversation.textContent = selectedConversationLabel(conversationId);
    elements.turnsCount.textContent = "Chargement";
    elements.inspectionStatus.textContent = "Aucun tour";
    elements.inspectionEmpty.hidden = false;
    elements.inspectionEmpty.textContent = "Selectionnez un tour pour lire ce qui est prouve, resume ou non reconstructible.";
    elements.inspectionBody.hidden = true;
    clearNode(elements.turnsList);
    clearNode(elements.inspectionBody);
    try {
      const payload = await fetchConversationTurns(conversationId);
      renderTurns(payload);
      elements.drilldownStatus.textContent = "Conversation ouverte";
    } catch (error) {
      elements.drilldownStatus.textContent = "Erreur";
      elements.turnsCount.textContent = "Erreur";
      const empty = document.createElement("p");
      empty.className = "dashboard-empty-inline";
      empty.textContent = error instanceof Error ? error.message : "Tours indisponibles.";
      elements.turnsList.replaceChildren(empty);
    }
  };

  const renderEmptyOverview = () => {
    elements.pulseCards.replaceChildren(
      metricCard({ label: "Tours reussis", value: "0", note: "Aucune activite observee." }),
      metricCard({ label: "Reponses degradees", value: "0", note: "Aucune activite observee." }),
      metricCard({ label: "Problemes rencontres", value: "0", note: "Aucune activite observee." }),
      metricCard({ label: "Latence moyenne", value: "Non mesure", note: "Aucun appel mesure." }),
      metricCard({ label: "Memoire utilisee", value: "0", note: "Aucun signal memoire." }),
      metricCard({ label: "Recherche web utile", value: "0", note: "Aucun signal web." }),
    );
    renderBars(elements.classificationBars, [], "Aucun tour observe dans cette periode.");
    renderBars(elements.memoryBars, [], "Aucun signal memoire observe.");
    renderBars(elements.webBars, [], "Aucune recherche web observee.");
    elements.latencyCards.replaceChildren(
      metricCard({ label: "Moyenne fenetre", value: "Non mesure", note: "Aucun appel principal." }),
      metricCard({ label: "Pic p95 bucket", value: "Non mesure", note: "Aucun appel principal." }),
    );
    clearNode(elements.trendCards);
    elements.trendCards.append(
      trendCard({
        title: "Reponses a surveiller",
        note: "Tours degrades, partiels ou historiques incomplets.",
        series: [],
        summary: [
          { label: "Total", value: "0 tour" },
          { label: "Dernier point", value: "0 tour" },
          { label: "Pic", value: "0 tour" },
        ],
      }),
    );
  };

  const renderDashboard = ({ overview, conversations }) => {
    state.lastOverview = overview;
    state.lastConversations = conversations;
    renderSource(overview);
    renderMetricCards(overview);
    renderTrends(overview);
    renderSignals(overview);
    renderConversations(conversations);
  };

  const loadDashboard = async () => {
    try {
      resetDrilldown();
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
    elements.conversationsBody?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-conversation-id]");
      if (!button) return;
      const conversationId = toText(button.dataset.conversationId);
      if (conversationId) {
        loadConversation(conversationId);
      }
    });
    elements.turnsList?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-turn-id]");
      if (!button) return;
      const conversationId = toText(button.dataset.conversationId || state.selectedConversation);
      const turnId = toText(button.dataset.turnId);
      if (conversationId && turnId) {
        loadTurnInspection({ conversationId, turnId });
      }
    });
    loadDashboard();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
