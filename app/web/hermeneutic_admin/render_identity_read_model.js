(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error(
      "admin_ui_common.js must be loaded before hermeneutic_admin/render_identity_read_model.js",
    );
  }

  const toText = (value) => String(value == null ? "" : value).trim();

  const createChip = (text) => {
    const chip = document.createElement("span");
    chip.className = "admin-chip";
    chip.textContent = text;
    return chip;
  };

  const createNote = (text) => {
    const note = document.createElement("p");
    note.className = "admin-section-note admin-section-note-left";
    note.textContent = text;
    return note;
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

  const detailValue = (value) => {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    return JSON.stringify(value, null, 2);
  };

  const mappingToDetailEntries = (mapping, source = "identity_read_model", omitKeys = []) => {
    const data = mapping && typeof mapping === "object" && !Array.isArray(mapping) ? mapping : {};
    const omitted = new Set(Array.isArray(omitKeys) ? omitKeys : []);
    return Object.keys(data)
      .filter((key) => !omitted.has(key))
      .sort()
      .map((key) => [
        key,
        {
          label: key
            .split("_")
            .filter(Boolean)
            .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
            .join(" "),
          value: detailValue(data[key]),
          source,
        },
      ]);
  };

  const renderReadonlyCollectionDetailed = (target, items, options = {}) => {
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
      renderReadonlyEntries(grid, mappingToDetailEntries(item, options.source || "identity_read_model"));
      group.appendChild(grid);
      target.appendChild(group);
    });
  };

  const appendMetaChip = (target, label, value, formatter = (raw) => raw) => {
    if (!target) return;
    const formatted = formatter(value);
    if (!formatted) return;
    target.appendChild(createChip(`${label}=${formatted}`));
  };

  const hasContent = (layer) => toText(layer?.content).length > 0;

  const stateLabel = (present) => (present ? "Presente" : "Absente");
  const runtimeLabel = (loaded) => (loaded ? "Charge" : "Non charge");
  const injectionLabel = (injected) => (injected ? "Injecte" : "Non injecte");

  const summarizeStaticLayer = (layer) => {
    const present = hasContent(layer);
    return [
      stateLabel(present),
      runtimeLabel(Boolean(layer?.loaded_for_runtime)),
      injectionLabel(Boolean(layer?.actively_injected)),
    ].join(", ");
  };

  const summarizeMutableLayer = (layer) => {
    const present = hasContent(layer);
    const parts = [
      stateLabel(present),
      runtimeLabel(Boolean(layer?.loaded_for_runtime)),
      injectionLabel(Boolean(layer?.actively_injected)),
    ];
    if (toText(layer?.updated_by)) {
      parts.push(`maj par ${toText(layer.updated_by)}`);
    }
    return parts.join(", ");
  };

  const identityStaging = (payload) =>
    payload?.identity_staging &&
    typeof payload.identity_staging === "object" &&
    !Array.isArray(payload.identity_staging)
      ? payload.identity_staging
      : {};

  const latestAgentActivity = (staging) =>
    staging?.latest_agent_activity &&
    typeof staging.latest_agent_activity === "object" &&
    !Array.isArray(staging.latest_agent_activity)
      ? staging.latest_agent_activity
      : {};

  const renderIdentityStaging = (target, staging, viewMode) => {
    const group = document.createElement("section");
    group.className = "admin-readonly-group";

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = "Staging identitaire";
    head.appendChild(title);
    group.appendChild(head);

    group.appendChild(
      createNote(
        "Le staging periodique garde des paires user/assistant hors canon actif. Il alimente l'agent identitaire, mais n'est injecte ni dans `identity_input`, ni dans le bloc runtime final.",
      ),
    );

    const activity = latestAgentActivity(staging);
    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`present=${Boolean(staging.present)}`));
    meta.appendChild(createChip(`injecte=${Boolean(staging.actively_injected)}`));
    meta.appendChild(
      createChip(
        `buffer=${Number(staging.buffer_pairs_count) || 0}/${Number(staging.buffer_target_pairs) || 0}`,
      ),
    );
    meta.appendChild(createChip(`gele=${Boolean(staging.buffer_frozen)}`));
    meta.appendChild(createChip(`suspendu=${Boolean(staging.auto_canonization_suspended)}`));
    if (toText(staging.last_agent_status)) {
      meta.appendChild(createChip(`agent=${toText(staging.last_agent_status)}`));
    }
    if (Number(activity.promotion_count) > 0) {
      meta.appendChild(createChip(`promotions=${Number(activity.promotion_count)}`));
    }
    group.appendChild(meta);

    const summaryEntries = [
      [
        "scope_kind",
        {
          label: "Portee",
          value: toText(staging.scope_kind) || "n/a",
          source: "identity_read_model",
        },
      ],
      [
        "conversation_id",
        {
          label: "Conversation",
          value: toText(staging.conversation_id) || "n/a",
          source: "identity_read_model",
        },
      ],
      [
        "buffer_pairs_count",
        {
          label: "Buffer courant",
          value: `${Number(staging.buffer_pairs_count) || 0}/${Number(staging.buffer_target_pairs) || 0}`,
          source: "identity_read_model",
        },
      ],
      [
        "last_agent_status",
        {
          label: "Dernier statut agent",
          value: toText(staging.last_agent_status) || "n/a",
          source: "identity_read_model",
        },
      ],
      [
        "last_agent_reason",
        {
          label: "Derniere raison",
          value: toText(staging.last_agent_reason) || "n/a",
          source: "identity_read_model",
        },
      ],
      [
        "last_agent_run_ts",
        {
          label: "Dernier passage",
          value: toText(staging.last_agent_run_ts) || "n/a",
          source: "identity_read_model",
        },
      ],
      [
        "auto_canonization_suspended",
        {
          label: "Suspension automatique",
          value: String(Boolean(staging.auto_canonization_suspended)),
          source: "identity_read_model",
        },
      ],
      [
        "latest_agent_verdict",
        {
          label: "Dernier verdict utile",
          value: toText(activity.reason_code) || "n/a",
          source: "identity_read_model",
        },
      ],
    ];

    const summaryGrid = document.createElement("div");
    summaryGrid.className = "admin-readonly-grid";
    renderReadonlyEntries(summaryGrid, summaryEntries);
    group.appendChild(summaryGrid);

    if (viewMode === "full" && activity.present) {
      const activityGroup = document.createElement("section");
      activityGroup.className = "admin-readonly-group";
      const activityHead = document.createElement("div");
      activityHead.className = "admin-readonly-group-head";
      const activityTitle = document.createElement("h4");
      activityTitle.textContent = "Derniere activite agent";
      activityHead.appendChild(activityTitle);
      activityGroup.appendChild(activityHead);

      const activityGrid = document.createElement("div");
      activityGrid.className = "admin-readonly-grid";
      renderReadonlyEntries(
        activityGrid,
        mappingToDetailEntries(activity, "identity_read_model", ["promotions"]),
      );
      activityGroup.appendChild(activityGrid);

      if (Array.isArray(activity.promotions) && activity.promotions.length) {
        const promotionsHost = document.createElement("div");
        renderReadonlyCollectionDetailed(promotionsHost, activity.promotions, {
          emptyMessage: "Aucune promotion recente.",
          source: "identity_read_model",
          identifyTitle: (item, index) =>
            toText(item?.subject) || `Promotion ${index + 1}`,
        });
        activityGroup.appendChild(promotionsHost);
      }

      group.appendChild(activityGroup);
    }

    target.appendChild(group);
  };

  const renderLayer = (subjectGroup, layerSpec, layer) => {
    if (!layer || typeof layer !== "object" || Array.isArray(layer)) {
      return;
    }

    const layerGroup = document.createElement("section");
    layerGroup.className = "admin-readonly-group";
    const layerHead = document.createElement("div");
    layerHead.className = "admin-readonly-group-head";
    const layerTitle = document.createElement("h4");
    layerTitle.textContent = layerSpec.label;
    layerHead.appendChild(layerTitle);
    layerGroup.appendChild(layerHead);

    const layerMeta = document.createElement("div");
    layerMeta.className = "admin-card-meta";
    appendMetaChip(layerMeta, "storage", toText(layer.storage_kind));
    layerMeta.appendChild(createChip(`stored=${Boolean(layer.stored)}`));
    layerMeta.appendChild(createChip(`charge=${Boolean(layer.loaded_for_runtime)}`));
    layerMeta.appendChild(createChip(`injection_active=${Boolean(layer.actively_injected)}`));
    if (layer.total_count != null) {
      layerMeta.appendChild(createChip(`count=${Number(layer.total_count) || 0}`));
    }
    layerGroup.appendChild(layerMeta);

    const summaryGrid = document.createElement("div");
    summaryGrid.className = "admin-readonly-grid";
    renderReadonlyEntries(summaryGrid, mappingToDetailEntries(layer, "identity_read_model", ["items"]));
    layerGroup.appendChild(summaryGrid);

    if (layerSpec.key !== "static" && layerSpec.key !== "mutable") {
      const itemsHost = document.createElement("div");
      renderReadonlyCollectionDetailed(itemsHost, layer.items, {
        emptyMessage: layerSpec.emptyMessage,
        source: "identity_read_model",
        identifyTitle: layerSpec.identifyTitle,
      });
      layerGroup.appendChild(itemsHost);
    }

    subjectGroup.appendChild(layerGroup);
  };

  const renderSubjectSummary = (target, subjectKey, subject) => {
    const subjectGroup = document.createElement("section");
    subjectGroup.className = "admin-readonly-group";

    const subjectHead = document.createElement("div");
    subjectHead.className = "admin-readonly-group-head";
    const subjectTitle = document.createElement("h4");
    subjectTitle.textContent = subjectKey;
    subjectHead.appendChild(subjectTitle);
    subjectGroup.appendChild(subjectHead);

    subjectGroup.appendChild(
      createNote(
        "Le detail editable du statique et de la mutable reste dans Pilotage canonique actif. Ici, on garde une synthese par sujet et les volumes historiques utiles.",
      ),
    );

    const staticLayer = subject.static || {};
    const mutableLayer = subject.mutable || {};
    const legacyLayer = subject.legacy_fragments || {};
    const evidenceLayer = subject.evidence || {};
    const conflictsLayer = subject.conflicts || {};

    const subjectMeta = document.createElement("div");
    subjectMeta.className = "admin-card-meta";
    subjectMeta.appendChild(createChip(`statique=${stateLabel(hasContent(staticLayer)).toLowerCase()}`));
    subjectMeta.appendChild(createChip(`mutable=${stateLabel(hasContent(mutableLayer)).toLowerCase()}`));
    subjectMeta.appendChild(createChip(`legacy=${Number(legacyLayer.total_count) || 0}`));
    subjectMeta.appendChild(createChip(`evidence=${Number(evidenceLayer.total_count) || 0}`));
    subjectMeta.appendChild(createChip(`conflicts=${Number(conflictsLayer.total_count) || 0}`));
    subjectGroup.appendChild(subjectMeta);

    const summaryGrid = document.createElement("div");
    summaryGrid.className = "admin-readonly-grid";
    renderReadonlyEntries(summaryGrid, [
      [
        "static_summary",
        {
          label: "Statique canonique",
          value: summarizeStaticLayer(staticLayer),
          source: "identity_read_model",
        },
      ],
      [
        "mutable_summary",
        {
          label: "Mutable canonique",
          value: summarizeMutableLayer(mutableLayer),
          source: "identity_read_model",
        },
      ],
      [
        "legacy_summary",
        {
          label: "Fragments legacy",
          value: `${Number(legacyLayer.total_count) || 0} element(s) visibles plus bas`,
          source: "identity_read_model",
        },
      ],
      [
        "evidence_summary",
        {
          label: "Evidences",
          value: `${Number(evidenceLayer.total_count) || 0} element(s) visibles plus bas`,
          source: "identity_read_model",
        },
      ],
      [
        "conflicts_summary",
        {
          label: "Conflits",
          value: `${Number(conflictsLayer.total_count) || 0} element(s) visibles plus bas`,
          source: "identity_read_model",
        },
      ],
    ]);
    subjectGroup.appendChild(summaryGrid);
    target.appendChild(subjectGroup);
  };

  const renderSubject = (target, subjectKey, subject) => {
    const subjectGroup = document.createElement("section");
    subjectGroup.className = "admin-readonly-group";

    const subjectHead = document.createElement("div");
    subjectHead.className = "admin-readonly-group-head";
    const subjectTitle = document.createElement("h4");
    subjectTitle.textContent = subjectKey;
    subjectHead.appendChild(subjectTitle);
    subjectGroup.appendChild(subjectHead);

    const subjectMeta = document.createElement("div");
    subjectMeta.className = "admin-card-meta";
    const staticLayer = subject.static || {};
    const mutableLayer = subject.mutable || {};
    const legacyLayer = subject.legacy_fragments || {};
    const evidenceLayer = subject.evidence || {};
    const conflictsLayer = subject.conflicts || {};
    subjectMeta.appendChild(createChip(`static_injecte=${Boolean(staticLayer.actively_injected)}`));
    subjectMeta.appendChild(createChip(`mutable_injecte=${Boolean(mutableLayer.actively_injected)}`));
    subjectMeta.appendChild(createChip(`legacy=${Number(legacyLayer.total_count) || 0}`));
    subjectMeta.appendChild(createChip(`evidence=${Number(evidenceLayer.total_count) || 0}`));
    subjectMeta.appendChild(createChip(`conflicts=${Number(conflictsLayer.total_count) || 0}`));
    subjectGroup.appendChild(subjectMeta);

    [
      {
        key: "static",
        label: "Statique canonique",
        identifyTitle: (_item, index) => `Static ${index + 1}`,
        emptyMessage: "Aucun contenu statique charge.",
      },
      {
        key: "mutable",
        label: "Mutable canonique",
        identifyTitle: (_item, index) => `Mutable ${index + 1}`,
        emptyMessage: "Aucune mutable narrative stockee.",
      },
      {
        key: "legacy_fragments",
        label: "Fragments legacy",
        identifyTitle: (item, index) => toText(item?.identity_id) || `Fragment ${index + 1}`,
        emptyMessage: "Aucun fragment legacy pour ce sujet.",
      },
      {
        key: "evidence",
        label: "Evidences",
        identifyTitle: (item, index) => toText(item?.evidence_id) || `Evidence ${index + 1}`,
        emptyMessage: "Aucune evidence pour ce sujet.",
      },
      {
        key: "conflicts",
        label: "Conflits",
        identifyTitle: (item, index) => toText(item?.conflict_id) || `Conflict ${index + 1}`,
        emptyMessage: "Aucun conflit pour ce sujet.",
      },
    ].forEach((layerSpec) => {
      renderLayer(subjectGroup, layerSpec, subject[layerSpec.key]);
    });

    target.appendChild(subjectGroup);
  };

  const renderIdentityReadModel = (metaTarget, target, payload, options = {}) => {
    if (!target) return;
    target.innerHTML = "";
    if (metaTarget) metaTarget.innerHTML = "";

    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const activeRuntime =
      safePayload.active_runtime &&
      typeof safePayload.active_runtime === "object" &&
      !Array.isArray(safePayload.active_runtime)
        ? safePayload.active_runtime
        : {};
    const subjects =
      safePayload.subjects && typeof safePayload.subjects === "object" && !Array.isArray(safePayload.subjects)
        ? safePayload.subjects
        : {};
    const staging = identityStaging(safePayload);
    const viewMode = toText(options.viewMode).toLowerCase() === "summary" ? "summary" : "full";

    if (metaTarget) {
      appendMetaChip(metaTarget, "read_model", toText(safePayload.read_model_version) || "n/a");
      appendMetaChip(metaTarget, "canonique_mutable", toText(activeRuntime.active_identity_source));
      appendMetaChip(metaTarget, "compile", toText(activeRuntime.active_prompt_contract));
      metaTarget.appendChild(createChip("pilotage_systeme=distinct"));
      metaTarget.appendChild(createChip("staging=separe"));
      appendMetaChip(metaTarget, "identity_input", toText(activeRuntime.identity_input_schema_version));
      metaTarget.appendChild(createChip(`used_ids=${Number(activeRuntime.used_identity_ids_count) || 0}`));
      if (toText(staging.last_agent_status)) {
        metaTarget.appendChild(createChip(`agent=${toText(staging.last_agent_status)}`));
      }
    }

    if (viewMode === "full") {
      const runtimeGroup = document.createElement("section");
      runtimeGroup.className = "admin-readonly-group";
      const runtimeHead = document.createElement("div");
      runtimeHead.className = "admin-readonly-group-head";
      const runtimeTitle = document.createElement("h4");
      runtimeTitle.textContent = "Repères runtime et compilation active";
      runtimeHead.appendChild(runtimeTitle);
      runtimeGroup.appendChild(runtimeHead);
      runtimeGroup.appendChild(
        createNote(
          "Ce bloc resume le runtime actif et le contrat de compilation de l'identite. Il ne remplace ni les couches canoniques statique/mutable, ni le pilotage systeme distinct.",
        ),
      );
      const runtimeGrid = document.createElement("div");
      runtimeGrid.className = "admin-readonly-grid";
      renderReadonlyEntries(runtimeGrid, mappingToDetailEntries(activeRuntime, "identity_read_model"));
      runtimeGroup.appendChild(runtimeGrid);
      target.appendChild(runtimeGroup);
    }

    renderIdentityStaging(target, staging, viewMode);

    [["llm", "llm"], ["user", "user"]].forEach(([subjectKey, label]) => {
      const subject = subjects[subjectKey];
      if (!subject || typeof subject !== "object" || Array.isArray(subject)) {
        return;
      }
      if (viewMode === "summary") {
        renderSubjectSummary(target, label, subject);
        return;
      }
      renderSubject(target, label, subject);
    });
  };

  window.FridaHermeneuticIdentityReadModelRender = Object.freeze({
    renderIdentityReadModel,
  });
})();
