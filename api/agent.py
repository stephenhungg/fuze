"""agent/action boundary for the fuze demo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import policy, retrieval
from . import runtime
from .db import DEMO_GOAL, store


def history_text(history: list[dict[str, Any]] | None) -> str:
    if not history:
        return ""
    text_parts: list[str] = []
    for message in history[-10:]:
        if not isinstance(message, dict):
            continue
        text = message.get("text") or message.get("message") or message.get("content") or ""
        if text:
            text_parts.append(str(text))
    return " ".join(text_parts).lower()


def expand_followup_goal(goal: str, history: list[dict[str, Any]] | None = None) -> str:
    """turn short follow-ups into standalone questions before retrieval."""
    question = goal.lower().strip()
    if not question:
        return goal

    thread = history_text(history)
    has_anderson_context = "anderson" in thread or "foundation report" in thread
    if not has_anderson_context or "anderson" in question:
        return goal

    if any(term in question for term in ["approval", "approve", "gate", "export", "review"]):
        return "what approvals are needed for the anderson report?"
    if any(term in question for term in ["source", "citation", "evidence", "doc", "document"]):
        return "what sources support the anderson report?"
    if any(term in question for term in ["blocked", "sensitive", "pii", "private", "policy", "case note"]):
        return "what sensitive context is blocked for the anderson report?"
    if any(term in question for term in ["owner", "who", "responsible", "jordan", "sarah"]):
        return "who owns the missing items for the anderson report?"
    if any(term in question for term in ["draft", "email", "write", "send", "follow-up", "followup"]):
        return "draft the jordan follow-up for the anderson report"
    if question in {"what", "why", "how", "that", "more", "again", "next"} or len(question.split()) <= 2:
        return "what else matters for the anderson report?"

    return goal


def create_tasks() -> list[dict[str, Any]]:
    tasks = [
        {
            "id": "task-jordan-volunteer-hours",
            "title": "ask Jordan for May volunteer hours",
            "owner": "Jordan",
            "status": "open",
            "priority": "high",
            "due": "today",
            "source": "program_metrics.csv#may",
        },
        {
            "id": "task-sarah-attendance",
            "title": "ask Sarah to confirm attendance data",
            "owner": "Sarah",
            "status": "open",
            "priority": "medium",
            "due": "today",
            "source": "program_metrics.csv#may",
        },
        {
            "id": "task-approved-story",
            "title": "approve third anonymized story",
            "owner": "program lead",
            "status": "approval_required",
            "priority": "high",
            "due": "before report export",
            "source": "case_notes.txt#maya",
        },
    ]
    return store.add_tasks(tasks)


def prepare_report(context: dict[str, Any] | None = None) -> dict[str, Any]:
    packet = context or store.last_context or retrieval.get_context()
    citations = packet["citations"]
    outline = [
        {
            "section": "executive summary",
            "draft": "Harbor Light is on track for the Anderson Foundation report, with aggregate meal and attendance metrics ready and two missing items queued for owner follow-up.",
            "citations": ["grant_requirements.txt#reporting", "program_metrics.csv#may"],
        },
        {
            "section": "impact metrics",
            "draft": "May delivery includes 1,284 meals served and 412 youth attendance records. May volunteer hours are still pending Jordan's update.",
            "citations": ["program_metrics.csv#may"],
        },
        {
            "section": "narrative",
            "draft": "Use an approved anonymized participant story only. Raw case notes and identifying details remain blocked by policy.",
            "citations": ["board_minutes.txt#approval"],
        },
        {
            "section": "approval packet",
            "draft": "Human approval is required before exporting or sending the report to the Anderson Foundation.",
            "citations": ["grant_requirements.txt#reporting"],
        },
    ]
    followups = [
        {
            "to": "Jordan",
            "subject": "May volunteer hours for Anderson report",
            "body": "Can you send the final May volunteer hours today? The Anderson Foundation report is due June 20, and this is the remaining metric gap.",
            "approval_required": False,
        },
        {
            "to": "Sarah",
            "subject": "Confirm May attendance total",
            "body": "Can you confirm the May youth attendance total of 412 before we lock the Anderson report packet?",
            "approval_required": False,
        },
        {
            "to": "program lead",
            "subject": "Approve anonymized story for Anderson report",
            "body": "Please approve one anonymized story for the Anderson narrative section. Raw case notes are blocked from external output.",
            "approval_required": True,
        },
    ]
    external_text = "\n".join(section["draft"] for section in outline)
    policy_result = policy.evaluate_output(external_text, citations=citations, external=True)
    return {
        "outline": outline,
        "followups": followups,
        "policy_result": policy_result,
        "approvals_required": [
            "external report export",
            "third anonymized story",
        ],
    }


def create_approvals(context: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    approvals = [
        {
            "id": "approval-external-report-export",
            "title": "approve external Anderson report export",
            "owner_role": "executive_director",
            "requested_by": context["user"]["id"],
            "risk": "external_output",
            "reason": "external funder delivery must be reviewed before any send/export action.",
            "source": "grant_requirements.txt#reporting",
            "required_for": report["approvals_required"][0],
        },
        {
            "id": "approval-third-anonymized-story",
            "title": "approve anonymized participant story",
            "owner_role": "program_lead",
            "requested_by": context["user"]["id"],
            "risk": "sensitive_story",
            "reason": "raw case notes are blocked; only a reviewed anonymized story can leave the local boundary.",
            "source": "case_notes.txt#maya",
            "required_for": report["approvals_required"][1],
        },
    ]
    return store.add_approvals(approvals)


def answer_goal(
    goal: str,
    context: dict[str, Any],
    tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    report: dict[str, Any],
) -> str:
    question = goal.lower().strip()
    sources = ", ".join(context["citations"][:3])
    missing = context.get("missing_info", [])
    missing_line = ""
    if missing:
        missing_line = f"the main gap is {missing[0]['label']}, owned by {missing[0]['owner']}."

    if question in {"hi", "hello", "hey", "yo", "sup"}:
        return (
            "hey — i’m here.\n\n"
            "ask me something concrete like:\n"
            "- what do we need for the anderson report?\n"
            "- who owns the missing volunteer hours?\n"
            "- draft the jordan follow-up\n"
            "- what sensitive context is blocked?"
        )

    if question in {"what", "why", "how", "help"} or len(question.split()) <= 1:
        return (
            "i need a little more direction.\n\n"
            "try asking about a report, owner, deadline, donor update, approval, blocked context, or a document source."
        )

    if "anderson" in question and any(term in question for term in ["approval", "approve", "gate", "export", "review"]):
        approval_titles = "; ".join(approval["title"] for approval in approvals[:2])
        return (
            "approvals for the anderson report:\n\n"
            f"- required gates: {approval_titles}\n"
            "- executive director: must approve the external report export before anything leaves fuze\n"
            "- program lead: must approve the anonymized participant story before it can be used\n"
            "- automatic guardrail: raw case notes and identifying details stay blocked from external output\n\n"
            f"sources: {sources}"
        )

    if "anderson" in question and any(term in question for term in ["source", "citation", "evidence", "doc", "document"]):
        cited = "; ".join(context["citations"][:5])
        allowed_titles = "; ".join(item["title"] for item in context["allowed_context"][:4])
        return (
            "sources for the anderson report:\n\n"
            f"- retrieved evidence: {allowed_titles}\n"
            f"- citations fuze can attach: {cited}\n"
            "- blocked evidence: raw case-note details are visible to policy checks but not allowed in external text\n\n"
            "that means the report can cite grant requirements, program metrics, approved story-bank material, and board approval evidence."
        )

    if "anderson" in question and any(term in question for term in ["blocked", "sensitive", "pii", "private", "policy", "case note"]):
        blocked = context.get("blocked_context", [])
        blocked_lines = "; ".join(f"{item['title']} ({', '.join(item['reasons'])})" for item in blocked[:3])
        return (
            "blocked context for the anderson report:\n\n"
            f"- policy-blocked items: {blocked_lines or 'none in the current packet'}\n"
            "- safe substitute: use an approved anonymized participant story from the story bank\n"
            "- action rule: fuze can draft internally, but external export waits for human approval\n\n"
            f"sources: {sources}"
        )

    if "anderson" in question and any(term in question for term in ["who", "owner", "responsible"]):
        owners = sorted({task["owner"] for task in tasks})
        return (
            "current owners for the anderson report:\n\n"
            f"- active owners: {', '.join(owners)}\n"
            "- jordan: missing may volunteer-hours update\n"
            "- sarah: attendance confirmation before the packet is locked\n"
            "- program leadership: anonymized story approval\n"
            "- executive director: final external export approval\n\n"
            "raw case notes stay blocked for external output."
        )

    if "anderson" in question and any(term in question for term in ["need", "required", "report", "ready", "missing"]):
        requirements = [
            "meals served",
            "youth attendance",
            "may volunteer hours",
            "budget variance",
            "one approved anonymized participant story",
        ]
        open_tasks = "; ".join(f"{task['owner']}: {task['title']}" for task in tasks[:3])
        approval_titles = "; ".join(approval["title"] for approval in approvals[:2])
        return (
            "for the anderson report, fuze found:\n\n"
            f"- required: {', '.join(requirements)}\n"
            "- already supported: meals served, youth attendance, and budget variance\n"
            f"- gap: {missing_line}\n"
            f"- next actions: {open_tasks}\n"
            f"- approvals before export: {approval_titles}\n\n"
            f"sources: {sources}"
        )

    if "anderson" in question and "else matters" in question:
        return (
            "the important anderson-report thread is:\n\n"
            "- the report is mostly ready, but may volunteer hours are still missing from jordan\n"
            "- sarah should confirm the attendance total before the packet is locked\n"
            "- one anonymized story still needs program-lead approval\n"
            "- external export needs executive-director approval\n"
            "- raw case notes stay blocked, even if they are useful for internal reasoning\n\n"
            f"sources: {sources}"
        )

    if any(term in question for term in ["who", "owner", "responsible"]):
        owners = sorted({task["owner"] for task in tasks})
        return (
            "current owners:\n\n"
            f"- active owners: {', '.join(owners)}\n"
            "- jordan: missing volunteer-hours update\n"
            "- sarah: attendance confirmation\n"
            "- program leadership: story approval\n\n"
            "raw case notes stay blocked for external output."
        )

    if any(term in question for term in ["draft", "email", "write", "send"]):
        followups = report["followups"]
        first = followups[0]
        return (
            "i can draft that inside fuze.\n\n"
            f"- first safe follow-up: {first['to']} — {first['subject']}\n"
            "- external export still needs approval\n"
            "- sensitive story/case-note content stays blocked unless reviewed"
        )

    context_titles = "; ".join(item["title"] for item in context["allowed_context"][:3])
    return (
        "i checked the local context core.\n\n"
        f"- relevant evidence: {context_titles}\n"
        f"- gap: {missing_line or 'none found in this packet'}\n"
        f"- workflow: {len(tasks)} open task(s), {len(approvals)} approval gate(s)\n\n"
        f"sources: {sources}"
    )


def response_kind(goal: str) -> str:
    question = goal.lower().strip()
    if question in {"hi", "hello", "hey", "yo", "sup", "what", "why", "how", "help"} or len(question.split()) <= 1:
        return "clarifying"
    return "workflow"


def run_agent(goal: str = DEMO_GOAL, role: str = "grant_manager", user_id: str | None = None) -> dict[str, Any]:
    context = retrieval.get_context(goal=goal, role=role, user_id=user_id, external=True)
    tasks = create_tasks()
    report = prepare_report(context)
    approvals = create_approvals(context, report)
    execution = runtime.local_execution_mode()
    inference_probe = runtime.local_inference_probe(goal, context.get("readiness_score"))
    audit = {
        "id": f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "goal": goal,
        "skill_activated": context["skill_label"],
        "user": context["user"],
        "role": context["role"],
        "groups": context["groups"],
        "graph_path_traversed": context["graph_path"],
        "sources_used": context["citations"],
        "context_allowed": [item["id"] for item in context["allowed_context"]],
        "context_blocked": [
            {"id": item["id"], "source": item["source"], "reasons": item["reasons"]}
            for item in context["blocked_context"]
        ],
        "policy_checks": report["policy_result"]["checks"],
        "actions_created": [task["id"] for task in tasks],
        "approvals_required": report["approvals_required"],
        "approval_ids": [approval["id"] for approval in approvals],
        "model_runtime": {
            "provider": execution["provider"],
            "execution_mode": execution["mode"],
            "inference": execution["inference"],
            "routing_model": "qwen3:8b",
            "planning_model": "qwen3:14b",
            "embedding_model": "nomic-embed-text",
            "local_inference": inference_probe,
            "cloud_calls": 0,
        },
        "identity_runtime": {
            "provider": "demo-adapter",
            "source": "active directory / entra-style group mapping",
            "role": context["role"],
            "groups": context["groups"],
        },
    }
    store.add_audit(audit)
    return {
        "status": "ready_for_review",
        "goal": goal,
        "response": answer_goal(goal, context, tasks, approvals, report),
        "response_kind": response_kind(goal),
        "context_packet": context,
        "tasks": tasks,
        "approvals": approvals,
        "drafts": report,
        "audit": audit,
    }


def pitch_packet() -> dict[str, Any]:
    return {
        "one_liner": "fuze is a local-first memory and governance layer for always-on business agents.",
        "problem": "companies cannot safely pour broad private context into cloud agents, so those agents stay context-starved.",
        "insight": "local ai moves the context boundary onto the gb10, but local still needs governance at retrieval, output, and action time.",
        "demo_goal": DEMO_GOAL,
        "demo_result": {
            "readiness_score": 72,
            "skill": "Nonprofit Grants",
            "tasks_created": [
                "ask Jordan for May volunteer hours",
                "ask Sarah to confirm attendance data",
                "approve third anonymized story",
            ],
            "blocked_context": ["minor name", "address", "raw case note"],
            "approvals_required": ["external report export", "third anonymized story"],
        },
        "technical_proof": [
            "target runtime runs on the gb10 through fuze-api, ollama, and qdrant",
            "uses local ollama models and nomic-embed-text embeddings when gb10 runtime is configured",
            "seeds/searches qdrant collection fuze_context",
            "keeps cloud llm calls at 0",
            "always-on monitor refreshes readiness/audit state",
            "local agent mesh streams index, policy, workflow, approval, and audit events",
            "policy checks block pii while preserving audit evidence",
        ],
        "rubric_mapping": {
            "local_first_always_on": "gb10 service target, local ollama, qdrant, always-on monitor, cloud calls 0",
            "business_value": "grant reporting readiness workflow with missing-info tasks, drafts, and approval packet",
            "demo_pitch": "three-panel ui shows goal, graph traversal, readiness, drafts, blocked context, and audit",
            "technical_execution": "tested fastapi app, retrieval endpoints, and browser checks; gb10 runtime requires secure tunnel config for prod",
        },
    }
