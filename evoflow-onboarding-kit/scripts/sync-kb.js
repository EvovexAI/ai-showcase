// EvoFlow 项目接入套件 · 通用脚本:把本地报告目录同步进 owned 知识库(自动建库/复用,增量幂等)
// 用法: node sync-kb.js --name "<知识库名>" --folder <报告目录> [--desc "<描述>"] [--kb-id <已知的kb_前缀ID>]
// 依赖: EvoFlow venv(可用环境变量 EVOFLOW_VENV_PYTHON 覆盖);进程内直调 owned KB,不依赖网关
// 已验证的 API 签名坑(2026-10-14): create_base({"name","description"}) 是单 payload 参数;
//   search 为 async;search_keyword 同步返回 list;resync_base(kb_id) 增量幂等
const { execFileSync } = require("child_process");

const args = process.argv.slice(2);
const getArg = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const name = getArg("--name");
const folder = getArg("--folder");
const desc = getArg("--desc") || "";
const kbIdArg = getArg("--kb-id");
if (!name || !folder) {
  console.error('用法: node sync-kb.js --name "<知识库名>" --folder <目录> [--desc "…"] [--kb-id kb_xxx]');
  process.exit(1);
}
if (!require("fs").existsSync(folder)) { console.error(`✗ 目录不存在: ${folder}`); process.exit(1); }

const venvPython = process.env.EVOFLOW_VENV_PYTHON || "D:\\dev\\github\\EvoFlow\\backend\\.venv\\Scripts\\python.exe";
const payload = JSON.stringify({ name, desc, folder, kbId: kbIdArg });

const py = `
import json, sys
from evoflow.knowledge.owned import service as s

p = json.loads(sys.argv[1])
kb_id = p["kbId"]

def find_kb(name):
    for kb in s.list_bases():
        if kb.get("name") == name:
            return kb
    return None

kb = ({"id": kb_id} if kb_id else None) or find_kb(p["name"])
if not kb:
    kb = s.create_base({"name": p["name"], "description": p["desc"]})
    print("CREATED:", kb.get("id"))
kb_id = kb.get("id")

r = s.import_local_folder(kb_id, p["folder"], upsert=True, remember_source=True, activity_action="import.folder")
print("KB:", kb_id)
print("IMPORT:", json.dumps({k: r.get(k) for k in ("created","updated","unchanged","skipped")}, ensure_ascii=False))
print("记住这个 kb id,后续增量同步直接: resync_base('"+kb_id+"')")
`;
const out = execFileSync(venvPython, ["-c", py, payload], { encoding: "utf8", timeout: 300000 });
console.log(out);
