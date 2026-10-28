---
name: smart-coach
description: >-
  学员智能陪练：梳资料大纲、记录进度、短问答培训、知识库答疑。
  本地面板 :8769；权威提示词 prompts/coach-system.md。
  Use for 陪练、培训、学习进度、答疑、outline、coach。
---

# 智能陪练（学员）

项目根：`D:\dev\github\feishu_downloads/ai-showcase/productivity/smart-coach`

## 分工

| 组件 | 职责 |
|------|------|
| 本地 `:8769` | 资料、大纲、进度、会话展示与 API |
| 员工陪练师 | 梳 / 练 / 答；回写本地真源 |
| 知识库「陪练资料库」 | 资料检索 |
| `prompts/coach-system.md` | 怎么问、怎么记进度 |

## Agent 标准作业

```
1. GET http://127.0.0.1:8769/api/health （必要时起 py -3.12 scripts/web_server.py）
2. 意图：梳资料 | 开练 | 答疑 | 查进度
3. 梳：读 materials/KB → 写 data/outline.json → 合并 progress → 汇报
4. 练：GET /api/overview → 短问 1～3 轮 → POST /api/sessions + PUT /api/progress
5. 答：knowledge 检索 → 结合 next_focus 回答
6. 汇报：percent / 刚练什么 / next_focus / 路径
```

## 关键 API

- `GET /api/overview`
- `GET|PUT /api/progress`
- `GET|PUT /api/outline`（PUT body 为 outline 对象或 `{ "outline": {...} }`）
- `POST /api/materials`（multipart 文件，或 JSON `{ name, content }`）
- `POST /api/sessions`（`{ title, body, next_focus?, mastery_updates?, weak_points? }`）

Web：`http://127.0.0.1:8769`
