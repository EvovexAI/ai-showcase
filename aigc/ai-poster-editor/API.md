# img2post API 服务

`server.cjs` 把编辑器和 API 合成一个进程：静态站点（UI）+ REST API（AI 生成能力）。纯 Node 内置模块，零依赖。

## 启动

```bash
node server.cjs                # 默认 127.0.0.1:8899
IMG2POST_PORT=9000 node server.cjs   # 自定义端口（PowerShell: $env:IMG2POST_PORT=9000; node server.cjs）
```

- UI：`http://127.0.0.1:8899/`
- 健康检查：`GET http://127.0.0.1:8899/health`

## 配置

优先级：**请求体 override > api.config.json > 代码内置默认值**。

可选配置：复制 `api.config.example.json` 为 `api.config.json`，填入自己的 Key。`GET /api/config` 可查看当前生效配置（Key 自动脱敏）。

## 接口

所有接口：`Content-Type: application/json`；CORS 已全开；返回统一 `{ success, data | error }`。

### 1. 生成海报背景

```bash
curl -X POST http://127.0.0.1:8899/api/generate/background \
  -H "Content-Type: application/json" \
  -d '{"description":"蓝色渐变科技感背景，带光效"}'
```

返回：`{ "imageUrl": "https://…", "size": "1125*2436" }`

参数：

| 字段 | 必填 | 说明 |
|---|---|---|
| description | ✅ | 背景描述（中文即可） |
| refImages | ❌ | 参考图数组（http URL 或 data:image base64），作为风格参考 |
| size | ❌ | 默认 `1125*2436` |
| override | ❌ | `{ apiBase, apiKey, model }` 逐次覆盖 Ark 配置 |

### 2. 生成绿幕素材

```bash
curl -X POST http://127.0.0.1:8899/api/generate/material \
  -H "Content-Type: application/json" \
  -d '{"description":"一个可爱的卡通龙猫形象"}'
```

返回：`{ "imageUrl": "https://…", "greenScreen": true, "size": "1K" }`

说明：提示词强制纯绿背景 `#00C800`，拿到图后自行抠绿（参考前端 `ai-image.js` 的 `removeGreenBackground`）。参数同上（`size` 默认 `1K`）。

### 3. 一键生成海报

```bash
curl -X POST http://127.0.0.1:8899/api/generate/poster \
  -H "Content-Type: application/json" \
  -d '{"topic":"618年中大促 手机全场8折"}'
```

返回：

```json
{
  "canvas": { "width": 375, "height": 812 },
  "layout": { "background": "…背景描述…", "elements": [ { "type": "text", "left": 37, "top": 80, "width": 300, "content": "…", "fontSize": 48 } ] },
  "background": { "prompt": "…", "imageUrl": "https://…" }
}
```

参数：

| 字段 | 必填 | 说明 |
|---|---|---|
| topic | ✅ | 海报主题 |
| fonts | ❌ | 字体列表（数组），默认系统字体 |
| generateBackground | ❌ | 默认 `true`：按布局里的背景描述自动调 Ark 生成背景图；传 `false` 只出文字布局（省时省钱） |
| override | ❌ | 覆盖 OpenAI 兼容网关配置 |
| overrideArk | ❌ | 单独覆盖背景生成用的 Ark 配置（缺省回落 override） |

### 查看配置

```bash
curl http://127.0.0.1:8899/api/config
```

## 常见问题

| 现象 | 处理 |
|---|---|
| 400 `Ark 未配置` | 建 `api.config.json` 或请求里带 `override` |
| 502 `HTTP 401/403` | Key 无效或无模型权限 |
| 502 `model_not_found` | 网关上模型已下架，`GET /v1/models` 查可用模型后换名 |
| 502 `未能解析出布局 JSON` | 网关模型输出不是 JSON，换视觉/指令跟随更好的模型；返回体里带 `raw` 可看原始输出 |
| CORS/连接问题 | 网关是 HTTP 时参考 `proxy.cjs` 方案（见 SETUP.md） |
| PowerShell 里 curl 传 JSON 报错 | PowerShell 会吃引号，用 `Invoke-RestMethod` 或 `-d @body.json` |

## 与 UI 的关系

- 两者读的是**同一套上游服务**（豆包 Agent Plan / OpenAI 兼容网关），但配置相互独立：UI 存浏览器 localStorage（设置弹窗），API 存 `api.config.json`
- API 与 UI 可同时用（同端口，互不干扰）；也可以只用 API（无头集成到内容流水线）
