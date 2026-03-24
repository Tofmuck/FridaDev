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
  const arbiterModelFieldSpecs = [
    {
      key: "model",
      label: "Modele",
      hint: "Modele utilise pour la decision memoire.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "temperature",
      label: "Temperature",
      hint: "Echantillonnage propre a l'arbitre.",
      inputType: "number",
      step: "0.1",
      min: "0",
      max: "2",
      autocomplete: "off",
    },
    {
      key: "top_p",
      label: "Top p",
      hint: "Coupe nucleus de l'arbitre.",
      inputType: "number",
      step: "0.05",
      min: "0.01",
      max: "1",
      autocomplete: "off",
    },
    {
      key: "timeout_s",
      label: "Timeout",
      hint: "Timeout applique aux appels arbitre.",
      inputType: "number",
      step: "1",
      min: "1",
      autocomplete: "off",
    },
  ];
  const summaryModelFieldSpecs = [
    {
      key: "model",
      label: "Modele",
      hint: "Modele utilise pour la synthese conversationnelle.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "temperature",
      label: "Temperature",
      hint: "Echantillonnage propre au resumieur.",
      inputType: "number",
      step: "0.1",
      min: "0",
      max: "2",
      autocomplete: "off",
    },
    {
      key: "top_p",
      label: "Top p",
      hint: "Coupe nucleus du resumieur.",
      inputType: "number",
      step: "0.05",
      min: "0.01",
      max: "1",
      autocomplete: "off",
    },
  ];
  const embeddingFieldSpecs = [
    {
      key: "endpoint",
      label: "Endpoint",
      hint: "Service HTTP d'embedding.",
      inputType: "url",
      autocomplete: "url",
    },
    {
      key: "model",
      label: "Modele",
      hint: "Modele actif du service d'embedding.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "dimensions",
      label: "Dimensions",
      hint: "Dimension vectorielle attendue par la base.",
      inputType: "number",
      step: "1",
      min: "1",
      autocomplete: "off",
    },
    {
      key: "top_k",
      label: "Top k",
      hint: "Nombre de voisins retournes lors de la recherche.",
      inputType: "number",
      step: "1",
      min: "1",
      autocomplete: "off",
    },
  ];
  const embeddingCheckFieldMap = {
    token_runtime: "token",
  };

  const state = {
    mainModel: {
      loaded: false,
      view: null,
      baseline: null,
      draft: null,
    },
    arbiterModel: {
      loaded: false,
      view: null,
      baseline: null,
      draft: null,
    },
    summaryModel: {
      loaded: false,
      view: null,
      baseline: null,
      draft: null,
    },
    embedding: {
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
    arbiterModelForm: document.getElementById("adminArbiterModelForm"),
    arbiterModelFields: document.getElementById("adminArbiterModelFields"),
    arbiterModelStatus: document.getElementById("adminArbiterModelStatus"),
    arbiterModelSave: document.getElementById("adminArbiterModelSave"),
    arbiterModelValidate: document.getElementById("adminArbiterModelValidate"),
    arbiterModelDirty: document.getElementById("adminArbiterModelDirty"),
    arbiterModelSource: document.getElementById("adminArbiterModelSource"),
    arbiterModelChecks: document.getElementById("adminArbiterModelChecks"),
    summaryModelForm: document.getElementById("adminSummaryModelForm"),
    summaryModelFields: document.getElementById("adminSummaryModelFields"),
    summaryModelStatus: document.getElementById("adminSummaryModelStatus"),
    summaryModelSave: document.getElementById("adminSummaryModelSave"),
    summaryModelValidate: document.getElementById("adminSummaryModelValidate"),
    summaryModelDirty: document.getElementById("adminSummaryModelDirty"),
    summaryModelSource: document.getElementById("adminSummaryModelSource"),
    summaryModelChecks: document.getElementById("adminSummaryModelChecks"),
    embeddingForm: document.getElementById("adminEmbeddingForm"),
    embeddingFields: document.getElementById("adminEmbeddingFields"),
    embeddingStatus: document.getElementById("adminEmbeddingStatus"),
    embeddingSave: document.getElementById("adminEmbeddingSave"),
    embeddingValidate: document.getElementById("adminEmbeddingValidate"),
    embeddingDirty: document.getElementById("adminEmbeddingDirty"),
    embeddingSource: document.getElementById("adminEmbeddingSource"),
    embeddingTokenSource: document.getElementById("adminEmbeddingTokenSource"),
    embeddingTokenState: document.getElementById("adminEmbeddingTokenState"),
    embeddingTokenMask: document.getElementById("adminEmbeddingTokenMask"),
    embeddingTokenReplace: document.getElementById("adminEmbeddingTokenReplace"),
    embeddingChecks: document.getElementById("adminEmbeddingChecks"),
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
  const emptyArbiterModelDraft = () => {
    const draft = {};
    arbiterModelFieldSpecs.forEach((spec) => {
      draft[spec.key] = "";
    });
    return draft;
  };
  const emptySummaryModelDraft = () => {
    const draft = {};
    summaryModelFieldSpecs.forEach((spec) => {
      draft[spec.key] = "";
    });
    return draft;
  };
  const emptyEmbeddingDraft = () => {
    const draft = {};
    embeddingFieldSpecs.forEach((spec) => {
      draft[spec.key] = "";
    });
    draft.token = "";
    return draft;
  };

  const mainModelFieldElement = (field) => document.querySelector(`[data-field="${field}"]`);
  const mainModelFieldInput = (field) => document.getElementById(`adminMainModel-${field}`);
  const mainModelErrorElement = (field) => document.getElementById(`adminMainModelFieldError-${field}`);
  const arbiterModelFieldElement = (field) => document.querySelector(`[data-arbiter-field="${field}"]`);
  const arbiterModelFieldInput = (field) => document.getElementById(`adminArbiterModel-${field}`);
  const arbiterModelErrorElement = (field) => document.getElementById(`adminArbiterModelFieldError-${field}`);
  const summaryModelFieldElement = (field) => document.querySelector(`[data-summary-field="${field}"]`);
  const summaryModelFieldInput = (field) => document.getElementById(`adminSummaryModel-${field}`);
  const summaryModelErrorElement = (field) => document.getElementById(`adminSummaryModelFieldError-${field}`);
  const embeddingFieldElement = (field) => document.querySelector(`[data-embedding-field="${field}"]`);
  const embeddingFieldInput = (field) => document.getElementById(`adminEmbedding-${field}`);
  const embeddingErrorElement = (field) => document.getElementById(`adminEmbeddingFieldError-${field}`);

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
  const renderArbiterModelChecks = (checks = []) => {
    if (!elements.arbiterModelChecks) return;
    if (!checks.length) {
      elements.arbiterModelChecks.innerHTML = '<p class="admin-check-empty">Aucune validation recente.</p>';
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

    elements.arbiterModelChecks.replaceChildren(fragment);
  };
  const renderSummaryModelChecks = (checks = []) => {
    if (!elements.summaryModelChecks) return;
    if (!checks.length) {
      elements.summaryModelChecks.innerHTML = '<p class="admin-check-empty">Aucune validation recente.</p>';
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

    elements.summaryModelChecks.replaceChildren(fragment);
  };
  const renderEmbeddingChecks = (checks = []) => {
    if (!elements.embeddingChecks) return;
    if (!checks.length) {
      elements.embeddingChecks.innerHTML = '<p class="admin-check-empty">Aucune validation recente.</p>';
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

    elements.embeddingChecks.replaceChildren(fragment);
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

  const buildMainModelDraftFromView = (view) => {
    const draft = {};
    mainModelFieldSpecs.forEach((spec) => {
      draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
    });
    draft.api_key = "";
    return draft;
  };
  const buildArbiterModelDraftFromView = (view) => {
    const draft = {};
    arbiterModelFieldSpecs.forEach((spec) => {
      draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
    });
    return draft;
  };
  const buildSummaryModelDraftFromView = (view) => {
    const draft = {};
    summaryModelFieldSpecs.forEach((spec) => {
      draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
    });
    return draft;
  };
  const buildEmbeddingDraftFromView = (view) => {
    const draft = {};
    embeddingFieldSpecs.forEach((spec) => {
      draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
    });
    draft.token = "";
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
  const updateArbiterDirtyChip = () => {
    const baseline = state.arbiterModel.baseline || emptyArbiterModelDraft();
    const draft = state.arbiterModel.draft || emptyArbiterModelDraft();
    let dirty = false;

    arbiterModelFieldSpecs.forEach((spec) => {
      const field = arbiterModelFieldElement(spec.key);
      const changed = toDraftString(draft[spec.key]) !== toDraftString(baseline[spec.key]);
      if (field) field.dataset.dirty = changed ? "true" : "false";
      if (changed) dirty = true;
    });

    if (elements.arbiterModelDirty) {
      elements.arbiterModelDirty.dataset.state = dirty ? "dirty" : "clean";
      elements.arbiterModelDirty.textContent = dirty ? "Modifications" : "A jour";
    }
  };
  const updateSummaryDirtyChip = () => {
    const baseline = state.summaryModel.baseline || emptySummaryModelDraft();
    const draft = state.summaryModel.draft || emptySummaryModelDraft();
    let dirty = false;

    summaryModelFieldSpecs.forEach((spec) => {
      const field = summaryModelFieldElement(spec.key);
      const changed = toDraftString(draft[spec.key]) !== toDraftString(baseline[spec.key]);
      if (field) field.dataset.dirty = changed ? "true" : "false";
      if (changed) dirty = true;
    });

    if (elements.summaryModelDirty) {
      elements.summaryModelDirty.dataset.state = dirty ? "dirty" : "clean";
      elements.summaryModelDirty.textContent = dirty ? "Modifications" : "A jour";
    }
  };
  const updateEmbeddingDirtyChip = () => {
    const baseline = state.embedding.baseline || emptyEmbeddingDraft();
    const draft = state.embedding.draft || emptyEmbeddingDraft();
    let dirty = false;

    embeddingFieldSpecs.forEach((spec) => {
      const field = embeddingFieldElement(spec.key);
      const changed = toDraftString(draft[spec.key]) !== toDraftString(baseline[spec.key]);
      if (field) field.dataset.dirty = changed ? "true" : "false";
      if (changed) dirty = true;
    });

    const hasSecretChange = Boolean(toDraftString(draft.token).trim());
    dirty = dirty || hasSecretChange;

    if (elements.embeddingDirty) {
      elements.embeddingDirty.dataset.state = dirty ? "dirty" : "clean";
      elements.embeddingDirty.textContent = dirty ? "Modifications" : "A jour";
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
  const applyArbiterDraftToForm = () => {
    const draft = state.arbiterModel.draft || emptyArbiterModelDraft();
    arbiterModelFieldSpecs.forEach((spec) => {
      const input = arbiterModelFieldInput(spec.key);
      if (!input) return;
      const nextValue = toDraftString(draft[spec.key]);
      if (input.value !== nextValue) input.value = nextValue;
    });
    updateArbiterDirtyChip();
  };
  const applySummaryDraftToForm = () => {
    const draft = state.summaryModel.draft || emptySummaryModelDraft();
    summaryModelFieldSpecs.forEach((spec) => {
      const input = summaryModelFieldInput(spec.key);
      if (!input) return;
      const nextValue = toDraftString(draft[spec.key]);
      if (input.value !== nextValue) input.value = nextValue;
    });
    updateSummaryDirtyChip();
  };
  const applyEmbeddingDraftToForm = () => {
    const draft = state.embedding.draft || emptyEmbeddingDraft();
    embeddingFieldSpecs.forEach((spec) => {
      const input = embeddingFieldInput(spec.key);
      if (!input) return;
      const nextValue = toDraftString(draft[spec.key]);
      if (input.value !== nextValue) input.value = nextValue;
    });
    if (elements.embeddingTokenReplace) {
      const nextSecret = toDraftString(draft.token);
      if (elements.embeddingTokenReplace.value !== nextSecret) {
        elements.embeddingTokenReplace.value = nextSecret;
      }
    }
    updateEmbeddingDirtyChip();
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
  const applyArbiterModelView = (responsePayload) => {
    state.arbiterModel.loaded = true;
    state.arbiterModel.view = {
      payload: responsePayload.payload || {},
      source: responsePayload.source || "env",
      source_reason: responsePayload.source_reason || "unknown",
    };
    state.arbiterModel.baseline = buildArbiterModelDraftFromView(state.arbiterModel.view);
    state.arbiterModel.draft = { ...state.arbiterModel.baseline };
    clearArbiterFieldErrors();
    renderArbiterModelMeta();
    applyArbiterDraftToForm();
    renderArbiterModelChecks([]);
  };
  const applySummaryModelView = (responsePayload) => {
    state.summaryModel.loaded = true;
    state.summaryModel.view = {
      payload: responsePayload.payload || {},
      source: responsePayload.source || "env",
      source_reason: responsePayload.source_reason || "unknown",
    };
    state.summaryModel.baseline = buildSummaryModelDraftFromView(state.summaryModel.view);
    state.summaryModel.draft = { ...state.summaryModel.baseline };
    clearSummaryFieldErrors();
    renderSummaryModelMeta();
    applySummaryDraftToForm();
    renderSummaryModelChecks([]);
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
  const resetArbiterSurface = (message, stateName = "error") => {
    state.arbiterModel.loaded = false;
    state.arbiterModel.view = null;
    state.arbiterModel.baseline = emptyArbiterModelDraft();
    state.arbiterModel.draft = emptyArbiterModelDraft();
    clearArbiterFieldErrors();
    renderArbiterModelMeta();
    applyArbiterDraftToForm();
    renderArbiterModelChecks([]);
    setArbiterControlsDisabled(true);
    setInlineStatus(elements.arbiterModelStatus, message, stateName);
  };
  const resetSummarySurface = (message, stateName = "error") => {
    state.summaryModel.loaded = false;
    state.summaryModel.view = null;
    state.summaryModel.baseline = emptySummaryModelDraft();
    state.summaryModel.draft = emptySummaryModelDraft();
    clearSummaryFieldErrors();
    renderSummaryModelMeta();
    applySummaryDraftToForm();
    renderSummaryModelChecks([]);
    setSummaryControlsDisabled(true);
    setInlineStatus(elements.summaryModelStatus, message, stateName);
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
  const setArbiterFieldError = (field, message = "") => {
    const host = arbiterModelFieldElement(field);
    const errorElement = arbiterModelErrorElement(field);
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
  const clearArbiterFieldErrors = () => {
    arbiterModelFieldSpecs.forEach((spec) => setArbiterFieldError(spec.key, ""));
  };
  const setSummaryFieldError = (field, message = "") => {
    const host = summaryModelFieldElement(field);
    const errorElement = summaryModelErrorElement(field);
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
  const clearSummaryFieldErrors = () => {
    summaryModelFieldSpecs.forEach((spec) => setSummaryFieldError(spec.key, ""));
  };
  const setEmbeddingFieldError = (field, message = "") => {
    const isSecretField = field === "token";
    const host = isSecretField ? document.getElementById("adminEmbeddingSecretCard") : embeddingFieldElement(field);
    const errorElement = embeddingErrorElement(field);
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
  const clearEmbeddingFieldErrors = () => {
    embeddingFieldSpecs.forEach((spec) => setEmbeddingFieldError(spec.key, ""));
    setEmbeddingFieldError("token", "");
  };
  const applyArbiterLocalFieldErrors = (errors) => {
    Object.entries(errors).forEach(([field, message]) => {
      setArbiterFieldError(field, message);
    });
  };
  const applySummaryLocalFieldErrors = (errors) => {
    Object.entries(errors).forEach(([field, message]) => {
      setSummaryFieldError(field, message);
    });
  };
  const applyEmbeddingLocalFieldErrors = (errors) => {
    Object.entries(errors).forEach(([field, message]) => {
      setEmbeddingFieldError(field, message);
    });
  };
  const applyArbiterBackendFieldError = (message) => {
    if (!message) return;
    arbiterModelFieldSpecs.forEach((spec) => {
      if (message.includes(`arbiter_model.${spec.key}`)) {
        setArbiterFieldError(spec.key, message);
      }
    });
  };
  const applySummaryBackendFieldError = (message) => {
    if (!message) return;
    summaryModelFieldSpecs.forEach((spec) => {
      if (message.includes(`summary_model.${spec.key}`)) {
        setSummaryFieldError(spec.key, message);
      }
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
  const setArbiterControlsDisabled = (disabled) => {
    if (elements.arbiterModelSave) elements.arbiterModelSave.disabled = disabled;
    if (elements.arbiterModelValidate) elements.arbiterModelValidate.disabled = disabled;
    arbiterModelFieldSpecs.forEach((spec) => {
      const input = arbiterModelFieldInput(spec.key);
      if (input) input.disabled = disabled;
    });
  };
  const setSummaryControlsDisabled = (disabled) => {
    if (elements.summaryModelSave) elements.summaryModelSave.disabled = disabled;
    if (elements.summaryModelValidate) elements.summaryModelValidate.disabled = disabled;
    summaryModelFieldSpecs.forEach((spec) => {
      const input = summaryModelFieldInput(spec.key);
      if (input) input.disabled = disabled;
    });
  };
  const setEmbeddingControlsDisabled = (disabled) => {
    if (elements.embeddingSave) elements.embeddingSave.disabled = disabled;
    if (elements.embeddingValidate) elements.embeddingValidate.disabled = disabled;
    if (elements.embeddingTokenReplace) elements.embeddingTokenReplace.disabled = disabled;
    embeddingFieldSpecs.forEach((spec) => {
      const input = embeddingFieldInput(spec.key);
      if (input) input.disabled = disabled;
    });
  };
  const collectArbiterFailedChecks = (checks) => {
    const errors = {};
    checks.forEach((check) => {
      if (check.ok) return;
      if (!errors[check.name]) {
        errors[check.name] = check.detail;
      }
    });
    return errors;
  };
  const collectSummaryFailedChecks = (checks) => {
    const errors = {};
    checks.forEach((check) => {
      if (check.ok) return;
      if (!errors[check.name]) {
        errors[check.name] = check.detail;
      }
    });
    return errors;
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
  const buildArbiterPatchPayload = () => {
    const payload = {};
    const localErrors = {};
    const baseline = state.arbiterModel.baseline || emptyArbiterModelDraft();
    const draft = state.arbiterModel.draft || emptyArbiterModelDraft();

    arbiterModelFieldSpecs.forEach((spec) => {
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
        payload[spec.key] = {
          value: spec.key === "timeout_s" ? Math.trunc(parsed) : parsed,
        };
        return;
      }

      payload[spec.key] = { value: nextRaw };
    });

    return {
      payload,
      localErrors,
      dirtyCount: Object.keys(payload).length,
    };
  };
  const buildSummaryPatchPayload = () => {
    const payload = {};
    const localErrors = {};
    const baseline = state.summaryModel.baseline || emptySummaryModelDraft();
    const draft = state.summaryModel.draft || emptySummaryModelDraft();

    summaryModelFieldSpecs.forEach((spec) => {
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

    return {
      payload,
      localErrors,
      dirtyCount: Object.keys(payload).length,
    };
  };
  const buildEmbeddingPatchPayload = () => {
    const payload = {};
    const localErrors = {};
    const baseline = state.embedding.baseline || emptyEmbeddingDraft();
    const draft = state.embedding.draft || emptyEmbeddingDraft();

    embeddingFieldSpecs.forEach((spec) => {
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
        payload[spec.key] = {
          value: Math.trunc(parsed),
        };
        return;
      }

      payload[spec.key] = { value: nextRaw };
    });

    const replaceValue = toDraftString(draft.token).trim();
    if (replaceValue) {
      payload.token = { replace_value: replaceValue };
    }

    return {
      payload,
      localErrors,
      dirtyCount: Object.keys(payload).length,
    };
  };
  const runArbiterValidation = async (payload) => {
    clearArbiterFieldErrors();
    renderArbiterModelChecks([]);
    setArbiterControlsDisabled(true);
    setInlineStatus(elements.arbiterModelStatus, "Validation technique en cours...", "info");

    try {
      const body = payload && Object.keys(payload).length ? { payload } : {};
      const response = await adminFetch("/api/admin/settings/arbiter-model/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (response.status === 401) {
        setInlineStatus(elements.arbiterModelStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await response.json();
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
  const runSummaryValidation = async (payload) => {
    clearSummaryFieldErrors();
    renderSummaryModelChecks([]);
    setSummaryControlsDisabled(true);
    setInlineStatus(elements.summaryModelStatus, "Validation technique en cours...", "info");

    try {
      const body = payload && Object.keys(payload).length ? { payload } : {};
      const response = await adminFetch("/api/admin/settings/summary-model/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (response.status === 401) {
        setInlineStatus(elements.summaryModelStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await response.json();
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
  const runEmbeddingValidation = async (payload) => {
    clearEmbeddingFieldErrors();
    renderEmbeddingChecks([]);
    setEmbeddingControlsDisabled(true);
    setInlineStatus(elements.embeddingStatus, "Validation technique en cours...", "info");

    try {
      const body = payload && Object.keys(payload).length ? { payload } : {};
      const response = await adminFetch("/api/admin/settings/embedding/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (response.status === 401) {
        setInlineStatus(elements.embeddingStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await response.json();
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
      const response = await adminFetch("/api/admin/settings/arbiter-model", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          updated_by: "admin_ui",
          payload,
        }),
      });

      if (response.status === 401) {
        setInlineStatus(elements.arbiterModelStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await response.json();
      if (!response.ok || !data.ok) {
        applyArbiterBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
        setInlineStatus(elements.arbiterModelStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
        return;
      }

      applyArbiterModelView(data);
      setArbiterControlsDisabled(false);
      setInlineStatus(elements.arbiterModelStatus, "Modele arbitre enregistre.", "ok");
      banner("Modele arbitre enregistre.", "ok");
      void loadRuntimeStatus();
    } catch (_error) {
      setInlineStatus(elements.arbiterModelStatus, "Enregistrement impossible pour le moment.", "error");
    } finally {
      setArbiterControlsDisabled(!state.arbiterModel.loaded);
    }
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
    setInlineStatus(elements.summaryModelStatus, "Enregistrement du modele resumieur...", "info");

    try {
      const response = await adminFetch("/api/admin/settings/summary-model", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          updated_by: "admin_ui",
          payload,
        }),
      });

      if (response.status === 401) {
        setInlineStatus(elements.summaryModelStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await response.json();
      if (!response.ok || !data.ok) {
        applySummaryBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
        setInlineStatus(elements.summaryModelStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
        return;
      }

      applySummaryModelView(data);
      setSummaryControlsDisabled(false);
      setInlineStatus(elements.summaryModelStatus, "Modele resumieur enregistre.", "ok");
      banner("Modele resumieur enregistre.", "ok");
      void loadRuntimeStatus();
    } catch (_error) {
      setInlineStatus(elements.summaryModelStatus, "Enregistrement impossible pour le moment.", "error");
    } finally {
      setSummaryControlsDisabled(!state.summaryModel.loaded);
    }
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
      const response = await adminFetch("/api/admin/settings/embedding", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          updated_by: "admin_ui",
          payload,
        }),
      });

      if (response.status === 401) {
        setInlineStatus(elements.embeddingStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await response.json();
      if (!response.ok || !data.ok) {
        applyEmbeddingBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
        setInlineStatus(elements.embeddingStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
        return;
      }

      applyEmbeddingView(data);
      setEmbeddingControlsDisabled(false);
      setInlineStatus(elements.embeddingStatus, "Bloc embeddings enregistre.", "ok");
      banner("Bloc embeddings enregistre.", "ok");
      void loadRuntimeStatus();
    } catch (_error) {
      setInlineStatus(elements.embeddingStatus, "Enregistrement impossible pour le moment.", "error");
    } finally {
      setEmbeddingControlsDisabled(!state.embedding.loaded);
    }
  };
  const loadArbiterModelSection = async () => {
    ensureArbiterModelFieldSkeleton();
    clearArbiterFieldErrors();
    setArbiterControlsDisabled(true);
    setInlineStatus(elements.arbiterModelStatus, "Chargement du modele arbitre...", "info");

    try {
      const response = await adminFetch("/api/admin/settings/arbiter-model");
      if (response.status === 401) {
        resetArbiterSurface("Acces admin requis pour charger le modele arbitre.", "error");
        return;
      }

      const data = await response.json();
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
  const loadSummaryModelSection = async () => {
    ensureSummaryModelFieldSkeleton();
    clearSummaryFieldErrors();
    setSummaryControlsDisabled(true);
    setInlineStatus(elements.summaryModelStatus, "Chargement du modele resumieur...", "info");

    try {
      const response = await adminFetch("/api/admin/settings/summary-model");
      if (response.status === 401) {
        resetSummarySurface("Acces admin requis pour charger le modele resumieur.", "error");
        return;
      }

      const data = await response.json();
      if (!response.ok || !data.ok) {
        resetSummarySurface(data.error || `Lecture impossible (${response.status}).`, "error");
        return;
      }

      applySummaryModelView(data);
      setSummaryControlsDisabled(false);
      setInlineStatus(elements.summaryModelStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
    } catch (_error) {
      resetSummarySurface("Lecture impossible du modele resumieur pour le moment.", "error");
    }
  };
  const loadEmbeddingSection = async () => {
    ensureEmbeddingFieldSkeleton();
    clearEmbeddingFieldErrors();
    setEmbeddingControlsDisabled(true);
    setInlineStatus(elements.embeddingStatus, "Chargement du bloc embeddings...", "info");

    try {
      const response = await adminFetch("/api/admin/settings/embedding");
      if (response.status === 401) {
        resetEmbeddingSurface("Acces admin requis pour charger le bloc embeddings.", "error");
        return;
      }

      const data = await response.json();
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
      if (section.key === "arbiter_model") {
        const detailChip = document.createElement("span");
        detailChip.className = "admin-chip";
        detailChip.textContent = "Bloc detaille actif";
        meta.appendChild(detailChip);
      }
      if (section.key === "summary_model") {
        const detailChip = document.createElement("span");
        detailChip.className = "admin-chip";
        detailChip.textContent = "Bloc detaille actif";
        meta.appendChild(detailChip);
      }
      if (section.key === "embedding") {
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
      banner("Etat runtime charge. Les blocs detailes deja ouverts sont maintenant editables dans cette tranche.", "ok");
    } catch (_error) {
      banner("Lecture admin impossible pour le moment.", "error");
    }
  };

  const loadAdminSurface = async () => {
    await Promise.all([loadRuntimeStatus(), loadMainModelSection(), loadArbiterModelSection(), loadSummaryModelSection(), loadEmbeddingSection()]);
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

  ensureMainModelFieldSkeleton();
  ensureArbiterModelFieldSkeleton();
  ensureSummaryModelFieldSkeleton();
  ensureEmbeddingFieldSkeleton();
  state.mainModel.baseline = emptyMainModelDraft();
  state.mainModel.draft = emptyMainModelDraft();
  state.arbiterModel.baseline = emptyArbiterModelDraft();
  state.arbiterModel.draft = emptyArbiterModelDraft();
  state.summaryModel.baseline = emptySummaryModelDraft();
  state.summaryModel.draft = emptySummaryModelDraft();
  state.embedding.baseline = emptyEmbeddingDraft();
  state.embedding.draft = emptyEmbeddingDraft();
  renderMainModelMeta();
  applyMainModelDraftToForm();
  renderMainModelChecks([]);
  renderArbiterModelMeta();
  applyArbiterDraftToForm();
  renderArbiterModelChecks([]);
  renderSummaryModelMeta();
  applySummaryDraftToForm();
  renderSummaryModelChecks([]);
  renderEmbeddingMeta();
  applyEmbeddingDraftToForm();
  renderEmbeddingChecks([]);
  setMainModelControlsDisabled(true);
  setArbiterControlsDisabled(true);
  setSummaryControlsDisabled(true);
  setEmbeddingControlsDisabled(true);
  updateTokenState();
  renderSectionCards({
    sections: Object.fromEntries(sections.map((section) => [section.key, { source: "env", source_reason: "loading" }])),
    bootstrap: { database_dsn_mode: "external_bootstrap" },
  });
  void loadAdminSurface();
})();
