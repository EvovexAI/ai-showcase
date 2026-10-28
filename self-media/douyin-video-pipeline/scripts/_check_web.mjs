// 静态自检脚本（保留备用）：node scripts/_check_web.mjs
import { execSync } from "child_process";
import fs from "fs";

function utf8(buf) {
  return Buffer.from(buf).toString("utf8").replace(/^\uFEFF/, "");
}
function sh(cmd) {
  return execSync(cmd, { maxBuffer: 1e8, encoding: "buffer" });
}
const git = (f) => utf8(sh(`git show HEAD:${f}`));
const rd = (f) => fs.readFileSync(f, "utf8");

function syntaxOk(code) {
  try { new Function(code); return true; } catch (e) { return false; }
}
function ids(html) {
  return new Set([...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]));
}

const res = {
  headAppSyntax: syntaxOk(git("web/assets/app.js")),
  curAppSyntax: syntaxOk(rd("web/assets/app.js")),
  missingIds: null,
};

const curHtml = rd("web/index.html");
const curApp = rd("web/assets/app.js");
const curIds = ids(curHtml);
const used = [...new Set([...curApp.matchAll(/\$\("#([A-Za-z0-9_-]+)"\)/g)].map(m => m[1]))];
res.missingIds = used.filter(id => !curIds.has(id));

console.log(JSON.stringify(res, null, 2));
if (!res.headAppSyntax || res.curAppSyntax || (res.missingIds && res.missingIds.length)) {
  process.exit(1);
}
