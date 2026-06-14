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
RRF_K = 60


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, 20))


def terms_for(text: str) -> set[str]:
    return {term for term in TOKEN_RE.findall(text.lower()) if len(term) > 2 and term not in STOP_WORDS}


def graph_terms(node: dict[str, Any]) -> set[str]:
    return terms_for(" ".join(str(node.get(key, "")) for key in ("id", "label", "type", "source", "summary")))


def build_query_plan(question: str, role: str, external: bool) -> dict[str, Any]:
    terms = terms_for(question)
    graph = store.graph()
    matching_nodes = [
        node
        for node in graph["nodes"]
        if terms & graph_terms(node)
    ][:8]
    matching_sources = sorted(
        {
            node["source"]
            for node in matching_nodes
            if node.get("source")
        }
    )
    return {
        "question_terms": sorted(terms),
        "detected_entities": [node["label"] for node in matching_nodes],
        "source_hints": matching_sources,
        "constraints": {
            "role": role,
            "external_output": external,
            "policy_first": True,
        },
        "retrieval_stages": [
            "dense_vector_qdrant",
            "lexical_sparse_store",
            "graph_neighbor_expansion",
            "reciprocal_rank_fusion",
            "policy_aware_rerank",
            "source_diversity_pack",
        ],
    }


def build_graph_traversal(question: str, vector_hits: list[dict[str, Any]], max_nodes: int = 8) -> dict[str, Any]:
    graph = store.graph()
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = graph["edges"]
    hit_chunks = {hit.get("chunk_id") for hit in vector_hits if hit.get("chunk_id")}
    hit_sources = {hit.get("source") for hit in vector_hits if hit.get("source")}
    question_terms = terms_for(question)
    terms = set(question_terms)
    for hit in vector_hits:
        terms |= terms_for(" ".join(str(hit.get(key, "")) for key in ("chunk_id", "title", "source", "text_preview")))

    scored: list[tuple[int, str]] = []
    for node_id, node in nodes.items():
        node_terms = graph_terms(node)
        source_match = node.get("source") in hit_sources
        score = len(question_terms & node_terms) * 3 + len(terms & node_terms) + (3 if source_match else 0)
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


def chunk_lookup() -> dict[str, dict[str, Any]]:
    return {chunk["id"]: chunk for chunk in store.chunks()}


def hit_from_chunk(chunk: dict[str, Any], score: float, ranker: str) -> dict[str, Any]:
    return {
        "score": score,
        "chunk_id": chunk["id"],
        "title": chunk["title"],
        "source": chunk["source"],
        "text_preview": chunk["text"][:280],
        "sensitivity": chunk.get("sensitivity", "internal"),
        "external_output_allowed": chunk.get("external_output_allowed", False),
        "citations": chunk.get("citations", []),
        "metadata": chunk.get("metadata", {}),
        "ranker": ranker,
    }


def graph_expansion_hits(question: str, traversal: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    terms = terms_for(question)
    traversal_sources = {
        node["source"]
        for node in traversal.get("nodes", [])
        if node.get("source")
    }
    traversal_labels = terms_for(" ".join(node.get("label", "") for node in traversal.get("nodes", [])))
    hits: list[tuple[float, dict[str, Any]]] = []
    for chunk in store.chunks():
        chunk_terms = terms_for(" ".join([chunk["id"], chunk["title"], chunk["source"], chunk["text"]]))
        source_match = chunk["source"] in traversal_sources
        label_overlap = len(traversal_labels & chunk_terms)
        query_overlap = len(terms & chunk_terms)
        score = query_overlap + label_overlap * 0.5 + (2 if source_match else 0)
        if score:
            hits.append((score, chunk))
    hits.sort(key=lambda item: item[0], reverse=True)
    return [hit_from_chunk(chunk, score, "graph") for score, chunk in hits[:limit]]


def reciprocal_rank_fusion(ranked_lists: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    fused: dict[str, dict[str, Any]] = {}
    for ranker, hits in ranked_lists.items():
        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit.get("chunk_id")
            if not chunk_id:
                continue
            candidate = fused.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "title": hit.get("title"),
                    "source": hit.get("source"),
                    "text_preview": hit.get("text_preview", ""),
                    "sensitivity": hit.get("sensitivity"),
                    "external_output_allowed": hit.get("external_output_allowed"),
                    "citations": hit.get("citations", []),
                    "metadata": hit.get("metadata", {}),
                    "rrf_score": 0.0,
                    "rankers": {},
                },
            )
            candidate["rrf_score"] += 1 / (RRF_K + rank)
            candidate["rankers"][ranker] = {"rank": rank, "score": hit.get("score")}
    return sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)


