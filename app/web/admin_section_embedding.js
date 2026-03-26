(() => {
  const createEmbeddingSectionController = ({
    adminApi,
    sectionRoute,
    embeddingFieldSpecs,
    embeddingCheckFieldMap,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    secretSourceLabel,
    toDraftString,
    renderCheckList,
    applyFieldError,
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved,
  }) => {
    const emptyEmbeddingDraft = () => {
      const draft = {};
      embeddingFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      draft.token = "";
      return draft;
    };

    const embeddingFieldElement = (field) => document.querySelector(`[data-embedding-field="${field}"]`);
    const embeddingFieldInput = (field) => document.getElementById(`adminEmbedding-${field}`);
    const embeddingErrorElement = (field) => document.getElementById(`adminEmbeddingFieldError-${field}`);

    const renderEmbeddingChecks = (checks = []) => {
      renderCheckList(elements.embeddingChecks, checks);
    };

    const ensureEmbeddingFieldSkeleton = () => {
      if (!elements.embeddingFields || elements.embeddingFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      embeddingFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.embeddingField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminEmbedding-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminEmbedding-${spec.key}`;
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
        source.id = `adminEmbeddingSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminEmbeddingFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.embeddingFields.appendChild(fragment);
    };

    const buildEmbeddingDraftFromView = (view) => {
      const draft = {};
      embeddingFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      draft.token = "";
      return draft;
    };

    const renderEmbeddingMeta = () => {
      const view = state.embedding.view;
      if (!view) {
        if (elements.embeddingSource) elements.embeddingSource.textContent = "Section: indisponible";
        if (elements.embeddingTokenSource) elements.embeddingTokenSource.textContent = "Token: indisponible";
        if (elements.embeddingTokenState) elements.embeddingTokenState.textContent = "Secret: indisponible";
        if (elements.embeddingTokenMask) elements.embeddingTokenMask.textContent = "Masque";
        embeddingFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminEmbeddingSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.embeddingSource) {
        elements.embeddingSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      const secretSource = view.secret_sources?.token || "missing";
      if (elements.embeddingTokenSource) {
        elements.embeddingTokenSource.textContent = `Token: ${secretSourceLabel(secretSource)}`;
      }

      const secretPresent = Boolean(view.payload?.token?.is_set);
      if (elements.embeddingTokenState) {
        elements.embeddingTokenState.textContent = secretPresent ? "Secret: present" : "Secret: absent";
      }
      if (elements.embeddingTokenMask) {
        elements.embeddingTokenMask.textContent = secretPresent ? "Masque" : "Aucun secret";
      }

      embeddingFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminEmbeddingSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateEmbeddingDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.embedding.baseline,
        draft: state.embedding.draft,
        emptyDraft: emptyEmbeddingDraft,
        fieldSpecs: embeddingFieldSpecs,
        fieldElement: embeddingFieldElement,
        dirtyChip: elements.embeddingDirty,
        secretKey: "token",
      });
    };

    const applyEmbeddingDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.embedding.draft,
        emptyDraft: emptyEmbeddingDraft,
        fieldSpecs: embeddingFieldSpecs,
        inputForField: embeddingFieldInput,
        secretInput: elements.embeddingTokenReplace,
        secretKey: "token",
        onDirtyUpdate: updateEmbeddingDirtyChip,
      });
    };

    const setEmbeddingFieldError = (field, message = "") => {
      const isSecretField = field === "token";
      const host = isSecretField ? document.getElementById("adminEmbeddingSecretCard") : embeddingFieldElement(field);
      const errorElement = embeddingErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearEmbeddingFieldErrors = () => {
      embeddingFieldSpecs.forEach((spec) => setEmbeddingFieldError(spec.key, ""));
      setEmbeddingFieldError("token", "");
    };

    const applyEmbeddingLocalFieldErrors = (errors) => {
      Object.entries(errors).forEach(([field, message]) => {
        setEmbeddingFieldError(field, message);
      });
    };

    const applyEmbeddingBackendFieldError = (message) => {
      if (!message) return;
      if (message.includes("embedding.token")) {
        setEmbeddingFieldError("token", message);
        return;
      }
      embeddingFieldSpecs.forEach((spec) => {
        if (message.includes(`embedding.${spec.key}`)) {
          setEmbeddingFieldError(spec.key, message);
        }
      });
    };

    const setEmbeddingControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.embeddingSave,
          validateButton: elements.embeddingValidate,
          fieldSpecs: embeddingFieldSpecs,
          inputForField: embeddingFieldInput,
          extraInputs: [elements.embeddingTokenReplace],
        },
        disabled,
      );
    };

    const collectEmbeddingFailedChecks = (checks) => {
      const errors = {};
      checks.forEach((check) => {
        if (check.ok) return;
        const field = embeddingCheckFieldMap[check.name] || check.name;
        if (!errors[field]) {
          errors[field] = check.detail;
        }
      });
      return errors;
    };

    const buildEmbeddingPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.embedding.baseline,
        draft: state.embedding.draft,
        emptyDraft: emptyEmbeddingDraft,
        fieldSpecs: embeddingFieldSpecs,
        integerFields: embeddingFieldSpecs.map((spec) => spec.key),
        secretKey: "token",
      });
    };

    const applyEmbeddingView = (responsePayload) => {
      state.embedding.loaded = true;
      state.embedding.view = {
        payload: responsePayload.payload || {},
        secret_sources: responsePayload.secret_sources || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.embedding.baseline = buildEmbeddingDraftFromView(state.embedding.view);
      state.embedding.draft = { ...state.embedding.baseline };
      clearEmbeddingFieldErrors();
      renderEmbeddingMeta();
      applyEmbeddingDraftToForm();
      renderEmbeddingChecks([]);
    };

    const resetEmbeddingSurface = (message, stateName = "error") => {
      state.embedding.loaded = false;
      state.embedding.view = null;
      state.embedding.baseline = emptyEmbeddingDraft();
      state.embedding.draft = emptyEmbeddingDraft();
      clearEmbeddingFieldErrors();
      renderEmbeddingMeta();
      applyEmbeddingDraftToForm();
      renderEmbeddingChecks([]);
      setEmbeddingControlsDisabled(true);
      setInlineStatus(elements.embeddingStatus, message, stateName);
    };

    const runEmbeddingValidation = async (payload) => {
      clearEmbeddingFieldErrors();
      renderEmbeddingChecks([]);
      setEmbeddingControlsDisabled(true);
      setInlineStatus(elements.embeddingStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.embeddingStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyEmbeddingBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.embeddingStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderEmbeddingChecks(checks);
        const failedChecks = collectEmbeddingFailedChecks(checks);
        applyEmbeddingLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.embeddingStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.embeddingStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.embeddingStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setEmbeddingControlsDisabled(!state.embedding.loaded);
      }
    };

    const validateEmbeddingSection = async () => {
      const { payload, localErrors } = buildEmbeddingPatchPayload();
      clearEmbeddingFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyEmbeddingLocalFieldErrors(localErrors);
        renderEmbeddingChecks([]);
        setInlineStatus(elements.embeddingStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runEmbeddingValidation(payload);
    };

    const saveEmbeddingSection = async () => {
      if (!state.embedding.loaded) return;

      const { payload, localErrors, dirtyCount } = buildEmbeddingPatchPayload();
      clearEmbeddingFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyEmbeddingLocalFieldErrors(localErrors);
        renderEmbeddingChecks([]);
        setInlineStatus(elements.embeddingStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.embeddingStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runEmbeddingValidation(payload);
      if (!validation.ok) return;

      setEmbeddingControlsDisabled(true);
      setInlineStatus(elements.embeddingStatus, "Enregistrement du bloc embeddings...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.embeddingStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyEmbeddingBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.embeddingStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applyEmbeddingView(data);
        setEmbeddingControlsDisabled(false);
        setInlineStatus(elements.embeddingStatus, "Bloc embeddings enregistre.", "ok");
        banner("Bloc embeddings enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.embeddingStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setEmbeddingControlsDisabled(!state.embedding.loaded);
      }
    };

    const loadEmbeddingSection = async () => {
      ensureEmbeddingFieldSkeleton();
      clearEmbeddingFieldErrors();
      setEmbeddingControlsDisabled(true);
      setInlineStatus(elements.embeddingStatus, "Chargement du bloc embeddings...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetEmbeddingSurface("Acces admin requis pour charger le bloc embeddings.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetEmbeddingSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyEmbeddingView(data);
        setEmbeddingControlsDisabled(false);
        setInlineStatus(elements.embeddingStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetEmbeddingSurface("Lecture impossible du bloc embeddings pour le moment.", "error");
      }
    };

    const bindEmbeddingSectionEvents = () => {
      elements.embeddingForm?.addEventListener("input", (event) => {
        if (!state.embedding.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;

        if (target.id === "adminEmbeddingTokenReplace") {
          state.embedding.draft.token = target.value;
          setEmbeddingFieldError("token", "");
          updateEmbeddingDirtyChip();
          return;
        }

        const fieldName = target.name;
        if (!fieldName) return;
        state.embedding.draft[fieldName] = target.value;
        setEmbeddingFieldError(fieldName, "");
        updateEmbeddingDirtyChip();
      });
      elements.embeddingValidate?.addEventListener("click", () => {
        void validateEmbeddingSection();
      });
      elements.embeddingSave?.addEventListener("click", () => {
        void saveEmbeddingSection();
      });
    };

    return {
      emptyEmbeddingDraft,
      ensureEmbeddingFieldSkeleton,
      renderEmbeddingMeta,
      applyEmbeddingDraftToForm,
      renderEmbeddingChecks,
      setEmbeddingControlsDisabled,
      loadEmbeddingSection,
      bindEmbeddingSectionEvents,
    };
  };

  window.FridaAdminEmbeddingSection = Object.freeze({
    createEmbeddingSectionController,
  });
})();
