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
    "org_profile": {
        "name": "Harbor Light Community Services",
        "mission": "after-school meals, family support, and youth stability services in east bay neighborhoods.",
        "fiscal_year": "2026",
        "annual_budget": "$3.8m",
        "staff_count": 42,
        "volunteer_count": 186,
        "active_grants": 7,
        "risk_posture": "moderate; high sensitivity around minors, addresses, and case notes.",
    },
    "skill": "nonprofit_grants",
    "connectors": [
        {
            "id": "connector-m365-sharepoint",
            "label": "microsoft 365 sharepoint",
            "status": "connected",
            "last_sync": "2026-06-14T18:20:00Z",
            "scope": "grants, board packets, finance exports",
            "change_detection": "graph delta query + change notifications",
        },
        {
            "id": "connector-google-drive",
            "label": "google drive",
            "status": "connected",
            "last_sync": "2026-06-14T18:11:00Z",
            "scope": "program narratives and volunteer ops",
            "change_detection": "drive changes feed",
        },
        {
            "id": "connector-crm-export",
            "label": "donor crm csv export",
            "status": "watching",
            "last_sync": "2026-06-14T17:45:00Z",
            "scope": "funder contacts and restricted gift notes",
            "change_detection": "local folder watcher",
        },
        {
            "id": "connector-case-notes",
            "label": "case management secure folder",
            "status": "restricted",
            "last_sync": "2026-06-14T16:55:00Z",
            "scope": "case notes and participant stories",
            "change_detection": "manual approval import",
        },
    ],
    "staff_profiles": [
        {
            "id": "morgan",
            "name": "Morgan Patel",
            "title": "Grant Manager",
            "department": "development",
            "role": "grant_manager",
            "systems": ["sharepoint", "crm export", "qdrant dashboard"],
            "responsibilities": ["grant reports", "funder updates", "budget narrative coordination"],
        },
        {
            "id": "alex",
            "name": "Alex Rivera",
            "title": "Executive Director",
            "department": "leadership",
            "role": "executive_director",
            "systems": ["board portal", "sharepoint", "finance exports"],
            "responsibilities": ["external approvals", "board reporting", "funder escalation"],
        },
        {
            "id": "sarah",
            "name": "Sarah Kim",
            "title": "Program Lead",
            "department": "youth programs",
            "role": "program_lead",
            "systems": ["program metrics sheets", "google drive"],
            "responsibilities": ["attendance verification", "story approvals", "program outcomes"],
        },
        {
            "id": "casey",
            "name": "Casey Nguyen",
            "title": "Case Manager",
            "department": "family support",
            "role": "case_manager",
            "systems": ["secure case folder"],
            "responsibilities": ["case notes", "participant consent", "sensitive story review"],
        },
        {
            "id": "jordan",
            "name": "Jordan Lee",
            "title": "Volunteer Coordinator",
            "department": "operations",
            "role": "volunteer_coordinator",
            "systems": ["volunteer export", "google drive"],
            "responsibilities": ["volunteer hours", "shift coverage", "training records"],
        },
    ],
    "funders": [
        {
            "id": "funder-anderson",
            "name": "Anderson Foundation",
            "status": "active",
            "relationship_owner": "Morgan",
            "report_due": "2026-06-20",
            "grant_amount": "$125,000",
        },
        {
            "id": "funder-east-bay-community",
            "name": "East Bay Community Trust",
            "status": "renewal pending",
            "relationship_owner": "Alex",
            "report_due": "2026-07-15",
            "grant_amount": "$80,000",
        },
        {
            "id": "funder-sunrise-corporate",
            "name": "Sunrise Corporate Giving",
            "status": "prospect",
            "relationship_owner": "Morgan",
            "report_due": None,
            "grant_amount": "$40,000 requested",
        },
    ],
    "programs": [
        {
            "id": "program-youth-meals",
            "name": "Youth Meals",
            "lead": "Sarah",
            "monthly_capacity": 1500,
            "sensitivity": "internal",
        },
        {
            "id": "program-family-support",
            "name": "Family Support",
            "lead": "Casey",
            "monthly_capacity": 90,
            "sensitivity": "restricted",
        },
        {
            "id": "program-volunteer-ops",
            "name": "Volunteer Operations",
            "lead": "Jordan",
            "monthly_capacity": 220,
            "sensitivity": "internal",
        },
    ],
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
            "id": "person-alex",
            "label": "Alex",
            "type": "person",
            "summary": "executive director who approves external funder exports.",
        },
        {
            "id": "person-casey",
            "label": "Casey",
            "type": "person",
            "summary": "case manager who can review restricted case context internally.",
        },
        {
            "id": "program-youth-meals",
            "label": "Youth Meals Program",
            "type": "program",
            "summary": "after-school meals program funded by Anderson and related grants.",
        },
        {
            "id": "program-family-support",
            "label": "Family Support Program",
            "type": "program",
            "summary": "restricted support workflow containing case notes and consent records.",
        },
        {
            "id": "doc-budget-variance",
            "label": "Budget Variance Notes",
            "type": "evidence",
            "source": "finance_export_may.xlsx",
            "summary": "food cost variance is documented and approved for funder reporting.",
        },
        {
            "id": "doc-volunteer-export",
            "label": "Volunteer Export",
            "type": "evidence",
            "source": "volunteers.csv",
            "summary": "may volunteer hours export is waiting on Jordan's final sign-off.",
        },
        {
            "id": "funder-east-bay-community",
            "label": "East Bay Community Trust",
            "type": "funder",
            "summary": "renewal funder with july outcome narrative due.",
        },
        {
            "id": "connector-sharepoint",
            "label": "SharePoint Connector",
            "type": "connector",
            "summary": "microsoft 365 connector watching grants, board, and finance folders.",
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
        {"source": "metric-program", "target": "doc-budget-variance", "label": "supported_by"},
        {"source": "missing-volunteer-hours", "target": "doc-volunteer-export", "label": "blocked_by"},
        {"source": "grant-anderson-2026", "target": "program-youth-meals", "label": "funds"},
        {"source": "program-youth-meals", "target": "person-sarah", "label": "led_by"},
        {"source": "program-family-support", "target": "person-casey", "label": "led_by"},
        {"source": "req-reporting", "target": "person-alex", "label": "approval_owner"},
        {"source": "connector-sharepoint", "target": "doc-grant-agreement", "label": "syncs"},
        {"source": "funder-east-bay-community", "target": "program-family-support", "label": "funds"},
        {"source": "doc-grant-agreement", "target": "case-note-sensitive", "label": "contains"},
    ],
    "metrics": [
        {
            "id": "metric-may-meals",
            "label": "may meals served",
            "value": 1284,
            "target": 1200,
            "status": "above target",
            "source": "program_metrics.csv#may",
        },
        {
            "id": "metric-may-attendance",
            "label": "may youth attendance",
            "value": 412,
            "target": 390,
            "status": "above target",
            "source": "program_metrics.csv#may",
        },
        {
            "id": "metric-may-volunteer-hours",
            "label": "may volunteer hours",
            "value": None,
            "target": 240,
            "status": "missing owner sign-off",
            "source": "volunteers.csv#jordan",
        },
        {
            "id": "metric-food-cost-variance",
            "label": "food cost variance",
            "value": "+6.4%",
            "target": "<=8%",
            "status": "acceptable",
            "source": "finance_export_may.xlsx#variance",
        },
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
            "metadata": {
                "source_type": "grant_agreement",
                "connector_id": "connector-m365-sharepoint",
                "document_hash": "sha256:grant-req-2026-06",
                "updated_at": "2026-06-10T15:00:00Z",
            },
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
            "metadata": {
                "source_type": "csv",
                "connector_id": "connector-google-drive",
                "document_hash": "sha256:metrics-may-v3",
                "updated_at": "2026-06-12T10:30:00Z",
            },
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
            "metadata": {
                "source_type": "board_minutes",
                "connector_id": "connector-m365-sharepoint",
                "document_hash": "sha256:board-may-approved",
                "updated_at": "2026-06-03T22:00:00Z",
            },
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
            "metadata": {
                "source_type": "csv",
                "connector_id": "connector-google-drive",
                "document_hash": "sha256:volunteer-may-draft",
                "updated_at": "2026-06-13T18:00:00Z",
            },
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
            "metadata": {
                "source_type": "case_note",
                "connector_id": "connector-case-notes",
                "document_hash": "sha256:case-maya-raw",
                "updated_at": "2026-05-29T09:15:00Z",
            },
        },
        {
            "id": "budget-1",
            "source": "finance_export_may.xlsx",
            "title": "may budget variance",
            "text": "may food purchasing ran 6.4 percent over baseline because attendance exceeded forecast. finance marked the variance acceptable and within the grant tolerance.",
            "allowed_roles": ["grant_manager", "executive_director"],
            "external_output_allowed": True,
            "sensitivity": "internal",
            "citations": ["finance_export_may.xlsx#variance"],
            "metadata": {
                "source_type": "spreadsheet",
                "connector_id": "connector-m365-sharepoint",
                "document_hash": "sha256:finance-may-v2",
                "updated_at": "2026-06-11T14:40:00Z",
            },
        },
        {
            "id": "staff-profile-1",
            "source": "staff_directory.csv",
            "title": "staff ownership map",
            "text": "Morgan owns grant reports, Alex approves external funder exports, Sarah owns program outcomes, Casey owns restricted case note review, and Jordan owns volunteer hour exports.",
            "allowed_roles": ["grant_manager", "program_lead", "executive_director"],
            "external_output_allowed": False,
            "sensitivity": "internal",
            "citations": ["staff_directory.csv#ownership"],
            "metadata": {
                "source_type": "directory_export",
                "connector_id": "connector-m365-sharepoint",
                "document_hash": "sha256:staff-directory-june",
                "updated_at": "2026-06-14T12:00:00Z",
            },
        },
        {
            "id": "consent-1",
            "source": "story_consent_tracker.xlsx",
            "title": "participant story consent status",
            "text": "two participant stories are approved for aggregate use. the third story is pending program lead review and cannot be exported until approved.",
            "allowed_roles": ["grant_manager", "program_lead", "case_manager", "executive_director"],
            "external_output_allowed": False,
            "sensitivity": "restricted",
            "citations": ["story_consent_tracker.xlsx#june"],
            "metadata": {
                "source_type": "spreadsheet",
                "connector_id": "connector-case-notes",
                "document_hash": "sha256:story-consent-june",
                "updated_at": "2026-06-09T16:10:00Z",
            },
        },
        {
            "id": "east-bay-1",
            "source": "east_bay_renewal_brief.md",
            "title": "east bay renewal brief",
            "text": "east bay community trust renewal narrative is due july 15. the funder cares most about family support outcomes, retention, and board-approved sustainability plans.",
            "allowed_roles": ["grant_manager", "executive_director"],
            "external_output_allowed": True,
            "sensitivity": "internal",
            "citations": ["east_bay_renewal_brief.md#requirements"],
            "metadata": {
                "source_type": "grant_brief",
                "connector_id": "connector-m365-sharepoint",
                "document_hash": "sha256:east-bay-renewal",
                "updated_at": "2026-06-01T11:25:00Z",
            },
        },
        {
            "id": "donor-1",
            "source": "donor_crm_export.csv",
            "title": "major donor restrictions",
            "text": "sunrise corporate giving prospect prefers volunteer engagement stories but has not consented to receive any participant-level case details.",
            "allowed_roles": ["grant_manager", "executive_director"],
            "external_output_allowed": False,
            "sensitivity": "confidential",
            "citations": ["donor_crm_export.csv#sunrise"],
            "metadata": {
                "source_type": "crm_export",
                "connector_id": "connector-crm-export",
                "document_hash": "sha256:donor-crm-june",
                "updated_at": "2026-06-14T17:45:00Z",
            },
        },
        {
            "id": "compliance-1",
            "source": "compliance_calendar.md",
            "title": "june compliance calendar",
            "text": "food safety training records are due june 25. volunteer background check attestations are due june 30 and owned by Jordan.",
            "allowed_roles": ["program_lead", "volunteer_coordinator", "executive_director"],
            "external_output_allowed": False,
            "sensitivity": "internal",
            "citations": ["compliance_calendar.md#june"],
            "metadata": {
                "source_type": "calendar",
                "connector_id": "connector-google-drive",
                "document_hash": "sha256:compliance-june",
                "updated_at": "2026-06-08T08:00:00Z",
            },
        },
        {
            "id": "case-summary-1",
            "source": "approved_story_bank.md",
            "title": "approved anonymized story bank",
            "text": "approved story bank includes anonymized language about a family stabilizing meal access after joining the youth meals program. no names, ages, addresses, or case identifiers are included.",
            "allowed_roles": ["grant_manager", "program_lead", "executive_director"],
            "external_output_allowed": True,
            "sensitivity": "internal",
            "citations": ["approved_story_bank.md#story-2"],
            "metadata": {
                "source_type": "story_bank",
                "connector_id": "connector-case-notes",
                "document_hash": "sha256:approved-story-bank",
                "updated_at": "2026-06-07T13:30:00Z",
            },
        },
        {
            "id": "board-risk-1",
            "source": "board_risk_register.md",
            "title": "board risk register",
            "text": "board risk register flags three active risks: late volunteer hour reporting, case note privacy, and dependency on manual csv exports for grant evidence.",
            "allowed_roles": ["grant_manager", "executive_director", "board_viewer"],
            "external_output_allowed": False,
            "sensitivity": "internal",
            "citations": ["board_risk_register.md#q2"],
            "metadata": {
                "source_type": "risk_register",
                "connector_id": "connector-m365-sharepoint",
                "document_hash": "sha256:board-risk-q2",
                "updated_at": "2026-06-05T19:00:00Z",
            },
        },
    ],
}


