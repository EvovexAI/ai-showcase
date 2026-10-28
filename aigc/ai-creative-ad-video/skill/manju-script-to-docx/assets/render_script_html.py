# -*- coding: utf-8 -*-
"""把《女猎户》正文 part1（体例：## 第N集 / 场景 / 出场人物 / **角色**（动作）："台词" / △ / 【本集卡点】）
   渲染成一份可读的 HTML 剧本阅读版（浅/深色自适应）。
   用法： python3 render_script_html.py <正文.md> <输出.html>
"""
import re, sys, html, os

src, dst = sys.argv[1], sys.argv[2]
raw = open(src, encoding='utf-8').read()

TITLE = ''
META = []
EP = re.compile(r'^## (第\d+集)（([^）]*)）\s*$')
# ★引号体例：正文以直角引号 U+0022 为主，但有极少数行混入全角弯引号 “ ”
#   （实测 E5／E6 各 1 行）—— 渲染器**两种都吃**，否则那两行会掉成普通段落
#   （同族坑：`dlgcheck.DQ` 只认直角 ⇒ ⑤ 少抽 2 句；`langcheck.DLG_IN` 已容忍两式）
DLG = re.compile(r'^\*\*([^*]+)\*\*(?:（([^）]*)）)?\s*[：:]\s*["“](.*?)["”]\s*$')
CARD = re.compile(r'^\*{0,2}【本集卡点】\*{0,2}\s*(.*)$')
END = re.compile(r'^——(第\d+集)完——\s*$')

CHANGED_EP = {'第1集'}          # ★本轮改过的集
body, ep_buf = [], []
cur_ep = None


def flush():
    global ep_buf, cur_ep
    if cur_ep is None:
        return
    cls = ' ep-changed' if cur_ep in CHANGED_EP else ''
    tag = ('<span class="tag">★ 2026-09-17 二次调整</span>'
           if cur_ep in CHANGED_EP else '')
    head = ep_buf[0]
    if tag:                                   # ★标签必须放进 <h2> 内，才能跟着 flex 右浮
        head = head.replace('</h2>', tag + '</h2>')
    body.append('<section class="ep%s">%s' % (cls, head))
    body.extend(ep_buf[1:])
    body.append('</section>')
    ep_buf, cur_ep = [], None


for line in raw.split('\n'):
    s = line.rstrip()
    if not s.strip():
        continue
    if s.startswith('# '):
        TITLE = s[2:].strip()
        continue
    if s.startswith('> '):
        META.append(s[2:].strip())
        continue
    m = EP.match(s)
    if m:
        flush()
        cur_ep = m.group(1)
        ep_buf = ['<h2>%s<em>%s</em></h2>' % (m.group(1), html.escape(m.group(2)))]
        continue
    if s.startswith('场景：') or s.startswith('出场人物：'):
        k, v = s.split('：', 1)
        ep_buf.append('<p class="hdr"><b>%s</b>：%s</p>' % (k, html.escape(v)))
        continue
    m = DLG.match(s)
    if m:
        who, act, txt = m.group(1), m.group(2) or '', m.group(3)
        a = '<span class="act">（%s）</span>' % html.escape(act) if act else ''
        ep_buf.append('<p class="dlg"><b>%s</b>%s<span class="q">“%s”</span></p>'
                      % (html.escape(who), a, html.escape(txt)))
        continue
    m = CARD.match(s)
    if m:
        ep_buf.append('<p class="card"><span>本集卡点</span>%s</p>' % html.escape(m.group(1)))
        continue
    m = END.match(s)
    if m:
        ep_buf.append('<p class="end">——%s 完 ——</p>' % m.group(1))
        continue
    if s.startswith('△'):
        ep_buf.append('<p class="act-line">%s</p>' % html.escape(s))
        continue
    ep_buf.append('<p class="other">%s</p>' % html.escape(s))
flush()

def md_clean(x):
    """元信息行里的 Markdown 强调/行内码去掉，避免页面上露出 ** 与 ` """
    x = re.sub(r'\*\*(.+?)\*\*', r'\1', x)
    x = x.replace('`', '')
    return x


meta_html = ''.join('<p>%s</p>' % html.escape(md_clean(x)) for x in META)

DOC = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<style>
:root{--bg:#f5f2ec;--paper:#fffdf8;--ink:#23201c;--muted:#8a8378;--rule:#e3ddd1;
      --dlg:#1b1a17;--act:#8b8578;--card:#8a2f1d;--cardbg:#fbeee9;--who:#1f4d3a;--tag:#8a2f1d}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--paper:#1e2126;--ink:#e6e3dd;--muted:#8d8b86;
      --rule:#33373d;--dlg:#eceae5;--act:#9a968d;--card:#e2a08c;--cardbg:#2c2320;--who:#8fc9ac;--tag:#e2a08c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font-family:-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
     line-height:1.85;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:40px 28px 80px}
h1{font-size:20px;margin:0 0 6px;letter-spacing:.5px}
.meta{border-left:3px solid var(--rule);padding:6px 0 6px 14px;margin:14px 0 30px;
      color:var(--muted);font-size:12.5px;line-height:1.9}
.meta p{margin:2px 0}
section.ep{background:var(--paper);border:1px solid var(--rule);border-radius:10px;
      padding:22px 26px 26px;margin:0 0 22px}
section.ep.ep-changed{border-color:var(--tag);box-shadow:0 0 0 3px rgba(138,47,29,.06)}
h2{font-size:15.5px;margin:0 0 16px;padding-bottom:10px;border-bottom:1px dashed var(--rule);
   display:flex;align-items:baseline;gap:10px}
h2 em{font-style:normal;font-size:12.5px;color:var(--muted);font-weight:400}
.tag{margin-left:auto;font-size:11px;color:var(--tag);border:1px solid var(--tag);
     border-radius:20px;padding:1px 9px;white-space:nowrap}
p{margin:0}
.hdr{font-size:12.5px;color:var(--muted);margin:0 0 2px}
.hdr b{color:var(--ink);font-weight:600}
.dlg{margin:11px 0 11px;font-size:15px}
.dlg b{color:var(--who);font-weight:700;margin-right:2px}
.dlg .act{color:var(--act);font-size:12.5px;margin:0 2px}
.dlg .q{color:var(--dlg)}
.act-line{color:var(--act);font-size:13.5px;margin:9px 0}
.card{margin:16px 0 12px;padding:9px 13px;background:var(--cardbg);border-radius:6px;
      font-size:13px;color:var(--card)}
.card span{font-weight:700;margin-right:8px;letter-spacing:1px}
.end{text-align:center;color:var(--muted);font-size:12px;letter-spacing:3px;margin:18px 0 0}
</style></head><body><div class="wrap">
<h1>%(title)s</h1><div class="meta">%(meta)s</div>
%(body)s
</div></body></html>""" % dict(title=html.escape(TITLE), meta=meta_html, body='\n'.join(body))

open(dst, 'w', encoding='utf-8').write(DOC)
print('★已生成阅读版：%s（%d 字节）' % (dst, os.path.getsize(dst)))
print('   集数 %d ｜ 段落 %d' % (len(CHANGED_EP) and sum(x.count('<h2>') for x in body) or 0,
                                 len(body)))
