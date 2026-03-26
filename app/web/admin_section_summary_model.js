(() => {
  const createSummaryModelSectionController = ({
    adminApi,
    sectionRoute,
    summaryModelFieldSpecs,
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
    const emptySummaryModelDraft = () => {
      const draft = {};
      summaryModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      return draft;
    };

    const summaryModelFieldElement = (field) => document.querySelector(`[data-summary-field="${field}"]`);
    const summaryModelFieldInput = (field) => document.getElementById(`adminSummaryModel-${field}`);
    const summaryModelErrorElement = (field) => document.getElementById(`adminSummaryModelFieldError-${field}`);

    const renderSummaryModelChecks = (checks = []) => {
      renderCheckList(elements.summaryModelChecks, checks);
    };

    const renderSummaryModelReadonlyInfo = () => {
      renderReadonlyInfoCards(elements.summaryModelReadonlyInfo, state.summaryModel.view?.readonly_info || {});
    };

    const ensureSummaryModelFieldSkeleton = () => {
      if (!elements.summaryModelFields || elements.summaryModelFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      summaryModelFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.summaryField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminSummaryModel-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminSummaryModel-${spec.key}`;
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
        source.id = `adminSummaryModelSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminSummaryModelFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.summaryModelFields.appendChild(fragment);
    };

    const buildSummaryModelDraftFromView = (view) => {
      const draft = {};
      summaryModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      return draft;
    };

    const renderSummaryModelMeta = () => {
      const view = state.summaryModel.view;
      if (!view) {
        if (elements.summaryModelSource) elements.summaryModelSource.textContent = "Section: indisponible";
        summaryModelFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminSummaryModelSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.summaryModelSource) {
        elements.summaryModelSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      summaryModelFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminSummaryModelSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateSummaryDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.summaryModel.baseline,
        draft: state.summaryModel.draft,
        emptyDraft: emptySummaryModelDraft,
        fieldSpecs: summaryModelFieldSpecs,
        fieldElement: summaryModelFieldElement,
        dirtyChip: elements.summaryModelDirty,
      });
    };

    const applySummaryDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.summaryModel.draft,
        emptyDraft: emptySummaryModelDraft,
        fieldSpecs: summaryModelFieldSpecs,
        inputForField: summaryModelFieldInput,
        onDirtyUpdate: updateSummaryDirtyChip,
      });
    };

    const setSummaryFieldError = (field, message = "") => {
      const host = summaryModelFieldElement(field);
      const errorElement = summaryModelErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearSummaryFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: summaryModelFieldSpecs,
        setFieldError: setSummaryFieldError,
      });
    };

    const applySummaryLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setSummaryFieldError);
    };

    const applySummaryBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "summary_model",
        fieldSpecs: summaryModelFieldSpecs,
        setFieldError: setSummaryFieldError,
      });
    };

    const setSummaryControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.summaryModelSave,
          validateButton: elements.summaryModelValidate,
          fieldSpecs: summaryModelFieldSpecs,
          inputForField: summaryModelFieldInput,
        },
        disabled,
      );
    };

    const collectSummaryFailedChecks = (checks) => {
      return collectSectionFailedChecks(checks);
    };

    const buildSummaryPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.summaryModel.baseline,
        draft: state.summaryModel.draft,
        emptyDraft: emptySummaryModelDraft,
        fieldSpecs: summaryModelFieldSpecs,
      });
    };

    const applySummaryModelView = (responsePayload) => {
      state.summaryModel.loaded = true;
      state.summaryModel.view = {
        payload: responsePayload.payload || {},
        readonly_info: responsePayload.readonly_info || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.summaryModel.baseline = buildSummaryModelDraftFromView(state.summaryModel.view);
      state.summaryModel.draft = { ...state.summaryModel.baseline };
      clearSummaryFieldErrors();
      renderSummaryModelMeta();
      applySummaryDraftToForm();
      renderSummaryModelReadonlyInfo();
      renderSummaryModelChecks([]);
    };

    const resetSummarySurface = (message, stateName = "error") => {
      state.summaryModel.loaded = false;
      state.summaryModel.view = null;
      state.summaryModel.baseline = emptySummaryModelDraft();
      state.summaryModel.draft = emptySummaryModelDraft();
      clearSummaryFieldErrors();
      renderSummaryModelMeta();
      applySummaryDraftToForm();
      renderSummaryModelReadonlyInfo();
      renderSummaryModelChecks([]);
      setSummaryControlsDisabled(true);
      setInlineStatus(elements.summaryModelStatus, message, stateName);
    };

    const runSummaryValidation = async (payload) => {
      clearSummaryFieldErrors();
      renderSummaryModelChecks([]);
      setSummaryControlsDisabled(true);
      setInlineStatus(elements.summaryModelStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.summaryModelStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applySummaryBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.summaryModelStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderSummaryModelChecks(checks);
        const failedChecks = collectSummaryFailedChecks(checks);
        applySummaryLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.summaryModelStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.summaryModelStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.summaryModelStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setSummaryControlsDisabled(!state.summaryModel.loaded);
      }
    };

    const validateSummarySection = async () => {
      const { payload, localErrors } = buildSummaryPatchPayload();
      clearSummaryFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applySummaryLocalFieldErrors(localErrors);
        renderSummaryModelChecks([]);
        setInlineStatus(elements.summaryModelStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runSummaryValidation(payload);
    };

    const saveSummarySection = async () => {
      if (!state.summaryModel.loaded) return;

      const { payload, localErrors, dirtyCount } = buildSummaryPatchPayload();
      clearSummaryFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applySummaryLocalFieldErrors(localErrors);
        renderSummaryModelChecks([]);
        setInlineStatus(elements.summaryModelStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.summaryModelStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runSummaryValidation(payload);
      if (!validation.ok) return;

      setSummaryControlsDisabled(true);
      setInlineStatus(elements.summaryModelStatus, "Enregistrement du modele resumeur...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.summaryModelStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applySummaryBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.summaryModelStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applySummaryModelView(data);
        setSummaryControlsDisabled(false);
        setInlineStatus(elements.summaryModelStatus, "Modele resumeur enregistre.", "ok");
        banner("Modele resumeur enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.summaryModelStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setSummaryControlsDisabled(!state.summaryModel.loaded);
      }
    };

    const loadSummaryModelSection = async () => {
      ensureSummaryModelFieldSkeleton();
      clearSummaryFieldErrors();
      setSummaryControlsDisabled(true);
      setInlineStatus(elements.summaryModelStatus, "Chargement du modele resumeur...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetSummarySurface("Acces admin requis pour charger le modele resumeur.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetSummarySurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applySummaryModelView(data);
        setSummaryControlsDisabled(false);
        setInlineStatus(elements.summaryModelStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetSummarySurface("Lecture impossible du modele resumeur pour le moment.", "error");
      }
    };

    const bindSummaryModelSectionEvents = () => {
      elements.summaryModelForm?.addEventListener("input", (event) => {
        if (!state.summaryModel.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const fieldName = target.name;
        if (!fieldName) return;
        state.summaryModel.draft[fieldName] = target.value;
        setSummaryFieldError(fieldName, "");
        updateSummaryDirtyChip();
      });
      elements.summaryModelValidate?.addEventListener("click", () => {
        void validateSummarySection();
      });
      elements.summaryModelSave?.addEventListener("click", () => {
        void saveSummarySection();
      });
    };

    return {
      emptySummaryModelDraft,
      ensureSummaryModelFieldSkeleton,
      renderSummaryModelMeta,
      applySummaryDraftToForm,
      renderSummaryModelReadonlyInfo,
      renderSummaryModelChecks,
      setSummaryControlsDisabled,
      loadSummaryModelSection,
      bindSummaryModelSectionEvents,
    };
  };

  window.FridaAdminSummaryModelSection = Object.freeze({
    createSummaryModelSectionController,
  });
})();
