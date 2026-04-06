(() => {
  const adminApi = window.FridaAdminApi;
  const api = window.FridaIdentityApi;
  const render = window.FridaHermeneuticAdminRender;
  const staticEditor = window.FridaHermeneuticIdentityStaticEditor;
  const mutableEditor = window.FridaHermeneuticIdentityMutableEditor;
  const governance = window.FridaHermeneuticIdentityGovernance;
  const runtimeRepresentations = window.FridaIdentityRuntimeRepresentationsRender;

  if (
    !adminApi ||
    !api ||
    !render ||
    !staticEditor ||
    !mutableEditor ||
    !governance ||
    !runtimeRepresentations
  ) {
    throw new Error("Identity surface dependencies are missing");
  }

  const elements = {
    tokenButton: document.getElementById("identityTokenButton"),
    clearToken: document.getElementById("identityClearToken"),
    refresh: document.getElementById("identityRefresh"),
    statusBanner: document.getElementById("identityStatusBanner"),
    promptContractMeta: document.getElementById("identityPromptContractMeta"),
    schemaVersionMeta: document.getElementById("identitySchemaVersionMeta"),
    injectedMeta: document.getElementById("identityInjectedMeta"),
    tokenState: document.getElementById("identityTokenState"),
    currentStateMeta: document.getElementById("identityCurrentStateMeta"),
    currentState: document.getElementById("identityCurrentState"),
    runtimeRepresentationsMeta: document.getElementById("identityRuntimeRepresentationsMeta"),
    structuredRepresentation: document.getElementById("identityStructuredRepresentation"),
    injectedRepresentation: document.getElementById("identityInjectedRepresentation"),
    staticEditStatus: document.getElementById("identityStaticEditStatus"),
    staticEditors: document.getElementById("identityStaticEditors"),
    mutableEditStatus: document.getElementById("identityMutableEditStatus"),
    mutableEditors: document.getElementById("identityMutableEditors"),
    governanceStatus: document.getElementById("identityGovernanceStatus"),
    governanceMeta: document.getElementById("identityGovernanceMeta"),
    governance: document.getElementById("identityGovernance"),
    legacyLayers: document.getElementById("identityLegacyLayers"),
    correctionsList: document.getElementById("identityCorrectionsList"),
  };

  const state = {
    readModelPayload: null,
    runtimeRepresentationsPayload: null,
    governancePayload: null,
  };

  const toText = (value) => String(value == null ? "" : value).trim();
  const injectedMetaText = (injectedBlock) =>
    injectedBlock && injectedBlock.present
      ? "Texte injecte present"
      : "Aucun bloc injecte";

  const syncMeta = () => {
    const runtimePayload =
      state.runtimeRepresentationsPayload &&
      typeof state.runtimeRepresentationsPayload === "object"
        ? state.runtimeRepresentationsPayload
        : {};
    const readModelPayload =
      state.readModelPayload && typeof state.readModelPayload === "object"
        ? state.readModelPayload
        : {};
    const activeRuntime =
      readModelPayload.active_runtime &&
      typeof readModelPayload.active_runtime === "object" &&
      !Array.isArray(readModelPayload.active_runtime)
        ? readModelPayload.active_runtime
        : {};
    const injectedBlock =
      runtimePayload.injected_identity_text &&
      typeof runtimePayload.injected_identity_text === "object" &&
      !Array.isArray(runtimePayload.injected_identity_text)
        ? runtimePayload.injected_identity_text
        : {};

    elements.promptContractMeta.textContent =
      toText(runtimePayload.active_prompt_contract) ||
      toText(activeRuntime.active_prompt_contract) ||
      "n/a";
    elements.schemaVersionMeta.textContent =
      toText(runtimePayload.identity_input_schema_version) ||
      toText(activeRuntime.identity_input_schema_version) ||
      "n/a";
    elements.injectedMeta.textContent = injectedMetaText(injectedBlock);
    elements.tokenState.textContent = adminApi.readToken() ? "Session active" : "Session vide";
  };

  const loadIdentityReadModel = async () => {
    const payload = await api.fetchIdentityReadModel({ limit: 20 });
    state.readModelPayload = payload;
    staticEditor.renderIdentityStaticEditors(elements.staticEditors, payload);
    mutableEditor.renderIdentityMutableEditors(elements.mutableEditors, payload);
    render.renderIdentityReadModel(elements.currentStateMeta, elements.currentState, payload);
    runtimeRepresentations.renderLegacyLayers(elements.legacyLayers, payload);
    syncMeta();
    return payload;
  };

  const loadRuntimeRepresentations = async () => {
    const payload = await api.fetchIdentityRuntimeRepresentations();
    state.runtimeRepresentationsPayload = payload;
    runtimeRepresentations.renderIdentityRuntimeRepresentations(
      elements.runtimeRepresentationsMeta,
      elements.structuredRepresentation,
      elements.injectedRepresentation,
      payload,
    );
    syncMeta();
    return payload;
  };

  const loadIdentityGovernance = async () => {
    const payload = await api.fetchIdentityGovernance();
    state.governancePayload = payload;
    governance.renderIdentityGovernance(
      elements.governanceMeta,
      elements.governance,
      payload,
    );
    return payload;
  };

  const loadCorrections = async () => {
    const payload = await api.fetchCorrectionsExport({ windowDays: 7, limit: 20 });
    render.renderCorrections(elements.correctionsList, payload.items);
    return payload;
  };

  const refreshAll = async () => {
    render.setStatusBanner(elements.statusBanner, "Chargement de la surface Identity...", "");
    try {
      await Promise.all([
        loadIdentityReadModel(),
        loadRuntimeRepresentations(),
        loadIdentityGovernance(),
        loadCorrections(),
      ]);
      render.setStatusBanner(elements.statusBanner, "Lecture Identity ok.", "ok");
    } catch (error) {
      syncMeta();
      render.setStatusBanner(
        elements.statusBanner,
        `Lecture Identity indisponible: ${error?.message || error}`,
        "error",
      );
    }
  };

  const refreshAfterContentEdit = async () => {
    await Promise.all([
      loadIdentityReadModel(),
      loadRuntimeRepresentations(),
      loadCorrections(),
    ]);
  };

  const refreshAfterGovernanceEdit = async () => {
    await Promise.all([
      loadIdentityGovernance(),
      loadIdentityReadModel(),
      loadCorrections(),
    ]);
  };

  const handleIdentityStaticEdit = async (event) => {
    const requestPayload = staticEditor.readIdentityStaticDraft(event.target);
    if (!requestPayload) return;
    const actionLabel = requestPayload.action === "clear" ? "Vidage" : "Edition";
    staticEditor.setIdentityStaticEditStatus(
      elements.staticEditStatus,
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
        elements.staticEditStatus,
        response,
        response.changed ? "ok" : "",
      );
      await refreshAfterContentEdit();
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
        elements.staticEditStatus,
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
    if (!requestPayload) return;
    const actionLabel = requestPayload.action === "clear" ? "Effacement" : "Edition";
    mutableEditor.setIdentityMutableEditStatus(
      elements.mutableEditStatus,
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
        elements.mutableEditStatus,
        response,
        response.changed ? "ok" : "",
      );
      await refreshAfterContentEdit();
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
        elements.mutableEditStatus,
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
    if (!requestPayload) return;
    governance.setIdentityGovernanceStatus(
      elements.governanceStatus,
      {
        ok: true,
        changed_count: 0,
        changed_keys: [requestPayload.key],
        reason_code: "pending",
        validation_ok: true,
      },
      "",
    );
    render.setStatusBanner(elements.statusBanner, "Gouvernance identity en cours...", "");
    try {
      const response = await api.updateIdentityGovernance(requestPayload);
      governance.setIdentityGovernanceStatus(
        elements.governanceStatus,
        response,
        response.changed_count ? "ok" : "",
      );
      await refreshAfterGovernanceEdit();
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
        elements.governanceStatus,
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

  elements.staticEditors.addEventListener("click", (event) => {
    if (event.target.closest("[data-identity-static-action]")) {
      void handleIdentityStaticEdit(event);
    }
  });

  elements.mutableEditors.addEventListener("click", (event) => {
    if (event.target.closest("[data-identity-mutable-action]")) {
      void handleIdentityMutableEdit(event);
    }
  });

  elements.governance.addEventListener("click", (event) => {
    if (event.target.closest("[data-identity-governance-save]")) {
      void handleIdentityGovernanceEdit(event);
    }
  });

  syncMeta();
  void refreshAll();
})();
