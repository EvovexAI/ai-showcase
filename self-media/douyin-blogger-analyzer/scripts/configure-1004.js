#!/usr/bin/env node
/** 1004 → EvoFlow 一键配置:装技能 / 建知识库+导入报告 / 建员工 */
const GW = process.env.GW || "http://127.0.0.1:8382";
const path = require("path");
const PROJ = process.env.PROJ || path.resolve(__dirname, "..", "..", "douyin-video-pipeline");

async function api(method, p, body) {
  const res = await fetch(GW + p, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = text.slice(0, 300); }
  return { status: res.status, json };
}

(async () => {
  // 1. 安装技能
  console.log("── 1. 安装技能 douyin-video-pipeline");
  const sk = await api("POST", "/api/skills/install-from-path", {
    path: PROJ + "\\skills\\douyin-video-pipeline",
  });
  console.log("   ", sk.status, JSON.stringify(sk.json).slice(0, 300));

  // 2. 创建知识库「视频拆解报告库」
  console.log("── 2. 创建知识库");
  const kb = await api("POST", "/api/knowledge/owned/bases", {
    name: "视频拆解报告库",
    description: "1004 抖音视频拆解流水线产出的爆款拆解报告(钩子/人群/黄金句/节奏/结构/情绪价值),写新视频脚本时的对标案例库",
  });
  console.log("   ", kb.status, JSON.stringify(kb.json).slice(0, 300));
  const kbId = kb.json && (kb.json.id || (kb.json.kb && kb.json.kb.id) || (kb.json.base && kb.json.base.id));

  // 3. 导入 data/reports 目录
  if (kbId) {
    console.log("── 3. 导入报告目录 data/reports");
    const imp = await api("POST", `/api/knowledge/owned/bases/${kbId}/import-folder`, {
      path: PROJ + "\\data\\reports",
    });
    console.log("   ", imp.status, JSON.stringify(imp.json).slice(0, 300));
  } else {
    console.log("   ! 未取到 kb_id,跳过导入");
  }

  // 4. 建员工「视频拆解师」
  console.log("── 4. 建员工 视频拆解师");
  const emp = await api("POST", "/api/proactive/employees", {
    role_name: "视频拆解师",
    department: "内容研究",
    responsibilities: [
      "接收抖音分享链接,调用 douyin-video-pipeline 本地流水线(127.0.0.1:8765)完成拆解",
      "向用户汇报:一句话速览、可参考学习的点(怎么抄+避坑)、报告路径",
      "拆解完成后把报告同步进知识库「视频拆解报告库」",
      "用户要写新视频脚本时,从报告库检索对标案例",
    ],
    workspace_path: PROJ,
    domain_scope: ["抖音拆解", "爆款分析", "自媒体内容研究"],
    knowledge_vault_ids: kbId ? [kbId] : [],
  });
  console.log("   ", emp.status, JSON.stringify(emp.json).slice(0, 400));

  // 5. 验证
  console.log("── 5. 验证");
  const skills = await api("GET", "/api/skills");
  const sList = Array.isArray(skills.json) ? skills.json : (skills.json && skills.json.skills) || [];
  console.log("   技能含 douyin-video-pipeline:", sList.some((s) => (s.name || s.skill_name || "").includes("douyin-video-pipeline")));
  const bases = await api("GET", "/api/knowledge/owned/bases");
  const bList = Array.isArray(bases.json) ? bases.json : (bases.json && bases.json.bases) || (bases.json && bases.json.items) || [];
  console.log("   知识库:", bList.map((b) => b.name || b.title).join(", ") || "(空)");
  const roles = await api("GET", "/api/proactive/roles");
  const rList = Array.isArray(roles.json) ? roles.json : (roles.json && roles.json.roles) || (roles.json && roles.json.items) || [];
  console.log("   员工/岗位:", rList.map((r) => r.role_name || r.name).join(", ") || "(空)");
})().catch((e) => { console.error("✗", e); process.exit(1); });
