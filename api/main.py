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
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, events, identity, ingest, onboarding, personal_agents, policy, retrieval, runtime, vector_memory
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


@app.middleware("http")
async def runtime_token_guard(request: Request, call_next: Any) -> Any:
    expected = os.getenv("FUZE_INBOUND_RUNTIME_TOKEN", "")
    if expected and request.url.path != "/health":
        received = request.headers.get("authorization", "")
        if received != f"bearer {expected}":
            return JSONResponse({"detail": "runtime token required"}, status_code=401)
    return await call_next(request)


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


class DirectorySyncRequest(BaseModel):
    actor: str = "admin"


class GroupRoleMappingRequest(BaseModel):
    group: str
    role: str
    actor: str = "admin"


class ApprovalDecisionRequest(BaseModel):
    status: str
    actor: str = "alex"
    note: str = ""


class PersonalAgentProvisionRequest(BaseModel):
    user_id: str = "morgan"
    actor: str = "admin"


def body(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


async def proxy_runtime(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 60,
) -> dict[str, Any]:
    try:
        return await runtime.proxy_json(method, path, payload, timeout=timeout)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"gb10 runtime unreachable: {exc}") from exc


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


async def ensure_demo_memory() -> None:
    has_ingested_sample = any(
        chunk.get("metadata", {}).get("derived_from") == "sample_data/harbor_light"
        for chunk in store.chunks()
    )
    if has_ingested_sample:
        return
    result = ingest.ingest_sample_corpus()
    store.replace_chunks(ingest.chunks_for_memory(result))
    await vector_memory.seed()


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


@app.get("/robots.txt")
def robots() -> FileResponse:
    return FileResponse(WEB_DIR / "robots.txt")


@app.get("/sitemap.xml")
def sitemap() -> FileResponse:
    return FileResponse(WEB_DIR / "sitemap.xml")


@app.get("/auth")
@app.get("/admin/login")
@app.get("/admin")
@app.get("/onboarding")
@app.get("/app")
def spa_route() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, Any]:
    gb10 = await runtime.gb10_status()
    return {
        "ok": True,
        "name": "fuze",
        "mode": gb10["execution"],
        "cloud_llm_calls": 0,
        "runtime": {
            "hosted_preview": gb10["execution"] == "hosted_preview",
            "gb10": gb10,
        },
        "ollama": await ollama_status(),
        "qdrant": await qdrant_status(),
        "identity": identity.identity_status(),
        "always_on": monitor_state,
    }


@app.get("/system/runtime")
async def system_runtime() -> dict[str, Any]:
    gb10 = await runtime.gb10_status()
    return {
        "cloud_llm_calls": 0,
        "local_execution": runtime.local_execution_mode(),
        "gb10": gb10,
        "security_boundary": {
            "raw_public_gb10_access": False,
            "requires_private_tunnel": True,
            "recommended": "cloudflare access, tailscale, or wireguard with oidc and server-side rbac",
        },
    }


@app.post("/demo/seed")
async def seed() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/demo/seed", timeout=120)
    snapshot = store.seed()
    vector_seed = await vector_memory.seed()
    return {"status": "seeded", "snapshot": snapshot, "vector_seed": vector_seed}


