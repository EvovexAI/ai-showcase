const $ = (sel) => document.querySelector(sel);

const shareText = $("#shareText");
const analyzeBtn = $("#analyzeBtn");
const libraryCount = $("#libraryCount");
const projectList = $("#projectList");
const viewAnalyzeInput = $("#viewAnalyzeInput");
const viewAnalyzeLibrary = $("#viewAnalyzeLibrary");
const viewAnalyzeDetail = $("#viewAnalyzeDetail");
const viewProduce = $("#viewProduce");
const viewSettings = $("#viewSettings");
const detailPanels = {
  overview: $("#detailPanelOverview"),
  chapters: $("#detailPanelChapters"),
  segments: $("#detailPanelSegments"),
  scenes: $("#detailPanelScenes"),
};
const detailTitle = $("#detailTitle");
const detailMeta = $("#detailMeta");
const detailActions = $("#detailActions");
const reanalyzeBtn = $("#reanalyzeBtn");
const reanalyzeFullBtn = $("#reanalyzeFullBtn");
const progress = $("#progress");
const progressFill = $("#progressFill");
const progressText = $("#progressText");
const summary = $("#summary");
const customFrameWrap = $("#customFrameWrap");
const frameCountInput = $("#frameCount");
const detailVideo = $("#detailVideo");
const videoPlayerWrap = $("#videoPlayerWrap");
const visionPanel = $("#visionPanel");
const exportReportBtn = $("#exportReportBtn");
const lightboxSeek = $("#lightboxSeek");

let pollTimer = null;
let activeProjectId = null;
let currentProject = null;
let currentScenes = [];
let lightboxIndex = -1;
let lightboxScene = null;
let chapterModalOpen = false;
let infoModalOpen = false;

function show(el) { el.classList.remove("hidden"); }

function getKeyframeSettings() {
  const mode = document.querySelector('input[name="keyframeMode"]:checked')?.value || "transcript";
  const frameCount = Math.max(5, Math.min(300, Number(frameCountInput?.value) || 30));
  return { keyframe_mode: mode, frame_count: frameCount };
}

function getVisionPrep() {
  return Boolean($("#visionPrep")?.checked);
}

function visionStateLabel(state) {
  const map = {
    none: "未准备",
    manifest_ready: "清单已生成",
    described: "描述待合并",
    merged: "已合并到报告",
  };
  return map[state] || state;
}

function formatVisionSummary(vision) {
  if (!vision) return "";
  const parts = [
    vision.visual_type,
    vision.layout,
    vision.how_made,
    vision.on_screen_text,
  ].filter(Boolean);
  return parts.join(" · ");
}

function sceneStartSeconds(scene) {
  if (!scene) return null;
  if (scene.start != null && !Number.isNaN(Number(scene.start))) {
    return Number(scene.start);
  }
  return parseTimeRangeStart(scene.time_range);
}

function parseTimeRangeStart(timeRange) {
  if (!timeRange) return null;
  const part = String(timeRange).split("-")[0]?.trim();
  if (!part) return null;
  const bits = part.split(":").map(Number);
  if (bits.some(Number.isNaN)) return null;
  if (bits.length === 2) return bits[0] * 60 + bits[1];
  if (bits.length === 3) return bits[0] * 3600 + bits[1] * 60 + bits[2];
  return null;
}

function closeOverlaysForSeek() {
  if (isLightboxOpen()) closeLightbox();
  if (chapterModalOpen) closeChapterModal();
}

function seekToScene(scene) {
  if (!detailVideo || !scene) return;
  const t = sceneStartSeconds(scene);
  if (t == null) return;

  closeOverlaysForSeek();
  show(videoPlayerWrap);
  detailVideo.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const applySeek = () => {
    try {
      detailVideo.currentTime = Math.max(0, t);
    } catch (_) {
      /* ignore seek errors before metadata */
    }
    detailVideo.play().catch(() => {});
  };

  if (detailVideo.readyState >= 1) {
    applySeek();
    return;
  }

  detailVideo.addEventListener("loadedmetadata", applySeek, { once: true });
  if (detailVideo.src) detailVideo.load();
}

function syncKeyframeModeUI() {
  const mode = document.querySelector('input[name="keyframeMode"]:checked')?.value || "transcript";
  if (customFrameWrap) {
    customFrameWrap.classList.toggle("hidden", mode !== "custom");
  }
}

