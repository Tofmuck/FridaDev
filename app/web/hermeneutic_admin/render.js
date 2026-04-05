(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error("admin_ui_common.js must be loaded before hermeneutic_admin/render.js");
  }

  const STAGE_ORDER = [
    "stimmung_agent",
    "hermeneutic_node_insertion",
    "primary_node",
    "validation_agent",
  ];

  const STAGE_LABELS = Object.freeze({
    stimmung_agent: "stimmung_agent",
    hermeneutic_node_insertion: "hermeneutic_node_insertion",
    primary_node: "primary_node",
    validation_agent: "validation_agent",
  });

  const toText = (value) => String(value == null ? "" : value).trim();

  const humanLabel = (raw) => {
    const normalized = toText(raw);
    if (!normalized) return "Champ";
    return normalized
      .split("_")
      .filter(Boolean)
      .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
      .join(" ");
  };

  const compactJson = (value, maxLength = 1200) => {
    if (value == null) return "";
    if (typeof value === "string") {
      const cleaned = value.trim();
      return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength - 3)}...` : cleaned;
    }
    const serialized = JSON.stringify(value, null, 2);
    if (serialized.length > maxLength) {
      return `${serialized.slice(0, maxLength - 3)}...`;
    }
    return serialized;
  };

  const compactValue = (value) => {
    if (value == null) return "";
    if (typeof value === "string") return compactJson(value, 800);
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    return compactJson(value, 1200);
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

  const renderEmpty = (target, message) => {
    if (!target) return;
    target.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    target.appendChild(empty);
  };

  const setStatusBanner = (element, message, state = "") => {
    if (!element) return;
    element.textContent = message;
    if (state) {
      element.dataset.state = state;
      return;
    }
    delete element.dataset.state;
  };

  const renderReadonlyEntries = (target, entries) => {
    adminUi.renderReadonlyInfoEntries(target, entries);
  };

  const mappingToEntries = (mapping, source = "read_only") => {
    const data = mapping && typeof mapping === "object" && !Array.isArray(mapping) ? mapping : {};
    return Object.keys(data)
      .sort()
      .map((key) => [
        key,
        {
          label: humanLabel(key),
          value: compactValue(data[key]),
          source,
        },
      ]);
  };

  const renderOverview = (cardsTarget, runtimeMetricsTarget, dashboard) => {
    if (!cardsTarget || !runtimeMetricsTarget) return;

    const counters = dashboard && typeof dashboard.counters === "object" ? dashboard.counters : {};
    const rates = dashboard && typeof dashboard.rates === "object" ? dashboard.rates : {};
    const latency = dashboard && typeof dashboard.latency_ms === "object" ? dashboard.latency_ms : {};
    const alerts = Array.isArray(dashboard?.alerts) ? dashboard.alerts : [];

    cardsTarget.innerHTML = "";
    const cards = [
      {
        title: "Mode et alertes",
        body: `Mode: ${toText(dashboard?.mode) || "n/a"}`,
        chips: alerts.length ? alerts : ["Aucune alerte"],
      },
      {
        title: "Compteurs",
        body: "Compteurs runtime hermeneutiques.",
        chips: Object.keys(counters).sort().map((key) => `${key}=${counters[key]}`),
      },
      {
        title: "Rates",
        body: "Rates deja calculees par le backend.",
        chips: Object.keys(rates).sort().map((key) => `${key}=${rates[key]}`),
      },
      {
        title: "Latences",
        body: "Latences stage par stage sur la fenetre courante.",
        chips: Object.keys(latency)
          .sort()
          .map((key) => {
            const item = latency[key] || {};
            return `${key}: p50=${item.p50_ms || 0} / p95=${item.p95_ms || 0}`;
          }),
      },
    ];

    const fragment = document.createDocumentFragment();
    cards.forEach((cardData) => {
      const card = document.createElement("article");
      card.className = "admin-card";

      const head = document.createElement("div");
      head.className = "admin-card-head";
      const title = document.createElement("h3");
      title.textContent = cardData.title;
      head.appendChild(title);
      card.appendChild(head);

      const body = document.createElement("p");
      body.textContent = cardData.body;
      card.appendChild(body);

      const meta = document.createElement("div");
      meta.className = "admin-card-meta";
      (cardData.chips.length ? cardData.chips : ["Aucune donnee"]).forEach((chipText) => {
        meta.appendChild(createChip(chipText));
      });
      card.appendChild(meta);
      fragment.appendChild(card);
    });
    cardsTarget.appendChild(fragment);

    renderReadonlyEntries(runtimeMetricsTarget, mappingToEntries(dashboard?.runtime_metrics, "dashboard"));
  };

  const replaceSelectOptions = (selectElement, options, selectedValue) => {
    if (!selectElement) return;
    const normalized = toText(selectedValue);
    selectElement.innerHTML = "";
    options.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      selectElement.appendChild(option);
    });
    if (options.some((item) => item.value === normalized)) {
      selectElement.value = normalized;
      return;
    }
    selectElement.value = options[0] ? options[0].value : "";
  };

  const renderConversationOptions = (selectElement, conversations, selectedConversationId) => {
    const options = [{ value: "", label: "Aucune conversation" }];
    (Array.isArray(conversations) ? conversations : []).forEach((item) => {
      const conversationId = toText(item?.conversation_id);
      if (!conversationId) return;
      const count = Number(item?.events_count);
      const suffix = Number.isFinite(count) ? ` (${count})` : "";
      options.push({ value: conversationId, label: `${conversationId}${suffix}` });
    });
    replaceSelectOptions(selectElement, options, selectedConversationId);
  };

  const renderTurnOptions = (selectElement, turns, selectedTurnId, conversationId) => {
    if (!selectElement) return;
    if (!toText(conversationId)) {
      replaceSelectOptions(selectElement, [{ value: "", label: "Selectionner une conversation" }], "");
      selectElement.disabled = true;
      return;
    }

    const options = [];
    (Array.isArray(turns) ? turns : []).forEach((item) => {
      const turnId = toText(item?.turn_id);
      if (!turnId) return;
      const count = Number(item?.events_count);
      const suffix = Number.isFinite(count) ? ` (${count})` : "";
      options.push({ value: turnId, label: `${turnId}${suffix}` });
    });

    if (!options.length) {
      replaceSelectOptions(selectElement, [{ value: "", label: "Aucun tour" }], "");
      selectElement.disabled = true;
      return;
    }

    replaceSelectOptions(selectElement, options, selectedTurnId);
    selectElement.disabled = false;
  };

  const renderStagePayload = (target, stage, payload) => {
    if (!target) return;
    target.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};

    if (stage === "hermeneutic_node_insertion" && safePayload.inputs && typeof safePayload.inputs === "object") {
      const summaryGrid = document.createElement("div");
      summaryGrid.className = "admin-readonly-grid";
      const topLevel = { ...safePayload };
      delete topLevel.inputs;
      renderReadonlyEntries(summaryGrid, mappingToEntries(topLevel, "chat_log"));
      target.appendChild(summaryGrid);

      const inputSection = document.createElement("section");
      inputSection.className = "admin-readonly-group";
      const inputHead = document.createElement("div");
      inputHead.className = "admin-readonly-group-head";
      const inputTitle = document.createElement("h4");
      inputTitle.textContent = "Inputs resumes";
      inputHead.appendChild(inputTitle);
      inputSection.appendChild(inputHead);
      const inputGrid = document.createElement("div");
      inputGrid.className = "admin-readonly-grid";
      renderReadonlyEntries(inputGrid, mappingToEntries(safePayload.inputs, "chat_log"));
      inputSection.appendChild(inputGrid);
      target.appendChild(inputSection);
      return;
    }

    const grid = document.createElement("div");
    grid.className = "admin-readonly-grid";
    renderReadonlyEntries(grid, mappingToEntries(safePayload, "chat_log"));
    target.appendChild(grid);
  };

  const renderTurnInspection = (target, items) => {
    if (!target) return;
    target.innerHTML = "";
    const safeItems = Array.isArray(items) ? items : [];
    if (!safeItems.length) {
      renderEmpty(target, "Aucun evenement de tour disponible pour inspection.");
      return;
    }

    STAGE_ORDER.forEach((stage) => {
      const stageItems = safeItems.filter((item) => toText(item?.stage) === stage);

      const group = document.createElement("section");
      group.className = "admin-readonly-group";

      const head = document.createElement("div");
      head.className = "admin-readonly-group-head";
      const title = document.createElement("h4");
      title.textContent = STAGE_LABELS[stage] || stage;
      head.appendChild(title);

      const meta = document.createElement("div");
      meta.className = "admin-card-meta";
      meta.appendChild(createChip(`events=${stageItems.length}`));
      if (!stageItems.length) {
        meta.appendChild(createChip("non observe"));
      } else {
        const latest = stageItems[0];
        const status = toText(latest?.status).toLowerCase();
        meta.appendChild(createChip(status || "unknown", { status }));
        const ts = toText(latest?.ts);
        if (ts) meta.appendChild(createChip(ts));
      }
      group.appendChild(head);
      group.appendChild(meta);

      if (!stageItems.length) {
        const empty = document.createElement("p");
        empty.className = "admin-readonly-empty";
        empty.textContent = "Aucun event pour ce stage sur le tour selectionne.";
        group.appendChild(empty);
        target.appendChild(group);
        return;
      }

      stageItems.forEach((item, index) => {
        const panel = document.createElement("article");
        panel.className = "admin-readonly-panel";

        const panelHead = document.createElement("div");
        panelHead.className = "admin-readonly-head";
        const labelWrap = document.createElement("div");
        const kicker = document.createElement("p");
        kicker.className = "admin-kicker";
        kicker.textContent = `Event ${index + 1}`;
        const label = document.createElement("h3");
        label.textContent = STAGE_LABELS[stage] || stage;
        labelWrap.appendChild(kicker);
        labelWrap.appendChild(label);
        panelHead.appendChild(labelWrap);
        panelHead.appendChild(createChip(toText(item?.status) || "unknown", { status: toText(item?.status).toLowerCase() }));
        panel.appendChild(panelHead);

        const panelMeta = document.createElement("div");
        panelMeta.className = "admin-card-meta";
        if (toText(item?.ts)) panelMeta.appendChild(createChip(toText(item.ts)));
        if (item?.duration_ms != null) panelMeta.appendChild(createChip(`duration=${item.duration_ms}ms`));
        panel.appendChild(panelMeta);

        const payloadHost = document.createElement("div");
        renderStagePayload(payloadHost, stage, item?.payload);
        panel.appendChild(payloadHost);
        group.appendChild(panel);
      });

      target.appendChild(group);
    });
  };

  const renderReadonlyCollection = (target, items, options = {}) => {
    if (!target) return;
    target.innerHTML = "";
    const safeItems = Array.isArray(items) ? items : [];
    if (!safeItems.length) {
      renderEmpty(target, options.emptyMessage || "Aucune donnee disponible.");
      return;
    }

    const identifyTitle = options.identifyTitle || (() => "");
    safeItems.forEach((item, index) => {
      const group = document.createElement("section");
      group.className = "admin-readonly-group";

      const head = document.createElement("div");
      head.className = "admin-readonly-group-head";
      const title = document.createElement("h4");
      title.textContent = identifyTitle(item, index) || `Item ${index + 1}`;
      head.appendChild(title);
      group.appendChild(head);

      const grid = document.createElement("div");
      grid.className = "admin-readonly-grid";
      renderReadonlyEntries(grid, mappingToEntries(item, options.source || "api"));
      group.appendChild(grid);
      target.appendChild(group);
    });
  };

  const renderArbiterDecisions = (metaTarget, listTarget, items, conversationId) => {
    if (metaTarget) {
      metaTarget.innerHTML = "";
      metaTarget.appendChild(createChip(`count=${Array.isArray(items) ? items.length : 0}`));
      metaTarget.appendChild(createChip(`conversation=${toText(conversationId) || "all"}`));
    }
    renderReadonlyCollection(listTarget, items, {
      emptyMessage: "Aucune decision arbitre disponible.",
      source: "arbiter",
      identifyTitle: (item, index) => {
        return toText(item?.decision_id) || toText(item?.conversation_id) || `Decision ${index + 1}`;
      },
    });
  };

  const renderIdentityCandidates = (target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const items = Array.isArray(safePayload.items) ? safePayload.items : [];

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    if (safePayload.legacy_only) meta.appendChild(createChip("legacy_only"));
    if (safePayload.evidence_only) meta.appendChild(createChip("evidence_only"));
    if (safePayload.drives_active_injection === false) meta.appendChild(createChip("injection_active=false"));
    if (toText(safePayload.active_identity_source)) {
      meta.appendChild(createChip(`active=${toText(safePayload.active_identity_source)}`));
    }
    if (toText(safePayload.active_prompt_contract)) {
      meta.appendChild(createChip(`prompt=${toText(safePayload.active_prompt_contract)}`));
    }
    if (meta.childNodes.length) {
      target.appendChild(meta);
    }

    const listHost = document.createElement("div");
    target.appendChild(listHost);
    renderReadonlyCollection(listHost, items, {
      emptyMessage: "Aucun fragment legacy d'identite disponible.",
      source: "identity",
      identifyTitle: (item, index) => {
        return toText(item?.identity_id) || toText(item?.content) || `Fragment legacy ${index + 1}`;
      },
    });
  };

  const renderCorrections = (target, items) => {
    renderReadonlyCollection(target, items, {
      emptyMessage: "Aucune correction recente disponible.",
      source: "correction",
      identifyTitle: (item, index) => {
        return toText(item?.identity_id) || toText(item?.event) || `Correction ${index + 1}`;
      },
    });
  };

  window.FridaHermeneuticAdminRender = Object.freeze({
    setStatusBanner,
    renderOverview,
    renderConversationOptions,
    renderTurnOptions,
    renderTurnInspection,
    renderArbiterDecisions,
    renderIdentityCandidates,
    renderCorrections,
  });
})();
