const $ = (sel) => document.querySelector(sel);

const shareText = $("#shareText");
const analyzeBtn = $("#analyzeBtn");
const libraryCount = $("#libraryCount");
const projectList = $("#projectList");
const viewAnalyzeInput = $("#viewAnalyzeInput");
const viewAnalyzeLibrary = $("#viewAnalyzeLibrary");
const viewAnalyzeDetail = $("#viewAnalyzeDetail");
const detailPanels = {
  report: $("#detailPanelReport"),
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
const reportInline = $("#reportInline");
const reportInlineBody = $("#reportInlineBody");
const reportEmpty = $("#reportEmpty");
const detailSubnav = $("#detailSubnav");
const crumbLibrary = $("#crumbLibrary");
const crumbTitle = $("#crumbTitle");
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

function getAnalysisMode() {
  const fixed = document.querySelector('input[name="analysisMode"][type="hidden"]');
  if (fixed?.value) return fixed.value;
  return document.querySelector('input[name="analysisMode"]:checked')?.value || "content";
}

function getKeyframeSettings() {
  const analysisMode = getAnalysisMode();
  const mode =
    document.querySelector('input[name="keyframeMode"]:checked')?.value ||
    "transcript";
  const frameCount = Math.max(5, Math.min(300, Number(frameCountInput?.value) || 30));
  return {
    analysis_mode: analysisMode,
    keyframe_mode: mode,
    frame_count: frameCount,
  };
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
  syncAnalyzeButtonLabel();
}

function syncAnalyzeButtonLabel() {
  if (!analyzeBtn || analyzeBtn.disabled) return;
  const label = analyzeBtn.querySelector("span:last-child");
  if (label) label.textContent = "开始拆解";
}

function onAnalysisModeChange() {
  syncKeyframeModeUI();
}

function keyframeModeLabel(mode, count) {
  if (mode === "transcript") return "口播一句一帧";
  if (mode === "custom") return `自定义 ${count || 30} 帧`;
  return "镜头切换";
}

function analysisModeLabel(_mode) {
  return "内容拆解";
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

function preferredDetailTab(data) {
  if (data?.has_report) return "report";
  return "overview";
}

async function selectProject(id, { force = false, tab = null, skipNavigate = false } = {}) {
  if (!id) return;
  if (!force && id === activeProjectId && !skipNavigate) return;
  try {
    activeProjectId = id;
    projectList.querySelectorAll(".project-card").forEach((card) => {
      card.classList.toggle("active", card.dataset.id === id);
    });
    await loadProject(id);
    AppNav.setProjectContext(id, currentProject?.title || "");
    const resolved = tab || preferredDetailTab(currentProject);
    showDetailTab(resolved);
    if (!skipNavigate) {
      AppNav.navigate(AppNav.routeForDetail(id, resolved));
    }
  } catch (err) {
    alert(err.message);
  }
}

function syncDetailSubnav(tab = "report") {
  if (!detailSubnav) return;
  detailSubnav.querySelectorAll(".subnav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
}

function showDetailTab(tab = "report") {
  const t = (AppNav.DETAIL_TABS || []).includes(tab) ? tab : "report";
  Object.entries(detailPanels).forEach(([name, el]) => {
    if (!el) return;
    el.classList.toggle("hidden", name !== t);
  });
  syncDetailSubnav(t);
}

function applyRoute(parsed) {
  [viewAnalyzeInput, viewAnalyzeLibrary, viewAnalyzeDetail].forEach(el => {
    el?.classList.add("hidden");
  });

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
    const tab = parsed.tab || "report";
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

async function renderReportInline(data) {
  if (!reportInline || !reportInlineBody) return;
  if (!data.has_report || !data.report_url) {
    reportInline.classList.add("hidden");
    reportInlineBody.innerHTML = "";
    if (reportEmpty) show(reportEmpty);
    return;
  }
  if (reportEmpty) reportEmpty.classList.add("hidden");
  show(reportInline);
  reportInlineBody.dataset.loadedFor = "";
  reportInlineBody.innerHTML = '<p class="report-loading">报告加载中…</p>';
  try {
    const res = await fetch(`/api/projects/${data.id}/report?view=html`);
    if (!res.ok) throw new Error(`加载失败 (${res.status})`);
    const payload = await res.json();
    reportInlineBody.innerHTML = payload.html;
    reportInlineBody.dataset.loadedFor = data.id;
    const rawLink = $("#reportModalRaw2");
    if (rawLink) {
      rawLink.href = payload.raw_url;
      rawLink.classList.remove("hidden");
    }
    const kbLink = $("#reportModalRaw");
    if (kbLink) {
      kbLink.href = payload.raw_url;
      kbLink.title = payload.kb_path || "Markdown 原文";
      kbLink.classList.remove("hidden");
    }
    // 默认展开完整报告
    reportInlineBody.classList.remove("collapsed");
    updateInlineToggle();
  } catch (err) {
    reportInlineBody.innerHTML = `<p class="report-loading">报告加载失败：${escapeHtml(err.message)}</p>`;
  }
}

function updateInlineToggle() {
  const btn = $("#reportInlineToggle");
  if (!btn || !reportInlineBody) return;
  const collapsed = reportInlineBody.classList.contains("collapsed");
  btn.textContent = collapsed ? "展开全部" : "收起";
}

function toggleReportInline() {
  if (!reportInlineBody) return;
  reportInlineBody.classList.toggle("collapsed");
  updateInlineToggle();
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

function bindExportReport(_data) {
  // 报告已是二级页签「报告」，不再用弹窗「查看报告」
}

async function openReportModal(data) {
  const modal = $("#reportModal");
  const body = $("#reportModalBody");
  const title = $("#reportModalTitle");
  const meta = $("#reportModalMeta");
  if (!modal || !body) return;
  title.textContent = (data.title || "拆解报告").slice(0, 30);
  meta.textContent = [data.duration_label, `${data.chapters?.length || 0} 章`, `${data.scenes?.length || 0} 帧`]
    .filter(Boolean).join(" · ");
  body.innerHTML = '<p class="report-loading">加载中…</p>';
  show(modal);
  document.body.classList.add("report-modal-open");
  try {
    const res = await fetch(`/api/projects/${data.id}/report?view=html`);
    if (!res.ok) throw new Error(`加载失败 (${res.status})`);
    const payload = await res.json();
    body.innerHTML = payload.html;
    const kbLink = $("#reportModalRaw");
    if (kbLink) {
      kbLink.href = payload.raw_url;
      kbLink.title = payload.kb_path || "知识库副本";
      kbLink.classList.remove("hidden");
    }
  } catch (err) {
    body.innerHTML = `<p class="report-loading">加载失败：${escapeHtml(err.message)}</p>`;
  }
}

function closeReportModal() {
  const modal = $("#reportModal");
  if (!modal) return;
  modal.classList.add("hidden");
  document.body.classList.remove("report-modal-open");
}

function bindDetailActions(data) {
  if (!detailActions) return;
  show(detailActions);
  if (reanalyzeBtn) {
    reanalyzeBtn.textContent = data.has_report ? "重新分析" : "继续分析";
  }
  if (reanalyzeFullBtn) {
    reanalyzeFullBtn.textContent = data.has_report ? "完整重拆" : "完整分析";
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
  analyzeBtn.querySelector("span:last-child").textContent = running
    ? "拆解中…"
    : "开始拆解";
  if (reanalyzeBtn) {
    reanalyzeBtn.disabled = running;
    reanalyzeFullBtn.disabled = running;
  }
}

function renderProject(data) {
  currentProject = data;
  activeProjectId = data.id;
  AppNav.setProjectContext(data.id, data.title || "");
  const titleText = data.title || "视频详情";
  detailTitle.textContent = titleText.slice(0, 40);
  detailTitle.title = "点击查看作品信息";
  if (crumbTitle) {
    crumbTitle.textContent = titleText.slice(0, 28) + (titleText.length > 28 ? "…" : "");
    crumbTitle.title = titleText;
  }
  detailMeta.textContent = [
    analysisModeLabel(data.analysis_mode),
    data.duration_label,
    data.media?.aspect_ratio || data.media?.resolution
      ? [data.media?.orientation, data.media?.aspect_ratio, data.media?.resolution]
          .filter(Boolean)
          .join(" ")
      : null,
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
  renderReportInline(data);
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
    AppNav.navigate(AppNav.routeForDetail(job.project_id, "report"));
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
  const { analysis_mode, keyframe_mode, frame_count } = getKeyframeSettings();
  const modeText = keyframeModeLabel(keyframe_mode, frame_count);
  const analysisText = analysisModeLabel(analysis_mode);
  const partial = currentProject?.analysis_status === "partial" && !currentProject?.has_report;
  const msg = force
    ? `将重新转写口播，模式「${analysisText}」，关键帧「${modeText}」，耗时较长，继续？`
    : partial
      ? `将从已有口播继续，模式「${analysisText}」，关键帧「${modeText}」（无需重新下载），继续？`
      : `将保留已有口播，模式「${analysisText}」，关键帧「${modeText}」重新生成报告，继续？`;
  if (!confirm(msg)) return;

  setJobRunning(true);
  setProgress(10, force ? "提交完整重拆…" : "提交重新拆解…");

  try {
    const { job_id } = await api(`/api/projects/${activeProjectId}/reanalyze`, {
      method: "POST",
      body: JSON.stringify({
        force,
        analysis_mode,
        keyframe_mode,
        frame_count,
      }),
    });
    pollTimer = setInterval(() => pollJob(job_id), 1500);
    await pollJob(job_id);
  } catch (err) {
    setJobRunning(false);
    progressText.textContent = `失败：${err.message}`;
  }
}

analyzeBtn.addEventListener("click", async () => {
  const text = shareText.value.trim();
  if (!text) return alert("请先粘贴分享文案或链接");

  const settings = getKeyframeSettings();
  analyzeBtn.disabled = true;
  analyzeBtn.querySelector("span:last-child").textContent =
    "拆解中…";
  setProgress(5, "提交任务…");

  try {
    const { job_id } = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({
        share_text: text,
        ...settings,
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
$("#reportInlineToggle")?.addEventListener("click", toggleReportInline);

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

$("#reportModalClose")?.addEventListener("click", closeReportModal);
$("#reportModalBackdrop")?.addEventListener("click", closeReportModal);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#reportModal")?.classList.contains("hidden")) closeReportModal();
});

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

AppNav.onRouteChange(applyRoute);
AppNav.init();

document.querySelectorAll('input[name="keyframeMode"]').forEach((radio) => {
  radio.addEventListener("change", syncKeyframeModeUI);
});
document.querySelectorAll('input[name="analysisMode"]').forEach((radio) => {
  radio.addEventListener("change", onAnalysisModeChange);
});
syncKeyframeModeUI();

detailSubnav?.querySelectorAll(".subnav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    const id = activeProjectId || AppNav.getProjectId();
    if (!id || !tab) return;
    AppNav.navigate(AppNav.routeForDetail(id, tab));
  });
});

crumbLibrary?.addEventListener("click", () => {
  AppNav.navigate("analyze/library");
});
