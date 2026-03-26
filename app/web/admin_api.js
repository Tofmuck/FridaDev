(() => {
  const TOKEN_KEY = "frida.adminToken";
  const SETTINGS_BASE = "/api/admin/settings";
  const SETTINGS_STATUS_ENDPOINT = "/api/admin/settings/status";
  const sectionRoutes = Object.freeze({
    mainModel: "main-model",
    arbiterModel: "arbiter-model",
    summaryModel: "summary-model",
    embedding: "embedding",
    database: "database",
    services: "services",
    resources: "resources",
  });
  const sectionEndpoints = Object.freeze({
    "main-model": "/api/admin/settings/main-model",
    "arbiter-model": "/api/admin/settings/arbiter-model",
    "summary-model": "/api/admin/settings/summary-model",
    embedding: "/api/admin/settings/embedding",
    database: "/api/admin/settings/database",
    services: "/api/admin/settings/services",
    resources: "/api/admin/settings/resources",
  });
  const sectionValidateEndpoints = Object.freeze({
    "main-model": "/api/admin/settings/main-model/validate",
    "arbiter-model": "/api/admin/settings/arbiter-model/validate",
    "summary-model": "/api/admin/settings/summary-model/validate",
    embedding: "/api/admin/settings/embedding/validate",
    database: "/api/admin/settings/database/validate",
    services: "/api/admin/settings/services/validate",
    resources: "/api/admin/settings/resources/validate",
  });

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

  const clearToken = () => {
    writeToken("");
  };

  const buildHeaders = (init = {}) => {
    const headers = new Headers(init.headers || {});
    const token = readToken();
    if (token) headers.set("X-Admin-Token", token);
    return headers;
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
    readToken,
    writeToken,
    clearToken,
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