function keyframeModeLabel(mode, count) {
  if (mode === "transcript") return "口播一句一帧";
  if (mode === "custom") return `自定义 ${count || 30} 帧`;
  return "镜头切换";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function setProgress(pct, text) {
  show(progress);
  progressFill.style.width = `${pct}%`;
  progressText.textContent = text;
}

function roleClass(role) {
  const r = (role || "body").replace(/-/g, "_");
  return `role role-${r}`;
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay) return "今天";
  if (d.toDateString() === yesterday.toDateString()) return "昨天";
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function renderProjectList(projects) {
  libraryCount.textContent = projects.length
    ? `共 ${projects.length} 个视频`
    : "暂无视频，粘贴链接开始第一个";

  if (!projects.length) {
    projectList.innerHTML = `
      <div class="library-empty">
        <div class="library-empty-icon">📂</div>
        <p>解析过的视频会出现在这里，方便随时切换查看</p>
      </div>`;
    return;
  }

  projectList.innerHTML = projects.map(p => {
    const active = p.id === activeProjectId ? " active" : "";
    const cover = p.cover_url
      ? `<img src="${p.cover_url}" alt="" loading="lazy" />`
      : `<div class="cover-placeholder">🎬</div>`;
    const statusClass = p.has_report ? "done" : p.analysis_status === "partial" ? "partial" : "pending";
    const statusText = p.has_report
      ? "已拆解"
      : p.analysis_status === "partial"
        ? "拆解中断"
        : "待拆解";
    const status = `<span class="project-badge ${statusClass}">${statusText}</span>`;

    return `
      <div class="project-card${active}" data-id="${escapeHtml(p.id)}">
        <div class="project-cover">${cover}</div>
        <div class="project-body">
          <div class="project-top">
            ${status}
            <span class="project-duration">${escapeHtml(p.duration_label || "-")}</span>
          </div>
          <button type="button" class="project-title-link">${escapeHtml(p.title || p.id)}</button>
          ${p.author ? `<div class="project-author">${escapeHtml(p.author)}</div>` : ""}
          <div class="project-stats">
            <span>${p.chapter_count || 0} 章</span>
            <span>${p.scene_count || 0} 镜头</span>
            <span>${p.script_chars || 0} 字</span>
          </div>
          <div class="project-date">${formatDate(p.updated_at)}</div>
        </div>
      </div>`;
  }).join("");

  projectList.querySelectorAll(".project-card").forEach(card => {
    card.addEventListener("click", () => selectProject(card.dataset.id));
    card.querySelector(".project-title-link")?.addEventListener("click", (e) => {
      e.stopPropagation();
      openInfoModal(card.dataset.id);
    });
  });
}

async function selectProject(id, { force = false, tab = "overview", skipNavigate = false } = {}) {
  if (!id) return;
  if (!force && id === activeProjectId && !skipNavigate) return;
  try {
    activeProjectId = id;
    projectList.querySelectorAll(".project-card").forEach(card => {
      card.classList.toggle("active", card.dataset.id === id);
    });
    await loadProject(id);
    AppNav.setProjectContext(id, currentProject?.title || "");
    showDetailTab(tab);
    if (!skipNavigate) {
      AppNav.navigate(AppNav.routeForDetail(id, tab));
    }
  } catch (err) {
    alert(err.message);
  }
}

function showDetailTab(tab = "overview") {
  Object.entries(detailPanels).forEach(([name, el]) => {
    if (!el) return;
    el.classList.toggle("hidden", name !== tab);
  });
}

function applyRoute(parsed) {
  [viewAnalyzeInput, viewAnalyzeLibrary, viewAnalyzeDetail, viewProduce, viewSettings].forEach(el => {
    el?.classList.add("hidden");
  });

  if (parsed.module === "settings") {
    show(viewSettings);
    loadTtsSettings().catch(console.error);
    return;
  }

  if (parsed.module === "produce") {
    show(viewProduce);
    const planId = parsed.planId || activePlanId;
    loadPlanList(planId).catch(console.error);
    if (planId) {
      const needLoad = !currentPlan || currentPlan.id !== planId;
      const view = parsed.view === "shot" ? "shot" : "info";
      const shotIndex = parsed.shotIndex || 1;
      if (needLoad) {
        loadPlan(planId, { skipNav: true }).then(() => {
          showProducePanel(view, shotIndex);
        }).catch(console.error);
      } else {
        showProducePanel(view, shotIndex);
      }
    } else {
      $("#planEditor")?.classList.add("hidden");
      $("#planEmpty")?.classList.remove("hidden");
    }
    return;
  }

  if (parsed.module !== "analyze") return;

  if (parsed.view === "input") {
    show(viewAnalyzeInput);
    return;
  }

  if (parsed.view === "library") {
    show(viewAnalyzeLibrary);
    loadLibrary().catch(console.error);
    return;
  }

  if (parsed.view === "detail") {
    const tab = parsed.tab || "overview";
    const projectId = parsed.projectId || AppNav.getProjectId() || activeProjectId;
    if (!projectId) {
      AppNav.navigate("analyze/library", { replace: true });
      return;
    }
    const needLoad = !currentProject || currentProject.id !== projectId;
    show(viewAnalyzeDetail);
    if (needLoad) {
      selectProject(projectId, { force: true, tab, skipNavigate: true }).catch(console.error);
    } else {
      activeProjectId = projectId;
      showDetailTab(tab);
    }
  }
}

function renderSummary(data) {
  show(summary);
  summary.innerHTML = `
    <div class="metric metric-wide">
      <div class="label">视频标题</div>
      <div class="value text">${escapeHtml(data.title || "-")}</div>
    </div>
    <div class="metric">
      <div class="label">时长</div>
      <div class="value">${escapeHtml(data.duration_label || "-")}</div>
    </div>
    <div class="metric">
      <div class="label">口播字数</div>
      <div class="value">${data.script?.total_chars || 0}</div>
    </div>
    <div class="metric">
      <div class="label">语速</div>
      <div class="value">${data.voice?.chars_per_minute || "-"}</div>
    </div>
    <div class="metric">
      <div class="label">章节</div>
      <div class="value">${data.chapters?.length || 0}</div>
    </div>
    <div class="metric">
      <div class="label">镜头</div>
      <div class="value">${data.scenes?.length || 0}</div>
    </div>
  `;
}

function renderChapters(chapters) {
  const el = $("#tab-chapters");
  if (!chapters?.length) {
    el.innerHTML = '<p class="empty">暂无章节数据，请使用完整拆解</p>';
    return;
  }
  el.innerHTML = `
    <p class="panel-hint">点击章节查看<strong>画面 + 口播</strong>对照时间轴</p>
    <div class="chapter-list">${chapters.map((ch, i) => `
    <button type="button" class="chapter-card" data-index="${i}">
      <div class="chapter-top">
        <span class="chapter-time">${escapeHtml(ch.time_range || "")}</span>
        <span class="chapter-title">${escapeHtml(ch.title || "章节")}</span>
        <span class="chapter-arrow">→</span>
      </div>
      <div class="chapter-meta">
        <span class="tag" style="background:rgba(52,199,89,0.12);color:#248a3d">${ch.chars || 0} 字</span>
        ${ch.scene_count ? `<span class="tag" style="background:rgba(175,82,222,0.12);color:#8e44ad">${ch.scene_count} 镜头</span>` : ""}
      </div>
      <p class="chapter-summary">${escapeHtml(ch.summary || "")}</p>
    </button>
  `).join("")}</div>`;

  el.querySelectorAll(".chapter-card").forEach(card => {
    card.addEventListener("click", () => openChapterModal(Number(card.dataset.index)));
  });
}

function inRange(item, start, end) {
  return item.end > start && item.start < end;
}

function buildChapterTimeline(chapter, scenes, segments, keyframeMode = "scene") {
  const chapterScenes = scenes
    .filter(s => inRange(s, chapter.start, chapter.end))
    .sort((a, b) => a.start - b.start);

  if (keyframeMode === "transcript" && chapterScenes.length) {
    return chapterScenes.map(scene => ({
      scene,
      speech: scene.text || scene.speech_text
        ? [{
            text: scene.text || scene.speech_text,
            time_range: scene.time_range || "",
            role_guess: "body",
          }]
        : [],
      oneToOne: true,
    }));
  }

  if (chapterScenes.length) {
    return chapterScenes.map(scene => {
      const segStart = Math.max(scene.start, chapter.start);
      const segEnd = Math.min(scene.end, chapter.end);
      const speech = segments
        .filter(s => inRange(s, segStart, segEnd))
        .sort((a, b) => a.start - b.start);
      return { scene, speech };
    });
  }

  const speech = segments
    .filter(s => inRange(s, chapter.start, chapter.end))
    .sort((a, b) => a.start - b.start);
  return [{ scene: null, speech }];
}

function openLightboxForScene(scene) {
  const idx = currentScenes.findIndex(s => s.index === scene.index || s.image_url === scene.image_url);
  if (idx >= 0) openLightbox(idx);
  else openLightboxScene(scene);
}

function openLightboxScene(scene) {
  lightboxScene = scene;
  lightboxIndex = -1;
  const box = $("#lightbox");
  $("#lightboxImg").src = scene.image_url;
  $("#lightboxTitle").textContent = `镜头 ${scene.index} · ${scene.time_range || ""}`;
  $("#lightboxSub").textContent = [
    formatDuration(scene.duration_seconds ?? (scene.end - scene.start)),
    scene.text || scene.speech_text || "",
    "点击左右切换，Esc 关闭",
  ].filter(Boolean).join(" · ");
  const visionEl = $("#lightboxVision");
  const visionText = formatVisionSummary(scene.vision);
  if (visionText) {
    visionEl.textContent = visionText;
    show(visionEl);
  } else {
    visionEl.classList.add("hidden");
    visionEl.textContent = "";
  }
  if (lightboxSeek) {
    lightboxSeek.textContent = scene.start != null
      ? `▶ 跳转原片 ${scene.time_range || formatDuration(scene.start)}`
      : "▶ 跳转原片";
  }
  show(box);
  document.body.classList.add("lightbox-open");
}

function openChapterModal(index) {
  if (!currentProject?.chapters?.[index]) return;
  const chapter = currentProject.chapters[index];
  const keyframeMode = currentProject.keyframe_mode || "scene";
  const pairs = buildChapterTimeline(
    chapter,
    currentProject.scenes || [],
    currentProject.segments || [],
    keyframeMode,
  );
  const unitLabel = keyframeMode === "transcript" ? "句" : "镜头";

  $("#chapterModalHeader").innerHTML = `
    <div class="chapter-modal-top">
      <span class="chapter-time">${escapeHtml(chapter.time_range || "")}</span>
      <span class="${roleClass(chapter.role)}">${escapeHtml(chapter.role || "body")}</span>
    </div>
    <h3 class="chapter-modal-title">${escapeHtml(chapter.title || "章节")}</h3>
    <p class="chapter-modal-summary">${escapeHtml(chapter.summary || "")}</p>
    <div class="chapter-modal-stats">
      <span>${formatDuration(chapter.duration_seconds ?? (chapter.end - chapter.start))}</span>
      <span>${chapter.chars || 0} 字口播</span>
      <span>${chapter.scene_count || pairs.filter(p => p.scene).length} ${unitLabel}</span>
    </div>`;

  $("#chapterModalBody").innerHTML = pairs.map(({ scene, speech, oneToOne }, blockIdx) => `
    <section class="timeline-block${oneToOne ? " timeline-one-to-one" : ""}">
      ${scene ? `
      <div class="timeline-scene">
        <button type="button" class="timeline-scene-thumb" data-block="${blockIdx}">
          <img src="${scene.image_url}" alt="片段 ${scene.index}" loading="lazy" />
          <span class="scene-zoom">🔍</span>
        </button>
        <div class="timeline-scene-meta">
          <div class="timeline-label">${oneToOne ? "画面 + 口播" : `画面 · 片段 ${scene.index}`}</div>
          <div class="timeline-scene-time">${escapeHtml(scene.time_range || "")}${scene.duration_seconds || scene.end != null ? ` · ${formatDuration(scene.duration_seconds ?? scene.end - scene.start)}` : ""}</div>
          ${scene.vision ? `<div class="timeline-scene-vision">${escapeHtml(formatVisionSummary(scene.vision))}</div>` : ""}
          <button type="button" class="timeline-seek-btn" data-block="${blockIdx}">▶ 跳转原片</button>
        </div>
      </div>` : `
      <div class="timeline-scene timeline-scene-empty">
        <div class="timeline-label">画面</div>
        <div class="timeline-scene-type">该时段暂无关键帧</div>
      </div>`}
      <div class="timeline-speech">
        <div class="timeline-label">${oneToOne ? "口播" : `口播 · ${speech.length} 段`}</div>
        ${speech.length ? speech.map(seg => `
          <div class="speech-line">
            <span class="speech-time">${escapeHtml(seg.time_range || "")}</span>
            <span class="${roleClass(seg.role_guess)}">${escapeHtml(seg.role_guess || "body")}</span>
            <p class="speech-text">${escapeHtml(seg.text || "")}</p>
          </div>
        `).join("") : '<p class="speech-empty">该时段无口播</p>'}
      </div>
    </section>
  `).join("");

  const sceneButtons = $("#chapterModalBody").querySelectorAll(".timeline-scene-thumb");
  sceneButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const scene = pairs[Number(btn.dataset.block)].scene;
      if (scene) openLightboxForScene(scene);
    });
  });
  $("#chapterModalBody").querySelectorAll(".timeline-seek-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const scene = pairs[Number(btn.dataset.block)].scene;
      if (scene) seekToScene(scene);
    });
  });

  show($("#chapterModal"));
  chapterModalOpen = true;
  document.body.classList.add("chapter-modal-open");
}

