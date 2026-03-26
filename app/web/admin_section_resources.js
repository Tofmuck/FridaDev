(() => {
  const createResourcesSectionController = ({
    adminApi,
    sectionRoute,
    resourcesFieldSpecs,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
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
    const emptyResourcesDraft = () => {
      const draft = {};
      resourcesFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      return draft;
    };

    const resourcesFieldElement = (field) => document.querySelector(`[data-resources-field="${field}"]`);
    const resourcesFieldInput = (field) => document.getElementById(`adminResources-${field}`);
    const resourcesErrorElement = (field) => document.getElementById(`adminResourcesFieldError-${field}`);

    const renderResourcesChecks = (checks = []) => {
      renderCheckList(elements.resourcesChecks, checks);
    };

    const ensureResourcesFieldSkeleton = () => {
      if (!elements.resourcesFields || elements.resourcesFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      resourcesFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.resourcesField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminResources-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminResources-${spec.key}`;
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
        source.id = `adminResourcesSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminResourcesFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.resourcesFields.appendChild(fragment);
    };

    const buildResourcesDraftFromView = (view) => {
      const draft = {};
      resourcesFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      return draft;
    };

    const renderResourcesMeta = () => {
      const view = state.resources.view;
      if (!view) {
        if (elements.resourcesSource) elements.resourcesSource.textContent = "Section: indisponible";
        resourcesFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminResourcesSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.resourcesSource) {
        elements.resourcesSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      resourcesFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminResourcesSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateResourcesDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.resources.baseline,
        draft: state.resources.draft,
        emptyDraft: emptyResourcesDraft,
        fieldSpecs: resourcesFieldSpecs,
        fieldElement: resourcesFieldElement,
        dirtyChip: elements.resourcesDirty,
      });
    };

    const applyResourcesDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.resources.draft,
        emptyDraft: emptyResourcesDraft,
        fieldSpecs: resourcesFieldSpecs,
        inputForField: resourcesFieldInput,
        onDirtyUpdate: updateResourcesDirtyChip,
      });
    };

    const setResourcesFieldError = (field, message = "") => {
      const host = resourcesFieldElement(field);
      const errorElement = resourcesErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearResourcesFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: resourcesFieldSpecs,
        setFieldError: setResourcesFieldError,
      });
    };

    const applyResourcesLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setResourcesFieldError);
    };

    const applyResourcesBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "resources",
        fieldSpecs: resourcesFieldSpecs,
        setFieldError: setResourcesFieldError,
      });
    };

    const setResourcesControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.resourcesSave,
          validateButton: elements.resourcesValidate,
          fieldSpecs: resourcesFieldSpecs,
          inputForField: resourcesFieldInput,
        },
        disabled,
      );
    };

    const collectResourcesFailedChecks = (checks) => {
      return collectSectionFailedChecks(checks);
    };

    const buildResourcesPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.resources.baseline,
        draft: state.resources.draft,
        emptyDraft: emptyResourcesDraft,
        fieldSpecs: resourcesFieldSpecs,
      });
    };

    const applyResourcesView = (responsePayload) => {
      state.resources.loaded = true;
      state.resources.view = {
        payload: responsePayload.payload || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.resources.baseline = buildResourcesDraftFromView(state.resources.view);
      state.resources.draft = { ...state.resources.baseline };
      clearResourcesFieldErrors();
      renderResourcesMeta();
      applyResourcesDraftToForm();
      renderResourcesChecks([]);
    };

    const resetResourcesSurface = (message, stateName = "error") => {
      state.resources.loaded = false;
      state.resources.view = null;
      state.resources.baseline = emptyResourcesDraft();
      state.resources.draft = emptyResourcesDraft();
      clearResourcesFieldErrors();
      renderResourcesMeta();
      applyResourcesDraftToForm();
      renderResourcesChecks([]);
      setResourcesControlsDisabled(true);
      setInlineStatus(elements.resourcesStatus, message, stateName);
    };

    const runResourcesValidation = async (payload) => {
      clearResourcesFieldErrors();
      renderResourcesChecks([]);
      setResourcesControlsDisabled(true);
      setInlineStatus(elements.resourcesStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.resourcesStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyResourcesBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.resourcesStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderResourcesChecks(checks);
        const failedChecks = collectResourcesFailedChecks(checks);
        applyResourcesLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.resourcesStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.resourcesStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.resourcesStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setResourcesControlsDisabled(!state.resources.loaded);
      }
    };

    const validateResourcesSection = async () => {
      const { payload, localErrors } = buildResourcesPatchPayload();
      clearResourcesFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyResourcesLocalFieldErrors(localErrors);
        renderResourcesChecks([]);
        setInlineStatus(elements.resourcesStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runResourcesValidation(payload);
    };

    const saveResourcesSection = async () => {
      if (!state.resources.loaded) return;

      const { payload, localErrors, dirtyCount } = buildResourcesPatchPayload();
      clearResourcesFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyResourcesLocalFieldErrors(localErrors);
        renderResourcesChecks([]);
        setInlineStatus(elements.resourcesStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.resourcesStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runResourcesValidation(payload);
      if (!validation.ok) return;

      setResourcesControlsDisabled(true);
      setInlineStatus(elements.resourcesStatus, "Enregistrement du bloc ressources...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.resourcesStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyResourcesBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.resourcesStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applyResourcesView(data);
        setResourcesControlsDisabled(false);
        setInlineStatus(elements.resourcesStatus, "Bloc ressources enregistre.", "ok");
        banner("Bloc ressources enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.resourcesStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setResourcesControlsDisabled(!state.resources.loaded);
      }
    };

    const loadResourcesSection = async () => {
      ensureResourcesFieldSkeleton();
      clearResourcesFieldErrors();
      setResourcesControlsDisabled(true);
      setInlineStatus(elements.resourcesStatus, "Chargement du bloc ressources...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetResourcesSurface("Acces admin requis pour charger le bloc ressources.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetResourcesSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyResourcesView(data);
        setResourcesControlsDisabled(false);
        setInlineStatus(elements.resourcesStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetResourcesSurface("Lecture impossible du bloc ressources pour le moment.", "error");
      }
    };

    const bindResourcesSectionEvents = () => {
      elements.resourcesForm?.addEventListener("input", (event) => {
        if (!state.resources.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const fieldName = target.name;
        if (!fieldName) return;
        state.resources.draft[fieldName] = target.value;
        setResourcesFieldError(fieldName, "");
        updateResourcesDirtyChip();
      });
      elements.resourcesValidate?.addEventListener("click", () => {
        void validateResourcesSection();
      });
      elements.resourcesSave?.addEventListener("click", () => {
        void saveResourcesSection();
      });
    };

    return {
      emptyResourcesDraft,
      resourcesFieldElement,
      resourcesFieldInput,
      resourcesErrorElement,
      renderResourcesChecks,
      ensureResourcesFieldSkeleton,
      buildResourcesDraftFromView,
      renderResourcesMeta,
      updateResourcesDirtyChip,
      applyResourcesDraftToForm,
      applyResourcesView,
      resetResourcesSurface,
      setResourcesFieldError,
      clearResourcesFieldErrors,
      applyResourcesLocalFieldErrors,
      applyResourcesBackendFieldError,
      setResourcesControlsDisabled,
      collectResourcesFailedChecks,
      buildResourcesPatchPayload,
      runResourcesValidation,
      validateResourcesSection,
      saveResourcesSection,
      loadResourcesSection,
      bindResourcesSectionEvents,
    };
  };

  window.FridaAdminResourcesSection = Object.freeze({
    createResourcesSectionController,
  });
})();
