(() => {
  const state = {
    kind: "dashboard_skeleton_lot5",
    dataLoaded: false,
    rawContentLoaded: false,
  };

  function setStatus(message, status) {
    const banner = document.getElementById("dashboardStatusBanner");
    if (!banner) return;
    banner.textContent = message;
    banner.dataset.state = status;
  }

  function boot() {
    document.documentElement.dataset.dashboardSkeleton = "ready";
    window.fridaDashboardSkeleton = { ...state };
    setStatus("Squelette dashboard pret. Les donnees longues arrivent au lot suivant.", "ok");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
