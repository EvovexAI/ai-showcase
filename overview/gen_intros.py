# -*- coding: utf-8 -*-
"""按 overview/project-template.html 的大厂风骨架，为每个项目生成 intro.html。
骨架改动时请同步本文件中的 PAGE 模板；运行：python gen_intros.py（在本目录执行）。
"""
import io, os
from string import Template

# ───────────────────────── 通用片段 ─────────────────────────
def goals(items):
    icons = ["i-zap", "i-layers", "i-db", "i-target"]
    return '<div class="grid g3">' + "".join(
        f'<div class="card"><svg class="ic lg"><use href="#{icons[i%4]}"/></svg><h3>{t}</h3><p>{d}</p></div>'
        for i, (t, d) in enumerate(items)) + "</div>"

def personas(items):
    icons = ["i-user", "i-pen", "i-cpu", "i-target"]
    return '<div class="grid g3">' + "".join(
        f'<div class="card"><svg class="ic lg"><use href="#{icons[i%4]}"/></svg><h3>{t}</h3><p>{d}</p></div>'
        for i, (t, d) in enumerate(items)) + "</div>"

def problems(rows):
    tr = ""
    for pain, gain in rows:
        tr += (f'<div class="prob-row"><div class="prob pain"><span class="tag">之前</span>{pain}</div>'
               '<div class="arrow"><svg class="ic"><use href="#i-arrow"/></svg></div>'
               f'<div class="prob gain"><span class="tag">之后</span>{gain}</div></div>')
    return f'<div class="prob-table">{tr}</div>'

def combo(title, who, steps):
    st = "".join(
        f'<div class="step"><span class="n">{n}</span><b>{name}</b><small>{desc}</small></div>'
        for n, name, desc in steps)
    return (f'<div class="combo"><h3>{title}<em>{who}</em></h3><p class="who"></p>'
            f'<div class="flow">{st}</div></div>')

def daily_cards(noun, product, kb):
    return ('<div class="grid g2" style="margin-bottom:20px">'
        f'<div class="card"><svg class="ic lg"><use href="#i-chat"/></svg><h3>工作台对话发起</h3><p>在 EvoFlow 对话框直接 <code>@员工</code> 甩一条任务，员工调起本台技能，{product}直接回进对话。</p></div>'
        '<div class="card"><svg class="ic lg"><use href="#i-phone"/></svg><h3>手机 IM 发起</h3><p>员工接入飞书 / 钉钉 / 微信等渠道后，手机发消息即可发起——通勤路上顺手一发，' + noun + '就跑完了。</p></div>'
        '<div class="card"><svg class="ic lg"><use href="#i-timer"/></svg><h3>自动化定时发起</h3><p>把「' + noun + '」挂成自动化任务：按计划自动执行，结果准时出现在对话和面板里。</p></div>'
        '<div class="card"><svg class="ic lg"><use href="#i-monitor"/></svg><h3>EvoFlow 面板直看</h3><p>本台 UI 以扩展面板嵌进 EvoFlow，不切窗口，对话和操作台同屏。</p></div>'
        '</div>') + (
        f'<div class="combo"><h3>沉淀闭环：越用越聪明<em>关键不在跑一次，而在产出落进知识库，反哺之后的每一次发起</em></h3><p class="who"></p>'
        '<div class="flow">'
        '<div class="step"><span class="n">发起</span><b>对话 / IM / 自动化</b><small>任一入口把任务丢给员工</small></div>'
        '<div class="step"><span class="n">执行</span><b>员工调本台技能</b><small>流水线跑完，产出' + product + '</small></div>'
        f'<div class="step"><span class="n">沉淀</span><b>报告进知识库</b><small>{kb}自动归档、可检索</small></div>'
        '<div class="step"><span class="n">复用</span><b>员工查库再生成</b><small>下次同类任务先查历史产出，结论更准</small></div>'
        '</div>'
        '<div class="loop-back"><svg class="ic"><use href="#i-loop"/></svg>复用的结论又变成下一次发起的输入 —— 知识库越厚，建议越准</div></div>')

def callout(icon, title, html):
    return (f'<div class="callout"><svg class="ic lg"><use href="#{icon}"/></svg>'
            f'<div><span class="t">{title}</span>{html}</div></div>')

def quickstart(prereq, steps, faqs):
    body = callout("i-check-c", "开始前确认（一次性准备）", prereq)
    qs = ""
    for i, st in enumerate(steps, 1):
        t, d = st[0], st[1]
        code = st[2] if len(st) > 2 else None
        c = f'<div class="code">{code}<button class="copy">复制</button></div>' if code else ""
        qs += f'<div class="q"><div class="n">{i}</div><div><h4>{t}</h4><p>{d}</p>{c}</div></div>'
    body += f'<div class="qs">{qs}</div>'
    if faqs:
        det = "".join(f"<details><summary>{q}</summary><div class=\"a\">{a}</div></details>" for q, a in faqs)
        body += ('<div style="margin-top:36px"><h3 style="font-size:17px;font-weight:600;margin-bottom:6px;letter-spacing:-.2px">常见问题</h3>'
                 f'<div class="faq">{det}</div></div>')
    return body

def prompt_block(tool, users, scene, expect, features, stack, port, launch):
    feats = "\n".join(f"{i}. {f}" for i, f in enumerate(features, 1))
    txt = (
f'''<span class="cm"># ── 角色与目标 ──</span>
你是资深全栈工程师。请帮我从零开发一个本地工具：<span class="ph">【{tool}】</span>。

<span class="cm"># ── 核心用户与场景 ──</span>
主要用户是<span class="ph">【{users}】</span>，他们在<span class="ph">【{scene}】</span>的场景下使用，期望得到<span class="ph">【{expect}】</span>。

<span class="cm"># ── 功能清单（MVP）──</span>
{feats}

<span class="cm"># ── 技术约束 ──</span>
- 技术栈：<span class="ph">【{stack}】</span>
- 全部本地运行，不依赖云服务；密钥走环境变量，代码里绝不硬编码
- 端口 <span class="ph">【{port}】</span>，启动方式：<span class="ph">【{launch}】</span>
- 关键步骤有实时进度提示；失败要给可读的中文报错

<span class="cm"># ── 质量要求 ──</span>
- 先给我目录结构和关键模块设计，我确认后再写代码
- 附 README（安装、启动、常见问题），按项目规范不硬编码任何密钥与内网地址
- 边界情况都要有兜底提示，宁可报错清晰也不静默失败''')
    return ('<div class="prompt-wrap"><div class="prompt-head"><b>从 0 到 1 建项目提示词</b>'
            '<small>替换蓝色填空 → 整段复制 → 发给 AI</small></div>'
            f'<div class="prompt-body" id="promptText">{txt}</div>'
            '<div class="prompt-foot"><button class="btn primary copy-prompt">复制整段提示词</button></div></div>')

TIPS = ('<div class="tips">'
    '<div class="tip"><b>填空技巧</b>「解决什么问题」越具体，AI 一次做对的概率越高。写「给人看报告」不如写「给新手照抄结构」。</div>'
    '<div class="tip"><b>小步快跑</b>先让 MVP 跑通再迭代功能；一次让 AI 做十个小功能，不如三轮各做三个。</div>'
    '<div class="tip"><b>安全红线</b>永远在提示词里写明「密钥走环境变量」——这是本系列所有项目的铁律。</div>'
    '<div class="tip"><b>验收标准</b>把「先出设计再写码」「失败要中文报错」写进提示词，能有效防住糊弄式实现。</div></div>')

# ───────────────────────── 页面骨架（与 project-template.html 同步） ─────────────────────────
PAGE = io.open(os.path.join(os.path.dirname(__file__), "project-template.html"), encoding="utf-8").read()

import re

SEC_META = [
    ("pos",   "01", "项目定位", "它是什么、不是什么，一句话说清边界。"),
    ("goal",  "02", "目标", "做这个项目想达成什么，按「给谁省什么」来写。"),
    ("who",   "03", "使用对象", "三类人，各自拿它干什么。"),
    ("prob",  "04", "解决什么问题", "左边是现状的痛，右边是用了之后的变。"),
    ("combo", "05", "推荐怎么配合使用", "单点是工具，串起来才是流水线。最常用的组合打法："),
    ("daily", "06", "日常怎么用", "单开网页只是「手动挡」。接入 EvoFlow 后，同一个能力有四种发起方式，外加一条沉淀闭环。"),
    ("start", "07", "小白怎么上手", "不写代码，三步跑通第一条产出。"),
    ("prompt","08", "想自己做一个？0→1 提示词", "把下面整段喂给 AI 编程助手（ZCode / Cursor 等）。<b style=\"color:#1d4ed8;font-weight:550\">蓝色填空</b>是你要替换的部分。"),
]

