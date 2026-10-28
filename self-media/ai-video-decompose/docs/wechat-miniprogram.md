# 起号 · 微信小程序产品方案

> 目标：云端提供 **链接下载（视频/图）** + **爆款拆解**，变现以激励视频广告为主。  
> 本文覆盖：架构、用户隔离、API、上架与合规。  
> 后端可复用现有 `起号/scripts/` 流水线。

---

## 1. 产品定位

| Tab | 功能 | 用户价值 |
|-----|------|----------|
| **保存到手机** | 贴分享链接 → 解析视频/图集 → 看广告 → 存相册 | 大众刚需，获客 |
| **爆款拆解** | 贴链接 → 口播转写 + 一句一帧 + 章节 | 起号人群，留存与差异化 |

对外一句话：**「贴抖音分享链接，保存素材或看懂爆款结构。」**

---

## 2. 用户怎么用（端到端）

### 2.1 下载流程

```
wx.login 静默登录
  → 用户粘贴分享文案/短链
  → POST /api/v1/parse（解析资源列表，不扣次）
  → 展示：视频预览 / 图集多选
  → 用户点「保存」→ 弹出激励视频广告
  → 广告 onClose 且 isEnded → POST /api/v1/download/consume（扣 1 次）
  → 返回临时下载 URL（HTTPS，域名在小程序 download 白名单）
  → wx.downloadFile → wx.saveVideoToPhotosAlbum / saveImageToPhotosAlbum
```

### 2.2 拆解流程

```
贴链接 → 选关键帧模式（一句一帧 / 自定义 N 帧）
  → 看广告或会员免广告
  → POST /api/v1/analyze → 返回 job_id
  → 轮询 GET /api/v1/jobs/{id}
  → 完成后：章节列表、口播、关键帧（逻辑同本地 Web 面板）
  → 复制文案 / 保存关键帧图（不下发整片 mp4 也可）
```

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│ 微信小程序（WXML + 原生 / uni-app）                        │
│  - 登录、贴链、广告、相册保存、拆解报告 UI                    │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS + JWT
┌──────────────────────────▼──────────────────────────────┐
│ API 服务（FastAPI / Node，建议 Python 复用现有脚本）          │
│  - 鉴权中间件（user_id 注入）                               │
│  - 配额 / 广告核销                                         │
│  - 任务入队                                                │
└───────┬──────────────────────────────┬──────────────────┘
        │                              │
┌───────▼────────┐            ┌────────▼─────────┐
│ PostgreSQL     │            │ Redis 队列        │
│ users/jobs/    │            │ Bull / Celery     │
│ quotas/ads     │            └────────┬─────────┘
└────────────────┘                     │
                              ┌────────▼─────────────────┐
                              │ Worker（Docker）          │
                              │ 复用 download-douyin.py  │
                              │      analyze_douyin.py   │
                              └────────┬─────────────────┘
                                       │
                              ┌────────▼─────────────────┐
                              │ 对象存储 COS/OSS          │
                              │ users/{uid}/jobs/{jid}/  │
                              │ 临时文件 TTL 7 天自动删   │
                              └──────────────────────────┘
```

与本地版关系：

- **同一套** `download` / `analyze` 逻辑，Worker 内 `import` 或子进程调用。
- 本地 `web_server.py` 可视为「无登录的单用户版」；云端加 **用户维度 + 队列 + OSS**。

---

## 4. 用户权限隔离（重点）

小程序没有传统账号密码，以 **微信 openid** 为身份根。

### 4.1 身份模型

| 字段 | 来源 | 用途 |
|------|------|------|
| `openid` | `wx.login` → 后端 `code2session` | 单小程序内用户唯一 ID |
| `unionid` | 同一开放平台下多应用统一（需绑定开放平台） | 可选，后期多端互通 |
| `internal_user_id` | 服务端 UUID | 数据库主键，不暴露 openid |

**原则：所有业务数据必须带 `user_id`，任何 API 不得信任客户端传的 user_id。**

### 4.2 登录与会话

```
1. 小程序：wx.login() → code
2. POST /api/v1/auth/wechat { code }
3. 服务端：code2session → openid + session_key
4. 查/建 users 表 → 签发 JWT（access 2h + refresh 30d）
5. 后续请求：Authorization: Bearer <token>
```

JWT payload 示例：

```json
{ "sub": "usr_uuid", "openid_hash": "...", "iat": 0, "exp": 0 }
```

### 4.3 数据隔离规则

**存储路径（OSS / 本地 Worker 缓存）：**

```
s3://bucket/users/{user_id}/jobs/{job_id}/video.mp4
s3://bucket/users/{user_id}/jobs/{job_id}/analysis/report.json
s3://bucket/users/{user_id}/jobs/{job_id}/scenes/sent_0001.jpg
```

**数据库：每张业务表含 `user_id`，并建联合索引。**

| 表 | 隔离 |
|----|------|
| `jobs` | `WHERE user_id = ?` |
| `parse_cache` | 可按 link_hash 全局缓存解析结果，但 **下载/拆解任务** 必须挂 user_id |
| `quota_ledger` | 按 user_id 记次数 |
| `ad_rewards` | 按 user_id + 广告单元去重防刷 |

**API 鉴权伪代码：**

```python
def get_job(job_id: str, current_user: User):
    job = db.get_job(job_id)
    if job.user_id != current_user.id:
        raise HTTPForbidden()  # 404 亦可，避免枚举
    return job
