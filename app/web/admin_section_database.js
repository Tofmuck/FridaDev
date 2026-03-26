(() => {
  const createDatabaseSectionController = ({
    adminApi,
    sectionRoute,
    databaseFieldSpecs,
    databaseCheckFieldMap,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    secretSourceLabel,
    toDraftString,
    renderCheckList,
    applyFieldError,
    clearSectionFieldErrors,
    applySectionLocalFieldErrors,
    applySectionBackendFieldError,
    collectSectionFailedChecks,
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved,
  }) => {
    const emptyDatabaseDraft = () => {
      const draft = {};
      databaseFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      draft.dsn = "";
      return draft;
    };

    const databaseFieldElement = (field) => document.querySelector(`[data-database-field="${field}"]`);
    const databaseFieldInput = (field) => document.getElementById(`adminDatabase-${field}`);
    const databaseErrorElement = (field) => document.getElementById(`adminDatabaseFieldError-${field}`);

    const renderDatabaseChecks = (checks = []) => {
      renderCheckList(elements.databaseChecks, checks);
    };

    const ensureDatabaseFieldSkeleton = () => {
      if (!elements.databaseFields || elements.databaseFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      databaseFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.databaseField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminDatabase-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminDatabase-${spec.key}`;
        input.name = spec.key;
        input.type = spec.inputType;
        input.autocomplete = spec.autocomplete || "off";
        if (spec.step) input.step = spec.step;
        if (spec.min) input.min = spec.min;
        if (spec.max) input.max = spec.max;

        const meta = document.createElement("div");
        meta.className = "admin-field-meta";

        const hint = document.createElement("small");
        hint.textContent = spec.hint;

        const source = document.createElement("span");
        source.id = `adminDatabaseSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminDatabaseFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.databaseFields.appendChild(fragment);
    };

    const buildDatabaseDraftFromView = (view) => {
      const draft = {};
      databaseFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      draft.dsn = "";
      return draft;
    };

    const renderDatabaseMeta = () => {
      const view = state.database.view;
      if (!view) {
        if (elements.databaseSource) elements.databaseSource.textContent = "Section: indisponible";
        if (elements.databaseDsnSource) elements.databaseDsnSource.textContent = "DSN: indisponible";
        if (elements.databaseDsnState) elements.databaseDsnState.textContent = "Secret: indisponible";
        if (elements.databaseDsnMask) elements.databaseDsnMask.textContent = "Masque";
        databaseFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminDatabaseSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.databaseSource) {
        elements.databaseSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      const secretSource = view.secret_sources?.dsn || "missing";
      if (elements.databaseDsnSource) {
        elements.databaseDsnSource.textContent = `DSN: ${secretSourceLabel(secretSource)}`;
      }

      const secretPresent = Boolean(view.payload?.dsn?.is_set);
      if (elements.databaseDsnState) {
        elements.databaseDsnState.textContent = secretPresent ? "Secret: present" : "Secret: absent";
      }
      if (elements.databaseDsnMask) {
        elements.databaseDsnMask.textContent = secretPresent ? "Masque" : "Aucun secret";
      }

      databaseFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminDatabaseSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateDatabaseDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.database.baseline,
        draft: state.database.draft,
        emptyDraft: emptyDatabaseDraft,
        fieldSpecs: databaseFieldSpecs,
        fieldElement: databaseFieldElement,
        dirtyChip: elements.databaseDirty,
        secretKey: "dsn",
      });
    };

    const applyDatabaseDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.database.draft,
        emptyDraft: emptyDatabaseDraft,
        fieldSpecs: databaseFieldSpecs,
        inputForField: databaseFieldInput,
        secretInput: elements.databaseDsnReplace,
        secretKey: "dsn",
        onDirtyUpdate: updateDatabaseDirtyChip,
      });
    };

    const setDatabaseFieldError = (field, message = "") => {
      const isSecretField = field === "dsn";
      const host = isSecretField ? document.getElementById("adminDatabaseSecretCard") : databaseFieldElement(field);
      const errorElement = databaseErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearDatabaseFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: databaseFieldSpecs,
        setFieldError: setDatabaseFieldError,
        extraFields: ["dsn"],
      });
    };

    const applyDatabaseLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setDatabaseFieldError);
    };

    const applyDatabaseBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "database",
        fieldSpecs: databaseFieldSpecs,
        setFieldError: setDatabaseFieldError,
        secretField: "dsn",
      });
    };

    const setDatabaseControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.databaseSave,
          validateButton: elements.databaseValidate,
          fieldSpecs: databaseFieldSpecs,
          inputForField: databaseFieldInput,
          extraInputs: [elements.databaseDsnReplace],
        },
        disabled,
      );
    };

    const collectDatabaseFailedChecks = (checks) => {
      return collectSectionFailedChecks(checks, (checkName) => databaseCheckFieldMap[checkName] || checkName);
    };

    const buildDatabasePatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.database.baseline,
        draft: state.database.draft,
        emptyDraft: emptyDatabaseDraft,
        fieldSpecs: databaseFieldSpecs,
        secretKey: "dsn",
      });
    };

    const applyDatabaseView = (responsePayload) => {
      state.database.loaded = true;
      state.database.view = {
        payload: responsePayload.payload || {},
        secret_sources: responsePayload.secret_sources || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.database.baseline = buildDatabaseDraftFromView(state.database.view);
      state.database.draft = { ...state.database.baseline };
      clearDatabaseFieldErrors();
      renderDatabaseMeta();
      applyDatabaseDraftToForm();
      renderDatabaseChecks([]);
    };

    const resetDatabaseSurface = (message, stateName = "error") => {
      state.database.loaded = false;
      state.database.view = null;
      state.database.baseline = emptyDatabaseDraft();
      state.database.draft = emptyDatabaseDraft();
      clearDatabaseFieldErrors();
      renderDatabaseMeta();
      applyDatabaseDraftToForm();
      renderDatabaseChecks([]);
      setDatabaseControlsDisabled(true);
      setInlineStatus(elements.databaseStatus, message, stateName);
    };

    const runDatabaseValidation = async (payload) => {
      clearDatabaseFieldErrors();
      renderDatabaseChecks([]);
      setDatabaseControlsDisabled(true);
      setInlineStatus(elements.databaseStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.databaseStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyDatabaseBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.databaseStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderDatabaseChecks(checks);
        const failedChecks = collectDatabaseFailedChecks(checks);
        applyDatabaseLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.databaseStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.databaseStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.databaseStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setDatabaseControlsDisabled(!state.database.loaded);
      }
    };

    const validateDatabaseSection = async () => {
      const { payload, localErrors } = buildDatabasePatchPayload();
      clearDatabaseFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyDatabaseLocalFieldErrors(localErrors);
        renderDatabaseChecks([]);
        setInlineStatus(elements.databaseStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runDatabaseValidation(payload);
    };

    const saveDatabaseSection = async () => {
      if (!state.database.loaded) return;

      const { payload, localErrors, dirtyCount } = buildDatabasePatchPayload();
      clearDatabaseFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyDatabaseLocalFieldErrors(localErrors);
        renderDatabaseChecks([]);
        setInlineStatus(elements.databaseStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.databaseStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runDatabaseValidation(payload);
      if (!validation.ok) return;

      setDatabaseControlsDisabled(true);
      setInlineStatus(elements.databaseStatus, "Enregistrement du bloc base de donnees...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.databaseStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyDatabaseBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.databaseStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applyDatabaseView(data);
        setDatabaseControlsDisabled(false);
        setInlineStatus(elements.databaseStatus, "Bloc base de donnees enregistre.", "ok");
        banner("Bloc base de donnees enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.databaseStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setDatabaseControlsDisabled(!state.database.loaded);
      }
    };

    const loadDatabaseSection = async () => {
      ensureDatabaseFieldSkeleton();
      clearDatabaseFieldErrors();
      setDatabaseControlsDisabled(true);
      setInlineStatus(elements.databaseStatus, "Chargement du bloc base de donnees...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetDatabaseSurface("Acces admin requis pour charger le bloc base de donnees.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetDatabaseSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyDatabaseView(data);
        setDatabaseControlsDisabled(false);
        setInlineStatus(elements.databaseStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetDatabaseSurface("Lecture impossible du bloc base de donnees pour le moment.", "error");
      }
    };

    const bindDatabaseSectionEvents = () => {
      elements.databaseForm?.addEventListener("input", (event) => {
        if (!state.database.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;

        if (target.id === "adminDatabaseDsnReplace") {
          state.database.draft.dsn = target.value;
          setDatabaseFieldError("dsn", "");
          updateDatabaseDirtyChip();
          return;
        }

        const fieldName = target.name;
        if (!fieldName) return;
        state.database.draft[fieldName] = target.value;
        setDatabaseFieldError(fieldName, "");
        updateDatabaseDirtyChip();
      });
      elements.databaseValidate?.addEventListener("click", () => {
        void validateDatabaseSection();
      });
      elements.databaseSave?.addEventListener("click", () => {
        void saveDatabaseSection();
      });
    };

    return {
      emptyDatabaseDraft,
      ensureDatabaseFieldSkeleton,
      renderDatabaseMeta,
      applyDatabaseDraftToForm,
      renderDatabaseChecks,
      setDatabaseControlsDisabled,
      loadDatabaseSection,
      bindDatabaseSectionEvents,
    };
  };

  window.FridaAdminDatabaseSection = Object.freeze({
    createDatabaseSectionController,
  });
})();
