"""context packet retrieval boundary."""

from __future__ import annotations

import re
from typing import Any

from . import identity, policy, vector_memory
from .db import DEMO_GOAL, store


GRAPH_PATH = [
    "Anderson Foundation",
    "Grant Agreement",
    "Reporting Requirements",
    "Program Metrics",
    "Missing Volunteer Hours",
    "Jordan",
]
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "about",
    "and",
    "are",
    "for",
    "from",
    "how",
    "into",
    "like",
    "the",
    "this",
    "to",
    "what",
    "with",
}


def terms_for(text: str) -> set[str]:
    return {term for term in TOKEN_RE.findall(text.lower()) if len(term) > 2 and term not in STOP_WORDS}


def graph_terms(node: dict[str, Any]) -> set[str]:
    return terms_for(" ".join(str(node.get(key, "")) for key in ("id", "label", "type", "source", "summary")))


def build_graph_traversal(question: str, vector_hits: list[dict[str, Any]], max_nodes: int = 8) -> dict[str, Any]:
    graph = store.graph()
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = graph["edges"]
    hit_chunks = {hit.get("chunk_id") for hit in vector_hits if hit.get("chunk_id")}
    hit_sources = {hit.get("source") for hit in vector_hits if hit.get("source")}
    terms = terms_for(question)
    for hit in vector_hits:
        terms |= terms_for(" ".join(str(hit.get(key, "")) for key in ("chunk_id", "title", "source", "text_preview")))

    scored: list[tuple[int, str]] = []
    for node_id, node in nodes.items():
        node_terms = graph_terms(node)
        source_match = node.get("source") in hit_sources
        score = len(terms & node_terms) + (3 if source_match else 0)
        if score:
            scored.append((score, node_id))
    scored.sort(key=lambda item: item[0], reverse=True)

    seed_ids = [node_id for _, node_id in scored[:3]]
    if not seed_ids:
        seed_ids = ["funder-anderson", "grant-anderson-2026", "doc-grant-agreement"]

    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for edge in edges:
        adjacency.setdefault(edge["source"], []).append((edge["target"], edge))
        adjacency.setdefault(edge["target"], []).append((edge["source"], edge))

    visited: list[str] = []
    selected_edges: list[dict[str, Any]] = []
    queue: list[tuple[str, int]] = [(node_id, 0) for node_id in seed_ids if node_id in nodes]
    seen: set[str] = set()
    while queue and len(visited) < max_nodes:
        node_id, depth = queue.pop(0)
        if node_id in seen:
            continue
        seen.add(node_id)
        visited.append(node_id)
        if depth >= 3:
            continue
        neighbors = sorted(
            adjacency.get(node_id, []),
            key=lambda item: len(terms & graph_terms(nodes.get(item[0], {}))),
            reverse=True,
        )
        for neighbor_id, edge in neighbors:
            if neighbor_id not in seen and len(visited) + len(queue) < max_nodes + 2:
                selected_edges.append(edge)
                queue.append((neighbor_id, depth + 1))

    visited_nodes = [nodes[node_id] for node_id in visited if node_id in nodes]
    return {
        "ephemeral_agent": "context-graph-walker",
        "query_terms": sorted(terms),
        "seed_chunk_ids": sorted(hit_chunks),
        "seed_sources": sorted(hit_sources),
        "seed_node_ids": seed_ids,
        "nodes": visited_nodes,
        "edges": selected_edges[: max_nodes - 1],
        "path": [node["label"] for node in visited_nodes] or GRAPH_PATH,
    }


def ranked_items(items: list[dict[str, Any]], ranked_chunk_ids: list[str]) -> list[dict[str, Any]]:
    rank = {chunk_id: index for index, chunk_id in enumerate(ranked_chunk_ids)}
    return sorted(items, key=lambda item: (rank.get(item["id"], len(rank) + 1), item["source"], item["id"]))


def get_context(
    goal: str = DEMO_GOAL,
    org_id: str = "harbor-light-nonprofit",
    skill: str = "nonprofit_grants",
    role: str = "grant_manager",
    user_id: str | None = None,
    external: bool = True,
    ranked_chunk_ids: list[str] | None = None,
    graph_traversal: dict[str, Any] | None = None,
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
            "metadata": chunk.get("metadata", {}),
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

    if ranked_chunk_ids:
        allowed_context = ranked_items(allowed_context, ranked_chunk_ids)
        blocked_context = ranked_items(blocked_context, ranked_chunk_ids)

    snapshot = store.snapshot()
    traversal = graph_traversal or {"path": GRAPH_PATH, "nodes": store.graph()["nodes"]}
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
        "org_profile": snapshot["org_profile"],
        "connectors": snapshot["connectors"],
        "staff_profiles": snapshot["staff_profiles"],
        "funders": snapshot["funders"],
        "programs": snapshot["programs"],
        "metrics": snapshot["metrics"],
        "graph_path": traversal.get("path", GRAPH_PATH),
        "relevant_nodes": traversal.get("nodes", store.graph()["nodes"]),
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
            "fallback": "deterministic lexical store when qdrant is unavailable",
            "context_core": "local mcp-style query server",
        },
    }
    store.last_context = packet
    return packet


async def query_context_core(
    question: str = DEMO_GOAL,
    org_id: str = "harbor-light-nonprofit",
    skill: str = "nonprofit_grants",
    role: str = "grant_manager",
    user_id: str | None = "morgan",
    external: bool = True,
    limit: int = 8,
) -> dict[str, Any]:
    limit = max(1, min(limit, 20))
    vector = await vector_memory.search(question, limit=limit)
    ranked_chunk_ids = [hit["chunk_id"] for hit in vector["hits"] if hit.get("chunk_id")]
    traversal = build_graph_traversal(question, vector["hits"], max_nodes=limit)
    packet = get_context(
        goal=question,
        org_id=org_id,
        skill=skill,
        role=role,
        user_id=user_id,
        external=external,
        ranked_chunk_ids=ranked_chunk_ids,
        graph_traversal=traversal,
    )
    selected_ids = set(ranked_chunk_ids)
    selected_context = [item for item in packet["allowed_context"] if item["id"] in selected_ids]
    if not selected_context:
        selected_context = packet["allowed_context"][:limit]

    return {
        "server": {
            "name": "fuze-context-core",
            "style": "local-mcp",
            "hosted_on": "dell-gb10",
            "cloud_llm_calls": 0,
        },
        "question": question,
        "identity": {
            "user": packet["user"],
            "role": packet["role"],
            "groups": packet["groups"],
            "external_output": external,
        },
        "vector_hits": vector,
        "graph_traversal": traversal,
        "context_packet": packet,
        "selected_context": selected_context[:limit],
        "blocked_context": packet["blocked_context"],
        "citations": packet["citations"],
        "runtime": {
            "retrieval": "embedding search -> ephemeral graph traversal -> policy-filtered context packet",
            "vector_collection": vector["collection"],
            "embedding_source": vector["embedding_source"],
            "graph_source": "local org graph",
            "policy": "role and external-output filters before agent prompt assembly",
            "no_cloud_llm_calls": True,
        },
    }
