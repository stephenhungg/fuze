# context packet

the context packet is the boundary between raw organizational memory and the
agent/action layer.

fields:

- `goal`
- `org_id`
- `skill`
- `user`
- `role`
- `groups`
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

## identity-aware retrieval

in the product architecture, context packets are role-aware.

identity providers such as microsoft entra id, active directory, ldap, okta, or
google workspace map users and groups into fuze roles. those roles constrain:

- which documents and graph nodes can be retrieved
- whether sensitive context may appear internally
- whether context can appear in external outputs
- whether an approval gate is required

example:

```text
cn=grant-team -> grant_manager
cn=case-management -> case_manager
cn=board -> board_viewer
```

the same raw memory can produce different packets depending on the requester and
the target output.

implemented demo proof:

- `morgan` belongs to `cn=grant-team` and maps to `grant_manager`
- `casey` belongs to `cn=case-management` and maps to `case_manager`
- the dashboard role switcher re-runs the context packet with the selected
  identity
- audit output records user, role, and groups
