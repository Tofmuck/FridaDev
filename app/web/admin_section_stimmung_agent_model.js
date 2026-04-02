(() => {
  const createStimmungAgentModelSectionController = ({
    adminApi,
    sectionRoute,
    stimmungAgentModelFieldSpecs,
    stimmungAgentModelCheckFieldMap,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    toDraftString,
    renderCheckList,
    renderReadonlyInfoCards,
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
    const emptyStimmungAgentModelDraft = () => {
      const draft = {};
      stimmungAgentModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      return draft;
    };

    const stimmungAgentModelFieldElement = (field) => document.querySelector(`[data-stimmung-agent-field="${field}"]`);
    const stimmungAgentModelFieldInput = (field) => document.getElementById(`adminStimmungAgentModel-${field}`);
    const stimmungAgentModelErrorElement = (field) => document.getElementById(`adminStimmungAgentModelFieldError-${field}`);

    const renderStimmungAgentModelChecks = (checks = []) => {
      renderCheckList(elements.stimmungAgentModelChecks, checks);
    };

    const renderStimmungAgentModelReadonlyInfo = () => {
      renderReadonlyInfoCards(elements.stimmungAgentModelReadonlyInfo, state.stimmungAgentModel.view?.readonly_info || {});
    };

    const ensureStimmungAgentModelFieldSkeleton = () => {
      if (!elements.stimmungAgentModelFields || elements.stimmungAgentModelFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      stimmungAgentModelFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.stimmungAgentField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminStimmungAgentModel-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminStimmungAgentModel-${spec.key}`;
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
        source.id = `adminStimmungAgentModelSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminStimmungAgentModelFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.stimmungAgentModelFields.appendChild(fragment);
    };

    const buildStimmungAgentModelDraftFromView = (view) => {
      const draft = {};
      stimmungAgentModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      return draft;
    };

    const renderStimmungAgentModelMeta = () => {
      const view = state.stimmungAgentModel.view;
      if (!view) {
        if (elements.stimmungAgentModelSource) elements.stimmungAgentModelSource.textContent = "Section: indisponible";
        stimmungAgentModelFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminStimmungAgentModelSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.stimmungAgentModelSource) {
        elements.stimmungAgentModelSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      stimmungAgentModelFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminStimmungAgentModelSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateStimmungAgentDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.stimmungAgentModel.baseline,
        draft: state.stimmungAgentModel.draft,
        emptyDraft: emptyStimmungAgentModelDraft,
        fieldSpecs: stimmungAgentModelFieldSpecs,
        fieldElement: stimmungAgentModelFieldElement,
        dirtyChip: elements.stimmungAgentModelDirty,
      });
    };

    const applyStimmungAgentDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.stimmungAgentModel.draft,
        emptyDraft: emptyStimmungAgentModelDraft,
        fieldSpecs: stimmungAgentModelFieldSpecs,
        inputForField: stimmungAgentModelFieldInput,
        onDirtyUpdate: updateStimmungAgentDirtyChip,
      });
    };

    const setStimmungAgentFieldError = (field, message = "") => {
      const host = stimmungAgentModelFieldElement(field);
      const errorElement = stimmungAgentModelErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearStimmungAgentFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: stimmungAgentModelFieldSpecs,
        setFieldError: setStimmungAgentFieldError,
      });
    };

    const applyStimmungAgentLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setStimmungAgentFieldError);
    };

    const applyStimmungAgentBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "stimmung_agent_model",
        fieldSpecs: stimmungAgentModelFieldSpecs,
        setFieldError: setStimmungAgentFieldError,
      });
    };

    const setStimmungAgentControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.stimmungAgentModelSave,
          validateButton: elements.stimmungAgentModelValidate,
          fieldSpecs: stimmungAgentModelFieldSpecs,
          inputForField: stimmungAgentModelFieldInput,
        },
        disabled,
      );
    };

    const collectStimmungAgentFailedChecks = (checks) => {
      return collectSectionFailedChecks(
        checks,
        (checkName) => stimmungAgentModelCheckFieldMap[checkName] || checkName,
      );
    };

    const buildStimmungAgentPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.stimmungAgentModel.baseline,
        draft: state.stimmungAgentModel.draft,
        emptyDraft: emptyStimmungAgentModelDraft,
        fieldSpecs: stimmungAgentModelFieldSpecs,
        integerFields: ["timeout_s", "max_tokens"],
      });
    };

    const applyStimmungAgentModelView = (responsePayload) => {
      state.stimmungAgentModel.loaded = true;
      state.stimmungAgentModel.view = {
        payload: responsePayload.payload || {},
        readonly_info: responsePayload.readonly_info || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.stimmungAgentModel.baseline = buildStimmungAgentModelDraftFromView(state.stimmungAgentModel.view);
      state.stimmungAgentModel.draft = { ...state.stimmungAgentModel.baseline };
      clearStimmungAgentFieldErrors();
      renderStimmungAgentModelMeta();
      applyStimmungAgentDraftToForm();
      renderStimmungAgentModelReadonlyInfo();
      renderStimmungAgentModelChecks([]);
    };

    const resetStimmungAgentSurface = (message, stateName = "error") => {
      state.stimmungAgentModel.loaded = false;
      state.stimmungAgentModel.view = null;
      state.stimmungAgentModel.baseline = emptyStimmungAgentModelDraft();
      state.stimmungAgentModel.draft = emptyStimmungAgentModelDraft();
      clearStimmungAgentFieldErrors();
      renderStimmungAgentModelMeta();
      applyStimmungAgentDraftToForm();
      renderStimmungAgentModelReadonlyInfo();
      renderStimmungAgentModelChecks([]);
      setStimmungAgentControlsDisabled(true);
      setInlineStatus(elements.stimmungAgentModelStatus, message, stateName);
    };

    const runStimmungAgentValidation = async (payload) => {
      clearStimmungAgentFieldErrors();
      renderStimmungAgentModelChecks([]);
      setStimmungAgentControlsDisabled(true);
      setInlineStatus(elements.stimmungAgentModelStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.stimmungAgentModelStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyStimmungAgentBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(
            elements.stimmungAgentModelStatus,
            data.error || `Validation impossible (${response.status}).`,
            "error",
          );
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderStimmungAgentModelChecks(checks);
        const failedChecks = collectStimmungAgentFailedChecks(checks);
        applyStimmungAgentLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.stimmungAgentModelStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.stimmungAgentModelStatus, "Validation technique OK.", "ok");
        return { ok: true };
      } catch (_error) {
        setInlineStatus(elements.stimmungAgentModelStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setStimmungAgentControlsDisabled(false);
      }
    };

    const validateStimmungAgentSection = async () => {
      const { payload, localErrors, dirtyCount } = buildStimmungAgentPatchPayload();
      clearStimmungAgentFieldErrors();
      applyStimmungAgentLocalFieldErrors(localErrors);
      if (Object.keys(localErrors).length) {
        setInlineStatus(elements.stimmungAgentModelStatus, "Le formulaire contient des erreurs locales.", "error");
        return false;
      }
      return (await runStimmungAgentValidation(dirtyCount ? payload : null)).ok;
    };

    const saveStimmungAgentSection = async () => {
      const { payload, localErrors, dirtyCount } = buildStimmungAgentPatchPayload();
      clearStimmungAgentFieldErrors();
      renderStimmungAgentModelChecks([]);
      applyStimmungAgentLocalFieldErrors(localErrors);

      if (Object.keys(localErrors).length) {
        setInlineStatus(elements.stimmungAgentModelStatus, "Le formulaire contient des erreurs locales.", "error");
        return;
      }

      if (!dirtyCount) {
        setInlineStatus(elements.stimmungAgentModelStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validationResult = await runStimmungAgentValidation(payload);
      if (!validationResult.ok) return;

      setStimmungAgentControlsDisabled(true);
      setInlineStatus(elements.stimmungAgentModelStatus, "Enregistrement en cours...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);
        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.stimmungAgentModelStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyStimmungAgentBackendFieldError(data.error || `Ecriture impossible (${response.status}).`);
          setInlineStatus(
            elements.stimmungAgentModelStatus,
            data.error || `Ecriture impossible (${response.status}).`,
            "error",
          );
          return;
        }

        applyStimmungAgentModelView(data);
        setInlineStatus(elements.stimmungAgentModelStatus, "Bloc Stimmung enregistre.", "ok");
        banner("Configuration admin enregistree.", "ok");
        if (typeof onSaved === "function") onSaved(data);
      } catch (_error) {
        setInlineStatus(elements.stimmungAgentModelStatus, "Ecriture impossible pour le moment.", "error");
      } finally {
        setStimmungAgentControlsDisabled(false);
      }
    };

    const loadStimmungAgentModelSection = async () => {
      setStimmungAgentControlsDisabled(true);
      setInlineStatus(elements.stimmungAgentModelStatus, "Chargement du bloc Stimmung...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetStimmungAgentSurface("Acces admin requis pour charger le bloc Stimmung.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetStimmungAgentSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyStimmungAgentModelView(data);
        setStimmungAgentControlsDisabled(false);
        setInlineStatus(elements.stimmungAgentModelStatus, "Bloc Stimmung charge.", "ok");
      } catch (_error) {
        resetStimmungAgentSurface("Lecture impossible de l'agent Stimmung pour le moment.", "error");
      }
    };

    const bindStimmungAgentModelSectionEvents = () => {
      elements.stimmungAgentModelForm?.addEventListener("input", (event) => {
        if (!state.stimmungAgentModel.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const fieldName = target.name;
        if (!fieldName) return;
        state.stimmungAgentModel.draft[fieldName] = target.value;
        setStimmungAgentFieldError(fieldName, "");
        updateStimmungAgentDirtyChip();
      });
      elements.stimmungAgentModelValidate?.addEventListener("click", () => {
        void validateStimmungAgentSection();
      });
      elements.stimmungAgentModelSave?.addEventListener("click", () => {
        void saveStimmungAgentSection();
      });
    };

    return {
      emptyStimmungAgentModelDraft,
      ensureStimmungAgentModelFieldSkeleton,
      renderStimmungAgentModelMeta,
      applyStimmungAgentDraftToForm,
      renderStimmungAgentModelReadonlyInfo,
      renderStimmungAgentModelChecks,
      setStimmungAgentControlsDisabled,
      loadStimmungAgentModelSection,
      bindStimmungAgentModelSectionEvents,
    };
  };

  window.FridaAdminStimmungAgentModelSection = Object.freeze({
    createStimmungAgentModelSectionController,
  });
})();
