v1

## User Profile

用户在本地 ai-demos / EvovexAI 工作区做 AI 实战演示与内容生产，项目常按编号目录组织，偏好小而完整、低依赖、数据真实可核查的交付。近期高频工作包括：用 pippit-tool-cli（小云雀）+ Seedance 做图生视频/参考视频合成，以及为工作区项目集生成机审数据和静态总览页。用户会主动纠偏画面动作、成本档位、水印/配音等细节，期望先用低成本样片验证，再做高成本版本。Windows 环境，常用 npm 全局 CLI、ffmpeg、本地静态页、JSON 数据真源。

## User preferences

- 视频合成先跑低成本档位试错：优先 480p / fast 模型 / 10s 小样；确认动作、音效、水印后再升 1080p，避免直接消耗高额积分。
- prompt 要把用户纠正过的动作约束写死，尤其是“短暂腾空飞越一次，禁止持续悬停”、翻滚、四喷口/气雾、落地喷气、继续行驶。
- 参考视频只作特效风格/主体外观参考，场景由参考图控制；prompt 中明确各自作用。
- 用户不要平台或抖音风格文字水印：参考素材必须先 delogo；“AI生成”合规角标若服务端强制加入，成片后本地擦除。
- 无人声版本要在 prompt 写明“全程无人声无旁白无对话无歌词”，并用转写验证；需要广告腔时写明中文男声、台词、BGM 与音效。
- 做项目盘点/总览时，以 package.json、配置文件和实际目录机审为准，不信任过时 README / PROJECTS_SUMMARY；交付数据真源 + 可离线打开的静态页 + 维护说明。
- 静态页在受限预览/`file://` 环境中要避免外部 fetch，优先单文件内嵌数据；另保留 JSON 真源和维护文档。

## General Tips

- Windows 全局 Node CLI 常见位置：`C:\Users\admin\AppData\Roaming\npm`；首次 `npx @pippit-dev/cli@latest install` 可能约 4 分钟，勿提前杀进程。
- pippit/Seedance 上传偶发 504 或云空间同步失败，通常原样重试即可。
- `generate-video --task-type reference` 中，参考视频喂主体外观/特效风格，参考图喂场景；多图要重复 `--image`，一个旗标不能传 `a + b`。
- 生图约 1–1.5 分钟；Seedance 2.5 10s/720p 参考生成约 5 分钟；480p fast 档曾约 60 积分，2.5 10s/1080p 带参考视频曾扣 1600 积分。
- delogo 后要从擦除后的视频重抽参考帧，并在多个时间点检查角标，因为水印可能换角或移动。
- 项目总览维护：改 `projects.overview.json` 后同步内嵌快照或重新生成页面；按 `overview/MAINTENANCE.md` 的字段字典、机审清单和自检流程走。

## What's in Memory

### workspace / feishu_downloads/ai-showcase/aigc/ai-creative-ad-video

#### 2026-10-16

- 特斯拉飞越堵车 pippit + Seedance 合成: pippit-tool-cli, Seedance_2.5, seedance2.0_fast_vision, generate-image, generate-video, delogo, 480p, 60积分, tesla_fly
  - desc: 小云雀图生视频、双参考合成、低成本试错、prompt 动作约束、无人声/广告配音和水印处理；搜索视频生成成本、CLI 参数、积分、参考素材处理时优先看。
  - learnings: 参考视频水印会被模型模仿；先 delogo 双角并重抽帧，平台“AI生成”角标需成片本地擦；用 480p fast 档验证，1080p 成本显著更高。[ad-hoc note]

### workspace / ai-demos 项目总览

#### 2026-10-15

- ai-demos 项目总览静态页: projects.overview.json, overview/data.js, overview/index.html, overview/MAINTENANCE.md, file://, 机审, package.json, 单文件内嵌
  - desc: 覆盖工作区项目的基本信息、标签、语言/资源类型、知识库、AI 员工、Agent 应用和技能清单；用于继续维护总览页或排查静态预览加载问题。
  - learnings: 文档可能过时，现状以 package.json/实际配置为准；外部 data.js 在面板预览和 file:// 下可能加载失败，已改为数据内嵌单文件并固化维护规范。[ad-hoc note]

### Older Memory Topics

#### workspace / feishu_downloads/ai-showcase/aigc/ai-creative-ad-video

- 特斯拉堵车腾空飞越视频复现: 1004拆解, video.mp4, ffmpeg, 夜间堵车, C2.0/480P, 持续飞行纠偏
  - desc: 既有 episode 记录了从本地视频拆解、ffmpeg 截段、小云雀生图到 Seedance 合成的端到端复现；适用于查找该任务的粗流程和用户多轮纠偏背景，cwd=workspace。