def sec_html(sid, body):
    no, title, sub = next((n, t, s) for m, n, t, s in
                          [(m[0], m[1], m[2], m[3]) for m in SEC_META] if m == sid)
    return (f'<section id="{sid}" class="reveal">\n'
            f'  <div class="sec-head"><span class="sec-no">{no}</span><div><h2>{title}</h2><p class="sec-sub">{sub}</p></div></div>\n'
            f'  <div class="sec-body">\n{body}\n  </div>\n</section>')

def render(p):
    s = PAGE
    s = s.replace("项目介绍 · 抖音视频拆解工作台（模板示例）", f"项目介绍 · {p['title']}")
    s = re.sub(r'<div class="tpl-note">.*?</div>\n\n', "", s, count=1)
    s = s.replace('<span class="badge"><span class="dot"></span>自媒体</span>', f'<span class="badge"><span class="dot"></span>{p["cat"]}</span>')
    s = s.replace('<span class="badge ok"><span class="dot"></span>可用</span>',
                  f'<span class="badge {"ok" if p["ok"] else "mut"}"><span class="dot"></span>{p["status"]}</span>')
    s = s.replace('<span class="badge mut"><span class="dot"></span>EvoFlow 打样项目</span>', f'<span class="badge mut"><span class="dot"></span>{p["extra"]}</span>')
    s = s.replace("抖音视频拆解工作台", p["title"])
    s = s.replace("粘贴一条抖音分享链接，自动完成「下载 → 转写 → 关键帧 → 章节 → 洞察报告」，把一条爆款视频拆成能直接照抄起号的弹药。", p["tagline"])
    s = re.sub(r'<div class="spec">.*?</div>\n    <div class="cta">', p["spec_html"] + '\n    <div class="cta">', s, count=1, flags=re.S)
    for sid in [m[0] for m in SEC_META]:
        s = re.sub(rf'<section id="{sid}" class="reveal">.*?\n</section>', p[sid].replace("\\", "\\\\"), s, count=1, flags=re.S)
    # hero 区遗留的 ✏️ 注释
    s = re.sub(r'[ \t]*<!-- ✏️[^>]*-->\n', "", s)
    return s

def spec(items):
    return '<div class="spec">' + "".join(
        f'<div class="m"><small>{k}</small><b>{v}</b></div>' for k, v in items) + "</div>"

# ───────────────────────── 十个项目的内容 ─────────────────────────
PROJS = []

PROJS.append(dict(
    dir="aigc/ai-poster-editor", cat="AIGC", title="AI 海报编辑器", status="可用", ok=True, extra="纯前端 · 零框架",
    tagline="拖拽排版、图层面板、艺术字一样不少，再加 AI 生成背景、绿幕自动抠绿、布局优化多轮预览——浏览器里就能出一张能发的海报。",
    specs=[("端口", "8899"), ("形态", "纯前端应用 · 零框架"), ("启动方式", "<code>node server.cjs</code>"), ("核心产出", "海报成品 PNG/JPG")],
    pos='<p class="lead">这是一个<b>浏览器里的小型设计台</b>：画布 + 图层 + 拖拽 + 艺术字，配上三件 AI 武器——描述生成背景（通义万象）、绿幕素材自动抠绿、AI 布局优化（多轮 diff 预览/可撤回），最后一键成稿导出 PNG/JPG。附一个零依赖 REST API，供其他项目调用生图能力。</p>'
        '<div class="kw"><span>#海报设计</span><span>#AI 生图</span><span>#抠图</span><span>#布局优化</span><span>#零框架</span></div>',
    deliveries='<ul><li>海报成品图（PNG / JPG 一键导出）</li><li>AI 生成背景 + 绿幕抠绿素材</li><li>布局优化多轮 diff 预览（可撤回）</li><li>零依赖 REST API（供其他项目调生图）</li></ul>',
    goal=[("出图从半天到十分钟", "不会 PS 也能排版：拖素材、调图层、点优化，一张能发的海报就出来了。"),
          ("把设计感觉参数化", "AI 布局优化给出多轮候选和 diff，好看不好看有得选、可回退。"),
          ("生图能力可复用", "自带 REST API，电商主图、封面图场景都能来调。")],
    who=[("运营 / 自媒体新手", "不做设计，但要天天出图——模板加 AI，够用了。"),
         ("电商卖家", "主图、促销海报批量出，抠绿换底一气呵成。"),
         ("其他项目的开发者", "要生图能力时直接调它的 API，不用重新造轮子。")],
    prob=[("设计工具又重又贵，只想出张海报却要学一个月", "打开浏览器就能排，AI 补设计感，导出即用"),
          ("绿幕素材抠图要专业软件来回倒", "上传绿幕图自动抠绿，直接进画布"),
          ("排版全凭感觉，改来改去没个准", "AI 布局优化给多轮候选，diff 一目了然，不满意就撤回")],
    combo=[("组合一 · 「拆解 → 封面」内容链<em>适合做短视频要封面的人</em>", "",
        [("Step 1", "抖音视频拆解工作台", ":8765 拆出爆款结构和卖点"),
         ("Step 2", "AI 海报编辑器", "按卖点做视频封面 / 传播海报"),
         ("Step 3", "宣传视频制作", ":8766 配上内容出成片")]),
        ("组合二 · 「主图精修」电商链<em>适合电商卖家</em>", "",
        [("Step 1", "商策造物", ":5173 全网洞察 + 主图套装批量生成"),
         ("Step 2", "AI 海报编辑器", ":8899 精修排版、艺术字、加促销层"),
         ("Step 3", "导出上架", "PNG/JPG 按平台规格导出")])],
    daily=daily_cards("出一张图", "海报成品", "设计产出库（建议命名）"),
    assets=None,
    prereq='本机装好 <b>Node.js 18+</b> 即可，浏览器打开 <code>http://127.0.0.1:8899</code> 使用；AI 生图/布局优化用到模型服务，按 README 配好对应 Key（走环境变量）。',
    steps=[("启动服务", "在项目根目录起本地服务，浏览器访问即可。", '<span class="c"># 在项目根目录执行</span>\nnode server.cjs\n<span class="ok"># ✓ Listening on http://127.0.0.1:8899</span>'),
           ("排版 + AI 增强", "拖素材进画布排版；需要背景就文字描述生成，绿幕图丢进去自动抠，版式没感觉就点 AI 布局优化挑一轮。"),
           ("一键成稿", "满意后导出 PNG/JPG；注意导出前确认图层都合并到位。")],
    faqs=[("生图报错 / 没反应？", "检查对应模型服务的 Key 是否配置（走环境变量，不写死在代码里）；网络不通时看服务端日志。"),
          ("抠图边缘有绿边？", "绿幕素材尽量平整、光线均匀；仍明显可在图层上再裁一道。"),
          ("端口被占用？", "默认 8899，改 server.cjs 里的端口号即可。")],
    prompt=dict(tool="AI 海报编辑器——浏览器画布排版 + AI 生成背景/抠绿/布局优化，导出 PNG/JPG",
        users="运营与电商卖家", scene="要频繁出海报、封面、主图但不会专业设计软件",
        expect="一张可直接发布的成品图",
        features=["画布编辑：拖拽素材、图层面板、艺术字、缩放对齐",
                  "AI 生成背景：输入描述生成背景图（接通义万象类服务）",
                  "绿幕抠图：上传绿幕素材自动抠绿进画布",
                  "导出：一键导出 PNG/JPG，另附零依赖 REST API 供其他项目调用生图"],
        stack="Vanilla JS 零框架 + Node 内置模块零依赖 API", port="8899", launch="node server.cjs")))

