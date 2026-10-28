/**
 * 抖音博主分析器 - 本地数据服务
 * 零依赖,Node 18+ 直接运行: node server.js
 * 数据持久化在 data/accounts.json,不会丢失;支持导出/导入备份。
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.PORT || 8787);
const HOST = "127.0.0.1";
const DATA_FILE = path.join(__dirname, "data", "accounts.json");
const PUBLIC_DIR = path.join(__dirname, "public");

function loadData() {
  try {
    const raw = fs.readFileSync(DATA_FILE, "utf8");
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed.accounts)) return parsed;
  } catch (e) {
    /* 首次运行或文件损坏时重建 */
  }
  return { accounts: [], savedAt: null };
}

function saveData(db) {
  db.savedAt = new Date().toISOString();
  const tmp = DATA_FILE + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(db, null, 2), "utf8");
  fs.renameSync(tmp, DATA_FILE);
}

function slugify(name, douyinId) {
  const base = String(name || "account")
    .replace(/[^\w\u4e00-\u9fa5-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "account";
  return douyinId ? `${base}-${douyinId}` : `${base}-${Date.now().toString(36)}`;
}

/** 接收 {account, works} 或单个 account 对象,做字段归一化 */
function normalizeAccount(input) {
  const acc = input.account || input;
  if (!acc || !acc.name) throw new Error("缺少 account.name");
  const works = Array.isArray(input.works) ? input.works : Array.isArray(acc.works) ? acc.works : [];
  const id = acc.id || slugify(acc.name, acc.douyinId);
  return {
    id,
    name: acc.name,
    douyinId: acc.douyinId || "",
    secUid: acc.secUid || "",
    gender: acc.gender || "",
    age: acc.age || "",
    location: acc.location || "",
    ipLocation: acc.ipLocation || "",
    bio: acc.bio || "",
    profileUrl: acc.profileUrl || "",
    metric: acc.metric || "likes", // likes=卡面点赞; plays=卡面播放(自己主页)
    notes: acc.notes || "",
    stats: {
      following: acc.stats?.following ?? null,
      followers: acc.stats?.followers ?? null,
      followersText: acc.stats?.followersText || "",
      totalLikes: acc.stats?.totalLikes ?? null,
      totalLikesText: acc.stats?.totalLikesText || "",
      workCount: works.length || acc.stats?.workCount || 0,
    },
    collectedAt: acc.collectedAt || new Date().toISOString().slice(0, 10),
    works: works.map((w) => ({
      id: String(w.id || ""),
      url: w.url || (w.id ? `https://www.douyin.com/video/${w.id}` : ""),
      title: w.title || "",
      likes: w.likes ?? null,
      plays: w.plays ?? null,
      comments: w.comments ?? null,
      collects: w.collects ?? null,
      shares: w.shares ?? null,
      duration: w.duration || null,
      pinned: !!w.pinned,
      visibility: w.visibility || "public",
      publishedAt: w.publishedAt || null, // 缺失时前端按视频ID推算
    })),
  };
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

function send(res, code, body, headers = {}) {
  res.writeHead(code, { "Access-Control-Allow-Origin": "*", ...headers });
  res.end(body);
}

// ---------- Markdown 报告生成(知识库喂养层) ----------
const HOOK_RULES = [
  ["利益/机会", /(变现|赚钱|吃上饭|收入|副业|商单|涨粉|接单|红利|风口|铁饭碗|远程打工|打工|营收|分账|薅|赚回|翻身|逆天改命)/],
  ["数字诱惑", /(\d+(\.\d+)?(万|千|亿|刀|元|粉|个|条|种|招|年|小时)|时薪|年薪|月薪|万八千)/],
  ["教程/干货", /(教程|指南|攻略|拆解|开源|扫盲|入门|保姆级|心得|方法|怎么用|如何|心法|避坑|工作流|流水线|实操)/],
  ["疑问/悬念", /(？|\?|为什么|凭什么|到底是|究竟|谁能|会不会)/],
  ["恐惧/风险", /(骗局|失业|危险|别再|千万不要|警告|风险|暴跌|逼死|破产|亏钱|烧钱|割韭菜|陷阱)/],
  ["反常识/揭秘", /(竟|居然|没想到|揭秘|真相|其实|白了很多|却|真正的|隐藏|隐蔽)/],
  ["人物/故事", /(马斯克|黄仁勋|贾跃亭|孙宇晨|王自如|刘慈欣|Tim|富豪|首富|小镇青年|帝国|至暗|逆天|历险记)/],
  ["测评/开箱", /(测评|体验|首发|开箱|深度|对比|锐评|盘点|扫一遍|测了一遍)/],
];
function classifyHook(title) {
  for (const [name, re] of HOOK_RULES) if (re.test(title)) return name;
  return "其他/直述";
}
function dateFromId(id) {
  const n = Number(id);
  if (!n || n < 6e18) return null;
  const d = new Date(Math.floor(n / 4294967296) * 1000);
  return isNaN(d) || d.getFullYear() < 2016 || d.getFullYear() > 2035 ? null : d.toISOString().slice(0, 10);
}
const fmtWan = (n) => (n == null ? "—" : n >= 10000 ? (n / 10000).toFixed(n >= 100000 ? 0 : 1) + "万" : String(n));

function renderReportMd(acc) {
  // 只有拿到计数的作品才进统计样本;无计数的须单列说明,否则爆款率/均值会被瞒报(见 SKILL 坑点 10)
  const valOf = (w) => (acc.metric === "plays" ? (w.plays ?? w.likes) : (w.likes ?? w.plays));
  const counted = acc.works.filter((w) => valOf(w) != null);
  const miss = acc.works.filter((w) => valOf(w) == null);
  const vals = counted.map(valOf).sort((a, b) => a - b);
  const n = vals.length, sum = vals.reduce((a, b) => a + b, 0);
  const hot = vals.filter((v) => v >= 10000).length;
  const metric = acc.metric === "plays" ? "播放" : "点赞";
  const wdate = (w) => w.publishedAt || dateFromId(w.id) || null;
  const dates = acc.works.map(wdate).filter(Boolean).sort();
  const months = {};
  for (const d of dates) { const k = d.slice(0, 7); months[k] = (months[k] || 0) + 1; }
  const top = [...acc.works].sort((a, b) => ((b.likes ?? b.plays ?? 0) - (a.likes ?? a.plays ?? 0))).slice(0, 10);
  const hooks = {};
  for (const w of acc.works) {
    const h = classifyHook(w.title);
    (hooks[h] = hooks[h] || { c: 0, likes: [] }).c++;
    const v = acc.metric === "plays" ? (w.plays ?? w.likes) : (w.likes ?? w.plays);
    if (v != null) hooks[h].likes.push(v);
  }
  const hookRows = Object.entries(hooks)
    .map(([k, g]) => ({ k, c: g.c, avg: Math.round(g.likes.reduce((a, b) => a + b, 0) / (g.likes.length || 1)) }))
    .filter((h) => h.k != null)
    .sort((a, b) => b.avg - a.avg);
  const tags = {};
  for (const w of acc.works) for (const t of w.title.match(/#[^\s#,，。;；@]+/g) || []) {
    const k = t.trim();
    (tags[k] = tags[k] || { c: 0, likes: [] }).c++;
    const v = acc.metric === "plays" ? (w.plays ?? w.likes) : (w.likes ?? w.plays);
    if (v != null) tags[k].likes.push(v);
  }
  const tagRows = Object.entries(tags)
    .sort(([, a], [, b]) => b.c - a.c).slice(0, 10)
    .map(([k, t]) => ({ k, c: t.c, avg: t.likes.length ? Math.round(t.likes.reduce((x, y) => x + y, 0) / t.likes.length) : null }));

  const L = [];
  L.push(`# 抖音博主分析报告:${acc.name}`);
  L.push(``);
  L.push(`> 采集于 ${acc.collectedAt || "—"} · 数据口径:卡面${metric} · 作品 ${acc.works.length} 条(${acc.stats.workCount && acc.stats.workCount !== acc.works.length ? `主页计数 ${acc.stats.workCount}` : "全量"})${miss.length ? ` · **有效计数 ${counted.length}/${acc.works.length}**,未取到${metric}的 ${miss.length} 条不计入统计` : ""}`);
  L.push(``);
  L.push(`## 一、基础信息`);
  L.push(``);
  L.push(`- **昵称**: ${acc.name}${acc.gender ? `(${acc.gender}${acc.age ? " " + acc.age : ""})` : ""}`);
  L.push(`- **抖音号**: ${acc.douyinId || "—"} · **地区**: ${acc.location || acc.ipLocation || "—"}${acc.ipLocation && acc.location !== acc.ipLocation ? `(IP ${acc.ipLocation})` : ""}`);
  L.push(`- **粉丝**: ${fmtWan(acc.stats.followers)} · **获赞**: ${fmtWan(acc.stats.totalLikes)} · **关注**: ${fmtWan(acc.stats.following)}`);
  L.push(`- **主页**: ${acc.profileUrl || "—"}`);
  if (acc.bio) L.push(`- **简介**: ${acc.bio.replace(/\n/g, " / ")}`);
  if (acc.notes) L.push(`- **备注**: ${acc.notes}`);
  L.push(``);
  L.push(`## 二、数据全景`);
  L.push(``);
  L.push(`| 指标 | 值 |`);
  L.push(`|---|---|`);
  L.push(`| 单条平均${metric} | ${n ? fmtWan(Math.round(sum / n)) : "—"} |`);
  L.push(`| ${metric}中位数 | ${n ? fmtWan(vals[Math.floor(n / 2)]) : "—"} |`);
  L.push(`| 爆款率(≥1万) | ${n ? Math.round((hot / n) * 100) + "%" : "—"}(${hot} 条) |`);
  L.push(`| 最高单条 | ${n ? fmtWan(vals[n - 1]) : "—"} |`);
  L.push(`| 时间跨度 | ${dates.length ? dates[0] + " ~ " + dates[dates.length - 1] : "—"} |`);
  L.push(`| 月均发布 | ${(() => { const uniq = [...new Set(dates)]; return uniq.length > 1 ? (dates.length / Math.max(1, (new Date(dates[dates.length - 1]) - new Date(dates[0])) / (86400000 * 30.4))).toFixed(1) + " 条" : "—"; })()} |`);
  L.push(``);
  if (miss.length) {
    L.push(``);
    L.push(`> ⚠️ 口径提示:以下 ${miss.length} 条作品未取到${metric}计数(采集时卡面未渲染),**未计入上方均值/中位数/爆款率**;若这些条目含爆款,真实爆款率高于表中数值。占比 ${Math.round((miss.length / acc.works.length) * 100)}%。`);
    L.push(``);
    L.push(`| 未计数作品 | 发布 | 链接 |`);
    L.push(`|---|---|---|`);
    miss.forEach((w) => L.push(`| ${(w.title || "(标题未取到)").slice(0, 40)} | ${wdate(w) || "—"} | ${w.url || "—"} |`));
  }
  L.push(``);
  L.push(`### 每月发布条数`);
  L.push(``);
  L.push(`| 月份 | ${Object.keys(months).sort().join(" | ")} |`);
  L.push(`|---|${Object.keys(months).map(() => "---").join("|")}|`);
  L.push(`| 条数 | ${Object.keys(months).sort().map((k) => months[k]).join(" | ")} |`);
  L.push(``);
  L.push(`## 三、TOP10 作品(按${metric})`);
  L.push(``);
  L.push(`| # | 标题 | ${metric} | 发布 |${top.some((w) => w.pinned) ? " 置顶 |" : ""}`);
  L.push(`|---|---|---|---|${top.some((w) => w.pinned) ? "---|" : ""}`);
  top.forEach((w, i) => {
    L.push(`| ${i + 1} | ${w.title.slice(0, 50)}${w.title.length > 50 ? "…" : ""} | ${fmtWan(acc.metric === "plays" ? (w.plays ?? w.likes) : (w.likes ?? w.plays))} | ${wdate(w) || "—"} |${w.pinned ? " ✓ |" : ""}`);
  });
  L.push(``);
  L.push(`## 四、标题钩子分布(按平均${metric}排序)`);
  L.push(``);
  L.push(`| 钩子类型 | 条数 | 平均${metric} |`);
  L.push(`|---|---|---|`);
  hookRows.forEach((h) => L.push(`| ${h.k} | ${h.c} | ${fmtWan(h.avg)} |`));
  L.push(``);
  L.push(`## 五、话题标签 TOP10`);
  L.push(``);
  L.push(`| 标签 | 次数 | 平均${metric} |`);
  L.push(`|---|---|---|`);
  tagRows.forEach((t) => L.push(`| ${t.k} | ${t.c} | ${t.avg != null ? fmtWan(t.avg) : "—"} |`));
  L.push(``);
  return L.join("\n");
}

function writeReportFile(acc) {
  try {
    const dir = path.join(__dirname, "data", "reports");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${acc.id}.md`), renderReportMd(acc), "utf8");
  } catch (e) { logger2 && logger2(e); }
}
const logger2 = (e) => console.error("[report]", e);

// ---------- 报告路由助手 ----------
function reportRoutes(req, res, p) {
  const db = loadData();
  let m;
  if ((m = p.match(/^\/api\/accounts\/([^/]+)\/report\.md$/))) {
    const acc = db.accounts.find((a) => a.id === decodeURIComponent(m[1]));
    if (!acc) return sendJSON(res, 404, { error: "account not found" });
    return send(res, 200, renderReportMd(acc), {
      "Content-Type": "text/markdown; charset=utf-8",
      "Content-Disposition": `inline; filename="${encodeURIComponent(acc.id)}.md"`,
    });
  }
  if (p === "/api/reports/rebuild" && req.method === "POST") {
    let count = 0;
    for (const acc of db.accounts) { writeReportFile(acc); count++; }
    return sendJSON(res, 200, { ok: true, reports: count, dir: path.join(__dirname, "data", "reports") });
  }
  if (p === "/api/reports") {
    return send(res, 200, db.accounts.map((a) => ({ id: a.id, name: a.name, url: `/api/accounts/${encodeURIComponent(a.id)}/report.md` })),
      { "Content-Type": "application/json; charset=utf-8" });
  }
  return false;
}


function sendJSON(res, code, obj) {
  send(res, code, JSON.stringify(obj), { "Content-Type": "application/json; charset=utf-8" });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on("data", (c) => {
      size += c.length;
      if (size > 50 * 1024 * 1024) { reject(new Error("body too large")); req.destroy(); }
      else chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const p = url.pathname;

  if (req.method === "OPTIONS") return send(res, 204, "");

  const handled = reportRoutes(req, res, p);
  if (handled !== false) return handled;
  try {
    // ---------- API ----------
    if (p === "/api/accounts" && req.method === "GET") {
      const db = loadData();
      return sendJSON(res, 200, db.accounts.map((a) => ({
        id: a.id, name: a.name, douyinId: a.douyinId, location: a.location,
        metric: a.metric, stats: a.stats, collectedAt: a.collectedAt, workCount: a.works.length,
      })));
    }
    if (p === "/api/accounts" && req.method === "POST") {
      const body = JSON.parse(await readBody(req));
      const acc = normalizeAccount(body);
      if (acc.works.length === 0 && !acc.stats.workCount) throw new Error("至少需要 1 条作品数据");
      const db = loadData();
      const idx = db.accounts.findIndex((a) => a.id === acc.id);
      if (idx >= 0) db.accounts[idx] = acc; else db.accounts.push(acc);
      saveData(db);
      writeReportFile(acc);
      return sendJSON(res, 200, { ok: true, id: acc.id, name: acc.name, works: acc.works.length });
    }
    let m = p.match(/^\/api\/accounts\/([^/]+)$/);
    if (m) {
      const db = loadData();
      const idx = db.accounts.findIndex((a) => a.id === decodeURIComponent(m[1]));
      if (idx < 0) return sendJSON(res, 404, { error: "account not found" });
      if (req.method === "GET") return sendJSON(res, 200, db.accounts[idx]);
      if (req.method === "DELETE") {
        const [removed] = db.accounts.splice(idx, 1);
        saveData(db);
        return sendJSON(res, 200, { ok: true, removed: removed.name });
      }
    }
    if (p === "/api/export" && req.method === "GET") {
      const db = loadData();
      const stamp = new Date().toISOString().slice(0, 10);
      return send(res, 200, JSON.stringify(db, null, 2), {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `attachment; filename="douyin-analyzer-backup-${stamp}.json"`,
      });
    }
    if (p === "/api/import" && req.method === "POST") {
      const body = JSON.parse(await readBody(req));
      if (!Array.isArray(body.accounts)) throw new Error("备份格式应为 {accounts:[...]}");
      const db = loadData();
      for (const raw of body.accounts) {
        const acc = normalizeAccount(raw);
        const idx = db.accounts.findIndex((a) => a.id === acc.id);
        if (idx >= 0) db.accounts[idx] = acc; else db.accounts.push(acc);
      }
      saveData(db);
      return sendJSON(res, 200, { ok: true, total: db.accounts.length });
    }
    if (p === "/api/health") return sendJSON(res, 200, { ok: true, dataFile: DATA_FILE });

    // ---------- 静态文件 ----------
    let file = p === "/" ? "/index.html" : p;
    const full = path.join(PUBLIC_DIR, path.normalize(file).replace(/^([.][.][/\\])+/, ""));
    if (!full.startsWith(PUBLIC_DIR)) return send(res, 403, "forbidden");
    const ext = path.extname(full);
    if (fs.existsSync(full) && fs.statSync(full).isFile()) {
      return send(res, 200, fs.readFileSync(full), { "Content-Type": MIME[ext] || "application/octet-stream" });
    }
    return send(res, 404, "not found");
  } catch (err) {
    return sendJSON(res, 400, { error: String(err.message || err) });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`抖音博主分析器已启动: http://${HOST}:${PORT}`);
  console.log(`数据文件: ${DATA_FILE}`);
});
