#!/usr/bin/env python3
"""Phase 3: prepare vision tasks and merge agent vision descriptions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import analysis_dir, load_meta, resolve_project, save_meta, vision_dir

VISION_PROMPT = """\
请分析这张抖音视频关键帧，结合同期口播上下文，用 JSON 回答（不要 markdown 代码块）：

{
  "layout": "画面布局一句话",
  "visual_type": "title_card|screen_recording|demo_playback|talking_head|mixed_ui|other",
  "tools_visible": ["看到的软件/网站/工具名，没有则空数组"],
  "elements": ["字幕", "箭头标注", "录屏", "动画", "..."],
  "text_on_screen": "画面上可见的关键文字，没有则空字符串",
  "how_made": "推测这个画面是怎么做的（1-2句）",
  "relation_to_voice": "画面与口播的关系（1句）"
}
"""

INSTRUCTIONS_MD = """# Phase 3 · 视觉模型解析说明

## 目标

为每个镜头关键帧生成**可读的画面描述**，补全「这个画面是怎么做的」。

## 前置条件

已运行：

```powershell
python scripts/analyze_douyin.py last --full --vision-prep
```

## Agent 操作步骤

### 1. 读取任务清单

打开 `{project}/analysis/vision/manifest.json`，里面有每个镜头的：
- `scene_index` / `time_range`
- `image` — 关键帧绝对路径（用 Read 工具看图）
- `voice_context` — 该时段口播摘要
- `heuristic_type` — Phase 2 启发式分类（仅供参考）

### 2. 逐镜头或按章节批量看图

**推荐策略（省 token）：**
- 每个**章节**只看 1–3 张代表帧（manifest 里 `representative: true`）
- 教程录屏类视频：重点看章节切换处的帧
- 若用户要求完整拆解：看全部 `tasks`

对每张图：
1. 用 **Read** 工具读取 `image` 路径
2. 把 `VISION_PROMPT` + `voice_context` 发给视觉模型
3. 解析返回的 JSON

### 3. 写入描述文件

将所有结果写入 `{project}/analysis/vision/descriptions.json`：

```json
{{
  "generated_at": "2026-...",
  "model": "你使用的视觉模型名",
  "scenes": [
    {{
      "scene_index": 1,
      "time_range": "0:00-0:22",
      "image": "analysis/scenes/scene_001_....jpg",
      "vision": {{
        "layout": "...",
        "visual_type": "screen_recording",
        "tools_visible": ["豆包", "ComfyUI"],
        "elements": ["录屏", "字幕"],
        "text_on_screen": "...",
        "how_made": "...",
        "relation_to_voice": "..."
      }}
    }}
  ]
}}
```

### 4. 合并进报告

```powershell
python scripts/vision_describe.py merge last
```

会更新 `analysis/report.json` 和 `analysis/report.md`，追加「视觉拆解」章节。

## 注意事项

