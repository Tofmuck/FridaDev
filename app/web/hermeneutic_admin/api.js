(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before hermeneutic_admin/api.js");
  }

  const buildQuery = (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      const normalized = String(value == null ? "" : value).trim();
      if (!normalized) return;
      query.set(key, normalized);
    });
    const suffix = query.toString();
    return suffix ? `?${suffix}` : "";
  };

  const readAdminJson = async (url, fallbackMessage) => {
    const response = await adminApi.fetchAdmin(url);
    const data = await adminApi.readJson(response);
    if (!response.ok || !data.ok) {
      const error = new Error(adminApi.errorMessage(data, fallbackMessage));
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  };

  const writeAdminJson = async (url, payload, fallbackMessage) => {
    const response = await adminApi.fetchAdmin(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await adminApi.readJson(response);
    if (!response.ok || !data.ok) {
      const error = new Error(adminApi.errorMessage(data, fallbackMessage));
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  };

  const fetchDashboard = () => {
    return readAdminJson(
      "/api/admin/hermeneutics/dashboard",
      "Echec dashboard hermeneutique.",
    );
  };

  const fetchLogMetadata = ({ conversationId = "" } = {}) => {
    return readAdminJson(
      `/api/admin/logs/chat/metadata${buildQuery({ conversation_id: conversationId })}`,
      "Echec metadata logs.",
    );
  };

  const fetchTurnLogs = ({ conversationId = "", turnId = "", limit = 200 } = {}) => {
    return readAdminJson(
      `/api/admin/logs/chat${buildQuery({
        conversation_id: conversationId,
        turn_id: turnId,
        limit,
      })}`,
      "Echec lecture logs du tour.",
    );
  };

  const fetchArbiterDecisions = ({ conversationId = "", limit = 25 } = {}) => {
    return readAdminJson(
      `/api/admin/hermeneutics/arbiter-decisions${buildQuery({
        conversation_id: conversationId,
        limit,
      })}`,
      "Echec lecture decisions arbitre.",
    );
  };

  const fetchIdentityReadModel = ({ limit = 20 } = {}) => {
    return readAdminJson(
      `/api/admin/identity/read-model${buildQuery({ limit })}`,
      "Echec lecture vue unifiee identity.",
    );
  };

  const fetchIdentityGovernance = () => {
    return readAdminJson(
      "/api/admin/identity/governance",
      "Echec lecture gouvernance identity.",
    );
  };

  const updateIdentityMutable = ({ subject = "", action = "", content = "", reason = "" } = {}) => {
    return writeAdminJson(
      "/api/admin/identity/mutable",
      {
        subject,
        action,
        content,
        reason,
      },
      "Echec edition mutable canonique.",
    );
  };

  const updateIdentityStatic = ({ subject = "", action = "", content = "", reason = "" } = {}) => {
    return writeAdminJson(
      "/api/admin/identity/static",
      {
        subject,
        action,
        content,
        reason,
      },
      "Echec edition statique canonique.",
    );
  };

  const updateIdentityGovernance = ({ updates = {}, reason = "" } = {}) => {
    return writeAdminJson(
      "/api/admin/identity/governance",
      {
        updates,
        reason,
      },
      "Echec gouvernance identity.",
    );
  };

  const fetchIdentityCandidates = ({ subject = "all", status = "all", limit = 25 } = {}) => {
    return readAdminJson(
      `/api/admin/hermeneutics/identity-candidates${buildQuery({
        subject,
        status,
        limit,
      })}`,
      "Echec lecture fragments legacy d'identite.",
    );
  };

  const fetchCorrectionsExport = ({ windowDays = 7, limit = 25 } = {}) => {
    return readAdminJson(
      `/api/admin/hermeneutics/corrections-export${buildQuery({
        window_days: windowDays,
        limit,
      })}`,
      "Echec lecture corrections recentes.",
    );
  };

  window.FridaHermeneuticAdminApi = Object.freeze({
    fetchDashboard,
    fetchLogMetadata,
    fetchTurnLogs,
    fetchArbiterDecisions,
    fetchIdentityReadModel,
    fetchIdentityGovernance,
    updateIdentityMutable,
    updateIdentityStatic,
    updateIdentityGovernance,
    fetchIdentityCandidates,
    fetchCorrectionsExport,
  });
})();
