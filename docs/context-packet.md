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

## local context core

the production retrieval path should be a local mcp-style context server, not
ad hoc file search inside each workflow agent.

implemented query:

```text
POST /context/query
GET /context/eval
```

the request carries `question`, `user_id`, `role`, `external`, and `limit`.
the response contains:

- `server`: local context-core identity and zero cloud calls
- `vector_hits`: dense qdrant hits or deterministic fallback
- `hybrid_retrieval`: query plan, lexical hits, graph hits, rrf fusion, reranked
  hits, and source-diverse packing
- `graph_traversal`: ephemeral graph-walker seeds, nodes, edges, and path
- `context_packet`: the role-aware packet used by agents
- `selected_context`: the allowed evidence selected for the current question
- `blocked_context`: redacted policy-blocked evidence with reasons
- `runtime`: retrieval stack proof for audit and demo

this is the “ask the organization” layer. agents query it for context; they do
not each own their own index, graph traversal, or policy filters. the demo path
is intentionally not naive top-k rag: dense retrieval, lexical retrieval, and
graph expansion are fused with reciprocal rank fusion, then reranked with policy
and source diversity before prompt assembly.

`GET /context/eval` runs golden nonprofit retrieval cases against the same local
context core. it scores source recall, graph-node recall, blocked-source recall,
hybrid stage coverage, rerank readiness, and policy guardrails. this gives the
demo a measurable answer to “is this better than basic rag?” without calling any
cloud service.

implemented demo proof:

- `morgan` belongs to `cn=grant-team` and maps to `grant_manager`
- `casey` belongs to `cn=case-management` and maps to `case_manager`
- the dashboard role switcher re-runs the context packet with the selected
  identity
- audit output records user, role, and groups
