#!/usr/bin/env node
/** 1004 品牌泛化:抖音视频拆解 → 视频拆解(保留技术 id 与抖音主路径描述) */
const fs = require("fs");
const root = "D:/dev/github/feishu_downloads/ai-showcase/self-media/douyin-video-pipeline";

const files = [
  "evoflow.extension.json",
  "README.md",
  "skills/douyin-video-pipeline/SKILL.md",
  "EVOFLOW-SETUP.md",
  "操作教程.md",
  "configure-1004.js",
];

// 通用替换(顺序执行,先长后短)
const REPL = [
  // 展示名:工作台
  ["抖音视频拆解工作台", "视频拆解工作台"],
  // 员工/知识库
  ["抖音拆解师", "视频拆解师"],
  ["抖音拆解报告库", "视频拆解报告库"],
  // 面板侧栏副标题
  ["抖音爆款 · 拆解对标", "爆款视频 · 拆解对标"],
  // EVOFLOW-SETUP 标题
  ["抖音视频拆解 · EvoFlow 使用操作步骤", "视频拆解工作台 · EvoFlow 使用操作步骤"],
  ["抖音视频拆解流水线(Agent 技能)", "视频拆解流水线(Agent 技能)"],
  ["把抖音视频变成**可参考学习的拆解报告**", "把视频变成**可参考学习的拆解报告**(抖音分享链接直达,B站/YouTube 等其他平台经 yt-dlp 通道)"],
  ["把一条抖音视频变成**能直接抄作业的拆解报告**", "把一条视频变成**能直接抄作业的拆解报告**(抖音分享链接直达;其他平台视频走 yt-dlp 通道)"],
  ["拆解任意抖音视频(公开可访问的)", "拆解视频:抖音分享链接直达;B站/YouTube 等其他平台经 yt-dlp 通道(公开可访问的)"],
  // 教程/SETUP 里的扩展入口名
  ["侧栏「更多 → 扩展应用」里出现「抖音视频拆解」", "侧栏「更多 → 扩展应用」里出现「视频拆解」"],
  ["扩展应用 → 抖音视频拆解", "扩展应用 → 视频拆解"],
  ["「扩展」分组出现「抖音视频拆解」", "「扩展」分组出现「视频拆解」"],
  ["「扩展」分组里出现「抖音视频拆解」", "「扩展」分组里出现「视频拆解」"],
  // manifest
  ["\"name\": \"抖音视频拆解工作台\"", "\"name\": \"视频拆解工作台\""],
  ["\"title\": \"抖音视频拆解\"", "\"title\": \"视频拆解\""],
  ["把一条抖音视频变成能直接抄作业的拆解报告：粘贴分享链接，自动下载、口播转写、关键帧、章节与洞察分析（钩子/人群/黄金句/节奏/结构）。全程本地运行，端口 8765。",
   "把一条视频变成能直接抄作业的拆解报告：粘贴链接，自动下载、口播转写、关键帧、章节与洞察分析（钩子/人群/黄金句/节奏/结构）。抖音分享链接直达，其他平台经 yt-dlp 通道支持。全程本地运行，端口 8765。"],
  // 技能 frontmatter
  ["Download and reverse-engineer Douyin videos into self-media insight reports.",
   "Download and reverse-engineer short/social videos into self-media insight reports. Douyin share links natively; other platforms via the yt-dlp fallback."],
  ["Use for 抖音拆解、口播分析、", "Use for 视频拆解、口播分析、"],
];

let total = 0;
for (const f of files) {
  const p = root + "/" + f;
  let s = fs.readFileSync(p, "utf8");
  let n = 0;
  for (const [a, b] of REPL) {
    while (s.includes(a)) { s = s.replace(a, b); n++; }
  }
  fs.writeFileSync(p, s);
  total += n;
  console.log(`${f}: ${n} 处替换`);
}
console.log("总替换:", total);
