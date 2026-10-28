#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 2 (doc-formatter / doc-typeset, genre=general) 构建产物：
   06-正文全本-E1-60.md  →  stage2/formatted-<主题>.html

只做版式美化，不改写、不增删任何剧情文字。
"""
import json
import os
import re
import sys

SRC_MD = "/Users/xiguang/WorkBuddy/Claw/漫剧剧本主编培训/实战/原创选题43-屠夫老周的荤日子（乡村草根技术流·大尺度荤喜剧·目的优先人味冗余）/06-正文全本-E1-60.md"
OUT_HTML = sys.argv[1]
OUT_TOKENS = sys.argv[2]

DOC_TITLE = "屠夫老周的荤日子 · 正文全本（E1—60）"

# ---------------------------------------------------------------- 解析
raw = open(SRC_MD, encoding="utf-8").read()
lines = raw.split("\n")

DLG_RE = re.compile(r"^\*\*(.+?)\*\*（(.+?)）：(.*)$")

title = ""
intro = ""
episodes = []          # [{'title':str,'blocks':[(kind,payload)]}]
cur = None
for ln in lines:
    t = ln.strip()
    if not t or t == "---":
        continue
    if t.startswith("## "):
        cur = {"title": t[3:].strip(), "blocks": []}
        episodes.append(cur)
        continue
    if t.startswith("# "):
        title = t[2:].strip()
        continue
    if t.startswith("> "):
        intro = t[2:].strip()
        continue
    if cur is None:
        continue
    if t.startswith("场景："):
        cur["blocks"].append(("scene", t))
    elif t.startswith("出场人物："):
        cur["blocks"].append(("cast", t))
    elif t.startswith("△"):
        cur["blocks"].append(("act", t[1:].strip()))
    elif t.startswith("——"):
        if t.endswith("集完"):
            cur["blocks"].append(("end", t))
        else:
            cur["blocks"].append(("trans", t))
    else:
        m = DLG_RE.match(t)
        if m:
            cur["blocks"].append(("dlg", (m.group(1), m.group(2), m.group(3))))
        else:
            cur["blocks"].append(("note", t))

assert len(episodes) == 60, len(episodes)
n_scene = sum(1 for e in episodes for k, _ in e["blocks"] if k == "scene")
n_dlg = sum(1 for e in episodes for k, _ in e["blocks"] if k == "dlg")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# 正文字数（含标点，剔除 markdown 标记/动作号/分隔线符号/空白）
body_chars = 0
for e in episodes:
    for k, p in e["blocks"]:
        if k == "dlg":
            s = p[0] + p[2]
        elif k == "act":
            s = p
        elif k in ("scene", "cast", "note"):
            s = p
        else:
            continue
        body_chars += len(re.sub(r"[\s*△—]", "", s))

WL = {"1": "浪 1", "2": "浪 2", "3": "浪 3", "4": "浪 4"}

# ---------------------------------------------------------------- 组装
out = []
A = out.append

A('<!DOCTYPE html>')
A('<html lang="zh-CN">')
A('<head>')
A('<meta charset="UTF-8">')
A('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
A('<meta name="docx-page-size" content="A4">')
A('<title>%s</title>' % esc(DOC_TITLE))
A('<style>')
A(':root {')
A('  /* Page layout */')
A('  --page-content-width: var(--layout-contentWidth, 15.6cm);')
A('  /* Typography */')
A('  --fs-title: var(--typography-fontSize-title, 24pt);')
A('  --fs-h1: var(--typography-fontSize-h1, 18pt);')
A('  --fs-h2: var(--typography-fontSize-h2, 15pt);')
A('  --fs-h3: var(--typography-fontSize-h3, 13pt);')
A('  --fs-body: var(--typography-fontSize-body, 11pt);')
A('  --fs-small: var(--typography-fontSize-small, 9pt);')
A('  --ff-heading: var(--typography-fontFamily-heading, "PingFang SC", sans-serif);')
A('  --ff-body: var(--typography-fontFamily-body, "PingFang SC", sans-serif);')
A('  --lh-body: var(--typography-lineHeight-body, 1.7);')
A('  --lh-heading: var(--typography-lineHeight-heading, 1.3);')
A('  --fw-bold: var(--typography-fontWeight-heading, 600);')
A('  --fw-normal: var(--typography-fontWeight-body, 400);')
A('  /* Color */')
A('  --color-primary: var(--color-primary, #2563EB);')
A('  --color-text: var(--color-text, #111827);')
A('  --color-muted: var(--color-textSecondary, #6B7280);')
A('  --color-border: var(--color-border, #E5E7EB);')
A('  --color-bg: var(--color-background, #FFFFFF);')
A('  --color-highlight: var(--color-highlight, #FEF3C7);')
A('  --color-soft: var(--color-divider, #F3F4F6);')
A('  /* Spacing */')
A('  --spacing-paragraph: var(--spacing-paragraph, 0.5em);')
A('  --spacing-section: var(--spacing-sectionGap, 2em);')
A('  --spacing-block: var(--spacing-block, 1em);')
A('  --margin-page: var(--layout-margin, 2.5cm);')
A('}')
A('')
A('@page { @bottom-center { content: counter(page); } }')
A('@page coverpage { @bottom-center { content: none; } }')
A('section[role="cover"] { page: coverpage; }')
A('')
A('* { box-sizing: border-box; margin: 0; padding: 0; }')
A('')
A('body {')
A('  font-family: var(--ff-body);')
A('  font-size: var(--fs-body);')
A('  line-height: var(--lh-body);')
A('  color: var(--color-text);')
A('  background: var(--color-bg);')
A('  max-width: var(--page-content-width);')
A('  margin-left: auto;')
A('  margin-right: auto;')
A('  padding: var(--margin-page) 0;')
A('}')
A('')
A('h1, h2, h3 {')
A('  font-family: var(--ff-heading);')
A('  line-height: var(--lh-heading);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-text);')
A('}')
A('h1 { font-size: var(--fs-h1); }')
A('h2 { font-size: var(--fs-h2); }')
A('h3 { font-size: var(--fs-h3); }')
A('')
A('/* ---------- 封面 ---------- */')
A('.cover-eyebrow {')
A('  font-family: var(--ff-heading);')
A('  font-size: var(--fs-small);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-primary);')
A('  letter-spacing: 0.18em;')
A('  margin-bottom: var(--spacing-block);')
A('}')
A('.cover-title { margin-bottom: var(--spacing-block); }')
A('.cover-subtitle {')
A('  font-family: var(--ff-heading);')
A('  font-size: var(--fs-h3);')
A('  line-height: var(--lh-heading);')
A('  color: var(--color-muted);')
A('  margin-bottom: var(--spacing-section);')
A('}')
A('.cover-meta {')
A('  font-size: var(--fs-body);')
A('  line-height: var(--lh-body);')
A('  color: var(--color-text);')
A('  margin-bottom: var(--spacing-paragraph);')
A('}')
A('.cover-rulewrap { margin-bottom: var(--spacing-section); }')
A('')
A('/* ---------- 目录 ---------- */')
A('.doc-toc {')
A('  padding: var(--spacing-block);')
A('  background: var(--color-soft);')
A('  border-left: 3px solid var(--color-primary);')
A('  margin-bottom: var(--spacing-section);')
A('}')
A('.toc-title {')
A('  font-family: var(--ff-heading);')
A('  font-size: var(--fs-h3);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-text);')
A('  margin-bottom: var(--spacing-paragraph);')
A('}')
A('.toc-list, .toc-list ol, .toc-list ul {')
A('  list-style: none;')
A('  list-style-type: none;')
A('  padding-left: 0;')
A('  margin-bottom: 0;')
A('}')
A('.toc-list li {')
A('  font-size: var(--fs-small);')
A('  line-height: var(--lh-body);')
A('  color: var(--color-muted);')
A('  margin-bottom: 0;')
A('}')
A('.toc-list a { color: var(--color-muted); text-decoration: none; }')
A('')
A('/* ---------- 集 / 场 ---------- */')
A('.ep-title {')
A('  text-align: left;')
A('  padding-bottom: var(--spacing-paragraph);')
A('  border-bottom: 2px solid var(--color-primary);')
A('  margin-top: var(--spacing-section);')
A('  margin-bottom: var(--spacing-block);')
A('}')
A('.wave-title {')
A('  font-family: var(--ff-heading);')
A('  font-size: var(--fs-small);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-primary);')
A('  letter-spacing: 0.22em;')
A('  text-align: center;')
A('  margin-bottom: var(--spacing-paragraph);')
A('}')
A('.scene-line {')
A('  font-size: var(--fs-small);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-text);')
A('  text-align: left;')
A('  margin-bottom: 0;')
A('}')
A('.cast-line {')
A('  font-size: var(--fs-small);')
A('  color: var(--color-muted);')
A('  text-align: left;')
A('  margin-bottom: var(--spacing-paragraph);')
A('}')
A('.dlg {')
A('  font-size: var(--fs-body);')
A('  line-height: var(--lh-body);')
A('  color: var(--color-text);')
A('  text-align: left;')
A('  margin-bottom: 0;')
A('}')
A('.dlg .who { font-weight: var(--fw-bold); }')
A('.dlg .tone { color: var(--color-muted); }')
A('.act {')
A('  font-size: var(--fs-body);')
A('  line-height: var(--lh-body);')
A('  color: var(--color-muted);')
A('  text-align: left;')
A('  border-left: 2px solid var(--color-border);')
A('  margin-bottom: 0;')
A('}')
A('.trans {')
A('  font-size: var(--fs-small);')
A('  color: var(--color-muted);')
A('  text-align: center;')
A('  margin-bottom: var(--spacing-paragraph);')
A('}')
A('.ep-end {')
A('  font-family: var(--ff-heading);')
A('  font-size: var(--fs-small);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-muted);')
A('  text-align: center;')
A('  margin-bottom: var(--spacing-section);')
A('}')
A('')
A('/* ---------- 装饰 ---------- */')
A('.callout {')
A('  padding: var(--spacing-block);')
A('  background: var(--color-soft);')
A('  border-left: 3px solid var(--color-primary);')
A('  margin-bottom: var(--spacing-section);')
A('}')
A('.callout-title {')
A('  font-family: var(--ff-heading);')
A('  font-size: var(--fs-body);')
A('  font-weight: var(--fw-bold);')
A('  color: var(--color-primary);')
A('  margin-bottom: var(--spacing-paragraph);')
A('}')
A('.callout-body {')
A('  font-size: var(--fs-small);')
A('  line-height: var(--lh-body);')
A('  color: var(--color-text);')
A('  margin-bottom: 0;')
A('}')
A('[data-component="divider"] {')
A('  border-top: 1px solid var(--color-border);')
A('  margin-top: var(--spacing-section);')
A('  margin-bottom: var(--spacing-section);')
A('}')
A('</style>')
A('</head>')
A('<body>')

# 封面
A('  <section role="cover">')
A('    <p class="cover-eyebrow" style="text-align: center;">原创漫剧 · 竖屏短剧剧本</p>')
A('    <h1 class="cover-title" style="text-align: center;">屠夫老周的荤日子</h1>')
A('    <p class="cover-subtitle" style="text-align: center;">正文全本 · 第 1—60 集</p>')
A('    <p class="cover-meta" style="text-align: center;">题材：乡村草根 · 技术流 · 荤喜剧</p>')
A('    <p class="cover-meta" style="text-align: center;">体量：60 集 · 121 场 · 955 句对白</p>')
A('    <p class="cover-meta" style="text-align: center;">正文合计 %s 字（含标点）</p>' % format(body_chars, ","))
A('  </section>')

# 正文
A('  <section role="body" data-page-restart="1">')

# 目录
A('    <nav class="doc-toc" aria-label="文档目录">')
A('      <p class="toc-title">目录</p>')
A('      <ol class="toc-list">')
for i, e in enumerate(episodes, 1):
    A('        <li><a href="#ep-%d">%s</a></li>' % (i, esc(e["title"])))
A('      </ol>')
A('    </nav>')

if intro:
    A('    <div class="callout" data-component="callout" data-variant="info">')
    A('      <p class="callout-title">创作说明</p>')
    A('      <p class="callout-body">&nbsp;&nbsp;%s</p>' % esc(intro))
    A('    </div>')

last_wave = None
for i, e in enumerate(episodes, 1):
    m = re.search(r"浪(\d)", e["title"])
    wave = m.group(1) if m else None
    if wave != last_wave:
        A('    <div data-component="divider"></div>')
        if wave:
            A('    <p class="wave-title">%s</p>' % WL.get(wave, "浪 " + wave))
        last_wave = wave
    A('    <h2 class="ep-title" id="ep-%d">%s</h2>' % (i, esc(e["title"])))
    for k, p in e["blocks"]:
        if k == "scene":
            A('    <p class="scene-line">%s</p>' % esc(p))
        elif k == "cast":
            A('    <p class="cast-line">%s</p>' % esc(p))
        elif k == "dlg":
            A('    <p class="dlg"><span class="who">%s</span><span class="tone">（%s）</span>：%s</p>'
              % (esc(p[0]), esc(p[1]), esc(p[2])))
        elif k == "act":
            A('    <p class="act">&nbsp;&nbsp;△%s</p>' % esc(p))
        elif k == "trans":
            A('    <p class="trans">%s</p>' % esc(p))
        elif k == "end":
            A('    <p class="ep-end">%s</p>' % esc(p))
        else:
            A('    <p class="dlg">%s</p>' % esc(p))
A('  </section>')
A('</body>')
A('</html>')

html = "\n".join(out) + "\n"
os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
with open(OUT_HTML, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)

# design tokens（design-token skill 静态查表产物：genre=general）
tok_src = "/Users/xiguang/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docx/5.5.3-wb.37748631.g104760a2.hde0fbd244c72/skills/design-token/tokens/compiled/general.json"
tokens = json.load(open(tok_src, encoding="utf-8"))
tokens["_resolved_for"] = {
    "request_id": os.path.basename(os.path.dirname(OUT_HTML.rstrip("/"))),
    "genre": "general",
    "theme_name": tokens.get("theme_name"),
    "note": "剧本体裁未命中垂类模板，按 doc-formatter §4.1 兜底 general → modern-minimal",
}
with open(OUT_TOKENS, "w", encoding="utf-8") as f:
    json.dump(tokens, f, ensure_ascii=False, indent=2)

print("HTML ->", OUT_HTML, os.path.getsize(OUT_HTML), "bytes")
print("TOKENS ->", OUT_TOKENS)
print("episodes=%d scene=%d dlg=%d body_chars=%d" % (len(episodes), n_scene, n_dlg, body_chars))