```

### 4.4 媒体 URL 安全

- 禁止 `GET /media/{job_id}/...` 无鉴权公开链。
- 推荐：**带签名的临时 URL**（OSS STS 或自建 HMAC，有效期 15 分钟）。
- 小程序 `downloadFile` 的域名必须在微信公众平台配置 **downloadFile 合法域名**。

### 4.5 配额与防刷

| 机制 | 说明 |
|------|------|
| 每日免费次数 | 如：下载 3 次/天，拆解 1 次/天 |
| 激励广告加次 | 看完广告 `ad_unit_id` 回调核销 +1 |
| 会员 | `users.plan = pro`，跳过广告与限额 |
| 频率限制 | 同一 user_id：parse 10 次/分钟 |
| 链接去重 | 同一用户 5 分钟内同一 aweme_id 不重复入队 |
| 设备风控 | 可选：记录 `device_info`，异常批量注册封禁 |

广告核销流程（防止客户端伪造）：

```
客户端：激励视频 onClose(res) → 仅当 res.isEnded
  → POST /api/v1/ads/reward { ad_unit_id, placement: "download" }
服务端：
  - 校验今日该 placement 核销次数上限
  - 可选：接入微信广告服务端回调（若有）
  - quota_ledger +1
  - 返回 reward_token（一次性，5 分钟内用于 consume 接口）
下载：POST /api/v1/download/consume { job_id, reward_token }
```

### 4.6 多租户总结清单

- [ ] 所有表有 `user_id`，外键 + 索引
- [ ] JWT 中间件统一注入当前用户
- [ ] 查询/删除/下载均校验 `job.user_id == current_user.id`
- [ ] OSS 路径含 `user_id` 前缀
- [ ] 临时 URL 短期有效
- [ ] 配额账本按用户独立
- [ ] 日志打 `user_id`、`job_id`，便于审计

---

## 5. 数据库草图（PostgreSQL）

```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  openid        VARCHAR(64) UNIQUE NOT NULL,
  unionid       VARCHAR(64),
  nickname      TEXT,
  avatar_url    TEXT,
  plan          VARCHAR(16) DEFAULT 'free',  -- free | pro
  created_at    TIMESTAMPTZ DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

CREATE TABLE jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id),
  type          VARCHAR(16) NOT NULL,  -- download | analyze
  status        VARCHAR(16) NOT NULL, -- queued|running|done|error
  share_text    TEXT,
  source_url    TEXT,
  aweme_id      VARCHAR(32),
  keyframe_mode VARCHAR(16),
  frame_count   INT,
  progress      INT DEFAULT 0,
  message       TEXT,
  storage_prefix TEXT,                -- users/{uid}/jobs/{jid}/
  created_at    TIMESTAMPTZ DEFAULT now(),
  finished_at   TIMESTAMPTZ
);
CREATE INDEX idx_jobs_user_created ON jobs(user_id, created_at DESC);

