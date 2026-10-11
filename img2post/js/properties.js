/* ==============================
   属性面板 — properties.js
   右侧常驻侧栏，选中元素时填充属性
   ============================== */

const Properties = (() => {
  let currentEl = null;

  // 容器
  const emptyState = document.getElementById('emptyState');
  const propsContainer = document.getElementById('propsContainer');
  const textProps = document.getElementById('textProps');
  const textIdVal = document.getElementById('textIdVal');
  const imageProps = document.getElementById('imageProps');
  const imgIdVal = document.getElementById('imgIdVal');
  const artProps = document.getElementById('artProps');

  // 文字控件
  const propColor = document.getElementById('propColor');
  const propFontSize = document.getElementById('propFontSize');
  const propFont = document.getElementById('propFont');
  const propOpacity = document.getElementById('propOpacity');
  const propLineHeight = document.getElementById('propLineHeight');
  const propLetterSpacing = document.getElementById('propLetterSpacing');
  const propBgColor = document.getElementById('propBgColor');
  const propBgOpacity = document.getElementById('propBgOpacity');
  const propWidth = document.getElementById('propWidth');
  const propHeight = document.getElementById('propHeight');
  const propAngle = document.getElementById('propAngle');
  const colorVal = document.getElementById('colorVal');
  const fontSizeVal = document.getElementById('fontSizeVal');
  const opacityVal = document.getElementById('opacityVal');
  const lineHeightVal = document.getElementById('lineHeightVal');
  const letterSpacingVal = document.getElementById('letterSpacingVal');
  const bgOpacityVal = document.getElementById('bgOpacityVal');
  const angleVal = document.getElementById('angleVal');

  // 样式按钮
  const btnBold = document.getElementById('btnBold');
  const btnItalic = document.getElementById('btnItalic');
  const btnUnderline = document.getElementById('btnUnderline');
  const btnStrikethrough = document.getElementById('btnStrikethrough');
  const btnFlip = document.getElementById('btnFlip');
  const btnAlignLeft = document.getElementById('btnAlignLeft');
  const btnAlignCenter = document.getElementById('btnAlignCenter');
  const btnAlignRight = document.getElementById('btnAlignRight');

  // 艺术效果开关
  const propShadow = document.getElementById('propShadow');
  const propStroke = document.getElementById('propStroke');
  const propEmboss = document.getElementById('propEmboss');
  const propGlow = document.getElementById('propGlow');

  // 艺术子选项容器
  const shadowOptions = document.getElementById('shadowOptions');
  const strokeOptions = document.getElementById('strokeOptions');
  const glowOptions = document.getElementById('glowOptions');
  const glowColor = document.getElementById('glowColor');
  const glowIntensity = document.getElementById('glowIntensity');

  // 艺术子控件
  const shadowX = document.getElementById('shadowX');
  const shadowY = document.getElementById('shadowY');
  const shadowBlur = document.getElementById('shadowBlur');
  const shadowColor = document.getElementById('shadowColor');
  const strokeWidth = document.getElementById('strokeWidth');
  const strokeColor = document.getElementById('strokeColor');

  // 关闭 = 取消选择
  document.getElementById('panelClose').addEventListener('click', () => {
    Elements.select(null);
  });

  // ===== 显示属性 =====

  function show(dom) {
    currentEl = dom;
    if (!dom) {
      emptyState.style.display = '';
      propsContainer.style.display = 'none';
      return;
    }
    emptyState.style.display = 'none';
    propsContainer.style.display = '';

    const isText = dom.classList.contains('canvas-text');
    const isImage = dom.classList.contains('canvas-image');
    textProps.style.display = isText ? '' : 'none';
    imageProps.style.display = isImage ? '' : 'none';
    artProps.style.display = isText ? '' : 'none';

    if (isText) {
      textIdVal.textContent = dom.id;
      textIdVal.onclick = () => {
        navigator.clipboard?.writeText(dom.id);
        textIdVal.style.color = 'var(--accent)';
        setTimeout(() => textIdVal.style.color = '', 800);
      };
      loadTextProps();
    }
    if (isImage) {
      imgIdVal.textContent = dom.id;
      imgIdVal.onclick = () => {
        navigator.clipboard?.writeText(dom.id);
        imgIdVal.style.color = 'var(--accent)';
        setTimeout(() => imgIdVal.style.color = '', 800);
      };
    }
  }

  // ===== 文字属性 =====

  function loadTextProps() {
    if (!currentEl) return;
    const cs = getComputedStyle(currentEl);

    const hex = toHex(cs.color);
    propColor.value = hex;
    colorVal.textContent = hex.toUpperCase();

    const fs = parseInt(cs.fontSize) || 24;
    propFontSize.value = fs;
    fontSizeVal.textContent = fs;

    const op = Math.round((parseFloat(cs.opacity) || 1) * 100);
    propOpacity.value = op;
    opacityVal.textContent = op;

    // 宽高
    propWidth.value = currentEl.offsetWidth;
    propHeight.value = currentEl.offsetHeight;
    if (propAngle) {
      propAngle.value = getRotation(currentEl);
      if (angleVal) angleVal.textContent = propAngle.value + '\u00B0';
    }

    // 行距
    const lh = parseFloat(currentEl.style.lineHeight) || 0;
    if (propLineHeight) propLineHeight.value = Math.round(lh * 10);
    if (lineHeightVal) lineHeightVal.textContent = lh || '\u9ED8\u8BA4';

    // 字距
    const ls = parseFloat(currentEl.style.letterSpacing) || 0;
    if (propLetterSpacing) propLetterSpacing.value = ls;
    if (letterSpacingVal) letterSpacingVal.textContent = ls;

    // 背景色
    const bgStyle = currentEl.style.backgroundColor || '';
    const rgbaMatch = bgStyle.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (rgbaMatch && propBgColor) {
      propBgColor.value = '#' + [rgbaMatch[1], rgbaMatch[2], rgbaMatch[3]]
        .map(x => parseInt(x).toString(16).padStart(2, '0')).join('');
      const aMatch = bgStyle.match(/[\d.]+\)$/);
      const alpha = aMatch ? parseFloat(aMatch[0]) : 1;
      if (propBgOpacity) propBgOpacity.value = Math.round(alpha * 100);
      if (bgOpacityVal) bgOpacityVal.textContent = Math.round(alpha * 100);
    } else {
      if (propBgColor) propBgColor.value = '#ffff00';
      if (propBgOpacity) propBgOpacity.value = 0;
      if (bgOpacityVal) bgOpacityVal.textContent = 0;
    }

    btnBold.classList.toggle('active', cs.fontWeight === 'bold' || parseInt(cs.fontWeight) >= 700);
    btnItalic.classList.toggle('active', cs.fontStyle === 'italic');
    if (btnUnderline) btnUnderline.classList.toggle('active', cs.textDecoration.includes('underline'));
    if (btnFlip) btnFlip.classList.toggle('active', (currentEl.style.transform || '').includes('scaleX(-1)'));
    if (btnStrikethrough) btnStrikethrough.classList.toggle('active', cs.textDecoration.includes('line-through'));

    const ta = cs.textAlign;
    btnAlignLeft.classList.toggle('active', ta === 'left' || ta === 'start');
    btnAlignCenter.classList.toggle('active', ta === 'center');
    btnAlignRight.classList.toggle('active', ta === 'right' || ta === 'end');

    syncArtToggles();
  }

  function syncArtToggles() {
    if (!currentEl) return;
    const hasShadow = !!currentEl.style.textShadow;
    const hasStroke = !!currentEl.style.webkitTextStroke && currentEl.style.webkitTextStroke !== 'initial';

    propShadow.checked = hasShadow;
    propStroke.checked = hasStroke;
    propEmboss.checked = false;
    const hasGlow = !!currentEl.dataset.glow;
    if (propGlow) propGlow.checked = hasGlow;
    if (glowOptions) glowOptions.style.display = hasGlow ? "" : "none";

    shadowOptions.style.display = hasShadow ? '' : 'none';
    strokeOptions.style.display = hasStroke ? '' : 'none';
  }

  function applyArtEffects() {
    if (!currentEl) return;
    const shadows = [];

    if (propShadow.checked) {
      shadowOptions.style.display = '';
      shadows.push(`${shadowX.value}px ${shadowY.value}px ${shadowBlur.value}px ${shadowColor.value}`);
    } else {
      shadowOptions.style.display = 'none';
    }

    if (propEmboss.checked) {
      shadows.push('1px 1px 0 #ccc', '-1px -1px 0 #555');
    }

    currentEl.style.textShadow = shadows.length ? shadows.join(', ') : '';

    // 霓虹发光
    if (propGlow && propGlow.checked) {
      if (glowOptions) glowOptions.style.display = '';
      const gc = glowColor ? glowColor.value : '#00ffff';
      const gi = glowIntensity ? parseFloat(glowIntensity.value) || 2 : 2;
      const glows = [];
      for (let i = 0; i < 3; i++) {
        glows.push('0 0 ' + (gi * 4 * (i + 1)) + 'px ' + gc);
      }
      currentEl.style.textShadow = (currentEl.style.textShadow ? currentEl.style.textShadow + ', ' : '') + glows.join(', ');
      currentEl.dataset.glow = '1';
    } else {
      if (glowOptions) glowOptions.style.display = 'none';
      delete currentEl.dataset.glow;
    }

    if (propStroke.checked) {
      strokeOptions.style.display = '';
      currentEl.style.webkitTextStroke = `${strokeWidth.value}px ${strokeColor.value}`;
    } else {
      strokeOptions.style.display = 'none';
      currentEl.style.webkitTextStroke = '';
    }
  }

  function applyBgColor() {
    if (!currentEl) return;
    const op = parseInt(propBgOpacity?.value) || 0;
    if (op > 0 && propBgColor) {
      const hex = propBgColor.value;
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      currentEl.style.backgroundColor = `rgba(${r},${g},${b},${op / 100})`;
      currentEl.style.padding = '2px 6px';
      currentEl.style.borderRadius = '3px';
    } else {
      currentEl.style.backgroundColor = '';
      currentEl.style.padding = '';
      currentEl.style.borderRadius = '';
    }
    if (bgOpacityVal) bgOpacityVal.textContent = op;
  }

  // ===== 工具函数 =====

  function toHex(rgb) {
    if (!rgb) return '#000000';
    if (rgb.startsWith('#')) return rgb;
    const m = rgb.match(/\d+/g);
    if (!m || m.length < 3) return '#000000';
    return '#' + m.slice(0, 3).map(x => parseInt(x).toString(16).padStart(2, '0')).join('');
  }

  // ===== 事件绑定 =====

  // 宽高
  propWidth?.addEventListener('input', () => {
    if (!currentEl) return;
    currentEl.style.width = parseInt(propWidth.value) + 'px';
  });
  propHeight?.addEventListener('input', () => {
    if (!currentEl) return;
    currentEl.style.height = parseInt(propHeight.value) + 'px';
  });

  // 旋转角度
  propAngle?.addEventListener('input', () => {
    if (!currentEl) return;
    const deg = parseInt(propAngle.value) || 0;
    if (typeof setRotation === 'function') setRotation(currentEl, deg);
    if (angleVal) angleVal.textContent = deg + '\u00B0';
  });

  // 文字
  propColor.addEventListener('input', () => {
    if (!currentEl) return;
    currentEl.style.color = propColor.value;
    colorVal.textContent = propColor.value.toUpperCase();
  });

  propFontSize.addEventListener('input', () => {
    if (!currentEl) return;
    currentEl.style.fontSize = propFontSize.value + 'px';
    fontSizeVal.textContent = propFontSize.value;
  });

  propFont.addEventListener('change', () => {
    if (!currentEl) return;
    currentEl.style.fontFamily = propFont.value;
  });

  propOpacity.addEventListener('input', () => {
    if (!currentEl) return;
    currentEl.style.opacity = propOpacity.value / 100;
    opacityVal.textContent = propOpacity.value;
  });

  btnBold.addEventListener('click', () => {
    if (!currentEl) return;
    const on = btnBold.classList.toggle('active');
    currentEl.style.fontWeight = on ? 'bold' : 'normal';
  });

  btnItalic.addEventListener('click', () => {
    if (!currentEl) return;
    const on = btnItalic.classList.toggle('active');
    currentEl.style.fontStyle = on ? 'italic' : 'normal';
  });

  btnUnderline?.addEventListener('click', () => {
    if (!currentEl) return;
    const on = btnUnderline.classList.toggle('active');
    const d = currentEl.style.textDecoration || '';
    const hasStrike = d.includes('line-through');
    currentEl.style.textDecoration = on
      ? (hasStrike ? 'underline line-through' : 'underline')
      : (hasStrike ? 'line-through' : 'none');
  });

  btnFlip?.addEventListener('click', () => {
    if (!currentEl) return;
    const t = currentEl.style.transform || '';
    if (t.includes('scaleX(-1)')) {
      currentEl.style.transform = t.replace(/\s*scaleX\(-1\)\s*/g, '').trim() || '';
      btnFlip.classList.remove('active');
    } else {
      currentEl.style.transform = (t ? t + ' ' : '') + 'scaleX(-1)';
      btnFlip.classList.add('active');
    }
  });

btnStrikethrough?.addEventListener('click', () => {
    if (!currentEl) return;
    const on = btnStrikethrough.classList.toggle('active');
    const d = currentEl.style.textDecoration || '';
    const hasUnder = d.includes('underline');
    currentEl.style.textDecoration = on
      ? (hasUnder ? 'underline line-through' : 'line-through')
      : (hasUnder ? 'underline' : 'none');
  });

  propLineHeight?.addEventListener('input', () => {
    if (!currentEl) return;
    const v = parseFloat(propLineHeight.value) || 0;
    currentEl.style.lineHeight = v > 0 ? (v / 10) : '';
    if (lineHeightVal) lineHeightVal.textContent = v || '\u9ED8\u8BA4';
  });

  propLetterSpacing?.addEventListener('input', () => {
    if (!currentEl) return;
    const v = parseFloat(propLetterSpacing.value) || 0;
    currentEl.style.letterSpacing = v + 'px';
    if (letterSpacingVal) letterSpacingVal.textContent = v;
  });

  propBgColor?.addEventListener('input', () => { applyBgColor(); });
  propBgOpacity?.addEventListener('input', () => { applyBgColor(); });

  // 对齐
  [
    { btn: btnAlignLeft, align: 'left' },
    { btn: btnAlignCenter, align: 'center' },
    { btn: btnAlignRight, align: 'right' },
  ].forEach(({ btn, align }) => {
    btn.addEventListener('click', () => {
      if (!currentEl) return;
      [btnAlignLeft, btnAlignCenter, btnAlignRight].forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentEl.style.textAlign = align;
    });
  });

  // 艺术效果
  [propShadow, propStroke, propEmboss, propGlow].forEach(ctrl => {
    ctrl?.addEventListener('change', applyArtEffects);
  });
  [
    shadowX, shadowY, shadowBlur, shadowColor,
    strokeWidth, strokeColor, glowColor, glowIntensity,
  ].forEach(ctrl => {
    ctrl.addEventListener('input', applyArtEffects);
  });

  /** 拖拽缩放时实时刷新宽高（由 Drag 模块调用） */
  function updateSize(w, h) {
    if (!propWidth || !propHeight) return;
    propWidth.value = Math.round(w);
    propHeight.value = Math.round(h);
  }

  /** 旋转时实时刷新角度（由 Drag 模块调用） */
  function updateRotation(deg) {
    if (propAngle) propAngle.value = deg;
  }

  return { show, updateSize, updateRotation };
})();

window.Properties = Properties;

// 属性面板变化时推入撤销历史
document.getElementById('sidebarBody')?.addEventListener('input', () => {
  if (window.History) window.History.push();
});
document.getElementById('sidebarBody')?.addEventListener('change', () => {
  if (window.History) window.History.push();
});
