#!/usr/bin/env python3
"""AIGC video prompt reverse-engineering (heuristic, no LLM).

Builds a fact table from keyframes + transcript, then assembles reusable
T2V / I2V prompts. Does NOT claim to recover the original generation prompt.
"""

from __future__ import annotations

import re
from typing import Any

# Seedance / 即梦 / 可灵等常见单次生成上限（秒）
MAX_CLIP_SECONDS = 15

_VISUAL_PROMPT = {
    "title_card": "暗底大字标题画面，中心高对比文字，电影感开场卡",
    "screen_recording": "软件界面录屏，清晰 UI，光标操作演示，产品功能特写",
    "mixed_ui": "图文混排讲解画面，偏亮，信息密度高",
    "static_slide": "静态幻灯/单图展示，构图简洁，低动态",
    "demo_playback": "成片级演示画面，主体清晰，电影感光影",
}

_VISUAL_CAMERA = {
    "title_card": "固定机位，正面平视，浅景深",
    "screen_recording": "固定俯拍/屏幕直录，无运镜",
    "mixed_ui": "缓慢推近，强调信息区域",
    "static_slide": "固定机位",
    "demo_playback": "缓慢推拉或跟拍，电影感构图",
}


def recommend_frame_count(duration: float) -> int:
    """Suggested keyframe count by duration (for custom mode)."""
    if duration <= 10:
        return 10
    if duration <= 20:
        return 14
    if duration <= 30:
        return 18
    return min(30, max(20, int(duration / 2)))


def recommend_keyframe_mode(analysis_mode: str, current: str | None = None) -> str:
    """Default keyframe: interval(~3.5s) for prompt_reverse, transcript for content.

    Respects an explicit non-empty current mode from UI/CLI.
    """
    if current in {"scene", "custom", "transcript", "interval"}:
        return current
    return "interval" if analysis_mode == "prompt_reverse" else "transcript"


def _clock(seconds: float) -> str:
    s = max(0, int(round(seconds)))
    return f"{s // 60:02d}:{s % 60:02d}"


def _clean_speech(text: str, limit: int = 80) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    if len(t) > limit:
        return t[:limit] + "…"
    return t


def _shot_from_scene(sc: dict, idx: int) -> dict:
    vtype = sc.get("visual_type") or "demo_playback"
    speech = sc.get("speech_text") or sc.get("text") or ""
    start = float(sc.get("start") or 0)
    end = float(sc.get("end") or start)
    dur = round(end - start, 2)
    vision = sc.get("vision") or {}
    return {
        "index": idx,
        "start": round(start, 2),
        "end": round(end, 2),
        "time_range": sc.get("time_range") or f"{_clock(start)}-{_clock(end)}",
        "duration_seconds": dur if dur > 0 else round(float(sc.get("duration_seconds") or 0), 2),
        "visual_type": vtype,
        "visual_hint": sc.get("visual_hint") or _VISUAL_PROMPT.get(vtype, ""),
        "camera_guess": _VISUAL_CAMERA.get(vtype, "固定机位"),
        "speech": _clean_speech(speech, 120),
        "frame_path": sc.get("frame_path") or "",
        "on_screen_text": vision.get("on_screen_text") or "",
        "layout": vision.get("layout") or "",
        "how_made": vision.get("how_made") or "",
    }


def _shots_from_report(report: dict) -> list[dict]:
    scenes = report.get("scenes") or []
    if scenes:
        return [_shot_from_scene(sc, i) for i, sc in enumerate(scenes, start=1)]

    chapters = report.get("aligned") or report.get("chapters") or []
    shots = []
    for i, ch in enumerate(chapters, start=1):
        shots.append(
            {
                "index": i,
                "start": float(ch.get("start") or 0),
                "end": float(ch.get("end") or 0),
                "time_range": ch.get("time_range") or "",
                "duration_seconds": float(ch.get("duration_seconds") or 0),
                "visual_type": (ch.get("visual_types") or ["demo_playback"])[0],
                "visual_hint": ch.get("visual_summary") or ch.get("title") or "",
                "camera_guess": "按章节推断，建议结合关键帧确认",
                "speech": _clean_speech(ch.get("summary") or ch.get("text") or "", 120),
                "frame_path": (ch.get("keyframes") or [""])[0],
                "on_screen_text": "",
                "layout": "",
                "how_made": "",
            }
        )
    return shots


