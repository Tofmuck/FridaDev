(() => {
  const SETTINGS_BASE = "/api/admin/settings";
  const SETTINGS_STATUS_ENDPOINT = "/api/admin/settings/status";
  const sectionRoutes = Object.freeze({
    mainModel: "main-model",
    arbiterModel: "arbiter-model",
    summaryModel: "summary-model",
    stimmungAgentModel: "stimmung-agent-model",
    validationAgentModel: "validation-agent-model",
    embedding: "embedding",
    database: "database",
    services: "services",
    resources: "resources",
  });
  const sectionEndpoints = Object.freeze({
    "main-model": "/api/admin/settings/main-model",
    "arbiter-model": "/api/admin/settings/arbiter-model",
    "summary-model": "/api/admin/settings/summary-model",
    "stimmung-agent-model": "/api/admin/settings/stimmung-agent-model",
    "validation-agent-model": "/api/admin/settings/validation-agent-model",
    embedding: "/api/admin/settings/embedding",
    database: "/api/admin/settings/database",
    services: "/api/admin/settings/services",
    resources: "/api/admin/settings/resources",
  });
  const sectionValidateEndpoints = Object.freeze({
    "main-model": "/api/admin/settings/main-model/validate",
    "arbiter-model": "/api/admin/settings/arbiter-model/validate",
    "summary-model": "/api/admin/settings/summary-model/validate",
    "stimmung-agent-model": "/api/admin/settings/stimmung-agent-model/validate",
    "validation-agent-model": "/api/admin/settings/validation-agent-model/validate",
    embedding: "/api/admin/settings/embedding/validate",
    database: "/api/admin/settings/database/validate",
    services: "/api/admin/settings/services/validate",
    resources: "/api/admin/settings/resources/validate",
  });

  const buildHeaders = (init = {}) => {
    return new Headers(init.headers || {});
  };

  const fetchAdmin = (url, init = {}) => {
    return fetch(url, {
      ...init,
      headers: buildHeaders(init),
    });
  };

  const readJson = async (response) => {
    return response.json();
  };

  const isUnauthorized = (response) => {
    return Number(response?.status) === 401;
  };

  const errorMessage = (data, fallbackMessage) => {
    const msg = data && typeof data.error === "string" ? data.error : "";
    return msg || fallbackMessage;
  };

  const sectionEndpoint = (sectionRoute) => {
    const route = String(sectionRoute || "").trim();
    if (!route) {
      throw new Error("sectionRoute is required");
    }
    return sectionEndpoints[route] || `${SETTINGS_BASE}/${route}`;
  };

  const sectionValidateEndpoint = (sectionRoute) => {
    const route = String(sectionRoute || "").trim();
    if (!route) {
      throw new Error("sectionRoute is required");
    }
    return sectionValidateEndpoints[route] || `${SETTINGS_BASE}/${route}/validate`;
  };

  const fetchAggregatedSettings = () => {
    return fetchAdmin(SETTINGS_BASE);
  };

  const fetchStatus = () => {
    return fetchAdmin(SETTINGS_STATUS_ENDPOINT);
  };

  const fetchSection = (sectionRoute) => {
    return fetchAdmin(sectionEndpoint(sectionRoute));
  };

  const patchSection = (sectionRoute, payload) => {
    return fetchAdmin(sectionEndpoint(sectionRoute), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        updated_by: "admin_ui",
        payload,
      }),
    });
  };

  const validateSection = (sectionRoute, payload) => {
    const body = payload && Object.keys(payload).length ? { payload } : {};
    return fetchAdmin(sectionValidateEndpoint(sectionRoute), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  };

  window.FridaAdminApi = Object.freeze({
    sectionRoutes,
    fetchAdmin,
    readJson,
    isUnauthorized,
    errorMessage,
    fetchAggregatedSettings,
    fetchStatus,
    fetchSection,
    patchSection,
    validateSection,
  });
})();
