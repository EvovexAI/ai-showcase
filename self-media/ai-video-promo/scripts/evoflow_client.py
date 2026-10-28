"""EvoFlow OpenAI-compatible chat client for 起号 workbench."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
EVOFLOW_CONFIG = ROOT / "workbench" / "config" / "evoflow.json"

SKILL_PROMPTS: dict[str, str] = {
    "douyin-analyze": "你是起号抖音拆解助手。用户会给你链接或 aweme_id，说明如何调用起号 scripts 完成下载与 analyze，并给出下一步建议。",
    "viral-collect": "你是爆款搜集助手。根据用户描述的平台与门槛，输出应对标账号/话题的结构化 JSON 建议。",
    "plan-from-report": "你是视频策划助手。根据 report.json 拆解结果，输出 productions 分镜策划 JSON 要点。",
    "cover-gen": "你是封面生成助手。说明如何用 HyperFrames 渲染 3:4/4:3 封面，以及文案要点。",
}


def load_evoflow_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    if EVOFLOW_CONFIG.exists():
        try:
            cfg = json.loads(EVOFLOW_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    base_url = os.getenv("EVOFLOW_GATEWAY_URL") or cfg.get("base_url") or "http://127.0.0.1:8080"
    api_key = os.getenv("EVOFLOW_API_KEY") or cfg.get("api_key") or ""
    return {
        "enabled": bool(cfg.get("enabled", False) or api_key),
        "base_url": str(base_url).rstrip("/"),
        "api_key": str(api_key).strip(),
        "default_model": str(cfg.get("default_model") or "agent:workbench-dispatch"),
        "skill_models": dict(cfg.get("skill_models") or {}),
        "timeout_seconds": float(cfg.get("timeout_seconds") or 120),
    }


def model_for_skill(skill_id: str | None, cfg: dict[str, Any] | None = None) -> str:
    c = cfg or load_evoflow_config()
    if skill_id:
        mapped = c.get("skill_models", {}).get(skill_id)
        if mapped:
            return str(mapped)
    return str(c.get("default_model") or "agent:workbench-dispatch")


def chat_completion(
    user_prompt: str,
    *,
    model: str | None = None,
    system: str | None = None,
    skill_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (assistant_text, meta). Raises on misconfiguration or HTTP error."""
    cfg = load_evoflow_config()
    if not cfg.get("enabled") or not cfg.get("api_key"):
        raise RuntimeError(
            "未配置 EvoFlow：请复制 workbench/config/evoflow.example.json → evoflow.json，"
            "填写 base_url 与 api_key（POST /api/auth/token 签发）"
        )

    use_model = model or model_for_skill(skill_id, cfg)
    messages: list[dict[str, str]] = []
    sys_text = system or (SKILL_PROMPTS.get(skill_id or "", "") if skill_id else "")
    if sys_text:
        messages.append({"role": "system", "content": sys_text})
    messages.append({"role": "user", "content": user_prompt})

    url = f"{cfg['base_url']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": use_model,
        "messages": messages,
        "stream": False,
    }

    with httpx.Client(timeout=cfg["timeout_seconds"]) as client:
        resp = client.post(url, json=payload, headers=headers)

    if resp.status_code == 404:
        raise RuntimeError(
            f"EvoFlow 尚未开放 {url}（404）。请升级 Gateway 或暂时关闭 evoflow.json 的 enabled。"
        )
    if resp.status_code != 200:
        raise RuntimeError(f"EvoFlow HTTP {resp.status_code}: {resp.text[:400]}")

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"EvoFlow 空响应: {data!r}")
    content = (choices[0].get("message") or {}).get("content") or ""
    meta = {
        "model": use_model,
        "usage": data.get("usage"),
        "id": data.get("id"),
    }
    return str(content).strip(), meta


def try_chat_or_hint(
    user_prompt: str,
    *,
    skill_id: str | None = None,
    context: dict[str, Any] | None = None,
) -> tuple[str, bool, str]:
    """Return (text, used_evoflow, status_message). Never raises."""
    extra = ""
    if context:
        extra = f"\n\n上下文：{json.dumps(context, ensure_ascii=False)}"
    full_prompt = user_prompt + extra
    try:
        text, meta = chat_completion(full_prompt, skill_id=skill_id)
        return text, True, f"EvoFlow {meta.get('model')}"
    except Exception as exc:
        cfg = load_evoflow_config()
        if not cfg.get("enabled"):
            hint = (
                "【本地模式】未启用 EvoFlow。请配置 workbench/config/evoflow.json 后重试。\n\n"
                f"任务摘要：{user_prompt[:500]}"
            )
        else:
            hint = f"【EvoFlow 调用失败】{exc}\n\n任务摘要：{user_prompt[:400]}"
        return hint, False, str(exc)
