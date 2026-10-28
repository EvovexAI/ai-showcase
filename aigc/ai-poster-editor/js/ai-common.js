/* ==============================
   AI 公共模块 — ai-common.js
   抽取 ai-gen / ai-image 共用逻辑：
   - SSE 流式读取（OpenAI 兼容）
   - 图片生成（豆包 Agent Plan / 火山方舟 Ark）
   - 图片 URL 提取
   - HTML 转义
   ============================== */

const AiCommon = (() => {

  /** HTML 转义 */
  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /** 从文本中提取图片 URL */
  function extractImageUrl(text) {
    const mdMatch = text.match(/!\[[^\]]*\]\((https?:\/\/[^)]+)\)/);
    if (mdMatch) return mdMatch[1];

    const labeledMatch = text.match(/IMAGE_URL[:：]\s*(https?:\/\/\S+)/i);
    if (labeledMatch) return labeledMatch[1].trim();

    const urlMatch = text.match(/(https?:\/\/[^\s"'<>]+\.(?:png|jpg|jpeg|webp|gif|svg)(?:\?[^\s"'<>]*)?)/i);
    if (urlMatch) return urlMatch[1];

    const anyUrl = text.match(/(https?:\/\/[^\s"'<>]+)/);
    if (anyUrl) return anyUrl[1];

    const b64Match = text.match(/(data:image\/[a-z]+;base64,[A-Za-z0-9+/=]+)/i);
    if (b64Match) return b64Match[1];

    return null;
  }

  /** 豆包 Agent Plan（火山方舟）图片生成 — /api/plan/v3/images/generations */
  async function requestArk({ cfg, text, onStream, controller, size, refImages }) {
    const model = cfg.model || 'doubao-seedream-5-0-pro';
    const imgSize = size || '2K';
    onStream('正在生成…\n');

    // 构建多模态 content：参考图（image_url）+ 文本提示词
    const content = [];
    if (refImages && refImages.length > 0) {
      refImages.forEach(url => content.push({ type: 'image_url', image_url: { url } }));
    }
    content.push({ type: 'text', text });

    const res = await fetch(`${cfg.apiBase}/images/generations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${cfg.apiKey}`,
      },
      body: JSON.stringify({
        model,
        prompt: content,
        size: imgSize,
        response_format: 'url',
        output_format: 'png',
        watermark: false,
      }),
      signal: controller.signal,
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.message || `HTTP ${res.status}: ${res.statusText}`);
    }

    const json = await res.json();
    const images = json.data || [];
    const first = images.find(it => it.url) || {};
    const imageUrl = first.url;
    if (imageUrl) {
      onStream(`IMAGE_URL:${imageUrl}\n`);
      return imageUrl;
    }
    throw new Error(first.error?.message || '生成成功但未获取到图片链接');
  }

  /** 读取 SSE 流 */
  async function readSSEStream(response, controller, onStream) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let accumulatedText = '';

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
            accumulatedText += content;
            onStream(accumulatedText);
          }
        } catch {}
      }
    }

    return accumulatedText;
  }

  /** OpenAI 兼容 SSE 流式请求 */
  async function requestOpenAI({ cfg, messageContent, controller, onStream }) {
    const body = {
      messages: [{ role: 'user', content: messageContent }],
      stream: true,
    };
    if (cfg.model) body.model = cfg.model;

    const res = await fetch(`${cfg.apiBase}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${cfg.apiKey}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status}: ${errText || res.statusText}`);
    }

    return await readSSEStream(res, controller, onStream);
  }

  /** 根据 Provider 发出请求 */
  async function request({ cfg, text, refImageUrls, controller, onStream, buildPromptFn, size }) {
    if (cfg.type === 'ark') {
      return await requestArk({ cfg, text, onStream, controller, size, refImages: refImageUrls });
    }
    if (cfg.type === 'openai') {
      return await requestOpenAI({ cfg, messageContent: text, controller, onStream });
    }
    throw new Error(`不支持的 Provider 类型: ${cfg.type}`);
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /** 将远程图片URL转为代理URL（通过 localhost:3459），绕过CORS */
  function proxyUrl(url) {
    if (!url || !url.startsWith('http')) return url;
    const u = new URL(url);
    return `http://localhost:3459/${u.host}${u.pathname}${u.search}`;
  }

  /** 通过代理加载远程图片为 data URL */
  async function loadImageAsDataUrl(url) {
    // 先尝试直接加载
    try {
      const res = await fetch(url);
      if (res.ok) {
        const blob = await res.blob();
        return await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.readAsDataURL(blob);
        });
      }
    } catch {}

    // 失败则通过代理
    const proxied = proxyUrl(url);
    const res = await fetch(proxied);
    if (!res.ok) throw new Error(`Proxy fetch failed: ${res.status}`);
    const blob = await res.blob();
    return await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(blob);
    });
  }

  return { escapeHtml, extractImageUrl, request, sleep, proxyUrl, loadImageAsDataUrl };
})();