PROJS.append(dict(
    dir="aigc/ai-creative-ad-video", cat="AIGC", title="AI 创意广告视频", status="可用（需小云雀会员）", ok=True, extra="CLI 工作流",
    tagline="用小云雀（Pippit）官方 CLI，从一句话到一支创意广告成片：脚本定稿 → 480p 样片预览 → 确认后转 1080p。沉淀了提示词套路库、积分策略和 PowerShell 封装。",
    specs=[("形态", "CLI 工作流"), ("依赖", "@pippit-dev/cli · Seedance"), ("跑法", "<code>powershell scripts/generate-ad.ps1</code>"), ("核心产出", "1080p 广告成片")],
    pos='<p class="lead">这是一条<b>跑通的「一句话 → 成片」CLI 流水线</b>：把小云雀官方 CLI 的操作、创意广告提示词套路、积分消耗策略全部封装成脚本和文档。按套路写一句需求，先出 480p 样片确认创意，再花积分转 1080p 成片——省积分，也省返工。</p>'
        '<div class="kw"><span>#广告视频</span><span>#小云雀 CLI</span><span>#提示词套路库</span><span>#样片确认制</span><span>#积分策略</span></div>',
    deliveries='<ul><li>1080p 创意广告成片（本地下载）</li><li>创意提示词套路库（prompts/）</li><li>PowerShell 参数化封装脚本</li><li>CLI 安装/登录/积分策略文档</li></ul>',
    goal=[("门槛从「会拍会剪」降到「会打字」", "一句话 + 套路库，出一条可投放的广告片。"),
          ("积分花在刀刃上", "先 480p 样片确认创意，避免 1080p 白烧积分。"),
          ("套路可沉淀", "每条好广告的提示词都进套路库，越攒越准。")],
    who=[("电商卖家 / 投放操盘手", "要批量出带货创意广告，测素材跑量。"),
         ("自媒体创作者", "给产品/账号做创意短片，不进专业剪辑软件。"),
         ("AI 效率玩家", "想把小云雀视频生成 CLI 玩明白的人——这里有踩完坑的完整文档。")],
    prob=[("请团队拍一条广告几千上万，周期还长", "一句话 + 样片确认制，几十分钟出可投放素材"),
          ("直接生成 1080p，创意不对全白花", "480p 样片先看创意，满意再转高清"),
          ("提示词全靠碰运气，效果不稳定", "套路库沉淀了验证过的写法，照抄就能出片")],
    combo=[("组合一 · 「反推 → 生成」复刻链<em>适合想复刻对标广告的人</em>", "",
        [("Step 1", "AIGC 反推提示词", ":8768 把对标广告反推成可粘贴 Prompt"),
         ("Step 2", "AI 创意广告视频", "用 Prompt 生成 480p 样片 → 确认 → 1080p"),
         ("Step 3", "宣传视频制作", ":8766 需要配音成稿时接上")]),
        ("组合二 · 「洞察 → 广告」电商链<em>适合电商卖家</em>", "",
        [("Step 1", "商策造物", ":5173 检索提炼痛点/卖点/创意方向"),
         ("Step 2", "AI 创意广告视频", "按卖点写提示词出广告样片与成片"),
         ("Step 3", "投放测试", "成片进广告账户跑素材")])],
    daily=daily_cards("出一条广告样片", "广告成片与提示词", "广告创意库（建议命名）"),
    assets=None,
    prereq='开通<b>小云雀会员</b>的账号；Node.js 22+；首次运行 <code>npx @pippit-dev/cli@latest install</code> 安装 CLI 并 <code>pippit-tool-cli login</code> 浏览器授权登录。',
    steps=[("安装并登录 CLI", "确认 logged_in 为 true，账号必须是开通会员的那个。", '<span class="c"># 安装（已装可跳过）</span>\nnpx @pippit-dev/cli@latest install\npippit-tool-cli login\npippit-tool-cli status\n<span class="ok"># ✓ logged_in: true</span>'),
           ("查积分，写需求出样片", "先查余额心里有数；把广告需求按套路库写好，跑封装脚本出 480p 样片。", '<span class="c"># 查积分 → 一键生成</span>\npippit-tool-cli get-credit-balance\npowershell -File scripts/generate-ad.ps1 -Prompt "你的广告创意"'),
           ("确认样片，转 1080p 成片", "样片满意再转 1080p，成片自动下载到本地。")],
    faqs=[("提示登录失效 / 401？", "会员账号才有效；重新 pippit-tool-cli login，确认浏览器授权完成。"),
          ("积分不够怎么办？", "先出 480p 样片控制消耗；删减镜头数也能省积分。"),
          ("生成的视频能商用吗？", "以小云雀平台的服务条款为准；投放前自行确认素材版权合规。")],
    prompt=dict(tool="小云雀 CLI 创意广告流水线——一句话需求 → 480p 样片确认 → 1080p 成片下载",
        users="电商卖家与投放操盘手", scene="要快速产出可投放的广告创意素材",
        expect="一条 1080p 广告成片 + 可复用的提示词套路",
        features=["封装小云雀官方 CLI 的安装/登录/状态检查",
                  "按提示词套路库组织需求，生成 480p 样片",
                  "样片确认后转 1080p 并自动下载",
                  "积分查询与消耗策略（先样片后成片）"],
        stack="@pippit-dev/cli（Node）+ PowerShell 封装脚本", port="—（CLI 工作流，无端口）", launch="powershell -File scripts/generate-ad.ps1")))

PROJS.append(dict(
    dir="aigc/aigc-prompt-reverse", cat="AIGC", title="AIGC 反推提示词工作台", status="可用", ok=True, extra="EvoFlow 接入项目",
    tagline="粘贴一条视频链接，约 3.5 秒一帧地拆：逐镜头时间轴 → 目标模型可粘贴的 T2V/I2V Prompt。想复刻一条爆款视频，从「看不懂」到「抄得走」。",
    specs=[("端口", "8768"), ("技术栈", "Python · yt-dlp · Whisper"), ("启动方式", "<code>python scripts/web_server.py</code>"), ("核心产出", "T2V / I2V 可粘贴 Prompt")],
    pos='<p class="lead">这是一个<b>只做「反推」的专项工作台</b>：从抖音拆解台复制并专项化，权威系统提示词固化在 <code>prompts/reverse-system.md</code>——逐镜头时间轴翻译成目标模型（T2V/I2V）的生成词，带禁止项，产出的 Prompt 可以直接粘进即梦/小云雀等工具。</p>'
        '<div class="kw"><span>#AIGC 反推</span><span>#逐镜头时间轴</span><span>#T2V / I2V</span><span>#可粘贴 Prompt</span></div>',
    deliveries='<ul><li>逐镜头时间轴 + 对应生成 Prompt</li><li>T2V / I2V 两种可直接粘贴的提示词</li><li>关键帧截图与转写稿</li><li>可进 EvoFlow 知识库的反推报告</li></ul>',
    goal=[("爆款从「看不懂」到「抄得走」", "把别人视频的镜头语言翻译成可执行的生成提示词。"),
          ("提示词质量稳定", "权威系统提示词 + 禁止项约束，不靠临场发挥。"),
          ("反推结果可积累", "报告进知识库，下次生成同类内容先查历史。")],
    who=[("短视频创作者", "看到好片子想复刻，需要把它变成生成词。"),
         ("AIGC 玩家", "研究爆款视频的镜头结构和对应 Prompt 写法。"),
         ("AI 工作流搭建者", "把反推挂进流水线：拆解 → 反推 → 生成一条龙。")],
    prob=[("看爆款只能干瞪眼，画面说不成提示词", "逐镜头时间轴自动翻译，生成词直接可粘贴"),
          ("自己写 Prompt 全靠猜，生成四不像", "系统提示词带禁止项，规避常见翻车写法"),
          ("反推结果散落聊天记录里，用完就丢", "统一成报告归档，可进知识库反复引用")],
    combo=[("组合一 · 「拆解 → 反推 → 复刻」全链路<em>想复刻爆款的标准打法</em>", "",
        [("Step 1", "抖音视频拆解工作台", ":8765 拆结构和钩子，看清凭什么火"),
         ("Step 2", "AIGC 反推提示词", ":8768 逐镜头反推成 T2V/I2V Prompt"),
         ("Step 3", "AI 创意广告视频", "用 Prompt 生成你自己的版本")]),
        ("组合二 · 「反推 → 沉淀 → 场景化」<em>把反推变成团队能力</em>", "",
        [("Step 1", "AIGC 反推提示词", "批量反推对标视频，产出 Prompt 报告"),
         ("Step 2", "EvoFlow 接入套件", "报告进知识库，雇反推员工"),
         ("Step 3", "EvoFlow 业务场景台", ":8877 在场景里演示调用")])],
    daily=daily_cards("反推一条视频", "反推 Prompt 报告", "AIGC 反推报告库"),
    assets='<code>aigc-prompt-reverser</code> 员工 · <code>aigc-prompt-reverse</code> 技能 · <code>AIGC 反推报告库</code> 知识库 · <code>AIGC 反推提示词 :8768</code> 扩展面板。接入或重建步骤见 <code>evoflow-onboarding-kit</code>。',
    prereq='装好 <b>Python 3.10+</b> 与 <b>ffmpeg</b>；首次运行自动下载 Whisper 模型（约 1GB）；视频链接需公开可访问。',
    steps=[("启动工作台", "在项目根目录执行，浏览器打开 8768 端口。", '<span class="c"># 在项目根目录执行</span>\npython scripts/web_server.py\n<span class="ok"># ✓ Listening on http://127.0.0.1:8768</span>'),
           ("粘贴链接开始反推", "约 3.5 秒一帧（20 秒视频 5~6 张关键帧），跑完出逐镜头 Prompt。"),
           ("复制 Prompt 去生成", "T2V/I2V 提示词直接粘进目标模型工具；报告也可导出归档。")],
    faqs=[("反推出来的 Prompt 生成效果不像？", "反推给的是结构级描述，不同模型理解有差异；微调主体/风格词即可。"),
          ("私密视频能反推吗？", "不能，链接必须公开可访问。"),
          ("和抖音拆解台什么关系？", "同源项目：拆解台做结构与洞察（:8765），本台只做提示词反推（:8768），不要把反推做回拆解台 UI。")],
    prompt=dict(tool="AIGC 反推提示词工作台——视频链接进，逐镜头 T2V/I2V 可粘贴 Prompt 出",
        users="短视频创作者与 AIGC 玩家", scene="看到想复刻的视频但写不出对应生成提示词",
        expect="逐镜头时间轴 + 可直接粘贴到生成工具的 Prompt",
        features=["输入视频链接，自动下载并抽关键帧（约 3.5 秒/帧）",
                  "按权威系统提示词逐镜头翻译为 T2V / I2V 生成词，带禁止项",
                  "Web 报告页展示时间轴 + Prompt，一键复制",
                  "历史记录本地保存，报告可进知识库"],
        stack="Python 标准库 HTTP + yt-dlp + Whisper + ffmpeg（复用拆解台内核）", port="8768", launch="python scripts/web_server.py")))

