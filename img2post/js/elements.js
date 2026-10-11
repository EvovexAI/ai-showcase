/* ==============================
   元素管理 — elements.js
   创建、删除、层级控制
   ============================== */

// 降级字体列表（当 queryLocalFonts 不可用时使用）
const FALLBACK_FONTS = [
  { family: "system-ui, sans-serif", fullName: "系统默认" },
  { family: "'PingFang SC', 'Microsoft YaHei', sans-serif", fullName: "苹方/雅黑" },
  { family: "'SimSun', '宋体', serif", fullName: "宋体" },
  { family: "'KaiTi', '楷体', serif", fullName: "楷体" },
  { family: "'SimHei', '黑体', sans-serif", fullName: "黑体" },
  { family: "'FangSong', '仿宋', serif", fullName: "仿宋" },
  { family: "monospace", fullName: "等宽" },
  { family: "cursive", fullName: "手写" },
];

let systemFonts = null; // 缓存系统字体

/** 获取可用字体（优先系统字体，降级 fallback） */
async function getAvailableFonts() {
  if (systemFonts) return systemFonts;

  if ('queryLocalFonts' in window) {
    try {
      const fonts = await window.queryLocalFonts();
      // 去重并按名称排序
      const seen = new Set();
      systemFonts = fonts
        .filter(f => {
          if (seen.has(f.family)) return false;
          seen.add(f.family);
          return true;
        })
        .map(f => ({ family: f.family, fullName: f.fullName || f.family }))
        .sort((a, b) => a.fullName.localeCompare(b.fullName, 'zh'));
      return systemFonts;
    } catch (e) {
      console.warn('queryLocalFonts 失败，使用降级字体列表:', e);
    }
  }

  systemFonts = FALLBACK_FONTS.map(f => ({ family: f.family, fullName: f.fullName }));
  return systemFonts;
}

/** 初始化字体下拉框 */
async function initFontSelect() {
  const select = document.getElementById('propFont');
  if (!select) return;

  const fonts = await getAvailableFonts();
  select.innerHTML = fonts.map(f =>
    `<option value="${f.family}">${f.fullName}</option>`
  ).join('');
}

