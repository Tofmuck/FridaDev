(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error(
      "admin_ui_common.js must be loaded before identity/render_identity_runtime_representations.js",
    );
  }

  const SUBJECTS = [
    { key: "llm", label: "llm" },
    { key: "user", label: "user" },
  ];

  const LEGACY_LAYERS = [
    { key: "legacy_fragments", label: "Fragments legacy" },
    { key: "evidence", label: "Evidences" },
    { key: "conflicts", label: "Conflits" },
  ];

  const toText = (value) => String(value == null ? "" : value).trim();

  const createChip = (text) => {
    const chip = document.createElement("span");
    chip.className = "admin-chip";
    chip.textContent = text;
    return chip;
  };

  const renderReadonlyEntries = (target, entries) => {
    adminUi.renderReadonlyInfoEntries(target, entries);
  };

  const renderEmpty = (target, message) => {
    if (!target) return;
    target.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "admin-readonly-empty";
    empty.textContent = message;
    target.appendChild(empty);
  };

  const detailValue = (value) => {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    return JSON.stringify(value, null, 2);
  };

  const mappingToEntries = (mapping, source = "identity_runtime_representations", omitKeys = []) => {
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

  const renderPayloadTextarea = (target, text, rows = 14) => {
    const textarea = document.createElement("textarea");
    textarea.className = "admin-readonly-textarea";
    textarea.rows = rows;
    textarea.readOnly = true;
    textarea.value = text;
    target.appendChild(textarea);
  };

  const renderStructuredRepresentation = (target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`present=${Boolean(safePayload.present)}`));
    meta.appendChild(createChip(`schema=${toText(safePayload.schema_version) || "n/a"}`));
    meta.appendChild(createChip(`role=${toText(safePayload.role) || "n/a"}`));
    meta.appendChild(createChip(`nom=${toText(safePayload.technical_name) || "n/a"}`));
    target.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(safePayload, "identity_runtime_representations", ["data"]),
    );
    target.appendChild(summary);

    renderPayloadTextarea(
      target,
      JSON.stringify(safePayload.data || {}, null, 2),
      22,
    );
  };

  const renderInjectedRepresentation = (target, payload, usedIdentityIdsCount) => {
    if (!target) return;
    target.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const content = String(safePayload.content || "");

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`present=${Boolean(safePayload.present)}`));
    meta.appendChild(createChip(`role=${toText(safePayload.role) || "n/a"}`));
    meta.appendChild(createChip(`nom=${toText(safePayload.technical_name) || "n/a"}`));
    meta.appendChild(createChip(`len=${content.length}`));
    meta.appendChild(createChip(`used_ids=${Number(usedIdentityIdsCount) || 0}`));
    target.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(safePayload, "identity_runtime_representations", ["content"]),
    );
    target.appendChild(summary);

    renderPayloadTextarea(target, content, 18);
  };

  const renderLayerItems = (target, layer, layerLabel) => {
    const safeLayer = layer && typeof layer === "object" && !Array.isArray(layer) ? layer : {};
    const items = Array.isArray(safeLayer.items) ? safeLayer.items : [];

    const layerGroup = document.createElement("section");
    layerGroup.className = "admin-readonly-group";

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = layerLabel;
    head.appendChild(title);
    layerGroup.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`count=${Number(safeLayer.total_count) || 0}`));
    meta.appendChild(createChip(`stored=${Boolean(safeLayer.stored)}`));
    meta.appendChild(createChip(`injected=${Boolean(safeLayer.actively_injected)}`));
    layerGroup.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(safeLayer, "identity_read_model", ["items"]),
    );
    layerGroup.appendChild(summary);

    if (!items.length) {
      const note = document.createElement("p");
      note.className = "admin-readonly-empty";
      note.textContent = "Aucun element dans cette couche.";
      layerGroup.appendChild(note);
      target.appendChild(layerGroup);
      return;
    }

    items.forEach((item, index) => {
      const itemPanel = document.createElement("article");
      itemPanel.className = "admin-readonly-panel";

      const itemHead = document.createElement("div");
      itemHead.className = "admin-readonly-head";
      const labelWrap = document.createElement("div");
      const kicker = document.createElement("p");
      kicker.className = "admin-kicker";
      kicker.textContent = `Element ${index + 1}`;
      const itemTitle = document.createElement("h3");
      itemTitle.textContent =
        toText(item?.identity_id) ||
        toText(item?.evidence_id) ||
        toText(item?.conflict_id) ||
        `${layerLabel} ${index + 1}`;
      labelWrap.appendChild(kicker);
      labelWrap.appendChild(itemTitle);
      itemHead.appendChild(labelWrap);
      itemHead.appendChild(createChip("visible seulement"));
      itemPanel.appendChild(itemHead);

      const itemGrid = document.createElement("div");
      itemGrid.className = "admin-readonly-grid";
      renderReadonlyEntries(itemGrid, mappingToEntries(item, "identity_read_model"));
      itemPanel.appendChild(itemGrid);
      layerGroup.appendChild(itemPanel);
    });

    target.appendChild(layerGroup);
  };

  const renderLegacyLayers = (target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    const subjects = payload?.subjects && typeof payload.subjects === "object" ? payload.subjects : {};

    if (!Object.keys(subjects).length) {
      renderEmpty(target, "Aucune couche legacy disponible.");
      return;
    }

    SUBJECTS.forEach(({ key, label }) => {
      const subject = subjects[key];
      if (!subject || typeof subject !== "object" || Array.isArray(subject)) {
        return;
      }

      const group = document.createElement("section");
      group.className = "admin-readonly-group";

      const head = document.createElement("div");
      head.className = "admin-readonly-group-head";
      const title = document.createElement("h4");
      title.textContent = label;
      head.appendChild(title);
      group.appendChild(head);

      const note = document.createElement("p");
      note.className = "admin-section-note admin-section-note-left";
      note.textContent =
        "Ces couches restent consultables pour comprendre l'historique et les contradictions, mais elles restent hors injection active.";
      group.appendChild(note);

      LEGACY_LAYERS.forEach(({ key: layerKey, label: layerLabel }) => {
        renderLayerItems(group, subject[layerKey], layerLabel);
      });

      target.appendChild(group);
    });
  };

  const renderIdentityRuntimeRepresentations = (metaTarget, structuredTarget, injectedTarget, payload) => {
    if (metaTarget) {
      metaTarget.innerHTML = "";
    }
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    if (metaTarget) {
      metaTarget.appendChild(createChip(`version=${toText(safePayload.representations_version) || "n/a"}`));
      metaTarget.appendChild(createChip(`prompt=${toText(safePayload.active_prompt_contract) || "n/a"}`));
      metaTarget.appendChild(createChip(`schema=${toText(safePayload.identity_input_schema_version) || "n/a"}`));
      metaTarget.appendChild(createChip(`meme_base=${Boolean(safePayload.same_identity_basis)}`));
      metaTarget.appendChild(createChip(`used_ids=${Number(safePayload.used_identity_ids_count) || 0}`));
    }
    renderStructuredRepresentation(structuredTarget, safePayload.structured_identity);
    renderInjectedRepresentation(
      injectedTarget,
      safePayload.injected_identity_text,
      safePayload.used_identity_ids_count,
    );
  };

  window.FridaIdentityRuntimeRepresentationsRender = Object.freeze({
    renderIdentityRuntimeRepresentations,
    renderLegacyLayers,
  });
})();
