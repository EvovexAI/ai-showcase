const $ = (s) => document.querySelector(s);

let scenarios = [];
let cfg = {};
let activeId = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.error || data.detail || data.message || `HTTP ${res.status}`;
    const err = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    err.data = data;
    throw err;
  }
  return data;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function wantLive() {
  // Config already decided; user never toggles dry-run in the UI
  return cfg.dry_run === false;
}

function route() {
  const hash = (location.hash || "#/").replace(/^#/, "") || "/";
  const path = hash.startsWith("/") ? hash : `/${hash}`;
  if (path === "/" || path === "") return { name: "home" };
  if (path === "/setup") return { name: "setup" };
  const m = path.match(/^\/(s[1-4])$/i);
  if (m) return { name: "scenario", id: m[1].toLowerCase() };
  return { name: "home" };
}

function showView(name) {
  $("#view-home").classList.toggle("hidden", name !== "home");
  $("#view-scenario").classList.toggle("hidden", name !== "scenario");
  $("#view-setup").classList.toggle("hidden", name !== "setup");
}

function updateNav(r) {
  document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));
  if (r.name === "home") {
    $('[data-nav="home"]').classList.add("active");
    $(".nav-scene").textContent = "当前场景";
    $(".nav-scene").setAttribute("href", "#/");
  } else if (r.name === "setup") {
    $('[data-nav="setup"]').classList.add("active");
  } else if (r.name === "scenario") {
    $(".nav-scene").classList.add("active");
    $(".nav-scene").textContent = `当前 · ${r.id.toUpperCase()}`;
    $(".nav-scene").setAttribute("href", `#/${r.id}`);
  }
}

function renderCatalog() {
  $("#catalog").innerHTML = scenarios
    .map((s) => {
      const id = String(s.id || "").toLowerCase();
      return `<a class="catalog-card" href="#/${id}">
        <div class="tag">${escapeHtml(s.industry || "")} · ${escapeHtml(id.toUpperCase())}</div>
        <h2>${escapeHtml(s.title || id)}</h2>
        <p>${escapeHtml(s.story || s.when_to_use || "")}</p>
      </a>`;
    })
    .join("");
}

function renderScenario(id) {
  const s = scenarios.find((x) => String(x.id).toLowerCase() === id);
  activeId = s ? id : null;
  if (!s) {
    $("#scTitle").textContent = "未找到场景";
    $("#scStory").textContent = "";
    $("#scSteps").innerHTML = "";
    return;
  }

  $("#scIndustry").textContent = `${s.industry || ""} · ${s.persona || ""}`;
  $("#scTitle").textContent = s.title || id;
  $("#scStory").textContent = s.story || "";
  $("#scSteps").innerHTML = (s.steps_human || [])
    .map((t) => `<li>${escapeHtml(t)}</li>`)
    .join("");

  $("#progress").classList.add("hidden");
  $("#resultTitle").textContent = "还没开始";
  $("#resultSummary").textContent = "参数已内置，直接点「开始演示」。";
  $("#resultLog").textContent = "";
  $("#runHint").textContent = wantLive()
    ? "将走真实网关。"
    : "当前是预览模式（未连实网）。先去「准备一下」配好环境。";
  $("#runBtn").disabled = false;
}

function renderSetup() {
  const seed = cfg.seed || {};
  const modeClass = wantLive() ? "badge-ok" : "badge-warn";
  $("#setupStatus").innerHTML = `
    <div class="row"><span class="muted">网关</span><strong>${escapeHtml(cfg.base_url || "—")}</strong></div>
    <div class="row"><span class="muted">状态</span><strong class="${modeClass}">${escapeHtml(cfg.mode_label || "—")}</strong></div>
    <div class="row"><span class="muted">演示员工</span><strong>${escapeHtml(seed.employee_code || cfg.default_employee_code || "待准备")}</strong></div>
    <div class="row"><span class="muted">知识库</span><strong>${escapeHtml(seed.kb_id || cfg.default_kb_id || "待准备")}</strong></div>
    <div class="row"><span class="muted">编排</span><strong>${escapeHtml(seed.app_id || cfg.default_app_id || "待准备")}</strong></div>
  `;
  $("#navMode").textContent = cfg.mode_label || "—";
  $("#navMode").className = "nav-foot " + (wantLive() ? "badge-ok" : "badge-warn");
}

async function refreshConfig() {
  cfg = await api("/api/health");
  renderSetup();
}

function friendlyScenarioResult(job) {
  const result = job.result || {};
  const ok = job.status === "done" && result.ok;
  const dry = result.config?.dry_run || result.note;
  const bits = [];
  if (result.dispatch_id) bits.push(`派工 ${result.dispatch_id}`);
  if (result.run_id) bits.push(`编排 ${result.run_id}`);
  if (result.search_hits != null) bits.push(`知识库命中 ${result.search_hits} 条`);
  if (result.final_status) bits.push(`状态 ${result.final_status}`);
  const title = ok ? (dry && result.config?.dry_run ? "预览成功（未算调通）" : "跑通了") : "没跑通";
  const summary = ok
    ? bits.length
      ? bits.join(" · ")
      : "关键步骤已完成。"
    : result.error || job.message || "请看详细日志，或先去「准备一下」。";
  return { title, summary, ok, raw: job };
}

