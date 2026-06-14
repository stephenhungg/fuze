"""fuze local-first demo api."""

from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, policy, retrieval
from .db import DEMO_GOAL, store


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

monitor_state: dict[str, Any] = {
    "enabled": os.getenv("FUZE_DISABLE_MONITOR") != "1",
    "interval_seconds": int(os.getenv("FUZE_MONITOR_INTERVAL", "60")),
    "runs": 0,
    "last_run": None,
    "last_status": "starting",
    "last_error": None,
    "next_check": None,
}
monitor_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global monitor_task
    if monitor_state["enabled"] and monitor_task is None:
        monitor_task = asyncio.create_task(monitor_loop())
    try:
        yield
    finally:
        if monitor_task is not None:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task
            monitor_task = None


app = FastAPI(
    title="fuze",
    description="local-first memory and governance layer for always-on business agents",
    version="0.1.0",
    lifespan=lifespan,
)

if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


class GoalRequest(BaseModel):
    goal: str = DEMO_GOAL
    role: str = "grant_manager"


class PolicyRequest(BaseModel):
    text: str
    citations: list[str] = []
    external: bool = True


async def ollama_status() -> dict[str, Any]:
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{host}/api/tags")
            response.raise_for_status()
            models = [model["name"] for model in response.json().get("models", [])]
        return {"available": True, "host": host, "models": models}
    except Exception as exc:
        return {"available": False, "host": host, "error": str(exc)}


async def qdrant_status() -> dict[str, Any]:
    host = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{host}/healthz")
            response.raise_for_status()
        return {"available": True, "host": host}
    except Exception as exc:
        return {"available": False, "host": host, "error": str(exc)}


async def monitor_loop() -> None:
    while True:
        try:
            result = agent.run_agent(goal=f"always-on monitor: {DEMO_GOAL}", role="grant_manager")
            monitor_state.update(
                {
                    "runs": monitor_state["runs"] + 1,
                    "last_run": result["audit"]["created_at"],
                    "last_status": result["status"],
                    "last_error": None,
                    "next_check": f"in {monitor_state['interval_seconds']}s",
                }
            )
        except Exception as exc:
            monitor_state.update({"last_status": "error", "last_error": str(exc)})
        await asyncio.sleep(monitor_state["interval_seconds"])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "name": "fuze",
        "mode": "local-first",
        "cloud_llm_calls": 0,
        "ollama": await ollama_status(),
        "qdrant": await qdrant_status(),
        "always_on": monitor_state,
    }


@app.post("/demo/seed")
def seed() -> dict[str, Any]:
    return {"status": "seeded", "snapshot": store.seed()}


@app.post("/agent/run")
def run_agent(request: GoalRequest) -> dict[str, Any]:
    return agent.run_agent(goal=request.goal, role=request.role)


@app.get("/agent/status")
def agent_status() -> dict[str, Any]:
    return {"always_on": monitor_state, "tasks": store.tasks, "audit_runs": store.audit_runs[-5:]}


@app.get("/graph")
def graph() -> dict[str, Any]:
    return store.graph()


@app.get("/tasks")
def tasks() -> dict[str, Any]:
    return {"tasks": store.tasks}


@app.get("/audit")
def audit() -> dict[str, Any]:
    return {"audit_runs": store.audit_runs}


@app.post("/tools/get_context")
def get_context(request: GoalRequest) -> dict[str, Any]:
    return retrieval.get_context(goal=request.goal, role=request.role, external=True)


@app.post("/tools/prepare_report")
def prepare_report() -> dict[str, Any]:
    return agent.prepare_report()


@app.post("/tools/policy_check")
def policy_check(request: PolicyRequest) -> dict[str, Any]:
    return policy.evaluate_output(
        text=request.text,
        citations=request.citations,
        external=request.external,
    )


@app.post("/tools/create_tasks")
def create_tasks() -> dict[str, Any]:
    return {"tasks": agent.create_tasks()}