PROJS.append(dict(
    dir="self-media/ai-video-decompose", cat="自媒体", title="AI 视频拆解（Web 全栈版）", status="原型（含样例数据）", ok=False, extra="Next.js 全栈",
    tagline="抖音视频一键拆解的 Next.js 重构版：链接 → 下载 → 转写 → 关键帧 → 章节 → 分镜，脚本/章节表/分镜表一键导出，带详情页可视化。",
    specs=[("端口", "3001 API / 3002 Web"), ("技术栈", "Next.js 14 · Prisma · pnpm monorepo"), ("启动方式", "<code>pnpm dev</code>"), ("核心产出", "脚本 / 章节表 / 分镜表")],
    pos='<p class="lead">这是拆解能力的<b>全栈工程化版本</b>：apps/api（Fastify + Prisma + SQLite）+ apps/web（Next.js 14），把「链接 → 下载 → 转写 → 关键帧 → 章节 → 分镜」做成正规流水线，数据落库、详情页可视化、三种格式一键导出。适合当工程化参考或二次开发底座。</p>'
        '<div class="kw"><span>#Next.js 全栈</span><span>#分镜表</span><span>#章节切分</span><span>#可视化详情</span><span>#monorepo</span></div>',
    deliveries='<ul><li>拆解全流程 Web 应用（列表 + 详情页可视化）</li><li>脚本 Markdown / 章节 JSON / 分镜 JSON 三种导出</li><li>Fastify API（apps/api 10 个模块）</li><li>含样例数据的 dev.db</li></ul>',
    goal=[("拆解从脚本堆到工程化", "数据进 SQLite，接口规范，页面可视，能长期迭代。"),
          ("产出直接可用", "分镜表导出即可进制作环节，不用二次整理。"),
          ("可二开的底座", "monorepo 结构清晰，加自己的分析模块很容易。")],
    who=[("全栈开发者", "想要一个拆解方向的工程项目做参考或二开。"),
         ("内容团队", "要一个带界面、能存历史、能导出分镜的拆解工具。"),
         ("EvoFlow 接入方", "把它当 API 服务的参考实现。")],
    prob=[("一次性脚本跑完就扔，历史记录没法管", "数据落库 + 列表管理，拆过什么随时回看"),
          ("产出是零散的文本，接不进下游", "分镜/章节结构化导出，直接进制作流程"),
          ("裸 Python 脚本难交付给非技术同事", "Web 界面点一点就能用")],
    combo=[("组合一 · 全栈版与实战版互备<em>工程化与轻量两条路</em>", "",
        [("Step 1", "AI 视频拆解（本台）", ":3002 全流程可视化拆解与导出"),
         ("Step 2", "抖音视频拆解工作台", ":8765 轻量实战版，规则引擎洞察更直接"),
         ("Step 3", "按需取用", "要工程化/二开用本台，要快出报告用 8765")]),
        ("组合二 · 「拆解 → 制作」<em>从分镜到成片</em>", "",
        [("Step 1", "AI 视频拆解", "导出分镜表 JSON"),
         ("Step 2", "宣传视频制作", ":8766 分镜策划 + TTS 配音出成片")])],
    daily=daily_cards("拆一条链接", "分镜与章节报告", "视频拆解库（建议命名）"),
    assets=None,
    prereq='<b>Node.js 18+ 与 pnpm</b>；首次先 <code>pnpm install</code>；Whisper/ffmpeg 等转写依赖见 apps/api 的 README；仓库已带含样例数据的 dev.db，可先体验再接真实任务。',
    steps=[("安装并启动", "monorepo 一次装好，turbo 并行起前后端。", '<span class="c"># 在项目根目录执行</span>\npnpm install\npnpm dev\n<span class="ok"># ✓ web http://localhost:3002/video-decompose</span>'),
           ("提交链接跑拆解", "页面提交抖音链接，流水线跑完进详情页看章节与分镜。"),
           ("导出使用", "按需导出脚本 MD / 章节 JSON / 分镜 JSON，进下游制作。")],
    faqs=[("为什么是「原型」？", "链路与界面已跑通并带样例数据，但按系列标准（文档/稳定性/真实任务验证）还未达「可用」，用于体验与二开。"),
          ("转写模型在哪配置？", "见 apps/api 的 README，本地 Whisper 或云端二选一。"),
          ("和 8765 拆解台重复吗？", "定位不同：本台是 Next.js 工程化全栈版，8765 是 Python 轻量实战版。")],
    prompt=dict(tool="AI 视频拆解 Web 全栈应用——链接进，转写/关键帧/章节/分镜出，可视化详情页",
        users="内容团队与全栈开发者", scene="要把视频拆解从脚本升级为可管理、可导出的工程化工具",
        expect="结构化的分镜/章节产出 + 可视化拆解详情",
        features=["输入：视频链接提交表单 + 任务列表管理",
                  "流水线：下载 → 音频转写 → 关键帧抽取 → 章节切分 → 分镜生成",
                  "详情页：转写稿、关键帧、章节、分镜可视化展示",
                  "导出：脚本 Markdown / 章节 JSON / 分镜 JSON"],
        stack="Next.js 14 + React 18 + Fastify + Prisma/SQLite + pnpm monorepo(turbo)", port="3001 API / 3002 Web", launch="pnpm dev")))

