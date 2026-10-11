/* ==============================
   布局导入导出 — layout.js
   JSON 格式保存/加载海报布局
   ============================== */

const Layout = (() => {
  const SCHEMA_VERSION = 1;
  const btnImport = document.getElementById('btnImportLayout');
  const btnExport = document.getElementById('btnExportLayout');
  const fileInput = document.getElementById('fileImportLayout');

  btnImport.addEventListener('click', () => fileInput.click());
  btnExport.addEventListener('click', exportLayout);
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) importLayout(file);
    fileInput.value = '';
  });

  /** 序列化当前画布为 JSON */
  function serialize() {
    const canvas = Canvas.getElement();
    const data = {
      version: SCHEMA_VERSION,
      canvas: {
        background: canvas.style.backgroundImage || null
      },
      elements: []
    };

    const els = canvas.querySelectorAll('.canvas-element');
    els.forEach(el => {
      if (el.classList.contains('canvas-text')) {
        data.elements.push(serializeText(el));
      } else if (el.classList.contains('canvas-image')) {
        data.elements.push(serializeImage(el));
      }
    });

    return data;
  }

  function serializeText(el) {
    const cs = getComputedStyle(el);
    return {
      type: 'text',
      id: el.id,
      left: parseInt(el.style.left) || 0,
      top: parseInt(el.style.top) || 0,
      width: parseInt(el.style.width) || 0,
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
      },
      role: el.dataset.role || null,
      rotation: parseRotation(el.style.transform),
      flip: (el.style.transform || '').includes('scaleX(-1)'),
      effects: {
        shadow: el.style.textShadow || null,
        stroke: (el.style.webkitTextStroke && el.style.webkitTextStroke !== 'initial') ? el.style.webkitTextStroke : null,
        glow: el.dataset.glow ? el.style.textShadow || null : null
      }
    };
  }

  function serializeImage(el) {
    const img = el.querySelector('img');
    const cs = img ? getComputedStyle(img) : {};
    return {
      type: 'image',
      id: el.id,
      left: parseInt(el.style.left) || 0,
      top: parseInt(el.style.top) || 0,
      width: parseInt(el.style.width) || 0,
      height: parseInt(el.style.height) || 0,
      src: img ? img.src : '',
      style: {
        objectFit: cs.objectFit || 'cover',
        objectPosition: cs.objectPosition || '50% 50%',
        opacity: parseFloat(el.style.opacity) || 1,
        borderRadius: el.style.borderRadius || null,
        clipPath: (el.style.clipPath && el.style.clipPath !== 'none') ? el.style.clipPath : null
      },
      role: el.dataset.role || null,
      rotation: parseRotation(el.style.transform),
      flip: (el.style.transform || '').includes('scaleX(-1)'),
    };
  }

  /** 导出 JSON 文件 */
  function exportLayout() {
    const data = serialize();
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `layout_${Date.now()}.json`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }

  /** 导入 JSON 文件 */
  async function importLayout(file) {
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      if (!data.version || data.version !== SCHEMA_VERSION) {
        alert('不支持的布局文件格式');
        return;
      }

      if (!Array.isArray(data.elements)) {
        alert('布局文件格式错误');
        return;
      }

      // 确认覆盖
      const hasContent = Canvas.hasContent();
      if (hasContent && !confirm('导入布局将覆盖当前内容，确定继续？')) return;

      // 清空画布
      const canvas = Canvas.getElement();
      canvas.querySelectorAll('.canvas-element').forEach(el => el.remove());
      canvas.style.backgroundImage = '';
      canvas.classList.remove('has-content');

      // 恢复背景
      if (data.canvas && data.canvas.background) {
        let bg = data.canvas.background;
        // 提取远程URL并转换
        const urlMatch = bg.match(/url\(["']?([^"')]+)["']?\)/);
        if (urlMatch && urlMatch[1].startsWith('http') && typeof AiCommon !== 'undefined') {
          try { 
            const dataUrl = await AiCommon.loadImageAsDataUrl(urlMatch[1]);
            bg = 'url(' + dataUrl + ')'; 
          } catch {}
        }
        canvas.style.backgroundImage = bg;
        canvas.classList.add('has-content');
      }

      // 恢复元素
      for (const elData of data.elements) {
        if (elData.type === 'text') {
          await deserializeText(canvas, elData);
        } else if (elData.type === 'image') {
          await deserializeImage(canvas, elData);
        }
      }

      // 取消选中
      Elements.select(null);
    } catch (err) {
      console.error('导入失败:', err);
      alert('导入失败：' + err.message);
    }
  }

  async function deserializeText(canvas, data) {
    const wrapper = document.createElement('div');
    wrapper.className = 'canvas-element canvas-text';
    wrapper.id = data.id || `el-${Date.now()}`;
    wrapper.style.left = data.left + 'px';
    wrapper.style.top = data.top + 'px';
    wrapper.style.width = data.width + 'px';
    wrapper.style.opacity = data.style.opacity;
    wrapper.textContent = data.content;

    wrapper.style.fontSize = data.style.fontSize + 'px';
    wrapper.style.fontFamily = data.style.fontFamily;
    wrapper.style.color = data.style.color;
    wrapper.style.fontWeight = data.style.fontWeight;
    wrapper.style.fontStyle = data.style.fontStyle;
    wrapper.style.textAlign = data.style.textAlign;

    if (data.style.lineHeight) wrapper.style.lineHeight = data.style.lineHeight;
    if (data.style.letterSpacing) wrapper.style.letterSpacing = data.style.letterSpacing + 'px';
    if (data.style.backgroundColor) {
      wrapper.style.backgroundColor = data.style.backgroundColor;
      wrapper.style.padding = '2px 6px';
      wrapper.style.borderRadius = '3px';
    }
    if (data.style.textDecoration && data.style.textDecoration !== 'none') {
      wrapper.style.textDecoration = data.style.textDecoration;
    }

    // 双击编辑
    wrapper.addEventListener('dblclick', (e) => {
      e.stopPropagation();
      wrapper.setAttribute('contenteditable', 'true');
      wrapper.focus();
      const range = document.createRange();
      range.selectNodeContents(wrapper);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    });
    wrapper.addEventListener('blur', () => {
      wrapper.removeAttribute('contenteditable');
    });

    // 缩放控制点（三向：右/下/角）
    Elements.createResizeHandles(wrapper);

    if (data.effects.shadow) wrapper.style.textShadow = data.effects.shadow;
    if (data.effects.stroke) wrapper.style.webkitTextStroke = data.effects.stroke;
    if (data.effects.glow) { wrapper.style.textShadow = data.effects.glow; wrapper.dataset.glow = '1'; }

    if (data.role) wrapper.dataset.role = data.role;

    // 旋转角度
    if (data.rotation || data.flip) { let t = ''; if (data.rotation) t += 'rotate(' + data.rotation + 'deg)'; if (data.flip) t += (t ? ' ' : '') + 'scaleX(-1)'; wrapper.style.transform = t; }

    canvas.appendChild(wrapper);
  }

  async function deserializeImage(canvas, data) {
    if (!data.src) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'canvas-element canvas-image';
    wrapper.id = data.id || `el-${Date.now()}`;
    wrapper.style.left = data.left + 'px';
    wrapper.style.top = data.top + 'px';
    wrapper.style.width = data.width + 'px';
    wrapper.style.height = data.height + 'px';
    wrapper.style.opacity = data.style.opacity;

    const img = document.createElement('img');
    let src = data.src;
    if (src.startsWith('http') && typeof AiCommon !== 'undefined') {
      try { src = await AiCommon.loadImageAsDataUrl(src); } catch {}
    }
    img.src = src;
    img.draggable = false;
    img.style.objectFit = data.style.objectFit || 'cover';
    img.style.objectPosition = data.style.objectPosition || '50% 50%';

    if (data.style.borderRadius) wrapper.style.borderRadius = data.style.borderRadius;
    if (data.style.clipPath) wrapper.style.clipPath = data.style.clipPath;

    wrapper.appendChild(img);

    // 缩放控制点
    const resizeHandle = document.createElement('div');
    resizeHandle.className = 'resize-handle';
    wrapper.appendChild(resizeHandle);

    if (data.role) wrapper.dataset.role = data.role;

    if (data.rotation || data.flip) { let t = ''; if (data.rotation) t += 'rotate(' + data.rotation + 'deg)'; if (data.flip) t += (t ? ' ' : '') + 'scaleX(-1)'; wrapper.style.transform = t; }

    canvas.appendChild(wrapper);
  }

  /** 应用布局数据到画布（用于 AI 优化等场景） */
  async function applyLayoutData(data) {
    if (!data || !Array.isArray(data.elements)) return;

    const canvas = Canvas.getElement();

    // 清空画布
    canvas.querySelectorAll('.canvas-element').forEach(el => el.remove());
    canvas.style.backgroundImage = '';
    canvas.classList.remove('has-content');

    // 恢复背景
    if (data.canvas?.background) {
      let bg = data.canvas.background;
      const urlMatch = bg.match(/url\(["']?([^"')]+)["']?\)/);
      if (urlMatch && urlMatch[1].startsWith('http') && typeof AiCommon !== 'undefined') {
        try { 
          const dataUrl = await AiCommon.loadImageAsDataUrl(urlMatch[1]);
          bg = 'url(' + dataUrl + ')'; 
        } catch {}
      }
      canvas.style.backgroundImage = bg;
      canvas.classList.add('has-content');
    }

    // 恢复元素
    for (const elData of data.elements) {
      if (elData.type === 'text') {
        await deserializeText(canvas, elData);
      } else if (elData.type === 'image') {
        await deserializeImage(canvas, elData);
      }
    }

    Elements.select(null);
    // 同步计数器，避免 AI 添加元素后 id 冲突
    Elements.syncIdCounter();
  }

  /** 从 CSS transform 中提取旋转角度 */
  function parseRotation(transform) {
    if (!transform) return 0;
    const m = transform.match(/rotate\(([-\d.]+)deg\)/);
    return m ? parseFloat(m[1]) : 0;
  }

  return { exportLayout, importLayout, applyLayoutData, serialize };
})();
