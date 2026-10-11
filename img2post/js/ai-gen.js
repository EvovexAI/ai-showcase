/* ==============================
   AI 生成背景 — ai-gen.js
   对接 Config 配置的 Provider（通义万象 / OpenAI 兼容）
   ============================== */

const AiGen = (() => {

  // DOM
  const btnAiGen = document.getElementById('btnAiGen');
  const aiGenModal = document.getElementById('aiGenModal');
  const aiGenInput = document.getElementById('aiGenInput');
  const aiGenBtn = document.getElementById('aiGenBtn');
  const aiGenLoading = document.getElementById('aiGenLoading');
  const aiGenStreamText = document.getElementById('aiGenStreamText');
  const aiGenPreview = document.getElementById('aiGenPreview');
  const aiGenPreviewImg = document.getElementById('aiGenPreviewImg');
  const aiGenConfirm = document.getElementById('aiGenConfirm');
  const aiGenClose = document.getElementById('aiGenClose');

  // 参考图
  const aiRefFile = document.getElementById('aiRefFile');
  const aiRefList = document.getElementById('aiRefList');
  const aiRefUploadBtn = document.getElementById('aiRefUploadBtn');
  const aiRefUploadLabel = document.getElementById('aiRefUploadLabel');

  // 参考图预览弹窗
  const aiRefPreviewModal = document.getElementById('aiRefPreviewModal');
  const aiRefPreviewImg = document.getElementById('aiRefPreviewImg');
  const aiRefPreviewClose = document.getElementById('aiRefPreviewClose');
  const aiRefPrev = document.getElementById('aiRefPrev');
  const aiRefNext = document.getElementById('aiRefNext');
  const aiRefCounter = document.getElementById('aiRefCounter');

  // Provider 标识
  const aiGenProvider = document.getElementById('aiGenProvider');

  let controller = null;
  let accumulatedText = '';
  let refImageUrls = [];
  let previewIndex = 0;

  // 绑定事件
  btnAiGen.addEventListener('click', openDialog);
  aiGenClose.addEventListener('click', closeDialog);
  aiGenConfirm.addEventListener('click', applyImage);

  aiRefFile.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) uploadRefImage(file);
  });
  aiRefPreviewClose.addEventListener('click', closeRefPreview);
  aiRefPrev.addEventListener('click', () => navigateRefPreview(-1));
  aiRefNext.addEventListener('click', () => navigateRefPreview(1));
  aiRefPreviewModal.addEventListener('click', (e) => {
    if (e.target === aiRefPreviewModal) closeRefPreview();
  });

  aiGenBtn.addEventListener('click', generate);
  aiGenInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) generate();
  });

  /** 更新弹窗内 Provider 标识 */
  function updateProviderLabel() {
    if (!aiGenProvider) return;
    const cfg = Config.getAiBg();
    aiGenProvider.textContent = cfg && cfg.name ? cfg.name : '未知';
  }

  /** 打开弹窗 */
  function openDialog() {
    aiGenModal.classList.add('open');
    resetState();
    aiGenInput.value = '';
    refImageUrls = [];
    aiRefFile.value = '';

    // 自动将当前画布背景图添加为参考图
    const canvas = Canvas.getElement();
    const bgImage = canvas.style.backgroundImage;
    if (bgImage && bgImage !== 'none') {
      const match = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
      if (match) {
        refImageUrls.push(match[1]);
      }
    }

    renderRefList();
    updateProviderLabel();
    setTimeout(() => aiGenInput.focus(), 100);
  }

  function closeDialog() {
    aiGenModal.classList.remove('open');
    abort();
  }

  function resetState() {
    abort();
    aiGenInput.disabled = false;
    aiGenBtn.disabled = false;
    aiGenBtn.textContent = '✨ 开始生成';
    aiGenLoading.style.display = 'none';
    aiGenStreamText.style.display = 'none';
    aiGenStreamText.textContent = '';
    aiGenPreview.style.display = 'none';
    aiGenConfirm.style.display = 'none';
    accumulatedText = '';
  }

  function abort() {
    if (controller) {
      controller.abort();
      controller = null;
    }
  }

  /** 背景生成提示词（OpenAI 兼容流式） */
  function buildOpenAIPrompt(userText, refCount) {
    const refDesc = buildRefDescription(refCount);
    return `请按以下要求生成一张背景图：

【用户描述】
${userText}
${refDesc}
【禁止事项 — 最高优先级】
❌ 绝对禁止在背景上生成任何文字、字母、数字、标志、标语
❌ 禁止生成可辨识的单词、品牌名、Logo
❌ 仅允许纯视觉元素：颜色、渐变、纹理、图案、几何图形、装饰性花纹

【生成要求】
1. 尺寸：1125 × 2436 像素（移动端竖版海报，3x 高清图，宽高比约 9:19.5）
2. 构图：上方和中间预留充足的空白区域用于后续添加文字
3. 风格：与用户描述匹配的高品质视觉设计
4. 色彩：鲜明、有层次感
5. 用途：移动端活动海报背景（文字由编辑器后续添加）

请直接返回生成的图片链接。`;
  }

  /** 通义万象背景生成提示词 */
  function buildTongyiBgPrompt(userText, refCount) {
    const refDesc = buildRefDescription(refCount);
    return `生成一张移动端竖版海报背景图。极其重要：必须是一张纯视觉背景，绝对不能包含任何文字！

${userText}
${refDesc}
核心约束（如违反则生成失败）：
❌ 严禁任何文字、字母、数字、标志、标语、品牌名
✅ 只允许纯视觉设计：颜色、渐变、纹理、图案、几何装饰

要求：
- 尺寸：1125×2436 高清
- 上方和中间留出大面积空白供后续文字排版
- 风格与用户描述匹配的高品质视觉设计
- 色彩鲜明有层次感
- 用途：移动端活动海报背景（文字由编辑器添加）`;
  }

  /** 构建参考图说明 */
  function buildRefDescription(refCount) {
    if (refCount === 0) return '';
    return '【参考图】上传的图片是当前海报背景，请基于此风格/色调生成新背景。\n';
  }
  async function generate() {
    const text = aiGenInput.value.trim();
    if (!text) { aiGenInput.focus(); return; }

    const cfg = Config.getAiBg();

    aiGenInput.disabled = true;
    aiGenBtn.disabled = true;
    aiGenBtn.textContent = '⏳ 生成中...';
    aiGenLoading.style.display = '';
    aiGenPreview.style.display = 'none';
    aiGenConfirm.style.display = 'none';
    accumulatedText = '';

    controller = new AbortController();

    const refCount = refImageUrls.length;
    // 通义万象用精简提示词，OpenAI 兼容走 buildPromptFn
    const promptText = cfg.type === 'dashscope' ? buildTongyiBgPrompt(text, refCount) : text;

    try {
      const result = await AiCommon.request({
        cfg,
        text: promptText,
        refImageUrls: refImageUrls.length > 0 ? refImageUrls : null,
        size: '1125*2436',
        controller,
        onStream: (content) => {
          accumulatedText = content;
          aiGenStreamText.style.display = '';
          aiGenStreamText.textContent = content;
          aiGenStreamText.parentElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
        },
        buildPromptFn: (t) => buildOpenAIPrompt(t, refCount),
      });

      let imageUrl = null;

      if (cfg.type === 'dashscope') {
        // DashScope 直接返回的是 imageUrl（通过 onStream 传入的文本中提取）
        imageUrl = AiCommon.extractImageUrl(accumulatedText) || result;
        // result 是 accumulateText，尝试提取 URL
        if (!imageUrl) imageUrl = result;
      } else {
        imageUrl = AiCommon.extractImageUrl(accumulatedText);
      }

      if (imageUrl && imageUrl.startsWith('http')) {
        showPreview(imageUrl);
      } else {
        aiGenStreamText.innerHTML = `<span style="color:#dc2626">⚠ 未能解析到图片链接</span>\n\n${AiCommon.escapeHtml(accumulatedText)}`;
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      aiGenStreamText.style.display = '';
      aiGenStreamText.innerHTML = `<span style="color:#dc2626">❌ 生成失败: ${AiCommon.escapeHtml(err.message)}</span>`;
    } finally {
      controller = null;
      aiGenLoading.style.display = 'none';
      aiGenInput.disabled = false;
      aiGenBtn.disabled = false;
      aiGenBtn.textContent = '✨ 重新生成';
    }
  }

  function showPreview(url) {
    aiGenPreviewImg.src = url;
    aiGenPreview.style.display = '';
    aiGenConfirm.style.display = '';
    aiGenStreamText.textContent = '';
    aiGenBtn.textContent = '✨ 重新生成';
  }

  async function applyImage() {
    const src = aiGenPreviewImg.src;
    if (!src) return;

    try {
      const dataUrl = await AiCommon.loadImageAsDataUrl(src);
      const canvas = Canvas.getElement();
      canvas.style.backgroundImage = `url(${dataUrl})`;
      canvas.classList.add('has-content');
      closeDialog();
    } catch (err) {
      const canvas = Canvas.getElement();
      canvas.style.backgroundImage = `url(${src})`;
      canvas.classList.add('has-content');
      closeDialog();
    }
  }

  async function uploadRefImage(file) {
    if (refImageUrls.length >= 4) return;
    aiRefFile.value = '';

    // 统一转 base64 data URL，不做服务端上传
    const dataUrl = await fileToBase64(file);
    refImageUrls.push(dataUrl);
    renderRefList();
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function removeRefImage(index) {
    refImageUrls.splice(index, 1);
    renderRefList();
  }

  function renderRefList() {
    aiRefList.innerHTML = '';
    refImageUrls.forEach((url, i) => {
      const thumb = document.createElement('div');
      thumb.className = 'ai-ref-thumb';
      thumb.innerHTML = `<img src="${url}" alt="参考图${i + 1}" title="点击预览"><button class="ai-ref-remove" data-index="${i}" title="移除">✕</button>`;
      thumb.querySelector('img').addEventListener('click', () => openRefPreview(i));
      thumb.querySelector('.ai-ref-remove').addEventListener('click', (e) => {
        e.stopPropagation();
        removeRefImage(i);
      });
      aiRefList.appendChild(thumb);
    });

    const isFull = refImageUrls.length >= 4;
    aiRefUploadBtn.classList.toggle('disabled', isFull);
    aiRefUploadLabel.textContent = isFull ? '已满' : refImageUrls.length > 0 ? '+ 更多' : '参考图';
  }

  function openRefPreview(index) {
    previewIndex = index;
    updateRefPreview();
    aiRefPreviewModal.classList.add('open');
  }

  function closeRefPreview() {
    aiRefPreviewModal.classList.remove('open');
  }

  function navigateRefPreview(dir) {
    if (refImageUrls.length <= 1) return;
    previewIndex = (previewIndex + dir + refImageUrls.length) % refImageUrls.length;
    updateRefPreview();
  }

  function updateRefPreview() {
    aiRefPreviewImg.src = refImageUrls[previewIndex];
    aiRefCounter.textContent = `${previewIndex + 1} / ${refImageUrls.length}`;
    aiRefPrev.style.display = refImageUrls.length > 1 ? '' : 'none';
    aiRefNext.style.display = refImageUrls.length > 1 ? '' : 'none';
  }

  return { openDialog, closeDialog, updateProviderLabel };
})();
