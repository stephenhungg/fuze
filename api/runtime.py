"""runtime boundary for hosted preview vs gb10 execution."""

from __future__ import annotations

import os
from typing import Any

import httpx


GB10_RUNTIME_URL = os.getenv("FUZE_GB10_RUNTIME_URL", "").rstrip("/")
GB10_RUNTIME_TOKEN = os.getenv("FUZE_GB10_RUNTIME_TOKEN", "")
HOSTED_PREVIEW = os.getenv("VERCEL") == "1" or os.getenv("FUZE_HOSTED_PREVIEW", "0") == "1"


def configured() -> bool:
    return bool(GB10_RUNTIME_URL)


def headers() -> dict[str, str]:
    if not GB10_RUNTIME_TOKEN:
        return {}
    return {"authorization": f"bearer {GB10_RUNTIME_TOKEN}"}


async def gb10_status() -> dict[str, Any]:
    """report whether this process can reach a secured gb10 runtime."""
    if not configured():
        return {
            "configured": False,
            "reachable": False,
            "execution": "hosted_preview",
            "message": "no FUZE_GB10_RUNTIME_URL configured; prod is using synthetic demo data locally in vercel.",
        }

    try:
        async with httpx.AsyncClient(timeout=2.5, headers=headers()) as client:
            response = await client.get(f"{GB10_RUNTIME_URL}/health")
            response.raise_for_status()
        payload = response.json()
        return {
            "configured": True,
            "reachable": True,
            "execution": "gb10_runtime",
            "url": GB10_RUNTIME_URL,
            "authenticated": bool(GB10_RUNTIME_TOKEN),
            "remote": {
                "ok": payload.get("ok"),
                "cloud_llm_calls": payload.get("cloud_llm_calls"),
                "ollama": payload.get("ollama", {}),
                "qdrant": payload.get("qdrant", {}),
                "always_on": payload.get("always_on", {}),
            },
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "execution": "gb10_runtime_unreachable",
            "url": GB10_RUNTIME_URL,
            "authenticated": bool(GB10_RUNTIME_TOKEN),
            "error": str(exc),
        }


def local_execution_mode() -> dict[str, Any]:
    if configured():
        return {
            "mode": "gb10_runtime_configured",
            "provider": "secured gb10 runtime",
            "inference": "remote local ollama behind private access boundary",
        }
    return {
        "mode": "hosted_preview",
        "provider": "deterministic demo engine",
        "inference": "none; responses are assembled from synthetic sample data",
    }
