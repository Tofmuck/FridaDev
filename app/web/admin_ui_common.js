(() => {
  const renderCheckList = (target, checks = []) => {
    if (!target) return;
    if (!checks.length) {
      target.innerHTML = '<p class="admin-check-empty">Aucune validation recente.</p>';
      return;
    }

    const fragment = document.createDocumentFragment();
    checks.forEach((check) => {
      const row = document.createElement("article");
      row.className = "admin-check";
      row.dataset.ok = check.ok ? "true" : "false";

      const name = document.createElement("strong");
      name.textContent = check.name;

      const detail = document.createElement("span");
      detail.textContent = check.detail;

      row.appendChild(name);
      row.appendChild(detail);
      fragment.appendChild(row);
    });

    target.replaceChildren(fragment);
  };

  const buildReadonlyInfoCard = (key, item = {}) => {
    const card = document.createElement("article");
    card.className = "admin-readonly-card";
    card.dataset.key = key;

    const head = document.createElement("div");
    head.className = "admin-readonly-card-head";

    const titleBlock = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.label || key;

    const label = document.createElement("p");
    label.className = "admin-readonly-label";
    label.textContent = key;

    titleBlock.appendChild(title);
    titleBlock.appendChild(label);

    const source = document.createElement("span");
    source.className = "admin-readonly-source";
    source.textContent = item.source || "read_only";

    head.appendChild(titleBlock);
    head.appendChild(source);
    card.appendChild(head);

    const value = item.value;
    if (typeof value === "string" && (value.includes("\n") || value.length > 180)) {
      const textarea = document.createElement("textarea");
      textarea.className = "admin-readonly-textarea";
      textarea.readOnly = true;
      textarea.value = value;
      card.appendChild(textarea);
      return card;
    }

    const body = document.createElement("div");
    body.className = "admin-readonly-value";
    body.textContent = value === undefined || value === null ? "" : String(value);
    card.appendChild(body);
    return card;
  };

  const renderReadonlyInfoEntries = (target, entries = []) => {
    if (!target) return;
    if (!entries.length) {
      target.innerHTML = '<p class="admin-readonly-empty">Aucune information read-only disponible.</p>';
      return;
    }

    const fragment = document.createDocumentFragment();
    entries.forEach(([key, item]) => {
      fragment.appendChild(buildReadonlyInfoCard(key, item));
    });
    target.replaceChildren(fragment);
  };

  const renderReadonlyInfoCards = (target, readonlyInfo = {}) => {
    renderReadonlyInfoEntries(target, Object.entries(readonlyInfo || {}));
  };

  const applyFieldError = (host, errorElement, message = "") => {
    if (host) {
      host.dataset.error = message ? "true" : "false";
    }
    if (!errorElement) return;
    if (message) {
      errorElement.hidden = false;
      errorElement.textContent = message;
      return;
    }
    errorElement.hidden = true;
    errorElement.textContent = "";
  };

  window.FridaAdminUiCommon = Object.freeze({
    renderCheckList,
    buildReadonlyInfoCard,
    renderReadonlyInfoEntries,
    renderReadonlyInfoCards,
    applyFieldError,
  });
})();
