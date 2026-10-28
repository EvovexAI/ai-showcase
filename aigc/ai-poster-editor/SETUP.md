# img2post 配置指南

> 本文档说明如何配置 img2post 海报编辑器的 AI 功能。支持两种 Provider：
>
> | Provider | 类型标识 | 负责的 AI 功能 |
> |---|---|---|
> | **豆包 Agent Plan**（火山方舟 Ark） | `ark` | 🎨 AI 背景生成、🖼 AI 图片生成（绿幕素材） |
> | **NewAPI**（OpenAI 兼容网关） | `openai` | 📐 AI 布局优化、🤖 AI 一键生成海报 |
>
> 四个功能模块相互独立、分别配置，配置保存在浏览器 localStorage，改一处不影响其他。
>
> 本项目同时内置 REST API 服务（`server.cjs`），接口用法见 `API.md`。

---

## 一、快速开始（3 分钟）

1. 启动服务：在项目目录执行 `node server.cjs`（推荐，UI+API 一体），浏览器打开 `http://127.0.0.1:8899`
2. 右上角 **⚙ 设置**，按「模块 × Provider 对照表」逐项填写
3. 点弹窗关闭按钮（✕）即自动保存，无需其他操作

### 模块 × Provider 对照表

| 设置弹窗分区 | 建议类型 | 需要填 | 作用 |
|---|---|---|---|
| 🎨 AI 背景生成 | 豆包 Agent Plan | API Base / API Key / Model | 输入描述生成海报背景图 |
| 🖼 AI 图片生成 | 豆包 Agent Plan | API Base / API Key / Model | 生成绿幕素材并自动抠成透明 PNG |
| 📐 AI 布局优化 | NewAPI | API Base / API Key / Model | 截图 + 对话式调整排版（需视觉模型） |
| 🤖 AI 一键生成 | NewAPI | API Base / API Key / Model | 输入主题直接产出完整海报 |

> 注意：一键生成的海报背景，内部会调用「AI 背景生成」模块的豆包配置去画背景图。所以若豆包没配好，一键生成仍能产出文字布局，但背景会退化为纯色。

---

## 二、获取 API Key

### 1. 豆包 Agent Plan（火山方舟 Ark）

前置：已订阅**火山方舟 Agent Plan** 套餐（生图计费走套餐 AFP，不产生按量费用；务必不要使用后付费方式）。

1. 登录火山方舟控制台 → **API 密钥管理** → 创建 **Agent Plan 专属 API Key**（其他方舟 Key 如 Coding Plan Key 不能用于 Agent Plan）
2. 专属 Base URL（必须含 `/api/plan/v3`，与其他方舟端点不可混用）：`https://ark.cn-beijing.volces.com/api/plan/v3`
3. 生图模型：`doubao-seedream-5-0-pro`（分辨率支持 1K / 1.5K / 2K）

**填法**：

| 字段 | 填什么 |
|---|---|
| 类型 | 豆包 Agent Plan |
| API Base | `https://ark.cn-beijing.volces.com/api/plan/v3`（默认值，不用改） |
| API Key | Agent Plan 专属 Key |
| Model | `doubao-seedream-5-0-pro` |

参考图会以 `image_url`（URL 或 base64 data URL）随 `prompt` 数组发送，支持单/多图参考。

### 2. NewAPI（OpenAI 兼容网关）

任意暴露 OpenAI 协议的网关均可：自建 NewAPI / OneAPI、OpenRouter、硅基流动、各厂商 OpenAI 兼容端点。仓库默认值指向一台内部测试服务器（`49.234.178.192:3000`），**请务必替换为你自己的**。

**前置要求**：
- 支持 SSE 流式 `POST /v1/chat/completions`
- 布局优化需要**视觉模型**（要读海报截图，`image_url` 传 JPEG base64）；一键海报用文本模型即可

**填法**：

| 字段 | 填什么 |
|---|---|
| 类型 | NewAPI |
| API Base | 如 `https://你的网关/v1`（**必须含 `/v1`**，代码会自动拼 `/chat/completions`） |
| API Key | 网关签发的 Key |
| Model | 视觉模型如 `doubao-seed-2.1-turbo`、`gpt-4o`、`qwen-vl-max` 等 |

