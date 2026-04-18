(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error(
      "admin_ui_common.js must be loaded before hermeneutic_admin/render_identity_governance.js",
    );
  }

  const toText = (value) => String(value == null ? "" : value).trim();
  const ITEM_CATEGORY_LABELS = Object.freeze({
    active_runtime_editable: "Runtime editable",
    active_subpipeline_editable: "Sous-pipeline editable",
    doctrine_locked_readonly: "Doctrine verrouillee",
    active_runtime_readonly: "Readonly runtime actif",
    active_subpipeline_readonly: "Readonly actif",
    legacy_inactive_readonly: "Legacy inactif",
  });
  const ITEM_CATEGORY_ORDER = Object.freeze([
    "active_runtime_editable",
    "active_subpipeline_editable",
    "doctrine_locked_readonly",
    "active_runtime_readonly",
    "active_subpipeline_readonly",
    "legacy_inactive_readonly",
  ]);
  const REGIME_CLASSIFICATION_LABELS = Object.freeze({
    active_readonly: "Regime actif readonly",
    doctrine_locked: "Doctrine verrouillee",
    legacy_inactive: "Legacy inactif",
  });
  const REGIME_CLASSIFICATION_ORDER = Object.freeze([
    "active_readonly",
    "doctrine_locked",
    "legacy_inactive",
  ]);

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

  const renderReadonlyEntries = (target, entries) => {
    adminUi.renderReadonlyInfoEntries(target, entries);
  };

  const detailValue = (value) => {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    return JSON.stringify(value, null, 2);
  };

  const mappingToEntries = (mapping, source = "identity_governance") => {
    const data = mapping && typeof mapping === "object" && !Array.isArray(mapping) ? mapping : {};
    return Object.keys(data)
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

  const normalizeItems = (payload) => {
    const items = payload?.items;
    if (!Array.isArray(items)) return [];
    return items.filter((item) => item && typeof item === "object" && !Array.isArray(item));
  };

  const normalizeRegimeSections = (payload) => {
    const sections = payload?.regime_sections;
    if (!Array.isArray(sections)) return [];
    return sections.filter((section) => section && typeof section === "object" && !Array.isArray(section));
  };

  const inputTypeFor = (valueType) => {
    if (valueType === "int" || valueType === "float") {
      return "number";
    }
    return "text";
  };

  const inputStepFor = (valueType) => {
    if (valueType === "float") return "0.01";
    if (valueType === "int") return "1";
    return "";
  };

  const renderEditableForm = (target, item) => {
    if (!item.editable) return;

    const form = document.createElement("form");
    form.className = "admin-form";
    form.dataset.identityGovernanceKey = toText(item.key);
    form.addEventListener("submit", (event) => event.preventDefault());

    const grid = document.createElement("div");
    grid.className = "admin-form-grid";

    const valueField = document.createElement("label");
    valueField.className = "admin-field";
    const valueLabel = document.createElement("span");
    valueLabel.textContent = "Valeur";
    valueField.appendChild(valueLabel);
    const valueInput = document.createElement("input");
    valueInput.type = inputTypeFor(item.value_type);
    valueInput.step = inputStepFor(item.value_type);
    valueInput.name = "value";
    valueInput.dataset.valueType = toText(item.value_type);
    valueInput.value = detailValue(item.current_value);
    valueField.appendChild(valueInput);
    grid.appendChild(valueField);

    const reasonField = document.createElement("label");
    reasonField.className = "admin-field";
    const reasonLabel = document.createElement("span");
    reasonLabel.textContent = "Justification operateur";
    reasonField.appendChild(reasonLabel);
    const reasonInput = document.createElement("input");
    reasonInput.type = "text";
    reasonInput.name = "reason";
    reasonInput.maxLength = 240;
    reasonInput.placeholder = "Pourquoi changer ce knob ?";
    reasonField.appendChild(reasonInput);
    grid.appendChild(reasonField);

    form.appendChild(grid);

    const actions = document.createElement("div");
    actions.className = "admin-inline-actions";
    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "admin-btn";
    saveButton.dataset.identityGovernanceSave = "true";
    saveButton.dataset.identityGovernanceKey = toText(item.key);
    saveButton.textContent = "Enregistrer";
    actions.appendChild(saveButton);
    form.appendChild(actions);

    target.appendChild(form);
  };

  const renderGroupTitle = (target, titleText, noteText = "") => {
    const wrapper = document.createElement("section");
    wrapper.className = "admin-readonly-group";

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = titleText;
    head.appendChild(title);
    wrapper.appendChild(head);

    if (noteText) {
      const note = document.createElement("p");
      note.className = "admin-section-note admin-section-note-left";
      note.textContent = noteText;
      wrapper.appendChild(note);
    }

    target.appendChild(wrapper);
  };

  const renderItem = (target, item) => {
    const card = document.createElement("section");
    card.className = "admin-readonly-group";
    card.dataset.identityGovernanceKey = toText(item.key);

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = toText(item.label) || toText(item.key) || "Knob";
    head.appendChild(title);
    card.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`key=${toText(item.key) || "n/a"}`));
    meta.appendChild(createChip(`category=${toText(item.category) || "n/a"}`));
    meta.appendChild(createChip(`scope=${toText(item.active_scope) || "n/a"}`));
    meta.appendChild(createChip(`editable=${Boolean(item.editable)}`));
    if (toText(item.unit)) {
      meta.appendChild(createChip(`unit=${toText(item.unit)}`));
    }
    card.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(
        {
          current_value: item.current_value,
          value_type: item.value_type,
          source_kind: item.source_kind,
          source_ref: item.source_ref,
          editable_via: item.editable_via,
          source_state: item.source_state,
          source_reason: item.source_reason,
          validation: item.validation,
          operator_note: item.operator_note,
        },
        "identity_governance",
      ),
    );
    card.appendChild(summary);

    renderEditableForm(card, item);
    target.appendChild(card);
  };

  const renderRegimeSection = (target, section) => {
    const card = document.createElement("section");
    card.className = "admin-readonly-group";
    card.dataset.identityGovernanceSection = toText(section.key);

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = toText(section.label) || toText(section.key) || "Regime";
    head.appendChild(title);
    card.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(
      createChip(
        REGIME_CLASSIFICATION_LABELS[toText(section.classification)] || `classification=${toText(section.classification) || "n/a"}`,
      ),
    );
    meta.appendChild(createChip(`scope=${toText(section.active_scope) || "n/a"}`));
    meta.appendChild(createChip(`editable=${Boolean(section.editable)}`));
    card.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(
        {
          source_kind: section.source_kind,
          source_ref: section.source_ref,
          details: section.details,
          operator_note: section.operator_note,
        },
        "identity_governance_regime",
      ),
    );
    card.appendChild(summary);
    target.appendChild(card);
  };

  const renderItemsByCategory = (target, items) => {
    const grouped = new Map();
    ITEM_CATEGORY_ORDER.forEach((category) => grouped.set(category, []));
    items.forEach((item) => {
      const category = toText(item.category);
      if (!grouped.has(category)) {
        grouped.set(category, []);
      }
      grouped.get(category).push(item);
    });

    Array.from(grouped.entries()).forEach(([category, groupItems]) => {
      if (!groupItems.length) return;
      renderGroupTitle(
        target,
        ITEM_CATEGORY_LABELS[category] || category,
        category === "doctrine_locked_readonly"
          ? "Caps visibles mais non reouverts a l edition."
          : category === "legacy_inactive_readonly"
            ? "Survivances legacy relisibles sans role actif dans le regime runtime."
            : "",
      );
      groupItems.forEach((item) => renderItem(target, item));
    });
  };

  const renderRegimeSectionsByClassification = (target, sections) => {
    const grouped = new Map();
    REGIME_CLASSIFICATION_ORDER.forEach((classification) => grouped.set(classification, []));
    sections.forEach((section) => {
      const classification = toText(section.classification);
      if (!grouped.has(classification)) {
        grouped.set(classification, []);
      }
      grouped.get(classification).push(section);
    });

    Array.from(grouped.entries()).forEach(([classification, groupSections]) => {
      if (!groupSections.length) return;
      renderGroupTitle(
        target,
        REGIME_CLASSIFICATION_LABELS[classification] || classification,
        classification === "active_readonly"
          ? "Contrat du regime identity actif: staging, scoring, promotion et suspension restent visibles ici sans etre edites comme de simples knobs."
          : classification === "doctrine_locked"
            ? "Doctrine visible, bornee et volontairement non editable."
            : "Legacy conserve pour diagnostic seulement.",
      );
      groupSections.forEach((section) => renderRegimeSection(target, section));
    });
  };

  const renderIdentityGovernance = (metaTarget, target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    if (metaTarget) metaTarget.innerHTML = "";

    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const items = normalizeItems(safePayload);
    const regimeSections = normalizeRegimeSections(safePayload);
    if (!items.length && !regimeSections.length) {
      renderEmpty(target, "Aucun knob identity gouvernable ou visible.");
      return;
    }

    if (metaTarget) {
      metaTarget.appendChild(createChip(`version=${toText(safePayload.governance_version) || "n/a"}`));
      metaTarget.appendChild(createChip(`editable=${Number(safePayload.editable_count) || 0}`));
      metaTarget.appendChild(createChip(`readonly=${Number(safePayload.readonly_count) || 0}`));
      metaTarget.appendChild(createChip(`doctrine_locked=${Number(safePayload.doctrine_locked_count) || 0}`));
      metaTarget.appendChild(createChip(`legacy=${Number(safePayload.legacy_inactive_count) || 0}`));
      metaTarget.appendChild(createChip(`active_runtime=${Number(safePayload.active_runtime_count) || 0}`));
      metaTarget.appendChild(createChip(`active_subpipeline=${Number(safePayload.active_subpipeline_count) || 0}`));
      metaTarget.appendChild(createChip(`regime_sections=${Number(safePayload.regime_section_count) || 0}`));
    }

    target.appendChild(
      (() => {
        const note = document.createElement("p");
        note.className = "admin-section-note admin-section-note-left";
        note.textContent =
          "La gouvernance identity ne se limite pas aux caps 3000/3300: elle distingue les knobs editables, le regime actif readonly, la doctrine verrouillee et le legacy inactif.";
        return note;
      })(),
    );

    if (regimeSections.length) {
      renderRegimeSectionsByClassification(target, regimeSections);
    }
    if (items.length) {
      renderItemsByCategory(target, items);
    }
  };

  const coerceDraftValue = (input) => {
    const valueType = toText(input?.dataset?.valueType).toLowerCase();
    const rawValue = toText(input?.value);
    if (valueType === "int") {
      return Number.parseInt(rawValue, 10);
    }
    if (valueType === "float") {
      return Number.parseFloat(rawValue);
    }
    return rawValue;
  };

  const readIdentityGovernanceDraft = (trigger) => {
    const button = trigger?.closest?.("[data-identity-governance-save]");
    if (!button) return null;
    const key = toText(button.dataset.identityGovernanceKey);
    const form = button.closest("form[data-identity-governance-key]");
    if (!key || !form) return null;
    const valueInput = form.querySelector('input[name="value"]');
    const reasonInput = form.querySelector('input[name="reason"]');
    return {
      key,
      updates: { [key]: coerceDraftValue(valueInput) },
      reason: toText(reasonInput?.value),
    };
  };

  const setIdentityGovernanceStatus = (target, payload, state = "") => {
    if (!target) return;
    target.innerHTML = "";
    if (!payload) return;

    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const message = document.createElement("p");
    message.className = "admin-section-note admin-section-note-left";
    if (state) {
      message.dataset.state = state;
    } else {
      delete message.dataset.state;
    }
    if (safePayload.ok) {
      message.textContent =
        safePayload.reason_code === "unchanged"
          ? "Gouvernance identity deja identique."
          : "Gouvernance identity mise a jour.";
    } else {
      message.textContent = toText(safePayload.error) || "Gouvernance identity indisponible.";
    }
    target.appendChild(message);

    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    const status = safePayload.ok ? "ok" : "error";
    meta.appendChild(createChip(`changed=${Number(safePayload.changed_count) || 0}`, { status }));
    meta.appendChild(createChip(`reason_code=${toText(safePayload.reason_code) || "n/a"}`, { status }));
    meta.appendChild(createChip(`validation_ok=${Boolean(safePayload.validation_ok)}`, { status }));
    if (toText(safePayload.validation_error)) {
      meta.appendChild(createChip(`validation=${toText(safePayload.validation_error)}`, { status }));
    }
    if (Array.isArray(safePayload.changed_keys) && safePayload.changed_keys.length) {
      meta.appendChild(createChip(`keys=${safePayload.changed_keys.join(",")}`, { status }));
    }
    target.appendChild(meta);
  };

  window.FridaHermeneuticIdentityGovernance = Object.freeze({
    renderIdentityGovernance,
    readIdentityGovernanceDraft,
    setIdentityGovernanceStatus,
  });
})();
