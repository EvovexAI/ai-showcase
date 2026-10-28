#!/usr/bin/env python3
"""Insight engine: derive self-media insights (hook / audience / golden lines /
why-it-works / traits) from an analysis report dict — heuristic only, no LLM."""

from __future__ import annotations

import re
from collections import Counter


# ---------- helpers ----------

_HOOK_CUES = [
    "你以为", "你有没有", "为什么", "凭什么", "别再", "不要", " STOP", "停",
    "告诉你", "真相", "秘密", "注意", "如果你", "你还", "千万别", "我敢",
    "99%", "90%", "80%", "大部分", "大多数人", "所有人", "揭秘", "内幕",
    "竟然", "居然", "其实", "一定", "绝对", "千万别",
]

_QUESTION_RE = re.compile(r"[?？]")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?(?:%|％|倍|年|个月|天|次|万|千|百|块钱|元)?")
_GOLDEN_CUES = [
    "本质", "核心", "真相", "逻辑", "记住", "一句话", "说白了", "换句话说",
    "底层", "公式", "密码", "心法", "原则", "标准", "关键", "重点",
]
_CTA_CUES = ["关注", "点赞", "收藏", "评论", "私信", "转发", "点个"]
_PERSON_RE = re.compile(
    r"(打工人|职场|宝妈|学生|创业者|老板|新手|小白|运营|博主|自媒体|程序员|设计师|"
    r"销售|管理者|副业| freelancers?|新手爸妈|考研|考公|大学生|毕业生|男生|女生|"
    r"男人|女人|年轻人|中年人|35岁)"
)
_SCENE_RE = re.compile(
    r"(刷到|下班|睡前|通勤|吃饭|开會|开会|带娃|躺平|内卷|迷茫|焦虑|加班|裁员|"
    r"工资|薪资|负债|存款|搞钱|变现|涨粉|完播|流量)"
)

PAIN_TRIGGERS = ["焦虑", "迷茫", "内卷", "裁员", "失败", "亏", "赔", "难", "累", "痛苦", "困扰", "烦恼", "不可能", "做不到"]
DESIRE_TRIGGERS = ["赚钱", "变现", "涨粉", "成功", "逆袭", "翻身", "搞钱", "副业", "流量", "爆款", "涨薪", "升职"]

# ---------- 情绪价值（Emotional Value）词库 ----------

# 情绪类别：识别词 → 观众获得的情绪价值
_EMOTION_LEXICON: list[dict] = [
    {
        "key": "relief",
        "label": "释然/减压",
        "value": "「原来不止我这样」——把观众的焦虑正常化，看完心里松一口气",
        "cues": ["焦虑", "内卷", "迷茫", "压力", "喘不过气", "失眠", "emo", "崩溃", "撑不下去", "好难", "委屈", "郁结"],
    },
    {
        "key": "hope",
        "label": "希望/激励",
        "value": "「我也可以」——给出可复制的路径，把羡慕转化为行动意愿",
        "cues": ["逆袭", "翻身", "从零", "普通人", "你也可以", "你也可以的", "起步", "零基础", "上手", "30天", "21天", "改变"],
    },
    {
        "key": "vindication",
        "label": "共鸣/被代言",
        "value": "「说到我心坎里」——观众觉得你替他说出了不敢说的话，转发欲最强",
        "cues": ["你是不是", "我们都", "大家都会", "别装了", "说实话", "扎心", "现实", "没有人告诉你", "没人告诉你"],
    },
    {
        "key": "anger",
        "label": "愤慨/打抱不平",
        "value": "「太对了，就是这个理」——共同敌人点燃情绪，评论区易吵热",
        "cues": ["凭什么", "凭什么啊", "恶心", "无耻", "割韭菜", "套路", "骗局", "黑幕", "不公", "资本"],
    },
    {
        "key": "superiority",
        "label": "优越/信息差快感",
        "value": "「我知道别人不知道的」——先人一步的信息差，驱使收藏和转发炫耀",
        "cues": ["99%", "大多数人都不知道", "90%的人", "内行", "内幕", "揭秘", "真相", "潜规则", "少走弯路", "提前知道"],
    },
    {
        "key": "competence",
        "label": "获得感/学会了的踏实",
        "value": "「今天没白刷」——明确的收获感，是收藏和关注的核心驱动",
        "cues": ["学会", "搞定", "三步", "一步", "公式", "方法", "教程", "手把手", "保姆级", "干货", "模板", "清单"],
    },
    {
        "key": "safety",
        "label": "安全感/避坑",
        "value": "「幸好早看到」——帮观众避开损失，信任感来自「替我挡刀」",
        "cues": ["避坑", "别再", "千万不要", "千万别", "小心", "警惕", "上当", "踩坑", "吃亏", "教训"],
    },
    {
        "key": "curiosity",
        "label": "好奇/反差震撼",
        "value": "「还有这种事？」——认知反差带来的情绪尖峰，驱动完播",
        "cues": ["竟然", "居然", "没想到", "万万没想到", "颠覆", "其实是", "背后", "隐藏", "秘密"],
    },
]

