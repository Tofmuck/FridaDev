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
    { key: "legacy_fragments", label: "Fragments legacy diagnostiques" },
    { key: "evidence", label: "Evidences legacy diagnostiques" },
    { key: "conflicts", label: "Conflits legacy diagnostiques" },
  ];

  const toText = (value) => String(value == null ? "" : value).trim();

  const createChip = (text) => {
    const chip = document.createElement("span");
    chip.className = "admin-chip";
    chip.textContent = text;
    return chip;
  };

  const createSummaryCard = ({ title, body, chips }) => {
    const card = document.createElement("article");
    card.className = "admin-card";

    const head = document.createElement("div");
    head.className = "admin-card-head";
    const heading = document.createElement("h3");
    heading.textContent = title;
    head.appendChild(heading);
    card.appendChild(head);

    const copy = document.createElement("p");
    copy.textContent = body;
    card.appendChild(copy);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    chips.forEach((chipText) => meta.appendChild(createChip(chipText)));
    card.appendChild(meta);
    return card;
  };
  const createNote = (text) => {
    const note = document.createElement("p");
    note.className = "admin-section-note admin-section-note-left";
    note.textContent = text;
    return note;
  };

  const identityStaging = (payload) =>
    payload?.identity_staging && typeof payload.identity_staging === "object" && !Array.isArray(payload.identity_staging)
      ? payload.identity_staging
      : {};

  const latestAgentActivity = (staging) =>
    staging?.latest_agent_activity &&
    typeof staging.latest_agent_activity === "object" &&
    !Array.isArray(staging.latest_agent_activity)
      ? staging.latest_agent_activity
      : {};

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
    meta.appendChild(createChip(`forme=compilee`));
    meta.appendChild(createChip(`usage=jugement`));
    meta.appendChild(createChip(`source=canonique`));
    target.appendChild(meta);

    target.appendChild(
      createNote(
        "Cette vue montre une projection structuree compilee pour le jugement hermeneutique. La source canonique reste le statique et la mutable; le staging periodique reste separe et non injecte.",
      ),
    );

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      [
        [
          "representation_kind",
          {
            label: "Nature",
            value: "Projection runtime compilee pour le jugement",
            source: "identity_runtime_representations",
          },
        ],
        [
          "canonical_source",
          {
            label: "Source canonique",
            value: "Statique + mutable canoniques",
            source: "identity_runtime_representations",
          },
        ],
        [
          "system_guidance",
          {
            label: "Pilotage systeme",
            value: "Distinct, hors de cette vue",
            source: "identity_runtime_representations",
          },
        ],
        ["staging_included", { label: "Staging injecte", value: "False", source: "identity_runtime_representations" }],
        [
          "technical_name",
          {
            label: "Nom technique",
            value: toText(safePayload.technical_name) || "n/a",
            source: "identity_runtime_representations",
          },
        ],
        [
          "role",
          {
            label: "Usage runtime",
            value: toText(safePayload.role) || "n/a",
            source: "identity_runtime_representations",
          },
        ],
        [
          "schema_version",
          {
            label: "Schema",
            value: toText(safePayload.schema_version) || "n/a",
            source: "identity_runtime_representations",
          },
        ],
        [
          "present",
          {
            label: "Present",
            value: String(Boolean(safePayload.present)),
            source: "identity_runtime_representations",
          },
        ],
      ],
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
    meta.appendChild(createChip(`forme=compilee`));
    meta.appendChild(createChip(`usage=reponse_finale`));
    meta.appendChild(createChip(`source=canonique`));
    meta.appendChild(createChip(`len=${content.length}`));
    meta.appendChild(createChip(`used_ids=${Number(usedIdentityIdsCount) || 0}`));
    target.appendChild(meta);

    target.appendChild(
      createNote(
        "Ce texte est la forme runtime compilee de l'identite injectee pour la reponse finale. Il ne remplace ni la source canonique statique/mutable, ni le staging periodique distinct.",
      ),
    );

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      [
        [
          "representation_kind",
          {
            label: "Nature",
            value: "Forme runtime compilee injectee",
            source: "identity_runtime_representations",
          },
        ],
        [
          "canonical_source",
          {
            label: "Source canonique",
            value: "Statique + mutable canoniques",
            source: "identity_runtime_representations",
          },
        ],
        [
          "system_guidance",
          {
            label: "Pilotage systeme",
            value: "Distinct, hors de cette vue",
            source: "identity_runtime_representations",
          },
        ],
        ["staging_included", { label: "Staging injecte", value: "False", source: "identity_runtime_representations" }],
        [
          "technical_name",
          {
            label: "Nom technique",
            value: toText(safePayload.technical_name) || "n/a",
            source: "identity_runtime_representations",
          },
        ],
        [
          "role",
          {
            label: "Slot technique",
            value: toText(safePayload.role) || "n/a",
            source: "identity_runtime_representations",
          },
        ],
        [
          "present",
          {
            label: "Present",
            value: String(Boolean(safePayload.present)),
            source: "identity_runtime_representations",
          },
        ],
        [
          "used_identity_ids_count",
          {
            label: "Ids legacy utilises",
            value: String(Number(usedIdentityIdsCount) || 0),
            source: "identity_runtime_representations",
          },
        ],
      ],
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
    if (toText(safeLayer.classification)) {
      meta.appendChild(createChip(`couche=${toText(safeLayer.classification)}`));
    }
    if (toText(safeLayer.runtime_authority)) {
      meta.appendChild(createChip(`runtime=${toText(safeLayer.runtime_authority)}`));
    }
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
      itemHead.appendChild(createChip("legacy diagnostique"));
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
      renderEmpty(target, "Aucune couche legacy diagnostique disponible.");
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
        "Ces couches viennent du pipeline legacy diagnostique (`persist_identity_entries`) et restent hors canon actif comme hors staging.";
      group.appendChild(note);

      LEGACY_LAYERS.forEach(({ key: layerKey, label: layerLabel }) => {
        renderLayerItems(group, subject[layerKey], layerLabel);
      });

      target.appendChild(group);
    });
  };

  const renderIdentityRuntimeRepresentationsMeta = (metaTarget, payload) => {
    if (metaTarget) {
      metaTarget.innerHTML = "";
    }
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    if (metaTarget) {
      metaTarget.appendChild(createChip(`version=${toText(safePayload.representations_version) || "n/a"}`));
      metaTarget.appendChild(createChip(`compile=${toText(safePayload.active_prompt_contract) || "n/a"}`));
      metaTarget.appendChild(createChip(`schema=${toText(safePayload.identity_input_schema_version) || "n/a"}`));
      metaTarget.appendChild(createChip("pilotage_systeme=distinct"));
      metaTarget.appendChild(createChip("staging=separe"));
      metaTarget.appendChild(createChip(`meme_base=${Boolean(safePayload.same_identity_basis)}`));
      metaTarget.appendChild(createChip(`used_ids=${Number(safePayload.used_identity_ids_count) || 0}`));
    }
  };

  const renderIdentityRuntimeSummary = (metaTarget, summaryTarget, payload) => {
    if (!summaryTarget) return;
    summaryTarget.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const structured = safePayload.structured_identity && typeof safePayload.structured_identity === "object"
      ? safePayload.structured_identity
      : {};
    const injected = safePayload.injected_identity_text && typeof safePayload.injected_identity_text === "object"
      ? safePayload.injected_identity_text
      : {};
    const staging = identityStaging(safePayload);
    const activity = latestAgentActivity(staging);
    const stagingScope = toText(staging.scope_kind);
    const stagingConversationId = toText(staging.conversation_id);
    renderIdentityRuntimeRepresentationsMeta(metaTarget, safePayload);
    summaryTarget.appendChild(
      createSummaryCard({
        title: "Projection jugement",
        body:
          "Repere compact de la fiche compilee `identity_input` lue par le noeud hermeneutique. Le detail complet reste sur Hermeneutic admin.",
        chips: [
          `present=${Boolean(structured.present)}`,
          `schema=${toText(structured.schema_version) || "n/a"}`,
          `meme_base=${Boolean(safePayload.same_identity_basis)}`,
        ],
      }),
    );
    summaryTarget.appendChild(
      createSummaryCard({
        title: "Injection reponse finale",
        body:
          "Repere compact du texte identity compile injecte au modele final. La lecture ligne a ligne quitte le flux principal de /identity.",
        chips: [
          `present=${Boolean(injected.present)}`,
          `len=${String((injected.content || "").length)}`,
          `used_ids=${Number(safePayload.used_identity_ids_count) || 0}`,
        ],
      }),
    );
    summaryTarget.appendChild(
      createSummaryCard({
        title: "Staging periodique observe",
        body:
          `Repere compact du dernier snapshot conversationnel connu${stagingScope ? ` (${stagingScope})` : ""} hors canon actif: il alimente l'agent identitaire, n'est pas un etat global du systeme, et n'est injecte ni au jugement ni a la reponse finale.`,
        chips: [
          `buffer=${Number(staging.buffer_pairs_count) || 0}/${Number(staging.buffer_target_pairs) || 0}`,
          `scope=${stagingScope || "n/a"}`,
          ...(stagingConversationId ? [`conversation=${stagingConversationId}`] : []),
          `agent=${toText(staging.last_agent_status) || "n/a"}`,
          `suspendu=${Boolean(staging.auto_canonization_suspended)}`,
          `promotions=${Number(activity.promotion_count) || 0}`,
          `tensions=${Number(activity.open_tension_count) || 0}`,
        ],
      }),
    );
  };

  const renderIdentityRuntimeRepresentations = (metaTarget, structuredTarget, injectedTarget, payload) => {
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    renderIdentityRuntimeRepresentationsMeta(metaTarget, safePayload);
    renderStructuredRepresentation(structuredTarget, safePayload.structured_identity);
    renderInjectedRepresentation(
      injectedTarget,
      safePayload.injected_identity_text,
      safePayload.used_identity_ids_count,
    );
  };

  window.FridaIdentityRuntimeRepresentationsRender = Object.freeze({
    renderIdentityRuntimeRepresentationsMeta,
    renderIdentityRuntimeSummary,
    renderIdentityRuntimeRepresentations,
    renderLegacyLayers,
  });
})();
