(() => {
  const rows = document.getElementById("rows");
  const status = document.getElementById("status");
  const limit = document.getElementById("limit");
  const refresh = document.getElementById("refresh");
  const restart = document.getElementById("restart");

  const fetchAdmin = async (url, init = {}) => {
    return fetch(url, init);
  };

  const eventClass = (event) => {
    if (!event) return "event-default";
    if (event === "UserMessage") return "event-user";
    if (event === "AssistantText") return "event-assistant";
    if (event.startsWith("conv_")) return "event-conv";
    if (event.startsWith("llm_")) return "event-llm";
    if (event.startsWith("usage_")) return "event-usage";
    if (event.startsWith("service_")) return "event-service";
    if (event === "token_window") return "event-token";
    return "event-default";
  };

  const levelClass = (level) => {
    if (!level) return "level-info";
    return level.toUpperCase() === "ERROR" ? "level-error" : "level-info";
  };

  const sortKeys = (event, keys) => {
    const preferred = [];
    if (event === "UserMessage") {
      preferred.push("user_tokens", "message_timestamp", "conversation_id");
    } else if (event === "AssistantText") {
      preferred.push("assistant_tokens", "message_timestamp", "conversation_id");
    } else {
      preferred.push("conversation_id");
    }
    const rest = keys.filter((key) => !preferred.includes(key));
    return [...preferred, ...rest];
  };

  const formatKey = (key, event) => {
    if (event === "UserMessage" && key === "user_tokens") return "UserMSG";
    if (event === "AssistantText" && key === "assistant_tokens") return "AssistantText";
    if (key === "message_timestamp") return "timestamp_msg";
    if (key === "message_count") return "messages";
    return key;
  };

  const formatValue = (value, key) => {
    if (value === null || value === undefined) return "-";
    if (
      key.endsWith("_tokens") ||
      key === "tokens" ||
      key === "user_tokens" ||
      key === "assistant_tokens"
    ) {
      if (typeof value !== "number" || Number.isNaN(value)) return "-";
      return `${Math.max(0, Math.floor(value))} tokens`;
    }
    if (typeof value === "number") return value.toString();
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };

  const formatDetails = (log) => {
    const { timestamp, event, level, ...rest } = log || {};
    const keys = Object.keys(rest || {});
    if (!keys.length) return "-";
    const ordered = sortKeys(event || "", keys);
    const lines = ordered.map((key) => {
      const label = formatKey(key, event || "");
      return `${label}: ${formatValue(rest[key], key)}`;
    });
    return lines.join("\n");
  };

  const render = (logs) => {
    rows.innerHTML = "";
    logs.forEach((log) => {
      const tr = document.createElement("tr");

      const tdTime = document.createElement("td");
      tdTime.textContent = log.timestamp || "";
      tr.appendChild(tdTime);

      const tdEvent = document.createElement("td");
      const eventBadge = document.createElement("span");
      eventBadge.className = `badge event ${eventClass(log.event || "")}`;
      eventBadge.textContent = log.event || "";
      tdEvent.appendChild(eventBadge);
      tr.appendChild(tdEvent);

      const tdLevel = document.createElement("td");
      const levelBadge = document.createElement("span");
      levelBadge.className = `badge level ${levelClass(log.level || "")}`;
      levelBadge.textContent = log.level || "";
      tdLevel.appendChild(levelBadge);
      tr.appendChild(tdLevel);

      const tdDetails = document.createElement("td");
      const pre = document.createElement("pre");
      pre.textContent = formatDetails(log);
      tdDetails.appendChild(pre);
      tr.appendChild(tdDetails);

      rows.appendChild(tr);
    });
  };

  const loadLogs = async () => {
    const limitValue = limit.value || "200";
    status.textContent = "Chargement...";
    try {
      const res = await fetchAdmin(`/api/admin/logs?limit=${encodeURIComponent(limitValue)}`);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Erreur");
      render(data.logs || []);
      status.textContent = `OK (${(data.logs || []).length})`;
    } catch (err) {
      status.textContent = String(err || "").includes("401") || String(err || "").includes("403")
        ? "Accès admin refusé"
        : "Erreur de chargement";
      rows.innerHTML = "";
    }
  };

  const restartService = async () => {
    status.textContent = "Redémarrage de Frida...";
    try {
      const res = await fetchAdmin("/api/admin/restart", { method: "POST" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      status.textContent = "Redémarrage de Frida demandé";
    } catch (err) {
      status.textContent = String(err || "").includes("401") || String(err || "").includes("403")
        ? "Accès admin refusé"
        : "Redémarrage de Frida impossible";
    }
  };

  refresh.addEventListener("click", () => loadLogs());
  limit.addEventListener("change", () => loadLogs());
  if (restart) restart.addEventListener("click", () => restartService());

  loadLogs();
  setInterval(loadLogs, 10000);
})();