function closeChapterModal() {
  $("#chapterModal").classList.add("hidden");
  chapterModalOpen = false;
  document.body.classList.remove("chapter-modal-open");
}

function infoRow(label, value, { mono = false, link = false, copy = false } = {}) {
  if (!value) {
    return `
      <div class="info-row">
        <div class="info-label">${escapeHtml(label)}</div>
        <div class="info-value muted">暂无</div>
      </div>`;
  }
  const valueHtml = link
    ? `<a href="${escapeHtml(value)}" target="_blank" rel="noopener" class="info-link">${escapeHtml(value)}</a>`
    : `<span class="${mono ? "info-mono" : ""}">${escapeHtml(value)}</span>`;
  const copyBtn = copy
    ? `<button type="button" class="info-copy" data-copy="${escapeHtml(value)}">复制</button>`
    : "";
  return `
    <div class="info-row">
      <div class="info-label">${escapeHtml(label)}</div>
      <div class="info-value">${valueHtml}${copyBtn}</div>
    </div>`;
}

function renderInfoModal(data) {
  const meta = data.meta || {};
  const hashtags = meta.hashtags?.length ? meta.hashtags : (data.hashtags || []);
  const authorLine = meta.author
    ? (meta.author_id ? `${meta.author} (@${meta.author_id})` : meta.author)
    : "";

  $("#infoModalHint").textContent = meta.aweme_id ? `作品 ID：${meta.aweme_id}` : "";
  $("#infoModalBody").innerHTML = `
    ${infoRow("作者", authorLine)}
    ${infoRow("作品标题", meta.desc || meta.title || data.title)}
    <div class="info-row">
      <div class="info-label">内容标签</div>
      <div class="info-value">
        ${hashtags.length
          ? `<div class="info-tags">${hashtags.map(t => `<span class="info-tag">${escapeHtml(t)}</span>`).join("")}</div>`
          : '<span class="muted">暂无</span>'}
      </div>
    </div>
    ${infoRow("分享短链", meta.source_url, { link: true, copy: true })}
    ${infoRow("作品页链接", meta.canonical_url, { link: true, copy: true })}
    ${infoRow("原始分享文案", meta.share_text)}
    ${infoRow("首次下载", formatDate(meta.created_at))}
    ${infoRow("最近拆解", formatDate(meta.last_analysis_at))}
  `;

  $("#infoModalBody").querySelectorAll(".info-copy").forEach(btn => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = "已复制";
        setTimeout(() => { btn.textContent = "复制"; }, 1500);
      } catch {
        alert("复制失败，请手动选择链接");
      }
    });
  });
}

