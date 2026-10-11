# img2post — 海报编辑器

纯前端海报/图片设计工具，集成 AI 背景生成、AI 素材生成、AI 布局优化。

## Project

- **Stack**: Vanilla HTML/CSS/JS，零构建工具，零框架
- **入口**: `index.html` — 直接在浏览器打开即可运行
- **唯一外部依赖**: html2canvas@1.4.1 CDN（用于截图/导出辅助）
- **AI 后端**: 通义万象（DashScope，图片生成）+ OpenAI 兼容接口（文本/多模态，布局优化与一键生成），均可配置；详见 `SETUP.md`
- **本地服务**: `node server.cjs` — UI + REST API 一体（见 `API.md`）

## Commands

无构建/测试/lint 命令。开发方式：

- **运行**: 直接用浏览器打开 `index.html`，或用任意静态文件服务（如 `npx serve .`）
- **部署**: 将整个目录放到任意静态服务器即可

## Architecture

IIFE 模块模式，每个 JS 文件是一个自执行闭包，挂载到 `window`：

| 文件 | 导出对象 | 职责 |
|------|----------|------|
| `js/canvas.js` | `Canvas` | 画布 DOM、背景图设置、缩放（10%~400%）、适应窗口 |
| `js/elements.js` | `Elements` | 文字/图片元素的增删、层级移动、选中管理、字体检测 |
| `js/drag.js` | `Drag` | Pointer Events 统一鼠标/触屏拖拽移动 + 控制点缩放 |
| `js/properties.js` | `Properties` | 右侧属性面板：字体/颜色/大小/透明度/对齐/艺术效果 |
| `js/export.js` | `Export` | Canvas 2D 手动绘制导出 PNG/JPG |
| `js/layout.js` | `Layout` | JSON 格式导入/导出海报布局（含背景和元素序列化） |
| `js/ai-gen.js` | `AiGen` | AI 背景生成：提示词 → 通义万象/OpenAI 兼容流式 → 设为画布背景 |
| `js/ai-image.js` | `AiImage` | AI 素材生成：绿幕背景生成 → 客户端抠绿 → 透明 PNG |
| `js/ai-optimize.js` | `AiOptimize` | 截图 + 布局 JSON → AI 视觉分析 → 返回优化布局 → 可撤回 |
| `js/app.js` | — | DOMContentLoaded 入口：绑定所有按钮事件、键盘快捷键 |

**数据流**: `app.js` 串联所有模块 → 用户操作 → 模块更新 DOM → `Canvas` 画布为单一真相源（375×812px）

## Conventions

- **模块模式**: 每个 JS 文件用 `const X = (() => { ... })();` 闭包封装，避免全局污染
- **DOM 操作**: 直接操作 DOM，不用虚拟 DOM；用 `document.getElementById` 获取元素
- **样式**: CSS 变量定义在 `:root`，浅色主题（大厂风），画布逻辑尺寸 375×812px
- **AI API**: OpenAI 兼容 `/chat/completions`（SSE 流式）+ DashScope 多模态生成；Authorization header 用 `Bearer {API_KEY}`
- **元素 ID**: 用 `el-` 前缀 + 自增计数器生成唯一 ID
- **文件命名**: 全小写，短横线分隔
- **编码**: 中文注释文档，UTF-8

## Notes

- 本仓库**不内置任何 API Key / 内网地址**：UI 在设置弹窗配置（存 localStorage），API 服务走 `api.config.json` 或环境变量
- 绿幕抠除阈值在 `ai-image.js` 的 `GREEN_THRESHOLD` 和 `GREEN_RATIO` 常量
- 布局序列化版本号在 `layout.js` 的 `SCHEMA_VERSION`
- 配置存储在 localStorage `img2post_ai_config_v3`