PROJS.append(dict(
    dir="self-media/ai-video-promo", cat="自媒体", title="宣传视频制作系统", status="可用（TTS 需配 Key）", ok=True, extra="从拆解台拆出的制作侧",
    tagline="从拆解台拆出的「制作 + 配音」专用系统：火山 TTS（seed-tts-2.0，291 音色）、分镜策划稿 AI 润色、一键配音、工作台 API，专注把分镜变成能发的成片。",
    specs=[("端口", "8766"), ("技术栈", "Python · 火山 OpenSpeech v3"), ("启动方式", "<code>python scripts/promo_server.py</code>"), ("核心产出", "配音成片 / 分镜策划稿")],
    pos='<p class="lead">这是一条<b>专注「制作侧」的流水线</b>：与抖音拆解台后端对齐，砍掉下载/拆解/视觉识别，只留分镜策划稿（AI 润色）、火山 TTS 一键配音（291 音色可选）、工作台 API（任务/技能/草稿/自动化/飞书推送）。拆解在别处做，成片在这里出。</p>'
        '<div class="kw"><span>#TTS 配音</span><span>#分镜策划</span><span>#火山 seed-tts</span><span>#工作台 API</span><span>#飞书推送</span></div>',
    deliveries='<ul><li>分镜策划稿（AI 润色可改）</li><li>一键配音成片（291 音色）</li><li>工作台 REST API（任务/草稿/自动化）</li><li>飞书推送集成</li></ul>',
    goal=[("配音不再求人", "火山 TTS 291 音色，文案进去语音出来。"),
          ("策划稿有 AI 把关", "分镜初稿 AI 润色，口语化、节奏感更好。"),
          ("制作过程可编排", "任务/草稿/自动化 API 化，能接进更大的流水线。")],
    who=[("短视频创作者", "有文案有分镜，缺配音和成片环节。"),
         ("内容团队操盘手", "要把「拆解 → 制作」流水线串起来的那一环。"),
         ("自动化玩家", "用工作台 API 把制作挂进定时任务。")],
    prob=[("配音要么贵要么慢，改一版等半天", "TTS 一键出音，291 音色即选即用"),
          ("分镜稿写得书面，读出来尴尬", "AI 润色成口播语感"),
          ("制作环节散在各个工具里没法自动化", "全流程 API 化，可编排可定时")],
    combo=[("组合一 · 「拆解 → 制作」主链<em>从爆款结构到成片</em>", "",
        [("Step 1", "抖音视频拆解工作台", ":8765 拆出结构与节奏"),
         ("Step 2", "宣传视频制作（本台）", ":8766 分镜策划稿润色 + TTS 配音"),
         ("Step 3", "成片交付", "导出成片，可飞书推送")]),
        ("组合二 · 「广告样片 → 成稿」<em>给广告片补上配音</em>", "",
        [("Step 1", "AI 创意广告视频", "小云雀出 1080p 无声/带声样片"),
         ("Step 2", "宣传视频制作", "补策划稿与配音，统一成稿")])],
    daily=daily_cards("做一版配音", "策划稿与配音成片", "制作产出库（建议命名）"),
    assets=None,
    prereq='<b>Python 3.10+</b>；火山 TTS 需要配 Key（走环境变量，公开/掩码双模式见 config/）；音色清单可从 EvoFlow voices 导出（scripts/export_tts_voices.py）。',
    steps=[("启动服务", "在项目根目录执行，浏览器打开 8766。", '<span class="c"># 在项目根目录执行</span>\npython scripts/promo_server.py\n<span class="ok"># ✓ Listening on http://localhost:8766</span>'),
           ("写/润色分镜策划稿", "录入或粘贴初稿，AI 润色成口播语感，手动微调定稿。"),
           ("选音色一键配音", "从 291 音色里试听挑选，一键合成，成片导出或飞书推送。")],
    faqs=[("TTS 报错 / 没声音？", "确认火山 Key 已配且有效（环境变量方式）；账号余额与并发限制见火山控制台。"),
          ("音色列表是空的？", "先跑 scripts/export_tts_voices.py 从 EvoFlow 导出音色到 config/tts_voices.json。"),
          ("能拆解视频吗？", "不能也没打算——拆解请用 ：8765 拆解台，本台只做制作侧。")],
    prompt=dict(tool="宣传视频制作系统——分镜策划稿 AI 润色 + 火山 TTS 一键配音 + 工作台 API",
        users="短视频创作者与内容团队", scene="有文案/分镜但缺配音与成片环节，想让制作可自动化",
        expect="配音成片与可编排的制作流水线",
        features=["分镜策划稿录入与 AI 润色",
                  "火山 TTS 配音（seed-tts-2.0，音色库可选可试听）",
                  "工作台 REST API：任务/技能/草稿/自动化调度",
                  "成片导出与飞书推送"],
        stack="Python httpx + 火山 OpenSpeech v3 TTS + 标准库 HTTP 服务", port="8766", launch="python scripts/promo_server.py")))

PROJS.append(dict(
    dir="self-media/douyin-video-pipeline", cat="自媒体", title="抖音视频拆解工作台", status="可用（zip 分发）", ok=True, extra="EvoFlow 打样项目",
    tagline="粘贴一条抖音分享链接，自动完成「下载 → 转写 → 关键帧 → 章节 → 洞察报告」，把一条爆款视频拆成能直接照抄起号的弹药。",
    specs=[("端口", "8765"), ("技术栈", "Python · yt-dlp · Whisper"), ("启动方式", "<code>python scripts/web_server.py</code>"), ("核心产出", "起号报告 / 黄金句 / 钩子分析")],
    pos='<p class="lead">这是一个<b>本地起号的「爆款视频 CT 机」</b>：把别人跑出来的爆款视频，机器化拆成可复用的结构——钩子怎么埋、节奏怎么排、人群怎么戳、黄金句在哪，输出一份份可读的报告。它只做<b>拆解分析</b>；生成新视频、反推提示词分别由系列内其他项目负责。</p>'
        '<div class="kw"><span>#爆款拆解</span><span>#规则引擎</span><span>#Whisper 转写</span><span>#关键帧</span><span>#起号报告</span></div>',
    deliveries='<ul><li>单视频拆解报告（钩子/人群/节奏/结构）</li><li>章节表 + 关键帧截图</li><li>全文转写稿（可导出 MD/JSON）</li><li>EvoFlow 知识库直接可投喂的报告库</li></ul>',
    goal=[("拆解从 2 小时到 3 分钟", "人工看一条视频做结构笔记要小半天；机器流水线一条命令出报告，人只做最后审核。"),
          ("把「感觉」变成「结构」", "爆款方法论不靠悟：钩子类型、节奏密度、人群话术全部落成字段，可对比、可积累。"),
          ("沉淀成可复用资产", "报告进知识库后，AI 员工写脚本、做分析时直接引用，越拆越值钱。")],
    who=[("起号新手 / 小白运营", "不会写脚本也没方法论——看报告照抄结构：开头钩子抄哪条、节奏怎么排、评论区埋什么话。"),
         ("内容创作者 / 编导", "批量拆对标账号的视频，提炼钩子库和黄金句库，直接喂进自己的选题会和脚本初稿。"),
         ("AI 工作流搭建者", "把它当 EvoFlow 的「眼睛」：报告进知识库，配合员工/技能做出更上游的自动化。")],
    prob=[("看爆款只能「感觉它火」，说不出为什么火，学不会也讲不清", "报告直接标出钩子类型、人群、黄金句、节奏曲线，每一条都有出处（第几秒第几帧）"),
          ("下载、转写、截图、记笔记全手工，一条视频耗掉半天", "粘贴分享链接一键流水线，3 分钟出全套材料，人只负责审和用"),
          ("拆完的笔记散在各处，AI 用不上，自己也不想翻", "报告格式统一、落进知识库，AI 员工写脚本/做分析时随取随用")],
    combo=[("组合一 · 「拆解 → 反推 → 复刻」全链路<em>适合想快速复刻爆款的内容团队</em>", "",
        [("Step 1", "抖音视频拆解工作台", ":8765 粘链接出拆解报告，看清这条视频凭什么火"),
         ("Step 2", "AIGC 反推提示词", ":8768 把关键帧反推成 T2V/I2V 可粘贴 Prompt"),
         ("Step 3", "AI 创意广告视频", "用 Prompt + 套路库在小云雀生成你的版本样片"),
         ("Step 4", "宣传视频制作", ":8766 TTS 配音 + 分镜成稿，交付成片")]),
        ("组合二 · 「对标 → 分析 → 沉淀」数据链<em>适合做账号矩阵、长期沉淀方法论的操盘手</em>", "",
        [("Step 1", "抖音博主分析器", ":8787 圈定对标账号，看板找哪些视频值得拆"),
         ("Step 2", "抖音视频拆解工作台", "只拆数据证明过的爆款，不浪费拆解额度"),
         ("Step 3", "EvoFlow 接入套件", "报告一键进知识库，雇一个分析师员工常驻使用")])],
    daily=daily_cards("拆一条视频", "拆解报告与素材", "抖音拆解报告库"),
    assets='<code>douyin-analyst</code> 员工 · <code>douyin-video-pipeline</code> 技能 · <code>抖音拆解报告库</code> 知识库 · <code>视频拆解工作台 :8765</code> 扩展面板。接入或重建步骤见 <code>evoflow-onboarding-kit</code>。',
    prereq='装好 <b>Python 3.10+</b> 和 <b>ffmpeg</b>（Windows 可用 <code>winget install ffmpeg</code>）；首次运行会自动下载 Whisper 转写模型（约 1GB，需耐心）；抖音链接在手机 App 点「分享 → 复制链接」获得。',
    steps=[("启动工作台", "打开终端，进入项目目录运行服务；看到端口提示即成功。", '<span class="c"># 在项目根目录执行</span>\npython scripts/web_server.py\n<span class="ok"># ✓ Listening on http://127.0.0.1:8765</span>'),
           ("粘贴链接，点「开始拆解」", "浏览器打开工作台，把抖音分享链接粘进输入框。进度条走完大约 3 分钟：下载 → 转写 → 关键帧 → 生成报告。", None),
           ("读报告，照抄结构", "重点看四块：<b>钩子</b>（前 3 秒怎么留人）、<b>人群</b>（戳的是谁）、<b>节奏</b>（多久一个信息点）、<b>黄金句</b>（可直接借用的话术）。照着结构写你的第一条脚本。", None)],
    faqs=[("转写特别慢 / 卡在 0%？", "首次运行在下载模型，看终端进度；国内网络建议先配置镜像。若一直 0%，删除缓存目录重跑。"),
          ("分享链接打不开 / 下载失败？", "确认复制的是完整短链（v.douyin.com 开头）；私密或仅粉丝可见的视频无法下载，换公开视频。"),
          ("端口被占用？", "默认 8765，改启动脚本里的端口号即可；先关掉旧的 python 进程再启。")],
    prompt=dict(tool="抖音视频拆解工作台——粘贴分享链接，自动输出爆款拆解报告",
        users="起号新手 / 内容编导", scene="刷到爆款但说不出为什么火",
        expect="钩子/人群/节奏/黄金句四维度的结构化报告",
        features=["输入：分享短链粘贴框，支持 v.douyin.com",
                  "处理流水线：下载视频 → 提取音频转写 → 按 N 秒抽关键帧 → 逐段分析结构",
                  "输出：Web 报告页——钩子类型、人群画像、节奏曲线、黄金句列表，可导出 MD/JSON",
                  "历史记录：本地保存每次拆解，可回看列表"],
        stack="Python 标准库 HTTP 服务 + yt-dlp + faster-whisper + ffmpeg，前端原生 HTML/JS，零框架", port="8765", launch="python scripts/web_server.py")))

