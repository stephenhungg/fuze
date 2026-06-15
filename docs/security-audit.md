# security audit

date: 2026-06-14

## bottom line

production does not currently ping the dell gb10.

`https://fuze.stephenhung.me` is a vercel-hosted fastapi/static demo with seeded nonprofit sample data. it proves the product flow, context retrieval contract, policy gates, audit packet shape, and zero cloud llm claim for the demo path, but it is not currently executing on the gb10 and it is not securely connected to the venue machine.

that is good enough for a public synthetic demo. it is not good enough for real nonprofit donor pii, case notes, phi, hipaa, or soc 2 claims.

## current production topology

```mermaid
flowchart lr
  browser["browser"]
  vercel["vercel serverless fastapi + static app"]
  memory["in-memory seeded demo store"]
  browser --> vercel
  vercel --> memory
```

what this means:

- there is no public tunnel from vercel to the dell.
- there is no ssh from production to the dell.
- there is no ollama, qdrant, or local model runtime exposed on the public internet.
- the prod api self-seeds synthetic sample data so the demo keeps working in serverless cold starts.
- `cloud_llm_calls` remains `0`, but that is because the public demo does not call any llm.
- `/system/runtime` now reports this explicitly. if `FUZE_GB10_RUNTIME_URL` is not set, it returns `hosted_preview`. if a secured gb10 tunnel url is set, it pings that runtime's `/health`.

## target secure topology

for the hackathon and early pilots, the clean model is:

```mermaid
flowchart lr
  user["authorized user"]
  edge["public control plane"]
  access["oidc + device posture + allowlist"]
  tunnel["cloudflare tunnel / tailscale / wireguard"]
  gateway["gb10 api gateway"]
  agents["local agents + ollama"]
  memory["qdrant + graph + audit store"]

  user --> edge
  edge --> access
  access --> tunnel
  tunnel --> gateway
  gateway --> agents
  gateway --> memory
```

rules:

- never expose ollama, qdrant, ssh, or the raw fastapi app directly to the internet.
- terminate public access through an identity-aware tunnel or vpn.
- require oidc/saml login, short-lived sessions, and role claims before any agent or context endpoint runs.
- put a small gateway in front of the gb10 runtime that enforces auth, rbac, rate limits, request size limits, tenant scoping, audit logging, and response redaction.
- keep phi/pii off vercel. vercel can host marketing and a thin control plane, but sensitive inference and retrieval should stay on the gb10 or customer-controlled infrastructure.

## hipaa posture

status: not compliant.

hipaa is not a sticker we can slap on because the model is local. hhs describes the security rule as requiring administrative, physical, and technical safeguards for ephi, plus risk analysis and reasonable protections for confidentiality, integrity, and availability.

current gaps:

- no covered-entity/business-associate determination.
- no baa story for any vendor involved in production.
- no formal risk analysis.
- no real user authentication.
- no unique user sessions.
- no enforced rbac on server routes.
- no audit controls that prove who accessed what over time.
- no immutable audit log.
- no encryption-at-rest story for production data.
- no key management story.
- no backup and disaster recovery controls.
- no retention/deletion policy.
- no incident response procedure.
- no device/security posture controls for the gb10.
- no physical security plan for a venue/customer appliance.

minimum before touching phi:

- synthetic data only until the above is closed.
- full-disk encryption on the gb10.
- private network access only.
- sso with unique users and group claims.
- server-side rbac on every api route.
- structured audit events for login, context query, retrieval source, policy block, approval, export, and admin changes.
- signed/append-only audit log.
- explicit export approval gates.
- no prompt, document, or generated answer leaves the local environment unless approved.

## soc 2 posture

status: not ready.

soc 2 is an attestation over organizational and technical controls. aicpa trust services criteria cover security, availability, processing integrity, confidentiality, and privacy. the product direction maps well to that, but the current repo is still a hackathon prototype.

current gaps:

- no production change-management process beyond git/vercel.
- no access review process.
- no vulnerability management process.
- no dependency review or sbom.
- no incident response runbook.
- no vendor risk register.
- no backup evidence.
- no uptime/error monitoring with alert ownership.
- no log retention and tamper-evidence policy.
- no tenant isolation tests.
- no security headers/csp hardening.
- no formal data classification policy.

good product primitives already present:

- role-aware context packets.
- policy blocking before prompt assembly.
- approval queue.
- audit packet shape.
- zero cloud llm claim in the demo path.
- local retrieval architecture with graph traversal and hybrid ranking.

## code-level findings

### critical

- admin routes are not protected. `/admin`, `/identity/*`, `/ingestion/run`, `/approvals/*`, and `/audit` are public demo endpoints.
- role is accepted from client request bodies. a user can request a stronger role unless server-side auth claims override it.
- public production copy can imply gb10-backed execution even though vercel is currently self-contained.

### high

- audit logs are in memory and mutable.
- no tenant/org isolation enforcement.
- no rate limiting on agent, ingestion, identity, or sse endpoints.
- no csrf/session model because there is no real auth.
- no csp or security headers.
- no encryption-at-rest implementation in the app layer.

### medium

- frontend stores selected demo users in `localStorage`.
- frontend uses `innerHTML` heavily, mostly with escaping helpers, but the safest long-term path is typed rendering/components.
- health endpoint exposes runtime details publicly.
- sse stream is unauthenticated and public.

## remediation plan

### now, for the hackathon

- keep public prod synthetic-only.
- label public prod as hosted demo preview if needed.
- demo true local-first execution from the gb10 on the venue network.
- do not ingest real nonprofit documents.
- do not expose the gb10 directly.

### secure gb10 demo path

- run the gb10 api on localhost or a private interface.
- expose it through tailscale, cloudflare tunnel with access, or wireguard.
- require sso before tunnel access.
- put the api behind a gateway that validates jwt claims and maps groups to roles.
- disable public access to ollama and qdrant.
- allow only `/health`, `/context/query`, `/agent/run`, `/events/stream`, and admin endpoints needed for the demo.
- record every request and policy decision to append-only local logs.

### pilot-ready path

- replace demo identity with oidc/saml and scim.
- derive role from signed identity claims, not the request body.
- add server-side authorization dependencies to every route.
- persist data in encrypted postgres/sqlite plus qdrant with encrypted disk.
- add tenant ids to every source, chunk, graph node, audit event, approval, and task.
- add csp/security headers/rate limits/request body limits.
- build admin access reviews and audit export.
- add backup/restore tests.
- add a data retention and deletion workflow.
- create incident response, vendor risk, access review, and change management evidence folders.

## safe demo language

say:

- "the public site is a hosted demo preview using synthetic nonprofit data."
- "the gb10 path is designed to run the agent runtime, retrieval, and local models without cloud llm calls."
- "for real deployments, sensitive context stays behind a private network boundary with sso, rbac, audit, and approval gates."

do not say yet:

- "production runs on the dell."
- "hipaa compliant."
- "soc 2 compliant."
- "safe for real phi today."
