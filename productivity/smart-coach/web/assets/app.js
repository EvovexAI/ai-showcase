import { renderAreaChart, renderRadarChart, setProgressRing } from "./charts.js";

const TREND_KEY = "smart-coach-trend-v1";
let state = null;

async function fetchJson(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || res.statusText || "request failed");
  }
  return data;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatSize(n) {
  n = Number(n) || 0;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return iso;
  }
}

function masteryMeta(level) {
  if (level === "mastered") return { text: "已掌握", cls: "done", score: 92 };
  if (level === "practicing") return { text: "练习中", cls: "almost", score: 58 };
  return { text: "未学", cls: "todo", score: 18 };
}

function setStatus(msg, isError) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.toggle("err", !!isError);
}

function showView(name) {
  document.querySelectorAll(".page-stack").forEach((el) => {
    el.classList.toggle("hidden", el.id !== `view-${name}`);
  });
  document.querySelectorAll(".sidebar nav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });
}

function openPhrase(text) {
  document.getElementById("coachCopy").textContent = text;
  document.getElementById("coachDialog").showModal();
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    setStatus("话术已复制，去 EvoFlow 粘贴发给陪练师。");
    return true;
  } catch {
    setStatus("请手动复制对话框里的话术。", true);
    return false;
  }
}

function clamp(n, lo = 0, hi = 100) {
  return Math.max(lo, Math.min(hi, Number(n) || 0));
}

/** Derive juice-style dimension scores from real coach state. */
function deriveDims(data) {
  const mats = (data.materials || []).length;
  const sessions = (data.sessions || []).length;
  const nodes = (data.outline && data.outline.nodes) || [];
  const mastery = (data.progress && data.progress.mastery) || {};
  const pct = clamp(data.percent);
  const weak = (data.weak_points || []).length;

  let mastered = 0;
  let practicing = 0;
  nodes.forEach((n, i) => {
    const id = String(n.id || `n${i + 1}`);
    const lv = mastery[id] || "unseen";
    if (lv === "mastered") mastered += 1;
    else if (lv === "practicing") practicing += 1;
  });

  const materials = clamp(mats === 0 ? 8 : 28 + Math.min(mats, 8) * 9);
  const outline = nodes.length
    ? clamp(35 + Math.min(nodes.length, 12) * 4 + mastered * 3)
    : 12;
  const practice = clamp(sessions === 0 ? 10 : 22 + Math.min(sessions, 10) * 7);
  const masteryScore = nodes.length
    ? clamp(pct)
    : clamp(sessions * 6);
  const closure = clamp(
    20 + (data.next_focus ? 18 : 0) + sessions * 5 + Math.max(0, 24 - weak * 8)
  );

  return {
    materials,
    outline,
    practice,
    mastery: masteryScore,
    closure,
    overall: Math.round(
      materials * 0.18 +
        outline * 0.22 +
        practice * 0.2 +
        masteryScore * 0.28 +
        closure * 0.12
    ),
    mastered,
    practicing,
    nodeCount: nodes.length,
  };
}

function pushTrend(pct) {
  let hist = [];
  try {
    hist = JSON.parse(localStorage.getItem(TREND_KEY) || "[]");
  } catch {
    hist = [];
  }
  if (!Array.isArray(hist)) hist = [];
  const last = hist[hist.length - 1];
  const value = clamp(pct);
  if (!last || last.value !== value) {
    hist.push({
      label: `第${hist.length + 1}次`,
      value,
      at: Date.now(),
    });
  }
  if (hist.length > 8) hist = hist.slice(-8);
  hist = hist.map((p, i) => ({
    ...p,
    label: i === hist.length - 1 ? "最近" : `第${i + 1}次`,
  }));
  try {
    localStorage.setItem(TREND_KEY, JSON.stringify(hist));
  } catch {
    /* ignore quota */
  }
  return hist;
}

function renderTags(el, items, emptyText) {
  if (!el) return;
  if (!items.length) {
    el.innerHTML = `<span>${escapeHtml(emptyText)}</span>`;
    return;
  }
  el.innerHTML = items.map((t) => `<span>${escapeHtml(t)}</span>`).join("");
}

