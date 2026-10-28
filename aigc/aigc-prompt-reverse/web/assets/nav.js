/**
 * 视频分析 · 壳层导航
 *
 * 左侧 = 主菜单（工作台级）
 * 视频内页 = 内容区二级页签（见 index.html #detailSubnav）
 *
 * 路由：
 *   #/analyze/input
 *   #/analyze/library
 *   #/analyze/{projectId}/{tab}
 *   tab ∈ report | overview | chapters | segments | scenes
 */
(function (global) {
  const DEFAULT_ROUTE = "analyze/input";
  const DETAIL_TABS = ["report", "overview", "chapters", "segments", "scenes"];

  /** 左侧只放主菜单，不放「当前视频」子项 */
  const NAV_GROUPS = [
    {
      id: "workspace",
      label: "工作台",
      items: [
        { route: "analyze/input", label: "开始反推", icon: "✦" },
        { route: "analyze/library", label: "视频库", icon: "📂" },
      ],
    },
  ];

  let activeRoute = "";
  let activeProjectId = null;
  let projectTitle = "";
  const handlers = new Set();

  function normalizeRoute(route) {
    return String(route || "")
      .replace(/^#\/?/, "")
      .replace(/\/+$/, "") || DEFAULT_ROUTE;
  }

  function parseRoute(route) {
    const r = normalizeRoute(route);
    const parts = r.split("/");

    if (parts[0] !== "analyze") {
      return { raw: DEFAULT_ROUTE, module: "analyze", view: "input" };
    }

    if (parts[1] === "input") {
      return { raw: r, module: "analyze", view: "input" };
    }
    if (parts[1] === "library") {
      return { raw: r, module: "analyze", view: "library" };
    }

    // 兼容旧路由 #/analyze/detail/:tab
    if (parts[1] === "detail") {
      const tab = DETAIL_TABS.includes(parts[2]) ? parts[2] : "report";
      return {
        raw: r,
        module: "analyze",
        view: "detail",
        tab,
        projectId: activeProjectId,
      };
    }

    // #/analyze/:projectId/:tab
    if (parts[1] && !["input", "library", "detail"].includes(parts[1])) {
      let tab = parts[2] || "report";
      if (tab === "overview" && !parts[2]) tab = "report";
      if (!DETAIL_TABS.includes(tab)) tab = "report";
      return {
        raw: r,
        module: "analyze",
        view: "detail",
        projectId: parts[1],
        tab,
      };
    }

    return { raw: DEFAULT_ROUTE, module: "analyze", view: "input" };
  }

  function routeForDetail(projectId, tab = "report") {
    const t = DETAIL_TABS.includes(tab) ? tab : "report";
    return `analyze/${projectId}/${t}`;
  }

  function hydrateContextFromRoute(route) {
    const parts = normalizeRoute(route).split("/");
    if (
      parts[0] === "analyze"
      && parts[1]
      && !["input", "library", "detail"].includes(parts[1])
    ) {
      activeProjectId = parts[1];
    }
  }

  function emitRoute() {
    buildSidebar();
    handlers.forEach((fn) => {
      try {
        fn(parseRoute(activeRoute));
      } catch (e) {
        console.error(e);
      }
    });
  }

  function persistRoute(route) {
    try {
      sessionStorage.setItem("app:last-route", normalizeRoute(route));
    } catch (_) {
      /* ignore */
    }
  }

  function buildSidebar() {
    const root = document.getElementById("sidebarNav");
    if (!root) return;

    const parsed = parseRoute(activeRoute);

    const groupsHtml = NAV_GROUPS.map((group) => {
      const items = group.items
        .map((item) => {
          let isActive = false;
          if (item.route === "analyze/library") {
            // 在视频详情时也高亮「视频库」（同一条主线）
            isActive =
              parsed.view === "library" || parsed.view === "detail";
          } else {
            isActive = item.route === activeRoute || (
              parsed.view === "input" && item.route === "analyze/input"
            );
          }
          return `
          <button type="button" class="nav-item${isActive ? " active" : ""}"
            data-route="${item.route}">
            <span class="nav-item-icon">${item.icon}</span>
            <span class="nav-item-label">${item.label}</span>
          </button>`;
        })
        .join("");
      return `
        <div class="nav-group" data-nav-group="${group.id}">
          <div class="nav-group-label">${group.label}</div>
          ${items}
        </div>`;
    }).join("");

    // 若正在看某条视频，侧栏底部给一个「当前位置」提示（不可点进子页签）
    let ctxHtml = "";
    if (activeProjectId && parsed.view === "detail") {
      const short =
        (projectTitle || activeProjectId).slice(0, 16) +
        ((projectTitle || "").length > 16 ? "…" : "");
      ctxHtml = `
        <div class="nav-group nav-context">
          <div class="nav-group-label">正在查看</div>
          <div class="nav-context-card" title="${escapeAttr(projectTitle || activeProjectId)}">
            <span class="nav-context-title">${escapeHtml(short)}</span>
            <button type="button" class="nav-context-back" data-route="analyze/library">← 返回视频库</button>
          </div>
        </div>`;
    }

    root.innerHTML = groupsHtml + ctxHtml;

    root.querySelectorAll("[data-route]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const route = btn.dataset.route;
        if (route) navigate(route);
      });
    });
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function escapeAttr(str) {
    return escapeHtml(str).replaceAll("'", "&#39;");
  }

  function syncHash(route, replace = false) {
    const hash = `#/${normalizeRoute(route)}`;
    if (replace) history.replaceState({ route: normalizeRoute(route) }, "", hash);
    else history.pushState({ route: normalizeRoute(route) }, "", hash);
  }

  function navigate(route, { replace = false } = {}) {
    const normalized = normalizeRoute(route);
    const parsed = parseRoute(normalized);

    if (parsed.module === "analyze" && parsed.view === "detail") {
      if (!parsed.projectId && !activeProjectId) {
        navigate("analyze/library", { replace });
        return;
      }
      if (parsed.projectId) activeProjectId = parsed.projectId;
      activeRoute = routeForDetail(activeProjectId, parsed.tab || "report");
    } else {
      activeRoute = normalized;
    }

    syncHash(activeRoute, replace);
    persistRoute(activeRoute);
    emitRoute();
  }

  function setProjectContext(projectId, title = "") {
    activeProjectId = projectId || null;
    projectTitle = title || "";
    buildSidebar();
  }

  function getProjectId() {
    return activeProjectId;
  }

  function getActiveRoute() {
    return activeRoute;
  }

  function onRouteChange(handler) {
    handlers.add(handler);
    return () => handlers.delete(handler);
  }

  function init() {
    const rawHash = (location.hash || "").trim();
    let fromHash;

    if (rawHash.length > 2) {
      fromHash = normalizeRoute(rawHash);
    } else {
      let saved = null;
      try {
        saved = sessionStorage.getItem("app:last-route");
      } catch (_) {}
      fromHash = saved ? normalizeRoute(saved) : DEFAULT_ROUTE;
      syncHash(fromHash, true);
    }

    hydrateContextFromRoute(fromHash);
    activeRoute = fromHash;
    persistRoute(activeRoute);
    emitRoute();

    window.addEventListener("popstate", () => {
      activeRoute = normalizeRoute(location.hash);
      hydrateContextFromRoute(activeRoute);
      persistRoute(activeRoute);
      emitRoute();
    });

    window.addEventListener("hashchange", () => {
      if (normalizeRoute(location.hash) === activeRoute) return;
      activeRoute = normalizeRoute(location.hash);
      hydrateContextFromRoute(activeRoute);
      persistRoute(activeRoute);
      emitRoute();
    });
  }

  global.AppNav = {
    NAV_GROUPS,
    DETAIL_TABS,
    DEFAULT_ROUTE,
    parseRoute,
    routeForDetail,
    navigate,
    setProjectContext,
    getProjectId,
    getActiveRoute,
    onRouteChange,
    init,
    buildSidebar,
  };
})(window);
