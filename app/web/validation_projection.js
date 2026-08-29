(() => {
  const CANONICAL_FAMILIES = Object.freeze([
    "time_input", "memory_retrieved", "memory_arbitration", "summary_input",
    "identity_input", "recent_context_input", "recent_window_input",
    "user_turn_input", "user_turn_signals", "stimmung_input", "web_input",
  ]);
  const HISTORICAL_V1_BUDGET_CHARS = 700;
  const CURRENT_V2_BUDGET_CHARS = 3840;

  const toText = (value) => String(value == null ? "" : value).trim();
  const list = (value) => Array.isArray(value) ? value.map(toText).filter(Boolean) : [];

  const invalidDelivery = (reasonCode, contractStatus = "incomplete_or_incoherent") => ({
    authoritative: false,
    status: "unknown",
    reasonCode: reasonCode || "unproved_projection",
    chars: 0,
    budgetChars: 0,
    omittedFamilies: [],
    contractStatus,
    noDataFamilies: [],
    redundantFamilies: [],
    optionalFamilies: [],
    invalidFamilies: [],
    budgetExceededFamilies: [],
    unspecifiedFamilies: [],
  });

  const normalize = (projection) => {
    const status = toText(projection.status);
    const reasonCode = toText(projection.reasonCode);
    const chars = Number(projection.chars);
    const budgetChars = Number(projection.budgetChars);
    const includedFamilies = list(projection.includedFamilies);
    const omittedFamilies = list(projection.omittedFamilies);
    const noDataFamilies = list(projection.noDataFamilies);
    const redundantFamilies = list(projection.redundantFamilies);
    const optionalFamilies = list(projection.optionalFamilies);
    const invalidFamilies = list(projection.invalidFamilies);
    const budgetExceededFamilies = list(projection.budgetExceededFamilies);
    const unspecifiedFamilies = list(projection.unspecifiedFamilies);
    const allowedFamilies = new Set(CANONICAL_FAMILIES);
    const projectedFamilies = [...includedFamilies, ...omittedFamilies];
    const familyListsValid = projectedFamilies.every((family) => allowedFamilies.has(family))
      && new Set(projectedFamilies).size === projectedFamilies.length;
    const dispositionFamilies = [
      ...includedFamilies, ...noDataFamilies, ...redundantFamilies,
      ...optionalFamilies, ...invalidFamilies, ...budgetExceededFamilies,
    ];
    const partitionValid = dispositionFamilies.length === CANONICAL_FAMILIES.length
      && new Set(dispositionFamilies).size === CANONICAL_FAMILIES.length
      && CANONICAL_FAMILIES.every((family) => dispositionFamilies.includes(family))
      && omittedFamilies.length === CANONICAL_FAMILIES.length - includedFamilies.length
      && omittedFamilies.every((family) => !includedFamilies.includes(family));
    const version = toText(projection.version);
    const declaredContractStatus = toText(projection.contractStatus);
    const historicalV1 = ["", "historical_v1"].includes(declaredContractStatus)
      && version === "validation_canonical_inputs_v1"
      && budgetChars === HISTORICAL_V1_BUDGET_CHARS;
    const currentV2 = declaredContractStatus === "current_v2"
      && version === "validation_canonical_inputs_v2"
      && budgetChars === CURRENT_V2_BUDGET_CHARS && partitionValid;
    const reasonValid = status === "full"
      ? reasonCode === "included" && includedFamilies.includes("stimmung_input")
        && !omittedFamilies.includes("stimmung_input")
      : ["signal_not_present", "invalid_signal", "contract_budget_exceeded"].includes(reasonCode)
        && !includedFamilies.includes("stimmung_input")
        && (reasonCode === "signal_not_present" || omittedFamilies.includes("stimmung_input"));
    const stimmungDispositionValid = !currentV2 || (
      status === "full"
        ? includedFamilies.includes("stimmung_input")
        : reasonCode === "signal_not_present"
          ? noDataFamilies.includes("stimmung_input")
          : reasonCode === "invalid_signal"
            ? invalidFamilies.includes("stimmung_input")
            : budgetExceededFamilies.includes("stimmung_input")
    );
    const authoritative = projection.authoritative === true
      && toText(projection.sourceKind) === "validation_prompt_prepared"
      && (historicalV1 || currentV2)
      && ["full", "absent"].includes(status)
      && Number.isInteger(chars) && Number.isInteger(budgetChars)
      && chars >= 0 && chars <= budgetChars
      && familyListsValid && reasonValid && stimmungDispositionValid
      && projection.rawContentIncluded === false;
    if (!authoritative) {
      const unknownVersion = version && ![
        "validation_canonical_inputs_v1", "validation_canonical_inputs_v2",
      ].includes(version);
      return invalidDelivery(reasonCode, unknownVersion ? "unknown_version" : undefined);
    }
    return {
      authoritative: true,
      status,
      reasonCode,
      chars,
      budgetChars,
      omittedFamilies,
      contractStatus: historicalV1 ? "historical_v1" : declaredContractStatus,
      noDataFamilies,
      redundantFamilies,
      optionalFamilies,
      invalidFamilies,
      budgetExceededFamilies,
      unspecifiedFamilies,
    };
  };

  const fromEventPayload = (stage, payload = {}) => normalize({
    authoritative: stage === "validation_prompt_prepared",
    sourceKind: stage,
    status: payload.stimmung_delivery_status,
    reasonCode: payload.stimmung_delivery_reason_code,
    chars: payload.canonical_projection_chars,
    budgetChars: payload.canonical_projection_budget_chars,
    version: payload.canonical_projection_version,
    contractStatus: payload.canonical_projection_contract_status,
    includedFamilies: payload.canonical_projection_included_families,
    omittedFamilies: payload.canonical_projection_omitted_families,
    noDataFamilies: payload.canonical_projection_no_data_families,
    redundantFamilies: payload.canonical_projection_redundant_families,
    optionalFamilies: payload.canonical_projection_optional_families,
    invalidFamilies: payload.canonical_projection_invalid_families,
    budgetExceededFamilies: payload.canonical_projection_budget_exceeded_families,
    rawContentIncluded: payload.raw_content_included,
  });

  const fromReadModel = (provider = {}) => {
    const projection = provider.canonical_projection || {};
    return normalize({
      authoritative: projection.authoritative,
      sourceKind: projection.source_kind,
      status: projection.stimmung_delivery_status,
      reasonCode: projection.stimmung_delivery_reason_code,
      chars: projection.chars,
      budgetChars: projection.budget_chars,
      version: projection.projection_version,
      contractStatus: projection.contract_status,
      includedFamilies: projection.included_families,
      omittedFamilies: projection.omitted_families,
      noDataFamilies: projection.no_data_families,
      redundantFamilies: projection.redundant_families,
      optionalFamilies: projection.optional_families,
      invalidFamilies: projection.invalid_families,
      budgetExceededFamilies: projection.budget_exceeded_families,
      unspecifiedFamilies: projection.unspecified_families,
      rawContentIncluded: false,
    });
  };

  const invalidRequest = (reasonCode = "unproved_validation_request") => ({
    authoritative: false,
    status: "unknown",
    reasonCode,
    policyVersion: "",
    transport: "unknown",
    decisionSource: "unknown",
    requestedModel: "",
    observedModel: "",
    observedProvider: "",
    reasoningEffortRequested: "unknown",
    reasoningEffortEffective: "unknown",
    reasoningSent: false,
    reasoningExcluded: false,
    maxTokensEffective: 0,
    temperatureSent: false,
    topPSent: false,
    providerFallbacksAllowed: false,
  });

  const normalizeRequest = (request = {}) => {
    const policyVersion = toText(request.policyVersion);
    const transport = toText(request.transport);
    const decisionSource = toText(request.decisionSource);
    const requestedModel = toText(request.requestedModel);
    const requestedEffort = toText(request.reasoningEffortRequested);
    const effectiveEffort = toText(request.reasoningEffortEffective);
    const maxTokens = Number(request.maxTokensEffective);
    const active = policyVersion === "validation_request_gemini_3_7_flash_medium_v1"
      && decisionSource === "primary"
      && requestedModel === "google/gemini-3.7-flash"
      && requestedEffort === "medium" && effectiveEffort === "medium"
      && request.reasoningSent === true && request.reasoningExcluded === true
      && maxTokens === 500 && request.temperatureSent === false && request.topPSent === false;
    const fallback = policyVersion === "validation_request_gpt_5_4_nano_fallback_v1"
      && decisionSource === "fallback"
      && requestedModel === "openai/gpt-5.4-nano"
      && requestedEffort === "none" && effectiveEffort === "none"
      && request.reasoningSent === false && request.reasoningExcluded === false
      && maxTokens === 140 && request.temperatureSent === true && request.topPSent === true;
    const legacy = policyVersion === "validation_request_gemini_3_1_flash_lite_v1"
      && decisionSource === "primary"
      && requestedModel === "google/gemini-3.1-flash-lite"
      && requestedEffort === "none" && effectiveEffort === "none"
      && request.reasoningSent === false && request.reasoningExcluded === false
      && maxTokens === 140 && request.temperatureSent === true && request.topPSent === true;
    const authoritative = request.authoritative === true
      && transport === "standard"
      && request.providerFallbacksAllowed === false
      && request.providerRequireParameters === true
      && (active || fallback || legacy);
    if (!authoritative) return invalidRequest(toText(request.reasonCode));
    return {
      authoritative: true,
      status: toText(request.status) || "prepared",
      reasonCode: toText(request.reasonCode) || "observed_effective_request",
      policyVersion,
      transport,
      decisionSource,
      requestedModel,
      observedModel: toText(request.observedModel),
      observedProvider: toText(request.observedProvider),
      reasoningEffortRequested: requestedEffort,
      reasoningEffortEffective: effectiveEffort,
      reasoningSent: request.reasoningSent,
      reasoningExcluded: request.reasoningExcluded,
      maxTokensEffective: maxTokens,
      temperatureSent: request.temperatureSent,
      topPSent: request.topPSent,
      providerFallbacksAllowed: request.providerFallbacksAllowed,
    };
  };

  const requestFromEventPayload = (stage, payload = {}) => {
    const request = payload.validation_request || payload;
    return normalizeRequest({
      authoritative: stage === "validation_prompt_prepared",
      status: payload.validation_status,
      reasonCode: "observed_effective_request",
      policyVersion: request.validation_request_policy_version,
      transport: request.validation_transport,
      decisionSource: request.validation_attempt_decision_source || payload.attempt_decision_source,
      requestedModel: request.validation_requested_model,
      observedModel: payload.observed_model,
      observedProvider: payload.observed_provider,
      reasoningEffortRequested: request.validation_reasoning_effort_requested,
      reasoningEffortEffective: request.validation_reasoning_effort_effective,
      reasoningSent: request.validation_reasoning_sent,
      reasoningExcluded: request.validation_reasoning_excluded,
      maxTokensEffective: request.validation_max_tokens_effective,
      temperatureSent: request.validation_temperature_sent,
      topPSent: request.validation_top_p_sent,
      providerFallbacksAllowed: request.validation_provider_fallbacks_allowed,
      providerRequireParameters: request.validation_provider_require_parameters,
    });
  };

  const requestFromReadModel = (provider = {}) => {
    const request = provider.request || {};
    return normalizeRequest({
      authoritative: request.authoritative,
      status: request.status,
      reasonCode: request.reason_code,
      policyVersion: request.policy_version,
      transport: request.transport,
      decisionSource: request.decision_source,
      requestedModel: request.requested_model,
      observedModel: request.observed_model,
      observedProvider: request.observed_provider,
      reasoningEffortRequested: request.reasoning_effort_requested,
      reasoningEffortEffective: request.reasoning_effort_effective,
      reasoningSent: request.reasoning_sent,
      reasoningExcluded: request.reasoning_excluded,
      maxTokensEffective: request.max_tokens_effective,
      temperatureSent: request.temperature_sent,
      topPSent: request.top_p_sent,
      providerFallbacksAllowed: request.provider_fallbacks_allowed,
      providerRequireParameters: request.provider_require_parameters,
    });
  };

  window.FridaValidationProjection = Object.freeze({
    fromEventPayload,
    fromReadModel,
    requestFromEventPayload,
    requestFromReadModel,
  });
})();
