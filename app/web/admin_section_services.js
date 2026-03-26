(() => {
  const createServicesSectionController = ({
    adminApi,
    sectionRoute,
    servicesFieldSpecs,
    servicesCheckFieldMap,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    secretSourceLabel,
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
    const emptyServicesDraft = () => {
      const draft = {};
      servicesFieldSpecs.forEach((spec) => {
        draft[spec.key] = "";
      });
      draft.crawl4ai_token = "";
      return draft;
    };

    const servicesFieldElement = (field) => document.querySelector(`[data-services-field="${field}"]`);
    const servicesFieldInput = (field) => document.getElementById(`adminServices-${field}`);
    const servicesErrorElement = (field) => document.getElementById(`adminServicesFieldError-${field}`);

    const renderServicesChecks = (checks = []) => {
      renderCheckList(elements.servicesChecks, checks);
    };

    const renderServicesReadonlyInfo = () => {
      renderReadonlyInfoCards(elements.servicesReadonlyInfo, state.services.view?.readonly_info || {});
    };

    const ensureServicesFieldSkeleton = () => {
      if (!elements.servicesFields || elements.servicesFields.children.length > 0) return;

      const fragment = document.createDocumentFragment();
      servicesFieldSpecs.forEach((spec) => {
        const field = document.createElement("label");
        field.className = "admin-field";
        field.dataset.servicesField = spec.key;
        field.dataset.dirty = "false";
        field.setAttribute("for", `adminServices-${spec.key}`);

        const label = document.createElement("span");
        label.textContent = spec.label;

        const input = document.createElement("input");
        input.id = `adminServices-${spec.key}`;
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
        source.id = `adminServicesSource-${spec.key}`;
        source.className = "admin-field-source";
        source.textContent = "Source: chargement";

        meta.appendChild(hint);
        meta.appendChild(source);

        const error = document.createElement("p");
        error.id = `adminServicesFieldError-${spec.key}`;
        error.className = "admin-field-error";
        error.hidden = true;

        field.appendChild(label);
        field.appendChild(input);
        field.appendChild(meta);
        field.appendChild(error);
        fragment.appendChild(field);
      });

      elements.servicesFields.appendChild(fragment);
    };

    const buildServicesDraftFromView = (view) => {
      const draft = {};
      servicesFieldSpecs.forEach((spec) => {
        draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
      });
      draft.crawl4ai_token = "";
      return draft;
    };

    const renderServicesMeta = () => {
      const view = state.services.view;
      if (!view) {
        if (elements.servicesSource) elements.servicesSource.textContent = "Section: indisponible";
        if (elements.servicesCrawl4aiTokenSource) elements.servicesCrawl4aiTokenSource.textContent = "Token: indisponible";
        if (elements.servicesCrawl4aiTokenState) elements.servicesCrawl4aiTokenState.textContent = "Secret: indisponible";
        if (elements.servicesCrawl4aiTokenMask) elements.servicesCrawl4aiTokenMask.textContent = "Masque";
        servicesFieldSpecs.forEach((spec) => {
          const source = document.getElementById(`adminServicesSource-${spec.key}`);
          if (source) source.textContent = "Source: indisponible";
        });
        return;
      }

      if (elements.servicesSource) {
        elements.servicesSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
      }

      const secretSource = view.secret_sources?.crawl4ai_token || "missing";
      if (elements.servicesCrawl4aiTokenSource) {
        elements.servicesCrawl4aiTokenSource.textContent = `Token: ${secretSourceLabel(secretSource)}`;
      }

      const secretPresent = Boolean(view.payload?.crawl4ai_token?.is_set);
      if (elements.servicesCrawl4aiTokenState) {
        elements.servicesCrawl4aiTokenState.textContent = secretPresent ? "Secret: present" : "Secret: absent";
      }
      if (elements.servicesCrawl4aiTokenMask) {
        elements.servicesCrawl4aiTokenMask.textContent = secretPresent ? "Masque" : "Aucun secret";
      }

      servicesFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminServicesSource-${spec.key}`);
        if (!source) return;
        source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
      });
    };

    const updateServicesDirtyChip = () => {
      updateSectionDirtyChip({
        baseline: state.services.baseline,
        draft: state.services.draft,
        emptyDraft: emptyServicesDraft,
        fieldSpecs: servicesFieldSpecs,
        fieldElement: servicesFieldElement,
        dirtyChip: elements.servicesDirty,
        secretKey: "crawl4ai_token",
      });
    };

    const applyServicesDraftToForm = () => {
      applySectionDraftToForm({
        draft: state.services.draft,
        emptyDraft: emptyServicesDraft,
        fieldSpecs: servicesFieldSpecs,
        inputForField: servicesFieldInput,
        secretInput: elements.servicesCrawl4aiTokenReplace,
        secretKey: "crawl4ai_token",
        onDirtyUpdate: updateServicesDirtyChip,
      });
    };

    const setServicesFieldError = (field, message = "") => {
      const isSecretField = field === "crawl4ai_token";
      const host = isSecretField ? document.getElementById("adminServicesSecretCard") : servicesFieldElement(field);
      const errorElement = servicesErrorElement(field);
      applyFieldError(host, errorElement, message);
    };

    const clearServicesFieldErrors = () => {
      clearSectionFieldErrors({
        fieldSpecs: servicesFieldSpecs,
        setFieldError: setServicesFieldError,
        extraFields: ["crawl4ai_token"],
      });
    };

    const applyServicesLocalFieldErrors = (errors) => {
      applySectionLocalFieldErrors(errors, setServicesFieldError);
    };

    const applyServicesBackendFieldError = (message) => {
      applySectionBackendFieldError({
        message,
        sectionKey: "services",
        fieldSpecs: servicesFieldSpecs,
        setFieldError: setServicesFieldError,
        secretField: "crawl4ai_token",
      });
    };

    const setServicesControlsDisabled = (disabled) => {
      setSectionControlsDisabled(
        {
          saveButton: elements.servicesSave,
          validateButton: elements.servicesValidate,
          fieldSpecs: servicesFieldSpecs,
          inputForField: servicesFieldInput,
          extraInputs: [elements.servicesCrawl4aiTokenReplace],
        },
        disabled,
      );
    };

    const collectServicesFailedChecks = (checks) => {
      return collectSectionFailedChecks(checks, (checkName) => servicesCheckFieldMap[checkName] || checkName);
    };

    const buildServicesPatchPayload = () => {
      return buildSectionPatchPayload({
        baseline: state.services.baseline,
        draft: state.services.draft,
        emptyDraft: emptyServicesDraft,
        fieldSpecs: servicesFieldSpecs,
        integerFields: ["searxng_results", "crawl4ai_top_n", "crawl4ai_max_chars"],
        secretKey: "crawl4ai_token",
      });
    };

    const applyServicesView = (responsePayload) => {
      state.services.loaded = true;
      state.services.view = {
        payload: responsePayload.payload || {},
        readonly_info: responsePayload.readonly_info || {},
        secret_sources: responsePayload.secret_sources || {},
        source: responsePayload.source || "env",
        source_reason: responsePayload.source_reason || "unknown",
      };
      state.services.baseline = buildServicesDraftFromView(state.services.view);
      state.services.draft = { ...state.services.baseline };
      clearServicesFieldErrors();
      renderServicesMeta();
      applyServicesDraftToForm();
      renderServicesReadonlyInfo();
      renderServicesChecks([]);
    };

    const resetServicesSurface = (message, stateName = "error") => {
      state.services.loaded = false;
      state.services.view = null;
      state.services.baseline = emptyServicesDraft();
      state.services.draft = emptyServicesDraft();
      clearServicesFieldErrors();
      renderServicesMeta();
      applyServicesDraftToForm();
      renderServicesReadonlyInfo();
      renderServicesChecks([]);
      setServicesControlsDisabled(true);
      setInlineStatus(elements.servicesStatus, message, stateName);
    };

    const runServicesValidation = async (payload) => {
      clearServicesFieldErrors();
      renderServicesChecks([]);
      setServicesControlsDisabled(true);
      setInlineStatus(elements.servicesStatus, "Validation technique en cours...", "info");

      try {
        const response = await adminApi.validateSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.servicesStatus, "Acces admin requis pour verifier la section.", "error");
          return { ok: false };
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyServicesBackendFieldError(data.error || `Validation impossible (${response.status}).`);
          setInlineStatus(elements.servicesStatus, data.error || `Validation impossible (${response.status}).`, "error");
          return { ok: false };
        }

        const checks = Array.isArray(data.checks) ? data.checks : [];
        renderServicesChecks(checks);
        const failedChecks = collectServicesFailedChecks(checks);
        applyServicesLocalFieldErrors(failedChecks);

        if (!data.valid) {
          setInlineStatus(elements.servicesStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
          return { ok: false };
        }

        setInlineStatus(elements.servicesStatus, "Validation technique OK.", "ok");
        return { ok: true, data };
      } catch (_error) {
        setInlineStatus(elements.servicesStatus, "Validation impossible pour le moment.", "error");
        return { ok: false };
      } finally {
        setServicesControlsDisabled(!state.services.loaded);
      }
    };

    const validateServicesSection = async () => {
      const { payload, localErrors } = buildServicesPatchPayload();
      clearServicesFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyServicesLocalFieldErrors(localErrors);
        renderServicesChecks([]);
        setInlineStatus(elements.servicesStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
        return;
      }

      await runServicesValidation(payload);
    };

    const saveServicesSection = async () => {
      if (!state.services.loaded) return;

      const { payload, localErrors, dirtyCount } = buildServicesPatchPayload();
      clearServicesFieldErrors();

      if (Object.keys(localErrors).length > 0) {
        applyServicesLocalFieldErrors(localErrors);
        renderServicesChecks([]);
        setInlineStatus(elements.servicesStatus, "Correction requise avant enregistrement.", "error");
        return;
      }

      if (dirtyCount === 0) {
        setInlineStatus(elements.servicesStatus, "Aucune modification a enregistrer.", "info");
        return;
      }

      const validation = await runServicesValidation(payload);
      if (!validation.ok) return;

      setServicesControlsDisabled(true);
      setInlineStatus(elements.servicesStatus, "Enregistrement du bloc services externes...", "info");

      try {
        const response = await adminApi.patchSection(sectionRoute, payload);

        if (adminApi.isUnauthorized(response)) {
          setInlineStatus(elements.servicesStatus, "Acces admin requis pour enregistrer la section.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          applyServicesBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
          setInlineStatus(elements.servicesStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
          return;
        }

        applyServicesView(data);
        setServicesControlsDisabled(false);
        setInlineStatus(elements.servicesStatus, "Bloc services externes enregistre.", "ok");
        banner("Bloc services externes enregistre.", "ok");
        if (onSaved) onSaved();
      } catch (_error) {
        setInlineStatus(elements.servicesStatus, "Enregistrement impossible pour le moment.", "error");
      } finally {
        setServicesControlsDisabled(!state.services.loaded);
      }
    };

    const loadServicesSection = async () => {
      ensureServicesFieldSkeleton();
      clearServicesFieldErrors();
      setServicesControlsDisabled(true);
      setInlineStatus(elements.servicesStatus, "Chargement du bloc services externes...", "info");

      try {
        const response = await adminApi.fetchSection(sectionRoute);
        if (adminApi.isUnauthorized(response)) {
          resetServicesSurface("Acces admin requis pour charger le bloc services externes.", "error");
          return;
        }

        const data = await adminApi.readJson(response);
        if (!response.ok || !data.ok) {
          resetServicesSurface(data.error || `Lecture impossible (${response.status}).`, "error");
          return;
        }

        applyServicesView(data);
        setServicesControlsDisabled(false);
        setInlineStatus(elements.servicesStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
      } catch (_error) {
        resetServicesSurface("Lecture impossible du bloc services externes pour le moment.", "error");
      }
    };

    const bindServicesSectionEvents = () => {
      elements.servicesForm?.addEventListener("input", (event) => {
        if (!state.services.draft) return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;

        if (target.id === "adminServicesCrawl4aiTokenReplace") {
          state.services.draft.crawl4ai_token = target.value;
          setServicesFieldError("crawl4ai_token", "");
          updateServicesDirtyChip();
          return;
        }

        const fieldName = target.name;
        if (!fieldName) return;
        state.services.draft[fieldName] = target.value;
        setServicesFieldError(fieldName, "");
        updateServicesDirtyChip();
      });
      elements.servicesValidate?.addEventListener("click", () => {
        void validateServicesSection();
      });
      elements.servicesSave?.addEventListener("click", () => {
        void saveServicesSection();
      });
    };

    return {
      emptyServicesDraft,
      ensureServicesFieldSkeleton,
      renderServicesMeta,
      applyServicesDraftToForm,
      renderServicesReadonlyInfo,
      renderServicesChecks,
      setServicesControlsDisabled,
      loadServicesSection,
      bindServicesSectionEvents,
    };
  };

  window.FridaAdminServicesSection = Object.freeze({
    createServicesSectionController,
  });
})();
