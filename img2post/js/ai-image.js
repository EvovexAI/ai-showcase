/* ==============================
   AI 生成图片 — ai-image.js
   对接 Config 配置的 Provider（通义万象 / OpenAI 兼容）
   绿幕生成 → 客户端抠绿 → 透明 PNG
   ============================== */

const AiImage = (() => {
  const GREEN_THRESHOLD = 160;
  const GREEN_RATIO = 2;

  // DOM
  const btnAiImage = document.getElementById('btnAiImage');
  const aiImageModal = document.getElementById('aiImageModal');
  const aiImgInput = document.getElementById('aiImgInput');
  const aiImgBtn = document.getElementById('aiImgBtn');
  const aiImgLoading = document.getElementById('aiImgLoading');
  const aiImgStreamText = document.getElementById('aiImgStreamText');
  const aiImgPreview = document.getElementById('aiImgPreview');
  const aiImgPreviewImg = document.getElementById('aiImgPreviewImg');
  const aiImgConfirm = document.getElementById('aiImgConfirm');
  const aiImageClose = document.getElementById('aiImageClose');

  // 参考图
  const aiImgRefFile = document.getElementById('aiImgRefFile');
  const aiImgRefList = document.getElementById('aiImgRefList');
  const aiImgRefUploadBtn = document.getElementById('aiImgRefUploadBtn');
  const aiImgRefUploadLabel = document.getElementById('aiImgRefUploadLabel');

  // 参考图预览
  const aiRefPreviewModal = document.getElementById('aiRefPreviewModal');
  const aiRefPreviewImg = document.getElementById('aiRefPreviewImg');
  const aiRefPreviewClose = document.getElementById('aiRefPreviewClose');
  const aiRefPrev = document.getElementById('aiRefPrev');
  const aiRefNext = document.getElementById('aiRefNext');
  const aiRefCounter = document.getElementById('aiRefCounter');

  // Provider 标识
  const aiImgProvider = document.getElementById('aiImgProvider');

  let controller = null;
  let accumulatedText = '';
  let refImageUrls = [];
  let previewIndex = 0;

  // 事件绑定
  btnAiImage.addEventListener('click', openDialog);
  aiImageClose.addEventListener('click', closeDialog);
  aiImgConfirm.addEventListener('click', applyImage);

  aiImgRefFile.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) uploadRefImage(file);
  });
  aiRefPreviewClose.addEventListener('click', () => closeRefPreview());
  aiRefPrev.addEventListener('click', () => navigateRefPreview(-1));
  aiRefNext.addEventListener('click', () => navigateRefPreview(1));
  aiRefPreviewModal.addEventListener('click', (e) => {
    if (e.target === aiRefPreviewModal) closeRefPreview();
  });

  aiImgBtn.addEventListener('click', generate);
  aiImgInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) generate();
  });

  function updateProviderLabel() {
    if (!aiImgProvider) return;
    const cfg = Config.getAiImage();
    aiImgProvider.textContent = cfg && cfg.name ? cfg.name : '未知';
  }

  function openDialog() {
    aiImageModal.classList.add('open');
    resetState();
    aiImgInput.value = '';
    refImageUrls = [];
    aiImgRefFile.value = '';
    renderRefList();
    updateProviderLabel();
    setTimeout(() => aiImgInput.focus(), 100);
  }

  function closeDialog() {
    aiImageModal.classList.remove('open');
    abort();
  }

  function resetState() {
    abort();
    aiImgInput.disabled = false;
    aiImgBtn.disabled = false;
    aiImgBtn.textContent = '✨ 开始生成';
    aiImgLoading.style.display = 'none';
    aiImgStreamText.style.display = 'none';
    aiImgStreamText.textContent = '';
    aiImgPreview.style.display = 'none';
    aiImgConfirm.style.display = 'none';
    accumulatedText = '';
  }

  function abort() {
    if (controller) { controller.abort(); controller = null; }
  }

  /** 绿幕素材生成提示词 */
  function buildGreenScreenPrompt(userText) {
    return `请生成一张图片素材：

【用户描述】
${userText}

【生成要求】
1. 背景色必须为纯绿色 #00C800（绿幕色），不可使用其他颜色
2. 主体清晰突出，边缘干净
3. 风格：与用户描述匹配
4. 用途：海报素材（需要透明背景，绿幕用于后期抠图）

请直接返回生成的图片链接。`;
  }

  async function generate() {
    const text = aiImgInput.value.trim();
    if (!text) { aiImgInput.focus(); return; }

    const cfg = Config.getAiImage();

    aiImgInput.disabled = true;
    aiImgBtn.disabled = true;
    aiImgBtn.textContent = '⏳ 生成中...';
    aiImgLoading.style.display = '';
    aiImgPreview.style.display = 'none';
    aiImgConfirm.style.display = 'none';
    accumulatedText = '';

    controller = new AbortController();

    // 绿幕提示词统一走 buildGreenScreenPrompt
    const promptText = cfg.type === 'dashscope'
      ? buildGreenScreenPrompt(text).replace('请直接返回生成的图片链接。', '').trim()
      : text;

    try {
      const result = await AiCommon.request({
        cfg,
        text: promptText,
        refImageUrls: refImageUrls.length > 0 ? refImageUrls : null,
        size: '1K',
        controller,
        onStream: (content) => {
          accumulatedText = content;
          aiImgStreamText.style.display = '';
          aiImgStreamText.textContent = content;
          aiImgStreamText.parentElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
        },
        buildPromptFn: buildGreenScreenPrompt,
      });

      let imageUrl = null;
      if (cfg.type === 'dashscope') {
        imageUrl = AiCommon.extractImageUrl(accumulatedText) || result;
        if (!imageUrl) imageUrl = result;
      } else {
        imageUrl = AiCommon.extractImageUrl(accumulatedText);
      }

      if (imageUrl && imageUrl.startsWith('http')) {
        showPreview(imageUrl);
      } else {
        aiImgStreamText.style.display = '';
        aiImgStreamText.innerHTML = `<span style="color:#dc2626">⚠ 未能解析到图片链接</span>\n\n${AiCommon.escapeHtml(accumulatedText)}`;
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      aiImgStreamText.style.display = '';
      aiImgStreamText.innerHTML = `<span style="color:#dc2626">❌ 生成失败: ${AiCommon.escapeHtml(err.message)}</span>`;
    } finally {
      controller = null;
      aiImgLoading.style.display = 'none';
      aiImgInput.disabled = false;
      aiImgBtn.disabled = false;
      aiImgBtn.textContent = '✨ 重新生成';
    }
  }

  function showPreview(url) {
    aiImgPreviewImg.src = url;
    aiImgPreview.style.display = '';
    aiImgConfirm.style.display = '';
    aiImgStreamText.textContent = '';
    aiImgBtn.textContent = '✨ 重新生成';
  }

  /** 抠除绿幕背景 */
  function removeGreenBackground(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const c = document.createElement('canvas');
        c.width = img.naturalWidth;
        c.height = img.naturalHeight;
        const ctx = c.getContext('2d');
        ctx.drawImage(img, 0, 0);

        const imageData = ctx.getImageData(0, 0, c.width, c.height);
        const data = imageData.data;

        for (let i = 0; i < data.length; i += 4) {
          const r = data[i], g = data[i + 1], b = data[i + 2];
          if (g > GREEN_THRESHOLD && r < g / GREEN_RATIO && b < g / GREEN_RATIO) {
            data[i + 3] = 0;
          }
        }

        ctx.putImageData(imageData, 0, 0);
        c.toBlob((blob) => {
          if (blob) resolve(blob);
          else reject(new Error('抠图处理失败'));
        }, 'image/png');
      };
      img.onerror = () => reject(new Error('图片加载失败'));
      img.src = src;
    });
  }

  async function applyImage() {
    let src = aiImgPreviewImg.src;
    if (!src) return;

    // 先转为 data URL（避免 canvas taint）
    if (src.startsWith('http') && typeof AiCommon !== 'undefined') {
      try { src = await AiCommon.loadImageAsDataUrl(src); } catch {}
    }

    try {
      // 统一抠绿（无绿色像素不会误删）
      const blob = await removeGreenBackground(src);
      const file = new File([blob], 'ai-element.png', { type: 'image/png' });
      Elements.addImage(file);
      closeDialog();
    } catch (err) {
      try {
        const dataUrl = await AiCommon.loadImageAsDataUrl(src);
        const resp = await fetch(dataUrl);
        const blob = await resp.blob();
        const file = new File([blob], 'ai-element.png', { type: blob.type || 'image/png' });
        Elements.addImage(file);
        closeDialog();
      } catch (err2) {
        alert('添加失败：' + err2.message);
      }
    }
  }

  async function uploadRefImage(file) {
    if (refImageUrls.length >= 4) return;
    aiImgRefFile.value = '';

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
    aiImgRefList.innerHTML = '';
    refImageUrls.forEach((url, i) => {
      const thumb = document.createElement('div');
      thumb.className = 'ai-ref-thumb';
      thumb.innerHTML = `<img src="${url}" alt="参考图${i + 1}" title="点击预览"><button class="ai-ref-remove" data-index="${i}" title="移除">✕</button>`;
      thumb.querySelector('img').addEventListener('click', () => openRefPreview(i));
      thumb.querySelector('.ai-ref-remove').addEventListener('click', (e) => {
        e.stopPropagation();
        removeRefImage(i);
      });
      aiImgRefList.appendChild(thumb);
    });

    const isFull = refImageUrls.length >= 4;
    aiImgRefUploadBtn.classList.toggle('disabled', isFull);
    aiImgRefUploadLabel.textContent = isFull ? '已满' : refImageUrls.length > 0 ? '+ 更多' : '参考图';
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
