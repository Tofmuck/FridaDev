(() => {
  const adminApi = window.FridaAdminApi;
  if (!adminApi) {
    throw new Error("admin_api.js must be loaded before memory_admin/api.js");
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

  const fetchDashboard = ({ windowDays = 7, turnLimit = 8, previewLimit = 12 } = {}) => {
    return readAdminJson(
      `/api/admin/memory/dashboard${buildQuery({
        window_days: windowDays,
        turn_limit: turnLimit,
        preview_limit: previewLimit,
      })}`,
      "Echec lecture dashboard Memory Admin.",
    );
  };

  const fetchLogMetadata = ({ conversationId = "" } = {}) => {
    return readAdminJson(
      `/api/admin/logs/chat/metadata${buildQuery({ conversation_id: conversationId })}`,
      "Echec lecture metadata logs.",
    );
  };

  const fetchTurnLogs = ({ conversationId = "", turnId = "", limit = 120 } = {}) => {
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

  window.FridaMemoryAdminApi = Object.freeze({
    fetchDashboard,
    fetchLogMetadata,
    fetchTurnLogs,
    fetchArbiterDecisions,
  });
})();
