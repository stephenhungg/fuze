import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app, sse_frame


client = TestClient(app)


def test_agent_run_produces_hackathon_demo_packet():
    client.post("/demo/seed")
    ingestion = client.post("/ingestion/run")
    assert ingestion.json()["memory_chunks"] == ingestion.json()["chunks_created"]
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
    assert packet["org_profile"]["name"] == "Harbor Light Community Services"
    assert len(packet["connectors"]) == 4
    assert len(packet["staff_profiles"]) == 5
    assert len(packet["funders"]) == 3
    assert len(packet["programs"]) == 3
    assert len(packet["metrics"]) == 4
    assert "- required:" in data["response"]
    assert "meals served" in data["response"]
    assert "approval" in data["response"]
    assert "may volunteer hours" in packet["missing_info"][0]["label"]
    assert any(item["metadata"].get("derived_from") == "sample_data/harbor_light" for item in packet["allowed_context"])
    assert any(item["source"] == "case_notes.txt" for item in packet["blocked_context"])
    assert packet["blocked_context"]
    assert data["audit"]["model_runtime"]["cloud_calls"] == 0


def test_health_reports_local_runtime_surfaces():
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["cloud_llm_calls"] == 0
    assert data["mode"] in {"hosted_preview", "local_runtime", "gb10_runtime", "gb10_runtime_unreachable"}
    assert data["runtime"]["gb10"]["execution"] in {"hosted_preview", "local_runtime", "gb10_runtime", "gb10_runtime_unreachable"}
    assert "ollama" in data
    assert "qdrant" in data
    assert data["identity"]["provider"] == "demo-adapter"
    assert data["always_on"]["enabled"] is True


def test_agent_audit_exposes_local_inference_probe_state():
    response = client.post(
        "/agent/run",
        json={"goal": "get us ready for the anderson foundation report", "role": "grant_manager"},
    )

    assert response.status_code == 200
    probe = response.json()["audit"]["model_runtime"]["local_inference"]
    assert probe["model"] == "qwen3:8b"
    assert "cloud_calls" not in probe or probe["cloud_calls"] == 0


def test_agent_chat_handles_greetings_and_vague_prompts_without_fake_readiness_answer():
    greeting = client.post("/agent/run", json={"goal": "Hi", "role": "grant_manager", "user_id": "morgan"})
    assert greeting.status_code == 200
    greeting_data = greeting.json()
    assert greeting_data["response_kind"] == "clarifying"
    assert "ask me something concrete" in greeting_data["response"]
    assert "72% ready" not in greeting_data["response"]

    vague = client.post("/agent/run", json={"goal": "What", "role": "grant_manager", "user_id": "morgan"})
    assert vague.status_code == 200
    vague_data = vague.json()
    assert vague_data["response_kind"] == "clarifying"
    assert "more direction" in vague_data["response"]
    assert "may volunteer hours" not in vague_data["response"]


