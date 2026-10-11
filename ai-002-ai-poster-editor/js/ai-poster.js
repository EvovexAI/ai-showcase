/* ==============================
   AI 一键生成海报 — ai-poster.js
   输入主题 → AI 返回完整布局 → 生成背景+元素
   ============================== */

const AiPoster = (() => {
  const btn = document.getElementById('btnAiPoster');
  const modal = document.getElementById('aiPosterModal');
  const input = document.getElementById('aiPosterInput');
  const genBtn = document.getElementById('aiPosterBtn');
  const loading = document.getElementById('aiPosterLoading');
  const streamText = document.getElementById('aiPosterStreamText');
  const closeBtn = document.getElementById('aiPosterClose');
  const provider = document.getElementById('aiPosterProvider');

  let controller = null;
  let accumulatedText = '';
  let refImageUrls = [];
  let previewIndex = 0;

  // 参考图
  const refFile = document.getElementById('aiPosterRefFile');
  const refList = document.getElementById('aiPosterRefList');
  const refUploadBtn = document.getElementById('aiPosterRefUploadBtn');
  const refUploadLabel = document.getElementById('aiPosterRefUploadLabel');

  btn?.addEventListener('click', open);
  closeBtn?.addEventListener('click', close);
  genBtn?.addEventListener('click', generate);
  modal?.addEventListener('click', (e) => { if (e.target === modal) close(); });
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) generate();
  });

  refFile?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) uploadRefImage(file);
  });

  function open() {
    if (provider) provider.textContent = Config.getAiPosterName() || '未配置';
    modal.classList.add('open');
    refImageUrls = [];
    renderRefList();
    resetState();
    setTimeout(() => input?.focus(), 100);
  }

  function close() { modal.classList.remove('open'); abort(); }

  function resetState() {
    abort();
    if (input) { input.disabled = false; input.value = ''; }
    if (genBtn) { genBtn.disabled = false; genBtn.textContent = '✨ 一键生成'; }
    if (loading) loading.style.display = 'none';
    if (streamText) { streamText.style.display = 'none'; streamText.textContent = ''; }
    accumulatedText = '';
  }

  function abort() {
    if (controller) { controller.abort(); controller = null; }
  }

  function buildPrompt(topic) {
    const fonts = getFontNames();
    return `你是专业海报设计师。请根据主题设计一张移动端竖版海报（画布 375×812 像素）。

【主题】${topic}
【可用字体】${fonts}
【字号范围】12 ~ 72

请输出严格的 JSON 布局（不要任何其他文字）：

\`\`\`json
{
  "background": "简短描述背景图的视觉设计（颜色/渐变/纹理风格，禁止包含文字），用于 AI 生成背景",
  "elements": [
    {
      "type": "text",
      "left": 数字(px),
      "top": 数字(px),
      "width": 数字(px, 建议200-300),
      "content": "文字内容",
      "fontSize": 数字(px),
      "fontFamily": "从可用字体中选",
      "color": "#HEX",
      "fontWeight": "normal 或 bold",
      "fontStyle": "normal 或 italic",
      "textAlign": "left 或 center 或 right",
      "lineHeight": 1.5,
      "letterSpacing": 0,
      "backgroundColor": null,
      "textDecoration": "none",
      "rotation": 0,
      "role": "title 或 subtitle 或 body 或 cta"
    }
  ]
}
\`\`\`

设计原则：
- 主标题最大最醒目(32-56px, bold)，居中放置(通常 left=37, width=300)
- 副标题/描述稍小(16-24px)，在标题下方
- 可加 CTA 按钮文字或标语(18-24px)
- 留出充足间距，元素之间垂直距离 ≥ 20px
- 整体视觉平衡，信息层级清晰
- background 描述用中文，供 AI 生成背景图
- 最多 5 个文字元素

只返回 JSON，不要任何解释。`;
  }

  function getFontNames() {
    const select = document.getElementById('propFont');
    if (!select) return 'system-ui, sans-serif';
    return Array.from(select.options).map(o => o.value).join(', ');
  }

  async function generate() {
    const topic = input?.value.trim();
    if (!topic) { input?.focus(); return; }

    const cfg = Config.getAiPoster();
    const prompt = buildPrompt(topic);

    if (input) input.disabled = true;
    if (genBtn) { genBtn.disabled = true; genBtn.textContent = '⏳ 生成中…'; }
    if (loading) loading.style.display = '';
    if (streamText) { streamText.style.display = 'none'; streamText.textContent = ''; }
    accumulatedText = '';

    controller = new AbortController();

    try {
      // OpenAI 兼容接口（支持参考图多模态）
      const content = refImageUrls.length > 0
        ? [...refImageUrls.map(url => ({ type: 'image_url', image_url: { url } })), { type: 'text', text: prompt }]
        : prompt;
      accumulatedText = await AiCommon.request({
        cfg, text: content, refImageUrls: null, controller,
        onStream: (c) => { if (streamText) { streamText.style.display = ''; streamText.textContent = c; } },
        buildPromptFn: t => t,
      });

      const layout = extractLayoutJson(accumulatedText);
      if (layout && Array.isArray(layout.elements) && layout.elements.length > 0) {
        await applyLayout(layout, topic);
        close();
      } else {
        if (streamText) streamText.innerHTML = `<span style="color:#dc2626">⚠ 未能解析到完整布局</span>\n\n${escapeHtml(accumulatedText)}`;
        if (streamText) streamText.style.display = '';
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (streamText) streamText.innerHTML = `<span style="color:#dc2626">❌ 生成失败: ${escapeHtml(err.message)}</span>`;
      if (streamText) streamText.style.display = '';
    } finally {
      controller = null;
      if (loading) loading.style.display = 'none';
      if (input) { input.disabled = false; }
      if (genBtn) { genBtn.disabled = false; genBtn.textContent = '✨ 一键生成'; }
    }
  }

  function extractLayoutJson(text) {
    // 尝试从 markdown code block 提取
    const code = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
    if (code) {
      try { return JSON.parse(code[1]); } catch {}
    }
    // 尝试直接解析
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start !== -1 && end > start) {
      try { return JSON.parse(text.slice(start, end + 1)); } catch {}
    }
    return null;
  }

  async function applyLayout(layout, topic) {
    // 1. 先撤销历史（保留当前状态的 snapshot for undo）
    if (window.History) window.History.push();

    // 2. 设置背景
    if (layout.background) {
      try {
        // 用 background 描述生成背景图
        const bgCfg = Config.getAiBg();
        const bgResult = await AiCommon.request({
          cfg: bgCfg,
          text: layout.background,
          refImageUrls: null,
          size: '1125*2436',
          controller: new AbortController(),
          onStream: () => {},
          buildPromptFn: (t) => `请生成一张移动端竖版海报背景图。禁止任何文字。${t}`,
        });
        const bgUrl = AiCommon.extractImageUrl(bgResult) || bgResult;
        if (bgUrl && bgUrl.startsWith('http')) {
          const canvas = Canvas.getElement();
          canvas.style.backgroundImage = `url(${bgUrl})`;
          canvas.classList.add('has-content');
        }
      } catch (e) {
        console.warn('背景生成失败，使用纯色:', e);
      }
    }

    // 3. 清空已有元素并创建新元素
    const canvas = Canvas.getElement();
    canvas.querySelectorAll('.canvas-element').forEach(el => el.remove());

    for (const elData of layout.elements) {
      if (elData.type !== 'text') continue;
      const wrapper = document.createElement('div');
      wrapper.className = 'canvas-element canvas-text';
      wrapper.id = `el-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      wrapper.style.left = (elData.left || 0) + 'px';
      wrapper.style.top = (elData.top || 0) + 'px';
      wrapper.style.width = (elData.width || 250) + 'px';
      wrapper.textContent = elData.content || '';
      wrapper.style.fontSize = (elData.fontSize || 24) + 'px';
      wrapper.style.fontFamily = elData.fontFamily || 'system-ui, sans-serif';
      wrapper.style.color = elData.color || '#000000';
      wrapper.style.fontWeight = elData.fontWeight || 'normal';
      wrapper.style.fontStyle = elData.fontStyle || 'normal';
      wrapper.style.textAlign = elData.textAlign || 'left';
      if (elData.lineHeight) wrapper.style.lineHeight = elData.lineHeight;
      if (elData.letterSpacing) wrapper.style.letterSpacing = elData.letterSpacing + 'px';
      if (elData.backgroundColor) { wrapper.style.backgroundColor = elData.backgroundColor; wrapper.style.padding = '2px 6px'; wrapper.style.borderRadius = '3px'; }
      if (elData.textDecoration && elData.textDecoration !== 'none') wrapper.style.textDecoration = elData.textDecoration;
      if (elData.rotation) wrapper.style.transform = 'rotate(' + elData.rotation + 'deg)';
      wrapper.style.opacity = elData.opacity || 1;
      if (elData.role) wrapper.dataset.role = elData.role;

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
      wrapper.addEventListener('blur', () => wrapper.removeAttribute('contenteditable'));

      Elements.createResizeHandles(wrapper);
      canvas.appendChild(wrapper);
    }

    Elements.select(null);
    Elements.syncIdCounter();
    Canvas.markHasContent();

    if (window.History) window.History.push();
  }

  function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  async function uploadRefImage(file) {
    if (refImageUrls.length >= 4) return;
    refFile.value = '';
    // 一律转 base64，不做服务端上传
    const dataUrl = await new Promise((resolve) => {
      const r = new FileReader(); r.onload = () => resolve(r.result); r.readAsDataURL(file);
    });
    refImageUrls.push(dataUrl);
    renderRefList();
  }

  function removeRefImage(index) {
    refImageUrls.splice(index, 1);
    renderRefList();
  }

  function renderRefList() {
    if (!refList) return;
    refList.innerHTML = '';
    refImageUrls.forEach((url, i) => {
      const thumb = document.createElement('div');
      thumb.className = 'ai-ref-thumb';
      thumb.innerHTML = `<img src="${url}" alt="参考图${i+1}" title="点击预览"><button class="ai-ref-remove" data-index="${i}" title="移除">✕</button>`;
      thumb.querySelector('img').addEventListener('click', () => {
        // reuse global preview modal
        const m = document.getElementById('aiRefPreviewModal');
        const img = document.getElementById('aiRefPreviewImg');
        if (m && img) { img.src = url; m.classList.add('open'); }
      });
      thumb.querySelector('.ai-ref-remove').addEventListener('click', (e) => { e.stopPropagation(); removeRefImage(i); });
      refList.appendChild(thumb);
    });
    const isFull = refImageUrls.length >= 4;
    if (refUploadBtn) refUploadBtn.classList.toggle('disabled', isFull);
    if (refUploadLabel) refUploadLabel.textContent = isFull ? '已满' : refImageUrls.length > 0 ? '+ 更多' : '参考图';
  }

  return { open, close };
})();
