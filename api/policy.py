"""policy and governance checks for fuze demo outputs."""

from __future__ import annotations

import re
from typing import Any


PII_PATTERNS = [
    re.compile(r"\b\d{1,5}\s+[a-z][a-z\s]+(?:ave|avenue|st|street|rd|road|blvd)\b", re.I),
    re.compile(r"\bage\s+\d{1,2}\b", re.I),
    re.compile(r"\bclient\s+[a-z]+\b", re.I),
]


def is_blocked(chunk: dict[str, Any], role: str, external: bool) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    allowed_roles = set(chunk.get("allowed_roles", []))
    if allowed_roles and role not in allowed_roles:
        reasons.append(f"role `{role}` is not allowed")
    if external and not chunk.get("external_output_allowed", False):
        reasons.append("not allowed in external output")
    if chunk.get("sensitivity") == "restricted" and role != "case_manager":
        reasons.append("restricted sensitivity")
    if external and contains_pii(chunk.get("text", "")):
        reasons.append("pii detected")
    return bool(reasons), reasons


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS)


def redact(text: str) -> str:
    redacted = text
    for pattern in PII_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    return redacted


def evaluate_output(text: str, citations: list[str], external: bool = True) -> dict[str, Any]:
    checks = [
        {
            "id": "no_raw_client_pii_external",
            "status": "pass" if not external or not contains_pii(text) else "fail",
            "detail": "external output contains no raw client pii.",
        },
        {
            "id": "cite_all_metrics",
            "status": "pass" if citations else "fail",
            "detail": "metric claims are backed by source citations.",
        },
        {
            "id": "approval_required_external",
            "status": "needs_approval" if external else "pass",
            "detail": "external send/export is prepared but not executed.",
        },
    ]
    return {
        "passed": all(check["status"] in {"pass", "needs_approval"} for check in checks),
        "checks": checks,
        "redacted_text": redact(text),
    }
