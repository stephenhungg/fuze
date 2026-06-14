"""small in-memory store for the hackathon demo.

the storage shape mirrors what would later become sqlite/postgres plus qdrant.
for the venue demo it stays deterministic, local, and easy to reset.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


DEMO_GOAL = "get us ready for the anderson foundation report"


SEED_DATA: dict[str, Any] = {
    "org_id": "harbor-light-nonprofit",
    "skill": "nonprofit_grants",
    "nodes": [
        {
            "id": "funder-anderson",
            "label": "Anderson Foundation",
            "type": "funder",
            "summary": "funder requesting the june impact report.",
        },
        {
            "id": "grant-anderson-2026",
            "label": "Anderson Youth Meals Grant",
            "type": "grant",
            "summary": "restricted grant supporting after-school meals and family support.",
        },
        {
            "id": "doc-grant-agreement",
            "label": "Grant Agreement",
            "type": "evidence",
            "source": "grant_requirements.txt",
            "summary": "requires meal count, attendance, volunteer hours, and one approved story.",
        },
        {
            "id": "req-reporting",
            "label": "Reporting Requirements",
            "type": "deadline",
            "summary": "impact report due june 20 with metrics, narrative, and budget notes.",
        },
        {
            "id": "metric-program",
            "label": "Program Metrics",
            "type": "outcome_metric",
            "summary": "may meals and attendance totals are available; volunteer hours are incomplete.",
        },
        {
            "id": "missing-volunteer-hours",
            "label": "Missing Volunteer Hours",
            "type": "task",
            "summary": "may volunteer hours are missing from the report packet.",
        },
        {
            "id": "person-jordan",
            "label": "Jordan",
            "type": "person",
            "summary": "volunteer coordinator who owns may volunteer hour totals.",
        },
        {
            "id": "person-sarah",
            "label": "Sarah",
            "type": "person",
            "summary": "program lead who can confirm attendance totals.",
        },
        {
            "id": "case-note-sensitive",
            "label": "Sensitive Case Note",
            "type": "client_story",
            "summary": "raw client note contains a minor name and address and must stay internal.",
            "sensitivity": "restricted",
        },
    ],
    "edges": [
        {"source": "funder-anderson", "target": "grant-anderson-2026", "label": "funds"},
        {"source": "grant-anderson-2026", "target": "doc-grant-agreement", "label": "governed_by"},
        {"source": "doc-grant-agreement", "target": "req-reporting", "label": "requires"},
        {"source": "req-reporting", "target": "metric-program", "label": "checks"},
        {"source": "metric-program", "target": "missing-volunteer-hours", "label": "blocked_by"},
        {"source": "missing-volunteer-hours", "target": "person-jordan", "label": "owned_by"},
        {"source": "metric-program", "target": "person-sarah", "label": "confirmed_by"},
        {"source": "doc-grant-agreement", "target": "case-note-sensitive", "label": "contains"},
    ],
    "chunks": [
        {
            "id": "grant-req-1",
            "source": "grant_requirements.txt",
            "title": "anderson reporting requirements",
            "text": "anderson foundation report due june 20. include total meals served, youth attendance, may volunteer hours, budget variance, and one approved anonymized participant story.",
            "allowed_roles": ["grant_manager", "executive_director"],
            "external_output_allowed": True,
            "sensitivity": "internal",
            "citations": ["grant_requirements.txt#reporting"],
        },
        {
            "id": "metrics-1",
            "source": "program_metrics.csv",
            "title": "may program metrics",
            "text": "may meal count is 1,284. may youth attendance total is 412. volunteer hours field is blank pending jordan's update.",
            "allowed_roles": ["grant_manager", "program_lead", "executive_director"],
            "external_output_allowed": True,
            "sensitivity": "internal",
            "citations": ["program_metrics.csv#may"],
        },
        {
            "id": "board-1",
            "source": "board_minutes.txt",
            "title": "board approval",
            "text": "board approved sharing aggregate may meal count, attendance totals, and anonymized impact language with anderson foundation.",
            "allowed_roles": ["grant_manager", "executive_director"],
            "external_output_allowed": True,
            "sensitivity": "internal",
            "citations": ["board_minutes.txt#approval"],
        },
        {
            "id": "volunteer-1",
            "source": "volunteers.csv",
            "title": "volunteer owner",
            "text": "jordan lee owns the may volunteer hour export. status is waiting on final sign-off.",
            "allowed_roles": ["grant_manager", "program_lead"],
            "external_output_allowed": False,
            "sensitivity": "internal",
            "citations": ["volunteers.csv#jordan"],
        },
        {
            "id": "case-1",
            "source": "case_notes.txt",
            "title": "raw case note",
            "text": "client maya, age 15, lives at 44 cedar ave. raw case note describes family housing instability and food access needs.",
            "allowed_roles": ["case_manager"],
            "external_output_allowed": False,
            "sensitivity": "restricted",
            "citations": ["case_notes.txt#maya"],
        },
    ],
}


class DemoStore:
    def __init__(self) -> None:
        self.seed()

    def seed(self) -> dict[str, Any]:
        self.data = deepcopy(SEED_DATA)
        self.tasks: list[dict[str, Any]] = []
        self.audit_runs: list[dict[str, Any]] = []
        self.last_context: dict[str, Any] | None = None
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "org_id": self.data["org_id"],
            "skill": self.data["skill"],
            "nodes": deepcopy(self.data["nodes"]),
            "edges": deepcopy(self.data["edges"]),
            "chunks": deepcopy(self.data["chunks"]),
            "tasks": deepcopy(self.tasks),
            "audit_runs": deepcopy(self.audit_runs),
        }

    def graph(self) -> dict[str, Any]:
        return {"nodes": deepcopy(self.data["nodes"]), "edges": deepcopy(self.data["edges"])}

    def chunks(self) -> list[dict[str, Any]]:
        return deepcopy(self.data["chunks"])

    def add_tasks(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        existing = {task["id"] for task in self.tasks}
        for task in tasks:
            if task["id"] not in existing:
                self.tasks.append({**deepcopy(task), "created_at": now})
        return deepcopy(self.tasks)

    def add_audit(self, audit: dict[str, Any]) -> dict[str, Any]:
        self.audit_runs.append(deepcopy(audit))
        return deepcopy(audit)


store = DemoStore()