# 情绪峰值信号（标点/表达强度）
_EMOTION_INTENSITY_RE = re.compile(r"!!+|？？+|[!！？]{1}[!！]|[屎血泪汗]|绝了|疯了|爆炸|离谱|破防|上头|泪目|太真实了")
_COMFORT_CUES = ["没关系", "正常", "别急", "慢慢来", "你可以", "接纳", "允许", "放下", "不必"]


def _detect_emotion_values(report: dict) -> list[dict]:
    """从口播全文检测视频向观众提供的情绪价值（启发式）。"""
    full_text = report.get("script", {}).get("full_text", "")
    segments = report.get("script", {}).get("segments", [])
    if not full_text:
        return []

    total_len = max(len(_clean(full_text)), 1)
    hits: list[dict] = []
    for lex in _EMOTION_LEXICON:
        found = [c for c in lex["cues"] if c in full_text]
        if not found:
            continue
        # 出现位置越靠前，情绪价值兑现越早（对完播越有利）
        first_pos = min(full_text.find(c) for c in found)
        first_pct = round(first_pos / total_len * 100)
        intensity = sum(1 for s in segments if s.get("text") and _EMOTION_INTENSITY_RE.search(s["text"]))
        hits.append(
            {
                "key": lex["key"],
                "label": lex["label"],
                "value": lex["value"],
                "cue_words": _unique(found, 4),
                "first_pct": first_pct,
                "intensity_hits": intensity,
            }
        )

    # 按信号强度排序：命中词数 > 情绪强度标记 > 出现早晚
    hits.sort(key=lambda h: (-len(h["cue_words"]), -h["intensity_hits"], h["first_pct"]))
    return hits[:4]


def _emotion_value_summary(hits: list[dict]) -> str:
    if not hits:
        return "以信息价值为主，情绪价值偏弱——观众「有收获」但「没感觉」，转发/评论动力不足"
    top = hits[0]
    main = f"主打「{top['label']}」情绪（{top['value'].split('——')[0].strip('「」')}）"
    if len(hits) > 1:
        return main + f"；叠加 {'、'.join(h['label'] for h in hits[1:3])} 形成组合情绪"
    return main


