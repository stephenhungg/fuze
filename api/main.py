"""fuze local-first demo api."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, policy, retrieval
from .db import DEMO_GOAL, store


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

app = FastAPI(
    title="fuze",
    description="local-first memory and governance layer for always-on business agents",
    version="0.1.0",
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
    }


@app.post("/demo/seed")
def seed() -> dict[str, Any]:
    return {"status": "seeded", "snapshot": store.seed()}


@app.post("/agent/run")
def run_agent(request: GoalRequest) -> dict[str, Any]:
    return agent.run_agent(goal=request.goal, role=request.role)


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
