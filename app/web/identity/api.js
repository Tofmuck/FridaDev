(() => {
  const adminApi = window.FridaAdminApi;
  const hermeneuticApi = window.FridaHermeneuticAdminApi;
  if (!adminApi || !hermeneuticApi) {
    throw new Error("identity/api.js requires admin_api.js and hermeneutic_admin/api.js");
  }

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

  const fetchIdentityRuntimeRepresentations = () => {
    return readAdminJson(
      "/api/admin/identity/runtime-representations",
      "Echec lecture des representations identity runtime.",
    );
  };

  window.FridaIdentityApi = Object.freeze({
    fetchIdentityReadModel: hermeneuticApi.fetchIdentityReadModel,
    fetchIdentityGovernance: hermeneuticApi.fetchIdentityGovernance,
    fetchCorrectionsExport: hermeneuticApi.fetchCorrectionsExport,
    updateIdentityMutable: hermeneuticApi.updateIdentityMutable,
    updateIdentityStatic: hermeneuticApi.updateIdentityStatic,
    updateIdentityGovernance: hermeneuticApi.updateIdentityGovernance,
    fetchIdentityRuntimeRepresentations,
  });
})();
