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
    if health["qdrant"]["available"]:
        assert_true(vector_seed["available"] is True, "qdrant seed is available")
        assert_true(vector_seed["points"] == 5, "qdrant has five demo memory points")

    run = request(
        "/agent/run",
        {"goal": "get us ready for the anderson foundation report", "role": "grant_manager"},
    )
    packet = run["context_packet"]
    assert_true(packet["skill_label"] == "Nonprofit Grants", "nonprofit grants skill activated")
    assert_true(packet["user"]["id"] == "morgan", "context packet records user identity")
    assert_true(packet["role"] == "grant_manager", "context packet records role")
    assert_true(packet["readiness_score"] == 72, "readiness score is 72")
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
    if search["available"]:
        hit_ids = [hit["chunk_id"] for hit in search["hits"]]
        assert_true("grant-req-1" in hit_ids, "vector search finds grant requirements")

    mesh = request("/agents/status")
    agent_ids = {agent["id"] for agent in mesh["agents"]}
    assert_true("index-agent" in agent_ids, "index agent is registered")
    assert_true("policy-agent" in agent_ids, "policy agent is registered")
    assert_true("grant-readiness-agent" in agent_ids, "grant workflow agent is registered")
    assert_true(len(mesh["events"]) >= 1, "agent stream has events")

    pitch = request("/demo/pitch")
    assert_true("local_first_always_on" in pitch["rubric_mapping"], "pitch maps local-first rubric")
    assert_true(pitch["demo_result"]["readiness_score"] == 72, "pitch packet matches demo readiness")

    print("[ok] fuze demo verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
