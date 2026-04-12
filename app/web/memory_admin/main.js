(() => {
  const api = window.FridaMemoryAdminApi;
  const overview = window.FridaMemoryAdminRenderOverview;
  const turns = window.FridaMemoryAdminRenderTurns;
  if (!api || !overview || !turns) {
    throw new Error("Memory Admin dependencies are missing");
  }

  const elements = {
    refresh: document.getElementById("memoryAdminRefresh"),
    statusBanner: document.getElementById("memoryAdminStatusBanner"),
    modeMeta: document.getElementById("memoryAdminModeMeta"),
    rerankerMeta: document.getElementById("memoryAdminRerankerMeta"),
    sourcesMeta: document.getElementById("memoryAdminSourcesMeta"),
    scopeCards: document.getElementById("memoryAdminScopeCards"),
    sourcesLegend: document.getElementById("memoryAdminSourcesLegend"),
    durableCards: document.getElementById("memoryAdminDurableCards"),
    durableDetails: document.getElementById("memoryAdminDurableDetails"),
    retrievalCards: document.getElementById("memoryAdminRetrievalCards"),
    embeddingsCards: document.getElementById("memoryAdminEmbeddingsCards"),
    basketCards: document.getElementById("memoryAdminBasketCards"),
    arbiterCards: document.getElementById("memoryAdminArbiterCards"),
    arbiterRuntimeMetrics: document.getElementById("memoryAdminArbiterRuntimeMetrics"),
    injectionCards: document.getElementById("memoryAdminInjectionCards"),
    recentTurns: document.getElementById("memoryAdminRecentTurns"),
    conversationId: document.getElementById("memoryAdminConversationId"),
    turnId: document.getElementById("memoryAdminTurnId"),
    turnStages: document.getElementById("memoryAdminTurnStages"),
    arbiterMeta: document.getElementById("memoryAdminArbiterMeta"),
    arbiterList: document.getElementById("memoryAdminArbiterList"),
  };

  const state = {
    dashboard: null,
    conversationId: "",
    turnId: "",
  };

  const syncSelectionMeta = () => {
    state.conversationId = overview.toText(elements.conversationId?.value);
    state.turnId = overview.toText(elements.turnId?.value);
  };

  const loadMetadata = async ({ conversationId = "", turnId = "" } = {}) => {
    const payload = await api.fetchLogMetadata({ conversationId });
    turns.renderConversationOptions(elements.conversationId, payload.conversations, conversationId);
    turns.renderTurnOptions(elements.turnId, payload.turns, turnId, conversationId);
    syncSelectionMeta();
  };

  const loadTurnInspection = async () => {
    if (!state.conversationId || !state.turnId) {
      turns.renderTurnInspection(elements.turnStages, []);
      return;
    }
    const payload = await api.fetchTurnLogs({
      conversationId: state.conversationId,
      turnId: state.turnId,
      limit: 120,
    });
    turns.renderTurnInspection(elements.turnStages, payload.items);
  };

  const loadArbiterDecisions = async () => {
    const payload = await api.fetchArbiterDecisions({
      conversationId: state.conversationId,
      limit: 25,
    });
    turns.renderArbiterDecisions(
      elements.arbiterList,
      elements.arbiterMeta,
      payload.items,
      state.conversationId,
    );
  };

  const renderDashboard = (payload) => {
    state.dashboard = payload;
    overview.renderHero(elements, payload);
    overview.renderScope(elements, payload);
    overview.renderDurableState(elements, payload);
    overview.renderRetrievalEmbeddings(elements, payload);
    overview.renderBasketArbiter(elements, payload);
    overview.renderInjectionAndRecentTurns(elements, payload);

    if (Array.isArray(payload.read_errors) && payload.read_errors.length) {
      overview.setStatusBanner(
        elements.statusBanner,
        `Memory Admin charge avec ${payload.read_errors.length} lecture(s) degradee(s).`,
        "error",
      );
      return;
    }
    overview.setStatusBanner(
      elements.statusBanner,
      "Memory Admin charge. Les provenances durable / calculee / runtime / logs sont separees.",
      "ok",
    );
  };

  const refreshAll = async () => {
    overview.setStatusBanner(elements.statusBanner, "Chargement de Memory Admin...");
    const payload = await api.fetchDashboard({ windowDays: 7, turnLimit: 8, previewLimit: 12 });
    renderDashboard(payload);

    const suggestedTurn = payload?.recent_turns?.items?.[0] || {};
    const suggestedConversationId = state.conversationId || overview.toText(suggestedTurn.conversation_id);
    const suggestedTurnId = state.turnId || overview.toText(suggestedTurn.turn_id);
    await loadMetadata({
      conversationId: suggestedConversationId,
      turnId: suggestedTurnId,
    });
    await loadTurnInspection();
    await loadArbiterDecisions();
  };

  const onConversationChange = async () => {
    syncSelectionMeta();
    await loadMetadata({ conversationId: state.conversationId, turnId: "" });
    await loadTurnInspection();
    await loadArbiterDecisions();
  };

  const onTurnChange = async () => {
    syncSelectionMeta();
    await loadTurnInspection();
  };

  elements.refresh?.addEventListener("click", () => {
    refreshAll().catch((error) => {
      overview.setStatusBanner(
        elements.statusBanner,
        error instanceof Error ? error.message : "Echec rafraichissement Memory Admin.",
        "error",
      );
    });
  });
  elements.conversationId?.addEventListener("change", () => {
    onConversationChange().catch((error) => {
      overview.setStatusBanner(
        elements.statusBanner,
        error instanceof Error ? error.message : "Echec chargement conversation.",
        "error",
      );
    });
  });
  elements.turnId?.addEventListener("change", () => {
    onTurnChange().catch((error) => {
      overview.setStatusBanner(
        elements.statusBanner,
        error instanceof Error ? error.message : "Echec chargement tour.",
        "error",
      );
    });
  });

  refreshAll().catch((error) => {
    overview.setStatusBanner(
      elements.statusBanner,
      error instanceof Error ? error.message : "Echec chargement Memory Admin.",
      "error",
    );
  });
})();
