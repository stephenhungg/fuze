# todo

- [x] audit current production-to-dell security posture
- [x] document hipaa/soc2 readiness gaps and secure connectivity plan
- [x] patch misleading gb10 production copy
- [x] run verification after security/docs changes

## security audit

- current production at `fuze.stephenhung.me` is a vercel-hosted demo and does not ping, tunnel to, ssh into, or execute on the dell gb10.
- the public app is acceptable only for synthetic demo data right now.
- do not claim production is hipaa compliant, soc 2 compliant, or on-prem execution until auth, tunnel, audit, encryption, retention, evidence, and organizational controls are implemented.

- [x] replace the root landing page with the supplied architectural landing direction
- [x] keep workspace routing and chat interface unchanged
- [x] verify locally, deploy, and smoke-test production
- [x] add more generated landing assets and svg architecture where appropriate

## current landing update

- scope the zip's visual system to `/` only: dark architectural surface, sharp grid, large type, orange accent.
- adapt the content to fuze's local-first nonprofit appliance story instead of the template's agency copy.
- avoid remote landing assets so the page stays aligned with the offline/local-first demo.
- generated a local hero bitmap for the landing and preserved the reference motion language with gsap reveal, stagger, counters, and parallax.
- matched the palette reference: vibrant orange, off-white, grey sand, deep taupe, and pitch black.
- added generated document-ingestion and observability/approval visuals, plus an inline svg architecture diagram for the local context core flow.

- [x] inspect current retrieval, vector memory, and graph boundaries
- [x] add local context core query contract for agent-to-agent retrieval
- [x] rank vector hits, traverse graph nodes, and return a policy-filtered context packet
- [x] expose context core in api, verifier, docs, and dashboard
- [x] run tests locally and on gb10
- [x] upgrade retrieval beyond basic rag with hybrid fusion, graph expansion, and reranking
- [x] add retrieval eval harness for golden nonprofit questions

## review

- context core now has an explicit `/context/query` contract with local vector search, ephemeral graph traversal, policy filtering, selected evidence, blocked evidence, citations, and zero-cloud runtime proof.
- verified locally and on the gb10 with pytest plus `offline/verify_demo.sh`.
- context core now avoids naive top-k rag by fusing dense, lexical, and graph candidate rankers with rrf, then applying policy-aware rerank and source-diverse packing.
- context eval now runs three golden nonprofit questions and reports source recall, graph-node recall, blocked-source recall, hybrid stage coverage, rerank readiness, and policy guardrails.