- 口播稿来自 Whisper，专有名词可能有误（豆包/ComfyUI/Vidu），视觉识别结果优先
- 同一章节内连续录屏帧可只描述一次，其余写「同上一镜，继续演示 XXX」
- 不要编造看不清的内容；不确定就写「无法识别」
"""


def format_clock(seconds: float) -> str:
    total = int(round(seconds))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def load_report(project: Path) -> dict:
    report_path = analysis_dir(project) / "report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Missing report.json — run analyze --full first: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def voice_context_for_scene(report: dict, start: float, end: float) -> str:
    segments = report.get("script", {}).get("segments", [])
    texts = [s["text"] for s in segments if s["end"] > start and s["start"] < end]
    merged = "".join(texts)
    return merged[:200] + ("…" if len(merged) > 200 else "")


def pick_representative_scenes(scenes: list[dict], aligned: list[dict]) -> set[int]:
    """One representative frame per chapter (first scene in chapter)."""
    reps: set[int] = set()
    for ch in aligned:
        for sc in scenes:
            if sc["index"] not in reps and sc["end"] > ch["start"] and sc["start"] < ch["end"]:
                reps.add(sc["index"])
                break
    return reps


def prepare_vision_manifest(project: Path) -> Path:
    report = load_report(project)
    scenes = report.get("scenes", [])
    if not scenes:
        raise RuntimeError("No scenes in report — run analyze with --full first")

    aligned = report.get("aligned", [])
    representatives = pick_representative_scenes(scenes, aligned) if aligned else {s["index"] for s in scenes[:9]}

    out_dir = vision_dir(project)
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for sc in scenes:
        img_rel = sc["frame_path"].replace("\\", "/")
        img_abs = (analysis_dir(project) / img_rel).resolve()
        tasks.append(
            {
                "scene_index": sc["index"],
                "time_range": sc.get("time_range", f"{format_clock(sc['start'])}-{format_clock(sc['end'])}"),
                "image": str(img_abs),
                "image_relative": img_rel,
                "voice_context": voice_context_for_scene(report, sc["start"], sc["end"]),
                "heuristic_type": sc.get("visual_type", ""),
                "heuristic_hint": sc.get("visual_hint", ""),
                "representative": sc["index"] in representatives,
                "prompt": VISION_PROMPT,
            }
        )

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project.resolve()),
        "title": report.get("title", ""),
        "total_scenes": len(tasks),
        "representative_scenes": sorted(representatives),
        "prompt_template": VISION_PROMPT,
        "output_file": str((out_dir / "descriptions.json").resolve()),
        "tasks": tasks,
    }

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    instructions = out_dir / "INSTRUCTIONS.md"
    instructions.write_text(
        INSTRUCTIONS_MD.format(project=str(project.resolve())),
        encoding="utf-8",
    )
    return out_dir / "manifest.json"


def render_vision_section(report: dict) -> list[str]:
    lines = [
        "",
        "## 视觉拆解（Phase 3）",
        "",
        "| 时间 | 类型 | 工具/元素 | 怎么做的 |",
        "|------|------|-----------|----------|",
    ]
    for sc in report.get("scenes", []):
        v = sc.get("vision") or {}
        if not v:
            continue
        tools = ", ".join(v.get("tools_visible") or []) or "-"
        elements = ", ".join(v.get("elements") or [])[:40] or "-"
        how = (v.get("how_made") or "-").replace("|", "\\|")[:60]
        lines.append(
            f"| {sc.get('time_range', '')} | {v.get('visual_type', '-')} | {tools}/{elements} | {how} |"
        )
    if len(lines) <= 5:
        lines.append("| （待完成） | 运行 vision_describe.py prepare + Agent 看图 | | |")
    return lines


def merge_descriptions(project: Path) -> Path:
    report = load_report(project)
    desc_path = vision_dir(project) / "descriptions.json"
    if not desc_path.exists():
        raise FileNotFoundError(f"Missing descriptions.json — complete Phase 3 vision step first: {desc_path}")

    desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
    by_index = {item["scene_index"]: item.get("vision", {}) for item in desc_data.get("scenes", [])}

    for sc in report.get("scenes", []):
        vision = by_index.get(sc["index"])
        if vision:
            sc["vision"] = vision

    # Enrich aligned chapters with vision summaries.
    for ch in report.get("aligned", []):
        matched = [
            sc.get("vision", {})
            for sc in report.get("scenes", [])
            if sc["end"] > ch["start"] and sc["start"] < ch["end"] and sc.get("vision")
        ]
        if matched:
            tools = list(dict.fromkeys(t for v in matched for t in v.get("tools_visible", [])))
            ch["vision_tools"] = tools
            ch["vision_summary"] = matched[0].get("how_made", "")

    report["vision_meta"] = {
        "merged_at": datetime.now().isoformat(timespec="seconds"),
        "model": desc_data.get("model", "unknown"),
        "scene_count": len(by_index),
    }

    analysis = analysis_dir(project)
    (analysis / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Re-render markdown（内容洞察）并同步知识库副本
    analysis = analysis_dir(project)
    meta = load_meta(project)

    try:
        from analyze_douyin import render_markdown
        from insights import build_insights

        insights = build_insights(report, meta)
        md_body = render_markdown(report, insights)

        vision_lines = render_vision_section(report)
        md_full = md_body.rstrip() + "\n" + "\n".join(vision_lines) + "\n"
        (analysis / "report.md").write_text(md_full, encoding="utf-8")
    except Exception as exc:
        print(f"WARN: report re-render failed: {exc}", file=sys.stderr)
        md_path = analysis / "report.md"
        if md_path.exists():
            md = md_path.read_text(encoding="utf-8")
            if "## 视觉拆解（Phase 3）" in md:
                md = md.split("## 视觉拆解（Phase 3）")[0].rstrip()
            vision_lines = render_vision_section(report)
            md_path.write_text(md + "\n".join(vision_lines) + "\n", encoding="utf-8")
        md_full = None

    # 同步知识库副本（存在才更新；没有则补建）
    try:
        from paths import report_kb_path

        kb_path = Path(meta.get("report_kb_path") or "") if meta.get("report_kb_path") else report_kb_path(
            project.name, report.get("title", ""), meta.get("last_analysis_at", "")
        )
        if md_full is None:
            md_path = analysis / "report.md"
            md_full = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        kb_path.write_text(md_full, encoding="utf-8")
        meta["report_kb_path"] = str(kb_path)
        save_meta(project, meta)
    except Exception as exc:
        print(f"WARN: knowledge-base report sync failed: {exc}", file=sys.stderr)

    return analysis / "report.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 vision describe prep/merge")
    parser.add_argument("command", choices=["prepare", "merge"], help="prepare manifest or merge descriptions")
    parser.add_argument(
        "target",
        nargs="?",
        default="last",
        help="Project dir, aweme id, or 'last' (default)",
    )
    args = parser.parse_args()

    try:
        project = resolve_project(args.target)
        if args.command == "prepare":
            path = prepare_vision_manifest(project)
            print(f"Manifest: {path}")
            print(f"Instructions: {path.parent / 'INSTRUCTIONS.md'}")
            print("Next: Agent reads images from manifest and writes descriptions.json")
        else:
            path = merge_descriptions(project)
            print(f"Merged report: {path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
