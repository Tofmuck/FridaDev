(() => {
  const createArbiterModelSectionController = ({
    adminApi,
    sectionRoute,
    arbiterModelFieldSpecs,
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
    const emptyArbiterModelDraft = () => {
      const draft = {};
      arbiterModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      return draft;
    };

    const arbiterModelFieldElement = (field) => document.querySelector(`[data-arbiter-field="${field}"]`);
    const arbiterModelFieldInput = (field) => document.getElementById(`adminArbiterModel-${field}`);
    const arbiterModelErrorElement = (field) => document.getElementById(`adminArbiterModelFieldError-${field}`);

    const renderArbiterModelChecks = (checks = []) => {
      renderCheckList(elements.arbiterModelChecks, checks);
    };

    const renderArbiterModelReadonlyInfo = () => {
      renderReadonlyInfoCards(elements.arbiterModelReadonlyInfo, state.arbiterModel.view?.readonly_info || {});
    };

    const ensureArbiterModelFieldSkeleton = () => {
      if (!elements.arbiterModelFields || elements.arbiterModelFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      arbiterModelFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.arbiterField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminArbiterModel-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminArbiterModel-${spec.key}`;
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
        source.id = `adminArbiterModelSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminArbiterModelFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.arbiterModelFields.appendChild(fragment);
    };

    const buildArbiterModelDraftFromView = (view) => {
      const draft = {};
      arbiterModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      return draft;
    };

    const renderArbiterModelMeta = () => {
      const view = state.arbiterModel.view;
      if (!view) {
        if (elements.arbiterModelSource) elements.arbiterModelSource.textContent = "Section: indisponible";
        arbiterModelFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminArbiterModelSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.arbiterModelSource) {
        elements.arbiterModelSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      arbiterModelFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminArbiterModelSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateArbiterDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.arbiterModel.baseline,
        draft: state.arbiterModel.draft,
        emptyDraft: emptyArbiterModelDraft,
        fieldSpecs: arbiterModelFieldSpecs,
        fieldElement: arbiterModelFieldElement,
        dirtyChip: elements.arbiterModelDirty,
      });
    };

    const applyArbiterDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.arbiterModel.draft,
        emptyDraft: emptyArbiterModelDraft,
        fieldSpecs: arbiterModelFieldSpecs,
        inputForField: arbiterModelFieldInput,
        onDirtyUpdate: updateArbiterDirtyChip,
      });
    };

    const setArbiterFieldError = (field, message = "") => {
      const host = arbiterModelFieldElement(field);
      const errorElement = arbiterModelErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearArbiterFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: arbiterModelFieldSpecs,
        setFieldError: setArbiterFieldError,
      });
    };

    const applyArbiterLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setArbiterFieldError);
    };

    const applyArbiterBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "arbiter_model",
        fieldSpecs: arbiterModelFieldSpecs,
        setFieldError: setArbiterFieldError,
      });
    };

    const setArbiterControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.arbiterModelSave,
          validateButton: elements.arbiterModelValidate,
          fieldSpecs: arbiterModelFieldSpecs,
          inputForField: arbiterModelFieldInput,
        },
        disabled,
      );
    };

    const collectArbiterFailedChecks = (checks) => {
      return collectSectionFailedChecks(checks);
    };

    const buildArbiterPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.arbiterModel.baseline,
        draft: state.arbiterModel.draft,
        emptyDraft: emptyArbiterModelDraft,
        fieldSpecs: arbiterModelFieldSpecs,
        integerFields: ["timeout_s"],
      });
    };

    const applyArbiterModelView = (responsePayload) => {
      state.arbiterModel.loaded = true;
      state.arbiterModel.view = {
        payload: responsePayload.payload || {},
        readonly_info: responsePayload.readonly_info || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.arbiterModel.baseline = buildArbiterModelDraftFromView(state.arbiterModel.view);
      state.arbiterModel.draft = { ...state.arbiterModel.baseline };
      clearArbiterFieldErrors();
      renderArbiterModelMeta();
      applyArbiterDraftToForm();
      renderArbiterModelReadonlyInfo();
      renderArbiterModelChecks([]);
    };

    const resetArbiterSurface = (message, stateName = "error") => {
      state.arbiterModel.loaded = false;
      state.arbiterModel.view = null;
      state.arbiterModel.baseline = emptyArbiterModelDraft();
      state.arbiterModel.draft = emptyArbiterModelDraft();
      clearArbiterFieldErrors();
      renderArbiterModelMeta();
      applyArbiterDraftToForm();
      renderArbiterModelReadonlyInfo();
      renderArbiterModelChecks([]);
      setArbiterControlsDisabled(true);
      setInlineStatus(elements.arbiterModelStatus, message, stateName);
    };

    const runArbiterValidation = async (payload) => {
      clearArbiterFieldErrors();
      renderArbiterModelChecks([]);
      setArbiterControlsDisabled(true);
      setInlineStatus(elements.arbiterModelStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.arbiterModelStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyArbiterBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.arbiterModelStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderArbiterModelChecks(checks);
        const failedChecks = collectArbiterFailedChecks(checks);
        applyArbiterLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.arbiterModelStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.arbiterModelStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.arbiterModelStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setArbiterControlsDisabled(!state.arbiterModel.loaded);
      }
    };

    const validateArbiterSection = async () => {
      const { payload, localErrors } = buildArbiterPatchPayload();
      clearArbiterFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyArbiterLocalFieldErrors(localErrors);
        renderArbiterModelChecks([]);
        setInlineStatus(elements.arbiterModelStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runArbiterValidation(payload);
    };

    const saveArbiterSection = async () => {
      if (!state.arbiterModel.loaded) return;

      const { payload, localErrors, dirtyCount } = buildArbiterPatchPayload();
      clearArbiterFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyArbiterLocalFieldErrors(localErrors);
        renderArbiterModelChecks([]);
        setInlineStatus(elements.arbiterModelStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.arbiterModelStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runArbiterValidation(payload);
      if (!validation.ok) return;

      setArbiterControlsDisabled(true);
      setInlineStatus(elements.arbiterModelStatus, "Enregistrement du modele arbitre...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.arbiterModelStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyArbiterBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.arbiterModelStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applyArbiterModelView(data);
        setArbiterControlsDisabled(false);
        setInlineStatus(elements.arbiterModelStatus, "Modele arbitre enregistre.", "ok");
        banner("Modele arbitre enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.arbiterModelStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setArbiterControlsDisabled(!state.arbiterModel.loaded);
      }
    };

    const loadArbiterModelSection = async () => {
      ensureArbiterModelFieldSkeleton();
      clearArbiterFieldErrors();
      setArbiterControlsDisabled(true);
      setInlineStatus(elements.arbiterModelStatus, "Chargement du modele arbitre...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetArbiterSurface("Acces admin requis pour charger le modele arbitre.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetArbiterSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyArbiterModelView(data);
        setArbiterControlsDisabled(false);
        setInlineStatus(elements.arbiterModelStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetArbiterSurface("Lecture impossible du modele arbitre pour le moment.", "error");
      }
    };

    const bindArbiterModelSectionEvents = () => {
      elements.arbiterModelForm?.addEventListener("input", (event) => {
        if (!state.arbiterModel.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const fieldName = target.name;
        if (!fieldName) return;
        state.arbiterModel.draft[fieldName] = target.value;
        setArbiterFieldError(fieldName, "");
        updateArbiterDirtyChip();
      });
      elements.arbiterModelValidate?.addEventListener("click", () => {
        void validateArbiterSection();
      });
      elements.arbiterModelSave?.addEventListener("click", () => {
        void saveArbiterSection();
      });
    };

    return {
      emptyArbiterModelDraft,
      arbiterModelFieldElement,
      arbiterModelFieldInput,
      arbiterModelErrorElement,
      renderArbiterModelChecks,
      renderArbiterModelReadonlyInfo,
      ensureArbiterModelFieldSkeleton,
      buildArbiterModelDraftFromView,
      renderArbiterModelMeta,
      updateArbiterDirtyChip,
      applyArbiterDraftToForm,
      setArbiterFieldError,
      clearArbiterFieldErrors,
      applyArbiterLocalFieldErrors,
      applyArbiterBackendFieldError,
      setArbiterControlsDisabled,
      collectArbiterFailedChecks,
      buildArbiterPatchPayload,
      applyArbiterModelView,
      resetArbiterSurface,
      runArbiterValidation,
      validateArbiterSection,
      saveArbiterSection,
      loadArbiterModelSection,
      bindArbiterModelSectionEvents,
    };
  };

  window.FridaAdminArbiterModelSection = Object.freeze({
    createArbiterModelSectionController,
  });
})();
