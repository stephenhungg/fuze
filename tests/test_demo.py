from fastapi.testclient import TestClient

from api.main import app


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
