# product context

## product direction

fuze is an on-prem agent hub for nonprofits and regulated teams.

the dell gb10 is the shared local appliance. staff do not download models or
configure agents on their own laptops. they use a browser dashboard while the
gb10 hosts:

- long-running workflow agents
- shared local inference
- vector and graph memory
- policy enforcement
- approvals
- audit logs
- dashboard event streams

## nonprofit wedge

nonprofits are the first wedge because they have high-value private context and
low technical capacity:

- grant requirements
- donor and funder records
- program metrics
- volunteer operations
- board packets
- sensitive case notes
- compliance deadlines

the product promise is:

```text
plug in the dell, connect your systems, invite staff, and get governed agents
watching your nonprofit operations.
```

the demo vertical is grant reporting, but the platform should support more
nonprofit skills:

- grant readiness
- donor updates
- volunteer gap monitoring
- board packet prep
- compliance deadline monitoring
- case note governance

## centralized local inference

fuze should not load a separate large model for every agent.

the target architecture is:

```text
one shared local inference runtime
one vector memory service
one graph/structured memory service
one policy/audit layer
many lightweight logical agents
```

logical agents are async workers/state machines that call the shared model
runtime only when needed.

## a2a-style agent mesh

the dell should run a local agent mesh. agents communicate through explicit
messages and context packets rather than rummaging through raw files.

core agents:

- index agent: watches connectors/folders, parses docs, updates qdrant and graph memory
- graph memory agent: maintains entities, relationships, owners, deadlines, and citations
- policy agent: labels sensitivity, checks pii, applies role and output rules
- workflow agents: grant readiness, donor updates, volunteer ops, compliance
- approval agent: routes high-risk actions to humans
- audit agent: records context, policy checks, model/runtime, actions, and approvals
- dashboard agent: streams status and events to the ui

example handoff:

```text
grant readiness agent
-> asks memory agent for get_context(anderson report)
-> memory agent returns nodes, evidence, citations, missing info
-> policy agent filters context for the current role/output
-> grant agent drafts tasks and report sections
-> approval agent gates external export
-> audit agent records the run
-> dashboard streams progress
```

the demo currently implements this as one api with clear boundaries. the product
direction is to split those boundaries into long-running agents behind the same
local trust boundary.

## identity and role mapping

fuze should not own enterprise identity. it should consume existing identity and
map users/groups into fuze roles used by policy checks.

target integrations:

- small nonprofits: local user directory or csv import
- google workspace: oauth/oidc group mapping
- microsoft entra id / active directory: oidc/saml/ldap group mapping
- larger enterprises: okta/entra/saml/oidc
- legacy/internal: ldap/ad group sync

conceptual flow:

```text
ad / entra id / ldap / okta
-> oidc / saml / ldap sync
-> fuze identity adapter
-> users + groups + roles
-> policy engine + context packets
```

demo role examples:

- `executive_director`
- `grant_manager`
- `program_lead`
- `case_manager`
- `volunteer_coordinator`
- `board_viewer`

example group mapping:

- `cn=grant-team` -> `grant_manager`
- `cn=programs` -> `program_lead`
- `cn=case-management` -> `case_manager`
- `cn=executive` -> `executive_director`
- `cn=board` -> `board_viewer`

policy behavior:

- role controls which context may enter the context packet
- output type controls what may leave the system
- case managers may see more sensitive context internally
- external donor/grant outputs still block raw pii and raw case notes
- high-risk external sends/exports require approval

## dashboard onboarding

nontechnical onboarding should feel like:

1. choose a mission template, such as grants or volunteer ops
2. connect folders, exports, google drive, crm dumps, or shared drives
3. map users/groups to roles
4. enable skills/agents
5. watch the dashboard stream readiness, missing info, blocked context, tasks,
   approvals, and audit trails

## current demo versus product-next

implemented now:

- local gb10 api/ui
- ollama model runtime
- qdrant vector memory
- seeded nonprofit grant workflow
- demo identity adapter with active directory / entra-style group-to-role mapping
- dashboard identity switcher for role-aware context packets
- policy-filtered context packet
- tasks, drafts, approval packet, audit trail
- always-on monitor
- pitch packet and verifier

product-next:

- real identity adapter wired to microsoft entra id, active directory, ldap, okta,
  google workspace, or local csv import
- persistent graph database
- connector onboarding
- event bus for agent-to-agent messages
- long-running index/policy/workflow/audit agents
- dashboard stream timeline
- role switcher and approval queue ui
