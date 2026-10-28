---
name: douyin-blogger-analysis
description: >-
  抖音博主账号分析:打开指定博主的抖音主页,采集基础信息(昵称/抖音号/粉丝/获赞/简介)与
  全部作品的标题、点赞、发布日期,生成标准 JSON 并 POST 到本地分析器
  (http://127.0.0.1:8787/api/accounts),最后输出数据报告。
  Use when 用户要求"分析/采集/对比某个抖音博主"、
  "把这个博主加进分析器"、"更新某博主的数据"时。
---

# 抖音博主分析(采集 → 入库 → 报告)

把任意抖音博主的公开数据采集进本地分析器并出报告。零手工。

## 跨平台运行:两条路线,按平台能力选

### 路线 A|独立脚本(任何能跑命令行的平台:Codex CLI / Claude Code / Cursor / 人)
```bash
cd D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer && npm install   # 一次性,装 playwright-core
# 一次性:带调试端口启动 Chrome 并登录抖音(会话保存在独立目录,此后免登录)
#   chrome.exe --remote-debugging-port=9222 --user-data-dir="D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer/.chrome-profile"
node scripts/collect-douyin.js <博主主页URL>            # 采集→解析→自动POST入库→打印摘要
node scripts/collect-douyin.js <URL> --no-post          # 只采集不入库
```
脚本内置:内嵌JSON挖简介、DOM直采卡片(点赞徽章/时长/置顶/专属会员)、ID推算发布日期、
一致性留档(`data/_collect-*.json`)、自动POST。DOUYIN_CDP / ANALYZER_API 可用环境变量改地址。
**Agent 平台只需 shell + Node,不用浏览器接口——本文件 Step 1-7 的浏览器细节只在路线 B 需要。**

### 路线 B|浏览器接口直采(本文件主体,适合 ZCode / 配了 Playwright MCP 的平台)
直接执行下方 Step 1-7。若平台用的是 Playwright MCP,快照格式与 Step 4 的解析正则兼容,直接套用。

**Playwright MCP 工具映射**:browser_navigate=goto、browser_snapshot=domSnapshot、browser_click=click、
browser_evaluate=evaluate;滚动用 evaluate 滚动容器或按 PageDown。
EvoFlow 配置:连接器手动添加 `npx -y @playwright/mcp@latest --browser chrome --user-data-dir <本项目\.chrome-profile>`,
登录态与路线 A 的脚本共用同一 profile。

---

## 前置条件

1. 本地分析器在运行:`curl http://127.0.0.1:8787/api/health`,没运行则 `cd D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer && node server.js`(后台)
2. 浏览器里有已登录的抖音会话(任意一个已打开的 douyin.com 标签页即可,登录哪个账号不限)

## 流程总览

```
定位/新建标签页 → 打开博主主页 → 采基础信息 → 展开完整简介
→ 滚动加载全部作品 → 解析 → 组装 JSON → POST 入库 → 验收 + 报告
```

## Step 1|打开博主主页,采基础信息

导航到博主主页 URL(用户提供,或从当前活跃标签页/搜索取得),等待渲染后 `domSnapshot()`,提取:

- **昵称/头像**: `heading` (level=1) + `img "<昵称>头像"`
- **关注/粉丝/获赞**: 页头三个 generic 对,按 `关注 N / 粉丝 N / 获赞 N` 顺序配对(注意 22.2万 这类格式,存数字与原文两份)
- **抖音号/年龄/地区/IP**: `抖音号:xxx` `IP属地:x` `28岁` `上海·浦东` 等短 generic
- **作品计数**: tab 名 `作品 N`

## Step 2|展开完整简介

主页签名默认截断(以 `...` 结尾)。两种取法,按顺序尝试:

1. 点 `更多`(exact 文本,count==1 才点)。若点不动(被浮层挡),改用页面内 JS 点击:
```js
await tab.playwright.evaluate(`(() => {
  const els = [...document.querySelectorAll('span,div')].filter(e => e.children.length===0 && e.textContent.trim()==="更多");
  if (els.length) els[els.length-1].click();
  return els.length;
})()`)
```
2. 仍截断 → 从页面内嵌数据挖全量(必成功):
```js
await tab.playwright.evaluate(`(() => {
  const s = [...document.querySelectorAll('script')].map(x=>x.textContent).join("");
  const i = s.indexOf("<签名前10个字>");
  return i>=0 ? s.slice(i-100, i+600) : "";
})()`)
```
在返回的 JSON 串里找 `"desc":"..."` 字段(含 \n 转义,还原成真实换行)。

## Step 3|滚动加载全部作品

```js
for (let r = 0; r < 15; r++) {           // 100+ 作品给 20 轮
  await tab.cua.scroll({ x: 520, y: 540, scrollX: 0, scrollY: 2200 });
  await tab.playwright.waitForTimeout(700);
  const s = await tab.playwright.domSnapshot();
  if (s.includes("暂时没有更多了")) break;
}
```

## Step 4|解析作品(核心代码,替换 NAME 为博主昵称)

```js
const snap = await tab.playwright.domSnapshot();
const tail = snap.slice(snap.indexOf('tabpanel "作品"'));
const NAME = "博主昵称";                    // ← 替换
const blocks = tail.split(new RegExp("- '?link \"" + NAME + "：")).slice(1);

const toNum = (v) => v ? (v.endsWith("万") ? Math.round(parseFloat(v)*10000) : parseInt(v,10)) : null;
const works = [];
for (const b of blocks) {
  const urlM = b.match(/\/url: (\/video\/\d+)/);
  if (!urlM) continue;
  const pinned  = /Tag: 置顶/.test(b);
  const members = /generic: 专属会员/.test(b);
  let likes = null, dur = null;
  const genRe = /generic: "?([^"\n]+)"?/g; let g;
  while ((g = genRe.exec(b)) !== null) {
    const v = g[1].trim();
    if (/^\d+(\.\d+)?万?$/.test(v)) { likes = v; break; }
    if (/^\d{2}:\d{2}$/.test(v) && !dur) dur = v;
  }
  const durAll = b.match(/(\d\d:\d\d)\s*\n\s*- text: \/\s*\n\s*- generic: (\d\d:\d\d)/);
  if (durAll) dur = durAll[2];
  const pM = b.match(/paragraph: "?([^\n]+?)"?\s*$/m);
  const title = (pM ? pM[1] : b.split("\n")[0]).replace(/Tag: 置顶$/, "").trim();
  const id = urlM[1].replace("/video/", "");
  const ts = Math.floor(Number(id) / 4294967296);   // ID高32位≈发布unix秒(已两次实测验证)
  works.push({ id, url: "https://www.douyin.com"+urlM[1], title,
    likes: toNum(likes), duration: dur, pinned,
    visibility: members ? "members" : "public",
    publishedAt: new Date(ts*1000).toISOString().slice(0,10) });
}
// 校验: blocks.length 应≈主页"作品 N"计数(差值=私密/仅会员不可见,记进 notes)
JSON.stringify({ blocks: blocks.length, parsed: works.length, works });
```

## Step 5|组装并入库

组装(参考已存数据 `D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer/data/accounts.json`):

```json
{
  "account": {
    "name": "", "douyinId": "", "gender": "", "age": "", "location": "", "ipLocation": "",
    "bio": "完整简介,\\n 还原换行",
    "profileUrl": "", "metric": "likes",
    "notes": "口径备注/异常说明",
    "stats": { "following": 0, "followers": 0, "followersText": "", "totalLikes": 0, "totalLikesText": "", "workCount": 0 },
    "collectedAt": "YYYY-MM-DD"
  },
  "works": [ { "id": "", "title": "", "likes": 0, "pinned": false, "publishedAt": "", "url": "" } ]
}
```

一致性校验后才入库:works 的 likes 总和 ≈ 主页"获赞"总数(偏差<5%)。不符则检查是否把播放量当成了点赞(见坑点①)。

入库(临时文件方式,防 shell 转义事故):
```bash
curl -s -X POST http://127.0.0.1:8787/api/accounts -H "Content-Type: application/json" --data-binary @采集.json
```
同 id(name+douyinId)自动覆盖更新 → 重采集=数据刷新。

## Step 6|验收 + 报告 + 知识库同步

1. `GET /api/accounts` 确认新账号出现、workCount 正确
2. 浏览器打开 `http://127.0.0.1:8787/#/account/<id>`(URL编码),截图确认看板渲染
3. 报告结构:基础信息表 → 数据全景(平均/中位数/爆款率/月均/时间跨度) → TOP5 及共性 → 内容/钩子洞察 → 与已存账号对比 → 行动建议
4. **报告落盘与知识库同步**(每次入库后做一遍):
   - 分析器入库/更新账号时自动把分析报告写到 `data/reports/<昵称>-<抖音号>.md`(账号数据全景/内容分析/钩子分析/账号对比)
   - 同步进 EvoFlow owned 知识库「**抖音博主分析报告库**」(kb_e2a8f73a8d9a4fafad6159b251ab1b41):

```bash
# EvoFlow venv 解释器进程内直调,不依赖网关(建过源记忆,重复跑只增量更新)
"D:\dev\github\EvoFlow\backend\.venv\Scripts\python.exe" -c "import asyncio; from evoflow.knowledge.owned import service as s; r = s.resync_base('kb_e2a8f73a8d9a4fafad6159b251ab1b41'); print(r)"
```

## 登录、验证与风控(必读)

- **登录**:用 `start.bat`(或手动 chrome.exe --remote-debugging-port=9222 --user-data-dir=...\.chrome-profile)启动采集浏览器,**扫码登录一次,会话永久保存在独立目录**。脚本有登录预检:未登录直接退出(exit 5),不会采半截数据
- **风控验证**:出现 `second_verify` 遮罩 = 抖音风控(本会话在点登录时真实遇到过)。唯一正确动作:**人工完成滑块,等 1-2 分钟,重跑**。脚本检测到会自动停(exit 4),绝不硬重试——硬刚会升级风控
- **频率纪律**:一天采集别超过 3-5 个账号;连采多个中间隔几分钟;被风控就当天收工
- **账号策略**:建议用小号跑采集(风控记在登录号头上),主号只用来逛
- **一键启动**:`start.bat` = 起分析器服务 + 起采集浏览器 + 开分析器页面

## 坑点清单(每条都踩过,必读)

1. **卡面数字口径**:他人主页=点赞(♥);自己主页=播放(▶,metric 填 `plays`)。发布前先看卡面图标
2. 视频详情页 `screenshot()` 可能报 "capture failed for guest"——改用 domSnapshot 读标题/时长/章节/发布时间
3. 主页计数 ≠ 可见作品数(差额=私密/会员可见),以网格实采为准,notes 里注明
4. 标题含引号时快照用 `- 'link "..."'` 单引号包裹,split 正则必须兼容 `- '?link "`
5. 点赞数可能是 `generic: "164"`(带引号)或 `generic: 3.2万`(不带),正则两者都吃
6. 跨 turn 后标签页会被释放:先 `browser.user.openTabs()` 找到再 `claimTab`,认领过的用 `browser.tabs.get(id)`
7. 简介/会员信息藏在页面内嵌 script 标签的 JSON 里(`__pace_f`),ARIA 快照拿不到就去那里挖
8. 付费视频(专属会员)只能看到标题/试看时长/购买弹窗价格(680钻/月这类),本体打不开,如实记录
9. **内嵌 JSON 含两份数据**:登录用户 + 主页主人同页共存,全局搜第一个 `nickname` 会抓到登录号(2026-10-13 采小天fotos 实踩,把采集小号 atai_888 当成博主入库)。正确做法:用 URL 里的 secUid 定位主页主人数据段;昵称以 DOM h1 为准,关注/粉丝/获赞以页头文本为准(页头永远是主页主人)
10. **报告「话题标签 TOP10」全 undefined**:`server.js` 里 `tags[k]={c,likes}` 只存值没存 key,渲染却用 `t.k` → 整列 undefined。修法:`tagRows` 改走 `Object.entries(tags).map(([k,t])=>…)`;改完要重生成全部旧报告,否则历史报告仍带脏列
11. **部分作品取不到点赞(卡面未渲染)→ 统计口径被瞒报**(2026-10-21 巡检发现):银泰AI实战 8/42、小天fotos 7/26 条作品 `title` 与 `likes` 同为 null(占位卡没渲染完)。旧 `renderReportMd` 把它们丢出样本,均值/中位数/爆款率的分母变成「有计数条数」,报告头部却写「作品 42 条(全量)」——读者会把「爆款率 0%」当成全集结论(实为 34 条,19% 未计数)。已修:`server.js` 拆分 `counted/miss`,头部标「有效计数 N/总数」,未计数条目单列成表(占比+链接)。改完必须重生成报告,否则旧报告口径不变
12. **跨账号对比表(`data/_table.md`)会悄悄过期,别直接引用**(2026-10-22 巡检发现):该表是手写快照,不随重采自动更新。实测偏差:银泰AI实战 粉丝 5485→6869、作品 32→42、均赞 549→716(旧表按全部 32 条摊了未计数条目);AI邪修•黎小小 最高 29000→36000;小天fotos 均赞/中位/爆款率 4800/1494/11.5% → 6568/2130/15.8%(旧表未剔除 7 条未计数)。做法:引用前先按 `accounts.json` 用统一口径重算(有效计数分母、涨粉效率=粉丝÷总作品数),重算样板见 `docs/roles/douyin-blogger-analyst/20261022-04/口径校对-四账号对比表-20261022.md`
13. **一致性校验偏差对不上,先数未计数条目**:小天fotos 作品点赞合计仅为主页获赞的 22.6%(-77.4%),主因不是把播放当点赞,而是可见作品只有 26/84 且其中 7 条无计数。「偏差<5%」只适用于「可见作品≈主页计数 且 无未计数条目」的账号,否则在 notes 写清偏差成因

9. **项目目录改过名(2026-10-27)**:项目目录由旧名 `ai-demos/1005` 改为 `ai-demos/1005-douyin-blogger-analyzer`,但 start.bat、本 SKILL 文档、collect-douyin.js 注释仍写旧路径 → start.bat 报“系统找不到指定的路径”,分析器压根没起(8787 空响应)。已全部改为新路径并实测启动成功(health ok);以后遇路径类报错,先 `ls` 本机实际目录名,别照抄文档

## 报告口径约定

- 平均/中位数/TOP10 用卡面数据;爆款线 = 1万赞
- **分母口径**:均值/中位数/爆款率只对有卡面计数的作品算,报告须标出有效计数覆盖率;未计数条目不进统计,但不能从报告里消失(见坑点 11)
- 涨粉效率 = 粉丝 ÷ 作品数(跨账号可比)
- 钩子分类沿用分析器内置 9 类(利益/数字/教程/悬念/恐惧/反常识/人物/测评/其他)
