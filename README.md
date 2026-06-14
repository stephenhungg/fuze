# fuze

federated understanding & zero-trust execution.

fuze is a local-first memory and governance layer for always-on business agents.
the hackathon demo target is nonprofit grant reporting, but the architecture
should stay skill-driven and runtime-agnostic.

## thesis

cloud agents are context-starved because organizations cannot safely give them
all internal context. fuze keeps broad private context inside the local trust
boundary, then applies governance at retrieval, output, and action time.

## demo workflow

goal:

> get us ready for the anderson foundation report.

conceptual flow:

1. retrieve operational context
2. apply skill-specific policy
3. produce a context packet
4. draft safe action packets
5. ask for approval before external actions
6. update audit and memory

## repo shape

```text
api/
  main.py
  db.py
  ingest.py
  graph_memory.py
  retrieval.py
  agent.py
  policy.py
  skills/
    nonprofit_grants.yaml
web/
sample_data/
precomputed/
offline/
docs/
```

## planned endpoints

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

## scaffold status

this repo is intentionally scaffold-only right now. the files define boundaries,
contracts, and demo fixtures, but do not implement the app logic yet.
