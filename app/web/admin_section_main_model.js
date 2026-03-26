(() => {
  const createMainModelSectionController = ({
    adminApi,
    sectionRoute,
    mainModelFieldSpecs,
    mainModelCheckFieldMap,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    secretSourceLabel,
    toDraftString,
    renderCheckList,
    renderReadonlyInfoEntries,
    renderReadonlyInfoCards,
    applyFieldError,
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved,
  }) => {
    const emptyMainModelDraft = () => {
      const draft = {};
      mainModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      draft.api_key = "";
      return draft;
    };

    const mainModelFieldElement = (field) => document.querySelector(`[data-field="${field}"]`);
    const mainModelFieldInput = (field) => document.getElementById(`adminMainModel-${field}`);
    const mainModelErrorElement = (field) => document.getElementById(`adminMainModelFieldError-${field}`);

    const renderMainModelChecks = (checks = []) => {
      renderCheckList(elements.mainModelChecks, checks);
    };

    const renderMainModelReadonlyInfo = () => {
      const readonlyInfo = state.mainModel.view?.readonly_info || {};
      const systemPromptEntries = readonlyInfo.system_prompt
        ? [["system_prompt", readonlyInfo.system_prompt]]
        : [];
      const hermeneuticalPromptEntries = readonlyInfo.hermeneutical_prompt
        ? [["hermeneutical_prompt", readonlyInfo.hermeneutical_prompt]]
        : [];
      const remainingReadonlyInfo = {};

      Object.entries(readonlyInfo).forEach(([key, item]) => {
        if (key === "system_prompt" || key === "hermeneutical_prompt") return;
        remainingReadonlyInfo[key] = item;
      });

      renderReadonlyInfoEntries(elements.mainModelSystemPromptInfo, systemPromptEntries);
      renderReadonlyInfoEntries(elements.mainModelHermeneuticalPromptInfo, hermeneuticalPromptEntries);
      renderReadonlyInfoCards(elements.mainModelReadonlyInfo, remainingReadonlyInfo);
    };

    const ensureMainModelFieldSkeleton = () => {
      if (!elements.mainModelFields || elements.mainModelFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      mainModelFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.field = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminMainModel-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminMainModel-${spec.key}`;
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
        source.id = `adminMainModelSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminMainModelFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.mainModelFields.appendChild(fragment);
    };

    const buildMainModelDraftFromView = (view) => {
      const draft = {};
      mainModelFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      draft.api_key = "";
      return draft;
    };

    const renderMainModelMeta = () => {
      const view = state.mainModel.view;
      if (!view) {
        if (elements.mainModelSource) elements.mainModelSource.textContent = "Section: indisponible";
        if (elements.mainModelApiKeySource) elements.mainModelApiKeySource.textContent = "API key: indisponible";
        if (elements.mainModelApiKeyState) elements.mainModelApiKeyState.textContent = "Secret: indisponible";
        if (elements.mainModelApiKeyMask) elements.mainModelApiKeyMask.textContent = "Masque";
        mainModelFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminMainModelSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.mainModelSource) {
        elements.mainModelSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      const secretSource = view.secret_sources?.api_key || "missing";
      if (elements.mainModelApiKeySource) {
        elements.mainModelApiKeySource.textContent = `API key: ${secretSourceLabel(secretSource)}`;
      }

      const secretPresent = Boolean(view.payload?.api_key?.is_set);
      if (elements.mainModelApiKeyState) {
        elements.mainModelApiKeyState.textContent = secretPresent ? "Secret: present" : "Secret: absent";
      }
      if (elements.mainModelApiKeyMask) {
        elements.mainModelApiKeyMask.textContent = secretPresent ? "Masque" : "Aucun secret";
      }

      mainModelFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminMainModelSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateMainModelDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.mainModel.baseline,
        draft: state.mainModel.draft,
        emptyDraft: emptyMainModelDraft,
        fieldSpecs: mainModelFieldSpecs,
        fieldElement: mainModelFieldElement,
        dirtyChip: elements.mainModelDirty,
        secretKey: "api_key",
      });
    };

    const applyMainModelDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.mainModel.draft,
        emptyDraft: emptyMainModelDraft,
        fieldSpecs: mainModelFieldSpecs,
        inputForField: mainModelFieldInput,
        secretInput: elements.mainModelApiKeyReplace,
        secretKey: "api_key",
        onDirtyUpdate: updateMainModelDirtyChip,
      });
    };

    const setMainModelFieldError = (field, message = "") => {
      const isSecretField = field === "api_key";
      const host = isSecretField ? document.querySelector(".admin-secret-card") : mainModelFieldElement(field);
      const errorElement = mainModelErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearMainModelFieldErrors = () => {
      mainModelFieldSpecs.forEach((spec) => setMainModelFieldError(spec.key, ""));
      setMainModelFieldError("api_key", "");
    };

    const applyMainModelLocalFieldErrors = (errors) => {
      Object.entries(errors).forEach(([field, message]) => {
        setMainModelFieldError(field, message);
      });
    };

    const applyMainModelBackendFieldError = (message) => {
      if (!message) return;
      if (message.includes("main_model.api_key")) {
        setMainModelFieldError("api_key", message);
        return;
      }
      mainModelFieldSpecs.forEach((spec) => {
        if (message.includes(`main_model.${spec.key}`)) {
          setMainModelFieldError(spec.key, message);
        }
      });
    };

    const setMainModelControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.mainModelSave,
          validateButton: elements.mainModelValidate,
          fieldSpecs: mainModelFieldSpecs,
          inputForField: mainModelFieldInput,
          extraInputs: [elements.mainModelApiKeyReplace],
        },
        disabled,
      );
    };

    const collectMainModelFailedChecks = (checks) => {
      const errors = {};
      checks.forEach((check) => {
        if (check.ok) return;
        const field = mainModelCheckFieldMap[check.name] || check.name;
        if (!errors[field]) {
          errors[field] = check.detail;
        }
      });
      return errors;
    };

    const buildMainModelPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.mainModel.baseline,
        draft: state.mainModel.draft,
        emptyDraft: emptyMainModelDraft,
        fieldSpecs: mainModelFieldSpecs,
        integerFields: ["response_max_tokens"],
        secretKey: "api_key",
      });
    };

    const applyMainModelView = (responsePayload) => {
      state.mainModel.loaded = true;
      state.mainModel.view = {
        payload: responsePayload.payload || {},
        readonly_info: responsePayload.readonly_info || {},
        secret_sources: responsePayload.secret_sources || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.mainModel.baseline = buildMainModelDraftFromView(state.mainModel.view);
      state.mainModel.draft = { ...state.mainModel.baseline };
      clearMainModelFieldErrors();
      renderMainModelMeta();
      applyMainModelDraftToForm();
      renderMainModelReadonlyInfo();
      renderMainModelChecks([]);
    };

    const resetMainModelSurface = (message, stateName = "error") => {
      state.mainModel.loaded = false;
      state.mainModel.view = null;
      state.mainModel.baseline = emptyMainModelDraft();
      state.mainModel.draft = emptyMainModelDraft();
      clearMainModelFieldErrors();
      renderMainModelMeta();
      applyMainModelDraftToForm();
      renderMainModelReadonlyInfo();
      renderMainModelChecks([]);
      setMainModelControlsDisabled(true);
      setInlineStatus(elements.mainModelStatus, message, stateName);
    };

    const runMainModelValidation = async (payload) => {
      clearMainModelFieldErrors();
      renderMainModelChecks([]);
      setMainModelControlsDisabled(true);
      setInlineStatus(elements.mainModelStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.mainModelStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyMainModelBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.mainModelStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderMainModelChecks(checks);
        const failedChecks = collectMainModelFailedChecks(checks);
        applyMainModelLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.mainModelStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.mainModelStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.mainModelStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setMainModelControlsDisabled(!state.mainModel.loaded);
      }
    };

    const validateMainModelSection = async () => {
      const { payload, localErrors } = buildMainModelPatchPayload();
      clearMainModelFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyMainModelLocalFieldErrors(localErrors);
        renderMainModelChecks([]);
        setInlineStatus(elements.mainModelStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runMainModelValidation(payload);
    };

    const saveMainModelSection = async () => {
      if (!state.mainModel.loaded) return;

      const { payload, localErrors, dirtyCount } = buildMainModelPatchPayload();
      clearMainModelFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyMainModelLocalFieldErrors(localErrors);
        renderMainModelChecks([]);
        setInlineStatus(elements.mainModelStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.mainModelStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runMainModelValidation(payload);
      if (!validation.ok) return;

      setMainModelControlsDisabled(true);
      setInlineStatus(elements.mainModelStatus, "Enregistrement du modele principal...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.mainModelStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyMainModelBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.mainModelStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applyMainModelView(data);
        setMainModelControlsDisabled(false);
        setInlineStatus(elements.mainModelStatus, "Modele principal enregistre.", "ok");
        banner("Modele principal enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.mainModelStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setMainModelControlsDisabled(!state.mainModel.loaded);
      }
    };

    const loadMainModelSection = async () => {
      ensureMainModelFieldSkeleton();
      clearMainModelFieldErrors();
      setMainModelControlsDisabled(true);
      setInlineStatus(elements.mainModelStatus, "Chargement du modele principal...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetMainModelSurface("Acces admin requis pour charger le modele principal.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetMainModelSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyMainModelView(data);
        setMainModelControlsDisabled(false);
        setInlineStatus(elements.mainModelStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetMainModelSurface("Lecture impossible du modele principal pour le moment.", "error");
      }
    };

    const bindMainModelSectionEvents = () => {
      elements.mainModelForm?.addEventListener("input", (event) => {
        if (!state.mainModel.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;

        if (target.id === "adminMainModelApiKeyReplace") {
          state.mainModel.draft.api_key = target.value;
          setMainModelFieldError("api_key", "");
          updateMainModelDirtyChip();
          return;
        }

        const fieldName = target.name;
        if (!fieldName) return;
        state.mainModel.draft[fieldName] = target.value;
        setMainModelFieldError(fieldName, "");
        updateMainModelDirtyChip();
      });
      elements.mainModelValidate?.addEventListener("click", () => {
        void validateMainModelSection();
      });
      elements.mainModelSave?.addEventListener("click", () => {
        void saveMainModelSection();
      });
    };

    return {
      emptyMainModelDraft,
      ensureMainModelFieldSkeleton,
      renderMainModelMeta,
      applyMainModelDraftToForm,
      renderMainModelReadonlyInfo,
      renderMainModelChecks,
      setMainModelControlsDisabled,
      loadMainModelSection,
      bindMainModelSectionEvents,
    };
  };

  window.FridaAdminMainModelSection = Object.freeze({
    createMainModelSectionController,
  });
})();
