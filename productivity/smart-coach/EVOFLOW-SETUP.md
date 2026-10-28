# 智能陪练 · EvoFlow 接入（学员版）

> 打开 EvoFlow，把本文档发给助手，说：「**按这个文档帮我完成接入**」。

前提：本项目能启动（`py -3.12 scripts/web_server.py` → `http://127.0.0.1:8769`）。

---

## 接入总览

### 推荐：一包导入（资源包）

项目根已有 [`evoflow.organization.json`](evoflow.organization.json)：扩展 + 技能（`link: true` 挂源目录）+ 陪练师 + 陪练资料库。

在 EvoFlow：**设置 → 资源中心 → 导入本地**，选本项目文件夹；或对助手说：

> 请用组织安装接口导入本项目（读 evoflow.organization.json）。

技能与扩展都是 **folder-link**：改仓库即生效，不会拷进 `skills/custom` 实体副本。

### 或分 4 步

| 步骤 | 一句话 |
|------|--------|
| 1 | 安装**扩展应用** — 侧栏出现「智能陪练」面板 |
| 2 | 安装**技能** `smart-coach`（`install-from-path` 且 `link: true`） |
| 3 | 创建**员工**「陪练师」并挂上技能 / 知识库 |
| 4 | 创建**知识库**「陪练资料库」，同步 `data/materials/` |

也可对照仓库 [`../evoflow-onboarding-kit`](../evoflow-onboarding-kit) 的 register-extension / sync-kb / hire-employee 脚本。

---

## 第 1 步：扩展应用

> 请把本项目（本文档所在文件夹）安装为 EvoFlow 扩展应用。

完成：侧栏扩展里出现「智能陪练」，能打开学员面板。

---

## 第 2 步：技能

> 请把本项目 `skills/smart-coach` 安装为 EvoFlow 技能并启用。

完成：技能列表有 `smart-coach`。

---

## 第 3 步：员工

> 请创建员工：名字「陪练师」，agent_code `smart-coach`，挂 skill `smart-coach`，  
> 职责是梳资料大纲、短问答陪练、答疑，并读写本地面板进度（8769）。

可用仓库内 [`employees/smart-coach.json`](employees/smart-coach.json) 与 [`agents/`](agents/) 作为模板。

完成：员工列表有「陪练师」（active）。

---

## 第 4 步：知识库

> 请创建知识库「陪练资料库」，把本项目 `data/materials` 设为同步源（import-folder / upsert），  
> 并把陪练师绑定到该库。

完成：库内能搜到已上传资料；之后面板上传新文件可再 sync / 让员工提醒导入。

---

## 日常话术（学员）

| 你想… | 跟陪练师说 |
|--------|------------|
| 梳大纲 | 按我的资料梳一份学习大纲 |
| 开练 | 继续陪练 |
| 答疑 | 「某某」是什么意思？（结合我当前进度） |
| 查进度 | 我现在学到哪了 |

面板按钮「请陪练师继续」会给出可复制话术；真正开练仍在 EvoFlow 聊天里由员工完成。

---

## 完成自测

- [ ] 面板能打开，进度区可见  
- [ ] 技能 `smart-coach` 已启用  
- [ ] 员工「陪练师」在职  
- [ ] 知识库「陪练资料库」能搜到资料  
- [ ] 说「梳大纲」后，`data/outline.json` 有节点，面板焦点更新  
