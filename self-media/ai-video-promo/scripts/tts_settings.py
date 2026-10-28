"""Local TTS settings for 起号 — mirrors EvoFlow media TTS fields."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from paths import CONFIG_DIR, tts_settings_file

DEFAULT_TTS_RESOURCE_ID = "seed-tts-2.0"
DEFAULT_TTS_SPEAKER = "zh_female_vv_uranus_bigtts"
TTS_VOICES_FILE = CONFIG_DIR / "tts_voices.json"

DEFAULTS: dict[str, Any] = {
    "apiKey": "",
    "ttsResourceId": DEFAULT_TTS_RESOURCE_ID,
    "ttsSpeaker": DEFAULT_TTS_SPEAKER,
}

# Fallback when config/tts_voices.json is missing
TTS_VOICES_FALLBACK: list[dict[str, str]] = [
    {"id": "zh_female_vv_uranus_bigtts", "label": "Vivi 2.0（女声，通用/多语种）"},
    {"id": "zh_female_xiaohe_uranus_bigtts", "label": "小何 2.0（女声，通用）"},
    {"id": "zh_male_m191_uranus_bigtts", "label": "云舟 2.0（男声，通用）"},
    {"id": "zh_male_jieshuoxiaoming_uranus_bigtts", "label": "解说小明 2.0（通用）"},
    {"id": "zh_male_cixingjieshuonan_uranus_bigtts", "label": "磁性解说男声 2.0（通用）"},
    {"id": "zh_female_kefunvsheng_uranus_bigtts", "label": "暖阳女声 2.0（客服）"},
]

MASK_PLACEHOLDER = "********"


def load_tts_voices() -> list[dict[str, str]]:
    if TTS_VOICES_FILE.exists():
        try:
            data = json.loads(TTS_VOICES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return [{"id": str(v["id"]), "label": str(v["label"])} for v in data if v.get("id")]
        except Exception:
            pass
    return list(TTS_VOICES_FALLBACK)


def _normalize_key(raw: str) -> str:
    return str(raw or "").strip().strip('"').strip("'")


def _env_api_key() -> str:
    for name in (
        "VOLCENGINE_SPEECH_API_KEY",
        "BYTEPLUS_SEED_SPEECH_API_KEY",
        "ARK_API_KEY",
        "VOLCENGINE_API_KEY",
        "VOLCENGINE_TTS_ACCESS_TOKEN",
    ):
        val = _normalize_key(os.getenv(name, ""))
        if val:
            return val
    return ""


def _load_file() -> dict[str, Any]:
    path = tts_settings_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_file(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tts_settings_file().write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def mask_api_key(key: str) -> str:
    key = _normalize_key(key)
    if not key:
        return ""
    if len(key) <= 8:
        return MASK_PLACEHOLDER
    return f"{key[:4]}{MASK_PLACEHOLDER}{key[-4:]}"


def is_masked_value(value: str) -> bool:
    return MASK_PLACEHOLDER in str(value or "")


def load_tts_settings() -> dict[str, Any]:
    merged = deepcopy(DEFAULTS)
    merged.update(_load_file())
    env_key = _env_api_key()
    if env_key and not _normalize_key(merged.get("apiKey", "")):
        merged["apiKey"] = env_key
    if os.getenv("VOLCENGINE_TTS_RESOURCE_ID"):
        merged["ttsResourceId"] = os.getenv("VOLCENGINE_TTS_RESOURCE_ID", "").strip()
    if os.getenv("VOLCENGINE_TTS_SPEAKER"):
        merged["ttsSpeaker"] = os.getenv("VOLCENGINE_TTS_SPEAKER", "").strip()
    return merged


def get_resolved_credentials() -> tuple[str, str, str]:
    cfg = load_tts_settings()
    api_key = _normalize_key(cfg.get("apiKey", ""))
    resource = str(cfg.get("ttsResourceId") or DEFAULT_TTS_RESOURCE_ID).strip()
    speaker = str(cfg.get("ttsSpeaker") or DEFAULT_TTS_SPEAKER).strip()
    return api_key, resource, speaker


def tts_configured() -> bool:
    return bool(get_resolved_credentials()[0])


def public_tts_settings() -> dict[str, Any]:
    cfg = load_tts_settings()
    api_key = _normalize_key(cfg.get("apiKey", ""))
    return {
        "configured": bool(api_key),
        "apiKeyMasked": mask_api_key(api_key) if api_key else "",
        "ttsResourceId": cfg.get("ttsResourceId") or DEFAULT_TTS_RESOURCE_ID,
        "ttsSpeaker": cfg.get("ttsSpeaker") or DEFAULT_TTS_SPEAKER,
        "voices": load_tts_voices(),
        "voiceCount": len(load_tts_voices()),
        "agentPlanHint": "Agent Plan 用户填 ark- 开头的火山方舟 Key，与 EvoFlow 设置 → 创意媒体相同。",
        "docUrl": "https://www.volcengine.com/docs/82379/2516286?lang=zh",
    }


def save_tts_settings(updates: dict[str, Any]) -> dict[str, Any]:
    current = _load_file()
    merged = {**DEFAULTS, **current}

    if "ttsResourceId" in updates:
        merged["ttsResourceId"] = str(updates.get("ttsResourceId") or DEFAULT_TTS_RESOURCE_ID).strip()
    if "ttsSpeaker" in updates:
        merged["ttsSpeaker"] = str(updates.get("ttsSpeaker") or DEFAULT_TTS_SPEAKER).strip()

    raw_key = updates.get("apiKey")
    if raw_key is not None:
        key = str(raw_key).strip()
        if key and not is_masked_value(key):
            merged["apiKey"] = key

    _save_file(merged)
    return public_tts_settings()
