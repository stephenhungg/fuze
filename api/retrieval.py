"""context packet retrieval boundary."""

from __future__ import annotations

from typing import Any

from . import identity, policy
from .db import DEMO_GOAL, store


GRAPH_PATH = [
    "Anderson Foundation",
    "Grant Agreement",
    "Reporting Requirements",
    "Program Metrics",
    "Missing Volunteer Hours",
    "Jordan",
]


def get_context(
    goal: str = DEMO_GOAL,
    org_id: str = "harbor-light-nonprofit",
    skill: str = "nonprofit_grants",
    role: str = "grant_manager",
    user_id: str | None = None,
    external: bool = True,
) -> dict[str, Any]:
    user = identity.get_user(user_id)
    role = role or user["role"]
    allowed_context: list[dict[str, Any]] = []
    blocked_context: list[dict[str, Any]] = []
    citations: list[str] = []

    for chunk in store.chunks():
        blocked, reasons = policy.is_blocked(chunk, role=role, external=external)
        item = {
            "id": chunk["id"],
            "title": chunk["title"],
            "source": chunk["source"],
            "text": chunk["text"],
            "citations": chunk.get("citations", []),
            "sensitivity": chunk.get("sensitivity", "internal"),
        }
        if blocked:
            blocked_context.append({**item, "reasons": reasons, "redacted_preview": policy.redact(chunk["text"])})
        else:
            allowed_context.append(item)
            citations.extend(chunk.get("citations", []))

    missing_info = [
        {
            "id": "missing-may-volunteer-hours",
            "label": "may volunteer hours",
            "owner": "Jordan",
            "impact": "required by the Anderson Foundation report.",
        },
        {
            "id": "missing-approved-story",
            "label": "one approved anonymized story",
            "owner": "program lead",
            "impact": "needed for narrative section; raw case note is blocked.",
        },
    ]

    recommended_actions = [
        "ask Jordan for May volunteer hours",
        "ask Sarah to confirm attendance data",
        "approve third anonymized story",
        "prepare report outline for human approval",
    ]

    packet = {
        "goal": goal,
        "org_id": org_id,
        "skill": skill,
        "skill_label": "Nonprofit Grants",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "title": user["title"],
        },
        "role": role,
        "groups": user["groups"],
        "graph_path": GRAPH_PATH,
        "relevant_nodes": store.graph()["nodes"],
        "evidence": allowed_context,
        "citations": sorted(set(citations)),
        "missing_info": missing_info,
        "allowed_context": allowed_context,
        "blocked_context": blocked_context,
        "readiness_score": 72,
        "confidence": "high",
        "recommended_actions": recommended_actions,
        "constraints": {
            "identity_provider": "demo-adapter",
            "role": role,
            "groups": user["groups"],
            "external_output": external,
            "no_cloud_llm_calls": True,
        },
        "memory_runtime": {
            "vector_index": "qdrant",
            "embedding_model": "nomic-embed-text",
            "collection": "fuze_context",
            "fallback": "deterministic in-memory context packet",
        },
    }
    store.last_context = packet
    return packet
