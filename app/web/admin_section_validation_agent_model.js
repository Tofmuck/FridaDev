(() => {
  const createValidationAgentModelSectionController = ({
    adminApi,
    sectionRoute,
    validationAgentModelFieldSpecs,
    validationAgentModelCheckFieldMap,
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
    const emptyValidationAgentModelDraft = () => {
      const draft = {};
      validationAgentModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      return draft;
    };

    const validationAgentModelFieldElement = (field) => document.querySelector(`[data-validation-agent-field="${field}"]`);
    const validationAgentModelFieldInput = (field) => document.getElementById(`adminValidationAgentModel-${field}`);
    const validationAgentModelErrorElement = (field) => document.getElementById(`adminValidationAgentModelFieldError-${field}`);

    const renderValidationAgentModelChecks = (checks = []) => {
      renderCheckList(elements.validationAgentModelChecks, checks);
    };

    const renderValidationAgentModelReadonlyInfo = () => {
      renderReadonlyInfoCards(elements.validationAgentModelReadonlyInfo, state.validationAgentModel.view?.readonly_info || {});
    };

    const ensureValidationAgentModelFieldSkeleton = () => {
      if (!elements.validationAgentModelFields || elements.validationAgentModelFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      validationAgentModelFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.validationAgentField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminValidationAgentModel-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminValidationAgentModel-${spec.key}`;
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
        source.id = `adminValidationAgentModelSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminValidationAgentModelFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.validationAgentModelFields.appendChild(fragment);
    };

    const buildValidationAgentModelDraftFromView = (view) => {
      const draft = {};
      validationAgentModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      return draft;
    };

    const renderValidationAgentModelMeta = () => {
      const view = state.validationAgentModel.view;
      if (!view) {
        if (elements.validationAgentModelSource) elements.validationAgentModelSource.textContent = "Section: indisponible";
        validationAgentModelFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminValidationAgentModelSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.validationAgentModelSource) {
        elements.validationAgentModelSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      validationAgentModelFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminValidationAgentModelSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateValidationAgentDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.validationAgentModel.baseline,
        draft: state.validationAgentModel.draft,
        emptyDraft: emptyValidationAgentModelDraft,
        fieldSpecs: validationAgentModelFieldSpecs,
        fieldElement: validationAgentModelFieldElement,
        dirtyChip: elements.validationAgentModelDirty,
      });
    };

    const applyValidationAgentDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.validationAgentModel.draft,
        emptyDraft: emptyValidationAgentModelDraft,
        fieldSpecs: validationAgentModelFieldSpecs,
        inputForField: validationAgentModelFieldInput,
        onDirtyUpdate: updateValidationAgentDirtyChip,
      });
    };

    const setValidationAgentFieldError = (field, message = "") => {
      const host = validationAgentModelFieldElement(field);
      const errorElement = validationAgentModelErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearValidationAgentFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: validationAgentModelFieldSpecs,
        setFieldError: setValidationAgentFieldError,
      });
    };

    const applyValidationAgentLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setValidationAgentFieldError);
    };

    const applyValidationAgentBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "validation_agent_model",
        fieldSpecs: validationAgentModelFieldSpecs,
        setFieldError: setValidationAgentFieldError,
      });
    };

    const setValidationAgentControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.validationAgentModelSave,
          validateButton: elements.validationAgentModelValidate,
          fieldSpecs: validationAgentModelFieldSpecs,
          inputForField: validationAgentModelFieldInput,
        },
        disabled,
      );
    };

    const collectValidationAgentFailedChecks = (checks) => {
      return collectSectionFailedChecks(
        checks,
        (checkName) => validationAgentModelCheckFieldMap[checkName] || checkName,
      );
    };

    const buildValidationAgentPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.validationAgentModel.baseline,
        draft: state.validationAgentModel.draft,
        emptyDraft: emptyValidationAgentModelDraft,
        fieldSpecs: validationAgentModelFieldSpecs,
        integerFields: ["timeout_s", "max_tokens"],
      });
    };

    const applyValidationAgentModelView = (responsePayload) => {
      state.validationAgentModel.loaded = true;
      state.validationAgentModel.view = {
        payload: responsePayload.payload || {},
        readonly_info: responsePayload.readonly_info || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.validationAgentModel.baseline = buildValidationAgentModelDraftFromView(state.validationAgentModel.view);
      state.validationAgentModel.draft = { ...state.validationAgentModel.baseline };
      clearValidationAgentFieldErrors();
      renderValidationAgentModelMeta();
      applyValidationAgentDraftToForm();
      renderValidationAgentModelReadonlyInfo();
      renderValidationAgentModelChecks([]);
    };

    const resetValidationAgentSurface = (message, stateName = "error") => {
      state.validationAgentModel.loaded = false;
      state.validationAgentModel.view = null;
      state.validationAgentModel.baseline = emptyValidationAgentModelDraft();
      state.validationAgentModel.draft = emptyValidationAgentModelDraft();
      clearValidationAgentFieldErrors();
      renderValidationAgentModelMeta();
      applyValidationAgentDraftToForm();
      renderValidationAgentModelReadonlyInfo();
      renderValidationAgentModelChecks([]);
      setValidationAgentControlsDisabled(true);
      setInlineStatus(elements.validationAgentModelStatus, message, stateName);
    };

    const runValidationAgentValidation = async (payload) => {
      clearValidationAgentFieldErrors();
      renderValidationAgentModelChecks([]);
      setValidationAgentControlsDisabled(true);
      setInlineStatus(elements.validationAgentModelStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.validationAgentModelStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyValidationAgentBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(
            elements.validationAgentModelStatus,
            data.error || `Validation impossible (${response.status}).`,
            "error",
          );
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderValidationAgentModelChecks(checks);
        const failedChecks = collectValidationAgentFailedChecks(checks);
        applyValidationAgentLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.validationAgentModelStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.validationAgentModelStatus, "Validation technique OK.", "ok");
        return { ok: true };
      } catch (_error) {
        setInlineStatus(elements.validationAgentModelStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setValidationAgentControlsDisabled(false);
      }
    };

    const validateValidationAgentSection = async () => {
      const { payload, localErrors, dirtyCount } = buildValidationAgentPatchPayload();
      clearValidationAgentFieldErrors();
      applyValidationAgentLocalFieldErrors(localErrors);
      if (Object.keys(localErrors).length) {
        setInlineStatus(elements.validationAgentModelStatus, "Le formulaire contient des erreurs locales.", "error");
        return false;
      }
      return (await runValidationAgentValidation(dirtyCount ? payload : null)).ok;
    };

    const saveValidationAgentSection = async () => {
      const { payload, localErrors, dirtyCount } = buildValidationAgentPatchPayload();
      clearValidationAgentFieldErrors();
      renderValidationAgentModelChecks([]);
      applyValidationAgentLocalFieldErrors(localErrors);

      if (Object.keys(localErrors).length) {
        setInlineStatus(elements.validationAgentModelStatus, "Le formulaire contient des erreurs locales.", "error");
        return;
      }

      if (!dirtyCount) {
        setInlineStatus(elements.validationAgentModelStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validationResult = await runValidationAgentValidation(payload);
      if (!validationResult.ok) return;

      setValidationAgentControlsDisabled(true);
      setInlineStatus(elements.validationAgentModelStatus, "Enregistrement en cours...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);
        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.validationAgentModelStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyValidationAgentBackendFieldError(data.error || `Ecriture impossible (${response.status}).`);
          setInlineStatus(
            elements.validationAgentModelStatus,
            data.error || `Ecriture impossible (${response.status}).`,
            "error",
          );
          return;
        }

        applyValidationAgentModelView(data);
        setInlineStatus(elements.validationAgentModelStatus, "Bloc validation enregistre.", "ok");
        banner("Configuration admin enregistree.", "ok");
        if (typeof onSaved === "function") onSaved(data);
      } catch (_error) {
        setInlineStatus(elements.validationAgentModelStatus, "Ecriture impossible pour le moment.", "error");
      } finally {
        setValidationAgentControlsDisabled(false);
      }
    };

    const loadValidationAgentModelSection = async () => {
      setValidationAgentControlsDisabled(true);
      setInlineStatus(elements.validationAgentModelStatus, "Chargement du bloc validation...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetValidationAgentSurface("Acces admin requis pour charger le bloc validation.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetValidationAgentSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyValidationAgentModelView(data);
        setValidationAgentControlsDisabled(false);
        setInlineStatus(elements.validationAgentModelStatus, "Bloc validation charge.", "ok");
      } catch (_error) {
        resetValidationAgentSurface("Lecture impossible de l'agent de validation pour le moment.", "error");
      }
    };

    const bindValidationAgentModelSectionEvents = () => {
      elements.validationAgentModelForm?.addEventListener("input", (event) => {
        if (!state.validationAgentModel.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const fieldName = target.name;
        if (!fieldName) return;
        state.validationAgentModel.draft[fieldName] = target.value;
        setValidationAgentFieldError(fieldName, "");
        updateValidationAgentDirtyChip();
      });
      elements.validationAgentModelValidate?.addEventListener("click", () => {
        void validateValidationAgentSection();
      });
      elements.validationAgentModelSave?.addEventListener("click", () => {
        void saveValidationAgentSection();
      });
    };

    return {
      emptyValidationAgentModelDraft,
      ensureValidationAgentModelFieldSkeleton,
      renderValidationAgentModelMeta,
      applyValidationAgentDraftToForm,
      renderValidationAgentModelReadonlyInfo,
      renderValidationAgentModelChecks,
      setValidationAgentControlsDisabled,
      loadValidationAgentModelSection,
      bindValidationAgentModelSectionEvents,
    };
  };

  window.FridaAdminValidationAgentModelSection = Object.freeze({
    createValidationAgentModelSectionController,
  });
})();
