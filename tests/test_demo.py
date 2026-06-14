from fastapi.testclient import TestClient

from api.main import app, sse_frame


client = TestClient(app)


def test_agent_run_produces_hackathon_demo_packet():
    client.post("/demo/seed")
    response = client.post(
        "/agent/run",
        json={"goal": "get us ready for the anderson foundation report", "role": "grant_manager"},
    )

    assert response.status_code == 200
    data = response.json()

    packet = data["context_packet"]
    assert packet["skill_label"] == "Nonprofit Grants"
    assert packet["readiness_score"] == 72
    assert packet["graph_path"] == [
        "Anderson Foundation",
        "Grant Agreement",
        "Reporting Requirements",
        "Program Metrics",
        "Missing Volunteer Hours",
        "Jordan",
    ]
    assert len(data["tasks"]) == 3
    assert len(data["approvals"]) == 2
    assert "may volunteer hours" in packet["missing_info"][0]["label"]
    assert packet["blocked_context"]
    assert data["audit"]["model_runtime"]["cloud_calls"] == 0


def test_health_reports_local_runtime_surfaces():
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["cloud_llm_calls"] == 0
    assert "ollama" in data
    assert "qdrant" in data
    assert data["identity"]["provider"] == "demo-adapter"
    assert data["always_on"]["enabled"] is True


def test_demo_seed_reports_vector_memory_status():
    response = client.post("/demo/seed")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "seeded"
    assert "vector_seed" in data
    assert "embedding_source" in data["vector_seed"]


def test_vector_search_endpoint_has_safe_fallback_shape():
    response = client.post(
        "/tools/vector_search",
        json={"query": "anderson foundation volunteer hours", "limit": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["collection"] == "fuze_context"
    assert "hits" in data
    assert "embedding_source" in data


def test_pitch_packet_maps_to_judging_rubric():
    response = client.get("/demo/pitch")

    assert response.status_code == 200
    data = response.json()
    assert "local_first_always_on" in data["rubric_mapping"]
    assert data["demo_result"]["readiness_score"] == 72
    assert "cloud llm calls at 0" in " ".join(data["technical_proof"])


def test_policy_blocks_raw_external_pii():
    response = client.post(
        "/tools/policy_check",
        json={
            "text": "client maya age 15 lives at 44 cedar ave",
            "citations": ["case_notes.txt#maya"],
            "external": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["checks"][0]["status"] == "fail"
    assert "[redacted]" in data["redacted_text"]


def test_identity_users_expose_group_role_mapping():
    response = client.get("/identity/users")

    assert response.status_code == 200
    data = response.json()
    roles = {user["id"]: user["role"] for user in data["users"]}
    assert roles["morgan"] == "grant_manager"
    assert roles["casey"] == "case_manager"
    assert data["role_map"]["cn=grant-team"] == "grant_manager"


def test_context_packet_records_identity_and_role():
    response = client.post(
        "/tools/get_context",
        json={"goal": "get us ready for the anderson foundation report", "user_id": "morgan", "role": "grant_manager"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == "morgan"
    assert data["role"] == "grant_manager"
    assert data["groups"] == ["cn=grant-team"]
    assert any(item["id"] == "case-1" for item in data["blocked_context"])


def test_case_manager_can_use_restricted_context_internally():
    response = client.post(
        "/tools/get_context",
        json={"goal": "review case note internally", "user_id": "casey", "role": "case_manager"},
    )

    assert response.status_code == 200
    data = response.json()
    blocked_ids = {item["id"] for item in data["blocked_context"]}
    assert "case-1" in blocked_ids

    from api import retrieval

    internal = retrieval.get_context(
        goal="review case note internally",
        user_id="casey",
        role="case_manager",
        external=False,
    )
    allowed_ids = {item["id"] for item in internal["allowed_context"]}
    assert "case-1" in allowed_ids


def test_agent_mesh_status_and_events():
    client.post(
        "/agent/run",
        json={"goal": "get us ready for the anderson foundation report", "user_id": "morgan", "role": "grant_manager"},
    )
    response = client.get("/agents/status")

    assert response.status_code == 200
    data = response.json()
    agent_ids = {agent["id"] for agent in data["agents"]}
    assert "index-agent" in agent_ids
    assert "policy-agent" in agent_ids
    assert "grant-readiness-agent" in agent_ids
    assert data["events"]
    assert data["transport"] == "local in-process a2a-style messages"


def test_observability_summary_and_sse_stream_shape():
    client.post(
        "/agent/run",
        json={"goal": "get us ready for the anderson foundation report", "user_id": "morgan", "role": "grant_manager"},
    )

    summary = client.get("/observability/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["sse"]["endpoint"] == "/events/stream"
    assert data["sse"]["transport"] == "text/event-stream"
    assert data["events_buffered"] >= 1
    assert "agent-health" in {dashboard["id"] for dashboard in data["dashboards"]}

    frame = sse_frame("agent_event", {"ok": True}, "evt-test")
    assert frame.startswith("id: evt-test\nevent: agent_event\ndata:")
    assert frame.endswith("\n\n")


def test_onboarding_flow_covers_identity_docs_and_agents():
    response = client.get("/onboarding/flow")

    assert response.status_code == 200
    data = response.json()
    step_ids = {step["id"] for step in data["flow"]}
    assert {"identity", "role-map", "connect-docs", "ingest", "activate-agents"}.issubset(step_ids)
    assert "scim 2.0" in data["identity_management"]["provisioning"]
    assert "microsoft graph delta queries" in data["identity_management"]["directory_sync"]
    assert "graph webhooks/change notifications" in data["doc_ingestion"]["change_detection"]


def test_approval_queue_created_and_decision_is_auditable():
    client.post("/demo/seed")
    run = client.post(
        "/agent/run",
        json={"goal": "get us ready for the anderson foundation report", "user_id": "morgan", "role": "grant_manager"},
    )

    assert run.status_code == 200
    assert [approval["status"] for approval in run.json()["approvals"]] == ["pending", "pending"]

    queue = client.get("/approvals")
    assert queue.status_code == 200
    approvals = {approval["id"]: approval for approval in queue.json()["approvals"]}
    assert approvals["approval-external-report-export"]["owner_role"] == "executive_director"
    assert approvals["approval-third-anonymized-story"]["risk"] == "sensitive_story"

    decision = client.post(
        "/approvals/approval-external-report-export/decision",
        json={"status": "approved", "actor": "alex", "note": "reviewed for venue demo"},
    )

    assert decision.status_code == 200
    approval = decision.json()["approval"]
    assert approval["status"] == "approved"
    assert approval["decided_by"] == "alex"
    assert approval["decision_note"] == "reviewed for venue demo"

    mesh = client.get("/agents/status").json()
    assert any(event["type"] == "approval_decision" for event in mesh["events"])