const Elements = (() => {
  const canvas = Canvas.getElement();
  let elements = [];
  let selectedId = null;
  let idCounter = 0;
  let imgIdCounter = 0;

  /** 创建文字元素 */
  function addText(text = '双击编辑文字') {
    const id = `el-${++idCounter}`;
    const wrapper = document.createElement('div');
    wrapper.className = 'canvas-element canvas-text';
    wrapper.id = id;

    const cw = canvas.clientWidth || 375;
    const ch = canvas.clientHeight || 812;
    const w = Math.round(cw * 0.6);
    wrapper.style.width = w + 'px';
    wrapper.style.left = Math.round((cw - w) / 2) + 'px';
    wrapper.style.top = Math.round(ch * 0.42) + 'px';
    wrapper.style.fontSize = '24px';
    wrapper.style.color = '#000000';
    wrapper.style.fontFamily = "system-ui, sans-serif";
    wrapper.textContent = text;

    // 缩放控制点（三向：右/下/角）
    createResizeHandles(wrapper);

    // 双击编辑
    wrapper.addEventListener('dblclick', (e) => {
      e.stopPropagation();
      wrapper.setAttribute('contenteditable', 'true');
      wrapper.focus();
      // 选中所有文字
      const range = document.createRange();
      range.selectNodeContents(wrapper);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    });

    wrapper.addEventListener('blur', () => {
      wrapper.removeAttribute('contenteditable');
    });

    canvas.appendChild(wrapper);
    const el = { id, type: 'text', dom: wrapper };
    elements.push(el);
    select(id);
    Canvas.markHasContent();
    if (window.History) window.History.push();
    return el;
  }

  /** 创建图片元素 */
  function addImage(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const id = `el-img-${++imgIdCounter}`;
        const wrapper = document.createElement('div');
        wrapper.className = 'canvas-element canvas-image';
        wrapper.id = id;
        const cw = canvas.clientWidth || 375;
        const ch = canvas.clientHeight || 812;
        wrapper.style.width = Math.round(cw * 0.5) + 'px';
        wrapper.style.left = Math.round(cw * 0.25) + 'px';
        wrapper.style.top = Math.round(ch * 0.3) + 'px';

        const img = document.createElement('img');
        img.src = e.target.result;
        img.draggable = false;

        // 图片加载后按比例设置高度
        img.onload = () => {
          const ratio = img.naturalHeight / img.naturalWidth;
          wrapper.style.height = Math.round(wrapper.offsetWidth * ratio) + 'px';
        };

        wrapper.appendChild(img);

        // 缩放控制点
        const resizeHandle = document.createElement('div');
        resizeHandle.className = 'resize-handle';
        wrapper.appendChild(resizeHandle);

        // 旋转手柄
        const rotHandle = document.createElement('div');
        rotHandle.className = 'rotate-handle';
        rotHandle.title = '旋转';
        wrapper.appendChild(rotHandle);

        canvas.appendChild(wrapper);
        const el = { id, type: 'image', dom: wrapper };
        elements.push(el);
        select(id);
        Canvas.markHasContent();
        if (window.History) window.History.push();
        resolve(el);
      };
      reader.readAsDataURL(file);
    });
  }

  /** 选中元素 */
  function select(id) {
    // 取消之前的选中
    if (selectedId) {
      const prev = getElement(selectedId);
      if (prev) prev.classList.remove('selected');
    }
    selectedId = id;
    if (id) {
      const el = getElement(id);
      if (el) el.classList.add('selected');
    }
    // 通知属性面板
    if (window.Properties) {
      window.Properties.show(id ? getElement(id) : null);
    }
  }

  /** 获取当前选中的元素 ID */
  function getSelectedId() {
    return selectedId;
  }

  /** 根据 ID 获取 DOM */
  function getElement(id) {
    return document.getElementById(id);
  }

  /** 删除元素 */
  function remove(id) {
    const dom = getElement(id);
    if (dom) dom.remove();
    elements = elements.filter(e => e.id !== id);
    if (selectedId === id) {
      selectedId = null;
      if (window.Properties) {
        window.Properties.show(null);
      }
    }
    if (window.History) window.History.push();
  }

  /** 获取画布上所有元素按 z-index 排序的列表 */
  function getZOrdered() {
    const canvas = Canvas.getElement();
    const els = Array.from(canvas.querySelectorAll('.canvas-element'));
    els.sort((a, b) => (parseInt(a.style.zIndex) || 1) - (parseInt(b.style.zIndex) || 1));
    return els;
  }

  /** 置顶 */
  function bringToFront(id) {
    const dom = getElement(id);
    if (!dom) return;
    const maxZ = getZOrdered().reduce((max, el) => Math.max(max, parseInt(el.style.zIndex) || 1), 1);
    dom.style.zIndex = maxZ + 1;
  }

  /** 置底 */
  function sendToBack(id) {
    const dom = getElement(id);
    if (!dom) return;
    const minZ = getZOrdered().reduce((min, el) => Math.min(min, parseInt(el.style.zIndex) || 1), Infinity);
    dom.style.zIndex = Math.max(0, minZ - 1);
  }

  /** 上移一层（与上层元素交换 z-index） */
  function bringForward(id) {
    const dom = getElement(id);
    if (!dom) return;
    const ordered = getZOrdered();
    const idx = ordered.indexOf(dom);
    if (idx === -1 || idx === ordered.length - 1) return; // 已是最前
    const curZ = parseInt(dom.style.zIndex) || 1;
    const above = ordered[idx + 1];
    const aboveZ = parseInt(above.style.zIndex) || 1;
    dom.style.zIndex = aboveZ;
    above.style.zIndex = curZ;
  }

  /** 下移一层（与下层元素交换 z-index） */
  function sendBackward(id) {
    const dom = getElement(id);
    if (!dom) return;
    const ordered = getZOrdered();
    const idx = ordered.indexOf(dom);
    if (idx <= 0) return; // 已是最末
    const curZ = parseInt(dom.style.zIndex) || 1;
    const below = ordered[idx - 1];
    const belowZ = parseInt(below.style.zIndex) || 1;
    dom.style.zIndex = belowZ;
    below.style.zIndex = curZ;
  }

  /** 获取元素信息 */
  function get(id) {
    return elements.find(e => e.id === id);
  }

  /** 获取所有元素 */
  function getAll() {
    return elements;
  }

  /** 同步 idCounter，避免 AI 添加元素后与手动添加冲突 */
  function syncIdCounter() {
    let maxText = 0;
    let maxImg = 0;
    const canvas = Canvas.getElement();
    canvas.querySelectorAll('.canvas-element').forEach(el => {
      if (el.classList.contains('canvas-text')) {
        const m = el.id.match(/^el-(\d+)$/);
        if (m) maxText = Math.max(maxText, parseInt(m[1]));
      } else if (el.classList.contains('canvas-image')) {
        const m = el.id.match(/^el-img-(\d+)$/);
        if (m) maxImg = Math.max(maxImg, parseInt(m[1]));
      }
    });
    if (maxText >= idCounter) idCounter = maxText;
    if (maxImg >= imgIdCounter) imgIdCounter = maxImg;
  }

  // 剪贴板
  let clipboardItem = null;

  /** 复制选中元素到剪贴板 */
  function copySelected() {
    const id = selectedId;
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;

    if (el.classList.contains('canvas-text')) {
      const cs = getComputedStyle(el);
      clipboardItem = {
        type: 'text',
        left: parseInt(el.style.left) || 0,
        top: parseInt(el.style.top) || 0,
        width: parseInt(el.style.width) || 0,
        height: el.style.height ? parseInt(el.style.height) : undefined,
        content: el.textContent || '',
        style: {
          fontSize: parseInt(cs.fontSize) || 24,
          fontFamily: cs.fontFamily || '',
          color: cs.color || '#000000',
          fontWeight: cs.fontWeight || 'normal',
          fontStyle: cs.fontStyle || 'normal',
          textAlign: cs.textAlign || 'left',
          opacity: parseFloat(el.style.opacity) || 1,
          lineHeight: parseFloat(el.style.lineHeight) || 0,
          letterSpacing: parseFloat(el.style.letterSpacing) || 0,
          backgroundColor: el.style.backgroundColor || null,
          textDecoration: el.style.textDecoration || null,
          flip: (el.style.transform || '').includes('scaleX(-1)'),
        },
        effects: {
          shadow: el.style.textShadow || null,
          stroke: (el.style.webkitTextStroke && el.style.webkitTextStroke !== 'initial') ? el.style.webkitTextStroke : null,
          glow: el.dataset.glow ? (el.style.textShadow || null) : null,
        },
        role: el.dataset.role || null,
      };
    } else if (el.classList.contains('canvas-image')) {
      const img = el.querySelector('img');
      clipboardItem = {
        type: 'image',
        left: parseInt(el.style.left) || 0,
        top: parseInt(el.style.top) || 0,
        width: parseInt(el.style.width) || 0,
        height: parseInt(el.style.height) || 0,
        src: img ? img.src : '',
        style: {
          objectFit: img ? (getComputedStyle(img).objectFit || 'cover') : 'cover',
          opacity: parseFloat(el.style.opacity) || 1,
          borderRadius: el.style.borderRadius || null,
          clipPath: (el.style.clipPath && el.style.clipPath !== 'none') ? el.style.clipPath : null,
        },
        role: el.dataset.role || null,
      };
    }
  }

  /** 粘贴剪贴板元素 */
  function paste() {
    if (!clipboardItem) return;

    if (clipboardItem.type === 'text') {
      addText(clipboardItem.content);
      const newEl = document.getElementById(selectedId);
      if (!newEl) return;

      // 覆盖样式和位置（偏移 20px 避免完全重叠）
      newEl.style.left = (clipboardItem.left + 20) + 'px';
      newEl.style.top = (clipboardItem.top + 20) + 'px';
      newEl.style.width = clipboardItem.width + 'px';
      if (clipboardItem.height) newEl.style.height = clipboardItem.height + 'px';
      else newEl.style.height = '';

      const s = clipboardItem.style;
      newEl.style.fontSize = s.fontSize + 'px';
      newEl.style.fontFamily = s.fontFamily;
      newEl.style.color = s.color;
      newEl.style.fontWeight = s.fontWeight;
      newEl.style.fontStyle = s.fontStyle;
      newEl.style.textAlign = s.textAlign;
      newEl.style.opacity = s.opacity;

      if (s.lineHeight) newEl.style.lineHeight = s.lineHeight;
      if (s.letterSpacing) newEl.style.letterSpacing = s.letterSpacing + 'px';
      if (s.backgroundColor) {
        newEl.style.backgroundColor = s.backgroundColor;
        newEl.style.padding = '2px 6px';
        newEl.style.borderRadius = '3px';
      }
      if (s.textDecoration && s.textDecoration !== 'none') {
        newEl.style.textDecoration = s.textDecoration;
      }
      if (s.flip) { newEl.style.transform = (newEl.style.transform || '') + ' scaleX(-1)'; }
      if (clipboardItem.effects?.glow) {
        newEl.style.textShadow = clipboardItem.effects.glow;
        newEl.dataset.glow = '1';
      }

      if (clipboardItem.effects.shadow) newEl.style.textShadow = clipboardItem.effects.shadow;
      if (clipboardItem.effects.stroke) newEl.style.webkitTextStroke = clipboardItem.effects.stroke;
      if (clipboardItem.role) newEl.dataset.role = clipboardItem.role;

      // 通知属性面板
      if (window.Properties) window.Properties.show(newEl);
    } else if (clipboardItem.type === 'image') {
      const src = clipboardItem.src;
      if (!src) return;

      // 用 fetch 转 Blob 然后 addImage
      fetch(src)
        .then(r => r.blob())
        .then(blob => {
          const file = new File([blob], 'clipboard-image.png', { type: blob.type || 'image/png' });
          addImage(file).then(() => applyImageClipboard());
        })
        .catch(() => { /* 跨域等原因失败，静默 */ });
      return; // 异步流程不阻塞
    }
  }

  /** 对刚粘贴的图片应用剪贴板样式 */
  function applyImageClipboard() {
    const newEl = document.getElementById(selectedId);
    if (!newEl || !clipboardItem || clipboardItem.type !== 'image') return;

    newEl.style.left = (clipboardItem.left + 20) + 'px';
    newEl.style.top = (clipboardItem.top + 20) + 'px';
    newEl.style.width = clipboardItem.width + 'px';
    newEl.style.opacity = clipboardItem.style.opacity;

    const img = newEl.querySelector('img');
    if (img) {
      img.style.objectFit = clipboardItem.style.objectFit;
      if (clipboardItem.style.borderRadius) newEl.style.borderRadius = clipboardItem.style.borderRadius;
      if (clipboardItem.style.clipPath) newEl.style.clipPath = clipboardItem.style.clipPath;
    }
    if (clipboardItem.role) newEl.dataset.role = clipboardItem.role;

    if (window.Properties) window.Properties.show(newEl);
  }

  /** 为文字元素创建三向缩放手柄 */
  function createResizeHandles(wrapper) {
    const dirs = [
      { cls: 'resize-handle-e',  title: '宽度' },
      { cls: 'resize-handle-s',  title: '高度' },
      { cls: 'resize-handle',    title: '缩放' },
    ];
    dirs.forEach(({ cls, title }) => {
      const h = document.createElement('div');
      h.className = cls;
      if (title) h.title = title;
      wrapper.appendChild(h);
    });

    // 旋转手柄
    const rotHandle = document.createElement('div');
    rotHandle.className = 'rotate-handle';
    rotHandle.title = '旋转';
    wrapper.appendChild(rotHandle);
  }

  return {
    addText,
    addImage,
    select,
    getSelectedId,
    getElement,
    remove,
    bringToFront,
    sendToBack,
    bringForward,
    sendBackward,
    get,
    getAll,
    syncIdCounter,
    createResizeHandles,
    copySelected,
    paste,
  };
})();
