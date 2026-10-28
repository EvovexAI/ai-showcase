"""Render the insight sections as markdown lines for report.md (v2)."""
from __future__ import annotations


def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def render_insights_markdown(insights: dict) -> list[str]:
    lines: list[str] = []
    hook = insights.get("hook", {})
    audience = insights.get("audience", {})
    golden = insights.get("golden_lines", [])
    why = insights.get("why_attractive", {})
    traits = insights.get("traits", [])
    pacing = insights.get("pacing") or {}
    visual = insights.get("visual_language") or {}
    structure = insights.get("structure") or {}
    emotion = insights.get("emotion") or {}
    eval = insights.get("emotional_value") or {}
    data_notes = insights.get("data_notes") or []
    takeaways = insights.get("takeaways") or {}

    # ── 顶部一句话速览 ──
    lines.extend([
        "",
        "## ⚡ 一句话速览",
        "",
    ])
    quick_bits = []
    if hook.get("techniques"):
        quick_bits.append(f"钩子：{'/'.join(hook['techniques'])}")
    if audience.get("identity_tags"):
        quick_bits.append(f"人群：{'、'.join(audience['identity_tags'][:3])}")
    if eval.get("main_emotion"):
        quick_bits.append(f"情绪价值：{eval['main_emotion']}")
    if pacing.get("pace_label"):
        quick_bits.append(f"节奏：{pacing['pace_label']}（{pacing.get('chars_per_minute', '—')} 字/分）")
    if structure.get("formula"):
        quick_bits.append(f"结构：{structure['formula']}")
    if quick_bits:
        lines.append("> " + " ｜ ".join(quick_bits))
    lines.append("")

    # ── 可参考学习的点（放最前，用户最关心怎么抄） ──
    if takeaways:
        lines.extend(["## 🎯 可参考学习的点", ""])
        for i, item in enumerate(takeaways.get("copy", []), 1):
            lines.append(f"**{i}. {item.get('what', '')}**")
            lines.append("")
            lines.append(f"   ↳ {item.get('how', '')}")
            lines.append("")
        if takeaways.get("avoid"):
            lines.append("**⚠️ 避坑提醒**")
            lines.append("")
            for a in takeaways["avoid"]:
                lines.append(f"- {a}")
            lines.append("")
        if takeaways.get("checklist"):
            lines.append("**✅ 套用到你自己的视频（检查清单）**")
            lines.append("")
            for c in takeaways["checklist"]:
                lines.append(f"- [ ] {c}")
            lines.append("")

    # ── 一、开场钩子 ──
    lines.extend(["## 一、开场钩子（Hook）", ""])
    if hook.get("hook_text"):
        dur = f"（前 {hook['hook_seconds']} 秒）" if hook.get("hook_seconds") else ""
        lines.append(f"> {hook['hook_text']}{dur}")
        lines.append("")
    if hook.get("techniques"):
        lines.append("**钩子手法**：" + "、".join(hook["techniques"]))
    if hook.get("why_it_works"):
        lines.append("")
        lines.append(f"**为何有效**：{hook['why_it_works']}")

    # ── 二、目标人群 ──
    lines.extend(["", "## 二、目标人群", ""])
    if audience.get("audience_line"):
        lines.append(audience["audience_line"])
    bits = []
    if audience.get("pain_points"):
        bits.append("**痛点词**：" + "、".join(audience["pain_points"]))
    if audience.get("desires"):
        bits.append("**欲望词**：" + "、".join(audience["desires"]))
    if audience.get("hashtags"):
        bits.append("**话题标签**：" + " ".join(audience["hashtags"]))
    if audience.get("author"):
        bits.append(f"**作者**：{audience['author']}")
    for b in bits:
        lines.extend(["", b])

    # ── 三、黄金句 ──
    lines.extend(["", "## 三、黄金句（可复用表达）", ""])
    if golden:
        lines.extend(["| 时间 | 金句 | 亮点词 |", "|------|------|--------|"])
        for g in golden:
            cues = "、".join(g.get("cue_words") or []) or "-"
            lines.append(f"| {g.get('time_range', '')} | {_esc(g.get('text', ''))} | {cues} |")
    else:
        lines.append("（未识别出明显的金句——口播偏叙述型，建议人工从完整口播稿中摘取）")

    # ── 四、节奏剖面 ──
    if pacing:
        lines.extend(["", "## 四、节奏剖面", ""])
        lines.append(
            f"**{pacing.get('pace_label', '—')}节奏** · {pacing.get('chars_per_minute', '—')} 字/分钟 · "
            f"{pacing.get('segment_count', '—')} 段口播（平均 {pacing.get('avg_segment_seconds', '—')}s/段） · "
            f"{pacing.get('cuts_per_minute', '—')} 次切镜/分钟"
        )
        if pacing.get("pace_note"):
            lines.append("")
            lines.append(f"- {pacing['pace_note']}")
        if pacing.get("cut_note"):
            lines.append(f"- {pacing['cut_note']}")

    # ── 五、视觉语言 ──
    if visual:
        lines.extend(["", "## 五、视觉语言", ""])
        if visual.get("summary"):
            lines.append(visual["summary"])
        vtypes = visual.get("types") or []
        if vtypes:
            lines.extend(["", "| 画面形态 | 占比 | 说明 |", "|----------|------|------|"])
            for t in vtypes:
                lines.append(f"| {t['label']} | {t['pct']}% | {t.get('note', '')} |")
        if visual.get("tools_visible"):
            lines.extend(["", f"**出现的工具/产品**：{'、'.join(visual['tools_visible'])}"])
        if visual.get("elements"):
            els = "、".join(e["name"] for e in visual["elements"][:6])
            lines.extend(["", f"**常见元素**：{els}"])

    # ── 六、结构模板 ──
    if structure and structure.get("formula"):
        lines.extend(["", "## 六、结构模板（可直接套用）", ""])
        lines.append(f"**公式**：{structure['formula']}")
        lines.append("")
        lines.extend(["| 时间 | 段落 | 角色 | 占比 | 内容 |", "|------|------|------|------|------|"])
        for b in structure.get("beats", []):
            lines.append(
                f"| {b.get('time_range', '')} | {_esc(b.get('title', ''))} | {b.get('role', '')} | {b.get('pct', 0)}% | {_esc(b.get('summary', ''))[:60]} |"
            )

    # ── 七、情绪/密度曲线 ──
    if emotion and emotion.get("buckets"):
        lines.extend(["", "## 七、信息密度曲线", ""])
        lines.append(f"**形态**：{emotion.get('shape', '—')}")
        lines.append("")
        lines.append("```")
        peak = max(b["chars_per_min"] for b in emotion["buckets"]) or 1
        for b in emotion["buckets"]:
            bar = "█" * max(1, round(b["chars_per_min"] / peak * 24))
            lines.append(f"{b['range']} | {bar} {b['chars_per_min']}")
        lines.append("```")
        roles_flat = sorted({r for b in emotion["buckets"] for r in b.get("roles", [])})
        if roles_flat:
            lines.append("")
            lines.append(f"段落角色分布：{'、'.join(roles_flat)}")

    # ── 八、为什么吸引人 ──
    lines.extend(["", "## 八、为什么吸引人", ""])
    for p in why.get("points", []):
        lines.append(f"- {p}")

    # ── 九、情绪价值 ──
    if eval:
        lines.extend(["", "## 九、情绪价值（观众得到了什么感觉）", ""])
        if eval.get("summary"):
            lines.append(f"**{eval['summary']}**")
            lines.append("")
        hits = eval.get("hits") or []
        if hits:
            lines.extend(["| 情绪 | 给观众的价值 | 触发词 | 兑现位置 |", "|------|-------------|--------|---------|"])
            for h in hits:
                pos = f"前 {h['first_pct']}%" if h.get("first_pct") is not None else "—"
                lines.append(
                    f"| {h['label']} | {_esc(h['value'])} | {'、'.join(h.get('cue_words', [])) or '—'} | {pos} |"
                )
            lines.append("")
        if eval.get("early_delivered") is False and hits:
            lines.append("> ⚠️ 主情绪出现偏晚（30% 之后）：开场情绪钩子弱，前段流失风险高。")
        elif hits and eval.get("early_delivered"):
            lines.append(f"> ✅ 主情绪在前 {hits[0].get('first_pct', '—')}% 兑现，情绪钩子成立。")
        if eval.get("how_to"):
            lines.extend(["**怎么抄这份情绪设计**", ""])
            if eval.get("peak_note"):
                lines.append(f"- {eval['peak_note']}")
            for t in eval["how_to"]:
                lines.append(f"- {t}")

    # ── 十、作品特点 ──
    lines.extend(["", "## 十、作品特点", ""])
    for t in traits:
        lines.append(f"- {t}")

    # ── 十一、对标数据（自查基准） ──
    if data_notes:
        lines.extend(["", "## 十一、对标数据（做同款时对齐）", ""])
        lines.extend(["| 指标 | 本片 | 常见基准 | 判读 |", "|------|------|----------|------|"])
        for d in data_notes:
            lines.append(f"| {d['metric']} | {_esc(d['value'])} | {d['benchmark']} | {d['note']} |")

    return lines