PROJS.append(dict(
    dir="self-media/douyin-blogger-analyzer", cat="自媒体", title="抖音博主分析器", status="可用（EvoFlow 接入打样）", ok=True, extra="数据双轨 · 机器真源",
    tagline="采集抖音博主公开数据做分析看板：数据看板 / 内容分析 / 标题钩子分类 / 多账号对比。accounts.json 是机器真源，markdown 报告是知识库喂养层。",
    specs=[("端口", "8787"), ("技术栈", "Node 18+ 零依赖 · playwright-core"), ("启动方式", "<code>node server.js</code>"), ("核心产出", "账号看板 / 钩子分析 / 对比报告")],
    pos='<p class="lead">这是一个<b>对标账号的「作战地图」</b>：采集博主公开数据（带登录态的浏览器采集 + API 直灌双轨），沉淀成看板——内容分析、标题钩子分类、多账号对比。<b>accounts.json 是机器真源</b>，<code>data/reports/*.md</code> 是给知识库吃的喂养层，两层分离互不污染。</p>'
        '<div class="kw"><span>#对标账号</span><span>#数据看板</span><span>#钩子分类</span><span>#多账号对比</span><span>#数据双轨</span></div>',
    deliveries='<ul><li>博主数据看板（内容/互动/更新节奏）</li><li>标题钩子分类分析</li><li>多账号横向对比报告</li><li>知识库喂养层 markdown 报告</li></ul>',
    goal=[("选对标不靠拍脑袋", "数据说话：谁的爆款密度高、钩子强，看板一眼见分晓。"),
          ("钩子方法可统计", "标题钩子自动分类，哪类钩子在这个赛道吃香一目了然。"),
          ("分析结论能喂 AI", "markdown 报告层直接进知识库，员工张口就能引用。")],
    who=[("账号操盘手", "起号前先摸清对标：发什么、怎么发、多久发。"),
         ("内容策略 / 编导", "从钩子分类里提炼标题套路库。"),
         ("AI 工作流搭建者", "把它当数据源：看板数据 + 报告层一起喂给员工。")],
    prob=[("刷了 hundreds 条视频也说不出对标号强在哪", "看板量化：爆款率、互动、节奏全摆出来"),
          ("标题好坏全凭感觉，没积累", "钩子自动分类统计，套路越攒越清楚"),
          ("分析结论写完就沉底，AI 用不上", "喂养层 markdown 进知识库，员工随时引用")],
    combo=[("组合一 · 「对标 → 拆解」选品链<em>先选对视频再拆</em>", "",
        [("Step 1", "抖音博主分析器", ":8787 圈定对标账号，看板找爆款密度高的"),
         ("Step 2", "抖音视频拆解工作台", ":8765 只拆数据证明过的爆款"),
         ("Step 3", "EvoFlow 接入套件", "报告进知识库沉淀")]),
        ("组合二 · 「分析 → 内容」生产链<em>把结论变成内容</em>", "",
        [("Step 1", "抖音博主分析器", "钩子分类出标题套路库"),
         ("Step 2", "宣传视频制作", ":8766 按套路出策划稿与配音")])],
    daily=daily_cards("分析一个账号", "账号分析报告", "抖音博主分析报告库"),
    assets='<code>douyin-blogger-analyst</code> 员工 · <code>douyin-blogger-analysis</code> 技能 · <code>抖音博主分析报告库</code> 知识库 · <code>抖音博主分析 :8787</code> 扩展面板。接入或重建步骤见 <code>evoflow-onboarding-kit</code>。',
    prereq='<b>Node.js 18+</b>（零依赖服务）；采集用 playwright-core 连接本机 Chrome/Edge（需带调试端口启动并登录一次抖音，见 start.bat 一键脚本）；采集只取公开数据，遵守平台条款。',
    steps=[("一键启动分析器 + 采集浏览器", "start.bat 同时起服务（8787）和带抖音登录态的独立 Chrome。", '<span class="c"># Windows 一键</span>\nstart.bat\n<span class="c"># 或手动：</span>\nnode server.js\n<span class="ok"># ✓ Listening on http://127.0.0.1:8787</span>'),
           ("采集 / 直灌数据", "用采集脚本抓博主公开数据，或 API 直灌；accounts.json 始终是机器真源。", '<span class="c"># 采集示例</span>\nnode scripts/collect-douyin.js <博主主页URL>'),
           ("看板分析，导出报告", "看板看内容与钩子分析，多账号对比；markdown 报告导出进知识库。")],
    faqs=[("采集浏览器起不来 / 没登录态？", "用 start.bat 的独立 user-data-dir；首次手动登录一次抖音并保持会话。"),
          ("数据会污染吗？", "不会：机器写 accounts.json，报告层在 data/reports/*.md，两层分离。"),
          ("能采集私信等非公开数据吗？", "不能，也不应该——只做公开数据分析。")],
    prompt=dict(tool="抖音博主分析器——采集公开数据出分析看板与钩子报告",
        users="账号操盘手 / 内容策略", scene="起号前要摸清对标账号的打法与钩子套路",
        expect="账号看板、钩子分类统计、多账号对比报告",
        features=["输入：博主主页链接采集（playwright-core 连本机浏览器）+ API 直灌",
                  "数据双轨：accounts.json 机器真源 + data/reports/*.md 知识库喂养层",
                  "看板：数据看板 / 内容分析 / 标题钩子分类 / 多账号对比",
                  "报告 markdown 导出，可直接投喂知识库"],
        stack="Node 18+ 零依赖 HTTP 服务 + playwright-core（采集）", port="8787", launch="node server.js")))

