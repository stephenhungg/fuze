# architecture scaffold

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
