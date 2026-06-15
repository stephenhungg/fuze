# personal agents

fuze provisions one lightweight personal agent per employee, hosted on the dell
gb10. these agents do not each load their own large model. they share the local
ollama runtime, qdrant, graph memory, policy engine, approvals, and audit stream.

## runtime shape

each employee agent gets a scoped home:

```text
/var/lib/fuze/agents/{user_id}/
  workspace/
  memory/
  skills/
  mcp/
  logs/
  runs/
  tmp/
  secrets/
  cron/
```

the supervisor writes a bash env with:

- `FUZE_AGENT_ID`
- `FUZE_USER_ID`
- `FUZE_USER_ROLE`
- `FUZE_USER_GROUPS`
- `FUZE_WORKSPACE`
- `FUZE_MEMORY_DIR`
- `FUZE_SKILLS_DIR`
- `FUZE_MCP_CONFIG`
- `FUZE_CONTEXT_CORE_URL`
- `OLLAMA_HOST`
- `QDRANT_URL`
- `NO_CLOUD_LLM_CALLS=1`

## mcp tool registry

default servers:

- `fuze-context-core`: local mcp-style context server for org questions,
  citations, graph traversal, and retrieval evals
- `fuze-filesystem`: scoped workspace file access
- `fuze-bash`: bash/script execution with audit and approval gates
- `fuze-web-search`: public web search with citations, blocked from receiving
  restricted org context
- `fuze-approvals`: human approval requests and audit events

## cron and heartbeat

default schedules:

- heartbeat every minute
- memory refresh every five minutes
- morning digest at 8am on weekdays
- role skill watch every fifteen minutes

these schedules are meant to run under a supervisor on the dell. the current demo
exposes the contract and event proof through api endpoints.

## security boundaries

- personal agents query `fuze-context-core`; they do not rummage through raw
  shared drives directly
- context packets are role-aware and policy-filtered before prompt assembly
- public web search is allowed, but restricted org context, pii, case notes,
  donor secrets, and secrets cannot be sent to the web-search tool
- destructive bash actions require approval
- command, tool call, context query, external fetch, heartbeat, and approval
  events are audit records

## implemented api

- `GET /personal-agents`
- `GET /personal-agents/{user_id}`
- `POST /personal-agents/provision`
- `POST /personal-agents/{user_id}/heartbeat`

`GET /agents/status` also includes a compact `personal_agents` summary for the
dashboard and sse observability proof.
