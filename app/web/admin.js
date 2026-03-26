(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before admin.js");
  }
  const adminUiCommon = window.FridaAdminUiCommon;
  if (!adminUiCommon) {
    throw new Error("admin_ui_common.js must be loaded before admin.js");
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
  const { createResourcesSectionController } = resourcesSectionModule;
  const sectionRoutes = adminApi.sectionRoutes;
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
  const emptyDatabaseDraft = () => {
    const draft = {};
    databaseFieldSpecs.forEach((spec) => {
      draft[spec.key] = "";
    });
    draft.dsn = "";
    return draft;
  };
  const emptyServicesDraft = () => {
    const draft = {};
    servicesFieldSpecs.forEach((spec) => {
      draft[spec.key] = "";
    });
    draft.crawl4ai_token = "";
    return draft;
  };
  const emptyResourcesDraft = () => resourcesSection.emptyResourcesDraft();

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
  const databaseFieldElement = (field) => document.querySelector(`[data-database-field="${field}"]`);
  const databaseFieldInput = (field) => document.getElementById(`adminDatabase-${field}`);
  const databaseErrorElement = (field) => document.getElementById(`adminDatabaseFieldError-${field}`);
  const servicesFieldElement = (field) => document.querySelector(`[data-services-field="${field}"]`);
  const servicesFieldInput = (field) => document.getElementById(`adminServices-${field}`);
  const servicesErrorElement = (field) => document.getElementById(`adminServicesFieldError-${field}`);
  const resourcesFieldElement = (field) => resourcesSection.resourcesFieldElement(field);
  const resourcesFieldInput = (field) => resourcesSection.resourcesFieldInput(field);
  const resourcesErrorElement = (field) => resourcesSection.resourcesErrorElement(field);

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
  const renderArbiterModelChecks = (checks = []) => {
    renderCheckList(elements.arbiterModelChecks, checks);
  };
  const renderArbiterModelReadonlyInfo = () => {
    renderReadonlyInfoCards(elements.arbiterModelReadonlyInfo, state.arbiterModel.view?.readonly_info || {});
  };
  const renderSummaryModelChecks = (checks = []) => {
    renderCheckList(elements.summaryModelChecks, checks);
  };
  const renderSummaryModelReadonlyInfo = () => {
    renderReadonlyInfoCards(elements.summaryModelReadonlyInfo, state.summaryModel.view?.readonly_info || {});
  };
  const renderEmbeddingChecks = (checks = []) => {
    renderCheckList(elements.embeddingChecks, checks);
  };
  const renderDatabaseChecks = (checks = []) => {
    renderCheckList(elements.databaseChecks, checks);
  };
  const renderServicesChecks = (checks = []) => {
    renderCheckList(elements.servicesChecks, checks);
  };
  const renderServicesReadonlyInfo = () => {
    renderReadonlyInfoCards(elements.servicesReadonlyInfo, state.services.view?.readonly_info || {});
  };
  const renderResourcesChecks = (checks = []) => resourcesSection.renderResourcesChecks(checks);

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
  const ensureDatabaseFieldSkeleton = () => {
    if (!elements.databaseFields || elements.databaseFields.children.length > 0) return;

    const fragment = document.createDocumentFragment();
    databaseFieldSpecs.forEach((spec) => {
      const field = document.createElement("label");
      field.className = "admin-field";
      field.dataset.databaseField = spec.key;
      field.dataset.dirty = "false";
      field.setAttribute("for", `adminDatabase-${spec.key}`);

      const label = document.createElement("span");
      label.textContent = spec.label;

      const input = document.createElement("input");
      input.id = `adminDatabase-${spec.key}`;
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
      source.id = `adminDatabaseSource-${spec.key}`;
      source.className = "admin-field-source";
      source.textContent = "Source: chargement";

      meta.appendChild(hint);
      meta.appendChild(source);

      const error = document.createElement("p");
      error.id = `adminDatabaseFieldError-${spec.key}`;
      error.className = "admin-field-error";
      error.hidden = true;

      field.appendChild(label);
      field.appendChild(input);
      field.appendChild(meta);
      field.appendChild(error);
      fragment.appendChild(field);
    });

    elements.databaseFields.appendChild(fragment);
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
  const ensureResourcesFieldSkeleton = () => resourcesSection.ensureResourcesFieldSkeleton();

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
  const buildDatabaseDraftFromView = (view) => {
    const draft = {};
    databaseFieldSpecs.forEach((spec) => {
      draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
    });
    draft.dsn = "";
    return draft;
  };
  const buildServicesDraftFromView = (view) => {
    const draft = {};
    servicesFieldSpecs.forEach((spec) => {
      draft[spec.key] = toDraftString(view.payload?.[spec.key]?.value);
    });
    draft.crawl4ai_token = "";
    return draft;
  };
  const buildResourcesDraftFromView = (view) => resourcesSection.buildResourcesDraftFromView(view);

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
  const renderDatabaseMeta = () => {
    const view = state.database.view;
    if (!view) {
      if (elements.databaseSource) elements.databaseSource.textContent = "Section: indisponible";
      if (elements.databaseDsnSource) elements.databaseDsnSource.textContent = "DSN: indisponible";
      if (elements.databaseDsnState) elements.databaseDsnState.textContent = "Secret: indisponible";
      if (elements.databaseDsnMask) elements.databaseDsnMask.textContent = "Masque";
      databaseFieldSpecs.forEach((spec) => {
        const source = document.getElementById(`adminDatabaseSource-${spec.key}`);
        if (source) source.textContent = "Source: indisponible";
      });
      return;
    }

    if (elements.databaseSource) {
      elements.databaseSource.textContent = `Section: ${sourceLabel(view)} / ${view.source_reason}`;
    }

    const secretSource = view.secret_sources?.dsn || "missing";
    if (elements.databaseDsnSource) {
      elements.databaseDsnSource.textContent = `DSN: ${secretSourceLabel(secretSource)}`;
    }

    const secretPresent = Boolean(view.payload?.dsn?.is_set);
    if (elements.databaseDsnState) {
      elements.databaseDsnState.textContent = secretPresent ? "Secret: present" : "Secret: absent";
    }
    if (elements.databaseDsnMask) {
      elements.databaseDsnMask.textContent = secretPresent ? "Masque" : "Aucun secret";
    }

    databaseFieldSpecs.forEach((spec) => {
      const source = document.getElementById(`adminDatabaseSource-${spec.key}`);
      if (!source) return;
      source.textContent = `Source: ${fieldOriginLabel(view.payload?.[spec.key]?.origin)}`;
    });
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
  const renderResourcesMeta = () => resourcesSection.renderResourcesMeta();

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
  const updateEmbeddingDirtyChip = () => {
    updateSectionDirtyChip({
      baseline: state.embedding.baseline,
      draft: state.embedding.draft,
      emptyDraft: emptyEmbeddingDraft,
      fieldSpecs: embeddingFieldSpecs,
      fieldElement: embeddingFieldElement,
      dirtyChip: elements.embeddingDirty,
      secretKey: "token",
    });
  };
  const updateDatabaseDirtyChip = () => {
    updateSectionDirtyChip({
      baseline: state.database.baseline,
      draft: state.database.draft,
      emptyDraft: emptyDatabaseDraft,
      fieldSpecs: databaseFieldSpecs,
      fieldElement: databaseFieldElement,
      dirtyChip: elements.databaseDirty,
      secretKey: "dsn",
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
  const updateResourcesDirtyChip = () => resourcesSection.updateResourcesDirtyChip();

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
  const applyArbiterDraftToForm = () => {
    applySectionDraftToForm({
      draft: state.arbiterModel.draft,
      emptyDraft: emptyArbiterModelDraft,
      fieldSpecs: arbiterModelFieldSpecs,
      inputForField: arbiterModelFieldInput,
      onDirtyUpdate: updateArbiterDirtyChip,
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
  const applyEmbeddingDraftToForm = () => {
    applySectionDraftToForm({
      draft: state.embedding.draft,
      emptyDraft: emptyEmbeddingDraft,
      fieldSpecs: embeddingFieldSpecs,
      inputForField: embeddingFieldInput,
      secretInput: elements.embeddingTokenReplace,
      secretKey: "token",
      onDirtyUpdate: updateEmbeddingDirtyChip,
    });
  };
  const applyDatabaseDraftToForm = () => {
    applySectionDraftToForm({
      draft: state.database.draft,
      emptyDraft: emptyDatabaseDraft,
      fieldSpecs: databaseFieldSpecs,
      inputForField: databaseFieldInput,
      secretInput: elements.databaseDsnReplace,
      secretKey: "dsn",
      onDirtyUpdate: updateDatabaseDirtyChip,
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
  const applyResourcesDraftToForm = () => resourcesSection.applyResourcesDraftToForm();

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
  const applyDatabaseView = (responsePayload) => {
    state.database.loaded = true;
    state.database.view = {
      payload: responsePayload.payload || {},
      secret_sources: responsePayload.secret_sources || {},
      source: responsePayload.source || "env",
      source_reason: responsePayload.source_reason || "unknown",
    };
    state.database.baseline = buildDatabaseDraftFromView(state.database.view);
    state.database.draft = { ...state.database.baseline };
    clearDatabaseFieldErrors();
    renderDatabaseMeta();
    applyDatabaseDraftToForm();
    renderDatabaseChecks([]);
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
  const applyResourcesView = (responsePayload) => resourcesSection.applyResourcesView(responsePayload);

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
  const resetDatabaseSurface = (message, stateName = "error") => {
    state.database.loaded = false;
    state.database.view = null;
    state.database.baseline = emptyDatabaseDraft();
    state.database.draft = emptyDatabaseDraft();
    clearDatabaseFieldErrors();
    renderDatabaseMeta();
    applyDatabaseDraftToForm();
    renderDatabaseChecks([]);
    setDatabaseControlsDisabled(true);
    setInlineStatus(elements.databaseStatus, message, stateName);
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
  const resetResourcesSurface = (message, stateName = "error") => {
    resourcesSection.resetResourcesSurface(message, stateName);
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
    applyFieldError(host, errorElement, message);
  };
  const clearArbiterFieldErrors = () => {
    arbiterModelFieldSpecs.forEach((spec) => setArbiterFieldError(spec.key, ""));
  };
  const setSummaryFieldError = (field, message = "") => {
    const host = summaryModelFieldElement(field);
    const errorElement = summaryModelErrorElement(field);
    applyFieldError(host, errorElement, message);
  };
  const clearSummaryFieldErrors = () => {
    summaryModelFieldSpecs.forEach((spec) => setSummaryFieldError(spec.key, ""));
  };
  const setEmbeddingFieldError = (field, message = "") => {
    const isSecretField = field === "token";
    const host = isSecretField ? document.getElementById("adminEmbeddingSecretCard") : embeddingFieldElement(field);
    const errorElement = embeddingErrorElement(field);
    applyFieldError(host, errorElement, message);
  };
  const clearEmbeddingFieldErrors = () => {
    embeddingFieldSpecs.forEach((spec) => setEmbeddingFieldError(spec.key, ""));
    setEmbeddingFieldError("token", "");
  };
  const setDatabaseFieldError = (field, message = "") => {
    const isSecretField = field === "dsn";
    const host = isSecretField ? document.getElementById("adminDatabaseSecretCard") : databaseFieldElement(field);
    const errorElement = databaseErrorElement(field);
    applyFieldError(host, errorElement, message);
  };
  const clearDatabaseFieldErrors = () => {
    databaseFieldSpecs.forEach((spec) => setDatabaseFieldError(spec.key, ""));
    setDatabaseFieldError("dsn", "");
  };
  const setServicesFieldError = (field, message = "") => {
    const isSecretField = field === "crawl4ai_token";
    const host = isSecretField ? document.getElementById("adminServicesSecretCard") : servicesFieldElement(field);
    const errorElement = servicesErrorElement(field);
    applyFieldError(host, errorElement, message);
  };
  const clearServicesFieldErrors = () => {
    servicesFieldSpecs.forEach((spec) => setServicesFieldError(spec.key, ""));
    setServicesFieldError("crawl4ai_token", "");
  };
  const setResourcesFieldError = (field, message = "") => resourcesSection.setResourcesFieldError(field, message);
  const clearResourcesFieldErrors = () => resourcesSection.clearResourcesFieldErrors();
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
  const applyDatabaseLocalFieldErrors = (errors) => {
    Object.entries(errors).forEach(([field, message]) => {
      setDatabaseFieldError(field, message);
    });
  };
  const applyServicesLocalFieldErrors = (errors) => {
    Object.entries(errors).forEach(([field, message]) => {
      setServicesFieldError(field, message);
    });
  };
  const applyResourcesLocalFieldErrors = (errors) => resourcesSection.applyResourcesLocalFieldErrors(errors);
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
  const applyDatabaseBackendFieldError = (message) => {
    if (!message) return;
    if (message.includes("database.dsn")) {
      setDatabaseFieldError("dsn", message);
      return;
    }
    databaseFieldSpecs.forEach((spec) => {
      if (message.includes(`database.${spec.key}`)) {
        setDatabaseFieldError(spec.key, message);
      }
    });
  };
  const applyServicesBackendFieldError = (message) => {
    if (!message) return;
    if (message.includes("services.crawl4ai_token")) {
      setServicesFieldError("crawl4ai_token", message);
      return;
    }
    servicesFieldSpecs.forEach((spec) => {
      if (message.includes(`services.${spec.key}`)) {
        setServicesFieldError(spec.key, message);
      }
    });
  };
  const applyResourcesBackendFieldError = (message) => resourcesSection.applyResourcesBackendFieldError(message);
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
  const setEmbeddingControlsDisabled = (disabled) => {
    setSectionControlsDisabled(
      {
        saveButton: elements.embeddingSave,
        validateButton: elements.embeddingValidate,
        fieldSpecs: embeddingFieldSpecs,
        inputForField: embeddingFieldInput,
        extraInputs: [elements.embeddingTokenReplace],
      },
      disabled,
    );
  };
  const setDatabaseControlsDisabled = (disabled) => {
    setSectionControlsDisabled(
      {
        saveButton: elements.databaseSave,
        validateButton: elements.databaseValidate,
        fieldSpecs: databaseFieldSpecs,
        inputForField: databaseFieldInput,
        extraInputs: [elements.databaseDsnReplace],
      },
      disabled,
    );
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
  const setResourcesControlsDisabled = (disabled) => resourcesSection.setResourcesControlsDisabled(disabled);
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
  const collectDatabaseFailedChecks = (checks) => {
    const errors = {};
    checks.forEach((check) => {
      if (check.ok) return;
      const field = databaseCheckFieldMap[check.name] || check.name;
      if (!errors[field]) {
        errors[field] = check.detail;
      }
    });
    return errors;
  };
  const collectServicesFailedChecks = (checks) => {
    const errors = {};
    checks.forEach((check) => {
      if (check.ok) return;
      const field = servicesCheckFieldMap[check.name] || check.name;
      if (!errors[field]) {
        errors[field] = check.detail;
      }
    });
    return errors;
  };
  const collectResourcesFailedChecks = (checks) => resourcesSection.collectResourcesFailedChecks(checks);
  const buildArbiterPatchPayload = () => {
    return buildSectionPatchPayload({
      baseline: state.arbiterModel.baseline,
      draft: state.arbiterModel.draft,
      emptyDraft: emptyArbiterModelDraft,
      fieldSpecs: arbiterModelFieldSpecs,
      integerFields: ["timeout_s"],
    });
  };
  const buildSummaryPatchPayload = () => {
    return buildSectionPatchPayload({
      baseline: state.summaryModel.baseline,
      draft: state.summaryModel.draft,
      emptyDraft: emptySummaryModelDraft,
      fieldSpecs: summaryModelFieldSpecs,
    });
  };
  const buildEmbeddingPatchPayload = () => {
    return buildSectionPatchPayload({
      baseline: state.embedding.baseline,
      draft: state.embedding.draft,
      emptyDraft: emptyEmbeddingDraft,
      fieldSpecs: embeddingFieldSpecs,
      integerFields: embeddingFieldSpecs.map((spec) => spec.key),
      secretKey: "token",
    });
  };
  const buildDatabasePatchPayload = () => {
    return buildSectionPatchPayload({
      baseline: state.database.baseline,
      draft: state.database.draft,
      emptyDraft: emptyDatabaseDraft,
      fieldSpecs: databaseFieldSpecs,
      secretKey: "dsn",
    });
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
  const buildResourcesPatchPayload = () => resourcesSection.buildResourcesPatchPayload();
  const runArbiterValidation = async (payload) => {
    clearArbiterFieldErrors();
    renderArbiterModelChecks([]);
    setArbiterControlsDisabled(true);
    setInlineStatus(elements.arbiterModelStatus, "Validation technique en cours...", "info");

    try {
      const response = await adminApi.validateSection(sectionRoutes.arbiterModel, payload);

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
  const runSummaryValidation = async (payload) => {
    clearSummaryFieldErrors();
    renderSummaryModelChecks([]);
    setSummaryControlsDisabled(true);
    setInlineStatus(elements.summaryModelStatus, "Validation technique en cours...", "info");

    try {
      const response = await adminApi.validateSection(sectionRoutes.summaryModel, payload);

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
  const runEmbeddingValidation = async (payload) => {
    clearEmbeddingFieldErrors();
    renderEmbeddingChecks([]);
    setEmbeddingControlsDisabled(true);
    setInlineStatus(elements.embeddingStatus, "Validation technique en cours...", "info");

    try {
      const response = await adminApi.validateSection(sectionRoutes.embedding, payload);

      if (adminApi.isUnauthorized(response)) {
        setInlineStatus(elements.embeddingStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await adminApi.readJson(response);
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
  const runDatabaseValidation = async (payload) => {
    clearDatabaseFieldErrors();
    renderDatabaseChecks([]);
    setDatabaseControlsDisabled(true);
    setInlineStatus(elements.databaseStatus, "Validation technique en cours...", "info");

    try {
      const response = await adminApi.validateSection(sectionRoutes.database, payload);

      if (adminApi.isUnauthorized(response)) {
        setInlineStatus(elements.databaseStatus, "Acces admin requis pour verifier la section.", "error");
        return { ok: false };
      }

      const data = await adminApi.readJson(response);
      if (!response.ok || !data.ok) {
        applyDatabaseBackendFieldError(data.error || `Validation impossible (${response.status}).`);
        setInlineStatus(elements.databaseStatus, data.error || `Validation impossible (${response.status}).`, "error");
        return { ok: false };
      }

      const checks = Array.isArray(data.checks) ? data.checks : [];
      renderDatabaseChecks(checks);
      const failedChecks = collectDatabaseFailedChecks(checks);
      applyDatabaseLocalFieldErrors(failedChecks);

      if (!data.valid) {
        setInlineStatus(elements.databaseStatus, "Validation technique incomplete. Corrige les champs marques.", "error");
        return { ok: false };
      }

      setInlineStatus(elements.databaseStatus, "Validation technique OK.", "ok");
      return { ok: true, data };
    } catch (_error) {
      setInlineStatus(elements.databaseStatus, "Validation impossible pour le moment.", "error");
      return { ok: false };
    } finally {
      setDatabaseControlsDisabled(!state.database.loaded);
    }
  };
  const runServicesValidation = async (payload) => {
    clearServicesFieldErrors();
    renderServicesChecks([]);
    setServicesControlsDisabled(true);
    setInlineStatus(elements.servicesStatus, "Validation technique en cours...", "info");

    try {
      const response = await adminApi.validateSection(sectionRoutes.services, payload);

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
  const runResourcesValidation = async (payload) => resourcesSection.runResourcesValidation(payload);
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
  const validateDatabaseSection = async () => {
    const { payload, localErrors } = buildDatabasePatchPayload();
    clearDatabaseFieldErrors();

    if (Object.keys(localErrors).length > 0) {
      applyDatabaseLocalFieldErrors(localErrors);
      renderDatabaseChecks([]);
      setInlineStatus(elements.databaseStatus, "Validation locale incomplete. Corrige les champs marques.", "error");
      return;
    }

    await runDatabaseValidation(payload);
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
  const validateResourcesSection = async () => resourcesSection.validateResourcesSection();
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
      const response = await adminApi.patchSection(sectionRoutes.arbiterModel, payload);

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
    setInlineStatus(elements.summaryModelStatus, "Enregistrement du modele resumeur...", "info");

    try {
      const response = await adminApi.patchSection(sectionRoutes.summaryModel, payload);

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
      const response = await adminApi.patchSection(sectionRoutes.embedding, payload);

      if (adminApi.isUnauthorized(response)) {
        setInlineStatus(elements.embeddingStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await adminApi.readJson(response);
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
  const saveDatabaseSection = async () => {
    if (!state.database.loaded) return;

    const { payload, localErrors, dirtyCount } = buildDatabasePatchPayload();
    clearDatabaseFieldErrors();

    if (Object.keys(localErrors).length > 0) {
      applyDatabaseLocalFieldErrors(localErrors);
      renderDatabaseChecks([]);
      setInlineStatus(elements.databaseStatus, "Correction requise avant enregistrement.", "error");
      return;
    }

    if (dirtyCount === 0) {
      setInlineStatus(elements.databaseStatus, "Aucune modification a enregistrer.", "info");
      return;
    }

    const validation = await runDatabaseValidation(payload);
    if (!validation.ok) return;

    setDatabaseControlsDisabled(true);
    setInlineStatus(elements.databaseStatus, "Enregistrement du bloc base de donnees...", "info");

    try {
      const response = await adminApi.patchSection(sectionRoutes.database, payload);

      if (adminApi.isUnauthorized(response)) {
        setInlineStatus(elements.databaseStatus, "Acces admin requis pour enregistrer la section.", "error");
        return;
      }

      const data = await adminApi.readJson(response);
      if (!response.ok || !data.ok) {
        applyDatabaseBackendFieldError(data.error || `Enregistrement impossible (${response.status}).`);
        setInlineStatus(elements.databaseStatus, data.error || `Enregistrement impossible (${response.status}).`, "error");
        return;
      }

      applyDatabaseView(data);
      setDatabaseControlsDisabled(false);
      setInlineStatus(elements.databaseStatus, "Bloc base de donnees enregistre.", "ok");
      banner("Bloc base de donnees enregistre.", "ok");
      void loadRuntimeStatus();
    } catch (_error) {
      setInlineStatus(elements.databaseStatus, "Enregistrement impossible pour le moment.", "error");
    } finally {
      setDatabaseControlsDisabled(!state.database.loaded);
    }
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
      const response = await adminApi.patchSection(sectionRoutes.services, payload);

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
      void loadRuntimeStatus();
    } catch (_error) {
      setInlineStatus(elements.servicesStatus, "Enregistrement impossible pour le moment.", "error");
    } finally {
      setServicesControlsDisabled(!state.services.loaded);
    }
  };
  const saveResourcesSection = async () => resourcesSection.saveResourcesSection();
  const loadArbiterModelSection = async () => {
    ensureArbiterModelFieldSkeleton();
    clearArbiterFieldErrors();
    setArbiterControlsDisabled(true);
    setInlineStatus(elements.arbiterModelStatus, "Chargement du modele arbitre...", "info");

    try {
      const response = await adminApi.fetchSection(sectionRoutes.arbiterModel);
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
  const loadSummaryModelSection = async () => {
    ensureSummaryModelFieldSkeleton();
    clearSummaryFieldErrors();
    setSummaryControlsDisabled(true);
    setInlineStatus(elements.summaryModelStatus, "Chargement du modele resumeur...", "info");

    try {
      const response = await adminApi.fetchSection(sectionRoutes.summaryModel);
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
  const loadEmbeddingSection = async () => {
    ensureEmbeddingFieldSkeleton();
    clearEmbeddingFieldErrors();
    setEmbeddingControlsDisabled(true);
    setInlineStatus(elements.embeddingStatus, "Chargement du bloc embeddings...", "info");

    try {
      const response = await adminApi.fetchSection(sectionRoutes.embedding);
      if (adminApi.isUnauthorized(response)) {
        resetEmbeddingSurface("Acces admin requis pour charger le bloc embeddings.", "error");
        return;
      }

      const data = await adminApi.readJson(response);
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
  const loadDatabaseSection = async () => {
    ensureDatabaseFieldSkeleton();
    clearDatabaseFieldErrors();
    setDatabaseControlsDisabled(true);
    setInlineStatus(elements.databaseStatus, "Chargement du bloc base de donnees...", "info");

    try {
      const response = await adminApi.fetchSection(sectionRoutes.database);
      if (adminApi.isUnauthorized(response)) {
        resetDatabaseSurface("Acces admin requis pour charger le bloc base de donnees.", "error");
        return;
      }

      const data = await adminApi.readJson(response);
      if (!response.ok || !data.ok) {
        resetDatabaseSurface(data.error || `Lecture impossible (${response.status}).`, "error");
        return;
      }

      applyDatabaseView(data);
      setDatabaseControlsDisabled(false);
      setInlineStatus(elements.databaseStatus, "Section chargee. Verifie puis enregistre les changements utiles.", "ok");
    } catch (_error) {
      resetDatabaseSurface("Lecture impossible du bloc base de donnees pour le moment.", "error");
    }
  };
  const loadServicesSection = async () => {
    ensureServicesFieldSkeleton();
    clearServicesFieldErrors();
    setServicesControlsDisabled(true);
    setInlineStatus(elements.servicesStatus, "Chargement du bloc services externes...", "info");

    try {
      const response = await adminApi.fetchSection(sectionRoutes.services);
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
  const loadResourcesSection = async () => resourcesSection.loadResourcesSection();
  const bindResourcesSectionEvents = () => resourcesSection.bindResourcesSectionEvents();

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
      loadArbiterModelSection(),
      loadSummaryModelSection(),
      loadEmbeddingSection(),
      loadDatabaseSection(),
      loadServicesSection(),
      loadResourcesSection(),
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
  elements.databaseForm?.addEventListener("input", (event) => {
    if (!state.database.draft) return;
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;

    if (target.id === "adminDatabaseDsnReplace") {
      state.database.draft.dsn = target.value;
      setDatabaseFieldError("dsn", "");
      updateDatabaseDirtyChip();
      return;
    }

    const fieldName = target.name;
    if (!fieldName) return;
    state.database.draft[fieldName] = target.value;
    setDatabaseFieldError(fieldName, "");
    updateDatabaseDirtyChip();
  });
  elements.databaseValidate?.addEventListener("click", () => {
    void validateDatabaseSection();
  });
  elements.databaseSave?.addEventListener("click", () => {
    void saveDatabaseSection();
  });
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
  bindResourcesSectionEvents();

  ensureMainModelFieldSkeleton();
  ensureArbiterModelFieldSkeleton();
  ensureSummaryModelFieldSkeleton();
  ensureEmbeddingFieldSkeleton();
  ensureDatabaseFieldSkeleton();
  ensureServicesFieldSkeleton();
  ensureResourcesFieldSkeleton();
  state.mainModel.baseline = emptyMainModelDraft();
  state.mainModel.draft = emptyMainModelDraft();
  state.arbiterModel.baseline = emptyArbiterModelDraft();
  state.arbiterModel.draft = emptyArbiterModelDraft();
  state.summaryModel.baseline = emptySummaryModelDraft();
  state.summaryModel.draft = emptySummaryModelDraft();
  state.embedding.baseline = emptyEmbeddingDraft();
  state.embedding.draft = emptyEmbeddingDraft();
  state.database.baseline = emptyDatabaseDraft();
  state.database.draft = emptyDatabaseDraft();
  state.services.baseline = emptyServicesDraft();
  state.services.draft = emptyServicesDraft();
  state.resources.baseline = emptyResourcesDraft();
  state.resources.draft = emptyResourcesDraft();
  renderMainModelMeta();
  applyMainModelDraftToForm();
  renderMainModelReadonlyInfo();
  renderMainModelChecks([]);
  renderArbiterModelMeta();
  applyArbiterDraftToForm();
  renderArbiterModelReadonlyInfo();
  renderArbiterModelChecks([]);
  renderSummaryModelMeta();
  applySummaryDraftToForm();
  renderSummaryModelReadonlyInfo();
  renderSummaryModelChecks([]);
  renderEmbeddingMeta();
  applyEmbeddingDraftToForm();
  renderEmbeddingChecks([]);
  renderDatabaseMeta();
  applyDatabaseDraftToForm();
  renderDatabaseChecks([]);
  renderServicesMeta();
  applyServicesDraftToForm();
  renderServicesReadonlyInfo();
  renderServicesChecks([]);
  renderResourcesMeta();
  applyResourcesDraftToForm();
  renderResourcesChecks([]);
  setMainModelControlsDisabled(true);
  setArbiterControlsDisabled(true);
  setSummaryControlsDisabled(true);
  setEmbeddingControlsDisabled(true);
  setDatabaseControlsDisabled(true);
  setServicesControlsDisabled(true);
  setResourcesControlsDisabled(true);
  updateTokenState();
  renderSectionCards({
    sections: Object.fromEntries(sections.map((section) => [section.key, { source: "env", source_reason: "loading" }])),
    bootstrap: { database_dsn_mode: "external_bootstrap" },
  });
  void loadAdminSurface();
})();
