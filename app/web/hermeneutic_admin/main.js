(() => {
  const adminApi = window.FridaAdminApi;
  const api = window.FridaHermeneuticAdminApi;
  const render = window.FridaHermeneuticAdminRender;
  const governance = window.FridaHermeneuticIdentityGovernance;
  const staticEditor = window.FridaHermeneuticIdentityStaticEditor;
  const mutableEditor = window.FridaHermeneuticIdentityMutableEditor;
  const runtimeRepresentations = window.FridaIdentityRuntimeRepresentationsRender;

  if (!adminApi || !api || !render || !governance || !staticEditor || !mutableEditor || !runtimeRepresentations) {
    throw new Error("Hermeneutic admin dependencies are missing");
  }

  const elements = {
    refresh: document.getElementById("hermeneuticAdminRefresh"),
    statusBanner: document.getElementById("hermeneuticAdminStatusBanner"),
    modeMeta: document.getElementById("hermeneuticAdminMode"),
    modeMetaNote: document.getElementById("hermeneuticAdminModeMetaNote"),
    conversationMeta: document.getElementById("hermeneuticAdminConversationMeta"),
    turnMeta: document.getElementById("hermeneuticAdminTurnMeta"),
    overviewCards: document.getElementById("hermeneuticOverviewCards"),
    runtimeMetrics: document.getElementById("hermeneuticRuntimeMetrics"),
    conversationId: document.getElementById("hermeneuticConversationId"),
    turnId: document.getElementById("hermeneuticTurnId"),
    turnStages: document.getElementById("hermeneuticTurnStages"),
    arbiterMeta: document.getElementById("hermeneuticArbiterMeta"),
    arbiterList: document.getElementById("hermeneuticArbiterList"),
    identityStaticEditStatus: document.getElementById("hermeneuticIdentityStaticEditStatus"),
    identityStaticEditors: document.getElementById("hermeneuticIdentityStaticEditors"),
    identityMutableEditStatus: document.getElementById("hermeneuticIdentityMutableEditStatus"),
    identityMutableEditors: document.getElementById("hermeneuticIdentityMutableEditors"),
    identityGovernanceStatus: document.getElementById("hermeneuticIdentityGovernanceStatus"),
    identityGovernanceMeta: document.getElementById("hermeneuticIdentityGovernanceMeta"),
    identityGovernance: document.getElementById("hermeneuticIdentityGovernance"),
    identityReadModelMeta: document.getElementById("hermeneuticIdentityReadModelMeta"),
    identityReadModel: document.getElementById("hermeneuticIdentityReadModel"),
    identityRuntimeMeta: document.getElementById("hermeneuticIdentityRuntimeMeta"),
    identityStructuredRepresentation: document.getElementById("hermeneuticIdentityStructuredRepresentation"),
    identityInjectedRepresentation: document.getElementById("hermeneuticIdentityInjectedRepresentation"),
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
    dashboard: null,
  };

  const toText = (value) => String(value == null ? "" : value).trim();

  const buildModeObservationNote = (dashboard) => {
    const modeObservation = dashboard && typeof dashboard.mode_observation === "object"
      ? dashboard.mode_observation
      : {};
    if (modeObservation.current_mode_observed && toText(modeObservation.observed_since)) {
      return `Observe depuis ${modeObservation.observed_since} (logs admin retenus).`;
    }
    if (toText(modeObservation.latest_observed_mode) && toText(modeObservation.latest_observed_at)) {
      return `Derniere observation retenue: ${modeObservation.latest_observed_mode} le ${modeObservation.latest_observed_at}.`;
    }
    return "Aucune observation retenue du mode courant pour l'instant.";
  };

  const syncMeta = ({ mode, dashboard } = {}) => {
    const effectiveDashboard = dashboard || state.dashboard;
    elements.modeMeta.textContent = toText(mode) || "n/a";
    if (elements.modeMetaNote) {
      elements.modeMetaNote.textContent = buildModeObservationNote(effectiveDashboard);
    }
    elements.conversationMeta.textContent = toText(state.conversationId) || "Aucune";
    elements.turnMeta.textContent = toText(state.turnId) || "Aucun";
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
    state.dashboard = dashboard;
    render.renderOverview(elements.overviewCards, elements.runtimeMetrics, dashboard);
    syncMeta({ mode: dashboard.mode, dashboard });
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

  const loadIdentityReadModel = async () => {
    const payload = await api.fetchIdentityReadModel({ limit: 20 });
    staticEditor.renderIdentityStaticEditors(
      elements.identityStaticEditors,
      payload,
    );
    mutableEditor.renderIdentityMutableEditors(
      elements.identityMutableEditors,
      payload,
    );
    render.renderIdentityReadModel(
      elements.identityReadModelMeta,
      elements.identityReadModel,
      payload,
    );
    return payload;
  };

  const loadIdentityRuntimeRepresentations = async () => {
    const payload = await api.fetchIdentityRuntimeRepresentations();
    runtimeRepresentations.renderIdentityRuntimeRepresentations(
      elements.identityRuntimeMeta,
      elements.identityStructuredRepresentation,
      elements.identityInjectedRepresentation,
      payload,
    );
    return payload;
  };

  const loadIdentityGovernance = async () => {
    const payload = await api.fetchIdentityGovernance();
    governance.renderIdentityGovernance(
      elements.identityGovernanceMeta,
      elements.identityGovernance,
      payload,
    );
    return payload;
  };

  const handleIdentityStaticEdit = async (event) => {
    const requestPayload = staticEditor.readIdentityStaticDraft(event.target);
    if (!requestPayload) {
      return;
    }
    const actionLabel = requestPayload.action === "clear" ? "Vidage" : "Edition";
    staticEditor.setIdentityStaticEditStatus(
      elements.identityStaticEditStatus,
      {
        ok: true,
        subject: requestPayload.subject,
        action: requestPayload.action,
        changed: false,
        old_len: 0,
        new_len: requestPayload.action === "clear" ? 0 : requestPayload.content.length,
        stored_after: false,
        resource_field: requestPayload.subject === "llm" ? "llm_identity_path" : "user_identity_path",
        resolution_kind: "pending",
        reason_code: "pending",
      },
      "",
    );
    render.setStatusBanner(
      elements.statusBanner,
      `${actionLabel} statique canonique en cours...`,
      "",
    );
    try {
      const response = await api.updateIdentityStatic(requestPayload);
      staticEditor.setIdentityStaticEditStatus(
        elements.identityStaticEditStatus,
        response,
        response.changed ? "ok" : "",
      );
      await Promise.all([loadIdentityReadModel(), loadIdentityRuntimeRepresentations()]);
      render.setStatusBanner(
        elements.statusBanner,
        `Edition statique canonique ${response.reason_code}.`,
        "ok",
      );
    } catch (error) {
      const errorPayload = error?.data && typeof error.data === "object"
        ? error.data
        : {
            ok: false,
            subject: requestPayload.subject,
            action: requestPayload.action,
            changed: false,
            old_len: 0,
            new_len: requestPayload.action === "clear" ? 0 : requestPayload.content.length,
            stored_after: false,
            resource_field: requestPayload.subject === "llm" ? "llm_identity_path" : "user_identity_path",
            resolution_kind: "request_failed",
            reason_code: "request_failed",
            validation_error: "request_failed",
            error: error?.message || String(error),
          };
      staticEditor.setIdentityStaticEditStatus(
        elements.identityStaticEditStatus,
        errorPayload,
        "error",
      );
      render.setStatusBanner(
        elements.statusBanner,
        `Edition statique canonique indisponible: ${error?.message || error}`,
        "error",
      );
    }
  };

  const handleIdentityMutableEdit = async (event) => {
    const requestPayload = mutableEditor.readIdentityMutableDraft(event.target);
    if (!requestPayload) {
      return;
    }
    const actionLabel = requestPayload.action === "clear" ? "Effacement" : "Edition";
    mutableEditor.setIdentityMutableEditStatus(
      elements.identityMutableEditStatus,
      {
        ok: true,
        subject: requestPayload.subject,
        action: requestPayload.action,
        changed: false,
        old_len: 0,
        new_len: requestPayload.action === "clear" ? 0 : requestPayload.content.length,
        stored_after: false,
        reason_code: "pending",
      },
      "",
    );
    render.setStatusBanner(
      elements.statusBanner,
      `${actionLabel} mutable canonique en cours...`,
      "",
    );
    try {
      const response = await api.updateIdentityMutable(requestPayload);
      mutableEditor.setIdentityMutableEditStatus(
        elements.identityMutableEditStatus,
        response,
        response.changed ? "ok" : "",
      );
      await Promise.all([loadIdentityReadModel(), loadIdentityRuntimeRepresentations()]);
      render.setStatusBanner(
        elements.statusBanner,
        `Edition mutable canonique ${response.reason_code}.`,
        "ok",
      );
    } catch (error) {
      const errorPayload = error?.data && typeof error.data === "object"
        ? error.data
        : {
            ok: false,
            subject: requestPayload.subject,
            action: requestPayload.action,
            changed: false,
            old_len: 0,
            new_len: requestPayload.action === "clear" ? 0 : requestPayload.content.length,
            stored_after: false,
            reason_code: "request_failed",
            validation_error: "request_failed",
            error: error?.message || String(error),
          };
      mutableEditor.setIdentityMutableEditStatus(
        elements.identityMutableEditStatus,
        errorPayload,
        "error",
      );
      render.setStatusBanner(
        elements.statusBanner,
        `Edition mutable canonique indisponible: ${error?.message || error}`,
        "error",
      );
    }
  };

  const handleIdentityGovernanceEdit = async (event) => {
    const requestPayload = governance.readIdentityGovernanceDraft(event.target);
    if (!requestPayload) {
      return;
    }
    governance.setIdentityGovernanceStatus(
      elements.identityGovernanceStatus,
      {
        ok: true,
        changed_count: 0,
        changed_keys: [requestPayload.key],
        reason_code: "pending",
        validation_ok: true,
      },
      "",
    );
    render.setStatusBanner(
      elements.statusBanner,
      "Gouvernance identity en cours...",
      "",
    );
    try {
      const response = await api.updateIdentityGovernance(requestPayload);
      governance.setIdentityGovernanceStatus(
        elements.identityGovernanceStatus,
        response,
        response.changed_count ? "ok" : "",
      );
      await Promise.all([loadIdentityGovernance(), loadIdentityReadModel()]);
      render.setStatusBanner(
        elements.statusBanner,
        `Gouvernance identity ${response.reason_code}.`,
        "ok",
      );
    } catch (error) {
      const errorPayload = error?.data && typeof error.data === "object"
        ? error.data
        : {
            ok: false,
            changed_count: 0,
            changed_keys: [requestPayload.key],
            reason_code: "request_failed",
            validation_ok: false,
            validation_error: "request_failed",
            error: error?.message || String(error),
          };
      governance.setIdentityGovernanceStatus(
        elements.identityGovernanceStatus,
        errorPayload,
        "error",
      );
      render.setStatusBanner(
        elements.statusBanner,
        `Gouvernance identity indisponible: ${error?.message || error}`,
        "error",
      );
    }
  };

  const loadIdentityCandidates = async () => {
    state.identitySubject = toText(elements.identitySubject.value) || "all";
    state.identityStatus = toText(elements.identityStatus.value) || "all";
    const payload = await api.fetchIdentityCandidates({
      subject: state.identitySubject,
      status: state.identityStatus,
      limit: 20,
    });
    render.renderIdentityCandidates(elements.identityList, payload);
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
        loadIdentityReadModel(),
        loadIdentityRuntimeRepresentations(),
        loadIdentityGovernance(),
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
        `Lecture fragments legacy d'identite indisponible: ${error?.message || error}`,
        "error",
      );
    });
  });

  elements.identityStatus.addEventListener("change", () => {
    void loadIdentityCandidates().catch((error) => {
      render.setStatusBanner(
        elements.statusBanner,
        `Lecture fragments legacy d'identite indisponible: ${error?.message || error}`,
        "error",
      );
    });
  });

  elements.identityStaticEditors.addEventListener("click", (event) => {
    void handleIdentityStaticEdit(event);
  });

  elements.identityMutableEditors.addEventListener("click", (event) => {
    void handleIdentityMutableEdit(event);
  });

  elements.identityGovernance.addEventListener("click", (event) => {
    void handleIdentityGovernanceEdit(event);
  });

  syncMeta();
  void refreshAll();
})();
