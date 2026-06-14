# context packet

the context packet is the boundary between raw organizational memory and the
agent/action layer.

fields:

- `goal`
- `org_id`
- `skill`
- `relevant_nodes`
- `evidence`
- `citations`
- `missing_info`
- `allowed_context`
- `blocked_context`
- `readiness_score`
- `recommended_actions`
- `policy_results`
- `audit_ref`

the implemented demo returns allowed context with citations and blocked context
with policy reasons plus redacted previews.
