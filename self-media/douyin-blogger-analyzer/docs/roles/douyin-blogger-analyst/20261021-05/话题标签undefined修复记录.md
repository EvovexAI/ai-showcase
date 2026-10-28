# 报告「话题标签 TOP10」全 undefined 修复记录

- 日期：2026-10-21
- 发现场景：本班次巡检（无待办任务，做数据/报告完整性抽查时发现）

## 现象

`data/reports/*.md` 四份报告（柱子哥TzFilm / AI邪修•黎小小 / 小天fotos / 银泰AI实战）的
「## 五、话题标签 TOP10」表格，**标签列 100% 显示 `undefined`**，而次数、平均点赞数值本身是对的。

例（银泰AI实战，修复前）：

| 标签 | 次数 | 平均点赞 |
|---|---|---|
| undefined | 27 | 879 |

## 根因

`server.js` 内 `renderReportMd()` 话题统计处：

```js
const tags = {};
for (const w of acc.works) for (const t of w.title.match(/#[^\s#,，。;；@]+/g) || []) {
  const k = t.trim();
  (tags[k] = tags[k] || { c: 0, likes: [] }).c++;   // ← 只把 k 当作对象 key，没写进对象值
  ...
}
const tagRows = Object.values(tags)...               // ← 这里 key 已经丢了
```

渲染行用的是 `t.k`：

```js
tagRows.forEach((t) => L.push(`| ${t.k} | ${t.c} | ...`));
```

但 `tags` 的值只有 `{c, likes}`，没有 `k` 字段 → 恒为 `undefined`。

> 同文件里「钩子分布」表用的是 `Object.entries(hooks)`，拿到了 k，所以那张表正常。
> 这也说明是标签分支单独写漏了，不是渲染层问题。

## 修改（仅 `server.js`，不动采集脚本）

```js
// 修前
const tagRows = Object.values(tags).sort((a, b) => b.c - a.c).slice(0, 10)
  .map((t) => ({ ...t, avg: ... }));

// 修后
const tagRows = Object.entries(tags)
  .sort(([, a], [, b]) => b.c - a.c).slice(0, 10)
  .map(([k, t]) => ({ k, c: t.c, avg: ... }));
```

另在 `hookRows` 后加了 `.filter((h) => h.k != null)` 作为防御性兜底（同源 `h.k` 用法）。

## 验证

1. `node --check server.js` → 通过
2. 重启分析器（`node server.js`，端口 8787，仅单实例）
3. `POST /api/reports/rebuild` → `{"ok":true,"reports":4}`
4. 四份报告 `grep -c undefined` → **全部 0**
5. 抽查渲染结果正常，例（银泰AI实战）：

| 标签 | 次数 | 平均点赞 |
|---|---|---|
| #抖加小助手 | 27 | 879 |
| #真实生活分享计划 | 24 | 911 |
| #workbuddy | 20 | 946 |
| #agent | 13 | 949 |

6. 知识库「抖音博主分析报告库」resync → `updated: 4`，四份报告均已刷新

## 影响面

- 只影响报告文本展示，**原始数据（accounts.json）无污染**，无需重新采集
- 事前已重建全部历史报告，旧报告不再带脏列
- 已把该坑写入 `skills/douyin-blogger-analysis/SKILL.md` 坑点清单第 9 条

## 备注（顺带观察，未改）

- 标签提取完全依赖标题内 `#xxx` 文本解析。抖音标题过长时会被截断（如 `#age…`、`#workbu`），
  导致 `#workbuddy` 与 `#workbu` 被当成两个标签分别计数。
  → 属于采集口径问题，非本次 bug；若要优化需从页面抓 `textExtra.hashtagName` 原始标签，
  会涉及采集脚本核心解析逻辑，按纪律**先记坑、后动工**，本轮未改。
