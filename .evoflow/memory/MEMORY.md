# Task Group: feishu_downloads/ai-showcase/aigc/ai-creative-ad-video / pippit-tool-cli 图生视频合成
scope: 使用小云雀 pippit-tool-cli 生图、Seedance 参考视频合成、ffmpeg 截段/delogo、低成本试错与验收；适用于特斯拉飞越堵车及类似广告短视频复刻。
applies_to: cwd=workspace/1006-ai-creative-ad-video（产物目录 output/tesla_fly/）；reuse_rule=CLI 参数、积分档位、水印处理和 prompt 约束可复用于同类 pippit/Seedance 合成，具体 delogo 坐标仍需按分辨率和素材重新测量。

## Task 1: 特斯拉飞越堵车视频双参考合成与 v4 无水印无人声迭代，已产出 480p 成片

### rollout_summary_files

- memory/episodic/20261016-episode.md (cwd=workspace, rollout_path=unknown, updated_at=2026-10-16T09:57:32Z, thread_id=unknown, 端到端复现摘要；细节由同日 ad-hoc note 补充)
- memory/_inbox/notes/2026-10-16T18-00-00-tesla-flyover-pipeline.md (cwd=workspace/1006-ai-creative-ad-video, rollout_path=note-only, updated_at=2026-10-16T18:00:00Z, thread_id=unknown, 权威 ad-hoc 项目记录) [ad-hoc note]

### keywords

- pippit-tool-cli@1.0.41, 小云雀, 智能图片V2.5 Pro, Seedance_2.5, seedance2.0_fast_vision, generate-image, generate-video, task-type reference, query-result, get-credit-balance, ffmpeg, delogo, Tesla, Cybertruck, tesla_fly, 480p, 720p, 1080p, 60积分, 1600积分, 抖音水印, AI生成, faster-whisper, no speech, --image, 504

## User preferences

- 当复现飞车动作时，用户纠正为“普通城市马路（非高速）+ 仅一小段被几辆追尾车堵死 + 特斯拉被挡去路才起飞”；后续不要自行改成高速公路或持续飞行场景。[Task 1] [ad-hoc note]
- 动作弧线必须完整：正常行驶 -> 遇堵点 -> 腾空约 30 米 -> 空中翻滚 -> 车底气雾 -> 飞越堵点 -> 落地气雾炸开 -> 继续行驶；关键词“短暂腾空飞越一次，禁止持续悬停”必须写进 prompt，否则模型容易做成持续悬飞。[Task 1] [ad-hoc note]
- 用户明确关注成本：先用低分辨率省积分，验证动作四要素（腾空/四喷口/转圈/落地喷气）后再考虑高清；480p 试错首选。[Task 1] [ad-hoc note]
- 需要配音时，用户偏好高燃广告表达：Seedance 原生出音，prompt 写“配音：中文男声激情高燃广告腔：'…' 音效：…”；不需要人声时则必须全程无人声、无旁白、无对话、无歌词，只保留 BGM 和音效。[Task 1] [ad-hoc note]
- 用户不接受仿抖音文字/水印；参考素材和成片都要主动检查并处理，不要只在 prompt 里“禁止水印”后假定生效。[Task 1] [ad-hoc note]

## Reusable knowledge

