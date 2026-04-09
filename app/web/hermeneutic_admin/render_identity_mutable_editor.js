(() => {
  const adminUi = window.FridaAdminUiCommon;
  if (!adminUi) {
    throw new Error(
      "admin_ui_common.js must be loaded before hermeneutic_admin/render_identity_mutable_editor.js",
    );
  }

  const TARGET_CHARS = 1500;
  const MAX_CHARS = 1650;
  const SUBJECTS = ["llm", "user"];

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

  const mappingToEntries = (mapping, source = "identity_mutable_editor") => {
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

  const subjectMutableLayer = (payload, subject) => {
    const subjects = payload?.subjects && typeof payload.subjects === "object" ? payload.subjects : {};
    const subjectBlock = subjects[subject];
    if (!subjectBlock || typeof subjectBlock !== "object" || Array.isArray(subjectBlock)) {
      return {};
    }
    const layer = subjectBlock.mutable;
    if (!layer || typeof layer !== "object" || Array.isArray(layer)) {
      return {};
    }
    return layer;
  };

  const renderSubjectEditor = (target, payload, subject, options = {}) => {
    const mutableLayer = subjectMutableLayer(payload, subject);
    const currentContent = toText(mutableLayer.content);
    const titleText = toText(options.title) || `${subject} mutable canonique`;
    const noteText =
      toText(options.noteText) ||
      "Edition controlee de la mutable canonique injectee activement. Le statique dispose d'un editeur distinct; le legacy, les evidences et les conflits restent read-only.";

    const card = document.createElement("section");
    card.className = "admin-readonly-group";
    card.dataset.identityMutableSubject = subject;

    const head = document.createElement("div");
    head.className = "admin-readonly-group-head";
    const title = document.createElement("h4");
    title.textContent = titleText;
    head.appendChild(title);
    card.appendChild(head);

    const note = document.createElement("p");
    note.className = "admin-section-note admin-section-note-left";
    note.textContent = noteText;
    card.appendChild(note);

    const meta = document.createElement("div");
    meta.className = "admin-card-meta";
    meta.appendChild(createChip(`stored=${Boolean(mutableLayer.stored)}`));
    meta.appendChild(createChip(`loaded=${Boolean(mutableLayer.loaded_for_runtime)}`));
    meta.appendChild(createChip(`injected=${Boolean(mutableLayer.actively_injected)}`));
    meta.appendChild(createChip(`len=${currentContent.length}`));
    meta.appendChild(createChip(`target=${TARGET_CHARS}`));
    meta.appendChild(createChip(`max=${MAX_CHARS}`));
    if (toText(mutableLayer.updated_by)) {
      meta.appendChild(createChip(`updated_by=${toText(mutableLayer.updated_by)}`));
    }
    if (toText(mutableLayer.updated_ts)) {
      meta.appendChild(createChip(`updated_ts=${toText(mutableLayer.updated_ts)}`));
    }
    card.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "admin-readonly-grid";
    renderReadonlyEntries(
      summary,
      mappingToEntries(
        {
          storage_kind: toText(mutableLayer.storage_kind) || "identity_mutables",
          stored: Boolean(mutableLayer.stored),
          loaded_for_runtime: Boolean(mutableLayer.loaded_for_runtime),
          actively_injected: Boolean(mutableLayer.actively_injected),
          source_trace_id: toText(mutableLayer.source_trace_id),
          updated_by: toText(mutableLayer.updated_by),
          update_reason: toText(mutableLayer.update_reason),
          updated_ts: toText(mutableLayer.updated_ts),
        },
        "identity_mutable_editor",
      ),
    );
    card.appendChild(summary);

    const form = document.createElement("form");
    form.className = "admin-form";
    form.dataset.identityMutableSubject = subject;
    form.addEventListener("submit", (event) => event.preventDefault());

    const grid = document.createElement("div");
    grid.className = "admin-form-grid";

    const contentField = document.createElement("label");
    contentField.className = "admin-field admin-field-wide";
    const contentLabel = document.createElement("span");
    contentLabel.textContent = "Mutable canonique";
    contentField.appendChild(contentLabel);
    const textarea = document.createElement("textarea");
    textarea.className = "admin-readonly-textarea";
    textarea.name = "content";
    textarea.rows = 8;
    textarea.value = currentContent;
    contentField.appendChild(textarea);
    const contentMeta = document.createElement("small");
    contentMeta.textContent = `Cible ${TARGET_CHARS} caracteres, plafond dur ${MAX_CHARS}, aucune troncature.`;
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
    reasonInput.placeholder = "Pourquoi modifier ou effacer cette mutable ?";
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
    saveButton.dataset.identityMutableAction = "set";
    saveButton.dataset.identityMutableSubject = subject;
    saveButton.textContent = "Enregistrer mutable";
    actions.appendChild(saveButton);

    const clearButton = document.createElement("button");
    clearButton.type = "button";
    clearButton.className = "admin-btn";
    clearButton.dataset.identityMutableAction = "clear";
    clearButton.dataset.identityMutableSubject = subject;
    clearButton.textContent = "Effacer mutable";
    actions.appendChild(clearButton);

    form.appendChild(actions);
    card.appendChild(form);
    target.appendChild(card);
  };

  const renderIdentityMutableEditors = (target, payload) => {
    if (!target) return;
    target.innerHTML = "";
    const safePayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
    const subjects = safePayload.subjects && typeof safePayload.subjects === "object" ? safePayload.subjects : {};
    const available = SUBJECTS.filter((subject) => subjects[subject] && typeof subjects[subject] === "object");
    if (!available.length) {
      renderEmpty(target, "Aucune mutable canonique editable disponible.");
      return;
    }
    available.forEach((subject) => renderSubjectEditor(target, safePayload, subject));
  };

  const renderIdentityMutableEditorCard = (target, payload, subject, options = {}) => {
    if (!target) return;
    target.innerHTML = "";
    renderSubjectEditor(target, payload, subject, options);
  };

  const readIdentityMutableDraft = (trigger) => {
    const button = trigger?.closest?.("[data-identity-mutable-action]");
    if (!button) return null;
    const subject = toText(button.dataset.identityMutableSubject).toLowerCase();
    const action = toText(button.dataset.identityMutableAction).toLowerCase();
    const form = button.closest("form[data-identity-mutable-subject]");
    if (!form) return null;
    const contentField = form.querySelector('textarea[name="content"]');
    const reasonField = form.querySelector('input[name="reason"]');
    return {
      subject,
      action,
      content: action === "clear" ? "" : toText(contentField?.value),
      reason: toText(reasonField?.value),
    };
  };

  const setIdentityMutableEditStatus = (target, payload, state = "") => {
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
        message.textContent = `Mutable ${toText(safePayload.subject)} mise a jour.`;
      } else if (safePayload.reason_code === "clear_applied") {
        message.textContent = `Mutable ${toText(safePayload.subject)} effacee.`;
      } else if (safePayload.reason_code === "already_cleared") {
        message.textContent = `Mutable ${toText(safePayload.subject)} deja absente.`;
      } else {
        message.textContent = `Mutable ${toText(safePayload.subject)} deja identique.`;
      }
    } else {
      message.textContent = toText(safePayload.error) || "Edition mutable indisponible.";
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
    meta.appendChild(createChip(`reason_code=${toText(safePayload.reason_code) || "n/a"}`, { status }));
    if (toText(safePayload.validation_error)) {
      meta.appendChild(createChip(`validation=${toText(safePayload.validation_error)}`, { status }));
    }
    target.appendChild(meta);
  };

  window.FridaHermeneuticIdentityMutableEditor = Object.freeze({
    renderIdentityMutableEditors,
    renderIdentityMutableEditorCard,
    readIdentityMutableDraft,
    setIdentityMutableEditStatus,
  });
})();
