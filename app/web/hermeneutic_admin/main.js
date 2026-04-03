(() => {
  const adminApi = window.FridaAdminApi;
  const api = window.FridaHermeneuticAdminApi;
  const render = window.FridaHermeneuticAdminRender;

  if (!adminApi || !api || !render) {
    throw new Error("Hermeneutic admin dependencies are missing");
  }

  const elements = {
    tokenButton: document.getElementById("hermeneuticAdminTokenButton"),
    clearToken: document.getElementById("hermeneuticAdminClearToken"),
    refresh: document.getElementById("hermeneuticAdminRefresh"),
    statusBanner: document.getElementById("hermeneuticAdminStatusBanner"),
    modeMeta: document.getElementById("hermeneuticAdminMode"),
    conversationMeta: document.getElementById("hermeneuticAdminConversationMeta"),
    turnMeta: document.getElementById("hermeneuticAdminTurnMeta"),
    tokenState: document.getElementById("hermeneuticAdminTokenState"),
    overviewCards: document.getElementById("hermeneuticOverviewCards"),
    runtimeMetrics: document.getElementById("hermeneuticRuntimeMetrics"),
    conversationId: document.getElementById("hermeneuticConversationId"),
    turnId: document.getElementById("hermeneuticTurnId"),
    turnStages: document.getElementById("hermeneuticTurnStages"),
    arbiterMeta: document.getElementById("hermeneuticArbiterMeta"),
    arbiterList: document.getElementById("hermeneuticArbiterList"),
    identitySubject: document.getElementById("hermeneuticIdentitySubject"),
    identityStatus: document.getElementById("hermeneuticIdentityStatus"),
    identityList: document.getElementById("hermeneuticIdentityList"),
    correctionsList: document.getElementById("hermeneuticCorrectionsList"),
  };

  const state = {
    conversationId: "",
    turnId: "",
    identitySubject: "all",
    identityStatus: "all",
  };

  const toText = (value) => String(value == null ? "" : value).trim();

  const syncMeta = ({ mode } = {}) => {
    elements.modeMeta.textContent = toText(mode) || "n/a";
    elements.conversationMeta.textContent = toText(state.conversationId) || "Aucune";
    elements.turnMeta.textContent = toText(state.turnId) || "Aucun";
    elements.tokenState.textContent = adminApi.readToken() ? "Session active" : "Session vide";
  };

  const chooseConversationId = (conversations) => {
    const safeItems = Array.isArray(conversations) ? conversations : [];
    if (safeItems.some((item) => toText(item?.conversation_id) === state.conversationId)) {
      return state.conversationId;
    }
    return toText(safeItems[0]?.conversation_id);
  };

  const chooseTurnId = (turns) => {
    const safeItems = Array.isArray(turns) ? turns : [];
    if (safeItems.some((item) => toText(item?.turn_id) === state.turnId)) {
      return state.turnId;
    }
    return toText(safeItems[0]?.turn_id);
  };

  const loadOverview = async () => {
    const dashboard = await api.fetchDashboard();
    render.renderOverview(elements.overviewCards, elements.runtimeMetrics, dashboard);
    syncMeta({ mode: dashboard.mode });
  };

  const loadInspection = async ({ keepTurn = true } = {}) => {
    const rootMetadata = await api.fetchLogMetadata();
    const nextConversationId = chooseConversationId(rootMetadata.conversations);
    let metadata = rootMetadata;

    if (nextConversationId) {
      metadata = await api.fetchLogMetadata({ conversationId: nextConversationId });
    }

    state.conversationId = nextConversationId;
    if (!keepTurn) {
      state.turnId = "";
    }
    state.turnId = chooseTurnId(metadata.turns);

    render.renderConversationOptions(
      elements.conversationId,
      rootMetadata.conversations,
      state.conversationId,
    );
    render.renderTurnOptions(
      elements.turnId,
      metadata.turns,
      state.turnId,
      state.conversationId,
    );
    syncMeta();

    if (!state.conversationId || !state.turnId) {
      render.renderTurnInspection(elements.turnStages, []);
      return;
    }

    const logs = await api.fetchTurnLogs({
      conversationId: state.conversationId,
      turnId: state.turnId,
      limit: 200,
    });
    render.renderTurnInspection(elements.turnStages, logs.items);
  };

  const loadArbiterDecisions = async () => {
    const payload = await api.fetchArbiterDecisions({
      conversationId: state.conversationId,
      limit: 20,
    });
    render.renderArbiterDecisions(
      elements.arbiterMeta,
      elements.arbiterList,
      payload.items,
      state.conversationId,
    );
  };

  const loadIdentityCandidates = async () => {
    state.identitySubject = toText(elements.identitySubject.value) || "all";
    state.identityStatus = toText(elements.identityStatus.value) || "all";
    const payload = await api.fetchIdentityCandidates({
      subject: state.identitySubject,
      status: state.identityStatus,
      limit: 20,
    });
    render.renderIdentityCandidates(elements.identityList, payload.items);
  };

  const loadCorrections = async () => {
    const payload = await api.fetchCorrectionsExport({ windowDays: 7, limit: 20 });
    render.renderCorrections(elements.correctionsList, payload.items);
  };

  const refreshAll = async ({ keepTurn = true } = {}) => {
    render.setStatusBanner(elements.statusBanner, "Chargement de la surface hermeneutique...", "");
    try {
      await loadOverview();
      await loadInspection({ keepTurn });
      await Promise.all([
        loadArbiterDecisions(),
        loadIdentityCandidates(),
        loadCorrections(),
      ]);
      render.setStatusBanner(elements.statusBanner, "Lecture hermeneutique ok.", "ok");
    } catch (error) {
      syncMeta();
      render.setStatusBanner(
        elements.statusBanner,
        `Lecture hermeneutique indisponible: ${error?.message || error}`,
        "error",
      );
    }
  };

  elements.tokenButton.addEventListener("click", () => {
    const nextToken = window.prompt("Token admin", adminApi.readToken());
    if (nextToken == null) return;
    adminApi.writeToken(nextToken);
    syncMeta();
    void refreshAll();
  });

  elements.clearToken.addEventListener("click", () => {
    adminApi.clearToken();
    syncMeta();
    void refreshAll();
  });

  elements.refresh.addEventListener("click", () => {
    void refreshAll();
  });

  elements.conversationId.addEventListener("change", async () => {
    state.conversationId = toText(elements.conversationId.value);
    state.turnId = "";
    await refreshAll({ keepTurn: false });
  });

  elements.turnId.addEventListener("change", () => {
    state.turnId = toText(elements.turnId.value);
    void refreshAll();
  });

  elements.identitySubject.addEventListener("change", () => {
    void loadIdentityCandidates().catch((error) => {
      render.setStatusBanner(
        elements.statusBanner,
        `Lecture identites indisponible: ${error?.message || error}`,
        "error",
      );
    });
  });

  elements.identityStatus.addEventListener("change", () => {
    void loadIdentityCandidates().catch((error) => {
      render.setStatusBanner(
        elements.statusBanner,
        `Lecture identites indisponible: ${error?.message || error}`,
        "error",
      );
    });
  });

  syncMeta();
  void refreshAll();
})();
