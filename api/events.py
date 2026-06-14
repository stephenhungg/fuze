"""lightweight local event stream for the demo agent mesh."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any


AGENTS = [
    {
        "id": "index-agent",
        "label": "Index Agent",
        "kind": "memory",
        "status": "watching",
        "description": "watches local docs and keeps qdrant plus graph memory fresh.",
    },
    {
        "id": "graph-memory-agent",
        "label": "Graph Memory Agent",
        "kind": "memory",
        "status": "ready",
        "description": "maintains funders, grants, programs, tasks, people, citations, and edges.",
    },
    {
        "id": "policy-agent",
        "label": "Policy Agent",
        "kind": "governance",
        "status": "ready",
        "description": "filters role-aware context and blocks pii from external output.",
    },
    {
        "id": "grant-readiness-agent",
        "label": "Grant Readiness Agent",
        "kind": "workflow",
        "status": "running",
        "description": "prepares readiness packets, tasks, report sections, and follow-ups.",
    },
    {
        "id": "approval-agent",
        "label": "Approval Agent",
        "kind": "governance",
        "status": "waiting",
        "description": "holds external report export until human approval.",
    },
    {
        "id": "audit-agent",
        "label": "Audit Agent",
        "kind": "audit",
        "status": "recording",
        "description": "records model runtime, context, blocked evidence, actions, and approvals.",
    },
]

EVENTS: deque[dict[str, Any]] = deque(maxlen=80)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(agent_id: str, event_type: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    event = {
        "id": f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": now(),
        "agent_id": agent_id,
        "type": event_type,
        "message": message,
        "payload": payload or {},
    }
    EVENTS.appendleft(event)
    return event


def bootstrap() -> None:
    if EVENTS:
        return
    emit("index-agent", "watch", "watching grant docs, metrics, volunteer exports, and case notes")
    emit("graph-memory-agent", "ready", "graph memory loaded anderson foundation path")
    emit("policy-agent", "ready", "role and external-output policies loaded")
    emit("grant-readiness-agent", "ready", "grant readiness workflow armed")
    emit("audit-agent", "ready", "audit stream recording locally")


def agent_status() -> dict[str, Any]:
    bootstrap()
    return {
        "agents": AGENTS,
        "events": list(EVENTS)[:12],
        "event_count": len(EVENTS),
        "transport": "local in-process a2a-style messages",
    }


def record_run(result: dict[str, Any], trigger: str) -> None:
    packet = result["context_packet"]
    audit = result["audit"]
    emit(
        "index-agent",
        "context",
        f"served context packet for {packet['user']['name']} as {packet['role']}",
        {"allowed": len(packet["allowed_context"]), "blocked": len(packet["blocked_context"])},
    )
    emit(
        "policy-agent",
        "policy",
        f"blocked {len(packet['blocked_context'])} context item(s) before external output",
        {"blocked": audit["context_blocked"]},
    )
    emit(
        "grant-readiness-agent",
        "workflow",
        f"readiness {packet['readiness_score']}% with {len(result['tasks'])} task(s)",
        {"trigger": trigger, "tasks": [task["id"] for task in result["tasks"]]},
    )
    emit(
        "approval-agent",
        "approval",
        f"{len(result['approvals'])} approval gate(s) queued",
        {"approval_ids": [approval["id"] for approval in result["approvals"]]},
    )
    emit(
        "audit-agent",
        "audit",
        f"recorded {audit['id']} with cloud calls {audit['model_runtime']['cloud_calls']}",
        {"audit_id": audit["id"]},
    )


def record_approval_decision(approval: dict[str, Any]) -> None:
    emit(
        "approval-agent",
        "approval_decision",
        f"{approval['title']} {approval['status']} by {approval['decided_by']}",
        {
            "approval_id": approval["id"],
            "status": approval["status"],
            "decided_by": approval["decided_by"],
        },
    )
    emit(
        "audit-agent",
        "audit",
        f"recorded approval decision for {approval['id']}",
        {"approval_id": approval["id"], "status": approval["status"]},
    )
