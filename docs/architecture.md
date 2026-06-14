# architecture

## layers

1. local runtime/model layer
2. ingestion layer
3. memory layer
4. skill layer
5. retrieval/context layer
6. agent/action layer
7. policy/governance layer
8. audit layer

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