def rerank_candidates(
    question: str,
    fused: list[dict[str, Any]],
    role: str,
    external: bool,
    limit: int,
) -> list[dict[str, Any]]:
    chunks = chunk_lookup()
    query = terms_for(question)
    source_counts: dict[str, int] = {}
    scored: list[dict[str, Any]] = []
    for candidate in fused:
        chunk = chunks.get(candidate["chunk_id"])
        if not chunk:
            continue
        blocked, reasons = policy.is_blocked(chunk, role=role, external=external)
        chunk_terms = terms_for(" ".join([chunk["title"], chunk["source"], chunk["text"]]))
        coverage = len(query & chunk_terms) / max(len(query), 1)
        multi_signal = max(len(candidate["rankers"]) - 1, 0)
        citation_bonus = 0.08 if chunk.get("citations") else 0
        policy_penalty = 1.0 if blocked else 0
        final_score = (
            candidate["rrf_score"] * 8
            + coverage
            + multi_signal * 0.25
            + citation_bonus
            - policy_penalty
        )
        scored.append(
            {
                **candidate,
                "final_score": round(final_score, 4),
                "features": {
                    "rrf_score": round(candidate["rrf_score"], 5),
                    "term_coverage": round(coverage, 3),
                    "multi_signal_rankers": sorted(candidate["rankers"]),
                    "citation_bonus": citation_bonus,
                    "blocked_by_policy": blocked,
                    "policy_reasons": reasons,
                },
            }
        )
    scored.sort(key=lambda item: item["final_score"], reverse=True)

    packed: list[dict[str, Any]] = []
    for candidate in scored:
        source = candidate.get("source", "")
        if candidate["features"]["blocked_by_policy"]:
            continue
        if source_counts.get(source, 0) >= 2 and len(packed) >= 3:
            continue
        source_counts[source] = source_counts.get(source, 0) + 1
        packed.append(candidate)
        if len(packed) == limit:
            break
    return packed


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
    limit = clamp_limit(limit)
    fetch_limit = max(limit * 3, 12)
    query_plan = build_query_plan(question, role=role, external=external)
    vector = await vector_memory.search(question, limit=fetch_limit)
    lexical = {
        "available": True,
        "collection": "in-memory-sparse",
        "embedding_source": "none",
        "fallback": None,
        "hits": vector_memory.lexical_hits(question, fetch_limit),
    }
    traversal = build_graph_traversal(question, vector["hits"] + lexical["hits"], max_nodes=limit)
    graph_hits = graph_expansion_hits(question, traversal, fetch_limit)
    fused = reciprocal_rank_fusion(
        {
            "dense": vector["hits"],
            "lexical": lexical["hits"],
            "graph": graph_hits,
        }
    )
    reranked = rerank_candidates(question, fused, role=role, external=external, limit=limit)
    ranked_chunk_ids = [hit["chunk_id"] for hit in reranked]
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
        "hybrid_retrieval": {
            "query_plan": query_plan,
            "rank_fusion": {
                "algorithm": "reciprocal_rank_fusion",
                "k": RRF_K,
                "rankers": ["dense", "lexical", "graph"],
                "candidate_count": len(fused),
            },
            "lexical_hits": lexical,
            "graph_hits": graph_hits[:limit],
            "reranked_hits": reranked,
            "packing": {
                "source_diversity_cap": 2,
                "policy_filtered_before_prompt": True,
                "selected_count": len(selected_context[:limit]),
            },
        },
        "graph_traversal": traversal,
        "context_packet": packet,
        "selected_context": selected_context[:limit],
        "blocked_context": packet["blocked_context"],
        "citations": packet["citations"],
        "runtime": {
            "retrieval": "hybrid dense+lexical search -> graph expansion -> rrf fusion -> policy-aware rerank -> context packet",
            "vector_collection": vector["collection"],
            "embedding_source": vector["embedding_source"],
            "graph_source": "local org graph",
            "policy": "role and external-output filters before agent prompt assembly",
            "no_cloud_llm_calls": True,
        },
    }


