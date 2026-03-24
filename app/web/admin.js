(() => {
  const TOKEN_KEY = "frida.adminToken";
  const sections = [
    {
      key: "main_model",
      title: "Modele principal",
      description: "Provider principal, routage, titres OpenRouter et echantillonnage global.",
    },
    {
      key: "arbiter_model",
      title: "Modele arbitre",
      description: "Decision memoire, timeout et reglages propres a l'arbitre.",
    },
    {
      key: "summary_model",
      title: "Modele resumieur",
      description: "Synthese conversationnelle et reglages de resume.",
    },
    {
      key: "embedding",
      title: "Embeddings",
      description: "Endpoint, modele, dimensions et top-k pour la memoire vectorielle.",
    },
    {
      key: "database",
      title: "Base de donnees",
      description: "Lecture de la config V1 cote base, avec bootstrap externe maintenu.",
    },
    {
      key: "services",
      title: "Services externes",
      description: "SearXNG, Crawl4AI et surfaces d'appel reseau.",
    },
    {
      key: "resources",
      title: "Ressources",
      description: "Chemins identite et ressources runtime externes au depot logique.",
    },
  ];

  const elements = {
    refresh: document.getElementById("adminRefresh"),
    tokenButton: document.getElementById("adminTokenButton"),
    clearToken: document.getElementById("adminClearToken"),
    statusBanner: document.getElementById("adminStatusBanner"),
    dbState: document.getElementById("adminDbState"),
    bootstrapMode: document.getElementById("adminBootstrapMode"),
    tokenState: document.getElementById("adminTokenState"),
    sectionGrid: document.getElementById("adminSectionGrid"),
  };

  const readToken = () => window.sessionStorage.getItem(TOKEN_KEY) || "";

  const writeToken = (value) => {
    const cleaned = String(value || "").trim();
    if (!cleaned) {
      window.sessionStorage.removeItem(TOKEN_KEY);
      return "";
    }
    window.sessionStorage.setItem(TOKEN_KEY, cleaned);
    return cleaned;
  };

  const sourceLabel = (sectionStatus) => {
    if (!sectionStatus) return "indisponible";
    if (sectionStatus.source === "db") return "DB";
    if (sectionStatus.source === "env") return "ENV";
    return String(sectionStatus.source || "inconnu").toUpperCase();
  };

  const statusLabel = (dbState) => {
    if (dbState === "db_rows") return "DB active";
    if (dbState === "empty_table") return "DB vide";
    if (dbState === "db_unavailable") return "DB indisponible";
    return "Etat inconnu";
  };

  const banner = (message, state = "info") => {
    if (!elements.statusBanner) return;
    elements.statusBanner.textContent = message;
    elements.statusBanner.dataset.state = state;
  };

  const updateTokenState = () => {
    if (!elements.tokenState) return;
    elements.tokenState.textContent = readToken() ? "Session active" : "Session vide";
  };

  const adminFetch = async (url, init = {}) => {
    const headers = new Headers(init.headers || {});
    const token = readToken();
    if (token) headers.set("X-Admin-Token", token);
    return fetch(url, { ...init, headers });
  };

  const promptToken = () => {
    const current = readToken();
    const next = window.prompt("Token admin", current);
    if (next === null) return false;
    writeToken(next);
    updateTokenState();
    return true;
  };

  const renderSectionCards = (status) => {
    if (!elements.sectionGrid) return;

    const fragment = document.createDocumentFragment();
    sections.forEach((section) => {
      const sectionStatus = status.sections?.[section.key];

      const card = document.createElement("article");
      card.className = "admin-card";

      const head = document.createElement("div");
      head.className = "admin-card-head";

      const titleWrap = document.createElement("div");
      const title = document.createElement("h3");
      title.textContent = section.title;
      titleWrap.appendChild(title);

      const source = document.createElement("span");
      source.className = "admin-card-source";
      source.dataset.source = sectionStatus?.source || "missing";
      source.textContent = sourceLabel(sectionStatus);

      head.appendChild(titleWrap);
      head.appendChild(source);

      const description = document.createElement("p");
      description.textContent = section.description;

      const meta = document.createElement("div");
      meta.className = "admin-card-meta";

      const reasonChip = document.createElement("span");
      reasonChip.className = "admin-chip";
      reasonChip.textContent = `Source: ${sectionStatus?.source_reason || "indisponible"}`;
      meta.appendChild(reasonChip);

      if (status.bootstrap?.database_dsn_mode && section.key === "database") {
        const bootstrapChip = document.createElement("span");
        bootstrapChip.className = "admin-chip";
        bootstrapChip.textContent = `Bootstrap: ${status.bootstrap.database_dsn_mode}`;
        meta.appendChild(bootstrapChip);
      }

      card.appendChild(head);
      card.appendChild(description);
      card.appendChild(meta);
      fragment.appendChild(card);
    });

    elements.sectionGrid.replaceChildren(fragment);
  };

  const renderStatus = (status) => {
    if (elements.dbState) {
      elements.dbState.textContent = statusLabel(status.db_state);
    }
    if (elements.bootstrapMode) {
      elements.bootstrapMode.textContent = status.bootstrap?.database_dsn_mode || "Externe";
    }
    updateTokenState();
    renderSectionCards(status);
  };

  const loadRuntimeStatus = async () => {
    banner("Chargement du statut runtime…", "info");
    try {
      const response = await adminFetch("/api/admin/settings/status");
      if (response.status === 401) {
        banner("Acces admin requis. Definis le token pour charger l'etat runtime.", "error");
        return;
      }
      if (!response.ok) {
        banner(`Lecture admin impossible (${response.status}).`, "error");
        return;
      }

      const payload = await response.json();
      if (!payload.ok) {
        banner(payload.error || "Lecture admin invalide.", "error");
        return;
      }

      renderStatus(payload);
      banner("Etat runtime charge. La configuration detaillee sera branchee section par section.", "ok");
    } catch (_error) {
      banner("Lecture admin impossible pour le moment.", "error");
    }
  };

  elements.refresh?.addEventListener("click", () => {
    void loadRuntimeStatus();
  });

  elements.tokenButton?.addEventListener("click", () => {
    if (!promptToken()) return;
    void loadRuntimeStatus();
  });

  elements.clearToken?.addEventListener("click", () => {
    writeToken("");
    updateTokenState();
    banner("Token admin efface pour cette session.", "info");
  });

  updateTokenState();
  renderSectionCards({
    sections: Object.fromEntries(sections.map((section) => [section.key, { source: "env", source_reason: "loading" }])),
    bootstrap: { database_dsn_mode: "external_bootstrap" },
  });
  void loadRuntimeStatus();
})();
