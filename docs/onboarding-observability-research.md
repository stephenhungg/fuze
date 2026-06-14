# onboarding and observability research

## sources checked

- fastapi supports streaming responses from generators, which is the local
  backend shape used for server-sent events.
  source: https://fastapi.tiangolo.com/advanced/custom-response/
- sse is a standard http server-to-client stream with `event`, `id`, `data`,
  and blank-line-delimited messages. it fits live logs, ai progress, and
  observability without requiring websocket state.
  source: https://fastapi.tiangolo.com/tutorial/server-sent-events/
- opentelemetry is the vendor-neutral path for production traces, metrics, and
  logs. the demo should use stable event/metric names now so an otel collector
  can be added later without renaming everything.
  source: https://opentelemetry.io/docs/
- microsoft entra provisioning is built around scim 2.0-compatible endpoints for
  users and groups. fuze should consume identity, not become the identity source
  of truth.
  source: https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups
- microsoft graph delta queries track users, groups, and files without a full
  rescan every time. graph change notifications are the push/webhook side.
  sources: https://learn.microsoft.com/en-us/graph/delta-query-overview and
  https://learn.microsoft.com/en-us/graph/change-notifications-overview
- microsoft 365 file discovery at scale starts from drives, uses delta queries,
  and can pair with webhooks for notifications.
  source: https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/scan-guidance
- qdrant retrieval should store metadata payloads and filter by fields such as
  org, source, role, sensitivity, and external-output permission.
  source: https://qdrant.tech/documentation/search/filtering/
- ingestion should be a pipeline of transformations with caching/document
  management so unchanged docs are skipped and changed docs are reprocessed.
  source: https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/
- raw documents should be partitioned into typed elements before chunking.
  source: https://docs.unstructured.io/open-source/core-functionality/partitioning

## optimal onboarding flow

the clean flow for a nonprofit or low-technical-skill org is:

1. choose a mission template
2. connect identity
3. map groups to roles
4. connect document sources
5. ingest and classify
6. activate agents
7. watch observability, approvals, and audit

this avoids asking users to understand models, embeddings, qdrant, or policy
engines upfront. they start with a concrete operational template, then fuze
walks them through the minimum admin choices that determine safety.

## identity and ad management

fuze should use this identity stack:

- login: oidc or saml
- provisioning: scim 2.0 for users and groups
- microsoft sync: graph delta queries and change notifications
- legacy sync: ldap/ad group sync
- source of truth: the external identity provider
- fuze-owned state: role mappings, policy labels, approvals, and audit records

important product rule: if a user/group came from entra/ad/okta/google, fuze
should not pretend to be the place where that account is edited. fuze can map,
review, and audit groups, but the source identity system owns membership.

## docs ingestion

the index agent should treat ingestion as an auditable pipeline:

```text
connector change
-> partition document into typed elements
-> chunk by section/semantic boundary
-> classify sensitivity and allowed roles
-> embed locally
-> upsert qdrant payloads
-> update graph entities and edges
-> emit index-agent event
```

minimum payload fields for qdrant:

- `org_id`
- `source_id`
- `source_type`
- `title`
- `section`
- `chunk_index`
- `allowed_roles`
- `sensitivity`
- `external_output_allowed`
- `citations`
- `document_hash`
- `updated_at`

## observability

the demo now exposes:

- `GET /observability/summary`
- `GET /events/stream`

the production direction is:

- keep sse for the browser dashboard because it is simple and firewall-friendly
- keep a short local event buffer for the live ui
- export traces, metrics, and logs through opentelemetry when moving beyond demo
- track agent run latency, queue depth, approval latency, blocked context count,
  ingestion lag, qdrant availability, ollama availability, and cloud llm calls
- treat `cloud_llm_calls = 0` as a first-class safety metric

## dashboard shape

the dashboard should have four operational views:

- mission workflow: tasks, drafts, approvals, readiness
- observability: live sse stream, agent health, event counts, runtime status
- governance: blocked context, policy checks, approval decisions, audit trail
- onboarding/admin: identity source, group-role mappings, doc connectors, ingest
  health, enabled agents

for the hackathon demo, these are represented inside one page. for product, they
should become separate nav items with role-based access.
