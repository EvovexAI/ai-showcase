"""Volcano Engine TTS (OpenSpeech v3) — adapted from EvoFlow volcengine_speech.py."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import uuid

import httpx

logger = logging.getLogger(__name__)

OPENSPEECH_BASE = "https://openspeech.bytedance.com"
TTS_URL_STANDARD = f"{OPENSPEECH_BASE}/api/v3/tts/unidirectional"
TTS_URL_AGENT_PLAN = f"{OPENSPEECH_BASE}/api/v3/plan/tts/unidirectional"

DEFAULT_TTS_RESOURCE_ID = "seed-tts-2.0"
DEFAULT_TTS_SPEAKER = "zh_female_vv_uranus_bigtts"


def normalize_key(raw: str) -> str:
    return str(raw or "").strip().strip('"').strip("'")


def is_agent_plan_key(api_key: str) -> bool:
    return normalize_key(api_key).lower().startswith("ark-")


def speech_headers(*, api_key: str, resource_id: str, request_id: str | None = None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
    }
    if request_id:
        headers["X-Api-Request-Id"] = request_id
        headers["X-Api-Sequence"] = "-1"
    return headers


def tts_url_for_synthesis(
    *,
    agent_plan: bool,
    explicit_speaker: bool,
    preview: bool,
    resource_id: str,
) -> str:
    if explicit_speaker or preview or resource_id == "seed-tts-2.0":
        return TTS_URL_STANDARD
    return TTS_URL_AGENT_PLAN if agent_plan else TTS_URL_STANDARD


def resolve_tts_resource_id(speaker: str, configured: str) -> str:
    sid = str(speaker or "").strip().lower()
    fallback = str(configured or "").strip() or DEFAULT_TTS_RESOURCE_ID
    if not sid:
        return fallback
    if sid.startswith("s_"):
        return "seed-icl-2.0"
    if sid.startswith("saturn_") or "_uranus_" in sid:
        return "seed-tts-2.0"
    if sid.startswith("icl_uranus_"):
        return "seed-tts-2.0"
    if sid.startswith("icl_"):
        return "seed-tts-1.0"
    if sid.endswith("_moon_bigtts") or sid.endswith("_mars_bigtts") or "_conversation_wvae_bigtts" in sid:
        return "seed-tts-1.0"
    return fallback


def parse_tts_ndjson(body: str) -> bytes:
    chunks: list[bytes] = []
    decoder = json.JSONDecoder()
    idx = 0
    raw = body.strip()
    while idx < len(raw):
        while idx < len(raw) and raw[idx].isspace():
            idx += 1
        if idx >= len(raw):
            break
        try:
            obj, end = decoder.raw_decode(raw, idx)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"TTS invalid NDJSON at {idx}: {raw[idx : idx + 120]!r}") from e
        idx = end
        code = obj.get("code")
        if code == 0 and obj.get("data"):
            chunks.append(base64.b64decode(str(obj["data"])))
            continue
        if code == 20000000:
            break
        if code not in (0, 20000000):
            message = obj.get("message") or obj.get("msg") or str(obj)
            raise RuntimeError(f"TTS error code={code}: {message}")
    if not chunks:
        raise RuntimeError("TTS returned empty audio")
    return b"".join(chunks)


def synthesize_speech(
    text: str,
    *,
    api_key: str,
    speaker: str | None = None,
    resource_id: str | None = None,
    preview: bool = False,
) -> tuple[bytes, str]:
    """Return (mp3_bytes, speaker_used)."""
    key = normalize_key(api_key)
    if not key:
        raise ValueError(
            "未配置火山语音 API Key。请在「设置 → 配音」填写 Agent Plan Key（ark- 开头），"
            "或设置环境变量 ARK_API_KEY / VOLCENGINE_SPEECH_API_KEY。"
        )

    agent_plan = is_agent_plan_key(key)
    configured_resource = str(resource_id or "").strip() or DEFAULT_TTS_RESOURCE_ID
    default_speaker = str(speaker or "").strip() or DEFAULT_TTS_SPEAKER
    explicit_speaker = bool(str(speaker or "").strip())
    use_speaker = default_speaker
    resolved_resource = resolve_tts_resource_id(use_speaker, configured_resource)

    req_params: dict = {
        "text": text[:4000],
        "speaker": use_speaker,
        "audio_params": {"format": "mp3", "sample_rate": 24000},
    }
    if preview:
        req_params["additions"] = json.dumps(
            {
                "cache_config": {"text_type": 1, "use_cache": False},
                "section_id": str(uuid.uuid4()),
            },
            ensure_ascii=False,
        )

    payload = {
        "user": {"uid": f"qihhao-{'preview' if preview else 'tts'}-{uuid.uuid4().hex[:12]}"},
        "req_params": req_params,
    }
    headers = speech_headers(
        api_key=key,
        resource_id=resolved_resource,
        request_id=str(uuid.uuid4()),
    )
    url = tts_url_for_synthesis(
        agent_plan=agent_plan,
        explicit_speaker=explicit_speaker,
        preview=preview,
        resource_id=resolved_resource,
    )

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload, headers=headers)
    if resp.status_code != 200 and url == TTS_URL_STANDARD and agent_plan:
        logger.warning("Standard TTS failed (%s), retrying plan endpoint", resp.status_code)
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(TTS_URL_AGENT_PLAN, json=payload, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"TTS HTTP {resp.status_code}: {resp.text[:300]}")

    audio = parse_tts_ndjson(resp.text)
    digest = hashlib.md5(audio).hexdigest()[:12]
    logger.info("TTS ok speaker=%s resource=%s digest=%s", use_speaker, resolved_resource, digest)
    return audio, use_speaker
