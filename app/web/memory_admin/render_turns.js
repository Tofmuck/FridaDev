(() => {
  const overview = window.FridaMemoryAdminRenderOverview;
  if (!overview) {
    throw new Error("memory_admin/render_overview.js must be loaded before memory_admin/render_turns.js");
  }

  const STAGE_ORDER = [
    "embedding",
    "memory_retrieve",
    "summaries",
    "arbiter",
    "hermeneutic_node_insertion",
    "prompt_prepared",
    "branch_skipped",
  ];

  const STAGE_LABELS = Object.freeze({
    embedding: "embedding",
    memory_retrieve: "memory_retrieve",
    summaries: "summaries",
    arbiter: "arbiter",
    hermeneutic_node_insertion: "hermeneutic_node_insertion",
    prompt_prepared: "prompt_prepared",
    branch_skipped: "branch_skipped",
  });

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
    if (options.some((item) => item.value === normalized)) {
      selectElement.value = normalized;
      return;
    }
    selectElement.value = options[0] ? options[0].value : "";
  };

  const renderConversationOptions = (selectElement, conversations, selectedConversationId) => {
    const options = [{ value: "", label: "Aucune conversation" }];
    (Array.isArray(conversations) ? conversations : []).forEach((item) => {
      const conversationId = overview.toText(item?.conversation_id);
      if (!conversationId) return;
      options.push({
        value: conversationId,
        label: `${conversationId} (${Number(item?.events_count || 0)})`,
      });
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
    const options = [];
    (Array.isArray(turns) ? turns : []).forEach((item) => {
      const turnId = overview.toText(item?.turn_id);
      if (!turnId) return;
      options.push({
        value: turnId,
        label: `${turnId} (${Number(item?.events_count || 0)})`,
      });
    });
    if (!options.length) {
      replaceSelectOptions(selectElement, [{ value: "", label: "Aucun tour" }], "");
      selectElement.disabled = true;
      return;
    }
    replaceSelectOptions(selectElement, options, selectedTurnId);
    selectElement.disabled = false;
  };

  const stagePayloadEntries = (stage, payload) => {
    const data = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    if (stage === "prompt_prepared" && data.memory_prompt_injection && typeof data.memory_prompt_injection === "object") {
      return overview.mappingToEntries(data.memory_prompt_injection, "historical_logs");
    }
    if (stage === "hermeneutic_node_insertion" && data.inputs && typeof data.inputs === "object") {
      return overview.mappingToEntries(data.inputs, "historical_logs");
    }
    return overview.mappingToEntries(data, "historical_logs");
  };

  const renderTurnInspection = (target, items) => {
    if (!target) return;
    target.innerHTML = "";
    const safeItems = Array.isArray(items) ? items : [];
    if (!safeItems.length) {
      overview.renderEmpty(target, "Aucun evenement memory/RAG pour ce tour.");
      return;
    }

    const fragment = document.createDocumentFragment();
    STAGE_ORDER.forEach((stage) => {
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

      if (!stageItems.length) {
        const empty = document.createElement("p");
        empty.className = "admin-readonly-empty";
        empty.textContent = "Non observe pour ce tour.";
        group.appendChild(empty);
        fragment.appendChild(group);
        return;
      }

      stageItems.forEach((item, index) => {
        const panel = document.createElement("article");
        panel.className = "admin-readonly-panel";

        const panelHead = document.createElement("div");
        panelHead.className = "admin-readonly-head";
        const wrap = document.createElement("div");
        const kicker = document.createElement("p");
        kicker.className = "admin-kicker";
        kicker.textContent = `Event ${index + 1}`;
        const label = document.createElement("h3");
        label.textContent = STAGE_LABELS[stage] || stage;
        wrap.appendChild(kicker);
        wrap.appendChild(label);
        panelHead.appendChild(wrap);
        panelHead.appendChild(
          overview.createChip(overview.toText(item?.status) || "unknown", {
            status: overview.toText(item?.status).toLowerCase(),
          })
        );
        panel.appendChild(panelHead);

        const panelMeta = document.createElement("div");
        panelMeta.className = "admin-card-meta";
        if (overview.toText(item?.ts)) panelMeta.appendChild(overview.createChip(overview.toText(item.ts)));
        if (item?.duration_ms != null) panelMeta.appendChild(overview.createChip(`duration=${item.duration_ms}ms`));
        panel.appendChild(panelMeta);

        const grid = document.createElement("div");
        grid.className = "admin-readonly-grid";
        overview.renderReadonlyEntries(grid, stagePayloadEntries(stage, item?.payload));
        panel.appendChild(grid);
        group.appendChild(panel);
      });
      fragment.appendChild(group);
    });
    target.appendChild(fragment);
  };

  const renderArbiterDecisions = (target, metaTarget, items, conversationId = "") => {
    if (metaTarget) {
      metaTarget.innerHTML = "";
      metaTarget.appendChild(
        overview.createChip(
          conversationId ? `conversation=${conversationId}` : "conversation=toutes"
        )
      );
      metaTarget.appendChild(overview.createChip(`count=${Array.isArray(items) ? items.length : 0}`));
    }
    if (!target) return;
    target.innerHTML = "";
    const safeItems = Array.isArray(items) ? items : [];
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
      head.appendChild(
        overview.createChip(item?.keep ? "keep" : "reject", {
          status: item?.keep ? "ok" : "error",
        })
      );
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
        ["conversation_id", {
          label: "Conversation",
          value: overview.toText(item?.conversation_id) || "n/a",
          source: "durable_persistence",
        }],
        ["candidate_content", {
          label: "Contenu candidat",
          value: overview.compactValue(item?.candidate_content, 320) || "",
          source: "durable_persistence",
        }],
        ["reason", {
          label: "Raison",
          value: overview.compactValue(item?.reason, 320) || "",
          source: "durable_persistence",
        }],
        ["model", {
          label: "Modele",
          value: overview.toText(item?.model) || "n/a",
          source: "durable_persistence",
        }],
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
