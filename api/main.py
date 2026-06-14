"""fuze local-first demo api."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, events, identity, ingest, onboarding, policy, retrieval, vector_memory
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
    user_id: str | None = "morgan"


class PolicyRequest(BaseModel):
    text: str
    citations: list[str] = []
    external: bool = True


class VectorSearchRequest(BaseModel):
    query: str = DEMO_GOAL
    limit: int = 5


class ContextQueryRequest(BaseModel):
    question: str = DEMO_GOAL
    org_id: str = "harbor-light-nonprofit"
    skill: str = "nonprofit_grants"
    role: str = "grant_manager"
    user_id: str | None = "morgan"
    external: bool = True
    limit: int = 8


class ApprovalDecisionRequest(BaseModel):
    status: str
    actor: str = "alex"
    note: str = ""


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
    return await vector_memory.status()


async def monitor_loop() -> None:
    while True:
        try:
            result = agent.run_agent(goal=f"always-on monitor: {DEMO_GOAL}", role="grant_manager", user_id="morgan")
            events.record_run(result, trigger="always-on")
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


def sse_frame(event: str, data: dict[str, Any], event_id: str | None = None) -> str:
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, separators=(',', ':'))}")
    return "\n".join(lines) + "\n\n"


async def event_stream() -> AsyncIterator[str]:
    sent_ids: set[str] = set()
    while True:
        status = events.agent_status()
        for event in reversed(status["events"]):
            if event["id"] in sent_ids:
                continue
            sent_ids.add(event["id"])
            yield sse_frame("agent_event", event, event["id"])
        yield sse_frame("observability", events.observability_summary())
        await asyncio.sleep(2)


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
        "identity": identity.identity_status(),
        "always_on": monitor_state,
    }


@app.post("/demo/seed")
async def seed() -> dict[str, Any]:
    snapshot = store.seed()
    vector_seed = await vector_memory.seed()
    return {"status": "seeded", "snapshot": snapshot, "vector_seed": vector_seed}


@app.post("/agent/run")
def run_agent(request: GoalRequest) -> dict[str, Any]:
    result = agent.run_agent(goal=request.goal, role=request.role, user_id=request.user_id)
    events.record_run(result, trigger="manual")
    return result


@app.get("/demo/pitch")
def demo_pitch() -> dict[str, Any]:
    return agent.pitch_packet()


@app.get("/agent/status")
def agent_status() -> dict[str, Any]:
    return {
        "always_on": monitor_state,
        "tasks": store.tasks,
        "audit_runs": store.audit_runs[-5:],
        "mesh": events.agent_status(),
    }


@app.get("/agents/status")
def agents_status() -> dict[str, Any]:
    return events.agent_status()


@app.get("/agents/events")
def agents_events() -> dict[str, Any]:
    return {"events": events.agent_status()["events"]}


@app.get("/events/stream")
async def events_stream() -> StreamingResponse:
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/observability/summary")
def observability_summary() -> dict[str, Any]:
    return events.observability_summary()


@app.get("/ingestion/status")
def ingestion_status() -> dict[str, Any]:
    result = ingest.ingest_sample_corpus()
    return {key: value for key, value in result.items() if key != "chunks"}


@app.post("/ingestion/run")
async def ingestion_run() -> dict[str, Any]:
    result = ingest.ingest_sample_corpus()
    memory_chunks = ingest.chunks_for_memory(result)
    store.replace_chunks(memory_chunks)
    vector_seed = await vector_memory.seed()
    result["memory_chunks"] = len(memory_chunks)
    result["vector_seed"] = vector_seed
    events.record_ingestion(result)
    return result


@app.get("/identity/users")
def identity_users() -> dict[str, Any]:
    return {"users": identity.list_users(), "role_map": identity.GROUP_ROLE_MAP}


@app.get("/onboarding/flow")
def onboarding_flow() -> dict[str, Any]:
    return onboarding.onboarding_status()


@app.get("/graph")
def graph() -> dict[str, Any]:
    return store.graph()


@app.get("/tasks")
def tasks() -> dict[str, Any]:
    return {"tasks": store.tasks}


@app.get("/approvals")
def approvals() -> dict[str, Any]:
    return {"approvals": store.approvals}


@app.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, Any]:
    try:
        approval = store.decide_approval(
            approval_id=approval_id,
            status=request.status,
            actor=request.actor,
            note=request.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found")
    events.record_approval_decision(approval)
    return {"approval": approval}


@app.get("/audit")
def audit() -> dict[str, Any]:
    return {"audit_runs": store.audit_runs}


@app.post("/tools/get_context")
def get_context(request: GoalRequest) -> dict[str, Any]:
    return retrieval.get_context(goal=request.goal, role=request.role, user_id=request.user_id, external=True)


@app.post("/context/query")
async def context_query(request: ContextQueryRequest) -> dict[str, Any]:
    return await retrieval.query_context_core(
        question=request.question,
        org_id=request.org_id,
        skill=request.skill,
        role=request.role,
        user_id=request.user_id,
        external=request.external,
        limit=request.limit,
    )


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


@app.post("/tools/vector_search")
async def vector_search(request: VectorSearchRequest) -> dict[str, Any]:
    return await vector_memory.search(query=request.query, limit=request.limit)
