"""Render AIGC prompt-reverse sections as markdown lines for report.md."""
from __future__ import annotations


def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def render_prompt_reverse_markdown(pr: dict) -> list[str]:
    lines: list[str] = []
    style = pr.get("style") or {}
    strategy = pr.get("strategy") or {}
    facts = pr.get("facts") or {}
    prompts = pr.get("prompts") or {}
    notes = pr.get("confidence_notes") or []
    checklist = pr.get("agent_checklist") or []
    media = pr.get("media") or {}
    replicate = pr.get("replicate") or {}

    media_line = replicate.get("specs_line") or " · ".join(
        x
        for x in [
            f"{media.get('orientation', '')} {media.get('aspect_ratio', '')}".strip(),
            media.get("resolution") or "",
            f"{pr.get('duration_seconds', '—')}s",
            f"{media.get('fps')} fps" if media.get("fps") else "",
        ]
        if x
    )

    lines.extend(
        [
            "",
            "## 📋 系统提示词（权威）",
            "",
            "> 精修遵循 `prompts/reverse-system.md`："
            "关键帧图（约 20 秒 5～6 张）+ 音频 → 模型理解 → 反推视频生成提示词；"
            "少而准，不写成影评。",
            "",
            "## ⚡ 反推速览",
            "",
            f"> **成片规格**：{media_line}",
            "",
            f"> 镜头 **{facts.get('shot_count', 0)}** ｜ "
            f"节拍 **{facts.get('beat_count', 0)}** ｜ "
            f"风格：**{style.get('look', '—')}** ｜ "
            f"单次上限 **{pr.get('max_clip_seconds', 15)}s**",
            "",
            "> 说明：下列内容用于**复刻观感**（人可照做 / AI 可当作业清单），"
            "不是原片隐藏 Prompt 的精确还原。",
            "",
        ]
    )

    # ── 复刻操作步骤（最靠前，可直接照做）──
    if replicate:
        lines.extend(
            [
                "## 零、按这个步骤复刻（复制粘贴 / 照做即可）",
                "",
                f"**{replicate.get('headline', '按下列步骤复刻')}**",
                "",
                f"- **成片规格**：{replicate.get('specs_line') or media_line}",
                f"- **推荐路线**：{replicate.get('recommended_route', '—')}"
                f"（{replicate.get('route_why', '')}）",
                f"- **可用平台**：{replicate.get('platform_hint', '即梦 / Seedance / 可灵等')}",
                "",
            ]
        )
        if replicate.get("style_one_liner"):
            lines.append(f"- **风格一句话**：{replicate['style_one_liner']}")
            lines.append("")

        for step in replicate.get("steps") or []:
            lines.append(f"### 步骤 {step.get('n')} · {step.get('title', '')}")
            lines.append("")
            how = (step.get("how") or "").strip()
            for para in how.split("\n"):
                if para.strip():
                    lines.append(para.strip())
            lines.append("")
            if step.get("copy_prompt"):
                lines.extend(
                    [
                        "**可直接复制的 Prompt：**",
                        "",
                        "```",
                        step["copy_prompt"],
                        "```",
                        "",
                    ]
                )

        if replicate.get("checklist"):
            lines.extend(["**完成勾选**", ""])
            for c in replicate["checklist"]:
                lines.append(f"- [ ] {c}")
            lines.append("")

    if notes:
        lines.extend(["### 使用注意", ""])
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    lines.extend(
        [
            "## 一、成片规格 & 生成策略",
            "",
            f"- **时长**：{pr.get('duration_seconds', '—')}s"
            f"（{media.get('duration_label') or '—'}）",
            f"- **比例**：{media.get('orientation') or ''} {media.get('aspect_ratio') or '—'}",
            f"- **分辨率**：{media.get('resolution') or '—'}",
            f"- **帧率**：{media.get('fps') or '—'} fps",
            f"- **推荐关键帧**：{strategy.get('prefer_keyframe', 'scene')}",
            f"- **建议帧数（custom）**：{pr.get('recommended_frame_count', '—')}",
            f"- **文生视频（T2V）**：{strategy.get('t2v_when', '')}",
            f"- **图生视频（I2V）**：{strategy.get('i2v_when', '')}",
            f"- **是否分段**：{'是，' + str(strategy.get('segment_count', 0)) + ' 段' if strategy.get('need_split') else '否，可一段生成'}",
            f"- **画面主型**：{style.get('dominant_label', '—')}",
            "",
        ]
    )

    beats = facts.get("beats") or []
    if beats:
        lines.extend(
            [
                "## 二、事实表（节拍）",
                "",
                "| 时间 | 运镜推断 | 画面 | 旁白/对白 |",
                "|------|----------|------|-----------|",
            ]
        )
        for b in beats:
            lines.append(
                f"| {_esc(b.get('time_range', ''))} | {_esc(b.get('camera', ''))} | "
                f"{_esc(b.get('visual_summary', ''))} | {_esc(b.get('speech', ''))} |"
            )
        lines.append("")

    # T2V
    lines.extend(["## 三、文生视频 Prompt（T2V · 备用整段复制）", ""])
    t2v_full = prompts.get("t2v_full")
    segments = prompts.get("t2v_segments") or []

    if t2v_full:
        lines.extend(
            [
                "### 整段（中文，可直接粘贴）",
                "",
                "```",
                t2v_full.get("prompt_zh") or "",
                "```",
                "",
                "### Full English",
                "",
                "```",
                t2v_full.get("prompt_en") or "",
                "```",
                "",
                f"*公式：{t2v_full.get('formula', '')}*",
                "",
            ]
        )
    elif segments:
        lines.append(
            f"片长超限，已拆成 **{len(segments)}** 段（每段 ≤{pr.get('max_clip_seconds', 15)}s）："
        )
        lines.append("")
        for seg in segments:
            lines.extend(
                [
                    f"### 段 {seg.get('index')} · `{seg.get('time_range')}`"
                    f"（{seg.get('duration_seconds')}s）",
                    "",
                    "```",
                    seg.get("prompt_zh") or "",
                    "```",
                    "",
                ]
            )
    else:
        lines.extend(["（暂无 T2V 产出）", ""])

    # I2V
    i2v = prompts.get("i2v_shots") or []
    lines.extend(["## 四、图生视频 Prompt（I2V · 逐镜明细）", ""])
    if i2v:
        lines.append("每镜：用关键帧作首帧参考 + Motion Prompt。硬切保留为独立生成任务。")
        lines.append("")
        for shot in i2v[:40]:
            lines.extend(
                [
                    f"### 镜 {shot.get('index')} · `{shot.get('time_range')}`"
                    f"（{shot.get('duration_seconds')}s）",
                    "",
                    f"- **首帧文件**：`{shot.get('first_frame_path') or '（无）'}`",
                    f"- **首帧描述**：{shot.get('first_frame_prompt_zh') or ''}",
                    f"- **动作 Prompt**：{shot.get('motion_prompt_zh') or ''}",
                    "",
                ]
            )
        if len(i2v) > 40:
            lines.append(f"- … 共 {len(i2v)} 镜，详见 `prompt_reverse.json`")
            lines.append("")
    else:
        lines.extend(["（暂无 I2V 产出）", ""])

    if checklist:
        lines.extend(["## 五、Agent 精修清单", ""])
        for c in checklist:
            # already may contain [x]/ keep as list item
            if c.strip().startswith("[x]") or c.strip().startswith("[ ]"):
                lines.append(f"- {c}")
            else:
                lines.append(f"- [ ] {c}")
        lines.append("")

    audio = facts.get("audio") or {}
    lines.extend(
        [
            "## 六、声音线索",
            "",
            f"- 语速：{audio.get('chars_per_minute', '—')} 字/分",
            f"- 音色推测：{audio.get('gender_guess', '—')}",
            f"- 疑似 AI 配音：{'是' if audio.get('likely_ai_tts') else '不确定/偏真人'}",
            "",
        ]
    )

    return lines