PROJS.append(dict(
    dir="productivity/evoflow-capability-demo", cat="个人效率", title="EvoFlow 业务场景台", status="可用（实网需 api_key）", ok=True, extra="S1–S4 场景演示",
    tagline="一场景一页的演示台：种子员工/知识库/编排后跑通 S1–S4（拆解师、KB 钩子、电商短视频编排、调研+成片大纲）。dry-run 只预览，真调通以 smoke_check --live 为准。",
    specs=[("端口", "8877"), ("技术栈", "EvoFlow Gateway API · scenario JSON"), ("启动方式", "<code>py -3.12 scripts/web_server.py</code>"), ("核心产出", "S1–S4 场景演示与验证")],
    pos='<p class="lead">这是 EvoFlow 能力的<b>「一场景一页」演示台</b>：每个场景一个页面，种子员工 + 知识库 + 编排跑给你看——S1 拆解师、S2 KB 钩子、S3 电商短视频编排、S4 调研+成片大纲。离线可 dry-run 预览流程，实网真调用以 <code>smoke_check --live</code> 通过为准，不糊弄。</p>'
        '<div class="kw"><span>#业务场景</span><span>#种子员工</span><span>#编排演示</span><span>#dry-run / live</span><span>#smoke 验证</span></div>',
    deliveries='<ul><li>S1–S4 四个场景演示页（scenarios/）</li><li>种子数据脚本（seed_demo.py）</li><li>smoke_check 离线/实网双模式验证</li><li>运行记录 JSON（data/runs/）</li></ul>',
    goal=[("能力看得见", "员工/知识库/编排不是概念，一页一个场景跑给你看。"),
          ("接入有标准", "smoke_check --live 是真调通的唯一标准，验收不扯皮。"),
          ("演示可复现", "seed 脚本一键铺底，任何时候能重演。")],
    who=[("给客户/领导演示的人", "几页页面把 EvoFlow 能力讲清楚。"),
         ("EvoFlow 接入开发者", "照场景学编排写法，照 smoke 学验收。"),
         ("培训讲师", "学员第一步先跑场景台建立体感。")],
    prob=[("平台能力文档一大堆，看完还是不知道能干嘛", "四个真实业务场景直接跑，看完就有体感"),
          ("「接好了」全靠嘴说，出问题互相甩锅", "smoke_check --live 一跑便知，通过才算数"),
          ("演示环境难复原", "seed 一键铺种子数据，dry-run 离线也能演")],
    combo=[("组合一 · 「接入 → 演示 → 验收」<em>新项目接入 EvoFlow 的标准动作</em>", "",
        [("Step 1", "EvoFlow 接入套件", "注册扩展/知识库/员工四脚本一条龙"),
         ("Step 2", "EvoFlow 业务场景台", ":8877 场景页演示编排效果"),
         ("Step 3", "smoke_check --live", "实网验证通过才算接入完成")]),
        ("组合二 · 「场景 → 业务项目」映射<em>演示场景对应真实项目</em>", "",
        [("Step 1", "S1 拆解师 / S2 KB 钩子", "对应抖音拆解台 :8765 与知识库体系"),
         ("Step 2", "S3 电商短视频编排", "对应商策造物与宣传视频制作"),
         ("Step 3", "S4 调研+成片大纲", "对应 AIGC 创作链的起点")])],
    daily=daily_cards("跑一个场景", "场景运行记录与报告", "场景演示库（建议命名）"),
    assets='<code>evoflow-capability-demo</code> 技能已注册平台技能；员工/知识库为场景内种子资产（seed_demo.py 铺设）。接入或重建步骤见 <code>evoflow-onboarding-kit</code>。',
    prereq='离线演示零依赖；实网调用需要 <b>EvoFlow Gateway api_key</b>（走环境变量）与 gateway 地址配置（config/evoflow.json）；Python 3.12。',
    steps=[("铺种子数据", "一键铺设演示用员工/知识库/场景数据。", '<span class="c"># 在项目根目录执行</span>\npy -3.12 scripts/seed_demo.py\npy -3.12 scripts/web_server.py\n<span class="ok"># ✓ Listening on http://127.0.0.1:8877</span>'),
           ("跑场景（dry-run / live）", "页面一场景一页：先 dry-run 预览流程，实网确认后 live 跑通。", '<span class="c"># 实网验收</span>\npy -3.12 scripts/smoke_check.py --live'),
           ("看运行记录", "每次运行落 JSON（data/runs/），演示完可回放复盘。")],
    faqs=[("dry-run 和 live 差在哪？", "dry-run 只按 scenario JSON 预览编排路径不发请求；live 真调 Gateway，以 smoke_check --live 全绿为准。"),
          ("实网 401 / 连不上？", "检查 api_key 环境变量与 config/evoflow.json 的 gateway 地址。"),
          ("能加自己的场景吗？", "能：在 scenarios/ 加一份场景 JSON + 一个页面，照 S1 的结构写。")],
    prompt=dict(tool="EvoFlow 业务场景演示台——一场景一页跑通员工/知识库/编排",
        users="演示者 / EvoFlow 接入开发者", scene="要把平台能力讲清楚、接入要可验收",
        expect="S1–S4 场景演示 + 可重复的验证手段",
        features=["场景 JSON 驱动：一场景一页，含编排路径展示",
                  "种子数据：一键铺设演示员工/知识库",
                  "双模式：dry-run 离线预览 / live 实网调用",
                  "smoke_check 验收脚本 + 运行记录 JSON 归档"],
        stack="Python 标准库 HTTP + EvoFlow Gateway API + scenario JSON", port="8877", launch="py -3.12 scripts/web_server.py")))

PROJS.append(dict(
    dir="productivity/smart-coach", cat="个人效率", title="智能陪练（学员版）", status="可用", ok=True, extra="EvoFlow 接入项目",
    tagline="学员向陪练台：上传资料、看进度与最近会话；梳大纲 / 短问答陪练 / 答疑由 EvoFlow 员工「陪练师」完成，本地 JSON 记录进度，学习不断档。",
    specs=[("端口", "8769"), ("技术栈", "Python 标准库 · EvoFlow 员工"), ("启动方式", "<code>py -3.12 scripts/web_server.py</code>"), ("核心产出", "大纲 / 陪练记录 / 答疑")],
    pos='<p class="lead">这是一个<b>学员视角的陪练面板</b>：本地面板管资料、进度和最近会话；真正的「梳大纲、短问答陪练、答疑」由 EvoFlow 员工「陪练师」完成。本地真源是 <code>data/outline.json</code> + <code>progress.json</code>，提示词在 <code>prompts/coach-system.md</code>，白盒可改。</p>'
        '<div class="kw"><span>#智能陪练</span><span>#学员面板</span><span>#进度追踪</span><span>#EvoFlow 员工</span><span>#白盒提示词</span></div>',
    deliveries='<ul><li>学员面板（资料/进度/最近会话）</li><li>梳大纲 / 短问答 / 答疑三类陪练</li><li>本地进度真源（outline + progress JSON）</li><li>可定制的陪练师系统提示词</li></ul>',
    goal=[("一个人也能练下去", "短问答陪练逼你输出，进度看得见，不靠意志力硬撑。"),
          ("学习过程有痕迹", "每次陪练落本地 JSON，回看薄弱点在哪一目了然。"),
          ("陪练风格可调", "系统提示词是明文文件，想要苏格拉底式还是直给式自己改。")],
    who=[("备考/学新技能的学员", "有资料没陪练，一个人刷题容易放弃。"),
         ("培训 / 教育机构", "给学员配一个不疲倦的陪练师。"),
         ("知识工作者", "把读过的文档变成可问答、可检验的知识。")],
    prob=[("资料存了一堆，从不回头看", "上传即成陪练素材，梳大纲逼你消化"),
          ("自学没人对练，学了就忘", "短问答反复练，答不上马上答疑补漏"),
          ("进度全凭感觉", "progress.json 量化记录，薄弱点可视化")],
    combo=[("组合一 · 「资料 → 陪练 → 沉淀」学习链<em>学员的日常闭环</em>", "",
        [("Step 1", "智能陪练（本台）", ":8769 上传资料，员工梳出大纲"),
         ("Step 2", "短问答陪练 + 答疑", "按大纲逐点练，不会的当场问"),
         ("Step 3", "进度沉淀", "outline/progress 本地归档，下次接着练")]),
        ("组合二 · 「知识库 → 陪练」复用链<em>组织知识变成训练场</em>", "",
        [("Step 1", "EvoFlow 接入套件", "把机构知识库接进 EvoFlow"),
         ("Step 2", "智能陪练", "陪练师查知识库出题与答疑"),
         ("Step 3", "EvoFlow 业务场景台", ":8877 演示教学场景编排")])],
    daily=daily_cards("练一轮问答", "陪练记录与进度更新", "陪练资料库"),
    assets='<code>smart-coach</code> 员工 · <code>smart-coach</code> 技能 · <code>陪练资料库</code> 知识库 · <code>智能陪练 :8769</code> 扩展面板。接入或重建步骤见 <code>evoflow-onboarding-kit</code>。',
    prereq='<b>Python 3.12</b>（标准库即可跑）；员工侧由 EvoFlow 平台承载，需 EvoFlow 环境可用；陪练资料提前备好（PDF/MD/文本）。',
    steps=[("启动陪练台", "在项目根目录执行，浏览器打开 8769。", '<span class="c"># 在项目根目录执行</span>\npy -3.12 scripts/web_server.py\n<span class="ok"># ✓ Listening on http://127.0.0.1:8769</span>'),
           ("上传资料，让陪练师梳大纲", "资料入库后一键梳大纲；对大纲顺序不满意可让它调整。"),
           ("逐点陪练 + 答疑", "短问答模式练大纲各点，答不上即时答疑；进度自动落 progress.json。")],
    faqs=[("陪练没反应？", "面板只做展示，梳/练/答在员工侧——确认 EvoFlow 环境与 smart-coach 员工在线。"),
          ("换一门课怎么重开？", "清空/替换 data/outline.json 与 progress.json（先备份），重新上传新资料。"),
          ("能改陪练风格吗？", "能：prompts/coach-system.md 是明文系统提示词，改完重开会话即可。")],
    prompt=dict(tool="智能陪练学员台——本地面板 + EvoFlow 员工完成梳大纲/陪练/答疑",
        users="备考与技能学习的学员", scene="有资料但没人陪练，自学难坚持",
        expect="大纲式陪练 + 可追踪的进度记录",
        features=["资料上传与管理",
                  "三类陪练：梳大纲 / 短问答陪练 / 答疑（员工侧完成）",
                  "学员面板：进度总览与最近会话展示",
                  "本地真源：outline.json + progress.json，提示词白盒可改"],
        stack="Python 标准库 HTTP 服务 + 本地 JSON 进度 + EvoFlow 员工/知识库", port="8769", launch="py -3.12 scripts/web_server.py")))

