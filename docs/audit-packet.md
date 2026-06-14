# audit packet

every `/agent/run` produces an audit packet.

fields:

- `goal`
- `skill_activated`
- `graph_path_traversed`
- `sources_used`
- `context_allowed`
- `context_blocked`
- `policy_checks`
- `actions_created`
- `approvals_required`
- `model_runtime`

the demo audit explicitly records `cloud_calls: 0`.