function renderNodes(container, nodes, mastery, limit) {
  const list = limit ? nodes.slice(0, limit) : nodes;
  if (!list.length) {
    container.innerHTML = `<p class="empty-hint">大纲还是空的。上传资料后，让陪练师梳一份大纲。</p>`;
    return;
  }
  container.innerHTML = list
    .map((node, i) => {
      const id = String(node.id || `n${i + 1}`);
      const m = masteryMeta(mastery[id] || "unseen");
      return `<div class="knowledge-row">
        <span class="${m.cls}"></span>
        <div>
          <b>${escapeHtml(node.title || id)}<em>${escapeHtml(m.text)}</em></b>
          <p>${escapeHtml(node.goal || node.practice_hint || "")}</p>
        </div>
        <small>#${i + 1}</small>
      </div>`;
    })
    .join("");
}

function renderDashboardExtras(data, dims) {
  const bars = [
    { label: "资料完备", value: dims.materials },
    { label: "大纲清晰", value: dims.outline },
    { label: "陪练活跃", value: dims.practice },
    { label: "掌握深度", value: dims.mastery },
  ];
  document.getElementById("growthIndex").textContent = String(dims.overall);
  const deltaEl = document.getElementById("growthDelta");
  const hist = pushTrend(data.percent);
  const prev = hist.length >= 2 ? hist[hist.length - 2].value : 0;
  const delta = Math.round(clamp(data.percent) - prev);
  if (hist.length < 2) {
    deltaEl.textContent = "刷新几次后会出现周期对比";
  } else if (delta > 0) {
    deltaEl.textContent = `较上次观察 +${delta}`;
  } else if (delta < 0) {
    deltaEl.textContent = `较上次观察 ${delta}`;
  } else {
    deltaEl.textContent = "与上次观察持平";
  }

  document.getElementById("archiveBars").innerHTML = bars
    .map(
      (b) => `<p>
        <span>${escapeHtml(b.label)}</span>
        <i><b style="width:${clamp(b.value)}%"></b></i>
        <em>${Math.round(b.value)}</em>
      </p>`
    )
    .join("");

  const trendHost = document.getElementById("trendChart");
  renderAreaChart(trendHost, hist);
  const badge = document.getElementById("trendBadge");
  if (hist.length >= 2 && hist[hist.length - 1].value > hist[0].value) {
    badge.textContent = "持续提升";
    badge.className = "badge badge-green";
  } else if (clamp(data.percent) > 0 || (data.sessions || []).length) {
    badge.textContent = "进行中";
    badge.className = "badge badge-blue";
  } else {
    badge.textContent = "待启动";
    badge.className = "badge badge-gray";
  }

  const mats = (data.materials || []).length;
  const sessions = (data.sessions || []).length;
  const focus = data.next_focus || "上传资料后梳大纲";
  const weak = data.weak_points || [];
  document.getElementById("insightCards").innerHTML = `
    <article class="card insight-card green hover-lift">
      <div class="insight-ico">★</div>
      <h3>本周期亮点</h3>
      <p>${
        mats || sessions || dims.nodeCount
          ? `已沉淀 ${mats} 份资料、${sessions} 次陪练、${dims.nodeCount} 个大纲节点；掌握 ${dims.mastered} 个，练习中 ${dims.practicing} 个。`
          : "还没有证据。上传第一份资料后，这里会出现可追踪的成长亮点。"
      }</p>
    </article>
    <article class="card insight-card orange hover-lift">
      <div class="insight-ico">◎</div>
      <h3>关键知识缺口</h3>
      <p>${
        weak.length
          ? escapeHtml(weak.slice(0, 2).join("；"))
          : escapeHtml(`下一步焦点：${focus}`)
      }</p>
    </article>
    <article class="card insight-card purple hover-lift">
      <div class="insight-ico">✦</div>
      <h3>行动建议</h3>
      <p>${
        !mats
          ? "先上传讲义 / 笔记，再让陪练师梳大纲。"
          : !dims.nodeCount
            ? "资料已在：复制「梳学习大纲」话术发给陪练师。"
            : sessions
              ? `围绕「${escapeHtml(focus)}」再开一轮短问答，巩固练习中的节点。`
              : `大纲已就绪。以「${escapeHtml(focus)}」为焦点，开始第一次陪练。`
      }</p>
    </article>`;
}

