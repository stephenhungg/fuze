"""demo identity adapter for role-aware context packets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


GROUP_ROLE_MAP = {
    "cn=executive": "executive_director",
    "cn=grant-team": "grant_manager",
    "cn=programs": "program_lead",
    "cn=case-management": "case_manager",
    "cn=volunteers": "volunteer_coordinator",
    "cn=board": "board_viewer",
}

VALID_ROLES = {
    "executive_director",
    "grant_manager",
    "program_lead",
    "case_manager",
    "volunteer_coordinator",
    "board_viewer",
}

DIRECTORY_GROUPS = [
    {
        "id": "group-executive",
        "dn": "cn=executive",
        "display_name": "executive leadership",
        "source": "entra id",
        "members": ["alex"],
    },
    {
        "id": "group-grant-team",
        "dn": "cn=grant-team",
        "display_name": "grant team",
        "source": "entra id",
        "members": ["morgan"],
    },
    {
        "id": "group-programs",
        "dn": "cn=programs",
        "display_name": "program staff",
        "source": "entra id",
        "members": ["sarah"],
    },
    {
        "id": "group-case-management",
        "dn": "cn=case-management",
        "display_name": "case management",
        "source": "ldap",
        "members": ["casey"],
    },
    {
        "id": "group-volunteers",
        "dn": "cn=volunteers",
        "display_name": "volunteer operations",
        "source": "entra id",
        "members": ["jordan"],
    },
    {
        "id": "group-board",
        "dn": "cn=board",
        "display_name": "board viewers",
        "source": "entra id",
        "members": ["board-viewer"],
    },
]

DIRECTORY_STATE: dict[str, Any] = {
    "provider": "demo-adapter",
    "source": "microsoft entra id / active directory simulator",
    "login": "oidc/saml",
    "provisioning": "scim 2.0",
    "sync": "graph delta query + ldap fallback",
    "last_sync": "2026-06-14T18:20:00Z",
    "delta_token": "delta-token-demo-2026-06-14T18:20:00Z",
    "last_actor": "system",
}


USERS = [
    {
        "id": "morgan",
        "name": "Morgan",
        "email": "morgan@harborlight.local",
        "groups": ["cn=grant-team"],
        "title": "Grant Manager",
    },
    {
        "id": "alex",
        "name": "Alex",
        "email": "alex@harborlight.local",
        "groups": ["cn=executive"],
        "title": "Executive Director",
    },
    {
        "id": "sarah",
        "name": "Sarah",
        "email": "sarah@harborlight.local",
        "groups": ["cn=programs"],
        "title": "Program Lead",
    },
    {
        "id": "casey",
        "name": "Casey",
        "email": "casey@harborlight.local",
        "groups": ["cn=case-management"],
        "title": "Case Manager",
    },
    {
        "id": "jordan",
        "name": "Jordan",
        "email": "jordan@harborlight.local",
        "groups": ["cn=volunteers"],
        "title": "Volunteer Coordinator",
    },
    {
        "id": "board-viewer",
        "name": "Board Viewer",
        "email": "board@harborlight.local",
        "groups": ["cn=board"],
        "title": "Board Viewer",
    },
]


def role_for_groups(groups: list[str]) -> str:
    for group in groups:
        role = GROUP_ROLE_MAP.get(group)
        if role:
            return role
    return "board_viewer"


def enrich_user(user: dict[str, Any]) -> dict[str, Any]:
    return {**user, "role": role_for_groups(user.get("groups", []))}


def list_users() -> list[dict[str, Any]]:
    return [enrich_user(user) for user in USERS]


def list_groups() -> list[dict[str, Any]]:
    groups = []
    for group in DIRECTORY_GROUPS:
        groups.append({**group, "mapped_role": GROUP_ROLE_MAP.get(group["dn"], "board_viewer")})
    return groups


def get_user(user_id: str | None) -> dict[str, Any]:
    selected = user_id or "morgan"
    for user in USERS:
        if user["id"] == selected:
            return enrich_user(user)
    return enrich_user(USERS[0])


def identity_status() -> dict[str, Any]:
    return {
        "provider": "demo-adapter",
        "mode": "seeded active directory / entra-style group mapping",
        "users": len(USERS),
        "groups": sorted(GROUP_ROLE_MAP),
        "role_map": GROUP_ROLE_MAP,
        "directory": DIRECTORY_STATE,
    }


def directory_status() -> dict[str, Any]:
    return {
        "source": DIRECTORY_STATE,
        "users": list_users(),
        "groups": list_groups(),
        "role_map": GROUP_ROLE_MAP,
        "supported_integrations": ["microsoft entra id", "active directory ldap", "okta", "google workspace"],
        "fuze_owned_state": ["group-to-role mappings", "policy decisions", "approval routing", "audit records"],
        "external_source_of_truth": True,
    }


def sync_directory(actor: str = "admin") -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    DIRECTORY_STATE.update(
        {
            "last_sync": now,
            "delta_token": f"delta-token-demo-{now}",
            "last_actor": actor,
        }
    )
    return {
        "status": "synced",
        "actor": actor,
        "last_sync": DIRECTORY_STATE["last_sync"],
        "delta_token": DIRECTORY_STATE["delta_token"],
        "users_seen": len(USERS),
        "groups_seen": len(DIRECTORY_GROUPS),
        "membership_edges": sum(len(group["members"]) for group in DIRECTORY_GROUPS),
        "source_of_truth": "external directory",
    }


def update_group_role(group_dn: str, role: str, actor: str = "admin") -> dict[str, Any]:
    if role not in VALID_ROLES:
        raise ValueError(f"unknown role: {role}")
    known_groups = {group["dn"] for group in DIRECTORY_GROUPS}
    if group_dn not in known_groups:
        raise ValueError(f"unknown group: {group_dn}")
    previous = GROUP_ROLE_MAP.get(group_dn)
    GROUP_ROLE_MAP[group_dn] = role
    return {
        "status": "updated",
        "actor": actor,
        "group": group_dn,
        "previous_role": previous,
        "role": role,
        "source_of_truth": "fuze mapping only; membership remains in external directory",
    }


def access_preview(user_id: str, external: bool = True) -> dict[str, Any]:
    from .db import store
    from . import policy

    user = get_user(user_id)
    allowed = []
    blocked = []
    for chunk in store.chunks():
        is_blocked, reasons = policy.is_blocked(chunk, role=user["role"], external=external)
        item = {
            "id": chunk["id"],
            "source": chunk["source"],
            "title": chunk["title"],
            "sensitivity": chunk.get("sensitivity", "internal"),
            "external_output_allowed": chunk.get("external_output_allowed", False),
        }
        if is_blocked:
            blocked.append({**item, "reasons": reasons})
        else:
            allowed.append(item)
    return {
        "user": user,
        "external_output": external,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "allowed_preview": allowed[:6],
        "blocked_preview": blocked[:6],
        "decision": "role mapping applied before context packet assembly",
    }