CREATE TABLE quota_ledger (
  id         BIGSERIAL PRIMARY KEY,
  user_id    UUID NOT NULL REFERENCES users(id),
  kind       VARCHAR(16) NOT NULL,  -- download | analyze
  delta      INT NOT NULL,           -- +1 / -1
  reason     VARCHAR(32),          -- daily_free | ad_reward | consume | admin
  ref_id     UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ad_rewards (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id),
  placement  VARCHAR(32) NOT NULL,
  token      VARCHAR(64) UNIQUE NOT NULL,
  used       BOOLEAN DEFAULT false,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 6. API 一览（v1）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/wechat` | 否 | code 换 JWT |
| POST | `/api/v1/parse` | 是 | 解析链接，返回视频/图列表（预览） |
| POST | `/api/v1/download` | 是 | 创建下载任务（可先 parse 复用） |
| POST | `/api/v1/download/consume` | 是 | 核销 reward_token，返回签名下载 URL |
| POST | `/api/v1/analyze` | 是 | `{ share_text, keyframe_mode, frame_count }` |
| GET | `/api/v1/jobs` | 是 | 当前用户任务列表 |
| GET | `/api/v1/jobs/{id}` | 是 | 任务状态 / 结果（校验 user_id） |
| GET | `/api/v1/projects/{id}` | 是 | 拆解详情（同本地 project_payload） |
| POST | `/api/v1/ads/reward` | 是 | 看完广告领取 token |
| GET | `/api/v1/quota` | 是 | 今日剩余次数 |

Worker 内部调用（与本地一致）：

```python
# 伪代码
project = download(url, share_text=share_text)
analyze(project, analysis_dir(project), full=True,
        keyframe_mode="transcript", vision_prep=False)
upload_tree_to_oss(f"users/{user_id}/jobs/{job_id}/", project)
```

---

## 7. 小程序页面结构（MVP）

```
pages/
  index/          # 贴链接 + Tab（保存 | 拆解）
  parse-result/   # 预览视频/图集，保存按钮
  analyze-progress/
  analyze-report/ # 章节 / 口播 / 关键帧（复用 web 交互逻辑）
  history/        # 我的记录（仅当前用户）
  mine/           # 次数、会员、协议
```

---

## 8. 个人能不能上架？怎么上架？

### 8.1 结论先说

| 问题 | 答案 |
|------|------|
| **个人能注册小程序吗？** | **能**。微信开放平台支持**个人主体**注册（需身份证实名）。 |
| **个人能上架这类产品吗？** | **有机会，但类目要选对**；纯「去水印搬运下载」审核风险高，需包装与合规。 |
| **比个人更稳的选择？** | **个体工商户**或**企业主体**，类目更广、过审率更高。 |

官方个人开放类目查询（以提交时后台为准）：  
https://developers.weixin.qq.com/miniprogram/product/material/#个人主体小程序开放的服务类目

### 8.2 推荐类目策略

| 主体 | 建议类目 | 说明 |
|------|----------|------|
| **个人** | `工具 > 效率工具` 或 `工具 > 图片/视频处理` | 强调「素材整理、学习笔记、效率工具」 |
| **个体工商户** | 同上 + 部分生活服务 | 过审更稳，可接支付 |
| **企业** | 可按需扩展会员、支付 | 适合正式商业化 |

**避坑：**

- 文案避免「去水印」「破解」「搬运」「批量下载竞品」等敏感表述；改为 **「保存素材」「学习收藏」「内容整理」**。
- **口播转写 / 智能拆解** 若强调 AI，可能触发 **「深度合成」** 类目要求——个人主体往往**不支持**，建议：
  - 产品文案写「语音转文字 · 学习笔记」而非「AI 问答」；
  - 或改 **个体工商户/企业** 主体；
  - 拆解 Tab 一期可弱化，先上「保存到手机」过审，二期再加拆解。
- 用户协议、隐私政策**必填**（收集链接、处理媒体、存储 openid）。
- 配置 **用户内容声明**：仅供个人学习，不得用于侵权传播。

### 8.3 个人上架步骤（实操）

```
1. 注册微信公众平台账号
   https://mp.weixin.qq.com/
   选择「小程序」→ 主体类型「个人」→ 管理员微信扫码 → 身份证实名

2. 获取 AppID
   开发 → 开发管理 → 开发设置

3. 配置服务器
   - request 合法域名（API HTTPS）
   - downloadFile 合法域名（媒体文件）
   - 上传小程序代码需 HTTPS，TLS 1.2+

4. 注册微信开放平台（可选）
   - 如需 unionid、多端统一，将小程序绑定到开放平台

5. 开发
   - 微信开发者工具 + 真机调试
   - 实现 wx.login、激励视频组件（adunit 需在流量主开通后创建）

6. 类目与备案
   - 设置 → 基本设置 → 服务类目（选工具类）
   - 按提示完成小程序备案（国内服务器必须）

7. 提交审核
   - 上传代码 → 填写版本说明、测试账号
   - 审核通常 1–7 天

8. 发布
   - 审核通过后「全量发布」

9. 流量主（广告）
   - 累计独立访问用户达标后申请开通（具体门槛以公众平台为准）
   - 创建激励视频广告位 → adunit-id 填入小程序
```

### 8.4 费用参考

| 项目 | 个人 |
|------|------|
| 小程序注册 | 免费 |
| 微信认证（个人） | 不支持企业式对公认证；个人无 300 元认证费那一套 |
| 服务器 + OSS + 带宽 | 按量，MVP 约 ¥100–500/月 起 |
| 域名 + SSL | ¥几十/年 |
| 个体工商户注册 | 若需要，各地不同，通常可低成本办理 |

---

## 9. 合规与风险（必读）

1. **版权**：用户仅下载自己有权的素材或用于个人学习；协议中免责声明 + 举报入口。
2. **平台规则**：抖音等平台禁止未授权抓取——技术服务方需有接口失效预案，勿承诺永久可用。
3. **用户隐私**：说明收集 openid、分享链接、临时存储媒体；提供删除账号/记录能力。
4. **内容安全**：可对解析出的标题/口播接文本审核 API（腾讯云 CMS），违规拒绝任务。
5. **深度合成**：若拆解含「AI 生成描述」，个人主体易被拒——拆解一期用规则/heuristic，二期再评估主体升级。

---

## 10. 实施分期建议

### Phase 1（4–6 周）— 能上架、能赚钱

- [ ] 个人/个体户主体 + 工具类目
- [ ] 登录 + user_id 隔离 + 配额
- [ ] 贴链 → 解析视频/图 → 激励广告 → 存相册
- [ ] 任务队列 + OSS 临时存储
- [ ] 隐私政策、用户协议

### Phase 2 — 差异化

- [ ] 拆解 Tab（复用 `analyze_douyin.py`，默认一句一帧）
- [ ] 章节弹窗、作品信息（同本地 Web）
- [ ] 会员免广告（需企业/个体户 + 微信支付）

### Phase 3 — 规模化

- [ ] 多 Worker、GPU 转写、缓存热门 aweme 解析
- [ ] 风控、监控、成本报表
- [ ] 可选：抖音以外平台（快手、小红书）统一 parse 层

---

## 11. 与现有仓库的代码映射

| 云端模块 | 复用本地文件 |
|----------|----------------|
| 链接解析 / 下载 | `scripts/download-douyin.py` |
| 拆解 | `scripts/analyze_douyin.py` |
| 路径约定 | `scripts/paths.py`；云存储前缀 `users/{openid}/jobs/{jobId}/` |
| 报告结构 | 与 `web_server.py` 的 `project_payload` 对齐（chapters/segments/scenes） |
| 参考 UI 交互 | `web/index.html` + `web/assets/app.js` |

**已落地目录（2026-07-15）：**

```
起号/
├── miniprogram/              # 原生小程序（微信开发者工具打开此目录）
│   ├── pages/                # 拆解 / 进度 / 报告 / 记录 / 我的 / 协议
│   ├── cloudfunctions/       # login、createAnalyzeJob、getJob…
│   ├── database/             # 集合权限草案
│   └── utils/config.js       # CLOUD_ENV、MOCK_ANALYZE
├── cloud-run/                # 云托管 Docker Worker
│   ├── Dockerfile
│   ├── server.py             # POST /internal/analyze → 复用 scripts
│   └── docker-compose.yml
└── docs/
    └── wechat-miniprogram.md
```

详细开通与上传步骤见：`miniprogram/README.md`、`cloud-run/README.md`。

---

## 12. 今晚可上传检查清单

1. [ ] 微信公众平台 AppID；个人主体类目选「工具」类  
2. [ ] 开发者工具打开 `起号/miniprogram`，开通云开发，填写 `utils/config.js` → `CLOUD_ENV`  
3. [ ] 创建集合 `jobs`、`users`；`jobs` 复合索引 `_openid` + `createdAt desc`  
4. [ ] 上传部署全部云函数；修改 `INTERNAL_TOKEN`  
5. [ ] 为 `updateJob`、`uploadFile` 开启 HTTP 访问，写入云托管环境变量 `CF_HTTP_BASE`  
6. [ ] 构建并部署 `cloud-run` 服务，名称与 `CLOUD_RUN_SERVICE`（默认 `analyze-worker`）一致  
7. [ ] 真机：贴链拆解 → 报告 → 关键帧存相册  
8. [ ] （可选）无 Worker 时设 `MOCK_ANALYZE: true` 先交审 UI  
9. [ ] 隐私政策 / 用户协议已内置；后台「用户隐私保护指引」勾选收集项（openid、剪切板若使用）  
10. [ ] 审核文案写「口播笔记 / 学习拆解」，避免「去水印」

---

## 13. 决策建议（给你）

| 若你… | 建议 |
|--------|------|
| 想最快验证、少办证 | **个人主体** + 云开发；文案走学习笔记 |
| 想长期做拆解 + 会员 | 直接 **个体工商户**，类目和支付一次到位 |
| 担心审核 | 不做「去水印」宣传；可先 `MOCK_ANALYZE` 演示流程再开真拆解 |

---

*文档版本：2026-07-15 · 云开发小程序 MVP 已落地*