- 已验证参考片段截取命令：`ffmpeg -i src.mp4 -t 15 -c:v libx264 -crf 18 -c:a aac first15s.mp4`；本项目直接用 ffmpeg 截段比走 1004 拆解管线更省事。[Task 1] [ad-hoc note]
- 生图命令形态：`pippit-tool-cli generate-image --model "智能图片V2.5 Pro" --ratio 2 --resolution 1K --effort medium ...`；`ratio` 是整数枚举：2=16:9、3=9:16、6=1:1；该模型的 `effort` 和 `resolution` 必填。[Task 1] [ad-hoc note]
- 双参考图生视频命令形态：`generate-video --model Seedance_2.5 --task-type reference --image 场景图 --video 参考片段 --prompt ... --duration 10 --ratio 16:9 --resolution 720p`；参考视频喂“主体外观/特效”，参考图喂“场景”，prompt 明确各自作用效果更好。[Task 1] [ad-hoc note]
- 轮询使用 `query-result --thread-id --run-id --download-dir`；生图约 1–1.5 分钟，Seedance 2.5 10s/720p 约 5 分钟。[Task 1] [ad-hoc note]
- 成本实测：Seedance_2.5 10s/1080p 带参考视频扣 1600 积分；seedance2.0_fast_vision 10s/480p 带参考视频约 60 积分；480p 是试错首选，1080p 档明显更贵。[Task 1] [ad-hoc note]
- 参考视频中的抖音水印会被模型当画面元素模仿，原片两个角都有水印且位置会换；必须先 delogo 擦干净参考视频，并从擦后视频重抽参考帧，再在多个时间点检查。960x544 参考片曾用左上 `x=4:y=4:w=210:h=140`、右下 `x=696:y=398:w=256:h=134`。[Task 1] [ad-hoc note]
- “AI生成”角标是平台服务端强制合规标识，prompt 禁不掉；只能成片后本地 delogo。864x496 成片曾用 `x=2:y=2:w=112:h=58`；v4 记录的另一覆盖框为 `x=10,y=8,w=92,h=46`。量边界可用 crop + scale 放大截帧。[Task 1] [ad-hoc note]
- 无人声纯 BGM/音效可在 prompt 中写“全程无人声无旁白无对话无歌词 + 高燃电子摇滚 BGM + 引擎/气雾/破空/落地音效”，验收用本地 faster-whisper 转写，结果为 `(no speech)` 即达标。[Task 1] [ad-hoc note]
- CLI 安装：pippit-tool-cli@1.0.41 最终安装到系统全局 `C:\Users\admin\AppData\Roaming\npm`；安装方式为 `npx @pippit-dev/cli@latest install`，registry 已是 npmmirror，首次 npx 后台下载约 4 分钟，不要提前杀。豆包办公沙箱另有独立安装，互不影响。[Task 1] [ad-hoc note]
- 登录态通过 browser 授权，有效期记录到 2027-10；积分查询用 `get-credit-balance`。[Task 1] [ad-hoc note]
- `--image` 每个旗标只能传一个路径，`"a + b"` 会报后缀错误；多图应重复 `--image`。上传偶发 504/云空间同步失败，原样重试通常即可。[Task 1] [ad-hoc note]
- 素材 `cf360265b0b5048cbb711b074329c998.mp4` 为 960x544@30、132s；0–4s 是体育场夜景 Cybertruck 拖拽白烟和红色光带，9–13s 是白色跑车悬空飞行、车底两道蓝紫等离子气柱，是本次核心参考。[Task 1] [ad-hoc note]
- 产物名：v3 `output/tesla_fly/tesla_jump_over_jam_v3_480p.mp4`（10.08s, 864×496，带音轨，动作四要素命中）；v4 无水印无人声版 `tesla_jump_v4_nolabel_480p.mp4`；另有 `tesla_jump_v4_final_480p.mp4`，场景图 `road_blocked_scene.png`。[Task 1] [ad-hoc note]

## Failures and how to do differently

- 症状：模型让车持续悬飞；原因：prompt 未禁止持续悬停，场景和动作弧线不具体；修复：写入“短暂腾空飞越一次，禁止持续悬停”，并补齐遇堵、起飞、翻滚、落地气雾、继续行驶的完整弧线。[Task 1] [ad-hoc note]
- 症状：成片右下角长出“TESLA 极客阿来”等仿水印文字；原因：模型把参考视频里的抖音/抖音号角标当画面元素模仿；修复：先对参考视频双角 delogo，重抽参考帧，prompt 再明令禁止文字水印，并全片多时间点复查。[Task 1] [ad-hoc note]
- 症状：试图用 prompt 去除“AI生成”角标无效；原因：这是平台服务端强制合规标识；修复：接受生成阶段存在，下载后按实际分辨率本地 delogo。[Task 1] [ad-hoc note]
- 症状：一次生成成本过高；原因：直接选择 Seedance_2.5 1080p 且带参考视频；修复：先用 seedance2.0_fast_vision/480p/10s 验证构图、动作、音轨和水印，再决定是否升级。[Task 1] [ad-hoc note]
- 症状：`--image "a + b"` 报后缀错误或多图未生效；原因：每个旗标只接受一个路径；修复：重复传入多个 `--image`。[Task 1] [ad-hoc note]
- 症状：上传 504 或云空间同步失败；原因：服务偶发问题；修复：原样重试，不立即改素材或命令。[Task 1] [ad-hoc note]
- 症状：1004 拆解管线不认纯哈希命名 mp4；原因：管线需要 `video.mp4` 或 `[id]` 后缀；本任务修复/绕法：用 ffmpeg 直接截参考段，1004 更适合链接到报告场景。[Task 1] [ad-hoc note]

# Task Group: ai-demos 项目总览静态页与机审数据
scope: 生成并维护覆盖工作区所有项目的总览 JSON、暗色仪表盘静态页、字段字典、机审清单和同步自检流程；处理 file:// 或面板预览的数据加载限制。
applies_to: cwd=workspace/ai-demos；reuse_rule=项目事实随仓库演进需重新机审，静态页架构、数据真源模式、file:// 适配和维护流程可复用。

## Task 1: 生成银泰需要的工作区项目总览机审数据和静态网页，后续改为单文件内嵌并固化维护规范

### rollout_summary_files

- memory/_inbox/notes/2026-10-15-projects-overview-page.md (cwd=workspace/ai-demos, rollout_path=note-only, updated_at=2026-10-15T00:00:00Z, thread_id=unknown, 权威 ad-hoc 项目记录) [ad-hoc note]

### keywords