async function openInfoModal(projectId = activeProjectId) {
  if (!projectId) return;
  show($("#infoModal"));
  infoModalOpen = true;
  document.body.classList.add("info-modal-open");
  $("#infoModalBody").innerHTML = '<p class="info-loading">加载作品信息…</p>';

  try {
    let data = currentProject?.id === projectId
      ? currentProject
      : await api(`/api/projects/${projectId}`);

    if (!data.meta?.author) {
      $("#infoModalBody").innerHTML = '<p class="info-loading">正在从抖音拉取作者信息…</p>';
      try {
        const refreshed = await api(`/api/projects/${projectId}/refresh-meta`, {
          method: "POST",
          body: "{}",
        });
        data = { ...data, meta: refreshed.meta };
        if (currentProject?.id === projectId) currentProject.meta = refreshed.meta;
      } catch {
        // Keep partial meta if refresh fails (offline / rate limit).
      }
    }

    renderInfoModal(data);
  } catch (err) {
    $("#infoModalBody").innerHTML = `<p class="info-loading">加载失败：${escapeHtml(err.message)}</p>`;
  }
}

function closeInfoModal() {
  $("#infoModal").classList.add("hidden");
  infoModalOpen = false;
  document.body.classList.remove("info-modal-open");
}

function renderSegments(segments) {
  const el = $("#tab-segments");
  if (!segments?.length) {
    el.innerHTML = '<p class="empty">暂无口播分段</p>';
    return;
  }
  const list = segments.slice(0, 200).map(seg => `
    <div class="segment">
      <div class="meta">
        <span class="${roleClass(seg.role_guess)}">${escapeHtml(seg.role_guess || "body")}</span>
        <span class="time">${escapeHtml(seg.time_range || "")} · ${seg.chars || 0} 字</span>
      </div>
      <div class="text">${escapeHtml(seg.text || "")}</div>
    </div>
  `).join("");
  const tail = segments.length > 200
    ? `<p class="empty">… 共 ${segments.length} 段，完整内容见 report.json</p>`
    : "";
  el.innerHTML = `<div class="segment-list">${list}</div>${tail}`;
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "";
  const s = Math.round(seconds);
  if (s < 60) return `${s} 秒`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m} 分 ${r} 秒` : `${m} 分`;
}

function openLightbox(index) {
  if (!currentScenes.length || index < 0 || index >= currentScenes.length) return;
  lightboxIndex = index;
  openLightboxScene(currentScenes[index]);
}

function closeLightbox() {
  $("#lightbox").classList.add("hidden");
  document.body.classList.remove("lightbox-open");
  lightboxIndex = -1;
  lightboxScene = null;
}

function isLightboxOpen() {
  return !$("#lightbox").classList.contains("hidden");
}

function shiftLightbox(delta) {
  if (lightboxIndex < 0) return;
  const next = (lightboxIndex + delta + currentScenes.length) % currentScenes.length;
  openLightbox(next);
}

function renderScenes(scenes, keyframeMode = "scene") {
  currentScenes = scenes || [];
  const el = $("#tab-scenes");
  if (!currentScenes.length) {
    el.innerHTML = '<p class="empty">暂无关键帧，请使用完整拆解（--full）</p>';
    return;
  }
  const hint = "点击卡片<strong>跳转原片</strong>，点 🔍 <strong>放大预览</strong>";
  el.innerHTML = `
    <p class="panel-hint">${hint}</p>
    ${currentScenes.map((sc, i) => {
      const dur = sc.duration_seconds ?? (sc.end != null && sc.start != null ? sc.end - sc.start : null);
      const speech = sc.text || sc.speech_text || "";
      const vision = formatVisionSummary(sc.vision);
      const subtitle = speech
        ? `<div class="scene-speech">${escapeHtml(speech)}</div>`
        : vision
          ? `<div class="scene-vision">${escapeHtml(vision)}</div>`
          : `<div class="type muted">画面待识别</div>`;
      const visionLine = speech && vision
        ? `<div class="scene-vision">${escapeHtml(vision)}</div>`
        : "";
      return `
    <button type="button" class="scene-card" data-index="${i}">
      <div class="scene-thumb">
        <img src="${sc.image_url}" alt="scene ${sc.index}" loading="lazy" />
        <span class="scene-zoom">🔍</span>
      </div>
      <div class="info">
        <div class="time">${escapeHtml(sc.time_range || "")}${dur ? ` · ${formatDuration(dur)}` : ""}</div>
        ${subtitle}
        ${visionLine}
      </div>
    </button>`;
    }).join("")}`;

  el.querySelectorAll(".scene-card").forEach(card => {
    card.addEventListener("click", () => {
      const idx = Number(card.dataset.index);
      const scene = currentScenes[idx];
      if (scene) seekToScene(scene);
    });
    card.querySelector(".scene-zoom")?.addEventListener("click", (e) => {
      e.stopPropagation();
      openLightbox(Number(card.dataset.index));
    });
  });
}

function renderVisionPanel(data) {
  if (!visionPanel || !data.has_report) {
    visionPanel?.classList.add("hidden");
    return;
  }
  const v = data.vision || {};
  const state = v.state || "none";
  const canMerge = v.has_descriptions && state !== "merged";
  const mergedHint = state === "merged"
    ? `已合并 ${v.merged_scene_count || 0} 个镜头的视觉描述`
    : v.has_manifest
      ? `代表帧 ${v.representative_count || 0} 张 · 共 ${v.task_count || 0} 个任务`
      : "拆解后可单独生成清单，不调用模型、不花钱";

  visionPanel.innerHTML = `
    <div class="vision-head">
      <div>
        <h3>视觉描述（Phase 3）</h3>
        <p class="vision-hint">看图写描述需要 Cursor 等带视觉能力的模型，会消耗 token。默认关闭，按需开启。</p>
      </div>
      <span class="vision-badge vision-${state}">${escapeHtml(visionStateLabel(state))}</span>
    </div>
    <p class="vision-status">${escapeHtml(mergedHint)}</p>
    <div class="vision-actions">
      <button type="button" id="visionPrepBtn" class="btn-secondary">生成视觉任务清单（免费）</button>
      ${canMerge
        ? '<button type="button" id="visionMergeBtn" class="btn-ghost">合并 descriptions.json</button>'
        : ""}
    </div>
    <details class="vision-guide">
      <summary>让 Cursor 看图写描述</summary>
      <ol>
        <li>点上方按钮生成 <code>analysis/vision/manifest.json</code>（或拆解时勾选「同时生成视觉任务清单」）</li>
        <li>在 Cursor 中对 Agent 说：读 manifest，用 Read 工具逐帧看图，写入 <code>descriptions.json</code></li>
        <li>写完后点「合并 descriptions.json」，或运行 <code>python scripts/vision_describe.py merge last</code></li>
      </ol>
    </details>`;

  show(visionPanel);
  $("#visionPrepBtn")?.addEventListener("click", startVisionPrep);
  $("#visionMergeBtn")?.addEventListener("click", startVisionMerge);
}

function bindVideoPlayer(data) {
  if (!detailVideo) return;
  if (data.video_url) {
    if (detailVideo.dataset.src !== data.video_url) {
      detailVideo.dataset.src = data.video_url;
      detailVideo.src = data.video_url;
      detailVideo.load();
    }
    show(videoPlayerWrap);
  } else {
    videoPlayerWrap?.classList.add("hidden");
    detailVideo.removeAttribute("src");
    detailVideo.dataset.src = "";
  }
}

function bindExportReport(data) {
  if (!exportReportBtn) return;
  if (data.has_report && data.report_url) {
    exportReportBtn.href = data.report_url;
    exportReportBtn.classList.remove("hidden");
  } else {
    exportReportBtn.classList.add("hidden");
  }
}

function bindDetailActions(data) {
  if (!detailActions) return;
  show(detailActions);
  if (reanalyzeBtn) {
    reanalyzeBtn.textContent = data.has_report ? "重新拆解" : "继续拆解";
  }
  if (reanalyzeFullBtn) {
    reanalyzeFullBtn.textContent = data.has_report ? "完整重拆" : "完整拆解";
  }
}

function renderAnalysisNotice(data) {
  const el = $("#analysisNotice");
  if (!el) return;
  if (data.has_report) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  const partial = data.analysis_status === "partial";
  el.innerHTML = `
    <div class="analysis-notice-inner">
      <strong>${partial ? "拆解未完成（口播已转写）" : "尚未完成拆解"}</strong>
      <p>${partial
        ? "关键帧和章节生成中断，无需重新下载。点右上角「继续拆解」会从已有口播接着跑（约几分钟）。"
        : "视频已入库。点右上角「继续拆解」开始分析。"}</p>
    </div>`;
  show(el);
}

function setJobRunning(running) {
  analyzeBtn.disabled = running;
  analyzeBtn.querySelector("span:last-child").textContent = running ? "拆解中…" : "开始拆解";
  if (reanalyzeBtn) {
    reanalyzeBtn.disabled = running;
    reanalyzeFullBtn.disabled = running;
  }
  $("#visionPrepBtn") && ($("#visionPrepBtn").disabled = running);
  $("#visionMergeBtn") && ($("#visionMergeBtn").disabled = running);
}

function renderProject(data) {
  currentProject = data;
  activeProjectId = data.id;
  AppNav.setProjectContext(data.id, data.title || "");
  detailTitle.textContent = (data.title || "视频详情").slice(0, 40);
  detailTitle.title = "点击查看作品信息";
  detailMeta.textContent = [
    data.duration_label,
    `${data.chapters?.length || 0} 章`,
    `${data.scenes?.length || 0} 帧`,
    keyframeModeLabel(data.keyframe_mode, data.frame_count),
  ].filter(Boolean).join(" · ");
  bindDetailActions(data);
  renderAnalysisNotice(data);
  renderSummary(data);
  renderChapters(data.chapters);
  renderSegments(data.segments);
  renderScenes(data.scenes, data.keyframe_mode);
  renderVisionPanel(data);
  bindVideoPlayer(data);
  bindExportReport(data);
}

async function loadLibrary(selectId = null) {
  const { projects } = await api("/api/projects");
  renderProjectList(projects);
  if (selectId) {
    await selectProject(selectId, { force: true });
  }
}

async function loadProject(id) {
  const data = await api(`/api/projects/${id}`);
  renderProject(data);
}

async function pollJob(jobId) {
  const job = await api(`/api/jobs/${jobId}`);
  setProgress(job.progress || 0, job.message || job.status);

  if (job.status === "done" && job.project_id) {
    clearInterval(pollTimer);
    setJobRunning(false);
    await loadLibrary(job.project_id);
    AppNav.navigate(AppNav.routeForDetail(job.project_id, "overview"));
    return;
  }
  if (job.status === "error") {
    clearInterval(pollTimer);
    setJobRunning(false);
    progressText.textContent = `失败：${job.message}`;
  }
}

async function startReanalyze(force = false) {
  if (!activeProjectId) return;
  const { keyframe_mode, frame_count } = getKeyframeSettings();
  const modeText = keyframeModeLabel(keyframe_mode, frame_count);
  const partial = currentProject?.analysis_status === "partial" && !currentProject?.has_report;
  const msg = force
    ? `将重新转写口播，并按「${modeText}」提取关键帧，耗时较长，继续？`
    : partial
      ? `将从已有口播继续，按「${modeText}」生成关键帧和章节（无需重新下载），继续？`
      : `将保留已有口播，按「${modeText}」重新提取关键帧和章节，继续？`;
  if (!confirm(msg)) return;

  setJobRunning(true);
  setProgress(10, force ? "提交完整重拆…" : "提交重新拆解…");

  try {
    const { job_id } = await api(`/api/projects/${activeProjectId}/reanalyze`, {
      method: "POST",
      body: JSON.stringify({
        force,
        keyframe_mode,
        frame_count,
        vision_prep: getVisionPrep(),
      }),
    });
    pollTimer = setInterval(() => pollJob(job_id), 1500);
    await pollJob(job_id);
  } catch (err) {
    setJobRunning(false);
    progressText.textContent = `失败：${err.message}`;
  }
}

async function startVisionPrep() {
  if (!activeProjectId) return;
  setJobRunning(true);
  setProgress(10, "生成视觉任务清单…");
  try {
    const { job_id } = await api(`/api/projects/${activeProjectId}/vision-prep`, {
      method: "POST",
      body: "{}",
    });
    pollTimer = setInterval(() => pollJob(job_id), 1500);
    await pollJob(job_id);
  } catch (err) {
    setJobRunning(false);
    progressText.textContent = `失败：${err.message}`;
  }
}

async function startVisionMerge() {
  if (!activeProjectId) return;
  if (!confirm("将把 descriptions.json 合并进 report，继续？")) return;
  setJobRunning(true);
  setProgress(50, "合并视觉描述…");
  try {
    const data = await api(`/api/projects/${activeProjectId}/vision-merge`, {
      method: "POST",
      body: "{}",
    });
    setJobRunning(false);
    renderProject(data);
    setProgress(100, "视觉描述已合并");
  } catch (err) {
    setJobRunning(false);
    progressText.textContent = `失败：${err.message}`;
  }
}

analyzeBtn.addEventListener("click", async () => {
  const text = shareText.value.trim();
  if (!text) return alert("请先粘贴分享文案或链接");

  analyzeBtn.disabled = true;
  analyzeBtn.querySelector("span:last-child").textContent = "拆解中…";
  setProgress(5, "提交任务…");

  try {
    const { job_id } = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({
        share_text: text,
        ...getKeyframeSettings(),
        vision_prep: getVisionPrep(),
      }),
    });
    pollTimer = setInterval(() => pollJob(job_id), 1500);
    await pollJob(job_id);
  } catch (err) {
    setJobRunning(false);
    progressText.textContent = `失败：${err.message}`;
  }
});

reanalyzeBtn.addEventListener("click", () => startReanalyze(false));
reanalyzeFullBtn.addEventListener("click", () => startReanalyze(true));
detailTitle.addEventListener("click", () => openInfoModal(activeProjectId));

$("#infoModalClose").addEventListener("click", closeInfoModal);
$("#infoModalBackdrop").addEventListener("click", closeInfoModal);

$("#lightboxClose").addEventListener("click", closeLightbox);
$("#lightboxPrev").addEventListener("click", () => shiftLightbox(-1));
$("#lightboxNext").addEventListener("click", () => shiftLightbox(1));
lightboxSeek?.addEventListener("click", () => {
  const scene = lightboxIndex >= 0 ? currentScenes[lightboxIndex] : lightboxScene;
  if (scene) seekToScene(scene);
});
$("#lightbox").addEventListener("click", (e) => {
  if (e.target.id === "lightbox") closeLightbox();
});
document.addEventListener("keydown", (e) => {
  if (isLightboxOpen()) {
    if (e.key === "Escape") closeLightbox();
    if (lightboxIndex >= 0 && e.key === "ArrowLeft") shiftLightbox(-1);
    if (lightboxIndex >= 0 && e.key === "ArrowRight") shiftLightbox(1);
    return;
  }
  if (chapterModalOpen && e.key === "Escape") closeChapterModal();
  if (infoModalOpen && e.key === "Escape") closeInfoModal();
});

$("#chapterModalClose").addEventListener("click", closeChapterModal);
$("#chapterModalBackdrop").addEventListener("click", closeChapterModal);

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// --- 制作策划 ---
let activePlanId = null;
let currentPlan = null;
let planDirty = false;
let planShotsData = [];
let cachedPlanList = [];
let activeShotIndex = 1;

function markPlanDirty() {
  planDirty = true;
}

function readShotFromRow(row) {
  if (!row) return null;
  const index = Number(row.dataset.shotIndex) || 1;
  const existing = planShotsData.find(s => (s.index ?? 0) === index) || {};
  return {
    ...existing,
    index,
    visual: row.querySelector('[data-field="visual"]')?.value || "",
    voiceover: row.querySelector('[data-field="voiceover"]')?.value || "",
    action: row.querySelector('[data-field="action"]')?.value || "",
    subtitle: row.querySelector('[data-field="subtitle"]')?.value || "",
  };
}

function persistShotFromEditor() {
  const row = $("#shotsTable")?.querySelector(".shot-row");
  if (!row || !planShotsData.length) return;
  const shot = readShotFromRow(row);
  if (!shot) return;
  const i = planShotsData.findIndex(s => (s.index ?? 0) === shot.index);
  if (i >= 0) planShotsData[i] = { ...planShotsData[i], ...shot };
  activeShotIndex = shot.index;
  refreshPlanTree();
}

function collectPlanFromForm() {
  persistShotFromEditor();
  return {
    ...(currentPlan || {}),
    id: currentPlan?.id || "untitled",
    title: $("#planTitle")?.value?.trim() || "未命名",
    goal: $("#planGoal")?.value?.trim() || "",
    aspect_ratio: $("#planAspect")?.value?.trim() || "9:16",
    total_duration: $("#planDuration")?.value?.trim() || "",
    shots: planShotsData.map((s, i) => ({ ...s, index: s.index ?? i + 1 })),
    full_script: $("#planFullScript")?.value || "",
    notes: $("#planNotes")?.value || "",
  };
}

const SHOT_TEXTAREA_MAX_PX = {
  visual: 280,
  voiceover: 280,
  action: 320,
  subtitle: 88,
};

function autoResizeShotTextarea(el) {
  if (!el) return;
  const field = el.dataset.field || "";
  const maxPx = SHOT_TEXTAREA_MAX_PX[field] || 260;
  el.style.height = "auto";
  const next = Math.max(el.scrollHeight, 0);
  if (next > maxPx) {
    el.style.height = `${maxPx}px`;
    el.style.overflowY = "auto";
  } else {
    el.style.height = `${next}px`;
    el.style.overflowY = "hidden";
  }
}

function autoResizeAllShotTextareas(root = $("#shotsTable")) {
  root?.querySelectorAll("textarea[data-field]").forEach((el) => {
    autoResizeShotTextarea(el);
  });
}

function renderShotRow(shot, idx) {
  const shotIndex = shot.index ?? idx + 1;
  return `
    <div class="shot-row" data-index="${idx}" data-shot-index="${shotIndex}">
      <div class="shot-fields shot-fields-stack">
        <label class="shot-field-wide">画面<textarea data-field="visual" rows="1">${escapeHtml(shot.visual || "")}</textarea></label>
        <label class="shot-field-wide">口播<textarea data-field="voiceover" rows="1">${escapeHtml(shot.voiceover || "")}</textarea></label>
        <label class="shot-field-wide">操作 / 录屏<textarea data-field="action" rows="1">${escapeHtml(shot.action || "")}</textarea></label>
        <label class="shot-field-wide shot-field-short">字幕 / 贴纸<textarea data-field="subtitle" rows="1">${escapeHtml(shot.subtitle || "")}</textarea></label>
      </div>
    </div>`;
}

function renderSingleShotEditor(shotIndex) {
  persistShotFromEditor();
  activeShotIndex = shotIndex;
  const shot = planShotsData.find(s => (s.index ?? 0) === shotIndex)
    || planShotsData[shotIndex - 1]
    || { index: shotIndex, time_range: "", visual: "", voiceover: "", action: "", subtitle: "" };
  const idx = planShotsData.findIndex(s => (s.index ?? 0) === shotIndex);
  $("#shotsTable").innerHTML = renderShotRow(shot, idx >= 0 ? idx : shotIndex - 1);
  bindShotRowEvents();
  requestAnimationFrame(() => autoResizeAllShotTextareas());
  const label = $("#activeShotLabel");
  if (label) {
    const time = shot.time_range ? ` · ${shot.time_range}` : "";
    label.textContent = `镜 ${shotIndex}${time}`;
  }
}

function showProducePanel(view = "info", shotIndex = 1) {
  const infoPanel = $("#planPanelInfo");
  const shotPanel = $("#planPanelShot");
  if (view === "shot") {
    infoPanel?.classList.add("hidden");
    shotPanel?.classList.remove("hidden");
    renderSingleShotEditor(shotIndex);
    refreshPlanTree();
  } else {
    persistShotFromEditor();
    infoPanel?.classList.remove("hidden");
    shotPanel?.classList.add("hidden");
    refreshPlanTree();
  }
}

function bindShotRowEvents() {
  $("#shotsTable")?.querySelectorAll("textarea[data-field]").forEach(el => {
    el.addEventListener("input", () => {
      markPlanDirty();
      persistShotFromEditor();
      autoResizeShotTextarea(el);
    });
  });
  autoResizeAllShotTextareas();
}

function reindexShots() {
  planShotsData = planShotsData.map((s, i) => ({ ...s, index: i + 1 }));
  refreshPlanTree();
}

function deleteActiveShot() {
  const parsed = AppNav.parseRoute(AppNav.getActiveRoute());
  if (parsed.view !== "shot" || !parsed.shotIndex) return;
  if (planShotsData.length <= 1) {
    alert("至少保留一镜");
    return;
  }
  if (!confirm(`删除镜 ${parsed.shotIndex}？`)) return;
  persistShotFromEditor();
  planShotsData = planShotsData.filter(s => (s.index ?? 0) !== parsed.shotIndex);
  reindexShots();
  markPlanDirty();
  const nextIndex = Math.min(parsed.shotIndex, planShotsData.length);
  AppNav.navigate(AppNav.routeForPlan(activePlanId, "shot", nextIndex));
}

function getShotsForPlanNav(plan) {
  if (plan.id === activePlanId && planShotsData.length) {
    return planShotsData.map(s => ({
      index: s.index,
      time_range: s.time_range || "",
    }));
  }
  return plan.shots || [];
}

function refreshPlanTree() {
  if (!cachedPlanList.length) return;
  renderPlanList(cachedPlanList);
}

function renderPlanList(plans) {
  cachedPlanList = plans;
  const el = $("#planList");
  if (!plans.length) {
    el.innerHTML = `<p class="plan-list-empty">暂无策划，点「+ 新建」</p>`;
    return;
  }

  const routeParsed = AppNav.parseRoute(AppNav.getActiveRoute());

  el.innerHTML = plans.map(p => {
    const isActivePlan = p.id === activePlanId;
    const shots = getShotsForPlanNav(p);
    const children = isActivePlan ? `
      <div class="plan-tree-children">
        <button type="button" class="plan-sub-item${routeParsed.view === "info" && routeParsed.planId === p.id ? " active" : ""}"
          data-plan-id="${escapeHtml(p.id)}" data-nav="info">策划总览</button>
        ${shots.map(s => {
          const active = routeParsed.view === "shot" && routeParsed.planId === p.id && routeParsed.shotIndex === s.index;
          const time = s.time_range ? ` · ${escapeHtml(s.time_range)}` : "";
          return `<button type="button" class="plan-sub-item${active ? " active" : ""}"
            data-plan-id="${escapeHtml(p.id)}" data-nav="shot" data-shot-index="${s.index}">镜 ${s.index}${time}</button>`;
        }).join("")}
      </div>` : "";

    return `
      <div class="plan-tree-item${isActivePlan ? " active" : ""}">
        <button type="button" class="plan-tree-head" data-plan-id="${escapeHtml(p.id)}">
          <span class="plan-tree-title">${escapeHtml(p.title || p.id)}</span>
          <span class="plan-tree-meta">${escapeHtml([p.total_duration, `${p.shot_count || shots.length || 0} 镜`].filter(Boolean).join(" · "))}</span>
        </button>
        ${children}
      </div>`;
  }).join("");

  el.querySelectorAll(".plan-tree-head").forEach(btn => {
    btn.addEventListener("click", () => {
      AppNav.navigate(AppNav.routeForPlan(btn.dataset.planId, "info"));
    });
  });
  el.querySelectorAll(".plan-sub-item").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const planId = btn.dataset.planId;
      if (btn.dataset.nav === "shot") {
        AppNav.navigate(AppNav.routeForPlan(planId, "shot", Number(btn.dataset.shotIndex) || 1));
      } else {
        AppNav.navigate(AppNav.routeForPlan(planId, "info"));
      }
    });
  });
}

function renderPlanEditor(plan) {
  currentPlan = plan;
  activePlanId = plan.id;
  AppNav.setPlanContext(plan.id);
  planDirty = false;
  show($("#planEditor"));
  $("#planEmpty")?.classList.add("hidden");

  $("#planTitle").value = plan.title || "";
  $("#planGoal").value = plan.goal || "";
  $("#planAspect").value = plan.aspect_ratio || "9:16";
  $("#planDuration").value = plan.total_duration || "";
  $("#planFullScript").value = plan.full_script || "";
  $("#planNotes").value = plan.notes || "";
  $("#planMeta").textContent = [
    plan.total_duration,
    `${(plan.shots || []).length} 镜`,
    plan.file_path,
    plan.updated_at ? `更新 ${formatDate(plan.updated_at)}` : "",
  ].filter(Boolean).join(" · ");

  planShotsData = (plan.shots?.length ? plan.shots : [
    { index: 1, time_range: "", visual: "", voiceover: "", action: "", subtitle: "" },
  ]).map((s, i) => ({ ...s, index: s.index ?? i + 1 }));

  ["planTitle", "planGoal", "planAspect", "planDuration", "planFullScript", "planNotes"].forEach(id => {
    const el = $(`#${id}`);
    if (!el) return;
    el.oninput = () => {
      markPlanDirty();
      if (id === "planTitle") refreshPlanTree();
    };
  });

  refreshPlanTree();
  renderTtsAudioList(plan.audio);
}

