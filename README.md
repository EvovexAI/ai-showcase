# AI Demos — EvovexAI 实战演示项目集

EvovexAI 的 AI 应用实战演示合集：小而完整、开箱即跑、无内置密钥。

## 项目列表

### img2post — AI 海报编辑器（`img2post/`）

纯前端海报/图片设计工具 + 轻量 API 服务，展示如何把多种 AI 能力组合成一个可用的产品：

- 🎨 **AI 背景生成**：文字描述 → 通义万象（DashScope）生图 → 一键设为画布背景
- 🖼 **AI 素材生成**：绿幕图生成 + 浏览器端自动抠绿 → 透明 PNG 素材
- 📐 **AI 布局优化**：截图 + 布局 JSON → 视觉模型分析 → 返回排版 diff → 预览/撤回（多轮对话）
- 🤖 **一键生成海报**：输入主题 → 布局 JSON + 自动配图 → 完整海报
- 📤 常规编辑器能力：拖拽/缩放/图层面板/艺术字效果/导出 PNG/JPG/布局 JSON

技术栈：Vanilla HTML/CSS/JS（零框架零构建）+ Node 内置模块（零依赖 API 服务）。

```bash
cd img2post
node server.cjs        # http://127.0.0.1:8899 — UI 与 REST API 同端口
```

配置自己的 API Key：见 `img2post/SETUP.md`（UI 弹窗 / api.config.json / 环境变量三种方式）。API 接口文档见 `img2post/API.md`。

> ⚠️ 本仓库不包含任何 API Key 或内网地址，请使用自己的账号与服务。

## 原则

- 每个项目尽量零依赖或极少依赖，克隆即跑
- 不硬编码任何密钥、内网 IP、公司域名
- 每个项目附 SETUP/使用文档

## License

MIT
