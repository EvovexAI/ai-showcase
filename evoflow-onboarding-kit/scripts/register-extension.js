// EvoFlow 项目接入套件 · 通用脚本:把带 evoflow.extension.json 的项目注册进 UI 扩展面板
// 用法: node register-extension.js --project <项目根目录>
// 特性: 幂等(同 id 更新 manifest,保留 installed_at);写前自动备份注册表
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const getArg = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const project = getArg("--project");
if (!project) { console.error("用法: node register-extension.js --project <项目根目录(含 evoflow.extension.json)>"); process.exit(1); }

// dev 环境注册表在 ~/.evoflow-dev(不是 ~/.evoflow,那是旧位置);可用环境变量覆盖
const REGISTRY = process.env.EVOFLOW_REGISTRY || path.join(process.env.USERPROFILE, ".evoflow-dev", "ui-extensions", "registry.json");
const manifestPath = path.join(project, "evoflow.extension.json");
if (!fs.existsSync(manifestPath)) { console.error(`✗ 未找到 ${manifestPath},先在项目根创建 manifest(参考 templates/)`) ; process.exit(1); }

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
if (!manifest.id || !manifest.name) { console.error("✗ manifest 缺 id/name"); process.exit(1); }

const reg = JSON.parse(fs.readFileSync(REGISTRY, "utf8"));
const bak = `${REGISTRY}.bak-${manifest.id}-${Date.now()}`;
fs.copyFileSync(REGISTRY, bak);

const existing = reg.find((e) => e.id === manifest.id);
if (existing) {
  existing.enabled = true;
  existing.install_path = project;
  existing.manifest = manifest;
  console.log(`↻ 已更新: ${manifest.id} (${manifest.name})`);
} else {
  reg.push({
    enabled: true,
    id: manifest.id,
    install_path: project,
    installed_at: new Date().toISOString(),
    manifest,
    source: "folder-link",
  });
  console.log(`+ 已注册: ${manifest.id} (${manifest.name})`);
}
fs.writeFileSync(REGISTRY, JSON.stringify(reg, null, 2), "utf8");
JSON.parse(fs.readFileSync(REGISTRY, "utf8")); // 写后校验
console.log(`✓ registry.json ${reg.length} 条 | 备份: ${bak}`);
console.log("→ 让面板生效: EvoFlow 设置→扩展 点「刷新」,或重启面板");
