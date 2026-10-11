/* ==============================
   img2post 本地服务 — server.cjs
   一个进程同时提供：
   1. 静态站点（编辑器 UI）
   2. REST API（AI 背景生成 / 绿幕素材 / 一键海报）

   启动：node server.cjs
   端口：IMG2POST_PORT，默认 8899
   配置：可选 api.config.json（见 SETUP.md），请求体 override 可逐次覆盖

   接口：
   - GET  /health
   - GET  /api/config
   - POST /api/generate/background  { description, refImages? }
   - POST /api/generate/material    { description }
   - POST /api/generate/poster      { topic, fonts?, generateBackground? }

   override（所有接口通用，可选）：{ apiBase?, apiKey?, model? }
   ============================== */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.IMG2POST_PORT || '8899', 10);
const ROOT = __dirname;
const BODY_LIMIT = 25 * 1024 * 1024; // 25MB（允许 base64 参考图）
const REQUEST_TIMEOUT_MS = 120000;

/* ---------- Provider 默认配置 ----------
   优先级：请求体 override > api.config.json > 环境变量 > 此处内置值（默认为空，不含任何密钥）
   环境变量：DASHSCOPE_API_BASE / DASHSCOPE_API_KEY / DASHSCOPE_MODEL
             OPENAI_API_BASE / OPENAI_API_KEY / OPENAI_MODEL                       */

const DEFAULT_TPL = {
  dashscope: {
    apiBase: process.env.DASHSCOPE_API_BASE || 'https://dashscope.aliyuncs.com/api/v1',
    apiKey: process.env.DASHSCOPE_API_KEY || '',
    model: process.env.DASHSCOPE_MODEL || 'wan2.7-image-pro',
  },
  openai: {
    apiBase: process.env.OPENAI_API_BASE || '',
    apiKey: process.env.OPENAI_API_KEY || '',
    model: process.env.OPENAI_MODEL || '',
  },
};

function loadFileConfig() {
  const file = path.join(ROOT, 'api.config.json');
  try {
    const raw = fs.readFileSync(file, 'utf8');
    const json = JSON.parse(raw);
    return {
      dashscope: { ...DEFAULT_TPL.dashscope, ...(json.dashscope || {}) },
      openai: { ...DEFAULT_TPL.openai, ...(json.openai || {}) },
    };
  } catch {
    return JSON.parse(JSON.stringify(DEFAULT_TPL));
  }
}

function resolveProvider(kind, override) {
  const base = loadFileConfig()[kind] || {};
  const o = override || {};
  return {
    apiBase: (o.apiBase || base.apiBase || '').replace(/\/+$/, ''),
    apiKey: o.apiKey || base.apiKey || '',
    model: o.model || base.model || '',
  };
}

/* ---------- 提示词（与前端 ai-gen / ai-image / ai-poster 保持一致） ---------- */

