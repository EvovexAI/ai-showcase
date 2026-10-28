/* ==============================
   应用入口 — app.js
   绑定按钮事件，初始化
   ============================== */

document.addEventListener('DOMContentLoaded', () => {
  // 初始化字体下拉框（从 FONT_LIST 动态生成）
  initFontSelect();
  // 初始化拖拽
  Drag.init();
  // 初始化编辑区缩放（含初始适应窗口）
  Canvas.initZoom();

  // ===== 工具栏按钮 =====

  // 上传背景
  const fileBg = document.getElementById('fileBg');
  document.getElementById('btnBg').addEventListener('click', () => fileBg.click());
  fileBg.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      Canvas.setBackground(file);
    }
    e.target.value = ''; // 重置，允许重复选择同一文件
  });

  // 添加文字
  document.getElementById('btnText').addEventListener('click', () => {
    Elements.addText();
  });

  // 添加图片
  const fileImage = document.getElementById('fileImage');
  document.getElementById('btnImage').addEventListener('click', () => fileImage.click());
  fileImage.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      Elements.addImage(file);
    }
    e.target.value = '';
  });

  // 导出
  document.getElementById('btnExport').addEventListener('click', () => {
    Export.open();
  });

  // 撤销/重做按钮
  document.getElementById('btnUndo').addEventListener('click', () => {
    if (window.History) window.History.undo();
  });
  document.getElementById('btnRedo').addEventListener('click', () => {
    if (window.History) window.History.redo();
  });

  // ===== 设置弹窗 =====
  initSettings();

  // ===== 属性面板按钮 =====

  // 层级上移
  document.getElementById('btnUp').addEventListener('click', () => {
    const id = Elements.getSelectedId();
    if (id) { Elements.bringForward(id); if (window.History) window.History.push(); }
  });

  // 层级下移
  document.getElementById('btnDown').addEventListener('click', () => {
    const id = Elements.getSelectedId();
    if (id) { Elements.sendBackward(id); if (window.History) window.History.push(); }
  });

  // 置顶
  document.getElementById('btnFront').addEventListener('click', () => {
    const id = Elements.getSelectedId();
    if (id) { Elements.bringToFront(id); if (window.History) window.History.push(); }
  });

  // 置底
  document.getElementById('btnBack').addEventListener('click', () => {
    const id = Elements.getSelectedId();
    if (id) { Elements.sendToBack(id); if (window.History) window.History.push(); }
  });

  // 删除
  document.getElementById('btnDelete').addEventListener('click', () => {
    const id = Elements.getSelectedId();
    if (id) {
      Elements.remove(id);
    }
  });

  // ===== 键盘快捷键 =====
  document.addEventListener('keydown', (e) => {
    // Delete / Backspace 删除选中元素
    if ((e.key === 'Delete' || e.key === 'Backspace') && Elements.getSelectedId()) {
      // 编辑模式下不删除，任何输入框内不删除
      if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      e.preventDefault();
      Elements.remove(Elements.getSelectedId());
    }

    // Ctrl+C 复制选中元素
    if ((e.ctrlKey || e.metaKey) && e.key === 'c' && Elements.getSelectedId()) {
      if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      e.preventDefault();
      Elements.copySelected();
    }

    // Ctrl+V 粘贴
    if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
      if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      e.preventDefault();
      Elements.paste();
    }

    // Ctrl+Z 撤销
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'z') {
      if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      e.preventDefault();
      if (window.History) window.History.undo();
    }

    // Ctrl+Y 或 Ctrl+Shift+Z 重做
    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
      if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      e.preventDefault();
      if (window.History) window.History.redo();
    }

    // Ctrl/Cmd + 0 适应窗口
    if ((e.ctrlKey || e.metaKey) && e.key === '0') {
      e.preventDefault();
      Canvas.fit();
    }

    // Escape 取消选中（任何输入框内不处理）
    if (e.key === 'Escape') {
      if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      Elements.select(null);
    }
  });

  // ===== demo 调试模式（?demo=1）：自动添加文字并展开艺术效果，用于截图验证布局 =====
  if (new URLSearchParams(location.search).get('demo') === '1') {
    Elements.addText('双击编辑文字');
    setTimeout(() => {
      const el = document.querySelector('.canvas-text');
      if (el) {
        Elements.select(el.id);
        // 展开阴影子选项（最宽的艺术参数行：4 个控件）
        const sh = document.getElementById('propShadow');
        sh.checked = true;
        sh.dispatchEvent(new Event('change'));
      }
    }, 300);
  }

  // ===== 设置弹窗逻辑 =====
  function initSettings() {
    const modal = document.getElementById('settingsModal');
    const btnSettings = document.getElementById('btnSettings');
    if (!btnSettings || !modal) { console.warn('Settings elements missing'); return; }
    const btnClose = document.getElementById('settingsClose');
    const btnReset = document.getElementById('btnResetConfig');

    // Per-module element IDs
    const mods = {
      bg:  { type:'setBgType', base:'setBgBase', key:'setBgKey', model:'setBgModel', modelRow:'setBgModelRow' },
      img: { type:'setImgType',base:'setImgBase',key:'setImgKey',model:'setImgModel',modelRow:'setImgModelRow' },
      opt: { type:'setOptType',base:'setOptBase',key:'setOptKey',model:'setOptModel',modelRow:'setOptModelRow' },
      poster: { type:'setPosterType',base:'setPosterBase',key:'setPosterKey',model:'setPosterModel',modelRow:'setPosterModelRow' },
    };

    // Cache DOM refs
    const $ = {};
    for (const [k, v] of Object.entries(mods)) {
      $[k] = {};
      for (const [f, id] of Object.entries(v)) $[k][f] = document.getElementById(id);
    }

    btnSettings.addEventListener('click', () => { refreshUI(); modal.classList.add('open'); });
    btnClose.addEventListener('click', () => { saveAll(); modal.classList.remove('open'); });
    modal.addEventListener('click', (e) => { if (e.target === modal) { saveAll(); modal.classList.remove('open'); } });

    $.bg.type.addEventListener('change', () => onTypeChange('bg'));
    $.img.type.addEventListener('change', () => onTypeChange('img'));
    $.opt.type.addEventListener('change', () => onTypeChange('opt'));
    $.poster.type.addEventListener('change', () => onTypeChange('poster'));

    btnReset.addEventListener('click', () => {
      if (confirm('确定恢复所有配置为默认值？')) { Config.resetAll(); refreshUI(); }
    });

    function onTypeChange(key) {
      const tpl = Config.getTemplate($[key].type.value);
      if (tpl) {
        $[key].base.value = tpl.apiBase || ''; $[key].key.value = tpl.apiKey || '';
        if ($[key].model) $[key].model.value = tpl.model || '';
      }
      applyUI(key);
    }

    function applyUI(key) {
      const tpl = Config.getTemplate($[key].type.value);
      const isArk = tpl && tpl.type === 'ark';
      const isOa = tpl && tpl.type === 'openai';
      if ($[key].modelRow) $[key].modelRow.style.display = (isArk || isOa) ? '' : 'none';
    }

    function saveModule(key) {
      const tpl = Config.getTemplate($[key].type.value);
      const fields = { name: (tpl && tpl.name) || '', type: (tpl && tpl.type) || '', apiBase: $[key].base.value, apiKey: $[key].key.value };
      if ($[key].model) fields.model = $[key].model.value;
      if (key === 'bg') Config.updateAiBg(fields);
      else if (key === 'img') Config.updateAiImage(fields);
      else if (key === 'opt') Config.updateAiOptimize(fields);
      else if (key === 'poster') Config.updateAiPoster(fields);
    }

    function saveAll() { saveModule('bg'); saveModule('img'); saveModule('opt'); saveModule('poster'); }

    function refreshUI() {
      render('bg', Config.getAiBg()); render('img', Config.getAiImage()); render('opt', Config.getAiOptimize()); render('poster', Config.getAiPoster());
    }

    function render(key, cfg) {
      if (!cfg) return;
      const typeMap = { ark:'ark', openai:'newapi' };
      $[key].type.value = typeMap[cfg.type] || cfg.type;
      $[key].base.value = cfg.apiBase || ''; $[key].key.value = cfg.apiKey || '';
      if ($[key].model) $[key].model.value = cfg.model || '';
      applyUI(key);
    }
    Config.load();
  }
});
