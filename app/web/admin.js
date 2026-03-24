(() => {
  const TOKEN_KEY = "frida.adminToken";
  const sections = [
    {
      key: "main_model",
      title: "Modele principal",
      description: "Provider principal, routage, titres OpenRouter et echantillonnage global.",
    },
    {
      key: "arbiter_model",
      title: "Modele arbitre",
      description: "Decision memoire, timeout et reglages propres a l'arbitre.",
    },
    {
      key: "summary_model",
      title: "Modele resumieur",
      description: "Synthese conversationnelle et reglages de resume.",
    },
    {
      key: "embedding",
      title: "Embeddings",
      description: "Endpoint, modele, dimensions et top-k pour la memoire vectorielle.",
    },
    {
      key: "database",
      title: "Base de donnees",
      description: "Lecture de la config V1 cote base, avec bootstrap externe maintenu.",
    },
    {
      key: "services",
      title: "Services externes",
      description: "SearXNG, Crawl4AI et surfaces d'appel reseau.",
    },
    {
      key: "resources",
      title: "Ressources",
      description: "Chemins identite et ressources runtime externes au depot logique.",
    },
  ];
  const mainModelFieldSpecs = [
    {
      key: "base_url",
      label: "Base URL",
      hint: "Endpoint provider principal.",
      inputType: "url",
      autocomplete: "url",
    },
    {
      key: "model",
      label: "Modele",
      hint: "Routage principal utilise par le chat.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "referer",
      label: "Referer",
      hint: "Header OpenRouter optionnel.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "app_name",
      label: "App name",
      hint: "Nom expose cote provider.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "title_llm",
      label: "Titre LLM",
      hint: "Titre du flux principal cote provider.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "title_arbiter",
      label: "Titre arbitre",
      hint: "Titre du flux arbitre cote provider.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "title_resumer",
      label: "Titre resumieur",
      hint: "Titre du flux resume cote provider.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "temperature",
      label: "Temperature",
      hint: "Echantillonnage global du modele principal.",
      inputType: "number",
      step: "0.1",
      min: "0",
      max: "2",
      autocomplete: "off",
    },
    {
      key: "top_p",
      label: "Top p",
      hint: "Coupe nucleus globale du modele principal.",
      inputType: "number",
      step: "0.05",
      min: "0.01",
      max: "1",
      autocomplete: "off",
    },
  ];
  const mainModelCheckFieldMap = {
    api_key_runtime: "api_key",
  };

  const state = {
    mainModel: {
      loaded: false,
      view: null,
      baseline: null,
      draft: null,
    },
  };

  const elements = {
    refresh: document.getElementById("adminRefresh"),
    tokenButton: document.getElementById("adminTokenButton"),
    clearToken: document.getElementById("adminClearToken"),
    statusBanner: document.getElementById("adminStatusBanner"),
    dbState: document.getElementById("adminDbState"),
    bootstrapMode: document.getElementById("adminBootstrapMode"),
    tokenState: document.getElementById("adminTokenState"),
    sectionGrid: document.getElementById("adminSectionGrid"),
    mainModelForm: document.getElementById("adminMainModelForm"),
    mainModelFields: document.getElementById("adminMainModelFields"),
    mainModelStatus: document.getElementById("adminMainModelStatus"),
    mainModelSave: document.getElementById("adminMainModelSave"),
    mainModelValidate: document.getElementById("adminMainModelValidate"),
    mainModelDirty: document.getElementById("adminMainModelDirty"),
    mainModelSource: document.getElementById("adminMainModelSource"),
    mainModelApiKeySource: document.getElementById("adminMainModelApiKeySource"),
    mainModelApiKeyState: document.getElementById("adminMainModelApiKeyState"),
    mainModelApiKeyMask: document.getElementById("adminMainModelApiKeyMask"),
    mainModelApiKeyReplace: document.getElementById("adminMainModelApiKeyReplace"),
    mainModelChecks: document.getElementById("adminMainModelChecks"),
  };

  const readToken = () => window.sessionStorage.getItem(TOKEN_KEY) || "";

  const writeToken = (value) => {
    const cleaned = String(value || "").trim();
    if (!cleaned) {
      window.sessionStorage.removeItem(TOKEN_KEY);
      return "";
    }
    window.sessionStorage.setItem(TOKEN_KEY, cleaned);
    return cleaned;
  };

  const sourceLabel = (sectionStatus) => {
    if (!sectionStatus) return "indisponible";
    if (sectionStatus.source === "db") return "DB";
    if (sectionStatus.source === "env") return "ENV";
    return String(sectionStatus.source || "inconnu").toUpperCase();
  };

  const statusLabel = (dbState) => {
    if (dbState === "db_rows") return "DB active";
    if (dbState === "empty_table") return "DB vide";
    if (dbState === "db_unavailable") return "DB indisponible";
    return "Etat inconnu";
  };

  const fieldOriginLabel = (origin) => {
    if (origin === "db" || origin === "admin_ui") return "db";
    if (origin === "env_seed") return "env fallback";
    if (origin === "seed_default") return "default";
    return String(origin || "inconnu");
  };

  const secretSourceLabel = (source) => {
    if (source === "db_encrypted") return "db_encrypted";
    if (source === "env_fallback") return "env_fallback";
    if (source === "missing") return "missing";
    return String(source || "inconnu");
  };

  const banner = (message, stateName = "info") => {
    if (!elements.statusBanner) return;
    elements.statusBanner.textContent = message;
    elements.statusBanner.dataset.state = stateName;
  };

  const setInlineStatus = (element, message, stateName = "info") => {
    if (!element) return;
    element.textContent = message;
    element.dataset.state = stateName;
  };

  const updateTokenState = () => {
    if (!elements.tokenState) return;
    elements.tokenState.textContent = readToken() ? "Session active" : "Session vide";
  };

  const adminFetch = async (url, init = {}) => {
    const headers = new Headers(init.headers || {});
    const token = readToken();
    if (token) headers.set("X-Admin-Token", token);
    return fetch(url, { ...init, headers });
  };

  const promptToken = () => {
    const current = readToken();
    const next = window.prompt("Token admin", current);
    if (next === null) return false;
    writeToken(next);
    updateTokenState();
    return true;
  };

  const toDraftString = (value) => (value === undefined || value === null ? "" : String(value));

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

  const setFieldError = (field, message = "") => {
    const isSecretField = field === "api_key";
    const host = isSecretField ? document.querySelector(".admin-secret-card") : mainModelFieldElement(field);
    const errorElement = mainModelErrorElement(field);
    if (host) {
      host.dataset.error = message ? "true" : "false";
    }
    if (!errorElement) return;
    if (message) {
      errorElement.hidden = false;
      errorElement.textContent = message;
      return;
    }
    errorElement.hidden = true;
    errorElement.textContent = "";
  };

  const clearMainModelFieldErrors = () => {
    mainModelFieldSpecs.forEach((spec) => setFieldError(spec.key, ""));
    setFieldError("api_key", "");
  };

  const setMainModelControlsDisabled = (disabled) => {
    if (elements.mainModelSave) elements.mainModelSave.disabled = disabled;
    if (elements.mainModelValidate) elements.mainModelValidate.disabled = disabled;
    if (elements.mainModelApiKeyReplace) elements.mainModelApiKeyReplace.disabled = disabled;
    mainModelFieldSpecs.forEach((spec) => {
      const input = mainModelFieldInput(spec.key);
      if (input) input.disabled = disabled;
    });
  };

  const renderMainModelChecks = (checks = []) => {
    if (!elements.mainModelChecks) return;
    if (!checks.length) {
      elements.mainModelChecks.innerHTML = '<p class="admin-check-empty">Aucune validation recente.</p>';
      return;
    }

    const fragment = document.createDocumentFragment();
    checks.forEach((check) => {
      const row = document.createElement("article");
      row.className = "admin-check";
      row.dataset.ok = check.ok ? "true" : "false";

      const name = document.createElement("strong");
      name.textContent = check.name;

      const detail = document.createElement("span");
      detail.textContent = check.detail;

      row.appendChild(name);
      row.appendChild(detail);
      fragment.appendChild(row);
    });

    elements.mainModelChecks.replaceChildren(fragment);
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

  const buildMainModelPatchPayload = () => {
    const payload = {};
    const localErrors = {};
    const baseline = state.mainModel.baseline || emptyMainModelDraft();
    const draft = state.mainModel.draft || emptyMainModelDraft();

    mainModelFieldSpecs.forEach((spec) => {
      const nextRaw = toDraftString(draft[spec.key]);
      const currentRaw = toDraftString(baseline[spec.key]);
      if (nextRaw === currentRaw) return;

      if (spec.inputType === "number") {
        const trimmed = nextRaw.trim();
        if (!trimmed) {
          localErrors[spec.key] = "Valeur numerique requise.";
          return;
        }
        const parsed = Number(trimmed);
        if (!Number.isFinite(parsed)) {
          localErrors[spec.key] = "Valeur numerique invalide.";
          return;
        }
        payload[spec.key] = { value: parsed };
        return;
      }

      payload[spec.key] = { value: nextRaw };
    });

    const replaceValue = toDraftString(draft.api_key).trim();
    if (replaceValue) {
      payload.api_key = { replace_value: replaceValue };
    }

    return {
      payload,
      localErrors,
      dirtyCount: Object.keys(payload).length,
    };
  };

  const updateDirtyChip = () => {
    const baseline = state.mainModel.baseline || emptyMainModelDraft();
    const draft = state.mainModel.draft || emptyMainModelDraft();
    let dirty = false;

    mainModelFieldSpecs.forEach((spec) => {
      const field = mainModelFieldElement(spec.key);
      const changed = toDraftString(draft[spec.key]) !== toDraftString(baseline[spec.key]);
      if (field) field.dataset.dirty = changed ? "true" : "false";
      if (changed) dirty = true;
    });

    const hasSecretChange = Boolean(toDraftString(draft.api_key).trim());
    dirty = dirty || hasSecretChange;

    if (elements.mainModelDirty) {
      elements.mainModelDirty.dataset.state = dirty ? "dirty" : "clean";
      elements.mainModelDirty.textContent = dirty ? "Modifications" : "A jour";
    }
  };

  const applyMainModelDraftToForm = () => {
    const draft = state.mainModel.draft || emptyMainModelDraft();
    mainModelFieldSpecs.forEach((spec) => {
      const input = mainModelFieldInput(spec.key);
      if (!input) return;
      const nextValue = toDraftString(draft[spec.key]);
      if (input.value !== nextValue) input.value = nextValue;
    });
    if (elements.mainModelApiKeyReplace) {
      const nextSecret = toDraftString(draft.api_key);
      if (elements.mainModelApiKeyReplace.value !== nextSecret) {
        elements.mainModelApiKeyReplace.value = nextSecret;
      }
    }
    updateDirtyChip();
  };

  const applyMainModelView = (responsePayload) => {
    state.mainModel.loaded = true;
    state.mainModel.view = {
      payload: responsePayload.payload || {},
      secret_sources: responsePayload.secret_sources || {},
      source: responsePayload.source || "env",
      source_reason: responsePayload.source_reason || "unknown",
    };
    state.mainModel.baseline = buildMainModelDraftFromView(state.mainModel.view);
    state.mainModel.draft = { ...state.mainModel.baseline };
    clearMainModelFieldErrors();
    renderMainModelMeta();
    applyMainModelDraftToForm();
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
    renderMainModelChecks([]);
    setMainModelControlsDisabled(true);
    setInlineStatus(elements.mainModelStatus, message, stateName);
  };

  const mapMainModelCheckField = (name) => mainModelCheckFieldMap[name] || name;

  const applyBackendFieldError = (message) => {
    if (!message) return;
    if (message.includes("main_model.api_key")) {
      setFieldError("api_key", message);
      return;
    }
    mainModelFieldSpecs.forEach((spec) => {
      if (message.includes(`main_model.${spec.key}`)) {
        setFieldError(spec.key, message);
      }
    });
  };

  const applyLocalFieldErrors = (errors) => {
    Object.entries(errors).forEach(([field, message]) => {
      setFieldError(field, message);
    });
  };

  const collectFailedChecks = (checks) => {
    const errors = {};
    checks.forEach((check) => {
      if (check.ok) return;
      const field = mapMainModelCheckField(check.name);
      if (!errors[field]) {
        errors[field] = check.detail;
      }
    });
    return errors;
  };

  const runMainModelValidation = async (payload) => {
    clearMainModelFieldErrors();
    renderMainModelChecks([]);
    setMainModelControlsDisabled(true);
    setInlineStatus(elements.mainModelStatus, "Validation technique en cours...", "info");

    try {
      const body = payload && Object.keys(payload).length ? { payload } : {};
      const response = await adminFetch("/api/admin/settings/main-model/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (response.status === 401) {
        setInlineStatus(elements.mainModelStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await response.json();
      if (!response.ok || !data.ok) {
        applyBackendFieldError(data.error || `Validation impossible (${response.status}).`);
        setInlineStatus(elements.mainModelStatus, data.error || `Validation impossible (${response.status}).`, "error");
        return { ok: false };
      }

      const checks = Array.isArray(data.checks) ? data.checks : [];
      renderMainModelChecks(checks);
      const failedChecks = collectFailedChecks(checks);
      applyLocalFieldErrors(failedChecks);

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
      applyLocalFieldErrors(localErrors);
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
      applyLocalFieldErrors(localErrors);
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
      const response = await adminFetch("/api/admin/settings/main-model", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          updated_by: "admin_ui",
          payload,
        }),
      });

      if (response.status === 401) {
        setInlineStatus(elements.mainModelStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await response.json();
      if (!response.ok || !data.ok) {
        applyBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
        setInlineStatus(elements.mainModelStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
        return;
      }

      applyMainModelView(data);
      setMainModelControlsDisabled(false);
      setInlineStatus(elements.mainModelStatus, "Modele principal enregistre.", "ok");
      banner("Modele principal enregistre.", "ok");
      void loadRuntimeStatus();
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
      const response = await adminFetch("/api/admin/settings/main-model");
      if (response.status === 401) {
        resetMainModelSurface("Acces admin requis pour charger le modele principal.", "error");
        return;
      }

      const data = await response.json();
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

  const renderSectionCards = (status) => {
    if (!elements.sectionGrid) return;

    const fragment = document.createDocumentFragment();
    sections.forEach((section) => {
      const sectionStatus = status.sections?.[section.key];

      const card = document.createElement("article");
      card.className = "admin-card";

      const head = document.createElement("div");
      head.className = "admin-card-head";

      const titleWrap = document.createElement("div");
      const title = document.createElement("h3");
      title.textContent = section.title;
      titleWrap.appendChild(title);

      const source = document.createElement("span");
      source.className = "admin-card-source";
      source.dataset.source = sectionStatus?.source || "missing";
      source.textContent = sourceLabel(sectionStatus);

      head.appendChild(titleWrap);
      head.appendChild(source);

      const description = document.createElement("p");
      description.textContent = section.description;

      const meta = document.createElement("div");
      meta.className = "admin-card-meta";

      const reasonChip = document.createElement("span");
      reasonChip.className = "admin-chip";
      reasonChip.textContent = `Source: ${sectionStatus?.source_reason || "indisponible"}`;
      meta.appendChild(reasonChip);

      if (section.key === "main_model") {
        const detailChip = document.createElement("span");
        detailChip.className = "admin-chip";
        detailChip.textContent = "Bloc detaille actif";
        meta.appendChild(detailChip);
      }

      if (status.bootstrap?.database_dsn_mode && section.key === "database") {
        const bootstrapChip = document.createElement("span");
        bootstrapChip.className = "admin-chip";
        bootstrapChip.textContent = `Bootstrap: ${status.bootstrap.database_dsn_mode}`;
        meta.appendChild(bootstrapChip);
      }

      card.appendChild(head);
      card.appendChild(description);
      card.appendChild(meta);
      fragment.appendChild(card);
    });

    elements.sectionGrid.replaceChildren(fragment);
  };

  const renderStatus = (status) => {
    if (elements.dbState) {
      elements.dbState.textContent = statusLabel(status.db_state);
    }
    if (elements.bootstrapMode) {
      elements.bootstrapMode.textContent = status.bootstrap?.database_dsn_mode || "Externe";
    }
    updateTokenState();
    renderSectionCards(status);
  };

  const loadRuntimeStatus = async () => {
    banner("Chargement du statut runtime...", "info");
    try {
      const response = await adminFetch("/api/admin/settings/status");
      if (response.status === 401) {
        banner("Acces admin requis. Definis le token pour charger l'etat runtime.", "error");
        return;
      }
      if (!response.ok) {
        banner(`Lecture admin impossible (${response.status}).`, "error");
        return;
      }

      const payload = await response.json();
      if (!payload.ok) {
        banner(payload.error || "Lecture admin invalide.", "error");
        return;
      }

      renderStatus(payload);
      banner("Etat runtime charge. Le modele principal est maintenant editable dans cette tranche.", "ok");
    } catch (_error) {
      banner("Lecture admin impossible pour le moment.", "error");
    }
  };

  const loadAdminSurface = async () => {
    await Promise.all([loadRuntimeStatus(), loadMainModelSection()]);
  };

  elements.mainModelForm?.addEventListener("input", (event) => {
    if (!state.mainModel.draft) return;
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;

    if (target.id === "adminMainModelApiKeyReplace") {
      state.mainModel.draft.api_key = target.value;
      setFieldError("api_key", "");
      updateDirtyChip();
      return;
    }

    const fieldName = target.name;
    if (!fieldName) return;
    state.mainModel.draft[fieldName] = target.value;
    setFieldError(fieldName, "");
    updateDirtyChip();
  });

  elements.refresh?.addEventListener("click", () => {
    void loadAdminSurface();
  });

  elements.tokenButton?.addEventListener("click", () => {
    if (!promptToken()) return;
    void loadAdminSurface();
  });

  elements.clearToken?.addEventListener("click", () => {
    writeToken("");
    updateTokenState();
    banner("Token admin efface pour cette session.", "info");
    void loadAdminSurface();
  });

  elements.mainModelValidate?.addEventListener("click", () => {
    void validateMainModelSection();
  });

  elements.mainModelSave?.addEventListener("click", () => {
    void saveMainModelSection();
  });

  ensureMainModelFieldSkeleton();
  state.mainModel.baseline = emptyMainModelDraft();
  state.mainModel.draft = emptyMainModelDraft();
  renderMainModelMeta();
  applyMainModelDraftToForm();
  renderMainModelChecks([]);
  setMainModelControlsDisabled(true);
  updateTokenState();
  renderSectionCards({
    sections: Object.fromEntries(sections.map((section) => [section.key, { source: "env", source_reason: "loading" }])),
    bootstrap: { database_dsn_mode: "external_bootstrap" },
  });
  void loadAdminSurface();
})();
