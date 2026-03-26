(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before admin.js");
  }
  const adminUiCommon = window.FridaAdminUiCommon;
  if (!adminUiCommon) {
    throw new Error("admin_ui_common.js must be loaded before admin.js");
  }
  const arbiterModelSectionModule = window.FridaAdminArbiterModelSection;
  if (
    !arbiterModelSectionModule
    || typeof arbiterModelSectionModule.createArbiterModelSectionController !== "function"
  ) {
    throw new Error("admin_section_arbiter_model.js must be loaded before admin.js");
  }
  const summaryModelSectionModule = window.FridaAdminSummaryModelSection;
  if (
    !summaryModelSectionModule
    || typeof summaryModelSectionModule.createSummaryModelSectionController !== "function"
  ) {
    throw new Error("admin_section_summary_model.js must be loaded before admin.js");
  }
  const embeddingSectionModule = window.FridaAdminEmbeddingSection;
  if (
    !embeddingSectionModule
    || typeof embeddingSectionModule.createEmbeddingSectionController !== "function"
  ) {
    throw new Error("admin_section_embedding.js must be loaded before admin.js");
  }
  const databaseSectionModule = window.FridaAdminDatabaseSection;
  if (
    !databaseSectionModule
    || typeof databaseSectionModule.createDatabaseSectionController !== "function"
  ) {
    throw new Error("admin_section_database.js must be loaded before admin.js");
  }
  const servicesSectionModule = window.FridaAdminServicesSection;
  if (
    !servicesSectionModule
    || typeof servicesSectionModule.createServicesSectionController !== "function"
  ) {
    throw new Error("admin_section_services.js must be loaded before admin.js");
  }
  const resourcesSectionModule = window.FridaAdminResourcesSection;
  if (
    !resourcesSectionModule
    || typeof resourcesSectionModule.createResourcesSectionController !== "function"
  ) {
    throw new Error("admin_section_resources.js must be loaded before admin.js");
  }
  const {
    renderCheckList,
    renderReadonlyInfoEntries,
    renderReadonlyInfoCards,
    applyFieldError,
  } = adminUiCommon;
  const { createArbiterModelSectionController } = arbiterModelSectionModule;
  const { createSummaryModelSectionController } = summaryModelSectionModule;
  const { createEmbeddingSectionController } = embeddingSectionModule;
  const { createDatabaseSectionController } = databaseSectionModule;
  const { createServicesSectionController } = servicesSectionModule;
  const { createResourcesSectionController } = resourcesSectionModule;
  const sectionRoutes = adminApi.sectionRoutes;
  let arbiterModelSection;
  let summaryModelSection;
  let embeddingSection;
  let databaseSection;
  let servicesSection;
  let resourcesSection;
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
      title: "Modele resumeur",
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
      label: "Titre resumeur",
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
    {
      key: "response_max_tokens",
      label: "Max tokens reponse",
      hint: "Budget de generation par defaut envoye au modele principal.",
      inputType: "number",
      step: "1",
      min: "1",
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
      hint: "Echantillonnage propre au resumeur.",
      inputType: "number",
      step: "0.1",
      min: "0",
      max: "2",
      autocomplete: "off",
    },
    {
      key: "top_p",
      label: "Top p",
      hint: "Coupe nucleus du resumeur.",
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
  const databaseFieldSpecs = [
    {
      key: "backend",
      label: "Backend",
      hint: "Backend runtime supporte pendant cette phase.",
      inputType: "text",
      autocomplete: "off",
    },
  ];
  const databaseCheckFieldMap = {
    dsn_transition: "dsn",
  };
  const servicesFieldSpecs = [
    {
      key: "searxng_url",
      label: "SearXNG URL",
      hint: "Endpoint de recherche federative.",
      inputType: "url",
      autocomplete: "url",
    },
    {
      key: "searxng_results",
      label: "SearXNG results",
      hint: "Nombre de resultats pris en compte cote recherche.",
      inputType: "number",
      step: "1",
      min: "1",
      autocomplete: "off",
    },
    {
      key: "crawl4ai_url",
      label: "Crawl4AI URL",
      hint: "Endpoint du service de crawl.",
      inputType: "url",
      autocomplete: "url",
    },
    {
      key: "crawl4ai_top_n",
      label: "Crawl4AI top n",
      hint: "Nombre de pages retenues dans le contexte.",
      inputType: "number",
      step: "1",
      min: "1",
      autocomplete: "off",
    },
    {
      key: "crawl4ai_max_chars",
      label: "Crawl4AI max chars",
      hint: "Budget maximal de caracteres injectes en contexte.",
      inputType: "number",
      step: "1",
      min: "1",
      autocomplete: "off",
    },
  ];
  const servicesCheckFieldMap = {
    crawl4ai_token_runtime: "crawl4ai_token",
  };
  const resourcesFieldSpecs = [
    {
      key: "llm_identity_path",
      label: "LLM identity path",
      hint: "Chemin du fichier d'identite charge cote modele.",
      inputType: "text",
      autocomplete: "off",
    },
    {
      key: "user_identity_path",
      label: "User identity path",
      hint: "Chemin du fichier d'identite utilisateur.",
      inputType: "text",
      autocomplete: "off",
    },
  ];

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
    database: {
      loaded: false,
      view: null,
      baseline: null,
      draft: null,
    },
    services: {
      loaded: false,
      view: null,
      baseline: null,
      draft: null,
    },
    resources: {
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
    mainModelSystemPromptInfo: document.getElementById("adminMainModelSystemPromptInfo"),
    mainModelHermeneuticalPromptInfo: document.getElementById("adminMainModelHermeneuticalPromptInfo"),
    mainModelReadonlyInfo: document.getElementById("adminMainModelReadonlyInfo"),
    mainModelChecks: document.getElementById("adminMainModelChecks"),
    arbiterModelForm: document.getElementById("adminArbiterModelForm"),
    arbiterModelFields: document.getElementById("adminArbiterModelFields"),
    arbiterModelStatus: document.getElementById("adminArbiterModelStatus"),
    arbiterModelSave: document.getElementById("adminArbiterModelSave"),
    arbiterModelValidate: document.getElementById("adminArbiterModelValidate"),
    arbiterModelDirty: document.getElementById("adminArbiterModelDirty"),
    arbiterModelSource: document.getElementById("adminArbiterModelSource"),
    arbiterModelReadonlyInfo: document.getElementById("adminArbiterModelReadonlyInfo"),
    arbiterModelChecks: document.getElementById("adminArbiterModelChecks"),
    summaryModelForm: document.getElementById("adminSummaryModelForm"),
    summaryModelFields: document.getElementById("adminSummaryModelFields"),
    summaryModelStatus: document.getElementById("adminSummaryModelStatus"),
    summaryModelSave: document.getElementById("adminSummaryModelSave"),
    summaryModelValidate: document.getElementById("adminSummaryModelValidate"),
    summaryModelDirty: document.getElementById("adminSummaryModelDirty"),
    summaryModelSource: document.getElementById("adminSummaryModelSource"),
    summaryModelReadonlyInfo: document.getElementById("adminSummaryModelReadonlyInfo"),
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
    databaseForm: document.getElementById("adminDatabaseForm"),
    databaseFields: document.getElementById("adminDatabaseFields"),
    databaseStatus: document.getElementById("adminDatabaseStatus"),
    databaseSave: document.getElementById("adminDatabaseSave"),
    databaseValidate: document.getElementById("adminDatabaseValidate"),
    databaseDirty: document.getElementById("adminDatabaseDirty"),
    databaseSource: document.getElementById("adminDatabaseSource"),
    databaseDsnSource: document.getElementById("adminDatabaseDsnSource"),
    databaseDsnState: document.getElementById("adminDatabaseDsnState"),
    databaseDsnMask: document.getElementById("adminDatabaseDsnMask"),
    databaseDsnReplace: document.getElementById("adminDatabaseDsnReplace"),
    databaseChecks: document.getElementById("adminDatabaseChecks"),
    servicesForm: document.getElementById("adminServicesForm"),
    servicesFields: document.getElementById("adminServicesFields"),
    servicesStatus: document.getElementById("adminServicesStatus"),
    servicesSave: document.getElementById("adminServicesSave"),
    servicesValidate: document.getElementById("adminServicesValidate"),
    servicesDirty: document.getElementById("adminServicesDirty"),
    servicesSource: document.getElementById("adminServicesSource"),
    servicesCrawl4aiTokenSource: document.getElementById("adminServicesCrawl4aiTokenSource"),
    servicesCrawl4aiTokenState: document.getElementById("adminServicesCrawl4aiTokenState"),
    servicesCrawl4aiTokenMask: document.getElementById("adminServicesCrawl4aiTokenMask"),
    servicesCrawl4aiTokenReplace: document.getElementById("adminServicesCrawl4aiTokenReplace"),
    servicesReadonlyInfo: document.getElementById("adminServicesReadonlyInfo"),
    servicesChecks: document.getElementById("adminServicesChecks"),
    resourcesForm: document.getElementById("adminResourcesForm"),
    resourcesFields: document.getElementById("adminResourcesFields"),
    resourcesStatus: document.getElementById("adminResourcesStatus"),
    resourcesSave: document.getElementById("adminResourcesSave"),
    resourcesValidate: document.getElementById("adminResourcesValidate"),
    resourcesDirty: document.getElementById("adminResourcesDirty"),
    resourcesSource: document.getElementById("adminResourcesSource"),
    resourcesChecks: document.getElementById("adminResourcesChecks"),
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
    if (origin === "db" || origin === "db_seed" || origin === "admin_ui") return "db";
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
    elements.tokenState.textContent = adminApi.readToken() ? "Session active" : "Session vide";
  };

  const promptToken = () => {
    const current = adminApi.readToken();
    const next = window.prompt("Token admin", current);
    if (next === null) return false;
    adminApi.writeToken(next);
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

  const setSectionControlsDisabled = (
    {
      saveButton,
      validateButton,
      fieldSpecs,
      inputForField,
      extraInputs = [],
    },
    disabled,
  ) => {
    if (saveButton) saveButton.disabled = disabled;
    if (validateButton) validateButton.disabled = disabled;
    extraInputs.forEach((input) => {
      if (input) input.disabled = disabled;
    });
    fieldSpecs.forEach((spec) => {
      const input = inputForField(spec.key);
      if (input) input.disabled = disabled;
    });
  };

  const buildSectionPatchPayload = ({
    baseline,
    draft,
    emptyDraft,
    fieldSpecs,
    integerFields = [],
    secretKey = null,
  }) => {
    const payload = {};
    const localErrors = {};
    const currentBaseline = baseline || emptyDraft();
    const currentDraft = draft || emptyDraft();
    const integerFieldSet = new Set(integerFields);

    fieldSpecs.forEach((spec) => {
      const nextRaw = toDraftString(currentDraft[spec.key]);
      const currentRaw = toDraftString(currentBaseline[spec.key]);
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
          value: integerFieldSet.has(spec.key) ? Math.trunc(parsed) : parsed,
        };
        return;
      }

      payload[spec.key] = { value: nextRaw };
    });

    if (secretKey) {
      const replaceValue = toDraftString(currentDraft[secretKey]).trim();
      if (replaceValue) {
        payload[secretKey] = { replace_value: replaceValue };
      }
    }

    return {
      payload,
      localErrors,
      dirtyCount: Object.keys(payload).length,
    };
  };

  const updateSectionDirtyChip = ({
    baseline,
    draft,
    emptyDraft,
    fieldSpecs,
    fieldElement,
    dirtyChip,
    secretKey = null,
  }) => {
    const currentBaseline = baseline || emptyDraft();
    const currentDraft = draft || emptyDraft();
    let dirty = false;

    fieldSpecs.forEach((spec) => {
      const field = fieldElement(spec.key);
      const changed = toDraftString(currentDraft[spec.key]) !== toDraftString(currentBaseline[spec.key]);
      if (field) field.dataset.dirty = changed ? "true" : "false";
      if (changed) dirty = true;
    });

    if (secretKey) {
      dirty = dirty || Boolean(toDraftString(currentDraft[secretKey]).trim());
    }

    if (dirtyChip) {
      dirtyChip.dataset.state = dirty ? "dirty" : "clean";
      dirtyChip.textContent = dirty ? "Modifications" : "A jour";
    }
  };

  const applySectionDraftToForm = ({
    draft,
    emptyDraft,
    fieldSpecs,
    inputForField,
    secretInput = null,
    secretKey = null,
    onDirtyUpdate = null,
  }) => {
    const currentDraft = draft || emptyDraft();
    fieldSpecs.forEach((spec) => {
      const input = inputForField(spec.key);
      if (!input) return;
      const nextValue = toDraftString(currentDraft[spec.key]);
      if (input.value !== nextValue) input.value = nextValue;
    });
    if (secretInput && secretKey) {
      const nextSecret = toDraftString(currentDraft[secretKey]);
      if (secretInput.value !== nextSecret) {
        secretInput.value = nextSecret;
      }
    }
    if (onDirtyUpdate) onDirtyUpdate();
  };

  const setFieldError = (field, message = "") => {
    const isSecretField = field === "api_key";
    const host = isSecretField ? document.querySelector(".admin-secret-card") : mainModelFieldElement(field);
    const errorElement = mainModelErrorElement(field);
    applyFieldError(host, errorElement, message);
  };

  const clearMainModelFieldErrors = () => {
    mainModelFieldSpecs.forEach((spec) => setFieldError(spec.key, ""));
    setFieldError("api_key", "");
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

  const updateDirtyChip = () => {
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
      onDirtyUpdate: updateDirtyChip,
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
      const response = await adminApi.validateSection(sectionRoutes.mainModel, payload);

      if (adminApi.isUnauthorized(response)) {
        setInlineStatus(elements.mainModelStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await adminApi.readJson(response);
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
      const response = await adminApi.patchSection(sectionRoutes.mainModel, payload);

      if (adminApi.isUnauthorized(response)) {
        setInlineStatus(elements.mainModelStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await adminApi.readJson(response);
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
      const response = await adminApi.fetchSection(sectionRoutes.mainModel);
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
      if (section.key === "database") {
        const detailChip = document.createElement("span");
        detailChip.className = "admin-chip";
        detailChip.textContent = "Bloc detaille actif";
        meta.appendChild(detailChip);
      }
      if (section.key === "services") {
        const detailChip = document.createElement("span");
        detailChip.className = "admin-chip";
        detailChip.textContent = "Bloc detaille actif";
        meta.appendChild(detailChip);
      }
      if (section.key === "resources") {
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
      const response = await adminApi.fetchStatus();
      if (adminApi.isUnauthorized(response)) {
        banner("Acces admin requis. Definis le token pour charger l'etat runtime.", "error");
        return;
      }
      if (!response.ok) {
        banner(`Lecture admin impossible (${response.status}).`, "error");
        return;
      }

      const payload = await adminApi.readJson(response);
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

  arbiterModelSection = createArbiterModelSectionController({
    adminApi,
    sectionRoute: sectionRoutes.arbiterModel,
    arbiterModelFieldSpecs,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    toDraftString,
    renderCheckList,
    renderReadonlyInfoCards,
    applyFieldError,
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved: () => void loadRuntimeStatus(),
  });

  summaryModelSection = createSummaryModelSectionController({
    adminApi,
    sectionRoute: sectionRoutes.summaryModel,
    summaryModelFieldSpecs,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    toDraftString,
    renderCheckList,
    renderReadonlyInfoCards,
    applyFieldError,
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved: () => void loadRuntimeStatus(),
  });

  embeddingSection = createEmbeddingSectionController({
    adminApi,
    sectionRoute: sectionRoutes.embedding,
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
    onSaved: () => void loadRuntimeStatus(),
  });

  databaseSection = createDatabaseSectionController({
    adminApi,
    sectionRoute: sectionRoutes.database,
    databaseFieldSpecs,
    databaseCheckFieldMap,
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
    onSaved: () => void loadRuntimeStatus(),
  });

  servicesSection = createServicesSectionController({
    adminApi,
    sectionRoute: sectionRoutes.services,
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
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved: () => void loadRuntimeStatus(),
  });

  resourcesSection = createResourcesSectionController({
    adminApi,
    sectionRoute: sectionRoutes.resources,
    resourcesFieldSpecs,
    state,
    elements,
    sourceLabel,
    fieldOriginLabel,
    toDraftString,
    renderCheckList,
    applyFieldError,
    setInlineStatus,
    setSectionControlsDisabled,
    buildSectionPatchPayload,
    updateSectionDirtyChip,
    applySectionDraftToForm,
    banner,
    onSaved: () => void loadRuntimeStatus(),
  });

  const loadAdminSurface = async () => {
    await Promise.all([
      loadRuntimeStatus(),
      loadMainModelSection(),
      arbiterModelSection.loadArbiterModelSection(),
      summaryModelSection.loadSummaryModelSection(),
      embeddingSection.loadEmbeddingSection(),
      databaseSection.loadDatabaseSection(),
      servicesSection.loadServicesSection(),
      resourcesSection.loadResourcesSection(),
    ]);
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
    adminApi.clearToken();
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
  arbiterModelSection.bindArbiterModelSectionEvents();
  summaryModelSection.bindSummaryModelSectionEvents();
  embeddingSection.bindEmbeddingSectionEvents();
  databaseSection.bindDatabaseSectionEvents();
  servicesSection.bindServicesSectionEvents();
  resourcesSection.bindResourcesSectionEvents();

  ensureMainModelFieldSkeleton();
  arbiterModelSection.ensureArbiterModelFieldSkeleton();
  summaryModelSection.ensureSummaryModelFieldSkeleton();
  embeddingSection.ensureEmbeddingFieldSkeleton();
  databaseSection.ensureDatabaseFieldSkeleton();
  servicesSection.ensureServicesFieldSkeleton();
  resourcesSection.ensureResourcesFieldSkeleton();
  state.mainModel.baseline = emptyMainModelDraft();
  state.mainModel.draft = emptyMainModelDraft();
  state.arbiterModel.baseline = arbiterModelSection.emptyArbiterModelDraft();
  state.arbiterModel.draft = arbiterModelSection.emptyArbiterModelDraft();
  state.summaryModel.baseline = summaryModelSection.emptySummaryModelDraft();
  state.summaryModel.draft = summaryModelSection.emptySummaryModelDraft();
  state.embedding.baseline = embeddingSection.emptyEmbeddingDraft();
  state.embedding.draft = embeddingSection.emptyEmbeddingDraft();
  state.database.baseline = databaseSection.emptyDatabaseDraft();
  state.database.draft = databaseSection.emptyDatabaseDraft();
  state.services.baseline = servicesSection.emptyServicesDraft();
  state.services.draft = servicesSection.emptyServicesDraft();
  state.resources.baseline = resourcesSection.emptyResourcesDraft();
  state.resources.draft = resourcesSection.emptyResourcesDraft();
  renderMainModelMeta();
  applyMainModelDraftToForm();
  renderMainModelReadonlyInfo();
  renderMainModelChecks([]);
  arbiterModelSection.renderArbiterModelMeta();
  arbiterModelSection.applyArbiterDraftToForm();
  arbiterModelSection.renderArbiterModelReadonlyInfo();
  arbiterModelSection.renderArbiterModelChecks([]);
  summaryModelSection.renderSummaryModelMeta();
  summaryModelSection.applySummaryDraftToForm();
  summaryModelSection.renderSummaryModelReadonlyInfo();
  summaryModelSection.renderSummaryModelChecks([]);
  embeddingSection.renderEmbeddingMeta();
  embeddingSection.applyEmbeddingDraftToForm();
  embeddingSection.renderEmbeddingChecks([]);
  databaseSection.renderDatabaseMeta();
  databaseSection.applyDatabaseDraftToForm();
  databaseSection.renderDatabaseChecks([]);
  servicesSection.renderServicesMeta();
  servicesSection.applyServicesDraftToForm();
  servicesSection.renderServicesReadonlyInfo();
  servicesSection.renderServicesChecks([]);
  resourcesSection.renderResourcesMeta();
  resourcesSection.applyResourcesDraftToForm();
  resourcesSection.renderResourcesChecks([]);
  setMainModelControlsDisabled(true);
  arbiterModelSection.setArbiterControlsDisabled(true);
  summaryModelSection.setSummaryControlsDisabled(true);
  embeddingSection.setEmbeddingControlsDisabled(true);
  databaseSection.setDatabaseControlsDisabled(true);
  servicesSection.setServicesControlsDisabled(true);
  resourcesSection.setResourcesControlsDisabled(true);
  updateTokenState();
  renderSectionCards({
    sections: Object.fromEntries(sections.map((section) => [section.key, { source: "env", source_reason: "loading" }])),
    bootstrap: { database_dsn_mode: "external_bootstrap" },
  });
  void loadAdminSurface();
})();
