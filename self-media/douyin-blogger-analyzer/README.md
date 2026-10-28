# 抖音博主分析器

本地网页工具:采集抖音博主的公开数据,做**数据看板 / 内容分析 / 标题钩子分析 / 多账号对比**。数据存在本地文件里,不会丢失。

## 启动

```bash
node server.js
# 打开 http://127.0.0.1:8787
```

零依赖,只要装了 Node 18+ 即可。换端口:`PORT=9000 node server.js`。

## 数据存储

- 所有数据保存在 `data/accounts.json`(人类可读的 JSON),删库 = 删文件,备份 = 复制文件。
- 网页右上角「导出备份」可下载 JSON 快照;「导入备份」可恢复/合并。

## 添加/更新账号(两种方式)

1. **网页粘贴**:点右上角「+ 添加/更新账号」→ 粘贴 JSON → 保存。相同账号(name+douyinId 生成的 id 相同)自动覆盖更新。
2. **API 直灌**(推荐,让 AI 助手自动完成):

```bash
curl -X POST http://127.0.0.1:8787/api/accounts \
  -H "Content-Type: application/json" \
  -d @collected.json
```

### JSON 格式

```jsonc
{
  "account": {
    "name": "柱子哥TzFilm",
    "douyinId": "21397448654",        // 用于生成唯一 id
    "gender": "男", "location": "福建·福州", "ipLocation": "福建",
    "bio": "简介原文",
    "profileUrl": "https://www.douyin.com/user/MS4wLjAB...",
    "metric": "likes",                // likes=他人主页(卡面为点赞); plays=自己主页(卡面为播放)
    "stats": { "following": 397, "followers": 222000, "totalLikes": 1644000 },
    "collectedAt": "2026-10-10"
  },
  "works": [
    {
      "id": "7657727877504437538",    // 抖音视频ID;缺 publishedAt 时按ID推算发布日期
      "title": "趁Ai真正的爆发期还没有到来… #标签",
      "likes": 124000,                // metric=likes 时必填
      "plays": 504,                   // metric=plays 时用这个字段
      "comments": 2589, "collects": 58000, "shares": 19000,  // 可选,进入详情页才有
      "pinned": false,
      "visibility": "public",         // public | private | friends
      "publishedAt": "2026-07-02"     // 可选
    }
  ]
}
```

## 功能说明

| 标签页 | 内容 |
|---|---|
| 📊 数据看板 | 粉丝/获赞/平均/中位数/爆款率/月均发布,每月条数图,数据分布直方图,TOP10 与最近作品 |
| 🧩 内容分析 | 话题标签频率(绑定哪些平台流量计划)、置顶策略、全量作品清单 |
| 🪝 钩子分析 | 标题按钩子类型自动分类(利益/数字/教程/悬念/恐惧/反常识/人物/测评),看哪类钩子对该博主最有效 |
| ⚖️ 账号对比 | 所有已存账号横向对比:粉丝、平均数据、爆款率、更新频率、主打钩子 |

## 技能化:重复分析不再需要重走流程

采集流程已固化为技能文件:`skills/douyin-blogger-analysis/SKILL.md`,含**两条运行路线**:

- **路线 A(任何能跑命令行的平台)**:`node scripts/collect-douyin.js <博主主页URL>` 一条命令完成采集→解析→入库。
  前置:`npm install` + 带调试端口启动 Chrome 并登录一次抖音(命令见 SKILL.md)。
- **路线 B(带浏览器接口的 ZCode / Playwright MCP)**:按 SKILL.md 的 Step 1-7 浏览器直采。

以后分析新博主,对 AI 助手说「**采集分析 xxx 博主**」即可。解析正则、发布日期推算(ID高32位=unix秒)、
口径坑点(播放量vs点赞、付费视频、私密作品)全部内置。

技能文件夹可整份拷贝到其他平台复用:`~/.claude/skills/`、`.cursor/skills/`、`EvoFlow/skills/custom/` 均可。

## 工作流(以后分析新博主)

1. 在 ZCode 里说「帮我采集 xxx 博主的数据」;
2. AI 助手用浏览器打开其抖音主页 → 滚动加载全部作品 → 解析成上面的 JSON;
3. 助手 POST 到 `http://127.0.0.1:8787/api/accounts`(或你在网页里手动粘贴);
4. 刷新分析器页面即可查看/对比。同一账号隔段时间再采一次,可观察涨粉与爆款变化。

## 知识库对接(MD 报告层)

数据双轨制:**`data/accounts.json` 是机器真源**(程序读写、幂等更新),**`data/reports/<账号id>.md` 是知识库喂养层**(人可读、分块友好、给模型检索用)。

- 每次采集/更新账号,自动重写对应 `data/reports/<id>.md`(基础信息/数据全景/每月节奏/TOP10/钩子分布/标签TOP10)
- 手动重建全部报告:`curl -X POST http://127.0.0.1:8787/api/reports/rebuild`
- 单份在线查看:`http://127.0.0.1:8787/api/accounts/<id>/report.md`(网页里账号详情页也有「MD报告」按钮)
- **对接知识库**:把 `data/reports/` 文件夹直接指向 EvoFlow 文档知识库/飞书/任何 RAG 管道即可;不要直接喂 accounts.json(RAG 分块会把嵌套 JSON 切碎)
