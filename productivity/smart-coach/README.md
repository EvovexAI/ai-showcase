# 1009 · 智能陪练（学员版）

学员把资料丢进来 → EvoFlow **陪练师**帮你梳大纲、记进度、短问答陪练、答疑。  
本地面板只展示进度与内容，**不替代员工思考**。

端口 **8769**。陪练口径：[`prompts/coach-system.md`](prompts/coach-system.md)。

---

## 快速开始

```powershell
cd d:\dev\github\feishu_downloads/ai-showcase/productivity/smart-coach
py -3.12 scripts/web_server.py
# → http://127.0.0.1:8769
```

1. 面板上传资料（或把文件放进 `data/materials/`）  
2. 在 EvoFlow 对「陪练师」说：按资料梳一份学习大纲  
3. 再说：继续陪练 / 问概念  

接入 EvoFlow：见 [EVOFLOW-SETUP.md](EVOFLOW-SETUP.md)。  
整包清单：[`evoflow.organization.json`](evoflow.organization.json)（技能/扩展均为 `link: true`）。

---

## 分工

| 角色 | 谁 | 干什么 |
|------|-----|--------|
| 面板 | 本项目 `:8769` | 进度、资料、最近会话 |
| 大脑 | 员工 `smart-coach` | 梳 / 练 / 答，回写 `data/` |
| 资料 | 知识库「陪练资料库」 | 检索用 |

首版**不做**讲师后台、多学员、自动判分引擎。