def build_emotional_value(report: dict) -> dict:
    """情绪价值：这条视频让观众「得到什么感觉」，以及怎么抄。"""
    hits = _detect_emotion_values(report)
    full_text = report.get("script", {}).get("full_text", "")
    segments = report.get("script", {}).get("segments", [])

    comfort = [c for c in _COMFORT_CUES if c in full_text]
    intensity_count = sum(1 for s in segments if s.get("text") and _EMOTION_INTENSITY_RE.search(s["text"]))

    # 情绪价值兑现时机：首个主情绪出现在前 30% → 情绪钩子成立
    first = hits[0] if hits else None
    early = bool(first and first["first_pct"] <= 30)

    # 可抄建议
    how_to = []
    if hits:
        top = hits[0]
        how_to.append(
            f"主情绪「{top['label']}」靠词面信号 {'、'.join(top['cue_words'][:3])} 兑现——把它安排进你的开场 30 秒，情绪钩子在前 30% 出现最有效"
            if early
            else f"主情绪「{top['label']}」在片子的 {top['first_pct']}% 处才出现——前段情绪太空，容易先流失；把同款触发词提前到开场"
        )
    if comfort:
        how_to.append(f"安抚型表达（{'、'.join(comfort[:3])}）在敲击痛点后使用，一压一放，情绪曲线更完整")
    if hits and hits[0]["intensity_hits"] == 0:
        how_to.append("全程情绪强度平：可在观点句后加感叹/反问或口语化强调词，拉 1–2 个情绪尖峰")
    if len(hits) >= 2:
        how_to.append(f"组合拳：{hits[0]['label']}解决「爽」，{hits[1]['label']}解决「值」——爽感拉完播，获得感促收藏，别只押一个")

    if not hits:
        how_to.append("给视频加一个情绪锚点：先敲一个具体痛点（焦虑/损失），再给一个「照做就能」的解药，情绪价值立刻成立")

    # 曲线章（七、信息密度曲线）若存在，则关联一句：情绪高光落在哪个密度桶
    peak_note = ""
    curve = build_emotion_curve(report)
    if hits and curve.get("peak_bucket") is not None and curve.get("buckets"):
        peak_range = curve["buckets"][curve["peak_bucket"]].get("range", "")
        peak_note = f"信息密度峰值在 {peak_range}，主情绪「{hits[0]['label']}」宜在此段或更早兑现"

    return {
        "hits": hits,
        "summary": _emotion_value_summary(hits),
        "main_emotion": hits[0]["label"] if hits else "",
        "early_delivered": early,
        "comfort_cues": _unique(comfort, 3),
        "intensity_count": intensity_count,
        "how_to": how_to,
        "peak_note": peak_note,
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _unique(items: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
        if len(out) >= limit:
            break
    return out


# ---------- section builders ----------

def build_hook(report: dict) -> dict:
    """Opening hook analysis: first 1-3 segments + first chapter."""
    segments = report.get("script", {}).get("segments", [])
    hook_segs = [s for s in segments if s.get("role_guess") == "hook"] or segments[:3]
    hook_text = "".join(s.get("text", "") for s in hook_segs)[:120]

    cues = [c for c in _HOOK_CUES if c.lower() in hook_text.lower()]
    has_number = bool(_NUMBER_RE.search(hook_text))
    has_question = bool(_QUESTION_RE.search(hook_text))
    chapters = report.get("chapters") or report.get("aligned") or []
    first_ch = chapters[0] if chapters else {}

    techniques: list[str] = []
    if has_number:
        techniques.append("数字对比/数据开场")
    if has_question:
        techniques.append("提问互动")
    if any(c in hook_text for c in PAIN_TRIGGERS):
        techniques.append("痛点敲击")
    if cues:
        techniques.append("悬念/反转信号词")
    if not techniques:
        techniques.append("直给型开场")

    why = []
    if has_number:
        why.append("具体数字制造可量化预期，观众能立刻对号入座「我是不是那 80%」")
    if has_question:
        why.append("疑问句触发大脑自动作答，注意力被拉住")
    if any(c in hook_text for c in PAIN_TRIGGERS):
        why.append("开头即点痛处，唤起损失厌恶")
    if not why:
        why.append("开场直接抛出与目标人群相关的核心话题，压缩进入门槛")

    return {
        "hook_text": hook_text,
        "hook_seconds": round(sum(max(0, s.get("end", 0) - s.get("start", 0)) for s in hook_segs), 1) or None,
        "techniques": _unique(techniques),
        "why_it_works": "；".join(why) or "",
        "first_chapter_title": first_ch.get("title", ""),
    }


def build_audience(report: dict, meta: dict) -> dict:
    """Audience inference from hashtags, persona words, pain/desire words."""
    hashtags = report.get("hashtags") or []
    full_text = report.get("script", {}).get("full_text", "")
    persons = _PERSON_RE.findall(full_text)
    scenes = _SCENE_RE.findall(full_text)
    pains = [w for w in PAIN_TRIGGERS if w in full_text]
    desires = [w for w in DESIRE_TRIGGERS if w in full_text]

    person_counts = Counter(persons).most_common(5)
    scene_counts = Counter(scenes).most_common(5)

    identity = _unique([p for p, _ in person_counts], 5)
    if not identity and any(t in "".join(hashtags) for t in ("运营", "IP", "自媒体", "内容创作")):
        identity = ["自媒体从业者/想做 IP 的人"]

    trigger_scene = _unique([s for s, _ in scene_counts], 4)
    pain_points = _unique(pains, 5)
    desires_u = _unique(desires, 5)

    profile = "、".join(identity) if identity else "泛兴趣人群"
    audience_line = f"主要内容消费者：{profile}"
    if trigger_scene:
        audience_line += f"；典型观看场景/情绪触发词：{'、'.join(trigger_scene)}"

    return {
        "audience_line": audience_line,
        "identity_tags": identity,
        "scene_tags": trigger_scene,
        "pain_points": pain_points,
        "desires": desires_u,
        "hashtags": hashtags,
        "author": meta.get("author_nickname", ""),
    }


def build_golden_lines(report: dict) -> list[dict]:
    """Golden / quotable lines: segment-level scoring."""
    segments = report.get("script", {}).get("segments", [])
    scored: list[dict] = []
    for seg in segments:
        text = _clean(seg.get("text", ""))
        if not text or len(text) < 6:
            continue
        score = 0
        hits = [c for c in _GOLDEN_CUES if c in text]
        score += len(hits) * 2
        if _NUMBER_RE.search(text):
            score += 1
        if _QUESTION_RE.search(text):
            score += 1
        if any(c in text for c in _CTA_CUES):
            score -= 2
        role = seg.get("role_guess", "")
        if role in ("hook", "cta"):
            score += role == "hook" and 2 or 0
        if 10 <= len(text) <= 40:
            score += 1  # quotable length
        if score >= 3:
            scored.append(
                {
                    "time_range": seg.get("time_range", ""),
                    "text": text[:60],
                    "score": score,
                    "cue_words": _unique(hits, 3),
                }
            )
    scored.sort(key=lambda x: -x["score"])
    out: list[dict] = []
    seen_text: set[str] = set()
    for item in scored:
        key = item["text"][:20]
        if key in seen_text:
            continue
        seen_text.add(key)
        out.append(item)
        if len(out) >= 5:
            break
    return out


def build_why_attractive(report: dict) -> dict:
    """Narrative/psychological mechanics from structure + voice + pacing."""
    script = report.get("script", {})
    voice = report.get("voice", {})
    segments = script.get("segments", [])
    chapters = report.get("chapters") or report.get("aligned") or []

    cpm = voice.get("chars_per_minute", 0)
    seg_count = script.get("segment_count", 0)
    duration = report.get("duration_seconds", 0) or 1
    cuts_per_min = round(len(scenes_) / max(duration / 60, 0.1), 1) if (scenes_ := report.get("scenes")) else None

    points: list[str] = []

    if cpm:
        pace = "快节奏高密度" if cpm >= 380 else ("中等节奏" if cpm >= 280 else "慢节奏")
        points.append(
            f"语速 {cpm} 字/分钟，{pace}信息密度，{'适合等地铁/碎片时间快速吸收' if cpm >= 380 else '给观众留出理解缓冲'}"
        )

    if seg_count and duration:
        avg_seg = round(duration / seg_count, 1)
        if avg_seg <= 3:
            points.append(f"口播切分为 {seg_count} 个微段、平均 {avg_seg}s 一段，句句有新信息点，避免观众跳出")
        else:
            points.append(f"口播平均 {avg_seg}s 一段，段落间留有呼吸感")

    if cuts_per_min:
        if cuts_per_min >= 8:
            points.append(f"平均每分钟 {cuts_per_min} 次画面切换，视觉刺激密集，抑制划走冲动")
        elif cuts_per_min >= 3:
            points.append(f"画面切换约 {cuts_per_min} 次/分钟，节奏与口播基本同步")
        else:
            points.append("画面切换少，靠口播与字幕抓人（口播驱动型）")

    roles = [s.get("role_guess") for s in segments]
    if "pain_point" in roles:
        points.append("结构上先立痛点再给方案，符合「问题-解药」说服模型")
    if "demo" in roles:
        points.append("中途插入案例/演示段，用具体性给抽象观点「落地感」")
    if "tutorial" in roles:
        points.append("使用「第一/第二…」步骤化表达，观众预期清晰、易跟着走")
    if "cta" in roles:
        points.append("结尾有明确行动引导（关注/点赞），把认同转化为粉丝动作")

    if chapters and len(chapters) >= 3:
        points.append(f"全片切分为 {len(chapters)} 个章节（{'→'.join(c.get('title', '') for c in chapters[:4])}…），每个章节独立成立，中段流失被章节钩子接住")

    return {
        "points": points,
        "pace_label": ("快" if cpm >= 380 else ("中" if cpm >= 280 else "慢")) if cpm else "",
    }


def build_traits(report: dict) -> list[str]:
    """Content traits/positioning summary."""
    traits: list[str] = []
    voice = report.get("voice", {})
    scenes = report.get("scenes", [])
    hashtags = report.get("hashtags") or []
    script = report.get("script", {})

    tts = voice.get("likely_ai_tts")
    if tts:
        traits.append("配音疑似 AI 合成（可低成本批量产出，但有「机器感」风险）")
    elif voice.get("gender_guess") in ("female_or_high_voice", "male_or_low_voice"):
        traits.append("真人配音，音色有辨识度，利于人设沉淀")

    vt_counts = Counter(s.get("visual_type", "") for s in scenes if s.get("visual_type"))
    if vt_counts:
        top, n = vt_counts.most_common(1)[0]
        label = {
            "title_card": "大字标题卡",
            "screen_recording": "软件录屏",
            "mixed_ui": "图文/UI 讲解",
            "static_slide": "静态图文",
            "demo_playback": "成片演示",
        }.get(top, top)
        total = sum(vt_counts.values()) or 1
        traits.append(f"画面以「{label}」为主（{n}/{total} 帧），{'实操演示型内容，信任感来自看得见的过程' if '录屏' in label or '演示' in label else '重信息呈现，弱真人出镜'}")

    if script.get("total_chars", 0) > 800:
        traits.append(f"口播密度高（全文 {script['total_chars']} 字 / {report.get('duration_label', '')}），信息量向「干货收藏型」倾斜")

    if any(t in "".join(hashtags) for t in ("个人IP", "IP", "自媒体", "运营", "内容创作")):
        traits.append("定位自媒体/运营赛道，目标观众同时是潜在同行——天然带「教-学」关系")

    return traits or ["信息型口播视频，靠内容密度而非制作精度取胜"]


def build_insights(report: dict, meta: dict | None = None) -> dict:
    """Assemble all insight sections for the report."""
    meta = meta or {}
    hook = build_hook(report)
    audience = build_audience(report, meta)
    golden = build_golden_lines(report)
    why = build_why_attractive(report)
    traits = build_traits(report)
    return {
        "hook": hook,
        "audience": audience,
        "golden_lines": golden,
        "why_attractive": why,
        "traits": traits,
        "pacing": build_pacing(report),
        "visual_language": build_visual_language(report),
        "structure": build_structure_template(report),
        "emotion": build_emotion_curve(report),
        "emotional_value": build_emotional_value(report),
        "data_notes": build_data_notes(report),
        "takeaways": build_takeaways(report),
    }


# ---------- extra dimensions (v2) ----------

def build_pacing(report: dict) -> dict:
    """节奏剖面：语速/密度/切镜频率 → 三段式标注 + 可复用参数。"""
    voice = report.get("voice", {})
    script = report.get("script", {})
    scenes = report.get("scenes", [])
    duration = report.get("duration_seconds", 0) or 1

    cpm = voice.get("chars_per_minute", 0)
    seg_count = script.get("segment_count", 0)
    cuts = len(scenes)
    cuts_per_min = round(cuts / max(duration / 60, 0.1), 1)

    if cpm >= 380:
        pace, pace_note = "极快", "观众几乎无思考间隙，靠信息流推着走"
    elif cpm >= 300:
        pace, pace_note = "快", "紧凑但能跟上，适合干货讲解"
    elif cpm >= 220:
        pace, pace_note = "中", "有呼吸感，观点型内容常用"
    else:
        pace, pace_note = "慢", "留足理解时间，适合深度/情感内容"

    if cuts_per_min >= 8:
        cut_note = "高频切镜，视觉刺激强，抑制划走"
    elif cuts_per_min >= 3:
        cut_note = "切镜与口播同步，一镜一观点"
    else:
        cut_note = "低切镜，靠口播与字幕抓人（口播驱动型）"

    return {
        "chars_per_minute": cpm,
        "pace_label": pace,
        "pace_note": pace_note,
        "segment_count": seg_count,
        "avg_segment_seconds": round(duration / seg_count, 1) if seg_count else None,
        "cuts": cuts,
        "cuts_per_minute": cuts_per_min,
        "cut_note": cut_note,
        "reusable_params": {
            "口播语速目标": f"≈{cpm} 字/分钟" if cpm else "—",
            "口播段落粒度": f"平均 {round(duration / seg_count, 1) if seg_count else '—'}s/段",
            "画面切换节奏": f"≈{cuts_per_min} 次/分钟" if cuts_per_min else "—",
        },
    }


def build_visual_language(report: dict) -> dict:
    """视觉语言：画面构成、字幕/标注习惯（启发式 + Phase3 数据当有）。"""
    scenes = report.get("scenes", [])
    if not scenes:
        return {"summary": "（无关键帧数据）", "types": {}, "vision_merged": False}

    type_labels = {
        "title_card": ("大字标题卡", "暗底高对比大字，常用于 Hook 与转场强调"),
        "screen_recording": ("软件录屏", "真实操作画面，信任感来源"),
        "mixed_ui": ("图文/UI 讲解", "界面+解说，信息型内容主力"),
        "static_slide": ("静态图文/单图", "成本最低，靠口播驱动"),
        "demo_playback": ("成片/演示播放", "展示效果或素材"),
        "talking_head": ("真人出镜", "人设沉淀利器"),
    }
    counts = Counter(s.get("visual_type", "") for s in scenes)
    total = sum(counts.values()) or 1
    types = []
    for vt, n in counts.most_common():
        label, note = type_labels.get(vt, (vt or "未知", ""))
        types.append({"type": vt, "label": label, "count": n, "pct": round(n / total * 100), "note": note})

    vision_merged = any(s.get("vision") for s in scenes)
    tools = sorted({t for s in scenes for t in (s.get("vision") or {}).get("tools_visible") or []})
    elements = Counter(
        e for s in scenes for e in (s.get("vision") or {}).get("elements") or []
    ).most_common(6)

    dominant = types[0]["label"] if types else "—"
    summary = f"主画面形态：{dominant}（{types[0]['pct']}%）" if types else "—"
    if vision_merged:
        summary += "；已融合 Phase 3 视觉描述"
    return {
        "summary": summary,
        "types": types,
        "tools_visible": tools,
        "elements": [{"name": e, "count": n} for e, n in elements],
        "vision_merged": vision_merged,
    }


def build_structure_template(report: dict) -> dict:
    """结构模板：把章节序列抽象成可套用的公式。"""
    chapters = report.get("chapters") or report.get("aligned") or []
    if not chapters:
        return {"formula": None, "beats": []}

    beats = []
    for ch in chapters:
        role = ch.get("role", "")
        beats.append(
            {
                "time_range": ch.get("time_range", ""),
                "title": ch.get("title", ""),
                "role": role,
                "seconds": ch.get("duration_seconds", 0),
                "chars": ch.get("chars", 0),
                "summary": ch.get("summary", ""),
            }
        )

    role_seq = [b["role"] for b in beats]
    if role_seq[:1] == ["hook"] and role_seq[-1:] == ["cta"] and "pain_point" in role_seq:
        formula = "Hook（钩子开场）→ 痛点共鸣 → 干货/论证 → CTA 收尾"
    elif role_seq[:1] == ["hook"] and role_seq[-1:] == ["cta"]:
        formula = "Hook → 主体讲解 → CTA 收尾"
    elif "tutorial" in role_seq:
        formula = "场景导入 → 分步教程 → 总结"
    else:
        formula = "线性叙事（无明确结构标签）"

    total_s = sum(b["seconds"] for b in beats) or 1
    for b in beats:
        b["pct"] = round(b["seconds"] / total_s * 100)

    return {"formula": formula, "beats": beats}


def build_emotion_curve(report: dict) -> dict:
    """情绪/张力曲线：按 10% 时长分桶统计密度与角色分布。"""
    script = report.get("script", {})
    segments = script.get("segments", [])
    duration = report.get("duration_seconds", 0) or 1
    if not segments:
        return {"buckets": [], "shape": "—"}

    n = 10
    buckets = []
    for i in range(n):
        lo, hi = duration * i / n, duration * (i + 1) / n
        inb = [s for s in segments if s["end"] > lo and s["start"] < hi]
        chars = sum(s["chars"] for s in inb)
        span = max(0.1, hi - lo)
        roles = {s.get("role_guess", "") for s in inb}
        buckets.append(
            {
                "range": f"{int(lo // 60)}:{int(lo % 60):02d}-{int(hi // 60)}:{int(hi % 60):02d}",
                "chars_per_min": round(chars / (span / 60)),
                "roles": sorted(r for r in roles if r),
            }
        )

    vals = [b["chars_per_min"] for b in buckets]
    peak = vals.index(max(vals))
    shape = "前高后稳（开场最密，符合完播逻辑）" if peak == 0 and vals[-1] < vals[0] * 0.9 else (
        "中段高潮（论证/案例段最密）" if 0 < peak < n - 1 else "后段冲刺（结尾信息量最大）"
    )
    return {"buckets": buckets, "shape": shape, "peak_bucket": peak}


def build_data_notes(report: dict) -> list[dict]:
    """可对标的硬指标：口播字数/时长比、语速、切镜、段粒度 —— 供自查。"""
    voice = report.get("voice", {})
    script = report.get("script", {})
    scenes = report.get("scenes", [])
    duration = report.get("duration_seconds", 0) or 1

    total_chars = script.get("total_chars", 0)
    notes = []

    def judge(ok: bool, good: str, bad: str) -> str:
        return good if ok else bad

    chars_per_sec = round(total_chars / duration, 2) if duration else 0
    notes.append(
        {
            "metric": "口播总字数 / 时长",
            "value": f"{total_chars} 字 / {report.get('duration_label', '')}（{chars_per_sec} 字/秒）",
            "benchmark": "60s 视频常见 260–380 字；口播信息型可到 450+",
            "note": judge(5.0 <= chars_per_sec <= 7.5, "密度合格，观众跟得上", "偏离常见区间，注意是否过密或注水"),
        }
    )
    cpm = voice.get("chars_per_minute", 0)
    notes.append(
        {
            "metric": "语速",
            "value": f"{cpm} 字/分钟",
            "benchmark": "中文口播 240–420 字/分钟；干货类普遍 340+",
            "note": judge(240 <= cpm <= 430, "在自然语速区间", "过快难消化或过慢易流失"),
        }
    )
    cuts_per_min = round(len(scenes) / max(duration / 60, 0.1), 1)
    notes.append(
        {
            "metric": "画面切换频率",
            "value": f"{len(scenes)} 帧 ≈ {cuts_per_min} 次/分钟",
            "benchmark": "口播一句一帧类 8–30 次/分钟；固定机位口播可 <3",
            "note": judge(3 <= cuts_per_min <= 35, "节奏正常", "视觉节奏异常，易单调或眼花"),
        }
    )
    seg = script.get("segment_count", 0)
    notes.append(
        {
            "metric": "口播粒度",
            "value": f"{seg} 段，平均 {round(duration / seg, 1) if seg else 0}s/段",
            "benchmark": "3s 以内 = 快节奏碎句；5s+ = 完整长句",
            "note": judge(seg > 0, "粒度已量化，可直接模仿", "无口播段数据"),
        }
    )
    return notes


def build_takeaways(report: dict) -> dict:
    """可参考学习的点：直接可抄的结构、话术、节奏、选题公式 + 避坑。"""
    hook = build_hook(report)
    pacing = build_pacing(report)
    structure = build_structure_template(report)
    golden = build_golden_lines(report)
    audience = build_audience(report, {})
    eval = build_emotional_value(report)
    voice = report.get("voice", {})
    hashtags = report.get("hashtags") or []
    script = report.get("script", {})

    # 1. 结构可抄
    structure_point = None
    if structure.get("formula"):
        beats_pct = " → ".join(f"{b['title']}({b['pct']}%)" for b in structure["beats"][:5])
        structure_point = {
            "what": f"整体结构：{structure['formula']}",
            "how": f"时长配比 {beats_pct}。做同题材时先按此配比搭骨架，再填肉。",
        }

    # 2. 钩子可抄
    hook_point = {
        "what": f"开场钩子：{'、'.join(hook['techniques'])}",
        "how": f"「{hook['hook_text'][:40]}…」的写法是 {hook['why_it_works']}。可用同款句式换成你自己的题材。",
    }

    # 3. 话术可抄
    golden_point = None
    if golden:
        top = golden[0]
        golden_point = {
            "what": f"高亮话术：{top['text'][:30]}",
            "how": f"亮点词「{'、'.join(top.get('cue_words') or ['—'])}」触发注意；套用「{top.get('cue_words')[0] if top.get('cue_words') else '本质'}+断言」句式做你的核心句。",
        }

    # 4. 节奏可抄
    pacing_point = {
        "what": f"节奏参数：{pacing['pace_label']}节奏 {pacing['chars_per_minute']} 字/分钟，{pacing['cuts_per_minute']} 次切镜/分钟",
        "how": f"{pacing['pace_note']}；{pacing['cut_note']}。模仿时直接对齐这三组数字。",
    }

    # 5. 情绪价值可抄
    emotion_point = None
    if eval.get("main_emotion"):
        first_h = (eval.get("hits") or [{}])[0]
        pos_note = f"前 {first_h.get('first_pct', '—')}% 即兑现" if eval.get("early_delivered") else "出现偏晚，开场情绪偏空"
        emotion_point = {
            "what": f"情绪价值：主打「{eval['main_emotion']}」" + (f"，叠加 {'、'.join(h['label'] for h in eval['hits'][1:2])}" if len(eval.get("hits") or []) > 1 else ""),
            "how": f"触发词 {'、'.join(first_h.get('cue_words', [])[:3]) or '—'} 是情绪开关，{pos_note}。做同款先想清楚观众看完要「得到什么感觉」，再反推开头怎么点。",
        }

    # 6. 选题/定位可抄
    topic_formula = "、".join(hashtags[:3]) if hashtags else ""
    topic_point = {
        "what": f"选题公式：{' + '.join(audience['identity_tags'][:2]) or '目标人群'} × {topic_formula or '热门话题'} × 干货",
        "how": "把这条视频的「人群 + 话题 + 价值承诺」三要素拆开，各替换成你自己的素材，就是一条新选题。",
    }

    avoid: list[str] = []
    if voice.get("likely_ai_tts"):
        avoid.append("配音疑似 AI：注意平台对低质 AI 音频的限流风险，或混入真人实录音轨")
    if script.get("segment_count", 0) > 300:
        avoid.append("口播碎句过多（>300 段）：转写噪音可能被当节奏，模仿时以句子而非碎片为单位")
    if pacing["chars_per_minute"] and pacing["chars_per_minute"] > 430:
        avoid.append("语速超 430 字/分钟：观众理解成本高，慎用")
    if not golden:
        avoid.append("未检出金句：说明表达平实，模仿时需自备 1–2 个记忆点")
    if not eval.get("hits"):
        avoid.append("情绪价值弱：只有信息没有情绪，观众「学到了但没感觉」，难转发；补一个情绪锚点")
    elif not eval.get("early_delivered"):
        avoid.append(f"主情绪「{eval['main_emotion']}」出现偏晚（{eval['hits'][0].get('first_pct', '—')}% 处）：前段流失风险，把情绪触发提前到开场")

    return {
        "copy": [p for p in [structure_point, hook_point, golden_point, pacing_point, emotion_point, topic_point] if p],
        "avoid": avoid,
        "checklist": [
            "拆出目标人群，核对与你账号粉丝画像的重合度",
            "照结构配比重排你自己的口播稿",
            "把黄金句句式替换成你领域的关键词",
            "录制后回看：语速/切镜频率是否对齐本片参数",
            "发布前自查：钩子前 3 秒是否出现数字/提问/痛点任一要素",
        ],
    }