async function pollJob(jobId) {
  const progress = $("#progress");
  progress.classList.remove("hidden");
  for (;;) {
    const job = await api(`/api/jobs/${jobId}`);
    progress.textContent = job.status === "running" ? "正在跑…" : `${job.status} · ${job.message || ""}`;
    if (job.status === "done" || job.status === "error") {
      const f = friendlyScenarioResult(job);
      $("#resultTitle").textContent = f.title;
      $("#resultTitle").className = "result-title " + (f.ok ? "badge-ok" : "badge-bad");
      $("#resultSummary").textContent = f.summary;
      $("#resultLog").textContent = JSON.stringify(job, null, 2);
      $("#runBtn").disabled = false;
      progress.classList.add("hidden");
      return;
    }
    await new Promise((r) => setTimeout(r, 800));
  }
}

async function startRun() {
  if (!activeId) return;
  $("#runBtn").disabled = true;
  $("#resultTitle").textContent = "提交中…";
  $("#resultSummary").textContent = "稍等。";
  $("#resultLog").textContent = "";
  try {
    // No form fields — server uses seed-state / scenario defaults
    const { job_id } = await api("/api/run", {
      method: "POST",
      body: JSON.stringify({
        scenario: activeId,
        live: wantLive(),
      }),
    });
    await pollJob(job_id);
  } catch (err) {
    $("#resultTitle").textContent = "失败";
    $("#resultTitle").className = "result-title badge-bad";
    $("#resultSummary").textContent = err.message;
    $("#resultLog").textContent = JSON.stringify(err.data || {}, null, 2);
    $("#runBtn").disabled = false;
    $("#progress").classList.add("hidden");
  }
}

async function doSeed() {
  $("#setupTitle").textContent = "准备中…";
  $("#setupSummary").textContent = "在创建演示员工 / 知识库 / 编排。";
  $("#setupLog").textContent = "";
  try {
    const result = await api("/api/seed", {
      method: "POST",
      body: JSON.stringify({ live: true }),
    });
    const ok = !!result.ok;
    $("#setupTitle").textContent = ok ? "环境就绪" : "准备失败";
    $("#setupTitle").className = "result-title " + (ok ? "badge-ok" : "badge-bad");
    const seed = result.seed || {};
    $("#setupSummary").textContent = ok
      ? `员工 ${seed.employee_code || "—"} · 知识库已就绪 · 编排 ${seed.app_id || "—"}`
      : result.error || "请看详细日志";
    $("#setupLog").textContent = JSON.stringify(result, null, 2);
    await refreshConfig();
  } catch (err) {
    $("#setupTitle").textContent = "准备失败";
    $("#setupTitle").className = "result-title badge-bad";
    $("#setupSummary").textContent = err.message;
    $("#setupLog").textContent = JSON.stringify(err.data || {}, null, 2);
  }
}

async function doSmoke() {
  $("#setupTitle").textContent = "验收中…";
  $("#setupSummary").textContent = "正在跑 S1–S4，可能要一两分钟。";
  $("#setupLog").textContent = "";
  try {
    const result = await api("/api/smoke", {
      method: "POST",
      body: JSON.stringify({ live: true, allow_dry_run: false }),
    });
    const accepted = !!result.accepted_as_live;
    $("#setupTitle").textContent = accepted
      ? "验收通过 · 已调通"
      : result.ok && !result.live
        ? "仅预览通过 · 未算调通"
        : "验收未通过";
    $("#setupTitle").className =
      "result-title " + (accepted ? "badge-ok" : result.ok ? "badge-warn" : "badge-bad");
    const fails = (result.rows || []).filter((r) => !r.ok).map((r) => r.check);
    $("#setupSummary").textContent = accepted
      ? "四条业务场景关键断言全绿。"
      : fails.length
        ? `未通过：${fails.join("、")}`
        : result.note || result.error || "请看详细日志";
    $("#setupLog").textContent = JSON.stringify(result, null, 2);
    await refreshConfig();
  } catch (err) {
    $("#setupTitle").textContent = "验收失败";
    $("#setupTitle").className = "result-title badge-bad";
    $("#setupSummary").textContent = err.message;
    $("#setupLog").textContent = JSON.stringify(err.data || {}, null, 2);
  }
}

function applyRoute() {
  const r = route();
  updateNav(r);
  if (r.name === "home") {
    showView("home");
    renderCatalog();
  } else if (r.name === "setup") {
    showView("setup");
    renderSetup();
  } else {
    showView("scenario");
    renderScenario(r.id);
  }
}

async function boot() {
  await refreshConfig();
  const data = await api("/api/scenarios");
  scenarios = data.items || data.scenarios || [];
  applyRoute();
}

$("#runBtn").addEventListener("click", startRun);
$("#seedBtn").addEventListener("click", doSeed);
$("#smokeBtn").addEventListener("click", doSmoke);
window.addEventListener("hashchange", applyRoute);

boot().catch((e) => {
  const el = $("#resultSummary") || $("#setupSummary");
  if (el) el.textContent = `启动失败：${e.message}`;
});
