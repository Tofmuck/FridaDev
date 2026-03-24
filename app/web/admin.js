(() => {
  const status = document.getElementById("admin-phase6-status");

  document.documentElement.dataset.adminSurface = "settings-v1-shell";

  if (!status) return;

  status.textContent =
    "Socle frontend reserve au nouvel admin V1. Les logs/restart restent backend-only pendant la transition.";
})();
