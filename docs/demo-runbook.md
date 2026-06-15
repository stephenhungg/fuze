# demo runbook

## gb10 url

open:

```text
http://promaxgb10-5d0c:8000
```

fallback ip from the venue setup:

```text
http://10.104.132.14:8000
```

## services

```bash
systemctl status fuze-api
systemctl status ollama
docker ps
```

expected:

- `fuze-api` active
- `ollama` active
- `fuze-qdrant` running

## restart

```bash
sudo systemctl restart fuze-api
sudo systemctl restart ollama
docker restart fuze-qdrant
```

## smoke test

```bash
./offline/verify_demo.sh
```

or manually:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS -X POST http://127.0.0.1:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"get us ready for the anderson foundation report","role":"grant_manager"}'
```

look for:

- `cloud_llm_calls: 0`
- `always_on.enabled: true`
- `qdrant.seeded: true`
- `identity.provider: demo-adapter`
- `skill_label: Nonprofit Grants`
- `readiness_score: 72`
- three tasks
- blocked context present
- agent stream events present
- sse observability endpoint advertised
- onboarding flow includes identity, docs, and agent activation

## identity proof

in the left panel, use the identity selector:

- `Morgan · grant_manager` shows grant-team context
- `Casey · case_manager` shows role-aware blocking for external grant output

the api proof:

```bash
curl -fsS http://127.0.0.1:8000/identity/users
```

## agent mesh proof

```bash
curl -fsS http://127.0.0.1:8000/agents/status
curl -fsS http://127.0.0.1:8000/agents/events
curl -fsS http://127.0.0.1:8000/observability/summary
curl -N http://127.0.0.1:8000/events/stream
```

stop the sse curl with `ctrl-c` after the first few events.

## onboarding proof

```bash
curl -fsS http://127.0.0.1:8000/onboarding/flow
```

## vector memory proof

```bash
curl -fsS -X POST http://127.0.0.1:8000/demo/seed
curl -fsS -X POST http://127.0.0.1:8000/tools/vector_search \
  -H 'Content-Type: application/json' \
  -d '{"query":"anderson foundation volunteer hours","limit":3}'
```

expected collection: `fuze_context`.

## pitch packet

```bash
curl -fsS http://127.0.0.1:8000/demo/pitch
```

talk track: `docs/pitch.md`.
