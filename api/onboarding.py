"""demo onboarding contract for enterprise/nonprofit setup."""

from __future__ import annotations

from typing import Any

from . import personal_agents


ONBOARDING_FLOW: list[dict[str, Any]] = [
    {
        "id": "mission-template",
        "label": "choose mission template",
        "status": "ready",
        "owner": "admin",
        "details": "start with nonprofit grants, volunteer ops, donor updates, or compliance.",
    },
    {
        "id": "identity",
        "label": "connect identity",
        "status": "demo-adapter",
        "owner": "it admin",
        "details": "use oidc/saml for login, scim for provisioning, and group-to-role mapping for policy.",
    },
    {
        "id": "role-map",
        "label": "map groups to roles",
        "status": "ready",
        "owner": "program admin",
        "details": "map entra/ad/ldap/okta groups into fuze roles like grant_manager and case_manager.",
    },
    {
        "id": "connect-docs",
        "label": "connect docs",
        "status": "planned",
        "owner": "ops admin",
        "details": "watch shared drives, google drive, microsoft 365, csv exports, and local folders.",
    },
    {
        "id": "ingest",
        "label": "ingest and classify",
        "status": "demo-seeded",
        "owner": "index agent",
        "details": "partition files, chunk semantically, attach metadata, embed locally, and update graph memory.",
    },
    {
        "id": "activate-agents",
        "label": "activate agents",
        "status": "ready",
        "owner": "admin",
        "details": "enable workflow agents with policy gates, approval routing, audit, and sse observability.",
    },
    {
        "id": "provision-personal-agents",
        "label": "provision personal agents",
        "status": "ready",
        "owner": "fuze supervisor",
        "details": "create per-employee agent homes with bash envs, scoped folders, mcp tools, web search policy, skills, cron, and heartbeats.",
    },
]


IDENTITY_MANAGEMENT: dict[str, Any] = {
    "login": ["oidc", "saml"],
    "provisioning": ["scim 2.0"],
    "directory_sync": ["microsoft graph delta queries", "microsoft graph change notifications", "ldap sync"],
    "source_of_truth": "external identity provider",
    "fuze_responsibility": [
        "map external groups to fuze roles",
        "enforce role-aware context retrieval",
        "record identity in audit packets",
        "route approvals to role owners",
    ],
}


DOC_INGESTION: dict[str, Any] = {
    "connectors": ["local folders", "google drive", "microsoft 365 sharepoint/onedrive", "csv exports"],
    "change_detection": ["file watcher", "drive delta query", "graph webhooks/change notifications"],
    "pipeline": [
        "partition raw documents into typed elements",
        "chunk by semantic/section boundaries",
        "classify sensitivity and allowed roles",
        "embed locally with ollama",
        "upsert qdrant payloads and graph entities",
        "emit index-agent events",
    ],
}


PERSONAL_AGENT_RUNTIME: dict[str, Any] = {
    "model": "one lightweight personal worker per employee; shared local inference on the dell",
    "home_root": personal_agents.AGENT_ROOT,
    "provisioning": [
        "create scoped folders for workspace, memory, skills, mcp config, logs, runs, tmp, secrets, and cron",
        "write a bash env with fuze agent/user ids, role, groups, context-core url, ollama host, qdrant url, and audit log path",
        "install mcp tools for context core, scoped filesystem, bash, web search, and approvals",
        "enable role-specific skills and cron entries for heartbeat, memory refresh, daily digest, and skill watches",
        "stream provisioning and heartbeat events to observability",
    ],
    "security": [
        "role-aware context packets instead of raw file access",
        "web search cannot receive restricted org context",
        "destructive shell actions require approval",
        "all commands, tool calls, external fetches, context queries, approvals, and heartbeats are audited",
    ],
}


def onboarding_status() -> dict[str, Any]:
    return {
        "flow": ONBOARDING_FLOW,
        "identity_management": IDENTITY_MANAGEMENT,
        "doc_ingestion": DOC_INGESTION,
        "personal_agent_runtime": PERSONAL_AGENT_RUNTIME,
        "recommended_first_run": [
            "pick nonprofit grants",
            "connect identity",
            "map grant-team/programs/case-management groups",
            "seed or ingest docs",
            "run grant readiness agent",
            "provision Morgan's personal grant agent",
            "watch sse observability and approval queue",
        ],
    }
