/* ==============================
   拖拽交互 — drag.js
   Pointer Events 统一处理鼠标和触屏
   文字元素支持三向缩放：右边缘/下边缘/右下角
   对齐吸附线：拖拽时自动吸附到相邻元素边缘 + 画布边界
   ============================== */

const Drag = (() => {
  let activeEl = null;
  let isDragging = false;
  let isResizing = false;
  let isRotating = false;
  let resizeDir = 'se';
  let startX = 0, startY = 0;
  let elStartX = 0, elStartY = 0;
  let elStartW = 0, elStartH = 0;
  let elStartAngle = 0;

  const SNAP_THRESHOLD = 6; // px，吸附阈值
  const RESIZE_HANDLES = ['resize-handle', 'resize-handle-e', 'resize-handle-s'];

  // 吸附参考线 DOM
  let snapLineH = null;
  let snapLineV = null;

  function ensureSnapLines() {
    const canvas = Canvas.getElement();
    if (!snapLineH) {
      snapLineH = document.createElement('div');
      snapLineH.className = 'snap-line snap-line-h';
      canvas.appendChild(snapLineH);
    }
    if (!snapLineV) {
      snapLineV = document.createElement('div');
      snapLineV.className = 'snap-line snap-line-v';
      canvas.appendChild(snapLineV);
    }
  }

  function hideSnapLines() {
    if (snapLineH) snapLineH.style.display = 'none';
    if (snapLineV) snapLineV.style.display = 'none';
  }

  function showSnapLineH(y) {
    ensureSnapLines();
    snapLineH.style.display = '';
    snapLineH.style.top = y + 'px';
  }

  function showSnapLineV(x) {
    ensureSnapLines();
    snapLineV.style.display = '';
    snapLineV.style.left = x + 'px';
  }

  function init() {
    const canvas = Canvas.getElement();
    canvas.addEventListener('pointerdown', onPointerDown);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', onPointerUp);
  }

  function onPointerDown(e) {
    const target = e.target;
    const canvas = Canvas.getElement();

    if (target === canvas) {
      Elements.select(null);
      return;
    }

    const el = target.closest('.canvas-element');
    if (!el) return;
    if (el.getAttribute('contenteditable') === 'true') return;

    e.preventDefault();
    e.stopPropagation();

    for (const cls of RESIZE_HANDLES) {
      if (target.classList.contains(cls)) {
        isResizing = true;
        resizeDir = cls === 'resize-handle-e' ? 'e' : cls === 'resize-handle-s' ? 's' : 'se';
        activeEl = el;
        startX = e.clientX;
        startY = e.clientY;
        elStartW = el.offsetWidth;
        elStartH = el.offsetHeight;
        el.setPointerCapture(e.pointerId);
        return;
      }
    }

    // 旋转手柄
    if (target.classList.contains('rotate-handle')) {
      isRotating = true;
      activeEl = el;
      startX = e.clientX;
      startY = e.clientY;
      elStartAngle = getRotation(el);
      el.setPointerCapture(e.pointerId);
      return;
    }

    Elements.select(el.id);

    isDragging = true;
    activeEl = el;
    startX = e.clientX;
    startY = e.clientY;
    elStartX = parseInt(el.style.left) || 0;
    elStartY = parseInt(el.style.top) || 0;
    el.setPointerCapture(e.pointerId);
  }

  /** 获取画布上所有其他元素的边缘集合 */
  function getSnapTargets(movingEl) {
    const canvas = Canvas.getElement();
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    const targets = [];

    // 画布边界
    targets.push({ type: 'boundary', x: 0 });
    targets.push({ type: 'boundary', x: cw });
    targets.push({ type: 'boundary', y: 0 });
    targets.push({ type: 'boundary', y: ch });

    // 画布水平/垂直中线
    targets.push({ type: 'center', x: Math.round(cw / 2) });
    targets.push({ type: 'center', y: Math.round(ch / 2) });

    // 其他元素边缘
    canvas.querySelectorAll('.canvas-element').forEach(el => {
      if (el === movingEl) return;
      const l = parseInt(el.style.left) || 0;
      const t = parseInt(el.style.top) || 0;
      const w = el.offsetWidth || 0;
      const h = el.offsetHeight || 0;
      if (w > 0 && h > 0) {
        targets.push({ type: 'element', x: l });           // 左边缘
        targets.push({ type: 'element', x: l + w });       // 右边缘
        targets.push({ type: 'element', y: t });           // 上边缘
        targets.push({ type: 'element', y: t + h });       // 下边缘
        targets.push({ type: 'element', x: l + Math.round(w / 2) }); // 水平中
        targets.push({ type: 'element', y: t + Math.round(h / 2) }); // 垂直中
      }
    });

    return targets;
  }

  /** 计算吸附后的坐标 */
  function applySnap(elX, elY, elW, elH, movingEl) {
    const targets = getSnapTargets(movingEl);
    let snappedX = null, snappedY = null;
    let snapH = null, snapV = null;

    // 移动元素的关键点
    const mx_center = elX + Math.round(elW / 2);
    const my_center = elY + Math.round(elH / 2);

    for (const t of targets) {
      if (t.x !== undefined) {
        // 左边缘吸附
        let dist = Math.abs(elX - t.x);
        if (dist < SNAP_THRESHOLD) { snappedX = t.x; snapV = t.x; }
        // 右边缘吸附
        dist = Math.abs(elX + elW - t.x);
        if (dist < SNAP_THRESHOLD) { snappedX = t.x - elW; snapV = t.x; }
        // 水平中线吸附
        dist = Math.abs(mx_center - t.x);
        if (dist < SNAP_THRESHOLD) { snappedX = t.x - Math.round(elW / 2); snapV = t.x; }
      }
      if (t.y !== undefined) {
        // 上边缘吸附
        let dist = Math.abs(elY - t.y);
        if (dist < SNAP_THRESHOLD) { snappedY = t.y; snapH = t.y; }
        // 下边缘吸附
        dist = Math.abs(elY + elH - t.y);
        if (dist < SNAP_THRESHOLD) { snappedY = t.y - elH; snapH = t.y; }
        // 垂直中线吸附
        dist = Math.abs(my_center - t.y);
        if (dist < SNAP_THRESHOLD) { snappedY = t.y - Math.round(elH / 2); snapH = t.y; }
      }
    }

    return {
      x: snappedX !== null ? snappedX : elX,
      y: snappedY !== null ? snappedY : elY,
      snapH,
      snapV,
    };
  }

  function onPointerMove(e) {
    if (!activeEl) return;
    e.preventDefault();

    const z = Canvas.getZoom();
    const dx = (e.clientX - startX) / z;
    const dy = (e.clientY - startY) / z;

    const canvas = Canvas.getElement();
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;

    if (isResizing) {
      hideSnapLines();
      let newW, newH;
      if (resizeDir === 'e') {
        newW = Math.max(20, elStartW + dx);
        newH = elStartH;
      } else if (resizeDir === 's') {
        newW = elStartW;
        newH = Math.max(20, elStartH + dy);
      } else {
        const ratio = elStartW / elStartH;
        newW = Math.max(20, elStartW + dx);
        newH = newW / ratio;
      }

      const elLeft = parseInt(activeEl.style.left) || 0;
      const elTop = parseInt(activeEl.style.top) || 0;
      if (elLeft + newW > cw) newW = cw - elLeft;
      if (resizeDir !== 'e' && elTop + newH > ch) newH = ch - elTop;

      activeEl.style.width = newW + 'px';
      activeEl.style.height = newH + 'px';
      if (window.Properties) window.Properties.updateSize(newW, newH);

    } else if (isRotating) {
      hideSnapLines();
      const rect = activeEl.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const angle = Math.atan2(e.clientY - cy, e.clientX - cx) * (180 / Math.PI) + 90;
      // 吸附到 15° 的倍数
      const snapped = Math.round(angle / 15) * 15;
      setRotation(activeEl, snapped);
      if (window.Properties) window.Properties.updateRotation(snapped);

    } else if (isDragging) {
      let newX = elStartX + dx;
      let newY = elStartY + dy;
      const elW = activeEl.offsetWidth;
      const elH = activeEl.offsetHeight;

      // 边界限制
      newX = Math.max(0, Math.min(newX, cw - elW));
      newY = Math.max(0, Math.min(newY, ch - elH));

      // 吸附计算
      const snapped = applySnap(newX, newY, elW, elH, activeEl);
      newX = snapped.x;
      newY = snapped.y;

      // 显示吸附线
      if (snapped.snapH !== null) showSnapLineH(snapped.snapH);
      else if (snapLineH) snapLineH.style.display = 'none';

      if (snapped.snapV !== null) showSnapLineV(snapped.snapV);
      else if (snapLineV) snapLineV.style.display = 'none';

      activeEl.style.left = newX + 'px';
      activeEl.style.top = newY + 'px';
    }
  }

  function onPointerUp(e) {
    hideSnapLines();
    if (activeEl) {
      try { activeEl.releasePointerCapture(e.pointerId); } catch (err) {}
    }
    const hadAction = isDragging || isResizing || isRotating;
    isDragging = false;
    isResizing = false;
    isRotating = false;
    activeEl = null;
    if (hadAction && window.History) window.History.push();
  }

  return { init };
})();

/** 从 CSS transform 读取旋转角度 */
function getRotation(el) {
  const t = el.style.transform || '';
  const m = t.match(/rotate\(([-\d.]+)deg\)/);
  return m ? parseFloat(m[1]) : 0;
}

/** 设置 CSS 旋转角度 */
function setRotation(el, deg) {
  const t = el.style.transform || '';
  // 保留其他 transform（如果有的话），替换 rotate
  const cleaned = t.replace(/\s*rotate\([^)]*\)\s*/g, '').trim();
  if (deg === 0 || deg === 360 || deg === -360) {
    el.style.transform = cleaned;
  } else {
    el.style.transform = cleaned ? `${cleaned} rotate(${deg}deg)` : `rotate(${deg}deg)`;
  }
}
