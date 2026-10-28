#!/usr/bin/env python3
"""Download Douyin videos — one project directory per video."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from paths import (
    VIDEOS_DIR,
    create_or_update_meta,
    load_meta,
    project_dir,
    video_file,
    write_last_project,
)

URL_RE = re.compile(
    r"https?://(?:v\.douyin\.com|www\.douyin\.com|www\.iesdouyin\.com)/[^\s\]\)\"'<>，。；]+",
    re.IGNORECASE,
)
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1"
)


def extract_url(text: str) -> str:
    text = text.strip()
    if text.startswith("http"):
        return text.rstrip("/.,;)")
    match = URL_RE.search(text)
    if not match:
        raise ValueError(f"No Douyin URL found in: {text!r}")
    return match.group(0).rstrip("/.,;)")


def extract_hashtags(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"#[\w\u4e00-\u9fff]+", text)))


def decode_json_string(text: str) -> str:
    return json.loads(f'"{text}"')


def sanitize_filename(name: str, *, max_len: int = 80) -> str:
    cleaned = "".join(c for c in name if c not in '<>:"/\\|?*').strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned


def fetch_share_page(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": MOBILE_UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


_TTWID_CACHE: str | None = None


def _mint_ttwid() -> str:
    """Mint a fresh ttwid cookie via bytedance's anonymous register API."""
    global _TTWID_CACHE
    if _TTWID_CACHE:
        return _TTWID_CACHE
    body = json.dumps(
        {
            "region": "cn",
            "aid": 1768,
            "needFid": False,
            "service": "www.ixigua.com",
            "migrate_info": {"ticket": "", "source": "node"},
            "cbUrlProtocol": "https",
            "union": True,
        }
    ).encode()
    req = urllib.request.Request(
        "https://ttwid.bytedance.com/ttwid/union/register/",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": MOBILE_UA},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        for cookie in resp.headers.get_all("Set-Cookie") or []:
            if cookie.startswith("ttwid="):
                _TTWID_CACHE = cookie.split(";")[0].split("=", 1)[1]
                break
    if not _TTWID_CACHE:
        raise RuntimeError("failed to mint ttwid")
    return _TTWID_CACHE


def fetch_m_share_page(aweme_id: str) -> str:
    """m.douyin.com share page with ttwid — current working source of play_addr."""
    req = urllib.request.Request(
        f"https://m.douyin.com/share/video/{aweme_id}",
        headers={
            "User-Agent": MOBILE_UA,
            "Cookie": f"ttwid={_mint_ttwid()}",
            "Referer": "https://www.douyin.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_m_share_page(page: str) -> dict:
    """Extract play_addr from m.douyin.com SSR page (both raw and \\u002F escaped forms)."""
    page = page.replace("\\u002F", "/")
    play_match = re.search(
        r'"(?:play_addr|playAddr)"\s*:\s*\{[^}]*?"url_list"\s*:\s*\["([^"]+)"', page
    )
    if not play_match:
        raise RuntimeError("no play_addr in m-share page")

    video_url = decode_json_string(play_match.group(1)).replace("playwm", "play")
    aweme_match = re.search(r'"aweme_id"\s*:\s*"(\d+)"', page)
    aweme_id = aweme_match.group(1) if aweme_match else "unknown"
    desc_match = re.search(r'"desc"\s*:\s*"((?:\\.|[^"\\])*)"', page)
    desc = decode_json_string(desc_match.group(1)) if desc_match else ""
    title = sanitize_filename(desc) if desc else f"douyin_{aweme_id}"
    nickname_match = re.search(r'"nickname"\s*:\s*"((?:\\.|[^"\\])*)"', page)
    author_nickname = decode_json_string(nickname_match.group(1)) if nickname_match else ""
    unique_match = re.search(r'"unique_id"\s*:\s*"([^"]+)"', page)
    author_unique_id = unique_match.group(1) if unique_match else ""
    return {
        "aweme_id": aweme_id,
        "title": title,
        "desc": desc,
        "video_url": video_url,
        "author_nickname": author_nickname,
        "author_unique_id": author_unique_id,
        "hashtags": extract_hashtags(desc),
    }


def download_via_m_share(aweme_id: str, share_text: str = "") -> Path:
    page = fetch_m_share_page(aweme_id)
    info = parse_m_share_page(page)
    if info["aweme_id"] == "unknown":
        info["aweme_id"] = aweme_id
    project = project_dir(info["aweme_id"])
    project.mkdir(parents=True, exist_ok=True)
    out = video_file(project)
    download_bytes(info["video_url"], out)
    apply_share_info(project, info, source_url=f"https://www.douyin.com/video/{aweme_id}", share_text=share_text)
    write_last_project(project)
    return project


def parse_share_page(page: str) -> dict:
    play_match = re.search(
        r'"play_addr"\s*:\s*\{[^}]*"url_list"\s*:\s*\["([^"]+)"',
        page,
    )
    if not play_match:
        raise RuntimeError("Could not find play_addr in share page")

    video_url = decode_json_string(play_match.group(1)).replace("playwm", "play")

    aweme_match = re.search(r'"aweme_id"\s*:\s*"(\d+)"', page)
    aweme_id = aweme_match.group(1) if aweme_match else "unknown"

    desc_match = re.search(r'"desc"\s*:\s*"((?:\\.|[^"\\])*)"', page)
    desc = decode_json_string(desc_match.group(1)) if desc_match else ""
    title = sanitize_filename(desc) if desc else f"douyin_{aweme_id}"
    if not title:
        title = f"douyin_{aweme_id}"

    nickname_match = re.search(r'"nickname"\s*:\s*"((?:\\.|[^"\\])*)"', page)
    author_nickname = (
        decode_json_string(nickname_match.group(1)) if nickname_match else ""
    )

    unique_match = re.search(r'"unique_id"\s*:\s*"([^"]+)"', page)
    author_unique_id = unique_match.group(1) if unique_match else ""

    return {
        "aweme_id": aweme_id,
        "title": title,
        "desc": desc,
        "video_url": video_url,
        "author_nickname": author_nickname,
        "author_unique_id": author_unique_id,
        "hashtags": extract_hashtags(desc),
    }


def download_bytes(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": MOBILE_UA, "Referer": "https://www.douyin.com/"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def apply_share_info(
    project: Path,
    info: dict,
    *,
    source_url: str = "",
    share_text: str = "",
) -> dict:
    aweme_id = info["aweme_id"]
    return create_or_update_meta(
        project,
        aweme_id=aweme_id,
        title=info.get("desc") or info["title"],
        desc=info.get("desc", ""),
        source_url=source_url,
        share_text=share_text,
        author_nickname=info.get("author_nickname", ""),
        author_unique_id=info.get("author_unique_id", ""),
        hashtags=info.get("hashtags", []),
        canonical_url=f"https://www.douyin.com/video/{aweme_id}",
    )


def refresh_meta(project: Path) -> dict:
    meta = load_meta(project)
    aweme_id = meta.get("aweme_id") or project.name
    source_url = meta.get("source_url") or f"https://www.iesdouyin.com/share/video/{aweme_id}/"
    page = fetch_share_page(source_url)
    info = parse_share_page(page)
    return apply_share_info(
        project,
        info,
        source_url=source_url,
        share_text=meta.get("share_text", ""),
    )


def download_via_share_page(url: str, share_text: str = "") -> Path:
    page = fetch_share_page(url)
    info = parse_share_page(page)

    project = project_dir(info["aweme_id"])
    project.mkdir(parents=True, exist_ok=True)
    out = video_file(project)
    download_bytes(info["video_url"], out)

    apply_share_info(project, info, source_url=url, share_text=share_text)
    write_last_project(project)
    return project


def download_via_ytdlp(url: str, share_text: str = "", *, cookies: Path | None = None) -> Path:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp not installed")

    tmp_dir = VIDEOS_DIR / "_tmp_ytdlp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts: dict = {
        "outtmpl": str(tmp_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "retries": 5,
        "fragment_retries": 5,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.douyin.com/",
        },
    }
    if cookies and cookies.exists():
        ydl_opts["cookiefile"] = str(cookies)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("Failed to extract video info")
        aweme_id = str(info.get("id") or "unknown")
        title = sanitize_filename(str(info.get("title") or f"douyin_{aweme_id}"))
        tmp_file = next(tmp_dir.glob(f"{aweme_id}.*"))

    project = project_dir(aweme_id)
    project.mkdir(parents=True, exist_ok=True)
    out = video_file(project)
    tmp_file.replace(out)

    create_or_update_meta(
        project,
        aweme_id=aweme_id,
        title=title,
        source_url=url,
        share_text=share_text,
        canonical_url=f"https://www.douyin.com/video/{aweme_id}",
        author_nickname=str(info.get("uploader") or info.get("channel") or ""),
    )
    write_last_project(project)
    return project


def download(
    url: str,
    share_text: str = "",
    *,
    cookies: Path | None = None,
    audio_only: bool = False,
) -> Path:
    if audio_only:
        return download_via_ytdlp(url, share_text, cookies=cookies)

    # 0) 优先 m.douyin.com + ttwid（当前最稳的免登录路径）
    try:
        # 从短链解析出 aweme_id（跟随跳转）
        req = urllib.request.Request(url, headers={"User-Agent": MOBILE_UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.geturl()
        aweme_match = re.search(r"/(?:video|note)/(\d+)", final_url)
        if aweme_match:
            try:
                return download_via_m_share(aweme_match.group(1), share_text)
            except Exception as m_err:
                print(f"m-share path failed: {m_err}", file=sys.stderr)
    except Exception as resolve_err:
        print(f"resolve short link failed: {resolve_err}", file=sys.stderr)

    try:
        return download_via_share_page(url, share_text)
    except Exception as share_err:
        print(f"Share-page fallback failed: {share_err}", file=sys.stderr)
        print("Trying yt-dlp...", file=sys.stderr)
        return download_via_ytdlp(url, share_text, cookies=cookies)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Douyin video into videos/{id}/")
    parser.add_argument("url", help="Douyin share URL or pasted share text")
    parser.add_argument("--cookies", help="Netscape cookies.txt (yt-dlp fallback)")
    parser.add_argument("--audio-only", action="store_true")
    args = parser.parse_args()

    try:
        share_text = args.url
        url = extract_url(args.url)
        project = download(
            url,
            share_text=share_text,
            cookies=Path(args.cookies) if args.cookies else None,
            audio_only=args.audio_only,
        )
        print(f"\nDone: {project}")
        print(f"Video: {video_file(project)}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
