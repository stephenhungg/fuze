# 5-minute pitch

## 0:00 - hook

cloud agents are powerful, but inside companies they are context-starved.
the best business context is private: donor records, grant requirements,
meeting notes, case notes, metrics, approvals, and internal owners.

most orgs cannot safely hand all of that to a cloud agent.

fuze fixes that by turning the dell gb10 into an on-prem agent hub: shared local
inference, governed organizational memory, long-running agents, and dashboard
streams for staff.

## 0:45 - what fuze is

fuze is federated understanding & zero-trust execution.

it is not a generic rag chatbot. basic rag does:

```text
question -> vector search -> answer
```

fuze does:

```text
goal -> operational context -> policy -> action packet -> approval -> audit
```

the agent can know more because the data stays local, and it can act more safely
because every retrieval/output/action is policy checked.

for nonprofits, this matters because staff should not have to download models or
learn ai infrastructure. they log into a dashboard, while the gb10 hosts the
agents, memory, permissions, approvals, and audit trail.

## 1:30 - demo setup

demo vertical: nonprofit grant reporting.

goal:

```text
get us ready for the anderson foundation report
```

the organization has scattered local context:

- grant requirements
- program metrics
- board notes
- volunteer ownership data
- sensitive case notes

fuze activates the nonprofit grants skill, traverses the memory graph, retrieves
evidence, blocks sensitive context, creates tasks, drafts follow-ups, prepares a
report outline, and records an audit packet.

## 2:15 - live demo beats

open:

```text
http://promaxgb10-5d0c:8000
```

show the left panel:

- local-first mode
- cloud llm calls: `0`
- ollama online
- qdrant online
- always-on monitor status
- qdrant seeded with local embeddings

show the graph:

```text
Anderson Foundation
-> Grant Agreement
-> Reporting Requirements
-> Program Metrics
-> Missing Volunteer Hours
-> Jordan
```

show the outcome:

- readiness score: `72%`
- missing info: may volunteer hours, approved anonymized story
- tasks: Jordan, Sarah, story approval
- drafts: report outline and follow-up emails
- blocked context: minor name, address, raw case note
- approvals required before external export

## 3:45 - why this matters

grant reporting is just the demo wedge. the product category is broader:
local-first context-to-action for business workflows where private context is
valuable but risky.

examples:

- sales account planning with private crm notes
- finance close with internal docs
- healthcare admin workflows
- hr/compliance packet prep
- enterprise support escalation

fuze lets companies run always-on agents inside the trust boundary without
turning governance into an afterthought.

the wedge is nonprofits with limited technical capacity. the expansion path is
regulated teams that need the same on-prem pattern with stronger identity
integration.

## 4:30 - technical proof

the demo runs on the gb10:

- `fuze-api` systemd service
- local ollama models: qwen3 8b/14b/32b and nomic-embed-text
- qdrant docker container
- qdrant collection: `fuze_context`
- local embeddings through ollama
- no cloud llm calls
- always-on monitor loop
- audit trail with policy checks and approvals
- centralized agent hub pattern: many lightweight logical agents sharing one
  local inference runtime
- product-next identity: active directory / entra id / ldap / okta group mapping
  into fuze roles and policies

## rubric mapping

local-first + always-on:

- runs on the gb10
- uses local ollama and qdrant
- cloud llm calls are `0`
- always-on monitor refreshes state over time
- staff access through the dashboard instead of installing local models

business value:

- turns scattered nonprofit reporting context into concrete tasks, drafts, and
  approval packets
- finds missing info before deadline
- prevents sensitive case-note leakage
- fits low-technical-capacity nonprofits through template-based onboarding and
  role-based permissions

demo + pitch:

- single goal input
- graph traversal visualization
- readiness score
- tasks/drafts/audit/policy trail

technical execution:

- tested backend endpoints
- browser verified live gb10 ui
- qdrant seeded and searched with local embeddings
- boot-enabled services for fuze, ollama, and qdrant