- 银泰, projects.overview.json, overview/data.js, overview/index.html, overview/MAINTENANCE.md, maintainDoc, file://, fetch 跨域, 面板预览, 数据内嵌, 单文件, 暗色仪表盘, 卡片视图, 表格视图, 语言筛选, 搜索, 机审, package.json, PROJECTS_SUMMARY.md, README, pnpm monorepo, Next.js14, Fastify, Prisma, EvoFlow, 知识库, AI员工, Agent应用

## User preferences

- 用户要“覆盖工作区每个项目的总览”，字段包括基本信息、标签（如“自媒体电商”）、语言与资源类型、知识库、AI 员工、Agent 应用清单；交付不能只做页面，要先做机审数据。[Task 1] [ad-hoc note]
- 项目盘点必须可信：README、PROJECTS_SUMMARY 与实际代码冲突时，以 package.json 等实际配置为准；不要照抄过时宣传/总结文档。[Task 1] [ad-hoc note]
- 页面需要可离线/无服务预览：最初外部 `data.js` 是为避免 `file://` fetch 跨域；后续面板预览仍加载不了外部 data.js，用户侧需要单文件内嵌方案和长期维护规范。[Task 1] [ad-hoc note]

## Reusable knowledge

- 初始产物：`projects.overview.json` 是数据真源，`overview/data.js` 是渲染快照（用于 file:// 下避免 fetch 跨域），`overview/index.html` 是暗色仪表盘，支持卡片/表格双视图、语言筛选和搜索。[Task 1] [ad-hoc note]
- 2026-10-15 后续调整：面板预览加载不了外部 `data.js`，页面已改为数据内嵌单文件；维护规范固化在 `overview/MAINTENANCE.md`，包含字段字典、机审清单、同步自检流程；JSON 顶部有 `maintainDoc` 指针。[Task 1] [ad-hoc note]
- 维护方式：修改 `projects.overview.json` 后必须同步 `overview/data.js` 或让 AI 重新生成/内嵌快照；若仅数据变化，页面模板通常无需改动。[Task 1] [ad-hoc note]
- 机审发现：1002 现状是 pnpm monorepo（Next.js 14 + Fastify + Prisma）；`PROJECTS_SUMMARY.md` 中“18个 Python 脚本/cloud-run/miniprogram”已过时，README 所说 Vue3 也与 package.json 不符，应以 package.json 为准。[Task 1] [ad-hoc note]
- `_1004-extract` 是 1004 的临时副本，总览不单列，只在 notes 中说明，避免重复项目数和资产数。[Task 1] [ad-hoc note]
- EvoFlow 接入资产盘点结果：1004、1005 各 1 个知识库 + 1 个员工 + 扩展；技能合计 4 个（1004 两个、1005 一个、kit 一个）。这些数字是 2026-10-15 时点，后续应重新扫描。[Task 1] [ad-hoc note]

## Failures and how to do differently

- 症状：项目简介把 1002 描述为 Python 脚本/cloud-run/miniprogram 或 Vue3；原因：信任过时 PROJECTS_SUMMARY/README；修复：打开 package.json 和实际配置机审，以当前依赖和脚本判定技术栈。[Task 1] [ad-hoc note]
- 症状：面板预览或 `file://` 页面加载不了外部数据；原因：环境限制外部脚本/数据加载或 fetch 跨域；修复：将数据内嵌为单文件，同时保留 JSON 真源与 MAINTENANCE.md 的同步流程。[Task 1] [ad-hoc note]
- 症状：临时副本 `_1004-extract` 被误算成独立项目；原因：目录名相似且包含可运行内容；修复：总览不单列，只在 notes 标明它是 1004 的临时副本。[Task 1] [ad-hoc note]

## Auto-Index

- memory/facts/20261014-evoflow-2.md (fact)
- memory/facts/20261014-evoflow-3.md (fact)
- memory/facts/20261014-evoflow-4.md (fact)
- memory/facts/20261014-evoflow.md (fact)
- memory/facts/20261014-fact-2.md (fact)
- memory/facts/20261014-fact-3.md (fact)
- memory/facts/20261014-fact-4.md (fact)
- memory/facts/20261014-fact-5.md (fact)
- memory/facts/20261014-fact-6.md (fact)
- memory/facts/20261014-fact-7.md (fact)
- memory/facts/20261014-fact-8.md (fact)
- memory/facts/20261014-fact-9.md (fact)
- memory/facts/20261014-fact.md (fact)
- memory/facts/20261016-1004-2.md (fact)
- memory/facts/20261016-1004.md (fact)
- memory/facts/20261016-1006-2.md (fact)
- memory/facts/20261016-1006-3.md (fact)
- memory/facts/20261016-1006-4.md (fact)
- memory/facts/20261016-1006-5.md (fact)
- memory/facts/20261016-1006-cli.md (fact)
- memory/facts/20261016-1006.md (fact)
- memory/facts/20261016-ai-prompt.md (fact)
- memory/facts/20261016-cli.md (fact)
- memory/facts/20261016-fact-2.md (fact)
- memory/facts/20261016-fact-3.md (fact)
- memory/facts/20261016-fact.md (fact)

