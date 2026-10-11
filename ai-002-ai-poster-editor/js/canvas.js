/* ==============================
   画布管理 — canvas.js
   管理画布 DOM、背景图、编辑区缩放
   ============================== */

const Canvas = (() => {
  const el = document.getElementById('canvas');
  const stage = document.getElementById('canvasWrapper');
  const zoomValueEl = document.getElementById('zoomValue');

  // 画布逻辑尺寸（移动端产物）
  const CANVAS_W = 375;
  const CANVAS_H = 812;
  const MIN_ZOOM = 0.1;
  const MAX_ZOOM = 4;

  let zoom = 1;

  /** 设置缩放比例并应用 */
  function setZoom(z) {
    zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z));
    document.documentElement.style.setProperty('--zoom', zoom);
    if (zoomValueEl) {
      zoomValueEl.textContent = Math.round(zoom * 100) + '%';
    }
  }

  function getZoom() {
    return zoom;
  }

  /** 以视口某点为锚点缩放（鼠标位置不变） */
  function zoomAt(clientX, clientY, factor) {
    const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * factor));
    if (newZoom === zoom) return;

    // 锚点在画布逻辑坐标系中的位置
    const rect = el.getBoundingClientRect();
    const lx = (clientX - rect.left) / zoom;
    const ly = (clientY - rect.top) / zoom;

    setZoom(newZoom);

    // 缩放后让该逻辑点回到原视口位置（调整滚动）
    const newRect = el.getBoundingClientRect();
    stage.scrollLeft += clientX - (newRect.left + lx * newZoom);
    stage.scrollTop += clientY - (newRect.top + ly * newZoom);
  }

  /** 适应窗口 */
  function fit() {
    const pad = 80;
    const sw = stage.clientWidth - pad;
    const sh = stage.clientHeight - pad;
    const s = Math.min(sw / CANVAS_W, sh / CANVAS_H);
    setZoom(s);
    stage.scrollLeft = 0;
    stage.scrollTop = 0;
  }

  /** 重置为 100% */
  function reset() {
    setZoom(1);
  }

  /** 绑定缩放 UI 与滚轮，并初始化适应窗口 */
  function initZoom() {
    const btnIn = document.getElementById('zoomIn');
    const btnOut = document.getElementById('zoomOut');
    const btnFit = document.getElementById('zoomFit');

    // 按钮缩放以画布中心为锚点
    const centerZoom = (factor) => {
      const r = stage.getBoundingClientRect();
      zoomAt(r.left + r.width / 2, r.top + r.height / 2, factor);
    };

    btnIn?.addEventListener('click', () => centerZoom(1.2));
    btnOut?.addEventListener('click', () => centerZoom(1 / 1.2));
    btnFit?.addEventListener('click', fit);
    zoomValueEl?.addEventListener('click', reset);

    // 滚轮缩放（以鼠标位置为锚点）
    stage.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      zoomAt(e.clientX, e.clientY, factor);
    }, { passive: false });

    // 初始适应窗口
    fit();
  }

  /** 设置背景图 */
  function setBackground(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        el.style.backgroundImage = `url(${e.target.result})`;
        el.classList.add('has-content');
        resolve();
      };
      reader.readAsDataURL(file);
    });
  }

  function getElement() {
    return el;
  }

  function getWidth() {
    return CANVAS_W;
  }

  function getHeight() {
    return CANVAS_H;
  }

  function markHasContent() {
    el.classList.add('has-content');
  }

  function hasContent() {
    return el.classList.contains('has-content') || el.children.length > 0;
  }

  return {
    getElement,
    setBackground,
    markHasContent,
    hasContent,
    getZoom,
    fit,
    reset,
    initZoom,
    getWidth,
    getHeight,
  };
})();
