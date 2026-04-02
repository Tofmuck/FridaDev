(() => {
  const createSectionStateSlice = () => ({
    loaded: false,
    view: null,
    baseline: null,
    draft: null,
  });

  const createAdminState = () => ({
    mainModel: createSectionStateSlice(),
    arbiterModel: createSectionStateSlice(),
    summaryModel: createSectionStateSlice(),
    stimmungAgentModel: createSectionStateSlice(),
    validationAgentModel: createSectionStateSlice(),
    embedding: createSectionStateSlice(),
    database: createSectionStateSlice(),
    services: createSectionStateSlice(),
    resources: createSectionStateSlice(),
  });

  const initializeAdminSectionDrafts = (state, draftFactories = {}) => {
    Object.entries(draftFactories).forEach(([sectionKey, createDraft]) => {
      if (typeof createDraft !== "function") return;
      const sectionState = state && state[sectionKey];
      if (!sectionState) return;
      sectionState.baseline = createDraft();
      sectionState.draft = createDraft();
    });
  };

  window.FridaAdminState = Object.freeze({
    createAdminState,
    initializeAdminSectionDrafts,
  });
})();