function renderTtsAudioList(audio) {
  const el = $("#ttsAudioList");
  if (!el) return;
  const items = audio?.items || [];
  if (!items.length) {
    el.innerHTML = `<p class="hint">尚未生成配音。保存策划后点「生成全部配音」。</p>`;
    return;
  }
  const when = audio.generated_at ? ` · ${escapeHtml(audio.generated_at)}` : "";
  el.innerHTML = `
    <p class="hint">已生成 ${items.length} 个文件${when}</p>
    ${items.map(item => `
      <div class="tts-audio-item">
        <div class="tts-audio-meta">
          <strong>${escapeHtml(item.filename || item.key)}</strong>
          <span class="hint">${escapeHtml((item.text || "").slice(0, 48))}${(item.text || "").length > 48 ? "…" : ""}</span>
        </div>
        <audio controls preload="none" src="${escapeHtml(item.url)}"></audio>
      </div>`).join("")}`;
}

async function loadPlanList(selectId = null) {
  const { plans } = await api("/api/productions");
  renderPlanList(plans);
  if (selectId) await loadPlan(selectId, { skipNav: true });
}

async function loadPlan(id, { skipNav = false } = {}) {
  const plan = await api(`/api/productions/${id}`);
  renderPlanEditor(plan);
  if (!skipNav) {
    const parsed = AppNav.parseRoute(AppNav.getActiveRoute());
    if (parsed.planId === id && parsed.view === "shot") {
      AppNav.navigate(AppNav.routeForPlan(id, "shot", parsed.shotIndex || 1));
    } else {
      AppNav.navigate(AppNav.routeForPlan(id, "info"));
    }
  }
}

