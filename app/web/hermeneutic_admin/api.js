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
      throw new Error(adminApi.errorMessage(data, fallbackMessage));
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
    fetchIdentityCandidates,
    fetchCorrectionsExport,
  });
})();
