/**
 * 起号 Web 壳层导航 · 各模块复用
 * 路由格式：#/analyze/... | #/produce | #/produce/:id/info | #/produce/:id/shot/:n
 */
(function (global) {
  const DEFAULT_ROUTE = "analyze/input";

  const NAV_GROUPS = [
    {
      id: "analyze",
      label: "拆解",
      items: [
        { route: "analyze/input", label: "粘贴拆解", icon: "✦" },
        { route: "analyze/library", label: "视频库", icon: "📂" },
      ],
    },
    {
      id: "project",
      label: "当前视频",
      labelId: "navProjectLabel",
      hiddenUntilProject: true,
      items: [
        { route: "analyze/detail/overview", label: "概览", icon: "📊", needsProject: true },
        { route: "analyze/detail/chapters", label: "章节结构", icon: "📑", needsProject: true },
        { route: "analyze/detail/segments", label: "口播分段", icon: "🎙", needsProject: true },
        { route: "analyze/detail/scenes", label: "关键帧", icon: "🖼", needsProject: true },
      ],
    },
    {
      id: "produce",
      label: "策划",
      items: [
        { route: "produce", label: "制作策划", icon: "📝" },
      ],
    },
    {
      id: "settings",
      label: "系统",
      items: [
        { route: "settings", label: "配音设置", icon: "🎙" },
      ],
    },
  ];

  let activeRoute = "";
  let activeProjectId = null;
  let activePlanId = null;
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

    if (parts[0] === "settings") {
      return { raw: r, module: "settings", view: "tts" };
    }

    if (parts[0] === "produce") {
      const planId = parts[1] || null;
      if (!planId) {
        return { raw: r, module: "produce", view: "list" };
      }
      if (parts[2] === "shot" && parts[3]) {
        return {
          raw: r,
          module: "produce",
          planId,
          view: "shot",
          shotIndex: Number(parts[3]) || 1,
        };
      }
      return { raw: r, module: "produce", planId, view: "info" };
    }

    if (parts[0] === "analyze") {
      if (parts[1] === "input") {
        return { raw: r, module: "analyze", view: "input" };
      }
      if (parts[1] === "library") {
        return { raw: r, module: "analyze", view: "library" };
      }
      if (parts[1] === "detail") {
        const tab = parts[2] || "overview";
        return {
          raw: r,
          module: "analyze",
          view: "detail",
          tab,
          projectId: activeProjectId,
        };
      }
      // #/analyze/:projectId/:tab
      if (parts.length >= 2 && parts[1] !== "input" && parts[1] !== "library" && parts[1] !== "detail") {
        return {
          raw: r,
          module: "analyze",
          view: "detail",
          projectId: parts[1],
          tab: parts[2] || "overview",
        };
      }
    }

    return { raw: DEFAULT_ROUTE, module: "analyze", view: "input" };
  }

  function routeForPlan(planId, view = "info", shotIndex = null) {
    if (view === "shot" && shotIndex) {
      return `produce/${planId}/shot/${shotIndex}`;
    }
    return `produce/${planId}/info`;
  }

  function isProduceItemActive(item) {
    return item.route === "produce" && activeRoute.startsWith("produce");
  }

  function routeForDetail(projectId, tab = "overview") {
    return `analyze/${projectId}/${tab}`;
  }

  function hydrateContextFromRoute(route) {
    const parts = normalizeRoute(route).split("/");
    if (parts[0] === "produce" && parts[1]) {
      activePlanId = parts[1];
    }
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
    handlers.forEach(fn => {
      try { fn(parseRoute(activeRoute)); } catch (e) { console.error(e); }
    });
  }

  function persistRoute(route) {
    try {
      sessionStorage.setItem("app:last-route", normalizeRoute(route));
    } catch (_) {
      /* ignore quota / private mode */
    }
  }

  function buildSidebar() {
    const root = document.getElementById("sidebarNav");
    if (!root) return;

    const groupsHtml = NAV_GROUPS.map(group => {
      const hidden = group.hiddenUntilProject && !activeProjectId ? " hidden" : "";
      const labelText = group.dynamicLabel && projectTitle
        ? projectTitle.slice(0, 18) + (projectTitle.length > 18 ? "…" : "")
        : group.label;
      const labelId = group.labelId ? ` id="${group.labelId}"` : "";
      const items = group.items.map(item => {
        const disabled = item.needsProject && !activeProjectId ? " disabled" : "";
        let isActive = false;
        if (item.route === activeRoute) {
          isActive = true;
        } else if (item.needsProject && activeRoute.startsWith("analyze/") && !activeRoute.startsWith("analyze/input") && !activeRoute.startsWith("analyze/library")) {
          const parsed = parseRoute(activeRoute);
          const itemTab = item.route.split("/").pop();
          isActive = parsed.view === "detail" && parsed.tab === itemTab;
        } else if (item.route === "produce" && activeRoute.startsWith("produce")) {
          isActive = true;
        } else if (item.route === "settings" && activeRoute.startsWith("settings")) {
          isActive = true;
        }
        return `
          <button type="button" class="nav-item${isActive ? " active" : ""}${disabled}"
            data-route="${item.route}"${disabled ? ' aria-disabled="true"' : ""}>
            <span class="nav-item-icon">${item.icon}</span>
            <span class="nav-item-label">${item.label}</span>
          </button>`;
      }).join("");
      return `
        <div class="nav-group${hidden}" data-nav-group="${group.id}">
          <div class="nav-group-label"${labelId}>${labelText}</div>
          ${items}
        </div>`;
    }).join("");

    root.innerHTML = groupsHtml;

    root.querySelectorAll(".nav-item:not([disabled])").forEach(btn => {
      btn.addEventListener("click", () => {
        const route = btn.dataset.route;
        if (!route) return;
        if (route.startsWith("analyze/detail/") && activeProjectId) {
          const tab = route.split("/").pop();
          navigate(routeForDetail(activeProjectId, tab));
          return;
        }
        navigate(route);
      });
    });
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
      activeRoute = routeForDetail(activeProjectId, parsed.tab || "overview");
    } else if (parsed.module === "produce") {
      if (parsed.planId) activePlanId = parsed.planId;
      if (parsed.view === "shot" && parsed.shotIndex && parsed.planId) {
        activeRoute = routeForPlan(parsed.planId, "shot", parsed.shotIndex);
      } else if (parsed.planId) {
        activeRoute = parsed.view === "list" ? "produce" : routeForPlan(parsed.planId, "info");
      } else {
        activeRoute = "produce";
      }
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

  function setPlanContext(planId) {
    activePlanId = planId || null;
  }

  function getPlanId() {
    return activePlanId;
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
      // 刷新时优先用地址栏 hash，保持当前页
      fromHash = normalizeRoute(rawHash);
    } else {
      // 无 hash 时尝试恢复上次停留的页面
      let saved = null;
      try { saved = sessionStorage.getItem("app:last-route"); } catch (_) {}
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
    DEFAULT_ROUTE,
    parseRoute,
    routeForDetail,
    routeForPlan,
    navigate,
    setProjectContext,
    setPlanContext,
    getPlanId,
    getProjectId,
    getActiveRoute,
    onRouteChange,
    init,
    buildSidebar,
  };
})(window);
