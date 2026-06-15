"""personal agent runtime contracts for employee-scoped agents.

the demo keeps this as deterministic control-plane data. on the gb10 these
contracts are the shape a supervisor would use to create folders, write env
files, schedule heartbeats, and launch long-running workers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import identity


AGENT_ROOT = "/var/lib/fuze/agents"
CONTEXT_CORE_URL = "http://127.0.0.1:8000/context/query"
MCP_BASE_URL = "http://127.0.0.1:8000/mcp"


ROLE_SKILLS: dict[str, list[str]] = {
    "executive_director": ["approval_routing", "board_packet_prep", "donor_updates", "compliance_packet"],
    "grant_manager": ["nonprofit_grants", "donor_updates", "compliance_packet"],
    "program_lead": ["program_metrics", "story_approval", "volunteer_ops"],
    "case_manager": ["case_note_governance", "consent_review", "restricted_context"],
    "volunteer_coordinator": ["volunteer_ops", "shift_gap_monitoring", "grant_metric_updates"],
    "board_viewer": ["board_packet_review", "read_only_context"],
}


PROVISIONED_AT: dict[str, str] = {}
LAST_HEARTBEAT: dict[str, str] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def agent_id(user_id: str) -> str:
    return f"personal-agent-{user_id}"


def agent_paths(user_id: str) -> dict[str, str]:
    home = f"{AGENT_ROOT}/{user_id}"
    return {
        "home": home,
        "workspace": f"{home}/workspace",
        "memory": f"{home}/memory",
        "skills": f"{home}/skills",
        "mcp": f"{home}/mcp",
        "logs": f"{home}/logs",
        "runs": f"{home}/runs",
        "tmp": f"{home}/tmp",
        "secrets": f"{home}/secrets",
        "cron": f"{home}/cron",
    }


def bash_env(user: dict[str, Any], paths: dict[str, str]) -> dict[str, str]:
    return {
        "SHELL": "/bin/bash",
        "FUZE_AGENT_ID": agent_id(user["id"]),
        "FUZE_USER_ID": user["id"],
        "FUZE_USER_ROLE": user["role"],
        "FUZE_USER_GROUPS": ",".join(user["groups"]),
        "FUZE_HOME": paths["home"],
        "FUZE_WORKSPACE": paths["workspace"],
        "FUZE_MEMORY_DIR": paths["memory"],
        "FUZE_SKILLS_DIR": paths["skills"],
        "FUZE_MCP_CONFIG": f"{paths['mcp']}/servers.json",
        "FUZE_CONTEXT_CORE_URL": CONTEXT_CORE_URL,
        "FUZE_AUDIT_LOG": f"{paths['logs']}/audit.jsonl",
        "OLLAMA_HOST": "http://127.0.0.1:11434",
        "QDRANT_URL": "http://127.0.0.1:6333",
        "NO_CLOUD_LLM_CALLS": "1",
    }


def mcp_servers(user: dict[str, Any], paths: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "id": "fuze-context-core",
            "transport": "http",
            "url": CONTEXT_CORE_URL,
            "tools": ["query_context", "explain_sources", "run_context_eval"],
            "policy": "role-aware context packets only; no raw file exfiltration",
        },
        {
            "id": "fuze-filesystem",
            "transport": "stdio",
            "command": "fuze-fs-mcp",
            "scope": paths["workspace"],
            "tools": ["read_workspace", "write_workspace", "list_workspace"],
            "policy": "scoped to the user's workspace and approved shared exports",
        },
        {
            "id": "fuze-bash",
            "transport": "stdio",
            "command": "/bin/bash",
            "tools": ["shell", "script", "log_tail"],
            "policy": "non-destructive commands by default; privileged actions require approval",
        },
        {
            "id": "fuze-web-search",
            "transport": "http",
            "url": f"{MCP_BASE_URL}/web-search",
            "tools": ["search", "fetch", "cite"],
            "policy": "public web only; never send restricted org context; citations required",
        },
        {
            "id": "fuze-approvals",
            "transport": "http",
            "url": f"{MCP_BASE_URL}/approvals",
            "tools": ["request_approval", "check_approval", "write_audit_event"],
            "policy": "external sends, pii, and high-risk writes require a human gate",
        },
    ]


def cron_entries(user: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "heartbeat",
            "schedule": "*/1 * * * *",
            "command": f"fuze-agent heartbeat --agent {agent_id(user['id'])}",
            "purpose": "prove the personal worker is alive and update the dashboard",
        },
        {
            "id": "memory-refresh",
            "schedule": "*/5 * * * *",
            "command": f"fuze-agent refresh-memory --agent {agent_id(user['id'])}",
            "purpose": "pull fresh role-scoped context from the local context core",
        },
        {
            "id": "morning-digest",
            "schedule": "0 8 * * mon-fri",
            "command": f"fuze-agent digest --agent {agent_id(user['id'])}",
            "purpose": "prepare a staff-facing daily brief without cloud calls",
        },
        {
            "id": "skill-watch",
            "schedule": "*/15 * * * *",
            "command": f"fuze-agent run-skills --agent {agent_id(user['id'])}",
            "purpose": "run enabled nonprofit skills against new events and deadlines",
        },
    ]


def skills_for_role(role: str) -> list[dict[str, Any]]:
    names = ROLE_SKILLS.get(role, ROLE_SKILLS["board_viewer"])
    return [
        {
            "id": name,
            "source": "api/skills or org-installed skill pack",
            "enabled": True,
            "execution": "local worker calls shared ollama/context-core as needed",
        }
        for name in names
    ]


def runtime_policy(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "identity_source": "external directory via oidc/saml/scim/ldap mapping",
        "role": user["role"],
        "groups": user["groups"],
        "model_loading": "shared ollama models; no dedicated model per employee",
        "context_boundary": "agents query fuze-context-core and receive policy-filtered packets",
        "web_search": {
            "enabled": True,
            "allowed": "public web search with citations",
            "blocked": "sending raw restricted org context, pii, case notes, donor secrets, or secrets",
        },
        "bash": {
            "enabled": True,
            "shell": "/bin/bash",
            "workspace_scoped": True,
            "destructive_commands": "approval required",
        },
        "quotas": {
            "workspace_mb": 512,
            "max_parallel_jobs": 2,
            "max_runtime_minutes_per_job": 20,
            "shared_model_context_tokens": 32768,
        },
        "audit": ["command", "tool_call", "context_query", "approval", "external_fetch", "heartbeat"],
    }


def personal_agent_for_user(user: dict[str, Any]) -> dict[str, Any]:
    paths = agent_paths(user["id"])
    provisioned_at = PROVISIONED_AT.get(user["id"])
    heartbeat = LAST_HEARTBEAT.get(user["id"])
    return {
        "id": agent_id(user["id"]),
        "user": user,
        "status": "provisioned" if provisioned_at else "planned",
        "runtime": "gb10-personal-agent",
        "supervisor": "fuze-agent-supervisor",
        "execution": "long-running lightweight worker with shared local inference",
        "paths": paths,
        "bash_env": bash_env(user, paths),
        "mcp_servers": mcp_servers(user, paths),
        "skills": skills_for_role(user["role"]),
        "cron": cron_entries(user),
        "policy": runtime_policy(user),
        "provisioned_at": provisioned_at,
        "last_heartbeat": heartbeat,
    }


def list_personal_agents() -> dict[str, Any]:
    agents = [personal_agent_for_user(user) for user in identity.list_users()]
    return {
        "root": AGENT_ROOT,
        "count": len(agents),
        "agents": agents,
        "shared_services": {
            "ollama": "http://127.0.0.1:11434",
            "qdrant": "http://127.0.0.1:6333",
            "context_core": CONTEXT_CORE_URL,
            "event_stream": "/events/stream",
        },
        "ram_strategy": "many lightweight personal workers share the same loaded qwen/embedding models",
        "cloud_llm_calls": 0,
    }


def get_personal_agent(user_id: str) -> dict[str, Any] | None:
    for user in identity.list_users():
        if user["id"] == user_id:
            return personal_agent_for_user(user)
    return None


def provision_personal_agent(user_id: str, actor: str = "admin") -> dict[str, Any]:
    agent = get_personal_agent(user_id)
    if agent is None:
        raise ValueError(f"unknown user: {user_id}")
    timestamp = now()
    PROVISIONED_AT[user_id] = timestamp
    LAST_HEARTBEAT[user_id] = timestamp
    agent = get_personal_agent(user_id)
    assert agent is not None
    return {
        "status": "provisioned",
        "actor": actor,
        "agent": agent,
        "actions": [
            {"type": "mkdir", "targets": list(agent["paths"].values())},
            {"type": "write_env", "target": f"{agent['paths']['home']}/.env", "keys": sorted(agent["bash_env"])},
            {"type": "write_mcp", "target": agent["bash_env"]["FUZE_MCP_CONFIG"], "servers": [server["id"] for server in agent["mcp_servers"]]},
            {"type": "install_skills", "target": agent["paths"]["skills"], "skills": [skill["id"] for skill in agent["skills"]]},
            {"type": "install_cron", "target": f"{agent['paths']['cron']}/fuze.crontab", "entries": [entry["id"] for entry in agent["cron"]]},
            {"type": "start_worker", "command": f"fuze-agent worker --agent {agent['id']} --env {agent['paths']['home']}/.env"},
        ],
    }


def heartbeat(user_id: str) -> dict[str, Any]:
    agent = get_personal_agent(user_id)
    if agent is None:
        raise ValueError(f"unknown user: {user_id}")
    timestamp = now()
    LAST_HEARTBEAT[user_id] = timestamp
    updated = get_personal_agent(user_id)
    assert updated is not None
    return {"status": "alive", "agent": updated, "last_heartbeat": timestamp}
