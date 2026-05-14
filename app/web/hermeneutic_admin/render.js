(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error("admin_ui_common.js must be loaded before hermeneutic_admin/render.js");
  }

  const STAGE_ORDER = [
    "stimmung_agent",
    "stimmung_prompt_prepared",
    "hermeneutic_node_insertion",
    "primary_node",
    "validation_prompt_prepared",
    "validation_agent",
    "prompt_prepared",
    "llm_call",
  ];

  const STAGE_LABELS = Object.freeze(Object.fromEntries(STAGE_ORDER.map((stage) => [stage, stage])));
  const FORBIDDEN_STAGE_PAYLOAD_KEYS = new Set([
    "prompt",
    "messages",
    "content",
    "user_message",
    "recent_window",
    "context_block",
    "canonical_inputs",
    "query",
    "results",
    "snippets",
    "secret",
    "token",
    "api_key",
    "dsn",
    "password",
    "authorization",
    "headers",
    "traceback",
    "stack",
    "exception",
    "error",
  ]);
  const SAFE_STAGE_TEXT_KEYS = new Set([
    "actor",
    "canonical_basis",
    "classification",
    "discursive_regime",
    "error_class",
    "error_code",
    "fallback_source",
    "final_status",
    "injection_class",
    "judgment_posture",
    "model",
    "node_stage",
    "payload_kind",
    "persist_phase",
    "provider",
    "provider_caller",
    "reason_code",
    "read_state",
    "role",
    "schema_version",
    "source",
    "source_kind",
    "status",
    "technical_name",
    "validation_error",
  ]);

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

  const isForbiddenStagePayloadKey = (key) => {
    const normalized = toText(key).toLowerCase();
    if (!normalized) return false;
    if (SAFE_STAGE_TEXT_KEYS.has(normalized)) return false;
    if (/_?(chars|count|counts|present|included|injected|enabled|configured|succeeded|attempted|valid|sha256_12)$/.test(normalized)) {
      return false;
    }
    if (FORBIDDEN_STAGE_PAYLOAD_KEYS.has(normalized)) return true;
    return /(^|_)(prompt|messages?|content|query|snippet|secret|token|password|dsn|authorization|traceback|stack|exception|canonical_inputs?)($|_)/.test(normalized);
  };

  const isSafeStageTextKey = (key) => {
    const normalized = toText(key).toLowerCase();
    return SAFE_STAGE_TEXT_KEYS.has(normalized)
      || normalized.endsWith("_id")
      || normalized.endsWith("_kind")
      || normalized.endsWith("_code")
      || normalized.endsWith("_class")
      || normalized.endsWith("_status")
      || normalized.endsWith("_sha256_12")
      || normalized.endsWith("_ts");
  };

  const stageTextSummary = (value) => {
    const text = toText(value);
    return {
      text_present: Boolean(text),
      text_chars: text.length,
    };
  };

  const sanitizeStagePayload = (value) => {
    const redaction = { count: 0 };
    const sanitize = (item, key = "") => {
      if (isForbiddenStagePayloadKey(key)) {
        redaction.count += 1;
        return undefined;
      }
      if (Array.isArray(item)) {
        return item
          .map((entry) => sanitize(entry, key))
          .filter((entry) => entry !== undefined);
      }
      if (!item || typeof item !== "object") {
        if (typeof item === "string" && !isSafeStageTextKey(key)) {
          return stageTextSummary(item);
        }
        return item;
      }
      return Object.fromEntries(
        Object.entries(item)
          .map(([childKey, childValue]) => [childKey, sanitize(childValue, childKey)])
          .filter(([, childValue]) => childValue !== undefined),
      );
    };
    const sanitized = sanitize(value);
    if (sanitized && typeof sanitized === "object" && !Array.isArray(sanitized) && redaction.count) {
      return {
        ...sanitized,
        redaction: {
          content_free: true,
          redacted_fields_count: redaction.count,
        },
      };
    }
    return sanitized;
  };

  const buildModeObservationBody = (dashboard) => {
    const modeObservation = dashboard && typeof dashboard.mode_observation === "object"
      ? dashboard.mode_observation
      : {};
    const mode = toText(dashboard?.mode) || "n/a";
    if (modeObservation.current_mode_observed && toText(modeObservation.observed_since)) {
      return `Mode: ${mode}. Observe dans les logs admin retenus depuis ${modeObservation.observed_since}.`;
    }
    return `Mode: ${mode}. Aucune bascule exacte n'est persistee; seule l'observation retenue du mode courant est disponible.`;
  };

  const buildModeObservationChips = (dashboard) => {
    const modeObservation = dashboard && typeof dashboard.mode_observation === "object"
      ? dashboard.mode_observation
      : {};
    const chips = [];
    chips.push(
      `observe_depuis=${toText(modeObservation.observed_since) || "inconnu"}`,
      `derniere_obs=${toText(modeObservation.last_observed_at || modeObservation.latest_observed_at) || "inconnue"}`,
      `bascule_exacte=${modeObservation.exact_switch_known ? "oui" : "inconnue"}`,
    );
    if (toText(modeObservation.previous_mode) && toText(modeObservation.previous_mode_last_observed_at)) {
      chips.push(`precedent=${modeObservation.previous_mode}@${modeObservation.previous_mode_last_observed_at}`);
    }
    return chips;
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
        body: buildModeObservationBody(dashboard),
        chips: [
          ...buildModeObservationChips(dashboard),
          ...(alerts.length ? alerts : ["Aucune alerte"]),
        ],
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
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload)
      ? sanitizeStagePayload(payload)
      : {};

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

    let renderedStageCount = 0;
    STAGE_ORDER.forEach((stage) => {
      const stageItems = safeItems.filter((item) => toText(item?.stage) === stage);
      if (!stageItems.length) {
        return;
      }
      renderedStageCount += 1;

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
      const latest = stageItems[0];
      const status = toText(latest?.status).toLowerCase();
      meta.appendChild(createChip(status || "unknown", { status }));
      const ts = toText(latest?.ts);
      if (ts) meta.appendChild(createChip(ts));
      group.appendChild(head);
      group.appendChild(meta);

      stageItems.forEach((item, index) => {
        const panel = document.createElement("details");
        panel.className = "admin-readonly-panel admin-disclosure";

        const panelHead = document.createElement("summary");
        panelHead.className = "admin-disclosure-summary";
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

        const body = document.createElement("div");
        body.className = "admin-disclosure-body";
        const panelMeta = document.createElement("div");
        panelMeta.className = "admin-card-meta";
        if (toText(item?.ts)) panelMeta.appendChild(createChip(toText(item.ts)));
        if (item?.duration_ms != null) panelMeta.appendChild(createChip(`duration=${item.duration_ms}ms`));
        body.appendChild(panelMeta);

        const payloadHost = document.createElement("div");
        renderStagePayload(payloadHost, stage, item?.payload);
        body.appendChild(payloadHost);
        panel.appendChild(body);
        group.appendChild(panel);
      });

      target.appendChild(group);
    });
    if (!renderedStageCount) {
      renderEmpty(target, "Aucun stage critique observe sur ce tour.");
    }
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
      meta.appendChild(createChip(`compile=${toText(safePayload.active_prompt_contract)}`));
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
        return toText(item?.identity_id)
          || toText(item?.source_kind)
          || toText(item?.subject)
          || `Fragment legacy ${index + 1}`;
      },
    });
  };

  const renderIdentityReadModel = (metaTarget, target, payload, options = {}) => {
    const identityRenderer = window.FridaHermeneuticIdentityReadModelRender;
    if (!identityRenderer || typeof identityRenderer.renderIdentityReadModel !== "function") {
      throw new Error(
        "hermeneutic_admin/render_identity_read_model.js must be loaded before renderIdentityReadModel()",
      );
    }
    return identityRenderer.renderIdentityReadModel(metaTarget, target, payload, options);
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
    renderIdentityReadModel,
    renderIdentityCandidates,
    renderCorrections,
  });
})();
