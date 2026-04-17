(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error(
      "admin_ui_common.js must be loaded before hermeneutic_admin/render_identity_governance.js",
    );
  }

  const toText = (value) => String(value == null ? "" : value).trim();

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

  const renderIdentityGovernance = (metaTarget, target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    if (metaTarget) metaTarget.innerHTML = "";

    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const items = normalizeItems(safePayload);
    if (!items.length) {
      renderEmpty(target, "Aucun knob identity gouvernable ou visible.");
      return;
    }

    if (metaTarget) {
      metaTarget.appendChild(createChip(`version=${toText(safePayload.governance_version) || "n/a"}`));
      metaTarget.appendChild(createChip(`editable=${Number(safePayload.editable_count) || 0}`));
      metaTarget.appendChild(createChip(`readonly=${Number(safePayload.readonly_count) || 0}`));
      metaTarget.appendChild(createChip(`legacy=${Number(safePayload.legacy_inactive_count) || 0}`));
      metaTarget.appendChild(createChip(`active_runtime=${Number(safePayload.active_runtime_count) || 0}`));
      metaTarget.appendChild(createChip(`active_subpipeline=${Number(safePayload.active_subpipeline_count) || 0}`));
    }

    target.appendChild(
      (() => {
        const note = document.createElement("p");
        note.className = "admin-section-note admin-section-note-left";
        note.textContent =
          "Les caps 3000/3300 bornent seulement la mutable canonique. Le regime actif comprend aussi le staging a 15 paires, le scoring Python, les promotions vers le statique et la suspension automatique.";
        return note;
      })(),
    );

    items.forEach((item) => renderItem(target, item));
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