function renderProfile(data, dims) {
  const course = data.course_title || "智能陪练";
  const mats = (data.materials || []).length;
  const sessions = (data.sessions || []).length;
  const nodes = (data.outline && data.outline.nodes) || [];
  const mastery = (data.progress && data.progress.mastery) || {};
  const weak = data.weak_points || [];

  document.getElementById("profileName").textContent =
    course && course !== "未命名课程" ? course : "学员 · 智能陪练";
  document.getElementById("profileMeta").textContent =
    `资料 ${mats} · 大纲节点 ${nodes.length} · 陪练 ${sessions} · 证据随本地进度同步`;
  document.getElementById("profileOverall").textContent = String(dims.overall);

  const hist = (() => {
    try {
      return JSON.parse(localStorage.getItem(TREND_KEY) || "[]");
    } catch {
      return [];
    }
  })();
  const prev = hist.length >= 2 ? hist[hist.length - 2].value : null;
  const trendEl = document.getElementById("profileTrend");
  if (prev == null) {
    trendEl.textContent = "本周期待形成对比";
  } else {
    const d = Math.round(clamp(data.percent) - prev);
    trendEl.textContent = d >= 0 ? `本周期 +${d}` : `本周期 ${d}`;
  }

  const tags = [];
  if (mats) tags.push("有资料");
  if (nodes.length) tags.push("大纲已梳");
  if (sessions) tags.push("陪练进行中");
  if (dims.mastered) tags.push(`已掌握 ${dims.mastered}`);
  if (data.next_focus) tags.push("有焦点");
  if (!tags.length) tags.push("待启动");
  renderTags(document.getElementById("profileTags"), tags, "待启动");

  const strengths = [];
  if (mats >= 2) strengths.push("资料积累稳定");
  if (dims.outline >= 50) strengths.push("大纲结构清晰");
  if (dims.practice >= 40) strengths.push("陪练节奏在线");
  if (dims.mastered) strengths.push(`已掌握 ${dims.mastered} 个节点`);
  if (!strengths.length) strengths.push("起步阶段 · 先攒证据");

  const gaps = weak.length
    ? weak.slice(0, 4)
    : data.next_focus
      ? [data.next_focus]
      : ["尚无薄弱点标记"];

  const nexts = [];
  if (!mats) nexts.push("上传第一份资料");
  else if (!nodes.length) nexts.push("让陪练师梳大纲");
  else if (!sessions) nexts.push("完成首次短问答");
  else nexts.push(`围绕：${data.next_focus || "当前焦点"}`);
  nexts.push("答疑闭环");

  renderTags(document.getElementById("traitStrengths"), strengths, "—");
  renderTags(document.getElementById("traitGaps"), gaps, "—");
  renderTags(document.getElementById("traitNext"), nexts, "—");

  let radarAxes;
  if (nodes.length >= 3) {
    radarAxes = nodes.slice(0, 6).map((n, i) => {
      const id = String(n.id || `n${i + 1}`);
      const m = masteryMeta(mastery[id] || "unseen");
      return {
        axis: String(n.title || id).slice(0, 6),
        value: m.score,
        baseline: 40,
      };
    });
  } else {
    radarAxes = [
      { axis: "资料", value: dims.materials, baseline: 40 },
      { axis: "大纲", value: dims.outline, baseline: 40 },
      { axis: "陪练", value: dims.practice, baseline: 40 },
      { axis: "掌握", value: dims.mastery, baseline: 40 },
      { axis: "答疑", value: dims.closure, baseline: 40 },
    ];
  }
  renderRadarChart(document.getElementById("radarChart"), radarAxes);
  renderNodes(document.getElementById("profileTrack"), nodes, mastery, 8);

  const pace = clamp(dims.overall);
  setProgressRing(document.getElementById("paceRing"), pace);
  const paceBadge = document.getElementById("paceBadge");
  const paceTitle = document.getElementById("paceTitle");
  const paceNote = document.getElementById("paceNote");
  if (pace >= 70) {
    paceBadge.textContent = "节奏稳健";
    paceTitle.textContent = "投入与反馈形成闭环";
    paceNote.textContent = "保持短问答频率即可；薄弱点优先练，不必拉长单次时长。";
  } else if (pace >= 35) {
    paceBadge.textContent = "升温中";
    paceTitle.textContent = "画像正在成型";
    paceNote.textContent = "建议每周至少完成一轮「梳大纲 / 陪练 / 查进度」，让趋势图有可对比的点。";
  } else {
    paceBadge.textContent = "待观察";
    paceTitle.textContent = "节奏尚未成型";
    paceNote.textContent =
      "上传资料并完成一次梳大纲、一次短问答后，这里会给出更稳的节奏建议。";
  }
}