def test_chat_endpoint_is_single_turn_chat_contract():
    response = client.post(
        "/chat",
        json={
            "message": "Hi",
            "role": "grant_manager",
            "user_id": "morgan",
            "thread_id": "thread-test",
            "history": [{"role": "assistant", "text": "hello"}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "thread-test"
    assert data["history_count"] == 1
    assert data["chat_runtime"]["backend"] == "/chat"
    assert data["response_kind"] == "clarifying"
    assert "ask me something concrete" in data["response"]

    report = client.post(
        "/chat",
        json={"message": "what do we need for the anderson report?", "role": "grant_manager", "user_id": "morgan"},
    )
    assert report.status_code == 200
    assert "- required:" in report.json()["response"]


def test_chat_endpoint_rewrites_followups_with_thread_history():
    first = client.post(
        "/chat",
        json={
            "message": "what do we need for the anderson report?",
            "role": "grant_manager",
            "user_id": "morgan",
            "thread_id": "thread-followup",
        },
    )
    assert first.status_code == 200

    followup = client.post(
        "/chat",
        json={
            "message": "what about approvals?",
            "role": "grant_manager",
            "user_id": "morgan",
            "thread_id": "thread-followup",
        },
    )

    assert followup.status_code == 200
    data = followup.json()
    assert data["history_used"] is True
    assert data["effective_goal"] == "what approvals are needed for the anderson report?"
    assert "executive director" in data["response"]
    assert "program lead" in data["response"]
    assert data["chat_runtime"]["mode"] == "history-aware chat turn"


def test_chat_endpoint_uses_client_history_for_followups():
    followup = client.post(
        "/chat",
        json={
            "message": "who owns that?",
            "role": "grant_manager",
            "user_id": "morgan",
            "thread_id": "thread-client-history",
            "history": [
                {"role": "user", "text": "what do we need for the anderson report?"},
                {"role": "assistant", "text": "for the anderson report, jordan owns the missing may volunteer hours."},
            ],
        },
    )

    assert followup.status_code == 200
    data = followup.json()
    assert data["effective_goal"] == "who owns the missing items for the anderson report?"
    assert "jordan" in data["response"]
    assert "sarah" in data["response"]


def test_chat_endpoint_answers_orientation_and_runtime_proof_questions():
    orientation = client.post(
        "/chat",
        json={"message": "whats going on", "role": "grant_manager", "user_id": "morgan"},
    )
    assert orientation.status_code == 200
    orientation_data = orientation.json()
    assert "here’s what’s going on" in orientation_data["response"]
    assert "local-first agent workspace" in orientation_data["response"]
    assert "i checked the local context core" not in orientation_data["response"]

    proof = client.post(
        "/chat",
        json={"message": "are we using llms here", "role": "grant_manager", "user_id": "morgan"},
    )
    assert proof.status_code == 200
    proof_data = proof.json()
    assert "api runtime" in proof_data["response"]
    assert "cloud llm calls: 0" in proof_data["response"]
    assert "i checked the local context core" not in proof_data["response"]


def test_system_runtime_is_honest_about_gb10_boundary():
    response = client.get("/system/runtime")

    assert response.status_code == 200
    data = response.json()
    assert data["cloud_llm_calls"] == 0
    assert data["security_boundary"]["raw_public_gb10_access"] is False
    assert data["security_boundary"]["requires_private_tunnel"] is True
    assert data["gb10"]["execution"] in {"hosted_preview", "local_runtime", "gb10_runtime", "gb10_runtime_unreachable"}
    if data["gb10"]["execution"] == "hosted_preview":
        assert data["local_execution"]["provider"] == "deterministic demo engine"


def test_configured_gb10_runtime_failures_do_not_fall_back_to_preview(monkeypatch):
    from api import runtime

    previous_url = runtime.GB10_RUNTIME_URL
    previous_token = runtime.GB10_RUNTIME_TOKEN
    runtime.GB10_RUNTIME_URL = "http://127.0.0.1:9"
    runtime.GB10_RUNTIME_TOKEN = "test-token"
    try:
        response = client.post(
            "/agent/run",
            json={"goal": "get us ready for the anderson foundation report", "role": "grant_manager"},
        )
    finally:
        runtime.GB10_RUNTIME_URL = previous_url
        runtime.GB10_RUNTIME_TOKEN = previous_token

    assert response.status_code == 502
    assert "gb10 runtime unreachable" in response.json()["detail"]


def test_static_seo_files_are_served_by_app():
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap: https://fuze.stephenhung.me/sitemap.xml" in robots.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "https://fuze.stephenhung.me/app" in sitemap.text


def test_demo_seed_reports_vector_memory_status():
    response = client.post("/demo/seed")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "seeded"
    assert "vector_seed" in data
    assert "embedding_source" in data["vector_seed"]
    assert len(data["snapshot"]["chunks"]) >= 13
    assert len(data["snapshot"]["connectors"]) == 4
    assert len(data["snapshot"]["staff_profiles"]) == 5


def test_demo_snapshot_is_read_only_shape_for_onboarding():
    response = client.get("/demo/snapshot")

    assert response.status_code == 200
    data = response.json()
    assert data["snapshot"]["org_profile"]["name"] == "Harbor Light Community Services"
    assert len(data["snapshot"]["connectors"]) == 4
    assert len(data["snapshot"]["metrics"]) == 4


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


def test_context_query_returns_local_context_core_answer():
    client.post("/demo/seed")
    client.post("/ingestion/run")
    response = client.post(
        "/context/query",
        json={
            "question": "what does anderson need and who owns the missing volunteer hours?",
            "user_id": "morgan",
            "role": "grant_manager",
            "external": True,
            "limit": 6,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["server"]["name"] == "fuze-context-core"
    assert data["server"]["style"] == "local-mcp"
    assert data["server"]["cloud_llm_calls"] == 0
    assert data["runtime"]["no_cloud_llm_calls"] is True
    assert data["vector_hits"]["collection"] == "fuze_context"
    assert data["vector_hits"]["hits"]
    assert data["hybrid_retrieval"]["rank_fusion"]["algorithm"] == "reciprocal_rank_fusion"
    assert data["hybrid_retrieval"]["rank_fusion"]["rankers"] == ["dense", "lexical", "graph"]
    assert "policy_aware_rerank" in data["hybrid_retrieval"]["query_plan"]["retrieval_stages"]
    assert data["hybrid_retrieval"]["reranked_hits"]
    assert all(not hit["features"]["blocked_by_policy"] for hit in data["hybrid_retrieval"]["reranked_hits"])
    assert data["hybrid_retrieval"]["packing"]["policy_filtered_before_prompt"] is True
    assert data["graph_traversal"]["ephemeral_agent"] == "context-graph-walker"
    assert data["graph_traversal"]["nodes"]
    assert data["selected_context"]
    assert any(item["metadata"].get("derived_from") == "sample_data/harbor_light" for item in data["selected_context"])
    assert any(item["source"] == "case_notes.txt" for item in data["blocked_context"])
    assert data["context_packet"]["constraints"]["no_cloud_llm_calls"] is True


def test_context_eval_scores_golden_retrieval_cases():
    client.post("/demo/seed")
    client.post("/ingestion/run")
    response = client.get("/context/eval")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "fuze-context-core-eval"
    assert data["cloud_llm_calls"] == 0
    assert data["retrieval_contract"] == "dense+lexical+graph rrf with policy-aware rerank"
    assert data["case_count"] == 3
    assert data["average_score"] >= 0.86
    assert data["passed"] is True
    assert all(result["passed"] for result in data["results"])
    assert all(result["metrics"]["stage_coverage"] == 1.0 for result in data["results"])
    assert all(result["metrics"]["policy_guardrail"] == 1.0 for result in data["results"])


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


def test_identity_directory_sync_role_mapping_and_access_preview():
    directory = client.get("/identity/directory")
    assert directory.status_code == 200
    data = directory.json()
    assert data["external_source_of_truth"] is True
    assert data["source"]["provisioning"] == "scim 2.0"
    assert any(group["dn"] == "cn=grant-team" for group in data["groups"])

    sync = client.post("/identity/sync", json={"actor": "alex"})
    assert sync.status_code == 200
    assert sync.json()["groups_seen"] >= 6

    update = client.post(
        "/identity/group-role-map",
        json={"group": "cn=grant-team", "role": "program_lead", "actor": "alex"},
    )
    assert update.status_code == 200
    assert update.json()["previous_role"] == "grant_manager"

    try:
        users = client.get("/identity/users").json()
        morgan = next(user for user in users["users"] if user["id"] == "morgan")
        assert morgan["role"] == "program_lead"

        preview = client.get("/identity/access-preview/morgan").json()
        assert preview["user"]["role"] == "program_lead"
        assert preview["blocked_count"] > 0

        mesh = client.get("/agents/status").json()
        event_types = {event["type"] for event in mesh["events"]}
        assert {"identity_sync", "role_mapping"}.issubset(event_types)
    finally:
        reset = client.post(
            "/identity/group-role-map",
            json={"group": "cn=grant-team", "role": "grant_manager", "actor": "test-reset"},
        )
        assert reset.status_code == 200


def test_context_packet_records_identity_and_role():
    client.post("/demo/seed")
    client.post("/ingestion/run")
    response = client.post(
        "/tools/get_context",
        json={"goal": "get us ready for the anderson foundation report", "user_id": "morgan", "role": "grant_manager"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == "morgan"
    assert data["role"] == "grant_manager"
    assert data["groups"] == ["cn=grant-team"]
    assert any(connector["id"] == "connector-m365-sharepoint" for connector in data["connectors"])
    assert any(metric["id"] == "metric-food-cost-variance" for metric in data["metrics"])
    assert any(item["source"] == "case_notes.txt" for item in data["blocked_context"])


def test_case_manager_can_use_restricted_context_internally():
    client.post("/demo/seed")
    client.post("/ingestion/run")
    response = client.post(
        "/tools/get_context",
        json={"goal": "review case note internally", "user_id": "casey", "role": "case_manager"},
    )

    assert response.status_code == 200
    data = response.json()
    blocked_sources = {item["source"] for item in data["blocked_context"]}
    assert "case_notes.txt" in blocked_sources

    from api import retrieval

    internal = retrieval.get_context(
        goal="review case note internally",
        user_id="casey",
        role="case_manager",
        external=False,
    )
    allowed_sources = {item["source"] for item in internal["allowed_context"]}
    assert "case_notes.txt" in allowed_sources


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
    assert data["personal_agents"]["count"] >= 5
    assert "fuze-context-core" in data["personal_agents"]["mcp_servers"]
    assert "fuze-web-search" in data["personal_agents"]["mcp_servers"]


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
    assert {"identity", "role-map", "connect-docs", "ingest", "activate-agents", "provision-personal-agents"}.issubset(step_ids)
    assert "scim 2.0" in data["identity_management"]["provisioning"]
    assert "microsoft graph delta queries" in data["identity_management"]["directory_sync"]
    assert "graph webhooks/change notifications" in data["doc_ingestion"]["change_detection"]
    assert "mcp tools" in " ".join(data["personal_agent_runtime"]["provisioning"])
    from api import personal_agents

    assert data["personal_agent_runtime"]["home_root"] == personal_agents.AGENT_ROOT


def test_personal_agents_expose_bash_mcp_web_search_cron_and_skills():
    response = client.get("/personal-agents")

    assert response.status_code == 200
    data = response.json()
    assert data["cloud_llm_calls"] == 0
    assert data["ram_strategy"].startswith("many lightweight")
    morgan = next(agent for agent in data["agents"] if agent["user"]["id"] == "morgan")
    assert morgan["paths"]["workspace"].endswith("/morgan/workspace")
    assert morgan["bash_env"]["SHELL"] == "/bin/bash"
    assert morgan["bash_env"]["FUZE_AGENT_ID"] == "personal-agent-morgan"
    assert morgan["bash_env"]["FUZE_CONTEXT_CORE_URL"].endswith("/context/query")
    assert morgan["bash_env"]["NO_CLOUD_LLM_CALLS"] == "1"
    mcp_ids = {server["id"] for server in morgan["mcp_servers"]}
    assert {"fuze-context-core", "fuze-bash", "fuze-web-search", "fuze-approvals"}.issubset(mcp_ids)
    web_search = next(server for server in morgan["mcp_servers"] if server["id"] == "fuze-web-search")
    assert "never send restricted org context" in web_search["policy"]
    cron_ids = {entry["id"] for entry in morgan["cron"]}
    assert {"heartbeat", "memory-refresh", "morning-digest", "skill-watch"}.issubset(cron_ids)
    skill_ids = {skill["id"] for skill in morgan["skills"]}
    assert {"nonprofit_grants", "donor_updates", "compliance_packet"}.issubset(skill_ids)
    assert morgan["policy"]["bash"]["workspace_scoped"] is True
    assert "context_query" in morgan["policy"]["audit"]


def test_personal_agent_provisioning_records_actions_files_and_events(tmp_path, monkeypatch):
    from api import personal_agents

    monkeypatch.setattr(personal_agents, "AGENT_ROOT", str(tmp_path / "agents"))
    response = client.post("/personal-agents/provision", json={"user_id": "morgan", "actor": "alex"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "provisioned"
    assert data["agent"]["status"] == "provisioned"
    assert data["agent"]["last_heartbeat"] is not None
    action_types = {action["type"] for action in data["actions"]}
    assert {"mkdir", "write_env", "write_mcp", "install_skills", "install_cron", "start_worker"}.issubset(action_types)
    assert data["materialized"] is True
    assert Path(data["agent"]["paths"]["workspace"]).exists()
    assert Path(data["agent"]["paths"]["home"], ".env").exists()
    mcp_config = Path(data["agent"]["paths"]["mcp"], "servers.json")
    assert mcp_config.exists()
    assert json.loads(mcp_config.read_text())["servers"][0]["id"] == "fuze-context-core"
    assert Path(data["agent"]["paths"]["cron"], "fuze.crontab").exists()

    heartbeat = client.post("/personal-agents/morgan/heartbeat")
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "alive"

    mesh = client.get("/agents/status").json()
    assert mesh["personal_agents"]["provisioned"] >= 1
    event_types = {event["type"] for event in mesh["events"]}
    assert {"provision", "heartbeat"}.issubset(event_types)


def test_onboarding_run_executes_backend_setup_and_materializes_agents(tmp_path, monkeypatch):
    from api import personal_agents

    monkeypatch.setattr(personal_agents, "AGENT_ROOT", str(tmp_path / "agents"))
    response = client.post("/onboarding/run", json={"actor": "alex", "provision_user_ids": ["morgan", "alex"]})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    step_ids = {step["id"] for step in data["steps"]}
    assert {"identity-sync", "ingestion", "personal-agents", "context-eval"}.issubset(step_ids)
    agent_step = next(step for step in data["steps"] if step["id"] == "personal-agents")
    assert len(agent_step["result"]) == 2
    assert all(item["files_written"] >= 5 for item in agent_step["result"])
    assert Path(tmp_path, "agents", "morgan", ".env").exists()
    assert Path(tmp_path, "agents", "alex", "mcp", "servers.json").exists()
    assert data["cloud_llm_calls"] == 0


def test_personal_agent_state_survives_memory_clear():
    from api import personal_agents

    response = client.post("/personal-agents/provision", json={"user_id": "alex", "actor": "alex", "materialize": False})
    assert response.status_code == 200

    personal_agents.PROVISIONED_AT.clear()
    personal_agents.LAST_HEARTBEAT.clear()
    status = client.get("/personal-agents/alex")

    assert status.status_code == 200
    data = status.json()
    assert data["status"] == "provisioned"
    assert data["last_heartbeat"] is not None


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
