# architecture

## layers

1. local runtime/model layer
2. identity and role mapping layer
3. ingestion/index layer
4. vector and graph memory layer
5. skill layer
6. retrieval/context layer
7. a2a-style agent mesh
8. personal agent runtime layer
9. policy/governance layer
10. approval and audit layer
11. dashboard/event stream layer

## deployment shape

fuze should be deployed as a centralized local agent hub on the dell gb10.
staff use a browser dashboard; they do not install models locally.

```text
staff dashboard / internal portal
        |
fuze api + auth/rbac
        |
local agent mesh on the dell
        |
shared inference + qdrant + graph memory + audit
```

logical agents share one local inference runtime. fuze should not load a
separate large model for each agent.

personal employee agents share the same runtime. the per-user unit is a scoped
home, bash env, mcp registry, skills, cron, memory, logs, and worker state. it
is not a separate qwen process.

## identity model

fuze consumes existing identity instead of owning it.

```text
ad / entra id / ldap / okta
-> oidc / saml / ldap sync
-> fuze identity adapter
-> users + groups + roles
-> policy engine + context packets
```

demo roles:

- `executive_director`
- `grant_manager`
- `program_lead`
- `case_manager`
- `volunteer_coordinator`
- `board_viewer`

role mapping determines which context enters a packet. output policy determines
what can leave the system.

implemented demo:

- `GET /identity/users` returns seeded users and group mappings
- `GET /identity/directory` returns directory sync status, users, groups, and
  group-to-role mappings
- `POST /identity/sync` simulates an entra/ad graph delta sync without taking
  ownership of directory membership
- `POST /identity/group-role-map` updates fuze-owned group-to-role mappings
- `GET /identity/access-preview/{user_id}` previews allowed and blocked context
  for a user before a workflow runs
- the dashboard identity selector switches between seeded users
- context packets include `user`, `role`, and `groups`
- audit packets record the same identity fields
- the demo adapter models active directory / entra-style group mapping without
  requiring real directory setup at the venue

implemented agent stream:

- `GET /agents/status` returns registered logical agents and recent events
- `GET /agents/events` returns the recent event stream
- `GET /events/stream` streams those events to the dashboard over sse
- `GET /observability/summary` returns dashboard counters and runtime stream
  metadata
- manual and always-on runs emit index, policy, workflow, approval, and audit
  events
- the dashboard renders agent mesh status and recent handoffs
- `GET /personal-agents` exposes per-employee agent homes, bash env, mcp
  servers, web-search policy, skills, cron entries, quotas, audit policy, and
  shared-service bindings
- `POST /personal-agents/provision` records a provisioning event for an employee
  agent and returns the folder/env/mcp/cron/worker actions the gb10 supervisor
  would apply

## onboarding/admin flow

implemented demo endpoint:

- `GET /onboarding/flow` returns the recommended org setup path, identity
  management model, and document ingestion model

target setup flow:

```text
mission template
-> identity connection
-> group-to-role mapping
-> document connectors
-> local ingestion/classification
-> agent activation
-> personal agent provisioning
-> observability + approvals + audit
```

fuze should use oidc/saml for login, scim 2.0 for user/group provisioning,
graph delta/change notifications for microsoft 365 changes, ldap sync for
legacy ad, and local policy mappings for fuze roles.

## a2a-style mesh

target agents:

- index agent
- graph memory agent
- policy agent
- workflow agents
- approval agent
- audit agent
- dashboard agent
- personal agent supervisor

workflow agents request context packets from memory/index agents. policy agents
filter context before drafts or actions are produced. approval and audit agents
record every high-risk handoff.

## key abstraction

`get_context(goal, org_id, skill, constraints)` should return a context packet:

- relevant nodes
- evidence snippets
- citations
- missing info
- allowed context
- blocked context
- confidence/readiness
- recommended actions

the stronger product boundary is the local context core: an mcp-style memory
server hosted on the gb10. agents ask it questions about the organization; it
does not call a cloud llm. the context core performs:

```text
agent question
-> deterministic query plan with entity/source hints
-> dense vector search in qdrant
-> lexical sparse search over local chunks
-> ephemeral graph walker expands connected evidence nodes
-> reciprocal rank fusion across dense, lexical, and graph rankers
-> policy-aware rerank and source-diverse packing
-> context packet with citations, blocked context, and traversal proof
```

implemented demo endpoint:

- `POST /context/query`
- `GET /context/eval`

the response includes `server`, `vector_hits`, `hybrid_retrieval`,
`graph_traversal`, `context_packet`, `selected_context`, `blocked_context`,
`citations`, and `runtime`. this is the contract future workflow agents should
use instead of querying raw files directly.

`GET /context/eval` measures the local context core against golden nonprofit
questions. the eval checks source recall, graph-node recall, blocked-source
recall, hybrid stage coverage, rerank readiness, and policy guardrails while
keeping cloud llm calls at zero.

## demo path

```text
Anderson Foundation
-> Grant Agreement
-> Reporting Requirements
-> Program Metrics
-> Missing Volunteer Hours
-> Jordan
```

## runtime

- api/ui: `fastapi` served from `api/main.py`
- local model status: `ollama` at `OLLAMA_HOST`, default `http://127.0.0.1:11434`
- local embeddings: `nomic-embed-text` through ollama
- deterministic venue fallback: in-memory seed data in `api/db.py`
- vector/runtime infra on gb10: qdrant docker container `fuze-qdrant`
- qdrant collection: `fuze_context`, seeded through `POST /demo/seed`

## product context

see `docs/product-context.md` for the nonprofit wedge, onboarding model,
identity/role mapping, and agent mesh direction.

## implemented endpoints

- `GET /health`
- `POST /demo/seed`
- `POST /agent/run`
- `GET /graph`
- `GET /tasks`
- `GET /audit`
- `GET /observability/summary`
- `GET /events/stream`
- `GET /onboarding/flow`
- `GET /identity/directory`
- `POST /identity/sync`
- `POST /identity/group-role-map`
- `GET /identity/access-preview/{user_id}`
- `GET /personal-agents`
- `GET /personal-agents/{user_id}`
- `POST /personal-agents/provision`
- `POST /personal-agents/{user_id}/heartbeat`
- `POST /tools/get_context`
- `POST /context/query`
- `GET /context/eval`
- `POST /tools/prepare_report`
- `POST /tools/policy_check`
- `POST /tools/create_tasks`
- `POST /tools/vector_search`
