/* ==============================
   AI 优化布局 — ai-optimize.js
   截图 + 当前布局摘要 → AI 视觉理解 → 返回 diff → 合并应用
   v3: 多轮对话 + 快捷预设 + 语义标注 + 快照栈
   ============================== */

const AiOptimize = (() => {

  // DOM
  const btnAiOptimize = document.getElementById('btnAiOptimize');
  const aiOptimizeModal = document.getElementById('aiOptimizeModal');
  const aiOptPreviewImg = document.getElementById('aiOptPreviewImg');
  const aiOptConversation = document.getElementById('aiOptConversation');
  const aiOptPresets = document.getElementById('aiOptPresets');
  const aiOptInput = document.getElementById('aiOptInput');
  const aiOptBtn = document.getElementById('aiOptBtn');
  const aiOptLoading = document.getElementById('aiOptLoading');
  const aiOptStreamText = document.getElementById('aiOptStreamText');
  const aiOptConfirm = document.getElementById('aiOptConfirm');
  const aiOptUndo = document.getElementById('aiOptUndo');
  const aiOptReset = document.getElementById('aiOptReset');
  const aiOptimizeClose = document.getElementById('aiOptimizeClose');

  // 参考图预览（复用全局预览弹窗）
  const aiOptRefPreviewModal = document.getElementById('aiRefPreviewModal');
  const aiOptRefPreviewImg = document.getElementById('aiRefPreviewImg');
  const aiOptRefPreviewClose = document.getElementById('aiRefPreviewClose');
  const aiOptRefPrev = document.getElementById('aiRefPrev');
  const aiOptRefNext = document.getElementById('aiRefNext');
  const aiOptRefCounter = document.getElementById('aiRefCounter');

  let controller = null;
  let accumulatedText = '';
  let snapshotStack = [];    // 快照栈（支持多次撤回）
  let tempBackup = null;    // 预览前的布局快照
  let pendingDiff = null;   // AI 返回的待应用 diff
  let aiAnalysis = '';      // AI 分析文本
  let conversationHistory = []; // 多轮对话历史 [{role, content}]
  let isFirstTurn = true;   // 是否是本对话的第一轮

  // 事件绑定
  btnAiOptimize?.addEventListener('click', openDialog);
  aiOptimizeClose?.addEventListener('click', closeDialog);
  aiOptBtn?.addEventListener('click', generate);
  aiOptConfirm?.addEventListener('click', previewLayout);
  aiOptUndo?.addEventListener('click', undoLayout);
  aiOptReset?.addEventListener('click', resetConversation);
  aiOptInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) generate();
  });

  // 截图点击放大
  aiOptPreviewImg?.addEventListener('click', () => openImagePreview());
  aiOptRefPreviewClose?.addEventListener('click', closeImagePreview);
  aiOptRefPreviewModal?.addEventListener('click', (e) => {
    if (e.target === aiOptRefPreviewModal) closeImagePreview();
  });

  // 预设按钮
  aiOptPresets?.addEventListener('click', (e) => {
    const btn = e.target.closest('.preset-btn');
    if (!btn) return;
    const prompt = btn.dataset.prompt;
    if (prompt) {
      aiOptInput.value = prompt;
      aiOptInput.focus();
    }
  });

  /** 打开弹窗 */
  async function openDialog() {
    resetState();
    // 更新 Provider 标识
    const badge = document.getElementById('aiOptProvider');
    if (badge) badge.textContent = Config.getAiOptimizeName() || '未知';
    // 重置对话
    conversationHistory = [];
    isFirstTurn = true;
    updateConversationDisplay();
    // 截图前先把远程背景转 data URL
    const canvas = Canvas.getElement();
    const bgImage = canvas.style.backgroundImage;
    if (bgImage && bgImage !== 'none') {
      const urlMatch = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
      if (urlMatch && urlMatch[1].startsWith('http') && typeof AiCommon !== 'undefined') {
        try {
          const dataUrl = await AiCommon.loadImageAsDataUrl(urlMatch[1]);
          canvas.style.backgroundImage = `url(${dataUrl})`;
        } catch {}
      }
    }
    // 截图用于弹窗预览
    const rendered = await html2canvas(canvas, {
      scale: 2, backgroundColor: '#ffffff', logging: false,
    });
    const blob = await new Promise(r => rendered.toBlob(r, 'image/jpeg', 0.85));
    aiOptPreviewImg.src = URL.createObjectURL(blob);
    aiOptimizeModal.classList.add('open');
    setTimeout(() => aiOptInput.focus(), 100);
  }

  /** 关闭弹窗 */
  function closeDialog() {
    aiOptimizeModal.classList.remove('open');
    abort();
  }

  function resetState() {
    abort();
    aiOptInput.value = '';
    aiOptInput.disabled = false;
    aiOptBtn.disabled = false;
    aiOptBtn.textContent = '✨ 开始优化';
    aiOptLoading.style.display = 'none';
    aiOptStreamText.style.display = 'none';
    aiOptStreamText.textContent = '';
    aiOptConfirm.style.display = 'none';
    aiOptUndo.style.display = 'none';
    if (aiOptReset) aiOptReset.style.display = 'none';
    accumulatedText = '';
    pendingDiff = null;
    aiAnalysis = '';
    tempBackup = null;
    // 不重置 conversationHistory 和 isFirstTurn（弹窗关闭再打开时才重置）
  }

  function abort() {
    if (controller) { controller.abort(); controller = null; }
  }

  /** 截图前修复远程背景 */
  async function fixBackgroundForScreenshot(canvas) {
    const bgImage = canvas.style.backgroundImage;
    if (!bgImage || bgImage === 'none') return;
    const urlMatch = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
    if (!urlMatch) return;
    const url = urlMatch[1];
    if (!url.startsWith('http') || typeof AiCommon === 'undefined') return;
    try {
      const dataUrl = await AiCommon.loadImageAsDataUrl(url);
      canvas.style.backgroundImage = `url(${dataUrl})`;
    } catch {}
  }

  /** 截取画布 base64（OpenAI 兼容接口用） */
  async function captureCanvasBase64() {
    const canvas = Canvas.getElement();
    const selectedId = Elements.getSelectedId();
    if (selectedId) {
      const sel = Elements.getElement(selectedId);
      if (sel) sel.classList.remove('selected');
    }

    await fixBackgroundForScreenshot(canvas);

    const rendered = await html2canvas(canvas, {
      allowTaint: true, foreignObjectRendering: true,
      scale: 2, backgroundColor: '#ffffff', logging: false,
    });

    if (selectedId) {
      const sel = Elements.getElement(selectedId);
      if (sel) sel.classList.add('selected');
    }

    return rendered.toDataURL('image/jpeg', 0.7);
  }

  function getFontList() {
    const propFont = document.getElementById('propFont');
    if (!propFont) return [];
    return Array.from(propFont.options).map(opt => ({
      name: opt.textContent,
      value: opt.value
    }));
  }

  /** 构建元素摘要（含角色标注） */
  function buildElementSummary(elements) {
    if (!elements || elements.length === 0) return '  （画布为空，无元素）';
    return elements.map(el => {
      if (el.type === 'text') {
        const content = (el.content || '').slice(0, 50).replace(/\n/g, ' ');
        const roleTag = el.role ? ` [${el.role}]` : '';
        const weight = el.style?.fontWeight === 'bold' ? ' bold' : '';
        const italic = el.style?.fontStyle === 'italic' ? ' italic' : '';
        const align = el.style?.textAlign !== 'left' ? ` align:${el.style?.textAlign}` : '';
        const lh = el.style?.lineHeight ? ` lh:${el.style.lineHeight}` : '';
        const ls = el.style?.letterSpacing ? ` ls:${el.style.letterSpacing}px` : '';
        const bg = el.style?.backgroundColor ? ' bg' : '';
        const deco = el.style?.textDecoration && el.style?.textDecoration !== 'none' ? ` deco:${el.style.textDecoration}` : '';
        const glow = el.dataset?.glow ? ' glow' : '';
        const flip = (el.style?.transform || '').includes('scaleX(-1)') ? ' flip' : '';
        return `  [${el.id}]${roleTag} text "${content}" at(${el.left},${el.top}) ${el.width}×${el.style?.fontSize || 24}px${weight}${italic}${align}${lh}${ls}${bg}${deco}${glow}${flip} font:${el.style?.fontFamily || 'auto'} color:${el.style?.color || '#000'}`;

      }
      const imageRoleTag = el.role ? ` [${el.role}]` : '';
      return `  [${el.id}]${imageRoleTag} image at(${el.left},${el.top}) ${el.width}×${el.height}px`;
    }).join('\n');
  }

  /** 构建当前上下文文本（用于对话消息） */
  function buildContextText(userText, currentLayout) {
    const cw = Canvas.getWidth();
    const ch = Canvas.getHeight();
    const elementSummary = buildElementSummary(currentLayout.elements);
    const fonts = getFontList().map(f => f.value).join(', ');

    return `【画布尺寸】${cw} × ${ch} 像素
【可用字体】${fonts}
【字号范围】12 ~ 120
【当前元素列表】
${elementSummary}
【用户要求】${userText}`;
  }

  /** 构建首轮提示词 */
  function buildFirstPrompt(userText, currentLayout) {
    const contextText = buildContextText(userText, currentLayout);
    return `你是专业海报排版优化 AI。请先观察上传的海报截图，然后根据用户要求优化排版。

${contextText}

请分析截图，返回优化方案。只返回变更的元素，未变更的元素不要返回。

输出格式（严格 JSON，不要其他文字）：
\`\`\`json
{
  "analysis": "简短优化分析（1-3句话，中文）",
  "changes": {
    "changed": [
      { "id": "el-1", "fontSize": 36, "fontWeight": "bold" },
      { "id": "el-img-1", "left": 50, "top": 300, "width": 200, "height": 150 }
    ],
    "added": [
      { "type": "text", "id": "el-new", "left": 100, "top": 500, "width": 200, "content": "新文字", "fontSize": 20, "color": "#333333", "fontFamily": "system-ui, sans-serif", "fontWeight": "normal", "fontStyle": "normal", "textAlign": "center", "opacity": 1, "lineHeight": 1.5, "letterSpacing": 0, "backgroundColor": null, "textDecoration": "none", "rotation": 0 }
    ],
    "deleted": ["el-3"]
  }
}
\`\`\`

规则：
- changed 可包含文字元素和图片元素。只列出要改的属性，未列出的保持原值
- 文字元素可改：left, top, width, height, fontSize, fontFamily, color, fontWeight, fontStyle, textAlign, opacity, lineHeight, letterSpacing, backgroundColor, textDecoration, rotation
- 图片元素可改：left, top, width, height, opacity, objectFit（cover/contain/fill）
- 调整图片宽高比时保持 width 和 height 比例协调
- added 只能新增文字元素，必须包含 type:"text"、id、left、top、width、content、fontSize、fontFamily、color
- deleted 是要删除的元素 id 列表（文字和图片均可）
- **元素之间垂直间距至少 8px，避免文字重叠**
- 只返回 JSON，禁止添加任何解释文字`;
  }

  /** 构建后续轮次提示词（无截图，纯文本） */
  function buildFollowUpPrompt(userText, currentLayout) {
    const contextText = buildContextText(userText, currentLayout);
    return `【当前海报元素状态】
${contextText}

请基于对话历史和当前元素状态，继续优化布局。可调整文字和图片元素的属性。注意保持元素间垂直间距至少 8px 避免重叠。返回 diff 格式 JSON（与之前相同的格式）。只返回 JSON，不要其他文字。`;
  }

  /** 修复常见 JSON 错误 */
  function fixJson(text) {
    let s = text.trim();
    const start = s.indexOf('{');
    const end = s.lastIndexOf('}');
    if (start !== -1 && end > start) {
      s = s.slice(start, end + 1);
    }
    try { JSON.parse(s); return s; } catch {}
    s = s.replace(/,(\s*[}\]])/g, '$1');
    try { JSON.parse(s); return s; } catch {}
    s = s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    try { JSON.parse(s); return s; } catch {}
    try { return JSON.parse(s.replace(/'/g, '"')); } catch {}
    return null;
  }

  /** 从 AI 回复中提取 diff JSON */
  function extractDiffJson(text) {
    const codeMatch = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
    if (codeMatch) {
      const fixed = fixJson(codeMatch[1]);
      if (fixed) { try { return JSON.parse(fixed); } catch {} }
    }
    const jsonMatch = text.match(/\{[\s\S]*("changes"|"elements")[\s\S]*\}/);
    if (jsonMatch) {
      const fixed = fixJson(jsonMatch[0]);
      if (fixed) { try { return JSON.parse(fixed); } catch {} }
    }
    const fixed = fixJson(text);
    if (fixed) { try { return JSON.parse(fixed); } catch {} }
    return null;
  }

  /** 将 diff 合并到当前布局 */
  function mergeDiff(currentLayout, diff) {
    const result = JSON.parse(JSON.stringify(currentLayout));

    if (diff.changes?.changed) {
      for (const change of diff.changes.changed) {
        const el = result.elements.find(e => e.id === change.id);
        if (!el) continue;

        // 通用属性（文字和图片都支持）
        if (change.left !== undefined) el.left = change.left;
        if (change.top !== undefined) el.top = change.top;
        if (change.width !== undefined) el.width = change.width;

        if (el.type === 'text') {
          // 宽度改变但高度未指定时，清除固定高度让文本自适应
          if (change.width !== undefined && change.height === undefined && el.height) {
            el.height = undefined;
          }
          if (change.height !== undefined) el.height = change.height;
          if (change.content !== undefined) el.content = change.content;
          const styleKeys = ['fontSize', 'fontFamily', 'color', 'fontWeight', 'fontStyle', 'textAlign', 'opacity', 'lineHeight', 'letterSpacing', 'textDecoration'];
          for (const key of styleKeys) {
            if (change[key] !== undefined) el.style[key] = change[key];
          }
          if (change.effects) Object.assign(el.effects, change.effects);
          if (change.backgroundColor !== undefined) el.style.backgroundColor = change.backgroundColor;
          if (change.rotation !== undefined) {
            el.style.transform = el.style.transform ? el.style.transform.replace(/rotate\([^)]*\)/g, '').trim() : '';
            if (change.rotation) el.style.transform = (el.style.transform ? el.style.transform + ' ' : '') + 'rotate(' + change.rotation + 'deg)';
            if (!el.style.transform) el.style.transform = '';
          }
        }

        if (el.type === 'image') {
          if (change.height !== undefined) el.height = change.height;
          if (change.opacity !== undefined) el.style.opacity = change.opacity;
          if (change.objectFit !== undefined) el.style.objectFit = change.objectFit;
        }
      }
    }

    if (diff.changes?.added) {
      const existingIds = new Set(result.elements.map(e => e.id));
      for (const add of diff.changes.added) {
        if (add.type !== 'text') continue;
        let newId = add.id;
        // 冲突检测：AI 提供的 id 无效或已存在则生成唯一 id
        if (!newId || existingIds.has(newId)) {
          newId = `el-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        }
        existingIds.add(newId);
        result.elements.push({
          type: 'text',
          id: newId,
          left: add.left || 0,
          top: add.top || 0,
          width: add.width || 200,
          content: add.content || '',
          style: {
            fontSize: add.fontSize || 24,
            fontFamily: add.fontFamily || 'system-ui, sans-serif',
            color: add.color || '#000000',
            fontWeight: add.fontWeight || 'normal',
            fontStyle: add.fontStyle || 'normal',
            textAlign: add.textAlign || 'left',
            opacity: add.opacity ?? 1,
            lineHeight: add.lineHeight ?? 0,
            letterSpacing: add.letterSpacing ?? 0,
            textDecoration: add.textDecoration || null,
            rotation: add.rotation || 0,
          },
          effects: add.effects || { shadow: null, stroke: null, glow: null },
          backgroundColor: add.backgroundColor || null,
        });
      }
    }

    if (diff.changes?.deleted) {
      result.elements = result.elements.filter(e => !diff.changes.deleted.includes(e.id));
    }

    return result;
  }

  /** 更新对话显示 */
  function updateConversationDisplay() {
    if (!aiOptConversation) return;
    if (conversationHistory.length === 0) {
      aiOptConversation.style.display = 'none';
      aiOptConversation.innerHTML = '';
      return;
    }
    aiOptConversation.style.display = '';
    aiOptConversation.innerHTML = conversationHistory
      .filter(m => m.role === 'user')
      .map((m, i) => {
        const label = i === 0 ? '初始' : `第${i + 1}轮`;
        return `<div class="ai-opt-turn">
          <span class="ai-opt-turn-label">${label}</span>
          <span class="ai-opt-turn-text">${escapeHtml(m.summary || m.text || '')}</span>
        </div>`;
      }).join('');
    aiOptConversation.scrollTop = aiOptConversation.scrollHeight;
  }

  /** 重置对话 */
  function resetConversation() {
    conversationHistory = [];
    isFirstTurn = true;
    updateConversationDisplay();
    if (aiOptReset) aiOptReset.style.display = 'none';
    aiOptStreamText.style.display = 'none';
    aiOptStreamText.textContent = '';
    aiOptConfirm.style.display = 'none';
    aiOptBtn.textContent = '✨ 开始优化';
  }

  /** 开始优化 */
  async function generate() {
    const userText = aiOptInput.value.trim();
    if (!userText) { aiOptInput.focus(); return; }

    const cfg = Config.getAiOptimize();

    aiOptInput.disabled = true;
    aiOptBtn.disabled = true;
    aiOptBtn.textContent = '⏳ 优化中...';
    aiOptLoading.style.display = '';
    aiOptStreamText.style.display = 'none';
    aiOptConfirm.style.display = 'none';
    accumulatedText = '';
    pendingDiff = null;
    aiAnalysis = '';

    controller = new AbortController();

    const currentLayout = Layout.serialize();
    const userSummary = userText.slice(0, 80) + (userText.length > 80 ? '…' : '');

    try {
      if (isFirstTurn) {
        // 首轮：截图 + prompt（OpenAI 兼容多模态）
        const prompt = buildFirstPrompt(userText, currentLayout);

        const dataUrl = await captureCanvasBase64();
        const result = await AiCommon.request({
          cfg,
          text: [
            { type: 'image_url', image_url: { url: dataUrl } },
            { type: 'text', text: prompt },
          ],
          refImageUrls: null,
          controller,
          onStream: (content) => {
            accumulatedText = content;
            aiOptStreamText.style.display = '';
            aiOptStreamText.textContent = content;
          },
        });
        accumulatedText = result;
      } else {
        // 后续轮次：纯文本多轮对话（OpenAI 兼容）
        const followUpText = buildFollowUpPrompt(userText, currentLayout);

        const messages = [];
        for (const m of conversationHistory) {
          if (m.role === 'user') {
            messages.push({ role: 'user', content: m.text || m.content || '' });
          } else if (m.role === 'assistant') {
            messages.push({ role: 'assistant', content: m.content || '' });
          }
        }
        messages.push({ role: 'user', content: followUpText });

        const res = await fetch(`${cfg.apiBase}/chat/completions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${cfg.apiKey}`,
          },
          body: JSON.stringify({
            model: cfg.model || 'gpt-3.5-turbo',
            messages,
            stream: true,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errT = await res.text().catch(() => '');
          throw new Error(`HTTP ${res.status}: ${errT || res.statusText}`);
        }
        accumulatedText = await readStream(res);
      }

      const diff = extractDiffJson(accumulatedText);

      // 兼容旧格式
      if (diff && diff.elements && !diff.changes) {
        pendingDiff = { _legacyLayout: diff, analysis: diff.analysis || '' };
        aiAnalysis = diff.analysis || '';
      } else if (diff && diff.changes) {
        pendingDiff = diff;
        aiAnalysis = diff.analysis || '';
      }

      if (pendingDiff) {
        aiOptConfirm.style.display = '';
        const analysisText = aiAnalysis ? `📝 ${aiAnalysis}\n\n` : '';
        aiOptStreamText.textContent = `${analysisText}✓ 优化完成，点击「预览」查看效果`;
        aiOptStreamText.style.display = '';

        // 记录对话历史
        conversationHistory.push({ role: 'user', text: userText, summary: userSummary });
        conversationHistory.push({ role: 'assistant', content: accumulatedText, analysis: aiAnalysis });
        isFirstTurn = false;
        updateConversationDisplay();
        if (aiOptReset) aiOptReset.style.display = '';
      } else {
        aiOptStreamText.innerHTML = `<span style="color:#dc2626">⚠ 未能解析到布局数据</span>\n\n${escapeHtml(accumulatedText)}`;
        aiOptStreamText.style.display = '';
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      aiOptStreamText.innerHTML = `<span style="color:#dc2626">❌ 优化失败: ${escapeHtml(err.message)}</span>`;
      aiOptStreamText.style.display = '';
    } finally {
      controller = null;
      aiOptLoading.style.display = 'none';
      aiOptInput.disabled = false;
      aiOptBtn.disabled = false;
      aiOptBtn.textContent = isFirstTurn ? '✨ 开始优化' : '✨ 继续优化';
      aiOptInput.value = '';
      aiOptInput.focus();
    }
  }

  /** 读取 SSE 流 */
  async function readStream(res) {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let text = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed === 'data: [DONE]') continue;
        if (!trimmed.startsWith('data: ')) continue;

        try {
          const json = JSON.parse(trimmed.slice(6));
          const content = json.choices?.[0]?.delta?.content;
          if (content) {
            text += content;
            aiOptStreamText.textContent = text;
          }
        } catch {}
      }
    }

    return text;
  }

  /** 预览布局 */
  function previewLayout() {
    if (!pendingDiff) return;

    tempBackup = Layout.serialize();

    let layoutToApply;

    if (pendingDiff._legacyLayout) {
      const originalLayout = tempBackup;
      layoutToApply = JSON.parse(JSON.stringify(pendingDiff._legacyLayout));
      const origImages = {};
      originalLayout.elements.forEach(el => {
        if (el.type === 'image' && el.src) origImages[el.id] = el.src;
      });
      layoutToApply.elements.forEach(el => {
        if (el.type === 'image' && origImages[el.id]) el.src = origImages[el.id];
      });
      if (originalLayout.canvas?.background) {
        layoutToApply.canvas.background = originalLayout.canvas.background;
      }
    } else {
      layoutToApply = mergeDiff(tempBackup, pendingDiff);
    }

    Layout.applyLayoutData(layoutToApply);
    aiOptimizeModal.classList.remove('open');
    showPreviewActions();
  }

  /** 浮动操作栏 */
  function showPreviewActions() {
    const old = document.getElementById('aiOptPreviewActions');
    if (old) old.remove();

    const bar = document.createElement('div');
    bar.id = 'aiOptPreviewActions';
    bar.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:8px;z-index:100;background:#ffffff;border:1px solid #e4e7ec;border-radius:10px;padding:8px 16px;box-shadow:0 8px 32px rgba(15,23,42,0.15);';
    bar.innerHTML = `
      <span style="color:#6b7280;font-size:12px;margin-right:4px;">预览中</span>
      <button id="aiOptPreviewConfirm" style="padding:6px 16px;background:#2563eb;border:none;color:#fff;border-radius:6px;cursor:pointer;font-size:12px;">确认</button>
      <button id="aiOptPreviewCancel" style="padding:6px 16px;background:#f2f3f5;border:1px solid #d0d5dd;color:#1f2329;border-radius:6px;cursor:pointer;font-size:12px;">取消</button>
    `;
    document.body.appendChild(bar);

    document.getElementById('aiOptPreviewConfirm').onclick = () => {
      bar.remove();
      // 推入快照栈
      snapshotStack.push(tempBackup);
      tempBackup = null;
      aiOptUndo.style.display = '';
    };
    document.getElementById('aiOptPreviewCancel').onclick = () => {
      bar.remove();
      if (tempBackup) {
        Layout.applyLayoutData(tempBackup);
        tempBackup = null;
      }
      aiOptimizeModal.classList.add('open');
      aiOptStreamText.textContent = '✓ 已恢复，可重新调整描述后再次优化';
      aiOptStreamText.style.display = '';
      aiOptConfirm.style.display = '';
    };
  }

  /** 撤回 — 弹出栈顶快照 */
  function undoLayout() {
    if (snapshotStack.length === 0) return;
    const prev = snapshotStack.pop();
    Layout.applyLayoutData(prev);
    if (snapshotStack.length === 0) {
      aiOptUndo.style.display = 'none';
    }
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /** 点击预览图放大 */
  function openImagePreview() {
    if (!aiOptPreviewImg.src) return;
    aiOptRefPreviewImg.src = aiOptPreviewImg.src;
    aiOptRefPrev.style.display = 'none';
    aiOptRefNext.style.display = 'none';
    if (aiOptRefCounter) aiOptRefCounter.style.display = 'none';
    aiOptRefPreviewModal.classList.add('open');
  }

  function closeImagePreview() {
    aiOptRefPreviewModal.classList.remove('open');
  }

  return { openDialog, closeDialog };
})();
