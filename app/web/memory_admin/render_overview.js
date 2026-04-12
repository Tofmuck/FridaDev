(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error("admin_ui_common.js must be loaded before memory_admin/render_overview.js");
  }

  const toText = (value) => String(value == null ? "" : value).trim();

  const toNumber = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const compactValue = (value, maxLength = 220) => {
    if (value == null) return "";
    if (typeof value === "string") {
      const cleaned = value.replace(/\s+/g, " ").trim();
      return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength - 3)}...` : cleaned;
    }
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
    const serialized = JSON.stringify(value);
    return serialized.length > maxLength ? `${serialized.slice(0, maxLength - 3)}...` : serialized;
  };

  const sourceLabel = (value) => {
    const normalized = toText(value);
    if (normalized === "durable_persistence") return "Persistance durable";
    if (normalized === "calculated_aggregate") return "Agregat calcule";
    if (normalized === "runtime_process_local") return "Runtime process-local";
    if (normalized === "historical_logs") return "Historique logs";
    return normalized || "Source";
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

  const setStatusBanner = (element, message, state = "") => {
    if (!element) return;
    element.textContent = message;
    if (!state) {
      delete element.dataset.state;
      return;
    }
    element.dataset.state = state;
  };

  const renderEmpty = (target, message) => {
    if (!target) return;
    target.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    target.appendChild(empty);
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
          label: key.replace(/_/g, " "),
          value: compactValue(data[key]),
          source,
        },
      ]);
  };

  const buildCard = ({ title, body = "", chips = [], source = "" }) => {
    const card = document.createElement("article");
    card.className = "admin-card";

    const head = document.createElement("div");
    head.className = "admin-card-head";
    const titleElement = document.createElement("h3");
    titleElement.textContent = title;
    head.appendChild(titleElement);
    if (source) {
      const badge = document.createElement("span");
      badge.className = "admin-card-source";
      badge.textContent = sourceLabel(source);
      head.appendChild(badge);
    }
    card.appendChild(head);

    const bodyElement = document.createElement("p");
    bodyElement.textContent = body;
    card.appendChild(bodyElement);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    (chips.length ? chips : ["Aucune donnee"]).forEach((chipText) => {
      meta.appendChild(createChip(chipText));
    });
    card.appendChild(meta);
    return card;
  };

  const replaceCards = (target, cards = []) => {
    if (!target) return;
    target.innerHTML = "";
    if (!cards.length) {
      renderEmpty(target, "Aucune donnee a afficher.");
      return;
    }
    const fragment = document.createDocumentFragment();
    cards.forEach((card) => fragment.appendChild(card));
    target.appendChild(fragment);
  };

  const renderHero = (elements, dashboard) => {
    const overview = dashboard?.overview || {};
    const surface = dashboard?.surface || {};
    if (elements.modeMeta) {
      elements.modeMeta.textContent = toText(overview.mode) || "inconnu";
    }
    if (elements.rerankerMeta) {
      elements.rerankerMeta.textContent = surface.reranker_decision === "no_go_for_now"
        ? "No-go for now"
        : "Inconnu";
    }
    if (elements.sourcesMeta) {
      elements.sourcesMeta.textContent = `${Array.isArray(dashboard?.sources_legend) ? dashboard.sources_legend.length : 0} familles`;
    }
  };

  const renderScope = (elements, dashboard) => {
    const scope = dashboard?.scope || {};
    const keptElsewhere = Array.isArray(scope.kept_elsewhere) ? scope.kept_elsewhere : [];
    replaceCards(elements.scopeCards, [
      buildCard({
        title: "Surface dediee",
        body: toText(dashboard?.overview?.summary),
        source: "calculated_aggregate",
        chips: [
          "distincte de /admin",
          "distincte de /hermeneutic-admin",
          "Memory Admin",
        ],
      }),
      ...keptElsewhere.map((item) =>
        buildCard({
          title: item.label || "Surface liee",
          body: item.reason || "",
          chips: [toText(item.route) || "route"],
          source: "calculated_aggregate",
        })
      ),
    ]);
    renderReadonlyEntries(
      elements.sourcesLegend,
      (Array.isArray(dashboard?.sources_legend) ? dashboard.sources_legend : []).map((item) => [
        item.key || "source",
        {
          label: item.label || sourceLabel(item.key),
          value: item.description || "",
          source: item.key || "read_only",
        },
      ]),
    );
  };

  const renderDurableState = (elements, dashboard) => {
    const durable = dashboard?.durable_state || {};
    const traces = durable.traces || {};
    const summaries = durable.summaries || {};
    const decisions = durable.arbiter_decisions || {};
    replaceCards(elements.durableCards, [
      buildCard({
        title: "Traces",
        body: "Etat durable des souvenirs traces persistes.",
        source: durable.source_kind,
        chips: [
          `total=${toNumber(traces.total)}`,
          `embed=${toNumber(traces.with_embedding)}`,
          `summary_id=${toNumber(traces.with_summary_id)}`,
          `conv=${toNumber(traces.conversations)}`,
        ],
      }),
      buildCard({
        title: "Summaries",
        body: "Voie de resumes persistants et couverture actuellement visible.",
        source: durable.source_kind,
        chips: [
          `total=${toNumber(summaries.total)}`,
          `embed=${toNumber(summaries.with_embedding)}`,
          `conv=${toNumber(summaries.conversations)}`,
        ],
      }),
      buildCard({
        title: "Arbiter decisions",
        body: "Persistances des decisions arbitre en base.",
        source: durable.source_kind,
        chips: [
          `total=${toNumber(decisions.total)}`,
          `kept=${toNumber(decisions.kept_count)}`,
          `rejected=${toNumber(decisions.rejected_count)}`,
          `fallback=${toNumber(decisions.fallback_count)}`,
        ],
      }),
    ]);

    const duplicateExamples = Array.isArray(traces.duplicate_examples) ? traces.duplicate_examples : [];
    const details = [];
    details.push(
      ["trace_roles", {
        label: "Repartition des traces",
        value: `user=${toNumber(traces.by_role?.user)} assistant=${toNumber(traces.by_role?.assistant)} summary=${toNumber(traces.by_role?.summary)}`,
        source: durable.source_kind || "durable_persistence",
      }],
      ["trace_latest_ts", {
        label: "Derniere trace",
        value: toText(traces.latest_ts) || "inconnue",
        source: durable.source_kind || "durable_persistence",
      }],
      ["duplicate_examples", {
        label: "Doublons notables",
        value: duplicateExamples.length
          ? duplicateExamples.map((item) => `${item.role}:${item.occurrences} ${item.content_excerpt}`).join(" | ")
          : "Aucun doublon notable remonte",
        source: durable.source_kind || "durable_persistence",
      }],
      ["top_rejection_reasons", {
        label: "Rejets arbitre les plus frequents",
        value: Object.keys(decisions.top_rejection_reasons || {}).length
          ? Object.entries(decisions.top_rejection_reasons).map(([reason, count]) => `${reason}=${count}`).join(" | ")
          : "Aucune raison remontee",
        source: durable.source_kind || "durable_persistence",
      }],
    );
    renderReadonlyEntries(elements.durableDetails, details);
  };

  const renderRetrievalEmbeddings = (elements, dashboard) => {
    const retrieval = dashboard?.retrieval || {};
    const retrievalActivity = retrieval.recent_activity || {};
    const embeddings = dashboard?.embeddings || {};
    const embeddingActivity = embeddings.recent_activity || {};
    const embeddingSettings = embeddings.settings || {};
    replaceCards(elements.retrievalCards, [
      buildCard({
        title: "Retrieval configure",
        body: "Reglages lus depuis les runtime settings et contracts actifs.",
        source: retrieval.config_source_kind,
        chips: [
          `top_k=${toNumber(retrieval.config?.top_k)}`,
          `basket_limit=${toNumber(retrieval.config?.basket_limit)}`,
          retrieval.config?.summary_lane_live ? "summaries=actif" : "summaries=neutre",
        ],
      }),
      buildCard({
        title: "Retrieval recent",
        body: "Moyennes observees dans les logs sur la fenetre recente.",
        source: retrieval.activity_source_kind,
        chips: [
          `turns=${toNumber(retrievalActivity.turns_observed)}`,
          `dense=${toNumber(retrievalActivity.avg_dense_candidates)}`,
          `lexical=${toNumber(retrievalActivity.avg_lexical_candidates)}`,
          `returned=${toNumber(retrievalActivity.avg_top_k_returned)}`,
        ],
      }),
    ]);
    replaceCards(elements.embeddingsCards, [
      buildCard({
        title: "Embeddings configures",
        body: "Configuration runtime des embeddings.",
        source: embeddings.settings_source_kind,
        chips: [
          `model=${toText(embeddingSettings.model) || "n/a"}`,
          `host=${toText(embeddingSettings.endpoint_host) || "n/a"}`,
          `dim=${toNumber(embeddingSettings.dimensions)}`,
          embeddingSettings.token_configured ? "token=present" : "token=absent",
        ],
      }),
      buildCard({
        title: "Embeddings recents",
        body: "Ventilation recente des appels embeddings par source_kind.",
        source: embeddings.activity_source_kind,
        chips: Object.entries(embeddingActivity.by_source_kind || {}).map(
          ([key, count]) => `${key}=${count}`
        ),
      }),
    ]);
  };

  const renderBasketArbiter = (elements, dashboard) => {
    const basket = dashboard?.pre_arbiter_basket || {};
    const basketActivity = basket.recent_activity || {};
    const arbiter = dashboard?.arbiter || {};
    const settings = arbiter.settings || {};
    replaceCards(elements.basketCards, [
      buildCard({
        title: "Panier pre-arbitre",
        body: "Objet calcule intermediaire avant le tri arbitre.",
        source: basket.contract_source_kind,
        chips: [
          `limit=${toNumber(basket.contract?.basket_limit)}`,
          ...(Array.isArray(basket.contract?.dedup_reason_codes) ? basket.contract.dedup_reason_codes : []),
        ],
      }),
      buildCard({
        title: "Panier recent",
        body: "Volumes moyens issus des logs recents.",
        source: basket.recent_activity_source_kind,
        chips: [
          `turns=${toNumber(basketActivity.turns_observed)}`,
          `raw=${toNumber(basketActivity.avg_raw_candidates)}`,
          `basket=${toNumber(basketActivity.avg_basket_candidates)}`,
          `kept=${toNumber(basketActivity.avg_kept)}`,
        ],
      }),
    ]);
    replaceCards(elements.arbiterCards, [
      buildCard({
        title: "Arbitre configure",
        body: "Reglages runtime actuels du modele arbitre.",
        source: arbiter.settings_source_kind,
        chips: [
          `model=${toText(settings.model) || "n/a"}`,
          `timeout=${toNumber(settings.timeout_s)}s`,
          `semantic=${compactValue(settings.min_semantic_relevance)}`,
          `contextual=${compactValue(settings.min_contextual_gain)}`,
        ],
      }),
      buildCard({
        title: "Arbitre persistant",
        body: "Compteurs lus dans arbiter_decisions.",
        source: arbiter.durable_source_kind,
        chips: [
          `total=${toNumber(arbiter.persisted_summary?.total)}`,
          `kept=${toNumber(arbiter.persisted_summary?.kept_count)}`,
          `rejected=${toNumber(arbiter.persisted_summary?.rejected_count)}`,
          `fallback=${toNumber(arbiter.persisted_summary?.fallback_count)}`,
        ],
      }),
      buildCard({
        title: "Reranker",
        body: "La decision projet reste no-go for now; aucun reranker n est introduit ici.",
        source: arbiter.settings_source_kind,
        chips: [
          "no-go for now",
          toText(settings.reranker_decision_doc) || "doc",
        ],
      }),
    ]);

    const runtimeEntries = [
      ...mappingToEntries(arbiter.runtime_metrics, arbiter.runtime_source_kind || "runtime_process_local"),
      ...mappingToEntries(arbiter.latency_ms, arbiter.admin_logs_source_kind || "historical_logs"),
      ...mappingToEntries(arbiter.mode_observation, arbiter.admin_logs_source_kind || "historical_logs"),
    ];
    renderReadonlyEntries(elements.arbiterRuntimeMetrics, runtimeEntries);
  };

  const renderInjectionAndRecentTurns = (elements, dashboard) => {
    const injection = dashboard?.injection || {};
    const activity = injection.recent_activity || {};
    replaceCards(elements.injectionCards, [
      buildCard({
        title: "Injection memoire",
        body: "Resume des injections memory/RAG dans le prompt prepare.",
        source: injection.source_kind,
        chips: [
          `events=${toNumber(activity.events_count)}`,
          `injected=${toNumber(activity.injected_turns)}`,
          `traces=${toNumber(activity.avg_memory_traces_injected_count)}`,
          `summaries=${toNumber(activity.avg_memory_context_summary_count)}`,
        ],
      }),
      buildCard({
        title: "Derniere injection utile",
        body: "Derniers candidate_ids visibles dans le resume d injection.",
        source: injection.source_kind,
        chips: Array.isArray(activity.latest_injected_candidate_ids) && activity.latest_injected_candidate_ids.length
          ? activity.latest_injected_candidate_ids
          : ["Aucun candidate_id recent"],
      }),
    ]);

    const items = Array.isArray(dashboard?.recent_turns?.items) ? dashboard.recent_turns.items : [];
    if (!items.length) {
      renderEmpty(elements.recentTurns, "Aucun tour memory/RAG recent observe.");
      return;
    }

    const fragment = document.createDocumentFragment();
    items.forEach((item, index) => {
      const stages = item.stages || {};
      const card = document.createElement("section");
      card.className = "admin-readonly-panel";

      const head = document.createElement("div");
      head.className = "admin-readonly-head";
      const titleWrap = document.createElement("div");
      const kicker = document.createElement("p");
      kicker.className = "admin-kicker";
      kicker.textContent = `Tour recent ${index + 1}`;
      const title = document.createElement("h3");
      title.textContent = `${toText(item.conversation_id) || "conversation"} / ${toText(item.turn_id) || "tour"}`;
      titleWrap.appendChild(kicker);
      titleWrap.appendChild(title);
      head.appendChild(titleWrap);
      head.appendChild(createChip(toText(item.latest_ts) || "ts inconnue"));
      card.appendChild(head);

      const meta = document.createElement("div");
      meta.className = "admin-card-meta";
      const retrieval = stages.memory_retrieve?.payload || {};
      const arbitration = stages.arbiter?.payload || {};
      const prompt = stages.prompt_prepared?.payload || {};
      meta.appendChild(createChip(`retrieved=${toNumber(retrieval.top_k_returned)}`));
      meta.appendChild(createChip(`basket=${toNumber(stages.hermeneutic_node_insertion?.payload?.basket_candidates_count)}`));
      meta.appendChild(createChip(`kept=${toNumber(arbitration.kept_candidates)}`));
      meta.appendChild(createChip(`injected=${toNumber(prompt.memory_traces_injected_count)}`));
      card.appendChild(meta);

      const grid = document.createElement("div");
      grid.className = "admin-readonly-grid";
      renderReadonlyEntries(grid, [
        ["retrieval", {
          label: "Retrieval",
          value: compactValue(retrieval),
          source: "historical_logs",
        }],
        ["arbiter", {
          label: "Arbitre",
          value: compactValue(arbitration),
          source: "historical_logs",
        }],
        ["prompt", {
          label: "Injection prompt",
          value: compactValue(prompt),
          source: "historical_logs",
        }],
      ]);
      card.appendChild(grid);
      fragment.appendChild(card);
    });
    elements.recentTurns.replaceChildren(fragment);
  };

  window.FridaMemoryAdminRenderOverview = Object.freeze({
    toText,
    compactValue,
    createChip,
    setStatusBanner,
    renderEmpty,
    renderReadonlyEntries,
    mappingToEntries,
    renderHero,
    renderScope,
    renderDurableState,
    renderRetrievalEmbeddings,
    renderBasketArbiter,
    renderInjectionAndRecentTurns,
  });
})();
