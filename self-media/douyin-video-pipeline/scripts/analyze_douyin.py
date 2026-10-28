#!/usr/bin/env python3
"""Analyze Douyin/local video: Phase 1 transcript + Phase 2 scene/chapter breakdown."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import (
    analysis_dir,
    create_or_update_meta,
    load_meta,
    report_kb_path,
    resolve_project,
    save_meta,
    video_file,
    vision_dir,
    write_last_project,
)
from insights import build_insights
from render_insights_md import render_insights_markdown

ROOT = Path(__file__).resolve().parent.parent


def recommend_keyframe_mode(_analysis_mode: str, current: str | None = None) -> str:
    """1004 仅内容拆解：默认 transcript；尊重 UI/CLI 显式关键帧模式。"""
    if current in {"scene", "custom", "transcript", "interval"}:
        return current
    return "transcript"

_download_mod = None
_download_spec = importlib.util.spec_from_file_location(
    "download_douyin",
    Path(__file__).with_name("download-douyin.py"),
)
if _download_spec and _download_spec.loader:
    _download_mod = importlib.util.module_from_spec(_download_spec)
    _download_spec.loader.exec_module(_download_mod)

download_video = getattr(_download_mod, "download", None) if _download_mod else None
extract_url = getattr(_download_mod, "extract_url", None) if _download_mod else None

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

PIP_MIRROR = [
    "-i",
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "--trusted-host",
    "pypi.tuna.tsinghua.edu.cn",
]

CHAPTER_SPLIT_RE = re.compile(
    r"接下来|下一个环节|第一个环节|最后一|直接开始|好了[，,]?|下面我们就|"
    r"第一步|第二步|第三步|那么接下来|本期视频|以上就是"
)
_SENTENCE_BREAK_RE = re.compile(r"[。！？；!?…\n]")
SENTENCE_END_RE = re.compile(r"[。！？；!?…]$")
KEYFRAME_MODES = {"transcript", "custom", "scene", "interval"}
ANALYSIS_MODES = {"content"}  # 反推已拆至 feishu_downloads/ai-showcase/aigc/aigc-prompt-reverse


@dataclass
class Segment:
    index: int
    start: float
    end: float
    text: str
    chars: int


@dataclass
class Scene:
    index: int
    start: float
    end: float
    frame_path: str
    visual_type: str
    visual_hint: str
    text: str = ""
    speech_index: int = 0


def ensure_packages(*names: str) -> None:
    import importlib.util

    missing = [n for n in names if importlib.util.find_spec(n) is None]
    if not missing:
        return
    pkg_map = {
        "scenedetect": "scenedetect[opencv]",
        "PIL": "pillow",
        "cv2": "opencv-python-headless",
        "numpy": "numpy",
    }
    to_install = [pkg_map.get(m.split(".")[0], m) for m in missing]
    subprocess.check_call([sys.executable, "-m", "pip", "install", *to_install, *PIP_MIRROR])


def run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffmpeg failed")


def probe_duration(video: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(proc.stdout.strip())


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return max(a, 1)


def aspect_ratio_label(width: int, height: int) -> str:
    """Human label like 9:16 / 16:9; falls back to reduced fraction."""
    if width <= 0 or height <= 0:
        return "未知"
    # Common social ratios first
    ratio = width / height
    known = [
        (9 / 16, "9:16"),
        (16 / 9, "16:9"),
        (1.0, "1:1"),
        (3 / 4, "3:4"),
        (4 / 3, "4:3"),
        (2 / 3, "2:3"),
        (3 / 2, "3:2"),
    ]
    for target, label in known:
        if abs(ratio - target) < 0.03:
            return label
    g = _gcd(width, height)
    return f"{width // g}:{height // g}"


def probe_video_media(video: Path) -> dict:
    """Return duration + resolution + fps + aspect for reports."""
    duration = probe_duration(video)
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate",
            "-of",
            "json",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams") or [{}]
    st = streams[0] if streams else {}
    width = int(st.get("width") or 0)
    height = int(st.get("height") or 0)

    def _fps(raw: str) -> float | None:
        if not raw or raw == "0/0":
            return None
        if "/" in raw:
            a, b = raw.split("/", 1)
            try:
                return round(float(a) / float(b), 3) if float(b) else None
            except ValueError:
                return None
        try:
            return round(float(raw), 3)
        except ValueError:
            return None

    fps = _fps(st.get("avg_frame_rate") or "") or _fps(st.get("r_frame_rate") or "")
    orientation = (
        "竖屏" if height > width else "横屏" if width > height else "方形"
    )
    return {
        "duration_seconds": round(duration, 2),
        "width": width,
        "height": height,
        "resolution": f"{width}×{height}" if width and height else "",
        "aspect_ratio": aspect_ratio_label(width, height),
        "orientation": orientation,
        "fps": fps,
    }


def extract_audio(video: Path, wav: Path) -> None:
    wav.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(video),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav),
        ]
    )


def transcribe(wav: Path, model_size: str) -> tuple[list[Segment], str, str]:
    ensure_packages("faster_whisper")
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, _info = model.transcribe(
        str(wav),
        language="zh",
        vad_filter=True,
        beam_size=5,
    )

    segments: list[Segment] = []
    lines: list[str] = []
    srt_lines: list[str] = []

    for idx, seg in enumerate(segments_iter, start=1):
        text = seg.text.strip()
        if not text:
            continue
        item = Segment(
            index=idx,
            start=round(seg.start, 2),
            end=round(seg.end, 2),
            text=text,
            chars=len(re.sub(r"\s+", "", text)),
        )
        segments.append(item)
        lines.append(text)
        srt_lines.extend(
            [
                str(idx),
                f"{format_ts(seg.start)} --> {format_ts(seg.end)}",
                text,
                "",
            ]
        )

    return segments, "\n".join(lines), "\n".join(srt_lines)


def format_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_clock(seconds: float) -> str:
    total = int(round(seconds))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def extract_hashtags(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"#[\w\u4e00-\u9fff]+", text)))


def guess_segment_role(text: str, index: int, total: int) -> str:
    if index == 1:
        return "hook"
    if index == total:
        return "cta"
    if re.search(r"第一|步骤|首先|接下来|然后|第二|第三", text):
        return "tutorial"
    if re.search(r"关注|点赞|收藏|评论|私信", text):
        return "cta"
    if re.search(r"问题|痛点|困扰|为什么|是不是", text):
        return "pain_point"
    if re.search(r"比如|案例|效果|结果|演示|看一下", text):
        return "demo"
    return "body"


def analyze_voice(wav: Path, segments: list[Segment], duration: float) -> dict:
    ensure_packages("librosa", "numpy")
    import librosa
    import numpy as np

    y, sr = librosa.load(str(wav), sr=16000, mono=True)
    speech_chars = sum(s.chars for s in segments)
    speech_seconds = sum(max(0.0, s.end - s.start) for s in segments)
    total_seconds = max(duration, speech_seconds, 1.0)

    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
    )
    voiced = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    pitch_hz = round(float(np.median(voiced)), 1) if voiced.size else None

    rms = librosa.feature.rms(y=y)[0]
    energy = round(float(np.mean(rms)), 4)

    if pitch_hz is None:
        gender_guess = "unknown"
    elif pitch_hz >= 190:
        gender_guess = "female_or_high_voice"
    elif pitch_hz <= 140:
        gender_guess = "male_or_low_voice"
    else:
        gender_guess = "neutral_or_mixed"

    chars_per_min = round(speech_chars / (speech_seconds / 60), 1) if speech_seconds else 0.0
    speech_ratio = round(speech_seconds / total_seconds, 3)

    likely_ai = (
        speech_ratio > 0.75
        and 180 <= (chars_per_min or 0) <= 340
        and energy < 0.08
    )

    return {
        "pitch_hz_median": pitch_hz,
        "gender_guess": gender_guess,
        "energy_mean": energy,
        "speech_seconds": round(speech_seconds, 2),
        "speech_ratio": speech_ratio,
        "chars_per_minute": chars_per_min,
        "likely_ai_tts": likely_ai,
        "note": (
            "Heuristic only. 'likely_ai_tts' means pacing/energy resembles TTS, "
            "not an exact voice ID."
        ),
    }


def detect_scenes(video: Path, duration: float, threshold: float) -> list[tuple[float, float]]:
    ensure_packages("scenedetect")
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    video_stream = open_video(str(video))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video_stream)
    scene_list = manager.get_scene_list()

    raw: list[tuple[float, float]] = []
    for start, end in scene_list:
        s = start.seconds if hasattr(start, "seconds") else start.get_seconds()
        e = end.seconds if hasattr(end, "seconds") else end.get_seconds()
        if e - s >= 0.3:
            raw.append((round(s, 2), round(e, 2)))

    if not raw:
        return [(0.0, round(duration, 2))]

    return merge_short_scenes(raw, min_duration=4.0, max_scenes=60)


def merge_short_scenes(
    scenes: list[tuple[float, float]],
    *,
    min_duration: float,
    max_scenes: int,
) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in scenes:
        if merged and (end - start) < min_duration:
            prev_s, prev_e = merged[-1]
            merged[-1] = (prev_s, end)
        else:
            merged.append((start, end))

    while len(merged) > max_scenes and min_duration < 20:
        min_duration += 2.0
        merged = []
        for start, end in scenes:
            if merged and (end - start) < min_duration:
                prev_s, prev_e = merged[-1]
                merged[-1] = (prev_s, end)
            else:
                merged.append((start, end))

    return merged


def extract_frame(video: Path, timestamp: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
    )


def classify_frame(image_path: Path) -> tuple[str, str]:
    ensure_packages("PIL", "numpy")
    import numpy as np
    from PIL import Image, ImageFilter

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    arr = np.asarray(img, dtype=np.float32) / 255.0
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    edges = np.asarray(img.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0
    edge_density = float(np.mean(edges > 0.25))

    # Center region often holds titles or UI focus.
    cy0, cy1 = int(h * 0.2), int(h * 0.8)
    cx0, cx1 = int(w * 0.1), int(w * 0.9)
    center_edges = float(np.mean(edges[cy0:cy1, cx0:cx1] > 0.25))

    color_std = float(np.std(arr.reshape(-1, 3), axis=0).mean())

    if brightness < 0.22 and center_edges > 0.08:
        return "title_card", "暗底+中心高对比，疑似大字标题/Hook 画面"
    if edge_density > 0.12 and color_std > 0.12:
        return "screen_recording", "高边缘密度+多色彩，疑似软件录屏/实操演示"
    if edge_density > 0.08 and brightness > 0.45:
        return "mixed_ui", "中等边缘+偏亮，疑似 UI 讲解或图文混排"
    if color_std < 0.08 and contrast < 0.12:
        return "static_slide", "低色彩变化，疑似静态幻灯/单图"
    return "demo_playback", "常规演示画面（动画/成片/素材播放）"


def analyze_scenes(
    video: Path,
    duration: float,
    scenes_dir: Path,
    *,
    threshold: float,
) -> list[Scene]:
    ranges = detect_scenes(video, duration, threshold)
    scenes: list[Scene] = []

    for idx, (start, end) in enumerate(ranges, start=1):
        mid = start + (end - start) / 2
        frame = scenes_dir / f"scene_{idx:03d}_{format_clock(mid).replace(':', '-')}.jpg"
        extract_frame(video, mid, frame)
        visual_type, visual_hint = classify_frame(frame)
        scenes.append(
            Scene(
                index=idx,
                start=start,
                end=end,
                frame_path=str(frame.relative_to(scenes_dir.parent)),
                visual_type=visual_type,
                visual_hint=visual_hint,
            )
        )

    return scenes


def merge_segments_into_sentences(segments: list[Segment]) -> list[Segment]:
    """Merge Whisper micro-segments into spoken sentences (一句一帧)."""
    if not segments:
        return []

    sentences: list[Segment] = []
    bucket: list[Segment] = []

    def flush() -> None:
        if not bucket:
            return
        text = text_of(bucket)
        if not text.strip():
            bucket.clear()
            return
        sentences.append(
            Segment(
                index=len(sentences) + 1,
                start=bucket[0].start,
                end=bucket[-1].end,
                text=text,
                chars=len(re.sub(r"\s+", "", text)),
            )
        )
        bucket.clear()

    for seg in segments:
        if bucket:
            gap = seg.start - bucket[-1].end
            if gap > 2.5:
                flush()
        bucket.append(seg)
        merged = text_of(bucket)
        if SENTENCE_END_RE.search(seg.text.strip()) or len(re.sub(r"\s+", "", merged)) >= 48:
            flush()
    flush()
    return sentences


def analyze_frames_from_units(
    video: Path,
    units: list[Segment],
    scenes_dir: Path,
    *,
    prefix: str = "sent",
) -> list[Scene]:
    scenes: list[Scene] = []
    for idx, unit in enumerate(units, start=1):
        start, end = unit.start, unit.end
        mid = start + max((end - start) / 2, 0.05)
        frame = scenes_dir / f"{prefix}_{idx:04d}_{format_clock(mid).replace(':', '-')}.jpg"
        extract_frame(video, mid, frame)
        visual_type, visual_hint = classify_frame(frame)
        scenes.append(
            Scene(
                index=idx,
                start=round(start, 2),
                end=round(end, 2),
                frame_path=str(frame.relative_to(scenes_dir.parent)),
                visual_type=visual_type,
                visual_hint=visual_hint,
                text=unit.text,
                speech_index=unit.index,
            )
        )
    return scenes


def analyze_frames_custom(
    video: Path,
    duration: float,
    frame_count: int,
    scenes_dir: Path,
) -> list[Scene]:
    count = max(5, min(int(frame_count), 300))
    step = duration / count
    units: list[Segment] = []
    for i in range(count):
        start = round(i * step, 2)
        end = round(duration, 2) if i == count - 1 else round((i + 1) * step, 2)
        units.append(
            Segment(
                index=i + 1,
                start=start,
                end=end,
                text="",
                chars=0,
            )
        )
    return analyze_frames_from_units(video, units, scenes_dir, prefix="frame")


def extract_keyframes(
    video: Path,
    duration: float,
    scenes_dir: Path,
    *,
    mode: str,
    segments: list[Segment],
    frame_count: int = 30,
    scene_threshold: float = 27.0,
    interval_seconds: float = 2.0,
) -> list[Scene]:
    scenes_dir.mkdir(parents=True, exist_ok=True)
    if mode == "transcript":
        sentences = merge_segments_into_sentences(segments)
        print(f"Transcript keyframes: {len(sentences)} sentences", file=sys.stderr)
        return analyze_frames_from_units(video, sentences, scenes_dir, prefix="sent")
    if mode == "custom":
        print(f"Custom keyframes: {frame_count} frames", file=sys.stderr)
        return analyze_frames_custom(video, duration, frame_count, scenes_dir)
    if mode == "interval":
        # AIGC reverse default: ~1 frame every N seconds (better storyboard coverage)
        step = max(0.5, float(interval_seconds or 2.0))
        count = max(5, min(300, int((duration / step) + 0.999) or 5))
        print(
            f"Interval keyframes: every {step:.1f}s → {count} frames (duration={duration:.1f}s)",
            file=sys.stderr,
        )
        return analyze_frames_custom(video, duration, count, scenes_dir)
    return analyze_scenes(video, duration, scenes_dir, threshold=scene_threshold)


def segments_in_range(segments: list[Segment], start: float, end: float) -> list[Segment]:
    return [s for s in segments if s.end > start and s.start < end]


def text_of(segs: list[Segment]) -> str:
    return "".join(s.text for s in segs)


def summarize_text(text: str, limit: int = 80) -> str:
    cleaned = re.sub(r"\s+", "", text)
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


def guess_chapter_title(text: str, role: str) -> str:
    if role == "hook":
        return "开场 Hook"
    if role == "pain_point":
        return "痛点/问题"
    if role == "tutorial":
        m = re.search(r"(第一|第二|第三|下一个|最后).{0,8}", text)
        if m:
            return f"教程 · {m.group(0)}"
        return "教程步骤"
    if role == "demo":
        return "案例演示"
    if role == "cta":
        return "收尾/引导"
    if "赚钱" in text or "变现" in text:
        return "变现逻辑"
    if "剪辑" in text:
        return "剪辑思维"
    if "剧本" in text or "分镜" in text:
        return "剧本/分镜"
    if "人物" in text or "角色" in text:
        return "人物设定"
    if "场景" in text:
        return "场景设定"
    if "视频" in text and "制作" in text:
        return "视频生成"
    return "正文讲解"


def build_chapters(segments: list[Segment], duration: float) -> list[dict]:
    if not segments:
        return []

    chapters: list[dict] = []
    bucket: list[Segment] = [segments[0]]

    def flush() -> None:
        if not bucket:
            return
        start = bucket[0].start
        end = bucket[-1].end
        text = text_of(bucket)
        role = guess_segment_role(bucket[0].text, bucket[0].index, len(segments))
        chapters.append(
            {
                "index": len(chapters) + 1,
                "start": round(start, 2),
                "end": round(end, 2),
                "time_range": f"{format_clock(start)}-{format_clock(end)}",
                "duration_seconds": round(end - start, 2),
                "chars": len(re.sub(r"\s+", "", text)),
                "role": role,
                "title": guess_chapter_title(text, role),
                "summary": summarize_text(text, 120),
                "text": text,
            }
        )

    for seg in segments[1:]:
        prev = bucket[-1]
        gap = seg.start - prev.end
        bucket_chars = len(re.sub(r"\s+", "", text_of(bucket)))
        # 硬上限切分：单章超 45s 或 260 字即切（Whisper 微段多无标点，不依赖句读）
        over_limit = bucket_chars >= 260 or (bucket and seg.start - bucket[0].start >= 45)
        should_split = (
            gap > 25
            or (gap > 8 and CHAPTER_SPLIT_RE.search(seg.text))
            or (bucket_chars > 500 and CHAPTER_SPLIT_RE.search(seg.text))
            or over_limit
        )
        if should_split:
            flush()
            bucket = [seg]
        else:
            bucket.append(seg)

    flush()

    # Merge tiny chapters (<8s) into previous.
    merged: list[dict] = []
    for ch in chapters:
        if merged and ch["duration_seconds"] < 8:
            prev = merged[-1]
            prev["end"] = ch["end"]
            prev["time_range"] = f"{format_clock(prev['start'])}-{format_clock(prev['end'])}"
            prev["duration_seconds"] = round(prev["end"] - prev["start"], 2)
            prev["text"] += ch["text"]
            prev["chars"] = len(re.sub(r"\s+", "", prev["text"]))
            prev["summary"] = summarize_text(prev["text"], 120)
        else:
            ch["index"] = len(merged) + 1
            merged.append(ch)

    return merged


def align_chapters_scenes(chapters: list[dict], scenes: list[Scene]) -> list[dict]:
    aligned: list[dict] = []
    for ch in chapters:
        matched = [s for s in scenes if s.end > ch["start"] and s.start < ch["end"]]
        visual_types = list(dict.fromkeys(s.visual_type for s in matched))
        aligned.append(
            {
                **ch,
                "scene_count": len(matched),
                "visual_types": visual_types,
                "visual_summary": " / ".join(
                    dict.fromkeys(s.visual_hint for s in matched)
                )[:160],
                "keyframes": [s.frame_path for s in matched[:6]],
            }
        )
    return aligned


def build_report(
    *,
    video: Path,
    title: str,
    duration: float,
    segments: list[Segment],
    transcript: str,
    hashtags: list[str],
    voice: dict,
    chapters: list[dict] | None = None,
    scenes: list[Scene] | None = None,
    aligned: list[dict] | None = None,
    keyframe_mode: str | None = None,
    frame_count: int | None = None,
    media: dict | None = None,
) -> dict:
    total_chars = sum(s.chars for s in segments)
    enriched = []
    for seg in segments:
        enriched.append(
            {
                **asdict(seg),
                "time_range": f"{format_clock(seg.start)}-{format_clock(seg.end)}",
                "role_guess": guess_segment_role(seg.text, seg.index, len(segments)),
            }
        )

    media_info = media or {}
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_video": str(video),
        "title": title,
        "duration_seconds": round(duration, 2),
        "duration_label": format_clock(duration),
        "hashtags": hashtags,
        "media": {
            "width": media_info.get("width") or 0,
            "height": media_info.get("height") or 0,
            "resolution": media_info.get("resolution") or "",
            "aspect_ratio": media_info.get("aspect_ratio") or "",
            "orientation": media_info.get("orientation") or "",
            "fps": media_info.get("fps"),
        },
        "script": {
            "total_chars": total_chars,
            "segment_count": len(segments),
            "avg_chars_per_segment": round(total_chars / len(segments), 1) if segments else 0,
            "full_text": transcript,
            "segments": enriched,
        },
        "voice": voice,
    }

    if chapters is not None:
        report["chapters"] = chapters
    if scenes is not None:
        report["scenes"] = [asdict(s) for s in scenes]
    if aligned is not None:
        report["aligned"] = aligned
    if keyframe_mode:
        report["keyframe_mode"] = keyframe_mode
    if frame_count is not None:
        report["frame_count"] = frame_count

    return report


def render_markdown(
    report: dict,
    insights: dict | None = None,
) -> str:
    title = "视频拆解报告"
    media = report.get("media") or {}
    media_bits = []
    if media.get("orientation") and media.get("aspect_ratio"):
        media_bits.append(f"{media['orientation']} {media['aspect_ratio']}")
    elif media.get("aspect_ratio"):
        media_bits.append(str(media["aspect_ratio"]))
    if media.get("resolution"):
        media_bits.append(str(media["resolution"]))
    if media.get("fps"):
        media_bits.append(f"{media['fps']} fps")
    lines = [
        f"# {title}",
        "",
        f"- **分析模式**: 内容拆解（起号）",
        f"- **标题**: {report['title']}",
        f"- **时长**: {report['duration_label']} ({report['duration_seconds']}s)",
        f"- **画面规格**: {' · '.join(media_bits) if media_bits else '（未探测）'}",
        f"- **标签**: {' '.join(report['hashtags']) or '（未识别）'}",
        f"- **口播总字数**: {report['script']['total_chars']}",
        f"- **口播段数**: {report['script']['segment_count']}",
        f"- **语速**: {report['voice']['chars_per_minute']} 字/分钟",
        f"- **音色推测**: {report['voice']['gender_guess']}"
        f"（基频 {report['voice']['pitch_hz_median']} Hz）",
        f"- **疑似 AI 配音**: {'是' if report['voice']['likely_ai_tts'] else '不确定/偏真人'}",
    ]

    if insights:
        lines.extend(render_insights_markdown(insights))
        lines.extend(["", "---"])

    if "chapters" in report:
        mode = report.get("keyframe_mode", "scene")
        mode_label = {
            "transcript": "口播一句一帧",
            "custom": f"自定义 {report.get('frame_count', '?')} 帧",
            "scene": "镜头切换检测",
        }.get(mode, mode)
        lines.extend(
            [
                f"- **章节数**: {len(report['chapters'])}",
                f"- **关键帧数**: {len(report.get('scenes', []))}",
                f"- **关键帧模式**: {mode_label}",
                "",
                "## 章节 × 口播（模仿用）",
                "",
                "| 时间 | 章节 | 字数 | 内容摘要 |",
                "|------|------|------|----------|",
            ]
        )
        for row in report.get("aligned", report["chapters"]):
            summary = row.get("summary", "").replace("|", "\\|")
            lines.append(
                f"| {row['time_range']} | {row['title']} | {row['chars']} | {summary} |"
            )

        lines.extend(["", "## 镜头列表", ""])
        for sc in report.get("scenes", [])[:40]:
            speech = sc.get("text") or sc.get("speech_text") or ""
            if len(speech) > 60:
                speech = speech[:60] + "…"
            speech_part = f"「{speech}」" if speech else ""
            vision = sc.get("vision") or {}
            vision_part = ""
            if vision:
                vision_bits = [vision.get("how_made"), vision.get("layout")]
                vision_part = " · " + " · ".join(b for b in vision_bits if b)
            lines.append(
                f"- `{sc['time_range'] if 'time_range' in sc else format_clock(sc['start']) + '-' + format_clock(sc['end'])}` "
                f"{speech_part}{vision_part} (`{sc['frame_path']}`)"
            )
        if len(report.get("scenes", [])) > 40:
            lines.append(f"- … 共 {len(report['scenes'])} 个镜头，详见 report.json")

    lines.extend(
        [
            "",
            "## 口播微段（Whisper 原始）",
            "",
            "| 时间 | 角色 | 字数 | 内容 |",
            "|------|------|------|------|",
        ]
    )

    for seg in report["script"]["segments"][:80]:
        text = seg["text"].replace("|", "\\|")
        if len(text) > 60:
            text = text[:60] + "…"
        lines.append(
            f"| {seg['time_range']} | {seg['role_guess']} | {seg['chars']} | {text} |"
        )
    if len(report["script"]["segments"]) > 80:
        lines.append(f"| … | … | … | 共 {report['script']['segment_count']} 段，详见 transcript.txt |")

    lines.extend(["", "## 完整口播稿", "", report["script"]["full_text"], ""])
    return "\n".join(lines)


def md_to_html(md: str) -> str:
    """Minimal, dependency-free markdown -> HTML for report viewing.

    Supports: h1-h3, blockquote, tables, ul/ol lists, hr, bold, inline code,
    links, and paragraphs. Escapes HTML first to stay safe with transcript text.
    """
    import html as _html

    def inline(text: str) -> str:
        text = _html.escape(text, quote=False)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" target="_blank" rel="noopener">\1</a>',
            text,
        )
        return text

    def split_row(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    def is_table_sep(line: str) -> bool:
        return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line

    out: list[str] = []
    lines = md.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("```"):
            code: list[str] = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # closing fence
            out.append(f"<pre><code>{_html.escape(chr(10).join(code))}</code></pre>")
            continue

        if line.startswith("### "):
            out.append(f"<h4>{inline(line[4:])}</h4>")
            i += 1
            continue
        if line.startswith("## "):
            out.append(f"<h3>{inline(line[3:])}</h3>")
            i += 1
            continue
        if line.startswith("# "):
            out.append(f"<h2>{inline(line[2:])}</h2>")
            i += 1
            continue
        if line.strip() in ("---", "***", "___"):
            out.append("<hr/>")
            i += 1
            continue
        if line.startswith("> "):
            quote: list[str] = []
            while i < n and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{'<br/>'.join(inline(q) for q in quote if q)}</blockquote>")
            continue
        if line.lstrip().startswith("|") and i + 1 < n and is_table_sep(lines[i + 1]):
            header = split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            thead = "".join(f"<th>{inline(h)}</th>" for h in header)
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            out.append(
                '<div class="md-table-wrap"><table><thead><tr>'
                f"{thead}</tr></thead><tbody>{tbody}</tbody></table></div>"
            )
            continue

        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            ordered = bool(re.match(r"\d+\.", m.group(2)))
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < n:
                m2 = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not m2:
                    break
                items.append(f"<li>{inline(m2.group(3))}</li>")
                i += 1
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        # paragraph: gather consecutive plain lines
        para: list[str] = []
        while i < n and lines[i].strip() and not lines[i].lstrip().startswith(("#", ">", "|", "```", "- ", "* ")):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f"<p>{'<br/>'.join(inline(p) for p in para)}</p>")
        else:
            i += 1  # safety: skip unrecognized line

    return "\n".join(out)


def resolve_project_input(raw: str) -> Path:
    try:
        return resolve_project(raw)
    except (FileNotFoundError, ValueError):
        pass

    if download_video is None or extract_url is None:
        raise FileNotFoundError(f"Cannot resolve project: {raw!r}")

    project = download_video(extract_url(raw), share_text=raw)
    write_last_project(project)
    return project


def derive_title(project: Path, video: Path) -> str:
    meta = load_meta(project)
    if meta.get("title"):
        return meta["title"]
    stem = video.stem
    if re.search(r"\s\[\d+\]$", stem):
        return re.sub(r"\s\[\d+\]$", "", stem)
    return stem


def load_existing_segments(output_dir: Path) -> tuple[list[Segment], str] | None:
    report_path = output_dir / "report.json"
    if not report_path.exists():
        return None
    data = json.loads(report_path.read_text(encoding="utf-8"))
    segs = data.get("script", {}).get("segments", [])
    if not segs:
        return None
    segments = [
        Segment(
            index=s["index"],
            start=s["start"],
            end=s["end"],
            text=s["text"],
            chars=s["chars"],
        )
        for s in segs
    ]
    transcript = data.get("script", {}).get("full_text", "\n".join(s.text for s in segments))
    return segments, transcript


def analyze(
    project: Path,
    output_dir: Path,
    *,
    model_size: str = "small",
    full: bool = False,
    scene_threshold: float = 27.0,
    force: bool = False,
    vision_prep: bool = False,
    keyframe_mode: str = "transcript",
    frame_count: int = 30,
    interval_seconds: float = 2.0,
    analysis_mode: str = "content",
) -> Path:
    video = video_file(project)
    if not video.exists():
        raise FileNotFoundError(f"Missing video.mp4 in {project}")

    analysis_mode = analysis_mode if analysis_mode in ANALYSIS_MODES else "content"
    keyframe_mode = recommend_keyframe_mode(analysis_mode, keyframe_mode)

    output_dir.mkdir(parents=True, exist_ok=True)
    title = derive_title(project, video)
    try:
        media = probe_video_media(video)
        duration = float(media["duration_seconds"])
    except Exception as exc:
        print(f"WARN: probe_video_media failed ({exc}), fallback duration only", file=sys.stderr)
        media = {}
        duration = probe_duration(video)

    wav = output_dir / "audio.wav"
    existing = None if force else load_existing_segments(output_dir)

    if existing:
        segments, transcript = existing
        if not wav.exists():
            extract_audio(video, wav)
        print("Reusing existing transcript.", file=sys.stderr)
    else:
        extract_audio(video, wav)
        segments, transcript, srt = transcribe(wav, model_size)
        (output_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
        (output_dir / "transcript.srt").write_text(srt, encoding="utf-8")

    hashtags = extract_hashtags(title)
    voice = analyze_voice(wav, segments, duration)

    chapters = None
    scenes = None
    aligned = None

    if full:
        mode = keyframe_mode if keyframe_mode in KEYFRAME_MODES else "transcript"
        print(
            f"Phase 2: keyframes ({mode}) and chapters… [analysis_mode={analysis_mode}]",
            file=sys.stderr,
        )
        scenes_dir = output_dir / "scenes"
        scenes = extract_keyframes(
            video,
            duration,
            scenes_dir,
            mode=mode,
            segments=segments,
            frame_count=frame_count,
            scene_threshold=scene_threshold,
            interval_seconds=interval_seconds,
        )
        chapters = build_chapters(segments, duration)
        aligned = align_chapters_scenes(chapters, scenes)
        (output_dir / "chapters.json").write_text(
            json.dumps(
                {
                    "chapters": chapters,
                    "aligned": aligned,
                    "keyframe_mode": mode,
                    "frame_count": frame_count if mode == "custom" else None,
                    "interval_seconds": interval_seconds if mode == "interval" else None,
                    "analysis_mode": analysis_mode,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    report = build_report(
        video=video,
        title=title,
        duration=duration,
        segments=segments,
        transcript=transcript,
        hashtags=hashtags,
        voice=voice,
        chapters=chapters,
        scenes=scenes,
        aligned=aligned,
        keyframe_mode=keyframe_mode if full else None,
        frame_count=frame_count if full and keyframe_mode == "custom" else None,
        media=media,
    )
    report["analysis_mode"] = analysis_mode

    # Enrich scene dicts with time_range for markdown/json readability.
    if report.get("scenes"):
        for sc in report["scenes"]:
            sc["time_range"] = f"{format_clock(sc['start'])}-{format_clock(sc['end'])}"
            sc["duration_seconds"] = round(sc["end"] - sc["start"], 2)
            if sc.get("text"):
                sc["speech_text"] = sc["text"]

    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta = load_meta(project)
    analysis_mode = "content"
    insights = build_insights(report, meta)
    md_body = render_markdown(report, insights)

    (output_dir / "report.md").write_text(md_body, encoding="utf-8")

    meta["last_analysis_at"] = datetime.now().isoformat(timespec="seconds")
    meta["analysis_dir"] = str(output_dir)
    meta["analysis_mode"] = analysis_mode

    # 固定知识库副本: reports/YYYY-MM/{date}_{id}_{slug}.md
    try:
        kb_path = report_kb_path(project.name, title or meta.get("title", ""), meta["last_analysis_at"])
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        kb_path.write_text(md_body, encoding="utf-8")
        meta["report_kb_path"] = str(kb_path)
    except Exception as exc:  # 知识库副本失败不阻塞主流程
        print(f"WARN: knowledge-base report copy failed: {exc}", file=sys.stderr)

    save_meta(project, meta)

    if vision_prep and full and scenes:
        from vision_describe import prepare_vision_manifest

        prepare_vision_manifest(project)

    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a Douyin/local video.")
    parser.add_argument(
        "input",
        help="Video project dir, aweme id, video.mp4, share link, or 'last'",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Output directory (default: videos/{id}/analysis)",
    )
    parser.add_argument(
        "--model",
        default="small",
        choices=["tiny", "base", "small", "medium"],
        help="faster-whisper model size (default: small)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Phase 2: scene detection, keyframes, chapter alignment",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=27.0,
        help="Scene cut sensitivity, higher = fewer cuts (default: 27)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run transcription even if report.json exists",
    )
    parser.add_argument(
        "--vision-prep",
        action="store_true",
        help="After --full, generate vision/manifest.json for Phase 3",
    )
    parser.add_argument(
        "--keyframe-mode",
        default=None,
        choices=sorted(KEYFRAME_MODES),
        help="Keyframe: transcript / custom / scene / interval；默认 transcript",
    )
    parser.add_argument(
        "--frame-count",
        type=int,
        default=30,
        help="Frame count when --keyframe-mode=custom (default: 30)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=2.0,
        help="Seconds between frames when --keyframe-mode=interval (default: 2)",
    )
    parser.add_argument(
        "--analysis-mode",
        default="content",
        choices=sorted(ANALYSIS_MODES),
        help="仅 content（内容拆解）。AIGC 反推请用 1008-aigc-prompt-reverse",
    )
    args = parser.parse_args()

    try:
        project = resolve_project_input(args.input)
        out = Path(args.output) if args.output else analysis_dir(project)
        result = analyze(
            project,
            out,
            model_size=args.model,
            full=args.full,
            scene_threshold=args.scene_threshold,
            force=args.force,
            vision_prep=args.vision_prep,
            keyframe_mode=args.keyframe_mode,
            frame_count=args.frame_count,
            interval_seconds=args.interval_seconds,
            analysis_mode=args.analysis_mode,
        )
        print(f"Done: {result / 'report.md'}")
        print(f"Project: {project}")
        if args.full:
            print(f"Scenes: {result / 'scenes'}")
            print(f"Chapters: {result / 'chapters.json'}")
        if args.vision_prep:
            print(f"Vision manifest: {result / 'vision' / 'manifest.json'}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
