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

## run locally

```bash
python3 -m pip install -r requirements.txt
./offline/run_local.sh
```

open `http://localhost:8000`.

on the gb10 venue box, the service is installed as `fuze-api` and is available
at `http://promaxgb10-5d0c:8000`.

## demo status

the repo now implements a deterministic local-first vertical slice for the
anderson foundation report workflow:

- seeded nonprofit grant memory
- context packet retrieval
- policy-filtered allowed and blocked context
- readiness score, missing information, tasks, report outline, follow-up drafts
- audit packet with graph path, sources, policy checks, approvals, and model runtime
- always-on local monitor loop that refreshes readiness/audit state while the service runs
- zero-build browser ui served by the backend

ollama/qdrant are runtime infrastructure on the gb10. the app does not make
cloud llm calls.

see `docs/demo-runbook.md` for venue restart and smoke-test commands.