function render(data) {
  state = data;
  const pct = Number(data.percent) || 0;
  const mats = data.materials || [];
  const sessions = data.sessions || [];
  const outline = data.outline || {};
  const progress = data.progress || {};
  const mastery = progress.mastery || {};
  const nodes = outline.nodes || [];
  const course = data.course_title || "智能陪练";
  const dims = deriveDims(data);

  document.getElementById("greeting").textContent =
    course && course !== "未命名课程"
      ? `继续学习「${course}」。当前完成 ${pct}%。`
      : `你好，学员。今天有 ${mats.length ? "资料可练" : "资料待上传"}。`;
  document.getElementById("percentLabel").textContent = String(pct);
  document.getElementById("progressBar").style.width = `${pct}%`;
  document.getElementById("nextFocus").textContent = data.next_focus || "上传资料后梳大纲";
  document.getElementById("practiceFocus").textContent =
    data.next_focus || "先上传资料，再让陪练师梳大纲";
  document.getElementById("chapterLine").textContent = data.current_chapter
    ? `当前章节：${data.current_chapter}`
    : "当前章节待定";
  document.getElementById("coachHint").textContent = data.coach_hint || "";
  document.getElementById("statMats").textContent = String(mats.length);
  document.getElementById("statSessions").textContent = String(sessions.length);
  document.getElementById("navMatBadge").textContent = String(mats.length);
  document.getElementById("navSessionBadge").textContent = String(sessions.length);
  document.getElementById("matCount").textContent = String(mats.length);
  document.getElementById("lastSessionLine").textContent = data.last_session_at
    ? `最近：${formatTime(data.last_session_at)}`
    : "尚无陪练记录";
  document.getElementById("percentHint").textContent = nodes.length
    ? `共 ${nodes.length} 个大纲节点`
    : "按大纲节点掌握度估算";

  const weak = data.weak_points || [];
  const weakBox = document.getElementById("weakList");
  if (!weak.length && !data.next_focus) {
    weakBox.innerHTML = `<div class="alert-row green"><span>✓</span><div><b>暂无告警</b><p>上传资料并完成一次梳大纲后，这里会出现薄弱点。</p></div></div>`;
  } else {
    const rows = [];
    if (data.next_focus) {
      rows.push(
        `<div class="alert-row purple"><span>✦</span><div><b>下一步焦点</b><p>${escapeHtml(data.next_focus)}</p></div><span class="badge badge-purple">陪练</span></div>`
      );
    }
    weak.forEach((w) => {
      rows.push(
        `<div class="alert-row orange"><span>!</span><div><b>薄弱点</b><p>${escapeHtml(w)}</p></div><span class="badge badge-orange">关注</span></div>`
      );
    });
    if (!weak.length && data.next_focus) {
      rows.push(
        `<div class="alert-row green"><span>✓</span><div><b>状态良好</b><p>还没有薄弱点标记，继续按焦点练习即可。</p></div></div>`
      );
    }
    weakBox.innerHTML = rows.join("");
  }

  const timeline = document.getElementById("recentTimeline");
  if (!sessions.length) {
    timeline.innerHTML = `<p class="empty-hint">还没有会话。点右下角或「请陪练师继续」去开练。</p>`;
  } else {
    timeline.innerHTML = sessions
      .slice(0, 4)
      .map(
        (s) => `<div class="timeline-row">
          <div class="timeline-dot"></div>
          <div>
            <b>${escapeHtml(s.name)}</b>
            <p>${escapeHtml(s.summary || "陪练会话")}</p>
          </div>
        </div>`
      )
      .join("");
  }

  document.getElementById("outlineCourse").textContent =
    outline.course_title || course || "课程节点";
  document.getElementById("outlineMeta").textContent = outline.updated_at
    ? `更新于 ${formatTime(outline.updated_at)}`
    : "等待陪练师写入大纲";
  renderNodes(document.getElementById("outlinePreview"), nodes, mastery, 5);
  renderNodes(document.getElementById("outlineTree"), nodes, mastery);

  const matBox = document.getElementById("materials");
  if (!mats.length) {
    matBox.innerHTML = `<p class="empty-hint">还没有资料。点右上角「上传资料」开始。</p>`;
  } else {
    matBox.innerHTML = mats
      .map(
        (m) => `<div class="file-row">
          <div>
            <div class="name">${escapeHtml(m.name)}</div>
            <div class="meta">${escapeHtml(m.path || "")}</div>
          </div>
          <div class="meta">${formatSize(m.size)}</div>
        </div>`
      )
      .join("");
  }

  const sessBox = document.getElementById("sessions");
  if (!sessions.length) {
    sessBox.innerHTML = `<p class="empty-hint">暂无记录。陪练结束后会出现在这里。</p>`;
  } else {
    sessBox.innerHTML = sessions
      .map(
        (s) => `<div class="timeline-row">
          <div class="timeline-dot"></div>
          <div>
            <b>${escapeHtml(s.name)}</b>
            <p>${escapeHtml(s.summary || "")}</p>
            <small>${escapeHtml(s.path || "")}</small>
          </div>
        </div>`
      )
      .join("");
  }

  renderDashboardExtras(data, dims);
  renderProfile(data, dims);
}

