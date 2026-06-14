#!/usr/bin/env python3
"""verify the fuze demo is ready from the outside of the api."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def request(path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} failed: {exc.code} {body}") from exc


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[ok] {message}")


def main() -> int:
    print(f"[info] verifying {BASE_URL}")

    health = request("/health")
    assert_true(health["ok"] is True, "api health ok")
    assert_true(health["cloud_llm_calls"] == 0, "cloud llm calls are zero")
    assert_true(health["always_on"]["enabled"] is True, "always-on monitor enabled")
    assert_true(health["identity"]["provider"] == "demo-adapter", "identity adapter is active")

    users = request("/identity/users")
    roles = {user["id"]: user["role"] for user in users["users"]}
    assert_true(roles["morgan"] == "grant_manager", "grant manager maps from group")
    assert_true(roles["casey"] == "case_manager", "case manager maps from group")

    seed = request("/demo/seed", {})
    vector_seed = seed["vector_seed"]
    assert_true(seed["status"] == "seeded", "demo seed endpoint works")
    assert_true(vector_seed["collection"] == "fuze_context", "qdrant collection is fuze_context")

    ingestion = request("/ingestion/run", {})
    assert_true(ingestion["files_seen"] == 13, "sample ingestion sees thirteen files")
    assert_true(ingestion["chunks_created"] > ingestion["files_seen"], "sample ingestion creates document chunks")
    assert_true(ingestion["memory_chunks"] == ingestion["chunks_created"], "ingested chunks become memory chunks")
    assert_true(ingestion["pii_chunks"] >= 2, "sample ingestion flags pii chunks")
    assert_true("case_notes.txt" in ingestion["restricted_files"], "sample ingestion tracks restricted case notes")
    if health["qdrant"]["available"]:
        assert_true(ingestion["vector_seed"]["available"] is True, "qdrant seed is available")
        assert_true(ingestion["vector_seed"]["points"] == ingestion["chunks_created"], "qdrant uses ingested chunks")

    run = request(
        "/agent/run",
        {"goal": "get us ready for the anderson foundation report", "role": "grant_manager"},
    )
    packet = run["context_packet"]
    assert_true(packet["skill_label"] == "Nonprofit Grants", "nonprofit grants skill activated")
    assert_true(packet["user"]["id"] == "morgan", "context packet records user identity")
    assert_true(packet["role"] == "grant_manager", "context packet records role")
    assert_true(packet["readiness_score"] == 72, "readiness score is 72")
    assert_true(packet["org_profile"]["name"] == "Harbor Light Community Services", "org profile is present")
    assert_true(len(packet["connectors"]) == 4, "connector profiles are present")
    assert_true(len(packet["staff_profiles"]) == 5, "staff profiles are present")
    assert_true(len(packet["funders"]) == 3, "funder profiles are present")
    assert_true(len(packet["metrics"]) == 4, "operating metrics are present")
    assert_true(
        any(item["metadata"].get("derived_from") == "sample_data/harbor_light" for item in packet["allowed_context"]),
        "context packet uses ingested source chunks",
    )
    assert_true(len(run["tasks"]) == 3, "three action tasks created")
    assert_true(len(run["approvals"]) == 2, "two approval gates created")
    assert_true(len(packet["blocked_context"]) >= 1, "sensitive context is blocked")
    assert_true(run["audit"]["model_runtime"]["cloud_calls"] == 0, "audit records zero cloud calls")
    assert_true("Jordan" in packet["graph_path"], "graph path reaches Jordan")

    approvals = request("/approvals")
    approval_ids = {approval["id"] for approval in approvals["approvals"]}
    assert_true("approval-external-report-export" in approval_ids, "external report approval gate is queued")
    assert_true("approval-third-anonymized-story" in approval_ids, "story approval gate is queued")

    search = request(
        "/tools/vector_search",
        {"query": "anderson foundation volunteer hours", "limit": 3},
    )
    assert_true(search["collection"] == "fuze_context", "vector search uses fuze_context")
    hit_sources = [hit["source"] for hit in search["hits"]]
    assert_true("grant_requirements.txt" in hit_sources, "vector search finds grant requirements")

    context_core = request(
        "/context/query",
        {
            "question": "what does anderson need and who owns missing volunteer hours?",
            "role": "grant_manager",
            "user_id": "morgan",
            "external": True,
            "limit": 6,
        },
    )
    assert_true(context_core["server"]["name"] == "fuze-context-core", "context core endpoint is active")
    assert_true(context_core["server"]["cloud_llm_calls"] == 0, "context core stays local")
    assert_true(context_core["vector_hits"]["hits"], "context core returns vector hits")
    assert_true(context_core["graph_traversal"]["nodes"], "context core traverses graph nodes")
    assert_true(context_core["selected_context"], "context core returns selected context")
    assert_true(context_core["runtime"]["no_cloud_llm_calls"] is True, "context core runtime records zero cloud calls")

    mesh = request("/agents/status")
    agent_ids = {agent["id"] for agent in mesh["agents"]}
    assert_true("index-agent" in agent_ids, "index agent is registered")
    assert_true("policy-agent" in agent_ids, "policy agent is registered")
    assert_true("grant-readiness-agent" in agent_ids, "grant workflow agent is registered")
    assert_true(len(mesh["events"]) >= 1, "agent stream has events")

    observability = request("/observability/summary")
    assert_true(observability["sse"]["endpoint"] == "/events/stream", "sse observability endpoint is advertised")
    assert_true(observability["events_buffered"] >= 1, "observability summary has buffered events")

    onboarding = request("/onboarding/flow")
    step_ids = {step["id"] for step in onboarding["flow"]}
    assert_true("identity" in step_ids, "onboarding covers identity connection")
    assert_true("connect-docs" in step_ids, "onboarding covers document ingestion setup")
    assert_true("activate-agents" in step_ids, "onboarding covers agent activation")

    pitch = request("/demo/pitch")
    assert_true("local_first_always_on" in pitch["rubric_mapping"], "pitch maps local-first rubric")
    assert_true(pitch["demo_result"]["readiness_score"] == 72, "pitch packet matches demo readiness")

    print("[ok] fuze demo verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
