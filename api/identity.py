"""demo identity adapter for role-aware context packets."""

from __future__ import annotations

from typing import Any


GROUP_ROLE_MAP = {
    "cn=executive": "executive_director",
    "cn=grant-team": "grant_manager",
    "cn=programs": "program_lead",
    "cn=case-management": "case_manager",
    "cn=volunteers": "volunteer_coordinator",
    "cn=board": "board_viewer",
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
    }