async function refresh() {
  const data = await fetchJson("/api/overview");
  render(data);
}

document.querySelectorAll(".sidebar nav button").forEach((btn) => {
  btn.addEventListener("click", () => showView(btn.dataset.view));
});

document.querySelectorAll("[data-goto]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const view = btn.dataset.goto;
    if (view) showView(view);
  });
});

document.getElementById("sidebarToggle").addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("collapsed");
  document.getElementById("main").classList.toggle("expanded");
});

function wirePhrase(el) {
  if (!el) return;
  el.addEventListener("click", () => {
    const phrase = el.dataset.phrase || "让陪练师继续陪练";
    openPhrase(phrase);
  });
}

["btnCoach", "btnCoachTop", "btnCoachHero", "fabCoach"].forEach((id) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("click", () => openPhrase("让陪练师继续陪练"));
});

document.querySelectorAll("[data-phrase]").forEach(wirePhrase);

document.getElementById("btnCopy").addEventListener("click", async (e) => {
  e.preventDefault();
  await copyText(document.getElementById("coachCopy").textContent);
  document.getElementById("coachDialog").close();
});

document.getElementById("btnRefresh").addEventListener("click", () => {
  refresh()
    .then(() => setStatus("已刷新进度"))
    .catch((err) => setStatus(String(err.message || err), true));
});

document.getElementById("fileInput").addEventListener("change", async (e) => {
  const file = e.target.files && e.target.files[0];
  e.target.value = "";
  if (!file) return;
  setStatus("上传中…");
  showView("materials");
  try {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/materials", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok || data.ok === false) throw new Error(data.error || "upload failed");
    setStatus(`已上传 ${data.material.name}。可以说：让陪练师按资料梳大纲。`);
    await refresh();
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
});

document.getElementById("btnSync").addEventListener("click", async () => {
  try {
    const data = await fetchJson("/api/sync-kb", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    setStatus(data.message || "已提示同步步骤");
    showView("overview");
  } catch (err) {
    setStatus(String(err.message || err), true);
  }
});

document.getElementById("searchInput").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim().toLowerCase();
  if (!q || !state) return;
  const hitMat = (state.materials || []).find((m) => m.name.toLowerCase().includes(q));
  const hitNode = ((state.outline && state.outline.nodes) || []).find((n) =>
    String(n.title || "").toLowerCase().includes(q)
  );
  if (hitMat) {
    showView("materials");
    setStatus(`找到资料：${hitMat.name}`);
  } else if (hitNode) {
    showView("outline");
    setStatus(`找到大纲节点：${hitNode.title}`);
  } else {
    openPhrase(`结合我当前进度，解释一下：${e.target.value.trim()}`);
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "/" && e.target.tagName !== "INPUT" && e.target.tagName !== "TEXTAREA") {
    e.preventDefault();
    document.getElementById("searchInput").focus();
  }
});

refresh().catch((err) => setStatus(String(err.message || err), true));
