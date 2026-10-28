// EvoFlow 项目接入套件 · 通用脚本:生成 agent + hire JSON 并执行 evoflow 注册(装技能→建 agent→上岗)
// 用法:
//   node hire-employee.js --config configs/douyin-blogger-analyst.example.json   # 从配置文件创建
//   node hire-employee.js --dry-run --config configs/xxx.json                    # 只打印不执行
// 前置: 技能文档已拷进 %USERPROFILE%\.evoflow-dev\skills\custom\<skill-name>\(本脚本会代劳 --install-skill)
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const args = process.argv.slice(2);
const getArg = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const has = (k) => args.includes(k);
const configFile = getArg("--config");
const dryRun = has("--dry-run");
const installSkillDir = getArg("--install-skill"); // 项目内 skills/<name> 目录
if (!configFile) { console.error("用法: node hire-employee.js --config <json> [--install-skill <skills目录>] [--dry-run]"); process.exit(1); }

const cfg = JSON.parse(fs.readFileSync(configFile, "utf8"));
const outDir = process.env.EVOFLOW_OUTPUTS || path.join(process.env.USERPROFILE, ".evoflow-dev", "outputs");

// 1. 装技能(可选):拷 SKILL.md 级文档进 skills/custom,skills list 即可识别
if (installSkillDir) {
  const skillName = path.basename(installSkillDir);
  const dest = path.join(process.env.USERPROFILE, ".evoflow-dev", "skills", "custom", skillName);
  fs.mkdirSync(dest, { recursive: true });
  fs.copyFileSync(path.join(installSkillDir, "SKILL.md"), path.join(dest, "SKILL.md"));
  console.log(`✓ 技能已装库: ${skillName} → ${dest}`);
}

// 2. 生成 agent / hire JSON(放 outputs/,改岗直接 update --file)
const agentFile = path.join(outDir, `agent-${cfg.agent_code}.json`);
const hireFile = path.join(outDir, `hire-${cfg.agent_code}.json`);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(agentFile, JSON.stringify({
  agent_code: cfg.agent_code, agent_name: cfg.agent_name, description: cfg.description,
  skills: cfg.skills || [], tags: cfg.tags || [], soul: cfg.soul,
}, null, 2), "utf8");
fs.writeFileSync(hireFile, JSON.stringify({
  role_name: cfg.role_name || cfg.agent_name, agent_code: cfg.agent_code,
  department: cfg.department || "", responsibilities: cfg.responsibilities || [],
  kpis: cfg.kpis || [], autonomy_level: cfg.autonomy_level || "approval_for_risky",
  risk_threshold: cfg.risk_threshold || "medium",   // 枚举:low/medium/high,写自然语言会被拒
  heartbeat_rrule: cfg.heartbeat_rrule || "FREQ=HOURLY;INTERVAL=2",
  status: "active", max_turns: cfg.max_turns || 14, timeout_seconds: cfg.timeout_seconds || 600,
  daily_budget_usd: 0,
}, null, 2), "utf8");
console.log(`✓ JSON 落盘: ${agentFile}\n           ${hireFile}`);

if (dryRun) { console.log("(dry-run 结束,未执行注册)"); process.exit(0); }

// 3. 注册
const run = (cmd, cmdArgs) => execFileSync(cmd, cmdArgs, { encoding: "utf8", timeout: 120000 });
console.log(run("evoflow", ["agents", "create", "--file", agentFile]));
console.log(run("evoflow", ["employees", "hire", "--file", hireFile]));
console.log("✓ 员工已上岗。核验: evoflow employees list --compact");