PROJS.append(dict(
    dir="ecommerce/ecommerce-content-studio", cat="电商", title="商策造物 · 电商智能创作中枢", status="可用（洞察开箱可用）", ok=True, extra="收录自黎小 1022 项目",
    tagline="单品电商内容生产全栈应用：公开网页检索提炼痛点/卖点/创意方向，按平台规格生成主图套装、SKU 套图、详情页与三类视频，含违禁词初筛、报价确认与成果管理。",
    specs=[("端口", "5173 Web / 8790 API"), ("技术栈", "React 18 · Vite · Express"), ("启动方式", "<code>npm run dev</code>"), ("核心产出", "主图 / SKU / 详情页 / 视频全套")],
    pos='<p class="lead">这是一个<b>单品电商内容工厂</b>：从「全网洞察」开始（公开网页检索提炼痛点/卖点/创意方向，免费开箱可用），到按平台规格批量生成主图套装、SKU 套图、详情页竖图与三类视频，全程带违禁词初筛、报价确认（生成前弹窗确认才扣费）与成果管理。生图/生视频由 BOLI CLI 承载。</p>'
        '<div class="kw"><span>#全网洞察</span><span>#主图套装</span><span>#详情页</span><span>#违禁词初筛</span><span>#BOLI CLI</span></div>',
    deliveries='<ul><li>痛点 / 卖点 / 创意方向洞察报告</li><li>主图套装 + SKU 套图 + 详情页竖图</li><li>三类平台规格视频</li><li>违禁词初筛 + 报价确认单 + 成果管理</li></ul>',
    goal=[("洞察→成图一条线", "调研和生图不用两头跑，同一个项目里做完。"),
          ("规格合规双保险", "平台规格自动适配，违禁词先筛一道再人工确认。"),
          ("花钱花得明白", "生成前报价确认，扣费透明。")],
    who=[("电商卖家 / 店铺运营", "上新要全套素材，一条流水线出齐。"),
         ("代运营 / 服务商", "多单品批量交付，成果管理跟得上。"),
         ("内容电商创作者", "短视频带货要图要视频都要，一站出。")],
    prob=[("洞察靠手动刷网页，卖点提炼全凭感觉", "公开网页检索自动提炼痛点/卖点/创意方向"),
          ("主图/详情页外包又贵又慢", "按平台规格批量生成，本地管理随时改"),
          ("AI 生图费用不透明，违禁词踩雷", "报价确认后才扣费；违禁词初筛前置")],
    combo=[("组合一 · 本台全流程（内置闭环）<em>单品内容生产的标准路径</em>", "",
        [("Step 1", "建项目 + 素材入库", "平台/语言/多视角图就位"),
         ("Step 2", "全网洞察 → 图片创作", "痛点卖点提炼，主图/SKU/详情页生成"),
         ("Step 3", "视频工坊 + 合规交付", "文生视频、违禁词初筛、报价确认、成果归档")]),
        ("组合二 · 「洞察 → 广告投放」放大链<em>从素材到投放</em>", "",
        [("Step 1", "商策造物", "洞察卖点 + 全套素材"),
         ("Step 2", "AI 创意广告视频", "把卖点写成广告片样片与成片"),
         ("Step 3", "AI 海报编辑器", ":8899 精修促销海报补充投放素材")])],
    daily=daily_cards("生成一套素材", "洞察报告与全套内容", "电商内容库（建议命名）"),
    assets=None,
    prereq='<b>Node.js 18+</b>；<code>npm install</code> 后 <code>npm run dev</code>；全网洞察零密钥开箱可用；主图/SKU/详情页/视频生成需安装并登录 <b>BOLI CLI</b>（<code>npm i -g @boli-ai/cli</code>，账号有积分）。',
    steps=[("起前后端", "一次安装，前端 5173 + API 8790 同时起。", '<span class="c"># 在项目根目录执行</span>\nnpm install\nnpm run dev\n<span class="ok"># ✓ web http://localhost:5173 · api http://localhost:8790</span>'),
           ("建项目 → 全网洞察", "选平台和语言建项目，素材入库（多视角图），跑全网洞察出痛点/卖点/创意方向。"),
           ("生图生视频，确认报价后交付", "主图/SKU/详情页/视频按需生成（需 BOLI CLI），违禁词初筛通过、报价确认后执行，成果进 generated/ 归档。")],
    faqs=[("洞察免费吗？", "免费——公开网页检索提炼，不依赖付费 API，开箱可用。"),
          ("生图报错？", "确认 BOLI CLI 已安装并登录、积分充足；生成前会弹报价确认，取消不扣费。"),
          ("能直接上架吗？", "产出为素材与初筛，上架前请人工复核平台合规要求。")],
    prompt=dict(tool="电商智能创作中枢——全网洞察 + 主图/SKU/详情页/视频批量生成",
        users="电商卖家与代运营", scene="单品上新要全套合规素材，人工出图慢且贵",
        expect="痛点/卖点洞察 + 平台规格的全套内容素材",
        features=["全网洞察：公开网页检索提炼痛点/卖点/创意方向（零密钥可用）",
                  "图片创作：主图套装 / SKU 套图 / 详情页竖图，按平台规格",
                  "视频工坊：文生视频三类规格",
                  "合规与费用：违禁词初筛 + 报价确认后才扣费 + 成果管理"],
        stack="React 18 + Vite 前端 + Express 单文件后端 + BOLI CLI（生图/生视频）", port="5173 Web / 8790 API", launch="npm install && npm run dev")))

# ───────────────────────── 生成 ─────────────────────────
def build(p):
    spec_html = spec(p["specs"])
    pos_body = p["pos"].replace("<!-- ✏️ 定位正文：它是什么 + 核心机制 + 边界 -->", "").replace("<!-- ✏️ 列出核心产出 -->", "")
    pos_body = ('<div class="card">' + p["pos"] + "</div>"
                '<div class="card"><svg class="ic lg"><use href="#i-box"/></svg><h3>交付物</h3>' + p["deliveries"] + "</div>")
    goal_body = goals(p["goal"])
    who_body = personas(p["who"])
    prob_body = problems(p["prob"])
    combo_body = "".join(combo(*c) for c in p["combo"])
    if p.get("assets"):
        assets_callout = callout("i-plug", "本项目已绑定的 EvoFlow 资产", p["assets"])
    else:
        assets_callout = callout("i-plug", "EvoFlow 接入",
            "本项目尚未注册 EvoFlow 资产——用 <code>evoflow-onboarding-kit</code> 一键接入：注册扩展面板 → 同步知识库 → 雇佣员工，四个脚本一条龙（已在拆解台 / 博主分析器打样）。")
    daily_body = p["daily"] + assets_callout
    start_body = quickstart(p["prereq"], p["steps"], p["faqs"])
    prompt_body = prompt_block(**p["prompt"]) + TIPS
    bodies = {"pos": pos_body, "goal": goal_body, "who": who_body,
              "prob": prob_body, "combo": combo_body, "daily": daily_body, "start": start_body,
              "prompt": prompt_body}
    p = {**p, "spec_html": spec_html}
    for sid, body in bodies.items():
        p[sid] = sec_html(sid, body)
    return render(p)

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in PROJS:
        html = build(p)
        out = os.path.join(base, p["dir"], "intro.html")
        io.open(out, "w", encoding="utf-8", newline="\n").write(html)
        print("ok", p["dir"] + "/intro.html")

if __name__ == "__main__":
    main()