async function saveCurrentPlan() {
  const plan = collectPlanFromForm();
  const saved = await api(`/api/productions/${plan.id}/save`, {
    method: "POST",
    body: JSON.stringify(plan),
  });
  renderPlanEditor(saved);
  await loadPlanList(saved.id);
  $("#aiPromptStatus")?.classList.add("hidden");
}

function exportPlanMarkdown() {
  const plan = collectPlanFromForm();
  const lines = [
    `# ${plan.title}`,
    "",
    `- **目标**：${plan.goal || "-"}`,
    `- **画幅**：${plan.aspect_ratio}`,
    `- **总时长**：${plan.total_duration}`,
    "",
    "## 分镜表",
    "",
    "| 镜号 | 时长 | 秒 | 画面 | 口播 | 操作 |",
    "|------|------|-----|------|------|------|",
  ];
  (plan.shots || []).forEach(s => {
    const esc = (t) => String(t || "").replace(/\|/g, "\\|").replace(/\n/g, " ");
    lines.push(`| ${s.index} | ${esc(s.time_range)} | ${s.duration_seconds || ""} | ${esc(s.visual)} | ${esc(s.voiceover)} | ${esc(s.action)} |`);
  });
  lines.push("", "## 完整口播稿", "", plan.full_script || "", "", "## 备注", "", plan.notes || "");
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${plan.title || plan.id}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function copyAiRevisePrompt() {
  const plan = collectPlanFromForm();
  const instruction = $("#aiReviseInstruction")?.value?.trim() || "";
  const { prompt, file_path } = await api(`/api/productions/${plan.id}/ai-prompt`, {
    method: "POST",
    body: JSON.stringify({ instruction, plan }),
  });
  try {
    await navigator.clipboard.writeText(prompt);
    const status = $("#aiPromptStatus");
    if (status) {
      status.textContent = `已复制修改指令。请在 Cursor 粘贴发送，改完后点「刷新」。文件：${file_path}`;
      show(status);
    }
  } catch {
    alert("复制失败，请手动从控制台或网络响应获取");
    console.log(prompt);
  }
}

async function createNewPlan() {
  const title = prompt("新视频标题", "新视频策划");
  if (!title) return;
  const useTemplate = confirm("是否从 EvoFlow 参赛模板复制？\n确定=模板 · 取消=空白");
  const plan = await api("/api/productions", {
    method: "POST",
    body: JSON.stringify({
      title,
      template: useTemplate ? "evoflow-web-coding" : undefined,
    }),
  });
  await loadPlanList(plan.id);
  AppNav.navigate(AppNav.routeForPlan(plan.id, "shot", 1));
}

$("#newPlanBtn")?.addEventListener("click", createNewPlan);
$("#savePlanBtn")?.addEventListener("click", () => saveCurrentPlan().catch(err => alert(err.message)));
$("#exportPlanBtn")?.addEventListener("click", exportPlanMarkdown);
$("#addShotBtn")?.addEventListener("click", () => {
  persistShotFromEditor();
  const newIndex = planShotsData.length + 1;
  planShotsData.push({
    index: newIndex,
    time_range: "",
    duration_seconds: 0,
    visual: "",
    voiceover: "",
    action: "",
    subtitle: "",
  });
  markPlanDirty();
  refreshPlanTree();
  AppNav.navigate(AppNav.routeForPlan(activePlanId, "shot", newIndex));
});
$("#deleteShotBtn")?.addEventListener("click", deleteActiveShot);
$("#copyAiPromptBtn")?.addEventListener("click", () => copyAiRevisePrompt().catch(err => alert(err.message)));
$("#reloadPlanBtn")?.addEventListener("click", () => {
  if (!activePlanId) return;
  const parsed = AppNav.parseRoute(AppNav.getActiveRoute());
  loadPlan(activePlanId, { skipNav: true })
    .then(() => showProducePanel(parsed.view === "shot" ? "shot" : "info", parsed.shotIndex || 1))
    .catch(err => alert(err.message));
});

let ttsPollTimer = null;

async function pollTtsJob(jobId) {
  const job = await api(`/api/jobs/${jobId}`);
  const wrap = $("#ttsProgress");
  const fill = $("#ttsProgressFill");
  const text = $("#ttsProgressText");
  if (wrap) show(wrap);
  if (fill) fill.style.width = `${job.progress || 0}%`;
  if (text) text.textContent = job.message || "";

  if (job.status === "done") {
    clearInterval(ttsPollTimer);
    ttsPollTimer = null;
    if (activePlanId) {
      const plan = await api(`/api/productions/${activePlanId}`);
      renderPlanEditor(plan);
      showProducePanel("info");
    }
    return;
  }
  if (job.status === "error") {
    clearInterval(ttsPollTimer);
    ttsPollTimer = null;
    alert(job.message || "配音失败");
  }
}

async function generateProductionTts({ includeFullScript = true } = {}) {
  if (!activePlanId) {
    alert("请先选择一个策划");
    return;
  }
  if (planDirty) {
    const ok = confirm("策划有未保存修改，是否先保存再生成配音？");
    if (ok) await saveCurrentPlan();
  }
  const { job_id } = await api(`/api/productions/${activePlanId}/tts`, {
    method: "POST",
    body: JSON.stringify({ include_full_script: includeFullScript }),
  });
  if (ttsPollTimer) clearInterval(ttsPollTimer);
  ttsPollTimer = setInterval(() => pollTtsJob(job_id).catch(console.error), 800);
  pollTtsJob(job_id).catch(console.error);
}

$("#generateTtsBtn")?.addEventListener("click", () => {
  generateProductionTts({ includeFullScript: true }).catch(err => alert(err.message));
});
$("#generateTtsShotsOnlyBtn")?.addEventListener("click", () => {
  generateProductionTts({ includeFullScript: false }).catch(err => alert(err.message));
});

let ttsSettingsCache = null;
let ttsSpeakerPickerCtrl = null;

async function loadTtsSettings() {
  const data = await api("/api/settings/tts");
  ttsSettingsCache = data;
  const status = $("#ttsSettingsStatus");
  if (status) {
    status.innerHTML = data.configured
      ? `<span class="pill pill-ok">已配置 ${escapeHtml(data.apiKeyMasked || "Key")}</span>`
      : `<span class="pill pill-warn">未配置 Key · 生成配音前请先填写</span>`;
  }
  const countEl = $("#ttsVoiceCount");
  if (countEl) countEl.textContent = `${data.voiceCount || (data.voices || []).length} 个音色 · 点选 · ▶ 试听`;

  const mountEl = $("#ttsSpeakerPicker");
  if (mountEl && globalThis.TtsSpeakerPicker?.mountInline) {
    mountEl.innerHTML = "";
    ttsSpeakerPickerCtrl = TtsSpeakerPicker.mountInline(mountEl, {
      presets: data.voices || [],
      value: data.ttsSpeaker || "",
    });
  }
  const keyEl = $("#ttsApiKey");
  if (keyEl && data.apiKeyMasked) keyEl.placeholder = data.apiKeyMasked;
  const resEl = $("#ttsResourceId");
  if (resEl) resEl.value = data.ttsResourceId || "seed-tts-2.0";
}

async function saveTtsSettingsForm() {
  const payload = {
    ttsSpeaker: ttsSpeakerPickerCtrl?.getValue() || "",
    ttsResourceId: $("#ttsResourceId")?.value || "seed-tts-2.0",
  };
  const key = $("#ttsApiKey")?.value?.trim();
  if (key) payload.apiKey = key;
  const saved = await api("/api/settings/tts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  ttsSettingsCache = saved;
  const msg = $("#ttsSettingsMessage");
  if (msg) {
    msg.textContent = "设置已保存";
    show(msg);
  }
  $("#ttsApiKey").value = "";
  if (ttsSpeakerPickerCtrl) ttsSpeakerPickerCtrl.setValue(saved.ttsSpeaker || "");
  const status = $("#ttsSettingsStatus");
  if (status) {
    status.innerHTML = saved.configured
      ? `<span class="pill pill-ok">已配置 ${escapeHtml(saved.apiKeyMasked || "Key")}</span>`
      : `<span class="pill pill-warn">未配置 Key · 生成配音前请先填写</span>`;
  }
}

$("#saveTtsSettingsBtn")?.addEventListener("click", () => {
  saveTtsSettingsForm().catch(err => alert(err.message));
});

AppNav.onRouteChange(applyRoute);
AppNav.init();

document.querySelectorAll('input[name="keyframeMode"]').forEach(radio => {
  radio.addEventListener("change", syncKeyframeModeUI);
});
syncKeyframeModeUI();
