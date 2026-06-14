# architecture

## layers

1. local runtime/model layer
2. identity and role mapping layer
3. ingestion/index layer
4. vector and graph memory layer
5. skill layer
6. retrieval/context layer
7. a2a-style agent mesh
8. policy/governance layer
9. approval and audit layer
10. dashboard/event stream layer

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

## a2a-style mesh

target agents:

- index agent
- graph memory agent
- policy agent
- workflow agents
- approval agent
- audit agent
- dashboard agent

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
- `POST /tools/get_context`
- `POST /tools/prepare_report`
- `POST /tools/policy_check`
- `POST /tools/create_tasks`
- `POST /tools/vector_search`