**CORS 提醒**：页面从 `http://127.0.0.1:8899` 发请求到别的域/端口时可能被浏览器拦截。两种解法：
1. 启动本项目自带代理：`node proxy.cjs`（监听 3459），API Base 改成 `http://localhost:3459/你的网关host:端口/v1`；
2. 网关侧返回 `Access-Control-Allow-Origin` 响应头。

---

## 三、逐模块详解

打开 **⚙ 设置**，切换「类型」下拉会自动填入该类型模板默认值，之后把 API Key 改成自己的即可。

### 🎨 AI 背景生成

- 类型：豆包 Agent Plan；Base/Key/Model 见上表
- 链路：输入描述（可传参考图，自动转 base64）→ Ark 图片生成 → 提取图片 URL → 设为画布背景
- 提示词已内置「禁止出现文字」等约束，无需手写

### 🖼 AI 图片生成（绿幕素材）

- 配置与背景生成一致
- 差异：提示词强制纯绿背景 `#00C800`，返回后浏览器端自动抠绿 → 透明 PNG 插入画布
- 阈值可调：`js/ai-image.js` 顶部 `GREEN_THRESHOLD`、`GREEN_RATIO`

### 📐 AI 布局优化

- 类型：NewAPI；**Model 必须是视觉模型**
- 链路：html2canvas 截图（JPEG base64）+ 布局元素摘要 → 首轮请求 → AI 返回 diff JSON → 预览/确认/撤回；后续轮次为纯文本多轮对话
- 支持连续对话微调，支持多次撤回

### 🤖 AI 一键生成海报

- 类型：NewAPI；文本模型即可，选多模态模型可支持传参考图
- 链路：主题 + 可用字体 → AI 返回布局 JSON（背景描述 + 文字元素）→ 自动调用豆包生成背景 → 按布局摆放文字

---

## 四、验证与排查

**自测清单**（配好一项测一项）：

1. 背景生成：输入「蓝色渐变科技感背景」→ 出图 → 确认后成为画布背景
2. 绿幕素材：输入「一个可爱卡通形象」→ 出图 → 确认后画布出现透明 PNG
3. 布局优化：画布放几个文字 → 打开优化 → 输入「标题放大居中」→ 出现分析文字 + 底部预览条 → 确认生效
4. 一键海报：输入主题 → 流式输出结束 → 画布出现完整海报
5. 各弹窗标题旁的 Provider 徽章应显示当前配置的名称

**排查**：F12 → Network → 筛 Fetch/XHR，看失败请求：

| 现象 | 原因 |
|---|---|
| 401 / 403 | Key 错误或无该模型权限 |
| 404 | API Base 路径不对（检查是否少 `/v1`） |
| CORS 报错 | 用上面的代理方案或改网关响应头 |
| `model not found` | 模型名与网关/账号不匹配（先 `GET /v1/models` 看可用列表） |
| 完全没有请求发出 | Console 看报错；先点设置里「↺ 恢复默认」再重配 |

---

## 五、进阶：修改代码默认值

全部默认值集中在 `js/config.js` 的 `TPL` / `DEFAULTS`。改这里只影响「从未保存过配置」的浏览器（首次加载）；已保存的 localStorage 不会被覆盖。

```js
const TPL = {
  ark: {
    type: 'ark',
    name: '豆包 Agent Plan',
    apiBase: 'https://ark.cn-beijing.volces.com/api/plan/v3',
    apiKey: '你的 Agent Plan 专属 Key',
    model: 'doubao-seedream-5-0-pro',
  },
  newapi: {
    type: 'openai',
    name: 'NewAPI',
    apiBase: 'https://your-gateway.example.com/v1',
    apiKey: 'sk-xxxx',
    model: 'doubao-seed-2.1-turbo',
  },
};

const DEFAULTS = {
  aiBg:       { ...TPL.ark },     // AI 背景生成
  aiImage:    { ...TPL.ark },     // AI 图片生成
  aiOptimize: { ...TPL.newapi },  // AI 布局优化
  aiPoster:   { ...TPL.newapi },  // AI 一键生成海报
};
```

配置存储键：localStorage `img2post_ai_config_v3`。

API 服务的默认值在 `server.cjs` 顶部 `DEFAULT_TPL`（或用 `api.config.json` 覆盖，见 `API.md`）。

---

## 六、安全提醒

- 硬编码在前端 JS 里的默认 Key 任何人可见，仅限开发测试。正式部署请：① 换成自己的 Key；② 更推荐把请求改指自己的后端代理，Key 放服务端。
- localStorage 配置仅存本机浏览器，不会上传。