@app.post("/agent/run")
async def run_agent(request: GoalRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/agent/run", body(request), timeout=120)
    await ensure_demo_memory()
    result = agent.run_agent(goal=request.goal, role=request.role, user_id=request.user_id)
    events.record_run(result, trigger="manual")
    return result


@app.get("/demo/pitch")
def demo_pitch() -> dict[str, Any]:
    return agent.pitch_packet()


@app.get("/agent/status")
async def agent_status() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/agent/status")
    return {
        "always_on": monitor_state,
        "tasks": store.tasks,
        "audit_runs": store.audit_runs[-5:],
        "mesh": events.agent_status(),
    }


@app.get("/agents/status")
async def agents_status() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/agents/status")
    return events.agent_status()


@app.get("/personal-agents")
async def personal_agents_index() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/personal-agents")
    return personal_agents.list_personal_agents()


@app.get("/personal-agents/{user_id}")
async def personal_agent_detail(user_id: str) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", f"/personal-agents/{user_id}")
    agent_config = personal_agents.get_personal_agent(user_id)
    if agent_config is None:
        raise HTTPException(status_code=404, detail="personal agent not found")
    return agent_config


@app.post("/personal-agents/provision")
async def personal_agent_provision(request: PersonalAgentProvisionRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/personal-agents/provision", body(request))
    try:
        result = personal_agents.provision_personal_agent(user_id=request.user_id, actor=request.actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    events.record_personal_agent_provision(result)
    return result


@app.post("/personal-agents/{user_id}/heartbeat")
async def personal_agent_heartbeat(user_id: str) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", f"/personal-agents/{user_id}/heartbeat")
    try:
        result = personal_agents.heartbeat(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    events.record_personal_agent_heartbeat(result)
    return result


@app.get("/agents/events")
async def agents_events() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/agents/events")
    return {"events": events.agent_status()["events"]}


@app.get("/events/stream")
async def events_stream() -> StreamingResponse:
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/observability/summary")
async def observability_summary() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/observability/summary")
    return events.observability_summary()


@app.get("/ingestion/status")
async def ingestion_status() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/ingestion/status")
    result = ingest.ingest_sample_corpus()
    return {key: value for key, value in result.items() if key != "chunks"}


@app.post("/ingestion/run")
async def ingestion_run() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/ingestion/run", timeout=120)
    result = ingest.ingest_sample_corpus()
    memory_chunks = ingest.chunks_for_memory(result)
    store.replace_chunks(memory_chunks)
    vector_seed = await vector_memory.seed()
    result["memory_chunks"] = len(memory_chunks)
    result["vector_seed"] = vector_seed
    events.record_ingestion(result)
    return result


@app.get("/identity/users")
async def identity_users() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/identity/users")
    return {"users": identity.list_users(), "role_map": identity.GROUP_ROLE_MAP}


@app.get("/identity/directory")
async def identity_directory() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/identity/directory")
    return identity.directory_status()


@app.post("/identity/sync")
async def identity_sync(request: DirectorySyncRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/identity/sync", body(request))
    result = identity.sync_directory(actor=request.actor)
    events.record_identity_sync(result)
    return result


@app.post("/identity/group-role-map")
async def identity_group_role_map(request: GroupRoleMappingRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/identity/group-role-map", body(request))
    try:
        result = identity.update_group_role(group_dn=request.group, role=request.role, actor=request.actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    events.record_role_mapping(result)
    return result


@app.get("/identity/access-preview/{user_id}")
async def identity_access_preview(user_id: str, external: bool = True) -> dict[str, Any]:
    if runtime.configured():
        suffix = "true" if external else "false"
        return await proxy_runtime("GET", f"/identity/access-preview/{user_id}?external={suffix}")
    return identity.access_preview(user_id=user_id, external=external)


@app.get("/onboarding/flow")
def onboarding_flow() -> dict[str, Any]:
    return onboarding.onboarding_status()


@app.get("/graph")
async def graph() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/graph")
    return store.graph()


@app.get("/tasks")
async def tasks() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/tasks")
    return {"tasks": store.tasks}


@app.get("/approvals")
async def approvals() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/approvals")
    return {"approvals": store.approvals}


@app.post("/approvals/{approval_id}/decision")
async def decide_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", f"/approvals/{approval_id}/decision", body(request))
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
async def audit() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/audit")
    return {"audit_runs": store.audit_runs}


@app.post("/tools/get_context")
async def get_context(request: GoalRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/tools/get_context", body(request), timeout=120)
    await ensure_demo_memory()
    return retrieval.get_context(goal=request.goal, role=request.role, user_id=request.user_id, external=True)


@app.post("/context/query")
async def context_query(request: ContextQueryRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/context/query", body(request), timeout=120)
    await ensure_demo_memory()
    return await retrieval.query_context_core(
        question=request.question,
        org_id=request.org_id,
        skill=request.skill,
        role=request.role,
        user_id=request.user_id,
        external=request.external,
        limit=request.limit,
    )


@app.get("/context/eval")
async def context_eval() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("GET", "/context/eval", timeout=120)
    await ensure_demo_memory()
    return await retrieval.evaluate_context_core()


@app.post("/tools/prepare_report")
async def prepare_report() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/tools/prepare_report")
    return agent.prepare_report()


@app.post("/tools/policy_check")
async def policy_check(request: PolicyRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/tools/policy_check", body(request))
    return policy.evaluate_output(
        text=request.text,
        citations=request.citations,
        external=request.external,
    )


@app.post("/tools/create_tasks")
async def create_tasks() -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/tools/create_tasks")
    return {"tasks": agent.create_tasks()}


@app.post("/tools/vector_search")
async def vector_search(request: VectorSearchRequest) -> dict[str, Any]:
    if runtime.configured():
        return await proxy_runtime("POST", "/tools/vector_search", body(request), timeout=120)
    await ensure_demo_memory()
    return await vector_memory.search(query=request.query, limit=request.limit)