def _merge_into_beats(shots: list[dict], max_beats: int = 6) -> list[dict]:
    """Merge many short shots into 3–6 narrative beats for T2V."""
    if not shots:
        return []
    if len(shots) <= max_beats:
        return [
            {
                "index": s["index"],
                "start": s["start"],
                "end": s["end"],
                "time_range": s["time_range"],
                "duration_seconds": s["duration_seconds"],
                "shots": [s],
                "speech": s["speech"],
                "visual_summary": s["visual_hint"],
                "camera": s["camera_guess"],
            }
            for s in shots
        ]

    # Bucket by equal count
    n = len(shots)
    size = max(1, (n + max_beats - 1) // max_beats)
    beats = []
    for i in range(0, n, size):
        group = shots[i : i + size]
        start = group[0]["start"]
        end = group[-1]["end"]
        speeches = [g["speech"] for g in group if g["speech"]]
        visuals = list(dict.fromkeys(g["visual_hint"] for g in group if g["visual_hint"]))
        cameras = list(dict.fromkeys(g["camera_guess"] for g in group if g["camera_guess"]))
        beats.append(
            {
                "index": len(beats) + 1,
                "start": start,
                "end": end,
                "time_range": f"{_clock(start)}-{_clock(end)}",
                "duration_seconds": round(end - start, 2),
                "shots": group,
                "speech": "；".join(speeches)[:160],
                "visual_summary": " / ".join(visuals)[:160],
                "camera": "；".join(cameras)[:80] or "固定机位",
            }
        )
    return beats


def _split_for_model(duration: float) -> list[tuple[float, float]]:
    """Split full video into ≤MAX_CLIP_SECONDS windows for generation."""
    if duration <= MAX_CLIP_SECONDS:
        return [(0.0, round(duration, 2))]
    windows = []
    t = 0.0
    while t < duration - 0.05:
        end = min(duration, t + MAX_CLIP_SECONDS)
        windows.append((round(t, 2), round(end, 2)))
        t = end
    return windows


def _style_guess(report: dict, shots: list[dict]) -> dict:
    types = [s["visual_type"] for s in shots]
    counter: dict[str, int] = {}
    for t in types:
        counter[t] = counter.get(t, 0) + 1
    dominant = max(counter, key=counter.get) if counter else "demo_playback"
    voice = report.get("voice") or {}
    likely_ai = bool(voice.get("likely_ai_tts"))
    tags = report.get("hashtags") or []
    return {
        "dominant_visual": dominant,
        "dominant_label": _VISUAL_PROMPT.get(dominant, dominant),
        "likely_ai_voice": likely_ai,
        "pace_cpm": voice.get("chars_per_minute"),
        "hashtags": tags[:12],
        "look": (
            "偏 AIGC/动画成片质感"
            if dominant in {"demo_playback", "title_card"} and likely_ai
            else "偏实拍/录屏讲解"
            if dominant in {"screen_recording", "mixed_ui"}
            else "混合风格，需结合关键帧确认"
        ),
    }


def _t2v_line(beat: dict, *, english: bool = False) -> str:
    """One beat → prompt fragment using 文生视频公式."""
    cam = beat.get("camera") or "固定机位"
    visual = beat.get("visual_summary") or "主体清晰的画面"
    speech = beat.get("speech") or ""
    tr = beat.get("time_range") or ""
    if english:
        dlg = f' Dialogue: "{speech}".' if speech else ""
        return (
            f"{tr}: {cam}, cinematic lighting, {visual}, "
            f"smooth continuous motion, coherent subject identity.{dlg}"
        ).strip()
    dlg = f' 对白/旁白：「{speech}」' if speech else ""
    return (
        f"{tr}：{cam}，电影感光影，{visual}，主体运动连贯，人物/产品外观前后一致。"
        f"{dlg}"
    ).strip()


def _assemble_t2v(beats: list[dict], style: dict, duration: float) -> dict:
    header_zh = (
        f"镜头语言与光影：电影感，主体突出；风格：{style.get('look', '写实或成片质感')}。"
        f"全片约 {duration:.1f} 秒，按时间轴生成，禁止无故跳切人物身份。"
    )
    header_en = (
        f"Cinematic lighting, subject-focused framing, style: {style.get('look', 'polished')}. "
        f"About {duration:.1f}s. Keep identity consistent across time."
    )
    body_zh = "\n".join(_t2v_line(b, english=False) for b in beats)
    body_en = "\n".join(_t2v_line(b, english=True) for b in beats)
    return {
        "prompt_zh": f"{header_zh}\n{body_zh}".strip(),
        "prompt_en": f"{header_en}\n{body_en}".strip(),
        "formula": "镜头语言+光影 + 主体 + 主体运动 + 场景 + 氛围+风格（时间轴分拍）",
    }


def _i2v_for_shot(shot: dict) -> dict:
    speech = shot.get("speech") or ""
    motion_zh = (
        f"{shot.get('camera_guess', '固定机位')}；"
        f"画面：{shot.get('visual_hint') or '主体清晰'}；"
        f"动作连贯，保持开场构图与主体外观。"
    )
    if speech:
        motion_zh += f" 同步旁白节奏：「{_clean_speech(speech, 60)}」。"
    first_zh = (
        f"{shot.get('visual_hint') or '清晰主体'}，"
        f"{shot.get('camera_guess', '平视构图')}，"
        f"高质量关键帧，适合作为图生视频首帧。"
    )
    if shot.get("on_screen_text"):
        first_zh += f" 画面文字：{shot['on_screen_text']}。"
    return {
        "index": shot["index"],
        "time_range": shot["time_range"],
        "duration_seconds": shot["duration_seconds"],
        "first_frame_path": shot.get("frame_path") or "",
        "first_frame_prompt_zh": first_zh,
        "motion_prompt_zh": motion_zh,
        "motion_prompt_en": (
            f"{shot.get('camera_guess', 'static camera')}; "
            f"{shot.get('visual_hint') or 'clear subject'}; "
            f"smooth motion, preserve identity from first frame."
        ),
    }


def _segment_prompts(shots: list[dict], style: dict, windows: list[tuple[float, float]]) -> list[dict]:
    segs = []
    for i, (start, end) in enumerate(windows, start=1):
        in_win = [s for s in shots if s["end"] > start and s["start"] < end]
        if not in_win:
            continue
        beats = _merge_into_beats(in_win, max_beats=5)
        t2v = _assemble_t2v(beats, style, end - start)
        segs.append(
            {
                "index": i,
                "start": start,
                "end": end,
                "time_range": f"{_clock(start)}-{_clock(end)}",
                "duration_seconds": round(end - start, 2),
                "prompt_zh": t2v["prompt_zh"],
                "prompt_en": t2v["prompt_en"],
                "shot_count": len(in_win),
            }
        )
    return segs


def _media_from_report(report: dict) -> dict:
    media = dict(report.get("media") or {})
    duration = float(report.get("duration_seconds") or media.get("duration_seconds") or 0)
    media.setdefault("duration_seconds", round(duration, 2))
    media.setdefault("duration_label", report.get("duration_label") or _clock(duration))
    return media


def _build_replicate_guide(
    *,
    media: dict,
    style: dict,
    shots: list[dict],
    i2v: list[dict],
    segments: list[dict],
    t2v_full: dict | None,
    need_split: bool,
) -> dict:
    """Human/AI playbook: copy-pasteable steps to recreate the clip."""
    orient = media.get("orientation") or ""
    aspect = media.get("aspect_ratio") or "按原片"
    res = media.get("resolution") or "尽量高清"
    dur = media.get("duration_seconds") or 0
    fps = media.get("fps")
    specs_line = " · ".join(
        x
        for x in [
            f"{orient} {aspect}".strip() if orient or aspect else "",
            res,
            f"{dur}s" if dur else "",
            f"{fps} fps" if fps else "",
        ]
        if x
    )

    prefer_i2v = len(shots) >= 2 or need_split
    route = "图生视频（I2V · 逐镜，更稳）" if prefer_i2v else "文生视频（T2V · 一段）"
    route_why = (
        "多镜头/超 15s，逐镜锁外观再拼接，比一段文生更像原片"
        if prefer_i2v
        else "镜头少且短，可直接一段文生"
    )

    steps: list[dict] = [
        {
            "n": 1,
            "title": "打开生成工具",
            "how": "打开即梦 / Seedance / 可灵 / Runway 等，新建「图生视频」或「文生视频」任务。",
        },
        {
            "n": 2,
            "title": "先对齐成片规格（别漏）",
            "how": (
                f"输出设为：**{specs_line or '与原片一致'}**。"
                f"单次生成时长 ≤{MAX_CLIP_SECONDS}s；"
                f"比例优先选 **{aspect}**（{orient or '按原片'}）。"
            ),
        },
        {
            "n": 3,
            "title": f"选路线：{route}",
            "how": route_why + "。下面步骤默认按推荐路线；另一条路线见报告后半 Prompt 区。",
        },
    ]

    if prefer_i2v and i2v:
        for shot in i2v:
            frame = shot.get("first_frame_path") or "（本镜关键帧）"
            motion = shot.get("motion_prompt_zh") or ""
            first = shot.get("first_frame_prompt_zh") or ""
            sub = ""
            # recover subtitle hint from matching shot facts if present in first prompt
            steps.append(
                {
                    "n": len(steps) + 1,
                    "title": (
                        f"生成镜 {shot.get('index')} · `{shot.get('time_range')}`"
                        f"（约 {shot.get('duration_seconds')}s）"
                    ),
                    "how": (
                        f"① 上传首帧：`{frame}`（没有文件就用「首帧描述」文生一张参考图）。\n"
                        f"② 首帧描述（可选）：{first}\n"
                        f"③ 动作 Prompt（复制）：{motion}\n"
                        f"④ 时长约 {shot.get('duration_seconds')}s，比例 {aspect}。"
                    ),
                    "copy_prompt": motion,
                    "first_frame": frame,
                }
            )
        steps.append(
            {
                "n": len(steps) + 1,
                "title": "拼接成片",
                "how": (
                    "按镜号顺序导入剪映/CapCut：硬切或短叠化；"
                    "核对字幕/旁白是否要对齐原片节奏；导出时保持同一比例与分辨率。"
                ),
            }
        )
    else:
        body = (t2v_full or {}).get("prompt_zh") if t2v_full else ""
        if need_split and segments:
            for seg in segments:
                steps.append(
                    {
                        "n": len(steps) + 1,
                        "title": (
                            f"文生段 {seg.get('index')} · `{seg.get('time_range')}`"
                            f"（{seg.get('duration_seconds')}s）"
                        ),
                        "how": f"复制下方 Prompt 粘贴到文生视频，时长 {seg.get('duration_seconds')}s，比例 {aspect}。",
                        "copy_prompt": seg.get("prompt_zh") or "",
                    }
                )
            steps.append(
                {
                    "n": len(steps) + 1,
                    "title": "拼接各段",
                    "how": "按时间顺序拼接，统一调色/字幕后导出。",
                }
            )
        elif body:
            steps.append(
                {
                    "n": len(steps) + 1,
                    "title": "粘贴整段文生 Prompt",
                    "how": f"一次生成约 {dur}s（若平台上限更短则自动切段）。比例 {aspect}。",
                    "copy_prompt": body,
                }
            )

    steps.append(
        {
            "n": len(steps) + 1,
            "title": "自检",
            "how": (
                "对照原片看：比例是否一致、人物外观是否跳变、运镜/场景顺序是否对、"
                "字幕文案是否齐。差得远就回到对应镜改 Prompt，不要整段重写。"
            ),
        }
    )

    checklist = [
        f"成片规格已对齐：{specs_line or '比例/分辨率/时长'}",
        f"生成路线已选：{route}",
        "各镜/各段 Prompt 已复制粘贴并导出",
        "已按顺序拼接并检查身份一致性",
    ]

    return {
        "headline": "按下列步骤操作即可复刻（人可照做，AI 可当作业清单）",
        "specs_line": specs_line,
        "recommended_route": route,
        "route_why": route_why,
        "platform_hint": "即梦 / Seedance / 可灵 / Runway（字段名略有差异，复制中文 Prompt 即可）",
        "steps": steps,
        "checklist": checklist,
        "style_one_liner": style.get("look") or style.get("dominant_label") or "",
    }


def build_prompt_reverse(report: dict, meta: dict | None = None) -> dict[str, Any]:
    """Derive reverse-prompt package from an analysis report dict."""
    duration = float(report.get("duration_seconds") or 0)
    media = _media_from_report(report)
    shots = _shots_from_report(report)
    style = _style_guess(report, shots)
    beats = _merge_into_beats(shots, max_beats=6)
    windows = _split_for_model(duration)
    t2v = _assemble_t2v(beats, style, duration)
    i2v = [_i2v_for_shot(s) for s in shots]
    segments = _segment_prompts(shots, style, windows)

    need_split = duration > MAX_CLIP_SECONDS
    notes = [
        "本结果是「可复现观感的生成指令」，不是原片隐藏 Prompt 的精确还原。",
        "无多模态看图时，画面细节来自关键帧启发式分类 + 口播对齐；建议 Agent 再读关键帧精修。",
    ]
    if need_split:
        notes.append(
            f"片长 {duration:.1f}s 超过常见单次上限 {MAX_CLIP_SECONDS}s，"
            f"已切成 {len(segments)} 段文生视频 Prompt；长片优先用 I2V 逐镜。"
        )
    if not shots:
        notes.append("未找到关键帧/章节，Prompt 质量会明显下降，请先 --full 拆解。")

    replicate = _build_replicate_guide(
        media=media,
        style=style,
        shots=shots,
        i2v=i2v,
        segments=segments,
        t2v_full=t2v if not need_split else None,
        need_split=need_split,
    )

    return {
        "mode": "prompt_reverse",
        "generated_for_title": report.get("title") or (meta or {}).get("title") or "",
        "duration_seconds": round(duration, 2),
        "media": media,
        "max_clip_seconds": MAX_CLIP_SECONDS,
        "recommended_frame_count": recommend_frame_count(duration),
        "recommended_keyframe_mode": "scene",
        "strategy": {
            "prefer_keyframe": "scene（切镜检测）；快切片可改 custom + recommended_frame_count",
            "t2v_when": f"整片 ≤{MAX_CLIP_SECONDS}s 或接受分段生成时",
            "i2v_when": "多硬切、要锁主体外观、或需要逐镜控制时",
            "need_split": need_split,
            "segment_count": len(segments),
        },
        "style": style,
        "replicate": replicate,
        "facts": {
            "shot_count": len(shots),
            "beat_count": len(beats),
            "shots": shots,
            "beats": [
                {
                    "index": b["index"],
                    "time_range": b["time_range"],
                    "duration_seconds": b["duration_seconds"],
                    "visual_summary": b["visual_summary"],
                    "camera": b["camera"],
                    "speech": b["speech"],
                }
                for b in beats
            ],
            "audio": {
                "chars_per_minute": (report.get("voice") or {}).get("chars_per_minute"),
                "likely_ai_tts": (report.get("voice") or {}).get("likely_ai_tts"),
                "gender_guess": (report.get("voice") or {}).get("gender_guess"),
            },
        },
        "prompts": {
            "t2v_full": t2v if not need_split else None,
            "t2v_segments": segments,
            "i2v_shots": i2v,
        },
        "agent_checklist": [
            "逐张阅读 analysis/scenes 关键帧，纠正 visual_hint / 运镜 / 主体外观",
            "核对每镜首态→末态：道具是否还在、动作是否完成、是否误判切镜",
            "按目标模型改写：Seedance/即梦偏中文时间轴；可灵/Runway 可保留英文",
            "超过 15s：用 t2v_segments 或 i2v_shots，不要硬塞超长一段",
            "需要角色一致性时：导出首帧做人设参考图，再跑 I2V",
        ],
        "confidence_notes": notes,
    }