function buildBgPrompt(userText, refCount) {
  const refDesc = refCount > 0
    ? '【参考图】上传的图片是当前海报背景，请基于此风格/色调生成新背景。\n'
    : '';
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

function buildMaterialPrompt(userText) {
  return `请生成一张图片素材：

【用户描述】
${userText}

【生成要求】
1. 背景色必须为纯绿色 #00C800（绿幕色），不可使用其他颜色
2. 主体清晰突出，边缘干净
3. 风格：与用户描述匹配
4. 用途：海报素材（需要透明背景，绿幕用于后期抠图）`;
}

function buildPosterPrompt(topic, fonts) {
  const fontStr = (fonts && fonts.length ? fonts : ['system-ui, sans-serif', 'PingFang SC', 'Microsoft YaHei']).join(', ');
  return `你是专业海报设计师。请根据主题设计一张移动端竖版海报（画布 375×812 像素）。

【主题】${topic}
【可用字体】${fontStr}
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

function buildBgFromDescriptionPrompt(desc) {
  return `请生成一张移动端竖版海报背景图。禁止任何文字。${desc}`;
}

/* ---------- 上游请求 ---------- */

function fetchWithTimeout(url, options, timeoutMs) {
  return fetch(url, { ...options, signal: AbortSignal.timeout(timeoutMs || REQUEST_TIMEOUT_MS) });
}

/** 通义万象（DashScope）生图，返回图片 URL */
async function dashscopeGenerate(provider, { text, refImages, size }) {
  if (!provider.apiBase || !provider.apiKey) throw new Error('DashScope 未配置（apiBase/apiKey 缺失）');

  const content = [];
  (refImages || []).forEach(url => content.push({ image: url }));
  content.push({ text });

  const res = await fetchWithTimeout(`${provider.apiBase}/services/aigc/multimodal-generation/generation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${provider.apiKey}`,
    },
    body: JSON.stringify({
      model: provider.model || 'wan2.7-image-pro',
      input: { messages: [{ role: 'user', content }] },
      parameters: { size: size || '2K', n: 1, watermark: false },
    }),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.message || `DashScope HTTP ${res.status}: ${res.statusText}`);
  }

  const json = await res.json();
  const images = json.output?.choices?.[0]?.message?.content || [];
  const imageUrl = images.find(c => c.image)?.image;
  if (!imageUrl) throw new Error('生成成功但未获取到图片链接');
  return imageUrl;
}

/** OpenAI 兼容 chat（非流式），返回文本 */
async function openaiChat(provider, { content, model }) {
  if (!provider.apiBase || !provider.apiKey) throw new Error('OpenAI 兼容网关未配置（apiBase/apiKey 缺失）');

  const body = { messages: [{ role: 'user', content }], stream: false };
  const m = model || provider.model;
  if (m) body.model = m;

  const res = await fetchWithTimeout(`${provider.apiBase}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${provider.apiKey}`,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`OpenAI 兼容网关 HTTP ${res.status}: ${errText || res.statusText}`);
  }

  const json = await res.json();
  return json.choices?.[0]?.message?.content || '';
}

/* ---------- 解析工具（与前端 ai-common / ai-poster 一致） ---------- */

function extractImageUrl(text) {
  if (!text) return null;
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

function extractLayoutJson(text) {
  const code = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
  if (code) {
    try { return JSON.parse(code[1]); } catch {}
  }
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start !== -1 && end > start) {
    try { return JSON.parse(text.slice(start, end + 1)); } catch {}
  }
  return null;
}

function maskKey(key) {
  if (!key) return '';
  return key.length <= 8 ? '****' : key.slice(0, 5) + '****' + key.slice(-4);
}

/* ---------- 业务处理 ---------- */

function validRefImages(refImages) {
  if (refImages === undefined || refImages === null) return [];
  if (!Array.isArray(refImages)) throw new Error('refImages 必须为数组（http URL 或 data:image base64）');
  for (const u of refImages) {
    if (typeof u !== 'string' || !(u.startsWith('http') || u.startsWith('data:image/'))) {
      throw new Error('refImages 元素必须是 http(s) URL 或 data:image base64 字符串');
    }
  }
  return refImages;
}

async function handleGenerateBackground(body) {
  const description = String(body.description || '').trim();
  if (!description) throw new Error('description 不能为空');
  const refImages = validRefImages(body.refImages);

  const provider = resolveProvider('dashscope', body.override);
  const imageUrl = await dashscopeGenerate(provider, {
    text: buildBgPrompt(description, refImages.length),
    refImages,
    size: body.size || '1125*2436',
  });
  return { imageUrl, size: body.size || '1125*2436' };
}

async function handleGenerateMaterial(body) {
  const description = String(body.description || '').trim();
  if (!description) throw new Error('description 不能为空');
  const refImages = validRefImages(body.refImages);

  const provider = resolveProvider('dashscope', body.override);
  const imageUrl = await dashscopeGenerate(provider, {
    text: buildMaterialPrompt(description),
    refImages,
    size: body.size || '1K',
  });
  return { imageUrl, greenScreen: true, size: body.size || '1K' };
}

async function handleGeneratePoster(body) {
  const topic = String(body.topic || '').trim();
  if (!topic) throw new Error('topic 不能为空');
  const fonts = Array.isArray(body.fonts) ? body.fonts.filter(f => typeof f === 'string') : null;

  const openaiProvider = resolveProvider('openai', body.override);
  const text = await openaiChat(openaiProvider, { content: buildPosterPrompt(topic, fonts) });

  const layout = extractLayoutJson(text);
  if (!layout || !Array.isArray(layout.elements) || layout.elements.length === 0) {
    const err = new Error('AI 返回内容未能解析出布局 JSON');
    err.raw = text.slice(0, 2000);
    throw err;
  }

  let backgroundImageUrl = null;
  const wantBg = body.generateBackground !== false; // 默认开启
  if (wantBg && layout.background) {
    try {
      const dashProvider = resolveProvider('dashscope', body.overrideDashscope || body.override);
      backgroundImageUrl = await dashscopeGenerate(dashProvider, {
        text: buildBgFromDescriptionPrompt(layout.background),
        size: '1125*2436',
      });
    } catch (e) {
      // 背景失败不阻断布局返回（与前端行为一致，退化为纯色背景）
      console.error('[api] 背景生成失败:', e.message);
    }
  }

  return {
    canvas: { width: 375, height: 812 },
    layout,
    background: { prompt: layout.background || null, imageUrl: backgroundImageUrl },
  };
}

/* ---------- HTTP 基础设施 ---------- */

function sendJson(res, status, obj) {
  const data = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
  });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > BODY_LIMIT) {
        reject(new Error('请求体超过 25MB 限制'));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('utf8');
        resolve(raw ? JSON.parse(raw) : {});
      } catch (e) {
        reject(new Error('请求体不是合法 JSON'));
      }
    });
    req.on('error', reject);
  });
}

const API_ROUTES = {
  'POST /api/generate/background': handleGenerateBackground,
  'POST /api/generate/material': handleGenerateMaterial,
  'POST /api/generate/poster': handleGeneratePoster,
};

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.cjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.md': 'text/markdown; charset=utf-8',
};

function serveStatic(req, res, pathname) {
  let rel = decodeURIComponent(pathname);
  if (rel === '/') rel = '/index.html';
  const filePath = path.normalize(path.join(ROOT, rel));
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403); res.end('Forbidden'); return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not Found');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = url.pathname;

  // CORS（便于外部页面/工具调用）
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  // 健康检查
  if (req.method === 'GET' && pathname === '/health') {
    return sendJson(res, 200, { ok: true, service: 'img2post', time: new Date().toISOString() });
  }

  // 查看当前配置（Key 脱敏）
  if (req.method === 'GET' && pathname === '/api/config') {
    const cfg = loadFileConfig();
    for (const k of Object.keys(cfg)) {
      cfg[k] = { ...cfg[k], apiKey: maskKey(cfg[k].apiKey) };
    }
    return sendJson(res, 200, cfg);
  }

  // AI 生成接口
  const route = API_ROUTES[`${req.method} ${pathname}`];
  if (route) {
    const started = Date.now();
    try {
      const body = await readBody(req);
      const result = await route(body);
      console.log(`[api] ${pathname} OK ${Date.now() - started}ms`);
      return sendJson(res, 200, { success: true, data: result });
    } catch (err) {
      console.error(`[api] ${pathname} FAIL ${Date.now() - started}ms:`, err.message);
      const payload = { success: false, error: err.message };
      if (err.raw) payload.raw = err.raw;
      const status = /未配置|不能为空|必须是|不是合法|超过/.test(err.message) ? 400 : 502;
      return sendJson(res, status, payload);
    }
  }

  if (pathname.startsWith('/api/')) {
    return sendJson(res, 404, { success: false, error: `unknown api: ${req.method} ${pathname}` });
  }

  // 其余走静态文件
  if (req.method === 'GET') return serveStatic(req, res, pathname);
  res.writeHead(405); res.end('Method Not Allowed');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`img2post 已启动: http://127.0.0.1:${PORT}`);
  console.log(`  UI:  http://127.0.0.1:${PORT}/`);
  console.log(`  API: POST /api/generate/background | /api/generate/material | /api/generate/poster`);
  console.log(`       GET  /health | /api/config`);
});
