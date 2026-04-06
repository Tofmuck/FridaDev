(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error(
      "admin_ui_common.js must be loaded before hermeneutic_admin/render_identity_static_editor.js",
    );
  }

  const SUBJECTS = ["llm", "user"];

  const toText = (value) => String(value == null ? "" : value).trim();
  const toRawText = (value) => String(value == null ? "" : value);

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

  const mappingToEntries = (mapping, source = "identity_static_editor") => {
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
          value:
            typeof data[key] === "string" || typeof data[key] === "number" || typeof data[key] === "boolean"
              ? String(data[key])
              : JSON.stringify(data[key], null, 2),
          source,
        },
      ]);
  };

  const subjectStaticLayer = (payload, subject) => {
    const subjects = payload?.subjects && typeof payload.subjects === "object" ? payload.subjects : {};
    const subjectBlock = subjects[subject];
    if (!subjectBlock || typeof subjectBlock !== "object" || Array.isArray(subjectBlock)) {
      return {};
    }
    const layer = subjectBlock.static;
    if (!layer || typeof layer !== "object" || Array.isArray(layer)) {
      return {};
    }
    return layer;
  };

  const renderSubjectEditor = (target, payload, subject) => {
    const staticLayer = subjectStaticLayer(payload, subject);
    const currentContent = toText(staticLayer.content);

    const card = document.createElement("section");
    card.className = "admin-readonly-group";
    card.dataset.identityStaticSubject = subject;

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = `${subject} statique canonique`;
    head.appendChild(title);
    card.appendChild(head);

    const note = document.createElement("p");
    note.className = "admin-section-note admin-section-note-left";
    note.textContent =
      "Edition controlee du contenu statique reel charge par le runtime. Les runtime settings conservent seulement la reference de ressource; la mutable et le legacy restent separes.";
    card.appendChild(note);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`stored=${Boolean(staticLayer.stored)}`));
    meta.appendChild(createChip(`loaded=${Boolean(staticLayer.loaded_for_runtime)}`));
    meta.appendChild(createChip(`injected=${Boolean(staticLayer.actively_injected)}`));
    meta.appendChild(createChip(`len=${currentContent.length}`));
    if (toText(staticLayer.resource_field)) {
      meta.appendChild(createChip(`field=${toText(staticLayer.resource_field)}`));
    }
    if (toText(staticLayer.resolution_kind)) {
      meta.appendChild(createChip(`resolution=${toText(staticLayer.resolution_kind)}`));
    }
    card.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(
        {
          storage_kind: toText(staticLayer.storage_kind) || "resource_path",
          source_kind: toText(staticLayer.source_kind) || "resource_path_content",
          resource_field: toText(staticLayer.resource_field),
          configured_path: toText(staticLayer.configured_path),
          resolution_kind: toText(staticLayer.resolution_kind),
          resolved_path: toText(staticLayer.resolved_path),
          editable_via: toText(staticLayer.editable_via),
        },
        "identity_static_editor",
      ),
    );
    card.appendChild(summary);

    const form = document.createElement("form");
    form.className = "admin-form";
    form.dataset.identityStaticSubject = subject;
    form.addEventListener("submit", (event) => event.preventDefault());

    const grid = document.createElement("div");
    grid.className = "admin-form-grid";

    const contentField = document.createElement("label");
    contentField.className = "admin-field admin-field-wide";
    const contentLabel = document.createElement("span");
    contentLabel.textContent = "Contenu statique actif";
    contentField.appendChild(contentLabel);
    const textarea = document.createElement("textarea");
    textarea.className = "admin-readonly-textarea";
    textarea.name = "content";
    textarea.rows = 8;
    textarea.value = currentContent;
    contentField.appendChild(textarea);
    const contentMeta = document.createElement("small");
    contentMeta.textContent =
      "Enregistre exactement le contenu demande dans la ressource resolue. Aucun plafond Lot 5 ni troncature cachee.";
    contentField.appendChild(contentMeta);
    grid.appendChild(contentField);

    const reasonField = document.createElement("label");
    reasonField.className = "admin-field";
    const reasonLabel = document.createElement("span");
    reasonLabel.textContent = "Justification operateur";
    reasonField.appendChild(reasonLabel);
    const reasonInput = document.createElement("input");
    reasonInput.type = "text";
    reasonInput.name = "reason";
    reasonInput.maxLength = 240;
    reasonInput.placeholder = "Pourquoi modifier ou vider ce statique ?";
    reasonField.appendChild(reasonInput);
    const reasonMeta = document.createElement("small");
    reasonMeta.textContent = "Obligatoire pour `set` et `clear`.";
    reasonField.appendChild(reasonMeta);
    grid.appendChild(reasonField);

    form.appendChild(grid);

    const actions = document.createElement("div");
    actions.className = "admin-inline-actions";

    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "admin-btn";
    saveButton.dataset.identityStaticAction = "set";
    saveButton.dataset.identityStaticSubject = subject;
    saveButton.textContent = "Enregistrer statique";
    actions.appendChild(saveButton);

    const clearButton = document.createElement("button");
    clearButton.type = "button";
    clearButton.className = "admin-btn";
    clearButton.dataset.identityStaticAction = "clear";
    clearButton.dataset.identityStaticSubject = subject;
    clearButton.textContent = "Vider statique";
    actions.appendChild(clearButton);

    form.appendChild(actions);
    card.appendChild(form);
    target.appendChild(card);
  };

  const renderIdentityStaticEditors = (target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const subjects = safePayload.subjects && typeof safePayload.subjects === "object" ? safePayload.subjects : {};
    const available = SUBJECTS.filter((subject) => subjects[subject] && typeof subjects[subject] === "object");
    if (!available.length) {
      renderEmpty(target, "Aucune ressource statique editable disponible.");
      return;
    }
    available.forEach((subject) => renderSubjectEditor(target, safePayload, subject));
  };

  const readIdentityStaticDraft = (trigger) => {
    const button = trigger?.closest?.("[data-identity-static-action]");
    if (!button) return null;
    const subject = toText(button.dataset.identityStaticSubject).toLowerCase();
    const action = toText(button.dataset.identityStaticAction).toLowerCase();
    const form = button.closest("form[data-identity-static-subject]");
    if (!form) return null;
    const contentField = form.querySelector('textarea[name="content"]');
    const reasonField = form.querySelector('input[name="reason"]');
    return {
      subject,
      action,
      content: action === "clear" ? "" : toRawText(contentField?.value),
      reason: toText(reasonField?.value),
    };
  };

  const setIdentityStaticEditStatus = (target, payload, state = "") => {
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
      if (safePayload.reason_code === "set_applied") {
        message.textContent = `Statique ${toText(safePayload.subject)} mis a jour.`;
      } else if (safePayload.reason_code === "clear_applied") {
        message.textContent = `Statique ${toText(safePayload.subject)} vide.`;
      } else if (safePayload.reason_code === "already_cleared") {
        message.textContent = `Statique ${toText(safePayload.subject)} deja vide.`;
      } else {
        message.textContent = `Statique ${toText(safePayload.subject)} deja identique.`;
      }
    } else {
      message.textContent = toText(safePayload.error) || "Edition statique indisponible.";
    }
    target.appendChild(message);

    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    const status = safePayload.ok ? "ok" : "error";
    meta.appendChild(createChip(`subject=${toText(safePayload.subject) || "n/a"}`, { status }));
    meta.appendChild(createChip(`action=${toText(safePayload.action) || "n/a"}`, { status }));
    meta.appendChild(createChip(`changed=${Boolean(safePayload.changed)}`, { status }));
    meta.appendChild(createChip(`old_len=${Number(safePayload.old_len) || 0}`, { status }));
    meta.appendChild(createChip(`new_len=${Number(safePayload.new_len) || 0}`, { status }));
    meta.appendChild(createChip(`stored_after=${Boolean(safePayload.stored_after)}`, { status }));
    meta.appendChild(createChip(`field=${toText(safePayload.resource_field) || "n/a"}`, { status }));
    meta.appendChild(createChip(`resolution=${toText(safePayload.resolution_kind) || "n/a"}`, { status }));
    meta.appendChild(createChip(`reason_code=${toText(safePayload.reason_code) || "n/a"}`, { status }));
    if (toText(safePayload.validation_error)) {
      meta.appendChild(createChip(`validation=${toText(safePayload.validation_error)}`, { status }));
    }
    target.appendChild(meta);
  };

  window.FridaHermeneuticIdentityStaticEditor = Object.freeze({
    renderIdentityStaticEditors,
    readIdentityStaticDraft,
    setIdentityStaticEditStatus,
  });
})();
