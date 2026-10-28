# 视频拆解工作台 · 抖音 / B站 / 教学视频通用

把一条视频变成**内容拆解（起号）报告**（抖音分享链接直达；B站/YouTube 等其他平台经 yt-dlp 通道）：钩子 / 人群 / 黄金句 / 节奏 / 可参考学习的点。

粘贴分享链接 → 自动下载 → 口播转写 → 关键帧 → 章节 → 洞察报告（页面可视化 + Markdown 知识库存档）。

> **AIGC 反推提示词**已拆到独立项目 → [`../../aigc/aigc-prompt-reverse`](../../aigc/aigc-prompt-reverse/)（端口 8768）。本台只做内容拆解（8765）。

**全程本地运行**，不上传任何数据；洞察为内置规则引擎，**免费、不调用任何付费模型**。

> 📦 **想接入 EvoFlow？**（面板一键打开 + AI 员工替你拆视频）
> 跟着 [EVOFLOW-SETUP.md](EVOFLOW-SETUP.md) 做：把文档发给 AI，说「按这个文档帮我完成接入」，5 步搞定。

---

## 这是什么 / 不是什么

| ✅ 能做 | ❌ 不能做 |
|---------|----------|
| 拆解视频（抖音分享链接直达；B站/YouTube 等经 yt-dlp 通道；公开可访问的） | 下载需要登录/付费的内容 |
| 生成带「可参考学习的点」的分析报告 | 替你直接在平台上生成成片 |
| 报告存成 Markdown 形成知识库 | AIGC 反推（请用 1008） |
| 浏览器里可视化查看，零学习成本 | 自动发布到任何平台 |

---

## 快速开始（3 步）

> 以下命令都在**项目根目录**执行（就是本 README 所在的文件夹）。
> Windows 用户推荐用 PowerShell。

### 第 1 步：装依赖（只做一次）

需要两样东西：

1. **Python 3.10+**（去 [python.org](https://www.python.org/downloads/) 装，安装时勾选 "Add Python to PATH"）
2. **ffmpeg**（音视频处理引擎，去 [ffmpeg.org](https://ffmpeg.org/download.html) 下载，解压后把 `bin` 目录加入 PATH）

然后装 Python 依赖：

```powershell
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

国内网络慢的话，上面的镜像参数别去掉。

### 第 2 步：启动

```powershell
python scripts/web_server.py
```

看到这个就成功了：

```
视频分析面板: http://127.0.0.1:8765
Ctrl+C 停止
```

### 第 3 步：拆第一条视频

1. 浏览器打开 **http://127.0.0.1:8765**
2. 在抖音 App 里点「分享 → 复制链接」
3. 把复制到的整段文案粘贴进输入框，点「**开始拆解**」
4. 等几分钟（下载 + 转写 + 截帧），完成后自动跳到详情页
5. 概览页往下滚，就是完整拆解报告；右上角「查看报告」可全屏阅读

**就这么多。** 之后每拆一条视频都是第 3 步。

---

## 更省事的方式：让 AI 替你操作

启动、拆解、读报告这些都可以不亲自做。本项目自带 Agent 技能文档
（`skills/douyin-video-pipeline/SKILL.md`），任何接入该技能的 AI 助手
（Cursor、EvoFlow 等）都能：

- 替你启动服务、提交拆解、轮询进度
- 拆完直接把报告要点讲给你听
- 甚至帮你「按报告写一条新视频的口播稿」

对 AI 只需要说一句话，例如：

> 用 douyin-video-pipeline 这个技能，拆解这条视频：<粘贴链接>，拆完给我讲讲可参考学习的点。

---

## 拆解报告里有什么

每份报告的阅读顺序（也是价值排序）：

| 章节 | 回答的问题 |
|------|-----------|
| ⚡ 一句话速览 | 这条视频 30 秒内是什么路数？ |
| 🎯 可参考学习的点 | **我要拍同款，具体抄哪几处？**（含避坑+检查清单） |
| 一~三 | 钩子怎么设计的 / 拍给谁看 / 哪些话值得背下来 |
| 四~七 | 节奏多快、画面怎么切换、结构公式、观众在哪里最兴奋 |
| 八~十 | 为什么吸引人 / **观众得到什么情绪价值** / 作品特点 |
| 十一 | 对标数据（本片 vs 常见基准，做同款时对齐） |

报告自动存两份：

- `data/reports/YYYY-MM/标题_MMDD_视频ID后6位.md` —— 知识库，日积月累就是你的爆款案例库（标题在前是核心，日期放后面）
- `data/videos/视频ID/analysis/report.md` —— 跟视频放在一起的工作副本

页面里的报告和 MD 内容一致，随便看哪份。

---

## 目录结构（项目 = 代码，数据 = data）

```
├── scripts/        # 全部代码（下载/拆解/洞察/服务）
├── web/            # 浏览器界面
├── skills/         # AI 技能文档（给 Cursor / EvoFlow 看）
└── data/           # ★ 所有运行产生的数据（视频/报告/转写…）
                     #   备份数据=备份这个目录；分享项目=不带这个目录
```

---

## 常见问题

<details>
<summary><b>点「开始拆解」转圈后报错 / 一直没反应？</b></summary>

- 确认服务窗口还开着（关掉窗口服务就停了）
- 确认用的是**系统 Python**，不是某个虚拟环境里的 Python（缺依赖会静默失败）
- 视频必须是公开可访问的；私密/审核中/需登录的视频拆不了
- 抖音接口偶尔变动，重启服务再试一次

</details>

<details>
<summary><b>口播文字有错别字（比如「向量」变「相量」）？</b></summary>

语音转写（Whisper）对专有名词偶有误差，属正常现象。要点内容以报告分析为准，
个别字词不影响结论。进阶做法：让 AI 看关键帧图片校正（见 skills 文档 Phase 3）。

</details>

<details>
<summary><b>端口被占用 / 打不开 8765？</b></summary>

```powershell
# 查看谁占着 8765 并结束它
Get-NetTCPConnection -LocalPort 8765 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
# 重新启动
python scripts/web_server.py
```

</details>

<details>
<summary><b>怎么把数据搬到另一台电脑 / 备份？</b></summary>

整个项目文件夹拷走即可。只想备数据就拷 `data/` 目录；
只想分享代码就排除 `data/`（它不在 git 跟踪范围内）。

</details>

<details>
<summary><b>拆解一个视频要多久？</b></summary>

主要耗时在语音转写，与视频时长相关：3 分钟视频约 1–3 分钟（首次运行需下载
转写模型，会多等几分钟，之后不再下载）。

</details>

---

## 进阶：CLI 直接操作（可选）

不想开浏览器时，命令行两步完成同样的拆解：

```powershell
# 内容拆解（支持分享文案 / 短链 / 视频ID / last=最近一条）
python scripts/analyze_douyin.py "粘贴分享文案或 https://v.douyin.com/xxxx/" --full

# 报告位置
#   data/videos/{视频ID}/analysis/report.md
#   data/reports/YYYY-MM/*.md
```

> AIGC 反推 CLI 请到 `feishu_downloads/ai-showcase/aigc/aigc-prompt-reverse`。

完整 API / Agent 调用说明见 **skills/douyin-video-pipeline/SKILL.md**。

---

## 隐私说明

- 全部处理在本机完成；唯一的外部请求是访问抖音获取视频本身
- 报告、转写、截图都只存在 `data/` 本地目录，不上传任何服务器