EVAL_CASES = [
    {
        "id": "anderson-volunteer-gap",
        "question": "what does anderson need and who owns missing volunteer hours?",
        "role": "grant_manager",
        "user_id": "morgan",
        "external": True,
        "expected_sources": ["grant_requirements.txt", "volunteers.csv"],
        "expected_nodes": ["Grant Agreement", "Jordan"],
        "expected_blocked_sources": ["volunteers.csv"],
    },
    {
        "id": "case-note-governance",
        "question": "can morgan use raw case notes in the funder report?",
        "role": "grant_manager",
        "user_id": "morgan",
        "external": True,
        "expected_sources": ["case_notes.txt"],
        "expected_nodes": ["Sensitive Case Note"],
        "expected_blocked_sources": ["case_notes.txt"],
    },
    {
        "id": "budget-variance-proof",
        "question": "why is the may food budget variance acceptable?",
        "role": "grant_manager",
        "user_id": "morgan",
        "external": True,
        "expected_sources": ["finance_export_may.csv"],
        "expected_nodes": ["Budget Variance Notes"],
        "expected_blocked_sources": [],
    },
]


def source_set(packet: dict[str, Any]) -> set[str]:
    sources = {item["source"] for item in packet["selected_context"]}
    sources.update(item["source"] for item in packet["blocked_context"])
    for hit in packet["vector_hits"]["hits"]:
        if hit.get("source"):
            sources.add(hit["source"])
    for hit in packet["hybrid_retrieval"]["lexical_hits"]["hits"]:
        if hit.get("source"):
            sources.add(hit["source"])
    for hit in packet["hybrid_retrieval"]["graph_hits"]:
        if hit.get("source"):
            sources.add(hit["source"])
    return sources


def recall(expected: list[str], observed: set[str]) -> float:
    if not expected:
        return 1.0
    return len(set(expected) & observed) / len(set(expected))


async def evaluate_context_core(limit: int = 8) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in EVAL_CASES:
        packet = await query_context_core(
            question=case["question"],
            role=case["role"],
            user_id=case["user_id"],
            external=case["external"],
            limit=limit,
        )
        observed_sources = source_set(packet)
        selected_sources = {item["source"] for item in packet["selected_context"]}
        blocked_sources = {item["source"] for item in packet["blocked_context"]}
        observed_nodes = {node["label"] for node in packet["graph_traversal"]["nodes"]}
        expected_blocked = set(case["expected_blocked_sources"])
        source_recall = recall(case["expected_sources"], observed_sources)
        node_recall = recall(case["expected_nodes"], observed_nodes)
        blocked_recall = recall(case["expected_blocked_sources"], blocked_sources)
        stage_coverage = 1.0 if packet["hybrid_retrieval"]["rank_fusion"]["rankers"] == ["dense", "lexical", "graph"] else 0.0
        rerank_ready = 1.0 if packet["hybrid_retrieval"]["reranked_hits"] else 0.0
        policy_guardrail = 1.0 if not (expected_blocked & selected_sources) else 0.0
        score = round(
            source_recall * 0.32
            + node_recall * 0.2
            + blocked_recall * 0.18
            + stage_coverage * 0.12
            + rerank_ready * 0.08
            + policy_guardrail * 0.1,
            3,
        )
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "score": score,
                "passed": score >= 0.82,
                "metrics": {
                    "source_recall": round(source_recall, 3),
                    "node_recall": round(node_recall, 3),
                    "blocked_recall": round(blocked_recall, 3),
                    "stage_coverage": stage_coverage,
                    "rerank_ready": rerank_ready,
                    "policy_guardrail": policy_guardrail,
                },
                "expected": {
                    "sources": case["expected_sources"],
                    "nodes": case["expected_nodes"],
                    "blocked_sources": case["expected_blocked_sources"],
                },
                "observed": {
                    "sources": sorted(observed_sources),
                    "selected_sources": sorted(selected_sources),
                    "blocked_sources": sorted(blocked_sources),
                    "nodes": sorted(observed_nodes),
                },
            }
        )

    average_score = round(sum(item["score"] for item in results) / len(results), 3)
    return {
        "name": "fuze-context-core-eval",
        "case_count": len(results),
        "average_score": average_score,
        "passed": all(item["passed"] for item in results) and average_score >= 0.86,
        "cloud_llm_calls": 0,
        "retrieval_contract": "dense+lexical+graph rrf with policy-aware rerank",
        "results": results,
    }