class DemoStore:
    def __init__(self) -> None:
        self.seed()

    def seed(self) -> dict[str, Any]:
        self.data = deepcopy(SEED_DATA)
        self.tasks: list[dict[str, Any]] = []
        self.approvals: list[dict[str, Any]] = []
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
            "org_profile": deepcopy(self.data["org_profile"]),
            "connectors": deepcopy(self.data["connectors"]),
            "staff_profiles": deepcopy(self.data["staff_profiles"]),
            "funders": deepcopy(self.data["funders"]),
            "programs": deepcopy(self.data["programs"]),
            "metrics": deepcopy(self.data["metrics"]),
            "tasks": deepcopy(self.tasks),
            "approvals": deepcopy(self.approvals),
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

    def add_approvals(self, approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        existing = {approval["id"] for approval in self.approvals}
        for approval in approvals:
            if approval["id"] not in existing:
                self.approvals.append(
                    {
                        **deepcopy(approval),
                        "status": approval.get("status", "pending"),
                        "created_at": now,
                        "decided_at": None,
                        "decided_by": None,
                        "decision_note": None,
                    }
                )
        return deepcopy(self.approvals)

    def decide_approval(self, approval_id: str, status: str, actor: str, note: str = "") -> dict[str, Any] | None:
        if status not in {"approved", "rejected"}:
            raise ValueError("approval status must be approved or rejected")

        now = datetime.now(timezone.utc).isoformat()
        for approval in self.approvals:
            if approval["id"] == approval_id:
                approval.update(
                    {
                        "status": status,
                        "decided_at": now,
                        "decided_by": actor,
                        "decision_note": note,
                    }
                )
                return deepcopy(approval)
        return None

    def add_audit(self, audit: dict[str, Any]) -> dict[str, Any]:
        self.audit_runs.append(deepcopy(audit))
        return deepcopy(audit)


store = DemoStore()
