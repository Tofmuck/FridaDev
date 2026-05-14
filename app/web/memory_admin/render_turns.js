(() => {
  const overview = window.FridaMemoryAdminRenderOverview;
  if (!overview) {
    throw new Error("memory_admin/render_overview.js must be loaded before memory_admin/render_turns.js");
  }

  const STAGE_ORDER = [
    "embedding",
    "memory_retrieve",
    "memory_chain_snapshot",
    "summaries",
    "arbiter",
    "hermeneutic_node_insertion",
    "prompt_prepared",
    "branch_skipped",
  ];

  const STAGE_LABELS = Object.freeze({
    embedding: "embedding",
    memory_retrieve: "memory_retrieve",
    memory_chain_snapshot: "memory_chain_snapshot",
    summaries: "summaries",
    arbiter: "arbiter",
    hermeneutic_node_insertion: "hermeneutic_node_insertion",
    prompt_prepared: "prompt_prepared",
    branch_skipped: "branch_skipped",
  });

  const toList = (value) => Array.isArray(value) ? value : [];
  const safeObject = (value) => value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const toNumber = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const replaceSelectOptions = (selectElement, options, selectedValue) => {
    if (!selectElement) return;
    selectElement.innerHTML = "";
    options.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      selectElement.appendChild(option);
    });
    const normalized = overview.toText(selectedValue);
    selectElement.value = options.some((item) => item.value === normalized)
      ? normalized
      : (options[0]?.value || "");
  };

  const renderConversationOptions = (selectElement, conversations, selectedConversationId) => {
    const options = [{ value: "", label: "Aucune conversation" }];
    toList(conversations).forEach((item) => {
      const conversationId = overview.toText(item?.conversation_id);
      if (!conversationId) return;
      options.push({ value: conversationId, label: `${conversationId} (${Number(item?.events_count || 0)})` });
    });
    replaceSelectOptions(selectElement, options, selectedConversationId);
  };

  const renderTurnOptions = (selectElement, turns, selectedTurnId, conversationId) => {
    if (!selectElement) return;
    if (!overview.toText(conversationId)) {
      replaceSelectOptions(selectElement, [{ value: "", label: "Selectionner une conversation" }], "");
      selectElement.disabled = true;
      return;
    }
    const options = toList(turns)
      .map((item) => {
        const turnId = overview.toText(item?.turn_id);
        return turnId ? { value: turnId, label: `${turnId} (${Number(item?.events_count || 0)})` } : null;
      })
      .filter(Boolean);
    if (!options.length) {
      replaceSelectOptions(selectElement, [{ value: "", label: "Aucun tour" }], "");
      selectElement.disabled = true;
      return;
    }
    replaceSelectOptions(selectElement, options, selectedTurnId);
    selectElement.disabled = false;
  };

  const summaryText = (data, entries) => entries
    .map(([label, key]) => `${label}=${overview.compactValue(data[key]) || "n/a"}`)
    .join(" ");

  const candidateSummary = (items, rankKey) => {
    const rows = toList(items).slice(0, 12).map((item) => {
      const data = safeObject(item);
      const rank = overview.toText(data[rankKey]) || "?";
      const sha = overview.toText(data.candidate_id_sha256_12 || data.basket_candidate_id_sha256_12) || "n/a";
      const statuses = [
        overview.toText(data.basket_status),
        overview.toText(data.arbiter_status),
        overview.toText(data.prompt_injection_status),
      ].filter(Boolean).join("/");
      const reason = overview.toText(data.reason_code || data.dedup_reason_code || data.pre_arbiter_reason_code);
      return `#${rank} sha=${sha} ${statuses || "status=n/a"} reason=${reason || "n/a"}`;
    });
    return rows.length ? rows.join(" | ") : "Aucun candidat detaille.";
  };

  const stagePayloadEntries = (stage, payload) => {
    const data = safeObject(payload);
    if (stage === "memory_chain_snapshot") {
      const retrieval = safeObject(data.retrieval);
      const basket = safeObject(data.basket);
      const arbiter = safeObject(data.arbiter);
      const injection = safeObject(data.injection);
      return [
        ["retrieval", {
          label: "retrieved",
          value: summaryText(retrieval, [["status", "status"], ["count", "retrieved_count"], ["reason", "reason_code"]]),
          source: "historical_logs",
        }],
        ["basket", {
          label: "basket",
          value: summaryText(basket, [["status", "status"], ["count", "basket_candidates_count"], ["deduped", "deduped_retrieved_count"]]),
          source: "historical_logs",
        }],
        ["arbiter", {
          label: "kept / rejected",
          value: summaryText(arbiter, [["status", "status"], ["kept", "kept_count"], ["rejected", "rejected_count"]]),
          source: "historical_logs",
        }],
        ["injection", {
          label: "injected",
          value: summaryText(injection, [["class", "injection_class"], ["count", "injected_candidate_count"], ["hints", "context_hints_count"]]),
          source: "historical_logs",
        }],
        ["retrieved_candidates", {
          label: "Candidats retrieved",
          value: candidateSummary(data.retrieved_candidates, "retrieval_rank"),
          source: "historical_logs",
        }],
        ["basket_candidates", {
          label: "Candidats basket",
          value: candidateSummary(data.basket_candidates, "basket_rank"),
          source: "historical_logs",
        }],
      ];
    }
    if (stage === "prompt_prepared") {
      const injection = safeObject(data.memory_prompt_injection);
      const retrieval = safeObject(data.memory_retrieval);
      return [
        ...overview.mappingToEntries({
          injected: injection.injected,
          injection_class: injection.injection_class,
          trace_memory_injected_count: injection.trace_memory_injected_count || injection.memory_traces_injected_count,
          summary_context_injected_count: injection.summary_context_injected_count || injection.memory_context_summary_count,
          context_hints_injected_count: injection.context_hints_injected_count,
          memory_retrieval_status: retrieval.status,
          memory_retrieval_reason_code: retrieval.reason_code,
          memory_retrieval_error_code: retrieval.error_code,
        }, "historical_logs"),
      ];
    }
    if (stage === "hermeneutic_node_insertion") {
      const inputs = safeObject(data.inputs);
      const retrieved = safeObject(inputs.memory_retrieved);
      const arbitration = safeObject(inputs.memory_arbitration);
      return overview.mappingToEntries({
        retrieved_count: retrieved.retrieved_count,
        retrieval_status: retrieved.status,
        retrieval_reason_code: retrieved.reason_code,
        basket_candidates_count: arbitration.basket_candidates_count,
        decisions_count: arbitration.decisions_count,
        kept_count: arbitration.kept_count,
        rejected_count: arbitration.rejected_count,
        arbitration_status: arbitration.status,
        reason_code: arbitration.reason_code,
      }, "historical_logs");
    }
    const allowlists = {
      embedding: ["source_kind", "mode", "provider", "dimensions", "reason_code", "error_code", "error_class"],
      memory_retrieve: ["top_k_requested", "top_k_returned", "dense_candidates_count", "lexical_candidates_count", "summary_candidates_count", "reason_code", "error_code", "error_class"],
      summaries: ["active_summary_present", "summary_count_used", "summary_usage", "in_prompt", "summary_generation_observed"],
      arbiter: ["raw_candidates", "kept_candidates", "rejected_candidates", "decision_source", "fallback_used", "fallback_decisions", "model", "rejection_reason_code_counts", "reason_code", "retrieval_status", "retrieval_error_code", "retrieval_error_class"],
      branch_skipped: ["reason_code", "reason_short"],
    };
    const compact = {};
    (allowlists[stage] || []).forEach((key) => {
      if (data[key] !== undefined) compact[key] = data[key];
    });
    return overview.mappingToEntries(compact, "historical_logs");
  };

  const appendDisclosure = (target, { title, kicker = "", chips = [], entries = [] }) => {
    const details = document.createElement("details");
    details.className = "admin-readonly-panel admin-disclosure";
    const summary = document.createElement("summary");
    summary.className = "admin-disclosure-summary";
    const wrap = document.createElement("div");
    const kickerElement = document.createElement("p");
    kickerElement.className = "admin-kicker";
    kickerElement.textContent = kicker || "Debug";
    const heading = document.createElement("h3");
    heading.textContent = title;
    wrap.appendChild(kickerElement);
    wrap.appendChild(heading);
    summary.appendChild(wrap);
    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    chips.forEach((chip) => meta.appendChild(chip));
    summary.appendChild(meta);
    details.appendChild(summary);
    const body = document.createElement("div");
    body.className = "admin-disclosure-body";
    overview.renderReadonlyEntries(body, entries);
    details.appendChild(body);
    target.appendChild(details);
  };

  const latestStagePayload = (events, stage) => {
    const item = toList(events).filter((event) => overview.toText(event?.stage) === stage).at(-1);
    return safeObject(item?.payload || item?.payload_json);
  };

  const ragFromSnapshot = (snapshot) => {
    const retrieval = safeObject(snapshot.retrieval);
    const basket = safeObject(snapshot.basket);
    const arbiter = safeObject(snapshot.arbiter);
    const injection = safeObject(snapshot.injection);
    if (!Object.keys(snapshot).length) return {};
    return {
      source_kind: "memory_chain_snapshot",
      status: overview.toText(retrieval.status) || "ok",
      reason_code: retrieval.reason_code || basket.reason_code || arbiter.reason_code,
      retrieved: toNumber(retrieval.retrieved_count),
      basket: toNumber(basket.basket_candidates_count),
      kept: toNumber(arbiter.kept_count),
      rejected: toNumber(arbiter.rejected_count),
      injected: toNumber(injection.injected_candidate_count),
      context_hints: toNumber(injection.context_hints_count),
      truncated: Boolean(snapshot.truncated),
    };
  };

  const appendPipelineSummary = (fragment, pipelineItem, events, source) => {
    const snapshot = latestStagePayload(events, "memory_chain_snapshot");
    const rag = safeObject(pipelineItem?.rag);
    const chain = Object.keys(rag).length ? rag : ragFromSnapshot(snapshot);
    if (!Object.keys(chain).length && !pipelineItem) return;
    const panel = document.createElement("section");
    panel.className = "admin-readonly-panel";
    const head = document.createElement("div");
    head.className = "admin-readonly-head";
    const wrap = document.createElement("div");
    const kicker = document.createElement("p");
    kicker.className = "admin-kicker";
    kicker.textContent = "Cockpit tour";
    const title = document.createElement("h3");
    title.textContent = `${overview.toText(pipelineItem?.conversation_id) || "conversation"} / ${overview.toText(pipelineItem?.turn_id) || "tour"}`;
    wrap.appendChild(kicker);
    wrap.appendChild(title);
    head.appendChild(wrap);
    head.appendChild(overview.createChip(overview.toText(pipelineItem?.classification) || "memory_focus", {
      status: overview.toText(pipelineItem?.classification).toLowerCase(),
    }));
    panel.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(overview.createChip(`score=${pipelineItem?.score ?? "n/a"}`));
    meta.appendChild(overview.createChip(`source=${overview.toText(chain.source_kind) || "historical_logs"}`));
    meta.appendChild(overview.createChip(`retrieved=${toNumber(chain.retrieved)}`));
    meta.appendChild(overview.createChip(`basket=${toNumber(chain.basket)}`));
    meta.appendChild(overview.createChip(`kept=${toNumber(chain.kept)}`));
    meta.appendChild(overview.createChip(`rejected=${toNumber(chain.rejected)}`));
    meta.appendChild(overview.createChip(`injected=${toNumber(chain.injected)}`));
    meta.appendChild(overview.createChip(`hints=${toNumber(chain.context_hints)}`));
    if (chain.truncated || pipelineItem?.source?.events_truncated || source?.events_truncated) {
      meta.appendChild(overview.createChip("truncated", { status: "degraded" }));
    }
    panel.appendChild(meta);
    fragment.appendChild(panel);
  };

  const appendStageGroups = (fragment, events) => {
    const safeItems = toList(events);
    const observedStages = STAGE_ORDER.filter((stage) =>
      safeItems.some((item) => overview.toText(item?.stage) === stage)
    );
    observedStages.forEach((stage) => {
      const stageItems = safeItems.filter((item) => overview.toText(item?.stage) === stage);
      const group = document.createElement("section");
      group.className = "admin-readonly-group";
      const head = document.createElement("div");
      head.className = "admin-readonly-group-head";
      const title = document.createElement("h4");
      title.textContent = STAGE_LABELS[stage] || stage;
      head.appendChild(title);
      group.appendChild(head);
      const meta = document.createElement("div");
      meta.className = "admin-card-meta";
      meta.appendChild(overview.createChip(`events=${stageItems.length}`));
      group.appendChild(meta);
      stageItems.forEach((item, index) => {
        const chips = [];
        chips.push(overview.createChip(overview.toText(item?.status) || "unknown", {
          status: overview.toText(item?.status).toLowerCase(),
        }));
        if (overview.toText(item?.ts)) chips.push(overview.createChip(overview.toText(item.ts)));
        if (item?.duration_ms != null) chips.push(overview.createChip(`duration=${item.duration_ms}ms`));
        appendDisclosure(group, {
          title: STAGE_LABELS[stage] || stage,
          kicker: `Event ${index + 1}`,
          chips,
          entries: stagePayloadEntries(stage, item?.payload || item?.payload_json),
        });
      });
      fragment.appendChild(group);
    });
  };

  const renderTurnInspection = (target, input) => {
    if (!target) return;
    target.innerHTML = "";
    const events = Array.isArray(input) ? input : toList(input?.events);
    const pipelineItems = Array.isArray(input) ? [] : toList(input?.pipelineItems);
    const pipelineItem = pipelineItems[0] || null;
    if (!events.length && !pipelineItem) {
      overview.renderEmpty(target, "Aucun evenement memory/RAG pour ce tour.");
      return;
    }
    const fragment = document.createDocumentFragment();
    appendPipelineSummary(fragment, pipelineItem, events, input?.pipelineSource);
    appendStageGroups(fragment, events);
    target.appendChild(fragment);
  };

  const renderArbiterDecisions = (target, metaTarget, items, conversationId = "") => {
    if (metaTarget) {
      metaTarget.innerHTML = "";
      metaTarget.appendChild(overview.createChip(conversationId ? `conversation=${conversationId}` : "conversation=toutes"));
      metaTarget.appendChild(overview.createChip(`count=${Array.isArray(items) ? items.length : 0}`));
    }
    if (!target) return;
    target.innerHTML = "";
    const safeItems = toList(items);
    if (!safeItems.length) {
      overview.renderEmpty(target, "Aucune decision arbitre persistante disponible.");
      return;
    }
    const fragment = document.createDocumentFragment();
    safeItems.forEach((item, index) => {
      const panel = document.createElement("article");
      panel.className = "admin-readonly-panel";
      const head = document.createElement("div");
      head.className = "admin-readonly-head";
      const wrap = document.createElement("div");
      const kicker = document.createElement("p");
      kicker.className = "admin-kicker";
      kicker.textContent = `Decision ${index + 1}`;
      const title = document.createElement("h3");
      title.textContent = overview.toText(item?.candidate_id) || "candidate_id absent";
      wrap.appendChild(kicker);
      wrap.appendChild(title);
      head.appendChild(wrap);
      head.appendChild(overview.createChip(item?.keep ? "keep" : "reject", { status: item?.keep ? "ok" : "error" }));
      panel.appendChild(head);
      const meta = document.createElement("div");
      meta.className = "admin-card-meta";
      meta.appendChild(overview.createChip(`source=${overview.toText(item?.decision_source) || "n/a"}`));
      meta.appendChild(overview.createChip(`semantic=${overview.compactValue(item?.semantic_relevance)}`));
      meta.appendChild(overview.createChip(`contextual=${overview.compactValue(item?.contextual_gain)}`));
      if (overview.toText(item?.created_ts)) meta.appendChild(overview.createChip(overview.toText(item.created_ts)));
      panel.appendChild(meta);
      const grid = document.createElement("div");
      grid.className = "admin-readonly-grid";
      overview.renderReadonlyEntries(grid, [
        ["conversation_id", { label: "Conversation", value: overview.toText(item?.conversation_id) || "n/a", source: "durable_persistence" }],
        ["candidate_role", { label: "Role candidat", value: overview.toText(item?.candidate_role) || "n/a", source: "durable_persistence" }],
        ["candidate_score", { label: "Score candidat", value: overview.compactValue(item?.candidate_score) || "0", source: "durable_persistence" }],
        ["candidate_content_chars", { label: "Taille contenu candidat", value: overview.compactValue(item?.candidate_content_chars) || "0", source: "durable_persistence" }],
        ["candidate_content_sha256_12", { label: "Hash contenu candidat", value: overview.toText(item?.candidate_content_sha256_12) || "n/a", source: "durable_persistence" }],
        ["reason_code", { label: "Code raison", value: overview.toText(item?.reason_code) || "n/a", source: "durable_persistence" }],
        ["reason_chars", { label: "Taille raison", value: overview.compactValue(item?.reason_chars) || "0", source: "durable_persistence" }],
        ["reason_sha256_12", { label: "Hash raison", value: overview.toText(item?.reason_sha256_12) || "n/a", source: "durable_persistence" }],
        ["redundant_with_recent", { label: "Redondant recent", value: item?.redundant_with_recent ? "oui" : "non", source: "durable_persistence" }],
        ["model", { label: "Modele", value: overview.toText(item?.model) || "n/a", source: "durable_persistence" }],
      ]);
      panel.appendChild(grid);
      fragment.appendChild(panel);
    });
    target.appendChild(fragment);
  };

  window.FridaMemoryAdminRenderTurns = Object.freeze({
    renderConversationOptions,
    renderTurnOptions,
    renderTurnInspection,
    renderArbiterDecisions,
  });
})();
