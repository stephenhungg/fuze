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
