# todo

- [x] inspect current retrieval, vector memory, and graph boundaries
- [x] add local context core query contract for agent-to-agent retrieval
- [x] rank vector hits, traverse graph nodes, and return a policy-filtered context packet
- [x] expose context core in api, verifier, docs, and dashboard
- [x] run tests locally and on gb10

## review

- context core now has an explicit `/context/query` contract with local vector search, ephemeral graph traversal, policy filtering, selected evidence, blocked evidence, citations, and zero-cloud runtime proof.
- verified locally and on the gb10 with pytest plus `offline/verify_demo.sh`.
